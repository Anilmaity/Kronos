# Threshold fits — turning the corpus's adjectives into numbers

**Workstream 2 of the analysis phase.** Inputs: `meta/qualifier_calls.md` (56 curated
narrated calls, Part A) and `python/fit_thresholds.py` run on
`m3_scalper/xau_m1_3y.parquet` — 1,074,472 XAUUSD M1 bars, 2023-07-02 → 2026-07-23.

This document exists to unblock the concept library. Across `concepts/`, **109 concepts**
carry an ambiguity naming one of `displacement`/`aggressive`, `small wick`/`large wick`,
`shallow`, or `strong`; **81 of them are currently `underspecified` or `contested`**.
Its job is to give each term a default, a sweep range, and a percentile — with the
evidence graded honestly, so a backtester knows which knobs are load-bearing guesses.

---

## The headline correction to RESUME finding #5

RESUME.md records as a *settled negative* that "wick size has no number anywhere,
checked across 443 videos". **That is right about the ratio and wrong about the
threshold.** No wick-to-body *ratio* is ever spoken. But the number 0.5 is spoken
constantly, under a different name — *equilibrium*, *the upper half*, *50% of the
wick* — and one video states outright that this is what it is for:

> It is a mechanical way to measure wick size.
> — `3eVxTV_7L2U`

