# Live Streams (batch 5) — study notes (unit_id: `live_streams_05`)

Channel: TTrades_edu. Playlist: "Live Streams", batch 5 of 5. Two videos, both transcripts
present (auto-en), 10,043s of runtime combined.

1. New York Open Live Q&A with NickDoesFutures — `tDiwwMRWF2k` (4414s) — **named guest**
2. TTrades Indicator Updates - Walkthrough and Q&A — `sdZkE-naNiY` (5629s) — his own tooling

These two videos are opposites in density. The Q&A is a slow pre-FOMC session in which almost
nothing sets up and roughly two thirds of the runtime is banter, giveaways and chat moderation;
it yields perhaps six genuinely mechanical claims, but two of them are unusually good because
they are *disagreements* between the host and the guest, spoken out loud. The indicator
walkthrough is the densest mechanical source in the whole corpus, because a TradingView
indicator has to decide things the prose lessons are free to leave vague — and this is the one
video in the corpus that states a **time zone**.

## Transcript hygiene

Both files are auto-captions with no timestamps, so **no `approx_time` is recorded anywhere in
this unit**. Decodings applied, all of them confirmed by surrounding context rather than guessed:

- **"candle to" = candle 2** — the standard corpus artifact. It appears here as "a daily candle
  to closure", "we had that candle to closure on the monthly", "wait for a daily candle to
  closure". Read as C2 closure throughout.
- **"CSD" = CISD.** The captioner alternates freely between "CISD", "CSD", "the change in the
  state delivery" (dropping the *of*) and the full phrase. All are the same object.
- **"MQ" = NQ**, in the load-bearing SMT line "I'll use ES and YM for MQ". The whole passage is
  about the index triplet, and NQ is spelled correctly elsewhere in the same paragraph. The
  quote is stored verbatim with the error and the decoding is recorded in the concept's
  `ambiguities` rather than silently fixed. Also seen: "N2" for NQ, "in Q" / "in in Q" for NQ,
  "N S E" for NQ/ES, "MQ2 overnight highs".
