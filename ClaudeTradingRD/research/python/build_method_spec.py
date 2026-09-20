r"""Load the concept library and emit digests for the method-spec synthesis pass.

Usage (run from research/):
    ..\.venv\Scripts\python.exe python\build_method_spec.py stats
    ..\.venv\Scripts\python.exe python\build_method_spec.py list --voice ttrades,mixed
    ..\.venv\Scripts\python.exe python\build_method_spec.py dump <id> [<id> ...]
    ..\.venv\Scripts\python.exe python\build_method_spec.py grep <regex>
    ..\.venv\Scripts\python.exe python\build_method_spec.py guests

This is a read-only analysis helper. It never writes into concepts/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONCEPTS = ROOT / "concepts"
CATEGORIES = ["entry", "liquidity", "model", "psychology", "risk", "structure", "time"]


def load_all() -> list[dict]:
    out = []
    for cat in CATEGORIES:
        for f in sorted((CONCEPTS / cat).glob("*.yaml")):
            try:
                d = yaml.safe_load(f.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                print(f"!! parse fail {f}: {e}", file=sys.stderr)
                continue
            if not isinstance(d, dict):
                continue
            d["_file"] = str(f.relative_to(ROOT)).replace("\\", "/")
            d.setdefault("category", cat)
            out.append(d)
    return out


def voice_of(c: dict) -> str:
    return (c.get("voice") or "unknown").strip()


def flat(x) -> list[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, list):
        r = []
        for i in x:
            r.extend(flat(i))
        return r
    if isinstance(x, dict):
        r = []
        for k, v in x.items():
            for s in flat(v):
                r.append(f"{k}: {s}")
        return r
    return [str(x)]


def cmd_stats(cs: list[dict]) -> None:
    from collections import Counter

    print("total", len(cs))
    print("voice", Counter(voice_of(c) for c in cs).most_common())
    print("status", Counter(c.get("status") for c in cs).most_common())
    print("category", Counter(c.get("category") for c in cs).most_common())
    own = [c for c in cs if voice_of(c) in ("ttrades", "mixed")]
    print("own-voice", len(own))
    print("own by cat", Counter(c["category"] for c in own).most_common())
    print("own by status", Counter(c.get("status") for c in own).most_common())


def cmd_list(cs: list[dict], voices: set[str], cats: set[str] | None) -> None:
    for c in cs:
        if voice_of(c) not in voices:
            continue
        if cats and c.get("category") not in cats:
            continue
        n_src = len(c.get("sources") or [])
        print(
            f"{c['category']:<10} {c.get('status','?'):<14} {voice_of(c):<7} "
            f"{c['id']:<48} src={n_src:<3} {c.get('name','')}"
        )


def cmd_dump(cs: list[dict], ids: list[str], full: bool) -> None:
    by_id = {c["id"]: c for c in cs}
    for cid in ids:
        c = by_id.get(cid)
        if not c:
            print(f"### {cid}  -- NOT FOUND")
            continue
        print("=" * 100)
        print(f"### {c['id']}  [{c.get('category')}/{c.get('status')}/{voice_of(c)}]  {c.get('name','')}")
        if c.get("aliases"):
            print("aliases:", ", ".join(flat(c["aliases"])))
        print("-- definition --")
        print((c.get("definition") or "").strip())
        for key in ("variants",):
            if c.get(key) and full:
                print(f"-- {key} --")
                print(yaml.safe_dump(c[key], sort_keys=False, allow_unicode=True)[:6000])
        for key in ("timeframes", "preconditions", "detection_rules", "invalidation",
                    "execution", "measurable", "ambiguities", "related"):
            v = c.get(key)
            if not v:
                continue
            print(f"-- {key} --")
            for s in flat(v):
                print("  *", s)
        srcs = c.get("sources") or []
        print(f"-- sources ({len(srcs)}) --")
        for s in srcs[: (999 if full else 6)]:
            if isinstance(s, dict):
                print(f"  * {s.get('video_id')} | {str(s.get('title'))[:60]} | {str(s.get('quote'))[:90]}")
        print()


def cmd_grep(cs: list[dict], pattern: str, voices: set[str]) -> None:
    rx = re.compile(pattern, re.I)
    for c in cs:
        if voice_of(c) not in voices:
            continue
        blob = json.dumps({k: v for k, v in c.items() if k != "sources"}, default=str)
        if rx.search(blob):
            hits = rx.findall(blob)
            print(f"{c['id']:<50} {c.get('status'):<14} {voice_of(c):<7} {c['category']:<10} n={len(hits)}")


def cmd_guests(cs: list[dict]) -> None:
    """Group guest concepts by the speakers/videos they came from."""
    from collections import defaultdict

    by_vid = defaultdict(set)
    vid_titles: dict[str, str] = {}
    for c in cs:
        if voice_of(c) != "guest":
            continue
        for s in c.get("sources") or []:
            if not isinstance(s, dict):
                continue
            vid = s.get("video_id")
            if not vid:
                continue
            by_vid[vid].add(c["id"])
            vid_titles.setdefault(vid, str(s.get("title") or ""))
    rows = sorted(by_vid.items(), key=lambda kv: -len(kv[1]))
    for vid, ids in rows:
        print(f"{vid}  n={len(ids):<3} {vid_titles.get(vid,'')}")
        print("    " + ", ".join(sorted(ids)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stats", "list", "dump", "grep", "guests"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--voice", default="ttrades,mixed")
    ap.add_argument("--cat", default="")
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()

    cs = load_all()
    voices = set(v.strip() for v in a.voice.split(",") if v.strip())
    cats = set(v.strip() for v in a.cat.split(",") if v.strip()) or None

    if a.cmd == "stats":
        cmd_stats(cs)
    elif a.cmd == "list":
        cmd_list(cs, voices, cats)
    elif a.cmd == "dump":
        cmd_dump(cs, a.args, a.full)
    elif a.cmd == "grep":
        cmd_grep(cs, a.args[0], voices)
    elif a.cmd == "guests":
        cmd_guests(cs)


if __name__ == "__main__":
    main()
