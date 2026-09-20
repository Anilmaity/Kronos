# Unit notes — `live_stream_guests_02` (playlist: "Live Stream Guests", batch 2)

Four live-streamed guest interviews, ~4 hours 12 minutes of runtime. TTrades hosts, reads
questions from the YouTube chat, and forwards them; the guest screen-shares and does most of
the talking. Unlike the T Talks batch, TTrades is a much more active participant here — he
answers audience questions about his OWN method inside three of the four streams, and in the
STRAT episode he takes the screen back at the end to demonstrate his own version of the
guest's tool. Those passages are the most valuable material in the unit and are tagged
`voice: ttrades` in the concept files; everything else is the guest's.

**These are four different traders with four incompatible methods.** Alex's Options runs
Rob Smith's TheSTRAT and does not use ICT at all any more; HolyAngelBruv runs ICT on top of
footprint/DOM order flow and auction market theory; AM Trades runs a news-anchored weekly
profile with standard-deviation projections; Day Trading Rauf runs a dollar-first,
New-York-only MMXM/breaker method. Where they contradict each other that is **not** recorded
as `status: contested` — contested is reserved for the channel disagreeing with itself. Guest
disagreements are given distinct concept ids and are catalogued in the cross-video section at
the bottom.

Two of the four guests (AM Trades, Day Trading Rauf) already appear in `t_talks_01`. Each
section below says explicitly what is new here versus what was already captured.

No transcript in this unit carries timestamps, so **no `approx_time` is recorded anywhere in
this unit's concept files.**

---

## Transcript hygiene

All four are `yt-dlp-auto` captions with no speaker labels and no punctuation. The known
corpus artifacts are present — **"candle 2" as "candle to"** (in the STRAT video the guest's
"a candle that went 2 and failed" is captioned "a candle that went to and failed", which is
the *definition* of an outside bar, so the sentence is unusable without knowing the artifact)
and **"reach" as "wretch"** (AM Trades: "I already wretched into the fair value Gap"). Beyond
those, each video has its own failure mode, and one of them changes the meaning of a claim:

- **`qFtfD09Vv3E` — a dropped negation.** "if you don't analyze the dollar first it makes it
  much easier to trade your USD and uh gold" is captioned inverted; the two minutes either
  side make it unambiguous that he means analyse the dollar first *and* it becomes easier.
  Any downstream reader taking that sentence at face value gets the rule backwards. Recorded
  in `dollar-gate-for-fx`.
- **`qFtfD09Vv3E` — names and instruments.** The guest's name "Rauf" is captioned "Ralph"
  throughout. "Judas swing" appears as "Judah swing", "judo swing", "due to swing" and "you to
  swing" — four spellings in one 41-minute stream, all for the single most automation-relevant
  claim in the video. "EURUSD" is "your USD"; "EURAUD" is "your AED"; "euro" is "Yuri";
  "NASDAQ" is "as that" and "us"; the GBP futures symbol 6B1! is "6v1"; "MMXM trader" is
  "mmx7 trader"; "cap the weekly range" alternates with "cut" and "cup"; "wicks" is "weeks";
  "trade" is "paid" ("I would never paid at the beginning of a Kill Zone"). The attribution
  for his 04:00 day-start is captioned "TCM" and cannot be resolved.
- **`wGYde-h84cs` — the vocabulary of the method itself is mangled.** "higher time frame" is
  almost always "hard time frame"; "PD array" is "Peter", "pdra", or (worst) "hard time for
  impede array"; "change in state of delivery" appears as "change in stated delivery", "change
  in sale delivery", "change in Theta delivery", and as the initialisms "CoD", "DOD" and
  "card". "Judas swing for deviation" is "Judas wins for Aviation". "open high low close" is
  "open eye low clothes" and "ATR trail stop" is "8 carat Trail stop" — both inside the host's
  own indicator inventory. "NFP" is "NSP"; "MMXM" is "nnxm"; "AM" (the guest) collides
  constantly with "AM" (the session) and once becomes "Pam". **"Strat" in this video means
  *strategy*, not TheSTRAT** ("what Strat do I use for highest win rate") — a collision with
  the other video in this same unit. Affected: the three-step CISD in
  `hourly-cisd-manipulation-confirmation` and the anchor definition in
  `standard-deviation-projection`, neither of which can be quoted verbatim with confidence.
- **`1XWyy6Q-_8Q` — STRAT jargon is comprehensively destroyed.** "Broadening formation"
  becomes "broad information", "Browning formation", "brown information", "abroad
  information", "routing formation" and "browning permission". "The tri" (the drawn triangle)
  becomes "the try", "the tribe", "the trial" and, in one place, "Chop Shop" survives intact
  only because it is a real term. "2-2 reversal" is rendered as "tutu", "T2", "tto", "t2",
  "teacher reversal", "2-tier reversal" and "o2t reversal" — *seven* spellings. "In force" is
  "enforce". The numeric labels 2-1-2 and 3-2-2 usually survive as "212" and "322". The
  concepts are recoverable only because the guest draws every one of them on screen and
  restates them a dozen times; **no sentence in this transcript should be trusted as wording.**
- **`8Z2AbZLjunU` — speaker identity is the problem, not vocabulary.** The guest's handle
  appears as "bruv", "brev", "brub", "brov", "proof", "grove" and "crow"; "ES" is transcribed
  "yes"; "the low" is "the slow"; "risk reward" is "wrist reward". More seriously, the host
  reads a chat question and then sometimes answers it himself without any handoff cue, so a
  block of first-person method talk can belong to either man. Every attribution in that
  section below is stated with its evidence, and the ones that cannot be pinned are listed in
  that video's ambiguities rather than turned into concept files.

---

