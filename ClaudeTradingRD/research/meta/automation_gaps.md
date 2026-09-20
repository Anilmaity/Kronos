# Automation gaps

Across **505 concepts** there are **3150 recorded ambiguities**. **255** concepts are not directly implementable (`underspecified` or `contested`).

The useful observation is that these are not 56 independent problems. A handful of undefined terms gate most of them, so defining one term unblocks many detectors at once.

## Undefined terms, ranked by concepts blocked

| term | concepts blocked | examples |
|---|---:|---|
| **session** | 68 | `average-daily-range`, `broadening-formation`, `chart-timezone-est`, `cisd` |
| **consolidation** | 47 | `breaker-block`, `cisd`, `consolidation`, `consolidation-avoidance` |
| **displacement** | 37 | `a-plus-entry-checklist`, `box-setup`, `breaker-block`, `breakeven-after-new-protected-swing` |
| **aggressive** | 34 | `aggressive-expansion-no-retracement`, `balanced-price-range-overlap`, `box-setup`, `breaker-block` |
| **timezone** | 34 | `daily-bias-framework`, `daily-candle-profile-open-low-first`, `daily-close-only-bias`, `daily-open-eighteen-hundred` |
| **strong** | 26 | `bias-confirmation-tradeoff`, `c2-confirmation-scaling`, `classic-expansion-week`, `consolidation` |
| **shallow** | 23 | `aggressive-expansion-no-retracement`, `classic-expansion-week`, `consolidation`, `continuation-signature` |
| **relevant** | 21 | `cisd`, `continuation-failure-short-term-target`, `daily-orderflow-confirms-draw`, `daily-wick-confirmation-timeframes` |
| **eq** | 21 | `daily-bias-c2-c3-h1-cisd`, `daily-candle-profile-open-low-first`, `daily-ohlc-candle-shape`, `deep-premium-deep-discount` |
| **equilibrium** | 13 | `daily-bias-c2-c3-h1-cisd`, `daily-ohlc-candle-shape`, `discount-requirement-before-entry`, `equilibrium-eq` |
| **small wick** | 13 | `aligning-expansion-candles`, `displacement`, `expansion-signature`, `fractal-model-c2` |
| **large wick** | 11 | `breaker-block`, `daily-bias-c2-c3-h1-cisd`, `equilibrium-eq`, `half-wick-respect` |
| **clean** | 11 | `cisd`, `daily-ohlc-candle-shape`, `dollar-gate-for-fx`, `midweek-reversal-week` |
| **t-spot** | 10 | `consolidation-reversal-week`, `daily-bias-c2-c3-h1-cisd`, `daily-tspot-open-poi`, `equilibrium-eq` |
| **protected swing** | 10 | `asia-session-c2-protected-swing`, `breakeven-after-new-protected-swing`, `consolidation-vs-retracement-test`, `harder-target-behind-protected-swing` |
| **obvious** | 9 | `buyside-sellside-liquidity`, `gap-open-adr-budget`, `htf-poi-gate-before-ltf`, `mechanical-trade-management` |
| **average daily range** | 9 | `average-daily-range`, `average-daily-range-targeting`, `breakeven-after-new-protected-swing`, `expansion-exhaustion-avoid-price` |
| **adr** | 8 | `adr-remaining-filter`, `dollar-gate-for-fx`, `intraweek-reversal-week`, `invalidation-first-timeframe-selection` |
| **most of the** | 5 | `est-timezone-anchor`, `rebalance`, `root-cause-diagnosis`, `seek-and-destroy-profile` |
| **significant** | 3 | `dont-trade-after-expansion`, `mmxm-phase-sequence`, `thursday-counter-week` |
| **relatively equal** | 3 | `failure-swing`, `relatively-equal-highs-lows`, `smt-reversal-continuation-double` |
| **exhaustion** | 1 | `clean-day-criteria` |
| **standard deviation** | 1 | `new-york-manipulation-profile` |

## Not directly implementable, by category

### entry (45)

