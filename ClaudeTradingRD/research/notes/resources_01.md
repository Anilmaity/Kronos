# Resources — study notes (unit_id: `resources_01`)

Channel: TTrades_edu. Playlist: "Resources". 4 videos assigned; **3 transcripts present**.

| video | id | duration | transcript |
|---|---|---:|---|
| Backtesting Simplified - A Clear Step-by-Step Approach | `MvD7fQQ0szE` | 4430s | **MISSING** |
| How To Journal Everyday For Trading | `wrIZ7CAuFCc` | 955s | present (auto-en) |
| Intro To Futures Trading & Prop Firms | `dtsrR8dX2Ro` | 1092s | present (auto-en) |
| TradingView Tutorial For Beginners [Full Guide] | `JPVhmPZiLKY` | 1122s | present (auto-en) |

`raw/transcripts/MvD7fQQ0szE.txt` does not exist, so **"Backtesting Simplified" is not
covered below and is cited nowhere**. At 74 minutes it is the longest video in the unit and,
given the titles of the other three, is very likely the richest — a 74-minute step-by-step
backtesting walkthrough is exactly where sample sizes, data periods and record-keeping
thresholds would live. It is the single highest-value re-fetch target in this unit.

**What this unit turned out to be.** All three available videos are tooling and process
walkthroughs, not trading lessons — which is good news, because tooling is mechanical by
construction. This is where the corpus's hard numbers live: contract multipliers, tick sizes,
session hours, chart settings, a contract-roll rule, prop-firm drawdown mechanics, and one of
the tightest statements of his trading window anywhere in the corpus. Almost nothing here
requires interpretation; it requires transcription and cross-checking, which is what the
concept files do. Note that these are also *early* videos — the TradingView tutorial shows
templates for tools (kill zones, OTE, a premium/discount box) that the later live-stream
material says he removed, so the unit doubles as a dated inventory of the method's tooling.

**Transcript hygiene.** None of the three transcripts carries timestamps, so **no
`approx_time` is recorded anywhere in this unit.** The corpus's standard artifacts ("candle 2"
→ "candle to", "reach" → "wretch") do **not** appear — the fractal-model vocabulary is largely
absent from these process videos, and "reach" is rendered correctly. The artifacts that do
appear and that matter for the quotes: **"OTE" → "OT"**, **"AGFX watermark" → "AG gfx
Watermark"**, **"back-adjust" → "be adjust" / "B adjust"**, **"Ninja Trader" → "ninja Trader"
/ "NinjaTrader"** inconsistently, **"TD Ameritrade" → "TDM Merit trade"**, **"OCO" → "Oco"**,
**"lows" → "Lowes"**, **"gann box" → "gone box"**, **"gains" → "games"**, **"take profit" →
"takeprofit"**, and — most consequentially — **the futures video's dollar figures are
mangled**: "$112,000" for what is clearly ~$12,000 of ES margin, "$133,000" for ~$13,000
initial margin, "$2,000 000 draw down", "it's really a $22,000 account" where the argument
requires ~$2,000. Those garbled figures are recorded as garbled in the concept `ambiguities`
and are **not** silently corrected; the ratios and the reasoning survive, the exact dollar
amounts do not. Quotes are copied verbatim including every artifact above.

---

## How To Journal Everyday For Trading (`wrIZ7CAuFCc`, https://youtu.be/wrIZ7CAuFCc, 955s)

### What is actually taught

This is a *market* journal, not a trade journal, and he makes the distinction the thesis of
the video: many people journal when they take trades, he journals whether or not a trade was
taken, and not doing so is "a disservice to yourself" that stunts growth as a trader. A
separate video on journaling trades specifically is offered if there is demand — it is not in
this unit.

