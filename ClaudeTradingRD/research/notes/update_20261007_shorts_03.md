# Study notes — unit `update_20261007_shorts_03` (Shorts, update pass)

Seven Shorts, 27–74 s each (334 s total; the unit header says "6 min"). All are TTrades
himself (voice: ttrades), several answering a viewer question read aloud. Auto-captions,
**no timestamps**, so no `approx_time` anywhere. Every transcript was read in full.

---

## Make A Change or Quit (7u_gshYuIKA, 36 s)
**Taught.** Reply to "I've followed you two years and haven't become successful": he cannot
know an individual's problem; the trader must find the root cause of what blocks progress —
usually tilt, oversizing, revenge trading, or not following a model. Once found, there are
two options: change or quit. Anything else wastes your own time.
**Examples.** None (talking head).
**Hygiene.** "two years, years" stutter; "over sizing" = oversizing.
**Library.** Exact repeat of `root-cause-diagnosis` (already aliased "change or quit"). Source only.

## Make Targets Simple Using the Fractal Model (CEm1Bnhvb2I, 39 s)
**Taught.** Target for an expected bearish candle 3 expansion: mark the previous lows on the
higher timeframe (two of them), carry them to the lower timeframe as target 1 and target 2.
Price makes a high, expands lower, hits target 1. He then asks: retracement, reversal, or
consolidation? It is a consolidation — "a continuation signature" — and price trades lower to
target 2. Rule stated: keep targets simple; on intraday timeframes or the hourly, focus on the
previous days' highs and lows.
**Examples.** One chart, no prices or times spoken. HTF implied daily, LTF hourly.
**Hygiene.** Clean.
**Library.** `draw-on-liquidity` (previous day H/L as objective) and `continuation-signature`.
Small nuance: here *retracement* is listed beside *reversal* as the alternative to consolidation,
while the library counts a retracement as a continuation signature as well — recorded as an
ambiguity, not a contest.

## Using Intra-Candle CISD to Trade Continuations (Kv6Y8IA7jYs, 60 s)
**Taught / trade walked.** Candle 2 closure, then a range. Bullish bias; point of interest is
the run of the lows. Price instead runs the highs first and moves aggressively against the
bias — he does **not** invalidate the bias "because it's not a reversal off of previous day
high", and waits for a new continuation. The first candidate looks like a consolidation, "really
hard to trust this level", so he needs **another sweep**. After it, an aggressive move out forms
a continuation inside candle 3, read as the daily wick having formed. Trade: long, stop on the
low, target the daily high, 2R available only from a **retest** entry. Not filled — "and that's
okay". No trade taken.
**Examples.** No instrument, prices or times stated.
**Hygiene.** "candle to closure" = candle 2 closure; "I've anticipate" = I'd anticipate.
**Library.** `ic-cisd`. Adds two decision rules the entry lacks: (1) an opposite-side run does
not kill the bias unless it is a reversal off the previous day high; (2) a consolidation-like first
intracandle swing is not trusted — wait for a second sweep plus an aggressive move. Also a
concrete no-fill-no-trade outcome with a limit priced for 2R (cf. `cancel-limit-after-target-run`).

## Intraweek Reversal Breakdown (W67tJ6fmAuc, 57 s)
**Taught.** Monday expands away → the weekly candle wants to go higher → trade a candle 4
continuation; it forms but is small after a large range, so wait for a new phase. Bullish bias
kept; a candle 2 closure appears, so expect the next day to take the previous day low or reach
a fair value gap. It takes the PDL and closes above, and an SMT with a correlated asset lets that
day be treated as a candle 2 closure / swing point. Sequence: Monday expansion, Tuesday–Wednesday
consolidation, Thursday = candle 2 / reversal, Friday = continuation.
**Examples.** One week chart, no prices/dates.
**Hygiene.** "SMT with RB" — instrument garbled (could be ES/NQ/YM; unrecoverable). "treat it
like it as a swing point" stutter.
**Library.** `intraweek-reversal-week` (Thursday-as-reversal variant already recorded) and
`smt-swing-point-substitute` (PDL sweep + close above + SMT = C2, already recorded). Source only.

## What Does "R" Actually Mean in Risk to Reward? (brI51kBw-Fk, 74 s)
**Taught.** R = risk = the size of your stop loss; for him, dollar risk, determined by entry and
stop, and it determines position size. Every trade risks exactly 1R, even with a bigger stop.
Reward is counted in R-rectangles: $100 risk → 1R target = $100, 2R = $200, 3R = $300. "I got
2R" = a target twice the stop distance, held to the end.
**Hygiene.** "Cuz" = because.
**Library.** `position-sizing-fixed-risk` (fixed dollar risk, size from stop). The library had no
plain definition of R in his words; added as a definition, untestable.

## Taking Profit Early Forces You to Have a Higher Win Rate (tCDsDlYQ1gw, 51 s)
**Taught.** Closing out early stems from fear. On a 2R system break-even win rate is 34%; taking
profit at 1:1 changes the system — break-even becomes 50%. "Locking in profits" is reframed as
forcing yourself to need a higher win rate.
**Hygiene.** "He trades" opening = garbled question start; "I'm I'm" stutter.
**Library.** `risk-reward-minimum` already has 34% @2R and the 1:1 → 50% arithmetic (partly from
a guest); this gives it a host-voice source. `root-cause-diagnosis` already maps "can't hold to
target → fear". No new rule.

## Define Your Setup to Avoid Watching Charts All Day (zo-3GgGp6pw, 27 s)
**Taught.** Define your model, what you are looking for, and when you look for it. He only really
trades New York, sometimes swings Asia or takes swing trades, never the PM session — "really just
the morning". Setup present → watch; absent → stop paying attention.
**Hygiene.** "looking for a charts" garble.
**Library.** `new-york-am-session-only` (adds a direct host statement excluding PM; still no clock
hours) and `one-model-focus` (previously guest-only; now has host voice).

---

## Cross-video: new vs repeat

**Genuinely new:** nothing warranting a new id. The update pass confirms saturation.

**Materially new rules on existing concepts (new_claim):**
- `ic-cisd` — bias survives an opposite-side run unless that run is a reversal off the previous
  day high; a consolidation-like first intracandle swing requires a second sweep before entry;
  limit at the retest priced for 2R, no fill = no trade.

**Repeats (sources added, voice strengthened):** `root-cause-diagnosis`, `draw-on-liquidity`,
`continuation-signature`, `intraweek-reversal-week`, `smt-swing-point-substitute`,
`position-sizing-fixed-risk` (R definition), `risk-reward-minimum` (host voice for the 34%/50%
arithmetic), `new-york-am-session-only`, `one-model-focus` (host voice).

**Open ambiguities carried forward:** "consolidation-like" and "aggressive move out" in the
IC-CISD walk are undefined; SMT instrument in W67tJ6fmAuc unrecoverable; still no session clock
hours.
