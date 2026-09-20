"""Find candidate duplicate concepts across study units.

Parallel agents coin their own ids, so the same idea arrives as
`small-wick-expansion-rule` from one unit and `small-wick-supports-expansion`
from another. Left alone the library fragments and a later consumer sees two
half-evidenced concepts instead of one well-evidenced one.

This script does NOT merge automatically. Some near-neighbours are genuinely
distinct (`internal-range-liquidity` vs `external-range-liquidity` differ by one
token but are opposites). It emits ranked candidate groups for a human/curator
decision, plus a starter alias map to edit.

Similarity = weighted blend of:
  * token Jaccard over id + name + aliases (structure of the label)
  * token Jaccard over the definition (what it actually claims)
Antonym guard: pairs whose only difference is an opposing token pair
(internal/external, bullish/bearish, high/low, buy/sell) are demoted, since
those are the classic false positives.

Writes research/meta/dedupe_candidates.md and research/meta/alias_map.starter.yaml
"""
from __future__ import annotations

import itertools
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "concepts" / "_inbox"
META = ROOT / "meta"

STOP = {"the", "a", "an", "of", "to", "in", "on", "is", "it", "and", "or", "for",
        "that", "this", "with", "as", "be", "by", "at", "from", "not", "you",
        "price", "candle", "trade", "rule", "concept"}

ANTONYMS = [("internal", "external"), ("bullish", "bearish"), ("high", "low"),
            ("buy", "sell"), ("buyside", "sellside"), ("up", "down"),
            ("long", "short"), ("premium", "discount"), ("before", "after")]

THRESHOLD = 0.34


def toks(*parts: str) -> set[str]:
    text = " ".join(str(p or "") for p in parts).lower()
    words = re.split(r"[^a-z0-9]+", text)
    return {w for w in words if w and w not in STOP and len(w) > 2}


def jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def antonym_split(a: set, b: set) -> bool:
    """True if the sets differ chiefly by an antonym pair -> likely NOT duplicates."""
    only_a, only_b = a - b, b - a
    for x, y in ANTONYMS:
        if (x in only_a and y in only_b) or (y in only_a and x in only_b):
            return True
    return False


def main() -> int:
    docs = []
    for f in sorted(INBOX.glob("*.yaml")):
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        docs.append({
            "file": f.name,
            "unit": f.stem.split("__", 1)[0],
            "id": str(d.get("id") or f.stem),
            "name": str(d.get("name") or ""),
            "category": str(d.get("category") or "?"),
            "status": str(d.get("status") or "?"),
            "label_toks": toks(d.get("id"), d.get("name"), " ".join(d.get("aliases") or [])),
            "def_toks": toks(d.get("definition")),
        })

    pairs = []
    for a, b in itertools.combinations(docs, 2):
        if a["id"] == b["id"]:
            continue
        lab = jac(a["label_toks"], b["label_toks"])
        dfn = jac(a["def_toks"], b["def_toks"])
        score = 0.65 * lab + 0.35 * dfn
        if a["category"] != b["category"]:
            score *= 0.85                      # cross-category dupes are rarer
        anto = antonym_split(a["label_toks"], b["label_toks"])
        if anto:
            score *= 0.45
        if score >= THRESHOLD:
            pairs.append((score, lab, dfn, anto, a, b))
    pairs.sort(key=lambda p: -p[0])

    lines = ["# Duplicate concept candidates", "",
             f"{len(docs)} drafts compared; {len(pairs)} candidate pairs at "
             f"score >= {THRESHOLD}.", "",
             "Nothing here is merged automatically. `antonym?` marks pairs whose "
             "labels differ mainly by an opposing term — those are usually "
             "**distinct** concepts, not duplicates, and are scored down.", "",
             "| score | label | defn | antonym? | A | B |",
             "|---:|---:|---:|:--:|---|---|"]
    for score, lab, dfn, anto, a, b in pairs:
        lines.append(
            f"| {score:.2f} | {lab:.2f} | {dfn:.2f} | {'YES' if anto else ''} | "
            f"`{a['id']}` <br><sub>{a['unit']} · {a['category']}</sub> | "
            f"`{b['id']}` <br><sub>{b['unit']} · {b['category']}</sub> |")

    (META / "dedupe_candidates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    starter = {"# how to use": "map ALIAS_ID -> CANONICAL_ID; merge_concepts reads this",
               "aliases": {}}
    for score, lab, dfn, anto, a, b in pairs:
        if score >= 0.55 and not anto:
            loser, winner = sorted([a["id"], b["id"]], key=len, reverse=True)
            starter["aliases"].setdefault(loser, winner)
    (META / "alias_map.starter.yaml").write_text(
        yaml.safe_dump(starter, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print(f"{len(docs)} drafts -> {len(pairs)} candidate pairs")
    print(f"{'score':>5}  {'ant':>3}  A / B")
    for score, lab, dfn, anto, a, b in pairs[:30]:
        print(f"{score:5.2f}  {'YES' if anto else '   ':>3}  {a['id']}  ||  {b['id']}")
    print(f"\nwrote {META / 'dedupe_candidates.md'}")
    print(f"wrote {META / 'alias_map.starter.yaml'} "
          f"({len(starter['aliases'])} high-confidence suggestions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
