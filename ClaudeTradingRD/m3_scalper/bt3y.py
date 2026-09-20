"""3-year backtest (2023-07 .. 2026-07): M3 stack (gated) vs S93 upgraded.

All frames resampled from the merged M1 (xau_m1_3y.parquet) for consistency.
Year-by-year: n, tr/day, WR, PF, net pts, maxDD, %positive weeks @0.45pt,
plus PF @0.80pt stress. Then the 3-year equity overlay PNG.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRATCH = Path(__file__).parent
sys.path.insert(0, str(SCRATCH))

from s93_struct_validate import m15_structure_on_m5, run_fvg_scalp_v2  # noqa: E402
from s93_ob_validate import run_combo  # noqa: E402

m1 = pd.read_parquet(SCRATCH / "xau_m1_3y.parquet")
m1["time"] = pd.to_datetime(m1["time"], utc=True)
m1 = m1.sort_values("time").reset_index(drop=True)


def resample(df, freq):
    out = (df.set_index("time").resample(freq)
           .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
           .dropna().reset_index())
    return out


m3 = resample(m1, "3min")
m5 = resample(m1, "5min")
m15 = resample(m1, "15min")
print(f"m1={len(m1):,} m3={len(m3):,} m5={len(m5):,} "
      f"{m1['time'].iloc[0].date()} .. {m1['time'].iloc[-1].date()}")

struct5 = m15_structure_on_m5(m5, m15)
WIDE = tuple(range(1, 16))
STACK_KW = dict(dispm=0.5, ob_break=3, ob_entry="edge", rsi_n=3, rsi_ob=85,
                rsi_os=15, rsi_mode="momentum", max_concurrent=1,
                ema_filter=True)

PERIODS = [
    ("2023H2", "2023-07-01", "2024-01-01"),
    ("2024", "2024-01-01", "2025-01-01"),
    ("2025", "2025-01-01", "2026-01-01"),
    ("2026YTD", "2026-01-01", "2026-12-31"),
]


def maxdd(p):
    eq = np.cumsum(p)
    return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0


def report(name, trades45, trades80):
    print(f"--- {name} ---")
    print(f"{'period':<9}{'n':>6}{'tr/day':>8}{'WR%':>6}{'PF':>7}{'net':>8}"
          f"{'maxDD':>8}{'posWk%':>8}{'PF@.80':>8}")
    for label, a, b in PERIODS:
        a, b = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
        sub = [t for t in trades45 if a <= t.t_entry < b]
        sub8 = [t for t in trades80 if a <= t.t_entry < b]
        if not sub:
            print(f"{label:<9} n=0")
            continue
        p = np.array([t.pnl for t in sub])
        p8 = np.array([t.pnl for t in sub8])
        days = len({t.t_entry.date() for t in sub})
        w = (p > 0).sum()
        gl = -p[p <= 0].sum()
        pf = p[p > 0].sum() / gl if gl > 0 else float("inf")
        gl8 = -p8[p8 <= 0].sum()
        pf8 = p8[p8 > 0].sum() / gl8 if gl8 > 0 else float("inf")
        wk = pd.DataFrame({"t": [t.t_entry for t in sub], "pnl": p})
        wkly = wk.groupby(wk["t"].dt.to_period("W"))["pnl"].sum()
        print(f"{label:<9}{len(p):>6}{len(p)/max(1,days):>8.1f}"
              f"{100*w/len(p):>6.1f}{pf:>7.2f}{p.sum():>8.0f}"
              f"{maxdd(list(p)):>8.0f}{100*(wkly>0).mean():>8.0f}{pf8:>8.2f}")


res = {}
for cost in (0.45, 0.80):
    trl, _ = run_combo(m3, models=("fvg", "ob", "rsi"), hours=WIDE, cost=cost,
                       struct=None, **STACK_KW)
    res[("stack", cost)] = trl
    res[("s93", cost)] = run_fvg_scalp_v2(m5, cost=cost, struct=struct5,
                                          struct_mode="soft", max_gap_atr=1.5)

report("M3 stack gated mc=1", res[("stack", 0.45)], res[("stack", 0.80)])
report("S93 upgraded (M5 KZ, SOFT+cap)", res[("s93", 0.45)], res[("s93", 0.80)])

fig, ax = plt.subplots(figsize=(16, 8))
for key, color, label in (("stack", "#f0b90b", "M3 stack gated"),
                          ("s93", "#2196F3", "S93 upgraded")):
    rows = sorted((t.t_exit, t.pnl) for t in res[(key, 0.45)])
    ax.plot([r[0] for r in rows], np.cumsum([r[1] for r in rows]),
            lw=2.0, color=color, label=f"{label} @0.45")
    rows8 = sorted((t.t_exit, t.pnl) for t in res[(key, 0.80)])
    ax.plot([r[0] for r in rows8], np.cumsum([r[1] for r in rows8]),
            lw=1.1, ls="--", color=color, alpha=0.7, label=f"{label} @0.80")
ax.axhline(0, color="gray", lw=0.6)
ax2 = ax.secondary_yaxis("right", functions=(lambda p: p * 10, lambda d: d / 10))
ax2.set_ylabel("USD at 0.10 lots")
ax.set_ylabel("points (flat per-trade size)")
ax.set_title("3-year backtest 2023-07 .. 2026-07 — M3 stack vs S93 upgraded "
             "(solid 0.45pt, dashed 0.80pt stress)")
ax.legend(loc="upper left", fontsize=10)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(r"E:\Projects\Kronos\bt3y_equity.png", dpi=110)
print("equity saved")
