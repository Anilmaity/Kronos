"""Wait for the public IP to change (VPN connect), then resume the transcript crawl.

Background: YouTube IP-banned this machine's home address (103.249.233.41) partway
through the crawl. Surfshark is installed but GUI-only, so the connect action is
manual. Rather than round-tripping, this watcher polls the public IP and starts
the fetch automatically the moment it changes AND YouTube actually answers.

It verifies reachability before spending the crawl: a new IP that is *also*
blocked (common for datacentre ranges) should not trigger a 350-video run.

Usage:
    python await_vpn_and_fetch.py --baseline 103.249.233.41 [--timeout-min 45]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TRANS = ROOT / "raw" / "transcripts"

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


def youtube_ok() -> tuple[bool, str]:
    """Probe one missing video. Returns (reachable, detail)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception as exc:
        return False, f"import failed: {exc}"

    have = {f.stem for f in TRANS.glob("*.txt")}
    pls = json.loads((ROOT / "meta" / "playlists.json").read_text(encoding="utf-8"))
    missing = [v for p in pls for v in p["videos"] if v["id"] not in have]
    if not missing:
        return True, "nothing missing"
    vid = missing[0]["id"]
    try:
        t = YouTubeTranscriptApi().fetch(vid)
        return True, f"probe {vid} ok ({len(t)} segments)"
    except Exception as exc:
        return False, f"probe {vid}: {type(exc).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="the blocked public IP")
    ap.add_argument("--timeout-min", type=float, default=45.0)
    ap.add_argument("--poll-sec", type=float, default=15.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    print(f"baseline (blocked) IP: {args.baseline}")
    print(f"waiting up to {args.timeout_min:.0f} min for the IP to change ...",
          flush=True)

    deadline = time.time() + args.timeout_min * 60
    last = None
    while time.time() < deadline:
        ip = public_ip()
        if ip and ip != last:
            print(f"  [{time.strftime('%H:%M:%S')}] public IP = {ip}", flush=True)
            last = ip
        if ip and ip != args.baseline:
            ok, detail = youtube_ok()
            print(f"  IP changed -> {ip}; youtube reachable = {ok} ({detail})",
                  flush=True)
            if ok:
                break
            print("  new IP is also blocked — switch VPN region and I'll keep "
                  "watching", flush=True)
        time.sleep(args.poll_sec)
    else:
        print("timed out waiting for a usable IP — nothing fetched.")
        return 1

    print("\nresuming transcript crawl ...\n", flush=True)
    proc = subprocess.run(
        [sys.executable, str(HERE / "fetch_transcripts.py"),
         "--workers", str(args.workers), "--delay", str(args.delay)],
        cwd=str(HERE),
    )
    have = len(list(TRANS.glob("*.txt")))
    print(f"\nfetch exited {proc.returncode}; transcripts on disk: {have}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
