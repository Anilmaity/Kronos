"""Query the local Kronos knowledge index.

    python ask.py "was the C2 wick asymmetry ever confirmed?"
    python ask.py -n 12 "what did we decide about raising the stop floor"
    python ask.py -s lab -s vault "S93 hours narrowing evidence"
    python ask.py --sources          # list what is indexed

Retrieval only — it returns the passages and where they came from. It does
not summarise or judge, because the point is to surface the primary record
(including the parts that refuted something) rather than a paraphrase of it.
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import chromadb

# Windows consoles default to cp1252, which mangles the em-dashes and callout
# glyphs that are all over the vault notes. Force UTF-8 on the way out.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_DIR = Path(__file__).resolve().parent / "chroma"
COLLECTION = "kronos"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*", help="natural-language question")
    ap.add_argument("-n", type=int, default=8, help="how many passages")
    ap.add_argument("-s", "--source", action="append", default=[],
                    help="restrict to a source label (repeatable)")
    ap.add_argument("--full", action="store_true", help="print whole passages")
    ap.add_argument("--sources", action="store_true", help="list indexed sources")
    args = ap.parse_args()

    client = chromadb.PersistentClient(path=str(DB_DIR))
    col = client.get_or_create_collection(COLLECTION)

    if args.sources:
        got = col.get(include=["metadatas"])
        counts: dict[str, int] = {}
        files: dict[str, set] = {}
        for md in got["metadatas"]:
            counts[md["source"]] = counts.get(md["source"], 0) + 1
            files.setdefault(md["source"], set()).add(md["path"])
        print(f"{col.count():,} chunks in '{COLLECTION}'\n")
        for s in sorted(counts, key=lambda k: -counts[k]):
            print(f"  {s:18} {counts[s]:>6,} chunks  {len(files[s]):>4} files")
        return 0

    if not args.query:
        ap.error("give a question, or --sources")

    where = None
    if args.source:
        where = ({"source": args.source[0]} if len(args.source) == 1
                 else {"$or": [{"source": s} for s in args.source]})

    res = col.query(query_texts=[" ".join(args.query)], n_results=args.n,
                    where=where, include=["documents", "metadatas", "distances"])
    docs, metas, dists = (res["documents"][0], res["metadatas"][0],
                          res["distances"][0])
    if not docs:
        print("nothing indexed matches that.")
        return 1

    for rank, (doc, md, dist) in enumerate(zip(docs, metas, dists), 1):
        sim = 1.0 - dist
        head = f" > {md['heading']}" if md.get("heading") else ""
        print(f"\n{'=' * 78}\n[{rank}] {sim:.3f}  {md['source']}: "
              f"{md['title']}{head}\n     {md['path']}\n")
        body = doc.split("\n\n", 1)[-1].strip()
        if not args.full:
            body = body[:700] + ("…" if len(body) > 700 else "")
        print(textwrap.indent(body, "     "))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
