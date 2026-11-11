"""Step 4 - charts for the write-up, drawn from trade_excursions.csv and results/*.csv (run 02 and 03 first).
Run: python 04_charts.py   -> charts/*.png
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from common import HERE, RES

OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, RED, MID = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#f0efec"   # validated: slots 1-3 all-pairs, blue<->red diverging
plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 10, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "savefig.facecolor": SURF, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True, "legend.frameon": False})


def title(ax, head, sub):
    ax.set_title(head, loc="left", color=INK, fontsize=12.5, fontweight="bold", pad=14 + 12 * (1 + sub.count(chr(10))))
    ax.text(0, 1.035, sub, transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom")


x = pd.read_csv(HERE / "trade_excursions.csv")
allr = pd.read_csv(RES / "cf_all.csv")
grid = pd.read_csv(RES / "cf_grid.csv")
drift = pd.read_csv(RES / "cf_drift.csv")

# 1 ---- how far under water each position went vs what it finally made -----------------------------------
fig, ax = plt.subplots(figsize=(10, 6.2))
kind = np.where(x.closeby | (x.reason == "SO"), "Margin stop-out or hedge lock", np.where(x.reason == "TP", "Take-profit hit", "Closed by hand"))
for lab, col in (("Closed by hand", BLUE), ("Take-profit hit", AQUA), ("Margin stop-out or hedge lock", ORANGE)):
    m = kind == lab
    ax.scatter(-x.mae_pts[m], x.pts_econ[m], s=52, color=col, edgecolor=SURF, linewidth=1.4, label=f"{lab} (n={m.sum()})", zorder=3)
lim = 70
ax.plot([0, lim], [0, -lim], color=AXIS, linewidth=1, zorder=1)
ax.text(52, -49, "closed at its worst point", color=MUTED, fontsize=9, rotation=-33, ha="center", va="bottom")
ax.axhline(0, color=AXIS, linewidth=1, zorder=1)
ax.annotate("two 0.12-lot longs, 10 Nov\nheld 5 h, wiped at the 13:30 release", xy=(66.5, -66.5), xytext=(40, -62), color=INK2, fontsize=9, ha="right", va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))
ax.annotate("20 winners were first\n20+ points under water", xy=(31, 22), xytext=(46, 30), color=INK2, fontsize=9, ha="left", va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))
ax.set_xlim(-1, lim); ax.set_ylim(-72, 36)
ax.set_xlabel("Worst point while open (points under water, exit-side quote)"); ax.set_ylabel("Realised points")
ax.legend(loc="lower left", fontsize=9.5, handletextpad=0.3)
title(ax, "Winners were allowed to sink deep; losers ended only when the margin ran out", "178 positions, XM Real, 4-11 Nov 2026. One dot per position.")
fig.tight_layout(); fig.savefig(OUT / "fig1_mae_vs_result.png", dpi=150); plt.close(fig)

# 2 ---- the TP x SL grid ------------------------------------------------------------------------------------
cmap = LinearSegmentedColormap.from_list("div", [RED, MID, BLUE])
fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.6), sharey=True)
for ax, sub, lab in zip(axes, ("ALL", "EX_ADDS"), ("All 178 entries", "Without the 71 adds to a loser (107 entries)")):
    p = grid[grid.subset == sub].pivot(index="tp", columns="sl", values="total_pts")
    ax.imshow(p.values, cmap=cmap, vmin=-800, vmax=800, aspect="auto")
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            ax.text(j, i, f"{int(round(p.values[i, j])):+d}", ha="center", va="center", color=INK, fontsize=8.2)
    ax.set_xticks(range(p.shape[1])); ax.set_xticklabels([f"{v:g}" for v in p.columns])
    ax.set_yticks(range(p.shape[0])); ax.set_yticklabels([f"{v:g}" for v in p.index])
    ax.set_xlabel("Hard stop-loss (points)"); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(lab, loc="left", color=INK2, fontsize=10.5)
axes[0].set_ylabel("Fixed take-profit (points)")
fig.suptitle("Same entries, fixed exits: total points per TP x SL cell", x=0.012, ha="left", color=INK, fontsize=12.5, fontweight="bold")
fig.text(0.012, 0.925, "Red = loss, blue = gain, grey = zero. His real exits made +402 points on all 178 and +155 on the 107. Stop slippage 0.30, 0.04 lots = $4 per point.",
         color=INK2, fontsize=9.5)
fig.tight_layout(rect=(0, 0, 1, 0.91)); fig.savefig(OUT / "fig2_tp_sl_grid.png", dpi=150); plt.close(fig)

# 3 ---- adding a hard stop --------------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharey=True)
for ax, fam, base_fam, head in zip(axes, ("e_actual_exits_plus_SL", "d_actualTP_SL_tpset141"), ("actual", "actual_tpset141"),
                                   ("His real exits, plus a hard stop", "His own take-profit levels, plus a hard stop (141 positions with a TP)")):
    f = allr[allr.family == fam]
    sls = sorted(f.sl.unique())
    pos = {s: i for i, s in enumerate(sls)}
    for sub, col, lab in (("ALL", BLUE, "all entries"), ("EX_ADDS", ORANGE, "without adds to a loser")):
        g = f[f.subset == sub].sort_values("sl")
        ax.plot([pos[s] for s in g.sl], g.total_pts, color=col, linewidth=2, marker="o", markersize=7, markeredgecolor=SURF, markeredgewidth=1.4, label=lab, zorder=3)
        b = allr[(allr.family == base_fam) & (allr.subset == sub)].total_pts.iloc[0]
        ax.plot([-0.4, len(sls) - 0.6], [b, b], color=col, linewidth=1, alpha=0.55, zorder=2)
        ax.text(len(sls) - 0.55, b, f"real: {b:+.0f}", color=INK2, fontsize=8.8, va="center", ha="left")
    ax.axhline(0, color=AXIS, linewidth=1.2, zorder=1)
    ax.set_xticks(range(len(sls))); ax.set_xticklabels(["none" if np.isinf(s) else f"{s:g}" for s in sls])
    ax.set_xlim(-0.5, len(sls) + 0.7)
    ax.set_xlabel("Hard stop-loss (points)"); ax.set_title(head, loc="left", color=INK2, fontsize=10.5)
axes[0].set_ylabel("Total points (0.04 lots: x $4)"); axes[0].legend(loc="upper left", fontsize=9.5)
fig.suptitle("A stop tighter than about 25 points removes the week's profit", x=0.012, ha="left", color=INK, fontsize=12.5, fontweight="bold")
fig.text(0.012, 0.915, "Thin horizontal lines = what he actually realised on the same positions with no stop. Stop slippage 0.30.", color=INK2, fontsize=9.5)
fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(OUT / "fig3_hard_stop.png", dpi=150); plt.close(fig)

# 4 ---- drift after entry ---------------------------------------------------------------------------------
d = drift[drift.subset == "ALL"].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(10, 5.4))
xs = np.arange(len(d))
ax.fill_between(xs, d.burst_mean - 2 * d.burst_se, d.burst_mean + 2 * d.burst_se, color=BLUE, alpha=0.10, linewidth=0, zorder=1)
ax.plot(xs, d.burst_mean, color=BLUE, linewidth=2, marker="o", markersize=7, markeredgecolor=SURF, markeredgewidth=1.4, zorder=3)
ax.axhline(0, color=AXIS, linewidth=1.2, zorder=1)
ax.axhline(-0.60, color=INK2, linewidth=1, zorder=2)
ax.set_xticks(xs); ax.set_xticklabels([f"{t} min" if t < 60 else f"{t // 60} h" for t in d.T_min])
ax.set_xlabel("Time after entry at which every position is simply closed"); ax.set_ylabel("Mean points per decision")
title(ax, "The entries show no drift in their own direction at any horizon", "Mean result of the 126 entry decisions if closed after a fixed time (no TP, no SL). Band = +-2 standard errors.\nDark line = the 0.60-point spread paid at entry, i.e. what an entry with no information earns.")
fig.tight_layout(); fig.savefig(OUT / "fig4_drift_after_entry.png", dpi=150); plt.close(fig)
print("wrote", sorted(p.name for p in OUT.glob("*.png")))
