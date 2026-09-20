# Live Streams — study notes (unit_id: `live_streams_03`)

Channel: TTrades_edu. Playlist: "Live Streams" — the channel's own **New York Open Live Q&A**
streams (not the guest interviews that share this playlist family). Four videos, all four
transcripts present and readable (auto-en), ~5 hours of runtime total.

| video | id | duration | trade taken on air? |
|---|---|---:|---|
| New York Open Live Q&A | `W7Fu3Rx5iMs` | 5027s | no (walks the setup, no position) |
| New York Open Live Q&A | `X4XSsv5CNqg` | 4757s | no position stated; full post-hoc review of the day's move |
| New York Open Live Q&A | `c7nk7ypJHN4` | 3395s | no — "there's just no framework for me today" |
| New York Open Live Q&A | `U4j-fZD-FJk` | 5019s | **yes** — SPX 0DTE puts, entered and fully exited live |

## What this genre is, honestly

This is a live chat show, not a lesson. A large share of the runtime — I would put it near
half, and in `W7Fu3Rx5iMs` and `X4XSsv5CNqg` more than half — is prop-firm and indicator
giveaways (rules about putting an email in your YouTube description, re-rolling winners,
policing spam), travel talk, cars, Clash of Clans, gym and sauna, monitor specs, chart hex
codes, and trolls. None of that is recorded here. What makes the genre worth mining is the
other half: viewers ask the questions the polished videos never answer, and he answers them
off the cuff with numbers, session times, order types and refusals. Those are what this unit
contributes, and they are concentrated in short bursts.

The single most valuable structural fact about the genre: **he is narrating a live chart he
can see and I cannot.** Almost every teaching sentence contains "this", "here", "that low".
Where the referent is not recoverable from the words alone I have left the concept
underspecified rather than guess what was on screen.

## Transcript hygiene

Auto-caption artifacts I had to decode. These are decoded silently in the notes below and never
inside a `quote:` field — every quote in the YAML files is copy-pasted verbatim, artifacts and
all.

- **"candle to" = candle 2.** The known corpus-wide artifact, present here: "Do we have a candle
  to closure right on the daily?", "you're basically entering a candle two closure", "a candle to
  closure entry". The same stream also renders it correctly as "candle two" and "candle 2", so all
  three spellings appear within one file.
- **CISD is mangled four different ways**: "CSD" ("entry on first CSD", "confirm daily bias with a
  1-hour CSD"), "CST" ("5-minute CST"), "change in the state of **delivering**" (X4XSsv5CNqg, twice
  in the same walkthrough), and — best of all — **"CIS team"** in `U4j-fZD-FJk`: "We want to see
  what? A V-shape reversal with a CIS team." Read as CISD.
- **Ticker mangling is constant.** "YM" becomes **"I am"**, **"Y'all"**, **"Y N"**, and "Y M".
  "NQ" becomes **"MQ"**, **"ENQ"**, **"InQ"**, **"Q"**. "GC1!" is transcribed as
  "GC1 {exclamation point}". "IFVG" becomes "IFG". "T-spot" becomes "T-stop". His own indicator
  "TTFM Pro" is rendered "GTFM Pro" in one stream and correctly in another; ttrades.com becomes
  "btrades.com" and "lucid.ttrades.com" becomes "Lucid ages.com".
- **"Vshape"** for V-shape, **"stop pop set"** for a prop-firm name, **"orange folder"** for a
  news-calendar impact colour.
- Two passages are garbled beyond safe recovery and I have not used them: the news-day exchange in
  `X4XSsv5CNqg` ("Don't trade the day that current day prior to the news") where the viewer's
  question and his answer have run together, and "Can you explain why 1:00 a.m. 1-hour TIC failed
  on gold?" where "TIC" is unrecoverable.
- **No timestamps anywhere in these four transcripts**, so **no `approx_time` is recorded in any
  concept file in this unit.**

---

## `W7Fu3Rx5iMs` — New York Open Live Q&A (5027s)

### What is actually taught

The richest of the four for mechanics, because there is no trade and he fills the time answering.
Three answers here are the kind that unblock automation.

