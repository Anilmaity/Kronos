# TTrades_edu research corpus

A structured study of the **TTrades_edu** YouTube channel (ICT / SMC methodology),
built so that later analysis and strategy work can consume it mechanically
rather than by re-reading prose.

Source channel: <https://www.youtube.com/@TTrades_edu>
Built: 2026-08-09

## Corpus at a glance

| | |
|---|---|
| playlists | 16 |
| unique videos | 443 |
| total runtime | ~101h |
| runtime excluding Shorts | ~98h across 214 videos |
| videos cross-listed in >1 playlist | 110 |

Full breakdown: [`meta/corpus_report.md`](meta/corpus_report.md).

## Layout

```
research/
├── meta/                     # machine-readable corpus state
│   ├── playlists.json        # every playlist -> every video (id,title,duration)
│   ├── corpus_report.md      # counts, runtimes, overlap
│   ├── study_units.json      # 32 work units; each video assigned EXACTLY once
│   └── transcripts_status.json
├── raw/transcripts/          # <video_id>.txt, header + flattened caption text
├── notes/                    # <unit_id>.md — deep per-video study notes
├── concepts/
│   ├── _SCHEMA.md            # THE contract for a concept entry — read first
│   ├── _inbox/               # per-unit concept drafts (avoids parallel write races)
│   └── <category>/           # merged, deduplicated concept library
└── python/                   # the pipeline + concept detectors
```

## Pipeline

Each script is re-runnable and resume-safe.

```bash
python python/enumerate_channel.py      # channel -> meta/playlists.json
python python/corpus_report.py          # -> meta/corpus_report.md
python python/assign_study_units.py     # -> meta/study_units.json
python python/fetch_transcripts.py      # -> raw/transcripts/*.txt
python python/fetch_transcripts.py --retry-failed --workers 1 --delay 5
```

### Two gotchas worth remembering

**yt-dlp pagination.** The first enumeration silently returned exactly 100 videos
for the three largest playlists, which really hold 108 / 141 / 229. It was a stale
yt-dlp (2026.03.17); upgrading fixed it. Any playlist reporting a round 100 should
be treated as truncated until proven otherwise.

**YouTube IP blocking.** Transcript fetching at 4 workers got ~93 videos before
YouTube began returning bot/cookie challenges, then a hard `IpBlocked`. The fetcher
now paces requests globally and backs off on consecutive blocks. On Windows,
`--cookies-from-browser chrome` does **not** work around it (Chrome App-Bound
Encryption; yt-dlp issue #10927), and there is no Firefox profile here. The
practical remedy is to wait out the block and resume with `--workers 1 --delay 5`.

## Concept library

`concepts/_SCHEMA.md` is the contract. The governing rule is that **a concept is
only useful if it is decidable** — given a chart and a bar index you must be able
to say whether it is present. Anything vaguer is recorded with
`status: underspecified` and an explicit list of what is missing, rather than
being smoothed over with generic ICT knowledge.

Concepts are drafted per study unit into `concepts/_inbox/`, then merged into
`concepts/<category>/`. Start at [`concepts/INDEX.md`](concepts/INDEX.md);
`concepts/index.json` is the machine-readable manifest.

**Current state — 270 concepts from 52 videos** (10 of 32 study units done):

| | |
|---|---|
| specified (decidable as taught) | 179 |
| underspecified (gap recorded) | 56 |
| contested (two readings kept) | 35 |
| TTrades' own voice | 155 |
| guest speakers | 110 |
| mixed / corroborated | 5 |

### `voice` is the field to read first

**T Talks** and **Live Stream Guests** are *interviews*. Each episode is a
different trader with his own, frequently contradictory, methodology. A concept
tagged `voice: guest` is evidence of what that guest teaches — **not** what this
channel teaches. Filter to `voice in (ttrades, mixed)` for the channel's own
method and treat the guest entries as a comparative library. Without this
distinction `contested` would conflate "the channel is inconsistent" with "two
different people disagree", which are entirely different claims.

### Provenance is enforced, not trusted

`python validate_concepts.py` checks every citation mechanically: the video must
exist in the corpus, have a transcript on disk, and belong to the unit that cited
it; every quote must be <= 15 words and actually occur in that transcript. It has
already caught a stitched, misspelled quote that an agent reconstructed instead of
copying. Run it before trusting any downstream use, and use `--library` to check
the merged output.

## Empirical grounding

`python measure_primitives.py` measures base rates on 3 years of real XAUUSD M1
(see [`meta/primitive_base_rates.md`](meta/primitive_base_rates.md)). The headline:
**~40–44% of candles sweep the prior candle's range** on every timeframe, and
another ~47–50% expand beyond it. "Price swept liquidity" is therefore close to a
coin flip on its own — treat these as the null hypothesis every concept must beat
before it earns the word *edge*.

Detectors live in `python/detectors/` with deterministic unit tests
(`python -m pytest detectors/ -q`, **43 passing**) plus real-data sanity checks:

- `primitives.py` — swing points, sweeps, candle-range (C1/C2), FVGs, displacement
- `cisd.py` — Change In State Of Delivery, the corpus's central confirmation
- `blocks.py` — order blocks ("opposing candles") and protected swings, both
  derived from the CISD close so the three concepts stay consistent by construction

### Contested concepts are parameterised, not resolved

Where the corpus disagrees with itself, the detector exposes the disagreement as
an argument instead of quietly picking a winner:

| concept | ambiguity in the source | parameter |
|---|---|---|
| `cisd` | which level must be closed through | `level_rule=` (3 readings) |
| `cisd` | "a series, never a single candle" vs walkthroughs showing one | `min_series=` |
| `order-block` | zone spans bodies or wicks — never stated | `zone=` |
| `order-block` | mitigation hinges on an "objective" never defined mechanically | caller supplies `objective_taken_at`; there is no default |
| `protected-swing` | "separation" from the swept level, with no tolerance given | `min_separation=` |

`measure_cisd.py` then makes the CISD disagreement numeric — see
[`meta/cisd_reading_comparison.md`](meta/cisd_reading_comparison.md). The three
readings pick the **same bar only 22–59% of the time** (Jaccard 0.218–0.588 across
15m/1h/4h/1D), so they are three different systems sharing one name. Any
performance number quoted for "CISD" is under-specified until the reading is named.

Detector outputs are **detections, not trades** — no direction filter, target, or
risk model. Given the base rates above, counts alone say nothing about edge.
