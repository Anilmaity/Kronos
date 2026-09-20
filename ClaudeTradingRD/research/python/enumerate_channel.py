"""Enumerate every playlist on a YouTube channel, then every video in each.

Writes research/meta/playlists.json:
    [{playlist_id, title, url, video_count, videos:[{id,title,duration,url}]}]

Uses yt-dlp in --flat-playlist mode (metadata only, no downloads). Run from
anywhere; paths resolve relative to this file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta"
META.mkdir(parents=True, exist_ok=True)

CHANNEL = "https://www.youtube.com/@TTrades_edu"


def ytdlp_json(url: str, items: str | None = None) -> dict:
    """Return yt-dlp's single-JSON dump for `url` (flat, metadata only).

    `items` sets --playlist-items. Without it yt-dlp's YouTube tab extractor
    stops at the first 100-entry page, which silently truncated the three
    largest playlists (108 / 141 / 229 real videos) on the first run.
    """
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist",
           "--dump-single-json", "--no-warnings"]
    if items:
        cmd += ["--playlist-items", items]
    cmd.append(url)
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise RuntimeError(f"yt-dlp failed for {url}: {(proc.stderr or '')[-500:]}")
    return json.loads(proc.stdout)


def main() -> int:
    print(f"[1/2] listing playlists on {CHANNEL} ...", flush=True)
    top = ytdlp_json(f"{CHANNEL}/playlists")
    entries = top.get("entries") or []
    print(f"      found {len(entries)} playlists")

    playlists = []
    for i, ent in enumerate(entries, 1):
        pid = ent.get("id")
        title = ent.get("title") or "(untitled)"
        purl = ent.get("url") or f"https://www.youtube.com/playlist?list={pid}"
        print(f"[2/2] ({i}/{len(entries)}) {title} ...", flush=True)
        try:
            detail = ytdlp_json(purl, items="1:2000")
        except Exception as exc:  # keep going; a single bad playlist is not fatal
            print(f"      !! {exc}")
            playlists.append({"playlist_id": pid, "title": title, "url": purl,
                              "video_count": 0, "videos": [], "error": str(exc)})
            continue
        vids = []
        for v in detail.get("entries") or []:
            if not v or not v.get("id"):
                continue
            vids.append({
                "id": v["id"],
                "title": v.get("title") or "",
                "duration": v.get("duration"),
                "url": f"https://youtu.be/{v['id']}",
            })
        print(f"      {len(vids)} videos")
        playlists.append({"playlist_id": pid, "title": title, "url": purl,
                          "video_count": len(vids), "videos": vids})

    out = META / "playlists.json"
    out.write_text(json.dumps(playlists, indent=2, ensure_ascii=False), encoding="utf-8")

    uniq = {v["id"] for p in playlists for v in p["videos"]}
    total = sum(p["video_count"] for p in playlists)
    print(f"\nwrote {out}")
    print(f"playlists={len(playlists)} video_slots={total} unique_videos={len(uniq)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
