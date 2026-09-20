"""Aggregate what actually blocks automation of this methodology.

Every concept file records its own `ambiguities`. Individually they read as minor
caveats; in aggregate they reveal a small number of undefined terms that gate a
large number of concepts. Those terms — not the concepts — are the real work
items, because one definition can unblock a dozen detectors.

Outputs research/meta/automation_gaps.md:
  * undefined terms ranked by how many concepts they block
  * the underspecified/contested concepts grouped by category
  * a shortlist of concepts that are implementable RIGHT NOW in TTrades' own voice
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "concepts"

# Terms that recur as undefined thresholds across the corpus. Matched against the
# ambiguity text; the point is to rank them, not to be exhaustive.
WATCH = [
    "displacement", "relatively equal", "significant", "obvious", "small wick",
    "large wick", "shallow", "aggressive", "relevant", "strong", "clean",
    "average daily range", "adr", "equilibrium", "eq", "consolidation",
    "timezone", "session", "protected swing", "t-spot", "tspot",
    "standard deviation", "overextended", "exhaustion", "most of the",
]


def load() -> list[dict]:
    out = []
    for d in sorted(CONCEPTS.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        for f in sorted(d.glob("*.yaml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(doc, dict):
                doc["_path"] = f"concepts/{d.name}/{f.name}"
                out.append(doc)
    return out


def main() -> int:
    docs = load()
    if not docs:
        print("no concepts — run merge_concepts.py first")
        return 1

    term_hits: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        blob = " ".join(str(a) for a in (d.get("ambiguities") or [])).lower()
        if not blob:
            continue
        for t in WATCH:
            if re.search(r"\b" + re.escape(t) + r"\b", blob):
                term_hits[t].add(str(d.get("id")))

    ranked = sorted(term_hits.items(), key=lambda kv: -len(kv[1]))

    blocked = [d for d in docs if d.get("status") in ("underspecified", "contested")]
    by_cat: dict[str, list] = defaultdict(list)
    for d in blocked:
        by_cat[str(d.get("category"))].append(d)

    ready = [d for d in docs
             if d.get("status") == "specified" and d.get("detection_rules")
             and d.get("voice") in ("ttrades", "mixed")]

    n_amb = sum(len(d.get("ambiguities") or []) for d in docs)

    L = ["# Automation gaps", "",
         f"Across **{len(docs)} concepts** there are **{n_amb} recorded ambiguities**. "
         f"**{len(blocked)}** concepts are not directly implementable "
         f"(`underspecified` or `contested`).", "",
         "The useful observation is that these are not 56 independent problems. A "
         "handful of undefined terms gate most of them, so defining one term "
         "unblocks many detectors at once.", "",
         "## Undefined terms, ranked by concepts blocked", "",
         "| term | concepts blocked | examples |", "|---|---:|---|"]
    for t, ids in ranked:
        if not ids:
            continue
        ex = ", ".join(f"`{i}`" for i in sorted(ids)[:4])
        L.append(f"| **{t}** | {len(ids)} | {ex} |")

    L += ["", "## Not directly implementable, by category", ""]
    for cat, items in sorted(by_cat.items()):
        L.append(f"### {cat} ({len(items)})")
        L.append("")
        for d in sorted(items, key=lambda x: str(x.get("id"))):
            first = (d.get("ambiguities") or ["—"])[0]
            first = str(first)
            if len(first) > 150:
                first = first[:147] + "..."
            L.append(f"- `{d.get('id')}` ({d.get('status')}, {d.get('voice','?')}) — {first}")
        L.append("")

    L += ["## Implementable now, TTrades' own voice", "",
          f"**{len(ready)}** concepts are `specified`, carry detection rules, and are "
          "not guest material. These are the safe starting set for detector work.", ""]
    cat_ready = Counter(str(d.get("category")) for d in ready)
    L.append("| category | n |")
    L.append("|---|---:|")
    for c, n in sorted(cat_ready.items()):
        L.append(f"| {c} | {n} |")
    L.append("")
    for d in sorted(ready, key=lambda x: (str(x.get("category")), str(x.get("id")))):
        L.append(f"- `{d.get('id')}` ({d.get('category')}) — "
                 f"{len(d.get('detection_rules') or [])} rules")

    out = CONCEPTS.parent / "meta" / "automation_gaps.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"{len(docs)} concepts, {n_amb} ambiguities, {len(blocked)} not implementable")
    print(f"{len(ready)} implementable now in TTrades' own voice\n")
    print("top blocking terms:")
    for t, ids in ranked[:12]:
        print(f"  {len(ids):3}  {t}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
