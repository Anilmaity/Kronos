"""Fetch transcripts for every unique video in meta/playlists.json.

Design notes
------------
* Resume-safe: a video whose .txt already exists is skipped, so the script can
  be re-run after a rate-limit without redoing work. Status lives in
  meta/transcripts_status.json and is rewritten after every completion.
* youtube-transcript-api >= 1.x instance API (`YouTubeTranscriptApi().fetch`).
  Prefers a manually-created English track, then any English, then any track at
  all, then a translation into English.
* Falls back to `yt-dlp --write-auto-subs` (vtt -> text) when the API fails,
  which covers videos the API refuses but yt-dlp can still reach.
* Modest concurrency + backoff: YouTube throttles aggressively and an IP block
  would cost far more time than the parallelism saves.

Usage:  python fetch_transcripts.py [--workers 4] [--limit N] [--retry-failed]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta"
TRANS = ROOT / "raw" / "transcripts"
TRANS.mkdir(parents=True, exist_ok=True)
STATUS = META / "transcripts_status.json"

_lock = threading.Lock()
_status: dict = {}

# ---- throttling -------------------------------------------------------------
# YouTube rate-limits hard: a 4-worker unthrottled run got ~93 videos before
# every subsequent request came back as a bot/cookie challenge. These two
# mechanisms keep the crawl under the limit instead of racing into a block.
_gate = threading.Lock()
_last_call = [0.0]
_blocks = [0]            # consecutive bot/cookie-looking failures
DELAY = [1.5]            # min seconds between any two outbound requests
COOKIES_FROM = [""]      # e.g. "chrome" -> yt-dlp --cookies-from-browser chrome

BLOCK_PAT = re.compile(r"cookie|not a bot|sign in|blocked|429|too many", re.I)


def _pace() -> None:
    """Space outbound requests globally, with jitter so calls don't align."""
    with _gate:
        wait = DELAY[0] - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


class Blocked(Exception):
    """Raised to abort the whole run once the IP is clearly banned."""


class NoCaptions(Exception):
    """The video genuinely has no caption track — a permanent miss, not a block.

    Distinguishing this matters twice over: retrying it 3x wastes 3 requests
    against a rate limit that is the real constraint, and a run of caption-less
    videos would otherwise look like the start of an IP ban.
    """


class Throttled(Exception):
    """The caption (timedtext) endpoint returned 429 for this IP.

    Measured behaviour: the video page and the player API keep answering
    normally while ONLY the caption download 429s, and it starts doing so after
    roughly 10-12 successful caption fetches from a given IP. That is a per-IP
    quota, not a request-rate limit, so pacing does not avoid it -- only waiting
    it out or changing egress does. Kept separate from a generic failure so the
    crawler can cool down instead of burning through the queue.
    """


# yt-dlp's own wording when a video has no usable subtitle track at all.
NO_CAPS_PAT = re.compile(
    r"no subtitles for the requested languages|has no automatic captions", re.I)
THROTTLE_PAT = re.compile(r"HTTP Error 429|Too Many Requests", re.I)


ABORT_AFTER = [12]       # consecutive blocks before giving up entirely
_aborted = [False]


