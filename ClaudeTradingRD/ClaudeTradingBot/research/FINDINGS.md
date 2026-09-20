# FINDINGS — XAU 5-second Microstructure / Liquidity Edge

_Synthesis after 3 research rounds (18 candidate strategies). Data: 30 cached
months of real OANDA S5 bid/ask, 2024-01 -> 2026-06. Train = 2024-01..2025-07,
OOS = 2025-08..2026-06, plus a +0.33pt (~1.5x median spread) stress pass._

## 1. Honest verdict

**No strategy cleared the acceptance bar in `research/GOAL.md`. Zero survivors.**

Not one of the 18 candidates produced a positive OOS net, let alone PF >= 1.3 with
>=100 OOS trades inside the 3-25 trades/day band. The **best** OOS profit factor
across all rounds was **0.803** (`fvg_htf_reclaim_origin`) — still a *losing*
system. The closest to break-even in dollar terms was `micro_bos_cont_maker`
(OOS net -$14.28), but it fired only **32 trades over 30 days (~1.07/day)**, an
order of magnitude below the >=100-trade / 3-25-per-day requirement, and its PF was
0.80. I re-ran it during this synthesis and the numbers reproduce exactly.

Distance to the stretch target (70-90% WR, 1-2% DD): **not close, and the WR moved
the wrong way.** Observed OOS win rates clustered at **31-35%** for the taker
variants and never exceeded ~40% for the makers. Nothing approached even the
minimum 55% WR, never mind 70%+. The "tiny DD" half of the target was sometimes
met (e.g. maxDD $43 on `micro_bos_cont_maker`) — but only as a *side effect of
trading almost nothing*, not because of a high-WR edge. Low DD on a PF<1 system is
not an achievement; it just means the system bled slowly.

## 2. Survivors

| Strategy | OOS trades | t/day | WR% | PF | net$ | stress net$ | file |
|---|---|---|---|---|---|---|---|
| _(none cleared the bar)_ | - | - | - | - | - | - | - |

For reference, the three that came *closest* (highest OOS PF, all maker-only,
all still losing and all far too infrequent) are kept in place:

| Strategy | OOS trades | t/day | WR% | PF | net$ | path |
|---|---|---|---|---|---|---|
| fvg_htf_reclaim_origin | 41 | 1.43 | ~37 | 0.803 | -110.97 | `bot/micro/strat_r2_5.py` |
| asian_amd_maker_revert | 30 | 1.00 | ~37 | 0.801 | -36.21 | `bot/micro/strat_r2_0.py` |
| micro_bos_cont_maker | 32 | 1.07 | 34.4 | 0.799 | -14.28 | `bot/micro/strat_r3_1.py` |

These are documented as the least-bad attempts, **not** as deployable edges.

## 3. What categorically failed, and why (the 0.66pt spread floor)

Every candidate maps to one of six liquidity/microstructure families; all six died,
and they died in a way that points straight back to the cost floor.

- **High-frequency taker triggers were destroyed by the spread.** Every variant that
  traded 10-25/day (`micro_bos_cont` -$2,458, `micro_bos_retest` -$3,743,
  `swept_swing_fade` -$2,099, `swing_sweep_fade_filtered` -$2,027,
  `eqhl_pool_bias_maker` -$4,170) posted OOS PF 0.46-0.68. This is the scout result
  reconfirmed: median 5s bar range ~ 0.26pt while a taker round-trip pays ~ 0.66pt,
  so the typical capturable move is ~2.4x *smaller* than the cost of capturing it.
  At 5s resolution there simply isn't enough signal per trade to clear the spread,
  and filtering/biasing the trigger reduced count but never inverted the sign.
- **Maker (limit) entries earned the spread back but starved on frequency.** The
  PF leaders were all maker-only, bias-gated variants — confirming scout finding #4
  that limit entries lift EV by roughly half a point. But that uplift only carried
  them from PF ~0.4 to PF ~0.8: it narrowed the loss, it did not create an edge. And
  the contexts clean enough to justify a resting limit occur only ~1/day, so even the
  best maker never reached double-digit trade counts in OOS — failing the >=100-trade
  bar regardless of sign.
- **Directional context (HTF bias, AMD session timing, absorption) did not generate
  excursion asymmetry.** Adding daily/HTF bias gates, Asian-range AMD windows, and
  volume-absorption confirmation all *reduced* trade count and *raised* PF modestly,
  but none produced the favorable->>adverse excursion the scout flagged as the only
  place an edge could live. Post-trigger MFE/MAE stayed roughly symmetric, so the
  expectancy stayed negative once the spread was paid.

