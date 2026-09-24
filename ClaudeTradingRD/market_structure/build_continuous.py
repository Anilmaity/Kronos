"""
build_continuous.py
-------------------
Rebuild the study on the now-CONTINUOUS 16-month XAU/USD series (gap backfilled in DB).
One regime, not two. Produces daily/H4/weekly OHLC, 3-scale zigzag over the whole
series, a continuity report, and a full-width Daily verification chart with macro panel.
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
SCALES = {"primary": 6.0, "secondary": 3.0, "minor": 1.5}

# reuse zigzag from foundation
from build_foundation import zigzag_pct, resample  # noqa: E402


def main():
    df = pd.read_parquet(os.path.join(ODATA, "cont_xau_M15.parquet"))
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()

    daily = resample(df, "1D")
    h4 = resample(df, "4h")
    weekly = resample(df, "1W")
    daily.to_csv(os.path.join(ODATA, "cont_daily.csv"))
    h4.to_csv(os.path.join(ODATA, "cont_h4.csv"))
    weekly.to_csv(os.path.join(ODATA, "cont_weekly.csv"))

    # continuity report
    gaps = daily.index.to_series().diff()
    big = gaps[gaps > pd.Timedelta("4D")]
    print(f"Daily bars: {len(daily)}  {daily.index.min().date()} -> {daily.index.max().date()}")
    print(f"Internal gaps > 4 days: {len(big)}")
    for t, g in big.items():
        print(f"   gap {g} ending {t.date()}")

    zz = {}
    for scale, pct in SCALES.items():
        z = zigzag_pct(daily.index.to_list(), daily["high"].values, daily["low"].values, pct)
        z.to_csv(os.path.join(ODATA, f"cont_zigzag_{scale}.csv"), index=False)
        zz[scale] = z
    print("primary pivots:")
    p = zz["primary"].copy()
    p["date"] = pd.to_datetime(p["date"]).dt.date
    print(p.to_string(index=False))
    print(f"\npivot counts: { {k: len(v) for k, v in zz.items()} }")

    make_chart(daily)
    make_interactive(daily, zz)


def make_chart(daily):
    macro = pd.read_csv(os.path.join(ODATA, "macro_daily.csv"), parse_dates=["time"]).set_index("time")
    fig, (ax, axm) = plt.subplots(2, 1, figsize=(20, 10), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    for i, (_, row) in enumerate(daily.iterrows()):
        up = row["close"] >= row["open"]
        c = "#2ca02c" if up else "#d62728"
        ax.plot([i, i], [row["low"], row["high"]], color=c, lw=0.5, alpha=0.7, zorder=2)
        ax.add_patch(Rectangle((i - 0.4, min(row["open"], row["close"])), 0.8,
                               max(abs(row["close"] - row["open"]), 0.01), color=c, alpha=0.9, zorder=2))
    dmap = {d.normalize(): i for i, d in enumerate(daily.index)}

    def xf(datestr):
        ts = pd.Timestamp(datestr, tz="UTC").normalize()
        if ts in dmap:
            return dmap[ts]
        pos = daily.index.normalize().searchsorted(ts)
        return min(max(pos, 0), len(daily) - 1)

    for scale, col, lw, ms in [("secondary", "#1f77b4", 1.1, 3), ("primary", "#111111", 2.4, 6)]:
        z = pd.read_csv(os.path.join(ODATA, f"cont_zigzag_{scale}.csv"), parse_dates=["date"])
        xs = [xf(str(pd.Timestamp(d).date())) for d in z["date"]]
        ax.plot(xs, z["price"], color=col, lw=lw, marker="o", ms=ms, alpha=0.85, zorder=3,
                label=f"{scale} zigzag ({SCALES[scale]}%)")
        if scale == "primary":
            for xx, pp, kk in zip(xs, z["price"], z["kind"]):
                ax.annotate(f"{pp:.0f}", (xx, pp), textcoords="offset points",
                            xytext=(0, 8 if kk == "H" else -15), ha="center", fontsize=7,
                            color="#111")

    # phase bands across the full continuous series (Dow+AMD+SMC synthesis)
    bands = [
        ("2025-01-06", "2025-06-29", "Accumulation (base; Apr VIX-47 spike)", "#4e79a7"),
        ("2025-06-29", "2025-12-26", "Public participation (markup)", "#59a14f"),
        ("2025-12-26", "2026-01-28", "Blow-off run", "#2f7d2f"),
        ("2026-01-28", "2026-03-02", "Distribution", "#edc948"),
        ("2026-03-02", "2026-03-23", "Markdown", "#e15759"),
        ("2026-03-23", "2026-05-22", "Correction / re-accum", "#9c9c9c"),
    ]
    ymax = daily["high"].max(); ymin = daily["low"].min(); pad = (ymax - ymin) * 0.04
    for s, e, lab, c in bands:
        x0, x1 = xf(s), xf(e)
        ax.axvspan(x0, x1, color=c, alpha=0.10, zorder=0)
        ax.text((x0 + x1) / 2, ymax + pad, lab, ha="center", va="bottom", fontsize=8,
                weight="bold", color=c, rotation=0)

    # master-range equilibrium (2615 -> 5602), 50% = 4108 — the markdown low (4099) returns to it
    eq = (2614.635 + 5602.225) / 2
    ax.axhline(eq, color="#9467bd", ls="--", lw=1.3, alpha=0.8, zorder=1)
    ax.text(2, eq, f"  master-range equilibrium {eq:.0f} (50% of 2615->5602)",
            color="#9467bd", fontsize=8, va="bottom")

    # key event callouts
    events = [
        ("2025-04-22", 3500, "3500 — Apr haven spike (VIX 47 intraday)", "top"),
        ("2025-10-20", 4381, "4381 — summer melt-up (TNX 3.99 low)", "top"),
        ("2026-01-28", 5602, "5602 BLOW-OFF TOP\nDXY 96.4 16-mo low | VIX 16 | silver SMT", "top"),
        ("2026-03-23", 4099, "4099 low = equilibrium (VIX 26, yields up)", "bottom"),
    ]
    for ds, pr, txt, va in events:
        x = xf(ds); dy = pad * (3.0 if va == "top" else -3.0)
        ax.annotate(txt, (x, pr), xytext=(x, pr + dy),
                    ha="center", va="bottom" if va == "top" else "top", fontsize=8,
                    weight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#444", alpha=0.9),
                    arrowprops=dict(arrowstyle="->", color="#444", lw=1.1), zorder=6)

    ax.set_title("XAU/USD — CONTINUOUS 16 months (Jan 2025 - May 2026), gap backfilled — Daily + zigzag",
                 fontsize=13, weight="bold")
    ax.set_ylabel("XAU/USD"); ax.legend(loc="upper left", fontsize=9); ax.grid(alpha=0.15)
    ax.set_ylim(ymin - pad, ymax + pad * 2.5)

    seg = macro.loc[daily.index.min(): daily.index.max()]
    mx = [xf(str(ts.date())) for ts in seg.index]
    axm.plot(mx, seg["DXY"], color="#8c564b", lw=1.4, label="DXY")
    axm.set_ylabel("DXY", color="#8c564b"); axm.tick_params(axis="y", labelcolor="#8c564b")
    axt = axm.twinx(); axt.plot(mx, seg["TNX"], color="#9467bd", lw=1.4)
    axt.set_ylabel("US10Y %", color="#9467bd"); axt.tick_params(axis="y", labelcolor="#9467bd")
    axm.grid(alpha=0.15)
    step = max(1, len(daily) // 18)
    ax.set_xticks(list(range(0, len(daily), step)))
    axm.set_xticklabels([daily.index[i].strftime("%Y-%m-%d") for i in range(0, len(daily), step)],
                        rotation=45, ha="right", fontsize=8)
    ax.set_xlim(-2, len(daily) + 1)
    fig.tight_layout()
    fig.savefig(os.path.join(OCHART, "CONTINUOUS_16mo_daily.png"), dpi=130)
    plt.close(fig)
    print("wrote charts/CONTINUOUS_16mo_daily.png")


def make_interactive(daily, zz):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=daily.index, open=daily["open"], high=daily["high"],
                                 low=daily["low"], close=daily["close"], name="Daily"))
    for scale, col in [("secondary", "#1f77b4"), ("primary", "#111111")]:
        z = zz[scale]
        fig.add_trace(go.Scatter(x=pd.to_datetime(z["date"]), y=z["price"], mode="lines+markers",
                                 line=dict(color=col, width=2.5 if scale == "primary" else 1.3),
                                 name=f"{scale} zigzag"))
    fig.update_layout(template="plotly_white", height=800, width=1900,
                      title="XAU/USD CONTINUOUS 16 months (gap backfilled) — Daily + zigzag",
                      xaxis_rangeslider_visible=False)
    fig.write_html(os.path.join(OCHART, "CONTINUOUS_16mo_interactive.html"))
    print("wrote charts/CONTINUOUS_16mo_interactive.html")


if __name__ == "__main__":
    main()