That sentence is the answer to the question the corpus was thought never to answer.
It is corroborated by `J_EeS2_2CAM` ("mechanically uh measures wick size that would
support expansion", which attributes the rule to TTrades) and, in TTrades' own voice,
by `Te9jUijPXZo` ("mark out the upper half of the candle for a bullish scenario") and
`LKNQDAdId4s` ("I'd want to see if price respects .5 of this Wick").

**But the number does not survive contact with the data as an operating point.** On
XAUUSD a 0.5-of-range cut admits **85% of all candles** (p85 on 15m/1h/4h, p87 on 1D).
It is a *ceiling* — the point past which a candle is definitively a reversal candle —
not a filter. The filter has to sit far tighter, and the corpus never says where.
So: the ceiling is found, the operating point is still fitted. That distinction runs
through every recommendation below.

## Evidence grades

| grade | meaning |
|---|---|
| **A** | a number is stated in the corpus, by ≥2 independent videos |
| **B** | a number is stated once, OR a comparative procedure is given and implemented literally |
| **C** | the corpus states a direction and a bound but no value; the value is fitted to XAUUSD outcomes |
| **D** | pure convention. The corpus supplies only the quantity; the number is chosen to land at a stated percentile |

## Recommended defaults — the whole answer in one table

| term | quantity | **default** | **sweep** | XAUUSD percentile of default | grade | concepts |
|---|---|---|---|---|---|--:|
| **small wick** / expansion candle | `opposing_run / abs(close-open)` ≤ cut | **1.0** | 0.6 – 1.6 | p66.4 (15m), p65.5 (1h), p65.0 (4h), p67.9 (1D) | **A** | 20 |
| — same, range parameterisation | `opposing_run / (high-low)` ≤ cut | **0.30** | 0.20 – 0.50 | p62.6 (15m), p62.5 (1h), p61.5 (4h), p66.9 (1D) | **C** (ceiling 0.5 is A) | 20 |
| — same, time axis | `time_share_to_extreme` ≤ cut | **0.25** | 0.10 – 0.50 | p66.3 (15m), p66.2 (1h), p59.7 (4h), p48.4 (1D) | **C** (ceiling 0.5 is B) | 20 |
| **large wick** / reversal candle | complement of the above | **> 1.0** | — | top p33 / p32 | **A** | 20 |
| **displacement** = **aggressive** (structural) | candle **closes** beyond the reference level | **hard gate, no knob** | — | — | **A** | 62 |
| **displacement** (magnitude, N-window) | `win_range/pre_range` ≥ r **and** `dist/pre_range` ≥ d, N candles from the break | **N=4, r=1.5, d=0.65** | N 2–8, r 1.3–2.0, d 0.5–1.0 | r at p45–p57, d at p47–p57 | **B** | 62 |
| **displacement** (FVG proxy) | a same-direction FVG inside the N-window | **advisory only** | — | fires on 61–77% of breaks | **A** (stated) / weak (measured) | 62 |
| **shallow** (retracement leg) | `pullback / impulse_leg` ≤ cut | **0.50** | 0.382 – 0.62 | p28 (15m), p33 (1h), p28 (4h), p38 (1D) of *continuation* legs | **B** | 23 |
| **shallow** (opposing run on a candle) | *alias of small wick* — do not give it a second threshold | see small wick | — | — | **A** | 23 |
| **strong** (closure) | `close_position = (close-low)/(high-low)` ≥ cut, mirrored for bearish | **0.85** | 0.75 – 0.95 | p67 (15m), p70 (1h/4h/1D) | **D** | 26 |
| **strong** (closure, time rider) | `time_share_to_extreme` ≤ 0.5 on the closing candle | **0.5** | 0.3 – 0.6 | p86.5 (15m), p84.8 (1h), p80.1 (4h), p62.6 (1D) | **B** | 26 |

Union of the four families: **109 concepts**, of which **81** are today
`underspecified`/`contested`. Per family, currently-blocked counts:
displacement+aggressive **46**, wick size **18**, shallow **19**, strong **18**.

---

## 1. Small wick / large wick — grade A on the quantity, C on the value

### What the corpus fixes for free

The **numerator is not ambiguous**, which the library previously recorded as an open
question (`wick-size-test`: "two different reference denominators are implied and never
reconciled"). It is stated outright:

> when I say opposing run, I mean from the opening price to that high
> — `SlWxhzhLo3A`

So the wick is **one-sided and directional**: open → extreme *against* the intended
direction. Not `high - low`, not the sum of both wicks. `fit_thresholds.candle_geometry`
computes exactly this. That single sentence resolves `wick-size-test`,
`small-wick-expansion-rule`, `aligning-expansion-candles` and
`small-wick-supports-expansion` to the same measurable object, and it also collapses
`shallow` (as applied to a candle) into the same object —

> Is this a shallow run? No, this is a large opposing run.
> — `aQoMSAaIXsg`

### The classification anchor: wick vs body, crossover 1.0

Three independent videos state it:

> A reversal candle has a large wick and a small body.
> — `ecTRHQrbYzI`

> the wick is larger than the body
> — `TND1aTpnq5c`

> Candles that support expansion will have a small wick and a large body
> — `Kf4c41_qO1s`

This is the only cut in the whole exercise that is both corpus-attested and behaves
consistently on data. Bucketing every candle by `opposing_run / body` at 1.0 and racing
a symmetric ±1 ATR(20) barrier from the close over the next 3 candles:

| tf | n small / large | barrier hit, small-wick | barrier hit, large-wick | separation |
|---|--:|--:|--:|--:|
| 15m | 47,636 / 24,154 | 50.3% | 50.1% | **+0.1pp** |
| 1h | 11,769 / 6,203 | 50.4% | 50.8% | **−0.4pp** |
| 4h | 3,161 / 1,701 | 53.8% | 49.8% | **+4.0pp** |
| 1D | 644 / 305 | 53.0% | 49.8% | **+3.2pp** |

The per-timeframe optimum lands at 0.8 (4h, +4.9pp) and 1.6 (1D, +5.9pp) — i.e. **1.0
is inside the plateau, not on a cliff**, which is the best thing that can be said about
a threshold you did not fit. **The edge is a higher-timeframe phenomenon**: 4h and 1D
carry it, 15m and 1h do not. Any 15m/1h use of the small-wick gate should be treated as
unsupported by this data.

### Why 0.5-of-range is a ceiling, not a filter

The EQ/upper-half formulation is more strongly attested (see the headline section) but
prices out much looser: `opposing_run/(high-low) ≤ 0.5` admits **84.6% / 84.9% / 84.9% /
87.1%** of 15m / 1h / 4h / 1D candles. A filter that passes six candles in seven is not
doing work. Barrier separation at 0.5 is **+0.5pp (15m), +0.5pp (1h), +3.2pp (4h),
−1.1pp (1D)** — and the 1D sign flip is the tell.

Tightening to **0.30** (p61.5–p66.9) recovers a consistent positive: +2.5pp on 1D, and
0.25 gives +5.2pp on 4h. **0.30 is a grade-C number**: the corpus supplies the quantity
and the ceiling; the value is fitted to XAUUSD.

The two 0.5s in the corpus — half the *candle* and half the *wick* — are not a
contradiction (the library's `half-wick-respect` records them as an unresolved
collision). One video resolves it as a branch:

> it was such a large wick on that candle I would use 50%
> — `07lOxv39LdY`

Default reference is 50% of the **candle**; you switch to 50% of the **wick** only when
the wick is large. One rule, one branch.

### The time axis — newly measurable, and it does not carry

`SlWxhzhLo3A` measures wick size on **two** axes, and only the range axis was previously
thought computable:

> We use almost half the time and quite a bit of range
> — `SlWxhzhLo3A` (a REJECT)

> It's going to use most of its time period and most of its range
> — `SlWxhzhLo3A`

Because this project holds M1, the time axis **is** computable: for every HTF candle,
the elapsed fraction of its period at which the opposing extreme printed
(`time_share_to_extreme`). Distribution is heavily left-skewed — median 0.067 (15m),
0.117 (1h), 0.167 (4h), 0.273 (1D) — so most candles do make their opposing extreme
early, and "almost half the time" really is unusual (p85 on 15m/1h).

Outcome fit is **weak and sign-unstable**: +0.4pp (15m), +1.1pp (1h), +3.9pp (4h),
**−2.7pp (1D)** at the 0.25 cut. **Recommendation: implement it, ship it default-off,
and treat any strategy that depends on it as unvalidated.** It is the axis with the
most corpus support and the least empirical support, which is worth knowing before
someone spends a week on it.

### A warning about two obvious outcome metrics

The two measures that most directly encode the corpus's own words —
"does the next candle extend beyond this candle's extreme" (continuation) and
"does the next candle trade back to this candle's open" (`5UsKZ7pZqvY`: *"when we have
a larger wick, my expectations is favoring back towards that daily open"*) — are
**geometrically confounded by the exact quantity being bucketed**. For a bullish candle
`range = opposing_run + body + far_wick`, so a large opposing run forces a small body,
which puts the close near the open (making "reverted" trivially easy) and near the high
(making "continued" trivially easy).

They therefore look spectacular and mean nothing: reverted separates by **−28pp to
−44pp** in the corpus's predicted direction at every cut on every timeframe. Anyone
re-deriving this will find those numbers first and should not report them as
confirmation. `fit_thresholds.outcomes` prints them flagged `[CONFOUNDED]` alongside
the scale-free barrier test for exactly this reason.

---

## 2. Displacement = aggressive — one term, two components

`b6yvRKf8haE` puts the two words in apposition — *"had an aggressive move or
displacement above"* — so the 37 `displacement`-blocked and 34 `aggressive`-blocked
concepts (union **62**) are gated by **one** threshold, not two. That halves the
problem before any measurement.

### Component (a): the structural gate — grade A, no knob

Every time the author adjudicates displacement on a chart, he resolves it as a
**close**:

> now we get some displacement a close over this previous high
> — `sgAnVR6RSDg`

> we can't get any displacement or a breakout of this range
> — `4WCiIyCiBrQ` (REJECT)

Implement as a hard gate: the candle must **close** beyond the reference level, not wick
through it. It has no parameter and it is unambiguous. It is also, by his own test,
satisfied by a one-tick close — which is precisely why component (b) is needed.

### Component (b): the magnitude gate — grade B

RESUME finding #7's comparative procedure is the only measurement procedure in the
corpus, and `fit_thresholds.displacement_windows` implements it literally: after a
short-term high/low (fractal 2/2) is broken, take N candles from the break and compute
the window's range and the distance travelled beyond the broken level.

> if you just take these four candles when we broke this High here
> — `1oco9lesido`

> in the same amount of time right we have a larger range
> — `1oco9lesido`

The corpus compares **one break to one other break on the same chart**. A single
reference is unstable, so `displacement_fire_rate` compares each break to the trailing
median of the previous 20 breaks — the same comparison, made repeatable:

| tf | N | breaks | fires (range **and** distance greater) | FVG inside window |
|---|--:|--:|--:|--:|
| 15m | 4 | 9,402 | 36.1% | 61.0% |
| 1h | 4 | 2,336 | 36.4% | 58.6% |
| 4h | 4 | 652 | 35.1% | 65.6% |
| 1D | 4 | 122 | 46.1% | 77.0% |

**The fire rate is stable at ~35% for N in 2–8 and across timeframes** (33.8%–46.1%
over the whole grid). That stability is the useful result: it means N is *not* a
sensitive knob, which retires the library's recorded worry in
`concepts/structure/displacement.yaml` that "whether the window is fixed at 4 or is
just 'the same amount of time' is not decidable".

To convert the relative test into an absolute one usable without a reference instance,
normalise both quantities by the pre-break N-candle range and cut at **1.5 / 0.65**.
That reproduces the relative procedure's fire rate closely — 30.6% / 37.2% / 39.9% /
35.2% on 15m / 1h / 4h / 1D — and sits at p45–p57 of each distribution. Sweep
r ∈ [1.3, 2.0], d ∈ [0.5, 1.0]; at 2.0/1.0 the fire rate falls to 14–22%.

### Component (c): the FVG proxy is real doctrine but a weak filter

Two independent narrated rejections turn on FVG absence:

> there's no displacement right there's no fair value gap or reach above
> — `FdRKBTz0Fps`

> no fair value gaps no aggression so there's no reason to be bullish
> — `UmLWRlXd_V8`

Measured on XAUUSD, a same-direction three-bar FVG appears inside the N=4 window on
**61.0% / 58.6% / 65.6% / 77.0%** of breaks, rising to 72–84% at N=8. So the test
rejects roughly a third of breaks at N=4 and only 15–28% at N=8. **It is not the
discriminator the phrasing implies**; the corpus's own evolution agrees, since
`_94CPMjWi9E` downgrades it from requirement to detection aid ("the easiest way to spot
it is just looking for fair value gaps"). Recommendation: **advisory, not gating** —
log it, do not filter on it, and never use it as the sole displacement test.

---

## 3. Shallow — grade B, and the corpus cuts at the median

Two distinct objects share this word and the corpus never distinguishes them:

1. **A candle's opposing run.** This is an alias of "small wick" (`aQoMSAaIXsg` uses
   "shallow run" and "large opposing run" as the two branches of one question). **Do not
   give it a separate threshold** — that would double-count a single parameter across
   `expansion-signature`, `wick-size-test` and `aggressive-expansion-no-retracement`.
2. **A counter-trend leg inside an expansion.**
   > very shallow moves against the trend and that is the signature of expansion
   > — `4Gm8p6O7Ebs`

Only (2) needs its own number. `fit_thresholds.retracement_depths` measures every
swing-to-swing pullback as a fraction of the preceding impulse leg, restricted to
**continuation** legs (depth < 1.0) — because "shallow moves against the trend"
presupposes the trend survived, and the all-legs population is half reversals:

| tf | n continuation legs | p25 | median | p75 | share ≤0.382 | share ≤0.5 |
|---|--:|--:|--:|--:|--:|--:|
| 15m | 8,238 | 0.47 | 0.64 | 0.81 | 14.4% | 29.3% |
| 1h | 1,983 | 0.43 | 0.62 | 0.80 | 18.2% | 33.2% |
| 4h | 602 | 0.46 | 0.65 | 0.79 | 15.6% | 28.4% |
| 1D | 109 | 0.44 | 0.62 | 0.78 | 15.6% | 37.6% |

**The finding that matters: the median continuation retracement on XAUUSD is 0.62–0.65,
which is the OTE lower boundary.** The library's `shallow-retracement` concept records
the rule that *reaching OTE invalidates the expansion read and is treated as a V-shape
reversal*. On this data that rule **discards half of all genuine continuations**. It may
still be right as a risk filter — a shallower entry is a better entry — but it must not
be sold as "identifying continuations". Anyone backtesting `expansion-signature`,
`continuation-signature` or `v-shape-reversal` should sweep this parameter first,
because it is the one with the largest gap between stated doctrine and base rate.

Default **0.50** (p28–p38 of continuation legs — genuinely selective, unlike the
0.5-of-range wick cut). Sweep 0.382 – 0.62.

---

## 4. Strong — grade D, and it is not a synonym for "small wick"

"Strong" is never given a test anywhere. What the corpus does supply is what it
*inherits*. The one narrated adjudication is:

> this move right here is what I would consider strong displacement
> — `gjoRPszj-Qk`

> You can see this is a pretty lopsided candle
> — `gjoRPszj-Qk`

Read that carefully: he accepts it **despite "a heavy wick"**, because there was a body
close. So **"strong" grades the CLOSE, not the wick**, and must not be aliased onto the
small-wick parameter. That corrects a natural but wrong simplification, and it matters
for `fractal-model-c4`, whose gate is "strong closure" in candle 3.

The matching quantity is already stated elsewhere:

> displacement is just large aggressive candles with closes in the high or the low
> — `5rbFskdmEmU`

i.e. `close_position = (close-low)/(high-low)` for a bullish candle, mirrored for
bearish. Distribution median is 0.72–0.755 and p90 is 0.933–0.959, so "in the high" is
not a rare event on XAUUSD. **0.85 is chosen because it sits at p67–p70 on all four
timeframes** — a stable top-third cut — and for no other reason. That is a grade-D
convention, stated as such. Sweep 0.75 – 0.95.

There is one genuine, and previously unrecorded, corpus test for closure quality, and
it is on the time axis:

> Just because it does have a closure over, doesn't mean it's a good closure
> — `vn1RYjhJUnQ`

> If it consolidates for half of the candle and then closes over
> — `vn1RYjhJUnQ`

Half the candle spent consolidating downgrades the close to "usually just a
consolidation". That is grade B — a stated bound with a number — and it is all the
corpus offers for `fractal-model-c4`, `bias-confirmation-tradeoff` and
`c2-confirmation-scaling`. Add it as a rider: `time_share_to_extreme ≤ 0.5`.

---

## What is corpus-anchored and what is convention

| corpus-anchored (do not re-litigate) | convention (yours to move) |
|---|---|
| the wick is the **opposing run**, open → extreme against the direction | the operating cut on `opposing_run/range` (0.30) |
| **wick vs body, crossover 1.0** separates reversal from expansion candles | the operating cut on `time_share_to_extreme` (0.25) |
| **0.5 of the range (EQ)** is the wick-size *ceiling*; 0.5 of the *wick* is its large-wick branch | `close_position ≥ 0.85` for "strong" (pure percentile pick) |
| displacement requires a **close** beyond the level | the absolute magnitude pair (1.5 / 0.65) |
| the **N-candle comparative** procedure, N=4 in the worked example | which N (empirically it barely matters) |
| **displacement == aggressive** (one term) | — |
| "shallow" on a candle **is** "small wick" (one parameter) | the leg-level shallow cut (0.50) |
| "strong" grades the **close**, not the wick | — |
| a closure preceded by half a candle of consolidation is **not** a good closure | — |

## What this exercise could not do, and why

**Zero of the 56 curated calls can be tied to a dated bar.** A transcript names no
instrument, no date and no price; the author says "this candle" while pointing at a
screen that is not in the corpus. So the supervised fit that Part A was meant to enable
— find the ratio that reproduces his labels — **is not available**, and nothing above
claims it. What the labels did deliver is the thing that was actually missing: **which
quantity to measure**, on which denominator, with the numerator pinned by his own words.
That was worth the mining even though it did not produce the fit.

Three further caveats a backtester needs:

- **One instrument, three years.** Every percentile here is XAUUSD 2023-07 → 2026-07.
  The corpus is taught on NQ/ES/YM index futures. Gold's wick geometry is not
  guaranteed to match, and the wick distributions above should be recomputed before
  any of these defaults is used on another instrument.
- **The small-wick edge is timeframe-conditional.** +3 to +4pp on 4h/1D, ~0 on 15m/1h.
  A 15m model that gates on wick size is trading a filter this data does not support.
- **The barrier test is a directional-persistence probe, not a strategy.** It says a
  small-wick 4h candle is ~4pp more likely to reach +1 ATR before −1 ATR. At a 50%
  base rate that is a real but thin effect, and it is measured with no costs, no
  entry logic and no multiple-testing correction across the ~60 cuts swept here.
  Treat every number in the sweep tables as a hypothesis to re-test out-of-sample, not
  as a result. RESUME next-step #1 (the C2 small-wick asymmetry, properly costed) is
  still the right first backtest.

## Reproducing

```bash
cd ClaudeTradingRD/research
../.venv/Scripts/python.exe python/mine_qualifiers.py     # Part A -> meta/qualifier_calls.{md,json}
../.venv/Scripts/python.exe python/fit_thresholds.py      # Part B -> stdout (this doc's numbers)
../.venv/Scripts/python.exe python/fit_thresholds.py --quick   # 4h/1D only
```

`mine_qualifiers.py` refuses to write if any curated quote is over 15 words or is not
verbatim in its transcript, which is the same rule `python/validate_concepts.py`
enforces on `concepts/`. Both scripts are offline.
