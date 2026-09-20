"""Merge per-unit concept drafts from concepts/_inbox into the concept library.

Parallel study agents each write `_inbox/<unit_id>__<concept-id>.yaml`, so the
same concept can be drafted independently by several units. This script folds
those drafts together by concept id:

  * list fields (aliases, preconditions, detection_rules, invalidation,
    measurable, sources, ambiguities, related, external_corroboration) are
    unioned, order-preserving, deduplicated;
  * scalar fields (name, definition, category, status) are taken from the draft
    with the most sources, and any *disagreeing* alternative is preserved under
    `variants` rather than silently dropped;
  * `status` escalates: if any draft says `contested`, the merged entry is
    contested; else if any says `underspecified`, it is underspecified.

Nothing is overwritten in place: the merged library is rebuilt from _inbox every
run, so re-running after new agents finish is always safe.

Usage: python merge_concepts.py [--check]   (--check = report only, write nothing)
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "concepts"
INBOX = CONCEPTS / "_inbox"

LIST_FIELDS = ["aliases", "preconditions", "detection_rules", "invalidation",
               "measurable", "sources", "ambiguities", "related",
               "external_corroboration", "targets", "guest_sources"]

# Playlists that are GUEST content rather than TTrades' own teaching. T Talks and
# Live Stream Guests are interviews: each episode is a different trader with his
# own (often mutually contradictory) methodology. Without this distinction the
# library silently presents a guest's rule as if the channel taught it, and the
# `contested` flag stops meaning "the channel is inconsistent" and starts meaning
# "two different people disagree", which is a completely different claim.
GUEST_PLAYLISTS = {"T Talks", "Live Stream Guests", "Strat + ICT"}
SCALARS = ["name", "definition", "category", "status", "python_detector"]
STATUS_RANK = {"specified": 0, "underspecified": 1, "contested": 2}
VALID_CATEGORIES = {"structure", "liquidity", "time", "entry", "risk", "model",
                    "psychology"}


def _norm(x) -> str:
    """Normalized form for dedupe: whitespace-collapsed, case-insensitive."""
    if isinstance(x, (dict, list)):
        return json.dumps(x, sort_keys=True, ensure_ascii=False).lower()
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def _union(values: list) -> list:
    out, seen = [], set()
    for v in values:
        k = _norm(v)
        if k and k not in seen:
            seen.add(k)
            out.append(v)
    return out


def load_drafts() -> dict[str, list[dict]]:
    drafts: dict[str, list[dict]] = defaultdict(list)
    bad = []
    for f in sorted(INBOX.glob("*.yaml")):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append((f.name, f"unparseable: {exc}"))
            continue
        if not isinstance(doc, dict):
            bad.append((f.name, "not a YAML mapping"))
            continue
        cid = doc.get("id") or (f.stem.split("__", 1)[1] if "__" in f.stem else f.stem)
        doc["_file"] = f.name
        doc["_unit"] = f.stem.split("__", 1)[0] if "__" in f.stem else "?"
        drafts[str(cid)].append(doc)
    if bad:
        print("!! skipped malformed drafts:")
        for n, why in bad:
            print(f"   {n}: {why}")
    return drafts


def merge(cid: str, docs: list[dict]) -> dict:
    # Primary = the draft citing the most sources (best-evidenced reading).
    docs = sorted(docs, key=lambda d: -len(d.get("sources") or []))
    primary = docs[0]
    out: dict = {"id": cid}

    for k in SCALARS:
        vals = [d.get(k) for d in docs if d.get(k) not in (None, "", [])]
        if not vals:
            continue
        out[k] = vals[0] if k != "status" else max(
            vals, key=lambda s: STATUS_RANK.get(str(s), 0))
        variants = _union([v for v in vals if _norm(v) != _norm(out[k])])
        if variants and k in ("name", "definition", "category"):
            out.setdefault("variants", {})[k] = variants

    for k in LIST_FIELDS:
        merged = _union([v for d in docs for v in (d.get(k) or [])])
        if merged:
            out[k] = merged

    # timeframes / execution: shallow-merge dict fields, primary wins on clash.
    for k in ("timeframes", "execution"):
        combined: dict = {}
        for d in reversed(docs):
            if isinstance(d.get(k), dict):
                combined.update(d[k])
        if combined:
            out[k] = combined

    # `voice` declared per-draft by the agent that actually READ the video is
    # strictly better information than tag_voice()'s playlist heuristic: only a
    # reader can tell who is speaking *inside* a guest interview, or spot a
    # visiting trader inside one of TTrades' own streams. Carry it through so
    # tag_voice() has something to defer to; without this the declaration was
    # silently discarded and recomputed from playlist membership alone.
    declared = {str(d["voice"]).strip().lower() for d in docs
                if str(d.get("voice", "")).strip().lower()
                in ("ttrades", "guest", "mixed")}
    if declared:
        out["voice_declared"] = "mixed" if len(declared) > 1 else declared.pop()

    out["contributing_units"] = sorted({d["_unit"] for d in docs})
    out["draft_count"] = len(docs)
    if "variants" in out and out.get("status") != "contested":
        out["status"] = "contested"
    return out


def _video_playlists() -> dict[str, list[str]]:
    pls = json.loads((ROOT / "meta" / "playlists.json").read_text(encoding="utf-8"))
    m: dict[str, list[str]] = {}
    for p in pls:
        for v in p["videos"]:
            m.setdefault(v["id"], []).append(p["title"])
    return m


def _video_titles() -> dict[str, str]:
    pls = json.loads((ROOT / "meta" / "playlists.json").read_text(encoding="utf-8"))
    return {v["id"]: v.get("title", "") for p in pls for v in p["videos"]}


def tag_voice(doc: dict, vp: dict[str, list[str]], vt: dict[str, str]) -> None:
    """Mark whether a concept comes from TTrades himself or from a guest.

    `voice` is 'ttrades' when every source video sits only in TTrades' own
    playlists, 'guest' when every source is guest content, and 'mixed' when a
    concept draws on both (which is genuine corroboration and worth seeing).
    `speakers` records the guest video titles so a reader can attribute a rule.
    """
    vids = [s.get("video_id") for s in (doc.get("sources") or [])
            if isinstance(s, dict) and s.get("video_id")]
    if not vids:
        return
    guest_flags, speakers = [], []
    for v in vids:
        names = vp.get(v, [])
        is_guest = bool(names) and all(n in GUEST_PLAYLISTS for n in names)
        guest_flags.append(is_guest)
        if is_guest:
            speakers.append(vt.get(v, v))
    derived = ("guest" if all(guest_flags)
               else "mixed" if any(guest_flags) else "ttrades")

    # A per-draft declaration beats the playlist heuristic, because the
    # heuristic cannot see *who is talking* within a video -- it would tag
    # TTrades' own statements inside a guest interview as `guest`, and a
    # visiting trader inside one of his streams as `ttrades`. Keep the derived
    # value alongside when they disagree so the discrepancy stays auditable
    # instead of vanishing.
    declared = doc.pop("voice_declared", None)
    doc["voice"] = declared or derived
    if declared and declared != derived:
        doc["voice_playlist"] = derived

    if speakers:
        doc["guest_sources"] = sorted(set(speakers)
                                      | set(doc.get("guest_sources") or []))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    if not INBOX.exists():
        print(f"no inbox at {INBOX} — nothing to merge")
        return 0

    drafts = load_drafts()
    if not drafts:
        print("inbox is empty — no concept drafts yet")
        return 0

    merged = {cid: merge(cid, docs) for cid, docs in drafts.items()}

    vp, vt = _video_playlists(), _video_titles()
    for doc in merged.values():
        tag_voice(doc, vp, vt)
    voices = defaultdict(int)
    for doc in merged.values():
        voices[doc.get("voice", "unknown")] += 1
    print(f"voice: " + ", ".join(f"{k}={v}" for k, v in sorted(voices.items())))

    by_cat: dict[str, list] = defaultdict(list)
    problems = []
    for cid, doc in sorted(merged.items()):
        cat = str(doc.get("category") or "uncategorized").strip().lower()
        if cat not in VALID_CATEGORIES:
            problems.append(f"{cid}: category '{cat}' not in {sorted(VALID_CATEGORIES)}")
            cat = "uncategorized"
        doc["category"] = cat
        if not doc.get("sources"):
            problems.append(f"{cid}: NO SOURCES — provenance is mandatory")
        if not doc.get("detection_rules"):
            problems.append(f"{cid}: no detection_rules (is it decidable?)")
        by_cat[cat].append(doc)

    print(f"drafts: {sum(len(v) for v in drafts.values())} files -> "
          f"{len(merged)} unique concepts")
    multi = {c: d["draft_count"] for c, d in merged.items() if d["draft_count"] > 1}
    if multi:
        print(f"merged from multiple units: {len(multi)}")
        for c, n in sorted(multi.items(), key=lambda kv: -kv[1])[:12]:
            print(f"   {c}  ({n} drafts)")
    contested = [c for c, d in merged.items() if d.get("status") == "contested"]
    if contested:
        print(f"contested (conflicting readings): {len(contested)} -> {contested[:10]}")

    if problems:
        print(f"\nquality flags ({len(problems)}):")
        for p in problems[:25]:
            print(f"   {p}")

    print("\nby category:")
    for cat, docs in sorted(by_cat.items()):
        print(f"   {cat:16} {len(docs)}")

    if args.check:
        print("\n--check: nothing written")
        return 0

    # Prune stale outputs first. Without this, a concept that was renamed or
    # recategorised in _inbox leaves its old file behind and the library slowly
    # accumulates ghosts that no draft supports -- which would defeat the whole
    # point of provenance.
    expected = {(doc["category"], f"{doc['id']}.yaml")
                for docs in by_cat.values() for doc in docs}
    pruned = 0
    for d in CONCEPTS.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        for f in d.glob("*.yaml"):
            if (d.name, f.name) not in expected:
                f.unlink()
                pruned += 1
        if not any(d.iterdir()):
            d.rmdir()
    if pruned:
        print(f"pruned {pruned} stale concept file(s) no longer backed by a draft")

    for cat, docs in by_cat.items():
        d = CONCEPTS / cat
        d.mkdir(parents=True, exist_ok=True)
        for doc in docs:
            clean = {k: v for k, v in doc.items() if not k.startswith("_")}
            (d / f"{doc['id']}.yaml").write_text(
                yaml.safe_dump(clean, sort_keys=False, allow_unicode=True,
                               default_flow_style=False, width=88),
                encoding="utf-8")
    print(f"\nwrote {sum(len(v) for v in by_cat.values())} concept files under {CONCEPTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
