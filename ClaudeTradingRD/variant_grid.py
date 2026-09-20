"""Grid search over sweep-reversal exit/stop/filter variants on OANDA XAU 1m.

Question: which configurations reach 50-60% win rate, and what do they pay?
Levers vs the base system (retest entry, tight stop, liquidity TP):
  - stop width:   tight (extreme+0.1pen) | wide (extreme+0.5pen) | leg origin
  - target:       1.0x / 1.5x / 2.0x penetration | nearest liquidity
  - breakeven:    move SL to entry once trade is +1R in profit (scratches)
  - displacement: confirmation bar body >= 1.2 x ATR20 (quality filter)

Run: python variant_grid.py   (needs xau_m1_oanda.parquet from fetch_oanda_m1.py)
"""

import numpy as np
import pandas as pd

from backtest_sweep_reversal import detect_sweeps, FAST_BARS, PEN_PCTL, \
    WARMUP_EVENTS, MIN_RR, ENTRY_TTL, HORIZON

COST = 0.30
DISP_MIN = 1.2


def simulate(df, sweeps, stop_mode, tp_mode, be_move, disp_filter):
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    atr = pd.Series(h - l).rolling(20).mean().values
    n = len(df)
    rows = []
    busy_until = -1
    pen_hist = []

    for ev in sweeps:
        qualifies = (ev.kind in ("PD", "session") or len(pen_hist) < WARMUP_EVENTS
                     or ev.m_pen >= np.quantile(pen_hist, PEN_PCTL))
        pen_hist.append(ev.m_pen)
        if ev.conf_i <= busy_until or ev.manip_bars > FAST_BARS or not qualifies:
            continue
        if disp_filter:
            a = atr[ev.conf_i]
            if not a or abs(c[ev.conf_i] - o[ev.conf_i]) < DISP_MIN * a:
                continue

        sign = -1 if ev.direction == "down" else 1
        if stop_mode == "tight":
            stop = ev.extreme - sign * 0.1 * ev.m_pen
        elif stop_mode == "wide":
            stop = ev.extreme - sign * 0.5 * ev.m_pen
        else:  # leg origin
            stop = ev.extreme - sign * (ev.m_pen + 0.5 * ev.m_pen)  # beyond leg midpoint proxy

        # retest limit entry at the swept level
        entry = ev.level
        fill_i = None
        for x in range(ev.conf_i + 1, min(ev.conf_i + 1 + ENTRY_TTL, n)):
            if (sign < 0 and h[x] >= entry) or (sign > 0 and l[x] <= entry):
                blown = h[x] >= stop if sign < 0 else l[x] <= stop
                fill_i = -1 if blown else x
                break
        if fill_i in (None, -1):
            continue

        risk = abs(stop - entry)
        if risk <= 0:
            continue
        if tp_mode == "liquidity":
            if ev.target is None:
                continue
            tp = ev.target
        else:
            tp = entry + sign * float(tp_mode) * ev.m_pen
        if abs(tp - entry) / risk < MIN_RR:
            continue

        be_trigger = entry + sign * risk
        cur_stop = stop
        outcome, exit_px, exit_i = None, None, min(fill_i + HORIZON, n - 1)
        for x in range(fill_i + 1, min(fill_i + HORIZON, n)):
            hit_sl = h[x] >= cur_stop if sign < 0 else l[x] <= cur_stop
            hit_tp = l[x] <= tp if sign < 0 else h[x] >= tp
            if hit_sl:
                outcome, exit_px, exit_i = "SL", cur_stop, x
                break
            if hit_tp:
                outcome, exit_px, exit_i = "TP", tp, x
                break
            if be_move and cur_stop == stop:
                fav = l[x] <= be_trigger if sign < 0 else h[x] >= be_trigger
                if fav:
                    cur_stop = entry
        if outcome is None:
            outcome, exit_px = "TIME", c[exit_i]

        pnl = sign * (exit_px - entry) - COST
        rows.append({"time": df["time"].iloc[fill_i], "r": pnl / risk,
                     "outcome": outcome})
        busy_until = exit_i
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_parquet("xau_m1_oanda.parquet")
    sweeps = detect_sweeps(df)
    print(f"{len(df):,} bars, {len(sweeps)} sweeps\n")
    results = []
    for stop_mode in ("tight", "wide", "leg"):
        for tp_mode in ("1.0", "1.5", "2.0", "liquidity"):
            for be in (False, True):
                for disp in (False, True):
                    tr = simulate(df, sweeps, stop_mode, tp_mode, be, disp)
                    if len(tr) < 30:
                        continue
                    wr = (tr.r > 0).mean()
                    pf = tr.r[tr.r > 0].sum() / max(1e-9, -tr.r[tr.r <= 0].sum())
                    eq = tr.r.cumsum()
                    results.append({
                        "stop": stop_mode, "tp": tp_mode, "BE": be, "disp": disp,
                        "n": len(tr), "WR%": round(100 * wr),
                        "avgR": round(tr.r.mean(), 3), "netR": round(tr.r.sum(), 1),
                        "PF": round(pf, 2), "maxDD": round((eq - eq.cummax()).min(), 1),
                    })
    res = pd.DataFrame(results).sort_values("netR", ascending=False)
    pd.set_option("display.width", 140)
    print("── all variants by netR ──")
    print(res.to_string(index=False))
    print("\n── variants with WR >= 45% ──")
    print(res[res["WR%"] >= 45].to_string(index=False))
    res.to_csv("variant_grid_results.csv", index=False)
