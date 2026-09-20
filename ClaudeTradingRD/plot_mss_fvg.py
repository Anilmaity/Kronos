"""Plot S99 MSS+FVG reversal setups on XAUUSD M5 (lightweight-charts -> PNG).

Faithful offline port of KronosStrategies backtest_strategies/s99_mss_fvg.py:
  sweep : rolling 48-bar extreme takes the last CONFIRMED fractal swing
  MSS   : the last closed M5 bar closes through the OPPOSITE confirmed swing
  FVG   : the displacement leaves a 3-bar gap (high[k] < low[k-2] for shorts)
  entry : first retrace to the proximal FVG edge within 24 bars (SL-first fill)
  stop  : distal edge +/- 0.2*ATR(14) ;  tp = 1.5R ;  hours 6-15 UTC ; hold 480m

Chart per setup:
  gray line   swept swing level (buy/sell-side liquidity taken)
  dashed gray opposite swing the MSS closed through
  orange box  the fair-value gap (proximal <-> distal edge)
  blue arrow  retrace entry at the proximal edge
  red / green SL / TP levels from entry to exit
  circle      exit marker (TP/SL/TIME) with realised R

Usage:  python plot_mss_fvg.py [--trades N] [--shot]
        (screen is headless -> --shot writes mss_fvg_chart.png)
"""
import sys
import threading
import time

import numpy as np
import pandas as pd
from lightweight_charts import Chart

# ── S99 knobs (validated 2026-07-06, hours trimmed 2026-07-07) ────────────────
SWEEP_N   = 48
RETRACE_W = 24
TP_R      = 1.5
BUF_ATR   = 0.2
ATR_N     = 14
SWING_W   = 2
HOURS     = set(range(6, 16))
MAX_HOLD  = 96            # 480 min / 5
COST_PT   = 0.45          # round-trip cost used in S99 validation
EXIT_NEXT_BAR = False     # True = scan exits from the bar AFTER the fill
                          # (optimize_manager_strategies house convention;
                          # False keeps this script's original fill-bar exits)
N_TRADES  = 12


def load_m5(path="xau_m1_oanda.parquet"):
    m1 = pd.read_parquet(path).set_index("time").sort_index()
    m5 = m1.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    return m5.reset_index()


def confirmed_swings_asof(h, l, w):
    """conf_hi[j]/conf_lo[j] = value of the last fractal swing CONFIRMED by
    bar j (a swing at i confirms at i+w; strict vs the w bars just before)."""
    n = len(h)
    conf_hi = np.full(n, np.nan)
    conf_lo = np.full(n, np.nan)
    last_hi = last_lo = np.nan
    hi_at = {}
    lo_at = {}
    for i in range(w, n - w):
        if h[i] == h[i - w:i + w + 1].max() and (h[i] > h[i - w:i]).all():
            hi_at[i + w] = float(h[i])
        if l[i] == l[i - w:i + w + 1].min() and (l[i] < l[i - w:i]).all():
            lo_at[i + w] = float(l[i])
    for j in range(n):
        if j in hi_at:
            last_hi = hi_at[j]
        if j in lo_at:
            last_lo = lo_at[j]
        conf_hi[j] = last_hi
        conf_lo[j] = last_lo
    return conf_hi, conf_lo


def atr_series(h, l, c, n):
    prev = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    return pd.Series(tr).rolling(n).mean().to_numpy()


def backtest(m5):
    h = m5["high"].to_numpy(float)
    l = m5["low"].to_numpy(float)
    c = m5["close"].to_numpy(float)
    hr = m5["time"].dt.hour.to_numpy()
    conf_hi, conf_lo = confirmed_swings_asof(h, l, SWING_W)
    atr = atr_series(h, l, c, ATR_N)
    n = len(c)
    trades = []
    busy_until = -1                       # max_concurrent_positions = 1

    for k in range(SWEEP_N + 3, n - 1):
        if k <= busy_until or hr[k] not in HOURS:
            continue
        shi, slo = conf_hi[k - 1], conf_lo[k - 1]
        a = atr[k]
        if np.isnan(shi) or np.isnan(slo) or not (a > 0):
            continue
        roll_hi = h[k - SWEEP_N:k].max()
        roll_lo = l[k - SWEEP_N:k].min()

        side = 0
        if roll_hi > shi and c[k] < slo and h[k] < l[k - 2]:
            side, prox, dist = -1, h[k], l[k - 2]
            sl = round(dist + BUF_ATR * a, 2)
        elif roll_lo < slo and c[k] > shi and l[k] > h[k - 2]:
            side, prox, dist = 1, l[k], h[k - 2]
            sl = round(dist - BUF_ATR * a, 2)
        if side == 0:
            continue
        risk = abs(sl - prox)
        if risk <= 0:
            continue
        tp = round(prox + side * TP_R * risk, 2)

        # ── retrace to the proximal edge over the next RETRACE_W bars ──────────
        fill_i = None
        for j in range(k + 1, min(k + 1 + RETRACE_W, n)):
            if hr[j] not in HOURS:
                break
            if side < 0:
                if h[j] >= sl:
                    break                 # phantom: ran through the stop first
                if h[j] >= prox:
                    fill_i = j
                    break
            else:
                if l[j] <= sl:
                    break
                if l[j] <= prox:
                    fill_i = j
                    break
        if fill_i is None:
            continue

        # ── exit: SL-first intrabar, else TP, else TIME backstop ──────────────
        outcome, exit_i, exit_px = "TIME", min(fill_i + MAX_HOLD, n - 1), None
        for m in range(fill_i + (1 if EXIT_NEXT_BAR else 0),
                       min(fill_i + MAX_HOLD, n)):
            if side < 0:
                if h[m] >= sl:
                    outcome, exit_i, exit_px = "SL", m, sl
                    break
                if l[m] <= tp:
                    outcome, exit_i, exit_px = "TP", m, tp
                    break
            else:
                if l[m] <= sl:
                    outcome, exit_i, exit_px = "SL", m, sl
                    break
                if h[m] >= tp:
                    outcome, exit_i, exit_px = "TP", m, tp
                    break
        if exit_px is None:
            exit_px = c[exit_i]

        r = side * (exit_px - prox) / risk - COST_PT / risk
        trades.append(dict(k=k, side=side, prox=float(prox), dist=float(dist),
                           sl=float(sl), tp=float(tp), risk=float(risk),
                           swept=float(shi if side < 0 else slo),
                           through=float(slo if side < 0 else shi),
                           fill_i=fill_i, exit_i=exit_i, exit_px=float(exit_px),
                           outcome=outcome, r=float(r)))
        busy_until = exit_i
    return trades


