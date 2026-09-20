"""Plot sweep-reversal signals with manipulation, trend and SD projections.

Default mode = the LOCKED strategy: RAW overlapping signals filtered by
HTF15 contained-or-wick validity, retest entry, stop = extreme + 10% pen,
TP = 2x penetration, breakeven move at +1R.   --raw disables the HTF filter.

Chart annotation per signal:
  - gray line   : the swept liquidity level
  - red line+box: the manipulation leg (origin -> sweep extreme)
  - blue line   : the actual distribution move (extreme -> trade exit)
  - dashed grays: SD projections of the manipulation leg (0.5-2.5x) from the
                  extreme in the reversal direction
  - markers     : entry arrow, TP/SL/TIME exit circle, gray square = NOFILL/SKIP

Usage:  python plot_sweeps.py [--raw] [--shot] [--trades N]
"""

import sys
import threading
import time

import numpy as np
import pandas as pd
from lightweight_charts import Chart

import backtest_sweep_reversal as bt
from backtest_compare import htf_masks

TF = "5min"
STOP_BUF = 0.10      # stop: extreme + 10% of penetration
TP_MULT = 2.0        # target = 2x penetration from entry
BE_MOVE = True       # stop to entry once +1R in profit
COST = 0.30
SD_UNIT = "leg"      # 1 SD = manipulation leg ('leg') or penetration ('pen')
SD_LEVELS = (0.5, 1.0, 1.5, 2.0, 2.5)
N_TRADES = 20


