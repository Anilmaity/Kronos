# Pre-registration — the conjunction test

**Phase 3, workstream B. Written 2026-08-25, BEFORE any conjunction result exists.**
No conjunction backtest has been run, and none is run by this document or by
`python/estimate_conjunction_power.py`. What follows is the specification of a valid
test, fixed in advance, plus a power analysis that says in advance which parts of it
this dataset can and cannot answer.

**Why this document exists.** Phase 2 refuted the project's headline claim by finding a
geometric confound (`meta/backtest_c2_wick.md`), and separately caught a units bug that
had survived self-review (`RESUME.md`, phase-2 traps). The conjunction that follows has
at least nine live knobs — POI on/off, CISD level rule, CISD series length, CISD speed,
C3 closure reference, session window, wick threshold, displacement threshold, target
rule, stop rule and timeframe pairing. Sweeping them and reporting the best cell is
guaranteed to manufacture a false positive: at 4 stacks × 6 rungs × 4 targets × 4 costs
× 2 CISD readings there are over 1,500 reportable cells, and roughly 77 of them will
clear p=0.05 by chance alone. This document fixes one configuration as the hypothesis
and demotes everything else to declared, corrected, non-verdict-bearing secondaries.

**The single most important thing in this file is §3.** Measured with the real gate
modules on the largest trustworthy sample that exists for this instrument — **2016-01-01
→ 2026-07-23, 10.55 years, 3,687,209 M1 bars** — the conjunction as taught, on his own
favourite timeframe stack, produces **722 events** and can only detect a **5.5 percentage
point** win-rate advantage, against a plausible true effect of **3–5 points**. **It
resolves the top of the plausible band and misses the middle of it.** A null result will
be genuinely ambiguous, and saying so now converts a future "we tested it and found
nothing" into a statement about what this dataset can and cannot decide.

**But one on-method configuration is fully answerable, and it was designated the powered
comparison before its count was known: the 5m playbook stack** (`ttfm-hourly-5m-playbook`,
the corpus's only written checklist) yields **2,234 events and a 3.1pp floor** on the same
span — below the bottom of the plausible band. **The verdict should be read there.** The
honest framing is that **the method is testable one rung below the timeframe he most
recommends.**

**More gold history will not close the 15m stack's gap, because there is no more.** The raw fetch
reaches 2010, but gold traded a **different session calendar before October 2015** — NY
hour 17 goes from ~2–3k bars a year to exactly zero and stays there — and every gate here
is session- or daily-calendar-dependent. On that data the gates do not fail; they quietly
compute different objects. Pre-2016 is admissible as regime evidence only. The remaining
route to a 3–4pp floor is **more instruments**, not more gold (§3.7.3).

> **A hard limit that bounds every conclusion this test can reach: there is no sustained
> bear market in the certified span.** The only real gold bear market in 16.5 years is
> 2013 (−28%), and it sits on the wrong side of the calendar break. The best available
> non-bull regimes are the 2016–2018 range and the 2021–2022 flat years. **No result from
> this test may be described as having been validated against a sustained gold
> downtrend.** See §3.7.2(a).

**Two things are fixed here that a reader will otherwise get wrong.** First, the
comparator for "does the conjunction work" is **rung 0 of the ladder, not zero** — bare
CISD already sits above its own matched control at 1h and 4h (§2.5), so a profitable
full model proves nothing on its own. Second, the **matched control's matching
dimensions are locked in §4.3**, including a ±30-day entry window; getting that wrong
inflated a rung-0 differential by 38% at 4h, and it would inflate the ladder's rungs
*unequally*.

**The ladder runs on the event layer.** Intersecting the gates at the day layer leaves
**9 qualifying days in three years** — and the same 9 in ten years. §2.0 explains why,
and why `no_fade` and day-level `POI` are resolution artefacts rather than weak gates.

---

## 0. Adopted without re-derivation

These are settled by earlier workstreams and are **not** knobs. Re-deriving them is out
of scope and re-sweeping them would inflate the multiple-testing count for no gain.

| item | value | source |
|---|---|---|
| timezone | `America/New_York`, **DST-aware** | spec §1.4; `session_window_fit.md` §5 (venue break resumes 18:00 NY on 99.8% of 605 occasions) |
| 4H opening grid | **forex**: 17/21/01/09 NY | spec §1.4; `session_window_fit.md` §6 (0% of forex-grid candles straddle the daily break vs 16.5% futures) |
| small-wick / expansion cut | `opposing_run / abs(close-open) <= 1.0`, grade A | `threshold_fits.md` §1 |
| opposing-run numerator | one-sided, **open → extreme against the intended direction** | `opposing-run`, `wick-size-test`; `threshold_fits.md` §1 |
| displacement, structural | candle **closes** beyond the reference level. Hard gate, no knob | `threshold_fits.md` §2a |
| displacement, magnitude | `N=4`, `range_ratio >= 1.5`, `dist_ratio >= 0.65` | `threshold_fits.md` §2b |
| `displacement` ≡ `aggressive` | **one term, one threshold**, 62 concepts | `b6yvRKf8haE`; `threshold_fits.md` §2 |
| FVG-in-window proxy | **advisory only**, logged, never gating (fires on 61–77% of breaks) | `threshold_fits.md` §2c |
| session filter | **a knob, not a default** — see §1.14 | `session_window_fit.md`: NY AM gating = −0.057R, t = −3.11 |
| data | **certified span**: `xau_m1_full.parquet` 2016-01-01 → 2026-07-23, 3,687,209 M1 bars, 10.55 years | `meta/xau_history_audit.md` |
| SMT correlate | `xag_h1_full.parquet` — 100,168 H1 bars, 2010-01-03 → 2026-07-23; r = 0.762 on the certified span | §2.1a |
| inverted proxy | `eur_h1_full.parquet` — **never to be called DXY**; r = 0.35 / 0.40 | §2.1a |

One caveat carried forward and never to be forgotten in the write-up: **the corpus is
taught on NQ/ES/YM**, and `excluded-tooling` says futures only, no CFDs, no scalping.
Gold is on his instrument list; a 1-minute entry timeframe is not. Every number below is
one instrument.

---

## 1. The locked primary configuration — "the method as taught"

This is the primary hypothesis. **It is fixed as of this document and may not be changed
once any conjunction result is seen.** Every parameter has a value and a citation. Where
the spec genuinely preserves two readings, the better-documented one is primary and the
other is named here as the pre-declared secondary — those two secondaries are the only
alternative *readings* permitted to be reported, and neither can change the verdict
(§4.7, §5).

### 1.1 Instrument, data, clock

XAUUSD M1 from **`m3_scalper/xau_m1_full.parquet`, restricted to the certified span
2016-01-01 → 2026-07-23** (§3.7). Bars built with `bars.resample`
(`label="left"`, empty buckets dropped, never forward-filled). Clock
`America/New_York` with DST. 4H grid = forex (17/21/01/09 NY).

### 1.2 The timeframe stack

**Primary: entry 15m / structure 4H / bias 1D** — the stack the corpus names his
favourite and A+ setup (`ttfm-favorite-daily-4h-15m`, spec §1.3), and a legal
three-slot chain under spec §1.2 rule 2 (entry → its paired HTF → that one's paired
HTF). The pairing table (spec §1.2, `timeframe-alignment-pairs`) is used as a lookup;
no rule generates it and none is invented.

Three further stacks are pre-declared, in the same table, as the secondary family:

| stack | entry | structure | bias | corpus name |
|---|---|---|---|---|
| **primary** | 15m | 4H | 1D | favourite / A+ (`ttfm-favorite-daily-4h-15m`) |
| powered secondary | 5m | 1H | 1D | playbook (`ttfm-hourly-5m-playbook`) — the corpus's only written checklist |
| power-ceiling reference | 1m | 15m | 4H | scalping model (`ttfm-scalping-model`) — **off-method**, `excluded-tooling` says no scalping; reported for its event count only |
| swing | 1H | 1D | 1W | swing model (`ttfm-swing-trading-model`) |

§3 shows the primary stack is underpowered and the 5m playbook stack is the highest-n
stack the corpus states as a full playbook. That is why the playbook stack is
pre-designated the **primary powered comparison** — declared here, before results, so
that reporting it later is not a post-hoc rescue.

### 1.3 Order of operations

The gate order is the corpus's own and is not rearrangeable (spec §2.1,
`top-down-analysis-procedure`, `overtrading-gate`, `htf-poi-gate-before-ltf`):

1. bias from the bias timeframe's closure;
2. profile must support the bias — *if it does not, no entry even though the bias stands*;
3. POI must be tagged before dropping timeframes;
4. structure-timeframe closure at that POI;
5. entry-timeframe CISD;
6. entry.

### 1.4 Bias (step 1)

The previous-candle engine (spec §2.3, `daily-bias-framework`, `next-day-model`,
`three-candle-outcomes`), evaluated on the **last closed** bias-timeframe candle:

- **continuation closure** — took out the prior candle's extreme and closed *outside* → bias = same direction;
- **reversal closure** — took out the prior extreme and closed back *inside* → bias = opposite direction;
- **both sides taken** → no bias → **no trade**;
- **inside bar** → no bias → **no trade**.

The spec says an inside bar means "default to trend continuation" (`daily-bias-framework`),
which requires a trend read the spec does not mechanise (`basic-trend-structure` vs
`trend-by-previous-day-extremes` vs `trend-as-aggressive-move-to-objective`, spec §2.3
**[GAP]**). **Primary: inside bar = no trade** (the conservative reading, and the one
that cannot be accused of borrowing a trend definition). Declared secondary:
inside bar inherits the previous non-zero bias.

A one-sided bias is mandatory: *"if there is no bias, do not go down to the hourly"*
(`ttfm-hourly-5m-playbook`, spec §1.3).

### 1.5 Profile support (step 2)

Spec §2.5. The only branch that is mechanically decidable from price today is the
**Seek & Destroy stand-aside**: London (02:00–05:00 NY) takes **both** Asia
(20:00–00:00 NY) extremes (`seek-and-destroy-profile`, `daily-profile-session-windows`).
Primary: **exclude those days**.

The rest of "the profile must support the bias" — discriminating London Reversal from
New York Reversal on the question *did London reach a relevant HTF PD array?*
(`relevant-htf-pd-array-test`) — turns on "relevant", which the corpus never defines
(spec §2.5 **[GAP]**). It is **not** implemented in the primary, and this is recorded as
a known incompleteness rather than silently filled from generic ICT. Any later profile
classifier is a new gate and re-enters the ladder as such.

### 1.6 The POI gate (step 3) — ON in the primary

**Without a POI, no candle closure and no CISD is valid** (`point-of-interest`, spec
§4.1; restated inside the CISD definition itself, spec §4.2 point 2).

Enumeration, in the corpus's own search order (spec §4.1):
1. is there a **fair value gap** traded into?
2. if not, is there a **swing high / low** to be taken out?
3. only if neither, use the **CISD level**, and additionally require 50% of the bodies
   of that opposing series to hold.
4. If **both** an FVG and a sweepable swing exist, **both** must be tagged.

**Resolution: the POI gate is evaluated per EVENT, on the entry timeframe, never per
day.** At day resolution it removes 0 days of 788 and 1 of 2,724, because a whole day of
hourly bars almost always contains some FVG or sweepable swing — the gate is asking a
question whose answer is always yes. Per event it retains **81.4%** on 15m and **80.4%**
on 1h (§2.0). POI timeframe: the structure timeframe or above
(`poi-timeframe-selection`, spec §1.2 rule 3), with the entry timeframe permitted as a
fallback. Density rule
(`poi-density-by-timeframe`): a POI is *required* on the hourly-and-below and merely
preferred on the 4-hour; the primary requires it everywhere, which is the stricter read.

FVG definition: three candles, wicks of 1 and 3 not overlapping, measured on wicks not
bodies (`fair-value-gap`, spec §3.9). Adjacent gaps are one gap.

**Why this is a switch in the ladder and not a hard-wired precondition.**
`external_crossref.md` §1c records that outside opinion is split — one implemented
detector requires the sweep, another states explicitly that it is a quality filter and
not definitional. The corpus is right about *the channel*; it is stricter than the
mainstream. So the primary has it ON, and rung R0 of the ladder has it OFF, and every
downstream statistic is reported both ways. It is the single biggest frequency lever in
the CISD detector.

### 1.7 The structure-timeframe closure (step 4)

A **C2** or **C3** closure on the structure timeframe, at a POI, in the bias direction
(spec §3.5 `indicator-print-conditions`: a "model" exists only when a HTF C2 or C3
closure at a POI is paired with a CISD on the aligned lower timeframe).

**C2** (`fractal-model-c2`, spec §3.2):
- bearish: `high[i] > high[i-1] AND close[i] < high[i-1]`
- bullish: `low[i] < low[i-1] AND close[i] > low[i-1]`
- a sweep without the close back inside is not a C2.

**C3 closure reference — [P], primary declared.**

> **Primary: Reading A — C3 closes beyond the OPENING PRICE of C2.**
> **Pre-declared secondary: Reading B — C3 closes beyond C2's EXTREME.**

