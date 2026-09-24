"""
build_waves.py
--------------
Restructure the continuous 16-month XAU/USD into an ELLIOTT WAVE count:
a 5-wave Primary impulse (2615 -> 5602) with an EXTENDED 5th (which subdivides
into 5, giving the 9-swing count), then an A-B-C flat correction to 4099 (=50%
Fib retrace). Draws daily candles + labelled wave count + Fibonacci retracements.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = os.path.dirname(os.path.abspath(__file__))
ODATA = os.path.join(OUT, "data")
OCHART = os.path.join(OUT, "charts")

# Primary-degree impulse (from the 10% zigzag) + ABC correction + current
IMPULSE = [
    ("2025-01-06", 2614.635, "0"),
    ("2025-04-22", 3500.200, "(1)"),
    ("2025-05-15", 3120.765, "(2)"),
    ("2025-10-20", 4381.440, "(3)"),
    ("2025-10-28", 3886.465, "(4)"),
    ("2026-01-28", 5602.225, "(5)"),
]
CORRECTION = [
    ("2026-01-28", 5602.225, ""),
    ("2026-02-02", 4402.380, "A"),
    ("2026-03-02", 5419.660, "B"),
    ("2026-03-23", 4099.125, "C"),
]
POST = [
    ("2026-03-23", 4099.125, ""),
    ("2026-04-17", 4891.540, "1?/B?"),
    ("2026-05-20", 4453.390, "2?/now"),
]
# Extended wave-5 sub-division (the "9" = waves 1-4 + these five sub-waves)
W5_SUB = [
    ("2025-10-28", 3886.465, ""),
    ("2025-12-26", 4550.150, "i"),
    ("2025-12-31", 4274.025, "ii"),
    ("2026-01-27", 5190.510, "iii"),
    ("2026-01-27", 5013.875, "iv"),
    ("2026-01-28", 5602.225, "v"),
]


def main():
    d = pd.read_csv(os.path.join(ODATA, "cont_daily.csv"), parse_dates=["time"]).set_index("time")
    dmap = {ts.normalize(): i for i, ts in enumerate(d.index)}

    def xf(ds):
        ts = pd.Timestamp(ds, tz="UTC").normalize()
        if ts in dmap:
            return dmap[ts]
        return min(max(d.index.normalize().searchsorted(ts), 0), len(d) - 1)

    fig, ax = plt.subplots(figsize=(20, 10))
    for i, (_, r) in enumerate(d.iterrows()):
        up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.5, alpha=0.6, zorder=2)
        ax.add_patch(Rectangle((i - 0.4, min(r["open"], r["close"])), 0.8,
                               max(abs(r["close"] - r["open"]), 0.01), color=c, alpha=0.85, zorder=2))

    ymax = d["high"].max(); ymin = d["low"].min(); pad = (ymax - ymin) * 0.05

    # Fibonacci retracements of the whole impulse 2615->5602
    top, bot = 5602.225, 2614.635; rng = top - bot
    for lvl, col in [(0.382, "#bbbbbb"), (0.5, "#9467bd"), (0.618, "#bbbbbb")]:
        y = top - rng * lvl
        ax.axhline(y, color=col, ls="--", lw=1.4 if lvl == 0.5 else 0.9,
                   alpha=0.85 if lvl == 0.5 else 0.6, zorder=1)
        ax.text(len(d) - 1, y, f" {lvl*100:.1f}% = {y:.0f}", color=col, fontsize=8,
                va="center", ha="left")

    def draw(points, color, lw, fs, dyfac):
        xs = [xf(p[0]) for p in points]; ys = [p[1] for p in points]
        ax.plot(xs, ys, color=color, lw=lw, zorder=4, alpha=0.9,
                marker="o", ms=7)
        for (ds, pr, lab), x in zip(points, xs):
            if not lab:
                continue
            isH = pr > (ymin + ymax) / 2 if lab in ("(1)", "(3)", "(5)", "B") else False
            up = lab in ("(1)", "(3)", "(5)", "B", "iii", "v", "1?/B?")
            ax.annotate(lab, (x, pr), xytext=(x, pr + pad * dyfac * (1 if up else -1)),
                        ha="center", va="bottom" if up else "top", fontsize=fs,
                        weight="bold", color=color, zorder=6,
                        bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=color, lw=1.4))

    draw(IMPULSE, "#1565c0", 2.6, 14, 2.2)      # primary impulse (1)-(5)
    draw(CORRECTION, "#c62828", 2.4, 13, 2.2)   # ABC correction
    draw(POST, "#777777", 1.8, 10, 2.0)         # current (ambiguous)
    # wave-5 sub-division (smaller, the "9")
    xs = [xf(p[0]) for p in W5_SUB]; ys = [p[1] for p in W5_SUB]
    ax.plot(xs, ys, color="#1565c0", lw=0.9, ls=":", alpha=0.7, zorder=3)
    for (ds, pr, lab), x in zip(W5_SUB, xs):
        if lab:
            ax.annotate(lab, (x, pr), textcoords="offset points", xytext=(6, 0),
                        fontsize=8, color="#1565c0", style="italic", zorder=5)

    # callouts
    ax.annotate("Wave (5) EXTENDED — subdivides i-ii-iii-iv-v\n=> impulse shows 9 swings (your 5->9)",
                (xf("2026-01-28"), 5602), xytext=(xf("2025-09-15"), 5450),
                fontsize=9, weight="bold", color="#1565c0",
                bbox=dict(boxstyle="round,pad=0.3", fc="#eef4ff", ec="#1565c0"))
    ax.annotate("C low 4099 = 50% Fib retrace (4108)\n= return to fair value",
                (xf("2026-03-23"), 4099), xytext=(xf("2026-03-25"), 3500),
                fontsize=9, weight="bold", color="#c62828",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fdeeee", ec="#c62828"),
                arrowprops=dict(arrowstyle="->", color="#c62828"))

    ax.set_title("XAU/USD 16-month ELLIOTT WAVE count — Primary 5-wave impulse (extended 5th => 9 swings) "
                 "+ A-B-C flat to 50% retrace", fontsize=13, weight="bold")
    ax.set_ylabel("XAU/USD")
    step = max(1, len(d) // 18)
    ax.set_xticks(list(range(0, len(d), step)))
    ax.set_xticklabels([d.index[i].strftime("%Y-%m-%d") for i in range(0, len(d), step)],
                       rotation=45, ha="right", fontsize=8)
    ax.set_xlim(-2, len(d) + 6); ax.set_ylim(ymin - pad, ymax + pad * 2.5)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(os.path.join(OCHART, "WAVES_16mo_elliott.png"), dpi=135)
    plt.close(fig)
    print("wrote charts/WAVES_16mo_elliott.png")

    make_interactive(d, xf)


def make_interactive(d, xf):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=d.index, open=d["open"], high=d["high"],
                                 low=d["low"], close=d["close"], name="Daily"))
    for pts, col, nm in [(IMPULSE, "#1565c0", "impulse (1)-(5)"),
                         (CORRECTION, "#c62828", "ABC"),
                         (POST, "#777777", "current")]:
        fig.add_trace(go.Scatter(x=[pd.Timestamp(p[0], tz="UTC") for p in pts],
                                 y=[p[1] for p in pts], mode="lines+markers+text",
                                 text=[p[2] for p in pts], textposition="top center",
                                 line=dict(color=col, width=3), name=nm))
    top, bot = 5602.225, 2614.635
    for lvl in [0.382, 0.5, 0.618]:
        y = top - (top - bot) * lvl
        fig.add_hline(y=y, line_dash="dash", line_color="#9467bd" if lvl == 0.5 else "#bbbbbb",
                      annotation_text=f"{lvl*100:.1f}% {y:.0f}")
    fig.update_layout(template="plotly_white", height=820, width=1900,
                      xaxis_rangeslider_visible=False,
                      title="XAU/USD Elliott Wave count (continuous 16mo) — extended-5th impulse + ABC to 50%")
    fig.write_html(os.path.join(OCHART, "WAVES_16mo_interactive.html"))
    print("wrote charts/WAVES_16mo_interactive.html")


if __name__ == "__main__":
    main()
