"""
build_final_chart.py
--------------------
Annotated verification charts synthesizing the Dow / AMD / SMC findings onto the
Daily timeframe, per segment, with phase shading + key-event labels + a macro panel
(DXY & TNX) that explains the turns. Plus an annotated interactive HTML.
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

PHASE_COLORS = {
    "Accumulation": "#4e79a7",
    "Markup": "#59a14f",
    "Distribution": "#edc948",
    "Markdown": "#e15759",
    "Re-accumulation": "#9c9c9c",
}

# Phase maps (converged across the 3 framework subagents) — (start, end, label)
PHASES = {
    "segA": [
        ("2025-01-06", "2025-01-22", "Accumulation"),
        ("2025-01-22", "2025-03-30", "Markup"),
    ],
    "segB": [
        ("2025-11-19", "2025-12-31", "Accumulation"),
        ("2025-12-31", "2026-01-28", "Markup"),
        ("2026-01-28", "2026-03-02", "Distribution"),
        ("2026-03-02", "2026-03-23", "Markdown"),
        ("2026-03-23", "2026-05-19", "Re-accumulation"),
    ],
}

# Key events: (date, price, text, va) — va='top' label above, 'bottom' below
EVENTS = {
    "segA": [
        ("2025-01-06", 2615, "Cycle low 2615\n(SSL grab, discount)", "bottom"),
        ("2025-02-28", 2833, "Secondary reaction\n-4.2% (HL holds)", "bottom"),
        ("2025-03-30", 3098, "+18.5% markup\n(data ends mid-trend)", "top"),
    ],
    "segB": [
        ("2025-12-31", 4274, "Judas low 4274\n(inducement)", "bottom"),
        ("2026-01-28", 5602, "BLOW-OFF TOP 5602\nAlgo candle / premium BSL raid\nDXY 96.4 low | VIX 16 (euphoria)", "top"),
        ("2026-01-30", 5100, "CHoCH (01-30)\nbull->bear", "bottom"),
        ("2026-03-02", 5420, "Lower high 5420\n(distribution / SMT)", "top"),
        ("2026-03-23", 4099, "Cycle low 4099\nVIX spike 26 | TNX up", "bottom"),
        ("2026-05-18", 4480, "Re-accum\n4480 (LH 4774)", "bottom"),
    ],
}

TITLES = {
    "segA": "SEGMENT A — XAU/USD Daily — Jan-Mar 2025  (one clean primary BULL: 2615 -> 3098, +18.5%)",
    "segB": "SEGMENT B — XAU/USD Daily — Nov 2025-May 2026  (full cycle: accumulation -> mania -> 5602 blow-off -> distribution -> markdown)",
}


def load_daily(seg):
    d = pd.read_csv(os.path.join(ODATA, f"daily_{seg}.csv"), parse_dates=["time"])
    return d.set_index("time")


def load_macro():
    m = pd.read_csv(os.path.join(ODATA, "macro_daily.csv"), parse_dates=["time"])
    return m.set_index("time")


def chart(seg):
    d = load_daily(seg)
    macro = load_macro()
    dmap = {ts.normalize(): i for i, ts in enumerate(d.index)}

    def xfor(datestr):
        ts = pd.Timestamp(datestr, tz="UTC").normalize()
        # nearest available trading day
        if ts in dmap:
            return dmap[ts]
        idx = d.index.normalize()
        pos = idx.searchsorted(ts)
        pos = min(max(pos, 0), len(d) - 1)
        return pos

    fig, (ax, axm) = plt.subplots(
        2, 1, figsize=(17, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06})

    # phase shading
    ymin, ymax = d["low"].min(), d["high"].max()
    pad = (ymax - ymin) * 0.08
    for start, end, label in PHASES[seg]:
        x0, x1 = xfor(start), xfor(end)
        ax.axvspan(x0, x1, color=PHASE_COLORS[label], alpha=0.13, zorder=0)
        ax.text((x0 + x1) / 2, ymax + pad * 0.3, label, ha="center", va="bottom",
                fontsize=10, weight="bold", color=PHASE_COLORS[label])

    # candles
    for i, (_, row) in enumerate(d.iterrows()):
        up = row["close"] >= row["open"]
        c = "#2ca02c" if up else "#d62728"
        ax.plot([i, i], [row["low"], row["high"]], color=c, lw=0.7, alpha=0.75, zorder=2)
        ax.add_patch(Rectangle((i - 0.32, min(row["open"], row["close"])), 0.64,
                               max(abs(row["close"] - row["open"]), 0.01),
                               color=c, alpha=0.9, zorder=2))

    # primary + secondary zigzag
    for scale, col, lw in [("secondary", "#1f77b4", 1.2), ("primary", "#111111", 2.4)]:
        z = pd.read_csv(os.path.join(ODATA, f"zigzag_{seg}_{scale}.csv"), parse_dates=["date"])
        if z.empty:
            continue
        xs = [xfor(str(x.date())) for x in z["date"]]
        ax.plot(xs, z["price"], color=col, lw=lw, alpha=0.85, zorder=3,
                marker="o", ms=5 if scale == "primary" else 3,
                label=f"{scale} zigzag")

    # event annotations
    for date, price, text, va in EVENTS[seg]:
        x = xfor(date)
        dy = pad * (1.4 if va == "top" else -1.4)
        ax.annotate(text, (x, price), xytext=(x, price + dy),
                    ha="center", va="bottom" if va == "top" else "top",
                    fontsize=8.5, weight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#444", alpha=0.9),
                    arrowprops=dict(arrowstyle="->", color="#444", lw=1.1), zorder=5)

    ax.set_ylabel("XAU/USD", fontsize=11)
    ax.set_ylim(ymin - pad, ymax + pad * 2.2)
    ax.set_title(TITLES[seg], fontsize=12.5, weight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.15)

    # macro panel: DXY (left axis) + TNX (right axis) aligned to segment window
    seg_macro = macro.loc[d.index.min(): d.index.max()]
    mx = [xfor(str(ts.date())) for ts in seg_macro.index]
    axm.plot(mx, seg_macro["DXY"], color="#8c564b", lw=1.6, label="DXY (US$ index)")
    axm.set_ylabel("DXY", color="#8c564b", fontsize=10)
    axm.tick_params(axis="y", labelcolor="#8c564b")
    axt = axm.twinx()
    axt.plot(mx, seg_macro["TNX"], color="#9467bd", lw=1.6, label="TNX (US10Y %)")
    axt.set_ylabel("US10Y yield %", color="#9467bd", fontsize=10)
    axt.tick_params(axis="y", labelcolor="#9467bd")
    axm.grid(alpha=0.15)
    axm.text(0.005, 0.9, "MACRO DRIVER:  gold rises as DXY & yields fall; "
             "DXY bottom + yields turning up = the markdown trigger",
             transform=axm.transAxes, fontsize=8.5, style="italic", color="#333")

    # x ticks as dates
    step = max(1, len(d) // 13)
    ax.set_xticks(list(range(0, len(d), step)))
    axm.set_xticklabels([d.index[i].strftime("%Y-%m-%d") for i in range(0, len(d), step)],
                        rotation=45, ha="right", fontsize=8)
    ax.set_xlim(-1, len(d))

    fig.tight_layout()
    path = os.path.join(OCHART, f"FINAL_{seg}_annotated.png")
    fig.savefig(path, dpi=135)
    plt.close(fig)
    print("wrote", path)


def interactive_annotated():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.05,
                        subplot_titles=("Segment A (Jan-Mar 2025)",
                                        "Segment B (Nov 2025-May 2026)"))
    for col, seg in enumerate(["segA", "segB"], start=1):
        d = load_daily(seg)
        fig.add_trace(go.Candlestick(x=d.index, open=d["open"], high=d["high"],
                                     low=d["low"], close=d["close"],
                                     showlegend=False, name=seg), row=1, col=col)
        z = pd.read_csv(os.path.join(ODATA, f"zigzag_{seg}_primary.csv"), parse_dates=["date"])
        fig.add_trace(go.Scatter(x=z["date"], y=z["price"], mode="lines+markers",
                                 line=dict(color="black", width=2.5),
                                 name="primary zigzag", showlegend=(col == 1)),
                      row=1, col=col)
        # phase shading via vrects
        for start, end, label in PHASES[seg]:
            fig.add_vrect(x0=start, x1=end, fillcolor=PHASE_COLORS[label],
                          opacity=0.12, line_width=0, row=1, col=col,
                          annotation_text=label, annotation_position="top left",
                          annotation_font_size=9)
        for date, price, text, va in EVENTS[seg]:
            fig.add_annotation(x=date, y=price, text=text.split("\n")[0],
                               showarrow=True, arrowhead=2,
                               ay=-40 if va == "top" else 40,
                               font=dict(size=9), row=1, col=col)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=col)
    fig.update_layout(template="plotly_white", height=780, width=1750,
                      title="XAU/USD 16-Month Structure — ANNOTATED (Dow+AMD+SMC synthesis). "
                            "7.5-month data gap between segments is NOT shown.")
    p = os.path.join(OCHART, "FINAL_interactive_annotated.html")
    fig.write_html(p)
    print("wrote", p)


if __name__ == "__main__":
    for seg in ["segA", "segB"]:
        chart(seg)
    interactive_annotated()
    print("DONE")