The unifying law, restated with this run's evidence: **on this instrument,
profit-factor and frequency are inversely coupled, and the coupling line sits
*below* break-even.** The configs with the best PF are precisely the ones trading
~1x/day; pushing frequency up into the required 3-25/day band collapses PF toward
0.3-0.5. There is no point on the observed curve that is simultaneously frequent
enough and profitable enough to pass. The 0.66pt spread is the wall, and 5s taker
microstructure does not clear it.

## 4. Single most promising direction next

**Stop mining 5s taker triggers; the cost floor has been demonstrated three times.**
The one direction with a live pulse is the **maker-only, daily-bias-gated resting
limit at HTF-validated liquidity** (the PF-0.80 cluster above, and the
`snap_ict_maker` line in project memory). It is the only family where execution
economics flip in our favor. The concrete next step is to push that line to PF > 1.0
by (a) restricting fills to genuinely *confirmed-and-held* swing/equal-level
liquidity rather than rolling extremes, (b) sizing risk-constant per trade to bound
the loss tail, and (c) accepting ~1-3 trades/day as the real ceiling — i.e. abandon
the 5-20/day clause of the goal, which the data shows is incompatible with a positive
edge here.

**Critical deployability caveat (do not skip):** the funded account
(FundingPips MT5, acct 6c7ce166) is **market-execution / taker-only**, so a
maker-only edge is research-valuable but **not deployable there** — consistent with
the prior `snap_ict_maker_rp` -> taker -$3,730 FAIL recorded in memory. If the
requirement is a *deployable* edge on that account, the honest answer from this
microstructure work is that **none exists at 5s**, and the deployable path remains
the already-validated higher-timeframe **H4 trend-follow** (`bot/challenge_xau.py`),
where the signal-to-spread ratio inverts in our favor.

## 5. Files kept in place
- `bot/micro/strat_r3_1.py` (micro_bos_cont_maker) — least-bad OOS net
- `bot/micro/strat_r2_0.py` (asian_amd_maker_revert) — maker AMD, PF 0.80
- `bot/micro/strat_r2_5.py` (fvg_htf_reclaim_origin) — highest OOS PF 0.80
- all other `strat_r*.py` retained for the audit trail; none are survivors.

---

# Round 2 — micro-BOS frequency expansion

The round-1 update isolated a REAL taker edge in the micro-BOS continuation signal
(`strat_r3_1.py`) that the wide 0.66 practice spread had masked. Round 2's only job:
raise frequency from ~1/day into the 3-25/day band while holding PF >= 1.3 @0.25 taker
and positive @0.30 taker, OOS trades >= 100. Three internal rounds, 18 variants.

## 1. Did any variant reach 3-25/day with the edge intact? NO.
Many variants cleared OOS>=100 and PF>=1.3 @0.25 taker, but EVERY ONE sat at ~1.0-1.5
trades/day. The 100-trade bar was met only by the length of the 90-trading-day OOS
window, never by 3+/day. Not a single configuration combined a real edge with the
3-25/day band. The literal 5-20/day goal is not reachable here.

## 2. The frequency<->PF frontier (why)
The binding constraint is OCCUPANCY, not signal supply. The best opener+rearm config
emits ~668 raw OOS signals (~7.4/day) but only ~135 execute (~80% skipped): the
signals across the four lookbacks + intra-leg rungs are COINCIDENT breaks of the SAME
trend leg. Distinct continuation legs in London/NY occur only ~1.5/day on XAU 5s, and
the single-position engine (one challenge account, no pyramiding) serialises the rest.

Measured levers (OOS 0.25-taker PF / grid N), each tried on the multiscale+rearm base:
  - TTL 480->120->60        : N 138->136->133 , PF 1.41->1.06->1.10  (slow deep fills ARE
                              the good trades; cutting limit-life kills edge, frees nothing)
  - maxhold/trail tightened : N ->152 , PF ->1.09  (the trailed runner IS the edge; clip it
                              and the asymmetry vanishes -> classic anti-continuation)
  - cooldown 6->0, rung-gap : N ->145-147 , PF 1.40-1.52  (adds a few real trades, edge held,
                              but t/d still ~1.5)
  - rung gates loosened     : N 147 , PF 1.52@0.25 / 1.39@0.30 (BEST PF; extra rungs are
    (ext0.3/gap6/mr80/hlk0.6) quality, not noise -> robustness evidence, not overfit)
  - 8-scale union           : N 145 , PF 1.41  (more scales = more coincident, not more legs)
  - K_DISP < 1.8 / RETR<0.6 : pure cliff to PF<1.0 (prior rounds): these ARE the edge, not a
                              frequency throttle.
