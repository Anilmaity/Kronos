# Guest methods — a comparative appendix

## What this is, and what it is not

**177 of the library's 505 concepts have `voice: guest`.** They do not belong in
`ttrades_method_spec.md` and they must not be merged into it.

The T Talks and Live Stream Guests playlists are **interviews**. Each episode is a different trader
describing his own method, on his own terms, on the host's channel. A `guest` concept is evidence of
**what that guest teaches** — nothing more. Several guests contradict the channel's own method
outright; several contradict each other; two of them do not trade ICT at all.

This appendix is therefore a **comparative library**, organised by speaker. Use it to see what the
neighbouring methods look like, to find ideas worth testing on their own merits, and — most usefully —
to see which of the channel's own positions are idiosyncratic and which are shared across the wider
community. Do not use it as a source for the channel's method. Filter to `voice in (ttrades, mixed)`
for that.

Two mechanical notes:

- Attribution is by **video**, because that is what the library records. Some ids appear under several
  speakers where two guests independently state the same thing — the concept file preserves both.
- `merge_concepts.py` respects a draft's *declared* voice and only falls back to the playlist
  heuristic when none is declared. That matters: the heuristic cannot see *who is speaking inside* a
  video, and it was silently re-tagging **TTrades' own rules stated inside guest interviews** as
  `guest` — six real cases, including his own position sizing and stop rules. Those are now in the
  main spec where they belong. If you re-study a guest unit, declare the voice.

---

## 1. Where guests directly contradict the channel

These are the ones that matter most, because they mark the boundary of what is actually *his*.

| # | Guest position | The channel's position | Concept |
|---|---|---|---|
| 1 | **A candle 2 closure is not required.** If C2 reaches a key level but does not visibly reverse on the HTF close, accept either a lower-timeframe reversal inside C2, or C3 confirming with a CISD. If C1 hits the level and closes as an expansion candle, revert to C1's low as the reversal reference. Restricted to daily and 4-hour. — *GxTradez* | The C2 closure is the foundation: sweep the previous extreme **and** close back inside, or it is not a C2 (`fractal-model-c2`) | `candle-two-closure-not-required` |
| 2 | **No daily bias at all** — enter purely from points of interest. — *Ash Trades*, and *DTR* builds a whole model (`c2-unicorn`) explicitly to need no daily bias | Step 1 of the published playbook is a hard stop-gate: no bias, do not go down to the hourly (`ttfm-hourly-5m-playbook`, `overtrading-gate`) | `daily-bias-requirement` |
| 3 | **Mechanical management only** — entry, stop and target set at entry and **never** adjusted; break-even moves, trailing and partials all refused. — *Ash Trades*, *AP* | He trails to each new protected swing, takes partials, and moves to break-even when scalping (`breakeven-after-new-protected-swing`, `partial-profit-taking`) | `mechanical-trade-management` |
| 4 | **Never touch the stop before the first target is hit** — even if structure shifts against you. — *AM Trades*, stated in the same stream where the host describes trailing along market structure on a 1–2 minute chart | `trail-market-structure-swings` | `no-stop-change-before-first-target` |
| 5 | **Risk is scaled by the last outcome** — base 1%, ±0.5% per outcome, capped at 2%, floored at 0.25%. — *Trader Kane* | He gives the arithmetic *against* this: scaling by recent outcome "adds another variable to the strategy" (`no-size-reduction-in-drawdown`) | `dynamic-risk-scaling-matrix` |
| 6 | **Market structure "break" ≠ "shift"** — a *shift* is the ordinary intraday case; a *break* is reserved for the taking of an intermediate-term swing point. — *AM Trades* | The host disagrees **on air in the same stream**, saying the terms are interchangeable (`market-structure-shift`) | `market-structure-break-significance` |
| 7 | **The 15-minute is the floor for narrative**; hourly-to-daily is the sweet spot. — *AM Trades* | He routinely builds narrative on the 4-hour and the daily, and executes down to 15 seconds in the earlier material (`poi-timeframe-selection`) | `htf-narrative-floor-fifteen-minute` |
| 8 | **Silver Bullet requires trading through a breaker — no time window of any kind.** — *DayTradingRauf* | His Silver Bullet is defined *by* its window, 10:00–11:00 (`silver-bullet-window`) | `silver-bullet-breaker-requirement` |
| 9 | **Order blocks are out; breakers and balanced price ranges are in.** — *Ben* | Order blocks / opposing candles are the core entry object (`order-block`, `opposing-candle`) | `single-pd-array-mastery` (mixed), `balanced-price-range-revisit` |
| 10 | **An order block must be the candle that produced a break of structure.** — *AP* | His validation is a close back through the block at an important level; no BOS required (`order-block`) | `order-block-requires-bos` |
| 11 | **Do not journal winners** — log losses only. — *Trader T* | He journals every day whether or not a trade was taken, with predictions written the night before (`daily-market-review-journal`) | `journal-losers-only` |
| 12 | **The 09:30 Judas swing works *better* on days with no news** — so a no-news day is the day to trade, not to sit out. — *DayTradingRauf* | He treats no-news days as low-interest and skips them in the earlier calendar material (`economic-calendar-filter`) | `no-news-judas-swing` |
| 13 | **Never trade at the *beginning* of a kill zone** — the start of the window does the opposite of what the session will do. — *DayTradingRauf* | His primary window *is* the first thirty minutes of the New York open, 09:30–10:00 (`entry-time-window`) | `killzone-open-avoidance` |
| 14 | **Bias must be dynamic** — mark the liquidity, let price choose, allow the bias to change intraday. — *Alex's Options* | "Come in and keep that bias"; a failed continuation signature is not grounds to switch (`structure-requires-htf-context`, `daily-profile-confirmation`) | `dynamic-daily-bias` |
| 15 | **Timeframe continuity above the monthly** — quarterly, six-month, yearly; "most ICT traders stop at the monthly and should not". — *Alex's Options* | The weekly chart is skipped entirely, and for intraday he says he does not care about anything above the daily (`weekly-chart-not-used`, `timeframe-pairing`) | `strat-timeframe-continuity` |