**The daily bias, stated as a formula.** Asked for a daily bias he says to keep it very simple and
gives the two-step rule outright: a candle 2 or candle 3 closure on the daily paired with an hourly
change in the state of delivery — "basically just my model on the daily and hourly". He then runs
it live on gold: candle 2 closure, CISD present, therefore bearish for the day. He also gives the
negative branch: if there is no daily C2 you either do not trade, or you trade a reversal day,
which needs a different framework — and in the New York session that reversal day is entered off a
**15-minute** CISD rather than the hourly one. He says a video on it is coming; it is not in this
unit.

**The session→timeframe map, drawn on screen.** Asked "1-hour 5-minute model for New York AM?" he
draws the whole table: Asia is daily/H1 or H4/M15; London is any of those or H1/M5; New York a.m.
is H4/M15, H1/M5, or 30-minute/3-minute. He then draws an axis and states the governing principle —
volatility rises down that list, and as volatility rises you are permitted a smaller timeframe;
when volatility is low, use a higher one. This is the closest thing in the corpus to a rule for
*choosing* the execution timeframe rather than asserting a favourite.

**Kill zones rejected, with the replacement argument.** "Do you consider kill zones? No. I just
trade within the higher time frame candles." The reasoning is drawn out: a 5-minute trade is always
inside an hourly, inside a 4-hour, inside a daily candle, so the question is whether those have
already expanded and whether they align to one target — not which session block the clock is in.
Note the tension: he rejects kill zones in the same stream where he gives a session-indexed
timeframe table and watches 9:30 / 10:00 closely.

Also here: the refinement cascade shown step by step (new 4-hour candle at 10:00 → the 15-minute
fair value gap is the point of interest → that gap is the 5-minute swing low → go to the 3-minute
and use 0.5 of it as the line price must not breach, with SMT confirming); the one-trade-per-day
rationale ("if you give them two trades, they will break all their rules"; every trade is another
exposure to your own weaknesses; moving a student from 1-minute to 15-minute entries fixes
impulsive re-entry because the setup now takes an hour); and, uniquely useful for a gold project,
the correlated-asset answer — a viewer insists you need silver for gold and he replies that he
generally uses **gold-euro and gold-pound**, and that he only looks at futures.

### Concepts introduced or answered

- Daily bias = daily C2/C3 closure + H1 CISD; no-C2 fallback = reversal day (15-minute CISD in NY).
- Asia / London / New York timeframe pairings; volatility ↔ timeframe inverse rule.
- Kill zones rejected in favour of "which higher-timeframe candle am I inside".
- Gold's correlated assets = gold-euro, gold-pound (not silver). Charts as CME `GC1!`.
- Refinement cascade 4H → 15m FVG → 5m swing → 3m, using 0.5 of the swing.
- One trade per day, with the psychological rationale and the 15-minute-entry remedy.
- Reduce a stop by "entering closer to your invalidation" (**contradicted in `X4XSsv5CNqg`**).
- 2R as the working minimum ("because I trade, I need 2R"), and refusing a trade where 2R is
  unreachable without dropping to a 1-minute swing point.
- Do not trade below the target / after the objective is hit (said of gold and of oil).
- "Invalidation trade" named in passing as a thing you may take toward a failure swing.
- T-spot used as the area where the daily wick should form; he redirects a viewer without the
  indicator to the EQ / equilibrium material instead.

### Asked and dodged

- "What's the ideal framework for the fractal model?" — deferred to an unreleased video.
- "How do you tell whether SMT is real or fake?" — no test given; "you really just got to wait for
  price to react around that level".
- Order flow, DR concept, "first presented" tools, midnight open, quarterly theory — each gets a
  flat "I don't use it / no opinion".
- "How would you detect the delivery?" and several indicator questions — he says he does not know
  what the asker means.

---

## `X4XSsv5CNqg` — New York Open Live Q&A (4757s)

### What is actually taught

The most complete single-day case study in the unit, and it contains the two most mechanical
answers in the whole unit.

