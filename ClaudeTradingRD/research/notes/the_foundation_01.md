# Study notes — unit `the_foundation_01` ("The Foundation", batch 1 of 2)

Channel: TTrades_edu. 20 videos in the unit; **14 transcripts available, 6 missing**
(see "Not yet available" at the end). Everything below comes only from the transcript
text actually present on disk. Auto-generated transcripts carry **no timestamps**, so no
`approx_time` is recorded anywhere in this unit — inventing one would be a fabrication.
Auto-caption mis-transcriptions are frequent and are flagged where they matter
("wrist reward" = risk-to-reward, "cby/civy/CBI" = SIBI, "bissy/busy" = BISI,
"gone box" = Gann box, "OT" = OTE, "main threshold" = mean threshold, "dogee" = doji,
"n9xm / mmxm" = MMXM Trader).

---

## Breaker Blocks Simplified - ICT Concepts  (75S4vwD4P1U, https://youtu.be/75S4vwD4P1U, 806s)

### What is actually taught
The video defines a breaker block purely as a **four-point swing sequence plus a candle
selection rule**, then layers displacement, entry, stop and target logic on top. A bullish
breaker requires the sequence low → high → lower low → higher high. The speaker is explicit
that each point must be *confirmed* as a swing before it counts, i.e. the pattern is only readable after the fourth
leg completes. Once the higher high exists, the breaker zone is the **single or series of
up-close candles located between the low and the high** — i.e. the up-close candles of the
first leg, not of the displacement leg. The bearish mirror is high → low → higher high →
lower low, with the zone being the series of **down-close** candles.

Marking convention is stated precisely and contrasted with order blocks: for a breaker the
speaker marks the **whole series of candles including the wicks** (a rectangle), whereas for
an order block he marks **only the opening price** of the series (a line). He notes both
refer to price action at a similar level but are different concepts, and shows the two
entries sitting at different prices in the same example.

Displacement is presented as a required quality filter: he wants displacement paired with the
breaker, specifically a fair value gap overlapping the breaker — that overlap is named the
**unicorn model** (bullish breaker + bullish FVG; bearish breaker + bearish FVG).

Two stop-loss choices are given: (a) beyond the breaker block itself (the breaker low for a
long, the breaker high for a short), or (b) at the swing low/high. He works an example where
the swing-based stop would have missed a 2R take-profit and then been hit, while the
breaker-based stop achieved 2R — but explicitly frames this as a trade-off, not a rule, and
in another example says the tighter breaker stop is the more sensible one because the
swing-based version pushes the 2R target far away.

Entry choice is also framed as discretionary: enter at the breaker itself (fill certainty,
allowing price to trade back into the zone) or wait at the start of the overlapping fair
value gap for better risk-to-reward and risk not being filled.

Targets: fixed 2R, or **standard-deviation projection of the manipulation leg**. In the
breaker pattern the manipulation leg is defined as **the leg down that created the lower
low** (bullish case), projected from the swing that produced the subsequent higher high;
he targets the −2 to −2.5 and −4 to −4.5 deviations.

Three worked top-down examples close the video, including one that **loses** (ES: sweep of
sell-side after the open, displacement through the breaker, unicorn entry, stopped out) —
shown deliberately, on the stated grounds that losses are part of trading.

### Concepts introduced (speaker's own terminology)
breaker block (bullish/bearish); "low high lower low higher high"; series or single up-close
candle; displacement; unicorn model; manipulation leg; projection / standard deviations
(−2, −2.5, −4, −4.5); order block vs breaker block marking difference; internal liquidity →
external liquidity (used to justify the HTF context); London Kill Zone; previous day low;
equal lows.

### Rules / conditions stated
- Bullish breaker = confirmed swing sequence low, high, lower low, higher high.
- Bearish breaker = confirmed swing sequence high, low, higher high, lower low.
- If the required 4th point never forms, there is **no** breaker (a candidate is discarded on-chart when the fourth point never prints).
- Breaker zone (bullish) = the single or series of **up-close** candles between the low and the high; marked **including wicks**.
- Breaker zone (bearish) = the single or series of **down-close** candles, marked including wicks.
- Order block, by contrast, is marked at the **opening price** only.
- Prefer displacement with the breaker; FVG overlapping the breaker = unicorn model.
- Stop: below the bullish breaker (low of the zone) **or** at the swing low. Same, mirrored, for shorts.
- Entry: at the breaker, or at the start of the overlapping FVG (better R:R, fill risk).
- Manipulation leg for projection = the leg that created the lower low (bullish) / higher high (bearish).
- Minimum target discussed = 2R; projection targets −2 to −2.5 and −4 to −4.5.

### Examples walked through
GBPUSD 5m bullish breaker (retest → sweep of the low into the breaker, bodies respecting,
continuation); EURUSD 5m bearish breaker (a first candidate that fails for lack of a lower
low, then a valid one with displacement and FVG = unicorn); a unicorn long where price never
returned to the FVG (entry-vs-R:R trade-off); GBPUSD hourly → 5m top-down (hourly unicorn in
the London killzone, 5m breaker + FVG, −2 deviation for 3.62R); hourly unicorn short into
previous-day-low equal lows; ES 60m → 5m losing trade.

### Quotes
- "with a bullish breaker we need a low high lower low then higher high"
- "I want to see displacement paired with them"

### Open questions / ambiguities
- "Displacement" is never quantified (no minimum candle range, ATR multiple, or gap size).
- Whether the breaker zone uses only the *contiguous* up-close candles immediately preceding the high, or every up-close candle between the low and high, is not stated.
- The confirmation rule for a swing point is not restated here (it is defined in the liquidity video as a 3-bar fractal); how many bars are needed to "confirm" is left implicit.
- Stop and entry selection are explicitly left to user discretion — not decidable from the video.
- Whether the FVG must overlap the breaker zone by any minimum amount for the "unicorn model" is unspecified.

---

## Change In State Of Delivery [CISD] - Orderblock Formation - ICT Concepts  (CHIK5oBRKiw, https://youtu.be/CHIK5oBRKiw, 944s)

### What is actually taught
CISD is defined as the moment price **goes from bullish to bearish or bearish to bullish**,
made operational as a *close through the opening price of the last single-or-series of
opposing-close candles into an important level*. Bearish CISD: price rallies into a higher
timeframe PD array / important level with one or more up-close candles; when price **closes
below the opening price of that up-close candle (or of the *first* candle when there is a
series)**, the state of delivery has changed and lower prices are anticipated. Bullish CISD
is the mirror: price puts in a swing low, raids sell stops, then closes **over** the series
of down-close candles.

The rule that a series uses the opening price of its FIRST candle is stated twice and is
the single most load-bearing mechanical detail in the video.

CISD is also presented as **the validation event for an order block** — the title itself is
"CISD — Orderblock Formation". He repeatedly narrates that close as the event validating the candles as an order block. So in this channel's vocabulary, CISD is the event and
the order block is the resulting zone.

The video then builds a full **entry model**: (1) manipulation — a sweep of an old high/low
out of a range, ideally an aggressive move out and back into the range; (2) CISD in the
opposite direction; (3) **project the manipulation leg** to standard deviations for targets
(−2 to −2.5 primary, −4 to −4.5 secondary), and look left for existing liquidity resting at
those deviations as confluence; (4) enter at the CISD level / order block / fair value gap,
stop on the manipulation extreme. He adds a filter: when bearish, only take entries inside the premium of the dealing range.