**And two guests who are not trading this method at all:**

- *STRATalorian* states plainly that he does not primarily trade ICT, and names three systems he does:
  John Carter's TTM squeeze, a **+3 ATR reversion to the 21 EMA**, and TheSTRAT
  (`mean-reversion-3atr-21ema`). The channel's toolkit excludes moving averages
  (`ttfm-minimal-toolkit`).
- *Alex's Options* left ICT for TheSTRAT and says why: objectivity at scale. ICT works when focused on
  one or two instruments; he runs scans and may hold seven or eight positions in a day. He stopped
  using order blocks specifically because they can be run through, and says combining STRAT and ICT
  confused him (`strat-vs-ict-objectivity-tradeoff`).

---

## 2. Where guests contradict *each other*

The library records four of these as `contested` at the concept level, which is exactly right — they
are corpus-level conflicts, not one speaker being inconsistent.

- **Is a daily bias required?** (`daily-bias-requirement`) Two speakers build bias first and treat it as
  the model's foundation; one refuses to use one at all; a fourth replaces it with a
  calendar-and-profile day-selection layer. Four positions, one concept file.
- **Trade management** (`mechanical-trade-management`) — doctrinal disagreement across three speakers,
  and **none of them cites data**.
- **Partials** (`partial-profit-taking`, mixed) — one guest: intraday partials steal from the future
  trade, and taking them means you either had a draw and should have held or had no trade. Another
  (`t1-t2-partial-system`, `mmxm-phase-sequence`): partial at T1, break-even, run the rest.
- **When you may execute** (`opening-time-only-execution`) — every speaker who states one restricts
  execution to a session open or the session immediately after, and **they disagree on which**: Ash
  permits London 02:00, $niper forbids anything before 09:30, AM forbids the PM session but never gives
  the AM session's end.
- **Risk and frequency caps** (`risk-limits-and-trade-frequency`) — two guests independently give the
  same hard cap (two losses and stop), but one applies it to live trading only and explicitly not to
  backtesting.
- **News tiering** (`news-impact-tiering`) — the same guest gives a three-tier framing in one video and
  a red-folder-only binary in another.
- **SMT** (`smt-divergence-confluence`) — both guests demote SMT to confirmation and both warn against
  hunting it on the 1- and 5-minute all day; one demonstrates it on the *weekly*. That agrees with the
  channel (`smt-requires-framework`), so it is a case where the guests corroborate rather than conflict.
- **Trade frequency** (`trade-frequency-under-two-per-day` vs `less-trades-more-capital`) — AM Trades
  reports ~8 trades a week; two futures-side guests budget **0–3 per week and end the week after two
  winners**. The channel's own baseline is 1–2 a week (`trade-frequency-baseline`). Roughly a fourfold
  spread across speakers who all describe themselves as selective.