def main():
    n_show = N_TRADES
    if "--trades" in sys.argv:
        n_show = int(sys.argv[sys.argv.index("--trades") + 1])

    m5 = load_m5()
    trades = backtest(m5)
    done = trades
    wr = np.mean([t["r"] > 0 for t in done]) if done else 0.0
    net = sum(t["r"] for t in done)
    gross_w = sum(t["r"] for t in done if t["r"] > 0)
    gross_l = -sum(t["r"] for t in done if t["r"] < 0)
    pf = gross_w / gross_l if gross_l else float("inf")
    print(f"S99 MSS+FVG  n={len(done)}  WR {100*wr:.0f}%  PF {pf:.2f}  net {net:+.0f}R")

    show = trades[-n_show:]
    if not show:
        print("no setups found")
        return
    lo = max(0, min(t["k"] - 6 for t in show) - 20)
    hi = min(len(m5) - 1, max(t["exit_i"] for t in show) + 12)
    sub = m5.iloc[lo:hi + 1].reset_index(drop=True)
    t = sub["time"].dt.tz_localize(None).astype("datetime64[ns]")

    def gi(idx):                          # global -> sub-frame index (clamped)
        return int(min(max(idx - lo, 0), len(sub) - 1))

    chart = Chart(width=1500, height=850, toolbox=True,
                  title=f"S99 MSS+FVG reversal — XAUUSD 5min · last {len(show)}")
    chart.layout(background_color="#DBDBDB", text_color="#000000")
    chart.candle_style(up_color="#089981", down_color="#000000",
                       border_up_color="#000000", border_down_color="#000000",
                       wick_up_color="#000000", wick_down_color="#000000")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox("info", f"MSS+FVG retest · TP {TP_R}R · hrs 6-15 · "
                                 f"{len(done)} trades · WR {100*wr:.0f}% · "
                                 f"PF {pf:.2f} · {net:+.0f}R")
    cdf = sub.copy()
    cdf["time"] = t
    chart.set(cdf.rename(columns={"time": "date"}))

    for tr in show:
        k, side = tr["k"], tr["side"]
        ki, fi, xi = gi(k), gi(tr["fill_i"]), gi(tr["exit_i"])
        # swept liquidity level + the opposite swing the MSS closed through
        chart.trend_line(t[gi(k - 30)], tr["swept"], t[ki], tr["swept"],
                         line_color="#666666", width=1, style="solid")
        chart.trend_line(t[gi(k - 30)], tr["through"], t[ki], tr["through"],
                         line_color="#999999", width=1, style="dashed")
        # the fair-value gap (proximal <-> distal edge), bar k-2 .. entry
        chart.box(t[gi(k - 2)], tr["prox"], t[fi], tr["dist"],
                  color="rgba(255,152,0,0.9)", fill_color="rgba(255,152,0,0.20)",
                  width=1)
        # SL / TP rails from entry to exit
        chart.trend_line(t[fi], tr["sl"], t[xi], tr["sl"],
                         line_color="#F44336", width=1, style="dashed")
        chart.trend_line(t[fi], tr["tp"], t[xi], tr["tp"],
                         line_color="#089981", width=1, style="dashed")
        # entry arrow (points the trade direction)
        chart.marker(time=t[fi], position="below" if side > 0 else "above",
                     shape="arrow_up" if side > 0 else "arrow_down",
                     color="#1E80F0",
                     text=f"{'BUY' if side>0 else 'SELL'} {tr['prox']:.1f}")
        col = {"TP": "#089981", "SL": "#F44336", "TIME": "#9E9E9E"}[tr["outcome"]]
        chart.marker(time=t[xi], position="above" if side > 0 else "below",
                     shape="circle", color=col,
                     text=f"{tr['outcome']} {tr['r']:+.1f}R")

    if "--shot" in sys.argv:
        # Headless: block=True returns immediately here, so screenshot
        # synchronously — render the window non-blocking, let it paint, grab.
        chart.show(block=False)
        try:
            chart.fit()               # frame every plotted setup in the shot
        except Exception:
            pass
        img = None
        for _ in range(20):
            time.sleep(1)
            try:
                img = chart.screenshot()
            except Exception as e:
                print(f"screenshot attempt failed: {e}")
                img = None
            if img and len(img) > 20000:
                break
        if img:
            with open("mss_fvg_chart.png", "wb") as f:
                f.write(img)
            print(f"saved mss_fvg_chart.png ({len(img)} bytes)")
        else:
            print("screenshot never succeeded")
        return

    chart.show(block=True)


if __name__ == "__main__":
    main()
