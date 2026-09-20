# Live Streams — batch 2 — study notes (unit_id: `live_streams_02`)

Channel: TTrades_edu. Playlist: "Live Streams". All four videos in this batch are the
channel's own **New York Open Live Q&A** streams — TTrades alone at his charts from roughly
9:10 a.m. until shortly after 10:00 a.m., narrating the open and answering chat. There is no
guest in any of the four, so everything here is `voice: ttrades`. All four transcripts are
present and readable (auto-en). Combined runtime 18,669 s (5h 11m).

| video_id | title | duration |
|---|---|---|
| `Je7cd9HJUBE` | New York Open Live Q&A | 4817 s |
| `G1IIdQ3RAkY` | New York Open Live Q&A | 3934 s |
| `m8xcjkOuBHU` | New York Open Live Q&A | 6026 s |
| `TjUolMJNCMY` | New York Open Live Q&A | 3892 s |

There is no stated order to the four and they are not a series. Internal evidence gives a
partial ordering only: `Je7cd9HJUBE` and `m8xcjkOuBHU` both reference the same recent absence
("there was mold in my house and I got sick"), so they sit close together; `G1IIdQ3RAkY`
refers back to the previous day's stream, in which "we did this a lot", and `TjUolMJNCMY`
opens the day before an FOMC decision. Nothing else is datable from the transcripts and no
dates are spoken, so no ordering is asserted here.

## Transcript hygiene

Auto-caption artefacts that had to be decoded before anything could be read:

- **"candle to" = candle 2** — the known corpus-wide artefact. It appears here in the same
  form ("candle to closure", "an ideal candle to closure and then trading candle 3") and is
  read as *candle 2* throughout, consistent with the fractal-model naming used elsewhere.
- **"CAD, ESD" = CISD.** In `TjUolMJNCMY` he lists his whole toolkit as "Highs, lows, air
  value, CAD, ESD, SMT" — that is *fair value [gaps]* and *CISD*, garbled twice in one
  sentence. It is quoted verbatim in `ttfm-minimal-toolkit.yaml` with the decoding recorded as
  an ambiguity rather than silently corrected, because the quote is load-bearing (it is the
  only place he closes the list).
- **"ICSD" / "IC CISD" / "ICCISD" / "CS day" / "CSD"** all mean CISD or intracandle CISD.
  `TjUolMJNCMY` even renders his own posted note as "looking for the CS day range around".
- **"in Q" / "ENQ" / "INQ" / "MQ" = NQ**; **"Y" / "YN" / "Y I'm" = YM**; **"yes" = ES** in
  several places ("YM strongest, yes in the middle"). These are constant and unmissable in
  context but would defeat naive string matching.
- **"handle 2" = candle 2**, **"dogey/dogee" = doji**, **"air value / fair valley / FEG /
  FVG / fair value up" = fair value gap**, **"Vshape" = V-shape**, **"PSP = precision swing
  point"** (he expands it himself), **"B adjust / P adjust" = back-adjust**,
  **"T-spot"** is sometimes "T spot" and once "the T-spot too".