---

## 3. By speaker

Ordered by concept count. Video ids are the library's `sources` keys.

### GxTradez — `J_EeS2_2CAM`, `3eVxTV_7L2U` (11)
Phases of price and profiles for expansion; a complete SMT/PSP framework.
`candle-two-closure-not-required` · `driver-pairing-rule` · `fake-smt-strength-switch` ·
`four-hour-session-if-then-chain` · `small-wick-supports-expansion` · `trade-away-from-manipulation` ·
`continuation-psp` · `correlated-triads` · `smt-break-reversal-trigger` · `two-stage-smt` ·
`universal-models`

The most *mechanically useful* guest for anyone building from the channel's own model, because he
mechanises pieces the channel leaves loose: an explicit **4-hour if-then chain** (if the 02:00 candle
manipulates, expect 06:00 continuation; if 06:00 manipulates, expect 10:00; etc.), a **driver pairing
rule** (a reversal before the driver ⇒ the driver expands away from it; no reversal before it ⇒ the
driver *is* the reversal; a driver that reaches a key level and fails to reverse invalidates the daily
profile), and **correlated triads** enumerated outright: DXY/EURUSD/GBPUSD, NQ/ES/YM, GC/XAU-EUR/XAU-GBP,
CL/RB/HO, with RTY paired to YM specifically. His `continuation-psp` correction is worth carrying: a PSP
printing *against* an open draw is a continuation signal, not a reversal — he says he was repeatedly
stopped out trading these as reversals. He also relaxes the C2 requirement (§1).

### Alex's Options — `V8P6lNIisvc`, `1XWyy6Q-_8Q` (26)
TheSTRAT, broadening formations, 0DTE options.
`strat-candle-taxonomy` · `strat-inside-bar` · `strat-outside-bar` · `strat-actionable-signals` ·
`strat-timeframe-continuity` · `strat-pivot-targets` · `strat-scalping-hour-two-filter` ·
`timeframe-continuity` · `timeframe-decoupling` · `new-period-open-new-participants` ·
`pivot-machine-gun` · `no-trade-into-blue-sky` · `no-reversal-means-still-going` ·
`stuck-inside-no-trade` · `gap-direction-fade-rule` · `add-to-winners-timeframe-cascade` ·
`dynamic-daily-bias` · `secondary-consolidation-breakout` · `target-consolidation-lows-not-fvgs` ·
`oversized-fvg-handling` · `fifteen-second-execution-timeframe` · `t1-t2-partial-system` ·
`zero-dte-strike-selection` · `prop-cushion-scaling` · `volume-spike-at-extremes` ·
`strat-vs-ict-objectivity-tradeoff`

The most complete *alternative* system in the corpus. Its core claim is that there are exactly three
candle types relative to the previous candle — 1 (inside bar, consolidation), 2 (takes one side,
directional), 3 (outside bar, "a 2 that failed") — so the set of reversal and continuation sequences is
**finite and enumerable**: 2-1-2, 2-2, 3-2-2, 3-1-2, 1-2-2 for reversals; 2-2 and 2-1-2 for
continuations. Note the channel's own `three-candle-outcomes` credits this same framing to the Strat.

Two of his ideas are genuinely orthogonal to anything in the channel's method and are worth testing on
their own: **timeframe decoupling** (at the session open every timeframe shares one opening price, so no
lower-timeframe participant group has expressed anything yet — lower-TF signals only become meaningful
once each has closed and reopened at a different price), and **new-period-open participants** (~70% of
volume is algorithmic; an algorithm must be told *when*, and that "when" is anchored to period opens, so
every new open introduces a fresh participant group). His management doctrine is the exact inverse of the
channel's: exit on a **reversal signal appearing against you**, not on a target — absence of an opposing
signal is itself the reason to stay in (`no-reversal-means-still-going`).

