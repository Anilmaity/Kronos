# Build A Model — Intro to TTrades Fractal Model, part 3 — study notes (unit_id: `build_a_model_intro_to_ttrades_fractal_model_03`)

Channel: TTrades_edu. Playlist: "Build A Model - Intro to TTrades Fractal Model (TTFM)", third
slice (4 videos). All four are also cross-listed under "Education - ICT (Updated)" and
"Education - ICT". All four transcripts present and readable.

These are **the four dedicated teaching videos** for four terms that the rest of the corpus uses
constantly and never defines: relevant swings, wick size, EQ, and the CISD-plus-order-block
continuation. Everywhere they disagree with a live Q&A answer, the disagreement is recorded here
as a finding rather than smoothed over — that is the whole point of reading the primary teaching.

The unit's headline result, stated up front so it is not buried: **three of the four videos
supply the mechanical rule the library was missing, and one does not.** The EQ measurement is
settled (wicks, never bodies, with a large-wick exception). The relevant-swing look-back is
settled (three higher-timeframe candles, current inclusive, fractal). The V-shape speed test is
settled (1–3 candles). **Wick size is not settled and, on the evidence of its own dedicated
video, cannot be — he never gives a ratio.** The nearest thing in the entire corpus is a
description of one example: "We use almost half the time and quite a bit of range".

## Transcript hygiene

The known playlist-wide artifact is present: the auto-captioner renders **"candle 2"** as
**"candle to"** — "a candle to closure" occurs once in `HbOeD_JVens`, twice in `PQiRV0JMhIQ`
and three times in `SlWxhzhLo3A`. It is read here as *candle 2 closure*. `SlWxhzhLo3A` also
renders **"candle 4"** as **"candle for"** ("looking for a candle for continuation") and mixes
digit and word forms freely ("candle 3", "candle three", "candle four"). `PQiRV0JMhIQ` mangles
**"down-close candles"** four different ways in one transcript — `downclo`, `downclosed`,
`downcloed`, `downlosed` — alongside the correct "down close"; all are the same term, and the
verbatim quotes below preserve whichever spelling the captioner produced. `IPZjNI1B5a0` is the
noisiest of the four: it is `auto-en` rather than `yt-dlp-auto`, has no sentence punctuation at
all, randomly capitalises mid-sentence ("fair value Gap", "down Clos candles", "Wick High"),
renders **0.5** as `0.5`, `05`, `0 five`, `the0 five` and `5 of that` in the same video, renders
"PD arrays" as `PD a`, `PD aray`, `PD arays`, `PDR a` and `pda`, and turns "retraced" into
"wretch into". **None of the four transcripts carry timestamps, so no `approx_time` is recorded
anywhere in this unit.**

One further caution for anyone diffing quotes against these notes: the corpus validator counts
words on a punctuation-stripped form, so a contraction ("don't", "we've") counts as two words
and "0.5" counts as two. Several quotes below are therefore clipped at what looks like an odd
place — they are verbatim substrings, just short ones.

---

## Which Swing Highs and Lows Matter in Trading? (Relevant Swings) (`HbOeD_JVens`, https://youtu.be/HbOeD_JVens, 789s)

### What is actually taught

The video opens by telling you to watch the failure-swings video first, then gives the swing
point primitive in one line each: a bullish swing point is "a candle that has a low and then a
higher low to its right" and to its left; a bearish swing point is a candle with a high and "a
high and then a lower high to its left and right". This matches the three-bar definition already
recorded in the library from `the_foundation_01` — the primary Build-A-Model teaching corroborates
it rather than contesting it.

A **relevant** swing is then a swing point filtered on one property: separation. "those are swing
points that are actually relevant". A swing sitting close to another same-side extreme is not
relevant, because you would expect price to run through it into the extreme — "these are not
relevant highs because we are not expecting a reversal right here", "we're not expecting a
reverse right here because there are still highs to its left". The remedy is always the same:
"we go find the extreme and that is our relevant swing high". The functional test he repeats
throughout the TradingView section is a trust question asked in the first person — would I trade
away from this low leaving that one below untaken? — and the answer is no whenever the two are
close: "so close to this one that I could not trust myself to trade away".

