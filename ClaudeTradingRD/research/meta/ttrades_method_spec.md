# The TTrades method — ordered specification

**Scope.** This document states the channel's *own* method, assembled only from concepts whose
`voice` is `ttrades` or `mixed` (328 of the library's 505). Guest material is excluded by
construction and is handled separately in `guest_methods_appendix.md` — the T Talks and Live Stream
Guests playlists are interviews with traders whose methods contradict each other and, in several
places, contradict this one.

**How to read it.** Every claim carries the concept id(s) it comes from, in `backticks`, so any line
can be traced to `concepts/<category>/<id>.yaml` and from there to the video and the verbatim quote.
Where a concept is `contested`, both readings are stated and the disagreement is carried forward as a
**parameter** — that is a standing project decision, not an oversight. Where the method has a hole,
the hole is named. No generic ICT knowledge has been used to fill a gap.

**Sibling documents.** Three analysis-phase workstreams produced findings that bear directly on this
spec, and it cites them where they change what a builder should do. They sit *beside* the corpus and are
never merged into it: `external_crossref.md` (an independent check of the corpus's hardest adjudications
against public ICT/SMC material), `threshold_fits.md` + `qualifier_calls.md` (turning the corpus's
adjectives into measured defaults on XAUUSD), and `session_window_fit.md` (the session gate, measured).
Every number attributed to them is **XAUUSD, 2023-07 → 2026-07, one instrument, three years** — the
corpus is taught on NQ/ES/YM, so recompute before porting. Note also the honest limit on the fitting
work: **none of the 56 curated narrated calls could be tied to a dated bar** (a transcript names no
instrument, date or price), so **no supervised fit was possible and none is claimed** — those numbers are
distribution-anchored recommendations with graded evidence, not fitted labels.

**Three conventions used throughout.**

- **[P]** marks a genuine free parameter — the corpus is silent or self-contradictory and a builder
  must choose. These should be exposed as configuration, and the disagreement rate measured.
- **[GAP]** marks something the method depends on that the corpus does not supply at all.
- **[WITHHELD]** marks something he states outright that he is not publishing. See §9.

---

# 1. The frame

## 1.1 The fractal premise

The model rests on one structural claim, stated identically across three videos: **price cannot
reverse without forming a swing point** — bearish-to-bullish requires a swing low, bullish-to-bearish
a swing high (`swing-point`, `four-candle-model-window`). Everything downstream is an attempt to
define, mechanically, *which* swing points matter and *when* one is confirmed.

A swing point is the three-candle fractal: `low[i] < low[i-1] AND low[i] < low[i+1]` for a swing low,
mirrored for a high (`swing-point`). It is only usable from bar `i+1`, because the right-hand candle
must close — which is precisely why the candle-2 and candle-3 *closure* definitions exist at all
(`swing-point`, `four-candle-model-window`).

The whole apparatus is explicitly fractal: the same tests are applied unchanged from monthly down to
15-second (`swing-point`, `fractal-model-c2`, `next-day-model`, `daily-bias-framework`).

**[GAP] — the swing filter.** The literal 3-bar fractal produces far more swings than he marks. He
states directly that he has *no mechanical rule* for which swings are "relevant"; the test is
separation from the neighbouring same-side extreme, judged by eye, "from experience and discernment"
(`relevant-swings-separation`). The one numeric instance in the corpus — 400 points on NASDAQ — is an
example, never normalised by ADR or instrument (`relevant-swing-separation`). Swings too close
together are demoted to *failure swings*, which are targets rather than levels to trade away from
(`failure-swing`). This is the single largest automation gap in the structural layer.

There is one bound that *is* stated: the look-back window for relevant swings is **three
higher-timeframe candles including the current one** — daily chart → three months, hourly chart →
three days (`relevant-swing-lookback`). Older levels may be looked at but are not the focus.

## 1.2 Timeframe pairing

Every model is a **pair**: a higher timeframe supplying the candle closure, and an aligned lower
timeframe supplying the change in the state of delivery (`timeframe-alignment-pairs`).

| Structure TF | Entry / confirmation TF | Source |
|---|---|---|
| Monthly | Daily | `timeframe-pairing` |
| Weekly | Daily (also weekly→4H) | `timeframe-pairing` |
| Daily | 1-hour | `timeframe-alignment-pairs`, `automatic-fractal-pairing` |
| 4-hour | 15-minute | `timeframe-alignment-pairs`, `automatic-fractal-pairing` |
| 1-hour | 5-minute | `timeframe-alignment-pairs`, `automatic-fractal-pairing` |
| 30-minute | 3-minute | `timeframe-alignment-pairs`, `timeframe-pairing` |
| 15-minute | 1-minute | `timeframe-alignment-pairs`, `timeframe-pairing` |

Rules attached to the table:

1. **Targets always come from the higher timeframe of the pair** (`timeframe-alignment-pairs`,
   `previous-period-high-low`).
2. **Three-slot stacks** are built by chaining: choose the entry timeframe first, take its paired
   higher timeframe, then that one's paired higher timeframe (`timeframe-alignment-pairs`). Worked:
   5m entry → hourly → daily.
3. **Which timeframes carry your points of interest is a function of your entry timeframe.** Entering
   on 5m/1m/sub-1m, POIs live on 1D/4H/1H and sometimes 15m — monthly and weekly are *not* used.
   Entering on the 4-hour, POIs come from weekly and above (`poi-timeframe-selection`).
4. **Messiness override:** if the paired timeframe's structure is unclean, step *up* one (15m→30m) or
   refine *down* one (5m→3m) rather than abandoning the setup (`timeframe-alignment-pairs`,
   `timeframe-pairing`, `swing-forming-candle-selection`). "Messy" is undefined **[GAP]**.
5. **Invalidation-first selection:** the number of timeframes is not fixed. If risk can be managed on
   the structure timeframe, execute there; dropping a timeframe exists only to improve R toward the
   *same* higher-timeframe target (`invalidation-first-timeframe-selection`).
6. **Volatility selects the execution timeframe**, inversely: low volatility → higher TF, high
   volatility permits lower (`volatility-timeframe-selection`). Volatility is never quantified **[GAP]**.
7. **Session-dependent floor** (`session-timeframe-model-map`): Asia → daily/1H or 4H/15m; London →
   those plus 1H/5m; New York AM → 4H/15m, 1H/5m, or 30m/3m.
8. The **weekly chart is skipped** — monthly steps straight to daily, and the weekly profile is read
   off daily candles (`weekly-chart-not-used`).
9. **Remediation:** persistent stop-outs on a correct bias mean the entry timeframe is one step too
   low. Raise it; do **not** widen the stop (`entry-timeframe-elevation`).
10. **Where the confirming structure shift must appear:** on the *intermediate* timeframe of the stack
    at minimum, with displacement and a close — the preferred sequence being a 1m break leading to a 5m
    break leading to a 15m break, a domino (`intermediate-timeframe-bridge`). The cost is stated
    honestly: by the time the 5-minute confirms you have usually missed the lowest-risk entry.

Note the ratios are not constant (daily→1H is 24:1, 30m→3m is 10:1) and he never states a rule that
generates the table (`timeframe-alignment-pairs`, `automatic-fractal-pairing`). Treat it as a lookup.

## 1.3 The named model stacks

| Name | Bias | Structure | Entry | Source |
|---|---|---|---|---|
| Swing model | Weekly (or monthly) C2 | Daily C2/C3 + CISD | Hourly continuation | `ttfm-swing-trading-model` |
| Favourite / A+ | Daily C2 | 4-hour C2/C3 | 15-minute CISD | `ttfm-favorite-daily-4h-15m` |
| Playbook | Daily closure | Hourly C2 + POI + closure | 5-minute CISD | `ttfm-hourly-5m-playbook` |
| Scalping model | Daily context | Hourly C2/C3 → 15m swing | 1-minute continuation | `ttfm-scalping-model` |
| Keep-it-simple | Daily C2 + H1 CISD | 4H (no POI needed) *or* 1H (POI required) | paired 15m/5m CISD | `keep-it-simple-c3-stack` |

The **published playbook** (`ttfm-hourly-5m-playbook`) is the closest thing in the corpus to a written
checklist, and it carries a hard stop-gate at step 1: derive a one-sided daily bias from daily
closures; **if there is no bias, do not go down to the hourly.**

## 1.4 The clock

- **Timezone: New York / Eastern.** Stated outright once — "all times are shown in Eastern Standard
  time" (`est-timezone-anchor`) — and again as the indicator's default (`chart-timezone-est`), and
  again as the TradingView setting "New York local time" (`est-timezone-anchor`,
  `tradingview-chart-workspace`).
  **DST — SETTLED. Use `America/New_York` (DST-aware). Do not present this as a knob.** He says "EST"
  literally and never "EDT", and the corpus never addresses the switch in words — but the kill-zone video
  resolves it operationally by setting TradingView's **New York** selector, which is DST-aware
  (`chart-timezone-est`, `est-timezone-anchor`), and the whole intraday clock is anchored on the NYSE
  cash open at 09:30 (`session-open-volume-nyse`, `new-york-intraday-time-levels`). It is also settled
  **empirically**: the venue's own daily break resumes at 18:00 NY on **99.8% of 605 occasions** under
  DST-aware Eastern, versus smearing across two hours (67.8% / rest) under a fixed UTC-5
  (`meta/session_window_fit.md`). The choice is **material, not cosmetic** — outside the break hour it
  moves up to 8.1pp of extreme-formation share and 23.3% of minute range between hours.
- **Session envelope (futures):** 18:00 to 17:00, Sunday through Friday, no Saturday session
  (`futures-trading-hours`).
- **Daily open — contested (evolution).** Later canon, asked directly: the daily open is **18:00**,
  the open of the actual daily candle on the data feed, and he says he *always* uses it rather than
  midnight or True Day Open. Earlier recording: the **midnight** opening price, with the whole worked
  example built on it (`daily-open-eighteen-hundred`, `daily-ohlc-candle-shape`). Both preserved; 18:00
  is canon **[P]**.
- **Six standing time levels** (all New York): 18:00 (new daily candle), 00:00 (midnight open), 08:30
  (news embargo lifts), 09:30 (NYSE opens), 10:00 (new 4-hour candle), 14:00 (new 4-hour candle)
  (`important-time-levels`).

**The 4-hour grid is asset-class specific.** This is load-bearing and easy to miss:

| Asset class | 4-hour opens (NY) | Source |
|---|---|---|
| Index futures | 02:00, 06:00, 10:00, 14:00 (+18:00, 22:00) | `po3-four-hour-opening-times`, `ten-am-candle-alignment` |
| Forex | 17:00, 21:00, 01:00, 09:00 (+05:00, 13:00) | `po3-four-hour-opening-times` |

He introduces the forex set by saying the timings are *different from futures*, so the offset is
deliberate (`po3-four-hour-opening-times`). He also says **"we don't really have the 09:30 open with
Forex"** — 09:30 matters because the NYSE opens, which makes it an index-class level only; 08:30 is
usable on forex when there is a release at that time (`est-timezone-anchor`, `session-open-volume-nyse`).
Any PO3 or session detector must branch on asset class.

**For gold specifically: use the forex grid (17/21/01/09 NY) — weakly, and sweep both.** The two grids
are statistically indistinguishable on candle behaviour (follow-through 59.6% vs 59.4%, z = 0.08), so
the tiebreak is purely **structural**: the forex grid opens a candle at 17:00 NY, exactly on the venue's
daily break, so **0% of its candles straddle the break against 16.5%** for the futures grid
(`meta/session_window_fit.md`). Confidence: **low-to-moderate**.

**10:00 is a structural boundary**, not a preference: a new 4-hour, hourly, 30-minute and 15-minute
candle all open together (`ten-am-candle-alignment`). Consequences: before 10:00 the hourly has not
closed, so pre-10:00 execution falls back to 30m/3m; from 10:00, 15m/5m becomes usable
(`ten-am-candle-alignment`, `timeframe-pairing`).

## 1.5 Chart and data configuration

These change the candles the whole model reads, so they are part of the spec, not cosmetics.

- Back-adjust / adjust for contract changes: **ON**. Settlement: **OFF** (he shows daily candles
  changing enough to flip a bias when toggled). Electronic trading (full session, ETH not RTH): **ON**.
  Chart timezone: New York local (`chart-data-settings`, `tradingview-chart-workspace`).
- Continuous contract for charting (NQ1!, 6E1!); roll by comparing open interest and volume on
  barchart and holding whichever has the most; month letters H = March, M = June
  (`futures-contract-rollover`).
- Chart the **minis, not the micros**; when they disagree on whether a level was taken, read the mini
  (`chart-data-settings`).
- Frame on the futures chart, execute the option on the ETF — because the futures series carries the
  overnight structure a cash-session ETF chart does not (`chart-futures-execute-elsewhere`,
  `options-proxy-execution`).
- Contract arithmetic: 1 point = 1 handle; ES/MES tick = 25c so 4 ticks = 1 point; NQ $20/point, MNQ
  $2/point; partials only in whole-contract increments (`futures-contract-specs`).
- Instruments: futures only — indices, gold, silver, oil, dollar. No CFDs, no Russell, no scalping
  (`excluded-tooling`). He uses gold-in-euro and gold-in-pound as gold's correlated set, **not**
  silver (`gold-correlated-assets`). The stated reason for futures over forex is execution: no
  broker-widened spread, no pattern-day-trading rule, and a market order on a liquid index future fills
  at the ask rather than slipping (`futures-vs-forex-differences`) — which matters for any backtest's
  cost model.
- Two-pane SMT layout: symbol sync OFF, interval / crosshair / time sync ON, data-range sync OFF, saved
  as a named layout (`smt-two-chart-layout`). Full workspace in `tradingview-chart-workspace`.

## 1.6 The toolkit — and the explicit exclusions

What is on the chart: **highs, lows, fair value gaps, opposing candles / order blocks, CISD, protected
swings, and higher-timeframe candles shown alongside the working timeframe** (`ttfm-minimal-toolkit`).
He states his own reduction plainly: highs, lows, and opposing candles / the change in the state of
delivery (`single-pd-array-mastery`).

Deliberately **not** in the model: kill zones, ICT macros, the midnight open, breaker blocks,
inversion fair value gaps, Silver Bullet, CRT, OTE, order flow / footprint / DOM / TPO, seasonal
tendencies, intraday fundamentals, "time distortion", fib retracements, the weekly EQ, volume-profile
POC, DXY-for-indices, RTY, rejection blocks (except as wicks on doji/hammer/shooting-star candles)
(`excluded-tooling`, `ttfm-minimal-toolkit`, `macros-not-used`, `intermarket-correlation-not-used`).

This list is *historically layered* — see §8. Several excluded items (OTE, breakers, kill zones, the
midnight open, Strat triggers) are taught in full in the earlier Education-ICT material and are
carried in the library as earlier readings, not as current practice.

His stated test for whether a tool survives is worth keeping as the selection rule: *is there a
mechanical definition of the thing and of where the entry is?* He drops order flow because there is
not (`ttfm-minimal-toolkit`).

---

# 2. Bias and the draw on liquidity

## 2.1 Order of operations

The gate that everything else sits under: **no entry without a higher-timeframe reason**
(`overtrading-gate`). Taking a pattern without one is named as the single most-repeated error on the
channel — you cannot pick a fair value gap at random, see a closure, and call it a setup; being right
about direction is not by itself a reason to trade (`pattern-trading-error`). A lower-timeframe
structure shift taken against the higher timeframe is, in his account, *just a retracement into a
higher-timeframe PD array*, and it is expected to fail (`structure-requires-htf-context`).

The canonical ladder (`top-down-analysis-procedure`, later reading):

1. **Daily bias** — from the daily closure, SMT with the correlated asset, previous day high/low.
2. **Daily profile** — name which profile the day is, and check it supports the bias. *If it does not,
   do not take the entry even though the bias stands.*
3. **Entry** — only then, on the level the first two steps produced.

Two hard gates sit around it:

- **Do not drop timeframes until the POI is tagged.** Mark one or two higher-timeframe points of
  interest before the session; if price does not reach one, do not open the 5m/15m chart at all
  (`htf-poi-gate-before-ltf`). Being at a price level you have an opinion about is not an entry.
- **Do not fade the current daily candle.** Read its direction before framing anything intraday; do
  not look for longs inside a bearish daily candle. Preference is daily, 4-hour and hourly all pointing
  at the same objective (`no-fading-the-daily-candle`, `timeframe-alignment`).

## 2.2 The draw on liquidity

The draw is the *destination*, and it is what the whole day is framed toward.

**Later canon — the simplified form.** Mark previous day high and previous day low; ask which is more
likely to be reached; that is the draw (`draw-on-liquidity`, `previous-period-high-low`). Look back
**three days** and mark each day's high and low, extending them forward (`previous-day-lookback-three-days`).

**Earlier canon — the open search list.** External liquidity (old highs/lows, equal highs/lows), then
internal liquidity (fair value gaps, order blocks, occasionally volume imbalances), plus two
behavioural reads: *failure to displace* over a low/high argues for the opposite side, and *following
the displacement* is "generally right" (`draw-on-liquidity`). No ranking is given among candidates
**[GAP]**.

Supporting definitions:

- **Buyside / sellside liquidity** = the price of an obvious swing high / swing low, where stops rest
  (`buyside-sellside-liquidity`). Also mark previous week/day/month extremes and session highs/lows as
  standing pools.
- **External range liquidity** = a swing high or low; **internal range liquidity** = a fair value gap
  (`external-range-liquidity`, `internal-range-liquidity`).
- **The rotation:** price sweeps external liquidity and *fails to displace* → the nearest unmitigated
  FVG becomes the draw; price reaches and respects that FVG → the opposing external extreme becomes
  the draw; repeat (`internal-external-rotation`, `internal-external-liquidity-model`,
  `irl-erl-flowchart-model`).
- **Relatively equal highs/lows** are a single, heavier pool and are preferred targets
  (`relatively-equal-highs-lows`). Tolerance is never given **[GAP]**.
- **Resistance grading.** *Low* resistance liquidity = a high or low carrying a failure swing, whose
  resting stops were never taken. *High* resistance = a level already swept before the reversal.
  Target the low-resistance side; keep the high-resistance side behind the stop
  (`high-vs-low-resistance-liquidity`). Do not target a high-resistance extreme directly — substitute
  the failure swing that formed after it, or the CE of the wick left by the close back inside
  (`high-resistance-target-adjustment`). On a low-expectation day take the failure swing to the right
  of the protected swing (`low-expectation-target-selection`). A target sitting behind a protected
  swing is harder to reach and is downgraded (`harder-target-behind-protected-swing`).
- **Range structure:** *dealing range* = the nearest high and low bounding where price is currently
  trading at your zoom; ranges nest, and external liquidity of the inner range is internal liquidity of
  the outer (`dealing-range`). *Displacement range* = the aggressive move over structure, anchored at
  the low that started it and trailed to the high it reaches (`displacement-range`).
- **Premium / discount:** 0.5 of the range is equilibrium; longs only in discount, shorts only in
  premium — and the stated purpose is **risk-to-reward, not prediction** (an entry exactly at
  equilibrium with the stop at the far extreme is 1R by construction)
  (`premium-discount-equilibrium`, `premium-discount`). See §8 for the inversion he later teaches.
  The earlier era carries a fully mechanical clock-based refinement: price below **either** the 08:30 or
  the midnight open is a discount, below **both** is a *deep* discount and that is where buys are sought
  on a buy day; mirrored above for shorts (`deep-premium-deep-discount`).
- **Bias can legitimately split across timeframes:** bullish to an upside target but bearish until the
  intervening liquidity below is taken (`bias-split-across-timeframes`).
- **Proximity read:** mark the previous period's high and low, measure distance to each, and the
  nearer one is the draw — demonstrated on the monthly and held for the month
  (`proximity-bias-nearest-extreme`).

**Targets** are exactly two things: liquidity and imbalances (`target-liquidity-and-imbalances`).
Concretely: the reference higher timeframe's previous candles' unswept extremes, starting with candle
1's (`previous-period-high-low`); the −2/−2.5 and −4/−4.5 standard-deviation projections of the
manipulation leg, preferentially where they coincide with resting liquidity
(`standard-deviation-projection`); and the drawn liquidity itself. The indicator's "formation
liquidity" line automates the first of these (`ttfm-indicator-settings`).

## 2.3 The previous-candle engine

The mechanical core of bias, applied at any scale (`daily-bias-framework`, `next-day-model`):

- **Continuation closure:** candle takes out the previous candle's high (or low) AND closes *outside*
  → anticipate the same direction on the next candle.
- **Reversal closure:** candle takes out the previous extreme AND closes back *inside* → anticipate the
  opposite direction next.
- **Both sides taken** → no bias; let another candle print.
- **Inside bar** → no information; default to trend continuation.
- **Range-bound** → mark the range high/low and wait for one to be reached.

The justification is the exhaustive three-way candle classification he credits to the Strat: relative
to the previous candle, a candle either consolidates, takes one side, or takes both — so unless it
consolidates, one of the two previous-candle levels must be reached (`three-candle-outcomes`).

The complementary form is **failure to displace**: price trades beyond a level and closes back inside
with no large closes beyond it; the lean is the opposite direction, and *the lack of displacement on
each side leans in the other direction* (`failure-to-displace`, `liquidity-grab`). Both sides failing
in sequence is a broadening formation / power of three (`failure-to-displace`, `broadening-formation`,
`broadening-formation-range-projection`).

At an old high or low there are exactly three outcomes (`old-high-low-three-outcomes`):
1. displacement out, shallow retracement, continuation;
2. displacement out **met with** aggressive displacement back in → reversal, target the opposite side;
3. no displacement out at all → return into the range, seek the opposite side.

**Trend** has three separate definitions in his own voice and they are not the same test:
higher highs and higher lows (`basic-trend-structure`); repeatedly taking the previous day's high or
low (`trend-by-previous-day-extremes` — the most mechanical); and "an aggressive move reaching towards
an objective" (`trend-as-aggressive-move-to-objective` — undefined **[GAP]**).

## 2.4 Daily bias — the mechanical framework

This is the version he calls "the easiest, most mechanical way to get bias"
(`daily-bias-c2-c3-h1-cisd`):

1. Mark **previous day high, previous day low, and the EQ of the previous day's range**
   (`daily-candle-profile-open-low-first`, `inside-day-three-levels`).
2. Bias is a **binary between a REVERSAL and a CONTINUATION**, and the reversal is *always* framed off
   the previous day's high or low — never an arbitrary level.
   - **Continuation branch:** price opens, trades *against* the bias first, **respects the EQ** — which
     is operationalised negatively as *no hourly closures beyond that EQ* — then trades through the
     previous day's extreme.
   - **Reversal branch:** price opens, trades into the previous day extreme, and a lower-timeframe CISD
     confirms the wick there.
3. **Confirmation:** a daily C2 or C3 closure **plus** an hourly change in the state of delivery in the
   same direction. Either alone → no bias.
   The hourly CISD is the single confirmation gate used in every video of the weekly-profile series
   (`hourly-cisd-confirmation`): on the 1H chart, restrict attention to price action *inside* the
   candidate daily candle; find the extreme; identify the consecutive series of opposing-close candles
   that made it; require a 1H close through that series. Until that close-through occurs the daily C2
   closure is explicitly **not** confirmed and no trade is taken. **[P]** — whether the CISD must sit
   inside the *wick* specifically or anywhere inside the daily candle's range is stated both ways across
   the series.
   The intraday equivalent that fixes the low/high of the day is the same shape one step up: a **4-hour
   candle closure** taking out a low **plus an hourly CISD**; once that exists, the extreme is treated
   as the day's low and a *new continuation* is sought to enter on — the reversal itself is not the entry
   (`intraday-reversal`).
4. **Reversal-day tradeability gate:** small wick → the reversal candle itself may be traded; large
   wick → do not, trade the following candle (§3.6).
5. Fractal: on the hourly, "previous day high" becomes "previous candle's high". He prefers not to
   frame reversals below the 4-hour ("it gets messy").

The if/then discipline that operationalises the EQ (`eq-if-then-pd-array-match`): before the next
candle opens, write **both** branches — EQ respected → target the far side; EQ not respected → flip.
Then search *only the half consistent with the bias* for a PD array (FVG, opposing candle / order
block, or protected swing), and take the protected swing in that half as the day's invalidation. A PD
array that is tagged and not respected is ignored; move to the next one in that half.

**Inside days** collapse to exactly three points of interest: previous day high, previous day EQ,
previous day low — and *only* those. A close through the EQ is read as a sweep of the liquidity around
it, not as a bias invalidation (`inside-day-three-levels`).

**Which timeframe confirms the day's wick depends on the session** (`daily-wick-confirmation-timeframes`),
because volatility rises across the day:

| Session | CISD timeframe | Closure alternative |
|---|---|---|
| Asia | 1-hour | 4-hour closure |
| London | 15-minute or 30-minute | 4-hour closure |
| New York | 5-minute or 15-minute | 1-hour closure (sometimes 30m) |

A higher-timeframe CISD always counts if it has already occurred; the map is a floor, not a ceiling.
The stated reason for dropping down in New York is that waiting for the hourly leaves you behind the
move. **There is only one CISD per day** — the one that forms the daily candle's wick; anything that
looks like a second is a continuation off the first (`one-cisd-per-day`).

**Daily bias from candle formation** covers the shapes: previous day swept the prior low and closed
back above → bullish; the developing candle's internal sequence (open, first extreme, close) is read
the same way; a contrary CISD on lower timeframes argues against the read
(`daily-bias-candle-formation`).

## 2.5 Profiles

### Daily profiles

Four shapes, classified by **where in the day the manipulation happens**
(`daily-profile-framework`). Session windows: **London 02:00–05:00**, **New York a.m. 08:30–12:00**
(the 12:00 end is stated to be his personal extension) (`daily-profile-session-windows`).

| Profile | Recognition | Source |
|---|---|---|
| **London Reversal / NY Continuation** | London (02:00–05:00) runs counter to the daily direction, **reaches a relevant HTF PD array**, and changes the state of delivery there. New York continues off it. | `london-reversal-profile` |
| **New York Reversal** | London ran counter but did **not** reach a relevant PD array — so the run continues into New York, where the level is finally reached and the reversal forms there. | `new-york-reversal-profile`, `relevant-htf-pd-array-test` |
| **New York Manipulation** | London consolidated or produced nothing usable. New York (08:30 or 09:30) sweeps one side of London's range, changes the state of delivery, and expands the other way. Textbook Power of Three. | `new-york-manipulation-profile` |
| **Seek & Destroy** | Every attempt to leave the range returns into it; London takes *both* Asia extremes; the daily candle is an outside/indecision bar. **Stand-aside day.** | `seek-and-destroy-profile` |

The discriminator between the first two is a single question: **did London reach a relevant
higher-timeframe PD array?** (`relevant-htf-pd-array-test`). A London structure shift with no relevant
level behind it is a *fake* change in the state of delivery, and the swept liquidity is expected to be
run again around the New York opens. "Relevant" is never defined **[GAP]** — this underspecification
propagates to both profiles.

Seek & Destroy has one handling if you trade it at all: **outside-in**. Mark every deviation out of
the range and trade back into it, targeting range equilibrium, then the OTE of the leg, then the
opposite extreme (`seek-destroy-target-ladder`, `seek-destroy-outside-in-entry`). No stop is ever
given for it **[GAP]**, and his own stated default is to avoid the profile entirely.

The daily-candle shape underneath all four is the OHLC/OLHC argument, which is arithmetic rather than
behavioural: a bullish candle that does not open exactly on its low **must** trade below its open to
put the low in first — open, low, high, close. Bearish mirrors. So with a bullish expectation you look
to buy at or below the opening price; with a bearish one, to sell between the high and the opening
price (`daily-ohlc-candle-shape`). The shape is chosen by the draw on liquidity, not by the candle.
Note the shape rule is about the *order* of the extremes, so on a closed candle it is not recoverable
from OHLC alone **[GAP]**.

**The profile must confirm the bias.** Where two outcomes are both live, do not choose — let the
profile show its hand. A single failed continuation signature is *not* grounds to switch the bias
(`daily-profile-confirmation`). What *would* count as invalidation is never given **[GAP]**.

### Weekly profiles

You do **not** predict which weekday makes the weekly extreme. You let it form, confirm it with a
**daily C2 closure plus an hourly CISD inside that candle**, and then trade the following days as
continuations away from it (`weekly-profile-framework`). The weekday of the confirmed extreme
classifies the week:

| Profile | Extreme forms | Trade | Source |
|---|---|---|---|
| Classic Expansion | Monday or Tuesday | C3 (next day), then C4 if C3 closes well; 2–3 expansion days; Friday caps the range | `classic-expansion-week` |
| Midweek Reversal | Wednesday (Mon+Tue oppose the bias, building the weekly wick) | Thursday = C3, Friday = C4 | `midweek-reversal-week` |
| Intraweek Reversal | A reversal that is *not* the weekly extreme (Mon+Tue expand, Wed reverses) | Leave the second expansion day alone; wait for the new swing point | `intraweek-reversal-week` |
| Thursday Counter | Mon–Wed expand with no significant internal swing into a relevant level | Thursday counters; trade Friday back into the range | `thursday-counter-week` |
| TGIF | A classic-expansion week whose weekly objective has been **hit** | Friday reversal back into the range; 20–30% of the weekly range as the zone | `tgif-setup` |

The weekly profile is *not* a weekly bias — he holds none. It is daily bias chained across the week,
which is the daily C2→C3→C4 sequence, and it stops before C5 (`weekly-profile`). Monday is skipped
"90–95% of the time"; the one stated exception is a **Friday reversal**, which makes Monday the C3 of
that sequence (`monday-trade-rule`, `no-monday-rule`). The **weekly opening price** is marked as a
single horizontal level across the week on the hourly chart and treated as "fair value for the week" —
though it is used for *review*, not entry, and no trading rule is derived from it
(`weekly-open-as-fair-value`).

## 2.6 Correlated assets: relative strength, SMT, PSP

**Ordering rule, stated as doctrine:** you do not find an SMT and build a model around it — you find
the model and *then* check for SMT (`smt-requires-framework`). The gate is concrete: a C2/C3 closure at
a POI **plus** the aligned lower-timeframe CISD must exist first. An SMT present before that is
ignored however clean it looks.

- **SMT** = pick **one** shared level; one asset trades beyond it and the correlated one does not. At
  the lows it is bullish, at the highs bearish (`smt-divergence`). Prefer the 15-minute for spotting;
  require it to coincide with a liquidity grab or a POI, not open space.
- Three variants by position in the sequence: **reversal SMT** (C1↔C2), **continuation SMT** (C2↔C3),
  and **double SMT** (`smt-reversal-continuation-double`).
- **SMT inside a fair value gap** is a third location: one asset trades up into its gap, the other does
  not (`smt-in-fair-value-gap`).
- **SMT has its own invalidation level** — the held low/high of the diverging asset; if that is taken
  the divergence no longer exists (`smt-invalidation-level`). This is the only place SMT is given a
  standalone stop.
- **SMT can substitute for a sweep.** Where the model needs a liquidity sweep to validate a swing
  point or a protected swing and *this* asset did not sweep but the correlated one did, treat the level
  as manipulated and use the opposing candles that made the failure swing. The closure is still
  required — SMT waives the sweep, not the confirmation (`smt-swing-point-substitute`).
- **[P] — is SMT ever a signal on its own?** Two videos in the same older playlist disagree
  (`smt-as-confirmation-not-signal`): one says SMT is a confluence to an *already existing* model and is
  never the trigger; the other permits a **direct entry on the diverging asset**, with the stop at the
  diverging low/high. The later canon sides with the first. Note the second is the only place SMT is
  given its own invalidation level, which is what makes it independently useful.
- **PSP** = two correlated markets closing opposite colours on the same candle; surfaced only as "C2
  plus a PSP", never standalone (`psp-precision-swing-point`).

**Asset selection** — rank the correlated set and trade the right one
(`relative-strength-asset-selection`, `relative-strength-weakness`), using three tools in order:
1. **SMT** at a shared level — the asset making the lower high is weaker.
2. **Separation** — with no obvious SMT, distance travelled from the shared reference; further = stronger.
3. **Candle closures** — doji/small range = weaker; engulfing = stronger.

Then: longs on the strongest, shorts on the weakest, **never the lagging asset**; when the ranking is
switching intraday, take the middle asset (ES for the index triad)
(`relative-strength-asset-selection`). Mechanical aid: chart **ES/NQ as a ratio** — bullish ratio means
ES strong / NQ weak (`es-nq-ratio-chart`). He offers, explicitly as an untested theory, that reversals
on the ratio chart may *lead* the instruments' own reversals (`ratio-chart-reversal-lead`).

Cross-asset sequencing rules: **the strongest asset must reverse before the weakest can expand**
(`cross-asset-reversal-confirmation`); a target can be taken as satisfied when the *correlated* asset
tags it (`cross-asset-target-transfer`); decoupled indices are expected back into alignment, and the
tradeable question is which one does the realigning (`decoupling-realignment`). One further move exists
and is stated to be undocumented elsewhere: **framework transfer** — import the C2/C3/C4 labelling from
a correlated asset that *does* show a clean framework onto one that does not, and trade the second
asset's candles as though they were C2/C3/C4, still requiring a continuation on the target asset
(`framework-transfer`). No condition is given for when transfer is legitimate versus when the asset
should simply be skipped **[GAP]**.

For **forex**: the dollar is the gate (`dollar-gate-for-fx`) — read DXY first; if it is consolidating,
do not frame EU/GU at all and pair currencies against each other instead. To choose between EURUSD and
GBPUSD, read the **EURGBP cross**: bullish EURGBP = euro stronger, pound weaker; then pair the weaker
foreign currency against a bullish dollar (`eurgbp-relative-strength-cross`,
`currency-pairing-opposition`). Never pair a directional currency against a consolidating one.

He does **not** use cross-*asset-class* correlation — no DXY-vs-gold, no DXY-vs-indices, no yields —
on the empirical claim that the correlation broke down (`intermarket-correlation-not-used`).

## 2.7 Phases of price

The cycle is **large range → small range → new large range** (`phases-of-price`). Four phases, with a
transition table (`phases-of-price-transitions`):

- **Expansion** — one-sided move with very shallow counter-moves (`expansion-signature`). It is the
  fixed entry point of the cycle.
- **Retracement** — slow, shallow, small range, terminating at a PD array (usually an FVG)
  (`retracement-phase`).
- **Consolidation** — price remains internal to a marked high and low (`consolidation-phase`,
  `consolidation`).
- **Reversal** — **expansion met with expansion**; that pair of legs *is* the higher-timeframe wick
  (`reversal-signature`, `htf-wick-formation`).

Legal transitions: expansion → retracement (continuation signature); expansion → consolidation
(ambiguous, resolved by whether the range is manipulated or broken out of); expansion → opposing
expansion (reversal). Consolidation → expansion is the only legal successor of consolidation
(`phases-of-price-transitions`, `continuation-signature`).

**The one mechanical test in the phase layer** is the protected-swing discriminator: a counter-move is
a *retracement* only if it forms a protected swing — i.e. price reaches an important level and then
closes through the series of opposing candles that made the extreme. If it does not, it is a
*consolidation* (`consolidation-vs-retracement-test`). Corroborating signatures: price staying inside
one prior candle's range; an inside bar; a close-through that takes longer than about half the candle.

Handling by phase:
- **Consolidation** → wait for one side of the range to be swept; only the range edges are traded, and
  only back into the range (`range-edge-trading`, `consolidation-sweep-entry`). At the instrument level
  he stops watching a consolidating market entirely until one side is taken
  (`consolidation-range-no-trade`, `consolidation-avoidance`). On a no-bias range day the working
  assumption at 09:30 is that the nearer extreme is swept first, then price rotates — and this is used
  to *stay out*, not to enter (`consolidation-open-whipsaw`).
- **Retracement** → wait for the closure through the opposing candles, then take the continuation.
- **Reversal** → only at a *relevant* level; previous day and previous week extremes always qualify
  (`reversal-signature`, `relevant-level`). The discriminator between a genuine sweep and a level taken
  as part of an ongoing consolidation is the **reaction**: a real sweep produces an immediate V-shaped
  reversal; a consolidation sweep is lethargic and drifts sideways (`liquidity-sweep-vs-consolidation`).
- **Sequence quality** → after an expansion leg the only continuation-compatible follow-ups are a
  consolidation or a retracement; a second expansion in the *opposing* direction flips the read to
  reversal and the extreme behind the move is expected to be taken. Let two candles print before
  classifying, and treat three consecutive expansions with no interleaved retracement or consolidation as
  a degraded sequence (`expansion-sequence-quality`).
- **Aggressive expansion yields little or no retracement** — either a very shallow one (into a fair value
  gap and no further) or none at all. If no retracement into a POI occurs there is simply **no setup**;
  if the trade is still wanted, enter at the candle **open** rather than waiting for a pullback
  (`aggressive-expansion-no-retracement`). "Aggressive" is the same single threshold as displacement
  (§3.9).
- **After three expansion days** (or two very large ones), stop seeking continuation — a new phase is
  due (`dont-trade-after-expansion`, `expansion-exhaustion-avoid-price`, `phases-of-price`).

"Failure to manipulate" is deliberately deflated to this framework: price expands into the target
level and either expands back out (reversal) or does not (continuation through it)
(`failure-to-manipulate`).

**The AMD / Power-of-Three layer is inherited and externally confirmed.** Accumulation near the period
open, a manipulation excursion sweeping stops *opposite* the intended move, then distribution to the
real objective; the manipulation forms the candle's **wick** and the distribution its **body**; applied
fractally across periods and anchored on the **opening price**; Asia accumulates / London manipulates /
New York distributes (`power-of-three-amd`, `manipulation-first-heuristic`, `box-setup`). The public
literature describes this line for line (`meta/external_crossref.md` §2). What is *not* inherited is the
C1–C4 sequence — PO3 is **intra-candle** (three phases inside one candle), the fractal model is
**inter-candle** (four consecutive candles with closure tests between them), and none of C2's, C3's or
C4's tests exists in any external PO3 description. The two meet at exactly one place: **IC-CISD is PO3
applied inside a single candle** — wick = manipulation, body = distribution, and the IC-CISD is the
mechanical trigger declaring the manipulation over (`ic-cisd`).

## 2.8 The no-bias states

The method has explicit ways of saying *no*:

- Both previous-candle sides taken, or an inside/indecision candle, or a doji daily close → no bias
  (`daily-bias-framework`, `daily-ohlc-candle-shape`).
- No daily C2/C3 closure, or no hourly CISD → no bias (`daily-bias-c2-c3-h1-cisd`).
- Instrument classified as consolidating → not watched (`consolidation-range-no-trade`).
- No level to trade away from → no trade, accept the missed move (`level-to-trade-away-from`).
- No trustworthy invalidation → an idea, not a setup (`idea-vs-executable-setup`).
- Seek & Destroy day → stand aside (`seek-and-destroy-profile`).

---

# 3. The fractal model (C1–C2–C3–C4)

## 3.1 The numbering

Anchored on the swing point, not the clock (`four-candle-model-window`):

- **C2** is always the swing high or swing low.
- **C1** is the candle before it — it supplies the liquidity C2 sweeps and carries no label of its own.
- **C3** is the candle after; **C4** the one after that.
- C1-C2-C3 constitute the swing point; C4 is the continuation.
- **There are exactly two closure definitions — C2 and C3. There is no C4 closure.**

He states the derivation: price cannot reverse without a swing point, so he labelled the candles around
the swing point and asked which of those he could actually *define* — producing exactly two
(`four-candle-model-window`). The labelling is retrospective: C2 is only known to be the swing once C3
exists, which is why the C3 closure exists (`four-candle-model-window`).

## 3.2 C2 — the reversal closure

**Test** (`fractal-model-c2`):
- Bearish C2: `high[i] > high[i-1] AND close[i] < high[i-1]`
- Bullish C2: `low[i] < low[i-1] AND close[i] > low[i-1]`
- A sweep of the previous extreme **without** the close back inside is not a C2 — discard it.

**Two gates**, both required (`fractal-model-c2`, `indicator-print-conditions`):
- **Gate 1 — point of interest.** The sweep must occur at a POI: a fair value gap traded into, or a
  high/low taken out. "I need a point of interest to frame a candle closure."
- **Gate 2 — lower-timeframe CISD.** A change in the state of delivery must form inside C2 on the
  aligned lower timeframe before C3 is traded.

**[P] — close reference.** "Closes back inside the previous candle's range" is stated as closing back
above/below candle 1's low/high specifically, so a close inside candle 1's *body* is not required — but
whether a body close or a wick close is required is never stated (`fractal-model-c2`).

**Quality tests on the C2** (`reversal-candle-quality`):
- **Internal sequence:** a bullish C2 should be open-low-high-close. An open-high-low-close candle is
  an *expansion* candle and is rejected as a reversal even if the closure levels line up.
- **Ideal formation:** the closure additionally clears the *series of opposing candles* that traded
  into the POI, creating a protected swing in the same bar (`ideal-formation`). Closing over candle 1's
  body alone explicitly does **not** make it ideal.
- **Two-sided C2** (valid on both bullish and bearish sides): take only the side carrying an hourly
  CISD, and demand additional intraday confirmation.
- **"Reversal looking" but not a C2 closure:** not tradeable; wait for the next candle's closure.
- If C2 has a large wick, mark 0.5 of the wick — C3's wick must respect that half
  (`half-wick-respect`).

## 3.3 C3 — the continuation, and its parameter

C3 is where the model actually makes its money. The stated reduction is: drop C2 and C4 and trade
**only C3, on several timeframes at once** (`keep-it-simple-c3-stack`). And the highest-win-rate subset
he names in the whole model is **C3 entered with an intracandle CISD**
(`c3-with-ic-highest-winrate`).

**C3 has two senses and they must be kept apart:**

**(a) C3 as a trade** — the candle after a *confirmed* C2. Direction is what C2 reversed toward. Trade
only when C2 was a genuine reversal candle; a C2 that already expanded is a disqualifier (a new phase
may begin) — *unless* short-term drawn liquidity is still intact (`fractal-model-c3`). Inside C3, let
the counter-directional wick form, then trade the body via a continuation order block (`ic-cisd`,
`wick-trust-test`).

**(b) C3 as a closure** — used when the reach into the POI produced *no* C2 closure. This is the
contested one. **C3 IS NO LONGER DEGENERATE** — the old EQ-based reading (~100% of candles qualify) has
been retired.

> **[P] — the C3 closure reference. Compute both; report the disagreement rate.**
>
> - **Reading A (this unit's dedicated Shorts):** C3 closes beyond the **BODY / opening price of C2**.
>   "Price is going to close over the body of candle two." A C3 closure exists *only when C2 failed to
>   close* (`fractal-model-c3`).
> - **Reading B (sibling unit):** the reference is C2's **EXTREME** — closes above C2's high (bullish) /
>   below C2's low. Strictly stronger, and will select a subset of Reading A's bars (`fractal-model-c3`).
>
> Neither source reconciles them. A detector should compute both and report the disagreement rate
> rather than pick one. Measured base rate for the sequential reading: ~20% of candles on 1h/4h/1D
> (`meta/fractal_reading_comparison.md`).

Note a further wrinkle inside Reading A itself: `vn1RYjhJUnQ` says "the opening price in candle 2" and
`SF61vCsBl1A` says "below the body of candle two" — these coincide only when C2 closed in the sweep
direction (`fractal-model-c3`).

**After a C3 closure:** mark the entire C3 range and require the relevant half of it to be respected
(`fractal-model-c3`, `upper-half-eq-expansion-filter`). If the continuation fails to close over its
level, wait for a **new** extreme to form a **new** protected swing and re-anchor (`fractal-model-c3`).

## 3.4 C4 — the second continuation

C4 is "always a continuation if the trend read is correct", and there is **no C4 closure**
(`fractal-model-c4`).

Preconditions: a confirmed three-candle swing point (C2's extreme flanked by a higher low / lower high
on each side), plus a **strong C3 closure** (`fractal-model-c4`). "Strong" is never given a test **[GAP]**
— but it is **not** a wick-quality term, and treating it as an alias for "small wick" is backwards. The
one narrated adjudication accepts a move as *strong displacement* **despite a heavy wick**, because
there was a body close: **"strong" grades the CLOSE** (`meta/threshold_fits.md` §4). The matching
quantity is stated elsewhere in his own words — "large aggressive candles with closes in the high or the
low" (`displacement`), i.e. where in its own range the candle closed. One further corpus test exists and
it is on the **time** axis: *"just because it does have a closure over, doesn't mean it's a good
closure"* — a close arriving after price consolidated for half the candle is downgraded to "usually just
a consolidation" (`consolidation-vs-retracement-test`, `daily-bias-c2-c3-h1-cisd`). That rider applies to
`fractal-model-c4`, `bias-confirmation-tradeoff` and `c2-confirmation-scaling` alike.

**The one numeric filter in the whole sequence:** mark 0.5 of C3's range. Bullish — C4's **low** must
form in the **upper half**. Bearish — C4's high in the lower half. The reason given is that expansions
do not give deep retracements (`fractal-model-c4`, `upper-half-eq-expansion-filter`).

Then: inside that half, find a POI on the intermediate timeframe for C4's wick to form at, and take the
entry on the lower timeframe (`fractal-model-c4`). SMT, or a daily CISD on the daily itself, can
substitute for the sweep at the swing point.

**Stand-aside:** from C5 onward, treat a new phase of price as likely; avoid C4 entirely if both C2 and
C3 already expanded (`fractal-model-c4`, `weekly-profile`).

**Only one CISD is needed per sequence, and it belongs to C2.** C3 and C4 continuations run off that
single confirmation (`single-cisd-at-swing-point`).

## 3.5 What counts as a valid model

A "model" exists only when a higher-timeframe C2 or C3 closure **at a point of interest** is paired
with a **CISD on the aligned lower timeframe**. Either alone is not a setup. Without the CISD you do
not drop timeframes, you do not look for SMT, and you do not trade (`indicator-print-conditions`).

**Clean-day checklist** (`clean-day-criteria`) — asked directly what makes a day clean:
1. Daily candle is a **C3** in the anticipated direction.
2. 4-hour candle is a **C4** within that daily candle.
3. The aligned timeframes have **not already expanded**.
4. A reversal has formed on the execution timeframe leaving a **new protected swing**.

**Alignment** is what he calls expansion: daily, 4-hour and hourly all supporting the same direction at
the same time (`timeframe-alignment`, `aligning-expansion-candles`). Minimum two aligned expansion
candles; three preferred for sub-5-minute execution. If any layer has a large wick or opens against the
intended direction, you do not trade that layer — you wait for its next open
(`aligning-expansion-candles`). The simplest expression: **C3 on the daily, C3 on the 4-hour, C3 on the
hourly — "by definition, that is just a trend."**

## 3.6 Wick geometry — the gate the whole model turns on

The primitive is the **opposing run**, which is his own term and is measurable *live*: the distance from
the candle's **opening price** to the extreme against the intended direction, plus the fraction of the
candle's period elapsed when that extreme printed. At the close it becomes the wick (`opposing-run`).

**The numerator is settled and one-sided.** "When I say opposing run, I mean from the opening price to
that high" — so the measured quantity is **open → extreme against the intended direction**, *not*
`high − low` and *not* the sum of both wicks (`opposing-run`, `wick-size-test`;
`meta/threshold_fits.md` §1). This resolves what the library previously recorded as an open question
about the denominator, and it collapses `wick-size-test`, `small-wick-expansion-rule`,
`aligning-expansion-candles` and the candle-level sense of "shallow" onto **one measurable object**.
Anywhere this spec says "measure the wick", use that definition.

**The rule** (`small-wick-expansion-rule`):
- **Small wick / shallow opposing run** → the candle supports expansion; it may be traded in its
  direction.
- **Large wick / large opposing run** → the candle does **not** support expansion; wait for the next
  candle open and trade C3 instead. Targets revert to the candle's opening price and the liquidity
  around it (`large-wick-target-adjustment`, `reversal-candle-target-adjustment`).

The reason given is range budgeting: in C2 and C3 price travels roughly the same distance, but C2
spends half its time going one way and half the other, while C3 is one-sided
(`small-wick-expansion-rule`).

**The three ways to trade a reversal, ranked by difficulty** (`wick-scenario-difficulty-ladder`):
1. *Preferred* — let the large-wick reversal candle close, then trade C3 provided C3 has a small wick
   and a lower-timeframe CISD.
2. *Harder* — the reversal-to-expansion candle (reverses and expands within itself): requires a small
   opposing run, a lower-timeframe CISD, **and** enough time left in the candle for the range to expand.
3. *Avoided* — trading the large-wick reversal candle itself. Daily only, executed on lower timeframes
   back toward the daily open. The stated reason it is worst: without the candle close there is no
   filter.

**Candle taxonomy** (`candle-type-wick-to-body`): **reversal candle = the wick is larger than the
body**; **indecision candle = a longer wick on each side with a small body, open and close very close
together**. The directional/expansion candle is the complement — small wick, large body
(`small-wick-expansion-rule`, `expansion-signature`).

> ### The wick-size threshold — a CEILING is given, the operating point is not.
>
> **Correction to RESUME finding #5.** The settled negative is right that **no wick-to-body *ratio* is
> ever spoken**. But it overstates the case: **0.5 is spoken constantly, under a different name** —
> *equilibrium*, *the upper half*, *50% of the wick* — and one video says outright that this is what it
> is for: *"It is a mechanical way to measure wick size."* That is corroborated in his own voice by
> `Te9jUijPXZo` ("mark out the upper half of the candle for a bullish scenario") and `LKNQDAdId4s`
> ("I'd want to see if price respects .5 of this Wick") (`meta/threshold_fits.md`, headline correction).
>
> **So the corpus does give a mechanical measure — and it is nearly non-binding in practice.** Measured
> on 1,074,472 XAUUSD M1 bars, a 0.5-of-range cut admits **~85% of all candles** (p85 on 15m/1h/4h, p87
> on 1D). It is a **ceiling** — the point past which a candle is definitively a *reversal* candle — not a
> filter. The filter has to sit far tighter, and the corpus never says where.
>
> What else is attested:
> - **The one corpus-attested classification cut: wick vs body, crossover 1.0.** Three independent videos
>   state it — "a large wick and a small body" / "the wick is larger than the body" / "a small wick and a
>   large body" (`candle-type-wick-to-body`, `small-wick-expansion-rule`, `aligning-expansion-candles`).
>   On XAUUSD it sits at p65–p68 and inside a plateau rather than on a cliff. **The separation it buys is
>   a higher-timeframe phenomenon** — ~+3 to +4pp on 4h/1D, ~0 on 15m/1h — so a 15m model gating on wick
>   size is using a filter this data does not support (`meta/threshold_fits.md` §1).
> - **Two axes, not one.** The dedicated video grades the run on *range consumed* **and** *time consumed*
>   — "we use almost half the time and quite a bit of range" (`wick-size-test`,
>   `small-wick-expansion-rule`, `opposing-run`). Both are computable given lower-timeframe data.
> - **"Shallow", applied to a candle, is the same object** — "is this a shallow run? No, this is a large
>   opposing run" (`wick-size-test`). Do not give it a second threshold.
>
> **Do not conflate two different questions** (RESUME finding #5): (i) *which level do I mark on this
> candle* — answered, see below; (ii) *is this wick small enough to count as expansion* — the ceiling is
> answered, the operating point is not.
>
> **Method:** the operating point must be fitted, and a supervised fit against his narrated accept/reject
> calls turned out **not to be available** — 56 curated calls were mined and *none* could be tied to a
> dated bar, because the transcripts name no instrument, date or price
> (`meta/qualifier_calls.md`, `meta/threshold_fits.md`). What the mining did deliver is **which quantity
> to measure**, with the numerator pinned by his own words. Everything past that is a
> distribution-anchored default, graded, and must be swept.

**Which level to mark IS answered** (`wick-vs-body-marking-rule`) — a within-candle comparison:
- Body dominant (full body, little wick) → zone = open..close; half-level = **mean threshold** (50% of
  the body).
- Wick dominant → zone = close..extreme; half-level = **0.5 of that wick**.
- Bodies must respect the level; wicks may trade into it.

**The two 0.5s are ONE rule with a branch, not two rival rules.** The library previously recorded 50%
of the *candle* and 50% of the *wick* as an unresolved collision (`half-wick-respect`,
`equilibrium-eq`). One video resolves it: *"it was such a large wick on that candle I would use 50%"* —
i.e. **the default reference is 50% of the candle, and you switch to 50% of the wick only when the wick
is large** (`meta/threshold_fits.md` §1). That is the same branch `wick-vs-body-marking-rule` states for
marking a block's level, and the same branch `equilibrium-eq` states for choosing the EQ. Implement it
once.

**The half-wick respect test** (`half-wick-respect`): measure the wick from the candle **body** to the
extreme and mark 50%. Bullish — the upper half of the wick must support price higher. A close through
0.5 of the wick means the candle is unlikely to be an expansion candle and the opposite extreme becomes
the more likely draw.

**Let the wick form, trade the body** (`wick-trust-test`) is the operational core. Do not try to catch
the extreme. Confirm the wick with a lower-timeframe protected swing / CISD, then trade the body. Three
conditions for trusting an extreme: it formed **early** in the higher-timeframe candle; the reach was a
**shallow** opposing run; and a lower-timeframe CISD closed through the series that made it. If all
three hold, the extreme is the stop; otherwise widen to a level you do trust, or skip.

**Higher-timeframe wick formation** (`htf-wick-formation`): an aggressive move into a level immediately
met by an aggressive move out of it is, one timeframe up, a single candle with a long wick — and one
above that, a reversal candle. That is the same event as *expansion met with expansion*
(`reversal-signature`). The lower-timeframe equivalent: run-and-return at a range low prints a hammer
on the timeframe up (`aggressive-run-hammer-signature`).

## 3.7 EQ, half levels, and the T-spot

**"EQ" names three different levels in this corpus and they are used for different jobs**
(`equilibrium-eq`) — this must be disambiguated before any detector is written:

| Reading | What it is | Used for |
|---|---|---|
| (a) Previous-day-range EQ | 50% of the previous day's high–low | Continuation days must respect it: *no hourly closures beyond it* |
| (b) Current-candle EQ | 50% of the HTF candle's range | C4 must respect 50% of C3's range; drawn by the indicator |
| (c) Wick EQ | 0.5 of a wick, body-to-extreme | The half-wick respect test |

Plus a fourth use: a range's equilibrium as a **magnet** — price deviating outside a consolidation is
expected back to the middle (`equilibrium-eq`, `seek-destroy-target-ladder`).

Selection rule where one is given: expansion candle (large body) → EQ = 50% of the full range; candle
with the larger feature in its wick → EQ = 50% of the wick (`equilibrium-eq`). **This is the same single
branch as §3.6** — default to 50% of the candle, switch to 50% of the wick only when the wick is large —
and readings (b) and (c) above are therefore *one rule*, not two rivals. The dedicated EQ video says to
draw the fib **wick high to wick low** and *not* to use bodies — bodies are reserved for the CISD and for
order blocks (`equilibrium-eq`). That directly contests the body-based readings elsewhere in the corpus
**[P]**.

**The upper-half EQ expansion filter** (`upper-half-eq-expansion-filter`) is the crispest form: when
price is expanding, the next candle must open and make its **low in the upper half** of the previous
candle's range (bearish mirror), then expand. Equivalently in fib terms: the retracement must not reach
into a *discount* of the higher-timeframe range. Two failure branches: (A) price opens and trades a lot
lower than the EQ → expansion is off, expect the previous candle's low to be taken; (B) price reverses
back to its opening price → the **next** candle becomes the expansion candidate.

**The T-spot** is the indicator-drawn box marking where the higher-timeframe candle's wick is expected
to form — where a bearish day should make its high (`t-spot`). Functionally it is the zone that must
hold: closing over it on a bearish setup is the early warning that the continuation will fail. Two
constructions appear: the overlap of 0.5 of the HTF wick and 0.5 of the CISD (or of the daily opposing
candle); and, in one example, simply "the equilibrium". **Its derivation is explicitly withheld** —
see §9.

## 3.8 Protected swing — the invalidation

The single most important structural object, because it is the stop.

**A protected swing is a high or low expected to hold while the trend continues.** Construction, in all
three variants, is *point of interest → closure through the series of opposing candles that made the
extreme* (`protected-swing`):

1. A short-term low/high is **swept**, then price closes through the series of opposing candles that
   made it.
2. No sweep here, but the **correlated asset swept** — SMT substitutes, and the opposing candles that
   made the failure swing are used (`smt-swing-point-substitute`).
3. No sweep at all, but price **reaches into a fair value gap**, and the opposing candles that made the
   extreme inside it are closed through.

Fallback where neither an FVG nor a sweepable extreme exists: use **0.5 of the opposing candle** as the
point of interest (`protected-swing`, `point-of-interest`).

Once closed through, the extreme is protected and must hold for the trend to continue. Each new
protected swing supersedes the last as the invalidation (`protected-swing`). If price makes a *new*
extreme before closing through, abandon the old series and track the new one.

**Filters he applies on top of the mechanical definition** (all discretionary **[GAP]**):
- Require "some sort of reach" — a negligible sweep at near-equal highs does not qualify, and he notes
  his own indicator *would* mark it (`protected-swing`).
- Require **separation** between the swept level and the new swing; a swing forming at equal lows with
  the swept level is not tradeable away from (`protected-swing`, `liquidity-sweep`).
- Reject a protected swing that took a long time to form relative to the move — read it as a
  consolidation range instead.
- When the lower-timeframe area is messy, **ignore the small candles and take the whole move** as the
  series (`swing-forming-candle-selection`).

## 3.9 Supporting structural primitives

- **Opposing candles** are always used as a **series**, never a single candle — because a series of
  same-direction closes is one candle a timeframe up (`opposing-candle`,
  `order-block-series-is-htf-candle`). A candle that opens and delivers one way with no wick does not
  make a relevant extreme and does not count (`opposing-candle`).
- **Fair value gap** = three candles where candle 1 and candle 3 do not overlap; measured on the
  **wicks**, not the bodies. Bullish: `low[i+1] > high[i-1]`; bearish: `high[i+1] < low[i-1]`
  (`fair-value-gap`). Consequent encroachment = the midpoint (`consequent-encroachment`). Multiple
  adjacent gaps are treated as one large gap; a closure must clear the whole series.
- **Inversion FVG** = a gap not respected and swiftly closed *through*; support becomes resistance. A
  close beyond the CE alone is explicitly **not** sufficient — the close must be beyond the whole gap
  (`inversion-fair-value-gap`, `consequent-encroachment`). Within the fractal model an inversion is only
  valid inside a C2 that supports expansion (small wick), after a sweep or SMT
  (`inversion-fair-value-gap`).
- **Rebalance** has two cases: a gap closed *after* it is created (no imbalance left, so a reversal
  becomes possible), and — the majority case — a gap rebalanced *before* it is created, where price
  trades back so that no FVG forms at all. He focuses on the second on the daily (`rebalance`).
- **Old gaps carried across the curve** — after a smart money reversal, fair value gaps left on the
  previous side of the curve are extended forward and reused as support (reaccumulation) or resistance
  (redistribution); the gap is not required to be respected in its original polarity, because it is being
  reused precisely *because* price traded through it (`old-fvg-across-the-curve`). No rule says which
  gaps to carry or how many **[GAP]**.
- **Volume imbalance** = a gap between one candle's close and the next candle's open where price
  nonetheless traded through (ranges overlap). A **gap** is the same with a complete absence of trading.
  Both are two-candle objects; an FVG is three (`volume-imbalance`).
- **Balanced price range** = the *overlap* of a bearish and a bullish FVG; the traded zone is the
  **smaller** of the two (`balanced-price-range-overlap`). Reject one sitting on the wrong side of
  equilibrium.
- **Market structure shift** = a prior swing high/low **broken with displacement**, and the displacing
  leg leaves a fair value gap which is the entry (`market-structure-shift`). It is a *different object*
  from the CISD — see §4.3. **Reversal-or-pullback test:** structure not broken ⇒ pullback, full stop;
  broken with displacement ⇒ reversal *on that timeframe* — and check the timeframe above, because a
  5-minute reversal under an intact 15-minute uptrend is a retracement toward the 15-minute imbalance
  (`reversal-vs-pullback-test`).
- **Displacement** — the corpus's highest-leverage undefined term. **"Displacement" and "aggressive" are
  the same thing**, used in apposition — *"an aggressive move or displacement above"* — so what looked
  like two separate undefined terms blocking 37 and 34 concepts is **one threshold governing 62**
  (`displacement`, `meta/threshold_fits.md` §2). That materially simplifies the model and should be
  implemented as a single parameter.
  It has **two components**. (a) A **structural gate with no knob**: every time he adjudicates
  displacement on a chart he resolves it as a **close** beyond the reference level, not a wick through
  it (`displacement`, `market-structure-shift`) — unambiguous, and satisfied by a one-tick close, which
  is why (b) exists. (b) The **comparative magnitude test**, the only measurement procedure in the
  corpus: after a short-term high breaks, take a fixed candle window (four in his worked example) and
  compare both the window's range and the distance travelled beyond the broken high against a
  *non-displacing* instance of the same event; displacement is the larger range AND greater distance in
  the same candle count. **This is relative, not absolute — no ATR multiple, body ratio or point value
  exists anywhere** **[GAP]**.
  The **FVG proxy** — a break with no fair value gap is rejected as not displacement — is the most
  mechanical thing on offer but is **weak in practice**: a same-direction FVG appears in **61–77% of
  break windows**, so "no FVG ⇒ no displacement" rejects only about a third
  (`meta/threshold_fits.md`). Treat it as **advisory, not gating**.
- **Advanced market structure** (short-/intermediate-/long-term highs and lows) is defined
  (`advanced-market-structure-labeling`, `intermediate-term-swing-formation`) and used for stop
  placement, but he later lists it among things he *removed* from his model
  (`ttfm-minimal-toolkit`).
- **Market curve side** — a positional filter (do not fade the direction price is currently seeking).
  **No rule locates the curve** — nothing says where the buy side ends and the sell side begins
  (`market-curve-side`) **[GAP]**.

---

# 4. Entry

## 4.1 The point-of-interest gate

**Without a POI, no candle closure and no CISD is valid** (`point-of-interest`).

The enumeration: **a fair value gap, a high being taken out, or a low being taken out** — "I use fair
value gaps and highs and lows" (`point-of-interest`). Two extensions: a series of opposing candles can
serve as a POI ("more advanced"); and where neither an FVG nor a sweepable extreme exists, **0.5 of the
opposing candle** is used instead.

The procedure is stated as an ordering: **find the candle closures first, then test each for a POI; a
closure without one is discarded** (`point-of-interest`).

Three refinements:

- **Search order within a range** (from the reversal point to the current extreme): (1) is there an FVG?
  (2) if not, is there a swing high/low to be taken? (3) only if neither, use the CISD level, and
  additionally require 50% of the bodies of that opposing series to hold. If **both** an FVG and a swing
  exist, require both to be tagged (`point-of-interest`).
- **Density scaling** (`poi-density-by-timeframe`): there are six 4-hour candles in a day, so a 4-hour
  candle without a POI is acceptable; there are ~24 hourly candles, so on the hourly a POI is **required**
  as the filter that says which of them matters. Preference is a POI on both the daily and the 4-hour.
- **Reversal vs continuation** (`point-of-interest`): the POI requirement is mandatory for a *reversal*
  and **waived for a continuation**. He says this contradicts his own simplified public teaching, and it
  does — see §8.

The negative form is stated as a standing rule: **no level to trade away from, no trade**
(`level-to-trade-away-from`). The rejection test given is positional — if reversing here would leave a
low untaken to the left, it does not make sense to reverse and form a failure swing there. Accept
missing the move.

"Relevant level" / "key level" / "higher-timeframe objective" / "drawn liquidity" are used
interchangeably and none is defined (`relevant-level`, `important-level`) **[GAP]**. Two decay rules
*are* given: a level price has already traded through stops being relevant; and reaching a level is not
sufficient — you must see whether price actually reversed off it (a V-shape) rather than retracing or
consolidating through (`relevant-level`).

## 4.2 CISD — adjudicated, with one residual parameter

**This is the definition.** From the video whose entire subject is separating CISD from MSS
(`cisd`):

> A change in the state of delivery is **displacement and a CLOSE below (bullish: above) THE OPENING
> PRICE of the up-close candle, or series of up-close candles, that ran into an important level** — and
> that close is what validates those candles as an order block.

Four things follow, all of them load-bearing:

1. **It is explicitly NOT a close beyond a swing high or low.** That is the market structure shift, a
   separate and generally *later* event (`cisd`, `market-structure-shift`). Anything firing on a close
   through a swing was a mislabelled MSS.
   **This is well-founded, not a hedge.** Four independent public sources split the two the same way —
   CISD defined on opens and closes, MSS on highs and lows — and independently reproduce the secondary
   claims that CISD fires earlier and is the less reliable of the two (`meta/external_crossref.md` §1a).
   Build them as **two separate detectors with separate statistics**; the outside consensus is that
   their false-signal rates differ materially.
2. **He requires a point of interest as part of the definition** — a bare close-through with no swept
   level and no FVG does not qualify (`cisd`, `point-of-interest`).
   **Treat this as *his* tightening, not as the definition of CISD.** Outside opinion is genuinely
   split: one implemented detector requires the sweep, another states explicitly that it is a *quality
   filter and not definitional*, and two more sources do not mention a sweep at all
   (`meta/external_crossref.md` §1c). The corpus's internal evidence is multiple videos stating the
   two-part form, so it is right about the channel — but it is stricter than the mainstream.
   **Build the POI gate as a switch, not a hard-wired precondition, and report event counts and every
   downstream statistic both ways.** It is the single biggest frequency lever in the CISD detector.
3. **Two requirements, both needed** in his strictest statement: price reaches into an important level,
   **and** price sweeps an extreme to the left of that level (`cisd`). Same switch applies.
4. **CISD occurs earlier than the MSS** — which is stated as both its advantage and its risk: "it may get
   you into a position that ends up to be a loser" (`cisd`).

**Procedure** (`cisd`):
1. Locate the extreme that engaged the point of interest.
2. Identify the **series** of opposing-close candles that produced it (may be one candle in the dedicated
   model video; a Sunday-session answer says he never uses one candle — **[P]**).
3. Mark the level of that series.
4. Require a **close through** it. Before that close there is no CISD — "we wait".
5. If price makes a **new extreme** before closing through, discard and re-derive from the new extreme.
6. **Fallback:** if there is no clean series of opposing candles, use the **whole move** as the reference.

**Quality tests:**
- A fast **V-shape** is wanted; a close-through that took roughly half the candle to arrive is read as
  consolidation, not a confirmed reversal (`cisd`, `v-shape-reversal-speed`).
- **Speed:** the closure should arrive within roughly **1 to 3 candles** of the reach into the level.
  This is the corpus's only candle-count threshold for "swift", and it is stated as a preference — "I
  prefer 1, 2, maybe three" (`v-shape-reversal-speed`). Longer ⇒ reclassify as consolidation.
- The CISD is not trusted when it simultaneously takes out a short-term high/low
  (`continuation-failure-short-term-target`) or sits at an already-hit objective
  (`continuation-failure-consolidation`).

> ### [P] — WHICH price of the series. This is the whole 22–59% agreement problem.
>
> The extreme reading is **ruled out** — "Mark out the opening price in that series" makes the level an
> *open*, not the swept extreme (`cisd`). What remains undetermined is whether the level is:
> - the **open of the FIRST candle** of the run (stated explicitly twice in one video), or
> - the **highest/lowest open** of the series (what the charts appear to show).
>
> Measured consequences on 3 years of data (`meta/cisd_reading_comparison.md`): series_open ≈ 127
> events per 1k bars on 15m; series_extreme ≈ 120; series_close ≈ 164. Jaccard agreement between
> series_open and series_extreme is **0.56–0.59**; between series_open and series_close, **0.22–0.29**.
> These are genuinely different trading systems wearing one name. **Carry the reading as a parameter.**
>
> **External input — tips the default, does not settle it.** Two independently built public detectors
> both anchor on the **open of the first candle** of the final unbroken run, and neither uses the run's
> extreme (`meta/external_crossref.md` §1b). That is convention from two vendors who may share lineage,
> not proof of what *this channel* means — the corpus's own *"Mark out the opening price in that
> series"* remains the better authority. So: **carry first-candle-open as the sensible default**, keep
> highest-open / series_extreme as the reported alternative, and note that `series_close` is attested
> **nowhere** outside — demote it from a co-equal reading to a diagnostic.

**Historical note that explains the confusion:** CISD appears **zero times** in the older Education-ICT
playlist — "break structure" did its job (`market-structure-shift`). It was later carved out of MSS. The
three readings are stages of an evolution, not simultaneous contradictions.

**Variants:**
- **Early CISD** — a CISD formed inside a still-open higher-timeframe candle. Drawn dotted by the
  indicator; confirms on the closure. Off by default so learners do not trade C2; he takes it only when
  his bias is strong enough (`early-cisd`).
- **Skip the CISD at the target** — when the CISD level coincides with the short-term target there is no
  reward left; substitute other evidence (V-shape, retracement into a gap, SMT) (`cisd-skip-at-target`).

## 4.3 IC-CISD — his own invention

**Purpose, stated as such:** to *mechanically define the formation of a wick* (`ic-cisd`). This is the
same CISD test **relocated** inside a continuation candle — not a rival system.

In C3 of a bullish sequence the candle opens with a short-term *bearish* trend while it forms its lower
wick. When that intracandle trend shifts — the same POI-plus-closure test, producing a protected swing
*inside* the candle — the wick is declared formed and the body can be traded. It applies to C4 as well
as C3 (`ic-cisd`).

**Timing rule attached to it:** it is ideal for the IC-CISD to form **early** in the candle so the candle
has time and range to expand. If it forms late but is still valid, **wait for the next candle** — it
brings new range (`ic-cisd`, `continuation-timing`).

It inherits the unresolved level-of-the-series question from §4.2 **[P]**.

## 4.4 The confirmation ladder

Reversals form in a stated **order**, and each rung is later in time and therefore a worse price. The
rung you take is your confirmation appetite (`order-of-reversal`):

| Rung | Event | Confirmation |
|---|---|---|
| 1 | The sweep / turtle soup / raid of stops | Least — no protected extreme yet |
| 2 | Close beyond the FVG that supported the prior move — an **inversion** | |
| 3 | **Change in the state of delivery** — close over the opposing-close candles that swept the extreme | Stated minimum with rung 2 |
| 4–5 | The **breaker** and the **fair value gap** | Most |

He says to choose one rung and use it consistently; at rung 1 specifically, price will stop you out
repeatedly unless it reverses immediately (`order-of-reversal`). **[P]** — one Short pairs steps 4 and 5
without separating them; the long-form entry orders breaker as 4 and FVG as 5.

**Confirmation scales inversely with bias strength** (`c2-confirmation-scaling`,
`bias-confirmation-tradeoff`):
- **Strong** HTF bias → entry allowed on the first lower-timeframe CISD that confirms the wick.
- **Medium** → require a continuation entry after that CISD, or SMT.
- **Weak** → require both a continuation *and* SMT; otherwise no trade.

Bias strength is never scored and he says so — "once you watch the daily chart enough you'll get a
feeling" (`bias-confirmation-tradeoff`) **[GAP]**.

## 4.5 The continuation entry — his preferred entry

**Doctrine: never enter on the reversal itself; always enter on the continuation that follows it**
(`continuation-over-reversal`). Simplest form: wait for a **lower high** in a bearish sequence, a
**higher low** in a bullish one. The reason given is that a reversal entry with the stop at the extreme
carries no confirmation that price will actually go.

**Two qualifying triggers and one waiver** (`continuation-order-block`):
- (a) price retraces into a **fair value gap**, **or** (b) price **sweeps a low/high**;
- then in either case, the **close through the series of opposing candles** that went into that level
  creates a new invalidation to position from;
- **waiver:** with correlated assets showing **SMT**, an opposing candle is accepted without its own
  sweep or gap tag.
- If neither trigger occurs: **"mechanically speaking there is nothing here for me"** — the move is
  missed.

Timing is a hard filter (`continuation-timing`): frame entries **while the higher-timeframe wick is
forming**, i.e. early in a new HTF candle. If the current candle has already expanded, do not enter —
wait for the next open. The worked rejection: 40 minutes left in an hourly candle.

**Two named continuation failures**, both of which say *wait for another continuation*:
1. **The closure also takes out a short-term high/low or a range extreme** — do not enter on that
   closure; a second, independent reason is that the protected swing is now too far away for acceptable
   R (`continuation-failure-short-term-target`).
2. **The recovery is not a V-shape** — the leg is a consolidation, not a retracement. Flip the level's
   role: the range low becomes the POI you wait for. Ignore every closure internal to the range. Never
   trade the breakout by itself (`continuation-failure-consolidation`).

## 4.6 The entry objects

| Object | Construction | Level used | Source |
|---|---|---|---|
| **Order block** | The opposing candle(s) inside the move that swept a short-term swing **into an important level**; validated only when price closes back through it | The **opening price**; refine to the **mean threshold** (50% of the bodies) | `order-block`, `mean-threshold`, `important-level` |
| **Continuation order block / propulsion block** | An order block formed off another order block, inside an existing leg | Opening price; must not break the **mean threshold** | `propulsion-block`, `continuation-order-block` |
| **Fair value gap** | Three candles, wicks of 1 and 3 not overlapping | Near edge / **CE** / full fill — three accepted return behaviours | `fair-value-gap`, `fvg-three-levels` |
| **Balanced price range** | Overlap of two opposing FVGs | The overlap (the smaller gap) | `balanced-price-range-overlap` |
| **Breaker** | high → low → higher high → **lower low** (bearish); zone = the down-close candles from the first high to the first low | Body or wick per `wick-vs-body-marking-rule` | `breaker-block`, `breaker-continuation` |
| **Mitigation block** | An opposing candle whose extreme is broken; its far extreme must not then be invalidated | Block high / opening price | `mitigation-block` |
| **Unicorn** | Breaker **overlapping** an FVG | The overlap | `unicorn-model` |
| **Inversion** | An FVG closed fully through; polarity flips | The zone, or its CE | `inversion-fair-value-gap` |

**Order-block grading** (`order-block-probability-grading`): large body + small wick = high probability →
use the **opening price**. Small body + large wick = low probability → use the **wick**, or wick-to-open
— and only in an established trend and only when it is the sole opposing-close candle in that range.

**Fair value gaps are not entries** (`fair-value-gap-not-an-entry`). A resting limit inside a gap gets
ripped through, leaving you wrong with no structure to lean on. Wait for a reaction inside the gap that
**validates a new order block**, which gives a usable stop, then enter on the close of that candle or at
market.

**Mitigated blocks stay usable** while the drawn objective they pointed at is untaken; once the objective
is reached the block is spent, and re-taking it is the specific error he names as where people get
stopped out (`mitigated-order-block-reuse`).

**Three ways to refine inside an FVG** (`fvg-entry-refinement`), stackable and expected to agree:
(1) enter at the gap's **0.5** rather than the far edge; (2) look **left** for an order block or breaker
overlapping the gap and enter at its **opening price**; (3) drop timeframes and use a smaller imbalance
or block inside the larger gap. The stated trade-off: you miss some entries, but the smaller stop lets
the model tolerate a lower win rate. Deepest form: **nest** a 15-second gap between an already-marked
15-minute and 5-minute gap — the claimed benefit is *little to no drawdown*
(`nested-fvg-entry-refinement`).

## 4.7 Named entry playbooks

- **Manipulation → CISD → projection** (`cisd-entry-model`) — the channel's explicit assembly:
  (1) manipulation (sweep out of a range and back inside); (2) CISD in the opposite direction; (3)
  project the manipulation leg to −2/−2.5 and −4/−4.5 standard deviations, preferring levels where
  resting liquidity coincides; (4) enter at the CISD level / order block / overlapping FVG, in premium
  for shorts; (5) stop on the manipulation extreme; (6) if the first entry is missed, use the next order
  block created by the next CISD in the same direction. **Minimum 2R** — if the nearest structural target
  gives less, use the −2 deviation instead.
- **Internal / external liquidity model** (`internal-external-liquidity-model`, `irl-erl-flowchart-model`)
  — (1) HTF level; (2) drop one TF, mark internal (FVG) and external (swing high/low) liquidity, and read
  the rotation; (3) on the execution TF require **kill zone → stop raid → market structure shift → fair
  value gap**; (4) target **2R fixed**; (5) stop over the opposing candles, widened a timeframe up if
  messy. *Note the kill-zone gate — see §6.*
- **Box setup** (`box-setup`) — resting liquidity taken by an **aggressive move OUT** of a range met by
  an **aggressive move BACK IN**; mark the deviation (bodies by default, wicks on the daily) and trade
  its retest. He states this **is** power-of-three / AMD, and that the aggressive-out-aggressive-in
  requirement exists because that is what forms the wick one timeframe up.
- **T-spot inversion entry** (`ltf-inversion-entry-in-tspot`) — after the HTF closure and lower-timeframe
  alignment, wait for price into the T-spot, drop one more timeframe, and require an **inversion**: an
  opposing FVG that price then closes back through. Enter on that close or its retest.
- **Trend entries** (`trend-entry-options`) — four, for when price will not retrace far enough for a
  normal FVG/OTE entry: (1) **inducement** (stops raided beyond a swing, price returns, enter on the
  return); (2) **mitigation block** retest; (3) **cheat code** — enter at the *open of the candle after*
  the opposing candle closes, stop one point beyond it (`cheat-code-entry`); (4) drop to 15s/30s inside
  the mitigation block. Do **not** enter directly off an FVG in a trend — the stop is too wide.
  *Inducement* itself is defined as a move that induces buyers or sellers in: with **bearish** order flow
  he wants **highs** run to position short, with bullish order flow **lows** run to position long,
  preferably inside a PD array and ideally where price barely reaches into it
  (`inducement-equals-sweep`).
- **Trading without a market structure shift** (`trading-without-structure-shift`) — built to fire
  *before* an MSS, because waiting for one made him miss moves. Two requirements: a higher-timeframe POI,
  and — named as the most important — a **run of a short-term high/low followed by an aggressive move
  back into the range**. That run-and-return produces the entry object: a balanced price range, a fair
  value gap, or a box. Separate branch: a HTF POI run aggressively with **no** HTF close beyond the level
  gives an OTE / discount-or-premium entry. Both present at once is the best case.
- **Strat triggers** (`strat-two-two-reversal`) — the 1-2-2 and 2-2 reversal, taken only after a
  liquidity run and **never on their own**: "there must be a higher-timeframe reason, like almost every
  strategy". Equivalent candle form: a hammer off a low or a shooter off a high, ideally at the edge of a
  broadening formation. Earlier era — the Strat vocabulary disappears from the later material.
- **Positional entries** (`positional-entry`, `positional-entry-before-open`) — at the **open** of a
  continuation candle when a protected swing already exists from before that open, because some C3s
  expand immediately and never give an IC-CISD. **Selection test:** the protected swing used must sit
  **beyond the EQ of C2** / outside the T-spot area where the wick is expected. Pre-open (before 09:30)
  the setup must be valid on the **15-minute** and the protected swing must be one you trust.
- **Trade the lack of displacement** (`lack-of-displacement-entry`) — named as his main takeaway in that
  video, and it inverts the usual emphasis: on the buy side of the curve, lows taken *without*
  displacement are long entries; on the sell side, highs taken without displacement are shorts.
- **Consolidation sweep entry** (`consolidation-sweep-entry`) — once a leg is called a consolidation,
  mark the range and wait for the extreme opposite your direction to be swept **into a
  higher-timeframe POI**, then drop down for the reversal structure.
- **Counter-trend OTE scalp** (`counter-trend-ote-scalp`) — 15-second, explicitly needing no
  higher-timeframe narrative. After an aggressive move stalls, take a counter-trend scalp into the OTE
  of that move in order to then target the original direction. Exit at ~0.62.
- **Silver Bullet (AM)** (`silver-bullet-am-model`) — a bias-free NQ session model: at 10:00 mark the
  09:00 hourly candle's high and low; wait for one side to be swept inside **10:00–11:00**; target the
  other side; stop to break-even at 3R; no sweep or no entry by 11:00 = no trade. Backtest reported
  (`silver-bullet-am-backtest-result`): 15 trades / 45 days, avg RR ~5, +44.4% on 1% risk — and he
  discounts the sample himself. *Note Silver Bullet appears in `excluded-tooling`; this is earlier
  material.*
- **Son's model** (`sons-model`), **Unicorn** (`unicorn-model`), **the four numbered entry models plus
  BPR** (`four-entry-models`), **the 2022 mentorship setup** (`ict-2022-mentorship-model`),
  **A+ checklist** (`a-plus-entry-checklist`), **Strat triggers** (`strat-trigger-entry`),
  **turtle soup** (`turtle-soup-sweep-entry`), **market-maker sell model** (`market-maker-model`,
  `mmxm-twitter-model`), **next day model** (`next-day-model`), **inducement model** (`inducement-model`),
  **invalidation trade** (`invalidation-trade`), **HTF opening-price entry** (`htf-opening-price-entry`)
  — all carried in the library. Most are **earlier-era** and several use tools now on the exclusion list;
  see §8.

## 4.8 Order mechanics and entry location

- **Enter at market** after the trigger prints; he does not use stop orders to enter
  (`market-order-entry`). The instructional overview also describes a resting limit bracketed by an
  **OCO** stop and target (`oco-bracket-order`) **[P]** — the two are not reconciled.
- **Enter around the higher-timeframe opening price**, early in the candle. To capture the body of an
  expansion candle you must be positioned before the body is built. Entering before the counter-wick has
  formed puts you in drawdown by construction; entering after the candle has made its average range is a
  chase (`htf-opening-price-entry`).
- **Upper-half positioning** (`upper-half-positioning`): when shorting toward a target, the entry must
  sit in the **upper 50%** of the distance from the swing being traded away from to the target. Below
  that there is nothing meaningful left to risk against.
- **Do not short below lows / buy above highs** once the drawn targets are taken and the daily range is
  largely spent — there is no remaining liquidity to trade toward (`no-shorting-below-lows`).
- **Refine downward until R works** (`rr-gated-entry-refinement`): fix the target first and **never move
  it**; compute R at the current timeframe; if unsatisfying, step down (15m → 5m → 1m) and look for a
  tighter structure. A step down may yield nothing. On the lowest timeframe wait for a *confirmed*
  setup rather than the raw level. Re-anchor the displacement range after every missed entry and repeat
  until the objective is reached (`displacement-range-re-anchor-ladder`).
- **Three entry-quality criteria**, improvised and then used repeatedly as a 3/2/1/0 grade
  (`three-entry-quality-criteria`): enter *before* the targets are hit; *before* the daily range is
  created; and *around* the daily open. He states outright he has not figured out how to define these
  mechanically **[GAP]**.
- **Exclude the news wick** when fibbing a range whose extreme was a scheduled-release spike
  (`ignore-news-wick-in-range-fib`).

---

# 5. Risk, stops, targets, management

## 5.1 The stop

**The stop is the protected swing. That is the whole answer** (`stop-loss-placement`) — which is why
§3.8 is a prerequisite for this section.

One documented modification: when the protected-swing stop does not give the required R, move the stop
to the **body extreme** of the opposing-candle series (the mean-threshold logic), with the acknowledged
cost that price will sometimes sweep the wick, stop you out, and then reach the target
(`stop-loss-placement`). The alternative to widening is to **improve the entry** — take a limit at the
level or wait for a retest — rather than move the stop (`stop-loss-placement`, `stop-size-reduction`).

**[P] — "how do you reduce a stop that feels too big" gets two different answers**: move the entry
closer to the invalidation, or keep the stop at structure and change position size
(`stop-size-reduction`). Both are his; neither transcript disambiguates. He also refuses the premise —
"big" is comparative and has no content.

Related placement facts:
- A stop behind **already-swept** liquidity is safe, because that pool is gone and there is no remaining
  reason to run it. A low formed *after* the sweep is *not* protected — running it is inducement
  (`stop-behind-already-swept-liquidity`).
- On instruments that habitually sweep (he names oil) allow extra room (`stop-loss-placement`) — not
  quantified **[GAP]**.
- Where no POI exists inside the range, the stop sits beyond **0.5 of the opposing-candle series**
  (the T-spot) (`stop-loss-placement`, `trailing-stop-opposing-candles`).

## 5.2 Targets

Two things only: **liquidity and imbalances** (`target-liquidity-and-imbalances`). Prefer a level where
both coincide. Accept that imbalance targets exit earlier than liquidity targets.

Concretely, in rough order of use:
1. **Previous candles' unswept extremes** on the reference higher timeframe, starting with candle 1's;
   skip anything already taken; prefer equal highs/lows; escalate one timeframe up for the runner
   (`previous-period-high-low`).
2. **Standard-deviation projections** of the manipulation leg — settings 1, 0, −1, −2, −2.5, −4; the
   **−2 to −2.5 band** is the first target and where a retracement or reversal is expected; a
   displacement *close* through it promotes **−4** (max expansion). If the manipulation leg is large
   relative to the available range, target **−1** only. Prefer levels where a projection coincides with
   resting liquidity; where −2/−2.5 sits just *beyond* a liquidity pool, take the pool
   (`standard-deviation-projection`).
3. **Failure swings / low-resistance liquidity** (`high-vs-low-resistance-liquidity`,
   `high-resistance-target-adjustment`, `low-expectation-target-selection`).

**The ADR budget caps everything.** He uses average daily range rather than an ATR indicator, does not
compute it, and **looks at the chart** — reading the recent *expansion* days only and ignoring quiet ones
(`average-daily-range`, `average-daily-range-targeting`, `daily-range-budget`). If the band is already
covered, stop seeking continuations. A **gap open spends the budget**: measure from the session open to
the target and, if that exceeds the eyeballed ADR, pull the target in to the nearest structural level
(`gap-open-adr-budget`). No lookback, no averaging method, no statistic is ever given **[GAP]**.

**Wick size changes the target set** (§3.6): large opposing run → targets revert to the candle's
**opening price**, the fair value gap around it, and session extremes — explicitly *not* the far extreme
or the deeper deviations (`large-wick-target-adjustment`, `reversal-candle-target-adjustment`).

## 5.3 Risk-to-reward

**2R is the floor**, stated in three separate videos, and it drives both target selection and entry
refinement (`risk-reward-minimum`). Below ~2R, refine the entry downward (deeper into the FVG, to the
CE, to the mean threshold) rather than take the trade; if refinement cannot reach 2R and the target is
fixed, **skip**. In the internal/external model 2R is the *fixed target* rather than a floor.
**[P]** — 2R appears as a floor, a fixed target, and a preference across three videos, unreconciled.

Break-even arithmetic he states himself: a 2R strategy is profitable above a **34%** win rate; a 1R
target needs above 50%; 1.5R needs ~43% (`realistic-r-expectations`, `no-size-reduction-in-drawdown`).

**Reported performance** (`realistic-r-expectations`) — the only concrete figures in the corpus, and both
are self-reported, not backtests: a mentorship student's four months on gold with the 4H/15m model at a
fixed 2R = **63R over 48 trades, 63% win rate, average RR 1.93**; and, asked what the fractal model does,
"people range from 30% to 80%" with ~50% at 1:2 as his impression. Treat runs of **5–7 consecutive
losses** as within normal variance.

## 5.4 Position sizing

**Size from the account's DRAWDOWN, never its nominal size** (`position-sizing`,
`prop-firm-drawdown-sizing`): a $50k account with a $2,500 drawdown *is* a $2,500 account.

`risk_per_trade = drawdown_allowance / N`, where **N is the number of consecutive losses you are willing
to survive** and is the trader's aggressiveness dial: 10–15 conservative ($200 on $2,500), ~7 aggressive
(~$350), 1–3 for deliberately disposable accounts, 15–20 for a single irreplaceable one
(`position-sizing`). **[P]** — the two divisors he gives (10–15 and 7) are not reconciled; he presents
the choice as a personal setting.

Then: **fix the dollar risk, derive the contract count from the stop distance**, and never deviate
(`position-sizing-fixed-risk`). Worked at $100 risk: ES 4-point stop → 5 contracts; ES 2-point → 10;
NQ 15-point → 3 micros. If the stop is too tight for the full-size contract, switch to micros.

**Do not reduce size in drawdown**, and he gives the arithmetic on air: on a fixed-2R strategy, halving
risk after a loss means the next winner only returns you to break-even, whereas constant risk puts you
1R ahead; scaling by recent outcome "adds another variable to the strategy"
(`no-size-reduction-in-drawdown`).

**Prop-firm drawdown mechanics** matter because they decide whether a risk plan survives
(`prop-firm-drawdown-types`): **static**; **trailing end-of-day** (floor trails to the day's closing
balance, intraday excursions ignored); **trailing unrealised** (floor trails the highest intraday value
*including open P&L*, so an unrealised excursion permanently raises it); and **daily loss limit plus
maximum loss limit** (the daily limit stops the day, the max limit fails the account). Identical realised
P&L can pass one and fail another.

## 5.5 Trade management

**The trailing rule** (`breakeven-after-new-protected-swing`): stops can **only** be trailed to **new
protected swings**. A down-close candle that price merely moved away from is not a protected swing and is
not a valid trail target — the swing must have engaged a POI and then been closed through. Two
constraints bound it:
- Do not trail past **50% of the current higher-timeframe candle's range**, because C4 is expected to
  respect that level and a stop above it gets swept by the next candle's normal wick.
- Whether to trail at all is a function of **remaining range**: trail when the entry was early with a
  distant draw; do **not** trail when the target is ~2R at the ADR — take profit at the objective.

**Break-even is contested, split by trade type** (`break-even-management`):
- **Intraday / swing:** argued against explicitly. "My trade is not invalidated at break even" — it is
  invalidated at the intermediate-term high, and he shows the exact drawdown that would have stopped a
  break-even trader out immediately before the target.
- **Scalps:** take the first partial, then move to break-even — qualified as *what he does when
  scalping*.
- The reconciling principle he states: risk is accepted at the **structural invalidation level**, not at
  the entry price.
- Break-even is permitted when a new protected swing happens to sit at the entry price
  (`breakeven-after-new-protected-swing`).

**Partials are contested** (`partial-profit-taking`): his own behaviour in the trade reviews is partial
at ~2R, partial again at each intermediate structural level, and hold a runner with the stop trailed to
each new protected swing. An interview guest argues intraday partials steal from the future trade. Both
readings preserved. In two of his own reviews the trailed runner produced **no additional profit** over
the take-profit level — evidence against the runner leg that the videos do not treat as such.

**Trailing by opposing candles** (`trailing-stop-opposing-candles`): after each close beyond a new
opposing candle, that candle's extreme is the current invalidation. The level used is **0.5 of the
opposing candle**, and the justification he gives is directional, not risk-based — he does not expect
price back above the half of that candle. He also calls it "a little bit too tight of a trail" without
offering a replacement **[P]**. `trail-market-structure-swings` gives a second method: require **both** a
new high **and** a completed higher low before each move, on a 1- or 2-minute chart, with displacement
over the prior high required first.

**Time-based exits** (`time-based-exit`, `time-based-exit-htf-close`): hold to the close of the
higher-timeframe expansion candle the trade is running inside, because expansion candles close into their
extreme. On indices that boundary is **10:00**, where a 4-hour, 1-hour and 30-minute expansion all end
and a new 4-hour candle opens. Less commonly 09:45 (a 15-minute expansion). If a price target is reached
first, the target takes precedence **[P]** — precedence is never actually stated.

**Other management rules:**
- **One trade per day cap** (`max-one-trade-per-day`) — prescribed as a remediation, justified
  psychologically and never with expectancy data. His own stated frequency is **one to two trades a
  week**, up to three or four; daily-chart swing setups come around **6–8 times a year**
  (`trade-frequency-baseline`).
- **Intraday trades hedge the swing, they do not double it** — he declines intraday trades in the same
  direction as an open swing (`hedge-not-double-exposure`).
- **An idea is not a setup** (`idea-vs-executable-setup`) — he spends an entire stream correctly bearish
  and takes nothing, because the swing he would risk against is a pair of near-equal highs with no SMT,
  so there is no invalidation he trusts.
- **Options**: expiry = **3× the expected time to target** (`options-expiry-3x-rule`); frame on the
  futures chart, take the identical setup on the ETF at the at-the-money strike, target read off the
  futures chart (`options-proxy-execution`).

---

# 6. Timing and session gating

> ### Headline: **for gold, time-of-day buys OPPORTUNITY, not ACCURACY.**
>
> The session concept is **strongly supported for opportunity and level-marking, and
> unsupported-to-negative for entry timing**. That distinction is the whole of what this section
> establishes, and it should govern how a session gate is implemented: as a *liquidity and range filter*
> — trade when there is something to trade, and size against a known range — **not** as an edge.
>
> **Correction to RESUME finding #8.** "The hours are never stated" is too strong. `killzones` records
> **two complete grids**, and all eight windows were verified verbatim against
> `raw/transcripts/MPeeE55rNOw.txt` (`meta/session_window_fit.md`):
>
> | grid | Asia | London | New York AM | fourth window |
> |---|---|---|---|---|
> | **forex** | 20:00–00:00 | 02:00–05:00 | 07:00–10:00 | London Close 10:00–12:00 |
> | **indices** | 20:00–00:00 | 02:00–05:00 | 08:30–11:00 | New York PM 13:30–16:00 |
>
> All New York time. **Provenance, precisely:** MPeeE55rNOw is a *solo instructional video walking a
> PDF*, so the windows are in **TTrades' own voice within it** — the concept's `voice: mixed` tag comes
> from merging that unit with two guest-heavy units, not from the windows being a guest's. But this is
> **taught convention presented in a lesson, not a rule he is narrated applying to his own entries**, it
> appears in essentially one video, and the concept is `contested`.
>
> **So narrow the finding: the hours are never stated *as his own gating rule*. The windows themselves
> are taught.** What the corpus does *not* supply is any evidence they work — "volatility is higher" is
> asserted in that video and never measured.

**What the measurement says** (XAUUSD, 1,074,472 M1 bars, 2023-07 → 2026-07;
`meta/session_window_fit.md`):

- **Opportunity: strong.** The **08:00–11:59 block carries 59.8% of daily-extreme formations on 17% of
  the traded clock** — a **1.72× lift**, verified *not* to be a boundary artefact (it survives changing
  the day anchor and dropping the weekly open and close). Minute-bar range there peaks at 2.9× the day's
  trough. **08:30 is the single densest half-hour for daily-extreme formation, at 10.2%.**
- **Edge: absent, and where measurable, negative.** See §8.4(b). Gating to the corpus's own forex NY AM
  window costs −0.057R (t = −3.11, n = 7,835) — the only result of twelve to survive multiple-testing
  correction, and it is negative. The indices NY AM window points the same way. Hour 08 is the day's
  worst at −0.109R.
- **Recommended default: 10:00–12:00 NY** — the corpus's own forex *London Close* window. It is chosen
  because it is **pre-specified rather than fitted** (stated in the corpus, agreed by outside convention,
  inside the attested 08:30–12:00 quote, and containing the Silver Bullet sub-window), and it happens to
  score best (−0.004R, 1.49× range density, 1.71× extreme density on 8.7% of the clock). Its edge over
  the rest of the day is **not** significant (t = +1.46). Conservative superset: **08:30–12:00**. Sweep
  `start` 08:30–10:30 and `end` 11:00–13:00.
- The **Asian window is the one externally contested**, and it is also the one where this data finds
  nothing.

Anything in the corpus leaning on *"this must all be done within a kill zone"*
(`irl-erl-flowchart-model`) to explain why a setup **works** is unsupported here.

What the corpus *does* give:

**The stated windows** (mutually overlapping, never reconciled):

| Window | Where stated | Source |
|---|---|---|
| **09:30–10:00** — "the opening drive movement", where the clean move happens most days | His primary window | `entry-time-window`, `new-york-intraday-time-levels` |
| **08:00–10:30** (interest drops after 11:00) | Personal routine | `trading-window`, `entry-time-window` |
| **08:30–11:00** | One stream | `entry-time-window` |
| **08:00–11:00 EST** | The indicator's setup time filter | `entry-time-window` |
| **08:30–12:00** | Widest attested; the daily-profile NY a.m. window | `entry-time-window`, `daily-profile-session-windows` |
| **06:00–10:00** | The 4-hour candle he prefers to be positioned inside | `entry-time-window`, `london-reversal-ny-continuation` |
| London **02:00–05:00** | Daily-profile series | `daily-profile-session-windows`, `london-reversal-profile` |
| Silver Bullet **10:00–11:00** | Dedicated video | `silver-bullet-window`, `silver-bullet-am-model` |

**The New York AM cascade** (`ny-am-time-level-cascade`) — 08:30 and 09:30 are named as the two most
important time levels, and the pattern in every branch is *one level manipulates, the next expands*:
- London **did** set the day's extreme → continuation. 08:30 makes the opposing run ⇒ 09:30 expands. If
  08:30 fails to ⇒ 09:30 makes the opposing run and **10:00** expands.
- London **did not** → 08:30 or 09:30 sets the extreme, with expansion one slot later.
The cascade only ever shifts one slot later when a level fails to deliver its manipulation.

**The opposing run / Judas swing** (`opposing-run-entry`): at midnight, 08:30 and 09:30 look for a move
*against* the anticipated daily order flow, then a close back over the candles that made it — those
candles are now an order block, and the low they created should not be taken. If 08:30 instead moves
*with* the anticipated direction, do not chase — expect a retracement into the previous session's range
and enter there.

**The 09:30 idea and its kill condition** (`nine-thirty-expansion-invalidation`): the 09:30 open should
push price directly into the marked target. If price instead takes out the protected swing that framed
the move, **the idea is over** and the session is reclassified as chop — even though the target may still
be reached later.

**Session cascade** (`session-cascade`): a session can only expand if a prior session supplied the
manipulation. Asia quiet ⇒ London manipulates ⇒ New York expands. Session highs and lows are marked as
liquidity pools of the same kind as previous-day levels (`session-high-low`).

**Participation window, as practice rather than rule** (`new-york-am-session-only`): he trades the **New
York a.m.** session, ends walkthroughs at the afternoon because he does not trade it, and stops on
reaching the overnight session. Preceding sessions are used for **context, not participation** — Asia's
range and London's take of it feed the New York expectation. Note the unit contains its own
counter-example: one video sets up a trade specifically for a bullish PM session, so the afternoon
exclusion is not absolute.

**The pre-session routine** (`ny-morning-routine`) — a fixed, ordered checklist:
1. Daily and weekly — establish the draw; note untaken equal highs/lows and any displacement range not
   yet retraced into.
2. 4-hour and 1-hour — fair value gaps, liquidity, points of interest.
3. Economic calendar — locate the high-impact release and **mark that time on the chart**.
4. 15-minute — mark the *obvious* highs and lows; keep the external ones, clear internal range liquidity
   off the chart.
5. Mark the midnight opening price.
6. Watch the lower timeframes for the entry after 08:30.

The output is a **written expectation** — a specific sequence such as "move lower to sweep this
liquidity, then move higher" — prepared *before* the session so positions can be taken as it unfolds.
If the primary entry is missed, drop to the 5-minute, fib its displacement range and take the ~0.62.

**Asia** is normally not traded and lower timeframes are not used during it. The single stated exception:
a **daily C2 closure with a protected swing already formed before the next daily open** — then a
positional entry with the stop just beyond it (`asia-session-c2-protected-swing`).

**He rejects kill zones as the organising principle** (`entry-time-window`, `macros-not-used`): asked why
he does not care about the kill zone, he answers that he is trading higher-timeframe candles, so what
matters is being inside a HTF candle that has formed its wick — not which named block the clock is in.
**Macros are dismissed by reduction** (`macros-are-htf-opens`): a "9:50–10:10 macro" is nothing but the
10:00 opening of a new 4-hour, 1-hour and 30-minute candle, and entering mid-candle contradicts the
method's own requirement to let the new candle form its wick first. Note he still uses 09:30, 09:45 and
10:00 heavily — the rejection is of the *window around* the times, not of the times.

**News** (`fomc-nfp-cpi-only`, `economic-calendar-filter`, `news-events-ignored`, `news-not-used`):
- Later canon: the entire calendar reduces to **three releases** — FOMC, NFP, CPI. Everything else,
  including all red/orange colour-coding, is ignored. **Never trade after FOMC**; wait for the next day.
- Earlier canon, credited to AM Trades: a full three-tier filter on red-folder events — HIGH impact avoid
  the day prior, avoid the release, watch after; MEDIUM avoid the session prior, avoid the release, watch
  after; LOW no restriction. Plus skip Mondays and do not trade before the week's first high-impact event.
- **Contested within his own material:** "nothing changes for me" on release days
  (`news-events-ignored`) sits against him twice attributing his own inaction to a pending NFP, and
  against downgrading a 09:30 idea because FOMC is later in the day (`news-not-used`,
  `fomc-day-participation`).
- **NFP week protocol** (`nfp-week-protocol`): Monday no trade; Tuesday only if Monday engaged a HTF PD
  array; Mon–Thu are data for the weekly profile; Friday post-08:30 is the primary opportunity.

**Monday** (`monday-trade-rule`, `no-monday-rule`): skipped ~90–95% of the time; the only stated
exception is a **prior-Friday reversal**, which makes Monday the C3 of that sequence.

---

# 7. Psychology and process — the rules that change decisions

Only the ones that alter what gets traded are listed; the rest are in `concepts/psychology/`.

**Gates on participation:**
- **No higher-timeframe reason, no entry** (`overtrading-gate`). He estimates ~2 in 10 trades in a
  typical overtrader's journal would have one. Per day, expect at most **one A+ idea across the
  watchlist** — take it or take nothing.
- **Pattern trading is the error** (`pattern-trading-error`). "You can be right about the direction on
  something and not trade it."
- **The entry model is the least important part** (`entry-model-least-important`) — the model becomes
  *less* important the more you learn; trading is mostly managing risk. Corollary: do not switch entry
  models looking for an edge.
- **Pick ONE PD array and pair it with highs and lows** (`single-pd-array-mastery`). Selection is by
  three questions — which is easiest for *you* to see, which makes most sense, how much confirmation you
  need — and liquidity is mandatory alongside it. Do not switch after a rough patch.
- **Missed move, no chase** (`missed-move-no-chase`). Test: has the objective the trade was framed toward
  already been reached? If not, it is not too late — but return to the structure timeframe and wait for a
  new setup rather than entering late at market.

**Execution discipline:**
- **Wait for the candle to close.** The whole model is built on closures, so no decision can be made
  until the candle closes (`wait-for-candle-close`). This is his stated diagnosis for the
  backtest-to-live gap: in a backtest every candle is already closed; live, the trader acts on a forming
  candle and anticipates a closure that never happens (`wait-for-closure-discipline`). If intracandle
  watching causes forced entries, **move the execution timeframe up**. Note the IC-CISD is an explicit
  exception — "wait for the closure" means the closure of the timeframe the rule is written on.
- **Feel the emotion, do not act on it** (`feel-emotion-dont-act`). Judge the session by whether the
  impulse was acted on, not by P&L.
- **A loss is not a bad trade** — a bad trade is one that did not follow the rules
  (`loss-is-not-a-bad-trade`). Classify each trade as rule-following or rule-breaking, not by outcome.

**Diagnosis, which is where the actionable content is:**
- **Root-cause diagnosis** (`root-cause-diagnosis`): work out what your losing trades have in common and
  **stop taking that category** — the work is removing losers, not adding winners. Named symptom→fix
  pairs: stopped out then price runs to target → raise the execution timeframe one or two steps; cannot
  stop after a loss → hard cap of one trade per day; trades hit break-even then run → stop moving to
  break-even; cannot hold to target → fixed ~2R exit, no management.
- **Entry timeframe elevation** (`entry-timeframe-elevation`) — the standard answer to "my bias is right
  but I get stopped out". The fix is the timing of the entry, not the stop distance.
- **The hindsight daily-candle drill** (`hindsight-daily-bias-drill`): step the daily chart forward one
  candle at a time, mark only C2 and C3 closures, and call the next day before revealing it. Repeat until
  automatic. His stated sequence is **hindsight → forward test**; backtesting is framed as a tool for
  *learning* the model, not validating it, and he says he no longer backtests.
- **Journal every day, traded or not** (`daily-market-review-journal`). The template's load-bearing
  feature is two columns — **PREDICTIONS written the evening before, ACTUAL pasted in after** — which is
  what makes the bias accountable. Timeframes: daily, 1H, 15m, 5m per instrument. Mondays are not
  journalled because Mondays are not traded.
- **Eval vs funded** (`eval-vs-funded-mindset`): trade the evaluation exactly as you will trade the
  funded account, minus the risk, so no behavioural switch happens at funding.
- **Prescribed study path** (`ict-2022-mentorship-study-path`): ICT's 2022 mentorship start to finish, in
  order, before anything else; then the market maker series and advanced market structure.

**One disclosure that matters to anyone mining the live streams for signals:**
`hedge-driven-bias-disclosure` — his stated intraday direction is *sometimes a function of his existing
book rather than of the model*. He holds long swing exposure and buys six instruments daily on an
automated DCA, and says plainly that he therefore favours the downside intraday to hedge. He states the
motive when it applies rather than hiding it, but a scraper of his live calls will otherwise mis-read
those days.

---

# 8. Contradictions and evolution

The corpus's value is that it preserved these. They fall into four kinds.

## 8.1 Evolution — older Education-ICT playlist vs the later canon

Established pairs, from `notes/education_ict_01.md`'s 13-row table plus the concept files:

| Concept | Earlier | Later canon | Nature |
|---|---|---|---|
| `mmxm-twitter-model` | Five conditions = skip Mondays / NY only / 15m execution / calendar as roadmap / trade the day **after** the HTF level is hit | Five **different** conditions = PDH/PDL raid / hourly opposing FVG target / 15m MSS / SMT / midnight-open gate | Same name, same attribution, **two disjoint lists**. Only 15m execution shared. |
| `a-plus-entry-checklist` | The liquidity grab may be **substituted** by trading into a HTF imbalance | **Hard gate**: no LTF liquidity raid, no interest | Same condition, opposite direction of travel |
| `draw-on-liquidity` | Open search list of PD arrays, no ranking | Collapsed to a **binary**: previous day high or low | Deliberate simplification |
| `daily-bias-framework` | Five-item read (liquidity taken → structure → MSS+imbalances → premium/discount → swing sequence) | Previous-candle take-and-close test | **Entirely replaced** |
| `box-setup` | Credits "Alex"; rationale is PO3; adds an enter-early preference | No attribution; rationale is that the excursion forms the HTF wick; enter-early dropped | Rationale deepened, one rule lost |
| `broadening-formation` | "Strat + ICT part 1"; one high taking out another | Reframed as **ICT Seek & Destroy**; constant expansion; outside-bar HTF identity | Complete reframing; the Strat lineage disappears |
| `breaker-block` | Block = the **series** between H1 and L1; supplies the wick-vs-body marking rule | Block narrowed to "the lowest down-close candle prior to the move"; adds the unicorn | Later is more precise; earlier is the only source of the marking procedure |
| `economic-calendar-filter` | **Participation requirement** — skips no-news days, waits for the week's first red folder | Avoidance filter | Earlier stance is more aggressive |
| `market-structure-shift` | MSS = a swing broken with displacement. **CISD does not exist as vocabulary** — "break structure" does the job | MSS and CISD are separate signals; MSS gains a preferred stop raid and a required HTF-level engagement | This is the origin of the CISD confusion |
| `daily-open-eighteen-hundred` / `daily-ohlc-candle-shape` | **Midnight** opening price | **18:00**, "I always use 1,800" | Practice changed; both preserved |
| `premium-discount` | Orthodox — buy the discount | **Inverted for expansion phases** — during an expansion the *upper* half must hold and you do **not** expect a retracement into discount | He calls it "the opposite" himself; no rule says which framing governs when the phase is ambiguous |
| `midnight-open-directional-filter` | Classic buy day requires price below the midnight open; deep discount = below both midnight and 08:30 opens | Midnight open listed among tools he no longer uses | Superseded |
| `optimal-trade-entry` / `strat-trigger-entry` / `killzones` / `breaker-block` | Taught in full | Listed in `excluded-tooling` / `ttfm-minimal-toolkit` | Tools retired |
| `top-down-analysis-procedure` | Ladder is a **function of the entry timeframe**; 15-second charts routinely used | Ladder fixed at Daily → Hourly → 5-minute | Simplified |
| `intraday-bias-three-inputs` | Bias from displacement + structure + imbalances (a closed list) | Previous 4-hour candle's high and low as a continuous draw engine | Mechanism entirely replaced |
| `next-day-model` naming | The video titled "Next Day Model" **is** the Twitter model | The video titled "Next Day Model — Fractal Way To Get Bias" is the previous-candle framework | **The title was reused for a different model** — matching on titles will mis-merge these |

## 8.2 Contested within the same era — these are real parameters

- **The C3 closure reference** — C2's body/open vs C2's extreme (§3.3). Compute both.
- **Which price of the opposing series a CISD must clear** — first candle's open vs highest open (§4.2).
  Measured Jaccard 0.56–0.59 against the extreme reading; the extreme is ruled out.
- **CISD series length** — the dedicated model video accepts a single candle when the structure has only
  one; a Sunday-session answer says he never selects one candle and always uses a series (`cisd`).
- **"EQ" names three different levels** (§3.7), and the dedicated EQ video rules bodies **out** for EQ
  while other passages measure "the upper half of this from body to body" (`equilibrium-eq`,
  `half-wick-respect`).
- **Wick-size comparison basis** — against the candle's **body** in one unit, against its **range and
  time** in the dedicated long-form video (`small-wick-expansion-rule`, `wick-size-test`).
- **Consolidation direction** — the library holds that the manipulated side is chosen **by bias**
  (bullish requires the low to be run); a Short reads the direction **off whichever side is taken
  first**, with no prior bias needed. Both are his voice, unreconciled (`consolidation-phase`).
- **Retracement speed** — one Short says a retracement is **slow** (consuming more time than the
  expansion it retraces); another says it must be **quick**, and slowness is what reclassifies it as
  consolidation. No bar count separates them (`retracement-phase`).
- **Break-even** — argued against outright in the CPI review, practised in the 15-second scalp; the only
  discriminator offered is "scalping", with no timeframe or R threshold (`break-even-management`), and
  `root-cause-diagnosis` says flatly "stop going to break-even", which contradicts the
  move-only-after-a-new-protected-swing rule.
- **Point of interest for continuations** — mandatory in the polished lessons, **waived for
  continuations** in his stated real rule; he acknowledges the conflict himself (`point-of-interest`).
- **Failure swing** has two incompatible definitions in the corpus: by **proximity** (stacked extremes
  too close together to trade away from) and by **not having swept** prior liquidity. The two can
  disagree on the same bar (`failure-swing`).
- **Market entry vs OCO limit** (`market-order-entry` vs `oco-bracket-order`).
- **Position-sizing divisor** — 10–15 vs 7 (`position-sizing`).
- **2R** as floor / fixed target / preference (`risk-reward-minimum`).
- **Relative strength: "default to ES" vs "never trade the middle asset"** — advice for beginners against
  his own practice, in the same unit (`relative-strength-weakness`,
  `relative-strength-asset-selection`).
- **YM** — central to the index triad in one stream; "I never watch YM, it is very uncorrelated" in
  another (`relative-strength-asset-selection`).
- **SMT is confluence only** vs **SMT is what supplies the trustworthy invalidation without which he will
  not trade** (`smt-requires-framework` vs `idea-vs-executable-setup`, `smt-invalidation-level`).
- **News** (§6) — "nothing changes for me" against observed deferral and an explicit FOMC downgrade.
- **Phases mapping** — one unit maps *close back inside the range* to **retracement**; another maps
  *failing to close over the opposing series and falling back inside* to **consolidation**. These must be
  reconciled before a phase detector is written (`phases-of-price`).

## 8.3 Contested against mainstream ICT — deliberate positions, not errors

> ### ⚠ INTEROPERABILITY LANDMINE — his "breaker block" is not everyone else's.
>
> **His construction** (`breaker-block`) is a **pure four-point geometric sequence**: bearish =
> high → low → higher high → **lower low**; the zone is the down-close candles spanning the *first*
> high to the *first* low; incomplete until the fourth point prints; requires a higher-timeframe bias.
> It never mentions an order block at all.
>
> **The mainstream definition** is a **failed order block** — an order block price traded through, which
> then flips polarity — and the majority formulation additionally requires a **liquidity sweep plus a
> market structure shift** before it is valid. The standard discriminator against a *mitigation block*
> is stated crisply outside: mitigation block = the same failure **without** the preceding sweep
> (`meta/external_crossref.md` §6b).
>
> These are **different objects**. They coincide on a chart often and not always. Anyone wiring this
> spec to an external chart, indicator, dataset or labelled sample will silently get a different thing.
> **State which definition is in force in every comparison.** Related: his order block is traded at the
> block's **opening price**, where the mainstream uses the whole candle range as a zone or its 50% mean
> threshold — the same signature tightening, and the same interoperability hazard (`order-block`,
> `meta/external_crossref.md` §6a).
>
> A second, sharper collision: third-party descriptions of the *TTrades Fractal Model indicator* use
> **C1/C2/C3/C4 to mean "how many HTF candles have elapsed since the setup triggered"** — a setup-age
> counter — in addition to the closure semantics. The corpus uses C1 = the candle before the sweep,
> C2 = the sweep candle, C3 = the continuation. Two different indexings that can coincide by accident.
> **Assert the indexing before comparing against any indicator output** (`meta/external_crossref.md` §2).

- **CISD ≠ market structure shift** (`cisd`, `market-structure-shift`). ICT's rule that a CISD need not
  close beyond the opening price is raised by a viewer and **explicitly declined**. Externally confirmed
  — see §4.2.
- **Macros are fake** — reduced to higher-timeframe candle opens (`macros-not-used`,
  `macros-are-htf-opens`).
- **Kill zones are not used** — replaced by "which HTF candle am I inside, and has it formed its wick"
  (`entry-time-window`, `excluded-tooling`).
- **Premium/discount inverted for expansions** (`premium-discount`).
- **Intermarket correlation is not used** — DXY-vs-gold and DXY-vs-indices are dropped on an empirical
  claim that the correlation broke down (`intermarket-correlation-not-used`).
- **CRT is "a copy of my fractal model"** (`excluded-tooling`).

## 8.4 Where the method collides with the data

These are not two videos disagreeing. They are **his own rule, measured, and found to cost something**.
Both were produced offline on 1,074,472 XAUUSD M1 bars, 2023-07 → 2026-07, and both are
instrument-specific until recomputed elsewhere.

**(a) "Reaching OTE means reversal" discards about half of all genuine continuations.**
`shallow-retracement` records the rule that a retracement reaching the OTE of the impulse leg
invalidates the expansion read and is treated as a V-shape reversal. Measured, the **median continuation
retracement on XAUUSD is 0.62–0.65 — which is exactly the OTE lower bound** (`meta/threshold_fits.md`
§3). So the rule as taught rejects the median continuation. It may still be right as a *risk* filter — a
shallower entry is a better entry — but it must not be sold as "identifying continuations", and anyone
backtesting `expansion-signature`, `continuation-signature`, `shallow-retracement` or `v-shape-reversal`
should sweep this parameter first, because it has the largest gap between stated doctrine and base rate
of anything in the corpus. A default of **0.50** sits at p28–p38 of continuation legs and is genuinely
selective, unlike the 0.5-of-range wick cut.

**(b) The New York AM kill zone buys opportunity and costs accuracy — which is his own teaching,
expressed as a number.** See §6 for the full statement. In short: 08:30 NY is the **densest half-hour for
daily-extreme formation (10.2%)** and is simultaneously inside the day's **worst expectancy hour
(−0.109R)**. Gating entries to the corpus's own forex NY AM window (07:00–10:00) returns **−0.057R
against the rest of the day, t = −3.11 on 7,835 events** — the only one of twelve tested windows to
survive multiple-testing correction, and it is negative (`meta/session_window_fit.md`). This does not
refute the session concept; it **vindicates the mechanism and indicts the rule built on it**. *"The best
half-hour to have a level is not the best half-hour to take an entry"* is precisely his own
manipulation-then-distribution claim (`power-of-three-amd`, `opposing-run-entry`, `session-cascade`) —
the number just says the manipulation half is where the clock density lives.

**(c) The FVG displacement proxy is weaker than it reads.** A same-direction fair value gap appears in
**61–77%** of break windows, so "no FVG ⇒ no displacement" rejects only about a third of breaks
(`displacement`, `meta/threshold_fits.md`). Advisory, not gating.

## 8.5 Terms he uses that he also disowns

`phases-of-price` records him disowning "run" and "sweep" as terms he uses, in the same corpus where he
narrates setups as "the sweep and the closure back in" and ships an indicator with a "C1 sweep" setting.
Both readings are recorded.

---

# 9. The ceiling — what cannot be rebuilt, and why

This section exists because the honest answer to "can this be reimplemented faithfully?" is **no, not
completely** — and the reason is not a gap in the corpus. It is that the load-bearing definitions are
deliberately not published.

## 9.1 Paywalled at source

> **"I go over all the requirements for these within my course and mentorship."**
> — on the indicator's actual C2/C3/C4 conditions (`ttfm-indicator-settings`, `fractal-model-c2`)

The indicator is the arbiter throughout the corpus. Live calls, the C2 colour semantics (grey = the setup
stayed valid through candle 4; red = failed on the first candle after; orange = failed on the second),
the "automatic" fractal pairing, the T-spot box, the projections, the formation-liquidity line, the
autobias filter — these are read *off the tool* on screen, not constructed on air
(`ttfm-indicator-settings`, `autobias-filter`, `t-spot`, `indicator-print-conditions`, `cisd`,
`protected-swing`).

So the free material gives you the *shape* of the model and the tool gives you the *thresholds*, and the
thresholds are sold. **A faithful reimplementation is blocked at source.** Any detector built from this
corpus is a reconstruction whose parameters were fitted, not recovered — and it should be labelled as
such.

## 9.2 Withheld on purpose — confirmed on stream

He states outright that he has more advanced material he deliberately does not publish
(`ttfm-minimal-toolkit`). Specifically:

| Withheld | Evidence |
|---|---|
| **Anticipation CISD** | Named as unpublished; the "early CISD" setting is the only public trace (`ttfm-minimal-toolkit`, `early-cisd`) |
| **The inside-bar procedure** | He says he has a mechanical procedure for trading an inside day and will not publish it (`inside-day-three-levels`, `ttfm-minimal-toolkit`) |
| **C3-consolidation handling** | Named as unpublished (`ttfm-minimal-toolkit`) |
| **The T-spot's derivation** | Asked how the indicator prints it, he says only that it is what he coded; "I'm not explaining where the T-spot is derived from" (`t-spot`) |
| **Trailing stops and pyramiding** | "It would help a few people but hurt the masses" (`break-even-management`) |
| **The far-away-CISD alternative entry** | Described as advanced material he has not made a video on (`cisd`) |
| **The mechanical reversal-low definition** | "We can mechanically define with GXT" — and then does not (`aligning-expansion-candles`) |
| **The higher-timeframe-reason flowchart** | Exists only in the paid course (`overtrading-gate`) |
| **The reversal-day framework** (the alternative when there is no daily C2) | Named, never specified (`daily-bias-c2-c3-h1-cisd`) |

## 9.3 Not withheld — genuinely absent

These are settled negatives. More reading will not produce them — and the external check confirms they
are real absences rather than gaps in our reading: no public ICT/SMC source states a wick-size or
displacement threshold either (`meta/external_crossref.md`).

1. **The wick-size *operating point*.** Checked across 443 videos including a video titled for it: **no
   wick-to-body ratio is ever spoken** (`wick-size-test`, `small-wick-expansion-rule`). What *is* given —
   and RESUME finding #5 understates this — is a **ceiling**: 0.5, named as equilibrium / the upper half
   / 50% of the wick, with one video calling it a mechanical way to measure wick size outright. But 0.5
   of range admits ~85% of XAUUSD candles, so it marks where a candle is *definitively* a reversal
   candle and does not filter (§3.6). The one corpus-attested *classification* cut is wick-vs-body at
   1.0. Everything between the two is unstated. **This is the gate the entire model turns on** — C2
   tradeability, C3 quality, target selection, timeframe alignment and the reversal-vs-expansion
   classification all read from it.
2. **"Displacement" / "aggressive".** The single highest-leverage undefined term, because it gates the
   market structure shift, order-block validation, manipulation confirmation, phase classification and
   bias flips *simultaneously* (`displacement`). Only two procedures exist and both are **relative**: the
   comparative four-candle test, and the close-beyond-level proxy, under which a one-tick close qualifies.
   Worth noting: on displacement the corpus is actually **more specified than the public literature** —
   the comparative four-candle procedure has no external counterpart. The absence is the tradition's,
   not this channel's.
3. **Kill-zone hours *as his own gating rule*.** Narrowed, not absent: two complete grids **are** taught
   and verbatim-verified, but as convention in one instructional video rather than a rule he is narrated
   applying — and no evidence is offered that they work. §6. 68 concepts blocked.
4. **"Relevant" / "relevant swing separation".** He states directly that there is no mechanical rule and
   that it comes from experience (`relevant-swings-separation`). This is his own admission in the primary
   teaching video, so there is nothing to recover.
5. **"Consolidation"** is circular for automation: consolidation is the absence of displacement, and
   displacement is never quantified (`consolidation`). The one crisp test — *does it form a protected
   swing?* — is real and usable (`consolidation-vs-retracement-test`).
6. **Average daily range.** He is asked directly how to calculate it and the question is not answered;
   the figures are eyeballed (`average-daily-range-targeting`, `average-daily-range`).
7. **"Strong closure"**, the gate for taking C4 (`fractal-model-c4`) — the *quantity* is now settled (it
   grades where in its own range the candle closed, **not** the wick; §3.4), the value is not.
8. **"Shallow"**, the depth bound on a retracement inside an expansion (`expansion-signature`,
   `shallow-retracement`).
9. **The swing filter.** A literal 3-bar fractal produces far more swings than he marks, and no
   separation, range or lookback filter is given (`swing-point`).
10. **The intracandle-path problem.** Both the OHLC/OLHC shape rule and the reversal-candle test are
    statements about the **order** in which the extremes formed, which is not recoverable from closed-candle
    OHLC without lower-timeframe data (`daily-ohlc-candle-shape`, `reversal-candle-quality`).

## 9.4 The honest prior

Before treating any of this as a blueprint: **there is no peer-reviewed literature on ICT or SMC at
all** — targeted academic search returns zero papers testing these constructs by name
(`meta/external_crossref.md` §7). The best-documented public mechanical ICT bot **lost 45% over a year**
on EURUSD 15m: 125 trades, 29.6% win rate, profit factor 0.81, max drawdown $5,121 on a $10k account —
with its thresholds **frozen before the run**, and costs excluded. That is the correct methodology and it
still lost. Freezing thresholds is also the trap this project sits closest to: fitting the wick threshold
to *his narrated labels* would be a legitimate supervised reconstruction of what he teaches; fitting it
to *P&L* is not. **Fit on the label task, freeze, and only then backtest.** The two must never merge.

And the label task turned out not to be available: **56 narrated calls were curated (down from 1,926
regex candidates, because the auto-labeller agreed with hand review on only 17 of 31 directional calls),
and none of the 56 could be tied to a dated bar** — a transcript names no instrument, no date and no
price while he points at a screen that is not in the corpus (`meta/qualifier_calls.md`,
`meta/threshold_fits.md`). So the supervised fit does not exist and nothing here claims it. What the
mining *did* deliver is the thing that was actually missing: **which quantity to measure**, on which
denominator, with the numerator pinned by his own words. Every threshold past that is a
distribution-anchored default and must be swept.

## 9.5 What this means for a build

- **The model is a shape, not a system, until you fit it.** Treat the corpus as a *specification of
  structure* and the missing numbers as free parameters. The corpus pins **which quantity** each
  adjective measures; it does not pin the value, and — see §9.4 — a supervised fit against his narrated
  calls is not achievable because none can be tied to a dated bar. So: take the graded defaults, sweep
  them, and validate out-of-sample.
- **Sweep the load-bearing knobs first**, in this order: the retracement-depth cut (§8.4a, the largest
  gap between doctrine and base rate), the displacement magnitude pair, the wick operating point, and the
  session window. Everything else is downstream of those four.
- **Never quote a result for "CISD" or "C3" without stating the reading.** They are different systems
  wearing one name (`meta/cisd_reading_comparison.md`, `meta/fractal_reading_comparison.md`).
- **Base rates are brutal.** ~40–44% of candles sweep the prior candle's range on every timeframe, so
  "price swept liquidity" is near a coin flip on its own (`meta/primitive_base_rates.md`). Frequency
  proves nothing.
- **The one falsifiable, non-definitional prediction in the whole corpus is the C2 wick asymmetry**:
  small-wick C2s are followed by delivery beyond the C2 open 78–83% of the time vs 63–66% for large-wick,
  stable across 1h/4h/1D over three years (`meta/fractal_reading_comparison.md`). It survives testing and
  is the best backtest candidate — but note it is measured at the *median* wick split, which is arbitrary,
  and it is a raw directional-delivery rate with no target, stop, spread or slippage modelled.
- **A reimplementation will not reproduce his live calls**, and should not claim to. He reads levels off
  a tool whose rules are sold, applies discretionary filters he describes as "discernment", and discloses
  that some of his live directional calls are hedge-motivated rather than model-derived
  (`hedge-driven-bias-disclosure`).

---

*Generated from `concepts/**/*.yaml` via `python/build_method_spec.py`. Every id in backticks resolves to
a file; every file resolves to a video id and a verbatim quote of 15 words or fewer, provenance-checked
by `python/validate_concepts.py`. Guest material is excluded — see `guest_methods_appendix.md`.*
