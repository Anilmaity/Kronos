"""Measure the three contested CISD readings against real XAUUSD.

`concepts/entry/cisd.yaml` is `contested`: the corpus gives three incompatible
answers to "which level must price close through", and one speaker rejects the
opening-price rule by name. That disagreement is usually left as a footnote. Here
it is made numeric — how often each reading fires, how long it makes you wait,
and how much they overlap.

Writes research/meta/cisd_reading_comparison.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample                    # noqa: E402
from detectors.cisd import LEVEL_RULES, cisd_events   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["15min", "1h", "4h", "1D"]


def main() -> int:
    m1 = load_m1()
    print(f"loaded {len(m1):,} M1 bars")

    rows, overlaps = [], []
    for tf in TIMEFRAMES:
        df = resample(m1, tf)
        evs = {}
        for rule in LEVEL_RULES:
            ev = cisd_events(df, level_rule=rule, max_wait=40, min_series=2)
            evs[rule] = ev
            rows.append({
                "tf": tf, "rule": rule, "bars": len(df), "events": len(ev),
                "per_1k_bars": round(1000 * len(ev) / len(df), 1) if len(df) else 0,
                "median_wait": (round(float(ev["bars_waited"].median()), 1)
                                if len(ev) else float("nan")),
                "median_series": (round(float(ev["series_len"].median()), 1)
                                  if len(ev) else float("nan")),
            })
        # How often do two readings confirm on the SAME bar? If they nearly always
        # agree, the corpus's disagreement is academic; if rarely, it is material.
        base = evs["series_open"]
        if len(base):
            key = set(zip(base["direction"], base["confirm_time"]))
            for rule in ("series_extreme", "series_close"):
                other = evs[rule]
                k2 = set(zip(other["direction"], other["confirm_time"]))
                inter = len(key & k2)
                union = len(key | k2)
                overlaps.append({"tf": tf, "vs": rule,
                                 "same_bar": inter,
                                 "jaccard": round(inter / union, 3) if union else 0.0})

    L = ["# CISD — the three contested readings, measured", "",
         "`concepts/entry/cisd.yaml` carries `status: contested` because the corpus "
         "gives three incompatible answers to *which level* price must close through. "
         "One speaker explicitly rejects the opening-price rule. This table makes the "
         "disagreement measurable rather than rhetorical.", "",
         "- **series_close** — close beyond the last run candle's close (loosest)",
         "- **series_open** — close beyond the first run candle's open",
         "- **series_extreme** — close beyond the run's opposite extreme (strictest)",
         "",
         "Runs require >= 2 candles (`min_series=2`), matching the corpus's insistence "
         "that a CISD comes from a *series*, never a single candle.", "",
         "| TF | reading | bars | events | per 1k bars | median wait | median series |",
         "|---|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        L.append(f"| {r['tf']} | {r['rule']} | {r['bars']:,} | {r['events']:,} | "
                 f"{r['per_1k_bars']} | {r['median_wait']} | {r['median_series']} |")

    if overlaps:
        L += ["", "## Do the readings actually pick different moments?", "",
              "Agreement between `series_open` and each rival, counted as confirming "
              "the same direction on the same bar (Jaccard over the event sets).", "",
              "| TF | vs | same-bar events | Jaccard |", "|---|---|---:|---:|"]
        for o in overlaps:
            L.append(f"| {o['tf']} | {o['vs']} | {o['same_bar']:,} | {o['jaccard']} |")

    L += ["", "## Reading this", "",
          "A low Jaccard means the three readings are genuinely different trading "
          "systems wearing one name, and any result quoted for 'CISD' is "
          "under-specified until the reading is stated. A high one would mean the "
          "corpus's disagreement is cosmetic. Either way this is a prerequisite for "
          "attaching a performance number to the concept.",
          "",
          "Note these are *detections*, not trades — no direction filter, no target, "
          "no risk. Frequency alone says nothing about edge; see "
          "`primitive_base_rates.md` for why."]

    out = ROOT / "meta" / "cisd_reading_comparison.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[11:]))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
