"""Regime-gated 3-year backtest: daily ATR%-of-price percentile gate.

Gate: rel_atr = ATR(14, D1)/close, percentile-ranked over the trailing 252
completed D1 bars (min 60). Entries allowed on day D only if day D-1's
percentile >= threshold (fully causal). Sweep threshold {40, 60}%.
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
    return (df.set_index("time").resample(freq)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna().reset_index())


m3 = resample(m1, "3min")
m5 = resample(m1, "5min")
m15 = resample(m1, "15min")
d1 = resample(m1, "1D")

# daily relative-ATR percentile, shifted one day (causal)
h, l, c = d1["high"].to_numpy(), d1["low"].to_numpy(), d1["close"].to_numpy()
pc = np.concatenate(([c[0]], c[:-1]))
tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
rel = pd.Series(tr).rolling(14).mean() / pd.Series(c)
pct = rel.rolling(252, min_periods=60).rank(pct=True) * 100
d1["gate_pct"] = pct.shift(1)          # known at day open

def day_mask(frame, thresh):
    m = frame["time"].dt.floor("D").map(
        d1.set_index(d1["time"].dt.floor("D"))["gate_pct"])
    return (m >= thresh).fillna(False).to_numpy()


struct5 = m15_structure_on_m5(m5, m15)
WIDE = tuple(range(1, 16))
STACK_KW = dict(dispm=0.5, ob_break=3, ob_entry="edge", rsi_n=3, rsi_ob=85,
                rsi_os=15, rsi_mode="momentum", max_concurrent=1,
                ema_filter=True)
PERIODS = [("2023H2", "2023-07-01", "2024-01-01"),
           ("2024", "2024-01-01", "2025-01-01"),
           ("2025", "2025-01-01", "2026-01-01"),
           ("2026YTD", "2026-01-01", "2026-12-31")]


def maxdd(p):
    eq = np.cumsum(p)
    return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0


def report(name, t45, t80):
    print(f"--- {name} ---")
    print(f"{'period':<9}{'n':>6}{'tr/day':>8}{'WR%':>6}{'PF':>7}{'net':>8}"
          f"{'maxDD':>8}{'posWk%':>8}{'PF@.80':>8}")
    for label, a, b in PERIODS:
        a, b = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
        sub = [t for t in t45 if a <= t.t_entry < b]
        sub8 = [t.pnl for t in t80 if a <= t.t_entry < b]
        if not sub:
            print(f"{label:<9}     0  (gated off)")
            continue
        p = np.array([t.pnl for t in sub])
        p8 = np.array(sub8)
        days = len({t.t_entry.date() for t in sub})
        w = (p > 0).sum()
        gl = -p[p <= 0].sum()
        pf = p[p > 0].sum() / gl if gl > 0 else float("inf")
        gl8 = -p8[p8 <= 0].sum() if len(p8) else 0
        pf8 = (p8[p8 > 0].sum() / gl8) if gl8 > 0 else float("inf")
        wk = pd.DataFrame({"t": [t.t_entry.tz_localize(None) for t in sub], "pnl": p})
        wkly = wk.groupby(wk["t"].dt.to_period("W"))["pnl"].sum()
        print(f"{label:<9}{len(p):>6}{len(p)/max(1,days):>8.1f}"
              f"{100*w/len(p):>6.1f}{pf:>7.2f}{p.sum():>8.0f}"
              f"{maxdd(list(p)):>8.0f}{100*(wkly>0).mean():>8.0f}{pf8:>8.2f}")


results = {}
for thresh in (40, 60):
    mask3 = day_mask(m3, thresh)
    mask5 = day_mask(m5, thresh)
    print(f"\n===== gate: rel-ATR percentile >= {thresh} "
          f"(active {100*mask3.mean():.0f}% of bars) =====")
    t45, _ = run_combo(m3, models=("fvg", "ob", "rsi"), hours=WIDE, cost=0.45,
                       struct=None, regime_mask=mask3, **STACK_KW)
    t80, _ = run_combo(m3, models=("fvg", "ob", "rsi"), hours=WIDE, cost=0.80,
                       struct=None, regime_mask=mask3, **STACK_KW)
    report(f"M3 stack gated, thresh {thresh}", t45, t80)
    results[("stack", thresh)] = t45
    s45 = run_fvg_scalp_v2(m5, cost=0.45, struct=struct5, struct_mode="soft",
                           max_gap_atr=1.5, regime_mask=mask5)
    s80 = run_fvg_scalp_v2(m5, cost=0.80, struct=struct5, struct_mode="soft",
                           max_gap_atr=1.5, regime_mask=mask5)
    report(f"S93 upgraded, thresh {thresh}", s45, s80)
    results[("s93", thresh)] = s45

fig, ax = plt.subplots(figsize=(16, 8))
colors = {("stack", 40): "#f0b90b", ("stack", 60): "#ff7043",
          ("s93", 40): "#2196F3", ("s93", 60): "#7e57c2"}
for key, trl in results.items():
    rows = sorted((t.t_exit, t.pnl) for t in trl)
    ax.plot([r[0] for r in rows], np.cumsum([r[1] for r in rows]),
            lw=1.8, color=colors[key],
            label=f"{key[0]} vol-gate>={key[1]} "
                  f"({np.sum([r[1] for r in rows]):+.0f}pts)")
ax.axhline(0, color="gray", lw=0.6)
ax2 = ax.secondary_yaxis("right", functions=(lambda p: p * 10, lambda d: d / 10))
ax2.set_ylabel("USD at 0.10 lots")
ax.set_ylabel("points")
ax.set_title("Regime-gated 3-year equity (base 0.45pt) — daily rel-ATR "
             "percentile gate, causal")
ax.legend(loc="upper left", fontsize=10)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(r"E:\Projects\Kronos\bt3y_regime_equity.png", dpi=110)
print("\nequity saved")
