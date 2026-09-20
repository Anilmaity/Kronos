"""S99 hybrid: sweep + MSS computed on H1, FVG + entry executed on M5.

HTF-structure / LTF-entry port of plot_mss_fvg.py (classic ICT model):
  sweep : rolling 48 H1-bar extreme takes the last CONFIRMED H1 fractal swing
  MSS   : an H1 bar CLOSES through the opposite confirmed H1 swing
  FVG   : the first M5 3-bar gap in the MSS direction, formed during the MSS
          hour (causal: acted on only after the H1 close) or within the next
          FVG_W M5 bars
  entry : first M5 retrace to the proximal FVG edge within RETRACE_W bars
          after the gap (SL-first phantom check), from the H1 close onward
  stop  : distal M5 edge +/- 0.2*ATR(14, M5) ;  tp = 1.5R ;  hours 6-15 UTC
  hold  : 96 M5 bars (480 min — the original S99 backstop)

Chart: M5 candles; gray lines are the H1 swept / MSS swing levels, orange box
the M5 FVG, arrows/circles the M5 entry and exit.

Usage:  python plot_mss_fvg_h1_m5.py [--trades N] [--shot]
        (--shot writes mss_fvg_h1m5_chart.png)
"""
import sys
import time

import numpy as np
import pandas as pd
from lightweight_charts import Chart

from plot_mss_fvg import confirmed_swings_asof, atr_series

# ── knobs ─────────────────────────────────────────────────────────────────────
SWEEP_N   = 48            # H1 bars of liquidity memory (~2 trading days)
SWING_W   = 2             # H1 fractal half-width
FVG_W     = 12            # M5 bars after the H1 close to keep looking for a gap
RETRACE_W = 24            # M5 bars the FVG stays tradeable (as in S99)
TP_R      = 1.5
BUF_ATR   = 0.2
ATR_N     = 14            # ATR(14, M5) for the stop buffer
HOURS     = set(range(6, 16))
MAX_HOLD  = 96            # M5 bars = 480 min (as in S99)
COST_PT   = 0.45
MIN_RISK  = 0.0           # skip setups whose SL distance is below this (pts);
                          # sub-3pt stops are friction-dominated live
EXIT_NEXT_BAR = False     # True = scan exits from the bar AFTER the fill
N_TRADES  = 6


def load_frames(path="xau_m1_oanda.parquet"):
    m1 = pd.read_parquet(path).set_index("time").sort_index()
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    m5 = m1.resample("5min", label="left", closed="left").agg(agg).dropna()
    h1 = m1.resample("1h", label="left", closed="left").agg(agg).dropna()
    return m5.reset_index(), h1.reset_index()


def backtest(m5, h1):
    H = h1["high"].to_numpy(float)
    L = h1["low"].to_numpy(float)
    C = h1["close"].to_numpy(float)
    Hhr = h1["time"].dt.hour.to_numpy()
    conf_hi, conf_lo = confirmed_swings_asof(H, L, SWING_W)

    h = m5["high"].to_numpy(float)
    l = m5["low"].to_numpy(float)
    c = m5["close"].to_numpy(float)
    hr = m5["time"].dt.hour.to_numpy()
    atr5 = atr_series(h, l, c, ATR_N)
    m5_t = m5["time"].to_numpy()
    h1_t = h1["time"].to_numpy()
    n5 = len(c)

    trades = []
    busy_until = -1                       # M5 index; max_concurrent_positions = 1

    for k in range(SWEEP_N + 3, len(C) - 1):
        if Hhr[k] not in HOURS:
            continue
        shi, slo = conf_hi[k - 1], conf_lo[k - 1]
        if np.isnan(shi) or np.isnan(slo):
            continue
        roll_hi = H[k - SWEEP_N:k].max()
        roll_lo = L[k - SWEEP_N:k].min()

        side = 0
        if roll_hi > shi and C[k] < slo:      # buy-side swept, close below swing low
            side = -1
        elif roll_lo < slo and C[k] > shi:    # sell-side swept, close above swing high
            side = 1
        if side == 0:
            continue

        # M5 index of the MSS hour start and of the H1 close (first actionable bar)
        hour_start = int(np.searchsorted(m5_t, h1_t[k]))
        act = int(np.searchsorted(m5_t, h1_t[k] + np.timedelta64(1, "h")))
        if act >= n5 or act <= busy_until:
            continue

        # ── first M5 FVG in the MSS direction: displacement hour .. +FVG_W ────
        fvg_j = None
        for j in range(max(hour_start, 2), min(act + FVG_W, n5)):
            if side < 0 and h[j] < l[j - 2]:
                fvg_j = j
                break
            if side > 0 and l[j] > h[j - 2]:
                fvg_j = j
                break
        if fvg_j is None:
            continue

        if side < 0:
            prox, dist = h[fvg_j], l[fvg_j - 2]
        else:
            prox, dist = l[fvg_j], h[fvg_j - 2]
        a = atr5[fvg_j]
        if not (a > 0):
            continue
        sl = round(dist + BUF_ATR * a, 2) if side < 0 else round(dist - BUF_ATR * a, 2)
        risk = abs(sl - prox)
        if risk <= 0 or risk < MIN_RISK:
            continue
        tp = round(prox + side * TP_R * risk, 2)

        # ── retrace into the gap, from the H1 close onward ────────────────────
        fill_i = None
        scan_from = max(act, fvg_j + 1)
        for jj in range(scan_from, min(fvg_j + 1 + RETRACE_W, n5)):
            if hr[jj] not in HOURS:
                break
            if side < 0:
                if h[jj] >= sl:
                    break                 # phantom: ran through the stop first
                if h[jj] >= prox:
                    fill_i = jj
                    break
            else:
                if l[jj] <= sl:
                    break
                if l[jj] <= prox:
                    fill_i = jj
                    break
        if fill_i is None:
            continue

        # ── exit: SL-first intrabar, else TP, else TIME backstop ──────────────
        outcome, exit_i, exit_px = "TIME", min(fill_i + MAX_HOLD, n5 - 1), None
        for m in range(fill_i + (1 if EXIT_NEXT_BAR else 0),
                       min(fill_i + MAX_HOLD, n5)):
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
                           mss_i=act - 1, fvg_j=fvg_j,
                           fill_i=fill_i, exit_i=exit_i, exit_px=float(exit_px),
                           outcome=outcome, r=float(r)))
        busy_until = exit_i
    return trades