### AM Trades — `QmGJFxfSHxM`, `wGYde-h84cs`, `CrUfTskOveo` (27)
Economic calendar → daily chart → weekly profiles, and market maker models.
`news-impact-tiering` · `pre-event-avoidance-rule` · `fomc-week-protocol` ·
`consolidation-reversal-week` · `weekly-profile-alignment` · `weekly-profile-not-predicted-in-advance` ·
`daily-phases-of-price-delivery` · `consolidation-external-liquidity-only` · `large-range-day-targeting` ·
`hourly-cisd-manipulation-confirmation` · `context-over-pd-array-mechanics` · `daily-bias-requirement` ·
`smt-divergence-confluence` · `opening-time-only-execution` · `max-expansion-deviation-no-trade` ·
`nq-over-es-volatility-preference` · `futures-over-stocks-gap-continuity` ·
`no-stop-change-before-first-target` · `trade-frequency-under-two-per-day` ·
`market-structure-break-significance` · `htf-narrative-floor-fifteen-minute` ·
`backtest-annotation-method` · `mmxm-phase-sequence` · `mmxm-second-leg-entry` ·
`bitcoin-session-time-not-used` · `no-monday-rule` *(also stated by the host)* · `nfp-week-protocol`

The calendar-first method. Order of operations is inverted relative to the channel: **find the week's
first high-impact driver first**, because accumulation and liquidity engineering happen before it,
manipulation at or just prior to it, and expansion after. Red-folder only, filtered to the traded
currency, concentrating on 08:30 releases with FOMC at 14:30 as the exception. Days before high-impact
events are avoided; nothing is held through a release. His **three-step CISD confirmation** is more
specified than the channel's: (1) price engaging a HTF PD array, (2) that engagement paired with the day
the weekly profile calls for — *time and price together*, (3) an hourly close below the last up-close
candle that engaged the array.

One rule of his is a clean, testable addition: **no expansion immediately follows an expansion** — an
intermediate phase must occur first (`daily-phases-of-price-delivery`). The channel's own
`phases-of-price` does not state this, and explicitly leaves it unaddressed.

Also `max-expansion-deviation-no-trade`: once the 4/4.5 deviation is reached the weekly range is spent
and he takes no further trades in that direction that week — a hard stop the channel's version of
standard-deviation projection lacks.

### Jokerszn — `JABOO4LYNjQ` (14)
Daily order flow as a bias engine.
`daily-orderflow-confirms-draw` · `daily-close-only-bias` · `daily-close-inversion` ·
`three-daily-profiles` · `consolidation-profile-conditions` · `monday-range-marker` ·
`three-consecutive-closes-rule` · `range-eq-no-trade` · `pd-array-mean-threshold-test` ·
`daily-wick-as-balanced-price-range` · `killzone-execution-sequence` · `stuck-orderflow` ·
`no-draw-no-trade` · `valuation-by-speculation`

The most rule-dense guest, and several of his rules are directly falsifiable. Bias comes from exactly
two inputs: a liquidity objective drawn only from old highs/lows and HTF fair value gaps, plus **daily
order flow confirming that draw** — where order flow is defined by reaction to PD arrays (bullish order
flow = bullish arrays respected while bearish arrays to the left are disrespected and inverted). Once the
objective is reached, bias returns to **neutral** until price shows intention again.

Distinctive and testable: **only daily opens and closes define narrative** — wicks have one function,
taking liquidity, and never determine direction, so a level is disrespected only on a daily *body* close
(`daily-close-only-bias`). **A large daily wick IS a balanced price range** in its own right, marked low
to high, reaction expected from the lower half, EQ used as the stop reference because it survives a news
spike (`daily-wick-as-balanced-price-range`). **Never trade the EQ of a range** — the lowest-probability
location in price, because that is exactly where discount becomes premium (`range-eq-no-trade`). And a
frequency rule derived from observation: after **three consecutive same-direction daily closes**, take no
trades in that direction on the fourth day (`three-consecutive-closes-rule`) — compare the channel's soft
"three days of expansion" cue (`dont-trade-after-expansion`).

### DTR — `07lOxv39LdY` (13)
The C2 Unicorn — an explicit hybrid of the channel's fractal model and the unicorn model.
`c2-unicorn` · `fractal-c2-unicorn-pairing` · `unicorn-candle-count-filter` · `swing-point-above-fvg` ·
`three-pd-array-confluence` · `daily-tspot-open-poi` · `adr-remaining-filter` ·
`low-hanging-fruit-target` · `timeframe-alignment-ladder` · `mechanical-trade-management` ·
`opening-time-only-execution` · `seven-hour-candle-daily-profile` · `daily-bias-requirement`