**Bias by proximity.** He opens by pulling up a tweet: "Gold bias. Are we closer to previous
month's low or previous month's high?" He measures both distances on screen, the low is far nearer,
and that is the bias — and he says it can be carried for the whole month until that level is taken,
after which you watch the reaction there. This is a complete, decidable bias rule that needs no
candle reading at all, and I have not seen it stated anywhere else in the corpus.

**The invalidation trade.** This is the day's actual framing and he reads it off his own published
graphic, then matches it to the live hourly. The setup was a *valid bullish* model — candle 2
closure, change in state of delivery, SMT, expansion — which should have produced a small wick and
then expanded. Instead price opened, dumped below the EQ of that structure, and did not reclaim it.
His stated test: "if price closes below that EQ on the aligned time frame and fails to reclaim it,
that's failure", and the consequence is to expect expansion toward the opposite liquidity, usually
via a retracement into a fair value gap. He then executes exactly that shape: consolidation swept,
its high used as resistance, target previous day low — "it's the exact graphic, like literally to
the T almost."

**The clock.** Repeatedly and with numbers: the volatility comes 9:30–10:00; he wants the opening
move 9:30/9:40 to 10:00; 9:45 is a take-profit area; 10:00 is the final TP because it is
simultaneously the end of a 4-hour, a 1-hour and a 30-minute expansion candle; after 10:00 "we
don't really care". He also explains why he did not simply sit on the 15-minute — if the move
completes inside one 15-minute candle, waiting for its close means not being in it — which is the
volatility rule from the previous stream applied live.