- `a-plus-entry-checklist` (contested, ttrades) — EVOLUTION, NOT CONTRADICTION: this is the EARLIER recording. The later 0xygpCMwxbQ states a HARD gate - no lower-timeframe liquidity raid, no inter...
- `box-setup` (contested, ttrades) — 'Aggressive' is never quantified in either direction; it is the single decision the whole model turns on.
- `breaker-block` (contested, mixed) — 'Down close candles from the first high to the first low' does not say whether the zone is their combined open-to-close body span or the full high-...
- `breaker-continuation` (contested, ttrades) — 'Wicks kind of everywhere' is the stated trigger for switching to bodies; no test for messiness is given.
- `cisd` (contested, ttrades) — The word 'displacement' appears in the PDF definition ('close and displacement below the opening price') but every chart narration reduces it to 'w...
- `consequent-encroachment` (contested, ttrades) — Whether the fib is anchored wick-to-wick on the outer candles or to the gap boundary prices themselves is not stated (they differ).
- `continuation-failure-consolidation` (contested, ttrades) — No candle count is given in these Shorts for how long a failed recovery may take before reclassification is forced (the library's v-shape-reversal-...
- `continuation-order-block` (contested, ttrades) — He states a preference for the first continuation over later ones ('I feel like I'm chasing') without a rule for how many are acceptable.
- `continuation-timing` (contested, ttrades) — 'Early into the candle' is never given as a fraction of the period; the 40-minutes case is one example on an hourly, not a stated cut-off.
- `daily-tspot-open-poi` (underspecified, guest) — The T-spot is NEVER DEFINED in this video - it is an output of the TTFM fractal indicator and its construction is not explained, which is why this ...
- `discount-requirement-before-entry` (contested, guest) — The exact OTE band (0.62-0.79 in common ICT usage) is never spoken - only 'above equilibrium' and 'OTE' are said.
- `dont-trade-after-expansion` (contested, ttrades) — 'The end of' the candle is not defined as a fraction of elapsed time or of range.
- `equilibrium-eq` (contested, ttrades) — Three distinct levels share one name within a single unit; nothing in the material disambiguates them when 'the EQ' is used without qualification.
- `four-hour-wick-positioning` (underspecified, guest) — Inverting something inside the wick is the trigger and is never defined - it may be an inversion fair value gap, a close through a level, or someth...
- `hourly-cisd-confirmation` (contested, ttrades) — The scope of the search is stated inconsistently across the series: 'inside this wick' (Classic Expansion) versus 'inside that candle two' / 'insid...
- `hourly-cisd-manipulation-confirmation` (contested, guest) — Body close or wick close through the up-close candle is not specified.
- `htf-opening-price-entry` (contested, ttrades) — 'Near the opening price' is never bounded as a distance or fraction of the candle.
- `htf-reaction-mss-retrace-entry` (contested, guest) — Neither speaker quantifies the size of the structure break; $niper requires displacement with a fair value gap, Trader T requires only a break.
- `htf-two-entry-opportunities` (underspecified, guest) — 'Opportunity' is never defined; in the one worked example it is a tap into a daily fair value gap, but no rule says which fair value gaps qualify.
- `ic-cisd` (contested, ttrades) — The IC-CISD inherits the unresolved 'level of the series' question from the CISD definition.
- `ict-2022-mentorship-model` (underspecified, ttrades) — 'Displacement' carries no threshold here (as everywhere in the corpus), so the sequence is not decidable without an external displacement definition.
- `invalidation-first-timeframe-selection` (contested, ttrades) — 'If I can manage my risk' is not turned into a test - no maximum stop distance in points, percent of ADR, or R terms.
- `level-to-trade-away-from` (contested, ttrades) — "Relevant point of interest" and "key level" are used interchangeably in the clip and neither is defined here.
- `ltf-inversion-entry-in-tspot` (contested, ttrades) — The t-spot is drawn by his indicator and its derivation is not given in this video.
- `mean-threshold` (contested, ttrades) — The transcript renders '0.5 fib' as '8.5 FIB'; it is read as 0.5 (the 50% level), consistent with the rest of the corpus and with the arithmetic of...
- `mitigation-block` (contested, mixed) — EVOLUTION / DIVERGENCE, NOT CONTRADICTION: the library already holds two readings of this id - a four-point swing sequence with no sweep, and a gue...
- `no-shorting-below-lows` (contested, ttrades) — How far below the lows the rule starts to bite is not quantified; both examples were visually obvious.
- `old-fvg-across-the-curve` (underspecified, ttrades) — No rule for which old gaps to carry forward or how many — the examples pick visually obvious ones.
- `opening-price-breaker` (underspecified, guest) — No stop-loss placement is given anywhere in the talk.
- `opposing-run-entry` (contested, ttrades) — 'At' a time level is not bounded — how many minutes after 08:30 or 09:30 an opposing run still counts is never stated.
- `optimal-trade-entry` (contested, mixed) — EARLIER RECORDINGS. The OTE band's boundaries are never stated as numbers; 0.62 and 0.625 are read off charts, and 0.79 / 0.705 never appear in thi...
- `order-of-reversal` (contested, ttrades) — ORDERING CONFLICT: this Short pairs steps four and five as 'the fair value gap or the breaker' and does not separate them; the long-form entry in t...
- `oversized-fvg-handling` (underspecified, guest) — 'Big' is never quantified - no ATR multiple, point threshold or ratio to the execution timeframe's candle size.
- `point-of-interest` (contested, ttrades) — No ranking is given when several points of interest are available; the stated method is to wait and see which one a swing actually forms at.
- `positional-entry` (contested, ttrades) — 'Beyond the EQ' is stated for the ideal case, but one final example accepts a protected swing that 'doesn't technically cover the EQ' on the ground...
- `positional-entry-before-open` (contested, ttrades) — "A protected swing I can trust" adds a trust qualifier on top of the structural definition and never says what makes one untrustworthy.
- `rr-gated-entry-refinement` (contested, ttrades) — No minimum acceptable ratio is stated in this video; 1.79R is called 'not horrible'. The 2R minimum recorded elsewhere in the corpus is absent here.
- `seek-destroy-outside-in-entry` (underspecified, ttrades) — No stop placement is ever given, which makes the method unbacktestable as stated.
- `silver-bullet-breaker-requirement` (contested, guest) — Marked contested because this definition carries NO time component. The name is normally associated in ICT material with a fixed intraday window; t...
- `standard-deviation-projection` (contested, mixed) — Anchor ambiguity: the video says to project the manipulation leg but anchors 'from our high to our low', which combined with the indicator drawing ...
- `t-spot` (contested, ttrades) — The derivation of the T-spot is never given in the free material - it is only ever described by its function. One example equates it with the equil...
- `three-entry-quality-criteria` (underspecified, ttrades) — He states outright that he has not figured out how to define these mechanically.
- `trading-without-structure-shift` (contested, mixed) — 'Aggressive' is the load-bearing word in both branches and is never quantified - no candle-range, ATR or bar-count threshold is given.
- `turtle-soup-sweep-entry` (contested, ttrades) — The stop is described only as 'fixed' - no distance, no reference level.
- `unicorn-candle-count-filter` (underspecified, guest) — The threshold is a range ('10 to 12 or less') with no hard cut, so it is not decidable at the boundary - hence underspecified.

### liquidity (20)

- `buyside-sellside-liquidity` (contested, ttrades) — This is the EARLIER of two recordings of this topic; the updated playlist version (the_foundation_01) is the reference reading. The two agree in su...
- `delta-divergence-recency-limit` (underspecified, guest) — 'Too far' is given only by the four-hour counter-example; the actual cut-off is not stated.
- `draw-on-liquidity` (contested, ttrades) — EVOLUTION, NOT CONTRADICTION: the later FXJBFbZQbck collapses the draw to a binary between previous day high and previous day low; this earlier rec...
- `dxy-yields-smt-pair` (underspecified, guest) — He never says whether he charts bond PRICE or YIELD, which inverts the divergence reading.
- `engineered-liquidity-before-htf-array` (underspecified, guest) — 'Stop shy' has no distance attached - it could be one point or one percent.
- `external-range-liquidity` (contested, ttrades) — Which swing bounds 'the range' is judged visually; no algorithm selects it among nested swings.
- `high-vs-low-resistance-liquidity` (contested, ttrades) — 'A high or low with a failure swing' is decidable only relative to a chosen lookback: which price leg counts as 'the leg toward it' is not bounded ...
- `inducement-equals-sweep` (contested, ttrades) — The auto-captioner renders 'highs to be ran' as 'highest vram'; the meaning is fixed by the mirrored bullish clause in the same sentence.
- `internal-range-liquidity` (contested, ttrades) — Which timeframe's FVG counts as 'the' internal liquidity is not specified; one example uses a weekly FVG while working the 4H external swings.
- `old-accumulation-new-distribution` (contested, guest) — How wide the 'same zone' tolerance is - the new block only has to be inside the extended band, with no overlap fraction stated.
- `previous-period-high-low` (contested, ttrades) — 'Already taken out' has no lookback bound - how far back to keep marking extremes is not stated.
- `relatively-equal-highs-lows` (contested, ttrades) — 'Relatively equal' has no numeric tolerance anywhere in the unit — this is the blocking gap for detection.
- `relevant-level` (contested, ttrades) — 'Key level', 'relevant level', 'higher time frame objective' and 'the drawn liquidity' are used interchangeably across the series with no single de...
- `smt-as-confirmation-not-signal` (contested, ttrades) — The two videos are both in this older playlist and are not reconciled by the speaker.
- `smt-break-reversal-trigger` (underspecified, guest) — 'Clearly failed to manipulate' has no distance threshold.
- `smt-divergence` (contested, ttrades) — No comparison window is given: 'a certain high we are watching' is chosen visually and no rule bounds how far apart in time the two assets' reactio...
- `smt-divergence-confluence` (contested, guest) — Neither speaker gives a timeframe floor below which SMT should be ignored - Finessee_Fx warns about 1m and 5m but never rules them out formally.
- `smt-requires-framework` (contested, ttrades) — The doctrine is unambiguous, but it coexists in this unit with the SMT-as-swing-point substitute rule, where SMT DOES supply a missing structural p...
- `smt-reversal-continuation-double` (contested, ttrades) — Which correlated asset is authoritative is never specified; examples switch between ES, NQ and YM and one is described as 'a bit messy' for that re...
- `volume-spike-at-extremes` (underspecified, guest) — 'Spike' is never defined - no multiple of average volume, no lookback window, no threshold.

### model (54)

- `aligning-expansion-candles` (contested, ttrades) — 'Small wick' is the gate at every layer and is never quantified anywhere in this unit.
- `candle-two-closure-not-required` (contested, guest) — Marked contested because it explicitly conflicts with the candle 2 closure requirement taught in the TTrades fractal model elsewhere in this corpus...
- `consolidation-reversal-week` (contested, guest) — Whether Wednesday's close or Thursday's open defines the consolidation boundary is not stated.
- `continuation-failure-short-term-target` (contested, ttrades) — 'Scenario two' implies a numbered list of scenarios that is not enumerated in these Shorts.
- `continuation-over-reversal` (contested, ttrades) — He concedes continuation entry means a later, worse price in exchange for a higher win rate, but gives no numbers.
- `daily-bias-c2-c3-h1-cisd` (contested, ttrades) — The EQ used is the EQ of the PREVIOUS DAY'S RANGE here; elsewhere in the corpus 'EQ' means the current candle's equilibrium / T-spot. Both appear i...
- `daily-bias-framework` (contested, ttrades) — 'Displace out of this range' vs 'close outside' are used interchangeably; the operative test in every example is the CLOSE.
- `daily-bias-requirement` (contested, guest) — None of the four speakers addresses the others' position, so the conflict is inferred from the unit rather than debated in it.
- `daily-candle-profile-open-low-first` (contested, ttrades) — WHICH open is meant (the 18:00 open, midnight, or 09:30) is not stated in this Short.
- `daily-profile-confirmation` (contested, ttrades) — This is the crux and it is left open: "confirm or invalidate" is never given a test, so the concept stays underspecified. One clip shows confirmati...
- `daily-profile-framework` (underspecified, ttrades) — The decision tree above is assembled by the reader from four separate videos; the speaker never states it as a tree in one place.
- `dollar-gate-for-fx` (contested, mixed) — 'Agree' is never mechanised - it is whether the dollar's own PD-array read points the opposite way, judged by eye.
- `four-candle-model-window` (contested, ttrades) — The labelling is retrospective -- candle 2 is only known to be the swing point once candle 3 exists, which is exactly why candle 3 closures are nee...
- `fractal-model-c2` (contested, ttrades) — Body close versus wick close is implied by 'close back below' but never stated explicitly.
- `fractal-model-c3` (contested, ttrades) — 'Over the body of candle two' does not say whether the reference is C2's open or its close (they are the two body edges, and which one applies is n...
- `fractal-model-c4` (contested, ttrades) — 'Strong closure' / 'closes strong' in candle 3 is the gate for taking candle 4 and is never quantified.
- `framework-transfer` (underspecified, ttrades) — He states he 'also doesn't talk about this really anywhere' - only one worked example exists here.
- `ideal-formation` (contested, ttrades) — The Short does not bound the 'series of opposing candles' - the worked example happens to contain exactly two.
- `indicator-print-conditions` (contested, ttrades) — 'Aligned lower timeframe' is defined by the pairing table, which is itself only partially stated (daily->hourly, 4H->15m, hourly->5m).
- `inducement-model` (contested, ttrades) — EVOLUTION vs the Updated playlist: the later `Inducement` video (-GkOTMYoJT4) reduces this to a general definition ('a move that induces buyers or ...
- `internal-external-rotation` (contested, mixed) — When several unmitigated FVGs sit inside the range, no rule selects which is the draw — he uses proximity and premium/discount informally.
- `intraday-bias-three-inputs` (contested, ttrades) — EVOLUTION vs the Updated playlist: the later canonical intraday-bias video (6zTz7WMdMWg) derives bias from the PREVIOUS 4-HOUR CANDLE'S HIGH AND LO...
- `intraday-reversal` (underspecified, ttrades) — Whether the 4-hour closure and the hourly CISD must occur in a particular order, or simply both be present, is not stated.
- `intraweek-reversal-week` (contested, ttrades) — 'Already expanded a fair bit' is not quantified - no range or ADR fraction is given.
- `invalidation-trade` (contested, ttrades) — "The aligned time frame" is never defined - in the worked example the EQ was read on the hourly, but no rule maps a model to its aligned timeframe.
- `irl-erl-flowchart-model` (contested, ttrades) — THE KILL ZONE IS USED AS A HARD GATE AND ITS HOURS ARE NEVER GIVEN. Two of the three Shorts make it a requirement; one names London only as a label...
- `large-range-day-targeting` (underspecified, guest) — 'Large range' is never quantified - no ATR multiple, point threshold or percentile is given, which is why this entry is marked underspecified.
- `london-reversal-ny-continuation` (contested, ttrades) — The London session boundaries are never given in clock time in this unit.
- `london-reversal-profile` (contested, ttrades) — The London hours are given twice, as "2:5" and as "2 to 5", with NO timezone attached anywhere in the clip and no a.m./p.m. marker. Read as 02:00-0...
- `manipulation-first-heuristic` (underspecified, ttrades) — 'Aggressive' is the load-bearing term and is entirely undefined — no candle range, ATR multiple, velocity or bar-count criterion is given. Without ...
- `market-maker-model` (contested, ttrades) — EARLIER RECORDING and a single trade review - the model's phases are named in passing, never enumerated.
- `mean-reversion-3atr-21ema` (underspecified, guest) — ATR lookback period, chart timeframe, instrument and whether the rule is symmetric for longs and shorts are all unstated.
- `mmxm-hedging-program` (underspecified, guest) — The causal claim about central bank hedging is asserted, not evidenced beyond a single COT chart; marked underspecified because the mechanism is no...
- `mmxm-phase-sequence` (contested, guest) — 'Silver bullet' is used purely structurally here - it is the second distribution leg, with no time window of any kind attached.
- `mmxm-range-definition` (underspecified, guest) — 'The most obvious price swing where the high and low connect' is the entire range-selection rule and is purely visual; this is why the entry is mar...
- `mmxm-twitter-model` (contested, ttrades) — HEADLINE EVOLUTION FINDING: the same attributed model, the same channel, two different five-condition lists. This EARLIER recording is a timing/sel...
- `new-york-manipulation-profile` (contested, ttrades) — 'Consolidating' is never quantified. In one example London did make a high, and he simply substituted the current dealing range for the London range.
- `new-york-reversal-profile` (contested, ttrades) — 'Discount array' is used without a definition of which array or how the premium/discount range is anchored in this exchange.
- `next-day-model` (contested, ttrades) — 'Closes back into the range' — whether the close must be inside the previous candle's BODY or its full high-low range is never stated; the examples...
- `no-fading-the-daily-candle` (contested, ttrades) — The daily candle is still forming when the decision is made; no rule is given for how much of the day must have elapsed before its direction is tru...
- `power-of-three-amd` (contested, ttrades) — 'Generally I like to see' for the session sequence — it is an expectation, not a filter.
- `reversal-candle-target-adjustment` (contested, ttrades) — 'Large' opposing run remains unquantified.
- `seek-and-destroy-profile` (contested, mixed) — EVOLUTION vs the Updated playlist: the later canon (Tjk9bXERZy0) anticipates this profile from an EMPTY ECONOMIC CALENDAR ('a lack of news events')...
- `small-wick-expansion-rule` (contested, ttrades) — 'Small' is still unquantified in every one of these four Shorts - see wick-size-test.
- `smart-money-reversal` (contested, guest) — Never formally defined in any available transcript — the components are listed in passing in one video and assumed elsewhere.
- `tgif-setup` (contested, ttrades) — 'Candlestick confirmation' as an alternative to a CISD is not defined.
- `thursday-counter-week` (contested, ttrades) — 'A relevant level' is the trigger for expecting the counter and is not defined here.
- `timeframe-alignment-pairs` (contested, ttrades) — The pairing is stated as a fixed table but is also allowed to flex by one step for cleanliness - no rule says when flexing is permitted.
- `top-down-analysis-procedure` (contested, ttrades) — EVOLUTION vs the Updated playlist: the later canon fixes the ladder at Daily -> Hourly -> 5-minute in all three of its examples. This earlier versi...
- `ttfm-favorite-daily-4h-15m` (contested, ttrades) — "Around four R" is measured off the chart in the clip, not derived from a rule; it is an example, not a target policy.
- `ttfm-minimal-toolkit` (contested, ttrades) — The refusals are personal-preference statements, not claims that the tools do not work - he repeatedly tells viewers to use whatever they want as l...
- `unicorn-model` (contested, ttrades) — 'Overlapping' is not quantified — any overlap appears to qualify.
- `weekly-profile-alignment` (underspecified, guest) — Only three profiles are named here; the complete profile set is assumed from material outside this video.
- `weekly-profile-framework` (contested, ttrades) — The bias that must exist before applying the framework is sourced outside this unit; no bias-formation procedure is given in any of the six videos.

### psychology (9)

- `bias-confirmation-tradeoff` (contested, ttrades) — 'Strong bias' is never scored; the classification is entirely discretionary and he says so.
- `entry-timeframe-elevation` (contested, ttrades) — How far to keep elevating if the problem persists is not addressed.
- `journal-losers-only` (contested, guest) — Logging only losses means the base rate for the same pattern in winning trades is never recorded, so the avoidance decision is made on one half of ...
- `missed-move-no-chase` (contested, ttrades) — The boundary between 'a new phase of price' (tradeable) and 'a chase' (not) is judgemental; the only stated marker is a new swing plus a new contin...
- `pattern-trading-error` (contested, ttrades) — "Framework" is used interchangeably with bias, context and daily profile across the four streams and is never defined as a checklist.
- `post-trade-journaling-protocol` (contested, guest) — Neither gives a review cadence - when the log is read back, or against what benchmark.
- `root-cause-diagnosis` (contested, ttrades) — No minimum sample size is given before a category can be called a loser.
- `single-pd-array-mastery` (contested, mixed) — The selection criteria are subjective by design ('which is easiest for you to see'), so the rule cannot be applied mechanically.
- `tilt-stop-rule` (underspecified, guest) — The loss count is deliberately left unspecified - the speaker says the number differs for everybody - so the rule cannot be encoded without a user-...

### risk (30)

- `average-daily-range` (contested, ttrades) — No lookback length, no averaging method, no session basis (RTH vs full session) - he explicitly says he does not use an indicator.
- `average-daily-range-targeting` (underspecified, ttrades) — He is asked directly how to calculate average daily range and the question is not answered - the numbers are eyeballed off the chart.
- `break-even-management` (contested, mixed) — CONTESTED WITHIN THIS UNIT: the anti-break-even argument (CPI trade review) and the pro-break-even practice (15-second scalp) are both his, in the ...
- `breakeven-after-new-protected-swing` (contested, ttrades) — 'How much range is left' is judged by eye against the average daily range; no calculation is given.
- `chart-data-settings` (contested, ttrades) — One sentence in the futures video reads 'I have found that settlement works best for my strategy' immediately after he says he has settlement turne...
- `chart-futures-execute-elsewhere` (contested, mixed) — No adjustment is described for the price offset between ES and SPX, or between NQ and QQQ.
- `consolidation-range-no-trade` (contested, ttrades) — Sits in tension with range-edge-trading, where he does describe trading range edges back into the range. He does not state when a range is worth tr...
- `daily-range-budget` (underspecified, ttrades) — No lookback length or statistic (mean, median, percentile) is specified.
- `expansion-exhaustion-avoid-price` (contested, ttrades) — 'Very big' / 'large range' expansion days are never quantified, so the two-large-days trigger is not decidable from a chart.
- `harder-target-behind-protected-swing` (underspecified, ttrades) — "Protected swing" is used here as a property of the target rather than of the entry's invalidation, which is how the rest of the corpus uses it. Th...
- `htf-poi-gate-before-ltf` (contested, ttrades) — 'Reached' the point of interest is not defined as near edge, midpoint or full fill.
- `large-wick-target-adjustment` (contested, ttrades) — 'Larger wick' is not quantified - the threshold that separates it from a shallow run is the same unresolved judgement recorded in wick-size-test.
- `loss-and-gain-limit-rules` (underspecified, guest) — No numbers are given for any of the limits - the rule cannot be encoded without user-supplied parameters.
- `max-one-trade-per-day` (contested, ttrades) — The cap is justified psychologically, never with expectancy data.
- `mechanical-trade-management` (contested, guest) — Contested across three speakers with no shared test - the disagreement is doctrinal, and none of them cites data.
- `no-draw-no-trade` (contested, guest) — 'Clear' is not defined for either the monthly draw or the weekly expansion read.
- `partial-profit-taking` (contested, mixed) — The two readings are from different speakers (host vs interview guest) and neither addresses the other, so this is a corpus-level conflict rather t...
- `position-sizing` (contested, ttrades) — The two divisors given (10-15 and 7) are not reconciled; he presents the choice as a personal aggressiveness setting rather than a rule.
- `position-sizing-fixed-risk` (contested, mixed) — Four percent of the drawdown is conceded to be more than would normally be risked, and is justified only by a thirty-day deadline.
- `prop-account-scaling-plan` (underspecified, guest) — Very aggressive in phase 1 is not quantified in risk terms, and it directly contradicts the 1%-base scaling matrix he gives elsewhere in the same i...
- `prop-firm-drawdown-sizing` (contested, mixed) — The 25,000 / 1,500 framing is TTrades' own statement; the '10 percent to play with' arithmetic immediately preceding it is Trader T's. They converg...
- `range-market-avoidance` (underspecified, guest) — No threshold is given for a big enough range, so the trade-the-range branch is not decidable.
- `realistic-r-expectations` (contested, mixed) — The 63R figure is one student's result on one instrument over four months, presented on screen; it is not a backtest and no drawdown, sample-select...
- `risk-limits-and-trade-frequency` (contested, guest) — $niper says 'a session or a day I guess' - whether the counter resets between the AM and PM sessions is left open.
- `risk-reward-minimum` (contested, mixed) — 2R appears as a floor (6zTz7WMdMWg), a fixed target (mwmWNCTEYtY) and a preference (AdmnWLjf8rY) — the three uses are not reconciled.
- `stop-loss-placement` (contested, mixed) — 'A little bit more room than normal' for oil is not quantified.
- `stop-moves-when-adding` (contested, guest) — The size ratio between tranches is never given, so the blended entry and the true break-even price are undefined.
- `stop-size-reduction` (contested, mixed) — The two answers may be replies to two different questions - point distance versus dollar risk - but neither transcript disambiguates, and the quest...
- `trade-frequency-baseline` (contested, mixed) — The one-to-two-a-week figure is given for his own trading across his whole watchlist (indices plus gold plus occasional oil/dollar), not per instru...
- `trailing-stop-opposing-candles` (contested, ttrades) — Sourced from an ASR (whisper-small) transcript, not YouTube captions; wording may be imprecise.

### structure (65)

- `advanced-market-structure-labeling` (contested, ttrades) — The PDF definition of an intermediate-term point ('a short-term low with a higher short-term low on the right and left') and the chart procedure he...
- `aggressive-expansion-no-retracement` (underspecified, ttrades) — 'Aggressive' is never defined. No candle count, range, body-to-wick ratio or speed measure is given for what makes an expansion aggressive - the te...
- `aggressive-run-hammer-signature` (underspecified, ttrades) — No wick-to-body ratio is given, so 'hammer' here is a visual description, not a candlestick definition.
- `balanced-price-range-overlap` (contested, ttrades) — 'Aggressive' is again the load-bearing, unquantified word.
- `broadening-formation` (contested, mixed) — EVOLUTION, NOT CONTRADICTION: this earlier recording is framed as 'Strat + ICT part 1' and defines the formation as one high taking out another. Th...
- `consolidation` (underspecified, ttrades) — The definition is circular for automation purposes: consolidation is the absence of displacement, and displacement is itself never quantified in th...
- `consolidation-phase` (contested, ttrades) — DIRECT TENSION WITH THE LIBRARY'S EXISTING RULE. The library holds that the manipulated side is chosen BY BIAS (bullish requires the low to be run)...
- `consolidation-vs-retracement-test` (contested, ttrades) — The test is stated once, in passing, inside a longer example -- it is not presented as a named rule, so its intended generality is inferred from it...
- `continuation-signature` (contested, ttrades) — The three-way classifier is only as decidable as its inputs; consolidation is the only one of the three with a crisp test (price internal to a high...
- `cross-asset-reversal-confirmation` (contested, ttrades) — Reverses is defined only by V-shape displacement and closure back into the range, with no candle count.
- `cross-asset-target-transfer` (contested, ttrades) — 'Sometimes' - no rule says when this substitution applies.
- `currency-pairing-opposition` (contested, mixed) — Strength ranking is done visually from a watchlist; no metric or lookback is specified.
- `daily-ohlc-candle-shape` (contested, ttrades) — EVOLUTION / DIRECT CONFLICT: the daily open used in this recording is the MIDNIGHT opening price. The later canon anchors the daily candle at 18:00...
- `dealing-range-fib-grading` (underspecified, guest) — The fib's exact anchors are described only in words; the on-screen settings are shown but not read out, so the range cannot be reproduced reliably.
- `decoupling-realignment` (underspecified, ttrades) — No threshold defines 'decoupled' - the example used one index down ~0.63% while the other two were roughly flat on the day, but no percentage rule ...
- `displacement` (contested, mixed) — The four-candle window is the number used in his single worked comparison; he never states it as a parameter, so whether the window is fixed at 4 o...
- `eurgbp-relative-strength-cross` (contested, ttrades) — 'Consolidating' for the dollar reuses the consolidation definition and inherits its lack of a duration bound.
- `expansion-sequence-quality` (contested, ttrades) — 'Two candles' is the stated observation window in one example only; no general rule is given.
- `expansion-signature` (contested, ttrades) — 'Shallow' is never quantified. No percentage-of-leg, ATR multiple or fib level is given for the maximum counter-trend depth that still counts as ex...
- `failure-swing` (contested, ttrades) — CONTESTED against the corpus's other definition: elsewhere a failure swing is defined by not having swept prior liquidity. Here it is defined purel...
- `failure-to-displace` (contested, ttrades) — 'Not very aggressive' is the operative judgement on every chart and is never quantified beyond the candle-shape and comparative tests recorded unde...
- `fair-value-gap` (contested, mixed) — Asked directly at what point a gap counts as efficient, Finessee_Fx calls it a grey area that depends on context, then answers with the merge rule ...
- `half-wick-respect` (contested, mixed) — Two different 50% levels are used in the same corpus without being distinguished by name: 0.5 of the WICK (body-to-extreme, this concept) and 0.5 o...
- `htf-wick-formation` (contested, ttrades) — Sourced from an ASR (whisper-small) transcript, not YouTube captions; wording may be imprecise.
- `important-level` (underspecified, ttrades) — The list of qualifying levels is closed for continuation entries but explicitly open for reversal entries — the single biggest source of discretion...
- `intermarket-correlation-not-used` (contested, ttrades) — CONTESTED against mainstream ICT, which leans heavily on DXY and cross-asset correlation for bias. He offers an empirical claim (the correlation ha...
- `intermediate-term-swing-formation` (contested, mixed) — The bearish type-1 wording in the Short is loose - "a short-term high with a short-term high to its left and to its right" omits the LOWER qualifie...
- `intermediate-timeframe-bridge` (contested, mixed) — No time bound is given for how long the domino may take to complete.
- `inversion-fair-value-gap` (contested, ttrades) — 'Swiftly closed over' has no bar limit.
- `market-curve-side` (underspecified, ttrades) — NO RULE LOCATES THE CURVE. Nothing says where the buy side ends and the sell side begins - it is not tied to the range equilibrium, to a swing, or ...
- `market-structure-shift` (contested, mixed) — EVOLUTION vs the Updated playlist: the later canon (_94CPMjWi9E) adds two conditions absent here - a preferred stop raid before the break, and a RE...
- `order-block` (contested, mixed) — Whether the validating close must also displace (leave an FVG) is stated in E89d1HArbgM ('close and displacement') but only as 'closes below' in 7p...
- `order-block-requires-bos` (underspecified, guest) — 'CSS' is used repeatedly as a near-synonym with 'a little bit more rules' and those rules are never given, so the distinction between an order bloc...
- `original-consolidation-identification` (underspecified, guest) — 'A form of chop and consolidation' is the entire test and is never bounded - no candle count, range width or ATR fraction.
- `phases-of-price` (contested, ttrades) — "Large range" and "small range" are never given a measure - not in points, not as a multiple of the previous range, not versus an average.
- `phases-of-price-transitions` (contested, ttrades) — No threshold separates a retracement from a consolidation at the moment of transition - the distinction is made retrospectively.
- `premium-discount` (contested, ttrades) — EARLIER RECORDING. No precedence rule is given for when the displacement-range read and the overall-range read disagree - both are simply required ...
- `premium-discount-equilibrium` (contested, ttrades) — Selecting the most prominent range in the area is discretionary and has no algorithm; the speaker concedes the nesting gets confusing.
- `propulsion-block` (contested, ttrades) — Two different invalidation levels are used across the Shorts for the same object: "the mean threshold" and "the lower half of this". They may be th...
- `protected-swing` (contested, ttrades) — 'The series of opposing candles that made the extreme' is judged by eye; in several examples he chooses a different candle from the one the mechani...
- `psp-precision-swing-point` (contested, mixed) — No minimum body size; a doji-ish opposite close presumably counts.
- `ratio-chart-reversal-lead` (underspecified, ttrades) — The speaker frames this as an untested theory and solicits viewer feedback, so it carries no claimed hit rate.
- `relative-strength-asset-selection` (contested, ttrades) — 'Separation' is measured by eye off the chart; no normalisation (points, ATR, percentage) is given.
- `relative-strength-weakness` (contested, ttrades) — The three inputs are never weighted or ordered when they disagree.
- `relevant-htf-pd-array-test` (contested, ttrades) — 'Relevant' PD array is again asserted and never defined - this Short repeats the term without adding a test.
- `relevant-swing-separation` (contested, ttrades) — 400 points on NASDAQ is an instance, not a threshold - it is never normalised by ADR, timeframe or instrument, and no minimum is given.
- `relevant-swings-separation` (contested, ttrades) — He states directly that there is no mechanical rule for valid separation and that it comes from experience and discernment. This is the PRIMARY tea...
- `retracement-phase` (contested, ttrades) — THE SAME CONTRADICTION THE LIBRARY ALREADY CARRIES SURVIVES HERE, and these two Shorts are its clearest statement: one says the retracement is SLOW...
- `reversal-candle-quality` (contested, ttrades) — 'Candle 2 closure' itself is assumed knowledge from the TTrades Fractal Model playlists; its sweep-and-close-back definition is never restated anyw...
- `reversal-signature` (contested, ttrades) — 'Expansion met with expansion' inherits every ambiguity of 'expansion' - there is no threshold on either leg, so the test is decidable only once yo...
- `second-continuation-confirmation` (underspecified, guest) — What counts as a higher-timeframe key area is deliberately left open - the speaker declines to specify because different traders use different POIs...
- `small-wick-supports-expansion` (underspecified, guest) — No numeric threshold separates 'small' from 'large'; marked underspecified for that reason.
- `smt-swing-point-substitute` (contested, ttrades) — No rule for which correlated asset is authoritative when two disagree.
- `strat-two-two-reversal` (underspecified, ttrades) — The STRAT numeric candle classification (1 = inside bar, 2 = directional, 3 = outside bar) is never stated on air in this unit, so the pattern is o...
- `structure-requires-htf-context` (contested, mixed) — The rule is stated as a post-hoc read on charts already known to have failed; no forward test is given for deciding, at the time, whether the curre...
- `swing-forming-candle-selection` (contested, ttrades) — "Messy" and "small candles" are the trigger and are not defined - no candle-count, no range test.
- `swing-point` (contested, ttrades) — The three-candle test uses lows/highs, not bodies, but the same speaker elsewhere in this unit measures things body-to-body without saying which go...
- `three-drive-reversal-pattern` (underspecified, guest) — 'Three times above here' has no tolerance band - how close the three highs must be is not stated.
- `timeframe-alignment` (contested, ttrades) — 'Green' is read off his own indicator; the underlying colouring rule is not restated in these streams beyond the wick geometry.
- `trend-as-aggressive-move-to-objective` (underspecified, ttrades) — 'Aggressive' is the entire content of the definition and is never quantified anywhere in this unit - no ATR multiple, no body/range ratio, no candl...
- `upper-half-eq-expansion-filter` (contested, ttrades) — 'Respect' / 'hold' is not resolved into wick vs body - whether a wick through the EQ breaks the filter or only a close does is not stated in any of...
- `v-shape-reversal` (underspecified, ttrades) — No geometric definition (retracement fraction, bar count, wick/body ratio) is ever given.
- `v-shape-reversal-speed` (contested, ttrades) — The 1-3 candle count is stated as a preference ('I prefer', 'a lot of times') rather than a hard rule, and one accepted example is described as 'ta...
- `wick-size-test` (underspecified, ttrades) — NO NUMERIC THRESHOLD IS GIVEN ANYWHERE IN THIS UNIT. 'Large' and 'shallow' are labels applied to a run by eye; there is no ratio, percentage, fib l...
- `wick-trust-test` (contested, ttrades) — No deadline is given: how late into the higher-timeframe candle the wick may still form before the candle is abandoned is not stated (only that exp...

### time (32)

- `daily-open-eighteen-hundred` (contested, ttrades) — This draft supplies only the EARLIER reading; the 18:00 reading comes from other units and remains the canonical one.
- `daily-profile-session-windows` (underspecified, ttrades) — No timezone is stated in any of the four videos. EST/EDT is the ICT convention but the speaker never says it, so the windows are not fully decidabl...
- `daily-wick-confirmation-timeframes` (contested, ttrades) — Session boundaries are never given as clock times in this unit - Asia / London / New York are used without hours, and no timezone is named in these...
- `economic-calendar-filter` (contested, mixed) — The sub-tiering of red-folder events into high/medium/low is shown as a slide list, not a rule — CPI/FOMC/NFP are high and PPI is medium in his exa...
- `entry-time-window` (contested, ttrades) — The 8-11 EST figure is quoted while demonstrating an indicator setting, not stated as a trading rule; whether he personally trades to 11:00 is not ...
- `est-timezone-anchor` (contested, ttrades) — 'Eastern Standard time' is said literally; whether he means EST year-round or the New York local clock (EST/EDT) is not addressed anywhere in this ...
- `fomc-day-participation` (contested, mixed) — The auto-transcript's speaker markers are unreliable here; reading B is assigned to the guest on context (it follows his own commentary) but the at...
- `important-time-levels` (contested, ttrades) — The captioner renders 18:00 as '1,00' and '18800'; the daily-open reading is fixed by the surrounding sentence ('for the 18800 and0 that will be th...
- `killzones` (contested, mixed) — PARTIAL ANSWER TO THE LIBRARY'S 'SESSION HOURS' GAP. 8:30 and 9:30 are given as the New York morning session's start and its next marker, but NO EN...
- `macros-are-htf-opens` (contested, ttrades) — He concedes there are certain scenarios where a mid-candle window can work but declines to describe them.
- `macros-not-used` (contested, ttrades) — He labels this an opinion, not a finding, and offers no data against macros.
- `midnight-open-directional-filter` (contested, mixed) — NO TIMEZONE IS STATED for 'midnight' anywhere in this unit - the same gap the later corpus has.
- `monday-trade-rule` (contested, ttrades) — Whether the Friday candle 2 closure must additionally carry an hourly change in the state of delivery, as every other candle 2 closure in the serie...
- `new-york-am-session-only` (underspecified, ttrades) — NO HOURS ARE GIVEN for any session in this unit. 'New York a.m.', 'afternoon', 'overnight', 'London', 'Asia' and 'RTH open' are all used without cl...
- `new-york-intraday-time-levels` (contested, ttrades) — No timezone label is ever spoken in these four streams. The clock is pinned only indirectly - 09:30 is stated to be the New York stock market open,...
- `news-events-ignored` (contested, ttrades) — The X4XSsv5CNqg exchange is garbled by the auto-captioner - the text runs the viewer's question and his answer together as "Don't trade the day tha...
- `news-impact-tiering` (contested, guest) — This is a simplification relative to the same guest's three-tier (high / medium / low) framing recorded from another video: here everything non-red...
- `news-not-used` (contested, ttrades) — The two statements are eight days of streams apart with no acknowledgement of the conflict; it may be that FOMC specifically is the exception to a ...
- `nfp-week-protocol` (contested, mixed) — Whether to enter before or only after 08:30 on Friday is implied ('use the release as a driver') but not stated as a time gate.
- `no-monday-rule` (contested, mixed) — 'High resistance' is never quantified.
- `ny-am-time-level-cascade` (underspecified, ttrades) — NO TIMEZONE IS SPOKEN. The times are bare clock numbers; Eastern is the corpus-wide convention but is not stated in either Short.
- `opening-time-only-execution` (contested, guest) — The windows conflict: Ash permits London 02:00, Sniper forbids anything before 09:30, AM forbids the PM session but never gives the AM session's ex...
- `po3-four-hour-opening-times` (contested, ttrades) — The exact grids are shown on-screen as slides and only partially spoken; the futures set 02/06/10/14 and the forex set 17/21/01/09 are the values a...
- `session-cascade` (underspecified, ttrades) — Session boundaries are never defined in this transcript.
- `session-open-volume-nyse` (contested, ttrades) — Whether other equity-driven levels (10:00, 16:00) inherit the same asset-class restriction is not addressed.
- `seven-hour-candle-daily-profile` (underspecified, guest) — No timezone is stated for the 01:00 start, and the rest of the day's 7-hour candles are never enumerated.
- `silver-bullet-window` (contested, ttrades) — He mentions a possible PM-session version but does not give its window.
- `ten-am-candle-alignment` (contested, ttrades) — The timezone is never stated in the same breath as 10:00; it is fixed only by a separate remark elsewhere in the unit that the indicator time filte...
- `time-based-exit-htf-close` (contested, ttrades) — 10:00 being a 4-hour boundary implies a 4-hour grid at 02:00 / 06:00 / 10:00 / 14:00 / 18:00 / 22:00, but he never says so and never names the time...
- `timeframe-pairing` (contested, ttrades) — 'Messy' is the trigger for the override and is entirely visual.
- `volatility-timeframe-selection` (underspecified, ttrades) — Volatility is never quantified - no ATR, no range threshold, no lookback. The whole rule rests on an unmeasured word.
- `weekly-open-as-fair-value` (underspecified, ttrades) — 'Fair value' is asserted, never defined, and no trading rule is derived from the level in this video - it is used for review, not entry.

## Implementable now, TTrades' own voice

**119** concepts are `specified`, carry detection rules, and are not guest material. These are the safe starting set for detector work.

| category | n |
|---|---:|
| entry | 25 |
| liquidity | 12 |
| model | 24 |
| psychology | 11 |
| risk | 15 |
| structure | 20 |
| time | 12 |

- `c2-confirmation-scaling` (entry) — 4 rules
- `c3-with-ic-highest-winrate` (entry) — 3 rules
- `cheat-code-entry` (entry) — 5 rules
- `cisd-skip-at-target` (entry) — 3 rules
- `consolidation-sweep-entry` (entry) — 8 rules
- `counter-trend-ote-scalp` (entry) — 7 rules
- `displacement-range-re-anchor-ladder` (entry) — 6 rules
- `early-cisd` (entry) — 4 rules
- `eq-if-then-pd-array-match` (entry) — 8 rules
- `fair-value-gap-not-an-entry` (entry) — 6 rules
- `fvg-entry-refinement` (entry) — 5 rules
- `fvg-three-levels` (entry) — 7 rules
- `ignore-news-wick-in-range-fib` (entry) — 4 rules
- `lack-of-displacement-entry` (entry) — 6 rules
- `market-order-entry` (entry) — 3 rules
- `mitigated-order-block-reuse` (entry) — 2 rules
- `nested-fvg-entry-refinement` (entry) — 5 rules
- `oco-bracket-order` (entry) — 4 rules
- `one-cisd-per-day` (entry) — 4 rules
- `order-block-probability-grading` (entry) — 4 rules
- `poi-density-by-timeframe` (entry) — 3 rules
- `single-cisd-at-swing-point` (entry) — 4 rules
- `strat-trigger-entry` (entry) — 6 rules
- `trend-entry-options` (entry) — 6 rules
- `upper-half-positioning` (entry) — 3 rules
- `gold-correlated-assets` (liquidity) — 3 rules
- `high-resistance-target-adjustment` (liquidity) — 5 rules
- `inside-day-three-levels` (liquidity) — 5 rules
- `liquidity-grab` (liquidity) — 3 rules
- `liquidity-sweep` (liquidity) — 4 rules
- `liquidity-sweep-vs-consolidation` (liquidity) — 3 rules
- `low-expectation-target-selection` (liquidity) — 4 rules
- `previous-day-lookback-three-days` (liquidity) — 3 rules
- `session-high-low` (liquidity) — 5 rules
- `smt-in-fair-value-gap` (liquidity) — 3 rules
- `smt-invalidation-level` (liquidity) — 4 rules
- `smt-two-chart-layout` (liquidity) — 8 rules
- `autobias-filter` (model) — 4 rules
- `bias-split-across-timeframes` (model) — 5 rules
- `cisd-entry-model` (model) — 7 rules
- `classic-expansion-week` (model) — 6 rules
- `clean-day-criteria` (model) — 5 rules
- `consolidation-avoidance` (model) — 2 rules
- `consolidation-open-whipsaw` (model) — 5 rules
- `excluded-tooling` (model) — 8 rules
- `four-entry-models` (model) — 6 rules
- `internal-external-liquidity-model` (model) — 6 rules
- `keep-it-simple-c3-stack` (model) — 6 rules
- `midweek-reversal-week` (model) — 6 rules
- `ny-morning-routine` (model) — 7 rules
- `proximity-bias-nearest-extreme` (model) — 4 rules
- `range-edge-trading` (model) — 5 rules
- `seek-destroy-target-ladder` (model) — 6 rules
- `silver-bullet-am-model` (model) — 8 rules
- `sons-model` (model) — 7 rules
- `tradingview-chart-workspace` (model) — 14 rules
- `ttfm-hourly-5m-playbook` (model) — 6 rules
- `ttfm-indicator-settings` (model) — 12 rules
- `ttfm-scalping-model` (model) — 5 rules
- `ttfm-swing-trading-model` (model) — 6 rules
- `wick-scenario-difficulty-ladder` (model) — 4 rules
- `daily-market-review-journal` (psychology) — 10 rules
- `entry-model-least-important` (psychology) — 3 rules
- `eval-vs-funded-mindset` (psychology) — 3 rules
- `feel-emotion-dont-act` (psychology) — 3 rules
- `hedge-driven-bias-disclosure` (psychology) — 3 rules
- `hindsight-daily-bias-drill` (psychology) — 4 rules
- `ict-2022-mentorship-study-path` (psychology) — 4 rules
- `loss-is-not-a-bad-trade` (psychology) — 4 rules
- `overtrading-gate` (psychology) — 4 rules
- `wait-for-candle-close` (psychology) — 4 rules
- `wait-for-closure-discipline` (psychology) — 3 rules
- `futures-contract-rollover` (risk) — 4 rules
- `futures-contract-specs` (risk) — 6 rules
- `futures-vs-forex-differences` (risk) — 5 rules
- `gap-open-adr-budget` (risk) — 4 rules
- `hedge-not-double-exposure` (risk) — 3 rules
- `idea-vs-executable-setup` (risk) — 4 rules
- `no-size-reduction-in-drawdown` (risk) — 4 rules
- `options-expiry-3x-rule` (risk) — 3 rules
- `options-proxy-execution` (risk) — 4 rules
- `prop-firm-drawdown-types` (risk) — 6 rules
- `silver-bullet-am-backtest-result` (risk) — 5 rules
- `stop-behind-already-swept-liquidity` (risk) — 3 rules
- `target-liquidity-and-imbalances` (risk) — 5 rules
- `time-based-exit` (risk) — 2 rules
- `trail-market-structure-swings` (risk) — 4 rules
- `basic-trend-structure` (structure) — 6 rules
- `broadening-formation-range-projection` (structure) — 7 rules
- `candle-type-wick-to-body` (structure) — 5 rules
- `dealing-range` (structure) — 5 rules
- `deep-premium-deep-discount` (structure) — 5 rules
- `displacement-range` (structure) — 6 rules
- `es-nq-ratio-chart` (structure) — 5 rules
- `failure-to-manipulate` (structure) — 4 rules
- `old-high-low-three-outcomes` (structure) — 4 rules
- `opposing-candle` (structure) — 5 rules
- `opposing-run` (structure) — 5 rules
- `order-block-series-is-htf-candle` (structure) — 2 rules
- `rebalance` (structure) — 5 rules
- `relevant-swing-lookback` (structure) — 6 rules
- `reversal-vs-pullback-test` (structure) — 7 rules
- `shallow-retracement` (structure) — 3 rules
- `three-candle-outcomes` (structure) — 5 rules
- `trend-by-previous-day-extremes` (structure) — 5 rules
- `volume-imbalance` (structure) — 5 rules
- `wick-vs-body-marking-rule` (structure) — 5 rules
- `asia-session-c2-protected-swing` (time) — 4 rules
- `automatic-fractal-pairing` (time) — 5 rules
- `chart-timezone-est` (time) — 3 rules
- `daily-bias-candle-formation` (time) — 5 rules
- `fomc-nfp-cpi-only` (time) — 4 rules
- `futures-trading-hours` (time) — 3 rules
- `nine-thirty-expansion-invalidation` (time) — 4 rules
- `poi-timeframe-selection` (time) — 4 rules
- `session-timeframe-model-map` (time) — 5 rules
- `trading-window` (time) — 3 rules
- `weekly-chart-not-used` (time) — 4 rules
- `weekly-profile` (time) — 4 rules
