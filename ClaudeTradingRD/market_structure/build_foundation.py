"""
build_foundation.py
-------------------
Shared market-structure foundation for the 16-month XAU/USD study.

The raw feed (backtest/data/bars_M15.parquet) spans 2025-01-01 -> 2026-05-19 but is
DISCONTINUOUS: a ~233-day hole (2025-04-01 .. 2025-11-19) splits it into two segments.
We therefore treat the data as two independent regimes and never draw structure across
the void.

Outputs (all under MarketStructure/):
  data/daily_segA.csv, daily_segB.csv        Daily OHLC per segment (UTC days)
  data/h4_segA.csv,    h4_segB.csv           H4 OHLC per segment
  data/weekly_segA.csv, weekly_segB.csv      Weekly OHLC per segment
  data/zigzag_<seg>_<scale>.csv              Zigzag pivots (primary/secondary/minor)
  data/macro_daily.csv                       TNX / DXY / VIX / EURUSD aligned daily
  charts/master_segA.png, master_segB.png    Daily candles + 3-scale zigzag (verification)
  charts/master_interactive.html             Zoomable plotly chart of BOTH segments
  FOUNDATION.md                              Machine + human description for subagents
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backtest", "data")
OUT = os.path.dirname(os.path.abspath(__file__))
ODATA = os.path.join(OUT, "data")
OCHART = os.path.join(OUT, "charts")

# Zigzag reversal thresholds (% from last extreme) -> Dow trend hierarchy
SCALES = {"primary": 6.0, "secondary": 3.0, "minor": 1.5}

GAP_START = "2025-04-01"
GAP_END = "2025-11-19"


# --------------------------------------------------------------------------- #
# Resampling
# --------------------------------------------------------------------------- #
def load_bars():
    df = pd.read_parquet(os.path.join(DATA, "bars_M15.parquet"))
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time").sort_index()


def resample(df, rule):
    o = df.resample(rule, label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), ticks=("ticks", "sum"),
    )
    return o.dropna(subset=["open"])


def split_segments(df):
    a = df[df.index < GAP_START]
    b = df[df.index >= GAP_END]
    return a, b


# --------------------------------------------------------------------------- #
# Zigzag (percentage reversal on high/low)
# --------------------------------------------------------------------------- #
def zigzag_pct(dates, highs, lows, pct, one_pivot_per_bar=False):
    """Alternating H/L pivots; a leg confirms once price retraces `pct`% from the
    running extreme. Returns DataFrame[date, price, kind] kind in {H,L}.

    one_pivot_per_bar: a reversal only counts on a bar AFTER the one that set the
    extreme. Without it, a single wide bar that both extends the extreme and
    retraces `pct`% becomes the H (or L) and also opens the next leg, so it can
    carry both an H and an L — the bar's intrabar order is unknown, so that pair
    is not real structure. Default False keeps the study's published CSVs
    reproducible; the chart viewer (plot_xau.py) passes True."""
    pct = pct / 100.0
    n = len(highs)
    if n == 0:
        return pd.DataFrame(columns=["date", "price", "kind"])
    piv = []
    trend = 0                       # 0 unknown, +1 up-leg, -1 down-leg
    hi_i, hi = 0, highs[0]
    lo_i, lo = 0, lows[0]
    for i in range(1, n):
        if trend >= 0:              # looking for a swing high to end an up-leg
            if highs[i] >= hi:
                hi, hi_i = highs[i], i
            if (not one_pivot_per_bar or hi_i < i) and lows[i] <= hi * (1 - pct):
                piv.append((hi_i, hi, "H"))
                trend = -1
                lo, lo_i = lows[i], i
                continue
        if trend <= 0:              # looking for a swing low to end a down-leg
            if lows[i] <= lo:
                lo, lo_i = lows[i], i
            if (not one_pivot_per_bar or lo_i < i) and highs[i] >= lo * (1 + pct):
                piv.append((lo_i, lo, "L"))
                trend = 1
                hi, hi_i = highs[i], i
    # tail: append the still-developing extreme so the line reaches the edge
    if trend >= 0:
        piv.append((hi_i, hi, "H"))
    elif trend < 0:
        piv.append((lo_i, lo, "L"))
    # drop duplicate consecutive same-kind (keep more extreme) — safety
    out = []
    for idx, price, kind in piv:
        if out and out[-1][2] == kind:
            if (kind == "H" and price >= out[-1][1]) or (kind == "L" and price <= out[-1][1]):
                out[-1] = (idx, price, kind)
            continue
        out.append((idx, price, kind))
    return pd.DataFrame(
        {"date": [dates[i] for i, _, _ in out],
         "price": [p for _, p, _ in out],
         "kind": [k for _, _, k in out]}
    )


# --------------------------------------------------------------------------- #
# Macro
# --------------------------------------------------------------------------- #
def load_macro():
    files = {
        "TNX": "macro__TNX_daily.parquet",
        "DXY": "macro_DX_Y_NYB_daily.parquet",
        "VIX": "macro__VIX_daily.parquet",
        "EURUSD": "macro_EURUSD_X_daily.parquet",
    }
    out = {}
    for k, f in files.items():
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            d = pd.read_parquet(p)
            d["time"] = pd.to_datetime(d["time"], utc=True)
            out[k] = d.set_index("time")["close"].rename(k)
    m = pd.concat(out.values(), axis=1).sort_index()
    return m


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    df = load_bars()
    segs = {"segA": df[df.index < GAP_START], "segB": df[df.index >= GAP_END]}

    summary = {}
    for seg, sdf in segs.items():
        daily = resample(sdf, "1D")
        h4 = resample(sdf, "4h")
        weekly = resample(sdf, "1W")
        daily.to_csv(os.path.join(ODATA, f"daily_{seg}.csv"))
        h4.to_csv(os.path.join(ODATA, f"h4_{seg}.csv"))
        weekly.to_csv(os.path.join(ODATA, f"weekly_{seg}.csv"))

        zz = {}
        for scale, pct in SCALES.items():
            z = zigzag_pct(daily.index.to_list(), daily["high"].values,
                           daily["low"].values, pct)
            z.to_csv(os.path.join(ODATA, f"zigzag_{seg}_{scale}.csv"), index=False)
            zz[scale] = z

        summary[seg] = {
            "rows_M15": len(sdf),
            "daily_bars": len(daily),
            "start": str(daily.index.min().date()),
            "end": str(daily.index.max().date()),
            "open": float(daily["open"].iloc[0]),
            "close": float(daily["close"].iloc[-1]),
            "low": float(daily["low"].min()),
            "high": float(daily["high"].max()),
            "pivots": {s: len(z) for s, z in zz.items()},
        }

    macro = load_macro()
    macro.to_csv(os.path.join(ODATA, "macro_daily.csv"))

    # charts
    make_charts(segs)

    write_foundation_md(summary, macro)
    print("FOUNDATION BUILD COMPLETE")
    for seg, s in summary.items():
        print(f"  {seg}: {s['start']}..{s['end']}  daily={s['daily_bars']}  "
              f"O={s['open']:.0f} C={s['close']:.0f} L={s['low']:.0f} H={s['high']:.0f}  "
              f"pivots={s['pivots']}")


def make_charts(segs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    colors = {"primary": "#d62728", "secondary": "#1f77b4", "minor": "#bbbbbb"}
    titles = {"segA": "Segment A  —  Jan-Mar 2025  (XAU/USD Daily)",
              "segB": "Segment B  —  Nov 2025-May 2026  (XAU/USD Daily)"}

    for seg, sdf in segs.items():
        daily = resample(sdf, "1D")
        fig, ax = plt.subplots(figsize=(16, 8))
        # candles via simple high-low + open/close bars on integer x to avoid weekend gaps
        x = np.arange(len(daily))
        for i, (_, row) in enumerate(daily.iterrows()):
            up = row["close"] >= row["open"]
            c = "#2ca02c" if up else "#d62728"
            ax.plot([i, i], [row["low"], row["high"]], color=c, lw=0.6, alpha=0.7)
            ax.add_patch(plt.Rectangle((i - 0.3, min(row["open"], row["close"])),
                                       0.6, max(abs(row["close"] - row["open"]), 0.01),
                                       color=c, alpha=0.85))
        dmap = {d: i for i, d in enumerate(daily.index)}
        for scale in ["minor", "secondary", "primary"]:
            z = pd.read_csv(os.path.join(ODATA, f"zigzag_{seg}_{scale}.csv"),
                            parse_dates=["date"])
            if z.empty:
                continue
            z["date"] = pd.to_datetime(z["date"], utc=True)
            xs = [dmap.get(d) for d in z["date"]]
            pairs = [(xx, pp, kk) for xx, pp, kk in zip(xs, z["price"], z["kind"]) if xx is not None]
            if len(pairs) < 2:
                continue
            xx = [p[0] for p in pairs]; yy = [p[1] for p in pairs]
            lw = {"primary": 2.4, "secondary": 1.4, "minor": 0.7}[scale]
            ax.plot(xx, yy, color=colors[scale], lw=lw, alpha=0.9,
                    label=f"{scale} zigzag ({SCALES[scale]}%)",
                    marker="o", ms={"primary": 6, "secondary": 4, "minor": 2}[scale])
            if scale == "primary":
                for p in pairs:
                    ax.annotate(f"{p[1]:.0f}", (p[0], p[1]),
                                textcoords="offset points",
                                xytext=(0, 9 if p[2] == "H" else -16),
                                ha="center", fontsize=8, color=colors["primary"])
        # date ticks
        step = max(1, len(daily) // 12)
        ax.set_xticks(x[::step])
        ax.set_xticklabels([d.strftime("%Y-%m-%d") for d in daily.index[::step]],
                           rotation=45, ha="right", fontsize=8)
        ax.set_title(titles[seg], fontsize=13, weight="bold")
        ax.set_ylabel("XAU/USD"); ax.legend(loc="upper left", fontsize=9)
        ax.grid(alpha=0.15)
        fig.tight_layout()
        fig.savefig(os.path.join(OCHART, f"master_{seg}.png"), dpi=130)
        plt.close(fig)

    make_interactive(segs)


def make_interactive(segs):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "Segment A — Jan-Mar 2025", "Segment B — Nov 2025-May 2026"),
        horizontal_spacing=0.05)
    zzcolor = {"primary": "#d62728", "secondary": "#1f77b4"}
    for col, seg in enumerate(["segA", "segB"], start=1):
        daily = resample(segs[seg], "1D")
        fig.add_trace(go.Candlestick(
            x=daily.index, open=daily["open"], high=daily["high"],
            low=daily["low"], close=daily["close"], name=f"{seg} Daily",
            showlegend=False), row=1, col=col)
        for scale in ["secondary", "primary"]:
            z = pd.read_csv(os.path.join(ODATA, f"zigzag_{seg}_{scale}.csv"),
                            parse_dates=["date"])
            if z.empty:
                continue
            fig.add_trace(go.Scatter(
                x=z["date"], y=z["price"], mode="lines+markers",
                line=dict(color=zzcolor[scale],
                          width=3 if scale == "primary" else 1.5),
                name=f"{seg} {scale}", showlegend=(col == 1)), row=1, col=col)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=col)
    fig.update_layout(
        title="XAU/USD 16-Month Structure — two real-data segments "
              "(7.5-month gap between them NOT shown)",
        template="plotly_white", height=750, width=1700)
    fig.write_html(os.path.join(OCHART, "master_interactive.html"))


def write_foundation_md(summary, macro):
    def macro_at(date):
        try:
            row = macro.loc[:date].iloc[-1]
            return f"TNX {row.TNX:.2f} | DXY {row.DXY:.1f} | VIX {row.VIX:.1f}"
        except Exception:
            return "n/a"

    lines = []
    lines.append("# FOUNDATION — XAU/USD 16-Month Market-Structure Study\n")
    lines.append("## CRITICAL DATA REALITY\n")
    lines.append("The feed spans 2025-01-01 .. 2026-05-19 but is **discontinuous**. "
                 "A ~233-day hole (2025-04-01 .. 2025-11-19) splits it into TWO segments. "
                 "**Never analyze structure across the gap** — treat A and B as separate regimes.\n")
    for seg, s in summary.items():
        lines.append(f"### {seg}")
        lines.append(f"- Span: {s['start']} .. {s['end']}  ({s['daily_bars']} daily bars)")
        lines.append(f"- Open {s['open']:.0f} -> Close {s['close']:.0f}; "
                     f"Low {s['low']:.0f} / High {s['high']:.0f} "
                     f"(range {(s['high']-s['low']):.0f} pts, "
                     f"{(s['high']/s['low']-1)*100:.1f}%)")
        lines.append(f"- Zigzag pivots: {s['pivots']}")
        lines.append("")
    lines.append("## Macro context (daily, continuous incl. the gap)")
    lines.append(f"- At 2025-01-02: {macro_at('2025-01-02')}")
    lines.append(f"- At 2025-03-28: {macro_at('2025-03-28')}")
    lines.append(f"- At 2025-11-19: {macro_at('2025-11-19')}")
    lines.append(f"- At 2026-01-28 (peak): {macro_at('2026-01-28')}")
    lines.append(f"- At 2026-05-18: {macro_at('2026-05-18')}")
    lines.append("")
    lines.append("## Artifacts (all paths relative to MarketStructure/)")
    lines.append("- `data/daily_<seg>.csv`, `data/h4_<seg>.csv`, `data/weekly_<seg>.csv`")
    lines.append("- `data/zigzag_<seg>_<primary|secondary|minor>.csv` "
                 "(columns: date, price, kind[H/L]); thresholds "
                 f"{SCALES}")
    lines.append("- `data/macro_daily.csv` (TNX, DXY, VIX, EURUSD)")
    lines.append("- `charts/master_segA.png`, `charts/master_segB.png`, "
                 "`charts/master_interactive.html`")
    with open(os.path.join(OUT, "FOUNDATION.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
