"""Build a local Chroma index over the Kronos knowledge sources.

Everything runs offline: embeddings come from Chroma's bundled ONNX
all-MiniLM-L6-v2 (384-dim), cached under ~/.cache/chroma after first use.
No API key, no network once the model is cached.

    python index_kb.py            # incremental: only re-embeds changed files
    python index_kb.py --rebuild  # drop the collection and start clean

Chunking is heading-aware: markdown is split at ATX headings first so a
chunk keeps its section context, then any over-long section is hard-split.
Each chunk carries its file mtime+size hash so unchanged files are skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent          # E:/Projects/Kronos
VAULT = ROOT.parent / "KronosVault"
DB_DIR = Path(__file__).resolve().parent / "chroma"
COLLECTION = "kronos"

MAX_CHARS = 1400          # ~350 tokens; MiniLM truncates at 256 so keep it tight
MIN_CHARS = 40            # skip near-empty fragments

# (label, root, glob) — order matters only for readability
SOURCES: list[tuple[str, Path, str]] = [
    ("vault",           VAULT,                                          "**/*.md"),
    ("ttrades-concept", ROOT / "ClaudeTradingRD/research/concepts",      "**/*"),
    ("research",        ROOT / "ClaudeTradingRD/research/notes",         "**/*.md"),
    ("research-meta",   ROOT / "ClaudeTradingRD/research/meta",          "**/*.md"),
    ("lab",             ROOT / "KronosStrategies/strategies/lab",        "*.md"),
    ("docs",            ROOT / "KronosStrategies/docs",                  "**/*.md"),
    ("shared",          ROOT / "shared",                                 "*.md"),
]

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".obsidian",
             ".pytest_cache", "raw"}


def file_fingerprint(p: Path) -> str:
    st = p.stat()
    return hashlib.sha1(f"{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()[:16]


def split_markdown(text: str) -> list[tuple[str, str]]:
    """-> [(heading_path, chunk_text)]. Splits on ATX headings, then length."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    stack: list[str] = []
    buf: list[str] = []
    heading = ""

    def flush():
        if buf:
            sections.append((heading, buf[:]))
            buf.clear()

    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            flush()
            depth = len(m.group(1))
            stack[:] = stack[: depth - 1]
            stack.append(m.group(2).strip())
            heading = " > ".join(stack)
        else:
            buf.append(ln)
    flush()

    out: list[tuple[str, str]] = []
    for head, body in sections:
        blob = "\n".join(body).strip()
        if len(blob) < MIN_CHARS:
            continue
        if len(blob) <= MAX_CHARS:
            out.append((head, blob))
            continue
        # hard-split long sections on paragraph boundaries
        cur = ""
        for para in re.split(r"\n\s*\n", blob):
            if len(cur) + len(para) + 2 > MAX_CHARS and cur:
                out.append((head, cur.strip()))
                cur = ""
            cur += para + "\n\n"
        if cur.strip():
            out.append((head, cur.strip()))
    return out


def iter_files():
    seen: set[Path] = set()
    for label, root, pattern in SOURCES:
        if not root.exists():
            print(f"  ! missing, skipped: {root}", file=sys.stderr)
            continue
        for p in sorted(root.glob(pattern)):
            if not p.is_file() or p.suffix.lower() not in {".md", ".yaml", ".yml", ".txt"}:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p in seen:
                continue
            seen.add(p)
            yield label, root, p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    if args.rebuild:
        try:
            client.delete_collection(COLLECTION)
            print("dropped existing collection")
        except Exception:
            pass
    col = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"})

    # fingerprints already in the store, so unchanged files cost nothing
    known: dict[str, str] = {}
    got = col.get(include=["metadatas"])
    for cid, md in zip(got["ids"], got["metadatas"]):
        known[md["path"]] = md.get("fp", "")

    added = skipped = replaced = 0
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []

    for label, root, path in iter_files():
        rel = str(path.relative_to(root.parent if root.name else root))
        key = str(path)
        fp = file_fingerprint(path)
        if known.get(key) == fp:
            skipped += 1
            continue
        if key in known:
            col.delete(where={"path": key})
            replaced += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        chunks = split_markdown(text)
        if not chunks:
            continue
        for i, (head, body) in enumerate(chunks):
            ids.append(hashlib.sha1(f"{key}:{i}".encode()).hexdigest())
            docs.append(f"[{label}] {path.stem} :: {head}\n\n{body}" if head
                        else f"[{label}] {path.stem}\n\n{body}")
            metas.append({"source": label, "path": key, "file": path.name,
                          "title": path.stem, "heading": head, "fp": fp,
                          "rel": rel})
            added += 1

    for lo in range(0, len(ids), 256):
        col.upsert(ids=ids[lo:lo + 256], documents=docs[lo:lo + 256],
                   metadatas=metas[lo:lo + 256])
        print(f"  embedded {min(lo + 256, len(ids)):,}/{len(ids):,}", flush=True)

    print(f"\nchunks added {added:,} | files unchanged {skipped} | "
          f"files replaced {replaced}")
    print(f"collection '{COLLECTION}' now holds {col.count():,} chunks")
    print(f"store: {DB_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
