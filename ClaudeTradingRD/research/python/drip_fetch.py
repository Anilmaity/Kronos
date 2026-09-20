"""Quota-aware, unattended transcript crawler.

Why this exists (measured, not assumed)
---------------------------------------
`fetch_transcripts.py` assumes failures mean "IP banned, stop". The real
behaviour of the caption endpoint is narrower and more workable:

  * the video page and the player API keep answering normally, forever;
  * ONLY the `timedtext` caption download 429s;
  * it starts doing so after roughly 10-12 successful caption fetches per IP.

That is a per-IP *quota*, not a request *rate* limit. Pacing does not avoid it
-- an 8-video run at one request every 4s got zero. So the only two ways
forward are to wait the quota out or to change egress, and this script does
both without supervision:

  * fetch sequentially until the quota trips (parallelism cannot help against a
    quota; it only burns it faster and blurs the signal);
  * cool down, with the wait growing on repeated trips and shrinking again once
    fetches land, so it converges on the real reset period instead of guessing;
  * watch the public IP throughout -- if it changes (someone rotated the VPN),
    break the cooldown immediately and reset the backoff.

Resume-safe: transcripts already on disk are skipped, so this can be killed and
restarted at any point. Progress is written to meta/transcripts_status.json.

Usage:
    python drip_fetch.py                      # run until the corpus is complete
    python drip_fetch.py --max-hours 4        # or until a wall-clock budget ends
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

import fetch_transcripts as ft

IP_SERVICES = ["https://api.ipify.org", "https://ifconfig.me/ip",
               "https://icanhazip.com"]


def public_ip(timeout: int = 10) -> str | None:
    for url in IP_SERVICES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ip = r.read().decode().strip()
                if ip:
                    return ip
        except Exception:
            continue
    return None


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pending(status: dict) -> list[dict]:
    """Videos still worth attempting, in corpus order.

    Excludes anything already on disk and anything proven to have no caption
    track at all -- retrying those spends quota that recoverable videos need.
    """
    out = []
    for v in ft.load_videos():
        if ft._txt_path(v["id"]).exists():
            continue
        if status.get(v["id"], {}).get("permanent"):
            continue
        out.append(v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hours", type=float, default=0.0,
                    help="stop after this many hours (0 = until complete)")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="seconds between successful fetches")
    ap.add_argument("--cool-start", type=float, default=600.0,
                    help="first cooldown after the quota trips, seconds")
    ap.add_argument("--cool-max", type=float, default=3600.0)
    ap.add_argument("--trip-after", type=int, default=3,
                    help="consecutive 429s that count as the quota being spent")
    args = ap.parse_args()

    status: dict = {}
    if ft.STATUS.exists():
        status.update(json.loads(ft.STATUS.read_text(encoding="utf-8")))

    todo = pending(status)
    total = len(ft.load_videos())
    log(f"corpus {total} videos | on disk {total - len(todo)} | to fetch {len(todo)}")

    ip = public_ip()
    log(f"egress IP {ip}")

    deadline = time.time() + args.max_hours * 3600 if args.max_hours else None
    cool = args.cool_start
    throttles = 0
    got = missed = 0

    i = 0
    while i < len(todo):
        if deadline and time.time() > deadline:
            log("wall-clock budget reached — stopping cleanly")
            break

        v = todo[i]
        vid = v["id"]
        try:
            text, src = ft.via_ytdlp(vid)
            ft._write(vid, v, text, src)
            status[vid] = {"id": vid, "ok": True, "source": src,
                           "words": len(text.split())}
            got += 1
            throttles = 0
            # The quota reset faster than we feared; walk the cooldown back down
            # so the next trip does not over-wait.
            cool = max(args.cool_start, cool * 0.7)
            log(f"ok   {vid}  ({len(text.split())} words)  "
                f"[{got} this run, {i + 1}/{len(todo)}]")
            i += 1
            time.sleep(args.delay)

        except ft.NoCaptions:
            status[vid] = {"id": vid, "ok": False, "permanent": True,
                           "error": "no captions", "title": v.get("title", "")}
            missed += 1
            log(f"skip {vid}  no caption track (permanent)")
            i += 1

        except ft.Throttled:
            throttles += 1
            log(f"429  {vid}  caption quota hit ({throttles}/{args.trip_after})")
            if throttles < args.trip_after:
                time.sleep(15)
                continue          # same video, maybe a transient refusal
            # Quota is genuinely spent. Wait it out, but keep watching for a
            # rotation: a changed IP is a fresh quota and should not be wasted
            # sitting in a sleep.
            waited, before = 0.0, ip
            log(f"cooling down {cool / 60:.0f} min (or until the IP changes)")
            while waited < cool:
                time.sleep(30)
                waited += 30
                now = public_ip()
                if now and now != before:
                    log(f"egress changed {before} -> {now} — resuming now")
                    ip = now
                    cool = args.cool_start
                    break
            else:
                cool = min(cool * 1.5, args.cool_max)
            throttles = 0
            ft.STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
            continue              # retry the same video

        except Exception as exc:
            status[vid] = {"id": vid, "ok": False,
                           "error": f"{type(exc).__name__}: {exc}"[:300],
                           "title": v.get("title", "")}
            missed += 1
            log(f"fail {vid}  {type(exc).__name__}: {str(exc)[:90]}")
            i += 1

        if (got + missed) % 5 == 0:
            ft.STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                                 encoding="utf-8")

    ft.STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    have = len(list(ft.TRANS.glob("*.txt")))
    log(f"done. fetched {got}, permanent/failed {missed}, on disk {have}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