def simulate_detailed(df, sweeps, allow=None):
    """Overlapping signals; allow = per-sweep validity mask (None = all raw).
    NOFILL / SKIP signals are kept so they can be shown on the chart."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    out = []
    for k, ev in enumerate(sweeps):
        if allow is not None and not allow[k]:
            continue
        sign = -1 if ev.direction == "down" else 1

        # manipulation leg = the immediate stab through the level
        brk = ev.conf_i - ev.manip_bars + 1
        lo0 = max(0, brk - 3)
        if sign < 0:
            origin_i = lo0 + int(l[lo0: brk + 1].argmin())
            origin = l[origin_i]
        else:
            origin_i = lo0 + int(h[lo0: brk + 1].argmax())
            origin = h[origin_i]
        seg = (h if sign < 0 else l)[brk: ev.conf_i + 1]
        ext_i = brk + int(seg.argmax() if sign < 0 else seg.argmin())

        stop = ev.extreme - sign * STOP_BUF * ev.m_pen
        entry = ev.level
        tp = entry + sign * TP_MULT * ev.m_pen
        rec = dict(ev=ev, sign=sign, entry=entry, stop=stop, tp=tp,
                   fill_i=ev.conf_i, exit_i=ev.conf_i, exit_px=entry,
                   outcome=None, origin=origin, origin_i=origin_i,
                   ext_i=ext_i, r=0.0)

        fill_i = None
        for x in range(ev.conf_i + 1, min(ev.conf_i + 1 + bt.ENTRY_TTL, n)):
            if (sign < 0 and h[x] >= entry) or (sign > 0 and l[x] <= entry):
                fill_i = -1 if (h[x] >= stop if sign < 0 else l[x] <= stop) else x
                break
        risk = abs(stop - entry)
        if fill_i in (None, -1):
            rec["outcome"] = "NOFILL"
            out.append(rec)
            continue
        if risk <= 0 or abs(tp - entry) / risk < bt.MIN_RR:
            rec["outcome"] = "SKIP"
            out.append(rec)
            continue

        be_trigger = entry + sign * risk
        cur_stop = stop
        outcome, exit_px, exit_i = None, None, min(fill_i + bt.HORIZON, n - 1)
        for x in range(fill_i + 1, min(fill_i + bt.HORIZON, n)):
            if (h[x] >= cur_stop if sign < 0 else l[x] <= cur_stop):
                outcome = "BE" if cur_stop == entry else "SL"
                exit_px, exit_i = cur_stop, x
                break
            if (l[x] <= tp if sign < 0 else h[x] >= tp):
                outcome, exit_px, exit_i = "TP", tp, x
                break
            if BE_MOVE and cur_stop == stop:
                if (l[x] <= be_trigger if sign < 0 else h[x] >= be_trigger):
                    cur_stop = entry
        if outcome is None:
            outcome, exit_px = "TIME", c[exit_i]
        rec.update(fill_i=fill_i, exit_i=exit_i, exit_px=exit_px, outcome=outcome,
                   r=(sign * (exit_px - entry) - COST) / risk)
        out.append(rec)
    return out


def main():
    raw = "--raw" in sys.argv
    n_show = N_TRADES
    if "--trades" in sys.argv:
        n_show = int(sys.argv[sys.argv.index("--trades") + 1])

    m1 = pd.read_parquet("xau_m1_oanda.parquet").set_index("time")
    df = m1.resample(TF).agg(open=("open", "first"), high=("high", "max"),
                             low=("low", "min"), close=("close", "last")
                             ).dropna().reset_index()
    sweeps = bt.detect_sweeps(df)
    allow = None
    if not raw:
        c15, w15 = htf_masks(df, sweeps, 15)
        allow = c15 | w15
    trades = simulate_detailed(df, sweeps, allow=allow)
    done = [t for t in trades if t["outcome"] in ("TP", "SL", "BE", "TIME")]
    wr = np.mean([t["r"] > 0 for t in done]) if done else 0.0
    net = sum(t["r"] for t in done)
    mode = "RAW" if raw else "HTF15 cont|wick"
    print(f"5m bars={len(df):,} [{mode}] signals={len(trades)} traded={len(done)} "
          f"WR={100*wr:.0f}% netR={net:+.1f}")

    s = pd.DataFrame([{
        "time": df["time"].iloc[t["ev"].conf_i], "dir": t["ev"].direction,
        "kind": t["ev"].kind, "manip_bars": t["ev"].manip_bars,
        "m_pen": t["ev"].m_pen, "level": t["ev"].level,
        "extreme": t["ev"].extreme, "outcome": t["outcome"], "r": t["r"],
    } for t in trades])
    csv = "raw_signals_5m.csv" if raw else "htf15_signals_5m.csv"
    s.to_csv(csv, index=False)
    print(f"saved {csv} — outcomes: {s.outcome.value_counts().to_dict()}")

    show = trades[-n_show:]
    t = df["time"].dt.tz_localize(None).astype("datetime64[ns]")

    chart = Chart(width=1400, height=800, toolbox=True,
                  title=f"Sweep reversal — XAUUSD {TF} [{mode}] last {len(show)}")
    chart.layout(background_color="#DBDBDB", text_color="#000000")
    chart.candle_style(up_color="#089981", down_color="#000000",
                       border_up_color="#000000", border_down_color="#000000",
                       wick_up_color="#000000", wick_down_color="#000000")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox("info", f"{mode} · retest+{TP_MULT}x pen+BE · "
                                 f"{len(done)} trades · WR {100*wr:.0f}% · {net:+.1f}R")
    cdf = df.copy()
    cdf["time"] = t
    chart.set(cdf.rename(columns={"time": "date"}))

    for tr in show:
        ev, sign = tr["ev"], tr["sign"]
        brk = ev.conf_i - ev.manip_bars + 1
        leg = abs(ev.extreme - tr["origin"])
        sd = leg if SD_UNIT == "leg" else ev.m_pen

        chart.trend_line(t[max(0, brk - 40)], ev.level, t[ev.conf_i], ev.level,
                         line_color="#666666", width=1)
        chart.box(t[brk], ev.level, t[ev.conf_i], ev.extreme,
                  color="rgba(244,67,54,0.9)", fill_color="rgba(244,67,54,0.25)", width=1)
        chart.trend_line(t[tr["origin_i"]], tr["origin"], t[tr["ext_i"]], ev.extreme,
                         line_color="#F44336", width=2)
        chart.trend_line(t[tr["ext_i"]], ev.extreme, t[tr["exit_i"]], tr["exit_px"],
                         line_color="#1E80F0", width=2)
        end_i = min(tr["exit_i"] + 10, len(df) - 1)
        for k in SD_LEVELS:
            px = ev.extreme + sign * k * sd
            chart.trend_line(t[ev.conf_i], px, t[end_i], px,
                             line_color="rgba(80,80,80,0.55)", width=1)

        if tr["outcome"] in ("NOFILL", "SKIP"):
            chart.marker(time=t[ev.conf_i],
                         position="below" if sign > 0 else "above",
                         shape="square", color="#9E9E9E", text=tr["outcome"])
            continue
        chart.marker(time=t[tr["fill_i"]],
                     position="below" if sign > 0 else "above",
                     shape="arrow_up" if sign > 0 else "arrow_down",
                     color="#1E80F0", text=f"E {tr['entry']:.1f}")
        col = {"TP": "#089981", "SL": "#F44336", "BE": "#FF9800",
               "TIME": "#9E9E9E"}[tr["outcome"]]
        chart.marker(time=t[tr["exit_i"]],
                     position="above" if sign > 0 else "below", shape="circle",
                     color=col, text=f"{tr['outcome']} {tr['r']:+.1f}R")

    first = min(tr["origin_i"] for tr in show) - 30
    chart.run_script(f"{chart.id}.chart.timeScale().setVisibleLogicalRange("
                     f"{{from: {max(0, first)}, to: {len(df) + 5}}});")

    if "--shot" in sys.argv:
        def shot():
            time.sleep(8)
            try:
                with open("sweeps_chart.png", "wb") as f:
                    f.write(chart.screenshot())
                print("saved sweeps_chart.png")
            except Exception as e:
                print(f"screenshot failed: {e}")
        threading.Thread(target=shot, daemon=True).start()

    chart.show(block=True)


if __name__ == "__main__":
    main()