Directly relevant to anyone building from the main spec, because it is a *modification* of it: an hourly
swing point forms at a POI, drop to the 5-minute, look for a **unicorn inside the wick of that swing
point** — and a unicorn forming inside C2 is accepted as confirmation that C2 will be a valid closure, so
the trade is taken **inside C2** rather than waiting for the C2 close and trading C3. That is a
deliberate inversion of `continuation-over-reversal`. He also supplies the one **candle-count filter** in
the whole corpus for formation speed: the breaker-plus-FVG should complete within **roughly 10–12
candles, ideally fewer** (`unicorn-candle-count-filter`) — the closest thing anywhere to a quantitative
"aggressive" test, and it is a guest's.

### $niper — `UmLWRlXd_V8`, `5aRB_ZY3474` (12)
Market maker models, internal/external liquidity.
`mmxm-phase-sequence` · `mmxm-second-leg-entry` · `original-consolidation-identification` ·
`htf-reaction-mss-retrace-entry` · `htf-two-entry-opportunities` · `discount-requirement-before-entry` ·
`internal-external-range-liquidity` · `body-close-confirmation` · `daily-bias-requirement` ·
`opening-time-only-execution` · `smt-divergence-confluence` · `timeframe-alignment-ladder` ·
`post-trade-journaling-protocol` · `risk-limits-and-trade-frequency`

His MMXM sequence read left to right: original consolidation → push into a premium array → smart money
reversal → displacement lower (the MSS) → retracement into an OTE fair value gap in premium → break of
structure below that retracement → **a second distribution leg, which he names the silver bullet and
calls the highest-probability entry in the whole model**. Asked directly whether he enters at the
intermediate high/low or the failed swing, AM Trades gives the same answer for the same reason: the
**second leg**, at the failure swing (`mmxm-second-leg-entry`).

`discount-requirement-before-entry` is a hard location gate stated twice: no short unless price is above
equilibrium of the retracement leg, and the array must be an **OTE fair value gap** — a gap inside the
OTE band of that fib.

### Ben — `yRmKkR4CojU` (7)
Fractalising entries.
`sponsorship-vs-execution-timeframe` · `pd-array-matrix-ladder` · `balanced-price-range-revisit` ·
`backtesting-protocol` · `stop-moves-when-adding` · `post-trade-journaling-protocol` ·
`smt-divergence-confluence`

`sponsorship-vs-execution-timeframe` is the clearest automation-relevant idea any guest gives: **every
trade has two models**. The *sponsorship* model is where the idea comes from — the HTF PD array price
arrived at — and it fixes the **target**. The *execution* model is the same market-maker shape recreated
on a much lower timeframe inside that array, and it fixes the **entry**. The argument is arithmetic: a
weekly-sponsored short needs 300–500 points and months to make 2–3R, while the same idea executed on the
4-hour reaches 2R in 50 points. This is a cleaner statement of what the channel's timeframe pairing does
implicitly, and it is worth borrowing as vocabulary.

His `pd-array-matrix-ladder` is a targets method that uses **no projection tool at all**: enumerate every
PD array between price and the draw and take them in the order price must pass through them.
`balanced-price-range-revisit` gives a different BPR definition from the channel's: a BPR is a fair value
gap that has **already been filled** and is then revisited.

### Finessee_Fx — `eK_6wgNpNh0` (6)
Advanced directional bias.
`wick-to-body-order-block-zone` · `five-concept-entry-toolkit` · `old-accumulation-new-distribution` ·
`smart-money-reversal` · `engineered-liquidity-before-htf-array` · `smt-divergence-confluence`

His signature mechanic is a concrete answer to a question the channel leaves open: **draw the order-block
zone from the candle's wick extreme to the near edge of its body**, and extend it forward. Not the whole
candle, not its 50%. He defends it twice from chat and grounds it empirically — over years he found this
band the most sensitive part of the candle. Compare the channel's *opening price*
(`order-block`) and its wick-vs-body branch (`wick-vs-body-marking-rule`).

`old-accumulation-new-distribution` is the mirrored-curve claim: the same price zone that held as a
**bullish** order block on the left of a reversal reappears as a **bearish** order block on the right,
because positions accumulated there must be offset on the way back down.

