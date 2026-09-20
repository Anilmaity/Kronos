# Live Streams — study notes (unit_id: `live_streams_04`)

Channel: TTrades_edu. Playlist: "Live Streams" — the channel's **own** New York Open Live Q&A
streams (not the guest-interview streams). Four transcripts, all present and readable (auto-en),
totalling roughly 6.5 hours of runtime:

| video | id | duration |
|---|---|---|
| New York Open Live Q&A | `eIPM-D8RrSQ` | 6353s |
| New York Open Live Q&A | `i2HhHhWdaPQ` | 6523s |
| New York Open Live Q&A | `N3Ml-r0X30o` | 6042s |
| New York Open Live Q&A | `x4sRGuZIqWk` | 4718s |

All four carry the same title and none is numbered, so there is no stated order. Internal
evidence puts **`x4sRGuZIqWk` first**: he says the next video will be "finishing up the weekly
profile series" with "two more, I think, left", and a viewer asks about an Iran–US ceasefire
extension. The other three postdate the series' completion; `N3Ml-r0X30o` shows a student's
"4 months of 2026" results, and `eIPM-D8RrSQ` and `i2HhHhWdaPQ` both promote the same
NinjaTrader Arena Cup and both mention a Tampa move, so they are close together and late.
He states his schedule in two of them: **Tuesday and Wednesday, 9:15 a.m. to whenever he
finishes.**

## Transcript hygiene

Auto-caption artefacts that had to be decoded before anything could be extracted:

- **"candle to" = candle 2** — the known corpus-wide artefact, present here too ("candle to
  closure", "trade this candle too").
- **CISD is spelled four different ways in one unit**: `CISD`, `CIST`, `CSD`, `CSC`, and once
  `ICSD` (spoken by a viewer, and the one he answers is IC-CISD). All are read as change in the
  state of delivery; the IC-CISD answer is kept separate because he explicitly calls it his own
  distinct concept.
- **"dogee candles"** = doji candles; **"hammer shooter candles"** = hammer / shooting star.
- **"the PC"** = the POC (volume profile point of control) — decoded from context, since the
  whole answer is about not trading where all the volume sits.
- **"POIs to use your value gaps, highs, lows"** — "fair" is dropped by the captioner. Read as
  *fair value gaps, highs, lows*, which he restates cleanly later in the same stream as "all I
  know are highs, lows, and fair value".
- **"how to use 1800 6 10 1400 0 8"** — his own time-levels lesson title, read off screen. The
  trailing "0 8" is **not decoded** and is recorded as-is in the concept file rather than
  guessed at.
- **"a candle to closure at a relevant key level"**, **"RB"**, **"bolo PD array"** — the last
  two are viewer coinages he does not recognise either ("I don't know what a bolo PD array is").
- **None of the four transcripts carries timestamps**, so **no `approx_time` is recorded
  anywhere in this unit.**

## What a Live Q&A actually is, and how much of it is usable

These are not lessons. A large majority of each stream's runtime is: giveaway administration
(one stream loses roughly 25 minutes to re-rolling a Lucid account because winners will not put
an email in their YouTube description, and he accidentally costs himself $20 in refund fees on
another), supplement and sleep chat (magnesium taurate, sea salt, blue-light glasses), business
write-offs explained with a worked tax example, moderation of spam and rage-bait, and a running
apology that there is nothing to trade. Three of the four streams end with him having taken no
trade at all, and one of them is explicitly a day where he was *correctly* directional from the
open and still did not trade.

That is not padding to be skipped — it is where the genuinely new material is. The teaching in
these streams is almost entirely **corrective**: a viewer proposes something, and he explains
why it is not a setup. The unit's yield is therefore heavy on gates, refusals and parameters and
almost empty of new setups. Nothing below is a new model; everything below either narrows an
existing one or supplies a number the polished lessons never state.

Two honest caveats. First, he repeatedly declines to be pinned down — "I'm never going to tell
you how to trade", "this is for entertainment and educational purposes only", "I'm not a signal
bot" — and several answers end in an explicit refusal to mechanise (order flow, absorption,
news). Those refusals are recorded as such. Second, he is wrong on air and says so: "I'm not
right about everything", "It is not 100%. Things do fail", and one stream's entire plan simply
does not materialise.