The frontier is flat in N (133-152) and flat-to-slightly-up in PF across every
non-edge axis: a genuine parameter plateau pinned at ~1.5 trades/day.

## 3. Best deployable candidate -> `bot/micro/EDGE_microbos.py`
Promoted from `strat_mb_r3_4.py` (multiscale + intra-leg re-arm) at its proven config.
Full OOS spread grid (real S5 ticks, OOS 2025-08..2026-06):
  | spread | maker PF / net | taker PF / net |
  |--------|----------------|----------------|
  | 0.20   | 1.727 / +$139  | 1.540 / +$111  |
  | 0.30   | 1.517 / +$105  | 1.284 / +$64   |
  ~0.25 taker PF ~ 1.41 ; WR ~45% ; N=138 (~1.5/day) ; maxDD ~$107/$5k.
REQUIRED LIVE SPREAD: <= ~0.25pt taker in 07-15 UTC for the headline edge; break-even
is ~0.30-0.33 taker. At the 0.66 practice feed and the 1.5x-cost stress pass it is NET
NEGATIVE, and TRAIN-window grid PF is < 1 -- the realistic-spread edge is a 2025-26
regime property, so treat it as fragile and spread-gated, not an all-history plateau.

## 4. Honest call on the 5-20/day goal
Unreachable with a real edge on XAU 5s. The micro-BOS continuation edge is real but
RARE: it is the deep maker retest of a genuine displacement leg, and such legs print
~1-1.5/day in the London/NY window. Pushing for 3-25/day necessarily either (a) re-counts
the same leg (occupancy wall) or (b) loosens the displacement/retest/exit that constitute
the edge, collapsing PF through 1.0. ~1-1.5 trades/day is the true ceiling. This matches
every prior micro_bos / sweep dead end, now mapped as an explicit frontier rather than
asserted. Deployability caveat unchanged: FundingPips MT5 is taker-only and the edge needs
<=0.25 live spread -- verify the live XAU spread before risking the account; otherwise the
deployable path stays the H4 trend-follow (`bot/challenge_xau.py`).

---

# Round 3 — M1/M5 (the timeframe change that finally cleared the cost floor)

Round 3 abandoned the 5s resolution (proven three times to sit below break-even) and
ran the same liquidity/microstructure families on M1 (60s) and M5 (300s) bars, with a
deliberately STRICTER bar: a candidate had to be POSITIVE AT 0.25 TAKER IN BOTH TRAIN
AND OOS (the runner now prints `train_spread_grid` alongside `oos_spread_grid`), not
just OOS-positive. The prior 5s/round-2 "winner" (EDGE_microbos) was train-NEGATIVE —
a 2025-26 regime fit — and is retroactively reclassified as fragile by this bar. 18
M1/M5 candidates across three internal rounds.

## 1. Did any family produce a REGIME-ROBUST edge at 3-20/day? Edge YES, 3-20/day NO.

For the first time in this project a candidate is positive at 0.25 taker in TRAIN
*and* OOS *and* **every individual calendar year** *and* through the 1.5x-cost stress
pass: **`ob_retest_cont_m5` (M5 order-block retest continuation)**, promoted to
`bot/micro/EDGE_m1.py`. This is a genuine plateau survivor, materially stronger than
the round-2 EDGE which only held in the OOS regime. But its honest frequency is
~1.16-1.4 trades/day. The literal 3-20/day band remains unreachable WITH the edge
intact: the only families that fire 3-10/day are M1 mean-reversion (vwap/svwap/band-
fade) and they are all PF<1 in train. So the frequency<->edge inverse coupling first
documented at 5s survives the move to M1/M5 — the timeframe change raised the ceiling
of the *edge*, not the frequency at which the edge exists.

## 2. Survivors / near-survivors (PF at 0.25 taker; per-year = full-30mo constant-spread synth)

