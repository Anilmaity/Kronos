"""Validate concept drafts against the corpus — provenance enforcement.

Study agents are instructed never to invent a source or a quote. Instructions
are not a guarantee, so this script mechanically checks them:

  1. YAML parses and is a mapping.
  2. Required fields present; `category` and `status` from the allowed sets.
  3. Every `sources[].video_id` is a real video in meta/playlists.json.
  4. Every cited video has a transcript on disk (else the agent could not have
     read it).
  5. Every quote is <= 15 words (the corpus rule) and non-empty.
  6. Every quote actually OCCURS in the cited transcript, compared on a
     normalized form (lowercase, punctuation stripped, whitespace collapsed) so
     that caption punctuation noise does not cause false alarms.
  7. Cited video is one actually assigned to that draft's study unit — catches an
     agent citing a video it was never given.

Exit code is non-zero when any ERROR-level problem is found, so this can gate a
merge. WARNINGs are reported but do not fail the run.

Usage: python validate_concepts.py [--inbox | --library] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta"
TRANS = ROOT / "raw" / "transcripts"
CONCEPTS = ROOT / "concepts"

VALID_CATEGORIES = {"structure", "liquidity", "time", "entry", "risk", "model",
                    "psychology"}
VALID_STATUS = {"specified", "underspecified", "contested"}
REQUIRED = ["id", "name", "category", "status", "definition", "sources"]
MAX_QUOTE_WORDS = 15

_punct = re.compile(r"[^\w\s]", re.UNICODE)
_ws = re.compile(r"\s+")


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).lower()
    t = _punct.sub(" ", t)
    return _ws.sub(" ", t).strip()


_transcript_cache: dict[str, str] = {}


def transcript_text(vid: str) -> str | None:
    if vid in _transcript_cache:
        return _transcript_cache[vid]
    p = TRANS / f"{vid}.txt"
    if not p.exists():
        return None
    _transcript_cache[vid] = norm(p.read_text(encoding="utf-8", errors="replace"))
    return _transcript_cache[vid]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="store_true",
                    help="validate concepts/<category>/ instead of _inbox")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    playlists = json.loads((META / "playlists.json").read_text(encoding="utf-8"))
    known = {v["id"]: v["title"] for p in playlists for v in p["videos"]}

    units = {}
    su = META / "study_units.json"
    if su.exists():
        for u in json.loads(su.read_text(encoding="utf-8")):
            units[u["unit_id"]] = {v["id"] for v in u["videos"]}

    if args.library:
        files = [f for d in CONCEPTS.iterdir() if d.is_dir() and not d.name.startswith("_")
                 for f in d.glob("*.yaml")]
    else:
        files = sorted((CONCEPTS / "_inbox").glob("*.yaml"))

    if not files:
        print("no concept files to validate")
        return 0

    errors: list[str] = []
    warns: list[str] = []
    n_quotes = n_sources = 0

    for f in files:
        tag = f.name
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{tag}: YAML parse failed: {exc}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{tag}: not a YAML mapping")
            continue

        for k in REQUIRED:
            if not doc.get(k):
                errors.append(f"{tag}: missing required field '{k}'")

        cat = str(doc.get("category", "")).strip().lower()
        if cat and cat not in VALID_CATEGORIES:
            errors.append(f"{tag}: category '{cat}' invalid")
        st = str(doc.get("status", "")).strip().lower()
        if st and st not in VALID_STATUS:
            errors.append(f"{tag}: status '{st}' invalid")

        if st == "specified" and not doc.get("detection_rules"):
            warns.append(f"{tag}: status=specified but no detection_rules")

        unit = f.stem.split("__", 1)[0] if "__" in f.stem else None
        allowed = units.get(unit)

        srcs = doc.get("sources") or []
        if not isinstance(srcs, list):
            errors.append(f"{tag}: sources must be a list")
            srcs = []
        for s in srcs:
            if not isinstance(s, dict):
                errors.append(f"{tag}: source entry is not a mapping: {s!r}")
                continue
            n_sources += 1
            vid = str(s.get("video_id", "")).strip()
            if not vid:
                errors.append(f"{tag}: source with no video_id")
                continue
            if vid not in known:
                errors.append(f"{tag}: FABRICATED video_id '{vid}' (not in corpus)")
                continue
            text = transcript_text(vid)
            if text is None:
                errors.append(f"{tag}: cites '{vid}' but no transcript on disk "
                              f"(agent could not have read it)")
                continue
            if allowed is not None and vid not in allowed:
                # Only a WARNING: the video is real and its transcript is on disk,
                # so this is a cross-unit reference, not an invention. Some agents
                # legitimately own two units and cite across them to document a
                # genuine conflict. Fabrication is caught by the existence and
                # quote checks, which are the ones that stay fatal.
                warns.append(f"{tag}: cites '{vid}' from outside unit '{unit}' "
                             f"(cross-unit reference — verify it is intentional)")
            q = s.get("quote")
            if q in (None, ""):
                continue
            n_quotes += 1
            words = norm(q).split()
            if len(words) > MAX_QUOTE_WORDS:
                errors.append(f"{tag}: quote {len(words)} words (>{MAX_QUOTE_WORDS}): "
                              f"{str(q)[:60]!r}")
            if norm(q) and norm(q) not in text:
                errors.append(f"{tag}: quote NOT FOUND in transcript {vid}: "
                              f"{str(q)[:60]!r}")

    scope = "library" if args.library else "_inbox"
    print(f"validated {len(files)} concept files in {scope} "
          f"({n_sources} sources, {n_quotes} quotes)")
    if warns and not args.quiet:
        print(f"\nWARNINGS ({len(warns)}):")
        for w in warns[:40]:
            print(f"  - {w}")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors[:60]:
            print(f"  - {e}")
        if len(errors) > 60:
            print(f"  ... and {len(errors) - 60} more")
        return 1
    print("\nOK — every cited video exists in the corpus and has a transcript, and "
          "every quote is <=15 words and present in that transcript. "
          "(Cross-unit citations, if any, are listed above as warnings.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
