# Study notes — `shorts_03`

**Unit:** 60 YouTube Shorts, 21–80 seconds each (total ~48 minutes of speech).
**Transcripts available:** 60 / 60. None missing.
**Concept drafts produced:** 12 — **2 new ids, 10 reusing existing ids.**
**Shorts judged to contain nothing new:** 46 of 60 (see the explicit list at the end).

---

## What this genre is, and what it is worth

These Shorts are almost entirely re-cuts of the long-form lessons already studied in the 27
other units. The overwhelming majority are a single annotated chart replay of a concept the
library already holds — a CISD confirming a daily bias, a breaker in a continuation, a weekly
profile walked through on one example. Reading all 60 and mining them for volume would have
produced perhaps forty low-quality duplicate entries. That is the wrong output, so this unit
deliberately produced twelve.

The one thing the format genuinely buys is **compression under a hard time limit**. A 30-second
clip cannot afford the hour-long version's hedging, so he sometimes states as a flat declarative
sentence a rule the long video only demonstrates. Three of those compressions are the real
yield of this unit and all three land on terms the library had flagged as blocking.

**The headline find, verbatim, on the corpus's #1 unquantified term:**

> "A reversal candle has a large wick and a small body." — `ecTRHQrbYzI`

**And on "aggressive" / "shallow", both blocking terms, defined against each other in one breath:**

> "Expansion is aggressive, fast, and large range." / "Retracement is slow and shallow in a small range." — `OzugLBi0PVQ`

Neither is a *number*. There is no ratio, no percentage, no bar count, no fib bound anywhere in
these sixty Shorts. But both are procedures a detector can be built against, and both are
strictly more than the library had.

---

## Theme 1 — Wick size (the highest-value cluster)

Six Shorts are about wick size, and read together they finally answer *what is being sized* and
*by what evidence*, even though they never answer *how much*.

**What the wick is.** `aQoMSAaIXsg` states it outright while re-framing a bullish day as a bearish
setup: "this area from here to the high would be the wick" — i.e. the wick is the **opposing run**
the candle makes before it turns. He then poses the sizing question as a binary: "Is this a
shallow run? No, this is a large opposing run."

**How it is sized.** `ecTRHQrbYzI` supplies the only measurement basis in the unit. Distinguishing
a reversal candle from a directional one, he says the reversal candle's open-to-extreme leg is
large because "This used a bunch of time and a bunch of range" — so wick size is judged by the
*time* and the *range* the opposing run consumed, not by an absolute distance. The resulting
shape is the definition quoted above: large wick, small body.

