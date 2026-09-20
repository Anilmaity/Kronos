# Education - ICT (Updated), batch 2 — study notes (unit_id: `education_ict_updated_02`)

Channel: TTrades_edu. Playlist: "Education - ICT (Updated)", second batch of 11 videos. All 11
transcripts present and readable. Nine are cross-listed under the older "Education - ICT"
playlist as well; two (`4jU547ocod4`, `FXJBFbZQbck`) are listed only under the updated playlist
and are the newest material in the unit.

These are the channel's polished single-concept lessons — his canonical definitions, delivered
from a PDF and then walked through on charts. Where a Q&A stream and one of these disagree, this
is the reference reading. Two such cases are flagged explicitly below (breaker sequence, order
block validation).

## Transcript hygiene

Applies across the unit; every reading decision below is recorded in the concept files'
`ambiguities` as well.

- **`candle to` = candle 2.** The known corpus-wide artifact. It does not actually appear in
  this unit, because the fractal-model video here never says "candle 2" at all — it says "this
  first candle" and "this candle". The C1/C2/C3 numbering is *not* spoken in `4jU547ocod4`; the
  mapping to the fractal model is inferred from the rest of the corpus, and that is recorded as
  an ambiguity rather than smoothed over.
- **`breaker structure` / `brachet structure` = break of structure.** In `Y8DkNYhq0X0` the
  auto-captioner renders "break of structure" as "a breaker structure down" and once as "here is
  our brachet structure right here". This one is dangerous: read literally it makes the order
  block video appear to require a *breaker block*, which it does not. Elsewhere in the same video
  the phrase survives intact ("did we break the structure down not yet"), which settles it.
- **`8.5 FIB` = 0.5 fib.** In the mean-threshold section of `Y8DkNYhq0X0`. Settled by his own
  arithmetic in the next sentence: a stop that shrinks from 3.5 points to 1.75 points is exactly
  a halving.
- **`mxm` = MMXM**, throughout `WwmS47Gb3M0` and `wy3OSPxu5U0`. **`gu`** in `9PKJ0U1gl4g` and
  **`RB`** elsewhere are instrument tickers left unexpanded.
- **`to R` / `2 r` / `two R` = 2R**, used interchangeably in every video.
- None of the eleven transcripts carry timestamps, so **no `approx_time` is recorded anywhere in
  this unit.**

---

## Orderblocks Simplified (`Y8DkNYhq0X0`, https://youtu.be/Y8DkNYhq0X0, 501s)

### What is actually taught

The canonical order block definition, and it is *structural*, not candle-only. A bearish order
block needs two things in sequence: a sweep of a high, then a break of structure down. Only then
is the block valid, and the block itself is the up-close candle or series of up-close candles
that swept that liquidity immediately before the move down. Bullish is the mirror — sweep of
sell-side, break of structure up, then the single or series of down-close candles before the move
up. The sweep alone is not enough and the break alone is not enough.

Where the level sits inside the block is deliberately left open. He names three options — the
opening price, the wick, or the mean threshold — and ends the video telling the viewer to
experiment with open versus wick and single versus series and find what they enjoy. That is an
honest statement of a genuinely underdetermined rule, and it is the single biggest obstacle to
turning this video into a detector.

He then adds a grading he does not name elsewhere: **high probability** order blocks have large
candle bodies and small wicks, and for those he uses the opening price; **low probability** ones
are the other shape on his diagram, and for those he uses the wick, or the wick-to-open, as a
zone. He restricts the low-probability class hard: he only uses it when price is already in an
uptrend or downtrend *and* the candle is the only up-close (or down-close) candle on that range.

Two smaller points are worth more than their airtime. First, when asked why he marks the big
full-bodied candle rather than the small one adjacent to it, he says he wants the big full-bodied
candle on the move that swept below. Second — and this is the useful one — the reason blocks are
marked as a *series* rather than a single candle is that **a run of same-direction closes becomes
one candle a timeframe up**. That is a clean, testable equivalence and it explains the whole
series convention. Finally, the mean threshold is defined arithmetically: body high to body low,
0.5 fib, and its stated benefit is stop-size reduction (3.5 points down to 1.75 in his example).

### Concepts introduced

Order block (structural definition), break of structure as the validator, sweep of high/sell-side,
high vs low probability order blocks, opening price vs wick vs wick-to-open, series vs single
candle and the higher-timeframe-candle rationale, mean threshold, displacement, fair value gap
(used, not defined), higher-timeframe PD array as the objective.

### Rules / conditions stated

- Bearish: sweep a high → break structure down → block = the up-close candle(s) on that sweep.
- Bullish: sweep sell-side → break structure up → block = the down-close candle(s) on that move.
- Prefer the big full-bodied candle of the move, not an adjacent small one.
- Large bodies + small wicks → use the opening price. Otherwise → use the wick, or wick-to-open.
- Only use a low-probability block in an established trend and when it is the only opposing-close
  candle on that range.
- Mark a *series* of same-direction closes, because that series is one candle a timeframe up.
- Mean threshold = 0.5 of body-high-to-body-low; use it when the opening-price stop is too wide.
- While price travels toward a higher-timeframe PD array, expect it to respect blocks along the way.

### Examples walked through

5-minute ES (bullish OB after a low sweep and return into range); 1-hour NQ (bearish OB after a
buy-side sweep and break down); an in-trend example using two down-close candles inside an up
move; a small-body-candle variant; and a final sequence walking price from one order block to the
next up into a higher-timeframe objective. The mean-threshold demo closes the video.

### Quotes

- "in a bearish order block example is a sweep of a high"
- "if you move up a time frame that becomes a single candle"
- "from body high to body low 8.5 FIB of that area"

### Open questions / ambiguities

- "Break of structure" is never given a swing-confirmation rule — which swing, and whether a wick
  through counts, is not stated.
- The level inside the block is explicitly the trader's choice, so the block is not a single price.
- "Large candle bodies and small wicks" has no ratio threshold; the classes are shown, not defined.
- "Important level" is enumerated by example only.

---

## Propulsion Blocks Simplified (`9PKJ0U1gl4g`, https://youtu.be/9PKJ0U1gl4g, 550s)

### What is actually taught