---

## `eIPM-D8RrSQ` (https://youtu.be/eIPM-D8RrSQ, 6353s)

### What is actually taught

The market is already extended when the stream opens — gapped up, most of the daily range spent
— and the whole stream is built around what you do with a day like that. His answer arrives in
three parts and each is a rule.

First, **the average daily range is computed by eye, and by hand.** Asked directly whether he
has a video on determining an asset's daily range, he pulls up gold and reads the recent daily
candles aloud: 110, 150, 160, 150, 160, 140 — so at 170 the range "might be capped". He then
rejects the ADR indicator on a stated basis: an ADR averages in all the previous ranges, whereas
he only wants the expansion ones. This is the clearest version of the procedure in the corpus.

Second, **when the range is spent, you do not fade the daily candle** — you wait for the next
one. Said twice about crude ("this is technically fading the daily candle… I would rather wait
for today to close and then look for a small wick on the daily candle tomorrow") and once about
euro. This is the unit's most repeated single idea; it recurs in two of the other three streams.

Third, **the weekly profiles are fractal downward.** He points at an intraday chart where price
expanded away without establishing a low and says to go watch the *Thursday Counter* weekly
profile video, because "it's kind of the same thing… but it's just New York session forming a
reversal favouring back into the range". That is the only place in the corpus where the weekly
profile vocabulary is explicitly transposed onto a session.

The stream also contains two definitional answers that unblock existing library entries. He is
asked what IC-CISD is and gives the only definition of it anywhere: a concept he created inside
his fractal model **which determines the wick of a continuation candle**, adding that he has made
a video on it but does not use that name in it. And he is asked why he has no POI, which produces
the all-time-highs answer: at all-time highs there is nothing to the left, so there is no POI,
and the eyeballed daily range becomes the objective instead — "stop overthinking it just because
there's nothing to the left. You're still just trading these candles here."

Two protective refusals. Order flow: he says it is too subjective, and the test he applies is
worth more than the verdict — "what is absorption? Is there a mechanical definition for
absorption? Like when the delta flips, how do you actually define where your entry is?" Volume
profile: he would never trade the POC, because price sitting there means consolidation; if he
used it at all it would be on a higher timeframe, for low-volume nodes.

The psychology segment is the sharpest in the unit. A viewer says he has not passed a funded
account in over a year; he guesses the cause (tilt, revenge trading, oversizing, not following
strategy), is told it is revenge trading, and refuses sympathy: "you know your problem. You're
just too lazy to fix it." The prescription is one line and it is mechanical — **one trade a day
max, no matter what** — with the argument that you cannot revenge trade if you are only allowed
one trade.

### Concepts introduced or sharpened

- Eyeballed ADR from **expansion candles only**; explicit rejection of the ADR indicator.
- **No fading the daily candle**; wait for the next daily candle instead.
- Weekly profile (Thursday Counter) applied **intraday**.
- **IC-CISD** defined as determining the wick of a continuation candle.
- **No POI at all-time highs**; the daily range substitutes for one.
- POC rejected, low-volume nodes allowed on a higher timeframe.
- Order flow / absorption rejected for lack of a mechanical definition.
- **One trade a day max** as the revenge-trading fix.
- Protected swing **disqualified for taking too long to form** ("it's more of a consolidation
  range than an actual protected swing to me").
- Relative strength read off the **4-hour candle closures** of the correlated assets, plus
  divergence; he refuses to call that a PSP because PSP implies a reversal.
- Model construction: find concepts that make sense, blend them into a mechanical entry, remove
  everything else — he names breakers, advanced market structure and premium/discount as things
  he removed from his own earlier model.
- Options: buy expiry at **3x** the expected time-to-target.
- Continuations wanted **with the 9:30 or 10:00 expansion, not after it**.
- 6 a.m. 4-hour candle confirmed as a good time to position before the New York open.

### Quotes

- "I'm just focusing on the expansion ones"
- "you're not going to have a POI at all time highs"
- "One trade a day max, no matter what."
- "Is there a mechanical definition for absorption?"

### Open questions

- The ADR band is quoted as a range of values with no lookback and no rule for what counts as an
  expansion day — it is genuinely eyeballed.
- "Took how long to form" disqualifies a protected swing, but no candle count is given.
- IC-CISD has a job but no mechanics; the video he says exists is not named.

---

## `i2HhHhWdaPQ` (https://youtu.be/i2HhHhWdaPQ, 6523s)

### What is actually taught

The densest of the four for mechanics, and the only one where three separate viewer questions
each produce a rule the lesson videos do not state.

**"Which session CISD is more important, London or New York?"** The answer is that the question
is malformed: *there is only one change in the state of delivery per day*, the one that forms the
daily wick. If London produced it, what looks like a New York CISD is a continuation off the
first — those are opposing candles, not a second CISD. If London did not produce one, New York
forms it. He then defines the term itself: a CISD is the order block that confirms a shift in
trend. This is the single most automation-relevant thing in the unit, because a naive detector
will mark several CISDs a day and he is saying only one counts.

**"How long does a protected high or low stay protected?"** He draws a stack of protected swings
and answers: they all stay protected until the opposing extreme — the high the sequence is
trading toward — is taken out. Once it is, he expects price to run back through a former
protected swing and form a continuation there, often around the EQ, and calls that "actually a
framework that happens a lot". The library's protected-swing entry had no duration rule at all
before this.

**"How do I know if a level is a POI or a valid PDR?"** — "If you want to keep it very simple,
this is all I do. POIs, [fair] value gaps, highs, lows. That's it." Repeated later, unprompted,
when a viewer uses a term he does not recognise: "All I know are highs, lows, and fair value."
That is a closed enumeration and it is directly implementable.

Two further pieces of machinery. He gives the **derivation** of the candle numbering, which
produces a discriminator the descriptive videos never state: price can only reverse if it makes
a swing point, so he went looking for swing points he could define; sweep-and-close-back became
candle 2; then he noticed *"not all of them sweep and then close, some engulf"*, and that became
candle 3. Those are the only two he arrived at. And he answers **"what makes a day clean to
trade?"** with a four-item checklist: daily candle 3, 4-hour candle 4, a protected swing, and the
timeframes not already expanded — restated from the entry side as "in line with the daily candle,
in line with another time frame, and then you have a reversal, and it's a new protected swing."

The stream's spine is a refusal. He is bullish, price is above the previous day high, and the
only bearish framing he can construct requires 10:00 a.m. — because that is when a new
higher-timeframe candle opens and he can align with it. He draws out exactly what would have to
happen (10 a.m. opens, SMT against YM, trade it back into the range toward the daily open) and
then it does not happen, and he takes nothing. His stated reason for 10:00 is the general one:
"We want to align with a higher time frame candle… when do we get a new candle that we can align
with? At 10:00 a.m."

He also corrects the single most common viewer error about SMT: "everyone tries to do SMT first,
then frame around that. I always have a model first, use SMT to confirm." He refuses on air to
short on a bare ES/NQ divergence because it is not supported by his model.

The remediation segment repeats and extends the previous stream's: the root-cause list is tilt,
oversizing, revenge trading, over-managing and not following the model, and the plan is **one
trade a day, 2R or -1R, no management, follow the rules**. He shows a mentorship student twenty
days into it.

### Concepts introduced or sharpened

- **One CISD per day**, forming the daily wick; London CISD makes New York a continuation.
- CISD = the order block that confirms a trend shift.
- **Protected swings stay protected until the opposing extreme is taken**; then expect a
  run-back-and-continuation near the EQ.
- **POI = fair value gaps, highs, lows. Closed list.**
- **C2 = sweep and close back; C3 = engulf without a sweep.** C2 is always a swing point.
- **Clean day** = daily C3 + 4H C4 + protected swing + not already expanded.
- SMT is a confirmation of a model, never the model.
- Do not fade the daily candle; a counter-daily reversal is harder, needs more confirmation and
  justifies a less aggressive entry.
- **Exotics / crosses are only framed while the dollar is consolidating.**
- Rejection blocks not used, except as wicks on doji / hammer / shooting-star candles.
- Weekly EQ not used; DXY not used for index correlation; kill zones not used.
- **Failure to manipulate** deflated to phases of price: price expands into a level and either
  expands back out (reversal) or retraces/consolidates and continues (the "failure").
- Phases of price as three if-thens: manipulated the range edge → expect expansion; already
  expanded → expect consolidation; retracing → expect expansion.
- Break-even rule: short from a high can go to break-even because price should not return there.
- Timeframe pairing: daily/H4/M15 vs daily/H1/M5, mapped to different daily profiles.
- Middle asset traded only when one asset has already expanded or reversed and the middle one is
  expected to follow — and only with entry still in the upper half (short) / lower half (long).

### Quotes

- "you really only have one change in the state delivery per day"
- "These all are protected until when till this high is taken out"
- "All I know are highs, lows, and fair value."
- "I always have a model first, use SMT to confirm."

### Open questions

- The one-CISD rule does not say which timeframe the count is on, nor what happens if London's
  CISD is later invalidated.
- "Engulf" is not defined — body or full range is not stated.
- The daily/H4/M15 vs daily/H1/M5 mapping is spoken while pointing at a screen ("I think **this**
  is generally better for… London reversal. I think **that** is better for New York reversal"),
  so which pairing goes with which profile is **not recoverable from the transcript** and has
  been left out of the concept files rather than guessed.

---

## `N3Ml-r0X30o` (https://youtu.be/N3Ml-r0X30o, 6042s)

### What is actually taught

The only stream of the four with a clean framework from the open, and consequently the only one
that reads like a lesson. He is bearish before he opens the charts, states why in two sentences,
and the day delivers.

The **bias derivation** is the shortest in the corpus: yesterday closed bearish; is the previous
day high or the previous day low more likely to be reached today; the answer is the low;
therefore bearish. "It's not very complex." He then gives the indicator shortcut he actually
uses — daily plus hourly model, grey box bearish, green box bullish — and, importantly for anyone
without the indicator, says he marked all of it by hand on stream in early 2024.

He then volunteers a **whiteboard lesson he has not made a video of**, and it is the most
directly implementable thing in the unit. Asked how he confirms the high or low of the day, he
writes out two methods and a session-dependent timeframe table:

- **CISD**, scaled to session because price moves faster later: **Asia → H1. London → H1 or M30
  (M15 rarely, but allowed). New York → M15 or M5.**
- **Candle closure**, always on a higher timeframe: **H4 or H1 closure, never below those two**,
  and for the H1 it should be a candle 2 closure at a relevant key level.

He screenshots it himself, says "huh, good video idea", and posts it to his Discord — then uses
it twice more in the same stream, stacking both methods (a 4-hour candle 2 closure *and* a
15-minute CISD) in the closing review.

He states his **favourite setup** unprompted and writes it on screen: **daily C3/C4 + London
reversal + 15-minute continuation entry prior to the NYSE open** — "that's literally my
favourite". The reasoning for why the open then *drives* rather than manipulates is new: with
London having reversed, the day's manipulation already happened inside the daily range, so 9:30
has nothing left to manipulate and should deliver volatility in the continuation direction. The
expansion window he names for it is **6:00 to 10:00 a.m.**

He runs a live quiz on **time-based exits**: given price expanding lower off 9:30, when does the
move end? Answer, 10:00 a.m. — "because it's a 4-hour expansion, hourly expansion, 30-minute
expansion", with 9:45 as the occasional alternative when a 15-minute expansion ends there, though
"it's usually just the higher time frame candles".

And then, despite all of that, **he does not trade.** This is the most instructive stretch of the
unit. The continuation is there, the bias is right, but the high it would risk against is a pair
of near-equal highs with no SMT on ES or YM, so there is no opposing candle he trusts as an
invalidation. He says it plainly: "without an SMT there, I can't trust this high personally
within my system", and generalises it — **"there's a difference between an idea and having the
setup to actually execute on."** He walks through what the setup *would* have looked like with the
SMT present (opposing candles usable, entry anywhere in the block, 2R to the target, or 1.7R to
the nearer low) and takes nothing.

The stream also carries the only performance numbers stated aloud anywhere in this unit. He
reads a mentorship student's result off screen and endorses it: four months of 2026, **gold**
only, on the **4-hour / 15-minute model**, taking a flat 2R — **63R over 48 trades, 63% win rate,
average RR 1.93**. Roughly a dozen trades a month on one instrument.

Two smaller corrections. **"There is no candle four closure"** — candle 3 and candle 4 exist as
positions after a candle 2 closure, but only C2 and C3 are defined closures. And on relative
strength: **if you are uncertain which asset is stronger, trade ES**, because NQ and YM alternate
and bounce around while ES sits in the middle and moves most consistently. He demonstrates the
switch happening three times on air.

Where to sell is stated as a location rule: around the daily open or in the wick of the daily
candle, before the first target — "I don't want to be selling below previous day low." He closes
the stream on the same point after a viewer's short below the lows: "if you're shorting below the
lows, you're setting yourself up for a new phase of price… It doesn't make sense to short it
down here."

### Concepts introduced or sharpened

- **Session → timeframe table for confirming the daily wick** (Asia H1, London H1/M30, NY M15/M5;
  or an H4/H1 closure).
- **Favourite setup**: daily C3/C4 + London reversal + 15m continuation pre-NYSE-open; 6–10 a.m.
  expansion window; why 9:30 drives rather than manipulates.
- **Time-based exit at 10:00** (4H + H1 + 30m all expiring), 9:45 as the 15-minute alternative.
- **An idea is not a setup** — no trustworthy invalidation, no trade.
- Bias in two steps: previous daily closure → which previous-day extreme is more likely.
- **Benchmark numbers**: 48 trades / 63% WR / 1.93 avg RR / +63R over four months on gold.
- **No candle 4 closure.**
- **Default to ES when the strength ranking is unclear.**
- Sell at the daily open or in its wick; never below the previous day low.
- Consolidations are left at the **new** higher-timeframe candle, so trade the beginning of a
  candle rather than the end of one.
- Pre-open, prefer the 15-minute to the 5-minute — the 5-minute chops you out.
- Long-term investing: below the yearly open is a better buy than above it.
- Kill zones rejected again ("I just use higher time frame candles").
- FOMC: he checks the calendar and downgrades the 9:30 drive because the release later is
  expected to make the move; he does not trade post-FOMC.

### Quotes

- "There's a difference between an idea and having the setup to"
- "if you're in Asia, that's going to be like an H1 CSD"
- "London reversal and 15 continuation prior to NYSE open"
- "it either ends at 10:00 or it can sometimes end at 9:45"
- "63 R over 48 trades with a 63% win rate, average RR 1.93"

### Open questions

- The session boundaries the timeframe table keys off are never given in clock time, so the
  lookup is not fully decidable from this corpus.
- The 63R figure is one student's live result on one instrument, shown on screen — not a
  backtest, with no drawdown or sample-selection information.
- "Trustworthy invalidation" is illustrated (SMT present vs equal highs alone) rather than
  defined; SMT is the only substitute he names.

---

## `x4sRGuZIqWk` (https://youtu.be/x4sRGuZIqWk, 4718s)

### What is actually taught

The earliest of the four and the shortest. The market gives him nothing — most of the daily range
is spent before the open, the reversal he wants never forms — and roughly half the runtime is
supplements, giveaways and self-deprecation. What survives is a set of filters.

The stream opens on the **time levels**, because the first question is about 9:30, midnight and
1800. He answers by pulling up his own free lesson and reading its subtitle aloud: *"how to use
1800 6 10 1400 0 8"*. That enumeration is the closest the corpus comes to naming the
higher-timeframe boundaries he actually uses, and it directly fills the open question left in the
existing `entry-time-window` entry, which noted that the 4-hour boundaries other than 10:00 were
never enumerated. Later, asked whether he only trades after 10:00 a.m., he says no: **"I actually
prefer to trade the 6:00 to 10:00 a.m. 4-hour candle or in that range"** — 10:00 is the fallback
when the 6–10 candle gives him nothing, which is what happens on this day.

**ADR, again, in the most explicit form.** He scrolls gold's current month: the largest candle is
250 points, the typical expansion days are 100–130, so 150 is already beyond normal expectation
and that is when he stands aside. He repeats it for indices — "normally it's like 500 points
right now, 400, 500" — and for ES — "we've already expanded 75 points. Look at the previous day.
38. 64." He also concedes the chat's point that ADR was already hit on most instruments that day.

The **watchlist scan** is stated as a two-line checklist he draws on screen: go to the daily chart
of each asset and ask *can I anticipate this daily candle?* If yes, drop to the lower timeframe
and find the fractal aligned with it. If no, skip the asset — "don't go lower". For forex there is
a gate in front of it: he only looks at the dollar; if the dollar is clean he can look at the
pairs, otherwise nothing.

The **target-selection rule** is the one genuinely new mechanic in this stream, and he flags it
himself as the day's lesson. Liquidity is not equally reachable: a high or low that itself swept
out a run of previous highs or lows is harder for price to get to, because the sweep already
consumed what was there. So on a low-expectation day, with a protected swing in place, he takes
**the failure swing to the right of the protected swing** as the target rather than the deeper
swept extreme. He picks his YM target on exactly that basis and reviews it twice.

Two refusals worth recording. Oil: a viewer offers a clean hourly short and he agrees the pattern
looks great, then declines — "why would I try to short oil when it has failed to reach a relevant
level?" The pattern supports nothing without a level behind it. And news: **"I don't really use
macroeconomics and major news events in my trading decisions. I genuinely do not care"**, adding
that a lot of news is a smokescreen. That flatly contradicts the FOMC handling in `N3Ml-r0X30o`,
and both readings are preserved in a `contested` concept rather than reconciled.

On candle 2 quality he gives the wick condition explicitly for the first time in this unit: "if
you go look at how I trade candle two, **I need a small wick**. I don't ever trade a reversal day
that's a large wick trading back to the open. It's very specific when I do that."

The relative-strength teaching is the cleanest demonstration in the unit because he does it twice
in replay: compare the previous hourly candle's closure across the assets — one bullish, one
bearish — and that is the whole method, "don't make it super complex". He adds the timeframe
qualifier a viewer's objection forces out of him: if you are trading a 5-minute move you care
about the *lower*-timeframe relative strength, not the daily's. And the standing preference: **"I
don't like to trade the lagging asset… I always like to trade the strongest or the weakest."**

### Concepts introduced or sharpened

- **Time levels enumerated: 1800, 6, 10, 1400** (question also names 9:30 and midnight).
- **Preferred window: the 6:00–10:00 a.m. 4-hour candle**; 10:00 is the fallback.
- ADR read off the current month's expansion candles; concrete values for gold, NQ and ES.
- **Watchlist scan**: can I anticipate this daily candle? yes → go lower, no → skip.
- **Dollar gate**: only look at forex when the dollar is clean.
- **Low-expectation target selection**: prefer the failure swing to the right of the protected
  swing over a deeply-swept extreme.
- **No relevant level, no trade** — even for a good-looking pattern.
- **Candle 2 needs a small wick** to be tradeable; large-wick reversal days back to the open are
  reserved for "very specific" cases.
- Relative strength from the previous hourly closure, measured on the execution timeframe.
- Never trade the lagging asset.
- POI restated: not necessarily a higher-timeframe fair value gap, but "normally a high or a fair
  value gap"; without one, only a continuation can be anticipated, never a reversal.
- CRT explicitly not traded. Macro news explicitly not used. A single market algorithm explicitly
  not believed in.
- A candle 3 that opens with no wick is explained by a lower-timeframe protected swing having
  formed before the higher-timeframe candle opened.
- Trade frequency: "a couple trades a week max", not every day.

### Quotes

- "how to use 1800 6 10 1400 0 8"
- "prefer to trade the 6:00 to 10:00 a.m. 4-hour candle"
- "look at the failure swing to the right of it as a target"
- "how I trade candle two, I need a small wick"
- "I don't really use macroeconomics and major news events in my trading decisions"

### Open questions

- The "0 8" in the time-levels list is undecoded and has been left undecoded.
- "Lower expectations" and "harder to get to" are both unquantified.
- The news refusal here and the FOMC handling in `N3Ml-r0X30o` are irreconcilable as stated.

---

## Cross-video observations

- **The unit's centre of gravity is gates, not setups.** Of the concepts extracted, the majority
  are reasons *not* to take a trade: no relevant level, no trustworthy invalidation, range
  already covered, wrong side of the daily candle, wrong part of the higher-timeframe candle, no
  POI, dollar not clean, ranking unclear. He trades in one of the four streams.

- **One rule runs through all four: do not fade the daily candle.** Stated in three of them and
  applied to decline viewer ideas in all four. It is the only thing in this unit that reaches the
  frequency of the weekly-profile series' hourly-CISD gate.

- **Time is used exclusively as higher-timeframe candle boundaries, never as sessions.** Kill
  zones are rejected in two streams; macros are called fake; the New York p.m. session is never
  looked at. What replaces them is 6, 10 and 1400 — i.e. 4-hour opens — plus 9:30 as the NYSE
  cash open and 9:45 as a 15-minute boundary. The 6–10 a.m. candle is where he wants to be
  positioned; 10:00 is where the 9:30 drive is expected to end and where a new phase can start.

- **He coined the vocabulary and is happy to say so** — C2, C3, IC-CISD are all his ("If you look
  at C2, C3, all those, I created those"), which is why the corpus is the naming authority and
  generic ICT usage should not be imported over it.

- **Numbers actually stated aloud in this unit** (rare enough to list): 3x expiry for options;
  one trade a day; 2R target and -1R stop with no management; 1R needs >50% win rate; 48 trades /
  63% WR / 1.93 RR / +63R over four months on gold H4-M15; gold expansion days 100–170 points and
  a 250-point monthly extreme; NQ 400–500 points; ES 38–75 points; 2R and 1.7R on the setup he
  declined.

- **The timezone is still not stated.** Not once in 6.5 hours, across streams that name 1800, 6,
  8:30, 9:30, 9:45, 10:00, 10:30 and 1400. The strongest inference available is that the levels
  are self-consistent with 4-hour candles anchored to an 18:00 futures session open, which for
  CME index futures is US Eastern — but he never says it, so it is recorded as an inference in
  `ambiguities` and not asserted anywhere in a `definition` or a `detection_rule`.

- **Terms used but never defined in this unit** (assumed from other playlists): order block,
  fair value gap, failure swing, EQ, SMT, T-spot, opposing candle, inversion, breaker. Only the
  CISD-confirmation timeframes, the C2/C3 derivation and the POI enumeration are given from
  first principles here.