`engineered-liquidity-before-htf-array` is a behavioural expectation with a stated frequency ("nine times
out of ten"): before reaching a marked HTF array, price stops **shy** of it, consolidates, engineers more
liquidity, and only then spikes into the level and reverses. He explicitly does *not* want a straight run
to the level.

### DayTradingRauf — `qFtfD09Vv3E`, `wB-fQiT_UDo` (15)
MMXM models; weekly preparation.
`breaker-wick-vs-body-invalidation` · `smart-money-reversal-breaker-confirmation` ·
`breakaway-gap-anticipation` · `dealing-range-fib-grading` · `mmxm-hedging-definition` ·
`old-accumulation-new-distribution` · `silver-bullet-breaker-requirement` · `three-pd-array-confluence` ·
`three-drive-reversal-pattern` · `dxy-yields-smt-pair` · `no-draw-no-trade` · `no-news-judas-swing` ·
`four-am-analysis-start` · `killzone-open-avoidance` · `quarter-month-close-expectation-cap`

`breaker-wick-vs-body-invalidation` is offered as something the audience can *study*, and is directly
testable: take a bullish breaker and watch what price does to its low afterwards — if **bodies** close
below it he does not trust the breaker; if only **wicks** do, it holds, and he reports that returns into
such a breaker trade much better. `no-news-judas-swing` is his own study result and it inverts common
practice: on a day with no high-impact news, 09:30 is the *only* volatility injection of the day, and he
found the Judas swing forms **more** reliably on exactly those days.

`smart-money-reversal-breaker-confirmation` is a flat instruction that contradicts the channel's
preference: **stop looking for an order block at the reversal** — require a breaker, and require price
to trade through it into an area of fair value.

### Trader Kane — `1wKfc2gN4xg` (9)
`dynamic-risk-scaling-matrix` · `prop-account-scaling-plan` · `house-money-capital-structure` ·
`size-down-on-fear` · `tilt-stop-rule` · `journal-losers-only` *(also Trader T)* ·
`probabilistic-acceptance` · `range-market-avoidance` · `four-hour-wick-positioning`

Almost entirely capital structure and psychology, and the most interesting parts are the capital rules
rather than the setups: `house-money-capital-structure` (fund only what you will lose in full, withdraw
the original deposit once the account has grown, and size the remainder as house money) and
`prop-account-scaling-plan` (scale by the *number* of funded accounts, not by size in one — twenty
accounts inside a 70–80 day window). `range-market-avoidance` is a candid regime admission: his model is
completely unprofitable in range-bound markets because it buys a low and sells into 50% of the leg.

### STRATalorian — `kG8BuEPVppo` (10)
`no-plan-no-trade` · `loss-and-gain-limit-rules` · `loss-streak-statistical-expectation` ·
`incremental-size-scaling` · `pay-yourself-and-reset-size` · `compounding-math-reality-check` ·
`bracket-order-not-guaranteed` · `setup-timeframe-discipline` · `post-trade-journaling-protocol` ·
`mean-reversion-3atr-21ema`

Pure process, and unusually good on the risk side. `loss-and-gain-limit-rules` is the one place in the
corpus that argues for a **gain-side** stop-trading limit, on the grounds that euphoria is more dangerous
than fear. `loss-streak-statistical-expectation`: over a thousand trades it is near-certain you lose 5–10
in a row, so size such that a run cannot end the account. `compounding-math-reality-check` runs the
account-doubling-challenge arithmetic as a reductio. `setup-timeframe-discipline`: if the setup and stop
came from a daily chart you have no business watching the 5-minute — compare the channel's
`entry-timeframe-elevation`, which reaches the same place from the other direction.

### NickDoesFutures — `G44VpidBD_U`, `tDiwwMRWF2k` (13)
`unicorn-entry-model` · `low-probability-day-checklist` · `weekly-written-game-plan` ·
`model-vs-entry-pattern` · `less-trades-more-capital` · `no-draw-no-trade` · `stuck-orderflow` ·
`valuation-by-speculation` · `post-trade-journaling-protocol` · `new-york-only-930-1130-window` ·
`one-minute-premature-entry` · `consolidation-reactivation-alert` · `stop-moves-when-adding`

`low-probability-day-checklist` is the most complete stand-aside list in the corpus and is worth reading
against the channel's scattered no-trade rules: Monday with no news; the day before CPI; the day before
NFP; the session before FOMC; a London session that aggressively took both Asia extremes; a central-bank
speech before or during the session; indecision on the daily bias; and a HTF level already met before the
session began. `weekly-written-game-plan` pre-classifies each day of the coming week as
no-trade / low / medium probability, in words, before the week opens.

### Ash Trades — `zXtJSSkiNmo` (11)
`internal-external-range-liquidity` · `swing-point-stop-hunt` · `one-model-focus` ·
`model-persistence-through-drawdown` · `mechanical-trade-management` · `risk-limits-and-trade-frequency` ·
`futures-over-forex-for-fills` · `fund-trading-from-external-income` · `daily-bias-requirement` ·
`opening-time-only-execution` · `timeframe-alignment-ladder`

`futures-over-forex-for-fills` is a nice example of an instrument choice falling out of a model
mechanic: because his entry is a resting limit at the *beginning* of the breaker and price frequently
only just touches it, the forex spread leaves the order unfilled where the futures order fills.

### The MMXM Trader — `Ibw4saRtYMk` (6)
`mmxm-hedging-program` · `mmxm-range-definition` · `mmxm-timeframe-alignment` ·
`mitigation-block-nested-pd` · `cot-commercial-net-check` · `mmxm-phase-sequence`

The source the channel's own MMXM material points back at. `mmxm-timeframe-alignment` gives a fixed
pairing table (monthly↔daily, weekly↔4H, daily↔1H, 4H↔15m, 1H↔5m, 15m↔1m) explicitly for the
internal/external range play. `mitigation-block-nested-pd`: a mitigation block on its own is **not** the
entry — a new PD array must form *inside* it, and that nested array is what is traded.
`cot-commercial-net-check` is the only fundamental-data rule anywhere in the corpus.

### AP — `gjoRPszj-Qk` (12)
`gb-levels` · `gb-retracement-entry` · `gb-range-return-entry` · `valid-structure-flip` ·
`body-close-confirmation` · `failure-swing-draw` · `order-block-requires-bos` ·
`second-continuation-confirmation` · `wick-midpoint-rebalance-entry` · `three-pd-array-confluence` ·
`smt-divergence-confluence` · `mechanical-trade-management`

The most numerically specific guest, and the most testable as a standalone system: a fixed set of five
fib levels — **0.295, 0.41, 0.705, 0.7475, 0.79** — on a validly flipped structure. Primary entry is a
**blind limit at 0.7475** with no confirmation (he claims 90–95% of his trades are these); the
range-return entry is a **body close beyond 0.41 plus displacement** (he claims ~80% of such closes
produce the retracement leg). Those are stated hit rates on stated levels, which is rare here.
`valid-structure-flip` is a clean definition worth borrowing: an MSS is a close beyond the **last valid
swing**, after which the low behind the move is a *strong low* that should not be revisited and the
opposing extreme is the *weak high* price is expected to draw to.

### DexterLab — `wWIHS_dxbEY` (5)
`wick-to-pd-array-rule` · `internal-dynamics-sequence` · `opening-location-vs-previous-range` ·
`opening-price-breaker` · `deviation-close-continuation`

Four strong, falsifiable structural claims. `wick-to-pd-array-rule`: **both** extremes of any candle
terminate at a PD array from the same or a higher timeframe, never a lower one.
`internal-dynamics-sequence`: inside one PO3 candle the lower timeframe delivers a fixed *ordered*
sequence — turtle soup, then order block, then breaker (once price closes back through the current
candle's opening price), then the FVG/OTE zone carrying the continuation.
`opening-location-vs-previous-range`: classify the developing candle by where its **open** sits in the
standard-deviation projection of the previous candle's manipulation leg — opening at 1/1.5σ means
unfinished business and continuation to 2/2.5σ; opening at 2/2.5σ means the projection is satisfied and
expect a retracement to equilibrium. This is the only place the corpus gives standard-deviation
projections a *forward-looking classification* role rather than a targeting one.

### HolyAngelBruv — `8Z2AbZLjunU` (7)
`orderflow-narrows-ict-entry` · `orderflow-tight-stop-profile` · `balance-area-poc-target` ·
`volume-profile-ledge` · `level-two-orders-can-be-pulled` · `delta-divergence-recency-limit` ·
`daily-bias-requirement`

The only order-flow speaker, and directly relevant because the channel **evaluated and rejected** this
layer — his stated test was "is there a mechanical definition of absorption and of where the entry is?"
and he dropped it because there is not (`ttfm-minimal-toolkit`). This guest's answer is a division of
labour: ICT supplies the overarching context, footprint and DOM supply the entry. His stated live
numbers, unusually, include the payoff: ~40% win rate, 2.5-point stop, 8-point target, runners
(`orderflow-tight-stop-profile`). `volume-profile-ledge` makes the bridge explicit: **every fair value
gap is really a low-volume node**, because price moved so fast through it that little volume transacted.

### Trader T — `wCtxmWe4KNc` (5)
`backtesting-protocol` · `journal-losers-only` · `cancel-limit-after-target-run` ·
`htf-reaction-mss-retrace-entry` · `risk-limits-and-trade-frequency`

`cancel-limit-after-target-run` is his most mechanical rule and he supports it with his own logged
sample: if a pending limit has not filled and price instead runs to where the take-profit would have
been, **delete the order** — in most logged cases a limit filling after the target was reached goes on to
hit the stop. He demonstrates it twice in-session and both abandoned entries would have lost. His
`backtesting-protocol` carries the behavioural rule that matters: replay software's failure mode is
spamming through bars; move bar by bar and treat the session as live, because that is the behaviour you
are training.

### Gene — `nncJGt6j19Q` (7)
`weekly-candle-institutional-profile` · `weak-longs-weak-shorts` · `model-vs-entry-pattern` ·
`less-trades-more-capital` · `no-draw-no-trade` · `valuation-by-speculation` ·
`discount-requirement-before-entry`

`weekly-candle-institutional-profile` reads the weekly candle as three phases around its opening price
(measured at **midnight New York, not GMT**): accumulation below the open, profit release as the
one-sided expansion above it, distribution at a HTF premium. `weak-longs-weak-shorts` is a clean
behavioural account of why the retracement happens at all.

### Trade For Opportunity — `0bH_kkG2q6s` (3)
`daily-trade-cap-risk-envelope` · `multi-timeframe-fvg-indicator` · `volume-spike-at-extremes`

`daily-trade-cap-risk-envelope` derives the cap rather than asserting it: without a trade count there is
no ceiling on how much can be lost in a day, so three trades at 1% with a 2:1 payoff bounds the day at
−3% worst, +6% best.

### Rauf / others on smart money reversal — `uDJI2AbyyCs`, `bbWPoajy2MY`, `DMUiDBnTYc8`, `McJflkKuvrI`
`smart-money-reversal` · `consolidation-reversal-week` — terms used across several videos as assumed
knowledge and never formally defined. Recorded as `contested` for exactly that reason.

---

## 4. Cross-speaker agreements worth noticing

Where several *independent* guests converge, the claim is at least worth testing — though note none of
them cites data.

- **SMT is confluence, not a signal** — two guests (`smt-divergence-confluence`), agreeing with the
  channel's own `smt-requires-framework`.
- **Three stacked PD arrays at one price is the probability filter**, with the symmetric failure test:
  three arrays failing means the idea is invalid — three speakers (`three-pd-array-confluence`).
- **A model is not an entry pattern** — two speakers independently argue that what most traders call a
  model is only an entry protocol; a model must be the full filter including risk protocol, enumerated
  high/low-probability conditions, sessions, timeframes and journalling (`model-vs-entry-pattern`).
  This is the same position the channel takes in `entry-model-least-important` and
  `pattern-trading-error`.
- **Fewer trades, more capital** — two futures-side speakers report profitability improved as frequency
  fell, and both budget 0–3 trades per week (`less-trades-more-capital`).
- **Two losses and stop** — two guests, independently (`risk-limits-and-trade-frequency`).
- **Never trade Mondays** — AM Trades absolutely, the host concurring more softly (`no-monday-rule`).
- **Bodies tell the story, wicks do the damage** — a level holds while bodies fail to close through it
  (`body-close-confirmation`, `breaker-wick-vs-body-invalidation`), which corroborates the channel's
  `order-block` ("the wicks reach into there, the body is still respecting").
- **Stuck / trapped order flow** — price between two opposing HTF arrays is a no-trade state until one is
  closed through, named by two speakers (`stuck-orderflow`).
- **Valuation by speculation** — the early-week false move against the intended weekly direction, read
  the same way by three speakers who differ only on the response (`valuation-by-speculation`).

---

*Generated from `concepts/**/*.yaml` (`voice: guest`) via `python/build_method_spec.py guests`. Every id
resolves to a file with a video id and verbatim quotes of 15 words or fewer. Nothing here is the
channel's method — see `ttrades_method_spec.md`.*
