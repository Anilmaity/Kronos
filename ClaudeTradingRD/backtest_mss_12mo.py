"""12-month comparison of the MSS+FVG variants on one OANDA M1 cache.

Runs the three plot_* backtests (identical knobs, cost 0.45pt) over the full
xau_m1_oanda.parquet window, plus the hybrid with a 3pt minimum-risk floor.
Reports totals, calendar halves, quarterly R, and net at the 0.80pt cost
stress (recomputed per-trade from the stored risk).

Usage:  python backtest_mss_12mo.py
"""
import numpy as np
import pandas as pd

import plot_mss_fvg as m5s
import plot_mss_fvg_h1 as h1s
import plot_mss_fvg_h1_m5 as hyb

COST_BASE   = 0.45
COST_STRESS = 0.80


def load_frames(path="xau_m1_oanda.parquet"):
    m1 = pd.read_parquet(path).set_index("time").sort_index()
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    m5 = m1.resample("5min", label="left", closed="left").agg(agg).dropna()
    h1 = m1.resample("1h", label="left", closed="left").agg(agg).dropna()
    return m5.reset_index(), h1.reset_index()


def stats(trades, times, label):
    """times: pd.Series mapping fill_i -> timestamp for this variant's frame."""
    if not trades:
        print(f"{label:34s}  no trades")
        return
    t_fill = [times[tr["fill_i"]] for tr in trades]
    r = np.array([tr["r"] for tr in trades])
    risk = np.array([tr["risk"] for tr in trades])
    r080 = r - (COST_STRESS - COST_BASE) / risk        # stress the cost per trade

    def block(mask, rs):
        rs = rs[mask]
        if len(rs) == 0:
            return "n=0"
        w = rs[rs > 0]
        l = rs[rs < 0]
        pf = w.sum() / -l.sum() if len(l) and l.sum() < 0 else float("inf")
        return (f"n={len(rs):4d} WR {100 * (rs > 0).mean():4.1f}% "
                f"PF {pf:4.2f} net {rs.sum():+7.1f}R")

    all_mask = np.ones(len(r), bool)
    h1_mask = np.array([ts < pd.Timestamp("2026-01-16", tz="UTC") for ts in t_fill])
    print(f"{label:34s}  {block(all_mask, r)}")
    print(f"{'':34s}  first 6mo : {block(h1_mask, r)}")
    print(f"{'':34s}  last  6mo : {block(~h1_mask, r)}")
    print(f"{'':34s}  @0.80pt   : {block(all_mask, r080)}")
    q = pd.PeriodIndex([pd.Timestamp(ts).tz_convert(None).to_period("Q")
                        for ts in t_fill])
    qr = pd.Series(r).groupby(q).sum()
    print(f"{'':34s}  quarterly R: "
          + "  ".join(f"{p}: {v:+.1f}" for p, v in qr.items()))
    print()


def run_all(m5, h1, header):
    print(f"===== {header} =====\n")
    tr_m5 = m5s.backtest(m5)
    stats(tr_m5, m5["time"], "M5 structure + M5 FVG (S99)")

    tr_h1 = h1s.backtest(h1)
    stats(tr_h1, h1["time"], "H1 structure + H1 FVG")

    hyb.MIN_RISK = 0.0
    tr_hy = hyb.backtest(m5, h1)
    stats(tr_hy, m5["time"], "H1 structure + M5 FVG (hybrid)")

    hyb.MIN_RISK = 3.0
    tr_hy3 = hyb.backtest(m5, h1)
    stats(tr_hy3, m5["time"], "hybrid + 3pt min-risk floor")


def main():
    m5, h1 = load_frames()
    print(f"data: {m5['time'].min()} -> {m5['time'].max()}  "
          f"({len(m5):,} M5 / {len(h1):,} H1 bars)\n")

    for strict in (False, True):
        m5s.EXIT_NEXT_BAR = h1s.EXIT_NEXT_BAR = hyb.EXIT_NEXT_BAR = strict
        run_all(m5, h1, "STRICT: exits from next bar (house convention)"
                if strict else "AS-PLOTTED: fill-bar exits allowed (optimistic)")


if __name__ == "__main__":
    main()