def main():
    n_show = N_TRADES
    if "--trades" in sys.argv:
        n_show = int(sys.argv[sys.argv.index("--trades") + 1])

    m5, h1 = load_frames()
    trades = backtest(m5, h1)
    done = trades
    wr = np.mean([t["r"] > 0 for t in done]) if done else 0.0
    net = sum(t["r"] for t in done)
    gross_w = sum(t["r"] for t in done if t["r"] > 0)
    gross_l = -sum(t["r"] for t in done if t["r"] < 0)
    pf = gross_w / gross_l if gross_l else float("inf")
    print(f"S99 H1-MSS / M5-FVG  n={len(done)}  WR {100*wr:.0f}%  PF {pf:.2f}  net {net:+.1f}R")
    for t_ in done:
        print(f"  {m5['time'][t_['fill_i']].strftime('%m-%d %H:%M')}  "
              f"{'BUY ' if t_['side'] > 0 else 'SELL'}  prox {t_['prox']:.1f}  "
              f"risk {t_['risk']:.1f}  {t_['outcome']:4s}  {t_['r']:+.2f}R")

    show = trades[-n_show:]
    if not show:
        print("no setups found")
        return
    lo = max(0, min(t["fvg_j"] - 6 for t in show) - 30)
    hi = min(len(m5) - 1, max(t["exit_i"] for t in show) + 12)
    sub = m5.iloc[lo:hi + 1].reset_index(drop=True)
    t = sub["time"].dt.tz_localize(None).astype("datetime64[ns]")

    def gi(idx):                          # global -> sub-frame index (clamped)
        return int(min(max(idx - lo, 0), len(sub) - 1))

    chart = Chart(width=1500, height=850, toolbox=True,
                  title=f"S99 H1-MSS / M5-FVG — XAUUSD · last {len(show)}")
    chart.layout(background_color="#DBDBDB", text_color="#000000")
    chart.candle_style(up_color="#089981", down_color="#000000",
                       border_up_color="#000000", border_down_color="#000000",
                       wick_up_color="#000000", wick_down_color="#000000")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox("info", f"H1 structure, M5 entry · TP {TP_R}R · hrs 6-15 · "
                                 f"{len(done)} trades · WR {100*wr:.0f}% · "
                                 f"PF {pf:.2f} · {net:+.1f}R")
    cdf = sub.copy()
    cdf["time"] = t
    chart.set(cdf.rename(columns={"time": "date"}))

    for tr in show:
        side = tr["side"]
        mi, fj, fi, xi = gi(tr["mss_i"]), gi(tr["fvg_j"]), gi(tr["fill_i"]), gi(tr["exit_i"])
        # H1 swept liquidity level + the H1 swing the MSS closed through
        chart.trend_line(t[gi(tr["mss_i"] - 120)], tr["swept"], t[mi], tr["swept"],
                         line_color="#666666", width=1, style="solid")
        chart.trend_line(t[gi(tr["mss_i"] - 120)], tr["through"], t[mi], tr["through"],
                         line_color="#999999", width=1, style="dashed")
        # the M5 fair-value gap (proximal <-> distal edge), formation .. entry
        chart.box(t[gi(tr["fvg_j"] - 2)], tr["prox"], t[fi], tr["dist"],
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
            with open("mss_fvg_h1m5_chart.png", "wb") as f:
                f.write(img)
            print(f"saved mss_fvg_h1m5_chart.png ({len(img)} bytes)")
        else:
            print("screenshot never succeeded")
        return

    chart.show(block=True)


if __name__ == "__main__":
    main()