Reading A is chosen because it has the better-documented support: it comes from the
unit's *dedicated* Shorts on C3 and is stated in two separate videos
(`vn1RYjhJUnQ` "the opening price in candle 2", `SF61vCsBl1A` "below the body of candle
two"), whereas Reading B is a single sibling unit; and because Reading B is strictly
stronger and therefore selects a subset of Reading A's bars, so reporting A as primary
with B as secondary nests cleanly (spec §3.3). Where the two Reading-A phrasings differ —
"opening price" vs "body" coincide only when C2 closed in the sweep direction — the
primary takes **the opening price of C2**, the more literal statement. A C3 closure
exists **only when C2 failed to close** (spec §3.3).

Both readings must be computed and the **disagreement rate reported**, as the spec
standing decision requires.

### 1.8 CISD (step 5) — the definition

Spec §4.2, `cisd`:

> displacement and a **CLOSE beyond THE OPENING PRICE of the opposing-close candle, or
> series of opposing-close candles, that ran into an important level**.

Explicitly **not** a close beyond a swing high or low — that is the market structure
shift, a separate and later event (`market-structure-shift`). CISD and MSS are built as
two detectors with separate statistics (`external_crossref.md` §1a). **The primary uses
CISD, not MSS.**

Procedure (spec §4.2): locate the extreme that engaged the POI → identify the contiguous
run of opposing-close candles that produced it → mark the level → require a close
through it → if price makes a new extreme before closing through, discard and re-derive.

**Level of the series — [P], primary declared.**

> **Primary: the OPEN OF THE FIRST CANDLE of the run** (`cisd.level_rule="series_open"`).
> **Pre-declared secondary: the HIGHEST (bullish: LOWEST) OPEN of the series** —
> `level_rule="series_max_open"`, **which does not exist in `python/detectors/cisd.py`
> today and must be added before the test runs.**

First-candle-open is primary because it is stated explicitly twice in one video and is
independently the convention of two publicly built detectors (`external_crossref.md`
§1b). The run's **extreme** reading is **ruled out** by the corpus — *"Mark out the
opening price in that series"* makes the level an open, not the swept extreme — so
`level_rule="series_extreme"`, which the existing detector offers, **is not a legal
reading of this method** and is demoted to a diagnostic. `series_close` is attested
nowhere outside the corpus and is likewise a diagnostic only.

This parameter is not cosmetic: Jaccard agreement between `series_open` and
`series_extreme` is 0.56–0.59, and between `series_open` and `series_close` 0.22–0.29
(`meta/cisd_reading_comparison.md`). These are different trading systems wearing one
name, which is exactly why one is locked and the other is declared.

**Scope of the confirming CISD — [P], and the largest single lever in the model.**
Spec §2.4 step 3 states both ways whether the confirming lower-timeframe CISD must sit
inside the daily candle's **wick** specifically, or anywhere inside its **range**.

> **Primary: `cisd_scope = "range"`. Pre-declared secondary: `"wick"`.**

`range` is primary because it is the weaker precondition and therefore the one that does
not silently import an extra requirement the corpus states only ambiguously; `wick` is
the strictly stronger reading and nests inside it. Measured cost on the certified span:
biased days **862 → 311 (2.77×)**, and the day-level stack **153 → 36 (4.25×)**. That is
larger than the CISD level rule, `max_wait` and `min_series` **combined**, so it gets the
same both-ways reporting treatment as the level rule and neither reading may carry the
verdict alone.

**Series length — [P].** Primary `min_series = 1` (the dedicated model video accepts a
single candle). Declared secondary `min_series = 2` (a Sunday-session answer says he
never uses one candle; `opposing-candle` says a series is always used because a series
of same-direction closes is one candle a timeframe up). Measured cost of the secondary:
it removes **48–50%** of CISDs on every timeframe (§3.1), so it is a first-order
frequency lever and must be reported, not buried.

**Speed.** The closure should arrive within **1 to 3 candles** of the reach into the
level — the corpus's only candle-count threshold for "swift", stated as a preference:
*"I prefer 1, 2, maybe three"* (`v-shape-reversal-speed`, spec §4.2). **Primary
`max_wait = 3`.** Declared secondary `max_wait = 40` (the detector's current default,
i.e. effectively unbounded). Longer ⇒ reclassify as consolidation, not a CISD. Measured
cost: `max_wait=3` removes ~38% of events versus 40 (§3.1).

Swing definition for the extreme: 3-bar fractal with `left=2, right=2`
(`primitives.swing_points`), confirmation lag two bars, honoured. The corpus's
**relevant-swing filter is a [GAP]** (spec §1.1: "no mechanical rule", judged "from
experience and discernment") and is therefore **absent from the primary**. This is the
largest single gap between the primary configuration and the method as practised, and it
is stated here rather than papered over.

**One CISD per day** (`one-cisd-per-day`, spec §2.4) is a stated rule and is applied as a
**declared secondary** de-duplication, not in the primary — the primary measures
expectancy per event and a per-day cap changes the estimand.

### 1.9 Timeframe alignment

Spec §3.5, `timeframe-alignment`, `aligning-expansion-candles`: the bias timeframe and
the structure timeframe must support the same direction at the same time; minimum two
aligned expansion candles. Plus the wick gate: **if any layer has a large wick or opens
against the intended direction, do not trade that layer** (`aligning-expansion-candles`).

Primary implementation: bias-TF closure direction == structure-TF closure direction ==
trade direction, **and** the last closed structure-TF candle has
`opposing_run / abs(close-open) <= 1.0` in the trade direction.

### 1.10 Entry

**Doctrine is that you never enter on the reversal itself, always on the continuation
that follows it** (`continuation-over-reversal`, spec §4.5). The corpus also states the
CISD as the minimum acceptable confirmation rung (spec §4.4 rung 3).

> **Primary: entry at market on the close of the CISD confirmation bar**
> (`market-order-entry`, spec §4.8; confirmation ladder rung 3, spec §4.4).
> **Pre-declared primary-variant: the continuation entry** — after the CISD, require
> (a) a retrace into an FVG **or** (b) a sweep of a low/high, then the close through the
> opposing-candle series that went into that level (`continuation-order-block`, spec
> §4.5). If neither trigger occurs the move is missed and no trade is recorded.

The CISD-close variant is primary for one reason and it is stated in advance: it is
mechanically defined today, whereas the continuation variant needs a detector that does
not exist and has an unknown fill rate. **The continuation variant is strictly rarer**,
so if the CISD-close variant is underpowered — which §3 says it is — the method-faithful
variant is worse. That direction of the inequality is what makes the substitution
defensible.

Timing filter (`continuation-timing`, spec §4.5): frame entries while the higher-timeframe
wick is forming. **Not in the primary** — "already expanded" needs the ADR budget, which
is an eyeballed quantity with no lookback, no averaging method and no statistic
(`average-daily-range`, spec §5.2 **[GAP]**). Declared as an unimplementable gate.

### 1.11 Stop

**The protected swing** (`stop-loss-placement`, spec §5.1) — for a CISD entry that is
the extreme the CISD protects (`protected-swing`, spec §3.8), i.e.
`cisd_events.protected_swing`. `R = abs(entry - stop)`.

Declared secondary: the **body extreme** of the opposing-candle series (the
mean-threshold modification, spec §5.1). Not primary, because the spec presents it as a
modification made when R is unsatisfying, which is a discretionary branch.

### 1.12 Target

**Primary: 2R fixed.** 2R is stated as the floor in three separate videos and is the
*fixed* target in the internal/external model (`risk-reward-minimum`,
`internal-external-liquidity-model`, spec §5.3). He states the matching break-even
arithmetic himself: a 2R strategy is profitable above a **34%** win rate
(`realistic-r-expectations`).

Pre-declared secondary targets, all reported, none verdict-bearing: **1R**, **3R**, and
**structural** = the reference higher timeframe's previous candle's unswept extreme
(`previous-period-high-low`, spec §5.2). Phase 2 found `structural` — the model's own
implied target — is the only target that loses money in every period on every timeframe,
so it must be reported and must not be quietly dropped.

The **−2 / −2.5 standard-deviation projection** of the manipulation leg
(`standard-deviation-projection`) is the corpus's other stated target and is **not** in
the primary, because it needs the manipulation leg's anchor, which is the same
relevant-swing [GAP] as §1.8.

### 1.13 Hold and time exit

**Primary: max hold = 10 entry-timeframe periods**, unresolved trades exit at the last
M1 close in the window. This is chosen for exact comparability with
`meta/backtest_c2_wick.md`, not from the corpus.

Declared secondary: **hold to the close of the higher-timeframe expansion candle the
trade is running inside** (`time-based-exit`, `time-based-exit-htf-close`, spec §5.5) —
the corpus's own rule. Its precedence against a price target is never stated **[P]**;
the secondary takes the target first.

No break-even, no partials, no trailing in the primary. All three are **contested inside
the corpus** (spec §5.5: break-even argued against for swing and for on scalps; partials
contradicted by a guest; the trailing rule called "a little bit too tight" by its own
author). A contested management overlay cannot be part of a primary hypothesis.

### 1.14 Session — a knob, and OFF in the primary

**No session filter is applied in the primary configuration.** This is a decision with a
number behind it: gating to the corpus's own forex NY AM window returns **−0.057R
versus the rest of the day, t = −3.11 on 7,835 events** — the only one of twelve windows
to survive multiple-testing correction, and it is negative (`session_window_fit.md`,
spec §6). Applying it as a default would degrade the book for a reason unrelated to the
conjunction and would confound the test.

The session gate therefore enters **only** as rung R5 of the ablation ladder and as a
declared knob:

- default if swept: **10:00–12:00 NY** (the corpus's own forex London Close window,
  pre-specified rather than fitted, and the best-scoring of twelve at −0.004R with
  t = +1.46, i.e. not significant);
- conservative superset: **08:30–12:00** (the widest attested quote);
- sweep: `start` ∈ 08:30–10:30, `end` ∈ 11:00–13:00.

The corpus's own framing is the interpretation to hold: *for gold, time of day buys
opportunity, not accuracy*. The 08:00–11:59 block carries 29.9% of daily-extreme
formations on 17.4% of the clock (1.72×) while hour 08 is the day's **worst** at
−0.109R. **The best time to have a level is not the best time to take an entry.**

Two session traps are pre-registered as known and must not be rediscovered as findings:
the **18:00 NY hour is a market-reopen artefact** (first 15 minutes after a halt are
6.02× over-represented among daily extremes across 788 halts), and the **Asian window is
externally contested and finds nothing here**.

### 1.15 Costs

**PRIMARY: `0.04R` proportional. [AMENDED — §8, A4.]** Flat USD/oz levels
(**0.0, 0.2, 0.5**) are retained as diagnostics and for comparability with
`meta/backtest_c2_wick.md` §4, but they are no longer the base case.

The reason is §3.7.2(b): the certified span runs from ~$1,100 gold to ~$5,500, so a flat
0.2 USD/oz round trip is a **5× different relative tax** at the two ends of the sample.
It is the *only* absolute-price quantity in the whole locked configuration — every
threshold is a scale-free ratio — so leaving it absolute would make the cost model the
one component that silently means something different in 2016 than in 2026. On the
3-year file this was a 3× effect and was already flagged; over a decade it disqualifies
it as a base case.

Note the corpus's own execution assumption is **futures**, where he argues a market
order on a liquid index future fills at the ask with no broker-widened spread
(`futures-vs-forex-differences`, spec §1.5). XAUUSD spot does not behave that way. The
0.5 column is the honest one for a retail gold account.

### 1.16 Summary of the locked primary

| parameter | primary value | pre-declared secondary | source |
|---|---|---|---|
| instrument / data | XAUUSD M1, **certified 2016-01-01 → 2026-07-23, 10.55 y** | 3-year file, for phase-2 continuity | `meta/xau_history_audit.md` |
| timezone | `America/New_York` DST | none — settled | spec §1.4 |
| 4H grid | forex 17/21/01/09 NY | futures grid | spec §1.4 |
| stack | 15m / 4H / 1D | 5m/1H/1D, 1m/15m/4H, 1H/1D/1W | spec §1.3 |
| bias engine | previous-candle closure on 1D | inside-bar inherits prior bias | spec §2.3 |
| no-bias states | both-sides & inside bar → no trade | — | spec §2.3 |
| profile | exclude Seek & Destroy days | full profile classifier (unbuilt) | spec §2.5 |
| POI gate | **ON**; FVG → swing → CISD level; both if both exist | OFF (= ladder R0) | spec §4.1 |
| POI timeframe | structure TF and above; entry TF fallback | structure TF only | spec §1.2 r3 |
| structure closure | C2 or C3 at a POI, in the bias direction | — | spec §3.2, §3.5 |
| **C3 closure reference** | **C2's opening price (Reading A)** | **C2's extreme (Reading B)** | spec §3.3 [P] |
| **CISD level rule** | **open of the FIRST candle of the run** | **highest/lowest open of the series** | spec §4.2 [P] |
| CISD series length | `min_series = 1` | `min_series = 2` | spec §4.2 [P] |
| CISD speed | `max_wait = 3` candles | `max_wait = 40` | `v-shape-reversal-speed` |
| swing fractal | `left=2, right=2` | — | `primitives.swing_points` |
| relevant-swing filter | **absent** — corpus [GAP] | — | spec §1.1 |
| alignment | bias TF == structure TF == direction, structure wick `run/body <= 1.0` | — | spec §3.5, `threshold_fits.md` §1 |
| entry | market at the CISD confirm close | continuation order block | spec §4.4 r3, §4.5 |
| stop | protected swing (the CISD extreme) | body extreme of the series | spec §5.1 |
| target | **2R fixed** | 1R, 3R, structural | spec §5.3, §5.2 |
| max hold | 10 entry-TF periods | HTF expansion-candle close | phase-2 parity; spec §5.5 |
| management | none (no BE, no partials, no trail) | each, separately | spec §5.5 (all contested) |
| session | **OFF** (knob K1) | 10:00–12:00 NY, superset 08:30–12:00, swept | `session_window_fit.md` |
| **SMT** | **OFF** (knob K2) | XAG correlate 2010+, r = 0.762; 252 events, 9.3pp | §2.1a |
| **`cisd_scope`** | **`range`** | **`wick`** — 2.77× fewer biased days | spec §2.4 [P], §3.1 |
| cost | **0.04R proportional** | 0.0 / 0.2 / 0.5 USD/oz flat (diagnostic) | §3.7.2(b) |
| exit resolution | **M1, stop-first same-bar tie-break** | none — mandatory, see §4.2 | phase-2 §6c |
| IS / OOS boundary | 2025-07-02 | PRE block, §4.4 | phase-2 parity |
| robustness exclusion | 2019-02 → 2020-02 re-run **required** | — | §3.7.2(c) |

---

## 2. The ablation ladder

This is the actual scientific question. Not *"is the conjunction profitable"* — a
profitable conjunction whose profit comes entirely from one gate is not evidence for the
conjunction. The question is **does the conjunction add anything over its parts?**

### 2.0 The ladder runs on the EVENT layer, not the day layer [AMENDED — §8, A3]

The first version intersected the gates at the **day** layer. With the real
`detectors.bias` module that is not a test, it is an anecdote generator. Measured
cascade, 788 trading days on the legacy 3-year file — independently reproduced by this
workstream and by the coordinator, to the day:

| stage | days kept | % |
|---|---:|---:|
| all days | 788 | 100% |
| + bias | 212 | 26.9% |
| + profile | 94 | 11.9% |
| + alignment | 31 | 3.9% |
| + no_fade | 31 | 3.9% |
| + POI | 31 | 3.9% |
| + SMT | **9** | **1.1%** |

**Nine qualifying days in three years, about three per year.** On the certified 10.55-year
span it is 2,724 → 862 → 394 → 153 → 153 → 152 → **54** — about **5 per year**, and no
better in rate than the 3-year figure. No quantity of history repairs a day-level
conjunction.

**Therefore the unit of analysis is a CISD event on the entry timeframe, and the daily
gates are joined onto it as context columns.** A day that passes the bias gate can carry
several qualifying events; the day layer collapsed all of them to one bit. The join is
lookahead-free by two independent guards, both of which caught real bugs in this
workstream (§4.1a).

Two gates behave differently at the two layers, and the distinction is structural rather
than empirical:

- **`no_fade` fires on 100% of days and is definitionally redundant**, not empirically
  weak. A confirmed daily bias already entails a daily candle closing that way, so the
  gate can never fail once `gate_bias` has passed. **It is removed as a ladder rung** and
  retained only as an assertion that the bias module is self-consistent.
- **`POI` removes 0 days of 788, and 1 day of 2,724.** That is a resolution artefact:
  a full day of hourly bars almost always contains *some* FVG or sweepable swing, so at
  day resolution the gate is asking a question whose answer is always yes. **POI is not
  weak — it was being applied at the wrong resolution.** At the event layer it bites
  properly and stably: **81.4%** pass on 15m and **80.4%** on 1h across the certified
  span (82.8% and 80.3% at the detector's default `max_wait`, per the coordinator).
  That is the number the ladder uses.

### 2.1 The forward ladder

Each rung adds exactly one gate, in the corpus's own order of operations (§1.3). The
primary configuration is **R4**. Everything labelled **K** is a pre-declared knob, not
part of the primary, and each carries its own power line.

| rung | gate added | layer | what it operationalises |
|---|---|---|---|
| **R0** | bare CISD on the entry TF | event | the primitive alone |
| **R1** | **+ POI gate** | **event** | `point-of-interest`, spec §4.1 |
| **R2** | **+ HTF bias** (direction must agree) | day → event | spec §2.3, §2.4 |
| **R3** | **+ profile support** | day → event | spec §2.5 |
| **R4** | **+ timeframe alignment** | day → event | spec §3.5 |
| K1 | + session 10:00–12:00 NY | event | knob — `session_window_fit.md` |
| K2 | + SMT | day → event | knob — see §2.1a |
| K3 | + session + SMT | — | knob, reported for completeness |

#### 2.1a SMT is demoted from the primary to a declared knob [AMENDED — §8, A3]

SMT alone takes the day-level stack from 153 days to 54 on the certified span, and the
event-layer primary stack's R4 from **722 events to 252** — a 9.3pp floor against a
3–5pp plausible effect. Its best-powered line anywhere in this design is the 5m playbook
stack at **792 events, 5.2pp**, which still resolves only the top of the band. Including
it in the primary would therefore leave the primary hypothesis undecidable on the
timeframe it is stated for, violating this document's own rule that the primary must be
answerable (§5.3). **It is therefore a pre-declared secondary knob with its own power
line.**

This is a demotion in the test design, not a claim that SMT is unimportant — the corpus
makes it a substitute for the sweep in three separate places (`smt-swing-point-substitute`,
spec §3.8, §4.5). It is a statement that its event count cannot support inference here.

**The correlate is real and it is stable across a decade** [AMENDED — §8, A5]:

| | 3-year window | **certified span (2016–2026)** |
|---|---:|---:|
| XAG H1 bars | 18,107 | **62,401** |
| shared with gold H1 | 99.99% | **99.8%** (62,265) |
| H1 return correlation | 0.766 | **0.762** |
| daily return correlation | 0.796 | — |

The near-identical correlation ten years apart is worth stating in its own right: **the
SMT premise does not rest on a single regime the way rung 0 appears to.** Source:
`m3_scalper/xag_h1_full.parquet` (100,168 H1 bars, 2010-01-03 → 2026-07-23).

**DXY does not exist on OANDA.** The account's full 123-instrument list contains no
index-like entries. `EUR_USD` is carried as an **explicitly-labelled inverted proxy** at
correlation **0.35 / 0.40** (`eur_h1_full.parquet`), and **must never be described as
DXY** in any output of this test.

### 2.2 The reverse ladder — leave-one-out

The full model with **one gate removed at a time**, **four** variants (POI, bias, profile,
alignment). This is the half that actually identifies which gate carries the effect, and
it is the half a naive "does the strategy work" test omits.

On the event layer the removal multipliers are far more even than the day-layer proxy
suggested — **×1.25 / ×2.09 / ×2.44 / ×2.58** on the primary stack (§3.3) against a proxy
range of ×1.05 to ×10.8. **No single gate dominates the sample destruction any more**,
which materially improves the ladder's ability to attribute an effect to a gate rather
than to the one filter that removed almost everything.

### 2.3 What is measured at every rung

For each rung, forward and leave-one-out, on each stack, at the primary target and cost:

1. `n`, and `n` per year;
2. win rate and expectancy in R;
3. **the differential against a matched random-entry control** (§4.3) in both win rate
   and R, with a bootstrap 95% CI — **this, not the raw rate, is the quantity the ladder
   is read on**;
4. mean stop distance in USD/oz **and in ATR(20) units at the signal bar**;
5. mean bars to resolution, and time-exit share;
6. **total R per year** (the opportunity-cost column);
7. profit factor and max drawdown in R, as description only.

### 2.4 What counts as the conjunction adding value

Pre-declared, per rung transition R(k−1) → R(k):

- **ADDS VALUE** — the *differential against the matched control* rises, and the
  bootstrap 95% CI on the rise excludes zero after Holm correction within the ladder
  family. Raw win rate is irrelevant to this determination.
- **MERELY SHRINKS THE SAMPLE** — the raw win rate rises but the differential against
  the control does not rise (CI on the rise contains zero). This is the default
  expectation for any gate that selects rarer, larger-R or higher-volatility setups, and
  it is what the control is for. It is reported explicitly with that label.
- **COSTS** — the differential falls with a CI excluding zero. Pre-registered as the
  expected outcome for R5 (session), given `session_window_fit.md`.
- **INDETERMINATE** — the CI contains zero and `n` at that rung is below the power floor
  for a 5pp effect (§3.4). Given §3, this is the expected outcome for R4 and R5 on three
  of the four stacks, and saying so is the point of this document.

A rung is only reported as **"worth trading"** if it both ADDS VALUE and raises **total
R per year**. A gate that improves per-trade edge while cutting `n` sixfold is a
different claim from a gate that improves the account, and conflating them is how a
6-events-per-year model gets called an edge.

### 2.5 The conjunction claim itself — and why the bar is R0, not zero

The corpus's claim (`RESUME.md`, "what is worth doing next" item 1) is that the edge
lives in the *conjunction*, not the primitives. Formally, pre-registered:

> **H1.** The differential-against-control at R4 exceeds **the differential at R0** by an
> amount whose 95% CI excludes zero, after Holm correction within family A.
>
> **H0.** It does not.

**The comparator is rung 0, not zero, and this is not a technicality — rung 0 is
already not zero.** An independent coordinator baseline of bare CISD with no gates at
all (entry at the confirming bar's close, stop at `protected_swing`, 2R, M1 resolution,
stop-first ties, **no costs**, 3:1 control draw, single comparison, ±30-day matched
control) returned:

| TF | n | real | matched control | differential |
|---|---:|---|---|---:|
| 15m | 15,235 | +0.0310 R (34.37%) | +0.0214 R (34.05%) | **+0.0097 R** |
| 1h | 3,624 | +0.1118 R (37.06%) | +0.0476 R (34.92%) | **+0.0642 R** |
| 4h | 950 | +0.2032 R (40.11%) | +0.0804 R (36.01%) | **+0.1227 R** |

Those numbers are **provisional and not to be cited as results** — cost-free,
single-comparison, uncorrected, one control ratio. What they establish is a
methodological fact that must be fixed in advance: **the bare primitive at 1h and 4h
already sits meaningfully above its own control before any gate is applied.** Therefore:

> **"The full model is profitable" is not evidence for the conjunction.** It may be
> nothing but rung 0 surviving five gates. The pre-registered bar is that the full model
> **beats rung 0 by more than the ladder's multiple-testing correction allows** — §5.1
> item 5, which is a required condition and not a nice-to-have.

Note that H1 can be true while the R4 book is unprofitable after costs, and false while
the R4 book is profitable — both cases must be reported as what they are, in those
words. Profitability of the full model is a *separate, secondary* question and is not
the pre-registered primary.

---

## 3. Power — which rungs are answerable, and which are not

**Read this section before agreeing to run the test.** All counts below are from
`python/estimate_conjunction_power.py`, run on the real data with the existing detectors
at the locked primary parameters (`level_rule="series_open"`, `max_wait=3`,
`min_series=1`). No outcome was computed; these are event counts only.

**No longer provisional. [AMENDED — §8, A3/A4.]** All gates are now the real
`detectors.bias.bias_report` and `detectors.poi.poi_gate_events` modules, and all counts
are measured on the **certified span, 2016-01-01 → 2026-07-23, 10.55 years, 3,687,209 M1
bars** (`meta/xau_history_audit.md`). The earlier proxy figures are withdrawn; they were
flagged as upper bounds and they were, by roughly 5×.

The proxies were wrong in the direction the flag predicted, and one was badly wrong:

| gate | proxy retention | measured retention | |
|---|---|---|---|
| POI (event layer) | 96–98% | **81.4%** (15m) / 80.4% (1h) | proxy too generous, as flagged |
| bias | 31–36% of events | **12.7%** of events | proxy too generous |
| profile | ~93% of days | **14.5%** of days | **proxy badly wrong** — it implemented only the Seek & Destroy stand-aside (57 days of 788); the real gate tests whether the day's profile *supports the bias*, which is a far stronger claim |
| alignment | ~10% of events | 13.5% of days | comparable |

**The net effect is that the conjunction is rarer than the proxy said, not commoner.**
The primary stack's R4 falls from a proxied 454 events on 3 years to a measured **139 on
the same 3 years**, and **722 on the certified 10.55 years**.

### 3.1 The two frequency levers measured first

Before the ladder, the two CISD parameters that move `n` most, on bare CISD counts:

| TF | `max_wait=40`, `min_series=1` | `max_wait=3`, `min_series=1` (**primary**) | `max_wait=3`, `min_series=2` |
|---|---:|---:|---:|
| 15m | 15,255 | 9,410 (−38%) | 4,836 (−68%) |
| 1h | 3,679 | 2,256 (−39%) | 1,159 (−69%) |
| 4h | 1,046 | 621 (−41%) | 313 (−70%) |
| 1D | 185 | 122 (−34%) | 62 (−66%) |

Both are corpus-stated readings, and choosing between them changes the sample by a
factor of three. That is precisely why they are locked here rather than swept later.

**A third lever is larger than either, and it is the biggest anywhere in the model:
`cisd_scope`.** The corpus states both ways whether the confirming CISD must sit inside
the daily candle's **wick** specifically, or anywhere inside its **range** (spec §2.4
step 3 **[P]**). Measured on the certified span:

| `cisd_scope` | biased days | + profile | + alignment |
|---|---:|---:|---:|
| **`range` (primary)** | **862 (31.6%)** | 394 | 153 |
| `wick` (secondary) | 311 (11.4%) | 114 | 36 |

**A 2.77× swing in biased days**, and 4.25× by the end of the day-level stack — larger
than the CISD level rule, `max_wait` and `min_series` combined. It is corpus-ambiguous
rather than fitted, so it gets the same both-ways treatment as the CISD level rule
(§1.8): **`range` is primary**, `wick` is a pre-declared secondary reading, both are
reported, and neither may change the verdict alone.

### 3.2 Event counts at each rung — measured, certified span

XAUUSD, **2016-01-01 → 2026-07-23, 10.55 years**, real modules, locked primary
parameters. `n` per year in parentheses. The 5m playbook stack is reported at the
certified span where measured and is the pre-designated powered comparison.

| rung | **15m / 4H / 1D (PRIMARY)** | 1H / 1D / 1W (swing) |
|---|---:|---:|
| R0 bare CISD | 32,827 (3,110) | 8,034 (761) |
| R1 + POI (event layer) | 26,710 (2,531) | 6,458 (612) |
| R2 + HTF bias | 4,171 (395) | 1,034 (98) |
| R3 + profile support | 1,862 (176) | 484 (46) |
| **R4 + alignment = PRIMARY** | **722 (68)** | **176 (17)** |
| K1 + session (knob) | 43 (4) | 24 (2) |
| K2 + SMT (knob) | 252 (24) | 63 (6) |
| K3 + session + SMT | 15 (1.4) | 9 (0.9) |

Retention R0 → R4 is **2.2%** on both stacks — the conjunction discards roughly 44 CISDs
in 45, against the proxy's estimate of 19 in 20.

For continuity with phase 2, the same ladder on the legacy 3-year file, primary stack:
R0 **9,410** → R1 **7,625** (81.0%) → R2 **982** → R3 **431** → **R4 139** → K1 **9**.
The certified span multiplies the primary configuration's sample by **5.2×**.

**The 5m playbook stack, measured on the 3-year file** (real modules): R0 **28,179** →
R1 **22,815** (81.0%) → R2 **3,005** → R3 **1,333** → **R4 441** (7.0pp floor) → K1 **42**,
K2 **130**. Its leave-one-out multipliers are ×1.18 / ×2.07 / ×2.77 / ×3.02, the same
even profile as the primary stack.

**The 5m playbook stack, measured on the certified span** — the pre-designated primary
powered comparison, and the one configuration that changes the verdict:

| rung | events | per yr | vs R0 | MDE vs 5× control |
|---|---:|---:|---:|---:|
| R0 bare CISD | 98,346 | 9,318 | 100.0% | 0.5pp |
| R1 + POI | 79,692 | 7,551 | 81.0% | 0.5pp |
| R2 + HTF bias | 12,569 | 1,191 | 12.8% | 1.3pp |
| R3 + profile | 5,716 | 542 | 5.8% | 1.9pp |
| **R4 = PRIMARY config** | **2,234** | **212** | **2.3%** | **3.1pp** |
| K1 + session | 187 | 18 | 0.2% | 10.8pp |
| **K2 + SMT** | **792** | **75** | **0.8%** | **5.2pp** |
| K3 + session + SMT | 69 | 7 | 0.1% | 17.7pp |

**K2 here is the best-powered SMT line anywhere in this design** — 792 events, a 5.2pp
floor. It resolves the top of the plausible band and not its middle, so SMT stays a
declared knob (§2.1a, A5 ground (a)); but "underpowered at 5.2pp" is a very different
statement from the "untestable" this document briefly carried.

*A discipline note, recorded because the outcome is misleading:* the deep correlate
raised the 5m K2 from 130 to 792, a factor of 6.1 — **the same 6.1 the 15m stack showed
(41 → 252)**. Scaling would have produced the right answer here. That does not
retroactively justify scaling, and §3.7.1's rule is unchanged: the two previous times
this project inferred rather than measured, it was wrong both times, and a ratio that
happens to hold is not evidence that ratios hold.

Leave-one-out multipliers ×1.21 / ×2.06 / ×2.38 / ×2.56 — the same even profile again.
Note R0→R4 retention is **2.3%**, within a whisker of the primary stack's 2.2% and the
swing stack's 2.2%: **the conjunction discards the same ~97.7% of CISDs regardless of
timeframe**, which is a stronger regularity than anything the proxy suggested.

**Sanity check against the corpus's own claimed frequency — it still passes, and now more
precisely.** He states one to two trades a week, up to three or four
(`trade-frequency-baseline`), and daily-chart swing setups **6–8 times a year**. The
primary stack at R4 gives **68 per year** (≈1.3/week, squarely inside "one to two a
week"), and the swing stack at R4 gives **17 per year** against his 6–8 for daily swing
setups. The detector is not mis-calibrated; **the method genuinely fires this rarely, and
that rarity is the whole problem.**

### 3.3 Which gate does the cutting — leave-one-out multipliers

Full model (R4) with one gate removed, as a multiple of the full model's `n`, certified
span:

| gate removed | 15m primary | 1H swing |
|---|---:|---:|
| POI | ×1.25 | ×1.19 |
| HTF bias | ×2.09 | ×2.00 |
| profile | ×2.44 | ×2.37 |
| alignment | ×2.58 | ×2.75 |

**This is a materially better ladder than the proxy implied**, and the improvement is the
main structural gain from the real modules. Under the proxy the multipliers ran ×1.05 to
×10.8, so one gate (alignment, or session) destroyed nearly the whole sample and the rest
were free riders — a ladder in which three of five rungs could never be shown to do
anything. Measured, the four gates cut the sample **within a factor of two of each
other**, so each rung is a real comparison and an effect can be attributed to a gate
rather than to the one filter that removed everything.

The withdrawn proxy conclusion — *"POI and profile are nearly free, alignment and session
do all the work"* — was an artefact of the proxy and of the day-layer resolution, and is
retracted. POI removes 19% of events; profile is the **second strongest** gate, not the
weakest.

### 3.4 Minimum detectable effect

Same method as `meta/backtest_c2_wick.md` §5c so the numbers are directly comparable:
two-sided α = 0.05, 80% power, difference of proportions, at an assumed 2R win rate of
**p = 0.36** (phase 2 measured 35.8% / 35.7% / 40.5% / 38.9% on 15m/1h/4h/1D; p(1−p) is
nearly flat across that band). `MDE = (1.960 + 0.842) · sqrt(p(1−p)(1/n₁ + 1/n₂))`.

Two floors are given because the ladder makes two kinds of comparison: **rung vs rung**
(both arms real) and **rung vs a 5×-replicated matched control**.

> **Sample size and calendar requirement are different quantities. [AMENDED — see §8.]**
> A comparison between two *real* buckets needs `4p(1−p)(z/e)²` events and every one of
> them costs market history. A comparison against the **matched control** needs only
> `p(1−p)(1+1/K)(z/e)²` **real** trades, because the control arm is *resampled from
> history already held* — five random draws per real trade, from the same series. It
> consumes no additional calendar time. Charging the control's sample size to the
> calendar overstates the data requirement by `4K/(K+1)`, which is **3.33× at the locked
> K = 5**. The first version of this document made exactly that error.

| effect | REAL trades (sets the calendar) | both arms real (rung vs rung) |
|---|---:|---:|
| 3pp | **2,411** | 8,037 |
| 4pp | **1,356** | 4,521 |
| 5pp | **868** | 2,893 |
| 8pp | **339** | 1,130 |

Measured, certified span (10.55 years) unless marked:

| rung | stack | n | n / yr | MDE vs prior rung | MDE vs 5× control | yrs to 5pp | yrs to 3pp |
|---|---|---:|---:|---:|---:|---:|---:|
| R0 | 15m primary | 32,827 | 3,110 | — | **0.8pp** | 0.3 | 0.8 |
| R1 | 15m primary | 26,710 | 2,531 | 1.1pp | 0.9pp | 0.3 | 1.0 |
| R2 | 15m primary | 4,171 | 395 | 2.2pp | **2.3pp** | 2.2 | 6.1 |
| R3 | 15m primary | 1,862 | 176 | 3.7pp | 3.4pp | 4.9 | 13.7 |
| **R4** | **15m primary** | **722** | **68** | **5.9pp** | **5.5pp** | **12.7** | **35.2** |
| K1 | 15m + session | 43 | 4 | — | 22.5pp | 213 | 592 |
| K2 | 15m + SMT | 252 | 24 | — | 9.3pp | 36.4 | 101 |
| R0 | 5m playbook | 98,346 | 9,318 | — | 0.5pp | 0.1 | 0.3 |
| R2 | 5m playbook | 12,569 | 1,191 | 1.3pp | 1.3pp | 0.7 | 2.0 |
| **R4** | **5m playbook** | **2,234** | **212** | **3.4pp** | **3.1pp** | **4.1** | **11.4** |
| K1 | 5m + session | 187 | 18 | — | 10.8pp | 49.0 | 136 |
| K2 | 5m + SMT | 792 | 75 | — | 5.2pp | 11.6 | 32.1 |
| R0 | 1H swing | 8,034 | 761 | — | 1.6pp | 1.1 | 3.2 |
| R2 | 1H swing | 1,034 | 98 | 4.5pp | 4.6pp | 8.9 | 24.6 |
| **R4** | **1H swing** | **176** | **17** | **11.8pp** | **11.1pp** | **52.1** | **145** |
| K1 | 1H + session | 24 | 2 | — | 30.1pp | 382 | 1,060 |
| **R4** | **15m primary, 3y file** | **139** | **45** | 13.1pp | **12.5pp** | 19.1 | 53.0 |

For **expectancy in R** rather than win rate, with the 2R outcome distribution
(σ ≈ 1.44 R) and a 5× control, the floor is `MDE_R ≈ 4.42 / sqrt(n)` — this form was
already real-trades-only and is unchanged:

| n | detectable edge in R |
|---:|---:|
| 26,710 | 0.027 R |
| 4,171 | 0.068 R |
| 722 | 0.164 R |
| 176 | 0.333 R |
| 43 | 0.674 R |

Real trades needed: **7,807** for a 0.05R edge, **1,952** for 0.10R, **868** for 0.15R.

**The cross-check that catches this class of error, and that must be run every time.**
At a 2R target `d(expectancy)/d(win rate) = 3`, so an X pp win-rate effect *is* a 3X R
effect and the two independently derived floors must agree exactly:

| win-rate effect | real trades | equivalent R effect | real trades |
|---|---:|---|---:|
| 3pp | 2,411 | 0.09 R | 2,411 |
| 4pp | 1,356 | 0.12 R | 1,356 |
| 5pp | 868 | 0.15 R | 868 |

They now agree to the unit. **Under the erroneous figures they disagreed by 3.33×** — a
4pp requirement of 4,521 sat beside a 0.12R requirement of 1,356 in the same document,
which is the tell that should have been caught internally and was not. The assertion is
now in `estimate_conjunction_power.main` and fails the run if it is ever broken again.

### 3.5 What effect size is plausible — set before looking

This is the number the floors have to be compared against, and it comes from work
already done, not from the conjunction:

- the one published quantitative study of a same-family ICT construct (MPM Markets, 7
  years, 4 futures markets, ~40k occurrences) found it **~5pp above a matched random
  baseline** and untradeable after costs (`external_crossref.md`);
- phase 2's independent barrier test put the small-wick advantage at **+4.0pp (4h) and
  +3.2pp (1D), ≈0 on 15m and 1h** (`threshold_fits.md` §1);
- phase 2's C2-vs-control differentials, where any CI cleared zero at all, ran
  **+5.5 to +7.8pp**, on 4h only, and did not replicate across the split.

**Pre-registered plausible effect band: 3–5 percentage points of win rate, or
0.05–0.10 R of expectancy.** Anything the conjunction returns far above that band is
more likely a harness fault than a discovery (§4.2).

### 3.6 The verdict this section forces, stated in advance

Stated against the **certified span, 10.55 years**, which is the largest trustworthy
sample that exists for this instrument (§3.7).

> **The primary stack is close to answerable and does not quite get there.** 722 events,
> a **5.5pp** floor, against a plausible 3–5pp effect. It resolves the top of the band
> and misses the middle of it. **A null result on this stack will be genuinely
> ambiguous**, and that is known now rather than after the run. Reaching 5pp needs 12.7
> years against 10.55 available; reaching 3pp needs 35 years, which does not exist.
>
> **The 1H swing stack is out of reach and stays out of reach**: 176 events, an 11.1pp
> floor, 52 years needed for 5pp. Report for completeness, never for a verdict.
>
> **The session knob remains fatal, and extra history does not rescue it.** 43 events on
> the primary stack over a decade, a 22.5pp floor; 24 on the swing stack. This is a
> second, independent reason — after `session_window_fit.md`'s −0.057R — not to put the
> session filter in the primary.
>
> **SMT is measurable across the full decade and is still underpowered.** [AMENDED —
> §8, A5.] 252 events on the primary stack, a **9.3pp** floor — roughly twice the top of
> the plausible band, so it can neither confirm nor refute an effect of the size in play.
> It fires on **8.9% of days**, stably (7.1% on the 3-year window), against a decade-stable
> correlate. **Measurable, and not decidable** — which is a materially better position
> than the "untestable" this document briefly and wrongly claimed.
>
> **One on-method configuration IS fully answerable, and it is the pre-designated powered
> comparison: the 5m playbook stack at R4.** 2,234 events, a **3.1pp** floor — below the
> bottom of the 3–5pp plausible band. It resolves the whole band, detects a 0.09R
> expectancy edge, and needs 4.1 years for 5pp against 10.55 available. **This is the
> configuration the primary verdict should be read from**, and it was designated the
> powered comparison in §1.2 before its count was known.

**The certified span changed the verdict's character, and for one stack it changed the
conclusion.** The primary 15m stack moved from *hopeless* (139 events, 12.5pp) to
*marginal* (722, 5.5pp) — a 5.2× sample and a floor halved, still short of the band's
middle. But the 5m playbook stack moved from *marginal* to **decisive** (2,234, 3.1pp).
**For the first time in this project, an on-method configuration can resolve the effect
size the corpus's own claims imply.**

**Phase 2's structural complaint is now genuinely weakened, though not dissolved.** It
was: *the timeframes that carry the claim have no data, and the timeframes with data are
the ones the method disowns.* The 5m playbook stack is **not** disowned — it is
`ttfm-hourly-5m-playbook`, the corpus's only written checklist — and it now has the
sample. What survives is that his *stated favourite* stack, the 15m/4H/1D A+, still
cannot resolve a 3–4pp effect on the best data that exists. **The method is testable one
rung below the timeframe he most recommends.**

### 3.7 The certified span — what may be backtested on [AMENDED — §8, A4]

**The document is anchored on 2016-01-01 → 2026-07-23: 10.55 years, 3,687,209 M1 bars,
3.43× the legacy file.** Not on the 16.5 years the raw fetch returned.
Source: `meta/xau_history_audit.md`.

**Why 2016 and not 2010 — a market-structure change, not a data defect.** NY hour 17
carries 1,813–3,726 bars per year from 2010 through September 2015, then hits **exactly
zero in October 2015 and stays there**; the 2015 monthly series is unambiguous (Sep 142 →
Oct 0). Gold traded a genuine 24-hour day before that, and 2011 additionally carries 434
Saturday bars across 40 Saturdays. **Every gate in the locked configuration is session- or
daily-calendar-dependent** — the daily candle at 18:00, the 4H forex grid, the profile's
London and Asia windows, the session knob. On pre-2015 data none of them fails; they
**quietly compute different objects**, which is strictly worse than failing. Pre-2016 is
therefore admissible as regime and higher-timeframe evidence only, and is **explicitly
disqualified by the calendar, not by quality** — 2013–2014 are respectably dense at 47–83
ticks per minute.

The join is trustworthy: 6,709 timestamps overlap the legacy file and **all four OHLC
fields agree to exactly 0.0 on every one**, so nothing already computed changes. Prices
validate externally (2011 high 1921.07 against the ~1920.9 record).

#### 3.7.1 The audit's extrapolation was 2.2× optimistic — measured beats scaled

The audit projected ~1,570 events and a ~3.9pp floor on the certified span by scaling the
observed rate, and said plainly: *recount before relying on the MDE column.* Recounted:

| | events at R4 | MDE vs control |
|---|---:|---:|
| audit extrapolation | ~1,570 | ~3.9pp |
| **measured, real modules** | **722** | **5.5pp** |

The gap is not a per-year rate change; it is that the extrapolation scaled the **proxy**
count of 454, and the real gates are far stricter (§3 preamble). **Never scale an event
rate across a span or a detector change — measure it.** This is the same class of error
as the one in amendment A1, caught the same way, by recomputing rather than deriving.

#### 3.7.2 Three hard limits on what this test can ever conclude

**(a) There is no sustained bear market in the certified span, and this bounds every
conclusion.** The only real gold bear market in 16.5 years is 2013 (−28%), and it sits on
the wrong side of the calendar break. Within the certified span the best available
non-bull regimes are **2016–2018** (low-volatility range, and the cleanest pre-2022 data)
and **2021–2022** (two flat years). Those support a robustness check; **they are not a
downtrend.** No honest reading of any result from this test may claim the method has been
tested against a sustained gold downtrend on trustworthy data. This is a harder limit
than the B6 concentration flagged in §4.4b, and it is stated in the opening summary for
that reason.

**(b) Absolute-point thresholds are not comparable across the span — confirmed
threshold by threshold.** Median daily range ran **$15.3 → $90.3** across the span, though
only **1.21% → 1.94%** in relative terms, which is the reassuring part. Every locked
threshold was checked individually rather than assumed:

| locked quantity | form | scale-free? |
|---|---|---|
| `opposing_run / abs(close−open) ≤ 1.0` | ratio of two price distances | **yes** |
| `opposing_run / (high−low) ≤ 0.30` | ratio of two price distances | **yes** |
| displacement `range_ratio ≥ 1.5` | window range / pre-break range | **yes** |
| displacement `dist_ratio ≥ 0.65` | distance beyond level / pre-break range | **yes** |
| CISD level, C3 reference, POI tests | price *orderings*, no magnitude | **yes** |
| stop = protected swing; target = 2R | R is derived per trade | **yes** |
| `max_wait=3`, `min_series`, `N=4` | bar counts | **yes** |
| session window | wall clock | **yes** |
| **cost = 0.2 USD/oz flat** | **absolute price** | **NO** |

**One exception, and it is now fixed.** A flat 0.2 USD/oz round trip is a very different
tax on $1,100 gold in 2016 than on $5,500 gold in 2026 — a 5× swing in relative cost
across the span, where the 3-year file only spanned 3×. **The proportional `0.04R` column
therefore becomes the PRIMARY cost basis on the certified span**, and flat 0.2 USD/oz is
demoted to a diagnostic retained for comparability with phase 2. §1.15 is amended
accordingly. This is the one place where the extended history forces a change to the
locked configuration, and it is a change that makes the test stricter and more
scale-honest, not looser.

**(c) A declared robustness exclusion: 2019-02 → 2020-02.** A sharp, isolated feed
regression sitting inside otherwise-modern data — median tick density collapses from 83
to 6 ticks per minute, with up to 9% flat bars. It is **not** grounds to shorten the
span, but the primary result **must** be re-run with those thirteen months excluded and
both reported. Dropping it still leaves 9.4 years. Run it with
`--exclude-tick-regression`.

#### 3.7.3 Requirement table, on measured rates

Real trades needed against the 5× control (§3.4): 5pp → 868, 4pp → 1,356, 3pp → 2,411.

| stack | ev/yr at R4 | 5pp | 4pp | 3pp | available | verdict |
|---|---:|---:|---:|---:|---:|---|
| **5m / 1H / 1D playbook** | **212** | **4.1 yr** | **6.4 yr** | 11.4 yr | **10.55** | **answerable, 3.1pp floor** |
| 15m / 4H / 1D primary | 68 | 12.7 yr | 19.8 yr | 35.2 yr | 10.55 | marginal, 5.5pp |
| 1H / 1D / 1W swing | 17 | 52.1 yr | 81.4 yr | 145 yr | 10.55 | out of reach |

**Nothing available closes the 15m stack's 5pp gap by adding gold history**, because the
certified span is the whole trustworthy record. The routes, in order of cost:

1. **Read the verdict from the 5m playbook stack**, which is on-method, pre-designated,
   and clears the whole plausible band at 3.1pp. This is the cheapest route and it costs
   nothing — it was already the declared powered comparison.
2. **Accept a 5.5pp floor on the 15m stack** and report it as resolving only the top of
   the band — which §5.3 requires the write-up to say.
3. **More instruments**, the only route to a 3pp floor on the *15m* stack specifically.
   This partly reverses A2: with gold exhausted at 10.55 certified years, breadth is a
   power argument again as well as the SMT and replication argument. The corpus's own
   taught set — NQ, ES, YM, and gold-in-euro / gold-in-pound (`gold-correlated-assets`)
   — would take the 15m stack to roughly a 2.8pp floor at four markets.

#### 3.7.4 Footnote: the legacy file is missing two days

`xau_m1_3y.parquet` is missing **2025-12-09** and **2026-01-21** entirely, both of which
OANDA serves in full. They were deliberately not patched so that prior results stay
reproducible. Immaterial at n ≈ 788 days, but the record should state that **phase 2's
numbers were computed on marginally incomplete data**, and that this document's own
3-year comparison figures inherit the same two-day hole.


## 4. Statistical protocol

### 4.1 No lookahead — a mandatory pre-condition, not a recommendation

**A run without the assertions in this subsection passing is not a valid test and its
numbers may not be reported.**

`bars.resample` uses `label="left"`: **a bar's index timestamp is its START, not its
close.** A verification of a phase-2 result hit this directly — resolving exits by
scanning forward from the event timestamp replays the signal candle itself, the candle
touches its own extreme (which is the stop), the stop fires instantly, and the book
returns a **3.29% win rate** where the corrected version returns **32.94%**.

This failure mode is **sign-asymmetric and self-camouflaging**, which is why it belongs
in a pre-registration rather than a code comment. Off-by-one in one direction produces
an absurd result that reads as *"the strategy is terrible"* and gets believed. Off-by-one
in the other direction — a gate seeing any part of the bar it fires on — produces a
*spectacular* result that reads as success and is therefore far **less** likely to be
questioned. The conjunction stacks several gates that each read higher-timeframe bars
(daily bias from the daily closure, profile classification from London/Asia windows,
timeframe alignment from two HTFs, and SMT across two instruments if it is ever added),
so it has many independent opportunities to leak, and the leak that flatters is the one
nobody catches.

Three requirements:

1. **A no-lookahead assertion, per gate.** For every gate the write-up must state (a)
   which bar's information it consumes and (b) the exact timestamp at which that
   information becomes available. An automated check must confirm that **no gate uses
   data timestamped at or after the moment it claims to fire**, for every event in the
   book. Concretely, for a gate reading a bar on timeframe `T` at event time `t`: the
   consumed bar's index must satisfy `bar_start + period(T) <= t`, i.e. the bar has
   closed. `estimate_conjunction_power.last_closed_pos` implements exactly this and is
   the reference. The assertion must pass **before any result is computed**, and its
   pass/fail must be recorded in the output file.

2. **One entry-timing convention, stated once and applied everywhere.** Under the
   left-label convention, **entry occurs at `event_time + one bar` of the entry
   timeframe** — the signal bar's close is the price, but the *resolution index* starts
   strictly after the signal bar has closed. The first M1 bar eligible to resolve a trade
   is the first M1 bar whose start is `>= event_time + period(entry_tf)`. This matches
   `backtest_c2_wick.resolve`; any divergence from it is a bug, not a variant.

3. **A harness sanity floor.** Any rung returning an implausible extreme — a win rate
   below 10% or above 90% at a 2R target, an expectancy outside roughly ±1.0 R, a
   differential against the matched control outside ±15pp, or a profit factor above ~3 —
   is to be treated as a **suspected harness fault to be diagnosed, not a finding to be
   reported.** Phase 2's lesson is that a number can be internally consistent and still
   be measuring the machinery: a per-day event rate was published as a share of extremes
   (59.8% where the truth is 29.9%) and the derived lift was *correct*, because the
   expectation was scaled the same wrong way, so nothing looked inconsistent from the
   inside. **Recompute every headline number from raw bars, not from the pipeline that
   produced it.** Two further known traps: this pandas build's datetime resolution makes
   `index.view("int64")` arithmetic silently wrong by 10³, and gold's 1,800 → 5,500 drift
   makes any flat-USD quantity non-stationary across the split.

#### 4.1a Joining daily context onto events — two guards, both of which caught bugs

The ladder joins day-level verdicts onto entry-timeframe events (§2.0). That join is
where lookahead would enter, so it is specified here rather than left to the
implementation. `estimate_conjunction_power.join_day_gates` is the reference.

1. **Availability.** `bias_report` classifies day D from information that resolves at D's
   close, so each gate carries a `*_available_at` timestamp — the first moment its
   verdict may be acted upon. An event may use a day's verdict only if
   `event_time >= that day's available_at`. Spec §2.3's *"anticipate the same direction
   on the next candle"* means an event on day D+1 uses day D.
2. **Staleness.** The joined day must be within **one trading day** of the event's own
   day. Without this bound an event silently inherits the most recent day that happened
   to have *any* resolved verdict, which on a sparse column can be weeks earlier.

Guard 2 is not hypothetical. Joining the SMT column by "last resolved timestamp" alone
reported SMT firing on **99% of events** — because `smt_available_at` is populated only
on the ~56 days that actually had an SMT, and every event after one of them inherited
True forever. The correct figure is **2%**. A gate that is nearly always false was
reported as nearly always true, in the direction that would have made the conjunction
look both commoner and better-supported than it is.

**Requirement:** the write-up must report, for each gate, the share of events whose join
resolved (`_src >= 0`) and the distribution of the join's staleness in trading days. A
gate whose join fails on a large share of events is not a gate that fired; it is a gate
that was never evaluated, and the two must not be reported as the same thing.

#### 4.1b A default masquerading as a finding — the class of error to watch for

Two bugs in this workstream, caught days apart, share one shape: **a property of the
harness was read as a property of the market, and written down as a conclusion.** They
are recorded together because the shape is what generalises, not either instance.

| | what was observed | what it was taken to mean | what it actually was |
|---|---|---|---|
| SMT join | `smt_available_at` populated on ~56 days | SMT fires on **99%** of events | a sparse column carried forward; true rate **2%** |
| SMT history | `xag_h1.parquet` starts 2023-07-02 | **"SMT is unmeasurable before 2023"** | `fetch_correlated.py` had `DEFAULT_START = 2023-07-02`, inherited from the *gold 3-year* window. XAG is served from 2010-01-03. |

The second is the more instructive, because nothing about it looked like a bug. The file
genuinely started where it said it started; the inference was arithmetically sound; and
the conclusion was written into an amendment as a **methodological limit on what the
project could ever test**. The tell was available and was missed: **the correlate began on
exactly the same date as the unrelated gold file** — a coincidence with no market
explanation, which should have prompted a check of the fetch parameters rather than an
inference about OANDA's coverage.

**Standing rule, pre-registered:** never infer a data limit from a file's extent. Check
the parameters of the fetch that produced it. Where a limit is claimed in any output of
this test, the claim must cite the probe that established it, not the extent of a file on
disk. And where two datasets share a boundary date, treat that as a suspected shared
default until shown otherwise.

### 4.2 Exit resolution

**Every trade is resolved on M1 bars, never on the signal timeframe.** Phase 2 measured
this artefact rather than assuming it: the identical book at 1h/2R OOS gives **−0.032 R
on M1** and **+0.013 R on 1h bars with an optimistic same-bar tie-break** — a sign flip
(`backtest_c2_wick.md` §6c). The published FVG study saw the same failure turn ~73% into
~50%.

- **If stop and target are touched inside the same M1 bar, the stop is taken.** M1
  carries no intrabar order and assuming otherwise manufactures edge.
- A bar that **opens through the stop fills at that open** (gap risk paid).
- A bar that **gaps through the target still fills at the level** (gap gift refused).
- Unresolved at max hold → exit at the last M1 close in the window, recorded as a
  time-exit and reported as a share.
- The signal-timeframe resolution is computed **as a diagnostic** and reported beside
  M1, exactly as phase 2 did, so the size of the artefact is a number in the file rather
  than an assumption.
- Session-break handling: XAUUSD stops 17:00–18:04 NY daily and over weekends. The
  `truncated` variant (end every window at the first gap > 70 minutes) is reported for
  the entry timeframes where a hold window rarely reaches a break. At 4H and above a
  multi-period hold *must* span a weekend, so the truncated column there is a different
  strategy, not a robustness check, and must be labelled as such.

### 4.3 The matched random-entry control — matching dimensions locked

**This is the decisive comparison and the quantity the ladder is read on.** A win rate
against 50% means nothing; a win rate against this means something.

The control specification is **locked here in full**, because "a matched random control"
is not a specification and the matching dimensions turn out to move the headline by
about a third. Every conjunction trade is paired with **`reps = 5`** random trades
carrying:

| dimension | matched how |
|---|---|
| direction | **identical** (long ↔ long) |
| stop distance | **identical in price** (`abs(entry − stop)` in USD/oz) |
| target distance | **identical in price** |
| entry timeframe | **identical** — control entries are bar closes on the same TF |
| entry time | drawn uniformly at random from bars within **±30 calendar days** of the real trade's entry |
| max hold | **identical** (10 entry-TF periods) |
| exit resolution | **identical** — M1, stop-first same-bar tie-break |
| cost | **identical** |
| seed | fixed and recorded |

**The ±30-day window is mandatory and is the locked value.** It is not a nicety. Gold
ran ~1,800 → ~5,500 across this sample and realised volatility roughly tripled, so a
2026-sized stop distance dropped into 2023 is simply a different trade. An independent
rung-0 baseline run by the coordinator measured the size of this: drawing control entries
uniformly across the whole three years while applying the real trade's absolute USD risk
distance gave differentials of +0.0145 / +0.0918 / +0.1967 R at 15m / 1h / 4h; re-drawing
within ±30 days gave **+0.0097 / +0.0642 / +0.1227 R** — a **38% reduction at 4h.**

**And the inflation is unequal, which is why it is fatal to the ladder specifically.** An
unmatched-regime control inflates every rung, but it inflates *most* the rungs whose
gates concentrate trades into particular periods — a session gate, a profile gate, a
bias gate that fires in trends. Those are exactly the comparisons the ladder exists to
make, so an unmatched control does not add a constant offset, it adds a gradient along
the ladder in the direction that flatters the conjunction.

`±30 days` may not be swept, and no result computed against a differently matched
control may be reported. If a sensitivity check on the window is wanted it belongs in
family C as a landscape, and it cannot change any verdict.

Because the control shares direction, stop distance, target distance and local regime
with the trade, **any improvement produced by selecting rarer, larger-R or
higher-volatility setups appears in both arms and cancels.** That property is the whole
reason this control, and not a raw win rate, is the ladder's measurement.

Differences carry a **2,000-draw bootstrap 95% CI**; a CI straddling zero is no effect.
The control arm's `n` is `5 × n`, which is what the "MDE vs 5× control" column of §3.4
assumes; a different `reps` invalidates those floors.

### 4.4 In-sample / out-of-sample

**IS = before 2025-07-02 (two years). OOS = the remainder (~one year).** Identical to
`meta/backtest_c2_wick.md`, deliberately, so the two books can be laid side by side.

**Nothing is fitted on IS.** Every parameter in §1 comes from the corpus or from an
earlier workstream's already-published fit; none is chosen from this book's outcomes. The
split is therefore a **stability check, not a fit/holdout**, and the pre-registered
requirement is correspondingly stricter: **IS and OOS must agree in sign.** Phase 2's C2
wick effect was −0.034 R in-sample and +0.073 R out-of-sample, on twice the data in the
half that disagreed. That pattern — the larger sample contradicting the smaller — is
declared in advance to be **refutation, not "an edge with a bad year"**.

Any quantile edge, bucket boundary or threshold that must be estimated from data (there
should be none, but if one appears) is fitted on IS only and applied unchanged to OOS.

**The extended history creates a third, better block: PRE.** If the audit certifies
history before 2023-07-02, that span has **never been looked at by any workstream in this
project** — phase 1 read transcripts, and every phase-2 measurement ran on
`xau_m1_3y.parquet`. It is therefore genuinely virgin, in a way the 2025–2026 OOS is not
(phase 2 saw it). Pre-declared:

- **PRE** = certified history before 2023-07-02 — the **confirmatory** sample;
- **IS** = 2023-07-02 → 2025-07-02 — descriptive, and the phase-2 comparison window;
- **OOS** = 2025-07-02 onward — descriptive, already seen by phase 2.

The primary verdict is read on **PRE**, conditional on the audit certifying it, with IS
and OOS reported beside it. If the audit certifies nothing before 2023-07-02, this
paragraph lapses and §4.4's original IS/OOS reading stands unchanged.

### 4.4b Regime blocking — pre-declared before the data arrives

Pooling 16.5 years assumes an effect stable across regimes that are not alike. **A pooled
estimate alone is not admissible on the extended sample.** The blocks below are fixed
now, before any extended-history result exists.

**Primary blocking: four equal calendar quarters of the certified span**, i.e.
2016-01-01 → 2026-07-23 cut into four contiguous blocks of ~2.64 years, boundaries
computed arithmetically. Chosen as primary because it is **exogenous and cannot be
gerrymandered** — no price, no outcome and no judgement enters the boundary.

| block | span (approx) |
|---|---|
| Q1 | 2016-01 → 2018-08 |
| Q2 | 2018-09 → 2021-04 |
| Q3 | 2021-04 → 2023-11 |
| Q4 | 2023-12 → 2026-07 |

**Secondary blocking (declared now so it cannot be adjusted later): the gold cycle,
restricted to the certified span.** Four blocks:

| block | span | character |
|---|---|---|
| C1 | 2016-01 → 2018-09 | low-volatility base / range — the cleanest pre-2022 data |
| C2 | 2018-10 → 2020-08 | bull into the COVID peak |
| C3 | 2020-09 → 2022-10 | post-COVID range and drawdown — two flat years |
| C4 | 2022-11 → 2026-07 | the current bull (contains everything phase 2 ever saw) |

These boundaries are drawn from well-known cycle turns and are therefore mildly
outcome-adjacent, which is why they are secondary to the calendar blocking. They are
recorded here so the choice is fixed in advance.

**What this blocking cannot do, stated with the blocking rather than after it.** None of
C1–C4 is a sustained downtrend. The certified span contains no gold bear market at all
(§3.7.2a), so **regime agreement across these blocks demonstrates robustness across a
range, a spike and two bulls — and says nothing whatever about a bear.** The pre-2016
blocks that would have supplied one are disqualified by the calendar change. This is a
permanent limitation of the instrument's trustworthy record, not a shortfall of this
test's design, and it must be restated wherever regime robustness is claimed.

**Tertiary blocking (mechanical, causal): trailing trend state.** Terciles of the slope
of a 200-day simple moving average evaluated at the signal bar, using trailing data only.
Reported as a robustness cut, not a verdict-bearing partition.

**The requirement, pre-declared.** For any result on the extended sample:

1. the **pooled** differential is reported, and
2. the **per-block** differentials are reported for all four calendar blocks with CIs, and
3. **the sign must agree in at least 3 of the 4 calendar blocks**, with no block showing
   a CI that excludes zero *in the opposite direction*.

Failing (3) while the pooled estimate is significant is declared, in advance, to be a
**regime-dependent result, not an edge**, and must be reported in those words together
with which block carries it. Blocks will individually be badly underpowered — a quarter of the certified span at the
primary stack is **~180 events, an 11pp floor** — so the requirement is deliberately
**sign agreement, not per-block significance**, which is the strongest test the sample
can actually support. Anyone tempted to read a per-block point estimate as a result
should reread §5.4b first.

One consequence to state plainly: **C4 is the block every existing project result comes
from** — phase 2 ran entirely inside it, and so does the 3-year comparison book in this
document. If the conjunction's edge lives only in C4, then every phase-2 finding and this
test alike are describing a single bull market. The certified span makes that
measurable for the first time, and it is the single most valuable thing the extra history
buys — more valuable than the power gain, which only halved the floor.

### 4.5 Permutation and bootstrap

- **Rung-vs-rung and small-vs-large comparisons:** one-sided permutation test on
  `mean_R`, **10,000 label shuffles**, plus a **2,000-draw bootstrap 95% CI** on the
  difference. Same as phase 2.
- **Trade-vs-control:** bootstrap only (the pairing makes a label shuffle meaningless),
  2,000 draws, 95% CI on both the win-rate difference and the R difference.
- **Block bootstrap for overlap:** consecutive entry-TF bars can each produce an event
  and no position cap is applied in the primary, so trades overlap and the i.i.d.
  bootstrap understates variance. A **stationary block bootstrap with a 20-bar mean
  block** is run alongside the i.i.d. version and **the wider of the two CIs is the one
  the verdict uses.** Phase 2 did not do this and its CIs are correspondingly optimistic;
  this is a deliberate tightening.
- All seeds fixed and recorded.

### 4.6 Multiple testing — the explicit accounting

Counted in advance, because the ladder's comparison count is not obvious:

| family | contents | count | correction |
|---|---|---:|---|
| **primary** | R4 on the primary stack vs matched control, 2R, cost 0.2, OOS, plus the same on the pre-designated powered stack | **2** | none (pre-registered primary); both must be reported whatever they show |
| **A — the ladder** | per stack: 5 forward-rung increments + 5 leave-one-out + 6 rung-vs-control = 16, × 4 stacks | **64** | **Holm–Bonferroni within the family** |
| **B — declared readings** | CISD level rule (2) × `min_series` (2) × `max_wait` (2) × C3 reference (2) × inside-bar rule (2) | **32** | Holm within family; **no cell may change the verdict** |
| **C — declared knobs** | targets (4) × costs (4) × session grid (25 + off) × entry variant (2) × stop variant (2) | **large** | reported as a landscape with the sweep curve, **never as a maximum**; no significance claimed |

Total tests whose p-values are interpreted: **66**. At α = 0.05 that is **3.3 expected
false positives by chance**, which is why family A is Holm-corrected. Phase 2 is the
precedent: 4 of its 64 permutation tests came in under 0.05 against 3.2 expected, and
**none** survived correction.

Two standing rules:

- **The maximum of a sweep is never a result.** Family C is reported as full curves —
  IS beside OOS, as `backtest_c2_wick.md` §5 did — and the reader is pointed at *shape
  agreement between the two periods*, which is the actual test. A threshold that is
  monotone out-of-sample and flat in-sample is noise, and phase 2 says so with the
  numbers.
- **No cell outside the primary family can promote a null to a positive.** If the
  primary is indeterminate and one family-B or family-C cell is significant, the finding
  is *"indeterminate, with one uncorrected cell noted for a future, larger test"*.

### 4.7 Forbidden metrics

These may not be used as outcome measures, in the primary or anywhere else. Reporting
one as evidence is how phase 2's headline died, and it died twice, found independently
by two workstreams.

**The general rule: any outcome that reduces to "where did the candle close relative to
its own open or its own extreme" measures geometry, not prediction.** For a bullish
candle `range = opposing_run + body + far_wick`, so a small opposing run mechanically
forces a large body, which mechanically puts the close far from the open — and any test
that asks price to *retain* a cushion the entry has already banked is asking an easier
question of exactly the bucket being promoted.

Specifically forbidden as evidence:

1. **"Delivered beyond the C2/signal candle's open."** Separated by ~26pp across 1h wick
   quintiles while `open gap R` moved 0.817 → 0.157 in exact lockstep. On a target-free
   measure the ordering **reverses**.
2. **"Reverted to the open"** / **"continued beyond the extreme."** Separate by −28pp to
   −44pp in the flattering direction and mean nothing (`threshold_fits.md` §1, flagged
   `[CONFOUNDED]` in the code).
3. **Any target defined relative to the signal candle's own open, close or extreme** —
   including a target at the CISD level itself, which the entry has by construction
   already passed.
4. **Win rate quoted against 50%**, or against nothing. Only the differential against
   the matched control is admissible.
5. **Any outcome resolved on signal-timeframe OHLC**, and in particular anything using
   a target-first same-bar tie-break. Reported as a diagnostic, never as a result.
6. **MFE/MAE measured on signal-timeframe bars.** M1 MFE/MAE is admissible and is the
   target-free cross-check.
7. **Profit factor, expectancy or drawdown quoted without `n` and without the control.**
8. **Any statistic computed on the fitted window and presented without its holdout
   twin.** The two columns side by side are the test.

Two metrics are explicitly **safe** and should carry the argument: R-multiple and
structural targets resolved on M1 (target and stop are absolute prices fixed at entry,
decided by bars strictly after the signal closed), and M1 MFE/MAE over the hold window.

---

## 5. Pre-declared interpretation rules

Written before any result exists. These are the rules the write-up must be held to.

### 5.1 CONFIRMS the conjunction

**All** of the following, on the pre-designated powered comparison (5m playbook stack,
R4, 2R, cost 0.2, M1 resolution), and reported alongside the same cells on the primary
15m stack:

1. The differential against the matched control is **≥ +5pp win rate or ≥ +0.10 R**;
2. its bootstrap 95% CI — the **wider** of i.i.d. and block bootstrap — **excludes zero**;
3. **IS and OOS agree in sign**, and neither sits outside the other's CI;
4. the differential **survives cost 0.5 and cost 0.04R** with the same sign;
5. **H1 holds**: the R4 differential exceeds **the R0 differential** with a CI excluding
   zero after Holm correction within family A — i.e. the conjunction beats its own
   primitive, which is the actual claim. **This condition is required, not optional.**
   Rung 0 is already above its control at 1h and 4h (§2.5), so a profitable full model
   that fails this condition is *bare CISD surviving five gates* and must be reported in
   those words;
6. **at least one leave-one-out removal significantly reduces the differential** after
   Holm — i.e. some gate is load-bearing, and it can be named;
7. the result is **not sensitive to the two declared readings**: it holds under both
   CISD level rules and both C3 references, or the sensitivity is stated as a limit on
   the finding.

Failing 5 while passing 1–4 is a **profitable book, not a confirmed conjunction**, and
must be reported with that exact distinction. It is the most likely "positive" outcome
and the easiest one to overclaim.

### 5.2 REFUTES the conjunction

**Any** of:

1. The differential's 95% CI **contains zero** while `n` is at or above the power floor
   for a 5pp effect — **868 real trades** against the 5× matched control (§3.4; *not*
   the 2,893 equal-split figure, see §8) — a **well-powered zero**, which is a real
   result and should be stated as one. Note this threshold is already cleared by the
   playbook stack at R4 on current data (n = 1,441), so a null there is a finding today;
2. the differential is **negative with a CI excluding zero**;
3. **IS and OOS disagree in sign** with both CIs excluding zero;
4. **H1 fails with adequate power**: the R4 differential does not exceed the R0
   differential, at a sample able to detect a 5pp gap. This is the refutation that
   matters most — it says the conjunction is the sum of its parts at best, and the
   corpus's central claim is that it is not.

### 5.3 INDETERMINATE

**Any** of:

1. `n` at the rung under test is **below the power floor for a 5pp effect (868 real
   trades)** — which §3 predicts, *on the certified span*, for R4 on the primary 15m
   stack (722, below 868) and on the swing stack (176), and for every K-rung
   (43 / 187 / 24 and every SMT variant). It does **not** apply to the 5m playbook stack
   at R4 (2,234), which clears the floor comfortably — a null there is a finding;
2. the sign flips across the two declared CISD level rules or the two C3 references;
3. the sign depends on the cost level within 0.0–0.5;
4. the harness sanity floor (§4.1.3) trips anywhere in the book;
5. on the extended sample, the sign fails the regime-block agreement requirement of
   §4.4b (agreement in ≥ 3 of 4 calendar blocks) — reported as **regime-dependent**, with
   the carrying block named.

**An indeterminate result must be reported as "this dataset cannot answer this", with
the required data volume from §3.7 attached — never as "we found no edge".** The two are
different claims and phase 2 established the habit of separating them: *"refuted on 15m
and 1h, underpowered on 4h and 1D"* was worth more than a single verdict the sample could
not support.

### 5.4 The shrinking-sample trap, and how it is caught

**A gate that improves win rate purely by shrinking `n` toward rarer, larger-R setups is
not evidence of edge.** This is the most likely way the conjunction produces a
false positive, because every gate in the ladder is a selector and the ladder removes 95%
of events by R4. Pre-declared machinery:

1. **The matched control neutralises it by construction.** The control shares direction,
   stop distance, target distance and local window. A gate that merely finds
   bigger-R or higher-volatility setups improves both arms equally and the differential
   does not move. **The verdict is read off the differential, never the raw rate**
   (§2.4), and this is why.
2. **Report stop distance per rung**, in USD/oz **and** in ATR(20) units at the signal
   bar. A monotone rise in mean stop/ATR across R0 → R4 alongside a rising raw win rate
   and a flat differential is the signature, and it is to be labelled
   **"selection artefact"** in those words.
3. **Stratify.** Recompute the R4 differential within terciles of stop/ATR(20) and
   within terciles of realised volatility. A real edge survives inside strata; a
   composition effect does not.
4. **Report total R per year** (§2.3 item 6). A gate that raises per-trade expectancy
   0.05 R while cutting `n` from 2,950 to 454 is a worse account, and calling it an
   improvement is a category error.
5. **Report the hold-time and time-exit share per rung.** A gate that selects longer
   holds gets more chances to reach a 2R target and will look better at fixed R without
   any predictive content; if mean bars-to-resolution moves monotonically with the win
   rate, say so.
6. **Report the win rate at a fixed *dollar* target as a cross-check**, not only at a
   fixed R multiple. If the two disagree, the R-multiple version is being driven by stop
   sizing.

### 5.4b The timeframe gradient — declared in advance, with its discriminator

The coordinator's rung-0 baseline (§2.5) shows the differential growing monotonically
with timeframe — **+0.0097 → +0.0642 → +0.1227 R** at 15m → 1h → 4h — while `n`
collapses **15,235 → 3,624 → 950**. **That is simultaneously the exact shape a shrinking
sample manufactures and the exact shape a real higher-timeframe effect would take.** It
is pre-registered here as an expectation, because it will almost certainly reappear
along the full ladder (§3.2: `n` falls by ~20× from R0 to R4), and because deciding what
it means *after* seeing it is how the C2 wick claim survived counting for a year.

Four discriminators, all pre-declared, run before any interpretation of the gradient:

1. **The subsample calibration — the decisive one.** Take the highest-`n` timeframe,
   draw **1,000 random subsamples of exactly the low-`n` timeframe's size**, and compute
   the differential in each. Report the fraction of subsamples reaching the high-TF point
   estimate. This answers the trap's question directly and quantitatively: *how often
   does n = 950 manufacture +0.12 R when the underlying truth is +0.01 R?* If the answer
   is "often", the gradient is noise and must be reported as noise. If the answer is
   "essentially never", the timeframes genuinely differ. This is cheap, it needs no new
   theory, and its result is not negotiable after the fact.

2. **Incompatibility, not ordering.** A monotone sequence of point estimates inside
   overlapping confidence intervals is not a gradient. The pre-registered test is whether
   the **low-timeframe estimate's CI excludes the high-timeframe point estimate** (and
   vice versa). Where the CIs overlap, the gradient is **unresolved** and is reported as
   unresolved — the ordering of three point estimates is not evidence.

3. **Equalise the hold window.** `max_hold = 10` entry-TF periods gives a 4h trade 40
   hours and a 15m trade 2.5 hours. A longer window raises the chance of touching either
   barrier, and under any positive drift it favours the target. Re-resolve the whole book
   with `max_hold` set to the **same wall-clock duration** across timeframes and report
   whether the gradient survives; report the time-exit share per timeframe alongside. If
   the gradient collapses under equal wall-clock holds it is a hold-window artefact, not
   a timeframe effect.

4. **Persistence.** The gradient must hold **separately in IS and in OOS**, in the same
   order. Phase 2's 4h residue had the right sign and size and still failed this — it was
   +0.194 R OOS with a CI clearing zero, but +0.053 R IS with a CI that did not, on twice
   the data.

**Pre-declared reading.** If discriminator 1 shows the high-TF estimate is reachable by
chance at that `n`, or if 2 shows overlapping CIs, the gradient is **INDETERMINATE** and
the higher timeframes are reported as underpowered — exactly the verdict
`backtest_c2_wick.md` §8 reached for 4h and 1D. It is worth stating now that this is the
*expected* outcome: §3.4 puts the 4h-class floors at 5.7–12.0 pp against a 3–5 pp
plausible effect, so a genuine higher-timeframe gradient is very unlikely to be
*resolvable* here even if it is real.

### 5.5 What must appear in the output regardless of outcome

- Every rung of both ladders on all four stacks, with `n`, even where `n` is too small to
  test — the table of what could not be measured is a deliverable in its own right.
- The `n` and MDE table of §3 recomputed from the run, so the pre-registered floors can
  be checked against the realised ones.
- The M1-vs-signal-timeframe resolution diagnostic (§4.2).
- The CISD level-rule and C3-reference disagreement rates.
- The no-lookahead assertion's pass/fail (§4.1).
- The control's realised matching quality: the distribution of `|control stop − real
  stop|` (should be identically zero) and of the entry-time offset (should lie inside
  ±30 days), confirming §4.3 was applied as locked.
- **The rung-0 differential on every stack**, reported first and separately, so that
  every later rung is read against it rather than against zero (§2.5).
- The §5.4b subsample-calibration result and the equal-wall-clock-hold re-resolution,
  whenever any timeframe or rung gradient is discussed.
- On the extended sample: the **certified usable span** from `meta/xau_history_audit.md`,
  the **re-measured event rates per year** (§3.7.2b), and the §3.7.1 degradation row that
  applies — before any differential is quoted.
- On the extended sample: **per-block differentials for all four calendar blocks** with
  CIs, and the §4.4b sign-agreement determination (§4.4b).
- The full family-C sweep curves, IS beside OOS.
- A statement of which of §5.1 / §5.2 / §5.3 applies, in those words.

---

## 6. What this document does not cover

Named so that nobody later mistakes an omission for a decision.

- **SMT / correlated assets.** The method uses `gold-in-euro` and `gold-in-pound` as
  gold's correlated set (`gold-correlated-assets`) and SMT is a substitute for the sweep
  in three separate places (`smt-swing-point-substitute`, spec §3.8, §4.5). **One
  instrument cannot test it**, however long the history. It is out of scope here and is
  now the *primary* argument for the multi-instrument extension, since §3.7.3 removes the
  statistical-power argument for it.
- **The relevant-swing filter**, **"relevant"/"key" level**, **ADR budget**, **"messy"
  structure**, **bias strength scoring**, and **the three entry-quality criteria** — all
  **[GAP]** in the corpus, all absent from the primary, all listed in §1 where they bite.
- **The T-spot**, whose derivation is **[WITHHELD]**, and the indicator's actual C2/C3/C4
  conditions, which are **paywalled at source** (spec §9.1). A faithful reimplementation
  is blocked there, and this is a ceiling on the project, not a gap in the corpus.
- **Profile classification beyond the Seek & Destroy stand-aside** (§1.5).
- **Anything that would revisit the C2 wick claim on this data.** Two independent methods
  agree there is nothing at 15m/1h; a third look at the same three years is p-hacking,
  not replication (`backtest_c2_wick.md` §8).

---

## 7. Reproducing the power estimates

```
cd ClaudeTradingRD/research

# the powered comparison -- the stack the verdict should be read from
..\.venv\Scripts\python.exe -u python/estimate_conjunction_power.py     --span certified --stacks 5min

# primary and swing stacks
..\.venv\Scripts\python.exe -u python/estimate_conjunction_power.py     --span certified --stacks 15min,1h

# declared robustness exclusion (3.7.2c)
..\.venv\Scripts\python.exe -u python/estimate_conjunction_power.py     --span certified --exclude-tick-regression

# the secondary reading of the largest lever (3.1)
..\.venv\Scripts\python.exe -u python/estimate_conjunction_power.py     --span certified --cisd-scope wick

# phase-2 continuity
..\.venv\Scripts\python.exe -u python/estimate_conjunction_power.py --span 3y
```

Offline; reads only the M1 parquets and the XAG correlate. The span is read from the
data, so every calendar figure rescales automatically. The run asserts the section 3.4
cross-check (X pp and 3X-in-R floors must agree) and aborts if it fails.

Runtime is dominated by `poi_gate_events`, which is per event: ~4 minutes for the 15m
stack on the certified span, ~20 for 5m, ~1 for 1h. **The 1m stack is not run on the
certified span** -- it is off-method (`excluded-tooling`) and would take hours. Always
use `-u`: a buffered run of the 5m certified stack appeared to have produced nothing for
twenty minutes and was nearly re-run needlessly.

Gates are the **real** `detectors/bias.py` and `detectors/poi.py` modules as of amendment
A3; the proxy implementations this file originally carried are gone.

---

## 8. Amendment log

This document requires of itself that changes be recorded rather than silently edited.

**A1 — 2026-08-25, before any conjunction result existed. Arithmetic correction: the
calendar requirement was overstated 3.33×.** The first version computed data
requirements with `4p(1−p)(z/e)²`, the sample size for a comparison in which *both* arms
are real trades. The primary test compares a rung against a **matched control resampled
from history already held**, which costs no calendar time, so the calendar requirement is
`p(1−p)(1+1/K)(z/e)²` **real** trades. At the locked K = 5 the overstatement is
`4K/(K+1)` = 3.33×. Raised by the coordinator's independent recomputation, which found a
3.00× discrepancy against their own K = 3 check; both figures are explained by the same
formula.

Affected and corrected: §3.4 (years columns, and the new real-vs-equal-split table), §3.6
(verdict), §3.7 (requirements), §5.2 and §5.3 (the 5pp power floor, 2,893 → **868 real
trades**), and `n_for_effect` / `n_real_for_effect` in
`python/estimate_conjunction_power.py`. **MDE values were correct throughout and are
unchanged.** The R-expectancy floors were also already correct, which is what produced
the internal inconsistency that should have caught this: a 4pp requirement of 4,521 sat
beside an equivalent 0.12R requirement of 1,356 in the same section. That cross-check is
now an assertion in the script.

**A2 — 2026-08-25, same session. Data availability: XAU_USD M1 confirmed to 2010-01-03.**
OANDA's practice API serves ~16.5 raw years against the 3.06 then held; a fetch and audit was in
flight. §3.6, §3.7 and the opening summary are rewritten around this. The recommendation
in the withdrawn §3.7 — fan out to seven instruments for statistical power — **is
superseded**: extending gold history is cheaper and sufficient, and multi-instrument work
is now justified on SMT and cross-market-replication grounds instead. Added §3.7.1
(degradation table by certified span), §3.7.2 (regime-heterogeneity, event-rate and
data-quality caveats), §4.4's **PRE** block, and **§4.4b regime blocking**, which is
pre-declared here *before* the extended data exists precisely so the blocks cannot be
chosen to suit a result.

**A3 — 2026-08-25, before any conjunction result existed. The ladder moved from the day
layer to the event layer, and SMT was demoted from the primary to a declared knob.**

The real `detectors/bias.py` and `detectors/poi.py` modules replaced this document's
proxy gate estimates. Measured, day-level intersection of the gates leaves **9 qualifying
days in 788** (~3 per year), and **the same 9 in the 2,724-day certified span** — the
extra seven years add none, because the SMT correlate does not reach back that far. Even
16.5 years would yield roughly 50 qualifying days. **A day-level conjunction is
undecidable at any history length**, so the unit of analysis became a CISD event on the
entry timeframe, with the daily gates joined onto it as lookahead-free context columns
(§2.0, §4.1a).

The diagnosis matters as much as the decision, and both are recorded:

- **`no_fade` fires on 100% of days and is definitionally redundant**, not empirically
  weak — a confirmed daily bias already entails a daily candle closing that way, so the
  gate cannot fail once the bias gate has passed. Removed as a ladder rung; retained as a
  self-consistency assertion on the bias module.
- **`POI` removes 0 days of 788 and 1 of 2,724 — because it was applied at the wrong
  resolution**, not because it is weak. A whole day of hourly bars almost always contains
  some FVG or sweepable swing. At the event layer it removes ~20%: hourly
  3,679 → 2,953 and 15m 15,255 → 12,635 at the detector's default `max_wait`, and
  81.4% / 80.4% retention at the locked parameters. This reverses the withdrawn proxy
  conclusion that POI was a free rider.
- **SMT demoted from the primary configuration to declared knob K2** (§2.1a). It alone
  takes the day-level stack from 31 days to 9, and the event-layer primary stack from 722
  events to 41. Keeping it in the primary would guarantee an undecidable primary
  hypothesis at *any* history length, which violates §5.3's own requirement that the
  primary be answerable. ~~It is additionally unmeasurable on the certified span: the XAG
  correlate begins 2023-07-02, so every SMT event in a ten-year run falls inside the last
  three years.~~ **← WITHDRAWN BY A5: this second clause was false.** XAG is served from
  2010-01-03; the 2023 start was a fetch default. The demotion stands on the frequency
  argument alone.

Consequences elsewhere: §3.2, §3.3 and §3.4 are re-measured; the leave-one-out
multipliers tighten from a proxy range of ×1.05–×10.8 to a measured ×1.19–×2.75, which
materially **improves** the ladder's ability to attribute an effect to a gate. Amendment
A3 also records that the proxy's profile gate was badly wrong (~93% retention against a
measured 14.5%), so every count from R1 down was an upper bound by roughly 5×, as it was
flagged to be.

**A4 — 2026-08-25, before any conjunction result existed. The certified span is 10.55
years, not the ~16.5 announced in A2.**

The completed audit (`meta/xau_history_audit.md`) found a **trading-calendar change in
October 2015**: NY hour 17 carries 1,813–3,726 bars per year from 2010 through September
2015 and **exactly zero** thereafter, with the 2015 monthly series unambiguous
(Sep 142 → Oct 0). Gold traded a genuine 24-hour day before that; 2011 additionally
carries 434 Saturday bars. This is a market-structure change, not a data defect, which
makes it more dangerous rather than less: **every gate in the locked configuration is
session- or daily-calendar-dependent, and on pre-2015 data none of them fails — they
quietly compute different objects.** The document is therefore re-anchored on
**2016-01-01 → 2026-07-23, 3,687,209 M1 bars, 10.55 years**, with pre-2016 admissible as
regime and higher-timeframe evidence only, disqualified by the calendar rather than by
quality.

A2's recommendation — *extend the gold history, and instruments are not the power
argument* — is **partly superseded**. Extending the history was right and delivered a
5.2× sample and a floor cut from 12.5pp to 5.5pp, but the trustworthy record is now
exhausted at 10.55 years and the primary stack still needs 12.7 years for a 5pp effect.
**More instruments is once again the only route to a 3–4pp floor** (§3.7.3).

Two consequences A2 could not have known, both recorded because they bound what this test
can ever conclude:

- **The only sustained gold bear market in the whole 16.5-year record is 2013 (−28%), and
  it falls on the wrong side of the calendar break.** The four-quarter regime blocking
  pre-declared in §4.4b therefore **cannot test the method against a sustained downtrend
  on trustworthy data**, and no result may be described as having been. Stated in the
  opening summary as well as in §3.7.2(a) and §4.4b.
- **The flat USD/oz cost model was the one non-scale-free quantity in the locked
  configuration.** Median daily range ran $15.3 → $90.3 across the span (1.21% → 1.94%
  in relative terms), so a flat 0.2 USD/oz round trip is a 5× different relative tax at
  the two ends. **The proportional `0.04R` column is promoted to the primary cost basis**
  and the flat levels are demoted to diagnostics (§1.15). Every other locked threshold was
  checked individually and confirmed scale-free (§3.7.2b). This is the only change A4
  makes to §1, and it makes the test stricter.

Also recorded from the audit: the seam is clean (6,709 overlapping timestamps agreeing to
exactly 0.0 on all four OHLC fields); **2019-02 → 2020-02 is a declared robustness
exclusion** and the primary result must be reported with and without it (§3.7.2c); and
the legacy 3-year file is **missing 2025-12-09 and 2026-01-21** entirely, so phase 2's
numbers — and this document's 3-year comparison figures — were computed on marginally
incomplete data (§3.7.4).

**A5 — 2026-08-25, before any conjunction result existed. A3's SMT reasoning had two
grounds; one of them is withdrawn. The demotion itself is unchanged.**

A3 demoted SMT from the primary configuration to declared knob K2 on **two independent
grounds**:

- **(a) Frequency.** SMT alone takes the day-level stack from 153 days to 54 on the
  certified span, and the event-layer primary stack from 722 events to 252 — a **9.3pp**
  floor against a 3–5pp plausible effect. Including it would guarantee an undecidable
  primary hypothesis, violating §5.3's own requirement that the primary be answerable.
- **(b) Apparent unmeasurability before 2023.** A3 and A4 additionally claimed the XAG
  correlate began 2023-07-02, so a decade-long run would carry only three years of SMT
  and "the same 9 days".

> **Ground (b) is WITHDRAWN. It was never true.** XAG_USD H1 is served by OANDA from
> **2010-01-03**, the same as gold. The 2023-07-02 start of `xag_h1.parquet` was
> `fetch_correlated.py`'s `DEFAULT_START` — a default inherited from the *gold 3-year*
> window, not a property of the data source. See §4.1b.
>
> **Ground (a) stands on its own, so the demotion is unchanged.** SMT remains knob K2,
> outside the primary configuration. **This amendment is not a reason to promote SMT back
> into the primary**, and a later reader should not read it as one: the frequency argument
> was always sufficient by itself, and re-measurement on ten years has now confirmed it on
> five times the data rather than weakened it.

What changed factually, all **re-measured on the certified span rather than scaled**, per
§3.7.1's own rule:

| | A3/A4 claim | A5 measured |
|---|---|---|
| XAG coverage | 2023-07-02 onward | **2010-01-03 onward**, 100,168 H1 bars |
| day-level cascade end | 9 days (“same 9”) | **54 days**, ~5/yr |
| K2, 15m primary stack | 41 events, 23.0pp | **252 events, 9.3pp** |
| K2, 5m playbook stack | 130 events, 12.9pp | **792 events, 5.2pp** |
| K2, 1H swing stack | 7 events, 55.7pp | **63 events, 18.6pp** |
| gate_smt standalone | 7.1% of days (3y only) | **8.9% of days** across the decade |

**A finding in its own right: the correlate is stable across ten years.** H1 return
correlation is **0.762** on the certified span against **0.766** on the 3-year window,
with **99.8%** of bars shared. That near-identity a decade apart means **the SMT premise
does not rest on a single regime the way rung 0 appears to** — which is a genuinely
useful thing to know before designing any future test that leans on it.

Files installed under non-colliding names, so nothing in flight was disturbed:
`xag_h1_full.parquet`, `xag_d1_full.parquet`, `eur_h1_full.parquet`, `eur_d1_full.parquet`.
`estimate_conjunction_power.load_correlate` now prefers the deep series and carries the
explanation in its docstring so the mistake cannot be repeated silently.

The generalisable lesson — **a default masquerading as a finding** — is recorded in
§4.1b beside the SMT join bug, because the two share a shape: a property of the harness
read as a property of the market.

**A1–A5 were all made before any conjunction result existed**, as were A1 and A2.
The conjunction backtest has been dispatched and has produced nothing at the time of
writing. Every amendment in this log to date is therefore blind to outcomes; any future
entry made after results are seen must say so explicitly, because that distinction is the
entire value of the log.

**Unchanged by A1–A5, and not reopened:** the locked configuration (§1) apart from the
cost basis in A4 and the parameters explicitly named in A3, the ladder's logic (§2)
apart from its layer, the no-lookahead precondition (§4.1), the matched-control
specification (§4.3), the forbidden-metrics list (§4.7), rung 0 as the comparator (§2.5),
and the interpretation rules (§5) apart from the numeric floors named in A1.

---

**Signed off before results exist.** Any change to §1, §2, §4 or §5 after a conjunction
result has been seen must be recorded here as a further amendment with a date and a
reason, in the manner of `RESUME.md`'s amended finding 4 — never as a silent edit.