**And then he refuses to quantify it, explicitly and unprompted.** Near the end of the last
example he says: *"I don't have a mechanical reason to say, hey, this is valid separation"*, and
*"That just comes with experience and really the discernment of looking at it"*. That is the
dedicated teaching video for the term saying there is no rule. The library's `relevant` blocker
is therefore not an artefact of Q&A ambiguity that a better source would resolve — the vagueness
is his, and the concept must stay `underspecified` permanently unless someone quantifies it
themselves.

What the video *does* deliver mechanically is the **look-back period**, and this is the single
most valuable extraction from this video. Asked at what point a relevant high or low is too far
in the past to matter, he gives a fractal, countable window: "look in our current higher time
frame and then back two candles", i.e. "that same look back period of three higher time frame
candles" including the current one. On the daily chart the higher timeframe is monthly, so it is
three months; on the hourly chart, "I'm going to look back 3 days because that is my look back".
He states it in as many words: "It is fractal." Inside that window he further prefers relevant
swings that are *also* a higher-timeframe extreme — a relevant swing low that is also the monthly
low.

The last piece is the reaction test at a relevant level. Reaching it is not the signal; the phase
of price at it is. "Do we get a retracement, a reversal, or a consolidation?" — reversal means
manipulation and you can trade to the other side of the range; retracement or consolidation means
breakout and continuation through. The trigger he wants is a candle 2 or candle 3 closure ("I'm
going to be looking for a candle 2 or candle 3 closure"), with "the wick or the EQ" of that
candle as the level candle 3 must respect — which is exactly the hand-off into the EQ video.

The instrument is named once: the long middle example is **oil on the daily chart**.

### Concepts introduced

- **Swing point** — the three-bar definition, given plainly.
- **Relevant swing high / relevant swing low** — swing points with valid separation.
- **Valid separation** — and its explicit non-mechanisability.
- **Look-back period** — three higher-timeframe candles, current inclusive, fractal.
- **Failure swing** — here defined by *proximity*, not by whether it swept liquidity.
- **High resistance liquidity** — wanted on the stop-loss side, i.e. no failure swings there.
- **Phases of price at the level** — retracement / reversal / consolidation as the breakout-vs-manipulation test.
- **Candle 2 / candle 3 closure**, **wick or EQ** as the level to respect.
- **Multiple live relevant swings** — when a relevant high is reached and not reversed off, the
  next extreme beyond becomes relevant and both are tracked.

### Rules / conditions stated

- Mark swing points by the three-bar test, then filter for separation.
- A swing close to another same-side extreme is a failure swing; go outward and mark the extreme.
- A technically-failure-swing low can still be relevant if its separation is large.
- There is no mechanical rule for how much separation is enough.
- Only look for reactions and reversals at relevant swings; they are also the targets.
- Look-back window = current higher-timeframe candle + the two before it.
- Prefer relevant swings that are also a higher-timeframe extreme.
- Levels older than the window may be looked at but are not the focus.
- Keep failure swings off the stop-loss side; want high resistance liquidity there.
- At a relevant level, classify the phase before deciding reversal vs continuation.
- Without an SMT, do not anticipate a reversal at a level that is not relevant.
- Where separation is marginal, wait for a close through to confirm the low first.

### Quotes

- "I don't have a mechanical reason to say, hey, this is valid separation"
- "that same look back period of three higher time frame candles"
- "relevant swings are where I look for my model to form in the market"

### Open questions / ambiguities

- Separation is unquantified **by his own statement**, so the gap is permanent within the corpus.
- Whether separation is measured against the immediate neighbour only or against the whole cluster
  is never said.
- The failure-swing definition here (proximity) conflicts with the corpus's other definition
  (did not sweep liquidity); the two can disagree on the same bar.
- The higher-timeframe pairing that drives the look-back is deferred to his timeframe-alignment
  material; only daily→monthly and hourly→daily are given by example.
- What happens when the outer, better-separated extreme falls *outside* the three-candle window
  is not addressed.
- "The wick or the EQ" is offered as an either/or with no precedence rule.

---

## Why Your Continuations Fail (Order Blocks + CISD Explained) (`PQiRV0JMhIQ`, https://youtu.be/PQiRV0JMhIQ, 1776s)

### What is actually taught

Structured as three named failure modes, each with a remedy, then twenty minutes of TradingView
examples including two viewer setups sent to him on Twitter.

The **ideal** continuation is stated first so the failures have a reference: "we want to see a
nice aggressive V-shaped reversal" — price reaches a fair value gap or sweeps a low, recovers
swiftly, and closes through the series of opposing candles. And here the video delivers the
number the library has needed for `v-shape-reversal-speed`: **"It only takes a couple candles.
Now, I prefer 1 2 maybe three."** He adds that longer than that usually means "it just takes too
long to form this continuation". The rejected counter-example is explicitly a candle count:
"candles down and we have six candles up and we can't even get back" to the level — "That is not
fast or V-shaped." The accepted one is symmetric: "Two candles up. Takes two candles to come back
down." This converts a purely visual term into something a detector can compute.

**Reason one** is that the closure you read as validating the low is actually a manipulation of a
consolidation range's high: "This closure through which you think is validating this low is
actually a manipulation", "It's actually just sweeping out the high in the consolidation range".
The remedy is to reclassify the structure as a range the moment the recovery is slow, and then
take one of exactly two routes back in — "we can either trade the breakout with a continuation or
wait for a new manipulation". Neither is the naked closure. The universal first move is "step one
is to wait to see this next candle and how it reacts".

**Reason two** is a continuation that fires at the same moment price takes out a short-term high
or low: "the continuation forms at the same time that we are taking out highs". His scope for
"short-term high" is wider than it sounds — he says he is not just talking about the adjacent
candle but an actual high, and especially buy-side or sell-side liquidity, because "this is where
a bearish setup will form". The remedy is a second continuation off that level: "I need to see a
continuation or a new swing point form off". A secondary reason to wait is risk-to-reward — after
the high is taken the protected swing is too far away.

**Reason three** is a higher-timeframe target already taken: "a higher time frame target has
already been taken". This is framed as a FOMO trap. He is categorical — "look for continuations
after we've already hit a higher time frame objective" is what he does *not* do — and the closing
NQ example gives the count: "1 2 three candles of expansion and hitting a significant high", after
which "I do not want to be longing after price has already made it expansion".

Two smaller findings matter more than their airtime. First, a **series-selection rule**: "when we
have this candle that doesn't form a swing, generally I ignore it", using the neighbouring candle
that does form a swing as the continuation reference instead — which moves where the CISD level
sits. Second, an accepted substitute: "use inversions as a form of the change in the state of
delivery" when the candle range is extremely large.

The video closes on the timing doctrine, which he flags as the one takeaway: "Frame your entries
when it is forming the higher time frame wick." Applied to the second viewer setup: "I am waiting
for this next candle. This candle has already expanded."

### Does it adjudicate the CISD?

**Partly, and the part it settles is not the part the library most needed. Stated unambiguously:**

- **It does NOT decide which price the close must be measured against.** The library holds two
  incompatible readings — close through the *series' extreme* versus close through the *open of
  the first candle* of the run (from `CHIK5oBRKiw`). Across the entire 1776 seconds he says
  "closing through the series of downclo candles", "a closure through this down close candle",
  "closing below here", "do we get a closure through that level" — and never once names the
  price. The disagreement survives this video intact.
- **It DOES decide the series-length question, and against the library's current majority.**
  Recorded in `sunday_sessions_live_q_a_03` from `r7yW6ou1LDs`: "I never select one candle I always
  will use a series of candles", reinforced by two more Q&A rejections of single candles. Here, in
  the dedicated model video, he says the opposite in plain terms: **"use a singular candle in this
  case because there's not more than one candle"**. Both are his. This one is the primary teaching.
  A detector should treat the run as "the contiguous opposing-close candles that made the extreme,
  which may be one".
- **It adds a third, previously unrecorded gate**: speed. A closure that arrives only after a slow
  grind, or after a failed attempt plus consolidation, is not a CISD at all — it is a sweep of the
  consolidation high. That promotes the V-shape from a quality preference to a validity condition,
  and it is the one new constraint that would materially change a CISD detector's output.

### Concepts introduced

- **Ideal continuation** — point of interest → V-shape → swift closure through the opposing series.
- **The 1–3 candle speed threshold.**
- **Failure mode 1** — consolidation sweep masquerading as a validating closure.
- **Failure mode 2** — continuation coinciding with a short-term liquidity take.
- **Failure mode 3** — continuation after a higher-timeframe objective is already hit.
- **Two routes out of a consolidation** — manipulation of the low, or breakout *plus* a new continuation.
- **Wait one more candle** as the universal first remedy.
- **Ignore candles that do not form a swing** when selecting the continuation reference.
- **Inversion as a CISD substitute** on extremely large candle ranges.
- **Frame entries while the higher-timeframe wick is forming.**
- **T-spot** (used twice, never defined here).

### Rules / conditions stated

- Require a V-shaped recovery; count the candles; prefer 1–3, reclassify beyond that.
- Compare the recovery candle count with the approach candle count.
- A slow or failed recovery means consolidation: mark the range, ignore internal closures.
- Enter a range only on a manipulation of its extreme, or on a breakout that then forms a new
  continuation.
- Do not enter a continuation that simultaneously takes a short-term high/low; demand a second one.
- Do not seek continuations once a higher-timeframe objective is hit or after ~3 expansion candles.
- Skip a candle that does not form a swing when choosing the opposing series.
- A single candle may serve as the series when the structure contains only one.
- Inversions may substitute for the CISD on very large candle ranges.
- Frame entries early in a new higher-timeframe candle, while its wick is forming.
- On the entry he does show: enter on the closure through, stop on the low, target 2R.

### Examples walked through

Mostly unnamed instruments; **NQ** is named in the final example. Two examples are viewer setups
sent via Twitter (one credited on air to "JD"), both diagnosed the same way — the closure took too
long, so the structure was a consolidation and the low was the target rather than the support.
The remaining examples pair a clean case against a failure case for each of the three reasons,
with one example deliberately blending reasons one and two (a struggling closure that also wicks a
short-term high).

### Quotes

- "It only takes a couple candles. Now, I prefer 1 2 maybe three."
- "use a singular candle in this case because there's not more than one candle"
- "Frame your entries when it is forming the higher time frame wick."

### Open questions / ambiguities

- The CISD reference price is never named — the corpus's central CISD disagreement is untouched.
- The 1–3 candle count is hedged ("I prefer", "a lot of times"), and one accepted example is
  described as "taking a few candles to close over".
- The timeframe on which the candles are counted is whatever chart is on screen.
- "Doesn't form a swing" is not defined here; the three-bar test from `HbOeD_JVens` is the only
  candidate and he does not say it is the one meant.
- "Short-term high" is widened mid-video from the adjacent candle to any actual high to buy-side
  liquidity, with no qualifying rule.
- How many candles to wait for the second continuation varies ("another candle or two", "a couple
  candles", "give it one more candle").
- He permits the aggressive trader to take the first closure anyway "if you have enough trust", so
  the rule sits on a discretionary scale.
- "Significant high" (reason three) is undefined here.

---

## Wick Size Matters: The Key to Understanding Reversal and Expansion Candles (`SlWxhzhLo3A`, https://youtu.be/SlWxhzhLo3A, 1605s)

### What is actually taught

This is the video the library's only surviving falsifiable prediction depends on, and the honest
summary is: **he gives a procedure and a mechanism, but no threshold.**

The classification is binary. An expansion candle "has a small wick on both sides and a large
body"; a reversal candle has "a large wick and a small body". The primitive underneath both is
his own term, which he defines explicitly and which is worth lifting out because the library did
not have it: *"when I say opposing run, I mean from the opening price to that high"* — the move
against the intended direction, measurable while the candle is still open, which becomes the wick
at the close.

The crucial structural finding is that **"small" is two-dimensional, and time is the dimension the
library was missing.** He never grades range alone. The mechanism he gives is: "This small wick
supports expansion because it is making a shallow opposing run" — price opens, makes its extreme
early using a small amount of range, "and this leaves enough time for it to expand", closing near
its high or low. Conversely a reversal candle will "use most of its time period and most of its
range making the wick". He states the pairing directly: *"we don't use much range there, but also
we don't use much time"*, and *"We want to see that early into the candle."*

**The nearest thing to a threshold in the entire corpus appears here, and it is a description of
one example, not a rule.** Rejecting a candidate expansion candle he says: *"We use almost half the
time and quite a bit of range"* on the move up — therefore a large opposing run. That is it. There
is no wick-to-body ratio, no wick-to-range fraction, no percentage-of-period figure anywhere in the
1605 seconds. The only other numeric trace is a timing rejection: *"Does it make sense for price to
consolidate here and then with 40 minutes left"* in the candle, take the high and expand? No — wait
for the new candle.

A complication worth flagging for anyone building a detector: one grading is made against a
*different* candle's range. Assessing the forming daily candle from the hourly chart he says
*"Yes, we have a small wick relative to the daily range."* Elsewhere the wick is graded against
its own candle. The reference range is not consistent.

Wick size alone is also **not sufficient**. A shallow run with no confirmation is shown failing
explicitly: *"Without that change in the state of delivery there, we cannot confirm this wick
high"*, versus the good case where the run is "paired with a change in the state of delivery,
it's then confirming this wick". And there is a session overlay: "we want to see this high day
form early New York or before New York" so New York is left to expand.

The video's cleanest deliverable is the **difficulty ladder** — three ways to trade a reversal,
ranked, which the library did not have as a single ordered object. Easiest: "the easiest is
letting this candle to close" with its large wick, then trade candle 3 when candle 3 has a small
wick plus a CISD. Harder: the reversal-to-expansion candle, requiring a small opposing run, a
lower-timeframe CISD, *and* enough time left in the candle. Hardest and typically avoided: trading
the large-wick reversal candle itself — "I might as well just wait for the next candle to have a
small wick" — and the stated reason is the loss of a filter: with a large opposing run "we don't
really have the filter of the candle close", and "so many times price will just continue to trend
up" if the read is wrong. The exception he allows is timeframe-specific: "a reversal candle on the
daily, then I look to trade the lower time frames" back toward the daily open.

**Target adjustment** on a large-wick candle is stated in his own voice here, which matters because
the library previously held this rule only from a guest (GxTradez, `t_talks_02`) — the two agree.
"when we have a large opposing run, that's when I need to adjust my targets": not expansion, but
"the opening price or liquidity points or points of interest around there", typically a fair value
gap near the open. He gives the escalation condition for reaching further, to the session extreme:
only when that extreme is low-resistance liquidity — "we want to see price open and just make a
steady move higher", which will "make a bunch of failure swings and then we can trade that
reversal". Where a protected swing sits on the intraday extreme instead, he deliberately takes the
smaller target, reasoning that if he is wrong the higher low forms in exactly that area.

Instruments named: **silver** (hourly + daily), **oil / CL** (daily), then unnamed 4-hour and a
final 15-minute/1-minute fractal demonstration.

### Concepts introduced

- **Opposing run** — his measurement primitive, defined explicitly.
- **Expansion candle vs reversal candle** — small wick + large body vs large wick + small body.
- **The two-axis size test** — range consumed *and* time consumed.
- **"Early into the candle"** as the mechanism, not just a description.
- **The difficulty ladder** — three tradeable scenarios, ranked.
- **Target adjustment** on a large-wick candle — back to the opening price.
- **The candle closure as a filter** — the stated reason tier 3 is worst.
- **Wick confirmation via CISD** — shape alone does not confirm a wick.
- **Session overlay** — the extreme should form early New York or before.
- **Average candle's range** as an expansion target.
- **T-spot**, **SMT**, **protected swing**, **failure swings** — used, not defined.

### Rules / conditions stated

- opposing run := opening price → the extreme against the intended direction.
- Grade it on both range consumed and time consumed.
- Small wick + large body + close near the extreme = expansion candle, tradeable for expansion.
- Large wick + small body + return toward the open = reversal candle, not tradeable for expansion.
- "Almost half the time and quite a bit of range" describes a large opposing run.
- On a large wick, wait for the next higher-timeframe candle open and require a small wick there.
- Time-remaining check: reject when too little of the period is left for the expansion to complete.
- Require a lower-timeframe CISD before treating the wick as confirmed.
- On a large-wick candle, target the opening price and the liquidity around it.
- Escalate to the session extreme only when it carries failure swings; if a protected swing sits
  there, take the open instead.
- Large-wick reversal candles are traded only on the daily, executed on lower timeframes.
- Prefer the extreme to form early New York or before New York.

### Quotes

- "This small wick supports expansion because it is making a shallow opposing run."
- "We use almost half the time and quite a bit of range"
- "we don't use much range there, but also we don't use much time"

### Open questions / ambiguities

- **No ratio is given.** This is the dedicated wick video and it supplies no wick-to-body or
  wick-to-range fraction. The C2 small-wick prediction remains unquantified from the source.
- The two axes are never weighted against each other; a candle small in range but slow in time is
  not adjudicated.
- The reference range is inconsistent — once "relative to the daily range" for an hourly wick.
- The PDF says small wick "on both sides", but every worked example grades only the opposing side.
- "Early into the candle" is never a fraction of the period; the 40-minutes case is one hourly example.
- Tier 3 is said to be daily-only, which sits awkwardly with the Thursday Counter profile
  elsewhere in the corpus, built on a large-wick Thursday reversal candle.

---

## You Are Using Discount and Premium Wrong! - EQ For Expansions (`IPZjNI1B5a0`, https://youtu.be/IPZjNI1B5a0, 1164s)

### What is actually taught

The EQ video, and it settles the measurement question. **It confirms the Q&A-derived rule the
library was carrying and refines it in two ways.**

The tool is trivial: "a simple Fibonacci with a 0.5 and a 1 marked out", usually reduced to just
the 0.5. The measurement is stated as an invariant, in the first thirty seconds: *"I'm always
going to measure the candles from Wick High to Wick low"* and then mark equilibrium that way —
followed immediately by the exclusion, *"I'm not going to use the bodies"*, because bodies are
what he uses for the change in the state of delivery and for order blocks. **That is a direct
rejection of the "50% of the bodies of the opposing candle" reading recorded in the library from
`yud7TpE2AMs` / `00iZXPAdR5A`.** Bodies belong to the CISD and the order block; wicks belong to
the EQ. Both statements are his, so `equilibrium-eq` stays `contested`, but the primary teaching
is unambiguous on which construction it means by EQ.

The **large-wick exception is confirmed**, in almost the words the Q&A gave: on a candle with a
big wick, *"a very large Wick so it doesn't really make sense to use the EQ"* of the whole candle,
and *"it will make a lot more sense to use 0.5 of this Wick here"* — with an explicit cross-
reference back to the wick video. And he supplies something the Q&A did not: **a readable switch
trigger.** He views a candle as a reversal when price closes above the midpoint — *"this candle's
range which is generally when I view it as a reversal"* — and *then* uses 0.5 of that wick. So the
rule is ordered: default to 0.5 of the whole high-to-low range; if the candle reads as a reversal
(carrying a large wick, close beyond its own midpoint), switch to 0.5 of the wick.

The video's title claim is the **inversion of premium/discount**, and he gives the reason rather
than just the assertion. He acknowledges the standard ICT usage, then: *"however I use it the
opposite"*. The justification is phase-based — in an expansion phase, which is the phase he
trades, *"price rarely goes in retraces to a discount or to a premium"*, so waiting for a discount
entry means missing the move. He therefore uses the half as a **filter that must hold**, not a
place to enter counter to the leg: "looking for the upper half to respect for price to trade
higher" and the lower half for lower, and "if these do not respect I then can flip my bias and
anticipate the low" of the range being taken. This is the same rule the library holds from
GxTradez as `upper-half-eq-expansion-filter`, now in the channel's own voice.

The operating procedure is the other real deliverable and was not in the library at all. Each day
he writes an explicit conditional: *"I give myself an if then scenario"* — "if the EQ is respected
then we can trade lower through previous day low", if not, flip and target the failure swings on
the high. He then searches **only the half consistent with the bias** for something to react at:
*"match PD arrays in that range"* — a fair value gap, an opposing candle / order block, or a
protected swing — and takes the protected swing in that half as the day's invalidation, saying
*"I mainly focused on finding an invalidation for that day"*. A PD array that is tagged and not
respected is simply ignored ("is this fair value Gap respected no it is not so I pretty
much ignore") and he moves to the next. Entry is on the CISD or the order-block formation at the
array. He also concedes the half sometimes contains nothing usable — "this is where it's not
always perfect… we don't really have a PD in the lower half of this range" — and in that case
allows price to run further than usual on the basis of hourly structure.

Two further constraints surface in passing. An order block is rejected on structural grounds:
*"trust this as an order block because it is just in a consolidation"* is what he will not do, and
instead "I will use the high of the range as a point of interest", looking there to "either look
for a sweep or an smt on that high". And the exhaustion rule reappears with a count: "3 days of
expansion into lows this is where I'm going to avoid price", waiting for new daily closures.

The closing section demonstrates fractality by rerunning the whole method on the 4-hour: "this is
a fractal concept you can see I was using it on the daily", with the practical limit stated — "I
prefer the daily 4H hour hourly candles" because "doing this on a 5minute chart it just becomes a
lot to look at". A **propulsion block** is named once in this section (order block plus fair value
gap, once respected) and never defined. The one instrument named is **YM**.

### Concepts introduced

- **EQ measured wick-high to wick-low, never on bodies** — with bodies reassigned to CISD/order blocks.
- **The large-wick exception** — 0.5 of the wick instead of 0.5 of the candle.
- **The switch trigger** — a close beyond the candle's own 0.5 reads as a reversal.
- **Inverted premium/discount**, with the phases-of-price justification.
- **The upper-half / lower-half expansion filter**, and the bias flip on violation.
- **The if/then scenario** written before the candle opens.
- **PD array matching inside the correct half only.**
- **Invalidation-first preparation** — find the protected swing before the point of interest.
- **Order block rejected inside a consolidation** — use the range extreme, sweep or SMT.
- **Three-expansion-candle exhaustion** → avoid price.
- **Propulsion block** (named once, undefined), **T-spot** (named once).

### Rules / conditions stated

- Draw the fib wick-high to wick-low; EQ := 0.5. Never use bodies for EQ.
- If the candle carries a very large wick, use 0.5 of that wick instead.
- A close beyond 0.5 of a candle's range generally reads as a reversal; then use 0.5 of its wick.
- Apply the previous completed candle's EQ to govern the current one.
- Bullish: require the upper half to hold. Bearish: require the lower half.
- If the half is not respected, flip the bias and anticipate the opposite extreme.
- Write both branches of the if/then before the candle opens.
- Search only the correct half for a PD array; ignore one that is tagged and not respected.
- Take the protected swing in that half as the day's invalidation.
- Confirm with a CISD or an order-block formation before entry.
- Do not trust an order block formed inside a consolidation; use the range extreme instead.
- If the range has already expanded (e.g. a gap through), wait for the next closure.
- After roughly three expansion candles in one direction, avoid price and wait for new closures.
- Fractal across timeframes; daily / 4-hour / hourly preferred, 5-minute declined.

### Quotes

- "I'm always going to measure the candles from Wick High to Wick low"
- "it will make a lot more sense to use 0.5 of this Wick here"
- "however I use it the opposite"

### Open questions / ambiguities

- "A very large Wick" — the trigger for switching to the wick EQ — is not quantified, and the
  decidable proxy (a close beyond 0.5 of the range) is hedged with "generally".
- He allows price to trade "slightly a bit higher" than the exact 0.5 of a wick, so the level is a
  zone of unstated width.
- Wick touch versus body close through the EQ is never distinguished.
- CONTESTS the body-based EQ reading recorded elsewhere in the library; the two cannot both be the
  general rule.
- No precedence rule when several PD arrays sit in the correct half.
- "Three days of expansion" is stated once by example, not as a rule.
- Whether the if/then is written on the daily only or on whichever timeframe is in use is not said.
- The instrument for the SMT he looks for at a range extreme is never named.
- "Propulsion block" is used once and never defined.

---

## Cross-video observations

- **This unit is the primary teaching for four terms the rest of the corpus assumes.** Where it
  conflicts with a live Q&A answer, the conflict is recorded, not resolved by preference — but for
  a strategy build, the dedicated video should be treated as the reference reading.
- **Two of the four blockers are now mechanised, one is half-mechanised, one is not.**
  *Look-back* (three HTF candles, current inclusive, fractal) is fully decidable. *Speed* (1–3
  candles for the V-shape) is fully decidable. *EQ* is decidable once you accept the ordering
  (whole range by default, wick when the candle reads as a reversal) — the residual gap is the
  size of the "very large wick" that triggers the switch. *Separation* and *wick size* are not
  decidable and, on the evidence of their own dedicated videos, will not become so from this corpus.
- **The wick and the EQ videos are the same rule seen from two sides.** The wick video says a large
  opposing run makes the candle a reversal candle and moves the target to the open; the EQ video
  says a close beyond the candle's own 0.5 makes it a reversal candle and moves the reference to
  0.5 of the wick. The 0.5-of-range close is the closest thing the corpus gives to a *decidable
  proxy for "large wick"* — and it is the only one. That is the single most useful cross-video
  inference in this unit, and it is an inference, not a statement: he never says "a wick is large
  when price closes beyond the candle's EQ".
- **Time is the under-recorded half of the wick filter.** Every prior library entry grades wick
  size on price alone. The dedicated video grades it on price *and* elapsed candle time, and the
  timing half is what drives the "wait for the next candle open" doctrine, the difficulty ladder,
  the 40-minute rejection, and the dismissal of macros. A detector that only measures wick-to-range
  is implementing half of the taught rule.
- **The CISD question is narrowed but not closed.** The reference price is still unnamed. The
  series-length question is answered in favour of "may be one candle". A third gate — speed —
  is added.
- **One filter runs through all four videos**: nothing is tradeable on shape alone. A relevant
  swing needs a c2/c3 closure at it; a small wick needs a lower-timeframe CISD to confirm it; an EQ
  reaction needs a CISD or an order-block formation; a continuation needs a V-shaped closure and,
  where liquidity was just taken, a second one.
- **Terms used but never defined in this unit** (assumed from earlier playlists): candle 2 /
  candle 3 / candle 4 closure, protected swing, fair value gap, PD array, SMT, T-spot, high
  resistance liquidity, propulsion block, phases of price.
