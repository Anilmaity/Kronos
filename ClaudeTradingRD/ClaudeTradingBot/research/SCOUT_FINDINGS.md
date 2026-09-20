# Scout findings — read before designing (saves you rounds)

Measured on real S5 data, 2024-01..2024-08 (~2.6M bars). These kill the naive
approaches cheaply so you start from a higher floor.

## 1. The spread is the boss
Median S5 spread = **0.66pt**; median 5s bar range = 0.26pt. Any taker round-trip
pays ~0.66pt. Your per-trade edge must clear that with margin.

## 2. The naive "exceeded prior-N high/low" trigger has NO directional edge
- In a trend year (2024) it fires almost entirely one-sided (20,693 up-breaks vs 276
  down) — it's just **trend making new highs**, not a stop-hunt. Fading it = knife-catching.
- Post-trigger excursion over ~15 min is ~symmetric: MFE med ~2.3pt, MAE med ~3.0pt, in
  BOTH fade and continuation framings. EV is negative every bracket, both directions.
- LESSON: a bare breakout/sweep trigger is noise. The edge must come from a FILTER that
  produces excursion ASYMMETRY (favorable >> adverse) in a specific context.

## 3. Where asymmetry might actually live (hunt here)
- **Genuine resting liquidity**: equal highs/lows clusters, session highs/lows, prior
  *confirmed swing* levels that HELD — not every rolling-N extreme.
- **Rejection quality**: speed/size of the reversion wick; did the close reclaim the level
  decisively, with a volume spike (absorption) on the sweep bar?
- **HTF alignment**: only fade INTO higher-TF bias, or only continue WITH it.
- **Session cause/effect**: Asian-range build -> London sweep-and-reverse (AMD) is a
  distinct, time-localised pattern; test sessions separately, don't pool all hours.

## 4. Execution mode matters as much as the signal
- **Maker (limit) entry earns the spread**: it lifted EV by ~+0.5pt vs market even on the
  dead naive trigger. If you find a directional filter, a limit at the level is far more
  survivable than a market entry. Use kind=1 in Signals.
- DEPLOYABILITY CAVEAT: the user's funded account (FundingPips MT5) is taker-only, so a
  maker-only edge is research-valuable but not deployable there. Report which execution
  mode your result needs. A taker-survivable edge is the gold standard.

## 5. Frequency vs edge (from prior project research, still true)
Every prior attempt found frequency and profitability inversely related on this instrument.
5-20 trades/day AND a real edge is the hard part. Prefer FEWER, higher-quality entries; if
your filter only yields 3-6/day but they're real, that beats 20/day of noise.