He opens by re-stating the order block definition, and the restatement is **not the same one** as
in the order-block video: here an order block is a single or series of up-close candles into an
important level which price then displaces through, closing *below the opening price* of that
single or series — and that close is what validates it. No break of structure is mentioned. The
two formulations coexist in this unit and are not reconciled by the speaker; the candle-level one
is what he actually uses in every example here and in the IRL/ERL video.

A **propulsion block is an order block off of another order block**. Order block OB1 is validated;
price retraces and reaches back into OB1; the opposing-close candle or series that reacted inside
OB1 is itself closed through; that second block is the propulsion block. Two behavioural
requirements attach to it and they are the whole point of the concept: the opening price is
expected to be *very sensitive*, and price must not break or close beyond the propulsion block's
mean threshold. That mean-threshold condition is used as the live invalidation in every example —
he narrates price reaching into the block and explicitly checks that the mean threshold holds.

Risk placement is looser than elsewhere in the corpus: with a propulsion block he is fine putting
the stop on the other side of the *body* rather than the wick, precisely because he does not
expect the mean threshold to be touched. He shows a "safe" alternative (an intermediate-term low)
for the same trade. Targets are 2R or the liquidity resting beyond.

### Concepts introduced

Propulsion block, order block (candle-level definition), mean threshold as invalidation, opening
price sensitivity, body-side stop placement, inducement (previous days' highs lined up), breaker
block (named in passing as an alternative name for a stop location), volume imbalance, SMT,
Asia/London consolidation into a New York manipulation.

### Rules / conditions stated

- Order block = single/series of opposing-close candles into an important level, validated by a
  close beyond their opening price.
- Propulsion block = the same construction formed *off* an existing order block.
- Do not let price break or close beyond the propulsion block's mean threshold.
- Enter at the opening price; stop on the other side of the body is acceptable here.
- A close that does not clearly clear the level is rejected — "I do not count that as a close below it".
- Target 2R or the liquidity beyond; or drop a timeframe to refine.

### Examples walked through

Oil futures daily (OB → retest → propulsion block, taken on the daily, then refined on the hourly
with previous days' highs as inducement); a 60-minute currency example with SMT, displacement and
a breaker below an old low; a third with a volume imbalance; and a final oil futures 60-minute
example where Asia and London consolidate and New York manipulates, giving a propulsion block that
runs to 2R.

### Quotes

- "a propulsion block is an order block off of another order block"
- "I do not want to see price break the mean threshold of a propulsion block"
- "with a propulsion block I'm fine with the body"

### Open questions / ambiguities

- Whether OB2's candles must sit strictly inside OB1's range or merely react at it is not stated.
- "Break" and "close beyond" the mean threshold are used interchangeably — wick-through is unresolved.
- "I do not count that as a close below it" is a judgement call with no threshold.
- Whether propulsion blocks can chain further is never addressed.

---

## TTrades Fractal Model + Inversion (Intraday Strategy) (`4jU547ocod4`, https://youtu.be/4jU547ocod4, 1085s)

### What is actually taught

**This is the primary-source statement of the model** and it outranks the secondhand Q&A
assemblies in the library. It is also, notably, the longest video in the unit and the only one
that requires his paid indicator to reproduce.

The premise is stated in one sentence: the whole goal is to anticipate one candle's
open-high-low-close or open-low-high-close. That gives bias; the lower timeframe gives entry. The
trigger is the previous candle sweeping and closing back inside — "with the sweep of this first
candle and the closure back in then I can anticipate this candle to continue lower or to expand
lower". **Direction comes from the swept side**: sweep a high, expect a bearish expansion candle;
sweep a low, expect bullish.

Then the pipeline, in strict order:

1. **Higher-timeframe sweep and closure back in** (hourly in most examples, daily in the last).
2. **Timeframe alignment.** He explicitly waits until both timeframes are directional the same
   way, and alignment is achieved by the *lower* timeframe closing through the series of
   opposing candles that made the extreme. Until that close, not aligned, no setup — he
   demonstrates having to let another candle form for exactly this reason.
3. **Mark the t-spot** — only after 1 and 2. The t-spot is "the area in which I expect this
   higher time frame Wick to form".
4. **Drop one further timeframe and look for an inversion inside the t-spot.** 1-minute under an
   hourly/5-minute model; 15-minute under a daily/hourly model. The inversion needs a *close*
   through it — "no close yet got to wait for this close".
5. Enter on the close or on the retest (retest chosen when the close entry will not give 2R),
   stop on the swing low that formed the wick, target 2R, or hold to the higher-timeframe
   objective, or take a time-based exit at the higher-timeframe candle close (11:00 for an
   hourly model, because expansion candles usually close at their high or low).

The diagnostic use of the t-spot is the subtlest thing in the video and is stated twice. If the
higher-timeframe wick is *missing*, price can be anticipated to retrace into the t-spot to build
one. If the t-spot has *already* formed the wick, that is what he wants to see and the expansion
can be traded. If the t-spot prints large, he refuses a positional entry because the stop below
its lows makes the risk-to-reward unworkable, and waits for price to come back into it instead.

Two further qualifiers matter. He rejects setups where the t-spot has no sweep and no relevant
point of interest inside it ("we also have not swept out any lows or hit a relevant point of
Interest"), and where price merely consolidates inside the t-spot he waits for a high to be run
first so that there is a protected high. And he states outright, mid-example, that this is not
pattern trading — the inversion is only taken because of the context of trading toward the highs
after the lows have been taken.

The final example demonstrates the fractal claim by running the identical procedure on
daily/hourly with a 15-minute inversion.

### Concepts introduced

The model's stated goal (anticipate one candle's OHLC/OLHC), sweep-and-closure-back-in, timeframe
alignment as an explicit gate, t-spot (functional definition + the missing-wick diagnostic + the
too-large disqualifier), 1-minute inversion entry, positional entry off the higher-timeframe open
when the invalidation has already formed, time-based exit at the higher-timeframe close, conflicted
bias resolved by the daily profile, failure swings as targets, SMT as an alternative way on side,
phases of price / consolidation requiring a protected high, expansion candles closing on their
extreme.

### Rules / conditions stated

- Sweep + closure back inside → anticipate the next candle to expand away from the sweep.
- Wait until the paired timeframes are aligned in the same direction; alignment = a closure
  through the series of opposing candles.
- Only then mark the t-spot; look for a PD array / point of interest inside it.
- Require an inversion **with a close through it** on the execution timeframe.
- Do not take an inversion in a t-spot that has not swept a low or reached a relevant POI.
- In a consolidation, wait for a high to be run (a protected high) before trading lower.
- Stop at the swing low rather than waiting for another close above.
- Look for 2R, or hold to higher-timeframe targets, or exit on time at the higher-timeframe close.
- If the t-spot is large, do not take a positional entry — wait for price to reach back into it.
- Where the invalidation has already formed before the new higher-timeframe candle opens, enter on
  the open itself.
- Conflicted bias (bullish structure but a previous day high just taken) → use the daily profile.

### Examples walked through

Six. (1) Hourly reversal off previous day high with failure swings as the target; 5-minute
alignment arrives late; a 1-minute inversion in the t-spot gives 2R plus a time-based exit at
11:00. (2) NQ in a consolidation range, low swept, 10:00 a.m. (also a new 4-hour candle), 5-minute
already aligned, retest entry preferred to be safe from a nearby short-term high. (3) A
three-drive consolidation into previous day low where the first inversion is missed waiting for
5-minute confirmation; the trade never fills — an explicitly *missed* trade he keeps in the video.
(4) A t-spot with no inversion; price consolidates instead, and the way on side turns out to be an
ES/NQ SMT plus a bullish FVG closure. (5) The positional-entry-on-the-open case, with the
alternative of waiting for a later CISD / order block shown alongside. (6) The fractal
demonstration on daily/hourly with a 15-minute inversion, including a target-integrity check ("I
wouldn't want to trade this if it trades all the way to the highs and then back in").

### Quotes

- "to anticipate one candle's open high low close or open low high close"
- "with the sweep of this first candle and the closure back in"
- "I will wait until those time frames are aligned in the same direction"
- "the area in which I expect this higher time frame Wick to form"
- "this isn't just pattern trading"

### Open questions / ambiguities

- **The C1/C2/C3 numbering is never spoken.** The model is described purely as "this first candle"
  and "this candle". Anyone merging this into `fractal-model-c2` is making an inference.
- The t-spot's construction is not given — it comes from his indicator. Without it the fourth step
  of the pipeline cannot be reproduced from this video alone.
- "Inversion" is used throughout without definition here (deferred to his IFVG video).
- Selection among multiple inversions inside one t-spot is qualitative: "I want to see that
  inversion that forms the wick".
- "A bit large" as the positional-entry disqualifier is unquantified.
- Whether the 2R target or the time-based exit takes precedence is not resolved; both are shown on
  the same trades.

### On the standalone-C3 direction question

The library records the standalone C3 rule (no sweep required, close need not clear the opening
price, provided the EQ is respected — library wording, from other units) as degenerate, because with no externally supplied trend
direction essentially every candle qualifies. **This video does not fix that.** It never mentions
candle 3, never mentions an EQ-respect condition, and never describes a no-sweep branch. What it
*does* supply is a direction input for the **sweep-based** branch, and it supplies it three times
over: (a) direction is the side opposite the sweep; (b) it must be confirmed by the lower timeframe
closing through the series of opposing candles; (c) the trade must be travelling toward a stated
draw, and he rejects setups lacking that context. So the direction problem is solved for the C2
branch and left exactly where it was for the standalone C3 branch. See the closing section.

---

## The "Twitter Model" — The MMXM Trader (`WwmS47Gb3M0`, https://youtu.be/WwmS47Gb3M0, 573s)

### What is actually taught

A model taught explicitly on someone else's behalf — it is the MMXM Trader's, posted on his
Twitter — and it is the most completely enumerated setup in the unit. Five conditions, no
discretion in the statement:

- **Short:** previous day HIGH is raided → target a 1-hour **bullish** fair value gap below →
  require a 15-minute market structure shift **and** an SMT → enter only **above** the midnight open.
- **Long:** the exact mirror — previous day LOW raided → 1-hour **bearish** fair value gap above →
  15-minute structure shift + SMT → enter only **below** the midnight open.

He states it is fractal and can be lifted to weekly / 4-hour / 1-hour or dropped lower.

Two substitutions are permitted and both are stated as his own adjustments rather than the model's:
an **inversion or a change in the state of delivery** may stand in for the market structure shift,
and the **daily open** may stand in for the midnight open (used in the last example, unexplained).
One example shows fair-value-gap selection reasoning: prefer the gap not already reached into, and
check premium/discount — equilibrium of the range should sit at or beyond the chosen gap.

Stop placement is chosen to satisfy the 2R minimum rather than by a fixed rule: on the fair value
gap candle's low, on the swing, or below 0.5 of a wick, whichever makes the arithmetic work. He
says so directly — a swing-low stop would have been 1.4R, so he used the tighter one.

The midnight open is drawn by the *ICT Killzones & Pivots* indicator with everything switched off
except the midnight opening price.

### Concepts introduced

The Twitter model (5 conditions), midnight open as a directional gate, daily open as a variant
gate, external→internal liquidity on a smaller timeframe, market structure shift used
interchangeably with CISD, SMT against a named correlated asset (silver for gold; ES, YM for NQ;
GBPCAD in one case), premium/discount when choosing among fair value gaps, order block formation
after entry as a hold signal.

### Rules / conditions stated

- Short: PDH raid + hourly bullish FVG target + M15 MSS + SMT + entry above midnight open.
- Long: PDL raid + hourly bearish FVG target + M15 MSS + SMT + entry below midnight open.
- An inversion or a CISD may replace the market structure shift.
- The daily open may replace the midnight open.
- Prefer a fair value gap not already mitigated; check where equilibrium of the range sits.
- Choose the stop to give a 2R minimum.
- The model is fractal across timeframe triplets.

### Examples walked through

Gold daily→1H→15m with a silver SMT; NQ with an ES SMT and a large hourly FVG chosen on
premium/discount grounds; a third with a GBPCAD SMT where he enters immediately on the structure
shift close and notes the retracement to the order block would have been the better fill; a fourth
using an **inversion** rather than a structure shift on an FOMC-mitigated gap (2.26R); and a final
one substituting the daily open for the midnight open on a short.

### Quotes

- "moving from external liquidity to internal liquidity on a smaller time frame"
- "looking to only short above midnight open and then vice versa for Longs"
- "although the model says a market structure shift I will also look for an inversion"
- "instead of using midnight open I use the daily open"

### Open questions / ambiguities

- "Market structure shift" is never defined here and is used interchangeably with CISD.
- No rule selects the correlated asset for the SMT; it changes per example.
- No rule says when to use the midnight open and when the daily open.
- The FVG selection reasoning is given once and not stated as a rule.
- The time zone of "midnight" is not stated in this video.

---

## The Best Relative Strength Indicator For ES & NQ (`c_mh19e3mhI`, https://youtu.be/c_mh19e3mhI, 832s)

### What is actually taught

Relative strength is defined trivially — one of two correlated assets being more bullish or bearish
than the other — and then made operational three ways. The three things he judges on are named
outright: **swing points, candle closures, and the size of the candle.** Concretely: which asset
takes out a shared swing point and which cannot reach it; at a shared order block, which asset
closes inside the body and respects the mean threshold and which trades straight through; and which
produces the bigger candle out of the same level. SMT is presented as a fourth view of the same
thing rather than a separate tool.

Then the actual contribution, and the most automatable idea in the whole unit: **chart ES divided
by NQ as its own instrument.** If that ratio chart is bullish, ES has the relative strength and NQ
the relative weakness; if bearish, the reverse. He then reads the ratio chart's trend and reversals
like any other chart. The payoff is setup selection — the weaker asset gives the cleaner short, the
stronger asset the cleaner long — and he demonstrates it across a full week, day by day, with a
pre-recorded expectation stated *before* the week (down into a fair value gap, then expansion out).

The last section is flagged by the speaker himself as a **theory**: reversals on the ES/NQ
comparison chart show a change in correlation and can be used to anticipate a reversal on ES or NQ,
"kind of like an smt without an smt", sometimes printing *ahead* of the actual reversal. He gives
two intraday instances (a 9:30 case and a 10:00 ratio high preceding a 10:05 low) and then asks
viewers to test it and report back in the comments or Discord. That request is the tell: it is
unvalidated and should be treated as a research hypothesis, not a rule.

### Concepts introduced

Relative strength/weakness and its three tests, order block mean threshold as a strength gauge,
SMT as a strength read, the ES/NQ ratio chart, asset selection from the ratio read, ratio-chart
reversals as a change in correlation (theory), consequent encroachment used to compare two assets'
depth into the same wick.

### Rules / conditions stated

- Judge relative strength on swing points, candle closures, and candle size.
- The asset that takes a shared swing point is stronger; the one that cannot reach it is weaker.
- At a shared order block, respecting the mean threshold and closing inside the body = stronger.
- Chart ES/NQ; bullish ratio = ES strong, NQ weak; bearish = the reverse.
- Look for shorts on the weak asset and longs on the strong asset, each framed against its own
  higher-timeframe level.
- (Theory) A reversal on the ratio chart signals a change in correlation and may lead the
  instruments' own reversal.

### Examples walked through

Daily ES vs NQ around a shared 19 July swing high; a shared order block where NQ respects the mean
threshold and ES does not; a full week walked day by day against a pre-stated expectation; then
Friday's 5-minute price action with monthly and daily levels — shorts on NQ into last month's low,
longs on ES at the daily FVG consequent encroachment; and two ratio-chart reversal instances.

### Quotes

- "the main things I look for in judging relative strength or weakness is Swing points"
- "I go to trading View and I chart out es divided by NQ"
- "if it is bullish I know that es has the relative strength"
- "it's kind of like an smt without an smt"

### Open questions / ambiguities

- "Bullish"/"bearish" on the ratio chart is never defined — no MA, structure test or lookback.
- Which timeframe's ratio governs is unstated; he reads the daily and applies it to 5-minute setups.
- The ratio ticker cannot be replayed in his platform, so part of the walkthrough is hindsight.
- The lead-time claim rests on two intraday instances.
- Candle size is compared across two instruments with different point values, unnormalised.

---

## The Easiest Draw On Liquidity (DOL) — Daily Bias (`FXJBFbZQbck`, https://youtu.be/FXJBFbZQbck, 785s)

### What is actually taught

The most mechanical video in the unit, and he credits the MMXM Trader at the top. The claim: unless
price stays in a consolidation where it fails to take either side of the range, it is going to reach
for previous day high, previous day low, or both. So the daily-chart question reduces to a binary —
is price more likely to reach previous day high or previous day low — and answering it gives both a
bias and a target, after which he drops to a lower timeframe to frame an entry.

Trend is then defined by that same object, and this is the cleanest mechanical definition in the
corpus: **in a bullish trend price takes the previous day's high over and over again; in a bearish
trend it takes the previous day's low over and over again.** The repetition is the trend. When the
sequence breaks he inserts an interim target (a fair value gap) and waits, rather than flipping.

The bias section (a compressed version of his daily bias video) is about **displacement, or the
lack of it, over previous day high and low**. Failure to displace over previous day high gives a
downward bias with previous day low as the draw. Failure to displace below previous day low gives
a bias back into the range. A candle that *does* displace below a low implies continuation, and the
next day is expected to reach the new previous day low. A close over the previous day puts previous
day high back as the draw. In one sequence he adds a structural confirmation: after a sweep-and-
close-back-inside day that would tempt you long, he wants the *next* day to close below the
up-close candle, which validates it as an order block and keeps the bearish read.

The one hard number in the video: **he looks back three days** for previous-day highs and lows,
marks them and extends them forward, using them as targets and as confluence — his example shows
price deviating below an older previous-day low, returning, retesting it, then continuing (the box
setup shape).

He is deliberately honest about the limit of all this: he had a bias on almost every day in the
walkthrough, and still says it does not mean he will find an entry each day. Twice he skips the
New York session outright because the Asia session already took the day's draw.

### Concepts introduced

Previous day high/low as the default draw, trend by repeated previous-day extremes, displacement /
failure to displace as the bias engine, three-day lookback, order block validation as bias
confirmation, consequent encroachment of a fair value gap, new week opening gap, AMD (accumulation /
manipulation / distribution) across Asia–London–New York, 8:30 news as the manipulation, box setup
and deviation retest, and the explicit reminder that a bias is not an entry.

### Rules / conditions stated

- Unless consolidating, price reaches previous day high, previous day low, or both.
- Ask which is more likely; that answer is the bias and the target.
- Bullish trend = successive days take previous day high; bearish = successive days take PDL.
- Fail to displace over PDH → bearish bias, draw = PDL. Fail to displace below PDL → bias back
  into the range. Displace below a low → continuation expected.
- Close over the previous day → draw = PDH.
- Look back three days for previous-day levels and extend them forward.
- If the draw is already taken (e.g. in Asia), do not trade the later session.
- When actually watching price, extensions beyond PDH/PDL are also used as targets.

### Examples walked through

A bullish sequence of successive PDH takes; a bearish sequence of PDL takes with a fair value gap
inserted when a PDL is missed; then a full Nasdaq daily walkthrough deriving a bias for every day;
then four intraday days — a Monday with a new week opening gap and a 5-minute FVG entry to ~2R; a
day skipped because Asia took PDH; a day with 8:30 news as the manipulation into an AMD
distribution to PDH; and a final day skipped for the same Asia reason.

### Quotes

- "it is going to reach for previous day high or previous day low or both"
- "in a bullish Trend price will continue to take previous day's High"
- "for me that is three days that I will look back into price action"
- "we fail to displace over previous day's high that gives me a downwards bias"
- "it's not always possible to get an entry"

### Open questions / ambiguities

- "Consolidation" is the single exception to the entire rule and is never bounded.
- "Displacement" is never quantified anywhere in this unit.
- "Takes" the previous day high is not specified as a wick through or a close beyond.
- No count establishes or ends a trend.
- Three days is stated as a personal setting ("for me"), and trading vs calendar days is unstated.
- No ordering rule when both PDH and PDL are taken on the same day.

---

## Top Down Analysis | Daily Bias To Entries (`wy3OSPxu5U0`, https://youtu.be/wy3OSPxu5U0, 653s)

### What is actually taught

The answer to the question he says he got most after the daily bias video: having a bias, how do
you actually get in. The lesson is the layering itself, and he states it as the takeaway from the
first example — start on the daily, drop to a lower timeframe to get a point of interest, then drop
again to get the entry. Daily → hourly → 5-minute in all three of his own examples.

He opens by walking an MMXM Trader trade off Twitter, crediting him as "who taught me a lot of what
I know": daily gives the fair value gap fill and the sell-side objective; hourly gives the structure
shift and the breaker-plus-FVG retracement point; 5-minute gives the entry on a fair value gap fill.

His own three examples fill in what each layer contributes. Daily supplies the bias (a failure to
displace over a swing high; an up-close candle that will become an order block if the next day
closes below the previous day low; a Tuesday high-of-week implying expansion into Wednesday and
Thursday) plus the levels — previous day high, previous day low, a daily order block. Hourly
supplies the point of interest, in every case an order block or breaker validated by displacement
around the midnight open or just before New York. 5-minute supplies the entry: a fair value gap
with its consequent encroachment, or a breaker block marked from a high-low-higher-high-lower-low
sequence. SMT appears twice, both times as confirmation at the reaction rather than as the trigger.

Risk is stated the same way each time: stop above the high (or below the low) that is expected to
hold, minimum 2R marked out *before* leaving runners, runners to the swing point beyond.

### Concepts introduced

Three-layer top-down procedure, the MMXM Trader attribution, failure to displace over a swing high
as a bias, order block validation requiring the close below previous day low, hourly order block /
breaker as the point of interest, midnight open and 8:30 news as timing anchors, 5-minute FVG +
consequent encroachment entry, breaker block marked on a 5-minute reaction, SMT as confirmation,
minimum-2R-then-runners.

### Rules / conditions stated

- Daily → lower timeframe for the point of interest → lower timeframe again for the entry.
- The hourly point of interest must align with the daily bias.
- Validate an hourly order block by displacement out of it before treating it as the POI.
- Take the 5-minute entry only when price reaches the hourly POI.
- Mark the minimum 2R before leaving runners; runners target the swing point beyond.
- Stop beyond the extreme that the entry structure says must hold.
- SMT at the reaction is confirmation, not the trigger.

### Examples walked through

The MMXM Trader's own trade (daily FVG fill → hourly structure shift and breaker+FVG → 5-minute FVG
fill); NASDAQ 24 August (failure to displace over a swing high → hourly OB validated after a move
above the daily open → 5-minute breaker block, tagged in before 9:30, expansion to previous day low);
15 August (up-close candle needing a close below PDL → hourly OB → 5-minute SMT, displacement, FVG
consequent encroachment entry); and NQ Thursday 17th (Tuesday high of week → hourly up-close candle
into an FVG → 5-minute high-low-higher-high-lower-low breaker, 2R almost immediately, runners to the
swing low).

### Quotes

- "he is who taught me a lot of what I know"
- "started with the daily chart and then from there went to a lower time frame"
- "I can mark out my minimum 2R before I leave runners"
- "I use the weekly profile and daily bias and then using that daily bias"

### Open questions / ambiguities

- The daily bias step is delegated to his daily bias and weekly profile videos.
- "Aligns with my bias" has no test; the hourly POI is chosen visually.
- The 5-minute PD array used for entry varies by example with no selection rule.
- The timing anchors (midnight open, 8:30, 9:30) are used but not organised into rules here.

---

## Trade Continuations Using Breaker Blocks (`xP-o11jRCyg`, https://youtu.be/xP-o11jRCyg, 904s)

### What is actually taught

He opens by conceding that most people know how to trade breakers at the reversal, and that his own
model prefers order blocks — this video is about using breakers for **continuations** instead.

The definition first, and it is the reference reading the library needs. A breaker block is a
candlestick pattern in which we have a **high, low, higher high, lower low** — mark the down-close
candles from that high to the low, and that is what should resist price. A **bullish breaker** is a
**low, high, lower low, higher high** — mark the up-close candles before the move that made the
lower low, and expect them to support price. **This matches, word for word, the sequence the host
used on air to correct a guest** who had called a low-high-higher-high-lower-low structure a breaker
(the library's `breaker-block` `contested` entry). The lesson version confirms the host's reading;
the guest's reading remains a genuine disagreement, not a transcription accident.

The continuation application is the new mechanics. Having established the trend (a completed
reversal with a CISD, or a daily closure), a bullish continuation breaker requires: a swing low, a
**sweep of that low** giving low-high-lower-low, and then a **higher high** — the moment the higher
high prints, the breaker exists. Entry on the close or the retest, stop on the other side of the
breaker (his stated preference here) or the swept low, target 2R or the other side of the range.

He is asked and answers the exact question a detector would need: does it always have to take out
the low? "**yes it does unless it is paired with smt**." With an SMT against the correlated asset,
the unswept low is treated as protected and the structure is traded as a breaker anyway — he flags
this as more discretionary.

The fallback when there is no low to sweep is the most interesting departure. In advanced market
structure terms what he actually wants is an **intermediate-term low or high**, and that forms one
of exactly two ways: by sweeping out a low, or by **reaching into a fair value gap**. In the second
case the up-close candle before the move into the gap, once closed over, is the level. He then says
plainly that many will say it is not a breaker, "and it really isn't", but he keeps it because it
works. That is an unusually explicit admission that a rule in his own PDF is not what its name says.

Practical detail: where the wicks are scattered he marks the zone from the **bodies**.

### Concepts introduced

Breaker block (four-point definition, both orientations), breaker in a continuation, the mandatory
sweep and its SMT exception, intermediate-term low/high forming via a sweep OR a fair value gap,
bodies-not-wicks zone marking, phases of price (expansion → consolidation → manipulation) as the
continuation frame, propulsion block (named in the last example), mean threshold respect, his refusal to
blindly short before a bearish closure.

### Rules / conditions stated

- Bearish breaker: high, low, higher high, lower low; zone = the down-close candles from that high
  to the low.
- Bullish breaker: low, high, lower low, higher high; zone = the up-close candles before the move
  that made the lower low.
- The pattern does not exist until the fourth point prints.
- For a continuation: find a swing low, wait for it to be run, then wait for the higher high.
- The sweep is mandatory unless paired with SMT.
- Where no low can be swept, an intermediate-term low may form by reaching into a fair value gap.
- Mark from the bodies where the wicks are messy.
- Entry on the close or the retest; stop on the other side of the breaker or on the low; target 2R.
- Do not blindly short — wait for a bearish closure, then check the paired lower timeframe.

### Examples walked through

Five. RB hourly range (low swept, bullish structure, 5-minute CISD, then a swept low → high →
breaker continuation to the range high); an hourly bearish day with an indicator-marked
sweep-and-closure, a swept high giving a breaker to 2R; a daily-to-hourly-to-5-minute example
including one continuation taken purely on SMT with no swept low; a fourth run both ways (the
hourly-only entry and the refined 5-minute entry, both reaching 2R, the hourly one slower); and a
final 15-minute/1-minute example with equal highs, an NQ SMT, a propulsion block and a breaker
continuation to 2R.

### Quotes

- "in which we have a high low higher high and lower Low"
- "bullish breaker block we have a low a high lower low higher high"
- "yes it does unless it is paired with smt"
- "a breaker and it really isn't but I do find that it works"
- "I prefer to just use order blocks as I find them more simple and easy"

### Open questions / ambiguities

- For the bearish case the PDF says the zone runs "from this high to the low", but a later example
  marks "those down close candles on the move down" — whether the anchor is the *first* high or the
  higher high is stated both ways inside the same video.
- Whether the zone spans all same-direction closes between the two points or only the contiguous run
  is not stated.
- Wick vs body bounding is explicitly discretionary.
- Which swing low qualifies as "a low that can be swept" is unfiltered — no separation or age test.
- No bar-count limit between the sweep and the higher high.
- The SMT substitution names no correlated asset in most examples.
- He ends by saying he prefers plain order blocks, so this whole video is an alternative he offers
  rather than his own model.

---

## Trading IRL & ERL With Order Blocks! (`TfHlNgAZ_II`, https://youtu.be/TfHlNgAZ_II, 885s)

### What is actually taught

The mechanical range definitions the library's `consolidation` cluster has been missing, stated in
two flat sentences: **internal range liquidity is just a fair value gap. External range liquidity is
just a swing high or a swing low.** Their relationship is the model: price is expected to move from
internal to external and external to internal, oscillating until a trend shift or some other move
breaks it, at which point it restarts.

Then a genuine **flowchart**, which he reads out step by step:

1. Higher-timeframe bias.
2. Given the bias, pick the pair — either internal range liquidity (an FVG) as the reaction point
   and a high/low as the target, or a high/low as the reaction point and an FVG as the target.
3. Drop to the lower timeframe and require a **stop raid** followed by a **change in the state of
   delivery**.
4. Target around **2R**.
5. All of it inside a **kill zone**.

He calls the model simple and "fairly mechanical in its process" because only a few things have to
be determined — and, unusually for this corpus, that is close to true.

The CISD procedure is spelled out twice, identically and completely: find the low, find the series
or singular candle that made that low, mark the opening price of that series, and require a close
over it. He demonstrates the failure mode explicitly — price cannot close over before it makes a new
low, so the candidate is discarded and re-derived from the new low. The **fallback for untidy legs**
is stated once and is worth capturing: where there is no clean series of down-close candles, "I just
use this whole move".

Two risk details recur. When the swing-low stop does not give 2R, he raises the stop to just beyond
0.5 of the down-close candle body, describing that placement as similar to where a breaker block
entry's stop would be. And when a propulsion block forms on the retest, the swing low below its mean
threshold becomes the natural stop.

The honest part is the third example's caveat. After external liquidity has already been taken, he
says he can still anticipate support *if* he has a strong bias, but that without a strong narrative
this is exactly what he wants to avoid, because the next draw could be internal liquidity or the
other side of the range. He repeats it: "this only really makes sense if I have a very strong
narrative or bias to the upside".

The last section re-describes the whole rotation in trend terms: in a bullish trend, higher low
(internal) → higher high (external) → higher low → higher high, which is the same oscillation seen
from the outside.

### Concepts introduced

Internal range liquidity = FVG, external range liquidity = swing high/low, the internal↔external
rotation, the five-step flowchart, stop raid, CISD (full procedure + untidy-leg fallback), kill zone
as a hard gate, 2R minimum, 0.5-of-the-body stop as a breaker-like alternative, propulsion block on
the retest, continuation entry after the low is validated, the strong-narrative override and its
warning, higher-low/higher-high restatement of the rotation.

### Rules / conditions stated

- IRL = a fair value gap. ERL = a swing high or swing low.
- Expect internal → external and external → internal, repeating until something breaks it.
- Flowchart: HTF bias → choose the IRL/ERL pair → LTF stop raid → CISD → ~2R → inside a kill zone.
- CISD: find the low, find the candle(s) that made it, mark their opening price, require a close over.
- If a new low forms before the close over, that candidate is dead; re-derive.
- If the leg into the low is untidy, use the whole move as the reference.
- If the close entry does not give 2R, wait for a retest, or raise the stop beyond 0.5 of the body.
- Do not trade a re-entry after external liquidity is taken unless the narrative is strong.
- Sweeping the higher-timeframe low that the bias depends on invalidates the idea.

### Examples walked through

Gold weekly→4H→15m (weekly closed over the previous → 4H FVG as IRL, 4H swing high and previous week
high as ERL → 15m stop raid, discarded CISD candidate, then a valid CISD to 2R with the raised stop);
a daily sweep-and-close-back-inside with an hourly FVG as IRL and equal highs as ERL, where the first
5-minute CISD (marked using the "whole move" fallback) does not give 2R and the trade is only taken
later off a propulsion block; a continuation sequence showing higher-low/higher-high rotation with
both a limit-on-retest and a continuation entry; and a final daily-IRL/daily-ERL example run down to
the hourly.

### Quotes

- "internal range liquidity is just a fair value Gap"
- "external range liquidity is just a swing high or a swing low"
- "we expect price to move from internal to external and external to internal"
- "looking for a stop raid a change in the state of delivery"
- "this must all be done within a Kill Zone"
- "we don't have a clean series of down closed candles"
- "I just use this whole move"

### Open questions / ambiguities

- **Which kill zone, and on what clock, is never stated** — the term is used once, as a hard gate,
  with no hours attached.
- Which timeframe's FVG is "the" internal liquidity is set by the pairing in use, not by a rule; the
  examples mix 4H, hourly and daily gaps against weekly and daily swings.
- "Reaching" internal liquidity is not defined as near edge, consequent encroachment, or full fill.
- The "strong bias / strong narrative" override is explicitly discretionary and unquantified.
- The untidy-leg fallback has no boundary rule — where the "whole move" starts is chosen visually.
- "Just around a 2R trade" is a guideline, not a stated hard minimum.

---

## Trading without a Structure Shift / Break (`yq4Z7q4E6nU`, https://youtu.be/yq4Z7q4E6nU, 445s)

### What is actually taught

This video directly probes the precondition many library concepts assume. His motivation is stated
plainly: waiting for a market structure shift or break made him miss moves and feel FOMO, so he
worked out how to enter *before* it. So the answer to "is the structure shift required?" is **no,
and here is exactly what replaces it**.

Two things are required, and he ranks them. First, a **higher-timeframe point of interest** — highs
and lows, fair value gaps, order blocks, "whatever PD array that you select". Second, and named as
the most important, a **run of a short-term high or low followed by an aggressive move back** into
the range. The run-and-return produces a BPR, a fair value gap, or a box setup, and that construction
is the entry.

A second branch: a higher-timeframe point of interest that is itself run aggressively, such that the
higher timeframe **fails to close or displace beyond that level**, gives an OTE / discount-or-premium
entry. When both branches coincide the setup is at its best, and he draws that combined shape.

The mechanically useful observation is the timeframe equivalence: the aggressive move out and the
aggressive move back **create the wick of a hammer candle on the higher timeframe** — a "shooter"
candle at the top of a range. So the lower-timeframe run-and-return and the higher-timeframe wick are
the same event seen twice, which gives a cheap confirmation test.

He is careful about sequencing in the first example — before the low is taken there is "no reason to
be looking long yet" — and he closes by saying the whole thing can be used as bias rather than as an
entry model, with the emphasis on displacement after running lows or highs.

### Concepts introduced

Trading without a market structure shift, higher-timeframe point of interest, run of a short-term
high/low + aggressive return, BPR / box setup / fair value gap as the resulting entry, failure to
close or displace beyond the level, OTE entry (0.62 used), hammer/shooter wick equivalence across
timeframes, using the model as bias rather than entry, RTH open / "after nine" as a timing filter in
one example.

### Rules / conditions stated

- Require a higher-timeframe point of interest (any PD array the trader has selected).
- Require a run of a short-term high or low, then an aggressive move back into the range.
- The entry is the resulting BPR, fair value gap, or box setup.
- Alternative branch: HTF POI run aggressively with no HTF close/displacement beyond → OTE entry.
- Do not look long before the low has actually been taken.
- The run-and-return shows up as a hammer (or shooter) wick one timeframe up.
- The method can be used for bias only, on the analysis timeframe.

### Examples walked through

A 15-minute previous low, dropped to 5-minute (no take yet → no long), then 1-minute for the
aggressive move below and back, giving a BPR or box entry to ~2.6R at the internal highs; an hourly
OTE area worked down to the 15-second chart, entry at the down-close candle with the stop on the low
for just over 4R; and an hourly-as-bias example refined to a 5-minute OTE using the 0.62, targeting
the same level the hourly trade would have.

### Quotes

- "there are two things that I look for when trading without a market structure shift"
- "the next and most important is a run of a short-term high or low"
- "will create the wick of a hammer Candle on the entire time frame"
- "we failed to close or displace below this low"
- "just using the 0.62 as an entry"

### Open questions / ambiguities

- **"Aggressive" is the load-bearing word in both branches and is never quantified** — no candle
  range, ATR or bar-count threshold. This is what stops the concept being `specified`.
- "Short-term high or low" is undefined; no separation or age filter.
- BPR and the box setup are drawn but deferred to other videos.
- No rule chooses among BPR / FVG / box / OTE when several are available.
- The execution timeframe varies from 1-minute to 15-second with no selection rule beyond
  "depending on the time frame I am trading".

---

## Why You're Failing with ICT Concepts (`r_UF8U-hsL8`, https://youtu.be/r_UF8U-hsL8, 722s)

### What is actually taught

The unit's only psychology-first video, and it contains one genuinely mechanical artefact.

The diagnosis: people fail with ICT not from lack of knowledge but from an inability to filter the
concepts down to one. The prescription has a selection step and a constraint. Selection — ask which
PD array is easiest for *you* to see on the chart, which makes the most sense, and how much
confirmation you need. Constraint — use that single array **in combination with highs and lows**;
liquidity is mandatory alongside whatever array is chosen. Then stop switching after a rough patch.
He states his own answer with no hedging: highs, lows, and opposing candles / the change in the state
of delivery, and nothing else.

The mechanical artefact is the **order of a reversal**, which he takes from his own earlier video and
uses here as a confirmation ladder. As a reversal forms the arrays appear in a fixed order: **turtle
soup (the sweep) → inversion → change in the state of delivery / order block formation → breaker →
fair value gap.** Each rung is later, carries more confirmation that the extreme is in, and gives a
worse price. He walks the ladder rung by rung on one chart and states the cost of each: at rung 1
there is no protected high to trade against and price "will go ahead and stop that out numerous times
before catching a winner"; at rung 2 the fair value gap has been disrespected so the high is more
likely intact; at rung 3 the stop can go on the bodies or above the swing highs; by rungs 4 and 5
structure has clearly shifted. The trader's job is to pick a rung and always use it, because that is
what makes entry, stop and journal data comparable.

He then re-runs the same ladder inside the paired lower timeframe (30-minute chart, 3-minute pairing)
to show it is fractal, and demonstrates the same price action read entirely with inversions, and then
entirely with breakers, to make the point that the array choice is arbitrary but the *consistency* is
not. The closing argument is about execution rather than analysis: a simple model is executable, and
hindsight markup is not the skill.

### Concepts introduced

Order of a reversal (five-rung confirmation ladder), PD array enumeration, single-array selection
criteria, mandatory pairing of the chosen array with highs and lows, confirmation-versus-price
trade-off, repeatability as the goal (same entry, same stop, comparable journal), 30-minute/3-minute
timeframe pairing, continuation via opposing candles, "remove things instead of adding".

### Rules / conditions stated

- Enumerate the arrays: fair value gap, inversion, breaker, order block, CISD, OTE/Fibonacci.
- Pick exactly one, by three questions: easiest to see, makes most sense, how much confirmation.
- Always pair the chosen array with highs and lows / liquidity.
- Ignore the other arrays even when visible.
- Do not switch after a losing stretch.
- Order of a reversal: turtle soup → inversion → CISD/order block → breaker → fair value gap.
- His own model: the sweep, the closure through the series of opposing candles, then continuations
  off subsequent opposing candles.

### Examples walked through

One primary chart, worked three ways. Previous days' highs taken; the ladder walked rung by rung with
the stop placement stated at each; then the same price action re-read with only inversions; then with
only breakers. Then a zoom into the continuation phase — each move back into an opposing candle is a
sell opportunity — with the 30-minute chart dropped to its 3-minute pairing, where the identical
ladder appears again.

### Quotes

- "It's just the inability to filter through the concepts and focus on one"
- "We have a turtle soup, an inversion, a change in the state of delivery"
- "there is more and more confirmation"
- "use highs and lows or liquidity in combination with the selected PDA"
- "I use highs, lows, and opposing candles or the change in the state of delivery"
- "we are on the 30 minute and that is my time frame alignment"

### Open questions / ambiguities

- The ladder is an ordering, not a requirement that all five print; no rule covers a missing rung.
- "Turtle soup" is used here as a synonym for the sweep and is not otherwise defined.
- The confirmation-versus-price trade-off is qualitative; no R:R comparison across rungs is given.
- The selection criteria are subjective by design, so this cannot be applied mechanically.
- No guidance on when, if ever, a chosen array should be abandoned.

---

## Cross-video observations

- **Two order-block definitions coexist in this unit and are never reconciled.**
  `Y8DkNYhq0X0` requires a sweep *and* a break of structure; `9PKJ0U1gl4g` (and every example in
  `TfHlNgAZ_II`) requires only that price closes beyond the opening price of the opposing candles at
  an important level. The second is the one he actually uses in practice across the unit. Both are
  recorded in `order-block`.
- **The breaker conflict in the library is settled in the host's favour.** `xP-o11jRCyg` states
  bullish = low, high, lower low, higher high — matching the on-air correction verbatim. The guest's
  low-high-higher-high-lower-low reading remains a real disagreement, not a caption artefact.
- **The structure-shift precondition is optional, and the replacement is specified.** `yq4Z7q4E6nU`
  supplies the exception conditions: a higher-timeframe POI plus a run-and-return, or a POI run
  aggressively with no HTF close beyond it. The only thing blocking a detector is the word
  "aggressive".
- **Everything in this unit converges on 2R.** The IRL/ERL flowchart, the Twitter model, the fractal
  model, the top-down procedure, the propulsion block and the breaker continuation all state a 2R
  target or minimum, and in three separate videos the *stop placement* is chosen to make 2R work
  rather than by a fixed rule. 2R is effectively a constraint on entry selection, not an exit rule.
- **CISD is the load-bearing primitive.** Its full procedure appears in three videos with identical
  wording, and in `r_UF8U-hsL8` he names it as the one PD array he has chosen. Anything built from
  this unit should implement CISD first.
- **He repeatedly names the MMXM Trader as his source** — credited in `FXJBFbZQbck`, given a whole
  video in `WwmS47Gb3M0`, and called "who taught me a lot of what I know" in `wy3OSPxu5U0`. Three of
  the eleven videos in this unit are, by his own statement, someone else's material.
- **Indicator dependence is concentrated in one video.** Only `4jU547ocod4` (t-spot) and, secondarily,
  the midnight-open drawing in `WwmS47Gb3M0` need external tooling. Everything else in the unit is
  reproducible from raw candles.
- **Terms used but never defined anywhere in this unit:** displacement, aggressive, kill zone (used
  as a hard gate with no hours), consolidation (the single exception to the whole DOL rule), market
  structure shift, BPR, turtle soup, t-spot construction, inversion, "important level".