| strategy (file) | TF | TRAIN PF@.25 | OOS PF@.25 | 2024 | 2025 | 2026 | N(oos) | t/day | WR% | maxDD | 1.5x stress |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **EDGE_m1** ob_retest_cont_m5 (`strat_m1_r3_2.py`) | M5 | 1.235 | 1.760 | **1.28** | **1.15** | **2.12** | 107 | 1.16 | 38.3 | $46 (0.9%) | **+$34 PASS** |
| m1_fvg_fill_origin_bias (`strat_m1_r3_5.py`) | M1 | 1.529 | 1.514 | 0.95 | 1.65 | 1.53 | 335 | 2.41 | 57.2 | $67 | -$43 FAIL |
| m1_fvg_cont_bias_gapfloor (`strat_m1_r2_0.py`) | M1 | 1.727 | 1.843 | 0.89 | 1.67 | 2.04 | 146 | 1.64 | 54.2 | -$7 FAIL |

Only the top row is positive in ALL THREE years and survives the stress pass; it is
THE survivor. The two FVG-continuation rows have higher headline PF and ~2x the
frequency, but both go flat/negative in 2024 (PF 0.89-0.95) with trades concentrated
in the recent high-vol 2026 regime, and both turn net-negative under 1.5x cost — i.e.
real but regime-tilted, exactly what the stricter bar exists to flag. They are kept as
the higher-frequency / higher-WR alternatives, not promoted. The frequent M1 families
that met 3-10/day — `m1_vwap_dev_revert` (8.8/d), `m1_band_fade_htf` (10.1/d),
`m1_svwap_fairvalue_pullback` (3.2/d), `m1_confirmed_spike_rev` (2.6/d) — were ALL
PF<1 in train and are dead ends: frequency without edge.

## 3. Which family carried the edge, and why M1 worked where 5s did not

The edge is a **continuation/momentum** edge — order-block and FVG retests in the
direction of a fresh displacement leg, long-only into gold's 2024-26 uptrend — NOT
mean reversion. Every mean-reversion family at M1 (vwap/svwap deviation, band fade,
spike reversal) was frequent but sub-cost. The mechanism for why M1/M5 cleared the
floor where 5s could not is purely signal-to-cost geometry: at 5s the median bar
range (~0.26pt) is ~2.4x SMALLER than a taker round-trip (~0.66pt), so no single 5s
move pays for the spread and every 5s trigger stayed PF<1 regardless of filtering. At
M1 the bar range median (~2.06pt) is ~3.1x LARGER than the spread, and on M5 an
order-block retest spans a multi-point continuation leg whose favorable excursion
clears the cost with margin. The cost floor did not move; the move per trade grew past
it. The OB-retest specifically wins because the resting limit at the demand zone earns
position before the continuation, and the chandelier trail lets the few real legs run
(hence the low 38% WR but PF>1.5: many small losers, few large trailed winners).

## 4. Honest call on the 5-20/day + real-edge goal at M1, and the required live spread

The 5-20/day goal is still NOT reachable with a real, regime-robust edge on XAU —
that conclusion now holds across 5s, M1, and M5. The deployable answer is ~1.4
trades/day, not 5-20. But within that constraint Round 3 produced a real, defensible
WIN: `EDGE_m1` is positive at realistic taker spread in train, in OOS, in all three
years, and through a 1.5x-cost stress — the strongest robustness profile any candidate
in this project has shown, and a clear improvement over the train-negative round-2
edge. Required live spread: positive through 0.30 taker in both windows and through the
stress pass, so break-even is ~0.33-0.40 taker — a wider, more forgiving margin than
EDGE_microbos (<=0.25). DEPLOY CAVEAT (unchanged and load-bearing): FundingPips MT5
(acct 6c7ce166) is market-execution / taker-only; EDGE_m1 rests a maker limit at the
OB, so on that account you enter at market/stop when price reaches the zone (the
runner's taker grid already prices that). MEASURE the real XAU spread in 04-18 UTC
before risking the account — if it is at/below ~0.33 taker, EDGE_m1 is deployable;
above that, the H4 trend-follow (`bot/challenge_xau.py`) remains the safer funded path.

## 5. Files added/kept (Round 3)
- `bot/micro/EDGE_m1.py` — PROMOTED survivor (copy of `strat_m1_r3_2.py` + verified header).
- `bot/micro/strat_m1_r3_5.py` (m1_fvg_fill_origin_bias) — higher-freq FVG alt, regime-tilted.
- `bot/micro/strat_m1_r2_0.py` (m1_fvg_cont_bias_gapfloor) — highest PF FVG alt, regime-tilted.
- all other `strat_m1_r*.py` retained for the audit trail; none promoted.
