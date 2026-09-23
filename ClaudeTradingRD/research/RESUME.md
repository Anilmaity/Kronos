# Resume here — TTrades_edu research

Sessions of **2026-08-14** (corpus) and **2026-08-25** (phase 2: fitting and
backtesting). Everything below is verified state, not intention.

> **PHASE 4 (2026-09-23): all 471 non-psychology concepts were tested one by one. None is
> tradeable.** 43 raw EDGEs led to 5 that survived verification and BH, and the deep dive found 0 tradeable
> (2 artefacts, 3 descriptive only). Read
> [Phase 4 — the 471-concept campaign](#phase-4--the-471-concept-campaign) and
> `meta/concept_campaign_2026-09-23.md` before testing any concept again.

> **PHASE 2 IS DONE AND IT CHANGED THE HEADLINE.** The corpus phase ended
> believing the C2 small-wick asymmetry was the project's one surviving
> falsifiable edge. **It is a geometric artefact.** Read
> [Phase 2 — what testing found](#phase-2--what-testing-found) BEFORE acting on
> any finding in the older sections below; findings 4, 5 and 8 there are
> superseded and are marked inline.

## Where it stands — the corpus is COMPLETE and every unit is studied

| | |
|---|---|
| corpus mapped | 16 playlists, **443 unique videos**, ~101h |
| transcripts | **436 / 443** — everything obtainable; the 7 gaps are explained below |
| study units done | **32 of 32** |
| concepts in library | **505** (250 specified · 55 underspecified · 200 contested) |
| voice split | 290 TTrades · 177 guest · 38 mixed |
| notes | 32 files |
| distinct source videos cited | **381** |
| detectors | 4 modules, 60 passing tests |
| implementable now, TTrades' own voice | **119** |

### The 7 videos with no transcript, and why (all `permanent` — do not retry)
- **`MvD7fQQ0szE` "Backtesting Simplified" (74 min)** — **DRM protected.** yt-dlp's tv
  client says so outright; no caption track, and the audio 403s on every player
  client. Members-only/paid content. This is the one real content loss.
- 3 silent Shorts (23-36s): the vtt downloads but contains no speech.
- 3 Shorts with no title or duration in playlist metadata: deleted or private.

`Nlw-PZhoViQ` ("Top-Down Chart Lessons #1") also publishes no captions but WAS
recovered, by local ASR — see `python/whisper_fetch.py`.

## THE BLOCKER IS RESOLVED — what it actually was

The previous session concluded "YouTube IP-banned this machine, no software fix."
**That was half wrong**, and the wrong half cost a session.

Two independent failures were being read as one:

1. **No JavaScript runtime.** yt-dlp has deprecated JS-less YouTube extraction.
   Without a runtime it falls back to a path that reliably returns *"Sign in to
   confirm you're not a bot"* and HTTP 429 on the **webpage** fetch. Deno is
   yt-dlp's only default-enabled runtime and is not installed here — but **Node
   is on PATH** (nvm4w). Passing `--js-runtimes node` fixes this completely, on
   the home IP included. The home connection was never banned.

2. **A genuine per-IP quota on the caption (`timedtext`) endpoint.** The video
   page and player API keep answering forever; only caption downloads 429, and
   only after a budget is spent. The budget is **egress-class dependent**:

   | egress | captions before 429 |
   |---|---|
   | residential (home ISP) | ~93 |
   | VPN datacentre (Surfshark) | ~11 |

   It is a *quota*, not a rate limit — pacing does not avoid it (8 videos at one
   request per 4s got zero). A spent datacentre IP did **not** recover across
   two 60-minute cooldowns. **Prefer the home connection; use the VPN only to
   break a stuck quota.**

### The crawler to use now: `drip_fetch.py`

```bash
cd ClaudeTradingRD/research/python
python drip_fetch.py                 # runs until complete
python drip_fetch.py --max-hours 4   # or to a wall-clock budget
```

Sequential by design (parallelism cannot beat a quota, it only burns it faster
and blurs the signal). On quota trip it cools down with adaptive backoff, and it
**polls the public IP throughout — rotate the VPN and it resumes within 30s**,
backoff reset. Resume-safe; kill and restart freely.

`fetch_transcripts.py` was also fixed (node runtime; yt-dlp tried before the
permanently-`IpBlocked` API instead of after it, which was wasting one request
per video; caption-less videos classified `permanent` so they stop consuming
retries and stop tripping the ban detector). Prefer `drip_fetch.py` regardless.

Nothing is missing any more — the core curriculum (Build A Model / TTFM, both
Education-ICT playlists, all of The Foundation) is fetched AND studied.

`python/whisper_fetch.py` recovers caption-less videos with local ASR
(faster-whisper + ffmpeg, both already installed). Use it only when a video
truly publishes no captions — ASR mishears domain jargon, so its output is
headed `transcript_source: whisper-<model>` and any concept citing it must say
so in `ambiguities`. Quotes from ASR are verbatim against *our file*, not
necessarily against what the speaker said.

## Re-running the pipeline

All 32 units are studied. If you re-study a unit, always:
```bash
python validate_concepts.py      # provenance — MUST pass before merging
python merge_concepts.py         # _inbox -> concepts/<category>/, prunes stale
python build_index.py            # INDEX.md + index.json
python gaps_report.py
```

## Decisions already made — don't relitigate

- **`_inbox` staging** exists because parallel agents writing one concept file
  race. Merge groups by id, unions evidence, escalates disagreement to `contested`.
- **`voice` matters more than it looks.** T Talks and Live Stream Guests are
  *interviews* — different traders with contradictory methods. Filter to
  `voice in (ttrades, mixed)` for the channel's own method. 177 of 505 are guests.
  **`merge_concepts.py` now respects a draft's declared `voice`** and only falls
  back to the playlist heuristic when none is declared, recording the derived
  value as `voice_playlist` when they disagree. This matters: the heuristic
  cannot see *who is speaking within* a video, and it was silently re-tagging
  TTrades' own rules stated inside guest interviews as `guest` (6 real cases,
  including his own position sizing and stop rules).
- **Contested concepts are parameterised, never resolved silently.**
- **Provenance is enforced mechanically.** `validate_concepts.py` checks every
  cited video exists, has a transcript, and every quote is <=15 words and
  actually present. It has already caught a fabricated (stitched) quote.
- **A concept only earns an entry if it is decidable.** Otherwise
  `status: underspecified` plus explicit `ambiguities` — never backfilled from
  generic ICT knowledge.

## Findings worth carrying forward

1. **THE TIMEZONE IS ANSWERED: New York / EST**, and now stated outright, not
   inferred: *"all times are shown in Eastern Standard time"*. **Two caveats that
   matter for XAUUSD.** (a) He says "EST" literally, but the NYSE-cash-open
   anchor implies US-Eastern-with-DST — parameterise it, never hardcode UTC-5.
   (b) The grid is **asset-class specific**: futures 02/06/10/14 NY, forex offset
   to 17/21/01/09, and *"we don't really have the 930 open with Forex"*. Any PO3
   or session detector must branch on asset class.
2. **CISD IS ADJUDICATED.** One video defines MSS and CISD in explicit
   opposition: MSS is displacement through a swing high/low; CISD is *"focused
   on the close and displacement below the opening price"* of the opposing
   candle series, and *"happens prior to the market structure shift"*. So the
   **opening-price-of-the-opposing-series** reading is his; anything firing on a
   close through a swing was a mislabelled MSS. Two refinements: **the point of
   interest is part of the definition, not an extra filter** (a bare
   close-through with no swept level or FVG does not qualify), and **IC-CISD is
   the same test relocated** inside a continuation candle, not a rival system.
   *Residual gap, now narrow:* WHICH price of the series — first candle's open,
   highest open, or the extreme. The extreme reading is ruled out (*"Mark out the
   opening price in that series"*); the rest is undetermined and IS the whole
   22-59% agreement problem. Historical note that explains the confusion: **CISD
   appears ZERO times in the older Education-ICT playlist** — "break structure"
   did its job. It was later carved out of MSS. The three readings are stages of
   an evolution, not simultaneous contradictions.
3. **C3 IS NO LONGER DEGENERATE.** The old reading (~100% of candles qualify)
   came from recording it as an EQ test. It is not: a C3 closure exists **only
   when C2 failed to close**, and is measured against **candle 2's OPENING
   price**. One-sided and decidable. Filed `contested` because a sibling unit
   records the reference as C2's *extreme* (stricter) — a detector should compute
   both and report the disagreement rate rather than pick one.
4. ~~**The C2 wick claim still survives testing**~~ — **SUPERSEDED 2026-08-25.
   It survived *counting*, not *testing*.** The 78-83% vs 63-66% split replicates
   exactly and is a **geometric artefact**: entry (the C2 close) already sits
   beyond the C2 open, so "delivery beyond the open" asks price to *retain* a
   cushion it has already banked, and a small wick mechanically means a large
   body means a bigger cushion. Across 1h wick quintiles delivery runs
   84.2%->58.6% while the distance to that target runs 0.817R->0.157R in exact
   lockstep. On a target-free measure the ordering **reverses**. See
   `meta/backtest_c2_wick.md`.
5. **PARTLY SUPERSEDED 2026-08-25 — a number *is* spoken, under another name.**
   No wick-to-body *ratio* is ever stated, which is what made this look like a
   clean negative. But **0.5 is spoken constantly** and one video calls it a
   mechanical way to measure wick size outright (`3eVxTV_7L2U`), in his own voice
   in `Te9jUijPXZo` / `LKNQDAdId4s`. The catch, and the reason the negative felt
   true: **0.5-of-range admits ~85% of XAUUSD candles — it is a ceiling, not a
   filter.** The operating point still had to be fitted. See
   `meta/threshold_fits.md`. Original text follows, still correct on the ratio:
   ~~WICK SIZE HAS NO NUMBER ANYWHERE~~, checked
   across 443 videos including three Shorts batches and a video literally titled
   for it (which asks *"What does that look like?"* and answers with a procedure
   that is circular for a detector). What IS attested, by three independent
   units, is **candle classification by wick-vs-body**: reversal candle =
   *"the wick is larger than the body"*; directional = wick smaller than body.
   **Do not conflate two different questions:** (i) *which level do I mark on
   this candle* (full body -> 50% of body; large wick -> 50% of the wick), and
   (ii) *is this wick small enough to count as expansion* — only (i) is answered.
   The expansion threshold is **a parameter to FIT against his narrated
   accept/reject calls, not to find by more reading.**
6. **`consolidation` now has two mechanical tests**: *"price remains internal to
   a high and a low"*, and the retracement discriminator *"does it form a
   protected swing? No. That means it's then a consolidation."*
7. **`displacement`/"aggressive" has a comparative procedure** (the only one in
   the corpus): after a short-term high breaks, take a fixed candle window and
   compute the window's range and the distance travelled beyond the broken high;
   displacement is the larger range AND greater distance in the same candle
   count. Relative, not absolute — but implementable.
8. **NARROWED 2026-08-25 — the hours ARE stated, just never as *his own gating
   rule*.** `concepts/time/killzones.yaml` carries explicit windows,
   verbatim-verified against `raw/transcripts/MPeeE55rNOw.txt`: forex Asia
   20:00-00:00, London 02:00-05:00, NY AM 07:00-10:00, London Close 10:00-12:00;
   indices NY AM 08:30-11:00, PM 13:30-16:00 (all New York). It is a solo
   instructional video walking a PDF, so **taught convention rather than a rule
   he is narrated applying** — but that is far stronger than convention imported
   from outside. Do not use the old flat negative to justify picking a window
   arbitrarily; test the attested ones. See `meta/session_window_fit.md`.
   Original text: ~~`session` / kill-zone HOURS ARE NEVER STATED. Settled negative.~~ "Kill
   zone" is used as a hard gate — *"this must all be done within a kill zone"* —
   with no clock attached, and the phrase occurs zero times across whole
   playlists (grep-verified). The widest usable statement is *"I only look to
   take trades between 8:30 and 12"*. This blocks 68 concepts and **no amount of
   further reading will fix it** — pick a window and parameterise.
9. **Base rates are brutal**: ~40-44% of candles sweep the prior candle's range
   on every timeframe. "Price swept liquidity" is near a coin flip alone.
10. **Things withheld ON PURPOSE — stop hunting them.** Confirmed on stream:
   anticipation CISD, the inside-bar procedure, candle-3-consolidation handling,
   the T-spot's derivation. And **the indicator's actual C2/C3/C4 conditions are
   paywalled** — *"I go over all the requirements for these within my course and
   mentorship"*. A faithful reimplementation is blocked at source. That is a
   ceiling on this project, not a gap in the corpus.
11. **The corpus is SATURATED.** The last Shorts batch returned 0 new concepts
   from 49 videos — every candidate was already in the library. More TTrades
   material is unlikely to add much; the remaining work is fitting parameters and
   backtesting, not reading.
12. **Remaining blocking terms** (`meta/automation_gaps.md`): `session` (68),
   `consolidation` (47), `displacement` (37), `aggressive` (34), `timezone` (34),
   `strong` (26), `shallow` (23). Most now have partial answers above; the honest
   summary is that the corpus is qualitative by nature and the gap is closed by
   **fitting, not reading.**

## Gotchas that cost time

- **The 2026-08-09 "IP is banned, no software fix" conclusion was wrong.** It was
  a missing JS runtime. Before concluding an IP ban, check
  `python -m yt_dlp --js-runtimes node ...` — and note that a 429 on the
  *webpage* fetch means something different from a 429 on the *caption* fetch.
- **yt-dlp pagination**: a stale yt-dlp silently returned exactly 100 videos for
  the three largest playlists (really 108/141/229). Treat any round-100 playlist
  count as truncated until proven otherwise.
- **curl_cffi version trap**: yt-dlp supports `0.5.10` and `0.10.x–0.15.x` only.
  pip installs 0.16+, which yt-dlp ignores *silently*. Pinned to 0.15.0.
- Chrome cookies cannot be extracted on Windows (App-Bound Encryption, yt-dlp
  issue #10927), and there is no Firefox profile here. Cookies do not help
  anyway — the caption quota applied to the user's own logged-in browser too.
- **Public Invidious instances are not a workaround.** `inv.nadeko.net` returns
  caption *metadata* but zero-byte caption *bodies*; most other instances no
  longer serve the API at all.
- `await_vpn_and_fetch.py` is **stale**: its reachability probe uses
  youtube-transcript-api, which is permanently `IpBlocked` here, so it would
  never declare a working IP usable. `drip_fetch.py` supersedes it.

## Phase 2 — what testing found

Session of **2026-08-25**. Five parallel workstreams; all six of the old "next
steps" below are now done. Every headline number was independently recomputed by
the coordinator before being written here.

### The documents (read in this order)

| document | what it settles |
|---|---|
| `meta/backtest_c2_wick.md` | the C2 wick claim — **refuted where measurable** |
| `meta/threshold_fits.md` | numbers for `displacement`/`aggressive`/`small wick`/`shallow`/`strong` — **109 concepts** |
| `meta/session_window_fit.md` | the session window, DST, and the 4H grid for gold — **68 concepts** |
| `meta/ttrades_method_spec.md` | the ordered method spec — all **328** own-voice concepts, zero guest leakage |
| `meta/guest_methods_appendix.md` | the **177** guest concepts, as a comparative library |
| `meta/external_crossref.md` | independent outside check of the hardest adjudications |
| `meta/qualifier_calls.md` | 56 curated narrated accept/reject calls |

### The five findings that change what to build

1. **The C2 small-wick asymmetry is a geometric artefact.** See amended finding 4
   above. What matters operationally: **the effect is absent where this dataset
   has power and untested where it does not.** Minimum detectable win-rate
   difference is 1.9pp (15m) / 3.8pp (1h) / 7.4pp (4h) / 17.0pp (1D); at the
   fitted cut the measured effect is +1.4pp (15m) and +0.9pp (1h), both under
   their floors. A 4h residue of +4.6pp has the right sign and size versus an
   independently-measured +4.0pp, but sits below 4h's own 7.4pp floor and is
   **mostly C2-ness rather than wick size** (whole book +5.9pp vs small-wick
   +7.8pp). Resolving 4h/1D needs ~4,700 C2s — roughly 10 more years at 4h and 55
   at 1D. **That is more data, not more analysis. Do not re-run this on the same
   three years and expect a different answer.**
2. **Beware the confounded metric — it was found twice, independently.** Any
   outcome that reduces to "where did the candle close relative to its own open
   or extreme" measures geometry, not prediction. It separates by −28pp to −44pp
   in the flattering direction and means nothing. Always pair it with a
   **matched random-entry control** (same direction, stop distance and target
   distance) and resolve exits on **M1**: the same book resolved on
   signal-timeframe bars flips sign (1h/2R OOS: M1 −0.032R vs 1h bars +0.013R).
3. **For gold, time-of-day buys opportunity, not accuracy.** 29.9% of daily
   extremes form in 08:00-11:59 NY on 17.4% of the traded clock (1.72x) — but
   gating to the corpus's own forex NY AM window returns **−0.057R vs the rest of
   the day, t = −3.11**, the only multiple-testing-robust result of twelve
   windows. 08:30 NY is the densest half-hour for extreme formation *and* sits in
   the worst expectancy hour: the best time to *have a level* is not the best
   time to *take an entry*. That is his own "manipulation first" claim as a
   number.
4. **Two parameters are now settled — stop sweeping them.** Timezone is
   `America/New_York` **with DST**, decided empirically (the venue's daily break
   resumes at 18:00 NY on 99.8% of 605 occasions under DST-aware Eastern, but
   smears across two hours under fixed UTC-5). The 4H grid for gold is the
   **forex** grid (17/21/01/09 NY), weakly — the grids are behaviourally
   indistinguishable (z = 0.08) and the tiebreak is structural: 0% of forex-grid
   candles straddle the daily break vs 16.5% for futures.
5. **`displacement` and `aggressive` are one term, not two** — used in apposition
   in `b6yvRKf8haE`, so 62 concepts share a single threshold. Also settled from
   the corpus: the opposing-run numerator is **one-sided, open->extreme**
   (`SlWxhzhLo3A`), **"strong" grades the close, not the wick** (`gjoRPszj-Qk`),
   and the two 0.5 rules are **one rule with a branch** (`07lOxv39LdY`).

### Traps that cost time in phase 2 — check for these

- **The 18:00 NY "kill zone" does not exist.** It is the densest hour for daily
  extremes (11.2%) and it is a **market-reopen gap artefact**: the first 15
  minutes after a halt are **6.02x** over-represented among daily extremes across
  788 halts, and excluding the first 30 minutes collapses the hour while leaving
  the NY-morning block intact. The 18:00 *anchor* is still legitimate for framing
  a daily candle; the *window* is not tradeable.
- **Units bugs survive self-review when two scale errors cancel.** A per-day
  event rate was published as a share of extremes (59.8% where the true share is
  29.9%), and the derived lift was *correct* because the expectation was scaled
  the same wrong way — so nothing looked inconsistent internally. It only
  surfaced against an outside recomputation. **Recompute headline numbers from
  raw data, not from the pipeline that produced them.**
- **pandas datetime resolution**: this build uses **microseconds**, so
  `index.view("int64")` arithmetic is silently 1000x off.
- **`bars.resample` is `label="left"` — the event timestamp is the bar's START.**
  Entry happens at the bar's *close*, i.e. `event_time + one bar`. Scanning M1
  forward from `event_time` replays the signal candle itself, which by
  construction touches its own extreme, so the stop fires instantly and the book
  returns a **~3% win rate**. Verified 2026-08-25 by hitting it. The danger is
  that 3% does not look like a bug — it looks like a catastrophically bad
  strategy, and it is the *same* off-by-one-bar that in the other direction
  (peeking into the signal bar) manufactures a spectacular edge. Assert the
  entry index is strictly after the signal bar closes.
- **The corpus is not a labelled dataset.** Of 1,926 regex candidates, 56
  narrated accept/reject calls survived hand curation and **zero could be tied to
  a dated bar** — there is no chart in a transcript. No supervised fit is
  possible; the threshold recommendations are distribution-anchored with graded
  evidence. The auto-labeller agreed with hand review on only 17 of 31.

## Phase 3 — the conjunction is REFUTED

Session of **2026-08-25**, immediately after phase 2. Protocol pre-registered and signed
off *before results existed* (`meta/conjunction_preregistration.md`, amendments A1-A5 all
logged pre-result); executed in `meta/backtest_conjunction.md`. 209 tests green.

**The question:** every primitive sits near its base rate, but the corpus claims the edge
lives in the *conjunction* — HTF bias -> POI -> CISD -> timing. Does stacking the gates add
anything, or does it only shrink the sample until noise resembles skill?

**The answer: it adds nothing, and the baseline is null too.**

| cell | n | differential vs matched control | verdict |
|---|---:|---|---|
| **5m/1H/1D R4** (pre-designated powered cell) | 1,613 | **−0.021 R** [−0.079, +0.035] | **REFUTES — a well-powered zero** |
| 15m/4H/1D R4 (his favourite) | 534 | −0.028 R [−0.124, +0.069] | indeterminate — underpowered |
| PRE sample, 5m R4 (never examined before) | 1,285 | −0.004 R [−0.063, +0.056] | confirms |

- **Rung 0 is null on every stack** — 15m −0.006, 5m −0.005, 1h +0.009, all CIs containing
  zero on 8k-98k events. So "beats rung 0" and "beats its own control" converge; each
  verdict states which comparison it rests on.
- **No forward transition on any stack earns ADDS VALUE.** Family A: **39 comparisons, zero
  clear p=0.05 even uncorrected.** No leave-one-out removal is significant, so **no gate can
  be named load-bearing.**
- **It is not regime-dependent — it is uniformly absent.** All 15 rung-stack combinations
  meet >=3/4 sign agreement and on 12 the agreeing sign is **negative**; the differential
  sits at or below its control in **all four blocks including B4**.

### The coordinator's B4 prediction was wrong, and how

Mid-run I measured bare CISD collapsing from +0.12R (3-year file) to non-significant on the
certified span with the edge concentrated in B4, and predicted the whole ladder would prove
B4-carried. **It did not transfer to the locked ladder.** Two reasons, both worth keeping:

1. The 4h book I measured was **UTC-aligned**; on the **forex grid §1.4 locks for gold** the
   same book goes from +0.047R to **−0.0006R** (verified independently). B4 concentration
   survives the grid change (+0.206 -> +0.215) but the pooled effect does not.
2. **`session_window_fit.md`'s "the grids are behaviourally indistinguishable" (z=0.08) is
   true for follow-through and false for an outcome book.** Treat that phase-2 line as
   scoped to what it measured. The 4H grid is **not settled** — carry it as a knob.

### What the pre-registration itself got wrong (10 items, `meta/backtest_conjunction.md` §11)

The load-bearing one: **§4.1a specifies POI availability and §3.2 does not apply it.** The
third POI branch waits five bars to see whether 50% of the series bodies hold, while
`max_wait=3` puts the CISD three to five bars *earlier* — so the verdict usually resolves
**after** the event it qualifies. 23% of events carry such a pass; R4 falls 722->535 (15m),
2,234->1,618 (5m). Both ladders are reported; **the verdict is unchanged either way.**

Also: the two declared CISD level readings are **the same reading** (Jaccard 0.997); the
inside-bar [P] is inert; `no_fade` is not *definitionally* redundant (1 exception in 862);
and **the matched control makes §5.1's cost condition arithmetically vacuous** — cost
cancels exactly in the differential, so that "test" was guaranteed to pass.

### Bounds on this conclusion — state them whenever citing it

- **No sustained bear market in the certified span** (2013 is the only one and it is on the
  wrong side of the Oct-2015 calendar break). Nothing here is validated against a gold
  downtrend.
- **One instrument.**
- **The only stack whose R4 clears the power floor outright (1m, 8,532 events) is the one
  `excluded-tooling` disowns** — phase 2's structural complaint, restated: the timeframes
  carrying the claim have the least data, and the timeframe with data the method rejects.

### What is worth doing next

0. **Do not re-run the conjunction on this data expecting a different answer.** The powered
   cell is a measured zero and the confirmatory PRE sample agrees. The open question is
   *other instruments*, not more gold.
1. ~~**Test the model, not the primitive.**~~ **DONE — see Phase 3 above. Refuted.** Every
   primitive in isolation (sweeps at 40-44%, FVGs in 61-77% of break windows, wick size at
   ~0 where powered) sits near its base rate, **and so does their conjunction.**
2. **Get more 4h/1D data before revisiting the wick claim.** It is the one open
   question that is genuinely underpowered rather than answered. Note the certified span
   already tripled the sample and the effect shrank rather than clarified.
3. **Mine the `contested` set** (200 concepts) for older-vs-newer evolution pairs;
   `meta/ttrades_method_spec.md` §8.1 and the `education_ict_01/02` notes carry
   the tables. This is the last unexploited structure in the library.
4. **Do not import outside definitions into `concepts/`.** `meta/external_crossref.md`
   is deliberately a separate second opinion — the library's whole value is that
   every claim traces to a specific video.

## Phase 4 — the 471-concept campaign

Run on **2026-09-23**. Full record: [`meta/concept_campaign_2026-09-23.md`](meta/concept_campaign_2026-09-23.md).
The per-reading table is `concept_campaign/concept_verdicts.csv` (663 rows), built by
`concept_campaign/build_concept_verdicts.py`. Everything below is verified state.

**The question:** phase 3 refuted the conjunction. Does any *single* concept have a tradeable edge on
XAUUSD when it is tested on its own terms? **No.**

### Verified state

| | |
|---|---|
| roster | 471 concepts (the 505-concept library minus 34 psychology), 61 batches, 663 readings |
| harness | `python/concept_lab`, rules `concept_lab-rules-2`, locked before any result; symmetric look-ahead probe on every scored frame; false-EDGE rate on noise 2.1% |
| verdicts (readings) | NULL 311 (powered) · UNDERPOWERED 223 · UNTESTABLE 59 · EDGE 43 · NEGATIVE 27 |
| funnel | 43 raw EDGE → 9 upheld by two adversarial verifiers → 5 pass BH over 864 hypotheses (612 written + 252 ledger-only) → deep dive: **2 ARTEFACT, 3 DESCRIPTIVE_ONLY, 0 tradeable** |
| ARTEFACT | `cheat-code-entry`, `aggressive-run-hammer-signature`. The matched control copies stop *distance* but not *placement*. Against a stop at a fresh structural extreme, 60–85% of the effect goes. The rest is ≤ +0.03R and period-bound. Median stops of 0.44 / 0.59 pt make both deeply net-negative at a 0.25–0.35 pt spread. |
| DESCRIPTIVE_ONLY | `point-of-interest a`: CISDs off a non-extreme HL/LH lose ~0.08R; it is a negative filter, and the gated book nets −0.009R at 0.30 pt. `daily-profile-session-windows`: a volatility-only null explains 83% of the +12pp, and the residual decays to +0.2pp. `fvg-three-levels`: the leg extreme is reached first +1–2pp more often, against structural controls too, but every trade version is net-negative. |
| robust NEGATIVEs | on gold **09:30 NY, not 08:30, is the volatility step** (57.4% vs 73.6%, Holm). **Entering while the hour is already a "2"** costs −0.044R (Holm). Big-range days are followed by big days. Two-sided rotation is rarer than chance. V-shaped sweeps do worse than lethargic ones. PDH/PDL are reached slightly *less* often than equidistant levels. |
| why EDGEs died (34) | generic stop geometry or limit-fill emulation 10 · time of day not held 7 · rate null not vol/state-matched 5 · tested another claim 5 · knife-edge parameter or grid 4 · lucky control seed 3 |

### What to do next

1. **Change the harness before testing anything else.** Add a structural control (stop at a fresh extreme at matched distance), a
   volatility-matched rate null, a native limit-order entry, a realistic spread in pt (not a flat 0.04R) and management legs
   (partials, BE, trail). Section 3 of the report shows these gaps produced 22 of the 34 false EDGEs. Version the change as rules-3 and re-run
   calibration and the noise-book false-EDGE check before any concept.
2. **Then re-test only the short list:**
   - The 4 verifier-upheld but BH-failing candidates: `balanced-price-range-overlap a`, `intraday-reversal`, `no-shorting-below-lows b`, `inversion-fair-value-gap b`.
   - The two strongest UNDERPOWERED leads: `failure-to-manipulate` (+0.129R, q 0.017) and `htf-two-entry-opportunities a` (+0.23R, q 0.021).
   Give each a structural control and spread in pt, and run the two-lens verification before believing anything.
3. **Other instruments, not more gold.** The rare weekly, TGIF and MMXM setups (n < 30 in 10.5 years), the SMT concepts
   (tested only on XAG H1) and the ES/NQ concepts all need data this workspace does not hold. An economic calendar would unlock the ~7
   news concepts.
4. **Use the descriptive findings as context, not signals.** Extremes form in the 08:00–11:00 NY volatility block. Avoid 1h
   CISDs off a non-extreme HL/LH. Do not chase an hour that is already a 2.

### What not to redo

- **Do not re-run the 311 powered NULLs, or any concept, on the same harness and data** expecting a different answer.
- **Do not re-derive the 5 deep-dive verdicts.** Their scripts and outputs are in `concept_campaign/deepdive/<concept>/`.
- **Do not trust a raw `diff` for trading decisions.** Cost cancels in it. Any setup with a stop under ~1–2 pt is net-negative
  on XAUUSD whatever its diff says.
- **Do not treat BH/Holm survival as confirmation.** 5 of 8 Holm-surviving EDGEs were refuted as systematic confounds.
- **Do not edit `concept_lab`, `results/` or `tests/`.** They are the audit trail. New work goes in a new folder with its own ledger.