## HolyAngelBruv | ICT + Orderflow
(`8Z2AbZLjunU`, https://youtu.be/8Z2AbZLjunU, 3575s ≈ 60 min)

**Guest: HolyAngelBruv** (goes by "Bruv"/"Bruv Town", changes his handle often). His method is
ICT used as the *context* layer and Sierra Chart footprint / depth-of-market order flow used
as the *entry* layer, with volume profile supplying the levels in between.

Roughly **half this stream is non-technical**: how each of them got into trading, college
majors, Robinhood, whether red chart colours make you emotional, hippo-versus-killer-whale
digressions, trolls in the chat, channel plugs, and a long stretch of the host apologising
for not sharing his screen. The technical content is dense but arrives in bursts between chat
questions.

### What is actually taught

Bruv's path was TA → volume profile / market profile → ICT → order flow and auction market
theory, and he still runs the last three simultaneously. He is candid that this produces
analysis paralysis on some days — his own example is the flow reading bearish while a bullish
fair value gap is being retraced into with a break in market structure — and he offers no
tie-break for it.

The stack itself is clean. ICT supplies what to look at: equal highs and equal lows (he came
to ICT because he kept noticing failed breakouts and failed breakdowns), fair value gaps, and
which side of the market-maker curve you are on. Volume profile then narrows the level: he
uses exactly two features, **ledges** (a straight-out protrusion of volume, read as
absorption, which acts as a pivot in both directions — bounce off it, or break it and the
absorbers liquidate) and **low volume nodes**. He states the bridge explicitly: every fair
value gap is really just a low volume node, because price moved through too fast to transact.
Finally, once price is actually at the level, footprint and DOM decide whether to click —
is the speed of the tape picking up, is there aggression on the intended side. A level reached
on a dead tape is a reason *not* to enter.

Alongside this he runs an auction-market-theory setup he names as his main trade of the
session he walks through: when price leaves a **balance area** and then re-enters it, the
first target is the **point of control** and the second is the far edge of the balance. While
price is outside and below the balance he only looks for shorts.

On delta he is dismissive: usable as divergence, the way you would use RSI, but only while
recent — a divergence from four hours ago is disqualified — and he mostly does not use it,
preferring the speed of the tape for reversals. On level 2 he is more dismissive still:
displayed limit orders on ES can simply be pulled, and it is worth asking whether anyone
showing size wants to give away their hand; what matters is what happens at market.

Order blocks he actively demotes. He would rather take a fair value gap trade *supported by*
an order block than take the order block, and he says he is still holding off publishing a
video on them because which candle to use is subjective and changes with the timeframe — he
demonstrates the same structure resolving to different candles on the 5-minute and the
30-minute. He draws from the open, or the open plus the wick, but normally just the open.

Asked about bias, he says an uncertain daily bias does not stop him: he simply carries no
bias and trades a market structure break with displacement instead, on the reasoning that if
your bias is wrong you should still be fine focusing on the model. This sits awkwardly beside
his answer minutes earlier that the cure for seeing valid setups in both directions is
higher-timeframe narrative plus not skipping across timeframes (anchor on the 15-minute and
the hour).

### Numbers he gives that TTrades does not

- **Win rate averaging around 40%.**
- **2.5-point stop loss, 8-point target, then runners.** He frames this as deliberately
  unlike a standard ICT profile — smaller move, much tighter stop, "more like what the order
  flow people would be doing".
- Trading experience: two years, "only missed like a few days or weeks".
- Both men then insist a win rate means nothing without R and position size; the host offers
  his own case of an 86% win rate at 1R as the illustration.

### The host's own statements in this video

Three passages are attributable to TTrades with reasonable confidence, on the grounds that
the speaker is the one who owns the "Live Stream Guests" playlist and who says "I started
trading using the strat then I went into ICT" — the guest's history is TA → profile → ICT.

1. **Weekly power of three, walked on screen.** For a bullish week: the weekly open, then a
   move down which is the manipulation, then range expansion up (distribution), then a close
   near the highs. The operative claim is the timing — **the low should be put in Monday,
   Tuesday, or Wednesday morning, and "usually Tuesdays are a good idea"** — followed by an
   instruction to go back and check what every Tuesday did during a given move, and an
   immediate counter-example ("this week wasn't great"). Recorded as `power-of-three-amd`.
2. **His own point of interest**: "my point of interest for most my models is a liquidity run
   with an aggressive move back in the other direction or a fair value gap."
3. **His origin in TheSTRAT** — which matters because the next video in this unit *is* a
   STRAT video, and because his upcoming video at the time was "the part two to the strat and
   ict um going over strat entries".

### Concepts introduced (speaker's own terminology)

- "ledge" / low volume node / point of control / balance area (auction market theory)
- footprint, depth of market, "the tape", "speed picking up", absorption
- delta divergence "like RSI"; "who's trapped"
- ICT as the overarching layer, order flow as the narrowing layer
- "analysis paralysis"
- market maker buy/sell model, buy side vs sell side of the curve
- inducement as "running internal liquidity"
- power of three (host)

### Rules / conditions stated

- Select the trade with ICT (liquidity, FVGs, curve side); refine the entry with footprint/DOM.
- Do not drop to the entry layer until price is close to the point of interest.
- A level reached with no tape activity is a deterrent to entering.
- Volume profile is used only for ledges and low volume nodes; every FVG is a low volume node.
- On re-entry into a balance area: target the point of control, then the far edge.
- While price is below the balance area, only look for shorts.
- Delta divergence is only usable while recent (four hours ago is too far).
- Do not treat displayed level-2 size as a level; it can be pulled.
- Prefer a fair value gap trade supported by an order block over the order block itself.
- Draw order blocks from the open, or open plus wick; default to the open.
- If the daily bias is uncertain, carry no bias and trade a structure break with displacement.
- Entry timeframes: 15-minute for points of interest, then 5m / 1m / 15-second; the 15-second
  is only looked at when already at a point of interest.
- Trading window: after 08:30 to 11:00 Eastern (and 13:30 to close is named as the other kill
  zone). *Attribution uncertain — see ambiguities.*
- The stop raid does not have to occur inside a kill zone; only the entry must.
- Host: the low of a bullish week forms Monday, Tuesday or Wednesday morning, usually Tuesday.

### Examples walked through

- Daily chart with equal lows swept, a fair value gap on the smaller timeframe, and volume
  profile used to pick the entry price ("under like 37 35"); long taken there.
- Friday's session: he traded the re-entry into a balance area from around 55–65, targeting
  the point of control then the bottom of the balance; the rest of the day's trades were poor
  and he turned the computer off after the news rather than chase.
- Weekly chart: equal highs run into a weekly fair value gap, aggressive move down, small equal
  lows, retracement of the displacement range into an OTE — bearish, targeting the discount.
- The recurring London/New York setup on the 15-minute over three consecutive days: London
  takes the lows, structure breaks up, a fair value gap forms, and internal range liquidity is
  the objective at 09:30.
- Inducement walkthrough: lows run, aggressive move up breaking structure, discount of that
  range, longs induced and stopped out, entry into the OTE/FVG, first target the equal highs.
- Host's power-of-three walkthrough on two consecutive weeks — one that fits the template and
  one that does not.

### Quotes (verbatim, transcript-checked)

- "i use a sierra chart and then i just have my amp account connected"
- "every fair value gap is really just going to be a low volume node"
- "a straight out protrusion of volume is usually an area of like absorption"
- "the limit orders and like the level two on yes is usually not that important"
- "two and a half point stop loss and then i go for eight points"
- "take a fair value gap trade that is supported by an order block"
- Host: "you expect the slow to be put in monday tuesday or wednesday morning"
- Host: "i started trading using the strat then i went into and then into ict"

### Open questions / ambiguities

- **Attribution.** The transcript has no speaker labels and the host repeatedly reads a chat
  question and answers it himself with no cue. Three answers cannot be pinned and are
  therefore *not* recorded as concept files: (a) "I learned ICT just off the YouTube
  mentorship and my usual risk reward ratio is over 2R, that's where I go break even at 2R";
  (b) the kill zone windows "08:30 a.m. to 11 EST and then 1:30 to close"; (c) "does a stop
  raid have to happen during a kill zone — no, I just focus for my entry to form during a kill
  zone". Each would be a meaningful TTrades number if it is his; mis-tagging it would corrupt
  the `voice: ttrades` filter, so they are left here in prose only.
- "Speed picking up" and "aggressive on the buy side" are read by eye; no rate, delta or
  volume threshold is given.
- He states plainly that he has not mastered the DOM, so the top layer of his own stack is
  aspirational.
- No threshold defines a ledge (how much protrusion) or a low volume node (how low).
- "Re-enter" a balance area is not defined — wick inside, or close inside?
- The delta recency cut-off is given only by a counter-example (four hours), never as a number.
- The 2.5-point stop is stated without naming the instrument; ES and NQ are both under
  discussion and have different tick values, so the figure is not portable as spoken.
- His no-bias answer and his higher-timeframe-narrative answer are minutes apart and never
  reconciled.
- The host's Mon/Tue/Wed-morning window for the weekly low is **looser** than the channel's own
  later weekly-profile series, which classifies a Monday-or-Tuesday extreme as classic
  expansion and a Wednesday extreme as a *different* profile (midweek reversal). This is a
  genuine channel-internal inconsistency, not a guest disagreement.

---

## AM Trades | Weekly Profile
(`wGYde-h84cs`, https://youtu.be/wGYde-h84cs, 3826s ≈ 64 min)

**Guest: AM Trades** (21 at the time of recording). His method is a weekly profile anchored on
the red-folder economic calendar, confirmed by an hourly change in state of delivery, and
priced with standard-deviation projections of the manipulation leg.

Roughly **a quarter to a third of the runtime is non-technical** — repeated plugs for the
guest's PDF, Twitter and new YouTube channel, several minutes of the host failing to pin a
comment, chat moderation, ages, a hippo-versus-killer-whale question, and a stretch about
public-speaking anxiety and video production. The rest is a genuinely rapid Q&A and the host
apologises repeatedly for missing questions.

### What is new here versus `t_talks_01`

His previous appearance already established the three-tier news framework, "I do not trade
Mondays", phases of price delivery, the named weekly profiles, and the AM-session-only filter.
**New in this video**: the three-step form of the CISD check; the entire standard-deviation
projection methodology with its numbers; the max-expansion no-trade rule; his explicit
rejection of Seek & Destroy; the structural argument against trading stocks; the NQ-over-ES
rationale; M1–M5 execution; and the anti-prediction stance on the weekly profile.

### What is actually taught

Step one for any week is the economic calendar, filtered to **red folder only** — he says he
filters out yellow and orange on forexcalendar.com and does not consider them for weekly
manipulation at all. He concentrates on the 08:30 releases with FOMC at 14:30 as the odd one
out, and looks for the *first* high-impact driver of the week. Around that driver he expects
accumulation and the engineering of liquidity before it, manipulation at or just prior to it,
and — his phrasing — expansion always following manipulation. His model lives in the expansion.

He never trades Monday, and hardens the position on air (the host says "I usually don't even
trade Mondays"; AM replies "oh I never do, I know I said maybe but I never trade Mondays").
Three reasons: Monday is high-resistance accumulation; there is never high-impact news on a
Monday so volatility enters Tuesday at the earliest; and there is no weekly-profile data yet.
Monday is *data*. Tuesday only becomes a candidate if Monday engaged a higher-timeframe PD
array, which he says does not always happen.

The timeframes are: daily and 4-hour for the higher-timeframe PD array (the weekly chart is
rarely clean enough to trade off), hourly for the intraweek change in state of delivery. That
CISD is where he is most precise, and he gives it as three ordered steps: price is engaging a
higher-timeframe PD array; that engagement is paired with the day of the week the profile
calls for (time *and* price); and then the last up-close candle that engaged the array must be
closed *below* on the hourly. The observable consequence is a flip in what price respects —
before, it was respecting down-close candles on the way up; after, it retests up-close candles
and continues lower. He offers a 30-minute breaker close as an interchangeable alternative.

Then the projections, which is the most quantified material in the unit. He anchors standard
deviations on the **manipulation leg only** — the single swing move that drove into the PD
array that reversed price, from that leg's absolute extreme to the swing point where state of
delivery changed — and deliberately uses the *hourly* for weekly-scale projections because
lower timeframes add wick noise. **2 and 2.5 deviations are a good first target. 4 and 4.5 are
"max expansion" — what should cap the weekly range.** Intraday he repeats the construction
from the midnight open on a lower timeframe and takes the overlap of the intraday and weekly
projections as the target. And the rule that falls out of it is a hard no-trade: on the week
he walks through, Thursday already reached max expansion, so Friday was skipped — and he shows
Friday's attempt to extend being choppy rather than low resistance.

He is explicit that the profile is *recognised*, not predicted: when a week opens he does not
know what the profile will be and he lets the chart paint it out for him. This directly
matches the anti-template stance the channel takes throughout its own Weekly Profile Series (
do not predict which day makes the extreme; let it form, then trade), one of the few places
in this unit where guest and channel independently agree.

Asked about Seek & Destroy he says it is one of ICT's profiles and not one of his, and that he
never uses it: a profile where the external range is continuously swept both ways, whose order
flow is not clear. He gives the hourly signature — fail to displace over the buyside, fall
back in, fail to displace under the sellside, come back in, end up stuck in the middle. The
host adds that this is what he would call a broadening formation, which the guest accepts.

Two instrument-selection points close it out. He does not trade stocks: they do not trade
through London-to-Asia, so the daily chart is full of gaps and unreadable, whereas the futures
chart is fluid and each daily candle opens at the previous close (he demonstrates NQ futures
against QQQ). And he defaults to NQ over ES because NQ is more volatile, which exaggerates the
manipulation and the expansion and makes price come out cleaner — switching to ES only when ES
has been clearly the weaker of the two all week and he wants a short.

### Numbers he gives that TTrades does not

- **2 and 2.5 deviations = first target; 4 and 4.5 = max expansion capping the weekly range.**
- Execution on **M1 to M5**, "always with an understanding of at least the hourly profile" —
  which he prefaces with "I know it's probably unpopular".
- Age 21; started investing at 15–16, trading at 19–20.

### TTrades' own statements in this video

This is the richest ttrades material in the unit, because the host answers many audience
questions about himself directly and the "I don't know, AM, do you..." pattern makes the
attribution unambiguous.

- **He does not reduce position size in drawdown, and he shows the arithmetic on air.** Risk
  $100 per trade on a 2R strategy — "if you have a two hour strategy you can be profitable at
  34 win rate". Take a loss; halve the risk; the next 2R winner returns only $100 and gets you
  to break-even, whereas constant risk returns $200 and puts you 1R ahead. Scaling by recent
  outcome "adds another variable to the strategy". AM concurs, caveating that he would reduce
  only if mentally not performing or very deep in drawdown.
- **Fixed dollar risk**, stop from the chart, size solved to match — stated by both men in the
  same exchange, so this one is genuinely `mixed`.
- **"I think I do two are minimum"** (2R) for risk-to-reward, target-dependent.
- **The entry model is the least important part**: "the entry models the more and more you
  learn is like the least important part it's mostly about managing risk". What he does want
  to see is displacement and then failure swings behind it.
- **Daily bias**: "I get daily bias by using next day Model A lot of the times" — a daily candle
  closing while respecting a PD array, then aligned with the weekly profile.
- **The eight indicators on his chart**, enumerated: three watermarks, two open/high/low/close
  profile indicators (weekly and daily), a kill zones / sessions indicator, volume, and an ATR
  trailing stop he says he has never really used — and separately in the same video he says he
  does not personally use volume either. The working toolkit is therefore two power-of-three
  overlays and a sessions indicator. He charts on TradingView and executes on NinjaTrader.
- **Provenance**: "I do use standard deviations I have a video on that" and "I actually
  learned those from am". The ttrades-voiced standard-deviation material elsewhere in this
  corpus is downstream of this guest.
- **09:30 is asset-class-specific**: it matters because the New York Stock Exchange opens, so
  it is an index level, not a forex level; 08:30 is usable in forex when news lands there.
- **Day's Quarter Theory is not used** and is reduced in one sentence to "power of three based
  on session or opens of different time frames". In the same stream he also declines MACD,
  central bank dealing ranges, COT data, and analysing the proportions of ICT's logo ("I think
  it's a waste of time").
- **Structure**: "I personally focus on intermediate term structure the most", restated when
  the question is re-asked in the ICT-2022-mentorship context.
- **Lookback**: "I'm not looking at most things over a year ago" / "if anything I'll just be
  focused on old highs and lows". Not recorded as a concept file; too thin on its own.
- **Model pluralism**, twice: he says AM's model is slightly different from his and his from
  everyone else's, and that "you don't even have to use ICT" — "I know people
  that use a 21 EMA crosses with b-wop" (auto-caption: VWAP).

### The one place the host corrects the guest's material

A chat question challenges where AM anchored a projection ("why didn't you use the low with
the big candle down at 12"). The host answers *for* the guest and gets the construction right:
"he's projecting the manipulation so he's projecting the move up", not the move down. AM
then confirms and re-explains. It is a clarification rather than a disagreement, but it is the
clearest evidence in the unit that the host has internalised the guest's tool.

### Concepts introduced (speaker's own terminology)

- red folder only; "the first high impact news driver for the week"
- accumulation → manipulation → expansion, anchored on the calendar
- change in state of delivery, three-step form; the 30-minute breaker alternative
- standard deviations "anchored to market structure"; "max expansion"
- Seek & Destroy (defined, rejected); failure to displace both sides
- consolidation reversal on Thursday from the Monday–Wednesday external high and low
- "Monday is data"
- "letting the chart paint it out for me"

### Rules / conditions stated

- Filter the calendar to red folder only, for the traded instrument's currency (USD for indices).
- Find the first red-folder driver of the week; expect accumulation before, manipulation at or
  just before it, expansion after.
- Never trade Monday. Tuesday only if Monday engaged a higher-timeframe PD array.
- NFP week: no Monday, usually avoid the first half, Monday–Thursday are data, trade Friday
  using the 08:30 release as the volatility driver.
- Daily and 4-hour for the higher-timeframe PD array; hourly for the weekly CISD.
- For the weekly profile, only external liquidity counts — previous day high/low and above; no
  intra-session or internal liquidity.
- CISD: HTF PD array engaged + correct profile day + hourly close below the last up-close
  candle that engaged the array.
- Anchor deviations on the manipulation leg into the reversing PD array; hourly for weekly
  projections; 2/2.5 first target; 4/4.5 max expansion.
- If max expansion is already reached, do not take further continuation trades that week.
- If Monday–Wednesday consolidate with no HTF PD array engagement, mark Thursday's external
  high and low and look for manipulation there (consolidation reversal).
- Execute M1–M5, always backed by at least the hourly profile; do not trade before New York.
- AM session only; PM session only on FOMC days because that is where the volatility is.
- Never hold through high-impact news; if you trade London, do not trade before an 08:30 release.
- Stop from the chart, size solved for fixed risk; do not reduce size in drawdown.
- Do not trade instruments whose daily chart gaps (stocks, ETFs, CFDs).
- Default to NQ; switch to ES only on clear week-long relative weakness.

### Examples walked through

- A midweek reversal on NQ: Monday and Tuesday up-close, price in premium sweeping the previous
  day high on Wednesday, hourly close below the last up-close candle at 12:00 → CISD; shorts on
  Thursday and Friday at New York open. He shows the standard deviations on the same chart:
  2/2.5 as his full take-profit (a ~200-point move), 4/4.5 reached Thursday, so Friday skipped.
- The same trade broken to the 30-minute to show the breaker alternative to the CISD.
- The intraday version: Thursday's midnight price marked, the manipulation before the
  distribution isolated, market-structure high to low projected — the intraday and weekly
  levels line up and that overlap is the target.
- EURUSD used to illustrate Seek & Destroy: failure to displace over the highs, failure to
  displace under the lows, stuck in the middle.
- NQ futures daily versus QQQ daily, to show why the gaps make a stock chart unreadable.
- A last-week EURUSD review: Thursday made the high on high-impact news, then lower, equal lows.

### Quotes (verbatim, transcript-checked)

- "I only focus on red folder"
- "always following manipulation we look for expansion"
- "I never trade Mondays"
- "I don't know what the weekly profile is going to be"
- "2 and 2.5 is a good first Target"
- "for the week this is what I consider what should cap the weekly range"
- "not something I trade because the order flow isn't very clear"
- Host: "if you have a two hour strategy you can be profitable at 34 win rate"
- Host: "the entry models the more and more you learn is like the least important part"
- Host: "I actually learned those from am"
- Host: "three of them are watermarks two of them are open eye low clothes"

### Open questions / ambiguities

- The three-step CISD does not say whether the close through the up-close candle must be a
  body close.
- Whether the deviation anchor uses wicks or bodies is answered only for the high side ("the
  absolute high to the swing low").
- No rule chooses between the 2 and the 2.5 as the first target, or between the 4 and the 4.5
  as the max-expansion trigger.
- The max-expansion no-trade rule does not say whether it also bars trades in the *opposite*
  direction.
- "High resistance" (his description of Monday) is never quantified.
- "Clearly weaker throughout the entire week" (the ES switch) has no measure — no ratio chart,
  no percentage.
- The red-folder-only filter here is coarser than the high/medium/low tiering recorded from his
  earlier appearance. Both are his; the tiering is the finer statement, the red-folder filter is
  what he says he actually does. Recorded as a variant on `news-impact-tiering`, not as contested.
- The host's own indicator inventory contradicts itself inside one answer — volume is listed on
  the chart and disclaimed as unused in the same video. The resolution he gives is that it is
  simply left up there.

---

## Alex's Options | TheSTRAT & Broadening Formations
(`1XWyy6Q-_8Q`, https://youtu.be/1XWyy6Q-_8Q, 5313s ≈ 89 min)

**Guest: Alex (Alex's Options)**, of Strat Trading, with a partner Sarah and two others. His
method is Rob Smith's TheSTRAT — a complete, ICT-free system built on classifying each candle
by what it did to the previous candle's high and low, plus timeframe continuity and drawn
higher-timeframe outside bars — which he switched to *from* ICT for its objectivity.

This is by far the most technically dense video in the unit: **under ten percent is
non-technical**, essentially the introduction, one screen-sharing fumble, and the closing
link-swapping. Everything else is a continuous, chart-by-chart methodology walkthrough that
overruns the planned time.

**This section deliberately records the method in its own terms.** Where the guest himself
draws an ICT parallel it is noted as his parallel; nothing is translated into ICT vocabulary
that he did not use, and the STRAT-versus-ICT differences are *not* marked `contested`.

### What is actually taught

He states up front that he traded ICT alongside the STRAT, mostly on futures, and moved
because of objectivity at scale: ICT is workable when you focus on one or two indices and can
dial in every timeframe and reason about the draw on liquidity, but he runs scans and may hold
seven to eight positions in a day, and that gets hectic — "I like the Strat just because I
think a little bit less". He also abandoned order blocks specifically because they can be run
through, and he would rather be stopped out and take the trade straight back the other way
than be wrong slowly. He says mixing the two systems confused him.

**The taxonomy.** From one candle to the next there are only three possibilities, which is why
the labels are 1, 2 and 3. A **1** takes neither the previous high nor the previous low — an
inside bar, "by definition that is a consolidation", tradeable while open but choppy with small ranges.
A **2** takes exactly one side: a 2-up takes the previous high, a 2-down takes the previous
low, and a 2 is by definition directional. A **3** takes both — an outside bar, which he
describes as "a candle that went 2 and failed", normally failing near the beginning of the
candle, and which he notes an ICT trader would read as manipulation above the previous
candle's high. From a 2 the only further state available is a 3, and a 2 usually opens as a 1
first before triggering.

**Broadening formations.** This is the part that gives the video its title, and it is not a
pattern-recognition exercise. A broadening formation is the *drawn representation of a
higher-timeframe outside bar*. When a run of candles has collectively taken out both the high
and the low of the bars to their left, those bars would be a single 3 if compressed onto a
higher timeframe — a "compound three" — and you draw that fact by connecting the successive
highs and successive lows. You draw it, he says, because your broker will not show it to you:
the timeframe on which it would be one candle may be arbitrary, "some wonky time frame like a
two and a half day chart". You widen the drawing every time a new extreme prints, and when
price gets stuck inside without taking either side you terminate that formation and start a
new one from the stuck range — which is why the formations get bigger over time.

**Actionable signals.** Because the taxonomy is finite, the set of reversals is finite: 2-1-2,
2-2, 3-2-2, 3-1-2 and 1-2-2, with continuation forms 2-2, 2-1-2 and 3-2. Magnitude (first
target) is the previous candle's opposite extreme — for a bearish 2-2 reversal, the previous
candle's low; for a 3-2-2 that fails the high of the 3, the bottom of that 3 — and the reason
that is the target is that taking it makes the recent bars a compound outside bar on the next
timeframe up. He makes one explicit ICT mapping: **1-2-2 is what an ICT trader is actually
trading** when they trade accumulation–manipulation–distribution or the box setup.

**Timeframe continuity.** Multiple timeframes read purely by candle colour, month/week/day for
day trading, with quarter and year for positioning. The ideal is that every timeframe is *out
of a 1* before a trade, because a timeframe sitting inside means its participants are not in
control. His mechanism is participation: about 70% of traded volume is algorithmic, and an
algorithm must be told what to trade, how to trade it (sit on the bid, sit on the offer, take
the offer), and *when* — so every new period open introduces a new participant group, and a
new monthly or quarterly open flipping colour is the observable event. When volatility rises,
drop the continuity read a timeframe. And the operating instruction is to trade the lower
timeframes deliberately in order to *trigger* 2s on the higher ones.

**Management.** The single most repeated rule in the video: if it does not reverse against you
it is still going. A 2-2 against the position is the cue to lighten; a 3 against the position
gets time, because a 3 is itself a broadening formation and may resolve back your way; stops
move up promptly because "you don't want to let green go red". And you add: take the 15-minute
signal, add when it triggers the 30, add again when the hour prints a 2-1-2 — "we always want
to add to Winners" — because each higher timeframe triggered hands you that timeframe's runway.
He frames the contrast plainly: ICT focuses on trading the range, the STRAT is trying to create
winning positions and hold them as long as possible.

**Peripheral rules with real teeth.** Gap up, prefer to sell back into the previous range; gap
down, prefer to buy — *unless* the gap itself delivers a higher-timeframe trigger, in which
case it is continuation (his Apple example gapped down through the previous month's low). Do
not trade into clear blue skies, because with no previous range overhead there is nobody to
stop out. A **pivot machine gun** is five or more consecutive same-direction 2s (his partner
Sarah's rule) — the stack of pivots left behind is who bought all the way up, and taking them
back out is what accelerates the reverse. **Decoupling**: at the session open the day, hour, 30,
15 and 5 all share one opening price, so only the daily participants have spoken; each lower
timeframe's second candle is the first with its own open, and they decouple in sequence.
**Scalping** is only permitted while the hour is a 2 — if the hour is a 1 "it's doing nothing" —
and requires volatility, so he directs it at gappers and earnings names.

### Numbers he gives that TTrades does not

- **~70% of traded volume is algorithmic** (his justification for the whole continuity framework).
- **Five or more consecutive same-direction 2s** = pivot machine gun (Sarah's rule).
- **Seven to eight positions a day** — his own workflow, which is the stated reason for the
  switch away from ICT.
- Three going on four years trading TheSTRAT.

### TTrades' own statements in this video

Two passages, both substantial, and both revealing where the channel's boundary sits.

1. **Mid-video, he maps the STRAT 2-2 reversal onto his own next-day-bias model.** Looking at
   a candle that goes up, fails, and closes back into the range: "just looking at this candle
   at the next day bias video, we expect this next candle to drop down — well that's your two
   two reversal triggers down, where does it go, the other side of the range." He is asserting
   that his published daily-bias signal and the guest's 2-2 reversal are the same object.
2. **At the end he takes the screen and demonstrates his own version of the broadening
   formation.** He does not use compound outside bars at all. He marks a range, treats the two
   boundaries as sellside and buyside liquidity, and reasons that failing one side and falling
   back in makes the other side the objective — which incidentally produces the same drawn
   shape. He then drops a timeframe for the entry and expands the drawing as information
   arrives. He notes the drawing convention differs: Alex anchors from the extreme and draws
   backwards, he draws forward. What he takes from the tool is *target projection*. And he
   closes by asserting the equivalence outright — "most ICT people just see that as we took
   sell side and we're reaching for buy side, but there's other ways to look at it… it might
   not be ICT but you can use it, it all goes together."

That closing line is itself the interesting disagreement: the guest says mixing the two
systems confused him and he had to pick one; the host says they go together. Both readings are
preserved.

### Concepts introduced (speaker's own terminology)

- 1 / 2 / 2-up / 2-down / 3; inside bar, outside bar
- broadening formation / "the tri"; compound three; compound inside bar
- actionable signals: 2-1-2, 2-2, 3-2-2, 3-1-2, 1-2-2; Rev Strat; "shooter"
- magnitude / pivot target
- timeframe continuity; "in force"; "new participants"
- decoupling
- pivot machine gun (attributed to Sarah)
- "chop shop" / getting stuck inside
- Rob Smith (the STRAT's originator, who had recently died); his favourite setup the 3-2-2,
  "they're fun to say and fun to trade"

### Rules / conditions stated

- 1 = neither previous extreme taken; 2 = exactly one taken; 3 = both taken.
- The only state available from a 2 is a 3; a 2 usually opens as a 1 and triggers.
- A broadening formation is a higher-timeframe outside bar; draw it because the broker will not.
- Redraw the formation whenever a new extreme prints; start a new one when price gets stuck.
- Magnitude of a reversal = the previous candle's opposite extreme.
- Ideally no timeframe in the stack is a 1 before taking a trade.
- Trade the lower timeframes to trigger 2s on the higher timeframes.
- If it does not reverse against you, it is still going — hold.
- Lighten on a 2-2 against; give a 3 against some time; never let green go red.
- Add to winners as each higher timeframe triggers.
- Gap up → fade down into the range; gap down → fade up; unless the gap delivers a HTF trigger.
- Do not trade into all-time highs — no previous range means nobody to stop out.
- Five or more consecutive same-direction 2s = pivot machine gun.
- Do not trade while stuck inside a formation.
- Only scalp while the hour is a 2, and only in volatile / gapping names.
- Only regular trading hours — "we really only trade RTH so we have to trade the New York
  session only".
- Best entry after a 3 hits the top of the formation is *any* 1-minute or 5-minute reversal
  there, not only the obvious one.

### Examples walked through

- CCL on the 12-month chart: a 2 up that chopped, then a 2 down making a 2-2 reversal, and the
  three candles compressing into a higher-timeframe 3.
- SPY across year / quarter / month / week / day: a marginally higher yearly high that went red
  immediately, both sides of the previous year taken, the new yearly open flipping from selling
  to buying, and then the quarter taking control while the year sat inside.
- EA as the canonical chop shop — too weak to take the highs, not weak enough to take the lows,
  going nowhere since 2020.
- Apple: the exception to the gap rule — gapped down through the previous month's low, putting
  the month in force, so the gap was continuation not a fade; then 2-1-2 continuations down.
- DKNG on the Friday before: broadening formation on the daily, inside day before earnings,
  gap up, the 09:30 and 09:45 buying, then the 2-2 back down on the 30-minute; the 15-minute
  entry, add on the 30, add on the hour, exit around 3091.
- The same DKNG name on a 3-minute entry timeframe against hourly continuity, to demonstrate
  decoupling, the grey "in conflict" signals, partialling on a 2-2 against, and the hourly flip
  at 12:30 from selling to buying.
- NQ on the 15-minute through the daily and weekly: repeated formations, an order block noted
  as the ICT reading of the same area, and a long walk showing the try starting over, widening,
  and eventually resolving.
- Tesla, as the case for the yearly candle: a 3-2 up on the year, and every lower timeframe
  trending with it all year, with the 1s marked as where day traders get killed.
- The host's own EURUSD/NQ range demonstration at the end.

### Quotes (verbatim, transcript-checked)

- "one is a candle that did not take the previous candles high"
- "what the three is is a candle that went to and failed"  *(auto-caption: "went 2")*
- "the only thing that can happen from a two is a three"
- "taken out both sides of the range and created a higher time from outside bar"
- "your broker is not going to show you it"
- "if it doesn't reverse against you it is still going"
- "we always want to add to Winners"
- "the market has to trade in the direction of the most twos"
- "twos to the upside all in the same direction for five or more candles"
- "anytime this hour is two that's when you can start scalping"
- "ICT focuses a lot on trading the range"
- Host: "we're likely to reach for the other side of the range"
- Host: "it might not be ICT but you can use it it all goes together"

### Open questions / ambiguities

- Equal highs / equal lows are never addressed: whether `high == prev.high` counts as taking it
  is undefined, and the whole taxonomy hinges on it.
- No initial stop rule is given anywhere in 89 minutes. Only targets, partialling and "don't let
  green go red".
- The 70%-algorithmic figure is unsourced.
- Whether continuity colour is read live intrabar or only at close is never stated — the method
  requires it to be live.
- "Stuck inside", "volatile enough" and how long to give a 3 against you are all read by eye.
- Which bar anchors a broadening formation is chosen by eye; no rule selects the starting bar.
- The full signal chart was shown on screen and offered as a link; the transcript names only
  part of the set, so what is recorded is what was *spoken*, not the published set.
- "Rev Strat" and "shooter" are used as named signals without being defined in the audio.
- The claim that a 3 fails "near the beginning of that candle" is a tendency with no threshold.

---

## Day Trading Rauf | Preparing for a New Week
(`qFtfD09Vv3E`, https://youtu.be/qFtfD09Vv3E, 2475s ≈ 41 min)

**Guest: Day Trading Rauf** (captioned "Ralph" throughout). His method is dollar-first,
top-down weekly framing — DXY monthly draw, then everything priced in dollars derived from it —
executed in the New York session only, with the breaker as his preferred entry.

Perhaps **a fifth of the runtime is non-technical**, most of it forced: the first several
minutes are lost to the guest's audio dropping out and to him having the wrong week on screen,
and the last stretch is channel plugs and indicator questions. It is a Sunday preparation
stream, so the content is a live weekly plan rather than a taught model.

### What is new here versus `t_talks_01`

His previous appearance was a schematic MMXM lecture — mitigation of orders, old accumulation
becoming new distribution, the Silver Bullet requiring a breaker, mitigation blocks, fib
grading of the dealing range. **Almost nothing here overlaps that.** New: the calendar-as-
roadmap weekly skeleton; the no-news 9:30 Judas swing finding; the dollar-first order of
operations; the currency-futures pairing method; the wick-versus-body breaker filter; the
kill-zone-open avoidance rule; the 04:00 day start; stop placement by swing class; the
month-and-quarter-end dampener; and the three-drive read. The one carry-over is his preference
for breakers over order blocks, which is stated with a new mechanical filter attached.

### What is actually taught

He opens with the calendar, and the framing is strong: the economic calendar is where most of
your trades will be formed, because it creates the weekly range. For the week he is planning,
Monday has no USD news and reads as accumulation for the weekly range; Thursday is where he
expects distribution; and the open question the calendar leaves is *where the manipulation
occurs*, which is why he waits for external range liquidity to be taken. He explicitly
criticises reading red-folder events as a directional expectation on their own, preferring
candle closes; and he discounts 03:00 euro news entirely because he trades New York.

The analytical order is dollar first. He works DXY monthly (where the large funds are
positioned) → weekly → daily, identifies the draw, and then derives everything else by
inversion: dollar higher means EURUSD lower and NASDAQ lower; dollar lower means NASDAQ higher.
Gold gets the same treatment. He corroborates the dollar read against the bond/yield chart on
the stated relationship that yields and DXY move together, and says SMT is the easiest way to
see real accumulation happening; for indices he watches three averages.

For choosing an FX vehicle he charts the **individual currency futures** rather than the pair,
ranks them, and matches a weak currency against a strong one, because that is where the
low-resistance liquidity run forms. Live, sterling futures have been selling off and are in a
deeper discount than the euro, so he will not touch the pound and will trade EURUSD; scanning
the crosses he rejects the ones where both legs are merely consolidating, and flags EURAUD as
the one that does look good.

The gate on the whole thing is stated twice: if you do not have a clear draw on the monthly and
you do not have a clear idea which way the weekly candle is going to expand, there is no point
trading. He grounds it on the claim that a candle can only print two shapes — open-low-high-
close or open-high-low-close — so the whole question reduces to which one the week is printing.
And he applies a dampener: this week is both the last of the month and the last of the quarter,
so he does not expect much from price, and keeps the direction but shortens the ambition —
tag the draw, then close back into the fair value gap that caps the monthly candle.

**The most automation-relevant claim in the unit is his 9:30 finding.** On index futures 09:30
is a volatility injection. On a day with *no* high-impact news it is the *only* volatility
injection of the day, and he found in his own study that the Judas swing forms more reliably at
09:30 on exactly those days. The inversion matters: a no-news day is not a day to sit out, it
is the day the opening manipulation is cleanest — which is why he is willing to trade NASDAQ on
a Monday on the 1-minute and 5-minute charts when most people avoid Mondays. He recommends it
to the audience twice as something to study themselves.

On entries, the breaker is his favourite, because a breaker shows a real change in the state of
delivery and — quoting ICT — that is where opportunities are born. Structurally: low, high,
lower low, with the significant candle being the one no bodies subsequently pass. Functionally
it is another form of mitigation, the place where anyone positioned the other way squares or
offsets. And he attaches a filter he recommends studying: **bodies closing below a bullish
breaker's low kill it; wicks below it do not**, and a breaker that was only wicked trades much
better on the return. He generalises to ICT's principle that bodies tell the story of the
market narrative.

Two more discrete rules. He would **never trade at the beginning of a kill zone** — in the
forex 07:00–10:00 window the market at the start is doing the opposite of what it will do,
enticing traders the wrong way; use the 07:30 or 08:30 opening price as the reference instead.
And his **day starts at 04:00**; nothing before that is significant, he does not trade London,
and he watches New York only because New York is either a continuation of what London did or a
reversal of it — two players, simple framing. For stops he does not read market structure for
direction but does use it for placement: the best stops form at intermediate-term and long-term
highs and lows; short-term ones he considers much riskier.

Reviewing his own week he shows a **three drive pattern** — liquidity taken three times above
the same area — read as a reversal, argued as logic rather than rule: the buy stops are gone,
price is back in fair value, longs from there have failed, so running the sell stops below is
the easier path.

On COT he says it works better for long-term position holding — for an investor rather than a
speculator. He uses no indicators at all ("I used to back in the day but not anymore") and
charts forex.com data on TradingView because ICT uses it.

### The host's own statements in this video

TTrades takes the screen once, to answer a chat question about how to frame New York, and gives
the binary with the reasoning: using the midnight open, if he is bullish and London set the
current high of the day and there is a discount array below, he anticipates a **New York
reversal** — London's high must be taken, then the low forms and the day closes high, producing
a bullish reversal candle shape. Still bearish, he anticipates a reach back into premium or a
PD array then continuation lower into the close — the classic sell-day profile. He places it
inside the daily profile framework and limits it to the New York AM session. The guest's reply
is "yeah, that's what he meant, perfect explanation", and the guest's independent version of the
same binary is why he only trades New York — a genuine convergence.

He also lists his own chart tooling here, consistent with the AM video: a power-of-three
weekly/daily profile indicator (he names the author as sounding like "two degrees") and a kill
zones indicator, "most of the time my chart's pretty clean".

### Concepts introduced (speaker's own terminology)

- the economic calendar as "the roadmap" that "creates the weekly range"
- accumulation Monday / manipulation at external liquidity / distribution Thursday
- external range liquidity into internal range liquidity; "buy stops or sell stops or inefficiency"
- dollar-first analysis; individual currency futures; "low resistance liquidity run"
- the 9:30 volatility injection and the no-news Judas swing
- breaker as "another form of mitigation"; bodies versus wicks below the breaker
- "I would never trade at the beginning of a kill zone"; 07:30 / 08:30 opening price
- three drive pattern
- long-term / intermediate-term / short-term highs and lows for stop placement

### Rules / conditions stated

- Map the week's calendar first; a newsless early day is accumulation, the back half is distribution.
- Do not take direction from a news event; wait for external range liquidity to be taken.
- No clear monthly draw and no weekly expansion read → no trade.
- Analyse DXY before EURUSD, gold or NASDAQ; derive them by inversion.
- Corroborate the dollar with bonds/yields; use SMT to see real accumulation; three averages for indices.
- Chart individual currency futures; pair a weak currency against a strong one.
- Reject crosses whose legs are both consolidating.
- Closing week of a month and/or quarter: keep direction, reduce expected range.
- On no-news days expect the 09:30 Judas swing; fade it toward the draw on the 1m/5m.
- Never enter at the start of a kill zone; use the 07:30 / 08:30 opening price as reference.
- Start the day at 04:00; treat New York as continuation-or-reversal of London.
- Breaker = low, high, lower low; bodies through the defining extreme disqualify it, wicks do not.
- Stops behind long-term or intermediate-term swings only.
- Three runs into the same level is a reversal read.
- COT is for long-term investing, not speculation.

### Examples walked through

- DXY monthly: an open-low candle with a fair value gap above as the draw, so a high expected
  inside the gap, buyside taken, then back into the range; weekly showing the two levels he is
  watching; daily fair value gap as the internal target to cap the weekly range.
- EURUSD as the exact mirror: monthly fair value gap as the draw, two lows below as the deeper
  objective, lower into the internal range liquidity.
- Sterling versus euro currency futures — the pound too weak and too deep in discount to touch.
- NASDAQ: monthly close approaching, a run below the low into the weekly close, a fair value gap
  and a volume imbalance above as draws; bearish because bullish on the dollar.
- Gold: bearish dollar-derived, two marked areas below, but muted by the quarter-end dampener.
- EURAUD / GBPAUD from a chat suggestion: euro bearish and AUD/NZD consolidating on the daily.
- His own week: shorts from a fair value gap after a high was taken, re-entry lower, and the
  three-drive read that framed it.
- A 1-minute MMXM breaker (low, high, lower low) with no bodies passing it, shown as his entry.
- The host's New York reversal / continuation diagrams on the midnight open.

### Quotes (verbatim, transcript-checked)

- "the economic calendar that's where most your trades will be formed"
- "you trade from external range liquidity into internal range liquidity"
- "Judah swing is much likely to occur on 9 30"  *(auto-caption: "Judas")*
- "because there is no volatility injection apart from the 930"
- "Breakers are probably my favorite entry techniques to enter the market"
- "bodies that close below this low instead of weeks"  *(auto-caption: "wicks")*
- "I would never paid at the beginning of a Kill Zone"  *(auto-caption: "trade")*
- "the best ones will form at intermediate term highs and lows"
- "if you match up a weaker currency against a strong currency"
- "if you don't have a clear draw on the monthly" / "there's no point you trade in"
- Host: "there is a discount array down here then I'm anticipating a New York reversal"

### Open questions / ambiguities

- The 9:30 finding has no sample size, instrument set or period, and no size threshold separates
  a Judas swing from an expansion. It is the single best backtest candidate in the unit *and* the
  least evidenced as stated.
- "The beginning of a kill zone" has no duration; the rule is given for forex 07:00–10:00 and it
  is not said whether it transfers to the index open.
- The breaker filter does not say which timeframe's bodies count, nor whether one body close
  kills the breaker permanently.
- "4am" has no timezone stated (his other references imply EST) and the attribution for it is
  captioned "TCM" and unresolvable.
- "Three times above here" has no tolerance band for how close the three highs must be.
- The DXY–yield relationship is stated as a constant, and he never says whether he charts bond
  price or yield — which inverts any divergence reading.
- "Realistically trading starts on a Thursday and Friday" is contradicted later in the same
  stream when he says he does sometimes favour trading Mondays on NASDAQ.
- The month/quarter-end dampener is never quantified.
- No stop rule accompanies the breaker entry.

---

## Cross-video observations

The distinction that matters for this unit is between **four traders disagreeing** and **the
channel disagreeing with itself**. They are recorded differently.

### Guest-versus-guest methodological differences (NOT `contested`)

These are four separate methods. Each side gets its own concept id and neither is marked
contested, because a disagreement between two interviewees is not evidence that the channel is
inconsistent.

1. **When to execute relative to a session open.** Day Trading Rauf: *never* trade at the
   beginning of a kill zone — the opening move is the entice (`killzone-open-avoidance`). Ash
   Trades, from `t_talks_01`, executes *only* at a session open, London 02:00 or New York 09:30
   (`opening-time-only-execution`). These are exact opposites and both are held firmly.
2. **What confirms an entry.** Alex's Options: nothing but candle relationships — he abandoned
   order blocks because they get run through. HolyAngelBruv: the footprint and the tape, with
   ICT only supplying context. AM Trades: an hourly close through the last up-close candle at a
   higher-timeframe PD array. Rauf: a breaker that has only been wicked, never body-closed
   through. Four different confirmation objects for the same decision.
3. **Trade management.** Alex holds until a reversal signal prints against him and adds on every
   higher timeframe that triggers; Bruv runs a 2.5-point stop to an 8-point target with runners;
   AM projects deviations and takes profit at 2/2.5. Fixed-R, signal-based and projection-based
   exits, in one unit.
4. **Whether a bias is required.** Bruv: no — carry no bias and trade a structure break with
   displacement. AM: yes, but not until the week has painted the profile. Rauf: emphatically yes
   — no monthly draw and no weekly expansion read means no trade at all.
5. **News.** AM builds the entire week around red-folder events and avoids the days before them.
   Rauf takes the opposite operational stance on the specific case of the 09:30 open: a *newsless*
   day is the better day to trade the opening manipulation.
6. **Which instruments.** AM will not trade stocks at all because their daily charts gap. Alex
   trades mostly single-name equities and gappers and treats the gap as the opportunity.

### Where TTrades' own voice appears, and what it reveals

The host is not passive in this batch. His own statements — all tagged `voice: ttrades` — are:
the weekly power-of-three timing (low Monday/Tuesday/Wednesday morning, usually Tuesday); the
next-day model as his usual daily-bias source, and his on-air claim that it is the same object
as the STRAT 2-2 reversal; his own range-and-sweep reading of a broadening formation, drawn
forward rather than backwards; fixed dollar risk with no size reduction in drawdown, with the
2R/34%-win-rate arithmetic; a 2R minimum; the entry model being the least important part; his
eight-indicator chart inventory; 09:30 as an index-only level; Day's Quarter Theory reduced to
power of three on session opens; intermediate-term structure as his focus; and the New York
continuation-or-reversal binary off the midnight open. (His stated ~one-year analysis lookback
is recorded in prose only — too thin to stand as its own concept file.)

He does not push back hard on any guest in this batch — unlike the recorded T Talks case of him
correcting a guest's breaker/order-block labelling. The closest he comes is a *clarification*:
when a chat question challenges where AM anchored a standard-deviation projection, the host
answers for him and corrects the questioner ("he's projecting the manipulation so he's projecting the move up", not
the big move down"). What he does instead is **absorb**: he restates the STRAT 2-2 reversal as
his own next-day model, restates broadening formations as ranges with two liquidity sides, and
closes the STRAT stream with "it might not be ICT but you can use it, it all goes together" —
directly against the guest's own conclusion that mixing the two confused him and he had to pick.
That is the boundary this batch reveals: TTrades treats other systems as re-descriptions of his
own rather than as rivals.

He also discloses one provenance fact that changes how a corpus concept should be read: **he
learned standard-deviation projections from AM Trades.** The ttrades-voiced deviation material
elsewhere in the library is downstream of this guest.

### Channel self-inconsistency (this *is* a `contested` candidate)

One genuine case. In the Bruv stream TTrades gives the weekly power-of-three low as forming
"Monday, Tuesday or Wednesday morning, usually Tuesday". The channel's own later Weekly Profile
Series uses the day of the weekly extreme as the *classifier*: a Monday or Tuesday extreme is a
classic expansion, a Wednesday extreme is a midweek reversal — a different profile with
different tradeable days. The looser three-day window and the classifier cannot both be the
rule. This is flagged in `power-of-three-amd`'s ambiguities.

A second, smaller one: within the AM stream the host lists volume among the indicators on his
chart and, in the same video, says he does not personally use volume. His own resolution is that
it is simply left up there — recorded in `ttfm-minimal-toolkit` rather than treated as a conflict.

### The best backtestable material in this unit

- **Rauf's no-news 9:30 Judas swing** — a conditional, mechanically checkable claim (calendar
  filter × opening-impulse reversal rate) that nobody else in the corpus makes.
- **AM Trades' deviation ladder** — 2/2.5 as first target, 4/4.5 as the cap on the weekly range,
  with a hard no-trade rule once the cap is reached. Fully specified and directly measurable.
- **Alex's timeframe continuity and the 1/2/3 taxonomy** — the only fully algorithmic
  classification scheme in the corpus. Every rule is decidable from OHLC alone with no
  discretionary level-drawing, which makes it the cheapest thing here to implement and test,
  and the cleanest control against the discretionary ICT concepts.
