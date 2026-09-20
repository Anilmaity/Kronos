"""Recover transcripts for videos that publish NO caption track, via local ASR.

Most of the corpus comes from YouTube's own captions. A handful of videos have
none at all -- verified with `yt-dlp --list-subs`, which reports "has no
automatic captions" *and* "has no subtitles", so this is a property of the
video, not of our access. For those, the only route to the content is
transcribing the audio ourselves.

This matters because two of them are real teaching material: the 74-minute
"Backtesting Simplified" and "TTrades Top-Down Chart Lessons #1". The rest of
the caption-less set is silent Shorts and deleted videos, which nothing can
recover.

IMPORTANT — these transcripts are NOT equivalent to the caption-derived ones.
ASR mishears domain jargon ("CISD", "candle 2", ticker names), so a quote
lifted from here is verbatim with respect to *our* file but not necessarily
with respect to what the speaker said. The header records
`transcript_source: whisper-<model>` precisely so a downstream reader can tell
the difference, and `validate_concepts.py` will still enforce that any quote
actually appears in the file.

Usage:
    python whisper_fetch.py                      # all caption-less, >60s
    python whisper_fetch.py --ids MvD7fQQ0szE    # specific videos
    python whisper_fetch.py --model small        # tiny|base|small|medium
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import fetch_transcripts as ft

# Below this, a "no captions" video is a silent clip rather than a lesson --
# transcribing it produces nothing and just burns time.
MIN_DURATION_SEC = 60


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def caption_less(status: dict) -> list[str]:
    """Video ids marked permanent specifically for having no caption track."""
    return [k for k, v in status.items()
            if v.get("permanent") and "no caption track" in str(v.get("error", ""))]


def download_audio(vid: str, dest_dir: Path) -> Path:
    out = dest_dir / f"{vid}.%(ext)s"
    cmd = [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node",
           "-f", "bestaudio/best", "-x", "--audio-format", "mp3",
           "--audio-quality", "5", "--no-warnings", "-o", str(out),
           f"https://youtu.be/{vid}"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    files = list(dest_dir.glob(f"{vid}.*"))
    if not files:
        raise RuntimeError(f"audio download failed: {(proc.stderr or '')[-300:]}")
    return files[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--model", default="small")
    ap.add_argument("--min-duration", type=int, default=MIN_DURATION_SEC)
    args = ap.parse_args()

    status = json.loads(ft.STATUS.read_text(encoding="utf-8")) if ft.STATUS.exists() else {}
    meta = {v["id"]: v for v in ft.load_videos()}

    ids = args.ids or caption_less(status)
    todo = []
    for vid in ids:
        if ft._txt_path(vid).exists():
            continue
        dur = (meta.get(vid) or {}).get("duration") or 0
        if not args.ids and dur < args.min_duration:
            log(f"skip {vid} ({dur}s) — too short to be a lesson")
            continue
        todo.append(vid)

    if not todo:
        log("nothing to transcribe")
        return 0

    log(f"transcribing {len(todo)} video(s) with faster-whisper '{args.model}'")
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    ok = 0
    for vid in todo:
        v = meta.get(vid, {"id": vid})
        title = v.get("title", "")
        try:
            with tempfile.TemporaryDirectory() as td:
                log(f"  {vid} — downloading audio ({v.get('duration')}s) …")
                audio = download_audio(vid, Path(td))
                log(f"  {vid} — transcribing …")
                segments, _info = model.transcribe(str(audio), language="en",
                                                   vad_filter=True)
                text = " ".join(s.text.strip() for s in segments).strip()
            if len(text.split()) < 20:
                raise RuntimeError(f"ASR produced almost nothing ({len(text.split())} words)")
            ft._write(vid, v, text, f"whisper-{args.model}")
            status[vid] = {"id": vid, "ok": True, "source": f"whisper-{args.model}",
                           "words": len(text.split()), "title": title}
            ok += 1
            log(f"  {vid} — OK, {len(text.split())} words")
        except Exception as exc:
            log(f"  {vid} — FAILED: {type(exc).__name__}: {str(exc)[:160]}")

    ft.STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    log(f"done. transcribed {ok}/{len(todo)}; on disk {len(list(ft.TRANS.glob('*.txt')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
