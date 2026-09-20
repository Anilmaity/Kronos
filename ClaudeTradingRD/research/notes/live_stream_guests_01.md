# Unit notes — `live_stream_guests_01` (playlist: "Live Stream Guests", batch 1)

Four live-streamed guest sessions from 2022. TTrades hosts, reads the chat and relays audience
questions; the guest screen-shares and does most of the talking. Unlike the Weekly Profile or
Fractal Model playlists, **almost nothing here is the channel's own method** — each episode is a
different trader with his own vocabulary and, in two cases, mutually incompatible rules. Every
concept file from this unit therefore carries an explicit `voice`, and the handful of `ttrades`
entries are the ones worth the most: they are TTrades stating his own practice in 2022, sometimes
in ways that cut against what the channel teaches later.

All four transcripts are auto-generated captions with **no timestamps and no speaker labels**.
Consequently **no `approx_time` is recorded anywhere in this unit**, and in the two places where a
claim sits on a turn boundary the attribution is flagged in that file's `ambiguities` rather than
guessed.

Guests, one per video:

| video | guest | one-line method |
|---|---|---|
| `UmLWRlXd_V8` | **$niper** (introduces himself as Matt) | ICT market-maker sell model; the second distribution leg is the trade |
| `eK_6wgNpNh0` | **Finessee_Fx** | four PD arrays drawn wick-to-body, on every timeframe, with no structure trigger at all |
| `wCtxmWe4KNc` | **Trader T** (the transcript calls him Kristen / Tristan) | replay backtesting; hourly sweep → 5-minute break → limit → fixed 2R |
| `yRmKkR4CojU` | **Ben** (introduces himself as "Ben TT") | fractalising a higher-timeframe idea down to a 1-minute execution |

---

## Transcript hygiene

These four are noticeably worse than the solo-teaching playlists, because two speakers talk over
each other and the guests use jargon the captioner has never seen. The corruptions that actually
affect claims:

**"order block" → "water block"** (and once "older block", once "wall blocks"). This runs right
through the Finessee_Fx transcript and is unmistakable from context, but it means one of his
verbatim quotes — the two-consecutive-bullish-candles rule — reads "that creates the water blocks".
The quote is recorded as spoken, uncorrected, in `fair-value-gap`.

**"fair value gap" → almost anything**: "for Value Gap", "fair value cap", "fair value yet", "fair
value you got", "farewell yups", and in Ben's transcript "feg", "fpg", "fpc" and "fiji". Nothing is
lost semantically but no quote containing the phrase can be taken from Ben's transcript in clean
form, which is why his `fair-value-gap` and `balanced-price-range-revisit` quotes carry "fegs".

**"sells" → "cells"** throughout $niper's speech ("anticipation of cells", "I'm not looking for
cells underneath the 830 open"). Affects the quote in `midnight-open-directional-filter`, recorded
as spoken.

**"take profit" / "TP" → "ITP", "TV", "TB"**. Both quotes in `cancel-limit-after-target-run` and
one in `partial-profit-taking` contain the corruption. In each case the surrounding sentences make
the meaning certain.

**"smart money reversal" → "smart mini reversal", "smarmy reversal", "more money reversal"**, and
at its worst the audience question "for smart money reversals what are the key levels" is rendered
"for smart runny versus whole habit has occurred". No quote was taken from any corrupted instance.

