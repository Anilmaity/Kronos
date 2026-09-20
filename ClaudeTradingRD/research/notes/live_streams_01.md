# Live Streams — study notes (unit_id: `live_streams_01`)

Channel: TTrades_edu. Playlist: "Live Streams" — the channel's **own** New York Open Live Q&A
streams (not the guest-interview Live Stream Guests playlist). Four transcripts, all present
and readable (auto-en), 4,619 / 4,783 / 7,524 / 4,314 seconds.

| video_id | duration | what it is |
|---|---:|---|
| `m0wTBdUe7gs` | 4619s | Bullish NQ/ES continuation day; ADR reasoning; long psychology block; giveaway |
| `NESSCPMzWR0` | 4783s | First trading day of a new month; no bias; risk/R/position-sizing block |
| `xraklBJHW5k` | 7524s | FOMC day; he calls his own analysis wrong on stream; long off-topic health block |
| `yNgx9OAefuI` | 4314s | Bearish NQ day that works; the clearest single walk-through of his intraday timing |

## Genre warning — read this before trusting any density claim

This is not a lesson playlist. It is a live 9:15 a.m. chat stream, and a large fraction of the
runtime is not trading content at all. `xraklBJHW5k` in particular spends roughly its last third
on supplements, gut health, heavy-metal chelation, sleep stacks, nicotine pouches, car loans and
depreciation — he says so himself ("Super off-topic stream"). `m0wTBdUe7gs` spends a long stretch
on his YouTube RPM and mentorship pricing, and both that stream and `xraklBJHW5k` end in prop-firm
giveaway mechanics. Across all four there is a recurring, near-identical psychology loop
("make change or quit", "don't do dumb stuff", "fear of loss", "one trade a day") that is already
well covered by existing psychology concepts and is **not** re-extracted here beyond the parts
that carry a number or a rule.

What makes the playlist worth reading is a different thing entirely: because viewers push back in
real time, he is repeatedly forced to state parameters he never states in the polished lessons,
and to **reject** specific viewer setups with a reason. That is where nearly all the value is,
and it is where this unit's extraction is concentrated.

## Transcript hygiene

- These streams carry **no timestamps** in the transcript text, so **no `approx_time` is recorded
  anywhere in this unit's concept files.**
- The known corpus artifact — auto-captioner rendering **"candle 2"** as **"candle to"** — is
  present here too ("you do have a candle two closure", "a candle too", "candle to closure"). Read
  as *candle 2 / C2*.
- **CISD** is transcribed inconsistently within a single stream as `CISD`, `CSD`, `CIS`, `CIST`,
  and in one place `ICCD` for `ICCISD`. All are the same term.
- "change in the state of delivery" appears once as **"change in the stage delivery"**
  (`yNgx9OAefuI`) and once as **"an hourly change delivery"** (`m0wTBdUe7gs`), with the phrase
  spelled in full elsewhere in the same streams. The garbled forms are quoted verbatim in the
  concept files rather than repaired, per the no-editing-inside-a-quote rule.
- **"Bjust"** (`xraklBJHW5k`, "I personally have Bjust turned on") is **back-adjust** — it matches
  the `chart-data-settings` concept already in the library.
- **"API, FOMC, NFP"** (`m0wTBdUe7gs`) — FOMC and NFP are unambiguous. "API" is almost certainly
  **CPI** mis-captioned; there is no plausible reason for an index trader to rank the API crude
  stocks report alongside FOMC and NFP. Recorded as spoken, flagged in `ambiguities`.
- "whipssaw", "swing pots" (swing points), "RSQ8", "T-spot" spelled "T spot"/"tea spot" — minor,
  non-load-bearing.
- One quote deliberately preserves a doubled word from the captions rather than being cleaned.

---

## New York Open Live Q&A (`m0wTBdUe7gs`, https://youtu.be/m0wTBdUe7gs, 4619s)

### What is actually taught