Fractality is demonstrated top-down: a daily FVG as the draw, CISD confirmed on the hourly,
then the next day a sweep of buy-side at the 09:30 open, CISD on the 2-minute, targeting
equal lows and the hourly projection. Multiple sequential CISDs form successive order blocks
that "support price lower" — so a missed first entry can be replaced by the next one.

Finally CISD is combined with the **Box setup** (AMD): mark the accumulation range, mark the
**highest body** in the accumulation (the box level), mark the deviation/manipulation; the
plain Box entry is a retest of that previous-high body level, but the confirmed version waits
for an order block / CISD to form at that retest before entering.

### Concepts introduced
change in state of delivery (CISD); opening price of the first candle of a series;
order block validation; manipulation; higher timeframe PD array / important level;
standard deviation projection (−2, −2.5, −4, −4.5); dealing range; premium filter;
Box setup; accumulation / manipulation / deviation from the range; London lows;
next day model; lower-timeframe sweep preference.

### Rules / conditions stated
- Bearish CISD: price closes **below** the opening price of the single/series of up-close candles that made the high into an important level.
- Bullish CISD: price closes **over** the opening price of the single/series of down-close candles that made the low.
- With a **series**, use the opening price of the **first** candle of the series.
- The same close that produces CISD **validates the candle(s) as an order block**.
- Preferred (not required) precondition: a sweep of buyside/sellside liquidity first, ideally visible on a lower timeframe.
- Entry model order: manipulation → CISD → projection of the manipulation leg → entry at order block / FVG.
- Stop: on the manipulation high (short) / low (long).
- Minimum acceptable R:R is 2; if the nearest target gives less (example: 1.66R), use the −2 deviation instead.
- When bearish, only take entries in the **premium** of the dealing range.
- Box setup: mark the accumulation range, the highest body within it, and the deviation; entry on retest of that body level, optionally requiring an order block/CISD to form there.

### Examples walked through
5m sweep of old highs before New York open — first CISD attempt fails (no close below), a
second sweep then produces the close → short to London lows plus −2/−2.5 projection;
daily FVG → hourly CISD → next-day 09:30 sweep → 2-minute CISD, targets at −2/−2.5, −4 and
the hourly objective, all hit; a range example showing repeated CISDs creating successive
order blocks in a downtrend, and the mirror long at the −2/−2.5; the community-tab Box-setup
example where he waits for order-block confirmation at the box retest, both short and long.

### Quotes
- "price goes from bullish to bearish or from bearish to bullish"
- "what I focus on is a manipulation then a change in state of delivery"

### Open questions / ambiguities
- Closing below the opening price implies a body close, but wick-vs-body is never stated explicitly.
- "Important level" / "higher timeframe PD array" is not enumerated exhaustively here (the order-block video lists: previous order block, fair value gap, or a sweep).
- The series definition (must the up-close candles be contiguous? does one down-close candle break the series?) is not given.
- Projection anchor points are shown on charts but never stated as a general rule in words; the deviation scale is described as −2/−2.5 and −4/−4.5 without saying whether it is 1x the manipulation leg per deviation.
- The required aggressive move out of and back into the range is qualitative.

---

## Discount & Premium - ICT Concepts  (MlMsG7li9zY, https://youtu.be/MlMsG7li9zY, 518s)

### What is actually taught
The building block is the **range**: a swing high to a swing low, chosen as the most prominent range in the area. A Fib/Gann box is drawn high→low; the 0.5 is **equilibrium**;
above 0.5 is **premium**, below 0.5 is **discount**. He extends the box leftward purely for
visualisation.

The justification is risk-to-reward, not magic: entering long at equilibrium with the stop at
the range low and target at the range high gives exactly 1R; the deeper into discount the
entry, the greater the R:R. Therefore: **look for PD arrays in discount for longs, in premium
for shorts.**

A second, load-bearing mechanical point: **ranges are nested and expanding**. There is never just one
range — as price makes new highs he drags the range high up with it, re-anchoring until a swing high prints, and when a new swing low then a
new leg forms, a *new* range is created and the premium/discount frame is redrawn. He walks
this iteratively on DXY: each new high/low re-anchors the box, and each retracement is judged
against the *current* range.

Examples: NASDAQ daily (range from swing low up, tracked higher until a swing high prints;
long only in the discount FVG); DXY (nested ranges, a discount FVG reached, then a reversal
model — sweep of a lower-timeframe low, structure break up, mark the displacement range,
long from a discount order block whose **opening price** is respected); GBPUSD daily (daily
FVG filled, new high, aggressive displacement range marked high→low, small discount FVG as the
target; next day a sweep of Monday and Friday's highs, close back in → next-day model wants a
drop into that FVG); then down to 15m where midnight and the Asia range high/low are marked,
Asia low and prior lows swept, an aggressive move up creates a fresh range, and an **OTE**
entry is taken — he contrasts 3.43R at the OTE against 1.6R at equilibrium.

### Concepts introduced
range (swing high → swing low); equilibrium (0.5); premium; discount; PD array;
ranges within ranges / expanding ranges; displacement range; OTE (used, defined elsewhere);
reversal model; next day model; Asia range high/low; midnight.

### Rules / conditions stated
- Range = swing high to swing low, described as the most prominent range in the area.
- Equilibrium = 0.5 of that range; above = premium, below = discount.
- Longs are sought at PD arrays **below** 0.5; shorts at PD arrays **above** 0.5.
- While price is making new highs and no swing high is confirmed, keep re-anchoring the range high (the range expands).
- When a new leg forms after a new swing low/high, draw a new range; multiple ranges coexist.
- Entry at equilibrium with stop at the far side and target at the near side = 1R by construction.

### Examples walked through
NASDAQ daily discount FVG long; DXY nested equilibrium ranges and a discount order block
(opening price respected); GBPUSD daily → 15m, Asia-low sweep, OTE long into a daily FVG,
3.43R vs 1.6R at equilibrium.

### Quotes
- "anything above the 0.5 FIB is considered at a premium"
- "I am looking for PD arrays in a premium to get short"

### Open questions / ambiguities
- Selecting the most prominent range is discretionary — no algorithm is given for which swing high/low pair to use, and he concedes the nesting gets confusing.
- No rule for which nested range takes precedence when they disagree.
- Whether the range is drawn wick-to-wick or body-to-body is not stated.
- Fib vs Gann box is presented as interchangeable tooling.

---

## ICT Daily Bias - The Only Video You Will Ever Need!  (g3oDYq4P9ZE, https://youtu.be/g3oDYq4P9ZE, 1110s)

### What is actually taught
A ranked set of simple, decidable bias tools, credited in part to **MMXM Trader** (auto-caption renders it n9xm / mmxm) and his **next day model**.

1. **Previous day high/low.** Unless the day consolidates inside yesterday's range, price
takes previous day high, previous day low, or both. The bias question is reduced to: which is
it more likely to reach? Trend supplies the default answer (uptrend → previous day high).
2. **Previous day high/low as reversal points.** If price reaches a previous day high and
**cannot displace above it**, and closes back inside, expect the opposite side next.
3. **Previous week high/low** — the same two uses (draw and reversal), demonstrated week by
week on a daily chart, including an "indecision" week where he refuses to pick a side.
4. **Swing points** as the draw when previous-day levels are already consumed (look left to the lows resting below).
5. **Failure to displace**: price fails to displace under a swing low → bias up; fails to
displace over a swing high → bias down.
6. **Next day model**: when price sweeps a level/PD array and closes back inside, anticipate
the *next daily candle's* shape — **open-low-high-close (bullish)** after a failed low sweep,
**open-high-low-close (bearish)** after a failed high sweep. He then keeps using that bias
day after day until the draw on liquidity is reached.