**What follows from it.** Two consequences, both already in the library but stated here more
crisply. Small wick → expansion, with the EQ named as the target (`nyTiWfwWM6M`, `9dC9_ZunnTg`,
`dZz7ZG6oZQM`). Large wick → *adjust targets*: not the far extreme, but the daily open and the
session lows around it (`5UsKZ7pZqvY`: "when we have a larger wick, my expectations is favoring
back towards that daily open"; `aQoMSAaIXsg`: "I want to be focused on the opening price").
`5UsKZ7pZqvY` also gives the reasoning as a discipline rather than a mechanic — "not trying to be
greedy and look for a massive move" — and is explicit that price *may* still go further; the rule
sets expectation, not a ceiling.

**One genuine edge case** appears in `bsgh2HiRIXQ`: a candle that does not support expansion *and*
has no wick at all. It is not tradeable as a wick; it is downgraded to drawn liquidity and you
wait for a new candle open.

→ New id `wick-size-test`; contributions to `reversal-candle-quality`,
`small-wick-expansion-rule`, `large-wick-target-adjustment`.

## Theme 2 — Expansion vs retracement, and the half-level filter

Four Shorts (`OzugLBi0PVQ`, `WiYZKc6ZAxA`, `p6Cgc1mPCf4`, `g37Z3GpSLGc`) restate the retracement
phase. Beyond the aggressive/shallow pairing quoted above, the useful additions are:

The **half-level filter** in its most decidable form — `g37Z3GpSLGc`: "make its low in the upper
half of its previous candle's range". `p6Cgc1mPCf4` gives an equivalent fib phrasing, "Does this
retracement reach into a discount? No.", which is a second, independently checkable test of the
same thing.

The **failure branch**, which the library did not carry and which is two-sided: if price opens and
trades a lot lower than the EQ, expansion is off — price either fails and takes out the previous
candle's low, *or* it reverses back to its opening price and the **next** candle becomes the
expansion candidate.

Note that the unit reproduces, rather than resolves, the corpus's standing contradiction:
`OzugLBi0PVQ` says the retracement is **slow**, `WiYZKc6ZAxA` says it should be **quick**. Both are
recorded; neither Short reconciles them. This is flagged in the `retracement-phase` draft.

## Theme 3 — Time levels (the second-most-valuable find)

`B_7pMkbHyC4` is the only Short in the unit that attaches decidable behaviour to clock times, and
it does so as a complete if-then cascade rather than the descriptive clustering the library holds
in `new-york-intraday-time-levels`:

> "8:30 and 9:30 are the most important time levels"
> "if 8:30 makes an opposing run. And if it does, 9:30 can expand"
> "8:30 fails to make an opposing run, then I want to see 9:30" [make that opposing run, and 10:00 expand]

with an outer branch on whether London already set the day's extreme. `-fgyK1yb4Io` supplies the
lower-timeframe structure for the 9:30 case (HTF candle with a small wick, then a 9:30 CISD that
is either a closure right at the open or an opposing run followed by a close over).

**This does not solve the kill-zone-hours gap.** No session window is defined; "kill zone" is not
used at all in this unit. What it gives is three concrete decision timestamps with an ordering
rule between them. Two honest caveats are recorded in the draft: no timezone is ever spoken, and
"London has set the low of day" is a hindsight fact used as a live precondition.

→ New id `ny-am-time-level-cascade`.

## Theme 4 — Liquidity classification

`EuW3h0gKZKw` is the cleanest statement of high- vs low-resistance liquidity anywhere in the
corpus and — unlike the existing library entry — assigns each to a *job*: "I want to use low
resistance liquidity or these failure swings as a target" and "use high resistance liquidity or
these sweeps as a spot for my stop-loss". `kWKo5Mu0ANQ` shows the manufacturing step: inside a
consolidation he waits for a purge of the low specifically *in order to create* high resistance
liquidity to hide behind. That is target-and-stop selection reduced to one classification, which
is exactly what a detector wants.

## Theme 5 — Consolidation, with a real divergence

`yfj10dtkRKY` restates the consolidation definition and its preconditions ("following a large
range or after price reaches an important level"), but states the directional rule **the other way
round from the library**: "If the low of the range gets taken out first, that is generally
bullish" — direction read *off* the first side taken, rather than a pre-existing bias selecting
which side must be run. Both readings are TTrades' own voice. Recorded as an unreconciled tension
rather than smoothed over. The SMT exception (a correlated asset taking the side removes the need
for a sweep on this one) is stated in both readings.

## Theme 6 — Two mechanical refinements worth keeping

`OJPqaO6I-so` independently corroborates the **untidy-leg CISD fallback** the library currently
flags as an open question: "we don't have a clean series of down close candles… I just use this
whole move." Stated as general practice, not a one-off. It does **not** answer the library's
primary CISD question — which *price* of the series the close must clear — and neither does any
other Short in the unit.

`yTatKcNuKQU` sharpens relative-strength ranking from "bullish close = stronger" to a
CISD-referenced test: the weaker asset's close still sits below its down-close candles, the
stronger one "bought all the way back up and closing over this down close candle", and the finest
grade is an asset that "is not yet reaching for the opening price of this down close candle".

## Theme 7 — The 4th day of a swing

`Te9jUijPXZo` and `EnAoorLVtoQ` state candle 4 as a standalone **daily-bias procedure** rather than
a position in the sequence: third candle prints → mark the upper (bullish) or lower (bearish) half
→ that half is where the day's wick is expected → drop to the hourly for a POI inside it → wait for
an intraday CISD → take the LTF entry, stop on the low, 2R. The library's `fractal-model-c4`
already carries the half-filter; the four-step chain as a bias *method* is the addition.

---

## Transcript hygiene

All 60 are `yt-dlp-auto` captions with no timestamps, so **`approx_time` is omitted from every
source entry in this unit** per the schema rule. Known artifacts, confirmed present:

- **"candle 2" → "candle to"** fires once, in `KF20ga56xUo` ("is this a candle to closure? No"),
  where the same clip elsewhere renders it correctly as "candle two". Read as "candle 2".
  (`g37Z3GpSLGc` also matches the string but as an innocent "the next candle to open".) No quote
  cited in this unit contains the artifact. Grep for it before quoting any Short by hand.
- **"reach" → "wretch"** is the corpus-wide artifact flagged in `cisd.yaml`. It fires **zero times**
  across all 60 transcripts in this unit — "reach" survives intact in `EuW3h0gKZKw` and
  `p6Cgc1mPCf4`, both of which are cited on that word. Verified by grep before quoting.
- **"9:30 to 10:00" → "930 to10"** in `-fgyK1yb4Io`. Quoted verbatim including the artifact rather
  than corrected, per the no-retyping rule.
- **"up close" → "upcloed"** once in `gKlFierEBJg`, **"down close" → "down closed"** in `mARxFtQ-Ivg`.
  Both mean the ordinary opposing-candle term.
- `[clears throat]` markers appear inline in `bsgh2HiRIXQ` and `WPUR9IueLfo`; they sit mid-sentence
  and would break any quote spanning them. Avoided.
- Numerals are inconsistent ("candle 2" vs "candle two", "8:30" vs "830"). The validator's
  normalizer strips punctuation, so `8:30` counts as two words — this cost two quote trims and is
  worth knowing for anyone quoting clock times.

Every quote in the twelve drafts was copy-pasted from the transcript file, never retyped, and all
twelve pass `python/validate_concepts.py` with zero errors.

---

## Shorts that contained nothing new (46)

Grouped by what they restate. All were read in full; none produced a draft.

**Already-held entry mechanics, one worked example each (13):**
`ElgFCenHU58` (0.5 of a large wick — `half-wick-respect`) · `JkK03vA8uhY` (propulsion block mean
threshold — `propulsion-block`) · `Mqfwx-GiLgY` (unicorn = breaker + FVG — `unicorn-model`) ·
`m8N2yMkP5ls` and `WPUR9IueLfo` (breaker in a continuation — `breaker-continuation`) ·
`RPSDFTWeS0g` (IFVG needs a relevant level — `inversion-fair-value-gap`) · `sRMSRMO448o` and
`OzaK6Cz_J3Y` (IRL↔ERL rotation — `internal-external-rotation`) · `GCMfE8CfIeY` and `IO_hGI1XTwE`
(the Twitter model, verbatim to the existing entry — `mmxm-twitter-model`) · `-CK7ivvqKpU` and
`l6FV0DEgSp4` (top-down bias→structure→entry — `top-down-analysis-procedure`) · `1iop3u3K5-w`
(the same, labelled "fractal across timeframes").

**Fractal-model fundamentals restated (6):**
`uRyvRv9dj8Y` and `gKlFierEBJg` (price cannot reverse without a swing point) · `qKjsnabC7lU`
(how the candles are numbered) · `pj0svZASeWg` and `i0rBnxtQHzQ` (reverse-engineering a completed
expansion) · `U8w24xnzwnM` (expansion in + expansion out = reversal at a level).

**Profiles walked through on one example (10):**
`ANxA19GlVeg` (London reversal) · `H0mslrw704k` (New York manipulation) · `59HcozbMtn0` and
`zCr9H-Y-Xxw` (seek & destroy) · `KF20ga56xUo` (classic expansion week) · `-AFI7Z8fjcU`
(consolidation reversal week) · `sjTMUPoifr8` (midweek reversal week) · `ZwNOdZenLyk` (Thursday
counter week) · `fBqeeGe-9aA` (the Monday rule — a clean restatement of
`monday-trade-rule`, already 3-sourced) · `C19FFJKo7c0` (trading a bias invalidation).

**Structure / liquidity restatements (9):**
`QZ9-3qRntLw` (the three ways a protected swing forms — a tidy enumeration, but all three routes
are already in `protected-swing`) · `hAE00ZN4pxE` (SMT on inversely correlated pairs) ·
`MQ-qmO_KEtA` (ignore candles that don't form a swing — `swing-forming-candle-selection`) ·
`jDUXipRfk_A` (trade with the HTF trend) · `earn4hrj8bc` (don't long after expansion —
`dont-trade-after-expansion`) · `vA_kVHYHFXA` (four-candle daily read) · `65jeDJVNjKM` (target the
opening price when the intraday lows aren't failure swings — the reasoning is already in
`high-vs-low-resistance-liquidity` and `low-expectation-target-selection`) · `OJPqaO6I-so` and
`mARxFtQ-Ivg` were mined for the CISD draft and are *not* counted here.

**Platform tutorials with no trading rule at all (2):**
`5qLJDmZzgeE` (taking partials in TradingView) · `GIZQJRR6VaM` (OCO orders). Pure UI walkthroughs —
skipped entirely, as instructed.

**Motivation / no rule (0):** none. Notably, this unit contained no pure motivational or
promotional Shorts and no market recaps; every clip had a chart on screen.

---

## What this unit did NOT find

Recording the negatives so nobody re-mines these 60 clips hoping for them:

- **No numeric wick-size threshold.** No ratio, percentage, tick count or bar count. The best
  available answer is the relative procedure in `wick-size-test`.
- **No kill-zone hours.** The phrase "kill zone" does not occur in any of the 60 transcripts.
  Session names (Asia, London, New York) are used freely with no hours attached.
- **No definition of "strong".** The word is used ("this strong close through", "Thursday closed
  strong") and never bounded.
- **No answer to which price of the opposing-candle series a CISD closes through.** Both Shorts
  that discuss CISD construction say only "closure through the series". The question remains open
  after this unit.
- **"Aggressive" is glossed but not quantified** — `OzugLBi0PVQ` pairs it with "fast, and large
  range", which is a direction for a detector but not a threshold. `EnAoorLVtoQ` uses
  "aggressively move lower" as a hard gate with no definition at all.
