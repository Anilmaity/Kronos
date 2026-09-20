# Build A Model — Intro to TTrades Fractal Model, part 1 (unit_id: `build_a_model_intro_to_ttrades_fractal_model_01`)

Channel: TTrades_edu. Playlist: "Build A Model - Intro to TTrades Fractal Model (TTFM)".
20 of the playlist's videos; the remaining 24 sit in units `..._02` and `..._03`.
All 20 transcripts present and readable.

**This is the primary teaching.** Everywhere the library previously held a `fractal-model-*`
concept assembled from secondhand mentions in Q&A streams, this unit supersedes it. Where the
two disagree, the disagreement is recorded in the concept's `ambiguities` and this note's
cross-video section.

### Transcript hygiene

Sources are mixed: eight files are `auto-en` (punctuated), twelve are `yt-dlp-auto`. Two are
badly degraded and quotes from them look wrong but are verbatim:

- **`LKNQDAdId4s` (wicks)** has *no punctuation at all* and randomly capitalises: "Wicks"
  becomes **"Wix"**, "wick" becomes **"Wick"** mid-sentence. Quotes preserve this.
- **`kTWXpAo1uE8` (standard deviations)** mangles the negative fib numbers: "-2.5" appears as
  `-2 .5`, "-4" as **"the4"**, "-1" as **"ne1"**, "-2 to -2.5" as **"R2 to 2.5"**. The one
  quoted settings string (`1 0 -1 -2 -2.5 and -4`) is intact.
- **`-wr4xATE37g` (protected swings)** truncates "down-close" to **"downclo"** / "downlosed".
- The known corpus artifact **"candle 2" → "candle to"** appears throughout the punctuated
  files ("a candle to closure"). It is read as *candle 2 closure* everywhere.
- `-ocfPuD_oqE` renders `&` as `&amp;` ("S&amp;P 500") and ends with a stray "&gt;&gt; Hey."

**No transcript in this unit carries timestamps, so no `approx_time` is recorded anywhere in
this unit's concept files.**

---

## Best Trading Strategy for 2026 - TTFM (`v1X8UMWgWmI`, 955s)

### What is actually taught

The whole model in one video, pitched at beginners but explicitly not only for them. Three
layers, top down. Layer one is a **daily bias**, described as the most important part: you are
anticipating a daily *expansion* candle. That anticipation comes from a candle 2 closure (sweep
of the previous candle, close back inside) or — when candle 2 failed to close back inside — from
a candle 3 closure on the next candle, which engulfs the previous candle by closing over its
body. Either way an aligned lower-timeframe change in the state of delivery must exist inside
that candle before anything is tradeable: "If there is no change in the state of delivery" you
do not trade.

Layer two drops to the **4-hour** and looks for exactly the same thing again — a 4-hour candle 2
or candle 3 closure with its own CISD. Layer three drops to the **15-minute** and takes a
continuation entry: a point of interest (a swept low or a fair value gap, ideally both) followed
by a close over the series of opposing candles into it — a new protected swing. The stated goal
is to trade candle three on multiple timeframes at once.

The examples make the failure modes concrete. In the Bitcoin example a valid daily candle 2 with
an hourly CISD produces *no trade at all* on the first day because the 4-hour never formed a
swing point — it only made failure swings. He waits, the daily closes over candle 2's high
(licensing a candle 4 continuation), the next 4-hour candle prints a candle 2 closure, and only
then does the 15-minute entry exist. The last example shows the positional case: a continuation
had already formed *before* the daily open, so the entry is taken at the opening price with the
stop on that pre-open protected swing.

### Rules stated

- Daily bias comes from a daily C2 closure, or a C3 closure if C2 did not form.
- A C2 closure requires a CISD inside it before candle 3 is traded; a C3 closure requires one
  before candle 4 is traded.
- C3 closing over C2's high licenses a candle 4 continuation.
- Then the same test on the 4-hour, then a 15-minute continuation entry.
- The continuation needs a point of interest: a swept low, or a fair value gap, "or ideally both".
- Entering after the target has already been taken and price has consolidated is discouraged —
  wait for a new continuation.
- You do not *have* to trade an expansion candle on the daily; it is just the easiest.
- Counter-daily setups exist and are visible but are declined on principle.

### Open questions

- "Reversal then expansion" is the causal claim behind the whole model and is asserted, never
  evidenced.
- Nothing quantifies "the 4-hour never made a swing point" versus "made failure swings".

---

## Candle 2 Closure: The Foundation of TTrades Fractal Model (`tyoxl1l-6iI`, 786s)

### What is actually taught

**The primary-source definition of the model's foundation candle, and it is mechanical.** The
model has exactly two closure types, C2 and C3, and they are separated by *where the candle
closes relative to the previous candle's extreme*:

- **Continuation closure** — sweeps the previous candle's low and *closes below it*. Anticipate
  continuation.
- **Reversal closure = candle 2** — sweeps the previous candle's low but *closes back inside the
  previous candle's range*, i.e. back above that candle's low. Anticipate reversal.

Note the exact wording: the close must be back above **candle 1's low** (or below candle 1's
high), not back inside candle 1's *body*. That is a looser test than some Q&A-derived readings in
the library assume.

Two gates then apply and both are stated flatly. First, the closure must occur **at a
higher-timeframe key level / point of interest** — "If you just look for every pattern that has a
sweep and a closure back in, that is unlikely to work." His point-of-interest set is named:
fair value gaps, and highs and lows. Second, the closure is confirmed on the **aligned lower
timeframe** by a change in the state of delivery: find the extreme, find the series of candles
that made it, wait for the close through.

The teaching method is the most useful part: mark out *every* swing point on a daily chart, then
strike out the ones that are not candle 2 closures (price never closed back inside), then strike
out the ones with no point of interest. What survives gives the bias for each day. He runs this
live and produces a day-by-day bias string ("bearish this day, bullish this day…").

The sequence continues: C3 closing over C2's high licenses C4. Blending with the EQ video: if C2
has a large wick, watch the upper half of that wick — if candle 3 does not respect the 0.5, "then
it's likely to fail and a swing point is unlikely to form". For C3 he marks 50% of the *entire
candle's range* instead.

### Rules stated

- Bullish C2: trades below candle 1's low, closes back above it. Bearish: mirror.
- A close *beyond* candle 1's extreme is a continuation closure, not a C2.
- C2 requires a point of interest — fair value gap, or a high/low taken out. "I need a point of
  interest to frame a candle closure."
- A point of interest may come from far up the tree (a monthly high is used).
- Opposing candles / a protected swing can serve as the point of interest — flagged as "more
  advanced".
- Confirm on the aligned lower timeframe: daily→hourly, hourly→5-minute, 4-hour→15-minute.
- C2 should itself be a reversal; a C2 with a shallow wick that already expanded is *valid* but
  "does not set up the best conditions for candle 3".