The long DXY walkthrough is a bar-by-bar application of the above and is unusually explicit
about the failure mode: at an inside bar he says he does not have much bias and simply marks
both the high and the low to see which is taken first.

Two full top-down trades close the video. **London example**: daily failure to close over
previous day high in an existing downtrend → bias down → hourly shows a stop hunt into an FVG
during London → high of day set in London → enter the FVG, stop on the high, target previous
day low, then extend to the swing point below. **New York example**: previous day low swept
and closed back over → bias up to the swing high; next day sweeps that high and closes back
in → next-day model says down → hourly FVG marked as the point of interest, drop to 5m for a
5m FVG entry, stop above the high, 2.55R to lows below.

### Concepts introduced
daily bias; draw on liquidity; previous day high/low; previous week high/low;
failure to displace / lack of displacement; next day model; open-high-low-close and
open-low-high-close; swing points; reversal framing; midnight opening price; killzones
(London, New York); consolidation as the exception case.

### Rules / conditions stated
- Unless consolidating, the day takes previous day high, previous day low, or both.
- Close **above** previous day high → look for continuation to the next previous day high.
- Reach above previous day high **without** closing outside → bias flips to previous day low (and mirrored).
- Same logic applied to previous week high/low.
- Failure to displace under a swing low → bias up; over a swing high → bias down.
- Next day model: failed low sweep → expect an open-low-high-close candle; failed high sweep → expect an open-high-low-close candle.
- Keep the bias until the draw on liquidity is reached.
- On an inside/indecision bar: mark both extremes and wait — no bias.

### Examples walked through
An extended daily sequence using only previous day high/low; weekly-level sequence including
a Monday sweep of previous week's low producing a bullish reversal candle and expansion to
previous week's high; DXY daily bar-by-bar narrative; London-session trade (hourly FVG short
to previous day low then a swing point); New York-session trade (hourly FVG → 5m FVG, 2.55R).

### Quotes
- "price more likely to take previous day high or previous state low"
- "when price fails to displace over a high my bias can be down"

### Open questions / ambiguities
- "Displacement" over/under a level is again unquantified — the working proxy in the examples is a **close outside the range** vs a reach-and-close-back-inside, but he uses both "displace" and "close outside" as if interchangeable.
- Consolidation (no bias) is not defined by a threshold.
- Which timeframe's swing points to use when previous-day levels are consumed is discretionary ("look left").
- The next-day model is stated as an anticipation of candle shape, not a trade trigger; entry still requires a lower-timeframe model.
- The video never says what to do when previous day high and low are both taken (outside day) beyond "I'd like to see a continuation".

---

## ICT Killzones & Indicator Settings  (MPeeE55rNOw, https://youtu.be/MPeeE55rNOw, 827s)

### What is actually taught
A pure timing/reference video. All times are **New York time (EST)**; the daylight-savings
workaround is to verify in TradingView that the selected timezone displays as New York time.
Killzones are "specific time windows during the trading day in which the volatility is
higher", split into Asia, London and New York, and **differ between Forex and indices**:

- Forex: Asia 20:00–00:00, London 02:00–05:00, New York AM 07:00–10:00, London Close 10:00–12:00.
- Indices: Asia 20:00–00:00, London 02:00–05:00, New York AM **08:30–11:00**, PM **13:30–16:00**.

He then walks the manual markup of each session box on Forex and index charts, notes that a
large portion of the daily range is created in the New York AM session, and observes on one
example that "Asia accumulates, London manipulates, and then we distribute lower through the
New York session" with London Close holding the range — i.e. sessions map onto AMD.

The second half is a configuration walkthrough of the free TradingView indicator **"ICT
Killzones & Pivots" by TFO**: session count limit, timeframe limit (only draws below 30m),
timezone, label size, drawing cut-off time (default 12:00, extendable to 16:00), killzone
boxes and colours (his: Asia blue, London green, NY AM orange, PM yellow, lunch off),
**killzone pivots** (session highs and lows — he stresses these as liquidity), the
**opening price** feature (a horizontal line at any chosen time, e.g. 08:30 open) and
**timestamps** (vertical lines, e.g. midnight / true day open).

A worked example shows: Asia range formed → London sweeps Asia low and displaces back in,
leaving an FVG → box-setup resistance from previous highs → displacement lower with up-close
candles into a level then closed below (an order block) → project the **London manipulation**
leg high→low and mark −2/−2.5 → overlay the **OTE** of London high → current low → enter the
old FVG with stop on the high, targeting the low or the −4 deviation. He then shows the PM
session repeating the pattern.

Finally, the **Silver Bullet** window is introduced as narrowing a killzone to a one-hour
window (the one demonstrated is 10:00–11:00, marked with timestamps or by repurposing the
"New York lunch" session), within which he looks for price to draw to a liquidity pool. He
defers the detail to ICT's own channel.

### Concepts introduced
killzone / session; New York time (EST) as the reference; Forex vs indices killzone times;
Asia / London / New York AM / PM / London Close; session accumulate-manipulate-distribute;
killzone pivots (session highs/lows); true day open / midnight; 08:30 open;
Silver Bullet window; TFO's ICT Killzones & Pivots indicator; box setup; OTE; projections.

### Rules / conditions stated
- All killzone times are New York time; verify the chart timezone shows New York.
- Forex: Asia 20:00–00:00; London 02:00–05:00; NY AM 07:00–10:00; London Close 10:00–12:00.
- Indices: Asia 20:00–00:00; London 02:00–05:00; NY AM 08:30–11:00; PM 13:30–16:00.
- Session highs and lows are liquidity and should be marked.
- High-probability moves are asserted to occur generally during killzones.
- Silver Bullet = a 1-hour window inside a killzone; the demonstrated one is 10:00–11:00 NY.

### Examples walked through
Forex chart manual session boxes (Asia accumulation, London manipulation, NY distribution);
a second Forex day; an indices day including an NFP session; the indicator configuration;
the London-manipulation → NY-AM continuation trade with projections and OTE; the PM session
order block.

### Quotes
- "kill zones are specific time Windows during the trading day"
- "Asia accumulates London manipulates and then we distribute lower through the New York session"

### Open questions / ambiguities
- Only **one** Silver Bullet window (10:00–11:00) is actually named; ICT's other SB windows are not enumerated here.
- The EST/EDT question is deflected to "make TradingView say New York" rather than resolved as fixed UTC offsets — a backtest needs the exchange-time convention, not a UI setting.
- London Close (10:00–12:00) is listed for Forex only; whether it applies to indices is not said.
- "Volatility is higher" is asserted, not measured.
- Why NY AM differs between Forex (07:00) and indices (08:30) is not explained.

---

## ICT Power Of 3 - AMD  (TCFvsZeYvV8, https://youtu.be/TCFvsZeYvV8, 984s)

### What is actually taught
Power of Three = **accumulation, manipulation, distribution (AMD)**, framed as the mechanism
that produces an **open-high-low-close** (bearish) or **open-low-high-close** (bullish)
higher-timeframe candle. Opening caveat, stated before any mechanics: you must first have
higher-timeframe order flow or a draw on liquidity — without one you are only trading patterns.

Definitions given: **accumulation is a range or a consolidation**, which by existing creates
buy stops above its highs and sell stops below its lows. **Manipulation is a false breakout
outside that range**, which simultaneously stops out positions taken inside the range and
induces breakout traders in the wrong direction. **Distribution** is the resulting expansion
in the opposite direction, and it forms the body of the HTF candle while the manipulation
forms the wick.