A bullish continuation day on the indices. The pre-open read is entirely daily-chart: monthly EQ
not respected, so continuation higher; S&P reaching for all-time highs; the daily range budget
("about 400 points, I think we can reach for these highs") sets the target and nothing else does.
He then spends the open **not trading**, and the teaching is in why: price went straight up without
the sweep back into the gap he wanted, and he refuses to convert a missed condition into a
reversed opinion — "Just because I wanted something right and it didn't do it doesn't mean that I'm like,
'Oh, I'm bearish now.'"

The two mechanically useful things in this stream are the **10 a.m. answer** and the **ADR
answer**. Asked when a 4-hour expansion candle can change direction, he runs a call-and-response
with chat and lands on 10 — "usually 10", with 9:45 possible — because that is where a new
higher-timeframe candle opens. And asked how he measures ADR, he says plainly that he does not:
he looks at the daily chart, sees the last candles ran roughly 600 points each, and calls 600 a
good range for today. That number is then used twice more in the stream as the target check.

There is also a clean statement of his **hedging policy**: he is in long swings, so he will not
add intraday longs, because that doubles exposure in one direction; he would rather take intraday
shorts against the swing. This is the reason he sits out an otherwise valid day, and it matters
for anyone reconstructing his trade log — signals he declined are not signals his model rejected.

Late in the stream he gives the **intraday reversal** in one line: Asia formed a reversal by
taking out a low, "that would be what? A 4hour candle closure plus an hourly change delivery" —
and points at his dedicated *intraday reversals* video. He then says "consider this the low of the
day", which is the whole point of the pattern.

### Parameters and rules stated
- Target for the day = eyeballed daily range projected from the open (~600 NQ points).
- Do not enter after the candle has made its range: enter "in the middle of the candle or near the
  opening price".
- 10 a.m. (sometimes 9:45) is when direction can change.
- News: only three releases are tracked — captioned "API, FOMC, NFP".
- No kill zones. No seasonal tendencies. No breakers; higher-timeframe order blocks rarely; CISD
  yes; "gaps and highs and lows" mostly.
- Charting on the **minis only**, never the micros.
- London is not traded (asleep); a London reversal is held into New York, not closed before it.
- Top-down depth is task-dependent: intraday stops at the daily; swings go monthly, three-month,
  sometimes yearly.
- Bullish-day mechanics for that session: previous day's EQ, wick to form in the upper part of it,
  previous month's EQ nearby.
- Bias fix for "right bias, stopped out, then it goes to TP": **move up one timeframe** — and
  explicitly *not* widen the stop.

### Quotes
- "when becomes the time where something can adjust, usually 10"
- "I prefer trading short intraday against my long swings"

### Open questions
- "About 400 points… 500 600 somewhere in there" — the same session is sized three different ways
  in three minutes. The number is a feel, not a computation.
- He never says what timeframe the "expansion candle" whose 10 a.m. open matters is measured on;
  the 4-hour is implied by the example.

---

## New York Open Live Q&A (`NESSCPMzWR0`, https://youtu.be/NESSCPMzWR0, 4783s)

### What is actually taught

The best risk-and-arithmetic stream of the four, because the market gives him nothing (first
trading day of a new month, no bias — "It's a choppy range", "It's just not fun") and the chat asks
money questions instead. He states his position-sizing formula twice and the R arithmetic three
times.

**Sizing.** A prop account is its drawdown, not its headline number — "You don't have 50K of room
to trade. You have $2,500." Risk per trade = drawdown ÷ the number of consecutive losses you are
willing to survive; he gives 10–15 as the divisor here (2,500/12 ≈ 210, rounded to 200) and says a
prop firm's daily loss limit will not bind if you size this way.

**R arithmetic.** 1:1 needs a 51% win rate; 2R needs 34%. His own preference is the 2R–4R band
because one winner covers three losers. He then applies the same arithmetic to **partials**, and
this is the sharpest correction in the stream: taking half off at 1R on a 2R trade leaves +1.5R
against a −1R risk, so "it looks like you took a 2R trade, but you didn't", and the break-even win
rate moves from ~34% to roughly 43%. He is honest that the 43% is estimated on the fly.