- **"B adjust" / "B adjusted" = back-adjust(ed)** contract data.
- **"dogee candle" = doji candle.**
- **"1,800" = 18:00** (the answer to "Midnight open or 1,800?").
- **"Two degrees" / "two degrees package" = TwoDegrees**, the developer he says codes the
  indicator for him. **"GXT" is expanded on air as "Garrett XT trades"** (elsewhere in the
  corpus the guest GxTradez appears; this is the same person's shorthand).
- **"T trades wall" / "trades.com" = ttrades.com**; "indicator.teachertrading.com" in the Q&A is
  the captioner mangling indicator.ttrades.com, which he says correctly later in the same video.
- **"RRB"** appears once as the correlated instrument giving SMT on oil ("SMT off the previous
  day low with RRB"). Not expanded, not guessed — the same unexpanded "RB" appears in the weekly
  profile unit.
- **Speaker attribution is the real hazard in `tDiwwMRWF2k`.** The `>>` markers are applied
  inconsistently and sometimes flip mid-answer, so several answers cannot be assigned with
  certainty. Where the speaker is not certain, the tiebreaker used here is **who is driving the
  shared screen** — the host is the one navigating charts, drawing boxes and pulling up his
  website — and every remaining uncertainty is written into the concept's `ambiguities`. The
  running joke that chat keeps calling the guest "Matt" is not an attribution clue: Matt is a
  third person who normally co-streams, not either speaker here.

---

## TTrades Indicator Updates - Walkthrough and Q&A (`sdZkE-naNiY`, https://youtu.be/sdZkE-naNiY, 5629s)

### What is actually taught

This is a settings walkthrough followed by ~70 minutes of chat Q&A, most of it about a 72-hour
subscription sale. Skipping the commerce, what remains is the closest thing the corpus has to a
formal specification of the fractal model, because he is describing code rather than describing
a chart. The important structural fact he states twice: **the indicator has no buy/sell signals,
no stops and no targets, and therefore no win rate** — it is a renderer for his model, and a
printed model "is valid mechanically" without being a trade he wants.

The admission test is the single most valuable sentence in the unit. Asked why the indicator
sometimes stays blank where a viewer sees a setup, he says the setup is simply "not qualified as
a fractal setup", and gives the gate: **a candle 2 or candle 3 closure AND a change in the state
of delivery, both, or nothing prints.** By default nothing is drawn until the candle closes.
This makes the whole model decidable in a way the prose lessons never quite do.

**The time zone.** In the middle of the settings tour, describing a dropdown, he says you can use
a custom time zone if you don't use EST. That is the only clock statement in the corpus. It is
about the indicator rather than about the lessons, so it is not a promise that every session
window ever taught is EST — but it is the channel's own default, and it is the first hard anchor
the corpus has ever offered for the session windows and intraday time levels that were previously
un-decidable. The same settings block carries a **session filter**: setups outside a chosen
session are hidden entirely, and New York is the worked example ("if you don't want to see any
trades when you're asleep"). No numeric session boundaries are given anywhere in the video.

The **fractal pairing** is stated as a map, not a philosophy: on the hourly it uses the daily, on
the 15-minute the 4-hour, on the 5-minute the hourly. The same map governs alerts — sit on the
hourly to be alerted to daily closures, on the 15-minute for 4-hour closures. **Autobias** is a
direction filter built on the same ladder: autobias 1 aligns with the fractal one timeframe up,
autobias 2 goes two up, and in his worked example a bearish daily/hourly model suppresses *every*
bullish setup for the entire day even though one forms mechanically. This matters, because
elsewhere in the corpus he says the exact alignment does not matter as long as all timeframes
agree — the indicator enforces something stricter than the lesson.

**Protected swings** — the headline new feature — get the fullest mechanical treatment they have
had anywhere. They form on the closure through and are printed at the *open of the next candle*,
drawn as a dot plus a line. They **do not repaint**, stated as a matter of honesty: a protected
swing that gets taken out is not deleted, it turns gray and stays on the chart so a failure can
be reviewed. Asked about "false" protected swings he pushes back — a swing that forms and then
fails was still a valid protected swing. Asked about a swing that forms without interacting with
a fair value gap, he answers that would not be a protected swing at all, which supplies the
point-of-interest precondition the prose lessons assume.

Smaller mechanical items land in a row: **early CISD** (off by default, draws the CISD and its
continuations dotted before the close, solid on the closure — off deliberately "because people
learning my model, I don't really want you trading C2"); **PSP** (the same higher-timeframe
candle closing bearish on one asset and bullish on the other, displayed only as "C2 plus a PSP");
his **SMT taxonomy** (reversal SMT / continuation SMT / double SMT) with the default correlation
set named as ES and YM for NQ and an inverse option for negatively correlated pairs;
**projections** off by default, measured from the wicks unless switched to bodies, drawn at 2,
2.5 and 4; the **four-candle model window** ("my model just needs four candles… because I'm
trading swing points"), which is why the higher-timeframe candle default is 4 and why he refuses
a request to make it fewer; and **C1**, which is never labelled because it is only the liquidity
for candle 2's reversal.

Two openings questions get direct numeric answers. **"Midnight open or 1,800? I always use
1,800."** And on the True Day Open: he just uses the daily open, "the normal CME or whatever the
data feed is", with the reasoning that he is trading the actual daily candle so there is no
reason to take the open from a different timeframe. The weekly open is "literally just Sunday
open. Mark that out."

The live gold read is a good example of him refusing to have a bias: a doji closure means he
does not have much bias going into the day, there is a protected swing on each side and price is
in the middle, so he watches Asia and London and decides in New York.

### What is asked and dodged

- **How the T-spot is derived.** Asked point blank how the indicator prints it, the answer is
  "that's kind of what I had coded". He shows what it *does* (the box marks where the daily
  candle's wick should form; the thing inside it is a fair value gap) but the construction rule
  stays withheld, exactly as in the chart-lessons unit.
- **The continuation cut-off.** He confirms continuations are only printed "for a certain extent
  of time" and rejects one because it "forms too late into the move", but never gives the bar
  count. The only nearby numeric anchor is the four-candle model window.
- **What a PSP is for.** He defines it and defers the meaning to a promised standalone video.
- **Order flow** ("thoughts on the order flow hype") — declined twice, he does not use it.
- **Rejection blocks, ORB, CRT** — all disclaimed. "Are you trading CRT with SMT? No, this is
  not CRT."
- Most "what's your bias on X" questions are answered with a redirect to a video on his site.

### Numeric and setting defaults stated aloud

Time zone **EST** (custom available) · higher-timeframe candles default **4** (he refuses fewer;
demonstrates 10) · history default keeps **1 or 0** models on his own chart · calculation bars
"normally around **2,000**" (raised to 5,000 to look further back) · duplicate-indicator offset
**17** bars · projections **2 / 2.5 / 4**, from wicks by default · SMT default pairs **ES and
YM** for NQ · alerts: daily closures from the **hourly**, 4-hour closures from the **15-minute**
· automatic fractal **1H→1D, 15m→4H, 5m→1H** · autobias 1 = **one** timeframe up, autobias 2 =
**two** · daily open **18:00**, weekly open **Sunday open** · 4-hour power of three: "really
that's going to be **10:00 a.m.**" · custom pairs endorsed: **10m/30s**, 5m/15s, 7H/15m (3m/30s
declined).

### Open questions / ambiguities

- EST is stated for the *indicator's clock*, not explicitly for the taught session windows; and
  whether it means fixed UTC−5 or US Eastern with daylight saving is not said.
- The session filter's own New York boundaries are never given numerically, so the filter cannot
  be reimplemented from the transcript alone.
- The automatic fractal map is demonstrated at three rungs only; the generating rule is not
  stated, so the pair for e.g. a 3-minute chart is not decidable.
- "Candle zero or one 2 3 4" — he says both in one breath, so whether the count is 0-based or
  1-based is open.
- The T-spot box is grey in the index examples and green in the gold example with no stated
  difference.
- 10:00 a.m. for the 4-hour power of three is asserted with no derivation here.

---

## New York Open Live Q&A with NickDoesFutures (`tDiwwMRWF2k`, https://youtu.be/tDiwwMRWF2k, 4414s)

### What is actually taught

A pre-FOMC session with a scheduled speaker landing on the 9:30 open — he says outright it is
"not a good combination" — and the honest summary he gives himself is that he probably should
not have streamed. The trading content is therefore thin but unusually candid, because the one
idea he framed *fails on air* and he narrates the failure.

**The one idea**: previous day low on the indices, confirmed by checking all three (it remains on
ES; neither NQ nor YM has taken theirs), to be delivered by the 9:30 open pushing straight into
it. He states the kill condition in advance and then applies it: when price comes back and takes
out the high, invalidating the protected swing that framed the move, "the whole idea is… kind of
invalidated for me", the session is reclassified as chop, and he will not re-enter — while
conceding the target may still be reached later, after the event. In the middle of the same
sequence he gives the clean break-even rule: after the sweep, the candle 2 closure and a formed
continuation on the 1-minute, "you can be break even because price formed a new invalidation."

Two pieces of asset-selection realism. He wanted YM to be weakest so it would drag ES lower;
instead the ranking switched after the open, which he blames for the slow move, and states the
fallback: when strength and weakness are switching he cannot tell which asset will end up at
either extreme, **so he takes ES because it is generally in the middle.** Separately, the
back-adjust rationale, which is better than the bare setting recorded elsewhere in the library:
without back-adjustment the futures chart can show a high as taken while QQQ and NDX have not
taken it, and he wants the contract to agree with the index and the ETF.

The best pedagogy in the video is his answer on reading structure: doing it cold does not work,
because with no context you get alternating bullish and bearish CISDs and cannot tell which to
believe. The fix is ordered — **fix direction from a daily candle 2 closure first, then read
structure, trend and protected swings in that one direction only.** He gives the same daily-bias
recipe as "the easiest, most mechanical way to get bias within my model": daily C2 closure plus
an hourly CISD, both required, with the honest caveat that it is not always correct (he points to
a separate lesson on trading the invalidation of a daily bias). The protected-swing definition
also gets its verbal form here: price hits a point of interest, then "closes through the series
of candles into that point of interest" — the series being a single candle in his example.

He also demonstrates something not seen elsewhere: **trading options off the futures chart.** The
setup is framed on NQ, taken on QQQ at the same moment with an at-the-money strike (he shows a
742 put bought around $180 that would have carried ~$1,300 of intrinsic value at the close), with
the target still read off the futures chart.

### The guest, and where the two disagree

**NickDoesFutures** contributes four things worth keeping, all clearly his:

- **A fixed window: New York only, 9:30 to 11:30**, with a structural enforcement mechanism —
  meetings scheduled at 11:30 and commitments at 12:00 so he has to leave. Rationale: limiting
  time at the screen limits mistakes, and he attributes most errors to sitting there all day.
- **The 1-minute premature entry.** Mark the level on the 5-minute; instead of waiting for the
  5-minute close through it, enter when a **1-minute** candle closes through, keeping the
  5-minute stop; if the 5-minute then fails to close through, exit early for a small loss and
  wait for confirmation. Used when the 5-minute close comes too late or too close to target for
  2R.
- **Adding to a position moves the stop**, because otherwise you are carrying more risk than you
  originally put on, which is against his plan.
- **The gold reactivation alert**: while gold prints small days and small bodies, do not watch
  it; set a price alert above the opposing daily gap, and only above that does it become
  attractive. (The host concurred, saying he had the same level marked.)

**Disagreement 1 — the breaker.** Nick marks a low / high / higher high / lower low sequence on
the 5-minute and calls it a breaker. The host refuses the label — "that's not a breaker, that's
an order block" — and restates his own sequence: "a breaker would be a low, high, lower low,
higher high". He then works with Nick's level anyway, calling it a level rather than a breaker.
Part of the confusion is a stream delay on Nick's end, so the exchange is not purely definitional,
but the two sequences are stated plainly enough to record both.

**Disagreement 2 — FOMC days.** The host: trade before FOMC "if something's clean. But usually
not", and on this particular day he has no interest in trading the event and would rather wait
for tomorrow. The opposing line in the same conversation is to show up and run the same process
every day and take the setup if one appears, on the argument that days scratched off in advance
often turn out in hindsight to have had clean setups. The speaker markers here are unreliable;
the second reading is assigned to the guest on context and the uncertainty is recorded.

**A quiet rejection worth flagging.** Asked "what's the best way to know if it's a run or a
sweep", the host answers: "I don't use those terms so I don't know what they mean." He
substitutes the phases of price at the level — aggressive V-shape reversal → reversal;
consolidation → continuation or a coming reversal; retracement (two to three candles on the
1-minute) → continuation — and adds that he does not judge it from a single closure. This sits
directly against the indicator video in the *same unit*, where he narrates "we have the the
sweep, the closure back in" and ships a setting literally named **C1 sweep**, and against the
library concept `inducement-equals-sweep`. Recorded as contested with both readings.

### What is asked and dodged

- **"Can you do a quick daily bias so I can understand how you do it"** — deflected to "do you
  have a specific day or time", never delivered.
- **"Can you do an order flow tutorial"** — "Probably not. I don't use orderflow."
- **Dollar / EUR / German 40 (DAX) / natural gas** — all declined, the first two on the grounds
  that he does not care for the dollar, the last two as instruments he does not trade.
- **"Could you use the gaps NDX makes"** — "no, I don't use that personally."
- **Bonds** — used only for yields, not for dollar analysis.
- Several trading questions are simply crowded out by chat noise; he says as much ("that was the
  only question I got related to trading").

### Open questions / ambiguities

- No time zone is stated in this video at all, for 9:30, 11:30 or anything else.
- "Small loss" (the exit on a failed 1-minute premature entry) is not quantified, nor is the
  moment it is taken.
- The stated trade frequency in the same exchange is "two to four" a week from one speaker and
  "usually like one to two a week" from the other, and the markers do not reliably say which is
  which — while the advice given to an overtrader is the flat "limit yourself to one trade a
  day".
- The invalidation-of-daily-bias procedure is referenced but not given.
- Whether the 9:30 kill condition applies on days without a scheduled event is not addressed;
  this session had FOMC in the afternoon.

---

## Cross-video observations

- **The indicator is a specification and should be treated as one.** Where the prose lessons say
  "you want to see a change in the state of delivery", the indicator says: closure *and* CISD or
  nothing prints, on the close, no repaint, four candles, this fractal pair, these SMT partners.
  For anything in the library still marked `underspecified` on a threshold, this video is now
  the first place to look.
- **The timezone gap is closed, with a caveat.** EST is the indicator's default. It is stated
  about a settings dropdown rather than about the taught session windows, so the honest position
  is: the channel's own clock is EST, and `daily-profile-session-windows` /
  `new-york-intraday-time-levels` should be read that way unless a later source contradicts it.
- **Three genuine contradictions surfaced**, all recorded as `contested`:
  1. **Sweep vocabulary** — disowned in the Q&A, used freely (and shipped as a setting) in the
     indicator video.
  2. **The opening price** — "I always use 1,800" and an explicit rejection of the True Day Open,
     against the library's `new-york-intraday-time-levels`, which records the midnight opening
     price as an intraday reference and a partials level.
  3. **Breaker vs order block** — host and guest use incompatible swing sequences for the same
     word, in the same minute of tape.
- **Autobias is stricter than the lesson.** `timeframe-alignment-pairs` records him saying the
  exact pairing does not matter provided everything agrees; the indicator enforces a fixed one-
  or two-step ladder and suppresses counter-bias setups for a whole higher-timeframe period.
  Noted in the concept rather than resolved.
- **The teaching order is explicit for the first time**: learn to trade C3 and C4 after a valid
  model prints; add C2 later. That is why early C2 ships off by default, and it corroborates the
  continuation-over-reversal doctrine from the other direction — through a product decision
  rather than an opinion.
- **Nothing in either video quantifies a "small wick", a "strong close" or a "doji".** The
  indicator draws these decisions; it does not explain them. The corpus's oldest ambiguities
  survive this unit intact.