The first half builds the Notion template from an empty page, and the structure is worth
recording precisely because it encodes what he thinks a day consists of. A database with both
a **table view and a calendar view**, so any past day can be reached two ways. Each daily
entry carries a news callout (the day's forexfactory.com calendar, pasted in) and a notes
callout, then a collapsible **toggle heading per instrument** — ES, NQ, and a spare labelled
"X" for anything else being watched. Inside each instrument's section: a two-column block
headed **predictions** and **actual**, then a four-column block for the four timeframes he
works, **daily / hour / 15-minute / 5-minute**. A second template covers the **weekly review**:
prediction versus actual again, but only three timeframes — **daily / 4-hour / 1-hour** — plus
the week's Forex Factory calendar.

The predictions/actual split is the mechanism the whole thing exists for. The prediction is
written **the evening before** — he shows a Thursday-night entry anticipating Friday's daily
candle — and the actual is pasted in after the session. His stated purpose is accountability:
to find out whether the bias was correct, and if wrong, how it could be fixed to be on side
for the day. That is the entire remediation procedure; there is no scoring rubric.

The second half is him journaling a real day, which is where the process detail comes out.
Charts are marked up in TradingView and pasted with the copy-image shortcut. He does the daily
chart **three times** across one journal (daily section, weekly review, per instrument) and
explains why without prompting: the majority of his analysis, his narrative, is derived from
the daily chart. On the weekly hourly chart he does something structurally interesting — he
**separates each day with a vertical divider at midnight and labels them**, so the weekly
profile can be read day by day on one chart, and he draws the **weekly opening price** across
the whole week, calling it fair value for the week and pointing at how price reacted along it
all week. Both are chart-construction conventions with analytic claims attached.

Two hard constraints fall out of the workflow. He does not journal Mondays, because he never
trades Mondays. And the reason he only marks up the lower timeframes for part of the day is
stated flatly: he only looks to take trades between **8:30 and 12** — that is the session he
is trading, and he does not care much for price action outside it. That single sentence is one
of the tightest statements of his window in the corpus.

### Concepts introduced

- **Journal every day regardless of whether a trade was taken.**
- **Predictions written the night before vs actual pasted after** — the accountability loop.
- **Four daily timeframes: daily / 1H / 15m / 5m.** Three weekly: daily / 4H / 1H.
- **Forex Factory as the news source**, daily and weekly.
- **Per-instrument toggle sections** (ES, NQ, spare).
- **Midnight day-dividers on the weekly hourly chart** to read the weekly profile by day.
- **Weekly opening price as "fair value for the week".**
- **"I never trade Mondays"** — stated as settled habit, no justification offered here.
- **The 8:30-to-12 trading session.**
- Marked up in passing on the worked charts: SMT (daily, hourly and 5-minute), change in the
  state of delivery, order block, propulsion block, series of up-close candles, fair value
  gap, consequent encroachment of a wick, three drives, projections, midweek reversal with
  Thursday and Friday continuation, "old buying new selling", "es is the stronger index".

### Rules / conditions stated

- Journal every trading day, trade or no trade.
- Write the prediction the evening before, anticipating the next daily candle.
- Fill in the actual after the session and compare; if wrong, spend more time on price action
  to work out how the daily bias could have been correct.
- Daily entry: news, notes, then per instrument — predictions, actual, daily, hour, 15m, 5m.
- Weekly review: week's calendar, prediction, actual, daily, 4-hour, 1-hour.
- Re-do the daily chart on every entry — most of the narrative comes from it.
- On the weekly hourly, divide days at midnight, label them, and draw the weekly open.
- Do not journal Mondays; Mondays are not traded.
- Only take trades between 8:30 and 12; that is the session, and outside it price action is
  not analysed.

### Examples walked through

One full day (a Friday, journalled from the prior Thursday night) on **NQ and ES**: both daily
anticipations correct, SMTs marked on the daily and hourly, a 15-minute markup with an order
block, a high-to-low projection and an OHLC overlay showing the CISD at the reversal, and a
5-minute markup running from before 8:30 (a low-risk sell deliberately not taken), through the
8:30 release, the reach back to an old daily level, the close below the series of up-close
candles at the 8:30 opening price forming a propulsion block, and the 9:30 open. Then one full
weekly review: NQ's weekly anticipation correct, ES's direction correct but the previous
week's low not reached (explained by ES being the stronger index), a 4-hour SMT, and an hourly
chart with the day dividers showing a Wednesday/midweek reversal with Thursday and Friday
continuations.

### Quotes

- "important to journal regardless of if you take a trade or not"
- "I only look to take trades between 8:30 and 12"
- "the majority of my analysis or my narrative is derived from the daily chart"

### Open questions / ambiguities

- No scoring rubric for a prediction. The comparison is visual and narrative, and the
  worked weekly review is graded "not technically correct but I did get the direction
  correct" with no rule for how that is recorded.
- The remediation for a wrong bias is one clause ("spend more time focusing and looking at
  price action") — no error taxonomy, no follow-up loop.
- No timezone is spoken; the TradingView video in this same unit sets the chart to New York
  local time.
- 12 is the outer bound of the window here; other units in the corpus give 10:00, 10:30 or
  11:00. This is the widest statement of it.
- "Fair value for the week" is asserted for the weekly open and never defined; no trading rule
  is derived from it in this video — it is a review artefact.
- Whether losing trades receive any additional treatment is deferred to a video not in this
  unit.

---

## Intro To Futures Trading & Prop Firms (`dtsrR8dX2Ro`, https://youtu.be/dtsrR8dX2Ro, 1092s)

### What is actually taught

The unit's reference video for everything numeric about the vehicle. He repeatedly and
explicitly defers detail ("I would suggest Googling that"), so what he *does* state is
deliberately the minimum a trader needs, which makes it a clean spec.

**Session and instruments.** Futures run 6:00 p.m. to 5:00 p.m., Sunday to Friday, with no
Saturday session. Examples given span NQ and ES through lean hogs and orange juice.

**Points, ticks, handles.** A point is the smallest move left of the decimal; a tick is the
smallest move right of it; one point equals one handle. ES and MES move in 25-cent increments,
so four ticks make a point. The multiplier is given for the NASDAQ pair — the mini (NQ) moves
$20 a point, the micro (MNQ) $2, the micro being one tenth of the mini — and the same tenth
relationship is asserted for ES/MES **without its dollar figures ever being spoken**. His
worked example: 5 points × $20 × 2 contracts = $200.

**Contracts and the roll.** ES and NQ are quarterly. The symbol is root + month letter + year;
March is H and June is M, so the June 2024 S&P is ESM2024. September and December are named as
months but **their letters are never said** — so they are not recorded. The roll rule is the
find of the video: he goes to **barchart.com**, looks at **open interest and volume**, sees
which contract has the most, and switches to that one. This directly fills a hole the library
had recorded as unfillable — the existing `chart-data-settings` entry states he "does not
remember or care about roll dates, so no roll-date rule is given for a backtest". There is
one, and this is it. He charts on the continuous contract, which is why back-adjustment
matters.

**Chart data settings, demonstrated.** Back-adjust (adjust for contract changes) ON — with it
off the rollovers are visibly stitched together, with it on the series is "combined" and more
fluid. Settlement OFF — he toggles it live, points at two specific days whose candles change
enough that they "could have impacted my bias quite a bit", and says it gives cleaner candles.
(One sentence immediately after reads "I have found that settlement works best for my strategy",
which contradicts the demonstration and the TradingView video; it is treated as a misspeak or
caption error, and flagged as such rather than recorded as a second reading.) A real-time data
subscription is required or the feed is delayed about 15 minutes.

**Orders.** Limits fill at the price; stops convert to market on touch; market takes bid or
ask. The one he names as personally used is the **OCO** — placing a limit to get in, then
bracketing with a stop loss and a take profit where whichever fills cancels the other.
Partialling in futures can only be done in **whole-contract increments**, which he flags as
the thing forex traders get wrong.

**Futures versus forex.** The stated draws: no broker manipulation; the bid-ask spread is
genuinely just the bid and the ask, so hitting buy market on the S&P fills you at the ask
without slippage; pattern day trading does not apply; different tax treatment; leverage
without options Greeks. Vocabulary converts — lots to contracts, pips to points/handles/ticks
— and a forex trader can trade the currency future instead (6E for the euro, charted as 6E1!).
CFD mappings: SPX500 → ES, NAS → NQ, gold → GC, oil → CL.

**Prop firms.** The lifecycle is drawn as a loop: buy an evaluation → pass or fail → pay the
activation fee → funded → reach the minimum balance and pay out, or fail and return to
evaluation. Then the part that actually matters, **four drawdown types**: *static* (the
drawdown does not move for the life of the account); *trailing end-of-day* (intraday swings
ignored, the floor trails to wherever the balance finishes each day); *trailing unrealised*
(the floor trails the highest value including open profit — so the identical realised P&L that
survives an end-of-day account can fail this one, which he walks through explicitly); and
*daily loss limit plus maximum loss limit* (his TopStep example, where the daily limit stops
the day without failing the account, and the maximum limit trails up at end of day once the
balance is above the initial). Finally the purchasing lens: a "50k" account whose drawdown is
a couple of thousand is really an account of that couple of thousand, and the number to
compare is the **drawdown-to-profit-target ratio** — a $3,000 target on ~$2,000 of real
capital is ~150% required return. Costs are totalled as evaluation fee + activation fee, with
the observation that a cheaper *evaluation* is the better buy for anyone likely to fail
several attempts.

### Concepts introduced

- **Futures hours** 18:00–17:00, Sunday–Friday, no Saturday.
- **Point / tick / handle**, tick size, tick value, mini vs micro multipliers.
- **Quarterly contract naming** (H = March, M = June) and the **barchart open-interest-and-volume
  roll rule**.
- **Continuous contract charting**, back-adjust ON, settlement OFF, real-time data fee.
- **Order types**, and the **OCO bracket** as the one he uses.
- **Whole-contract partialling.**
- **Futures-vs-forex execution differences**: no broker manipulation, no spread, no slippage
  at the ask, no PDT, different tax, leverage without Greeks.
- **CFD-to-futures symbol map.**
- **Prop firm lifecycle** and the **four drawdown types**.
- **Effective account size = drawdown**, and the **drawdown-to-profit-target ratio**.

### Rules / conditions stated

- Sessions run 18:00 to 17:00, Sunday through Friday; no Saturday.
- 4 ticks = 1 point = 1 handle on ES/MES (25-cent ticks).
- NQ = $20/point, MNQ = $2/point; micro = 1/10 mini.
- P&L = points × multiplier × contracts.
- Partials only in whole-contract increments.
- Roll by comparing open interest and volume on barchart.com; hold whichever contract has the
  most.
- Chart the continuous contract; back-adjust ON, settlement OFF.
- Bracket the position with an OCO stop loss and take profit.
- Classify the account's drawdown type before choosing a management style — the same trade
  sequence passes an end-of-day-trailing account and fails an unrealised-trailing one.
- Size and compare offers against the drawdown, not the headline account number.

### Examples walked through

No market examples — this is a slide-and-screen-share video. The demonstrations are: the NQ
continuous daily chart with back-adjust toggled to show the rollover stitching; the same chart
with settlement toggled, pointing at two days whose candles change materially; EURUSD with the
6E futures chart overlaid to show similar-but-not-identical movement; four hand-drawn drawdown
diagrams (static, trailing end-of-day, trailing unrealised, daily-plus-maximum limit) with a
worked failure case on each; and a firm-comparison table for 50k accounts (Apex, TopStep, My
Funded Futures) that is on screen rather than spoken.

### Quotes

- "Futures run from 6:00 p.m. to 5:00 p.m."
- "look at the open interest and volume and see which contract has the most"
- "what it does is it Trails your unrealized p&l"

### Open questions / ambiguities

- **The dollar figures are garbled by the captioner** ($112,000 / $133,000 for ES margins,
  "$2,000 000 draw down", "$22,000 account"). The ratios and reasoning survive; the exact
  amounts do not, and are not reconstructed here.
- ES/MES dollar-per-point is never spoken — only the tick size and the mini/micro tenth
  relationship. Do not assume a figure.
- September and December contract letters are not spoken.
- No threshold for "has the most" in the roll rule, and no statement of what to do when open
  interest and volume disagree; no check frequency either.
- Whether the end-of-day trail stops once the account is in profit (a common "trail to
  breakeven then freeze" rule) is not addressed.
- Firm names and discount levels are date-specific and mostly on-screen only.
- The OCO description has him "placing a limit order to buy in", where other units have him
  entering at market. This is an instructional overview of order types, so it is recorded
  without disturbing the other reading.
- "No broker manipulation" is asserted, not evidenced; the no-slippage claim is hedged with
  "generally" and made for the S&P only.

---

## TradingView Tutorial For Beginners [Full Guide] (`JPVhmPZiLKY`, https://youtu.be/JPVhmPZiLKY, 1122s)

### What is actually taught

The full workspace behind every chart in the corpus, walked through setting by setting. It is
worth treating as the display contract: if a detector is meant to see what he sees, this is
the configuration it has to match.

**Chart settings.** Status line stripped — title, logo and all OHLC values off, because the
symbol, timeframe, date and his name come instead from an added watermark indicator; indicator
titles stay on so they can be toggled. Candles are green on up-close, black on everything else
including body and wick. Data: electronic trading on, adjust for contract changes on,
settlement off — and **"I'm always in New York local time"**, which is the corpus's clearest
statement of the chart clock. Canvas: solid background at hex **#F5F5F5**, no grid lines,
dotted very-light-grey crosshair at 100% opacity, price scale numbers stacked on the left.
Trading buttons and instant order placement off; all events off except alert lines.

**Templates, which is the real content.** He saves and stars **indicator templates** so each
is a one-click button: a *clean* template that strips everything back to the watermark, a
*3-day lookback*, an *open-high-low-close*, a *time* template where "almost everything [is]
turned off except for three time periods" — the closest the corpus comes to naming his session
windows, and it stops short of naming which three — plus *power of three*, *weekly candle
power of three*, and *kill zones and pivots*. **Drawing templates** work the same way, one per
PD-array type with a fixed colour, so colour identifies the object: breaker / mitigation block
rectangles, fair value gaps, deviations from a range, buyside and sellside liquidity trend
lines, order blocks (blue, thickened), SMT with *separate high and low templates*, buy stops
and sell stops, a premium/discount box built on price levels **0, 0.5 and 1**, **OTE** levels,
projections (one colour reused for every level, near-transparent background, font size 10),
and a risk-reward tool saved separately as long-position and short-position variants. The hex
codes are shown on screen at the end and, apart from the background, are never spoken.

**The SMT layout**, which is the most directly automatable thing in the video. Two panes;
**symbol sync OFF** so the panes hold different instruments; **interval synced** so both are
on the same timeframe; **crosshair synced ON**, which is what lets him hover an extreme in one
pane and see exactly which candle it corresponds to in the other ("it just allows me to see
which high and low is matching up… we have an smt right on this low"); **time synced** so the
x-axes stay aligned when either chart is dragged; **data range off**. The whole thing is saved
as a named layout. The single-pane alternative is the watch list: stay full-screen on a low
and flip symbols with the arrow keys to see whether the correlated instrument took the same
low.

**Shortcuts and housekeeping.** alt+R resets the price axes; alt+click focuses a pane; tab
cycles panes; shift+F toggles full screen; ctrl+shift+S copies the chart image to the
clipboard (the shortcut the journaling workflow depends on); ctrl+scroll is focus zoom; holding
ctrl activates magnet mode on demand rather than leaving it always on; holding shift constrains
a line to straight/45°; middle-click deletes a drawing; ctrl+drag duplicates one; the period key
loads a saved layout. Finished analysis is grouped in the object tree, renamed, locked and
hidden — with the caveat he flags himself and says he intends to raise with TradingView: "remove
all drawings" deletes the hidden groups too. Drawings are synced across the layout.

### Concepts introduced

- **The full chart configuration** (status line, candles, data, canvas, trading, events).
- **New York local time as the chart clock.**
- **Indicator templates** as one-click workspaces, including a *clean* baseline.
- **The watermark** carrying symbol / timeframe / date / name.
- **Drawing templates with fixed colours per PD-array type.**
- **The two-pane SMT layout** with deliberate sync choices.
- **Watch-list arrow-key symbol flipping** as the fast SMT check.
- **Object-tree drawing groups**, locked and hidden, and the "remove all drawings" trap.
- **Premium/discount box on price levels 0 / 0.5 / 1**, **OTE levels**, projections,
  risk-reward tool.

### Rules / conditions stated

- Strip the status line; carry identity in the watermark instead.
- Electronic trading on, adjust for contract changes on, settlement off, New York local time.
- Solid #F5F5F5 background, no grid lines, dotted crosshair, scales stacked left.
- Star templates so they load in one click; keep a clean baseline template.
- One drawing template per object type, colour-coded.
- For SMT: symbol sync off, interval synced, crosshair synced, time synced, data range off;
  save as a named layout.
- Magnet mode off by default; hold ctrl to engage it when placing a level.
- Group, lock and hide finished analysis; never use "remove all drawings".

### Examples walked through

No market analysis — it is a screen-share throughout. The only market-shaped moment is the SMT
demonstration: hovering a low on one instrument, seeing the synced crosshair land on the
matching candle in the other pane, then flipping symbols with the arrow key to confirm that
ES did not take the low NQ took.

### Quotes

- "I'm always in New York local time"
- "I have almost everything turned off except for three time periods"
- "I have a solid background here is my hex code for that F5 F5 F5"

### Open questions / ambiguities

- **The three time periods are never named.** The time-levels template is loaded and its
  settings shown on screen; had he read them out, this unit would have supplied the corpus's
  missing session windows.
- The **kill-zones-and-pivots indicator is loaded on camera and no kill-zone hours are stated**
  anywhere in the video.
- Almost all hex codes are on-screen only; only the background is spoken.
- "New York local time" is the platform setting (it follows daylight saving) while the corpus
  elsewhere says "Eastern Standard Time" — the two differ by an hour for part of the year and
  the discrepancy is never addressed.
- This is early-era tooling. OTE templates, the kill-zones indicator and the premium/discount
  box are all present here, and all three are among the tools the later live-stream material
  says he removed. The video shows the templates *exist*; it does not say he trades from them,
  so "uses" is an inference and is not asserted in the concept file.
- "AG gfx Watermark" and "OT" are caption renderings (AGFX watermark, OTE).

---

## Cross-video observations

- **The three videos interlock into one workflow.** The TradingView video builds the
  workspace, the futures video fixes the instrument, contract and data settings that workspace
  is pointed at, and the journaling video is what is done with it every evening. The
  ctrl+shift+S shortcut taught in one is the mechanism the other depends on; the back-adjust /
  settlement settings appear in both, stated identically.
- **This unit is where the corpus's execution assumptions come from.** Multipliers, tick
  sizes, whole-contract partialling, no-slippage-at-the-ask, the roll rule and the four
  drawdown types are all things a backtest has to encode and none of them appear in the
  trading-lesson playlists.
- **The roll rule closes a documented gap.** `chart-data-settings` recorded that no roll rule
  was available for a backtest. There is one: barchart open interest and volume, hold the
  contract with the most.
- **The window statement is the tightest in the corpus** — "I only look to take trades between
  8:30 and 12" — and it is stated as the reason for a workflow decision rather than as a rule
  being taught, which makes it more credible, not less. It is also the *widest* of the
  corpus's several statements of the window.
- **The unit does not move the library's biggest gaps.** No wick-size ratio anywhere. No
  kill-zone hours, despite a kill-zone indicator being loaded on screen and a time template
  with "three time periods" being opened and not read out — twice this unit comes within one
  sentence of supplying them and does not. Nothing on CISD closing prices. "Aggressive" is not
  used in a definitional sense in any of the three.
- **The dating matters.** Read alongside the later live streams, this unit is an inventory of
  tools he has since dropped (OTE, kill zones, premium/discount box, midnight open by way of
  the sister unit). The concept files flag that rather than presenting them as current.
