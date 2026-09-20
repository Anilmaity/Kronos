"""Out-of-sample validation of the brk1 x 2SD sweep-reversal config.

All parameters were chosen on 2026-04-05..2026-07-06 (in-sample). Everything
before 2026-04-05 is out-of-sample. Detection runs once over the full year;
trades are split by fill date.

Config: HTF15 contained-or-wick validity, retest entry, stop extreme+10% pen,
TP = 2.0 SD of the break-bar manipulation leg (brk1), BE at +1R, $0.30 cost,
overlapping signals.

Run: python validate_oos.py   (needs the 365d xau_m1_oanda.parquet)
"""

import pandas as pd

import backtest_sweep_reversal as bt
from backtest_compare import htf_masks, simulate
from leg_analysis import leg_defs

IS_START = pd.Timestamp("2026-04-05", tz="UTC")


def stats(tr, label):
    if tr.empty:
        print(f"{label}: no trades")
        return
    wr = (tr.r > 0).mean()
    pf = tr.r[tr.r > 0].sum() / max(1e-9, -tr.r[tr.r <= 0].sum())
    eq = tr.r.cumsum()
    dd = (eq - eq.cummax()).min()
    days = max(1, (tr.time.iloc[-1] - tr.time.iloc[0]).days)
    print(f"{label:22s} n={len(tr):4d} ({len(tr)/days*30:.0f}/mo)  "
          f"WR={100*wr:3.0f}%  avgR={tr.r.mean():+.3f}  netR={tr.r.sum():+7.1f}  "
          f"PF={pf:.2f}  maxDD={dd:6.1f}R")


if __name__ == "__main__":
    m1 = pd.read_parquet("xau_m1_oanda.parquet").set_index("time")
    df = m1.resample("5min").agg(open=("open", "first"), high=("high", "max"),
                                 low=("low", "min"), close=("close", "last")
                                 ).dropna().reset_index()
    print(f"XAU 5m: {len(df):,} bars  {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    sweeps = bt.detect_sweeps(df)
    c15, w15 = htf_masks(df, sweeps, 15)
    legs = leg_defs(df, sweeps)["brk1"]
    tr = simulate(df, sweeps, single_pos=False, be=True, allow=c15 | w15,
                  sd_mult=2.0, legs=legs)
    print(f"signals(valid)={int((c15 | w15).sum())}  trades={len(tr)}\n")

    oos = tr[tr.time < IS_START]
    ins = tr[tr.time >= IS_START]
    stats(oos, "OUT-OF-SAMPLE (pre-Apr)")
    stats(ins, "IN-SAMPLE (Apr-Jul)")
    stats(tr, "FULL YEAR")

    print("\nmonthly (full year):")
    for m, g in tr.groupby(tr.time.dt.tz_localize(None).dt.to_period("M")):
        tag = "IS " if pd.Timestamp(str(m)) >= IS_START.tz_localize(None) else "OOS"
        print(f"  {m} [{tag}]  n={len(g):3d}  WR={100*(g.r>0).mean():3.0f}%  "
              f"netR={g.r.sum():+7.1f}")
    tr.to_csv("oos_trades.csv", index=False)
    print("\nsaved oos_trades.csv")
