"""
build_h4_subwaves.py
--------------------
Carry the Primary-degree Elliott count down to H4: each motive Primary wave
subdivides into 5 sub-waves, each corrective into 3 (a-b-c). Total = 21 sub-waves,
the canonical next-degree count. Renders a 2x3 panel of H4 candles + labelled sub-waves.
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

# Each: title, (window_start, window_end), kind, [(timestamp, price, label), ...]
WAVES = [
    ("Wave (1)  2615->3500  (5: leading diagonal, iv~=i)", ("2025-01-04", "2025-04-24"), "motive", [
        ("2025-01-06 12:00", 2614.635, "0"),
        ("2025-02-24 12:00", 2956.310, "i"),
        ("2025-02-28 12:00", 2832.720, "ii"),
        ("2025-04-02 20:00", 3167.835, "iii"),
        ("2025-04-07 16:00", 2956.565, "iv"),
        ("2025-04-22 04:00", 3500.200, "v"),
    ]),
    ("Wave (2)  3500->3121  (3: a-b-c zigzag)", ("2025-04-21", "2025-05-17"), "corrective", [
        ("2025-04-22 04:00", 3500.200, "start"),
        ("2025-05-01 12:00", 3201.955, "a"),
        ("2025-05-06 20:00", 3435.055, "b"),
        ("2025-05-15 04:00", 3120.765, "c"),
    ]),
    ("Wave (3)  3121->4381  (5: extended iii)", ("2025-05-14", "2025-10-22"), "motive", [
        ("2025-05-15 04:00", 3120.765, "0"),
        ("2025-06-15 20:00", 3451.525, "i"),
        ("2025-06-29 20:00", 3244.415, "ii"),
        ("2025-10-16 20:00", 4380.990, "iii"),
        ("2025-10-17 16:00", 4185.910, "iv"),
        ("2025-10-20 16:00", 4381.440, "v"),
    ]),
    ("Wave (4)  4381->3886  (3: a-b-c)", ("2025-10-19", "2025-10-30"), "corrective", [
        ("2025-10-20 16:00", 4381.440, "start"),
        ("2025-10-22 00:00", 4004.280, "a"),
        ("2025-10-23 12:00", 4154.790, "b"),
        ("2025-10-28 08:00", 3886.465, "c"),
    ]),
    ("Wave (5)  3886->5602  (5: extended v blow-off)", ("2025-10-27", "2026-01-30"), "motive", [
        ("2025-10-28 08:00", 3886.465, "0"),
        ("2025-11-13 12:00", 4245.195, "i"),
        ("2025-11-18 04:00", 3997.985, "ii"),
        ("2025-12-26 16:00", 4550.150, "iii"),
        ("2025-12-31 04:00", 4274.025, "iv"),
        ("2026-01-28 20:00", 5602.225, "v"),
    ]),
    ("Correction A-B-C  5602->4099  (A,C=5 / B=3)", ("2026-01-27", "2026-03-25"), "corrective", [
        ("2026-01-28 20:00", 5602.225, "(5)"),
        ("2026-02-02 12:00", 4402.380, "A"),
        ("2026-03-02 12:00", 5419.660, "B"),
        ("2026-03-23 12:00", 4099.125, "C"),
    ]),
]


def main():
    h = pd.read_csv(os.path.join(ODATA, "cont_h4.csv"), parse_dates=["time"]).set_index("time")
    fig, axes = plt.subplots(2, 3, figsize=(22, 12))
    axes = axes.ravel()
    for ax, (title, (a, b), kind, pts) in zip(axes, WAVES):
        s = h[(h.index >= pd.Timestamp(a, tz="UTC")) & (h.index <= pd.Timestamp(b, tz="UTC"))]
        xmap = {ts: i for i, ts in enumerate(s.index)}
        for i, (_, r) in enumerate(s.iterrows()):
            up = r["close"] >= r["open"]; c = "#26a69a" if up else "#ef5350"
            ax.plot([i, i], [r["low"], r["high"]], color=c, lw=0.5, alpha=0.6, zorder=2)
            ax.add_patch(Rectangle((i - 0.4, min(r["open"], r["close"])), 0.8,
                                   max(abs(r["close"] - r["open"]), 0.01), color=c, alpha=0.85, zorder=2))

        def xf(tstr):
            ts = pd.Timestamp(tstr, tz="UTC")
            if ts in xmap:
                return xmap[ts]
            return int(s.index.searchsorted(ts).clip(0, len(s) - 1))

        col = "#1565c0" if kind == "motive" else "#c62828"
        xs = [xf(p[0]) for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=col, lw=2.2, marker="o", ms=7, zorder=4)
        ymin, ymax = s["low"].min(), s["high"].max(); pad = (ymax - ymin) * 0.07
        for (tstr, pr, lab), x in zip(pts, xs):
            if lab in ("0", "start", "(5)"):
                continue
            up = lab in ("i", "iii", "v", "b", "B")
            ax.annotate(lab, (x, pr), xytext=(x, pr + pad * (1 if up else -1)),
                        ha="center", va="bottom" if up else "top", fontsize=12, weight="bold",
                        color=col, zorder=6,
                        bbox=dict(boxstyle="circle,pad=0.22", fc="white", ec=col, lw=1.4))
        ax.set_title(title, fontsize=10.5, weight="bold")
        ax.set_ylim(ymin - pad * 2, ymax + pad * 2)
        step = max(1, len(s) // 6)
        ax.set_xticks(list(range(0, len(s), step)))
        ax.set_xticklabels([s.index[i].strftime("%m-%d") for i in range(0, len(s), step)],
                           fontsize=7, rotation=0)
        ax.grid(alpha=0.15)
        ax.set_ylabel("XAU/USD", fontsize=8)
    fig.suptitle("XAU/USD — Primary Elliott count carried onto H4: sub-wave subdivision "
                 "(5 per motive, 3 per corrective = 21 total)", fontsize=14, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    fig.savefig(os.path.join(OCHART, "WAVES_H4_subwaves.png"), dpi=125)
    plt.close(fig)
    print("wrote charts/WAVES_H4_subwaves.png")


if __name__ == "__main__":
    main()