Two entry windows are offered: a **reversal entry inside the manipulation** (catching the
whole distribution) or a **continuation entry within the distribution** if the first is
missed or disliked.

The concept is explicitly **fractal** — demonstrated on 1-minute, 5-minute and daily candles.
On the 1m example he notes that a market-structure-shift entry was not available (it would
require breaking a distant high), so he used an **inversion** or the **Box setup** (taking the
previous body's low/high of the range) instead — a useful statement that the entry trigger is
selected to fit the geometry.

The most operationally valuable section is the troubleshooting advice: many people cannot find
the consolidation, so **find the manipulation first** — look for aggressive price action out
of and back into a range — and then work backwards to identify the range it manipulated out
of. He repeats the instruction in the final example: find the manipulation, then work backwards to the accumulation.

Targets for the distribution come from **projecting the manipulation leg**: from the low that
made the manipulation high (or vice versa) — he drops to a 30-second chart in one example to
identify the exact low that made the high — then marks the 2–2.5 and 4–4.5 standard
deviations and checks whether existing PD arrays / equal lows / a prior session extreme line
up there.

Daily-candle examples: London manipulates the Asian range then New York distributes higher →
an open-low-high-close daily candle with London as the wick; a second identical case;
a nested 1m AMD inside the New York open using the new day opening gap; and a final example
where the manipulation above midnight open forms the daily wick and the distribution forms
the body down to the −4/−4.5 deviations.

### Concepts introduced
power of three; accumulation, manipulation, distribution (AMD); open-high-low-close /
open-low-high-close; buy stops / sell stops; false breakout; deviation from the range;
Box setup; inversion; failure swings; standard deviation projections (2–2.5, 4–4.5);
new day opening gap and its consequent encroachment; midnight open; fractality;
"find the manipulation first" heuristic; higher-timeframe narrative requirement.

### Rules / conditions stated
- Require a higher-timeframe draw on liquidity / narrative before applying AMD.
- Accumulation = a range/consolidation; it manufactures buy stops above and sell stops below.
- Manipulation = a move **outside** that range followed by an **aggressive move back into** it. If price fails to displace back into the range, expect continuation instead of a reversal.
- Distribution is expected in the direction **opposite** the manipulation.
- Entry either inside the manipulation (reversal) or inside the distribution (continuation).
- If the consolidation is hard to see, locate aggressive out-and-back price action (the manipulation) and derive the range from it.
- Project the manipulation leg for distribution targets: 2–2.5 and 4–4.5 standard deviations; prefer targets that coincide with PD arrays or resting liquidity.
- On the daily candle, the manipulation forms the wick and the distribution the body.

### Examples walked through
1m post-NY-open range, sweep of the morning low, inversion entry, 2R; 5m consolidation
sweeping sell-side into failure swings above; daily open-low-high-close with London as the
manipulation; a second daily case that reaches the new day opening gap; a 1m nested AMD short
with 30-second confirmation of the projection anchor, hitting −2/−2.5 and −4/−4.5; a final
daily short where the manipulation above midnight open caps the day.

### Quotes
- "accumulation is a range or a consolidation"
- "if you struggle to find the consolidations focus instead on the manipulations"

### Open questions / ambiguities
- "Aggressive" move out/back is never quantified (no candle-count, range or ATR criterion).
- No maximum time is given for how long a manipulation may last before it stops being a wick.
- The projection anchor (the low that made the new high) requires a lower timeframe in at least one example — so the anchor is timeframe-dependent and not uniquely defined on the trading timeframe.
- Whether accumulation requires a minimum number of bars, or a maximum range width, is unstated.
- The new day opening gap and its consequent encroachment are used but not defined in this video.

---

## Important Liquidity Levels - Draw On Liquidity - ICT  (YESqIoA7Wyg, https://youtu.be/YESqIoA7Wyg, 768s)

### What is actually taught
The framing device is **the three things a candlestick can do** relative to the previous
candle (credited to "the Strat"):
1. **Consolidation** — fails to take out the previous candle's high **or** low.
2. **One-sided / directional** — takes out one side only (buy-side or sell-side).
3. **Both sides** — takes out the previous candle's high **and** low.

From this: unless price is consolidating, it must be reaching for the previous candle's high,
low, or both — which is why those levels must be marked, **on multiple timeframes**. This is
the channel's cleanest statement of *why* previous-period levels are the draw.

He then applies it in descending order of timeframe: **previous month high/low** (gold daily
chart — repeated draws to previous month's low, one reversal off previous month's high),
**previous week high/low** (weekly walkthrough where he predicts the likely side each week and
openly flags indecision candles where either side is possible), and **previous day high/low**
(deferred largely to the daily bias video, but walked through several days).

Then **session liquidity**. Using the indices killzones (Asia 20:00–00:00, London 02:00–05:00,
NY AM 08:30–11:00) and TFO's indicator with pivots on, he focuses on **displacement or lack of
displacement** around session highs and lows: failing to displace out of one side directs
attention to the other side; a sweep of Asia high that holds, followed by displacement below
Asia low, sets the tone for New York. He projects the **London manipulation** (low→high) and
marks 2–2.5 / 4–4.5 as targets, and shows an old level being used as an **inversion** on the
way down.

The closing top-down example runs monthly → entry: NASDAQ reaches into a **monthly FVG** and
closes respecting its **consequent encroachment** → target = previous month's low → on the
daily there is an **SMT** (NASDAQ makes a lower high while ES makes a higher high — a crack in the correlation) → wait for a daily close below a series of up-close candles → next-day
model targets previous day low → intraday, the Asian range and London high are observed, and
after London high is swept with displacement lower he tracks an **OTE** of that range, enters,
stops above the high, and targets previous day low.

### Concepts introduced
three candle outcomes (consolidation / one-sided / both sides); buy-side and sell-side
liquidity; previous month high & low; previous week high & low; previous day high & low;
session (killzone) highs and lows; draw on liquidity; framing a reversal; displacement and
lack of displacement; standard deviation projection of the London manipulation; inversion;
SMT divergence; consequent encroachment; next day model; OTE; monthly fair value gap.

### Rules / conditions stated
- A candle either consolidates inside the prior candle's range, takes one side, or takes both.
- If not consolidating, anticipate price reaching the previous candle's high and/or low — apply on monthly, weekly and daily.
- Mark previous month, previous week, previous day highs and lows, plus session highs and lows.
- These levels serve two functions: a **draw on liquidity** or a point to **frame a reversal**.
- Trend biases which side is likelier: in a downtrend he expects the previous week's low.
- Lack of displacement out of one side of a session range → look to the other side.
- Displacement below a session low after the opposite side holds → expect continuation into New York.

### Examples walked through
Gold daily with previous month high/low; a multi-week weekly walkthrough including explicit
"indecision" candles; several daily previous-day-high/low sequences; an Asia/London session
example with a London-manipulation projection and an inversion; NASDAQ monthly FVG →
previous month low → daily SMT vs ES → next-day model → OTE short to previous day low.

### Quotes
- "there are three ways a Candlestick can form"
- "these levels are used to frame a draw in liquidity or a reversal"

### Open questions / ambiguities
- Whether "takes out" means a wick through the level or a close beyond it is not stated in the three-outcomes framework (elsewhere he distinguishes reach-vs-close, but not here).
- No rule decides *which* of the two sides is the draw when trend is unclear — he admits uncertainty on doji/indecision candles.
- SMT is used as confluence but is not defined beyond the single crack-in-the-correlation example; the dedicated SMT video in this unit is missing.
- Session times used are the **indices** set; the Forex set is only referenced by link.
- "Displacement" once again unquantified.

---

## Internal & External Liquidity (Daily Bias) - ICT Concepts  (3OivsP1j_UE, https://youtu.be/3OivsP1j_UE, 736s)

### What is actually taught
The tightest definitions in the whole unit, credited to **MMXM Trader**:

- **Internal range liquidity = a fair value gap.**
- **External range liquidity = a swing high or swing low, in the form of buy-side or sell-side liquidity.**

And the governing claim: the market does only two things — it reaches for old highs and lows,
or it seeks to rebalance a fair value gap. Therefore the two alternate:
after taking **external**, price seeks **internal**; after reaching **internal**, price seeks
**external**. This oscillation is the bias engine, and it works on any timeframe — a weekly
chart gives you a week's directional bias.

The conditional that makes it tradeable rather than circular: **respect vs violation of the
internal liquidity decides the next external target.** If the gap is respected, price reaches for external liquidity in the direction of that respect; if it is not respected, the opposite old high becomes the target. Similarly, when price **displaces over** an FVG it
creates an **inversion** and the bias flips.

He also notes the sequencing constraint that appears repeatedly: after taking external
liquidity, there may be **no internal liquidity yet** — you wait for a fair value gap to form
before you have a target — he waits explicitly until one forms.

Top-down examples: gold 60m FVG respected → target the old low (internal → external) → 5m
FVG puts in a high → 1m order block short = 3.23R. GBPJPY: old high taken (external) → weekly
FVG is the internal target → 4H shows the retracements → on reaching internal, eyes flip up to
external; wait for the **change in state of delivery / structure shift** before switching from
a sell model to a buy model → 15m sweep + CISD → order block long → targets 4H external, then
the weekly old high. He labels the nested structure a **market maker buy model within a larger
market maker buy model**. A final NQ 5m example runs the external↔internal rotation
bar-by-bar, including honest admissions that a retracement was skipped and that the sequence is not always perfect.

### Concepts introduced
internal range liquidity (= FVG); external range liquidity (= swing high/low as buy-side /
sell-side liquidity); the external↔internal rotation; respect vs violation of an FVG;
inversion; change in state of delivery / structure shift; market maker buy model and sell
model; buy side / sell side of the curve; failure to displace; order block entry; fractality.

### Rules / conditions stated
- Internal range liquidity = a fair value gap; external range liquidity = a swing high or low.
- After external is taken, the next target is internal; after internal is reached, the next target is external.
- If the FVG (internal) is respected, continue toward the external target in the direction of the respect; if it is violated/closed through, the opposite external target becomes the draw (inversion → bias flips).
- If no FVG exists yet after taking external, there is no internal target — wait for one to form.
- To switch from a sell model to a buy model, require a change in state of delivery / structure shift over the relevant high.
- Applies on all timeframes; a weekly read gives a weekly bias.

### Examples walked through
S&P futures weekly (failure to displace below an old low → internal FVG → external old high →
inversion flipping bias up); gold 60m → 5m → 1m short for 3.23R; GBPJPY weekly/4H/15m nested
market-maker buy model; NQ 5m external↔internal rotation.

### Quotes
- "internal range liquidity is just a fair value Gap"
- "external range liquidity is a swing high or a swing low"

### Open questions / ambiguities
- Which swing high/low counts as "the" external target when several exist is not specified (he uses the obvious/nearest one in examples).
- "Respect" of an FVG is judged visually (bodies not closing through) — no explicit rule here; the IFVG video supplies "close through the CE/the gap" as the violation test.
- The rotation is descriptive, not probabilistic: no statement of how often the sequence completes or how long it takes.
- Whether internal liquidity must be on the same timeframe as the external swing is not stated (he mixes weekly FVG with 4H swings in one example).

---

## Inversion Fair Value Gaps (IFVG) - ICT Concepts  (uDJI2AbyyCs, https://youtu.be/uDJI2AbyyCs, 615s)

### What is actually taught
Starts by restating the **fair value gap** definition: a **three-candlestick pattern in which
the first candle's low does not overlap the third candle's high (bearish/SIBI framing), or the
first candle's high does not overlap the third candle's low (bullish/BISI framing)**. This is
the only explicit FVG definition available in this unit.

**Inversion** = a fair value gap that gets **closed over / disrespected**. A bearish FVG that
price closes above becomes bullish support; a bullish FVG that price closes below becomes
bearish resistance. After the inversion, expect price to either retrace into the old gap and
respect it, or continue directly.

**Consequent encroachment (CE)** = **50% of a fair value gap**, marked with a Fib from the
gap's high to its low. Respect of the CE implies continuation in the respecting direction;
violation of the CE anticipates a move through the gap. He also uses the CE as an **entry
refinement**: in one example a plain inversion entry gave only ~1R, so he entered at the CE of
the old gap instead to satisfy his R:R minimum. A partial signal is acknowledged — closing
over the CE is only a hint, and he still requires a close beyond the whole gap to call it
an inversion.

Second half: inversions **within a trend**. When price trends up, the opposing (bearish) gaps
that fail become entry opportunities on each higher low — he chains several: order block →
order block off it (a **propulsion block**) → the SIBI created there → closes over it → higher
low → new gap → and so on.

Third: **old fair value gaps carried to the other side of the curve**. On the sell side of the
curve, note the fair value gaps; after the **smart money reversal** (CISD, inversion, market
structure shift, a short-term low put in), drag those old gaps forward to the buy side of the
curve and use them as **reaccumulation** support (mirror: old bullish gaps used for
**redistribution** on the sell side). Demonstrated on gold daily: equal highs above, a close
over the SIBI and over the down-close candles, a short-term low forms, then an old sell-side
gap is used as support into the buy-side sweep.

### Concepts introduced
fair value gap (3-candle definition); inversion / inversion fair value gap; consequent
encroachment (50% of the gap); SIBI ("cby/civy") and BISI ("bissy"); order block; propulsion
block; smart money reversal; market structure shift; change in state of delivery;
buy side / sell side of the curve; reaccumulation / redistribution; external vs internal
liquidity (referenced); higher low / higher high trend structure.

### Rules / conditions stated
- FVG = three-candle pattern; candle 1's low does not overlap candle 3's high (or candle 1's high does not overlap candle 3's low).
- Inversion requires a close beyond the gap; closing only through the CE is a hint, not a confirmation.
- After inversion, the old gap acts as support/resistance in the new direction; trade its retest.
- CE = 50% of the gap; respect of CE → continuation; violation of CE → anticipate the gap failing.
- Entry may be moved to the CE of the old gap when the plain inversion entry does not meet the R:R minimum (his example rejects ~1R).
- In a trend, failed opposing PD arrays are trend-continuation entries at each higher low / lower high.
- After a smart money reversal, drag old opposite-side fair value gaps across the curve and use them for reaccumulation/redistribution.

### Examples walked through
EURUSD 60m sweep → 5m bullish FVG closed below → inversion short to the lows; the same chart's
mirror after sell-side is swept (external → internal), using the CE of the old gap for entry;
NQ 2m with a SIBI turned inversion, CE respected, then an order block validated; the same NQ
chart used to chain trend-continuation inversions including a propulsion block; gold daily
old-gap reaccumulation into buy-side liquidity.

### Quotes
- "a fair value Gap is a three Candlestick pattern"
- "those opposing PD arrays that fail are actually opportunities to get into that Trend"

### Open questions / ambiguities
- The FVG definition turns on non-overlap but does not say whether touching (equal) prices count, nor whether wicks or bodies are used.
- A close over the gap implies a body close, but that is not stated; nor is it stated whether the close must be beyond the far edge or merely outside it.
- No expiry rule: how long an inversion stays valid, or how many retests it survives, is not given.
- **Propulsion block** is named once — an order block formed off another order block — and never properly defined here.
- "Smart money reversal" is used as a known term with its components listed (CISD, inversion, MSS) but no ordering requirement is stated.

---

## Liquidity: Buyside & Sellside - ICT Concepts  (U8xH2dEgH5A, https://youtu.be/U8xH2dEgH5A, 595s)

### What is actually taught
The most primitive video in the unit, and the one everything else silently depends on.

**Swing point definition (3-bar fractal):** a swing low is a low with a **higher low to the
left and a higher low to the right**; a swing high is a high with a **lower high on the left
and a lower high on the right**. This is the channel's only explicit swing definition.

**Why swings matter:** trader psychology. Longs entering a move place stops under the swing
low; shorts place stops above the swing high. Therefore **sell stops rest below swing lows =
sell-side liquidity**, and **buy stops rest above swing highs = buy-side liquidity**. "Smart
money will look to pair orders below these lows and above these highs."

A long practice segment walks a 4H chart identifying swings in real time, including the
important sequencing point that a swing is only confirmed once the **right-hand** bar exists, and the observation that when a low fails
to take out the previous low the two become **relatively equal lows** and act as one pool.

**Two liquidity types:** (1) **old highs / old lows** — a single prominent swing standing
alone; (2) **relatively equal highs / lows** — two or more swings at approximately the same
price, or a cluster.

**Levels always marked:** previous week high/low, previous day high/low, session highs/lows
(Asia, London). Each can frame a **draw**, a **reversal**, or a **narrative**.

Two worked days: New York taking London session high, then Asia high, followed by displacement
down into a 5m FVG (no body closes inside), targeting London-session equal lows; then a second
day where all session highs/lows are consumed, so previous day high becomes the remaining
target and price expands through it.

### Concepts introduced
swing high / swing low (3-bar fractal); buy stops / sell stops; buy-side liquidity;
sell-side liquidity; old highs and old lows; relatively equal highs and lows; smart money
pairing orders; previous week high/low; previous day high/low; session highs and lows;
draw on liquidity; framing a reversal; 5-minute fair value gap; break of structure
(mentioned); displacement.

### Rules / conditions stated
- Swing low = a low with a higher low immediately to its left **and** to its right.
- Swing high = a high with a lower high immediately to its left **and** to its right.
- A swing is only valid once the right-hand bar has formed.
- Sell-side liquidity sits **below** swing lows; buy-side liquidity sits **above** swing highs.
- When a new low fails to break the previous low, treat the pair as relatively equal lows (one pool); same for highs.
- Always have marked: previous week high/low, previous day high/low, Asia and London session highs/lows.
- Focus on "the really obvious highs and lows on the outside of the range" — minor internal swings are deliberately skipped.

### Examples walked through
4H swing-identification walkthrough; a New York session using London and Asia session highs
as the draw, then a 5m FVG short into London equal lows; a following day where session levels
are exhausted and previous day high becomes the draw.

### Quotes
- "we have a low right here with a higher low to the left"
- "smart money will look to pair orders below these lows and above these highs"

### Open questions / ambiguities
- The 3-bar fractal definition conflicts with his own practice: he explicitly filters to the obvious swings on the outside of the range, so an unfiltered 3-bar detector will produce far more swings than he uses. No filter rule (range, lookback, ATR) is given — this is the single biggest gap for automation.
- "Relatively equal" has no tolerance (points, pips, ATR fraction, or tick count).
- Whether swing detection uses wicks or bodies is not stated (examples use wicks).
- Session times are not given in this video (deferred to the killzone video).

---

## Mitigation Blocks Simplified - ICT Concepts  (bbWPoajy2MY, https://youtu.be/bbWPoajy2MY, 622s)

### What is actually taught
A mitigation block is defined **by contrast with the breaker**: where a bullish breaker needs
low → high → **lower low** → higher high (i.e. a sweep), a bullish mitigation block only needs
low → high → **higher low** → higher high — no sweep. The bearish mitigation block is
high → low → **lower high** → lower low; he verbalises exactly that sequence on the chart.
The zone is the down-close candle (bearish) / up-close candle (bullish) at the failure swing,
marked and dragged forward.

Then the honest part: **he generally does not like trading them.** Because no high/low was
swept, the failure swings that a mitigation block leaves behind are themselves liquidity — they are
precisely what he targets — so price tends to run straight through the block
later. He shows a mitigation block failing for exactly this reason.

**The one exception:** he will trade a mitigation block when there is an **SMT at the low** —
i.e. the correlated instrument *did* sweep, so it has a breaker there and the unswept
instrument should not reach that low. Demonstrated on YM with NQ making a higher high
(SMT) at the corresponding point; the down-close candle before the failure swing is marked and
reacts twice.

The larger use case is **inside market maker models**: on the sell side of the curve, order
blocks form; after price reaches a higher timeframe level and shifts structure (the smart
money reversal), those **old order blocks from the left side of the chart are dragged across**
and used as reaccumulation (or redistribution) zones on the other side of the curve. He looks
for a PD array **within** the mitigation block for the reaction (an FVG, a volume imbalance).
He also states plainly that "**a breaker is a form of mitigation**" and that mitigation amounts to dragging old highs forward and trading their retest.

### Concepts introduced
mitigation block (bullish/bearish); failure swing; breaker block (as contrast); SMT
divergence; smart money reversal; market maker model; buy side / sell side of the curve;
reaccumulation / redistribution; old order blocks dragged across; PD array inside a
mitigation block; volume imbalance; weekly/hourly fair value gap as the HTF point of interest;
market structure shift; discount of the range.

### Rules / conditions stated
- Bullish mitigation block: low → high → higher low → higher high (no sweep of the prior low).
- Bearish mitigation block: high → low → lower high → lower low (no sweep of the prior high).
- Zone = the down-close candle (bearish) or up-close candle (bullish) at the failure swing; wick-vs-body is left to the user.
- Higher probability when it overlaps a fair value gap.
- Default stance: avoid trading them, because the unswept failure swings become targets.
- Exception: trade it when an **SMT** exists at that low/high (the correlated instrument swept and has a breaker).
- In market maker models: after the smart money reversal, drag old opposite-side order blocks across the curve; require a PD array inside the block for the reaction.

### Examples walked through
GBPUSD 60m mitigation blocks (one works with an FVG overlap, the next fails as price runs the
failure swings); YM 5m with NQ SMT at the low — the exception case, two reactions; gold 4H
after a weekly-FVG smart money reversal, dragging old bearish order blocks across for
reaccumulation to the upside; a case where a breaker is marked and explicitly called a form of
mitigation; oil daily redistribution using old order blocks on the way down.

### Quotes
- "with a mitigation block we just have to make a lower low here"
- "a breaker is a form of mitigation"

### Open questions / ambiguities
- Whether a mitigation block requires displacement/CISD through the block to be "activated" is not stated as a rule, though he mentions that having closed below the block he could enter on its retest.
- Wick vs body marking is explicitly left open.
- SMT is used as the qualifying filter but is not defined here (dedicated SMT video missing from this unit).
- "PD array within the mitigation block" is required for the reaction but the acceptable array types are only illustrated (FVG, volume imbalance), not enumerated.
- No rule for how far back on the curve old order blocks may be dragged, or how many.

---

## Optimal Trade Entry (OTE) - ICT Concepts  (1YRs4Z1lMws, https://youtu.be/1YRs4Z1lMws, 765s)

### What is actually taught
The most numerically precise video in the unit. **Fib settings used: 0.5, 0.62, 0.705, 0.79,
1.0** (0 and 1 at the range ends). The **OTE zone is 0.62 → 0.79**, with **0.705 as the
midpoint** and the preferred entry; 0.5 marks discount/premium.

**Anchoring:** find a swing high and a swing low and drag the retracement **from the swing
high to the swing low** (bearish framing) or low→high (bullish). While the extreme is still
extending, keep re-anchoring ("I can continue to drag this up as we form our range... until a
swing high is put in") — the fib tracks the developing range exactly like the premium/discount
box does.

**Use:** after the range is defined, look for a retracement into 0.62–0.79 and take the entry
there, or drop a timeframe and use a lower-timeframe entry model within that zone.

**Confluence:** he explicitly looks left for PD arrays inside the OTE zone — a fair value gap,
up/down-close candles, an order block. When an order block's **opening price** falls outside
the OTE, he uses the order block's **mean threshold (50% of the body)** instead so the entry
sits inside the OTE. He notes others might use the volume imbalance in the same spot and says
he simply focuses on which PD array catches his eye.

**Nesting:** once price leaves an OTE and forms a new swing, a *new* range and a *new* OTE
exist; he shows the daily displacement range's OTE containing an hourly OTE, then tracking
lower-timeframe OTEs as new lows print.

**Filters shown in the examples:** a retracement into the OTE that occurs **outside the
killzone** is ignored because it falls outside the killzone; once inside the
killzone, the 0.79 tag with the hourly FVG bodies still respecting is taken. Entry preference:
0.705 ideally, 0.62 when he wants to be in the position.

Last example combines a TGIF/weekly-range idea with a projection (2–2.5 of the reversal leg
landing just above failure swings) and then an OTE long for 3.4R.

### Concepts introduced
optimal trade entry (OTE); fib levels 0.5 / 0.62 / 0.705 / 0.79 / 1; discount and premium;
swing high / swing low anchoring; PD array confluence; mean threshold of an order block;
volume imbalance; displacement range; nested OTEs across timeframes; killzone filter;
failure swings; standard deviation projection; TGIF; daily open as resistance; breaker
(as an OTE confluence); equal lows as generated liquidity.

### Rules / conditions stated
- Fib settings: 0.5, 0.62, 0.705, 0.79, 1.
- OTE = 0.62 to 0.79 of the retracement; 0.705 is the midpoint and the preferred entry; 0.62 is the "want to be in it" entry.
- Anchor from swing high to swing low (or low to high); re-anchor while the extreme extends until a swing point is confirmed.
- Look for PD arrays inside the OTE zone as confluence.
- If an order block's opening price is not inside the OTE, use its mean threshold (50% of the body).
- Ignore OTE taps that occur outside the killzone.
- After exiting an OTE and forming a new swing, mark the new range and its OTE.

### Examples walked through
A bearish fib drawn high→low, price returning to 0.705 then reaching sell-side; a bullish
example running out of the OTE to an overhead FVG; confluence hunting (FVG + up-close candles;
an order block whose mean threshold sits in the OTE, next to a volume imbalance);
EURUSD daily → hourly nested OTEs, one ending at a breaker; gold hourly → 5m → 1m with the
killzone filter and a 3R order-block entry; ES weekly TGIF framing with a projection and a
3.4R OTE long.

### Quotes
- "That's this zone from the 62 to the 79 including the midpoint of 705."
- "I have a fair value gap and an optimal trade entry"

### Open questions / ambiguities
- Which swing pair to anchor is discretionary; the displacement range is used as the anchor in several examples without a formal rule.
- Whether the fib is drawn wick-to-wick or body-to-body is not stated.
- The killzone filter is applied in an example but never stated as a rule.
- Invalidation of the OTE (a close beyond 0.79? beyond 1.0?) is never specified — stops in the examples sit at the swing extreme.
- No statement about whether a tag of 0.62 alone (without reaching 0.705) counts as an OTE fill.

---

## Order Blocks Simplified - ICT Concepts  (DMUiDBnTYc8, https://youtu.be/DMUiDBnTYc8, 898s)

### What is actually taught
The order block is defined as an event sequence, not a candle shape:
price reaches **an important level** → creates buy-side (or sell-side) liquidity →
**sweeps** it → then **displaces and closes below (above) the opening price** of the single or
series of up-close (down-close) candles into that level. That close **validates** the candles
as an order block; the retest is then used as resistance (support).

Two qualifications are stated with unusual force. First, the sweep is **preferred but not
strictly required** — he states he prefers it and always waits for one. Second, and emphatically, **the important level is mandatory** — the same pattern at a random chart location is explicitly not an order block. He proves it with a losing 5m trade whose order-block candidate had no HTF level behind it, then reframes the same market from the hourly (an hourly FVG),
producing a valid order block that wins.

**Mean threshold** = 50% of the order block measured **body low to body high** (a 0.5 fib on
the bodies). Ideal behaviour: no closes beyond the mean threshold. Its practical use is entry
refinement when the candle series is large and the opening price gives poor R:R — he shows
1.3R at the opening price becoming ~2.6R at the mean threshold, with the explicit trade-off
that the deeper entry may never fill.

**Order blocks on the buy/sell side of the curve (continuation):** after the smart money
reversal, he looks for a **down-close candle into an important level** where the important
level is one of exactly three things: **(1) a previous order block, (2) a fair value gap, or
(3) a sweep of a swing low**. The close over that candle validates a new order block for
continuation. This is the clearest enumeration of "important level" in the unit.

**Stops:** either the swing high/low or the far end of the order block. He states his own
preference clearly — put the stop on the swing and **adjust the entry** (via mean threshold or
FVG) to improve R:R rather than moving the invalidation closer to the entry, because a
stop at the order block's edge can be wicked while the trade is still valid.

### Concepts introduced
order block (bullish/bearish); opening price as the level; important level / higher timeframe
PD array; sweep; displacement; change in state of delivery (as the validating close);
mean threshold (50% of bodies); order blocks on the buy side / sell side of the curve;
smart money reversal; failure swings; equal highs; inefficiency / fair value gap;
propulsion-style stacking of successive order blocks; stop-loss placement philosophy;
previous month high as the important level.

### Rules / conditions stated
- Bearish order block: up-close candle(s) into an important level → (preferably) a sweep of buy-side liquidity → a close **below** the opening price of that candle/series → validated.
- Bullish order block: down-close candle(s) into an important level → (preferably) a sweep of sell-side liquidity → a close **over** the opening price → validated.
- The level is marked at the **opening price** of the (first) candle.
- **No important level ⇒ no order block**, regardless of the candle pattern.
- Important levels enumerated for continuation entries: a previous order block, a fair value gap, or a swept swing low/high.
- Mean threshold = 50% between body low and body high; ideally no closes beyond it.
- Use the mean threshold when the series is large and the opening-price entry gives insufficient R:R (his examples target ≥2R).
- Stop on the swing high/low (preferred) or the far end of the order block.
- A candle that never reached an important level is not an order block even if its opening price is closed through.

### Examples walked through
A 5m order-block candidate with no HTF level → stopped out; the same market framed from an hourly FVG
→ 5m order block → 2R win; oil 5m where the opening-price entry gives 1.3R and the mean
threshold gives ~2.6R; an Asia-lows sweep before New York with an FVG entry vs an order-block
entry vs a mean-threshold entry compared side by side; a previous-month-high continuation
sequence with successive order blocks, including one candidate rejected for never reaching an
important level; a final continuation long where the mean threshold coincides with a small
inversion for 2.5R.

### Quotes
- "the most important part on this slide is waiting for an important level"
- "I don't want to see any closes below the mean threshold"

### Open questions / ambiguities
- "Displacement" accompanying the validating close is required by wording but never quantified.
- Whether the candle series must be contiguous up-close candles is not stated.
- "Important level" is enumerated for continuation entries (previous OB, FVG, sweep) but the reversal case just says "higher timeframe PD array" — the full list is open.
- The mean threshold uses bodies; the order block level itself uses the opening price; the *zone* boundaries (does the block extend to the high/low of the candle?) are never defined.
- No expiry/invalidibility rule: how many touches an order block survives, or when it is dead, is not stated (beyond closes through the mean threshold being undesirable).

---

## Position Sizing For Trading - Futures & Forex  (0OjlQ91TZiU, https://youtu.be/0OjlQ91TZiU, 672s)

### What is actually taught
The only risk-management video in the unit, and the only one with arithmetic.

Core argument: the familiar win-rate × risk-reward profitability table **only holds if risk per
trade is constant**. Worked counterexample: a fixed 1:2 system at 50% win rate is +1R over two
trades when both risk $1,000; but risking $2,000 on the loser and $1,000 on the winner turns
the same sequence into break-even.

Three sizing methods are compared: **fixed contract size** (rejected), **fixed dollar risk**,
and **fixed percentage risk** (both endorsed). The fixed-contract example uses 2 NQ contracts
with 20-, 40- and 10-point stops = $800, $1,600 and $400 of risk — so a −1R, −1R, +4R sequence
finishes **−$800** instead of +2R. Under fixed dollar risk the same sequence finishes **+$2,000**.

**Sizing formula (as demonstrated):** contracts = defined risk ÷ value-per-point ÷ stop size in
points. NQ is $20/point, ES is $50/point. Examples: $1,000 ÷ 20 ÷ 20 = 2.5 contracts;
$1,000 ÷ 20 ÷ 40 = 1.25 contracts = 12.5 micros (he **rounds down**); $1,000 ÷ 20 ÷ 10 = 5
contracts = 50 micros. **Micros = minis × 10** (one-tenth the size), and he prefers micros
precisely because they allow finer sizing. For CFDs/forex, decimals are available so the
constraint disappears; he uses per-pip/per-point value from the broker.

**Tooling:** two shared Google Sheets calculators (futures and forex — make a copy of the file,
and do not request access), and TradingView's risk/reward tool, which must be configured per
instrument: forex EURUSD with lot size 1,000 gives a quantity directly; futures require lot
size **1** to produce correct contract quantities, and templates should be saved per account
size and instrument.

**Prop firms:** the headline account size is not the risked capital — **the drawdown is**.
A "25k account" with $1,500 drawdown means 1% of account = ~1.7% of drawdown, and six or seven
losses blow it. So he sizes off the **drawdown amount**, targeting **7–10% of drawdown per
trade**, which gives roughly **10–15 consecutive losses** of survival. After passing the
evaluation and being funded he **lowers risk** to increase the cushion. Same logic, different
numbers, for forex prop firms.

### Concepts introduced
position sizing; fixed contract size vs fixed dollar risk vs fixed percentage risk;
1R; win rate vs risk-to-reward table; value per point; micros vs minis; rounding down;
TradingView risk/reward tool configuration; prop firm drawdown-based sizing; evaluation vs
funded risk.

### Rules / conditions stated
- Keep risk per trade constant, or the win-rate/RR table does not apply.
- Prefer fixed dollar or fixed percentage risk over fixed contract size.
- Contracts = risk $ ÷ value per point ÷ stop size (points). NQ $20/pt, ES $50/pt.
- Micros = 10× the contract count of minis; round **down** to a whole micro.
- Forex/CFD: use the broker's per-pip value; decimals allowed.
- TradingView RR tool: lot size 1,000 for forex, lot size 1 for futures; save templates per account size.
- Prop firms: size off the **drawdown**, not the nominal account size; risk 7–10% of drawdown per trade in an evaluation (≈10–15 losses of runway); reduce risk once funded.

### Examples walked through
The 1:2 / 50% win-rate two-trade arithmetic with and without constant risk; the three
fixed-contract NQ scenarios and their inconsistent dollar risk; the same sequence under fixed
dollar risk; three sizing calculations converted to micros; the two spreadsheet calculators;
TradingView RR tool configuration for EURUSD and NQ (2.817 contracts → 28 micros);
the 25k prop account with $1,500 drawdown.

### Quotes
- "this table only works out if you have the same risk per trade"
- "I'm not looking to risk 1% of the overall account size"

### Open questions / ambiguities
- The auto-transcript garbles several dollar figures ("$11,000" for $1,000, "$994,000", "17%" for 1.7%, "2.81 7" / "2.18" for 2.817 contracts) — the arithmetic is reconstructable but the raw numbers in the transcript are unreliable.
- The exact percentage risk per trade for a normal (non-prop) account is never stated — only that it must be constant; the examples use 1%.
- Commissions, slippage and spread are not included in any calculation.
- No guidance on correlated concurrent positions or total portfolio heat.
- The post-funding risk reduction is not quantified.

---

## Not yet available

These 6 videos are listed in `study_units.json` for `the_foundation_01` but no transcript
exists at `research/raw/transcripts/<video_id>.txt` (the crawl was interrupted by a YouTube IP
block). **Nothing about their content has been recorded or inferred** — titles are reproduced
only for re-fetch purposes.

| video_id | title | duration (s) |
|---|---|---|
| MsuEQQl7L6s | Candle 3 Closure: TTrades Fractal Model | 719 |
| FGkb_50BfT8 | High Resistance vs Low Resistance Liquidity - ICT Concepts | 702 |
| sIcsLFSNoXM | Open High Low Close - Understanding Candlesticks | 850 |
| wik00c9_2nk | Reversal Sequence (TTRS) - How To Blend PD Arrays | 1025 |
| 27S9gjgcSlI | SMT Divergence - ICT Concepts | 1027 |
| ubCe509_JLY | Timeframe Alignment: How To Align Timeframes For Expansion | 976 |

Known consequences of these gaps for this unit:

- **SMT divergence** is used as a *required filter* for trading mitigation blocks (bbWPoajy2MY)
  and as confluence in a top-down example (YESqIoA7Wyg), but its dedicated video is missing, so
  the concept can only be recorded as underspecified.
- **Open-high-low-close / open-low-high-close** is used as the daily-candle vocabulary in both
  the Power of Three (TCFvsZeYvV8) and daily bias (g3oDYq4P9ZE) videos; the dedicated
  candlestick video is missing.
- **High-resistance vs low-resistance liquidity** is never referenced in any available
  transcript in this unit — no partial coverage exists.
- The **TTrades Fractal Model** candle sequence (C1/C2/C3) is referenced only obliquely; the
  Candle 3 Closure video is missing, so the fractal-model candle vocabulary is not covered here.
- **Timeframe alignment** is practised constantly in the top-down examples but never stated as
  a rule set; its dedicated video is missing.

Concepts named but **not substantively taught** anywhere in the available transcripts (recorded
here so a later pass does not mistake a passing mention for coverage): propulsion block,
volume imbalance, new day opening gap, TGIF, market structure shift (used, never defined),
smart money reversal (used repeatedly, components listed but never formally defined),
true day open / midnight opening price, dealing range, next-day-model attribution to
MMXM Trader, "the Strat" (source of the three-candle framework).

