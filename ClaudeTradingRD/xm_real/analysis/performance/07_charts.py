"""Two static charts for REPORT.md -> charts/equity_curve.png, charts/mae_vs_outcome.png
Palette: dataviz reference slots 1-3 (validated all-pairs, light surface); text in ink tokens; one y-scale per panel."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import OUT, HERE

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": AXIS, "axes.linewidth": 1,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
                     "legend.frameon": False, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left"})
(HERE / "charts").mkdir(exist_ok=True)

g = pd.read_csv(HERE / "equity_curve.csv", parse_dates=["time"]).set_index("time")
so = pd.read_csv(OUT / "tab_stopout_events.csv")
m = g[g.market_open].copy()                      # compress closed hours / the weekend
m["x"] = np.arange(len(m))
xof = lambda t: int(np.searchsorted(m.index.values, np.datetime64(pd.Timestamp(t).tz_convert(None)) if pd.Timestamp(t).tzinfo else np.datetime64(t)))
days = pd.date_range("2026-11-04", "2026-11-11", freq="D", tz="UTC")
ticks = [(int(np.searchsorted(m.index.values, d.tz_convert(None).to_datetime64())), d.strftime("%b %d")) for d in days if d != pd.Timestamp("2026-11-07", tz="UTC") and d != pd.Timestamp("2026-11-08", tz="UTC")]
ticks = [(x, l) for x, l in ticks if x < len(m)]
so_x = [int(np.searchsorted(m.index.values, np.datetime64(pd.Timestamp("2026-" + s)))) for s in so.first_so]

fig, ax = plt.subplots(3, 1, figsize=(12, 9.6), sharex=True, gridspec_kw={"height_ratios": [3, 3, 1.6], "hspace": 0.32})
a = ax[0]
a.plot(m.x, m.balance, color=BLUE, lw=1.6, label="Balance (realised)", solid_joinstyle="round")
a.plot(m.x, m.equity, color=ORANGE, lw=1.6, label="Equity (balance + bonus credit + open P&L)", solid_joinstyle="round")
a.set_title("Account balance and equity, USD (deposits and withdrawals included)")
a.plot(so_x, [0] * len(so_x), marker="v", ms=9, color=INK2, mec=SURF, mew=1.5, ls="none", zorder=5, clip_on=False, label="Margin stop-out event (7; equity about 0 after each)")
pk = m.balance.idxmax()
a.annotate(f"peak balance {m.balance.max():,.0f}", xy=(m.x[pk], m.balance.max()), xytext=(m.x[pk] - 14500, m.balance.max() - 60), color=INK2, fontsize=9,
           arrowprops=dict(arrowstyle="-", color=AXIS, lw=1))
a.legend(loc="upper left", ncols=1, fontsize=9, labelcolor=INK2)
a.set_ylim(-200, 2100)

b = ax[1]
b.plot(m.x, m.realised_pnl, color=BLUE, lw=1.6, label="Realised P&L")
b.plot(m.x, m.pnl_incl_floating, color=ORANGE, lw=1.6, label="Realised + open P&L")
b.fill_between(m.x, m.realised_pnl, m.pnl_incl_floating, color=ORANGE, alpha=0.10, lw=0)
b.set_title("Cumulative trading P&L, USD (cash flows removed). Shaded gap = open loss the balance does not show")
b.legend(loc="upper left", ncols=2, fontsize=9, labelcolor=INK2)
b.annotate(f"end +{m.realised_pnl.iloc[-1]:,.0f}", xy=(m.x.iloc[-1], m.realised_pnl.iloc[-1]), xytext=(m.x.iloc[-1] - 2500, 60), color=INK2, fontsize=9,
           arrowprops=dict(arrowstyle="-", color=AXIS, lw=1))
pk = m.realised_pnl.idxmax()
b.annotate(f"peak +{m.realised_pnl.max():,.0f}", xy=(m.x[pk], m.realised_pnl.max()), xytext=(m.x[pk] - 11000, m.realised_pnl.max() - 40), color=INK2, fontsize=9,
           arrowprops=dict(arrowstyle="-", color=AXIS, lw=1))
tr = (m.realised_pnl - m.pnl_incl_floating).idxmax()
b.annotate(f"open loss {m.floating[tr]:,.0f}", xy=(m.x[tr], m.pnl_incl_floating[tr]), xytext=(m.x[tr] - 17000, m.pnl_incl_floating[tr] - 420), color=INK2, fontsize=9,
           arrowprops=dict(arrowstyle="-", color=AXIS, lw=1))
b.axhline(0, color=AXIS, lw=1)

c = ax[2]
c.fill_between(m.x, 0, m.net_lots, step="post", color=MUTED, alpha=0.55, lw=0)
c.axhline(0, color=AXIS, lw=1)
c.set_title("Net open lots (+ long, - short); 0.04 lots = 4 oz, about 16,200 USD notional")
c.set_xticks([x for x, _ in ticks]); c.set_xticklabels([l for _, l in ticks])
c.set_xlabel("UTC trading time (market-closed hours and the weekend removed)")
for z in ax:
    z.tick_params(length=0); z.spines["left"].set_visible(False)
    z.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1 or v == 0 else f"{v:.1f}"))
fig.savefig(HERE / "charts" / "equity_curve.png", dpi=150, bbox_inches="tight")

# ---------------------------------------------------------------- MAE vs outcome
p = pd.read_csv(OUT / "positions_enriched.csv")
t = p[p.role == "trade"]
fig, a = plt.subplots(figsize=(9.5, 6.4))
lim = 70
a.plot([0, lim], [0, -lim], color=AXIS, lw=1); a.axhline(0, color=AXIS, lw=1)
for kinds, col, mk, lab in ((["TP"], BLUE, "o", "Take-profit hit"), (["MOBILE"], ORANGE, "s", "Closed by hand"), (["SO", "CLOSE_BY"], AQUA, "^", "Margin stop-out or locked by a hedge")):
    s = t[t.exit_kind.isin(kinds)]
    a.scatter(s.mae_pts, s.adj_pts, s=52, c=col, marker=mk, edgecolors=SURF, linewidths=1.5, label=f"{lab} (n={len(s)})", zorder=3)
a.set_xlabel("Worst adverse excursion while open, points (USD per oz)"); a.set_ylabel("Result at exit, points")
a.set_title("Every position: how far under water it went vs how it ended (n=174)")
a.legend(loc="lower left", fontsize=9, labelcolor=INK2)
a.annotate("exited at its worst point", xy=(52, -52), xytext=(36, -64), color=INK2, fontsize=9, arrowprops=dict(arrowstyle="-", color=AXIS, lw=1))
w = t[t.adj_pts > 0]
a.text(31, 36, f"{int((w.mae_pts >= 10).sum())} of {len(w)} winners were 10+ points\nunder water before they paid", color=INK2, fontsize=9, va="top")
a.set_xlim(-1, lim); a.set_ylim(-lim, 40); a.tick_params(length=0); a.spines["left"].set_visible(False)
fig.savefig(HERE / "charts" / "mae_vs_outcome.png", dpi=150, bbox_inches="tight")
print("ok")