- Numbers survive well; the timezone token **"EST"** survives intact, which matters (below).
- Speaker-change markers (`>>`) appear sporadically and are *chat questions read aloud*, not
  a second speaker. In `G1IIdQ3RAkY` one such line ("The equal lows that are made SMT are
  sus") is a viewer's opinion, not his — his reply is the opposite. That trap is recorded
  explicitly in `relatively-equal-highs-lows.yaml`.
- **No timestamps anywhere in these transcripts.** No `approx_time` is recorded on any
  concept in this unit.

## What this genre is, honestly

A large majority of the runtime is not teaching. Across the four streams the recurring
non-content is: prop-firm giveaway logistics and people spamming keywords in chat (several
minutes per stream, and in `m8xcjkOuBHU` an extended, exasperated stretch where chat cannot
follow the giveaway rules); indicator sales promotion (`Je7cd9HJUBE` carries a running
35%-off pitch); repeated refusals to look at gold ("you guys are going to make me crash out
on gold"); car, Clash of Clans, mould-in-the-house, supplements, public-speaking and
calculus-class tangents; and dealing with hecklers. Roughly a third to a half of each stream
is signal. This note only covers the signal; the padding is named here once so a later reader
does not go looking for content that is not there.

The genre does have a specific, high-value property: **he is asked closed questions and
answers them with numbers he never states in the polished lessons.** Session times, the
timezone, risk per trade, win rate, stop buffer, how the EQ is measured, which data feed —
all of these appear here and nowhere else so far. Equally valuable are the **refusals**: he
says out loud, several times, that he has advanced material he will not publish.

---

## `Je7cd9HJUBE` — New York Open Live Q&A (4817 s)

### What is actually taught

A Monday gap-up session on the indices where he opens by saying there is only one framable
idea and sticks to it: NQ short into a marked line. The teaching value is not the idea, it is
the reasoning around it.

The session is the clearest statement in the unit of the **relative-strength selection rule**.
YM is trending up, NQ is consolidating/falling, ES sits between them; he asks which one is
lying, then gives the negative rule as a slogan — he does not trade the lagging asset — and
spells it out: if he is bearish and YM is the strongest, he will not touch YM. He also makes
the point that a short taken in the *weakest* asset is preferable to one in the strongest,
and that ideally you want the strongest asset to reverse before the weakest expands.

Two exits are taught and both are non-price. The first is a **target that lives on another
chart**: NQ has run past everything on its own chart, so the exit is set by ES — when ES takes
its own low, that is the target on NQ, and he sets the alert on the ES chart. He states the
general form ("you can take profit on one asset because the other asset hits a target"). The
second is the **time-based exit at 10:00**, justified by enumerating the 4-hour, hourly and
30-minute expansion candles that all end there.

The most automation-relevant answers come from chat questions. Asked how many points above the
protected swing the stop should go, he says none — the stop goes at the protected swing, no
extra room, because a trade through it is the invalidation. Asked how the EQ is derived, off
candle size or candle body, he gives the first mechanical answer in the corpus: expansion
candle → measure high to very low; larger-wick candle → measure the wick. Asked the win rate
of the fractal model at 1:2, he gives 30–80% reported, ~50% typical. Asked how the CISD works
when the down-close series is far above, he draws it: the CISD is the closure through those
candles, and mechanically you wait for it.

The last quarter is a walkthrough of his indicator's settings, which doubles as a spec sheet.
Two settings are genuinely informative: the **time filter is demonstrated set to 8 to 11 EST**
— the only timezone stated anywhere in this unit — and the higher-timeframe candle count is
set to 4 ("I like it at four. That's how my model is."), matching C1–C4. He also gives a
backtesting gotcha: protected swings are valid on the closure through but **print at the open
of the next higher-timeframe candle, one second in**, so a replay that looks delayed is not.

### Concepts introduced or restated

Relative strength ranking; do-not-trade-the-lagging-asset; strongest-reverses-then-weakest-
expands; cross-asset target transfer; time-based exit at 10:00; stop at the protected swing
with no buffer; EQ measurement rule; CISD as closure through the opposing-close series;
trapped/stuck order flow (defined by him here, in his own words, as breakout traders caught
offside adding to momentum); enter near the higher-timeframe open; do not short below lows;
eyeballed ADR (500–600 points on the day's instrument); beginner timeframe pairing
(D+H1 bias, H4+M15 entry); protected-swing print timing; 8–11 EST filter; "trade something
that's trending".

### Rules / conditions stated

- Rank the correlated set; trade the weakest for downside, the strongest for upside; never the
  lagging asset.
- Prefer to see the strongest asset reverse before expecting the weakest to expand.
- Stop at the protected swing exactly; no buffer.
- EQ of an expansion candle = 50% high-to-low; EQ of a large-wick candle = 50% of the wick.
- CISD = a closure through the series of opposing-close candles that made the extreme.
- Exit at 10:00 when riding 4H/1H/30m expansion candles; or when the correlated asset tags its
  own target; or on ADR; else drop a timeframe and trail.
- Ask before every entry: am I entering near the higher-timeframe open?
- Almost never short below lows; if you must trade late, short before the low is run, and use
  the middle-ranked asset.
- On a Monday, be closer to the open if you trade at all; the weekly read is done on Tuesday
  after Monday prints.
- Beginner default: daily + H1 for bias, H4 + M15 for entry.

### Refusals and withheld material

- No signals, no entries, no exits, and no disclosure of whether he is in a trade — stated
  repeatedly and attributed to FTC/SEC exposure, not to preference.
- "C2 and C3 closures for daily bias" is what he teaches because it helps the most people;
  he says there are more advanced ways he does not talk about.
- He does not backtest any more ("back testing is to learn the model in my opinion").

### Open questions

- "Small wick" is used constantly and never quantified.
- The 8–11 EST figure is shown as an indicator setting, not stated as his trading window.
- Whether the 10:00 exit overrides an unmet price target is not addressed.
- The 30–80% win-rate range is second-hand from viewers; he never states his own.

---

## `G1IIdQ3RAkY` — New York Open Live Q&A (3934 s)

### What is actually taught

An **inside day** on the indices, and this produces the single cleanest bias procedure in the
unit: on an inside day he marks exactly three levels — previous day high, previous day EQ,
and (only if the EQ fails) previous day low — and says "I only have three points of interest.
That's all I'm looking for." The bias is bullish off a reaction at previous day EQ, targeting
previous day high. When price later closes below previous day EQ he refuses to flip, reading
it as a sweep of the liquidity around the EQ of the range, and says explicitly that a close
below previous day EQ is not automatically an invalidation; you should only act on invalidation
of bias, and that is an advanced skill.

He names the day's profile aloud — a **New York reversal** — and uses it to state the model's
order of operations when a viewer accuses him of favouring bias over profile: "my model is
daily bias, daily profile entry". Bias bullish + profile reversal ⇒ first target previous day
high, second target the intraday high; and a bullish bias does *not* license a long into a
dying sweep of previous day high, because the profile has to support it.

The clock rules are given here more precisely than anywhere else. Before 10:00 the hourly has
not closed, so trading the open requires the 30-minute plus 3-minute pair; from 10:00 the
15-minute and 5-minute become usable. 10:00 brings a new 4-hour, hourly, 30-minute *and*
15-minute candle simultaneously, which is why a new phase of price can start there. And the
move he actually wants is the **9:30-to-10:00 opening drive**.

Two definitional gifts. First, the **protected swing is given its mechanical definition and
its provenance**: it is his simplification of ICT's advanced market structure (short-term /
intermediate-term point labelling), which he found confusing and uncodeable; his version is
"we have to sweep out a low or reach into a gap and then we just have a CISD", with no need to
wait for a further swing to form. Second, **IC-CISD is explained rather than just named**: for
price to make a wick it must have a short-term trend in the opposite direction, so the
intracandle CISD is the flip of that internal trend — detected as a close over the series of
down-close candles that made the low into the point of interest, optionally respecting the
upper half. He states he invented IC-CISD himself, took CISD from AM Trades, and took swing
points largely from "the MMX trader".

An advanced entry is given and immediately flagged as advanced: when the CISD level is too far
away for the risk-to-reward to the target, you may enter directly off the candle 2 / candle 3
closure at the swing, and you may put the stop relative to 50% of that swing — below it, never
at it. He says he has this in his course, not on YouTube, because it would confuse 95% of
viewers.

The most useful *meta* content in the whole unit is here: he states plainly that he holds back
material — an anticipation-CISD video (would help 5%, hurt 95%), a mechanical procedure for
trading inside-bar days, and content on what to expect when candle 3 consolidates. That is a
hard boundary on what this corpus can ever contain.

### Rules / conditions stated

- Inside day ⇒ three levels only: PDH, PD EQ, PD low.
- A close below previous day EQ is not by itself an invalidation of bullish bias.
- Model order: daily bias → daily profile → entry; do not enter when the profile opposes.
- Pre-10:00 execution pair = 30m + 3m; post-10:00 = 15m + 5m.
- Want the directional move between 9:30 and 10:00 (the opening drive); the 9:30 low should
  hold in a bullish case, with SMT.
- Protected swing = sweep of a low (or reach into a gap) + a CISD.
- IC-CISD = close through the opposing-close series inside an unclosed higher-timeframe candle,
  at a point of interest.
- If the CISD level is too far for the RR, enter off the C2/C3 closure at the swing instead.
- Ideal setup = an ideal candle 2 closure, then trading candle 3.
- A sweep that cannot close over is a consolidation, and its resolution is a sweep of the
  opposite side, then an aggressive move back.

### Refusals and withheld material

- Anticipation CISD — will not make the video.
- Inside-bar trading procedure — exists, mechanical, will not publish.
- Candle 3 consolidation handling — exists, will not publish.
- No live trades on stream, ever, so viewers cannot copy.

### Open questions

- What *does* invalidate a bias is never stated, only what does not.
- Whether the 1-minute is usable is stated both ways within this unit (see cross-video below).
- The "advanced" C2/C3-instead-of-CISD entry has no stated condition for *how far* is too far.

---

## `m8xcjkOuBHU` — New York Open Live Q&A (6026 s)

The longest stream, and structurally two videos in one: about 25 minutes of top-down analysis
and open, then — once the market goes nowhere — an extended, unusually substantive
**trading-psychology clinic** built out of viewer problems, and finally a long tail of
giveaway chaos.

### The market half

He opens with a full top-down read across indices, oil, gold/silver, dollar and Bitcoin. The
index logic: a consolidation whose range low was run, so the risk-to-reward is to the upside;
previous day's low swept with a small wick, which supports expansion higher, so the mechanical
target is previous day high; a daily fair value gap sits just above it. NQ is strongest, so NQ
is the instrument for a run at highs.

The pre-open plan is stated as a conditional and then quizzed to chat, which makes it unusually
explicit: *if* NQ (the strongest) forms a reversal at that gap, the trade is a short in a
weaker asset — ES or YM, and he prefers ES because it has the cleaner range. The reversal does
happen and he then **refuses his own setup**, because ES has three equal highs and he will not
trade away from equal highs / failure swings even with an SMT present. That refusal is repeated
four or five times across the session and is the clearest instance in the corpus of a
structural veto overriding a signal that his own model produced.

Also stated here: the 4-hour candle must still support expansion (small wick, or a reversal
already formed) before a 15- or 30-minute CISD is tradeable; fading the daily range is
disliked; a setup that requires trading a reversal on *every* timeframe at once is the wrong
kind of alignment; ADR is eyeballed off the last few daily candles ("I'm just guessing like 80
to 100 maybe") and once covered he stops looking; the single best anti-chasing tip is to enter
around the opening price of the higher-timeframe candles; he does not use the RTH chart because
his analysis depends on the overnight session; and when micros and minis disagree he reads the
minis. Asked how to trade Asia if that is the only session available, the answer is positional:
only in line with a daily candle 2/3 expectation, entering near a protected swing with the
stop on the low, targeting previous day high — not lower-timeframe scalping.

The T-spot question is asked directly. He gives the purpose — "what it means is where the wick
should form" — and then explicitly refuses the derivation (the name is a joke he will not
explain). So the T-spot remains uncomputable from this corpus by the author's own choice.

### The psychology half

Structured as root-cause diagnosis: name the cause, then change or quit. He works through viewer
problems and gives a fixed fix for each — stopped out then it runs → move up a timeframe or
two; can't stop after a loss → one trade a day max; "market conditions" → take accountability,
limit trades and size correctly; two months without passing → fear and too-small size; "I've
learned so many strategies" → you have knowledge and no strategy; break-even then it runs →
stop going to break-even; can't hold to target → set a 2R exit and do nothing; struggling with
direction → the hindsight daily-candle drill. Asked whether to switch strategies, the answer is
no; the strategy is almost never the problem.

Two numeric passages matter for automation. First, **risk per trade** is finally quantified, as
a percentage of the *drawdown* rather than of equity, on a money-versus-time trade-off curve:
aggressive ≈ 20% (up to 50%), middle ≈ 7–10%, conservative ≈ 5% or below, worked on a $1,500
drawdown as ≈ $750 / $150 / $75, with the design constraint that sizing should absorb about 10
consecutive losers. Second, **the break-even math**: a 2R target needs about a 34% win rate to
break even, and moving to break-even early pushes the requirement about 16 points higher, to
about 50% — the same edge destroyed by management. He also insists a loss is not a bad trade
(a bad trade is not following rules) and that n must grow before a win rate means anything.

### Open questions

- The tiers are drawn as an illustrative curve and he explicitly disclaims them as
  prescriptions; he also self-corrects the middle band mid-sentence (5–7 then 7–10).
- "Stop going to break-even" contradicts the break-even / stop-migration rules taught elsewhere
  in the corpus.
- The 34% break-even figure carries no stated cost assumptions.
- All the diagnoses are made from one-line chat messages, and he says he is guessing.

---

## `TjUolMJNCMY` — New York Open Live Q&A (3892 s)

The thinnest session for setups and one of the richest for parameters — a pre-FOMC day where
his only idea is "NQ into the overnight lows and then the reaction there", and he says so at
the start and again at the end.

The framing is worth recording because it is complete and small: multiple days of expansion, so
expect consolidation or retracement; NQ takes previous day high, ES does not ⇒ SMT ⇒ bearish;
on the hourly it is a range, so range high taken ⇒ target range low; NQ is weakest so NQ is the
instrument; after the low is tagged, the reaction's target is the liquidity around the EQ of
that range. He then narrates it happening and stops: "if you don't know, I don't know. That
means I don't do anything."

The parameters answered in chat:

- **Kill zones rejected, with the reason.** "Why don't you care about the kill zone? Because
  I'm just trading higher time frame candles" — what matters is being inside a higher-timeframe
  candle that has formed its wick, not which session block the clock is in.
- **Risk per trade, live-account form**: decide the dollar risk, then derive contract size from
  the stop.
- **Point of interest enumerated**: a CISD can form from a point of interest, which is "a high,
  low, or fair value".
- **The complete toolkit, closed**: "Highs, lows, air value, CAD, ESD, SMT. That's it. No
  matter what, that's all I use."
- **Timeframe substitution**: hourly + 5-minute can be replaced by 30-minute + 3-minute.
- **10:00 as a deadline**: you would have to wait for 10 a.m. to properly trade the model, and
  if the low has not been hit by 10:00 it is more consolidation and you would not want to trade
  it.
- **He does not use the 1-minute** ("I don't really use the one minute") — which conflicts with
  the other two streams.
- **Back-adjust explained** in his own words (contract rollover, gap removed).
- **CRT rejected** ("I don't use CRT"), and in `Je7cd9HJUBE` called a copy of his model.
- **Hedging**: against a long he buys futures or options; he mentions inverse shares as
  possible but says they are not for him and he would prefer options.
- **Execution timeframe**: whichever one the setup appears on, up to and including the daily —
  he cites a silver position held around three weeks.

The closing five minutes are the best statement of the **candle-close discipline** in the unit:
the whole model is based on closures, so nothing can be decided until a candle closes; the
reason backtesting feels smooth and live feels frantic is that in a backtest you only ever see
closes; the fix is to stop predicting the close, and if that is hard, to move to the 15-minute
where you can see there is nothing to do for another five minutes.

### Open questions

- "Formed a wick" as the gate that replaces kill zones is not quantified.
- The bias framing depends on an SMT between NQ and ES that is read visually.
- The candle-close rule sits awkwardly with his own "early CISD" indicator setting.

---

## Cross-video observations

- **The timezone question is answered — once.** "8 to 11 EST" in `Je7cd9HJUBE` is the only
  timezone token in this unit, and it appears while he demonstrates an indicator time filter,
  not while stating a rule. Everything else in these streams (9:15, 9:30, 10:00, 8:30 a.m.
  posted bias, "10 a.m. is a new 4-hour candle") is consistent with US Eastern and with CME
  index futures, but he never says so. EST versus US-Eastern-with-DST is not addressed.
- **10:00 is the load-bearing clock fact.** It appears in three of the four streams and does
  three different jobs at once: a new 4H/1H/30m/15m candle open, a time-based exit, and the
  deadline that kills the opening idea. This is the most decidable, most automatable thing in
  the unit.
- **Relative strength is the first step of every session**, before any setup exists. Trade the
  strongest toward highs, the weakest toward lows, never the lagging one, and expect the
  ranking to switch intraday.
- **Structural vetoes beat signals.** The recurring shape of these streams is: the model
  produces a setup, and he refuses it — three equal highs on ES, a large opposing wick, a
  reversal that opposes every higher timeframe, an already-covered daily range, a level that
  has already been traded through. More airtime goes to *why not* than to *why*.
- **Everything is anchored to closures.** No decisions intracandle; bias comes from C2/C3
  closures; the CISD is a closure through a series; the daily bias question is settled at the
  daily close. A bar-close-driven detector matches his method exactly.
- **Provenance, stated by him**: fair value gaps, highs/lows, daily and weekly profiles from
  ICT; CISD from AM Trades; swing points substantially from "the MMX trader"; protected swings
  as his own simplification of ICT's advanced market structure; IC-CISD as his own invention.
  He says his version is mechanical specifically so it can be coded, which is the strongest
  in-corpus argument that the model is meant to be automatable.
- **Deliberate gaps.** Anticipation CISD, the inside-bar procedure, candle-3-consolidation
  handling and the derivation of the T-spot are all confirmed to exist and confirmed to be
  withheld. Any detector built from this corpus will be missing those four by the author's own
  decision, not because the corpus is incomplete.
- **Internal contradiction on the 1-minute.** `TjUolMJNCMY`: "I don't really use the one
  minute." `G1IIdQ3RAkY`: "I really don't really like using the one minute, but it is what it
  is", followed by a 1-minute entry walkthrough; `Je7cd9HJUBE` analyses the 1-minute repeatedly
  and calls it "a bit cleaner in this case". Recorded as an ambiguity on `timeframe-pairing`.
- **Terms used but never defined in this unit**: small wick, significant low, "clean" range,
  daily profile catalogue (only New York reversal and Asia reversal are named), the T-spot's
  derivation, and what actually invalidates a bias.

---

## Concept files written (31)

`_inbox/live_streams_02__*.yaml` — 6 new ids, 25 additions of evidence to ids already in the
library.

**New**: `ten-am-candle-alignment`, `cross-asset-target-transfer`, `inside-day-three-levels`,
`wait-for-candle-close`, `loss-is-not-a-bad-trade`, `hindsight-daily-bias-drill`.

**Existing**: `entry-time-window`, `equilibrium-eq`, `ic-cisd`, `cisd`, `protected-swing`,
`stop-loss-placement`, `prop-firm-drawdown-sizing`, `realistic-r-expectations`,
`chart-data-settings`, `timeframe-pairing`, `relative-strength-asset-selection`,
`cross-asset-reversal-confirmation`, `root-cause-diagnosis`, `entry-timeframe-elevation`,
`max-one-trade-per-day`, `small-wick-expansion-rule`, `t-spot`, `average-daily-range`,
`htf-opening-price-entry`, `time-based-exit-htf-close`, `relatively-equal-highs-lows`,
`no-shorting-below-lows`, `dont-trade-after-expansion`, `top-down-analysis-procedure`,
`ttfm-minimal-toolkit`.
