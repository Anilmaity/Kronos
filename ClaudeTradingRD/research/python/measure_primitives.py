"""Measure primitive base rates on real XAUUSD, across timeframes.

Purpose: a concept that fires on 90% of candles is not a signal, and one that
fires 3 times in 3 years is not tradeable. Recording base rates up front keeps
the concept library honest and gives every later "edge" claim a denominator.

Writes research/meta/primitive_base_rates.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample                      # noqa: E402
from detectors.primitives import (                      # noqa: E402
    candle_range_sweep, displacement, fair_value_gaps, swing_points,
)

ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["15min", "1h", "4h", "1D"]


def pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:5.1f}%" if d else "    -"


def main() -> int:
    m1 = load_m1()
    print(f"loaded {len(m1):,} M1 bars  {m1.index.min()} -> {m1.index.max()}")

    rows = []
    for tf in TIMEFRAMES:
        df = resample(m1, tf)
        n = len(df)
        crt = candle_range_sweep(df)
        fvg = fair_value_gaps(df)
        sw = swing_points(df, 2, 2)
        disp = displacement(df)

        sh = int(crt["swept_high"].sum())
        sl = int(crt["swept_low"].sum())
        both = int(crt["swept_both"].sum())
        eu = int(crt["expansion_up"].sum())
        ed = int(crt["expansion_down"].sum())
        ib = int(crt["inside_bar"].sum())
        rows.append({
            "tf": tf, "bars": n,
            "sweep_any": sh + sl - both, "sweep_high": sh, "sweep_low": sl,
            "sweep_both": both, "expansion": eu + ed, "inside": ib,
            "fvg": int(fvg["bullish_fvg"].sum() + fvg["bearish_fvg"].sum()),
            "swings": int(sw["swing_high"].sum() + sw["swing_low"].sum()),
            "displacement": int(disp.sum()),
        })

    lines = [
        "# Primitive base rates — XAUUSD",
        "",
        f"Source: `m3_scalper/xau_m1_3y.parquet` — {len(m1):,} M1 bars, "
        f"{m1.index.min():%Y-%m-%d} to {m1.index.max():%Y-%m-%d}.",
        "",
        "Percentages are of bars on that timeframe. `sweep_*` requires the bar to "
        "close back inside the prior bar's range; a close beyond it is counted as "
        "`expansion` instead. That split is the single most important distinction "
        "in candle-range reasoning, so it is measured separately.",
        "",
        "| TF | bars | sweep any | high | low | both | expansion | inside | FVG | swings | displacement |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        n = r["bars"]
        lines.append(
            f"| {r['tf']} | {n:,} | {pct(r['sweep_any'], n)} | {pct(r['sweep_high'], n)} | "
            f"{pct(r['sweep_low'], n)} | {pct(r['sweep_both'], n)} | "
            f"{pct(r['expansion'], n)} | {pct(r['inside'], n)} | {pct(r['fvg'], n)} | "
            f"{pct(r['swings'], n)} | {pct(r['displacement'], n)} |")

    lines += [
        "",
        "## Reading this",
        "",
        "A daily candle sweeping the prior day's high or low is *ordinary*, not rare. "
        "Any concept built on 'price swept liquidity' therefore carries almost no "
        "information on its own — the edge, if there is one, has to come from the "
        "conditions attached to it (which level, at what time, in what HTF context). "
        "Treat these numbers as the null hypothesis every concept must beat.",
    ]
    out = ROOT / "meta" / "primitive_base_rates.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