def _note_result(err: str | None) -> None:
    """Circuit breaker: back off, then abort once the IP is clearly banned.

    Continuing to hammer a banned IP does not just waste time, it extends the
    ban. Aborting early preserves the remaining work for a later run — the
    fetcher is resume-safe, so nothing is lost by stopping.
    """
    with _gate:
        if err and BLOCK_PAT.search(err):
            _blocks[0] += 1
        elif not err:
            _blocks[0] = 0
        n = _blocks[0]
        if n >= ABORT_AFTER[0]:
            _aborted[0] = True
    if _aborted[0]:
        return
    if n and n % 5 == 0:
        cool = min(30 * (n // 5), 300)
        print(f"    ! {n} consecutive blocks — cooling down {cool}s", flush=True)
        time.sleep(cool)


def load_videos() -> list[dict]:
    """Unique videos across all playlists, each tagged with its playlists."""
    pls = json.loads((META / "playlists.json").read_text(encoding="utf-8"))
    vids: dict[str, dict] = {}
    for p in pls:
        for v in p["videos"]:
            rec = vids.setdefault(v["id"], {**v, "playlists": []})
            rec["playlists"].append(p["title"])
    return list(vids.values())


def _txt_path(vid: str) -> Path:
    return TRANS / f"{vid}.txt"


def _write(vid: str, meta: dict, text: str, source: str) -> None:
    header = (
        f"# {meta.get('title','')}\n"
        f"video_id: {vid}\n"
        f"url: https://youtu.be/{vid}\n"
        f"duration_sec: {meta.get('duration')}\n"
        f"playlists: {'; '.join(meta.get('playlists', []))}\n"
        f"transcript_source: {source}\n"
        f"{'-' * 70}\n\n"
    )
    _txt_path(vid).write_text(header + text, encoding="utf-8")


def via_api(vid: str) -> tuple[str, str]:
    """(text, source) using youtube-transcript-api, or raise."""
    from youtube_transcript_api import YouTubeTranscriptApi

    _pace()
    api = YouTubeTranscriptApi()
    listing = api.list(vid)

    def pick():
        for finder, tag in (
            (lambda: listing.find_manually_created_transcript(["en", "en-US", "en-GB"]), "manual-en"),
            (lambda: listing.find_generated_transcript(["en", "en-US", "en-GB"]), "auto-en"),
        ):
            try:
                return finder(), tag
            except Exception:
                continue
        for t in listing:  # any language at all
            try:
                return (t.translate("en"), f"translated-from-{t.language_code}")
            except Exception:
                return t, f"orig-{t.language_code}"
        raise RuntimeError("no transcript tracks")

    tr, tag = pick()
    data = tr.fetch()
    parts = [(s.text if hasattr(s, "text") else s["text"]) for s in data]
    text = " ".join(p.strip() for p in parts if p and p.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text.split()) < 5:
        raise RuntimeError("transcript too short")
    return text, tag


_VTT_TS = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->")
_VTT_TAG = re.compile(r"<[^>]+>")


def via_ytdlp(vid: str) -> tuple[str, str]:
    """(text, source) by downloading auto-subs with yt-dlp and stripping VTT."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "s"
        # --sleep-requests paces yt-dlp's own calls; browser impersonation is used
        # automatically when a compatible curl_cffi is installed (yt-dlp supports
        # 0.5.10 and 0.10.x-0.15.x -- 0.16+ is silently ignored, which cost an hour
        # of debugging, so pin inside that range if you reinstall it).
        # --js-runtimes node: yt-dlp deprecated JS-less YouTube extraction; without a
        # runtime the webpage fetch falls back to a path that reliably returns
        # "Sign in to confirm you're not a bot" / 429. Node is on PATH here (nvm4w);
        # deno is yt-dlp's only default-enabled runtime and is NOT installed.
        cmd = [sys.executable, "-m", "yt_dlp", "--skip-download",
               "--js-runtimes", "node",
               "--write-auto-subs", "--write-subs", "--sub-langs", "en.*",
               "--sub-format", "vtt", "--no-warnings",
               "--sleep-requests", "1", "--retries", "3", "--retry-sleep", "5",
               "-o", str(out)]
        if COOKIES_FROM[0]:
            cmd += ["--cookies-from-browser", COOKIES_FROM[0]]
        cmd.append(f"https://youtu.be/{vid}")
        _pace()
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        files = list(Path(td).glob("*.vtt"))
        if not files:
            blob = (proc.stdout or "") + (proc.stderr or "")
            if NO_CAPS_PAT.search(blob):
                raise NoCaptions("no caption track published for this video")
            if THROTTLE_PAT.search(blob):
                raise Throttled("caption endpoint 429 for this IP")
            raise RuntimeError(f"yt-dlp produced no vtt ({(proc.stderr or '')[-200:]})")
        seen, words = set(), []
        for line in files[0].read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if (not line or line == "WEBVTT" or _VTT_TS.match(line)
                    or line.startswith(("Kind:", "Language:", "NOTE"))):
                continue
            line = _VTT_TAG.sub("", line).strip()
            if line and line not in seen:      # auto-subs repeat rolling lines
                seen.add(line)
                words.append(line)
        text = re.sub(r"\s+", " ", " ".join(words)).strip()
        if len(text.split()) < 5:
            raise RuntimeError("vtt yielded no text")
        return text, "yt-dlp-auto"


def fetch_one(v: dict, attempts: int = 3) -> dict:
    vid = v["id"]
    if _txt_path(vid).exists():
        return {"id": vid, "ok": True, "source": "cached", "words": None}
    if _aborted[0]:
        return {"id": vid, "ok": False, "error": "skipped: run aborted (IP blocked)",
                "title": v.get("title", ""), "skipped": True}
    last = ""
    for i in range(attempts):
        # yt-dlp FIRST: youtube-transcript-api is IpBlocked from this network and
        # every call to it is a wasted request against the rate limit that is the
        # actual bottleneck. It stays as a fallback because it still succeeds on
        # some videos yt-dlp refuses.
        for fn in (via_ytdlp, via_api):
            try:
                text, src = fn(vid)
                _write(vid, v, text, src)
                _note_result(None)
                return {"id": vid, "ok": True, "source": src, "words": len(text.split())}
            except NoCaptions as exc:
                _note_result(None)   # not a block; do not poison the circuit breaker
                return {"id": vid, "ok": False, "permanent": True,
                        "error": f"no captions: {exc}", "title": v.get("title", "")}
            except Exception as exc:
                last = f"{fn.__name__}: {type(exc).__name__}: {exc}"[:300]
        _note_result(last)
        time.sleep(2 * (i + 1))  # backoff before the next full round
    return {"id": vid, "ok": False, "error": last, "title": v.get("title", "")}


def save_status() -> None:
    with _lock:
        STATUS.write_text(json.dumps(_status, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry-failed", action="store_true",
                    help="only re-attempt videos previously recorded as failed")
    ap.add_argument("--delay", type=float, default=1.5,
                    help="min seconds between outbound requests (global)")
    ap.add_argument("--cookies-from-browser", default="",
                    help="pass a browser name (e.g. chrome) to yt-dlp to clear bot checks")
    args = ap.parse_args()
    DELAY[0] = args.delay
    COOKIES_FROM[0] = args.cookies_from_browser

    vids = load_videos()
    if STATUS.exists():
        _status.update(json.loads(STATUS.read_text(encoding="utf-8")))
    if args.retry_failed:
        # `permanent` = the video has no caption track at all; re-attempting it
        # only spends rate limit that the recoverable failures need.
        bad = {k for k, r in _status.items()
               if not r.get("ok") and not r.get("permanent")}
        vids = [v for v in vids if v["id"] in bad]
    pending = [v for v in vids if not _txt_path(v["id"]).exists()]
    cached = len(vids) - len(pending)          # count BEFORE --limit is applied
    todo = pending[:args.limit] if args.limit else pending

    print(f"unique videos: {len(vids)} | already cached: {cached} | "
          f"to fetch: {len(todo)} | workers: {args.workers}", flush=True)

    done = ok = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, v): v for v in todo}
        for fut in as_completed(futs):
            r = fut.result()
            done += 1
            ok += 1 if r["ok"] else 0
            with _lock:
                _status[r["id"]] = r
            if done % 10 == 0 or not r["ok"]:
                save_status()
                flag = "" if r["ok"] else f"  FAIL {r.get('error','')[:110]}"
                print(f"  [{done}/{len(todo)}] ok={ok}{flag}", flush=True)
    save_status()

    have = len(list(TRANS.glob("*.txt")))
    print(f"\ndone. transcripts on disk: {have}/{len(vids)}")
    if _aborted[0]:
        print(f"ABORTED after {ABORT_AFTER[0]} consecutive blocks — YouTube has "
              f"banned this IP. Nothing was lost: re-run later (the fetcher skips "
              f"anything already on disk). Probe first with:\n"
              f"  python fetch_transcripts.py --limit 1 --workers 1")
        return 2
    fails = [k for k, r in _status.items() if not r.get("ok")]
    if fails:
        print(f"failed: {len(fails)} -> re-run with --retry-failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