Smaller but concrete: he does not fade the daily candle ("I don't prefer to counter the daily
range", "I just like to align with the daily chart"); he does not trade the lagging asset; stops go
"on the high or above the bodies"; entries are **market orders**, never stop orders ("I always just
market order"); ADR is eyeballed, not an indicator, and he thinks ATR is probably the same thing;
and he is explicit that he has no ambition to be right all day — once the move is taken or missed,
he is done.

### The internal contradiction worth recording

Same viewer question, two streams, two opposite answers:

- `W7Fu3Rx5iMs`: "How to reduce the stop loss size? — you enter closer to your invalidation."
- `X4XSsv5CNqg`: "How do you reduce the stop loss size? — you just change your position size. You
  keep your stop loss."

They may be answering different questions (point distance vs dollar risk) but neither transcript
says so, and the viewer's wording is the same both times. Recorded as `contested`.

### Asked and dodged

- **"If you had a fresh 150k funded, how much would you risk per trade?"** — refused and handed
  back: "the question you have to answer for yourself is how many trades do you want to take before
  it's blown up if you lose every single time in a row." No percentage anywhere in this unit.
- "Now something like this where the bar didn't close, did you wait for retest or enter?" — "that's
  up to you and how confident you are… That's not what my streams are for."
- News days (CPI/NFP/FOMC): "Nothing changes for me" — and the surrounding sentence is garbled.
- Backtesting: "I don't really care about the backtesting personally."
- Quarterly theory, silver bullet, box setup, supply/demand, anchored volume profile, rejection
  blocks — all declined without opinion.

---

## `c7nk7ypJHN4` — New York Open Live Q&A (3395s)

### What is actually taught

The no-trade stream, and it is the most instructive of the four about *refusal*. He says some
version of "there's no framework for me today" perhaps a dozen times, on a day where he can name
the direction he favours and still will not take it: "You can be right about the direction on
something and not trade it." A viewer describes his own method as checking a higher-timeframe fair
value gap plus a candle 3 closure, and gets the correction that runs through all four streams:
"you're just pattern trading it… you still got to have some idea of what you want to see price do."

Two genuinely new mechanical answers appear here.

**Why a point of interest matters more on the hourly than the 4-hour** — argued from candle
density. "The 4 hour there are six candles in the day. A lot of times you're not going to have a
point of interest… Hourly there's 24 hours in a candle like in a day, so you're going to want a
point of interest here because you have so many candles." His preference is a POI on both daily and
4-hour, accepting that it does not always happen. Plus the general gate: "You generally need a
point of interest… for a model to form."

**Separation, with a number.** Comparing the same structure on two instruments, he measures 400
points between the two lows on NASDAQ and calls that good separation and the preferred structure;
on ES the same two lows sit close and it is "less ideal". Asked later why a particular low was
marked and not the one further left, the functional test comes out: "It has enough separation to
here that this could have remained while that goes there." Still no threshold, but it is the first
instance in the corpus with a measured distance attached.

Also here: an average daily range figure — a 300–400 point NQ day is "fine for an average daily
range"; the 50%-of-wick rule applied live with a speed condition ("respect 50% of this wick and
kind of do it rather quickly", with the next candle forming its low in the upper half, then closing
over); the asset-selection logic (wait for the stronger asset to reverse before trading the weakest;
ES is "just the cleanest" when the ranking whipsaws; ES leading is off-pattern and has happened
"three or four days out of the past month"); a full 1-minute scalp walked through as C2 → C3 →
C4 out of a fair value gap, immediately followed by his refusal to trade that way ("I used to in
2022 just trade like this all day long. It's just exhausting"); and the swing-trading answer — if
he swung, he would use the daily and hourly, ride an intraday move onside, and hold to daily targets.

### Asked and dodged

- "Once you have a daily bias, do you strictly follow the time alignment plan?" — **"Personally, no.
  I'm just going to find highs and lows to trade away from… If you need the mechanical plan, you
  can do that. I personally don't."** This is the clearest anti-mechanisation statement in the unit.
- "What are your rules for framing ideal IOD?" — "I don't use that. I don't have rules for that."
- "Is the hourly or 4-hour better for your framework?" — "it doesn't really matter. Whatever you
  find works for you."
- Two-stage CIC, rejection blocks, second-chart entries — declined.

---

## `U4j-fZD-FJk` — New York Open Live Q&A (5019s)

### What is actually taught

The only stream with a live trade, and the only one with a disclosure that changes how the other
three should be read.

**The trade.** Pre-open he has no clean daily framework and says so; what he does have is SMT on
the previous day high between NQ and ES, and a preference for the downside. He waits for 9:30, sees
NQ (the strongest) reverse off its high, takes ES because it is the middle asset and will not
whipsaw him the way the outer two do, drops from the 15-minute to the 5-minute for the closure
(because the 3-minute is "sloppy"), enters short — as **SPX 0DTE puts** (this one entered just out of the money and worth ~$1,000 a
contract, though he says his general practice on SPX 0DTE is to pick at the money so theta cannot
punish a timing miss) — scales at the first target and exits fully well before the deeper low,
explaining that he will not give back 13 points to chase 1.5. He recaps it top-down twice on air. The target-selection reasoning is the
transferable part: he targets the nearer low rather than the deeper one because the deeper one sits
behind a **protected swing** ("it's going to be a lot harder to get to this low"), and he draws the
expected reaction zone by taking the bodies of the relevant candles and eyeballing 50% of them.

**The disclosure.** He states plainly that he is long stocks/ETFs from a marked yearly imbalance,
DCAs into six instruments every day automatically, and therefore "I have long exposure, so I'm more
favoring downside in terms of hedging myself" — the same admission appears in `c7nk7ypJHN4` ("I'm
more inclined to trade short because it hedges my position"). Anyone treating these streams as a
signal source needs this: some of his stated intraday direction is book management, and he says so.

**The CISD-count answer.** A viewer asks whether trading C4 after a C3 closure requires C2 and C3
each to have a CISD. The answer is precise and, as far as I can tell, not stated this cleanly
anywhere else: "You just need a CISD from the swing point… You don't need a CISD in here and in
here. You just need one to confirm the swing low. So it's just in the C2." One CISD per sequence,
and it belongs to the candle 2.

**The pre-open gate.** Asked whether he would enter before the New York open on a confirmed setup:
only on a valid **15-minute** setup, and only with "a protected swing I can trust prior to the
open" — usually not on a lower timeframe. Stated negatively the same day: "there's nothing to base
my stop off of", therefore wait for the open.

**News.** There is a release at 10:00 and he says he does not care for it: "news lately based off
how the market's trading just doesn't care… even NFPs barely been reacting." Against that, in
`X4XSsv5CNqg` he attributes his own inaction on gold to "I was waiting for NFP" — so the unit
contains both a stated no-op and observed deferral, and I have recorded it as contested.

Also here: the reason 9:30 matters at all — "the reason is the New York stock market opens" (see
the timezone note below); a rejection of the word "decoupled"; the win-rate answer ("I wouldn't
worry about trying to add winners… what can you do to remove the losing trades"); the
entry-model-doesn't-matter statement ("it's really not that important. It's about the higher time
frame framework"), demonstrated by offering to reframe the same trade as an IFVG; and the origin
story of the model — "I learned swing points", chose which swing points to focus on (C2/C3
closures), then worked out how to confirm them lower and make the entry mechanical.

### Asked and dodged

- "Please do a video on how to react at 9:30 open" — **"that just comes with time and experience.
  There's not a video that's like you needed to do this."** An explicit refusal to mechanise the
  most-requested part of his process.
- "Please describe entry logic" — "the entry logic is I think it's going lower and we have an SMT
  up here, a candle closure. So I just enter."
- "Should I have waited for this M15 closure before taking a short?" — "It depends."
- Silver bullet ("I just don't have any opinion"), IPDA (redirected to phases of price), support
  and resistance ("I don't use that, so can't make a video on it").

---

## Cross-video observations

- **The timezone question, and how close this unit gets.** No timezone label — ET, EST, New York
  time, UTC — is spoken anywhere in these four transcripts. But two statements together pin the
  clock tighter than anything I have seen elsewhere in the corpus: (1) he uses 9:30 as *the* open
  and, asked why that time changes behaviour, answers "the reason is the New York stock market
  opens" — which is 9:30 **New York time** by definition; and (2) "here we got 10:00 a.m. What does
  that mean? We got a new 4-hour candle", corroborated by "end of a 4-hour expansion, end of a
  1-hour expansion, end of a 30-minute expansion" at 10:00 and by "the 4 hour there are six candles
  in the day". So the displayed clock is New York time and its 4-hour grid has a boundary at 10:00
  (implying 02:00 / 06:00 / 10:00 / 14:00 / 18:00 / 22:00 on a six-candle day). The boundary at
  10:00 is *stated*; the full grid and the ET label are *inferred* — recorded as ambiguities in
  `new-york-intraday-time-levels` and `time-based-exit-htf-close`, not as detection rules.
- **Numbers actually spoken in this unit** (rare enough to list): 2R minimum, and an explicit
  refusal of 1:1 ("I don't trade a one to one"); one trade per day; 400 points as "good separation"
  on NASDAQ; 300–400 points as a normal NQ average daily range; the 9:30 / 9:45 / 10:00 clock for
  the opening move; six 4-hour candles per day, ~24 hourly; and ES-leading
  days at "three or four out of the past month". No risk percentage, ever — that question is
  explicitly refused.
- **The process is deliberately not mechanical, and he says so twice.** "Once you have a daily
  bias, do you strictly follow the time alignment plan? Personally, no." And "there's a difference
  between being mechanical with something and just kind of giving what taking what the market has."
  Anything built from this unit is building a *filter set* he uses, not the decision procedure he
  runs.
- **One gate runs through all four streams and it is not a pattern.** Before anything is tradeable
  he requires a higher-timeframe framework — a bias plus a level to trade away from. Every refusal
  in the unit reduces to its absence, and every correction to a viewer reduces to them having a
  pattern without one.
- **His live bias is not always model-derived.** The hedging disclosure in `U4j-fZD-FJk` and
  `c7nk7ypJHN4` is the caveat to attach to any dataset built by scraping his stated intraday
  direction from these streams.
- **Terms used but never defined in this unit** (assumed from the model playlists): candle 2 / 3 / 4
  closure, CISD, protected swing, failure swing, fair value gap, inversion FVG, order block, SMT,
  T-spot, EQ, phases of price, point of interest. Only the daily-bias formula, the invalidation
  test, the CISD-count rule and the session/timeframe map are spelled out here from scratch.
