# kb — local semantic index over the Kronos knowledge sources

A local [Chroma](https://www.trychroma.com/) vector store so the research you
already paid for is reachable by question rather than by remembering which file
it landed in. Fully offline: embeddings come from Chroma's bundled ONNX
`all-MiniLM-L6-v2` (384-dim), cached under `~/.cache/chroma` after first run.
No API key, no per-query cost.

Nothing here is in a git repo — the workspace root is a plain folder — so the
`chroma/` store and `.venv/` stay local by construction.

## Use

```bash
kb/.venv/Scripts/python.exe kb/ask.py "was the C2 wick asymmetry confirmed?"
kb/.venv/Scripts/python.exe kb/ask.py -n 12 "why was the stop floor rejected"
kb/.venv/Scripts/python.exe kb/ask.py -s lab -s vault "S93 hours narrowing"
kb/.venv/Scripts/python.exe kb/ask.py --sources        # what is indexed
kb/.venv/Scripts/python.exe kb/ask.py --full "..."     # untruncated passages
```

Re-index after writing notes (incremental — unchanged files cost nothing,
they are fingerprinted on mtime+size):

```bash
kb/.venv/Scripts/python.exe kb/index_kb.py
kb/.venv/Scripts/python.exe kb/index_kb.py --rebuild   # start clean
```

## What is indexed

| label | source |
|---|---|
| `vault` | `E:\Projects\KronosVault` — the Obsidian vault |
| `ttrades-concept` | `ClaudeTradingRD/research/concepts` — the 505-concept corpus |
| `research` | `ClaudeTradingRD/research/notes` — per-unit study notes |
| `research-meta` | `ClaudeTradingRD/research/meta` — method specs, adjudications |
| `lab` | `KronosStrategies/strategies/lab` — campaign reports |
| `docs` | `KronosStrategies/docs` — plans and runbooks |
| `shared` | `shared/` — audit and optimization reports |

Deliberately **not** indexed: `research/raw` (436 transcript dumps — the
distilled notes already cover them and raw dumps would swamp retrieval), and
source code (grep is better at code than embeddings are).

## What it is for, and what it is not

It is a *recall* tool. `ask.py` returns passages and their file paths; it does
not summarise or adjudicate. That is deliberate — the highest-value hits in this
corpus are the refutations (the C2 wick artefact, the rejected stop floor, the
failed ARM_SL_FLOOR A/B), and a summary layer is exactly where a refuted claim
gets quietly restated as a finding. Read the passage, then open the file.

Retrieval scores are cosine similarity in `[0,1]`. In practice above ~0.6 is a
real hit; 0.45–0.6 is related context; below that is usually noise. MiniLM
truncates at 256 tokens, so chunks are kept to ~1400 characters.

## Not a time-series store

This index holds prose. The S5/M1 bar history lives in
`ClaudeTradingRD/ClaudeTradingBot/reports/s5/*.npz` and should stay there — a
vector store has no time ordering and no range scans, so it is the wrong shape
for bars. Load those with `bot/oanda_s5.py:load("2025-09", "2026-09")`.
