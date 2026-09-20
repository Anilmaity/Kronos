"""Build the consumable index over the merged concept library.

Two outputs:
  concepts/INDEX.md    — human-readable, grouped by category, flags gaps
  concepts/index.json  — machine-readable manifest for later analysis/strategy code

The JSON is the contract for downstream consumers: id, name, category, status,
timeframes, whether it has decidable detection rules, source video ids, and the
file path. A consumer can filter to `status == specified and has_rules` to get
only the concepts that are actually implementable today.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "concepts"

SKIP_DIRS = {"_inbox"}


def load_all() -> list[dict]:
    out = []
    for d in sorted(CONCEPTS.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith("_"):
            continue
        for f in sorted(d.glob("*.yaml")):
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(doc, dict):
                doc["_path"] = f"concepts/{d.name}/{f.name}"
                out.append(doc)
    return out


def main() -> int:
    docs = load_all()
    if not docs:
        print("no concepts in library — run merge_concepts.py first")
        return 1

    by_cat: dict[str, list] = defaultdict(list)
    for d in docs:
        by_cat[str(d.get("category", "uncategorized"))].append(d)

    status_counts = Counter(str(d.get("status", "?")) for d in docs)
    voice_counts = Counter(str(d.get("voice", "unknown")) for d in docs)
    with_rules = sum(1 for d in docs if d.get("detection_rules"))
    implementable = [d for d in docs
                     if d.get("status") == "specified" and d.get("detection_rules")]
    core = [d for d in implementable if d.get("voice") in ("ttrades", "mixed")]
    all_sources = {s.get("video_id") for d in docs for s in (d.get("sources") or [])
                   if isinstance(s, dict)}

    manifest = []
    for d in sorted(docs, key=lambda x: (x.get("category", ""), x.get("id", ""))):
        manifest.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "category": d.get("category"),
            "status": d.get("status"),
            "voice": d.get("voice"),
            "guest_sources": d.get("guest_sources") or [],
            "aliases": d.get("aliases") or [],
            "timeframes": d.get("timeframes") or {},
            "has_detection_rules": bool(d.get("detection_rules")),
            "n_detection_rules": len(d.get("detection_rules") or []),
            "n_ambiguities": len(d.get("ambiguities") or []),
            "source_video_ids": [s.get("video_id") for s in (d.get("sources") or [])
                                 if isinstance(s, dict)],
            "contributing_units": d.get("contributing_units") or [],
            "related": d.get("related") or [],
            "path": d["_path"],
        })
    (CONCEPTS / "index.json").write_text(
        json.dumps({"concepts": manifest,
                    "counts": {"total": len(docs),
                               "by_category": {k: len(v) for k, v in sorted(by_cat.items())},
                               "by_status": dict(status_counts),
                               "with_detection_rules": with_rules,
                               "implementable_now": len(implementable)}},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")

    L = ["# Concept index — TTrades_edu", "",
         f"**{len(docs)} concepts** distilled from {len(all_sources)} source videos.", "",
         "| status | n |", "|---|---:|"]
    for s, n in status_counts.most_common():
        L.append(f"| {s} | {n} |")
    L += ["", "| voice | n |", "|---|---:|"]
    for v, n in voice_counts.most_common():
        L.append(f"| {v} | {n} |")
    L += ["",
          f"- with `detection_rules`: **{with_rules}**",
          f"- implementable today (`specified` **and** has rules): **{len(implementable)}**",
          f"- of those, TTrades' own voice (excludes guests): **{len(core)}**",
          "",
          "`voice` matters more than it looks. **T Talks** and **Live Stream Guests** "
          "are interviews — each episode is a different trader with his own, often "
          "contradictory, methodology. A `guest` concept is evidence of what that "
          "guest teaches, NOT of what this channel teaches. Filter to "
          "`voice in (ttrades, mixed)` for the channel's own method; treat `guest` "
          "entries as a comparative library.",
          "",
          "`status` meanings: **specified** = decidable from a chart as taught; "
          "**underspecified** = taught but missing a threshold/definition needed to "
          "decide it (see each file's `ambiguities`); **contested** = two units read "
          "it differently, both readings preserved.",
          ""]

    for cat, items in sorted(by_cat.items()):
        L.append(f"## {cat} ({len(items)})")
        L.append("")
        L.append("| concept | voice | status | rules | sources | file |")
        L.append("|---|---|---|---:|---:|---|")
        for d in sorted(items, key=lambda x: str(x.get("id"))):
            L.append(f"| **{d.get('id')}** — {d.get('name','')} | {d.get('voice','?')} | "
                     f"{d.get('status')} | {len(d.get('detection_rules') or [])} | "
                     f"{len(d.get('sources') or [])} | `{d['_path']}` |")
        L.append("")

    if implementable:
        L += ["## Implementable today", "",
              "These have a status of `specified` and concrete detection rules, so a "
              "detector can be written and backtested without further source work.", ""]
        for d in sorted(implementable, key=lambda x: str(x.get("id"))):
            L.append(f"- `{d.get('id')}` — {d.get('name','')}")
        L.append("")

    (CONCEPTS / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"{len(docs)} concepts indexed")
    print(f"  by status: {dict(status_counts)}")
    print(f"  with detection_rules: {with_rules}")
    print(f"  implementable now: {len(implementable)}")
    print(f"  distinct source videos: {len(all_sources)}")
    print(f"wrote {CONCEPTS/'INDEX.md'} and {CONCEPTS/'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
