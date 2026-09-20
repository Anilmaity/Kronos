"""Profile the enumerated corpus: per-playlist counts, durations, overlap.

Prints a table and writes research/meta/corpus_report.md so the study plan is
reproducible rather than eyeballed.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta"

pls = json.loads((META / "playlists.json").read_text(encoding="utf-8"))


def hms(sec: float | None) -> str:
    if not sec:
        return "?"
    sec = int(sec)
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"


# Which playlists claim each video (overlap detection).
owner = Counter()
for p in pls:
    for v in p["videos"]:
        owner[v["id"]] += 1

rows = []
for p in sorted(pls, key=lambda x: -x["video_count"]):
    durs = [v["duration"] for v in p["videos"] if v.get("duration")]
    total = sum(durs)
    med = sorted(durs)[len(durs) // 2] if durs else 0
    rows.append({
        "title": p["title"],
        "n": p["video_count"],
        "total_sec": total,
        "median_sec": med,
        "no_dur": sum(1 for v in p["videos"] if not v.get("duration")),
    })

all_vids = {v["id"]: v for p in pls for v in p["videos"]}
grand = sum(v["duration"] or 0 for v in all_vids.values())
shorts_ids = {v["id"] for p in pls if p["title"] == "Shorts" for v in p["videos"]}
non_short = {k: v for k, v in all_vids.items() if k not in shorts_ids}
grand_ns = sum(v["duration"] or 0 for v in non_short.values())

lines = ["# Corpus report — TTrades_edu", "",
         f"- playlists: **{len(pls)}**",
         f"- unique videos: **{len(all_vids)}** (slots {sum(p['video_count'] for p in pls)})",
         f"- total runtime: **{hms(grand)}**",
         f"- excluding Shorts: **{len(non_short)}** videos, **{hms(grand_ns)}**",
         f"- videos in >1 playlist: **{sum(1 for c in owner.values() if c > 1)}**",
         "", "| playlist | videos | runtime | median | no-duration |",
         "|---|---:|---:|---:|---:|"]
for r in rows:
    lines.append(f"| {r['title']} | {r['n']} | {hms(r['total_sec'])} | "
                 f"{hms(r['median_sec'])} | {r['no_dur']} |")

out = META / "corpus_report.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(f"\nwrote {out}")
