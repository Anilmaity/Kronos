"""Assign every unique video to exactly ONE study unit, then chunk into batches.

Why this exists: 110 of the 443 videos appear in more than one playlist. Handing
each playlist to a subagent verbatim would duplicate ~25% of the corpus and let
two agents write conflicting notes on the same video. Instead each video is
assigned to its highest-priority playlist, and large units are split into
batches small enough for one agent to read carefully.

Writes research/meta/study_units.json and prints a plan table.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta"
TRANS = ROOT / "raw" / "transcripts"

# Highest educational density first. A video is assigned to the first playlist
# in this list that contains it.
PRIORITY = [
    "The Foundation",
    "Build A Model - Intro to TTrades Fractal Model (TTFM)",
    "Phases Of Price Series",
    "Weekly Profile Series",
    "Daily Profiles",
    "Chart Lessons",
    "Education - ICT (Updated)",
    "Education - ICT",
    "T Talks",
    "Trade Reviews",
    "Strat + ICT",
    "Resources",
    "Sunday Sessions - Live Q&A",
    "Live Stream Guests",
    "Live Streams",
    "Shorts",
]

# Max videos per subagent batch, tuned per unit type: long-form Q&A streams are
# far denser in tokens per video than Shorts.
BATCH = {
    "Live Streams": 4,
    "Sunday Sessions - Live Q&A": 4,
    "Live Stream Guests": 4,
    "T Talks": 6,
    "Shorts": 60,
}
DEFAULT_BATCH = 20


def _slug(title: str) -> str:
    """Full-title slug. Must not collapse 'Education - ICT (Updated)' and
    'Education - ICT' onto the same id -- they are different playlists and a
    collision would silently overwrite one unit's notes."""
    keep = [c.lower() if c.isalnum() else "_" for c in title]
    s = "".join(keep)
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")[:44]


def main() -> int:
    pls = json.loads((META / "playlists.json").read_text(encoding="utf-8"))
    by_title = {p["title"]: p for p in pls}
    missing = [t for t in PRIORITY if t not in by_title]
    extra = [p["title"] for p in pls if p["title"] not in PRIORITY]
    if missing:
        print(f"!! PRIORITY names not found in playlists.json: {missing}")
    if extra:
        print(f"!! playlists absent from PRIORITY (will be dropped): {extra}")

    assigned: dict[str, str] = {}
    meta: dict[str, dict] = {}
    for title in PRIORITY:
        p = by_title.get(title)
        if not p:
            continue
        for v in p["videos"]:
            if v["id"] not in assigned:
                assigned[v["id"]] = title
                meta[v["id"]] = v

    units = []
    for title in PRIORITY:
        vids = [meta[i] for i, t in assigned.items() if t == title]
        if not vids:
            continue
        vids.sort(key=lambda v: v["title"])
        size = BATCH.get(title, DEFAULT_BATCH)
        chunks = [vids[i:i + size] for i in range(0, len(vids), size)]
        for n, ch in enumerate(chunks, 1):
            have = sum(1 for v in ch if (TRANS / f"{v['id']}.txt").exists())
            units.append({
                "unit_id": f"{_slug(title)}_{n:02d}",
                "playlist": title,
                "batch": n,
                "of": len(chunks),
                "videos": ch,
                "n_videos": len(ch),
                "transcripts_present": have,
                "runtime_sec": sum(v.get("duration") or 0 for v in ch),
            })

    (META / "study_units.json").write_text(
        json.dumps(units, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nunique videos assigned: {len(assigned)}  |  study units: {len(units)}\n")
    print(f"{'unit_id':34} {'videos':>6} {'transcripts':>12} {'runtime':>9}")
    print("-" * 66)
    for u in units:
        hrs = u["runtime_sec"] / 3600
        print(f"{u['unit_id']:34} {u['n_videos']:>6} "
              f"{u['transcripts_present']:>7}/{u['n_videos']:<4} {hrs:>8.1f}h")
    print(f"\nwrote {META / 'study_units.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