- Large-wick C2 → candle 3's wick must respect 0.5 of that wick.
- C3 strong close over C2's high → candle 4 continuation.
- Candles 5 and 6 are where "you can get caught in a new phase of price".

### Open questions

- Whether the sweep must be a wick-through or may be a full trade-through is not said.
- No ranking among points of interest when several are present.
- "Shallow wick" appears again as a quality discriminator with no threshold.

---

## EURGBP for Relative Strength (EU vs GU) (`nWHint4Yano`, 724s)

### What is actually taught

A genuinely mechanical asset-selection procedure, and one of the few fully decidable things in
the unit. Precondition: **the dollar must not be consolidating** — only then are EURUSD/GBPUSD
tradeable at all. To decide which one, read the cross **EURGBP**: bullish EURGBP means euro
stronger / pound weaker; bearish means euro weaker / pound stronger. Then pair with the dollar's
direction — bullish dollar, short the weaker foreign currency; bearish dollar, long the stronger
one. "Pairing a strong currency with a weak currency gives you a nice bullish trend."

The cross itself is read with the ordinary machinery: daily candle 2 closures, hourly CISD,
protected swings. A secondary cross-check is offered — compare the individual daily closures of
EURUSD and GBPUSD directly; the weaker one closes more decisively through its opposing candles.
The final side-by-side comparison is the payoff: on the same expansion day GBPUSD trends cleanly
while EURUSD barely moves, and GBP runs its low at 08:00 while EUR does not until 09:00.

The video also drops a weekly-profile aside in passing: a Monday/Tuesday/Wednesday low on DXY
leads him to anticipate candles 3 and 4 finishing the week, and elsewhere a Mon–Wed expansion
with a Thursday counter leads him to expect Friday back into the range.

### Rules stated

- Dollar consolidating → do not trade EU or GU.
- EURGBP bullish → euro stronger. EURGBP bearish → euro weaker.
- Bullish dollar → short the weaker. Bearish dollar → long the stronger.
- Cross-check with the two pairs' individual daily closures.
- Then apply the ordinary fractal model on the selected pair.
- Consolidation on the selected pair is not traded away from without an SMT to substitute.

### Open questions

- No rule for what to do when the EURGBP read and the individual-closure check disagree.
- "Consolidating" for the dollar inherits the unbounded consolidation definition.
- The same logic is asserted for NQ/ES but the index equivalent of the cross is not named.

---

## Easy Daily Bias - Mechanical Framework (`-KKuZb5Z5aU`, 1051s)

### What is actually taught

The title promises mechanics and it mostly delivers. Bias is a **binary between reversal and
continuation**, and the reversal is *always* framed off the previous day's high or low — never an
arbitrary level.

- **Reversal**: price opens, trades into the previous day's extreme, a lower-timeframe CISD
  confirms the wick, price trades back into the range toward the EQ or the opposite previous-day
  extreme.
- **Continuation**: price opens, trades *against* the bias first, **respects the EQ of the
  previous day's range**, then trades through the previous day's extreme.

Two things here are more precise than anywhere else in the corpus. First, "respect the EQ" is
operationalised negatively: it is not about touching the level — "price can form its high below
that level" — it is about *closures*: "it's not ideal to have closures on the hourly chart below
that." Second, the candle-shape rule is stated bare: "When price opens and makes a low first,
that is bullish. When price opens and makes a high first, that is bearish."

The confirmation timeframe is set by session — hourly or 30-minute in Asia/London, 5-minute or
15-minute in New York — which is the same map the daily-profile video builds out fully.

Wick size decides whether the *reversal day itself* is tradeable: small wick yes, large wick no,
wait for the following candle. This is stated three separate times and never quantified. He also
says how far past the previous day's extreme to expect price to run "is really dependent on the
wick size of this reversal" — large wick, little range beyond; small wick, expansion.

Two other rules land here. Points of interest are sought *on the correct side of the EQ*, and
rather than guessing which of several will react, he waits for a swing or protected swing to form
in that area. And a protected swing "is only protected until it hits liquidity" — a recurring
pattern is liquidity taken, *then* the protected swing swept, *then* the true move.

The last third demonstrates the fractal application (hourly + 5-minute, using the previous
*candle's* high instead of the previous day's) with an important limit: "I don't prefer to go
below the four-hour time frame as it just becomes a bit more difficult" — for framing reversals
specifically.

### Rules stated