**The CISD correction.** A viewer defends a pound long with "there was an hourly change in the
state of delivery here". He rejects it on structure, not on bias: a single tiny opposing candle is
not a series of candles, "I'm looking for the actual structural point", and a close below a lone
consolidation candle is not a CISD. This is the most automation-relevant sentence in the unit
after the timezone — it means a CISD detector that accepts a 1-candle "series" is not implementing
his model.

**Gap opens.** Worked twice, on gold and on silver. If the instrument's assumed daily range is 80
points and price gaps up, "our 80 points become a lot harder to reach" — the far target (previous
month's low) is discarded for today and the previous day's low becomes the target instead. The
directional bias is unchanged; only the day's target moves.

Also here: the **minimal toolkit** enumerated ("realistically I use just like three concepts" —
highs and lows, fair value gap, CISD, EQ/50% fib, plus open-high-low-close logic), the statement
that he **does not use the weekly chart** at all (the weekly profile is read off the daily), the
Monday rule restated, and the claim that **candle 3 with an IC** is the highest win-rate part of
his strategy. He also refuses to answer "how to trade C4 if C3 couldn't close above" — "I'm not
going to talk about that. It's just going to confuse people" — a deliberate non-mechanisation
worth recording as a gap.

### Parameters and rules stated
- risk = drawdown ÷ 10–15; 50K prop account ⇒ $2,500 drawdown ⇒ ~$200/trade.
- 1:1 → 51% win rate; 2R → 34%; a 1R partial on a 2R trade → ~43%.
- One trade a day max; consistent position size; learn to lose.
- Timeframe vs setup count is inverse; risk per setup is inverse to setup count. Daily swings come
  "six to eight times a year", so they are sized much larger.
- If you don't understand the chart, **zoom out — do not zoom in** to find a trade.
- Daily bias, not weekly candle: previous week's high/low is just a daily swing high/low.
- CISD requires an actual structural series, not one consolidation candle.
- Model history: concepts assembled 2023, made mechanical and fractal in 2024.
- "reverse engineer before you ever backtest" — offered as the step that should precede any
  backtesting, with no procedure attached to it.

### Quotes
- "Take your drawdown divided by maybe 10 to 15"
- "it looks like you took a 2R trade, but you didn't"

### Open questions
- The two sizing divisors across the unit (10–15 here, 7 in `yNgx9OAefuI`) are never reconciled;
  he presents the divisor as an aggressiveness dial rather than a rule.
- "Still meets my requirement for a model" is the gate for when a partial *is* allowed — undefined.
- C4-after-a-weak-C3 is explicitly withheld.

---

## New York Open Live Q&A (`xraklBJHW5k`, https://youtu.be/xraklBJHW5k, 7524s)

### What is actually taught

An FOMC day, and the most instructive stream of the four precisely because **he gets it wrong on
air and then debugs himself in front of the chat**. His pre-open read was "no bias, expect
consolidation", and he walks chat through what consolidation means operationally: sweep the range
high, back into the range, sweep the range low, back into the range; with price sitting nearer the
high, expect 9:30 to take the high first and then rotate down. That much happens. Then price keeps
going, and instead of defending the call he says "I would say I'm wrong", replays his own opening
tweet about YM decoupling from NQ/ES, and shows the trade he should have taken: YM was the asset
coming back into alignment, its target was the previous day's low, so the next-weakest asset (ES)
was the one to trade — and viewers in chat who did reported 2R to 4R.

That decoupling logic is the stream's own new idea: when correlated indices diverge, "one of these
is lying", and "something has to come back into alignment". He offers no threshold for what counts
as decoupled and no rule for which side resolves it, which is why it is filed `underspecified`.

The other high-value blocks:

- **Session window.** "For New York, what time frame? I use 8:00 a.m. to around 11."
- **Timeframe pairs.** For pre-open / London: "H4 M15 or daily H1", preferring H4/M15 for London.
- **Midnight open rejected** — he uses the daily open, because the daily candle is what he trades.
- **ICCISD defined**: a CISD/continuation — a protected swing — that forms the wick of the
  higher-timeframe candle, in candle 3. Procedure: let the candle open, let the continuation form
  (that is what builds the wick), and once it closes, trade in the candle's direction with the stop
  on that wick. He calls it his mechanical way of forcing a trader to let the wick form.
- **Charting vehicle.** SPY has no overnight data, so chart ES and trade SPY/QQQ/options. Same
  reasoning for index options.
- **Targets.** "I almost always use daily highs and lows as targets."
- **Never trade the lagging asset, only the middle.**
- **The daily-timeframe POI exemption**: asked whether a daily candle must reach a point of
  interest before its closure is usable, he says the daily is "this one specific time frame that I
  don't require a point of interest" — provided the monthly context supports it. This cuts against
  the stricter POI requirement elsewhere in the corpus and is recorded as contested.
- **Backtest→live diagnosis**: the single most common cause he sees is that in backtesting you
  wait for closures, and live you act on a still-forming candle.
- **FOMC**: no expectation for the release, and he never trades after it — he waits for the next day.
- **Settlement off**, back-adjust ("Bjust") on, CME data via Ninja Trader.
- **Rejected as noise**: time distortion, macros, reaper gaps, "chain of custody", Silver Bullet,
  IFVGs, order flow / footprint / DOM / TPO.

He also demonstrates something the polished videos never do: he shows a *mechanically valid* C2/C3
in his own system and declines it because the higher timeframe does not back it — "just because
something mechanically shows up doesn't mean it's it's good". Any detector built from this corpus will
generate exactly those signals, and he would not take them.

### Quotes
- "I never trade the lagging only the middle"
- "you wait for closures in back testing"

### Open questions
- "Decoupled" has no threshold; the example was one index ~0.63% down with the other two flat.
- His own admission that he could not frame the move in advance is a caution against treating the
  decoupling read as a live signal rather than a post-hoc explanation.
- Roughly a third of the runtime is health/supplement/finance content with no trading value.

---

## New York Open Live Q&A (`yNgx9OAefuI`, https://youtu.be/yNgx9OAefuI, 4314s)

### What is actually taught

The cleanest full-cycle stream: bias formed pre-open, move delivered, then reverse-engineered on
air. It also contains **the only explicit timezone statement found anywhere in this corpus**.

**The timezone.** Telling a viewer where to scrub back to for his bias explanation, he says:
"Go to 954 EST on the video." That single line fixes every clock time in the corpus — 8:30, 9:15,
9:30, 9:45, 10:00, 10:30, 11:00 — to New York time. It is corroborated structurally in
`xraklBJHW5k`, where he explains that 9:30 matters because that is when SPY / the normal market
opens. He also states that he streams at 9:15 to have ten minutes before the open.

**The 9:45 / 10:00 derivation.** Asked why he uses 9:30, 9:45 and 10, he gives the full mechanism
and simultaneously explains why he thinks macros are fake. Enter at 9:31 and you are inside a
15-minute, 30-minute, hourly and 4-hour candle that are all still forming. 9:45 is where a new
15-minute candle opens. 10:00 is where a new 30-minute, hourly **and** 4-hour candle all open
together. So those are the moments direction can change — and a macro is just "arbitrary ranges
around the open of new higher time frame candles". He will not enter at 9:50, late inside a
15-minute candle; he waits for the next open.

**The time-based exit, derived rather than asserted.** An expansion candle has a small wick and a
large body, so once the wick is formed a bearish expansion candle "generally closes into the low of
the candle" — therefore holding to the candle's close gives an exit near its extreme. On the live
move he lists three acceptable exits: the price target, 9:45, and 10:00.

**The bias walk-through.** Monthly bearish, new protected swing, new gap, gap hit, candle 2 closure
⇒ bearish for the day; previous day low as the near target and the previous month's low as the
higher-timeframe one. (He gives the same treatment to gold in the same stream and puts its
previous-month objective at "right around 3955".) He then went to the 4-hour, found an SMT in
the previous 4-hour range's high, and asked the timing question: if price is going to expand, when?
8:30 had passed and done nothing, so 9:30. He states his own falsifier out loud: if the high gets
taken out at 9:30 or 10, he is wrong.

**Two corrections worth keeping.** First, he refuses chat's bullish SMT on the previous day low —
repeatedly — because the level was never reached: "it failed to actually hit anything relevant",
and SMT is only looked at inside a valid model ("it looks for a reversal SMT and a continuation SMT
within my model"). Second, a quiz: his indicator marked two protected swings, and he explains why
one is worse — the sweep is so shallow it "barely even forms a sweep", almost equal highs, so it
cannot be trusted. Trading away from a swing needs "some sort of reach". That is a discretionary
filter sitting on top of his own mechanical marker, and he says so.

**Sizing, again, differently.** Here he builds a time-versus-money curve for prop evaluations and
lands on drawdown ÷ 7 ≈ $350 on a $2,500 drawdown, versus ÷10–15 in `NESSCPMzWR0`. The divisor is
explicitly the trader's own aggressiveness choice: 1–3 for disposable accounts, 15–20 for a single
irreplaceable one.

**The window.** "go to 8 to 10:30 each day and mark that out" — that is the move he tries to catch,
and he calls it "my window where I like to trade". Asked whether one could trade 8–11 a.m. and then
close the charts for the day: "I mean, that's what I do."

### Quotes
- "Go to 954 EST on the video"
- "10 is where we get a new 4hour candle"

### Open questions
- 8–10:30 here versus 8:00–"around 11" in `xraklBJHW5k`; both are approximations, not rules.
- "EST" is said literally — whether he means fixed UTC−5 or the observed Eastern clock (EDT for
  most of the trading year) is never addressed. The 9:30-cash-open anchor implies the latter.
- The shallow-sweep filter is unquantified: no minimum reach in points, ticks or fraction of range.

---

## Cross-video observations

- **The timezone is settled.** `yNgx9OAefuI` states EST once, in passing, and `xraklBJHW5k` anchors
  9:30 to the US cash open. Nothing else in the corpus does this. Every session-time concept can
  now be resolved to America/New_York.
- **His clock is derived, not conventional.** 9:45 and 10:00 are not chosen times; they are where
  new higher-timeframe candles open. This is the same argument he uses to reject macros and kill
  zones, and it means a timing implementation should be built from candle-open boundaries rather
  than from a table of session windows.
- **Live Q&A is where the negative space is.** Across four streams he explicitly refuses: kill
  zones, macros, midnight open, breakers, IFVG, OTE, Silver Bullet, CRT ("a copy of my fractal
  model"), order flow / footprint / DOM / TPO, seasonality, intraday fundamentals, the weekly
  chart, CFDs, the Russell, scalping, signals and copy trading. A detector built from the positive
  concepts alone will over-generate; the exclusions are load-bearing.
- **Mechanically valid ≠ tradeable.** Stated in three of the four streams, most clearly on FOMC day.
  Higher-timeframe backing, a relevant level actually being *hit*, and remaining daily range are
  all gates applied after the pattern is found. A backtest that fires on the pattern alone is not
  testing his model.
- **He is willing to be wrong on air.** `xraklBJHW5k` contains a full self-debug. That is the only
  place in the corpus where the failure mode of his own read is documented from the inside, and it
  is worth more than another example of the pattern working.
- **The psychology loop is repetitive and already covered.** "Make change or quit", "don't do dumb
  stuff", fear-of-loss, tilt, revenge trading, one-trade-a-day: near-identical in all four streams,
  and mapped to existing psychology concepts. It has been deliberately not re-extracted here except
  where it carries a number or a rule.
- **What he still refuses to mechanise**: what makes a "series of candles" (no minimum count), how
  shallow a sweep must be to be rejected, what counts as decoupled, what a "clean setup" is, and
  C4 behaviour after a weak C3 — the last declined outright on the grounds that it would confuse
  people.