**"SMT divergence" → "type urgency"** in video 2 ("can we talk about um some Divergence real quick
… so type urgency"). The whole SMT segment survives only because the worked example is
unambiguous; the quote used in `smt-divergence-confluence` is taken from a clean sentence.

**Names**: Finessee_Fx is rendered "Vanessa effects" and "Vanessa's socials". Trader T is called
"Kristin", "Kristen" and "Tristan" in the same video, and the video title says Trader T — the guest
is named in the concept files as **Trader T** with the variants noted here. Ben names himself "ben
tt". **"MyForexFunds" → "my 4x1"**, which is why only his FTMO 400k figure is attributed with
confidence in `prop-firm-drawdown-sizing`.

**Tooling**: "soft4FX" appears as "soft FX", "soft.fx", "soft effects", "soft defense", "soft fax";
"backtesting" as "bath testing"; "prop firms" as "Proverbs", "prop terms" and "proves". These are
cosmetic.

**Two garbles that change a number.** Trader T's stop ceiling is transcribed "anything over your
boat 13" — the intended words are almost certainly "anything over, you're about 13", so the 12–13
pip ceiling in `stop-size-reduction` is approximate as spoken and is flagged there. And his
journaling line is "I think attacking the losses are way more important than the wins", where the
word is plainly *tracking*; the quote is recorded verbatim in `journal-losers-only` with the note.

Also worth recording as **negative** hygiene findings, because they are known artifacts elsewhere
in the corpus: the "candle 2" → "candle to" corruption does **not** occur here (no fractal-model
vocabulary is used by any of these guests), and "reach" → "wretch" does not occur either. Smaller
ones observed: "raided" → "rated" (Ben), "purge and revert" → "persian revert" / "norvert",
"OTE" → "OT" / "oce" / "ot fiji", "PD array" → "PDA" / "pdra" / "PD Ray" / "p array", "Nasdaq" →
"NASA work", and a profanity rendered as "I don't folk with" — which happens to sit inside the
single most important sentence Finessee_Fx says, so the quote in
`trading-without-structure-shift` is recorded exactly as the captioner produced it.

---

## $niper | 8/14/22 MMXM Live — ICT concepts
(`UmLWRlXd_V8`, https://youtu.be/UmLWRlXd_V8, 3755s)

**Guest: $niper (Matt).** He trades one thing — the ICT market maker *sell* model on indices — and
his whole method is a single left-to-right sequence ending in a second distribution leg he calls
the silver bullet.

Roughly a third to 40% of the hour is non-technical: self-introductions, screen-blur troubleshooting,
a TradingView how-to on saving drawing templates, a walk through his Notion journal and a promise to
credit whoever made the template, cross-promotion of his YouTube channel, and two separate
"we're not financial advisors" disclaimers. The teaching is concentrated in the first twenty minutes
and in the answers to about eight audience questions.

### What is actually taught

The model is drawn once, on a schematic, and then hunted on live charts. Left side of the chart:
an original consolidation, then a push up into a premium array — a previous daily high, a
higher-timeframe fair value gap, or plain buy-side liquidity. **The first thing you do on any MMXM
chart is decide which side of the curve you are on**; everything else follows from that. Where the
premium array is taken, he marks a grey box for the smart money reversal, but is careful that an
SMR is not simply a high being taken: the reaction after the sweep is what confirms it, and he
rejects a candidate on air for being "just a random High". Then the first aggressive drop is the
market structure break, the retracement into an OTE fair value gap is the first entry, the break of
the retracement's low is the break of structure, and the **second distribution leg** is the trade
he actually wants — "the second leg is the most the highest probability trade entry", the
confirmation that the sell-side lows will be taken.

Two location filters sit on top. First, a hard premium/discount gate: he does not take a short
unless price is above equilibrium of the fib drawn high-to-low on the retracement leg. Second, the
midnight and 08:30 opening prices — below both is "deep discount" and he will not look for sells
there at all; above both is deep premium and he expects a retracement. He frames the second as a
risk-to-reward device rather than a directional one: it stops you selling the bottom.

He identifies the original consolidation by session rather than by structure — Asia's price action,
Asia's lows, and the previous daily lows sitting together in a stretch of chop is the accumulation
block, and Asia's extremes are liquidity engineered to be taken later. He also relays an ICT
frequency claim he trades off: a higher-timeframe curve (weekly, daily, 4-hour) gives **two**
opportunities to enter before the premium array is reached, anything lower gives **one**.

Management is fixed: always take partials, first TP around 2:1 at the nearest structural low to the
left, stop to break even, leave about 20% running — and in the sell model the stop is pulled down
to sit exactly where the second-leg entry is, so the second entry is pre-covered.

**TTrades' own contributions in this video are substantial and belong to him, not the guest.** He
walks his own Friday NASDAQ short (chosen because NASDAQ was the weaker index and "barely tapped
into these highs"), a 15-second-chart entry that got stopped out on a 15-minute divergence, and
answers two audience questions himself. The most useful is his test for whether a break is real:
displacement must leave a fair value gap, and — the diagnostic version — if the up-legs on the
chart contain no fair value gaps then there is "no aggression so there's no reason to be bullish".
He also sketches the coming week as a weekly power of three (open, high on Tuesday into a daily
order block, then Wednesday–Friday lower to ~4150), explicitly not caring what Monday does. Two of
his asides are recorded because they contradict the channel's later doctrine: he says he takes
**two to three trades a day** and admits over-trading the 15-second chart, and he says that when he
is trading a 15-second chart he does not care what the monthly is doing.

### Concepts introduced (speaker's own terminology)
- "buy side of the curve" / "sell side of the curve"; original consolidation
- smart money reversal, requiring a reaction — not just a high being taken
- second distribution leg = "silver bullet" (purely structural; no time window)
- OTE fair value gap; premium/discount gate on every entry
- "deep discount" / "deep premium" via the midnight and 08:30 opens
- two-opportunities (HTF) vs one-opportunity (LTF) before the premium array
- protected highs at the shift and at the break of structure
- mitigation of the trade: partial at 2:1, stop to the second entry, 20% runner
- journaling *feelings during the trade* as a first-class column

### Rules / conditions stated
- Classify the curve side before anything else.
- SMR requires liquidity taken **and** a reaction; a random high does not qualify.
- Market structure break → retrace into an OTE fair value gap or order block → break of structure
  → second distribution leg (the preferred entry).
- No short unless price is above equilibrium of the retracement leg's fib.
- No sells below both the midnight and 08:30 opens; no buys above both.
- Entry requires an identified liquidity objective (previous daily low, session lows, relatively
  equal lows, trendline liquidity) to exist first.
- Displacement must create a fair value gap; a small wick through a low followed by an aggressive
  move back is a liquidity grab, not a break.
- Always take partials: first TP ≈ 2:1, stop to break even, ~20% runner.
- Maximum two losses in a session/day (−2R); target one trade per session.
- 1% risk per trade (stated as personal practice, with a disclaimer).
- Entries must fall inside kill-zone times.
- **TTrades:** two to three trades a day; risk the exact same amount every trade; the monthly is
  irrelevant on a 15-second chart.

### Examples walked through
- The schematic market maker sell model, drawn before the stream.
- A 15-minute chart used to identify an original consolidation from Asia's lows plus previous
  daily lows.
- A **daily** market maker sell model on the index: relatively equal highs as the buy-side draw,
  two daily fair-value-gap taps counted as the two HTF entry opportunities, then the objective.
- A live drill-down inside that daily model to the 4-hour, finding the MSS, the OTE fair value gap
  and the break of structure in sequence.
- TTrades' Friday NASDAQ short: relative weakness vs ES, a 15-second fair value gap entry after
  equal lows formed, stopped out on the 15-minute divergence; used to make the point that the
  up-moves contained no fair value gaps.
- TTrades' forward sketch of the following week as an open-high-low-close weekly candle.
- A weekly-chart read: price retraced into a weekly OTE fair value gap above the 0.62.

### Quotes (verbatim, transcript-checked)
- "identify whether you are on the buy side or the sell side"
- "the second leg is the most the highest probability trade entry"
- "I don't take a short unless price is above equilibrium"
- "no fair value gaps no aggression so there's no reason to be bullish" *(TTrades)*
- "trading a 15 second chart I don't really care what the monthly is doing" *(TTrades)*

### Open questions / ambiguities
- "Wait for the reaction" is the entire SMR confirmation test and is never quantified.
- "Silver bullet" is used with no time window at all — it is simply the second leg.
- The two-opportunities claim is relayed as ICT's, with no sample, instrument or period, and
  "opportunity" is only implicitly defined (a tap into a same-timeframe fair value gap).
- The original-consolidation procedure ("a form of chop and consolidation") has no bound of any
  kind — no candle count, no range width.
- No timezone is given for the midnight and 08:30 opens.
- The displacement exchange sits on a turn boundary: the captioner gives no speaker labels, so
  which of the two men said which half is inferred. Both state the fair-value-gap requirement in
  adjacent turns and agree, so the file is marked `voice: mixed` with the uncertainty recorded.
- TTrades' frequency and timeframe statements are August-2022 statements from a trader about a
  year in; they are recorded as spoken and deliberately not reconciled with the later doctrine.

---

## Finessee_Fx | Advanced ICT Directional Bias Teachings
(`eK_6wgNpNh0`, https://youtu.be/eK_6wgNpNh0, 3210s)

**Guest: Finessee_Fx.** The most disciplined and the most idiosyncratic of the four — he uses
exactly four PD arrays, draws every one of them wick-to-body, applies them identically from the
monthly to the 1-minute, and rejects market-structure analysis outright.

This is the most content-dense video in the unit; perhaps 15% is non-technical (introductions, his
admission that this is his first appearance on someone else's channel, some chat about whether
"forex is going to die", and the sign-off). Almost the entire hour is chart work on AUDUSD, EURUSD
and NASDAQ.

### What is actually taught

He types the list out before touching a chart: **order blocks, breakers, fair value gaps, and old
highs and lows** — with fair value gap, liquidity void, buy-side imbalance and sell-side imbalance
all treated as one thing. "I'm using those four to five Concepts I never deviate from that", and he
uses them on every timeframe. Standard-deviation projections are explicitly excluded.

The signature mechanic is the **wick-to-body zone**. He does not use the whole candle and he does
not use its 50%: he draws from the candle's wick extreme to its body edge and extends that band
forward in time, for order blocks *and* for breakers. Challenged on it twice from chat, he gives an
empirical answer rather than a theoretical one — over years he found that band to be the most
sensitive part of the candle, and, decisively, it gets him filled. He places limits *slightly
before* the zone is reached for exactly that reason, trading a worse price for a certain fill, and
he only goes deeper (towards equilibrium) when dissecting the block on a lower timeframe reveals a
nested array. Stops always go beyond the order block, and a violated order block is simultaneously
the stop-out and the signal to flip the bias.

Three structural claims carry real information. First, **the smart money reversal always happens at
a higher-timeframe PD array** — stated three times, and used to locate reversals rather than to
confirm them. Second, price **stops shy of the intended level and engineers liquidity first**: nine
times out of ten it will consolidate below/above the marked array, build stops, and only then spike
into it. He is explicit that he does *not* want the next candle to rally straight into a weekly
order block and turn, and that sitting through July's EURUSD chop cost him a couple of losses he
should not have taken. Third, the **curve mirror**: a bullish order block that held on the left side
of a swing reappears as a *bearish* order block inside the same band on the right side, because the
positions accumulated there have to be offset. He demonstrates this candle by candle down a daily
NASDAQ swing.

The most surprising answer of the unit comes when he is asked what a market structure shift means
to him: "I don't folk with Market structure breaks I don't ever … I just trade the raw price
action … I stick the one bias until I'm proven wrong". There is no confirmation trigger in his
model at all — arrival at the array *is* the trigger.

On SMT he warns against the exact habit the corpus's other guests practise: hunting divergence on
the 1-minute and 5-minute all day is how you get burned, and he demonstrates SMT on a **weekly**
candle instead. On the dollar he runs a straightforward gate — DXY bullish all year, therefore
foreign pairs lower, therefore shorts only.

### Concepts introduced (speaker's own terminology)
- the fixed four-array toolkit; "I never deviate from that"
- wick-to-body demarcation of order blocks *and* breakers; "the most sensitive price points"
- limit placed slightly early, for fill certainty over price
- "dissecting a candle" — going inside an array for a nested array
- smart money reversal located by higher-timeframe PD array
- "stop shy" then "engineer more liquidity"
- left side / right side of the curve; offsetting old positions
- fair value gap measured across two merged same-direction candles
- PD arrays as "ping pong" between opposing premium and discount arrays
- explicit rejection of market structure breaks and of projections

### Rules / conditions stated
- Only four arrays are ever used, on every timeframe; higher timeframe = more relevant.
- Draw every order block and breaker wick-to-body and extend forward indefinitely.
- Place limits slightly before the zone; take market orders only when awake for the session (he is
  US East Coast, so London is 03:00 for him).
- Stops always beyond the order block; a violated block flips the bias.
- Bearish breaker = the last down-close candle before two consecutive aggressive bullish candles
  that run stops; confirmed on the close back below. Mirror for the bullish breaker, which must
  also fill an imbalance on the decline.
- The smart money reversal is always at a higher-timeframe PD array.
- Expect price to stop shy of the intended level, consolidate, engineer liquidity, then spike in.
- A gap is only efficient when *fully* closed; merge two consecutive same-direction candles and
  span the gap across both.
- Left-curve bullish order blocks become right-curve bearish order blocks in the same band.
- Do not require a market structure break. Hold one bias until an array is violated.
- Do not hunt SMT on the 1-minute and 5-minute.

### Examples walked through
- **AUDUSD monthly**: a monthly bearish order block blended with a monthly bearish breaker; the
  reaction; the target set as old lows plus an unfilled buy-side imbalance inside one candle; the
  same levels shown holding on the weekly and then producing a 4-hour breaker and a 4-hour market
  maker sell model whose SMR sits exactly on the monthly zone.
- **EURUSD** July–September: the consolidation that stopped shy of the sell-side imbalance; the
  pop into premium; the market maker sell model whose reversal is the imbalance; the daily breaker
  that turns out to be the **monthly high of September**, shown on the monthly chart; and the
  weekly order block with its own fair value gap that price filled before reversing.
- **NASDAQ daily**: the curve-mirror walk — a vertical divider at the reversal, left-side bullish
  order blocks extended forward, and the matching bearish blocks forming inside the same bands on
  the way down, ending in a "low resistance liquidity run" of successive lows.
- **Weekly SMT**: EURUSD filled its weekly gap and hit its weekly order block while DXY never
  traded below its low, never hit its block and never filled its gap.
- **A bullish breaker found live on request** on USDCAD: a false break below, stops taken, the
  imbalance filled, the break above, and the resulting breaker holding twice afterwards.

### Quotes (verbatim, transcript-checked)
- "I'm using those four to five Concepts I never deviate from that"
- "I go from the wick to the body and extend that out in time"
- "the smart money reversal is always going to happen on a higher time frame"
- "it's always going to stop shy before the main intended level is hit"
- "I don't folk with Market structure breaks I don't ever"

### Open questions / ambiguities
- "Aggressive" is never quantified anywhere — not for the breaker's stop run, not for displacement.
- "A little bit before the order block" (the limit offset) has no distance attached.
- "Violated" is never defined as a wick or a body event, which matters because it is simultaneously
  his stop rule and his bias-flip rule.
- The nine-out-of-ten figure and the "most sensitive" claim are both years-of-experience assertions
  with no sample.
- The curve-mirror is shown on exactly one daily swing and asserted to generalise to the 15-minute.
- With no structure trigger, nothing in his model distinguishes "price arrived at the array" from
  "price is about to go straight through it".

---

## Trader T | Back Testing Live Session
(`wCtxmWe4KNc`, https://youtu.be/wCtxmWe4KNc, 3920s)

**Guest: Trader T** (the captioner writes Kristen / Tristan). Five years in, eight months full
time, funded ~700k across two prop firms; the session is a live replay-backtest of January 2021
EURUSD, narrated trade by trade.

**This is by far the most non-technical video in the unit — well over half.** The prop-firm
discussion, Canadian tax residency and LLC question, travelling and trading from Thailand, his
account-blowing history, how many hours he backtests, and a long stretch of soft4FX installation
and platform mechanics take most of the runtime. The actual method is stated compactly and then
demonstrated on about eight trades, of which several lose — which is the video's real value.

### What is actually taught

The strategy is one sentence: an **hourly sweep** of a high or low, then a **break of structure on
the 5-minute** measured against the *relative (fractal) low that existed prior to the sweep* — not
the low the sweep itself made — then a limit order back into the resulting block, targeting a fixed
**2R**. He pads the order to about 2.2R so the spread does not deny the fill. On EURUSD the stop
must be about 12 pips; much beyond 13 and he moves the *entry* deeper rather than moving the stop
in. When SMT is present he drops to the 5-minute and moves the stop to break even at 2R —
the only rule in the unit its speaker explicitly says he backtested.

The rule most worth automating is the abort: **if price runs to where the take-profit would be
before the limit fills, delete the order.** He states he has logged many such cases and in most of
them the eventual fill goes on to hit the stop, and he demonstrates it twice in the session — both
abandoned entries would have lost.

Around this sit his session windows (roughly 07:00–10:30 and 12:30/13:00–15:00 on his platform's
server clock, anchored by server 08:00 = London open = 03:00 Eastern; nothing after ~15:40), his
two-loss daily stop for live trading, and his sizing: 1% in the simulator, **0.5% per trade on
funded accounts**, pushed to 1% during a challenge, averaging 3–7% a month. His strike rate on the
2R strategy is "58 to 65 percent", averaging ~58, ranging 45 to 80 by month — and he argues at
length that an 80–90% expectation is fantasy and unnecessary.

The backtesting doctrine is the part he repeats three times, and it is behavioural: the failure
mode of replay software is spamming through bars. Move bar by bar, plan the trade, execute it, and
watch the fill — because the behaviour you practise is the behaviour you will have live. He journals
every loss with screenshots of four timeframes and treats winners as optional, and shows the payoff
live: a previously logged loss keeps him out of an otherwise identical setup later in the session.

TTrades' one substantive contribution is a risk framing in his own words, delivered right after
Trader T's "you only actually have 10 to play with": a $25,000 prop account with a $1,500 drawdown
is treated by most people as a $25,000 account "when in reality it's a fifteen hundred dollar
account".

### Concepts introduced (speaker's own terminology)
- hourly sweep → 5-minute break of structure → limit at the block → fixed 2R
- the **relative / fractal low prior to the sweep** as the structure reference
- delete the pending order once price has run to the target
- 12-pip stop ceiling on EURUSD; tighten the entry, never the stop
- SMT present → 5-minute entry + break even at 2R
- two losses and the day is over
- 0.5% funded / 1% challenge sizing; the drawdown *is* the account
- "treat it like it's live" as the backtesting rule
- journal losers exhaustively, winners loosely

### Rules / conditions stated
- Trade only inside his two session windows; stop about 15:40.
- Verify the platform's server clock against a live chart before trusting any session time.
- Entry: hourly sweep, 5-minute break of structure vs the pre-sweep relative low, limit at the block.
- Target a fixed 2R, ordered at ~2.2R for spread.
- Stop ≈ 12 pips on EURUSD; beyond ~13, move the limit deeper instead.
- If price reaches the target price before the limit fills, cancel the order.
- With SMT present: 5-minute entry, stop to break even at 2R.
- Two losses in a live day = stop for the day.
- Risk 1% in the simulator, 0.5% on funded accounts, ~1% in a challenge; do not push risk once
  already past the extension threshold (~5%).
- Log every loss with 4H/1H/5m/1m screenshots, pair, reason, kill zone, R and time.
- In the replay, advance bar by bar and never fast-forward.

### Examples walked through
All on EURUSD, January 2021, in the simulator, plus one live-called trade on gold from the
preceding Friday:
- Day 1: a rejection and sweep into a marked area, sell limit tightened because 2R was too far,
  filled, 2R hit — then a later setup skipped because the lows had already been swept.
- A no-fill: price ran to the target before touching the limit; order deleted; the replay shows the
  fill would have lost.
- A losing short after a 5-minute sweep inside an hourly break — journalled live.
- A skipped buy at 09:25 because the highs had been swept on the previous hourly candle, which he
  uses to show the journal doing its job.
- Two further losses taking the session to −2%, held up deliberately as what a real month looks like.
- Gold, the previous Friday: a 4-hour block plus a gap area, with EURUSD sweeping an hourly high
  inside its own block at the same moment (gold and EUR tending to follow each other), a 5-minute
  sweep and break of structure, entry on the retest, 2R.
- A demonstration of loading SP500 data in the simulator, with the caveat that index data there is
  gappy at the open and close.

### Quotes (verbatim, transcript-checked)
- "take your time treat it like it's live don't just Spam through it"
- "once it runs to my target without fill I usually um I do remove"
- "I really like 2R I find it's just peace of mind"
- "it hovers around 58 to 65 percent"
- "when in reality it's a fifteen hundred dollar account" *(TTrades)*

### Open questions / ambiguities
- "The block" is never defined; it is used for both an order block and a fair-value-gap zone.
- The session windows are on a broker server clock whose offset he says varies by MT4 build, and
  the second window's start is given twice with different values (12:30 and 13:00). His Eastern
  conversion implies a fixed 5-hour offset that will drift across daylight saving.
- The 12-pip ceiling is stated only for EURUSD; nothing is given for gold or the indices.
- "In most cases" (the no-fill rule) has no count, period or instrument behind it.
- The break-even-at-2R rule reads as break-even *at the exit*, and the transcript does not resolve
  whether the stop moves earlier or whether he is describing a partial-and-runner structure.
- Raising risk to pass a challenge is in direct tension with his own "the drawdown is the account"
  logic, and the tension is never addressed.
- His strike-rate figure blends simulated and live results.
- He cannot display DXY alongside a pair in the simulator, so every SMT-conditioned rule he states
  is untested inside his own sample — a fact he mentions in passing without drawing the conclusion.
- Logging only losses means the base rate of the same pattern among winners is never recorded, so
  the avoidance decisions are made on half the sample.

---

## Ben | Fractalizing Entries — Q&A
(`yRmKkR4CojU`, https://youtu.be/yRmKkR4CojU, 4061s)

**Guest: Ben ("ben tt").** Three years trading, five months on ICT material; his lesson is a single
idea — separate the timeframe that *sponsors* a trade idea from the timeframe you *execute* it on —
and it is the most directly automatable framing in the unit.

Perhaps 20–25% is non-technical: the introduction, advice on which ICT course to study first, a
polite but firm refusal to publish his rate of return when a viewer challenges the presentation's
validity, and the sign-off. The rest is chart work on SPX/ES weekly through 1-minute and one NASDAQ
session, plus about a dozen substantive Q&A answers.

### What is actually taught

Every trade has two models. The **sponsorship** model is where the idea comes from — the
higher-timeframe PD array price has arrived at — and it fixes the **target**: "weekly sponsorship
means weekly target". The **execution** model is the same shape (dealing range, structure shift,
fair value gap, entry beyond equilibrium) recreated on a much lower timeframe *inside* that array,
and it fixes the **entry**. The argument is arithmetic and he shows it: the weekly-chart short needs
300–500 points and months of holding to make 2–3R; the same idea taken on the 4-hour reaches 2R in
50 points; zoomed to the 5-minute and then the 1-minute, the same 2.5R comes off a leg starting
halfway through the move. Zooming also multiplies frequency and removes swap, overnight-event and
long-consolidation exposure. He is honest that he could not personally have held the weekly version.

Targets come from the **PD array matrix**, used as an ordered ladder rather than a projection: list
every array between price and the draw and take them in the order price must pass them — fair value
gap first, order block second, liquidity pool third. He states the polarity rule too: below a
bullish order block is sell-side liquidity, the bottom of the bullish matrix; break it and the
matrix inverts and you climb the other way. He does not use standard-deviation projections and does
not use COT data.

The question that produces his best answer is "what is the difference between a market structure
shift and a stop run?" — because locally they are identical, both breaking a swing with displacement
and a gap. His first answer is that you cannot tell without a daily bias and a draw. His second is
mechanical and testable: fib the impulse leg, and if price never returned to its equilibrium the leg
was never balanced, so the extension is a stop hunt, not a swing. He also states the general law
underneath it — price always oscillates from external to internal liquidity — and demonstrates it
across a whole swing.

Everything he takes is gated on the dollar: "if the dollar doesn't agree with my position i am not
interested in it", applied to SPY, NAS and the majors alike, and derived that week from interest-rate
differentials rather than from price. SMT is used but explicitly demoted — "it is not a leading
indication for me … it is a secondary confluence". He prefers breakers and **balanced price ranges**
(which he defines as fair value gaps *already filled* and then revisited, more sensitive in his
experience than untouched gaps) and openly avoids order blocks because he does not read them well —
which becomes a general principle: "don't get married to a p array because somebody else uses it".
Fair value gaps are invalidated by a candle **close** beyond the defending edge, not by a wick.
He scales in, moves the first tranche to break even, and insists on separating win rate from strike
rate for exactly that reason. He averages one to two trades a week even executing on the 1-minute,
and says that is where his best consistency has come from.

### Concepts introduced (speaker's own terminology)
- "sponsorship" vs execution timeframe; "the first model is the sponsorship"
- fractalising a model down until the R works
- the PD array matrix as an ordered target ladder
- balanced price range = a filled fair value gap, revisited
- breaker as "a flipped order block"; mitigation block = no new swing extreme
- candle-close invalidation for gaps and breakers
- the never-balanced-impulse test for a stop hunt
- "deviation from the range" (a large wick beyond a swing)
- secondary shift in market structure (visible only on the execution timeframe)
- the dollar as barometer and veto; risk-on / risk-off
- win rate vs strike rate

### Rules / conditions stated
- Identify the sponsoring timeframe; take targets from it and do not shorten them.
- Recreate the model on lower timeframes until it is clean; execute there.
- Targets = the PD arrays between price and the draw, in traversal order.
- Fair value gap invalidation = a candle close beyond the defending edge; wicks do not count.
- Prefer balanced price ranges and breakers; skip arrays you do not read well.
- The stop goes on the swing that was *not* just raided.
- Do not classify a break as a shift without a bias and a draw; use the equilibrium-balance test.
- The dollar must agree, or no trade — including on indices.
- SMT is a secondary confluence, checked in zones, never a lead.
- Reject 1:1 (it forces break-even at a 50% win rate); take 2–2.5R, prefer 3–3.5R; settle your own
  multiple by logging 20–50 trades at each.
- On scaling in, the first position goes to break even or trails to the second position's stop.
- Trade only in kill zones; he prefers the PM session and accepts missing the AM.
- One to two trades a week is the expected frequency.
- Journal every trade, before and after, including demo trades.

### Examples walked through
- **SPX weekly → 4H → 1H → 15m → 5m**: the weekly fair value gap and weekly order block as
  sponsorship, the 4-hour buy-model-into-sell-model recreation, the dealing range defined by
  buy-side then sell-side being taken, and the same 2R achieved in 50 points instead of 400.
- The swing-high selection question: aggressive (where the move originated) vs conservative, and
  the large wick above it read as a deviation from the range.
- **NASDAQ, the previous Friday**, called in foresight: a 4-hour order block and two liquidity
  pools, an hourly fair value gap to rebalance, a shift on the 5-minute giving a 2.5-to-1 trade with
  a 130-point stop, then the same idea on the 1-minute — a secondary shift invisible on the higher
  timeframe — producing the same 2.5R from a much smaller stop, entered halfway through the move.
- A stop-run vs shift walk-through on the same Friday: equal lows raided into an unmitigated
  inefficiency, rebalanced, then the real shift.
- A weekly order block on the index — the largest down-close candle in the consolidation before the
  energetic rally — used to show a possible buy model forming and a ladder of things inside the gap
  that could be delivered to.
- An impulse/retracement example ending in the equilibrium test that made him bearish, which he
  says he called publicly at the time.

### Quotes (verbatim, transcript-checked)
- "sponsorship is just where the original idea comes from"
- "weekly sponsorship means weekly target"
- "the same r gain in a literal fraction of the time"
- "if the dollar doesn't agree with my position i am not interested in it"
- "this impulse never came back to equilibrium so for me this is a stop hunt"

### Open questions / ambiguities
- Nothing says when to stop zooming in; he goes to the 1-minute in one example and stops at the
  5-minute in another, judged by whether the model "looks clean".
- "Partially mitigated" sponsorship is accepted with no fraction at which it expires.
- The equilibrium-balance test depends entirely on choosing the right dealing range, which he calls
  the prerequisite and then does not specify.
- He warns himself that price may leave from equilibrium without filling OTE gaps, so the test
  grades likelihood rather than deciding the case.
- "Clean enough" is the actual (visual) test by which he rejects an order block on air.
- His balanced-price-range definition is not the overlapping-opposing-gaps definition used elsewhere
  in the corpus — recorded under a separate id for that reason.
- The 20–50 trade sample he prescribes for choosing an R multiple is far too small to separate the
  candidates, and he does not say so.
- He declines to give a rate of return, so the mid-60s win rate is unaudited by his own framing.

---

## Cross-video observations

**1. Almost none of this is the channel's method, and the `voice` field is doing real work.**
Of the 43 concept drafts from this unit, 37 are `voice: guest`, 3 are `voice: ttrades` and 3 are
`voice: mixed`. Anyone filtering for the channel's own doctrine should expect this unit to
contribute almost nothing — which is the correct outcome, not a gap.

**2. Guest-vs-guest difference (NOT `contested`).** Four traders, four incompatible methods. These
are recorded as separate concepts or as separately attributed rules inside one file, never as
channel self-inconsistency:

- *Is a confirmation trigger required?* $niper will not act without a market structure break, and
  Trader T requires a 5-minute break of structure. Finessee_Fx rejects structure analysis entirely —
  arrival at the array is the trade. Ben is in between: he requires a shift but says a shift and a
  stop run are indistinguishable without a bias.
- *Where is the entry inside a candle?* Finessee_Fx: wick-to-body, deliberately early, fill
  certainty over price. $niper: the OTE fair value gap, which is a location gate rather than a
  candle band. Ben: whichever array he personally reads best, explicitly not the one others use.
- *Journaling.* Trader T logs losers exhaustively and treats winners as optional; Ben logs
  everything, before and after, including demo trades; $niper's distinguishing column is his
  emotional state during the trade.
- *Session.* Trader T names clock windows on a server clock; Ben prefers the PM session and names
  no times; $niper prefers the AM but says it is because August has been poor.
- *Trade management.* $niper always takes partials and moves to break even; Ben scales in and
  break-evens the first tranche; Trader T takes a flat fixed 2R and manages nothing.
- *Balanced price range.* Ben's definition (a filled gap, revisited) is simply not the definition
  used by another guest elsewhere in the corpus (overlapping opposing gaps). Separate ids.

**3. Genuine channel self-inconsistency (this IS what `contested` is for).** Three TTrades
statements in this unit sit against the channel's later doctrine, and are recorded as `contested`
with `voice: ttrades`: two-to-three trades a day with an admission of 15-second over-trading
(against the one-trade-per-day / one-to-two-a-week doctrine); the monthly being irrelevant when
trading a 15-second chart (against the top-down requirement); and, less sharply, his use of a
15-second execution timeframe at all. All three are August 2022, from a trader who says on air he
is "just over a year" in — they are recorded as spoken, not smoothed.

**4. Where the guests do converge, it is worth noticing.** Two independently state a hard two-loss
daily stop ($niper, Trader T). Two independently gate everything on the Dollar Index (Finessee_Fx,
Ben). Two independently demote SMT to a confirmation and warn against low-timeframe divergence
hunting (Finessee_Fx, Ben). Two independently reject the 80–90% win-rate expectation and report
mid-to-high-50s / mid-60s instead (Trader T, Ben). Convergence between two guests is still
`voice: guest` with two `guest_sources` — it is not `mixed`, because `mixed` is reserved for the
host and a guest converging on air.

**5. The guests supply the numbers the channel does not.** This is the single most useful property
of the unit for automation work: 0.5% risk on funded accounts and 1% in a challenge; a 12–13 pip
stop ceiling on EURUSD; a fixed 2R ordered at 2.2R for spread; a 58–65% strike rate with 45–80%
monthly dispersion; a mid-60s win rate; 3–7% monthly returns; two-loss daily stops; 07:00–10:30 and
12:30–15:00 session windows; one-to-two trades a week; "nine out of ten times" for the stop-shy
claim; two HTF entry opportunities vs one LTF. Every one of these is attributed to a named guest in
its concept file, and every one is stated without a sample size.