- Reversals are framed only off previous day high / previous day low (fractally: previous
  candle's high/low).
- Continuation requires: open, opposing move first, EQ of the previous day's range respected
  (no hourly closures beyond it), then through the previous day's extreme.
- Open-low-first = bullish; open-high-first = bearish.
- CISD timeframe by session: hourly/30m in Asia and London; 5m/15m in New York.
- Small-wick reversal candle → tradeable. Large-wick → wait for the next candle.
- Distance beyond the previous day's extreme scales with wick size.
- Do not guess which point of interest reacts; wait for a swing to form.
- A protected swing holds only until liquidity is hit.
- For reversal framing, do not go below the 4-hour.
- SMT is preferred alongside a candle 2 but is not required.

### Open questions

- Three different things are called "the EQ" across this unit (previous day's range, current
  candle, 0.5 of a wick) — see cross-video below.
- The bearish/bullish retracement case is muddied once: a bearish CISD at the previous day high
  is accepted as "part of a retracement, not a full on reversal" because bias was bullish, with
  no test for which reading applies.

---

## Higher Timeframe Analysis - Aligning Expansion Candles (`Kf4c41_qO1s`, 724s)

### What is actually taught

This is TTrades' own statement of a concept the library previously held only in a guest's voice
(`aligning-expansion-candles`, sourced from GxTradez in `t_talks_02`). The two readings agree.

Premise: "when a true trend occurs, all candles are aligned in the same direction." Wick size is
the gate at every layer — "Candles that support expansion will have a small wick and a large
body"; candles that don't "have a large wick or a large opposing run". The mechanism given is
temporal: a candle that opens and spends a long time making its opposing run *cannot* trend,
because it will return toward its opening price.

The quantities are unusually explicit for this channel. **Minimum two aligned expansion candles**
— a daily plus a 4-hour is enough to execute on the 15-minute. **Three preferred** (daily +
4-hour + hourly or 30-minute) for a 5-minute or 3-minute execution. And the cleanest expression:
"a daily candle 3, a 4hour candle 3, and an hourly candle 3 … By definition, that is just a
trend."

The second example is the interesting one because the daily *fails* the filter — it has a large
opposing run — and he does not stand aside. Instead the targets shrink: back toward the daily
open or the intraday highs rather than a large move, with the 4-hour and hourly still supplying
the aligned expansion. That is a branch the library did not have.

The video also gives his literal chart layout: a daily power-of-three indicator at offset 15
(or 32 for a three-layer view), his fractal model indicator at offset 17 with most drawings off,
and a third copy fully configured on the execution pairing.

### Rules stated

- Every layer must independently have a small wick / large body in the intended direction.
- A candle that opens and trades against the intended direction first does not support
  expansion — wait for its next open.
- Minimum two aligned layers; three for sub-5-minute execution.
- Then align structure via protected swings / continuation order blocks.
- Reversal variant is possible (small-wick reversal + protected swing) but harder to anticipate.
- Daily not supporting expansion → trade anyway with reduced targets (daily open / intraday
  extremes).
- Expansion candles are expected to close near their extremes.

### Open questions

- "Small wick" gates every layer and is never quantified.
- No rule for choosing between the reduced targets when the daily fails the filter.

---

## How To Actually Trade Inversion Fair Value Gaps (IFVG) (`FKTBkTzsmUA`, 760s)

### What is actually taught

The fair value gap definition is given cleanly — a three-candle pattern where "the wick of candle
one and the wick of candle three do not overlap" — and the inversion is a fair value gap "not
respected and swiftly closed over", flipping resistance to support.

But the video is really about the *gate*, not the pattern. The named mistake is pattern trading:
people look for a sweep, an inversion, an entry, and "they fail to look at the higher time
frames". Within the fractal model an inversion is only valid inside a **candle 2 that supports
expansion**: a sweep of candle one's high/low, a **small wick**, then the inversion. If the candle
has a large opposing run, the inversion is not traded on that candle — "generally that
expansion's going to wait for the next higher time frame candle", so you take the entry on the
next candle's open or on a continuation that follows.

Two mechanical refinements that are worth having. **Stacked gaps are treated as one**: "I want to
use all of those fair value gaps and treat it like one" — and the closure must clear the whole
series. In one example that rule alone "save[s] ourselves a loss". And a tolerance rule, stated
as "the one rule I have": a single rejection of the inverted level is fine provided price quickly
closes back through; repeated failure that becomes a consolidation means waiting for a new
high/low first.

Also stated: an inversion may be used **in place of** a change in the state of delivery to confirm
a continuation. And when a level is reached without a V-shape reversal — only consolidation —
"this is where I want to avoid price", even if the move would have worked.

### Rules stated

- FVG = 3 candles, wicks of 1 and 3 do not overlap.
- IFVG = that gap not respected and swiftly closed over; support/resistance flips.
- Valid only with: a sweep of the previous HTF candle's extreme (or SMT), a small wick on that
  candle, then the inversion.
- Stacked gaps count as one; the close must clear all of them.
- One rejection tolerated if price closes back through quickly; repeated failure → wait for a new
  extreme.
- Large opposing run → wait for the next HTF candle open.
- An inversion can substitute for the CISD on a continuation.
- SMT between candle 1's and candle 2's extremes is optional extra confluence.
- No V-shape at the level → avoid price.

### Open questions

- "Swiftly" has no bar limit; "small wick" again unquantified.
- The number of tolerated rejections beyond one is not given.

---

## How To Trade Consolidation - Phases Of Price (`WFqLwOp2pXw`, 1107s) — part 1 of 5

### What is actually taught

**The most valuable extraction in the unit: consolidation gets a crisp, decidable definition.**
"A consolidation is when price remains internal to a high and a low" — by marking a low and a
high, price does not take out the high and does not take out the low, for a period of time. It is
expected after a large range or when price hits a higher-timeframe level, because "price moves
from large ranges to small ranges".

The trading instruction is explicitly negative: do not trade inside the range, because that is
guessing the break direction, "which generally I do not know". Wait for **manipulation** — one
side run out — then trade away from it. Bullish wants the low run; bearish wants the high run.
This is framed as textbook accumulation / manipulation / distribution. The one exception is SMT:
"we don't need price to run out the high or the low" if the correlated asset ran it.

Consolidations resolve two ways and the discriminator is stated: **continuation** when no
higher-timeframe level has been hit and an objective is still open; **reversal** when a
higher-timeframe level has been hit. The associated PD array is discount/premium — if price
deviates from a consolidating range, expect a return to the equilibrium.

The rule survives contact with messy charts in a useful way. When price pokes outside the marked
range he does not abandon the label: "Is price remaining internal to these? No. But it is failing
to trade out of it, right? So, it is still consolidating" — and re-adjusts the range boundaries.
The last example flatly counts an 18-hour range on USDJPY. One example also introduces the
fallback point of interest: "We do not have a fair value gap or a low to be swept out in here…
That is when I can use 0.5 of this opposing candle here."

### Rules stated

- Consolidation = price internal to a marked high and low for a period of time.
- Occurs after a large range or at a higher-timeframe level.
- Do not trade inside the range; wait for one side to be manipulated.
- Bullish → wait for the low to be run. Bearish → the high.
- SMT on a correlated asset substitutes for the sweep.
- After the sweep: enter on the reversal, or wait for the closure through the opposing candles
  (the protected swing) and trade the continuation. He prefers the latter.
- Continuation vs reversal: no HTF level hit and an objective open → continuation; HTF level hit
  → reversal.
- Deviation from the range → expect a return to the range EQ.
- A close over the previous high without a sweep is a "breakout signature" and also continues.
- Fallback POI when there is no gap and no sweepable low: 0.5 of the opposing candle.

### Open questions

- "For a period of time" is unbounded — no minimum bar count. Examples span ~3 bars to 18 hours.
- The re-adjust-the-range allowance has no limit on how far a poke may go.
- Which of several highs/lows to mark as the boundary is done by eye.
- The breakout branch has no condition telling you when to trust it over waiting for a sweep.

---

## How To Trade Expansion - Phases Of Price (`4Gm8p6O7Ebs`, 1114s) — part 2 of 5

### What is actually taught

Expansion is defined twice, and both are qualitative: "expansion is when we have a one-sided
trending move", and — the signature — "we have very shallow moves against the trend and that is
the signature of expansion". Summarised later: "Expansions are large ranges that have shallow
retracements." The cycle is the organising idea: large range → small range → large range.

The interaction rule matters because it is a *negative* one: inside an expansion you do **not**
wait for price to trade back into a discount. You look for opposing candles to support price —
down-close candles in a bull leg, up-close candles in a bear leg — and take protected swings as
they form, positioning in the upper half of the higher-timeframe candle via the EQ.

The stand-aside rule is stated here and reused across the unit: "after we have 3 days of
expansion, this is generally when it can set up" some retracement, reversal or opposing move. He
also says plainly "I don't really want to enter a trade right after an expansion because that's
when we can get a new phase of price delivery." The silver example runs the count explicitly:
three days of expansion into an objective → let another day form.

The video's real content is the running commentary of labelling, and it is honest about the
ambiguity — repeatedly "let another candle print", "that looks like it could be a retracement or a
reversal based off this closure". The fractal claim is stated and demonstrated on daily and hourly
of the same chart.

### Rules stated

- Expansion = one-sided trending move; shallow moves against.
- Expected after a consolidation or a retracement.
- Do not seek deep retracements into discount; use opposing candles and protected swings.
- Position in the upper half of the higher-timeframe candle (bullish).
- After ~3 days of expansion, expect a new phase; do not enter right after an expansion.
- Reversals off an expansion form at previous day highs/lows.
- Anticipating a consolidation lets you refuse trades: no sweep of the range low, no long.

### Open questions

- No threshold for "shallow", "one-sided", or "large range".
- The 3-day count is hedged with "generally" and one example accepts two very large days.

---

## How To Trade Retracement - Phases Of Price (`F0G31iLVpVg`, 1076s) — part 3 of 5

### What is actually taught

A retracement is "a slow shallow move opposing the trend", the mirror of expansion:
"Expansion is aggressive, fast and large range. Retracement is slow and shallow in a small
range." It sits between two expansions and generally terminates in a **fair value gap**.

The one genuinely quantitative thing in the whole phases series is here, and it is a *time* ratio
rather than a price ratio: "9 hours worth of candles took up the range of about three hours of
expansion." The reversal video repeats the pattern — "Takes three candles to get all of this
range here. And it takes what? Eight candles to just go back up. 2/3 of that." So the operational
test for slowness is a bar-count ratio of roughly 3:1 against the leg being retraced. It is never
stated as a rule, only demonstrated twice.

Failure swings forming on the opposing extreme are named as the expected accompaniment and become
the targets once expansion resumes. Two entry options are given as equivalent: take the candle 2
closure inside the fair value gap on a lower timeframe, or wait for the closure through the
series of opposing candles on the current timeframe.

There is a direct **tension** the video does not resolve. Retracements should be slow (more bars
than the expansion) — but also: "generally another thing you want to see with retracements is you
want to see them be quick. You want to see expansion, retracement, expansion. If we expand, start
a retracement and then we fail to confirm that … This is now just a consolidation." So slowness is
the identifying signature and quickness is the quality filter, with no bar count separating them.

The EURUSD 5-minute example is deliberately a *failure* example — no sweep for the short, no
retracement into the gap for the continuation — used to make the point that "not everything is
going to be perfect" and that missing the move is an acceptable outcome. He also declines a
shallow reach into a gap: "I personally don't really trust that. I'd like to see a consolidation
low swept out. Give me a wick I trust."

### Rules stated

- Retracement = slow shallow move opposing the trend, between two expansions.
- Terminates at a PD array, generally a fair value gap. Bodies respect it even if wicks dig deeper.
- Failure swings form on the opposing side and become targets.
- Entry: candle 2 closure inside the gap (lower timeframe), or the protected-swing closure on the
  current timeframe.
- A retracement that fails to confirm with a closure and then ranges is re-labelled a consolidation.
- Strong expansions have shallow retracements or none at all.
- A shallow reach into a gap without a swept low is not trusted.
- Stop on the wick, or the body where a body stop is untrustworthy for lack of wick; target 2R.

### Open questions

- "Slow" and "quick" are both required and never reconciled.
- "Shallow" is unquantified; one example allows the retracement to "dig a bit deeper".
- Bodies-vs-wicks respect of the fair value gap is stated once, in passing.

---

## How To Trade Reversal - Phases Of Price (`VD4xb9VfMHA`, 1081s) — part 4 of 5

### What is actually taught

The crispest definition of the four: "A reversal is when we have expansion met with expansion."
It is the explicit opposite of a continuation signature (expansion → retracement, or expansion →
consolidation → manipulation). The pair of opposing expansion legs is what forms the
higher-timeframe wick, which is the bridge to the rest of the model.

The location gate is emphasised harder here than anywhere: "We want to see a reversal form at a
point of interest" — an old high/low or swing high/low — and, negatively, "you don't want to
choose a random high and low for price to reverse off". The easy way to find relevant ones is
named: "focus on previous days highs and lows or previous week's highs and lows". The first
example is built entirely around this: a structurally perfect reversal is rejected because it
would leave failure swing highs resting, i.e. the level was not relevant.

The ideal form is a V-shape: expansion into a low that sweeps out lows, then a clean expansion
away that also closes over the series of down-close candles. The rationale offered is
positioning-based — early longs get swept out, breakout shorts get trapped, "this structure here
is throwing everyone out of the market". You do not need to catch the extreme: the alternative is
to take the following continuation off a protected swing.

The video is also where the three-way classifier is drilled: after every expansion, ask — is this
a retracement (slow, shallow), a consolidation (sideways), or expansion met with expansion
(reversal)? If the candle does not decide, "the candle closures give you new data" and you let
another one close. Where a reversal candle carries a large wick, "would have to respect 50% of
this wick to trade lower".

### Rules stated

- Reversal = expansion met with expansion.
- Only sought at a relevant point of interest: an old/swing high or low; previous day and
  previous week extremes are always relevant.
- Ideal form: V-shape plus a close through the opposing candles (CISD).
- Prefer the swing high that *created* the swing low as the opposing-candle series.
- If the candle does not decide between the three phases, let another close.
- Large-wick reversal → 50% of that wick must be respected.
- Missing the extreme is fine — take the following continuation off a protected swing.
- Trading against the trend is only permitted after a relevant extreme has been taken.

### Open questions

- "Expansion met with expansion" inherits every ambiguity of "expansion", so the test is
  decidable only once an expansion detector is fixed.
- How *immediately* the second expansion must follow is not stated — one example takes several
  candles and still counts.
- Unlike the guest reading in `t_talks_02`, SMT is used here as confluence but is **not** stated
  as a requirement of the reversal signature.

---

## How To Use SMT Divergence - TTrades Fractal Model (`-ocfPuD_oqE`, 812s)

### What is actually taught

Doctrine first, mechanics second. "SMT is not used to force yourself upon a model, but it is used
as a confluence within the model" — and the ordering is absolute: "I'm finding a framework and
then applying SMT to that", "If my model has not formed, I do not look for SMT yet." One example
exists purely to enforce this: an SMT is clearly visible on gold, and he refuses it because the
hourly CISD has not closed through yet; once it does, the SMT is allowed to count.

The taxonomy is the new content and it is indexed on the candle sequence:

- **Reversal SMT** — divergence between candle 1 and candle 2 (at the reversal).
- **Continuation SMT** — divergence between candle 2 and candle 3 (during the continuation).
- **Double SMT** — both in the same sequence.

If you want to trade the candle 2 *reversal* itself rather than the C3 continuation, an extra gate
applies: the candle must independently support expansion — small wick — before the SMT counts.
The gold example uses gold-euro and gold-pound as the correlated set; the index examples use
ES/NQ/YM; USDCAD is paired against the dollar; AUDUSD against NZDUSD.

Two honest failures are shown. One valid model with SMT and a CISD simply loses because the day
opened low first and invalidated the EQ — "just because you see SMT doesn't mean everything's
going to work." Another is called "a bit messy" because the divergence resolves differently
depending on which of the three indices you stand on.

### Rules stated

- Find the model (C2/C3 closure + aligned CISD) first; only then look for SMT.
- Reversal SMT = C1↔C2; continuation SMT = C2↔C3; double = both.
- To trade the C2 reversal on SMT, the candle must have a small wick.
- SMT never replaces intraday confirmation that the wick has formed.
- SMT can be marked on both the higher and lower timeframe.

### Open questions

- Which correlated asset is authoritative when ES, NQ and YM disagree is never resolved.
- No tolerance for how far apart the two extremes may be and still count as a divergence.
- Whether the divergence must be at the same bar index on both assets is unstated.

---

## How to Confirm Daily Profile (High or Low of Day) (`Mo9QMtotQyo`, 1457s)

### What is actually taught

**The most explicit session→timeframe map in the corpus.** The single question asked all day is
"Has the daily candle formed its wick?" Two instruments answer it — a change in the state of
delivery, or a candle closure — and which timeframe you use is set by session volatility:

| session | CISD | candle closure |
|---|---|---|
| Asia | hourly | 4-hour |
| London | 15-minute or 30-minute | 4-hour |
| New York | 5-minute or 15-minute | hourly (sometimes 30-minute) |

A higher-timeframe CISD always counts if it has already occurred — the map is a floor, not a
ceiling. The reason for dropping down in New York is stated as a cost, not a preference: wait for
the hourly CISD there and "price will leave you behind". The typical New York shape is given
concretely: an opposing move at 9:30, the 09:00–10:00 candle closes as a candle 2, and the 10:00
candle is the tradeable candle 3.

The best teaching is the running refusal. Example one walks candle by candle through Asia and
London saying "no… no… I don't trust that" — including refusing an hourly doji closure after a
large move down ("This is expansion. This is more of a consolidation") — until *both* a 30-minute
CISD in London and later an hourly CISD plus a 4-hour candle 2 closure line up. He also declines
5-minute pre-market entries because they get swept, using the 15-minute pre-open instead and
dropping to 5-minute (or 3-minute) only after 9:30.

The third example is the one worth keeping: **bias dominates the mechanics**. "If you have a
wrong bias, you can mechanically confirm the wick high or wick low of the day and still be
wrong." The confirmation was correct; the read was not; the low got run.

The final point is subtle and reframes the whole exercise: the level being confirmed need not be
the literal high or low of the day. "This is not technically the high of the day… but we are
confirming this, treating it like the high of the day because we're trying to find a high to
trade away from."

### Rules stated

- Ask continuously: has the daily candle formed its wick?
- Asia: hourly CISD or 4-hour closure. London: 15m/30m CISD or 4-hour closure. New York: hourly
  closure or 5m/15m CISD.
- A higher-timeframe CISD is always acceptable if already present.
- The closure used must be a C2 or C3 closure at a point of interest, read against the daily EQ.
- Do not trust an hourly closure early in the day.
- Pre-open entries on the 15-minute, not the 5-minute.
- Confluence preferred: hourly CISD *and* 4-hour closure.
- Invalidation days: once price breaks the EQ level and stays below it, stay bearish.
- The confirmed level need only be a high/low to trade away from.

### Open questions

- Session boundaries are never given as clock times and no timezone is named in this video.
- The "either / both" question — is a 4-hour closure an alternative to the hourly CISD or should
  both be present — is stated both ways.
- The refusal of hourly closures "early in the day" is a judgement, applied inconsistently (they
  are accepted in New York).

---

## How to Set Price Targets Using the Fractal Model (`A4NasIa371c`, 793s)

### What is actually taught

Deliberately the simplest rule in the model: whatever timeframe you enter on, take the targets
from the **higher timeframe you are referencing**, and they are that higher timeframe's previous
candles' unswept highs (bullish) or lows (bearish). Candle 1's extreme first, then progressively
older ones. "We're always focused on swing highs and swing lows in the market."

Two filters. Extremes already taken out are not marked — "why am I not marking out this high
here? Well, it's already been taken out". And a target counts as satisfied when the *correlated*
asset takes it out: on gold he checks silver, and silver taking the low "allows us to say that the
target has been hit or has an SMT". Equal highs/lows are called out as particularly good targets.

The layered-target idea is the payoff and the stated route to high R: catch a lower-timeframe
fractal inside a higher-timeframe one ("trading C3 inside a C3"), take profit at the short-term
target, hold a runner to the higher-timeframe target. The worked runner reaches roughly 1:11 to
1:16. A feasibility check appears in passing — not reaching the final target in one day is fine,
"that's too much daily range".

### Rules stated

- Targets = previous candles' highs/lows on the reference higher timeframe, starting with candle 1.
- Skip extremes already taken out.
- Equal highs/lows are preferred targets.
- Escalate one timeframe for the runner target.
- A target counts as hit when the correlated asset takes it.
- Partial at the short-term target, runner to the higher-timeframe one.
- Do not expect all targets in one day.

### Open questions

- No lookback bound on how far left to keep marking extremes.
- No rule reconciles these targets with the standard-deviation projections, which are also called
  targets and generally sit elsewhere.
- "Too much daily range" is eyeballed; no ADR figure is used.

---

## Intracandle CISD (IC-CISD) - Improve Your Entries (`Vo2n47RjjMo`, 844s)

### What is actually taught

**The single most useful video for adjudicating "CISD" in this library.** It opens with the
cleanest definition of the base concept anywhere in the corpus: a change in the state of delivery
is "a shift in trend. We use that by **finding the level that hit a point of interest** so
interacting with a fair value gap, a high or a low and then **price closing over the series of
candles into that point of interest**." The point of interest is *part of the definition*, not an
extra filter — which is the discriminator between the readings the library currently holds.

Then the invention, stated as his own: "This is a concept that I created when I was forming my
model to **mechanically define the formation of a wick**." Previously the CISD was used at a
reversal to confirm a swing point; here the same test is applied *inside* a continuation candle.
Candle 3 opens with a short-term bearish trend while it makes its lower wick; when that
intracandle trend flips — the same POI-plus-closure test, producing a protected swing inside the
candle — the wick is declared formed and the body is traded. It applies to candle 4 identically.

The timing rule is the practically important addition. "It is ideal to have this form in the
beginning of the candle, so this candle can really expand lower." If instead it forms late, "it's
ideal to wait for the next candle to trade this… Because we get a new candle with new range."
There is also a location filter: a point of interest well above the T-spot is not wanted, "that's
too high up… then it's less likely to expand."

The closing line is the thesis in one sentence: "if you don't have the patience to let the wick
form, then generally you become the wick."

### Rules stated

- CISD = level that hit a point of interest + close over the series of candles into that POI.
- IC-CISD = the same test applied inside a continuation candle, marking its wick as formed.
- Ideally the POI is inside the T-spot; a POI too far into the candle is rejected.
- Once formed, trade the body away; entry on the close or the retest, stop on the bodies or the
  extreme, target ~2R.
- Ideal early in the candle; if late but valid, trade the next candle for its new range.
- Later new continuations inside the same candle are additional valid entries.
- Applies to candle 4 as well as candle 3.

### Open questions

- The unresolved part of the CISD definition survives: *which* level of the opposing-candle series
  the close must clear (their opens? the first open? the extremes?) is never stated.
- "Early" vs "late" in the candle is never a fraction or a clock time.
- "Too long consolidating" is deferred to a separate video (`PQiRV0JMhIQ`, unit 02).

---

## Intro To TTrades Fractal Model [Indicator & Settings] (`CqMIh-Vvhbg`, 1175s)

### What is actually taught

The indicator tour, and — as expected — the most mechanical video in the unit, with one large
caveat below. The model premise is stated up front: "the market cannot reverse without a swing
point."

Settings captured in full:

- **History** — how many past setups to show: 0 (current only) up to 40.
- **C2 / C3 / C4 toggles** — each closure type shown or hidden; he keeps all on.
- **C2 colour semantics** — **grey** = the setup stayed valid throughout candle 4; **red** = it
  failed within the first candle after; **orange** = it failed on the *second* candle after.
- **Bias selector** — bullish / bearish / neutral, filtering which setups draw.
- **Time filter (kill zones)** — up to three windows. Critical mechanic: "it's going to choose the
  whole hours candle", so an 08:00–11:30 window requires entering **07:00** to include the whole
  08:00 candle. A "choose below period" setting restricts the filter to timeframes at or below a
  chosen one, otherwise the setup will not print higher up.
- **HTF power-of-three candles** — hide/show, size small/medium/large, and an offset (default
  ~5; he uses 10, 15 and 32 in different layouts).
- **HTF open**, **open/close vertical separators** (he considers these important), **per-hour
  high/low lines** (off by default for him).
- **Model labels**, **candle-1 sweep marker**, separate bull/bear CISD colours, **candle
  equilibrium**, **T-spot** boxes (grey and green by default).
- **Projections** — "these are currently drawn from the bodies", i.e. from the bodies of the CISD
  series; extra values can be typed in comma-separated (he demonstrates adding 0.5).
- **Formation liquidity** — a dotted line marking the previous candle's / previous day's extreme
  in the bias direction that has **not** yet been taken.
- **Table** — timeframe, asset, active fractal model pairing, time until the HTF candle closes,
  selected bias, active time filters.
- **Automatic mode** pairs the chart timeframe with its higher timeframe; two copies of the
  indicator can be run to overlap an hourly T-spot with a 5-minute one.

**The caveat, and it is the finding:** the actual C2/C3/C4 requirements the indicator encodes are
withheld — "I go over all the requirements for these within my course and mentorship". The
indicator therefore cannot be reproduced from the free material. Also, the T-spot is described
purely by function ("this is the area in the higher time frame candles that I look for the higher
time frame Wick 2 form" — the auto-caption renders "to" as "2") and never derived.

### Open questions

- Default projection values are shown on screen but never spoken; the standard-deviation video's
  `1, 0, -1, -2, -2.5, -4` is the best available proxy.
- No timezone is stated for the kill-zone filter here.
- The failure test behind red/orange is not disclosed.

---

## Master Candlestick Wicks - The Key To Catching Reversals (`LKNQDAdId4s`, 717s)

### What is actually taught

The library's `small wick` blocking term does **not** get resolved here. This video is about wick
*respect*, not wick *size*.

A wick is read as a lower-timeframe reversal: during that period price made an aggressive move
and came back. The level marked is precise and worth quoting exactly: "the main focus for Wix is
marking out 0.5 of this Wick from the body to the low or the body to the high" — the midpoint of
the **wick itself**, not of the candle. The test: bullish, the upper half of the wick must support
price higher; bearish, the lower half must support price lower. On the higher timeframe a
respected wick shows up as open-low-high-close (bullish) or open-high-low-close (bearish).

Disrespect: "if the upper half of this Wick is not respected then it is likely to trade to this
low." Once price closes over 50%, "now I would say it's more likely to take out this High than it
is to expand lower."

**The one line in the whole unit that gestures at a size threshold** is here, and it is indirect:
of a candle falling through 50% of the reference wick immediately after the open — "it is not
likely to form an expansion candle within this given time period as **this would form too large
of a wick for an expansion candle**". So the only mechanisation offered is: *a candle that trades
through 0.5 of the prior wick will itself have too large a wick to be an expansion candle.* That
is a derived, conditional test — not a ratio.

The video is candid about the edge cases: sometimes price closes over the level and still expands,
sometimes it respects the level all period and runs it out at the very end. His response is to
seek more or less confirmation depending on the lower-timeframe picture — in one case waiting for
a close below the level before entering, then taking 2R.

### Rules stated

- Mark 0.5 of the wick measured from the BODY to the extreme.
- Bullish: upper half must support. Bearish: lower half must support.
- Respected wick → open-low-high-close (bullish) / open-high-low-close (bearish).
- A close through 0.5 → the opposite extreme becomes the more likely draw.
- A candle trading through 0.5 of the reference wick would itself form too large a wick to be an
  expansion candle.
- Context matters: a wick inside a consolidation is lower probability.
- Where confirmation is weak, wait for a close beyond the level before entering.

### Open questions

- **No size threshold. No ratio. No percentage.** The dedicated "Wick Size Matters"
  video (`SlWxhzhLo3A`) is in unit `..._03` — that is where to look next.
- Whether disrespect is a body close or a wick through is stated as a close but shown both ways.
- No rule for which half to use on a candle with wicks at both ends.

---

## Positional Entries - Enter Before The Expansion (`xMFd_kfmIqI`, 741s)

### What is actually taught

An entry taken at the **open of a continuation candle**, before its wick has formed, when a
protected swing already exists from before that open. The motivation is explicit and honest:
some candle 3s expand immediately and never give an intracandle CISD, so always waiting costs
those trades. "A positional entry is when we have a protected swing going into the open of a new
higher time frame candle."

The distinctive content is the **selection test for the stop**. The protected swing used must sit
*beyond* the equilibrium of candle 2 — "the stop on candle two is above the EQ of candle two. I
want to see that above the EQ." The AUDUSD example is built entirely on this: two protected swings
exist, and the nearer one is rejected because "it is not in respect to the equilibrium… I'd
honestly expect it to get taken out", while the further one is chosen because price can respect
the EQ without stopping him out. Mechanically both are protected swings; only one makes sense
given where the wick is expected to form.

Where risk-to-reward fails he moves the *entry* (down into the fair value gap, or waits for a
retest) rather than tightening the stop into the wick zone. If the positional entry is missed, the
IC-CISD and later continuations remain valid.

He closes by flagging it as advanced: "If you did find it confusing and you are newer to my model,
I would not worry about it… It is an advanced concept."

### Rules stated

- Requires a valid model (closure + CISD) and a protected swing formed *before* the open.
- Enter at the open; stop on that protected swing.
- The protected swing must sit beyond the EQ of candle 2 / outside the T-spot area.
- If R does not work, move the entry, not the stop.
- Missed positional entry → IC-CISD or a later new continuation.
- Also valid going into candle 4.

### Open questions

- The "beyond the EQ" test is softened in the final example, which accepts a swing that "doesn't
  technically cover the EQ" because the area is large enough — a preference, not a hard rule.
- No guidance on how recently before the open the protected swing must have formed.

---

## Protected Swings – Understanding Trend and Invalidations (`-wr4xATE37g`, 1015s)

### What is actually taught

The invalidation concept the entire model is built on: "A protected swing is a high or low in
which I'm expecting to hold as the trend continues." Three constructions are given, all with the
same shape (point of interest → closure through the series of opposing candles that made the
extreme):

1. **Sweep** — a short-term low/high is run out, then price closes through the series of
   down-close candles that made it.
2. **SMT substitute** — no sweep here, but the correlated asset ran it; use the opposing candles
   that made the **failure swing** instead.
3. **Fair value gap** — no sweep at all; price reaches into a fair value gap and the opposing
   candles that made the extreme inside it are closed through.

Two operationally important points come out of the examples. First, the negative case is taught
before the positive: a turtle soup at a previous day high fails specifically because "we never get
that confirmation of the close through the series of downclosed candles that made that high" —
that is *why* he waits. Second, the series is often a single candle ("In this case, it is just
one"), and the choice of which candles form the series is discretionary — in one messy case he
says "price went up, down, back up. So I can really just use this level in here".

The entry philosophy follows directly: he does not put the stop on a distant protected swing —
"that doesn't really give good risk-to-reward" — he waits for a **new** protected swing so the
entry sits close to the invalidation. "When I am looking for entries, I am mainly focused on a new
invalidation forming."

He also distinguishes **anticipating** a protected swing (marking on the daily where you expect
one, then dropping to the hourly to find it) from a protected swing **forming**.

### Rules stated

- Protected swing = POI engaged, then a close through the series of opposing candles that made
  the extreme.
- Three constructions: sweep, SMT substitute, fair value gap.
- Trend continues while successive protected swings hold.
- Each new one supersedes the last as the invalidation.
- Wait for a *new* protected swing so the entry sits close to the stop.
- Anticipate on the higher timeframe, confirm on the lower.
- A deep retracement that does not violate the protected swing leaves the trend intact.

### Open questions

- "The series of opposing candles that made the extreme" is judged by eye; he sometimes picks a
  different candle, justified as "that is the swing high that created this swing low".
- Whether the close must clear the first opposing candle's open or its extreme is never stated —
  this is the same unresolved question as in the CISD definition.

---

## Quit Moving Your Stop Loss Before You Know This (`CKltGYiesHA`, 977s)

### What is actually taught

The complete trailing rule, and it is a single sentence: "Our stop losses can only be trailed to
new protected swings." A down-close candle price merely moved away from is explicitly **not** a
valid trail target — the swing must have engaged a point of interest and then been closed through.
Break-even is the same rule applied earlier: when a new protected swing happens to sit at the
entry price, the stop may go there.

Two constraints bound it, and both are new material relative to the library. **Geometric**: do not
trail too far inside the current higher-timeframe candle, because candle 4 is expected to respect
50% of candle 3's range — "ideally, I don't want to trail my stop if I'm expecting it to go higher
too high up in this candle or I will get swept out in the next higher time frame candle."
**Range-budget**: whether to trail at all is a function of remaining range. Entry early with a
distant draw on liquidity → trail. Entry halfway through the daily range with 2R sitting at the
ADR → do not trail, take profit at the objective, because you will otherwise be reversed out for
1R or less. Get aggressive with trailing only once already at high R.

The final example is the cleanest statement of the negative case: "it doesn't make sense to trail
my stop loss because I have no protected swings before my target. We've already had quite a daily
range."

A useful diagnostic also appears: a newly formed protected swing that is *instantly invalidated*
is a signal that the sequence is consolidating or reversing — not necessarily that the trade
fails, but a warning of chop. The indicator marks that by turning the print grey.

### Rules stated

- Trail only to new protected swings; never to an opposing candle that reached no POI.
- Break-even permitted when a new protected swing sits at the entry.
- Do not trail past 50% of the current HTF candle's range.
- Trail when range remains; take profit when the target is ~2R at the ADR.
- Trail aggressively only at high R.
- No protected swing between price and target → do not trail.
- Instantly invalidated protected swing = consolidation/reversal warning.
- New continuations are also fresh entries at the same R.

### Open questions

- "How much range is left" is judged by eye against the ADR; no calculation.
- "High RR" is unquantified (examples show 4–5R already banked).
- What to do about break-even when no protected swing appears there is not addressed.

---

## Standard Deviation Projections - ICT Concepts (`kTWXpAo1uE8`, 872s)

### What is actually taught

Targets and reaction areas from projecting the **manipulation leg** with a Fibonacci retracement
tool. The manipulation leg is defined: "that manipulation leg is the swing that swept liquidity
before changing the state of delivery" — i.e. the leg that made the new high before the new low
(bearish) or the new low before the new high (bullish). The tool is then anchored across that leg
(high→low for a bearish projection) and projected forward.

**Fib settings, stated verbatim: `1 0 -1 -2 -2.5 and -4`.** Display detail is also given: values
on the left, middle position, font size 10, very transparent background.

The reading:

- **-2 to -2.5** — the area to expect a retracement or a reversal.
- A displacement **close through** that band → **-4** (max expansion) becomes the objective.
- After -4 is reached — mark discount/premium of that leg and expect a retrace to its equilibrium.

Confluence rules follow. Prefer levels where a projection coincides with a PD array — a fair value
gap, an order block's mean threshold, equal highs/lows. Resting liquidity sitting just short of
the -2/-2.5 band is called "the low hanging fruit". And **stacked projections**: where one
projection's -4 lines up with another's -2/-2.5, treat that as added confluence. The consequent
encroachment (midpoint) of the band can also be marked.

The final section runs the whole thing top-down: a daily fair value gap and a Tuesday reversal
produce a "classic sell week" expectation for Thursday; the manipulation leg is found on the
hourly and projected; the 15-minute shows Asia consolidation and a London manipulation; the
2-minute supplies an order block retest entry targeting the London lows, which sit just above -2.

### Rules stated

- Identify the manipulation leg: the swing that swept liquidity immediately before the CISD.
- Anchor the fib across it, project forward. Settings 1, 0, -1, -2, -2.5, -4.
- -2 to -2.5 → expect retracement or reversal.
- Close through -2/-2.5 → -4 becomes the objective.
- After -4 → mark premium/discount of the leg, expect a retrace to its EQ.
- Prefer projection + PD array confluence; resting liquidity just short of -2/-2.5 is low hanging
  fruit.
- Overlapping projections from different legs add confluence.

### Open questions

- Anchor convention is ambiguous: the video anchors "from our high to our low" (wicks) while the
  indicator draws projections "from the bodies".
- -2 to -2.5 is a band with no rule for which edge to use for an order.
- Nothing reconciles these projections with the previous-candle-extreme targets from `A4NasIa371c`
  — both are called targets and generally do not coincide.

---

## Cross-video observations

### 1. The four "Phases Of Price" videos deliver one crisp definition and three soft ones

- **Consolidation is decidable**: price remains internal to a marked high and low. This is the
  best result in the unit and directly attacks the library's #2 blocking term. It still lacks a
  minimum duration and the range boundaries are marked by eye, but a detector can be written.
- **Expansion, retracement and reversal are not** — they are all relational ("one-sided",
  "shallow", "slow", "met with expansion") and none carries a number. Reversal is the tidiest
  formulation ("expansion met with expansion") but is fully parasitic on the expansion definition.
- The one quantitative gesture in the whole series is a **bar-count ratio for retracement**
  (9 hours retracing 3 hours; 8 candles retracing 3), demonstrated twice and never stated as a rule.

### 2. `small wick` survives the primary teaching unquantified

Five videos gate on wick size (`Kf4c41_qO1s`, `-KKuZb5Z5aU`, `FKTBkTzsmUA`, `-ocfPuD_oqE`,
`v1X8UMWgWmI`) and the dedicated wick video gives only a *respect* test, not a *size* test. The
closest thing to a threshold is derived and conditional: a candle that trades through 0.5 of the
reference wick "would form too large of a wick for an expansion candle". The remaining candidate
is `SlWxhzhLo3A` ("Wick Size Matters") in unit `..._03`.

The library's surviving falsifiable prediction — the C2 small-wick claim — is **corroborated in
direction** by this unit (small wick → the reversal candle is tradeable; large wick → wait for
candle 3, stated identically in three videos) but gains no threshold to test it against.

### 3. CISD is defined more tightly here than anywhere else, and the residual ambiguity is now precise

`Vo2n47RjjMo` gives the canonical form: **find the level that hit a point of interest, then require
price to close over the series of candles into that point of interest.** Two consequences for the
library's three-way CISD disagreement:

- The point of interest is *part of the definition*. Any implementation that omits the POI gate is
  not this concept.
- The residual ambiguity is now narrow and stateable: **which price level of the opposing-candle
  series must be closed through** — the first candle's open, the highest open in the series, or
  their extremes. No video in this unit says. That single question is the whole remaining gap, and
  `-wr4xATE37g` shows it is discretionary in practice ("I can really just use this level in here").

`ic-cisd` is not a rival system: it is the same test relocated inside a continuation candle to
mark a wick as formed. That resolves one of the library's three readings as a *usage*, not a
competing definition.

### 4. Confirmations claimed in the brief

- **New York / EST clock** — NOT confirmed. Neither `CqMIh-Vvhbg` nor `Mo9QMtotQyo` names a
  timezone; sessions are referred to only as Asia / London / New York, and `Mo9QMtotQyo` uses
  9:30 / 10:00 without stating a zone. The New York equity-open times used are consistent with EST
  but the unit does not assert it.
- **The 4H grid (18/22/02/06/10/14) and the 10:00 four-timeframe open** — partially confirmed.
  `Mo9QMtotQyo` waits for "6" to close a 4-hour candle and describes "6:00 to 10:00 a.m." as one
  4-hour candle, which fits the grid. `Kf4c41_qO1s` waits for "that 10 a.m." to open a new 4-hour
  *and* hourly candle together, and `VD4xb9VfMHA` marks 10 a.m. The 30m/15m part of the claim is
  not stated here.
- **EQ = 50% high-to-low on an expansion candle; 50% of the wick on a large-wick candle** — mostly
  confirmed, but the unit uses *three* different 50% levels under the one name "EQ": (a) the EQ of
  the **previous day's range** (the continuation-day filter, `-KKuZb5Z5aU`); (b) the EQ of the
  **current candle** (`CKltGYiesHA`: candle 4 respects 50% of candle 3's range); (c) 0.5 of a
  **wick**, body-to-extreme (`LKNQDAdId4s`). Only (b) and (c) match the brief. Reading (a) is a
  distinct object and is the one used for daily bias.

### 5. Where this unit supersedes the Q&A-derived library

- `fractal-model-c2`: the close must return above candle 1's **low** (or below its **high**) — not
  necessarily into candle 1's body. More permissive than some Q&A readings.
- `aligning-expansion-candles` was held with `voice: guest` from GxTradez; TTrades states it
  himself here, with a *minimum of two* aligned layers and a documented reduced-target branch when
  the daily fails the filter. The guest and owner readings agree.
- `reversal-signature` was likewise guest-sourced and required SMT. TTrades' own version uses SMT
  as confluence only and does **not** require it — but adds a requirement the guest version lacks:
  the level must be *relevant* (previous day / previous week extremes).
- `t-spot` remains underspecified even in the indicator video — described only by function, never
  derived. One example equates it with the equilibrium, which conflicts with it being drawn as a
  box.
- The exact C2/C3/C4 conditions encoded in the indicator are **deliberately withheld** and sold via
  the course/mentorship. Any faithful reimplementation of the indicator is therefore blocked at
  source, not by transcript quality.

### 6. The stack, as a single procedure

Daily C2/C3 closure at a point of interest → hourly CISD confirming it → 4-hour C2/C3 closure
inside that daily candle → 15-minute continuation (POI + close through the opposing candles =
protected swing) → entry at the IC-CISD or positionally at the open → stop on the protected swing
(which must sit beyond candle 2's EQ) → 2R at the nearest unswept previous-candle extreme, runner
to the higher-timeframe version of the same target → trail only to new protected swings, and only
while range remains.

Every gate in that chain is decidable except the ones that depend on "expansion" and "small wick".
