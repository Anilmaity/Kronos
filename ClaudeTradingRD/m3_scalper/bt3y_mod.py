"""Modified-spec 3-year validation, stepwise:
  A baseline stack (current spec, hours 1-15)
  B +hours trim (1-8, 13-15)
  C +confirmation entries
  D +daily -15pt kill-switch  (full modified spec)
Year-by-year at 0.45pt with PF@0.80 column.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH = Path(__file__).parent
sys.path.insert(0, str(SCRATCH))

from s93_ob_validate import run_combo  # noqa: E402

m1 = pd.read_parquet(SCRATCH / "xau_m1_3y.parquet")
m1["time"] = pd.to_datetime(m1["time"], utc=True)
m3 = (m1.sort_values("time").set_index("time").resample("3min")
      .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
      .dropna().reset_index())

BASE_H = tuple(range(1, 16))
TRIM_H = (1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15)
KW = dict(dispm=0.5, ob_break=3, ob_entry="edge", rsi_n=3, rsi_ob=85,
          rsi_os=15, rsi_mode="momentum", max_concurrent=1, ema_filter=True)
PERIODS = [("2023H2", "2023-07-01", "2024-01-01"),
           ("2024", "2024-01-01", "2025-01-01"),
           ("2025", "2025-01-01", "2026-01-01"),
           ("2026", "2026-01-01", "2026-12-31")]


def maxdd(p):
    eq = np.cumsum(p)
    return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0


def report(name, t45, t80):
    print(f"--- {name} ---")
    print(f"{'period':<8}{'n':>6}{'tr/day':>8}{'WR%':>6}{'PF':>7}{'net':>8}"
          f"{'maxDD':>7}{'posWk%':>8}{'PF@.80':>8}")
    for label, a, b in PERIODS:
        a, b = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
        p = np.array([t.pnl for t in t45 if a <= t.t_entry < b])
        p8 = np.array([t.pnl for t in t80 if a <= t.t_entry < b])
        if len(p) == 0:
            print(f"{label:<8} n=0")
            continue
        days = len({t.t_entry.date() for t in t45 if a <= t.t_entry < b})
        w = (p > 0).sum()
        gl = -p[p <= 0].sum()
        pf = p[p > 0].sum() / gl if gl > 0 else float("inf")
        gl8 = -p8[p8 <= 0].sum() if len(p8) else 0
        pf8 = (p8[p8 > 0].sum() / gl8) if gl8 > 0 else float("inf")
        ts = pd.Series([t.t_entry.tz_localize(None) for t in t45
                        if a <= t.t_entry < b])
        wkly = pd.DataFrame({"w": ts.dt.to_period("W"), "p": p}).groupby("w")["p"].sum()
        print(f"{label:<8}{len(p):>6}{len(p)/max(1,days):>8.1f}"
              f"{100*w/len(p):>6.1f}{pf:>7.2f}{p.sum():>8.0f}"
              f"{maxdd(list(p)):>7.0f}{100*(wkly>0).mean():>8.0f}{pf8:>8.2f}")


VARIANTS = [
    ("A baseline", dict(hours=BASE_H)),
    ("B +hours trim", dict(hours=TRIM_H)),
    ("C +confirm entry", dict(hours=TRIM_H, confirm_entry=True)),
    ("D +daily kill -15pt (FULL)", dict(hours=TRIM_H, confirm_entry=True,
                                        daily_stop_pts=15.0)),
]
for name, extra in VARIANTS:
    t45, _ = run_combo(m3, models=("fvg", "ob", "rsi"), cost=0.45,
                       struct=None, **KW, **extra)
    t80, _ = run_combo(m3, models=("fvg", "ob", "rsi"), cost=0.80,
                       struct=None, **KW, **extra)
    report(name, t45, t80)
