"""Step 4 - two static figures from baseline_tests.csv (written by 02_baseline.py).

Run: ../../../.venv/bin/python 04_charts.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from lib import HERE, TOUCH

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"          # categorical slots 1-2 (validated: CVD dE 24.7, contrast >= 3:1)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False})
r = pd.read_csv(HERE / "baseline_tests.csv")

# ---- 1. standardised difference from random entries, feature by feature ----
LABEL = {
    "ret5_dir": "5-min return in trade direction", "ret1_dir": "1-min return in trade direction", "ret15_dir": "15-min return in trade direction",
    "ret60_dir": "60-min return in trade direction", "pos15_dir": "position in 15-min range (0 = bought low / sold high)",
    "pos60_dir": "position in 60-min range", "posday_dir": "position in the day's range", "fade_brk60": "enters beyond 60-min extreme AGAINST trade",
    "follow_brk60": "enters beyond 60-min extreme WITH trade", "fade_spike": "fades a 3-min spike", "follow_spike": "follows a 3-min spike",
    "ema20_m1_side": "price on with-trade side of EMA20 (M1)", "ema20_m5_side": "price on with-trade side of EMA20 (M5)",
    "ematrend_m5_dir": "EMA20 > EMA50 with trade (M5)", "sweep_stop_15": "liquidity sweep on stop side, last 15 min",
    "in_fvg5_dir": "inside a live M5 fair-value gap (with trade)", "disp5_dir": "M5 displacement bar with trade, last 15 min",
    "sw_stop_atr": "room to last M5 swing on stop side (ATR)", "beyond_pd_dir": "beyond prior-day high/low with trade",
    "rn5": "distance to nearest $5", "rn10": "distance to nearest $10", "rn50": "distance to nearest $50",
    "atr5": "ATR14 on M5", "volratio": "ATR vs 20-day same-hour median", "spread": "spread at entry"}
fig, axes = plt.subplots(1, 2, figsize=(13, 9), sharey=True)
order = list(LABEL)[::-1]
for ax, sub in zip(axes, ("first", "all")):
    x = r[(r.subset == sub) & r.feature.isin(order)].pivot(index="feature", columns="null", values=["d", "q"]).reindex(order)
    n = int(r[r.subset == sub].n.iloc[0])
    ax.axvline(0, color=MUTED, lw=1)
    for k, (null, col, dy) in enumerate((("A", BLUE, 0.16), ("C", ORANGE, -0.16))):
        sig = x[("q", null)] < 0.05
        yy = [i + dy for i in range(len(order))]
        ax.hlines(yy, 0, x[("d", null)], color=col, lw=2, alpha=0.35)
        ax.scatter(x[("d", null)][sig], [y for y, s in zip(yy, sig) if s], s=95, color=col, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label=("Null A: same hour, any day of the week" if null == "A" else "Null C: whole block slid +-5..90 min") + " - filled = q < 0.05")
        ax.scatter(x[("d", null)][~sig], [y for y, s in zip(yy, sig) if not s], s=42, facecolor=SURFACE, edgecolor=col, linewidth=1.5, zorder=3)
    ax.set_yticks(range(len(order)), [LABEL[f] for f in order])
    ax.set_title(("FIRST entries of a sequence" if sub == "first" else "All decisions") + f" (n = {n})", loc="left", color=INK, fontsize=11, fontweight="bold")
    ax.set_xlim(-1.0, 1.0)
    ax.grid(axis="x", color=GRID, lw=1)
    ax.tick_params(length=0)
fig.supxlabel("standardised difference from random entries (d, in SDs of a single random entry); hollow = not significant after FDR", color=MUTED, fontsize=10, y=0.075)
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=9, labelcolor=MUTED)
fig.suptitle("XM Real: what distinguishes the trader's entries from matched random entries", x=0.01, ha="left", color=INK, fontsize=13, fontweight="bold")
fig.text(0.01, 0.925, "Negative = against the trade direction. The entries fade the last 1-15 minutes and sit on the counter-trend side of the M1/M5 EMA.\n"
                      "Sweeps, fair-value gaps, displacement and round numbers do not separate them from random entries.", color=MUTED, fontsize=9.5)
fig.tight_layout(rect=(0, 0.09, 1, 0.91))
fig.savefig(HERE / "fig_effect_sizes.png", dpi=150)

# ---- 2. the win rate is the exit geometry: real vs random entries under four first-touch rules ----
o = r[(r.subset == "all") & r.feature.isin(TOUCH)].pivot(index="feature", columns="null", values=["real", "null_mean", "z", "p"]).reindex(list(TOUCH))
fig, ax = plt.subplots(figsize=(9.5, 4.6))
names = [f"TP {TOUCH[k][0]:g} / stop {TOUCH[k][1]:g} pt" for k in TOUCH]
for i, k in enumerate(TOUCH):
    mu, real = o.loc[k, ("null_mean", "A")], o.loc[k, ("real", "A")]
    sd = abs((real - mu) / o.loc[k, ("z", "A")])
    ax.hlines(i, mu - 1.96 * sd, mu + 1.96 * sd, color=BLUE, lw=2, alpha=0.35)
    ax.scatter(mu, i, s=80, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3, label="random entries, same hours and sides (mean and 95% band of 10,000 synthetic weeks)" if i == 0 else None)
    ax.scatter(real, i, s=80, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=4, label="the trader's 124 entry decisions, same exit rule" if i == 0 else None)
    ax.annotate(f"random {mu:.0%}   real {real:.0%}   p = {o.loc[k, ('p', 'A')]:.2f}", (1.0, i), xytext=(-4, 9), textcoords="offset points", ha="right", color=MUTED, fontsize=9)
ax.axvline(0.758, color=INK, lw=1)
ax.annotate("actual ledger: 75.8% of 178 positions closed in profit", (0.758, len(TOUCH) - 0.45), xytext=(-5, 0), textcoords="offset points", ha="right", color=INK, fontsize=9)
ax.set_yticks(range(len(TOUCH)), names)
ax.set_ylim(-0.6, len(TOUCH) - 0.2)
ax.set_xlim(0.3, 1.0)
ax.set_xticks([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], ["30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"])
ax.set_xlabel("share of entries that reach the target before the stop (spread paid, same-bar tie = stop)")
ax.grid(axis="x", color=GRID, lw=1)
ax.tick_params(length=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), frameon=False, fontsize=9, labelcolor=MUTED)
ax.set_title("Exit geometry sets the win rate - the entries do not", loc="left", color=INK, fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig(HERE / "fig_geometry_winrate.png", dpi=150)
print("wrote fig_effect_sizes.png, fig_geometry_winrate.png")
