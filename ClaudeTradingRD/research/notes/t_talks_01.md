# Unit notes — `t_talks_01` (playlist: "T Talks", batch 1 of 3)

Six guest interviews. TTrades hosts; the guest does nearly all the talking and screen-shares
their own charts. All six transcripts are present and readable (auto-en captions, no timestamps
embedded — therefore **no `approx_time` values are recorded anywhere in this unit**).

Important framing: these are *other people's* models, not TTrades' own. Where a guest
contradicts TTrades' published material (e.g. DTR entering inside Candle 2 rather than waiting
for the C2 close) that is recorded as stated, not smoothed over. Guests also cite each other —
DTR explicitly builds on AM Trades' expansion model, Ash Trades' unicorn model, and TTrades'
fractal model — so the same term can carry slightly different rules in different videos.

---

## $niper | Internal & External Liquidity - ICT Daily Bias
(`5aRB_ZY3474`, https://youtu.be/5aRB_ZY3474, 1626s)

### What is actually taught

Matt (a.k.a. $niper) presents a single-axis reading of price: the market only ever does two
things, and everything else is decoration. **External range liquidity** is old highs and lows.
**Internal range liquidity** is fair value gaps. Price alternates between them — when internal
range liquidity is tagged, the draw becomes external range liquidity, and when external is
taken, the draw becomes internal. (The transcript garbles this sentence, saying "internal"
twice; the alternation is unmistakable from the six worked examples that follow, but the
verbatim wording is corrupt.) He credits ICT for the concepts and the MMXM Trader for the
framing.

The second half of the method is **timeframe alignment**. You identify the internal/external
reaction on a higher timeframe, then drop to a specific paired timeframe to watch the reaction
and to execute. He states the pairs explicitly: monthly→daily, weekly→4H, daily→1H, 4H→15m,
1H→5m, 15m→1m. The higher timeframe supplies the key level; the paired lower timeframe supplies
the market structure shift. The trigger is a *candle close* above (for longs) a swing high after
price has reacted from the HTF level; entry is on the retracement into the resulting fair value
gap or breaker block; the stop rests at the low that tagged the level.

Layered on top are two confluences. **SMT divergence** taken at the moment price runs into the
HTF level is called an "extra confluence booster" and is used at both HTF (daily/weekly) and LTF
(1-minute) scale. **Advanced market structure** labelling — long-term / short-term /
intermediate-term highs and lows — supplies the refined entry: after price forms a long-term
low inside the HTF level, a short-term low that gets violated creates an intermediate-term low,
and the *short-term low to the right of that intermediate-term low* is the preferred entry (and
the mirror for shorts). He also reads daily candles by body, not wick — a level is holding while
the daily bodies fail to close through it even though wicks pierce it ("the wick is just doing
the damage").

He walks a personal execution rule: he does not execute on indices before the 09:30 equities
open, so a 4H-derived 15-minute setup that matures pre-open is *not* traded; instead he uses the
15-minute PD array as the new HTF reference and drops to the 1-minute after the open. Targets
are the opposing internal/external pool, optionally measured with standard deviation
projections (he shows a 1:2 to 1:2.5 example). Order blocks / up-close candles sitting on the
sell-side of the curve are treated as **mitigation blocks** marking reaccumulation.

### Concepts introduced (speaker's own terminology)
- "external range liquidity" (old highs and lows) / "internal range liquidity" (fair value gaps)
- "draw on liquidity"
- timeframe alignment (explicit HTF→LTF pairs)
- "market maker buy model" / "market maker sell model"
- SMT divergence as a "confluence booster"
- advanced market structure: long-term / short-term / intermediate-term high and low
- mitigation blocks (up-close candles on the sell-side of the curve)
- "energetic swing" (the impulsive leg used to measure premium/discount)
- change in state of delivery; breaker block; inversion gap
- "the body is telling us the story"

### Rules / conditions stated
- External range liquidity = old highs and lows. Internal range liquidity = fair value gaps.
- Tagging one type makes the *other* type the next draw.
- Apply the internal/external read on monthly, weekly, daily and 4H to build bias.
- Watch the reaction to a level on the paired timeframe: monthly→daily, weekly→4H, daily→1H,
  4H→15m, 1H→5m, 15m→1m.
- Trigger = a candle **close** above a swing high (long) / below a swing low (short) on the
  paired timeframe after the HTF level is tagged.
- Entry = retracement into the resulting fair value gap or breaker block after that close.
- Stop = the low (long) / high (short) that tagged the internal or external range.
- Preferred entry after advanced-structure labelling = the short-term low immediately to the
  right of the intermediate-term low (mirror for shorts).
- The internal range FVG that is the draw should sit in **premium** of the swing measured from
  the low that took external liquidity to the most recent energetic swing high.
- SMT divergence should be checked at the moment the HTF level is reached.
- No execution before the 09:30 equities open ("this is consistent to my rules prior to the
  equities open"); use a pre-open PD array as a reference level instead.
- Read daily reactions by candle **body**, not wick.

### Examples walked through
- NASDAQ hourly→5m: external high taken, draw into hourly bullish FVG with SMT vs S&P, close
  above swing high, 5-minute market maker buy model, two entry options (5m FVG or 5m bullish
  order block), target 17,5xx.
- Oil daily market maker sell model: external low taken, retrace to internal FVG in premium,
  hourly advanced market structure (LTH → STH → ITH) with the short-term high to the right of
  the ITH as the short entry.
- NASDAQ weekly bullish FVG → 4H reaction with SMT → 15m discounted FVG → 1-minute market maker
  buy model (CISD + bullish order block + inversion gap used as support).
- S&P daily external low with SMT vs NASDAQ → hourly bullish FVG in discount → 5-minute advanced
  market structure (LTL → STL → ITL).
- Daily internal→external example with YM SMT, ending in an hourly bullish breaker block tagged
  in the New York PM session; entry there, stop below, TP at 2–2.5 standard deviations (~1:2 to
  1:2.5).

### Quotes (verbatim, transcript-checked)
- "external range liquidity is just old highs and lows"
- "the wick is just doing the damage"

### Open questions / ambiguities
- The alternation sentence is corrupted in the caption; the rule is inferred from the examples.
- "Energetic swing" is never defined (no displacement or size threshold given).
- No rule for *which* fair value gap counts as the internal range pool when several exist.
- The timeframe pairs are asserted, never justified, and 15m→1m breaks the ratio pattern of the
  others.
- Whether the swing-high "closure" must be a body close is not stated (contrast AP, who is
  explicit about body closes).
- The SMT reference instrument is assumed (NQ/ES, NQ/YM) but no rule for choosing it is given.

---

## AM Trades | Blending The Economic Calendar, Daily Chart, & Weekly Profiles
(`QmGJFxfSHxM`, https://youtu.be/QmGJFxfSHxM, 1789s)

### What is actually taught

AM trades ES and NQ futures, mostly NQ, and states his whole objective up front: he only wants
**large-range trending daily candles**. Everything in the video is a filter for finding which
*days* those will be, and he insists this happens before any hourly confirmation and long before
any entry. The process has three ordered steps: economic calendar, then the daily chart, then
the weekly profile.

Step one is a three-tier classification of red-folder USD news. **High impact** is exactly three
events: CPI, the FOMC press conference (2:30 ET Wednesday, distinct from the 2:00 statement and
from the minutes/Powell speeches), and non-farm payroll (first Friday). These are defined as
events big enough to shape the *weekly* range, so you avoid the days before them and concentrate
on the days after. **Medium impact** is GDP, PCE, PPI — usually 08:30 — significant enough to
shape the *daily* range, so he will neither enter before the release on that day nor hold
through it. **Low impact** is everything else (10:00 events, unemployment claims); these give
intraday energy only. He explicitly rejects the common practice of using single news events to
*predict* the weekly high and low, because a release can enter as expansion, as manipulation, or
fall flat.

He then states a hard rule: he never trades Monday. His stated reasons are that Monday is on
average the smallest-range day, that Monday carries no news, and — the structural argument —
that on Monday there is no weekly-profile data to reference, so trading it means predicting from
nothing. Monday is instead used as *input*: what Monday did informs what the rest of the week
should do.

Step two is the daily chart, read purely as **phases of price delivery**. The stated tendency is
that an expansion is never followed directly by another expansion; an intermediate phase —
retracement, reversal, or consolidation — must come first. So after a large-range week close, he
is looking for that intermediate phase and deliberately holds back from getting on side with a
"new expansion" too early. If the daily is in a range/consolidation, he only takes interest in
the external high and external low.

Step three pairs the observed days with a named **weekly profile** (classic expansion,
consolidation reversal, midweek reversal). The confirming trigger for the manipulation is an
**hourly change in state of delivery**, ideally landing on a medium/high-impact release; once
the profile is confirmed he trades continuations on the following days at New York open, in the
AM session only (PM-session runs are explicitly ignored).

He closes with a process argument that most of the audience's PD-array problems are context
problems: an order block "is just an opposing closed candle" — what needs learning is *when* to
apply it. Trading only on-side of large ranges also fixes trade management, target-hitting and
the mental strain of chopping days.

### Concepts introduced (speaker's own terminology)
- high / medium / low impact news tiering
- "avoid the days prior", NFP protocol, FOMC protocol
- "I do not trade Mondays"
- phases of price delivery (expansion, retracement, reversal, consolidation)
- weekly profiles: classic expansion, consolidation reversal, midweek reversal
- change in state of delivery (hourly) as manipulation confirmation
- "external low" / "external high" of a daily range
- AM session vs PM session as a validity filter

### Rules / conditions stated
- High impact = CPI, FOMC press conference, non-farm payroll. Medium = GDP, PCE, PPI.
  Low = everything else.
- Avoid the days *before* a high-impact event; concentrate on the days after.
- Never hold a trade through a high- or medium-impact release; do not enter before a medium
  release on that day.
- Never trade Monday. Use Monday's range as data for the following days.
- NFP week: no Monday; cautious Tuesday/Wednesday (only on a "really specific and convincing
  signature"); avoid Thursday; trade Friday after the release.
- FOMC week: avoid Monday, avoid Tuesday, avoid anything before 2:30 Wednesday; trade Thursday
  and Friday based on how the event entered.
- Daily chart never goes expansion → expansion; expect retracement, reversal, or consolidation
  in between.
- While the daily is a range/consolidation, only the external high and external low are of
  interest.
- Manipulation must be "aggressive and fast and convincing"; shallow, unconvincing returns into
  the range are not manipulation.
- Confirmation of manipulation = hourly change in state of delivery (close through the opposing
  candle that dug into the swept level).
- Only AM-session New York setups count; a run on an external level during the PM session is
  ignored.

### Examples walked through
- Week of 26 Feb: no high-impact event; Monday skipped; Tuesday's AM low failed to run the
  external low (invalid); Wednesday's 08:30 gave nothing; Thursday's 08:30 ran the external low
  and returned into the range with an hourly CISD → **consolidation reversal** profile, entered
  in the wick, held overnight, re-entered Friday at NY open.
- Week of 4 Mar (NFP week): Monday skipped but used as data; ES showed a run above previous
  week/day high with a close below the up-close candle (CISD) plus NQ SMT → short Tuesday under
  a **classic expansion** profile; Wednesday's overnight invalidation → avoid Thursday; Friday
  NFP ran the external high of the internal week range → short with intraday SMT + LTF CISD.
- Week of 11 Mar: CPI Tuesday; the week opened inside a consolidation with an unrun external low
  as the draw; CPI's run higher read as manipulation; Wednesday's hourly close below the
  up-close candle after sweeping the previous high → **midweek reversal** profile; shorts at NY
  open Wednesday, Thursday, Friday.
- Forward plan for week of 18 Mar (FOMC Wednesday 2:30): avoid Monday, Tuesday and all of
  Wednesday pre-2:30.

### Quotes (verbatim, transcript-checked)
- "I do not trade Mondays that is an indisputable thing for me"
- "an order block is just an opposing closed candle"

### Open questions / ambiguities
- "Large range" is never quantified — no ATR multiple, no point threshold.
- The Monday statistic is stated as "the smallest Range Day by under 25% of the average", which
  is ambiguous (25% smaller than average? under 25% of the average?) and unsourced.
- Only three weekly profiles appear here; the full profile set is assumed from elsewhere.
- The AM session window is never given exact clock bounds (he points at the 09:00/10:00 candle).
- "Really specific and convincing signature in price" (the NFP-week Tuesday exception) is not
  defined beyond the one worked example.
- The intermediate phase between two expansions can be any of three things, with no stated test
  for telling which one is forming in real time.

---

## AP | Use Market Structure & Fibonacci Levels for Sniper Entries
(`gjoRPszj-Qk`, https://youtu.be/gjoRPszj-Qk, 4148s)

### What is actually taught

AP presents what he calls the **GB model** (internal nickname "Yeet"), a fixed set of Fibonacci
retracement levels layered on strict market structure. He is explicit that he no longer counts
himself an ICT trader; he uses order blocks, imbalances and measured moves but treats the levels
as the primary edge.

The levels, anchored from a swing low to a swing high (settings shown on screen): **0.295, 0.41,
0.705, 0.7475, 0.79**. He gives the derivation: 0.295 is the polar opposite of 0.7475, and 0.41
is "a negative one deviation away from" 0.705. He claims never to have seen 0.295 and 0.41
discussed elsewhere and calls them "a cheat code".

Before any level is drawn, structure must be valid. His definition of a flip is a **close beyond
the last valid swing** — he complains at length that people mark a random low on the right of the
chart as a market structure shift. Once price closes above a prior high, the low behind it is a
**strong low** that should not be revisited, and it becomes the anchor; the opposing extreme is
the **weak high**. He also uses failure swings: when price fails to make a new high, the lows
that produced that failure swing become the draw.

Two entry techniques come out of this. **Technique one** — after a valid flip, wait for the
retracement into 0.7475 (or 0.705/0.79 as the zone) and take a blind limit; target 0.41 and
0.295. He says 90–95% of his trades are blind limits at these levels. Which target you take
depends on conditions: in a consolidating market exit at 0.41/0.295, in a cleanly expanding
market hold for a new high/low. **Technique two** — trading *back into* the range: wait for a
body close through 0.41, require **displacement away** from it, then take the retracement back
to 0.41 (or 0.295 when trading out of the range) as the entry for the move to 0.7475/0.705/0.79.
He claims roughly 80% of the time a close beyond 0.41 produces that retracement leg.

His body-close rule is a distinct idea: when a level is pierced by a wick, he requires a true
body close beyond the *wick's* extreme before accepting it; leaving a heavy wick at a key level
means the level is being supported. He also refuses to call a candle an order block unless it is
the candle that produced a break of structure (a close above the previous high). Around each
level he insists on a second thing lining up — an unmitigated order block, an imbalance, a
"CSS", the 50% of an internal flip zone, a peak-consolidation/volume node, or the 50% of an
extreme wick (which he also uses as a stop-buy continuation entry). He notes direct imbalances
against the trade mean more drawdown should be expected, and that SMT only matters at the
extremes — did one index mitigate a swing or clear a weak high while the other failed — not
inside a range.

He demonstrates the same levels on daily, 4H, 15m, 5m, 1m and 5-second charts to argue the model
is fractal, and closes with a discipline segment: trading demands unusual discipline, imposter
syndrome is normal, and "time is your friend" — the process should not be rushed.

### Concepts introduced (speaker's own terminology)
- "GB levels" / "GB model" / "Yeet"
- 0.295, 0.41, 0.705, 0.7475, 0.79 (with the stated derivations)
- "valid flip", "strong low", "weak high", "failure swing"
- "true body close" (below/above the wick, not just the level)
- "S&D structure" (the structure responsible for a break)
- "CSS" (an order-block variant with more rules — not defined here)
- "peak consolidation area" / volume node
- "devil's mark" (his name for a wickless candle)
- "blind limit"
- "fractal" (low/high pair that repeats on a lower timeframe)
- "second continuation confirmation"

### Rules / conditions stated
- Fib anchor: swing low → swing high of the range created by a valid flip.
- A market structure shift = a close beyond the **last valid** swing, not any low/high.
- After a close above a prior high, the low behind it is a strong low; do not expect a return
  to it; that anchors the range.
- Technique 1: blind limit at 0.7475; target 0.41 / 0.295 in consolidating conditions, target a
  new high/low in expanding conditions.
- Technique 2: require a **body close** through 0.41 **and displacement away** from it before
  trading the retracement back into the range.
- First close beyond 0.295 is "riskier"; the close beyond 0.41 is the ~80% signal.
- Body-close rule: if a wick pierces a level, wait for a body close beyond the wick's extreme;
  a heavy wick with no such close means the level holds.
- A candle only qualifies as an order block if it caused a break of structure (closed above the
  previous high).
- Require at least one additional POI aligned with the level (unmitigated OB, imbalance, 50% of
  an internal flip zone, peak-consolidation/volume node, 50% of an extreme wick).
- Prefer the **second** continuation/structure break, not the first flip (first flips fake).
- SMT is only meaningful at extremes (weak highs, swing mitigation), not intra-range.
- When price fails to make a new high, the draw is the lows that produced the failure swing.
- Extreme-wick entry: measure the wick, take its 50%; buy-stop above the candle with the stop
  below the low.

### Examples walked through
- MNQ daily/4H: repeated wicking at 0.295 (21,093.50), failure swing high → draw to the lows;
  4H entry at 0.41 (20,568.25) with a wick, ~13 points of drawdown; then the body close below
  0.41 with displacement, retrace, and continuation to the 0.705/0.7475/0.79 zone.
- 5-minute example: valid flip, consolidation at 0.295, blind limit at 0.7475 into a
  50%-of-internal-flip confluence, exit at 0.41/0.295, then a continuation re-entry after the
  body close above 0.295.
- 1-minute examples: 0.295 consolidation at 19,467.5; unmitigated order block + wick + 0.295
  alignment; entries with 2.25 points and 3 ticks of drawdown; direct-imbalance caveat.
- 5-second examples: strong-high determination (19,664.75), body close above 0.41 at 19,631.75,
  entry into 0.7475, and the CSS/order-block confirmation alternative for those unwilling to
  blind limit.
- Live trade recap Thursday 13 Mar: long from a swept prior-day low into the 0.7475 with a
  15-minute volume node and 0.79/50%-of-structure alignment (missed by one tick); ~120 points;
  FOMC the following week cited as the reason for the range.

### Quotes (verbatim, transcript-checked)
- "the last valid low we closed above, that's our market structure shift"
- "I'm always looking for displacement away from that area"

### Open questions / ambiguities
- "GB" is never expanded; the origin of the name is not given.
- The derivations (0.295 as "polar opposite" of 0.7475; 0.41 as "negative one deviation" from
  0.705) do not reconcile arithmetically as stated and are not shown being computed.
- The ~80% and 90–95% figures are asserted with no sample, instrument or period.
- "CSS" is used repeatedly but explicitly not defined ("a CSS just has a little bit more rules").
- No rule distinguishes "expanding clean" from "consolidating" other than by eye — yet the
  target choice depends on it entirely.
- "Displacement away" has no size or candle-count threshold.
- Stop placement for the blind-limit entries is only given loosely ("at this extreme").

---

## Ash Trades | The Journey To Profitability & The Unicorn Model
(`zXtJSSkiNmo`, https://youtu.be/zXtJSSkiNmo, 5577s)

### What is actually taught

Roughly two-thirds of this 93-minute interview is process and risk doctrine; the mechanical model
comes at the end and is deliberately small.

The doctrine: he insists trading capital must come from *additional* work, never from money
already committed to rent, food or health. His argument is causal rather than moral — if the
money at risk is money you need, you will trail your stop to break-even at the first sign of
profit, take half-R, and never live long enough to observe the probabilities your model
depends on. He describes his own four-year arc: year one signal services and retail patterns
(unprofitable), year two self-designed experiments with moving averages/RSI/breakouts (break
even, and the lesson that "it's not the strategy, it's the execution"), year three annotating
every ICT video and choosing a single concept, year four profitability on prop and personal
accounts. He credits ICT's core content month 5 "institutional swing points" — a diagram
pointing an arrow at a breaker block as the entry — as the moment the model crystallised, and
ICT's later Twitter market reviews naming the breaker+FVG combination a "unicorn" as the
confirmation. His repeated slogan is **less is more**: pick one thing you can actually identify,
show up at one time each day, and stop consuming new concepts. He also stopped following ICT on
Twitter to remove noise. Finally, he insists you do not change a model after a five- or
six-trade losing streak; you submit to time and let the probabilities run.

The model: bias comes from the **daily** chart via internal (fair value gaps) vs external (swing
highs/lows) liquidity — price sitting at a daily bearish FVG means the draw is the swing low.
Then to the **hourly** for areas of interest: with a bearish bias, hourly bearish FVGs and hourly
swing highs. Then to the **5-minute** to execute, and only at a session open (London 02:00 EST,
New York 09:30). The entry function is the **unicorn**: a stop hunt of a swing point (a 3-candle
swing — lower highs either side of a high, higher lows either side of a low) into the hourly area
of interest, then displacement *through* the breaker block, leaving a fair value gap **aligned
with** the breaker. The breaker is the lowest down-close candle before the leg up that took
liquidity (mirrored for shorts); consecutive same-direction closes are all included.

Execution is fully mechanical and this is the part he defends hardest: a limit order at the
*beginning* of the breaker, a limit stop on the far side of the breaker, and a limit take-profit
at **2R**. No break-even, no trailing, no trimming — only validation or invalidation. He shows a
worked case where a trailed stop would have been taken out at break-even before price ran to
target. Risk is under 1% per trade, **one trade per day maximum**, **two trades per week
maximum**, win or lose. He trades futures rather than forex specifically because the spread in
forex may prevent a fill on a limit that price only just touches at the breaker. And after the
trade is done he turns the computer off and goes to the gym — the "cushion to work with" impulse
is named as the thing that undoes the day.

### Concepts introduced (speaker's own terminology)
- "the unicorn" / unicorn model (breaker block + fair value gap)
- breaker block (as ICT core content month 5 "institutional swing points")
- stop hunt; displacement through the breaker
- internal liquidity (FVGs) vs external liquidity (swing highs/lows) for daily bias
- "areas of interest" (hourly), "position searching"
- "validation or invalidation" (no third outcome)
- "submit to time"
- "less is more" / "quality over quantity"
- "work more" (funding trading from external income)
- "completing the justifications to your actions"

### Rules / conditions stated
- Daily bias: price at a daily bearish FVG → draw to the swing low (mirror for bullish).
- Timeframe chain: daily bias → hourly areas of interest → 5-minute entry.
- Bearish areas of interest = hourly bearish FVGs and hourly swing highs; bullish = hourly
  bullish FVGs and hourly swing lows.
- Only trade at an opening time: London 02:00 EST or New York 09:30.
- Swing high = a candle with a lower high on each side; swing low = higher lows on each side.
- Entry sequence, in order: (1) price reaches the hourly area of interest, (2) stop hunt of a
  swing point, (3) displacement through the breaker block, (4) an FVG left aligned with the
  breaker. Only then is a limit order set.
- Breaker = the lowest down-close candle before the leg up that took liquidity; if there are
  consecutive same-direction closes, use all of them.
- Entry at the beginning of the breaker; stop on the other side of the breaker; TP at 2R.
- Never move to break-even, never trail, never trim.
- Risk under 1% of the account per trade.
- Maximum one trade per day; maximum two trades per week — regardless of outcome.
- Do not change the model after a losing streak.
- Trade capital must come from income surplus to bills and savings.

### Examples walked through
- GBPUSD short at London open: daily bearish FVG → bearish bias; hourly bearish FVG and hourly
  swing high as the two areas of interest; London open drives into the hourly FVG; a 3-candle
  swing high is run; displacement through the breaker leaves an aligned FVG; limit short at the
  breaker, stop above, 2R target — including the note that the forex spread might have prevented
  the fill.
- NQ long at New York open: daily persistently closing above previous-day highs → bullish bias;
  hourly swing low inside a bullish FVG plus a second hourly bullish FVG as areas of interest;
  NY open creates the stop hunt below the swing low, displacement through the breaker with an
  aligned FVG, limit long at the breaker, 2R hit after a pullback that would have stopped out a
  trailed position at break-even.

### Quotes (verbatim, transcript-checked)
- "I do not accept break even I do not Trail my position"
- "the key for me is less is more"

### Open questions / ambiguities
- "Displacement" is never given a size, body-ratio or candle-count threshold.
- "Aligned with the breaker" is not defined — overlap, containment, or same price band?
- The daily-bias rule is stated for the simple case (price sitting *at* a daily FVG); no rule is
  given for when price is at neither an FVG nor a swing, or when both are in play.
- No time limit on how long after the session open the setup may form.
- The 2R target is fixed with no exception for the target sitting inside an obvious obstacle.
- The "under 1% per trade" is not reconciled with prop-firm drawdown rules.
- He quotes ICT verbatim from memory ("one of the strongest algorithmic entry patterns"); that
  claim is ICT's, relayed, not independently evidenced here.

---

## DTR | C2U - Blending The Fractal Model & Unicorn Model - No Daily Bias
(`07lOxv39LdY`, https://youtu.be/07lOxv39LdY, 1423s)

### What is actually taught

Day Trading Realtor presents the **C2U (C2 Unicorn)**, an explicit hybrid of TTrades' fractal
model, Ash Trades' unicorn model and AM Trades' expansion/daily-profile work. He is upfront that
parts of the model come from paid mentorships and are withheld.

The framing claim is that the model is **point-of-interest based and needs no daily bias**. His
reasoning: there are too many mutually inconsistent ways to build a daily bias, and TTrades
personally told him that nothing obliges him to use one. What replaces bias is a two-part
observation: TTrades' "price cannot reverse without creating a swing point", and ICT's claim
that the unicorn is the most powerful algorithmic reversal pattern. So he looks for hourly swing
points forming *at* a point of interest, then drops to 5-minute and looks for a unicorn inside
the wick of that swing point.

The points of interest he accepts are: another swing high/low, opposing range candles, fair value
gaps, previous day high/low, previous session high/low, previous week high/low, and the daily
"T-spot". His stated favourite formation is an hourly swing point resting **just above** a
bullish FVG (or just below a bearish FVG). He wants multiple POIs stacked.

The filter that makes the model his own is a **candle count**: the unicorn should form in about
**10 to 12 candles or less**, ideally 7–9 as in his examples. A unicorn built over several hours,
or one where a lot of consolidation sits between the breaker and the close through it, he treats
as consolidation dressed up as a pattern and rejects it.

He then states the departure from TTrades' fractal model: he does **not** wait for a valid C2
closure and trade in Candle 3. If the unicorn forms *inside* C2, that unicorn is his confirmation
that C2 will be a valid closure, and he takes the trade there.

Context is supplied by the **7-hour candle** as a simplified daily profile (from AM's expansion
model): the 01:00 candle spans 01:00–08:00 = London. A London C2 candle inside a 7-hour bearish
FVG that sweeps highs is read as a London reversal, and 50% of the previous 7-hour candle (or of
its wick if the wick is large) should be respected. Alongside this he runs an **average daily
range** check: he measures how much of the ADR has already been spent and whether the distance
to the intended target keeps the day inside (or reasonably beyond) it — he shows both a case
where 90 points of remaining move fits inside a 335-point NQ ADR and a case where the day has
already run 73.5 of a 66-point ADR and a reversal is therefore expected.

The model is fractal, with explicit pairings: 15m C2 with a 1m unicorn, 1H C2 with a 5m unicorn,
4H C2 with a 15m unicorn. Targets are deliberately modest — the "low hanging fruit" nearest
session level (Asia high, London low, New York open) for roughly 2 to 2.5R, which he frames as
what a funded trader needs.

### Concepts introduced (speaker's own terminology)
- "C2U" / "C2 unicorn"
- "point of interest based model" (no daily bias)
- unicorn candle-count filter (10–12 candles or fewer)
- 7-hour candle as the daily profile (01:00 candle = London)
- "daily t-spot" (an open-ended POI valid until an hourly close past it)
- "low hanging fruit" target
- average daily range (ADR) percentage / volatility condition
- hourly swing point resting just above/below a fair value gap
- "opposing range candles"
- "OSOK" (a separate one-shot news method, not taught here)

### Rules / conditions stated
- No daily bias is required to take a trade.
- Start on the hourly: identify hourly swing points; only consider those that reach a point of
  interest.
- Accepted POIs: swing high/low, opposing range candles, fair value gaps, previous day high/low,
  previous session high/low, previous week high/low, daily T-spot.
- Prefer hourly swing points with larger wicks; look for the unicorn inside the wick.
- The unicorn must form in ~10–12 candles or fewer; reject unicorns with heavy consolidation
  between the breaker and the close through it.
- A unicorn forming inside C2 is accepted as confirmation of a valid C2 closure — do not wait
  for the C2 close and Candle 3.
- On a London reversal, 50% of the previous 7-hour candle must be respected; if that candle has
  a large wick, use 50% of the wick instead.
- Favoured formation: hourly swing low resting just above a bullish FVG (mirror for bearish).
- Check the ADR: if the day has already exceeded the ADR, expect a reversal rather than
  continuation; if the distance to target keeps the day near/inside the ADR, the target is
  reasonable.
- Fractal pairings: 15m C2 → 1m unicorn; 1H C2 → 5m unicorn; 4H C2 → 15m unicorn.
- The daily T-spot is an open point of interest, on its own sufficient, until an hourly candle
  closes past it.
- Target the nearest "low hanging fruit" session level for ~2–2.5R.

### Examples walked through
- NQ A+ London reversal: 7-hour London C2 inside a 7-hour bearish FVG sweeping previous day
  high; ADR 335 with 214 spent and 90 to the London low; 5-minute stack of 50% of the 7H wick,
  hourly opposing candles and an hourly IFVG; unicorn inside C2; target the London low, hit with
  almost no retracement.
- Gold: Asia made the high, London failed to continue → New York reversal expected; hourly swing
  low above a small hourly FVG; unicorn in 8 candles; 2.41R at the Asia high.
- ES: day already 73.5 points into a 66-point ADR; 7-hour swing low above a 7-hour bullish FVG;
  hourly FVG + hourly swing low + hourly opposing candles; unicorn in 9 candles; target the New
  York session open.
- 6C: no other POI — only a bearish daily C2 T-spot flagged by the TTFM indicator overnight;
  unicorn in 7 candles at 09:00; ~2.25R first target, roughly 4R further down.
- Gold February 15m/1m fractal: 7-hour London reversal off 50% of an opposing candle body;
  15-minute C2 into a 15-minute FVG with a 1-minute unicorn in its wick; ~3R.
- A London-session example that took four hours (05:00–09:00) with a second tag-in and drawdown
  — used explicitly to show not every trade runs straight to target.
- 4H 06:00 C2 at a 4H swing high with a 15-minute unicorn, played for the 10:00 open high then
  lower, targeting the London low.

### Quotes (verbatim, transcript-checked)
- "I don't specifically rely on a daily bias in order to enter a trade"
- "I want to see a unicorn form quickly and concisely"

### Open questions / ambiguities
- The **T-spot** is central to one whole example but never defined in this video (it comes from
  the TTFM indicator).
- "Unicorn" is used throughout without a definition here — the breaker+FVG mechanics are assumed
  from Ash Trades / ICT.
- The candle-count filter is given as a range ("10 to 12 or less") with no hard cut, and the
  count's start point (from the breaker candle? from the sweep?) is not stated.
- "Opposing range candles" is used as a POI but never defined.
- The ADR lookback is given once as "the last 6 months on NQ" but not as a rule.
- No stop-placement rule is stated anywhere in the video; only targets are discussed.
- Parts of the model are explicitly withheld as paid material, so the published rule set is
  knowingly incomplete.

---

## DayTradingRauf | ICT MMXM Models
(`wB-fQiT_UDo`, https://youtu.be/wB-fQiT_UDo, 1087s)

### What is actually taught

Rauf's premise is that traders use market maker models without knowing what they *are*. His
definition: MMXM models are a **mitigation of orders** — a hedging program. Market makers are
not always on the profitable side; they facilitate flow for large institutions, so through the
whole buy-side of the curve they are in drawdown, selling short to fill the longs that retail and
funds want. Consolidation, breakout, re-accumulation, smart money reversal, then the return to
clear the original consolidation is described as that facilitation cycle. He insists the model is
a daily/weekly-timeframe phenomenon because banks cannot position size on 1-minute charts, even
though the pattern is fractal.

**Old accumulation → new distribution.** Only *old* fair value gaps matter — ones that were
traded into, accumulated in, and then departed from. Projected forward in time (he says the
algorithm returns to them for the next ~60 days), they become inversion levels and areas of new
distribution. In a bullish model, the bearish FVGs on the sell-side of the curve are the ones you
map forward and expect to be respected.

**The reversal test.** At the midpoint between the two halves of the curve sits the smart money
reversal. He tells the viewer not to look for an order block there. The requirement is a
**breaker** plus an area of fair value: "the Silver Bullet only forms when we trade through a
breaker" — said twice, emphatically. A bullish breaker is low → high → lower low; the up-close
candles are projected forward, and once price body-closes above them and returns into an area of
fair value, that is the reversal signature.

**Mitigation blocks.** An up-close candle qualifies as a mitigation block if it traded into fair
value; consecutive up-close candles are merged and projected forward as one block. He uses volume
as a tiebreak between two candidate candles. Their function is twofold: they are re-accumulation
entries, and they let you anticipate **breakaway gaps** — when a mitigation block and a fair
value gap overlap, longs are already accumulated, so the FVG should stay open and price should
leave it behind. His secondary rule: with three consecutive FVGs, use the middle one and expect
the one below to stay open. Three PD arrays overlapping is his high-probability threshold, and
three failing invalidates the idea.

**Grading price swings.** He draws a Fibonacci from the smart money reversal to the original
consolidation and assigns functions: below 0.25 is the low-risk buy/sell; just above 0.25 is the
first distribution; the Silver Bullet forming **below 50%** of the dealing range makes the next
leg high probability and fast; and re-accumulation at 0.75 is the highest-probability entry —
with the explicit invalidation that price must not return to 50% of the dealing range.

### Concepts introduced (speaker's own terminology)
- MMXM as "a mitigation of orders" / "a hedging program"
- buy-side vs sell-side of the curve; drawdown side
- "old accumulation, new distribution"; "old gaps" drawn forward in time
- smart money reversal
- Silver Bullet (redefined structurally, via a breaker — no time window given)
- mitigation block (merged consecutive up-close candles)
- breakaway gap
- "grading price swings" (fib over the dealing range: 0.25 / 0.5 / 0.75)
- "low risk buy" / "low risk sell"; "first distribution"
- three overlapping PD arrays

### Rules / conditions stated
- The model is a daily/weekly-timeframe construct; do not build it on 1m/5m even though it is
  fractal.
- Only map *old* fair value gaps — ones already accumulated in and departed from — and project
  them forward; expect the algorithm to return to them for ~60 days.
- When bullish, map bearish FVGs on the sell-side of the curve and expect them respected.
- The reversal is confirmed by trading **through a breaker** into an area of fair value, not by
  an order block.
- "The Silver Bullet only forms when we trade through a breaker."
- Bullish breaker = low → high → lower low; project the up-close candles forward; require a body
  close above them.
- A mitigation block is an up-close candle that traded into fair value; merge consecutive
  up-close candles into a single block and project it forward; prefer the higher-volume candle.
- Mitigation block + FVG overlapping → the FVG is a breakaway gap and should stay open; long
  there with the stop below the low, targeting the original consolidation.
- With three consecutive FVGs, use the middle one and expect the one below to stay open.
- Three overlapping PD arrays = high probability; three failing = the idea is invalid.
- Fib the dealing range from the smart money reversal to the original consolidation. Below 0.25
  = low-risk buy/sell. Just above 0.25 = first distribution. Silver Bullet below 0.50 = the next
  leg is high probability and fast. Re-accumulation at 0.75 = highest-probability entry.
- Invalidation: if price returns to 50% of the dealing range, drop the trade idea.

### Examples walked through
All examples are drawn on a single schematic/annotated market maker buy model rather than named
instruments and dates: the consolidation → breakout → re-accumulation → smart money reversal →
return sequence; sell-side-of-curve bearish FVGs projected forward and respected one after
another; a bullish breaker projected forward and traded through; two merged up-close mitigation
blocks projected forward and bought; a mitigation-block/FVG overlap producing a breakaway gap;
and the fib grading walk (0.25 low-risk buy, first distribution above 0.25, Silver Bullet below
0.50, 0.75 re-accumulation into a fast rally). He references his Twitter for real executions but
does not open them in this video.

### Quotes (verbatim, transcript-checked)
- "the Silver Bullet only forms when we trade through a breaker"
- "when you have three PD arrays overlapping each other"

### Open questions / ambiguities
- **Silver Bullet is redefined without any time window.** Mainstream ICT usage ties the Silver
  Bullet to a fixed hourly window; here it is purely structural. The conflict is not acknowledged.
- "Area of fair value" is used alongside "fair value gap" and it is unclear whether they are the
  same thing (at one point he uses 50% of a leg).
- The ~60-day validity of an old gap is asserted with no derivation, instrument or test.
- No timeframe is given for the "body close above the breaker" that confirms the reversal.
- The fib is drawn "from the area which created the smart money reversal to the original
  consolidation", but which exact price points anchor it is never pinned down.
- "First distribution" is named but its trading use (if any) is not explained.
- The volume tiebreak for choosing a mitigation block is eyeballed, with no measure.
- No examples on real, dated charts — everything is schematic, so none of it is verifiable from
  the video itself.

---

## Cross-video conflicts recorded in this unit

1. **Is a daily bias required?** Ash Trades and $niper both build bias first (internal vs
   external liquidity on the daily). DTR explicitly refuses to use one and enters purely from
   points of interest. AM Trades uses neither — his selection layer is the economic calendar and
   weekly profile. Recorded as `daily-bias-requirement`, status contested.
2. **Trade management.** Ash: never break-even, never trail, never trim, fixed 2R. AP: manages,
   re-enters, plays continuations, and explicitly says trailing/managing matters. DTR: trims and
   trails optionally but defaults to a fixed low-hanging-fruit target. Recorded as
   `mechanical-trade-management`, status contested.
3. **SMT divergence.** $niper uses SMT everywhere including inside ranges and on 1-minute charts.
   AP ignores intra-range SMT entirely and only counts it at extremes. Recorded as
   `smt-divergence-confluence`, status contested.
4. **Entering Candle 2 vs waiting for its close.** DTR takes the trade inside C2 on the unicorn;
   the TTrades fractal model (per DTR's own description of it) waits for a valid C2 closure and
   trades Candle 3. Recorded on `c2-unicorn`.
