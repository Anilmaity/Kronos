# The 471-concept campaign — final record (run 2026-09-23)

**Question.** Does any single concept in the TTrades library, tested one at a time on its own
terms, have a measurable and tradeable edge on XAUUSD? Phase 3 had already refuted the
*conjunction* (HTF bias → POI → CISD → timing). This campaign asked the same question of each
*piece*: every concept in the 471-concept campaign roster, which is the 505-concept library minus its
34 psychology concepts.

**Answer.** No. 43 of 663 readings came back EDGE under the locked per-concept rules. Adversarial
verification refuted 34 of those. Of the 9 that survived, 5 also survive Benjamini-Hochberg over the
864-hypothesis family. A deep dive on those 5 found **none that can be traded**:

- 2 are artefacts of how the control places its stop (`cheat-code-entry`, `aggressive-run-hammer-signature`).
- 3 are true but small statements about price with no entry that survives cost
  (`point-of-interest`, `daily-profile-session-windows`, `fvg-three-levels`).

The negative results say more than the positive ones. Six of them survive BH, and two survive Holm.

Per-reading table: `concept_campaign/concept_verdicts.csv` (663 rows). Builder:
`concept_campaign/build_concept_verdicts.py`. Everything below was recomputed from
`campaign_raw.json` / `campaign_adjusted.json` / `results/`, not copied from tester summaries.

---

## 1. Method

| component | what it did |
|---|---|
| harness | `research/python/concept_lab` (README there), `RULES_VERSION = concept_lab-rules-2 (2026-09-23)`, locked before any result was written and pinned by `tests/test_rules_locked.py`. Read-only for testers. |
| data | certified XAUUSD M1 mid-quote OHLC, 2016-01-04 → 2026-07-23 (10.55 years). No volume. Correlates: XAG_USD and EUR_USD **H1 only**; one batch fetched XAU_EUR/XAU_GBP H1. |
| test types | `trade_test` (234 readings): net R minus a **matched random-entry control** (same direction, stop distance, target distance, ±30-day regime, 5 reps). `gate_test` (294): control-adjusted R, gated arm minus complement. `rate_test` (85): hit rate minus a matched null rate. `write_untestable` (50). |
| execution model | entry at the open of the first M1 bar at or after the decision time; exits resolved on M1; same-bar stop and target resolve **stop-first**; flat 0.04R cost, which cancels in every differential. |
| look-ahead | symmetric `probe_lookahead` on the exact frame that was scored (≥100 random cuts plus 20 targeted decision times; extra, missing or changed events all fail). `write_result` refuses a result without a passing probe with a matching fingerprint. 13 adversarial look-ahead scenarios in `review_lookahead/`. |
| verdict | UNTESTABLE (declared, n < 30, sanity floor, or tie rule) → NEGATIVE (CI excludes 0 against the claim) → EDGE (CI excludes 0 for the claim, both halves same sign, MDE ≤ 0.10R or min(5pp, 25% of null), n and effective n ≥ 200) → NULL (CI contains 0, powered) → UNDERPOWERED. CI = the widest of i.i.d., 20-event block, trading-day block and cluster bootstraps (2,000 draws). |
| calibration | three phase-3 books reproduce (1h rung 0: n=7,995, diff +0.0093 vs published +0.009). 530 pure-noise books give **2.1% false EDGE** (`review_statistics/rules2_false_edge.py`). |
| scale | **61 batches** (6 categories × own/guest voice, split a/b), 663 result files, 1,077 ledgered runs, **864 distinct hypotheses** = 612 written with a p-value + **252 run but never written** (dropped readings, diagnostics, reruns). |
| verification | every raw EDGE went to **two independent adversarial agents**. The *implementation* lens looked for look-ahead and bugs and rebuilt the concept independently. The *faithfulness* lens asked whether it tests what the concept says and whether it survives robustness checks. An EDGE survives only if neither agent refutes it. |
| multiplicity | Holm and BH (q = 0.05) across the full 864-hypothesis family (`cl.adjust_campaign(ledger=True)`). A reading that was tried and dropped still costs multiplicity. |
| deep dive | the 5 EDGEs that survived both verification and BH got a dedicated study: structural controls, 50/50 tie re-scoring, calendar blocks, realistic spread (0.25–0.35 pt) and a search for a tradeable version. Scripts are in `concept_campaign/deepdive/<concept>/`. None of it wrote to the campaign ledger or results. |

## 2. Headline numbers

### The funnel

```
663 readings of 471 concepts
 ├─ 612 tested with a p-value  ·  51 without (50 declared UNTESTABLE + 1 with n=4)
 ├─ 43 raw EDGE  (38 concepts)          noise alone would give ~13-18 (2.1-3% of 612)
 │   ├─ 34 refuted by verification      (20 by both lenses, 13 faithfulness only, 1 implementation only)
 │   └─  9 upheld by both lenses
 │        ├─ 4 fail BH                  (q 0.11-0.20: BPR a, intraday-reversal, no-shorting-below-lows b, IFVG b)
 │        └─ 5 pass BH (3 also Holm)
 │             ├─ 2 ARTEFACT            cheat-code-entry, aggressive-run-hammer-signature
 │             └─ 3 DESCRIPTIVE_ONLY    point-of-interest, daily-profile-session-windows, fvg-three-levels
 └─ tradeable: 0
```

BH rejects 30 hypotheses in total and Holm rejects 13. 17 of the 30 BH rejections are raw EDGEs. 12 of those 17 were refuted by
verification, including 5 of the Holm survivors: both `est-timezone-anchor` readings,
`target-liquidity-and-imbalances b`, `trend-entry-options` and `gap-direction-fade-rule a`.
**Surviving multiplicity correction did not predict surviving verification.** The confounds the verifiers found are
systematic, so a large n makes them *more* significant, not less.

### Verdicts by category (readings / concepts)

Concept level uses the most informative reading: EDGE > NEGATIVE > NULL > UNDERPOWERED > UNTESTABLE.

| category | EDGE | NEGATIVE | NULL | UNDERPOWERED | UNTESTABLE | total |
|---|---:|---:|---:|---:|---:|---:|
| entry | 12 / 12 | 1 / 1 | 62 / 47 | 43 / 25 | 5 / 4 | 123 / 89 |
| liquidity | 3 / 2 | 2 / 2 | 26 / 22 | 19 / 11 | 5 / 5 | 55 / 42 |
| model | 6 / 5 | 5 / 4 | 56 / 40 | 61 / 40 | 15 / 8 | 143 / 97 |
| risk | 5 / 4 | 5 / 4 | 37 / 30 | 19 / 12 | 27 / 25 | 93 / 75 |
| structure | 13 / 12 | 8 / 7 | 79 / 55 | 56 / 30 | 3 / 2 | 159 / 106 |
| time | 4 / 3 | 6 / 6 | 51 / 36 | 25 / 15 | 4 / 2 | 90 / 62 |
| **all** | **43 / 38** | **27 / 24** | **311 / 230** | **223 / 133** | **59 / 46** | **663 / 471** |

### Verdicts by voice (readings / concepts)

| voice | EDGE | NEGATIVE | NULL | UNDERPOWERED | UNTESTABLE | total |
|---|---:|---:|---:|---:|---:|---:|
| own (TTrades) | 38 / 33 | 17 / 16 | 234 / 160 | 151 / 80 | 30 / 22 | 470 / 311 |
| guest | 5 / 5 | 10 / 8 | 77 / 70 | 72 / 53 | 29 / 24 | 193 / 160 |

All 9 verifier survivors and all 5 BH survivors are **own voice**. Guest concepts produced 5 raw
EDGEs, and every one was refuted. Guests produced proportionally more NEGATIVEs (10 of 193 vs 17 of 470) and more
UNTESTABLEs, mostly sizing, prop-firm and other-instrument advice.

**The modal result is a powered NULL.** 311 readings (47%) had enough data to see a 0.10R effect,
or the rate-test threshold, and saw none.

## 3. Every EDGE, with verification and q_BH

Diff is real minus control (trade tests), gated minus complement (gate tests), or observed minus null (rate
tests). The CI is the widest component. The *final* column is the outcome after verification and the deep dive.

| concept | rd | cat / voice | test | n | diff [CI] | q_BH | Holm | verification | final |
|---|---|---|---|---:|---|---:|:---:|---|---|
| `aggressive-run-hammer-signature` | – | structure / own | trade | 64,574 | +0.047 [+0.036, +0.059] R | <0.001 | ✓ | upheld (2/2) | **ARTEFACT** |
| `daily-profile-session-windows` | – | time / own | rate | 2,718 | +12.07 [+10.47, +13.69] pp | <0.001 | ✓ | upheld (2/2) | **DESCRIPTIVE_ONLY** |
| `cheat-code-entry` | – | entry / own | trade | 62,457 | +0.078 [+0.065, +0.091] R | <0.001 | ✓ | upheld (2/2) | **ARTEFACT** |
| `fvg-three-levels` | – | entry / own | rate | 34,790 | +0.96 [+0.40, +1.53] pp | 0.015 | – | upheld (2/2) | **DESCRIPTIVE_ONLY** |
| `point-of-interest` | a | entry / own | gate | 6,429 | +0.095 [+0.032, +0.161] R | 0.049 | – | upheld (2/2) | **DESCRIPTIVE_ONLY** |
| `balanced-price-range-overlap` | a | structure / own | trade | 16,595 | +0.024 [+0.005, +0.043] R | 0.11 | – | upheld (2/2) | candidate (fails BH) |
| `intraday-reversal` | – | model / own | rate | 1,584 | +3.36 [+0.77, +6.06] pp | 0.11 | – | upheld (2/2) | candidate (fails BH) |
| `no-shorting-below-lows` | b | entry / own | gate | 4,393 | −0.038 [−0.070, −0.005] R | 0.16 | – | upheld (2/2) | candidate (fails BH) |
| `inversion-fair-value-gap` | b | structure / own | trade | 22,252 | +0.018 [+0.001, +0.034] R | 0.20 | – | upheld (2/2) | candidate (fails BH) |
| `est-timezone-anchor` | a | time / own | rate | 2,682 | +10.12 [+8.03, +12.86] pp | <0.001 | ✓ | refuted (faithfulness) | refuted |
| `est-timezone-anchor` | b | time / own | rate | 2,688 | +24.39 [+21.64, +27.22] pp | <0.001 | ✓ | refuted (faithfulness) | refuted |
| `target-liquidity-and-imbalances` | b | risk / own | rate | 49,990 | +1.81 [+1.40, +2.20] pp | <0.001 | ✓ | refuted (faithfulness) | refuted |
| `trend-entry-options` | – | entry / own | trade | 8,174 | +0.088 [+0.053, +0.122] R | <0.001 | ✓ | refuted (2/2) | refuted |
| `gap-direction-fade-rule` | a | entry / guest | rate | 2,128 | +4.58 [+2.35, +6.71] pp | <0.001 | ✓ | refuted (faithfulness) | refuted |
| `failure-swing` | b | structure / own | rate | 59,067 | +0.89 [+0.44, +1.33] pp | 0.0019 | – | refuted (faithfulness) | refuted |
| `failure-to-displace` | a | structure / own | trade | 82,574 | +0.042 [+0.020, +0.068] R | 0.010 | – | refuted (faithfulness) | refuted |
| `dont-trade-after-expansion` | b | entry / own | gate | 29,837 | −0.027 [−0.043, −0.011] R | 0.014 | – | refuted (faithfulness) | refuted |
| `sons-model` | – | model / own | trade | 15,957 | +0.027 [+0.012, +0.043] R | 0.014 | – | refuted (2/2) | refuted |
| `trading-without-structure-shift` | a | entry / own | trade | 2,606 | +0.081 [+0.030, +0.132] R | 0.028 | – | refuted (2/2) | refuted |
| `volume-imbalance` | – | structure / own | trade | 14,958 | +0.039 [+0.013, +0.064] R | 0.035 | – | refuted (2/2) | refuted |
| `poi-density-by-timeframe` | – | entry / own | gate | 6,424 | +0.096 [+0.032, +0.159] R | 0.041 | – | refuted (faithfulness) | refuted |
| `deviation-close-continuation` | a | model / guest | rate | 2,823 | +2.80 [+0.84, +4.74] pp | 0.056 | – | refuted (2/2) | refuted |
| `propulsion-block` | b | structure / own | trade | 9,016 | +0.046 [+0.014, +0.078] R | 0.060 | – | refuted (2/2) | refuted |
| `harder-target-behind-protected-swing` | – | risk / own | rate | 21,898 | −0.99 [−1.69, −0.26] pp | 0.069 | – | refuted (2/2) | refuted |
| `internal-range-liquidity` | a | liquidity / own | rate | 6,277 | +1.82 [+0.39, +3.16] pp | 0.095 | – | refuted (2/2) | refuted |
| `po3-four-hour-opening-times` | a | time / own | trade | 1,091 | +0.079 [+0.018, +0.138] R | 0.095 | – | refuted (faithfulness) | refuted |
| `advanced-market-structure-labeling` | a | structure / own | trade | 86,190 | +0.010 [+0.002, +0.017] R | 0.11 | – | refuted (faithfulness) | refuted |
| `propulsion-block` | a | structure / own | trade | 9,523 | +0.035 [+0.007, +0.064] R | 0.14 | – | refuted (2/2) | refuted |
| `average-daily-range` | b | risk / own | gate | 28,458 | +0.040 [+0.005, +0.076] R | 0.18 | – | refuted (2/2) | refuted |
| `gb-range-return-entry` | – | entry / guest | trade | 1,931 | +0.051 [+0.005, +0.097] R | 0.18 | – | refuted (2/2) | refuted |
| `internal-range-liquidity` | b | liquidity / own | rate | 6,277 | +1.55 [+0.12, +2.86] pp | 0.18 | – | refuted (2/2) | refuted |
| `mitigation-block` | a | entry / own | trade | 25,934 | +0.022 [+0.003, +0.043] R | 0.18 | – | refuted (2/2) | refuted |
| `no-fading-the-daily-candle` | a | model / own | gate | 21,392 | +0.031 [+0.004, +0.060] R | 0.18 | – | refuted (2/2) | refuted |
| `order-block` | b | structure / own | trade | 2,605 | +0.053 [+0.006, +0.100] R | 0.18 | – | refuted (implementation) | refuted |
| `breaker-block` | a | entry / own | trade | 6,111 | +0.042 [+0.003, +0.081] R | 0.19 | – | refuted (faithfulness) | refuted |
| `average-daily-range` | a | risk / own | gate | 28,661 | +0.039 [+0.003, +0.075] R | 0.20 | – | refuted (2/2) | refuted |
| `mechanical-trade-management` | a | risk / guest | trade | 3,344 | +0.046 [+0.003, +0.089] R | 0.20 | – | refuted (2/2) | refuted |
| `fractal-model-c2` | a | model / own | trade | 3,584 | +0.029 [+0.002, +0.056] R | 0.21 | – | refuted (2/2) | refuted |
| `breakaway-gap-anticipation` | – | liquidity / guest | rate | 5,704 | −1.12 [−2.24, −0.11] pp | 0.22 | – | refuted (2/2) | refuted |
| `fair-value-gap` | b | structure / own | rate | 11,930 | +0.99 [+0.04, +1.98] pp | 0.23 | – | refuted (2/2) | refuted |
| `no-fading-the-daily-candle` | b | model / own | gate | 13,600 | +0.027 [+0.000, +0.054] R | 0.24 | – | refuted (faithfulness) | refuted |
| `opposing-run` | – | structure / own | gate | 8,898 | +0.041 [+0.000, +0.083] R | 0.24 | – | refuted (faithfulness) | refuted |
| `old-high-low-three-outcomes` | – | structure / own | trade | 2,561 | +0.051 [+0.001, +0.103] R | 0.25 | – | refuted (2/2) | refuted |

### Why the 34 refuted EDGEs fell

Each refuted EDGE is counted once, under its primary cause. The one-line reason for each is in the CSV `summary` column.

| cause | n | readings |
|---|---:|---|
| **generic stop geometry or limit-fill emulation.** A placebo with the same mechanics and no concept gives the same edge, or the edge sits in stops under $0.30 | 10 | gb-range-return-entry, mitigation-block a, trend-entry-options, volume-imbalance, breaker-block a, target-liquidity-and-imbalances b, advanced-market-structure-labeling a, propulsion-block a/b, failure-to-displace a |
| **time-of-day not held fixed** (trap 9). The effect goes NULL once the control keeps the NY clock (±30 min) | 7 | order-block b, po3-four-hour-opening-times a, internal-range-liquidity a/b, sons-model, average-daily-range a/b |
| **rate null not matched on volatility or state.** A mirror target or vol-matched null is hit just as often | 5 | fair-value-gap b, deviation-close-continuation a, harder-target-behind-protected-swing, breakaway-gap-anticipation, gap-direction-fade-rule a |
| **tested a different claim from the concept** | 5 | est-timezone-anchor a/b, poi-density-by-timeframe, dont-trade-after-expansion b, mechanical-trade-management a |
| **knife-edge parameter or 4H grid.** Neighbouring values or the futures grid are NULL | 4 | opposing-run, failure-swing b, fractal-model-c2 a, no-fading-the-daily-candle b |
| **locked control draw was unusually favourable** | 3 | old-high-low-three-outcomes, trading-without-structure-shift a, no-fading-the-daily-candle a |

The first two rows are **harness blind spots**, not tester errors. The matched control copies the stop
*distance* but places it at an arbitrary price. Rate nulls default to random moments that are
not matched on clock or volatility. Section 7 carries both into the bounds.

## 4. The five deep dives

All five are own-voice. None of them is tradeable.

### `cheat-code-entry` — ARTEFACT
Fade the last opposing 15m candle in an aggressive trend, with the stop at its extreme and a 2R target.

- **Harness result:** +0.078R [+0.065, +0.091] on 62,457 trades. The concept's own net avg R is −0.020 (gross +0.020).
- **Structural controls:** these place the control's stop at a fresh structural extreme at the same distance
  (10% bins, ±30 days, own trades excluded, 5 reps). They leave only **+0.012 to +0.030R**:
  - prior 1–3 candle extremes with random direction: +0.019, H1 +0.003;
  - the exact geometry without the trend: +0.030;
  - the same plus a matched NY hour: +0.024, with B2 −0.006;
  - k = 2–3 only: +0.012 [−0.001, +0.025].
- Every structural residual is 3–8× below the 0.10R threshold. It is ~0 in 2019–20 and negative in 2024 under every control.
- **Cost kills it.** The median stop is 0.435 pt (deciles 0.09 / 0.44 / 1.84 pt). A realistic spread of 0.25 / 0.30 / 0.35 pt gives a
  mean net of **−1.93 / −2.32 / −2.71R**. Even the widest-stop quintile nets −0.15R.
- **No tradeable version found:**
  - Stop floors of ≥2 pt net −0.064R and ≥3 pt net −0.001R.
  - A ≥5 pt floor nets +0.011R on n=1,131 (SE ≈ 0.04), no better than the trend-free fade null.
  - ATR-widened stops beat the null by only 0.006–0.012R gross and are negative net.

### `aggressive-run-hammer-signature` — ARTEFACT
A 5m candle that pokes the 20-bar extreme and closes back inside with a hammer or shooter wick, traded as a fade with the stop at the wick and a 2R target.

- **Harness result:** +0.047R (+0.040 with ties scored 50/50) on 64,574 trades. Gross +0.022R, harness net −0.018R.
- **Structural controls,** cell-matched on year × risk decile × NY 3h bucket × direction:
  - S1, own-bar wick stop with random direction: +0.037;
  - S2, last 1–3 bars' extreme: +0.024;
  - S3, a **generic 3-bar mini-sweep, faded, stop at the wick**: **+0.010 [−0.001, +0.020]**.
- **Against S3 the effect is in 2016–20 only:** H1 +0.031, H2 **−0.007**, B3 −0.013, B4 −0.006.
- The 20-bar range edge and the wick shape add nothing measurable after 2021.
- **Cost:** stops are median 0.59 pt (p10 0.165 pt). At risk ≥2 pt gross is −0.0005R and net is −0.08 to −0.11R.
  Every stop-distance decile is net negative at a 0.25–0.35 pt spread.

### `point-of-interest` (reading a) — DESCRIPTIVE_ONLY
The POI gate on the 1h CISD book: pass vs fail.

- **Harness result:** +0.095R [+0.032, +0.161], 6,429 gated vs 1,566 complement. The 50/50 tie re-score changes nothing.
- **The gate split survives structural controls** (+0.10 to +0.12R, p 0.001–0.006), and it is concept-specific.
  The same gate applied to random structural books gives −0.002 and −0.008.
- **It is a negative filter.**
  - 99.8% of the fail group are CISDs whose extreme is *not* the range extreme (a higher low or lower high). That group runs
    adj −0.062R with a 41.5% stop rate.
  - The fallback branch passes 100% of its events. Scoring it as a fail gives NULL.
  - The gated arm beats structural controls by only +0.007 to +0.034 (2 of 4 variants have a CI including 0).
- **Fragile:**
  - B1 (2016–18) ≈ 0.
  - 4 of 11 years are negative.
  - The H1 CI includes 0.
  - BH q = 0.049; Holm fails.
- **Cost:** the gated book is gross +0.042R [+0.015, +0.067] and net −0.009R at 0.30 pt (median stop $7.10). The complement nets −0.12R.
- **What it says:** avoid 1h CISDs fired off a non-extreme higher low or lower high. It is not a book to trade.

### `daily-profile-session-windows` — DESCRIPTIVE_ONLY
The claim: the day's high or low forms in London 02–05 NY or NY 08:30–12.

- **Rate result:** 37.4% vs 25.3% under a block-shift null. That is +12.1pp on 2,718 days, positive in all four blocks.
- **Most of it is volatility.** A **volatility-only null** (each day's own M1 moves with random signs) puts the extremes in those windows
  33.7% of the time vs 35.5% observed. **That explains 83% of the lift.**
- **The residual is +1.8pp [+0.5, +3.1]** and it fades by block: +3.1, +2.1, +1.5, +0.2pp. 2022 is −2.9pp.
  London's residual is +0.1pp; all of the residual is in the NY window.
- **No trade works:**
  - Fading fresh day extremes inside the windows does *worse* than a structure-matched random control (−0.004 to −0.021R).
  - The harness gate reads NEGATIVE on 5m rr1 (−0.033R), agreeing with phase 2's NY AM result (−0.057R).
  - Betting at window end that the window's extreme holds ranks inside the spread of 16 placebo windows (z −0.46 to +0.97).
  - Everything is gross ≈ 0 and net −0.08 to −0.38R at 0.30 pt.
- **What it says:** extremes form where gold moves most (the 08:00–11:00 NY releases and open). That is useful for *when to
  watch*, not for an entry.

### `fvg-three-levels` — DESCRIPTIVE_ONLY
After a 15m FVG's first return, does price reach the leg extreme before a 15m close beyond the far edge?

- **Rate result:** 39.8% vs 38.9% (+0.96pp, n=34,784).
- **This one is not a generic effect.** It **survives structural controls:**
  - time-of-day matched: +1.02pp;
  - structure-placed stop at matched distance: +1.05pp;
  - random direction: +0.78pp;
  - structural stop *and* target: **+1.80pp [+1.23, +2.39]**.
- It holds in both halves under every control. It is zero for gaps with stops under 0.3 pt and +2.5pp at stops ≥2 pt.
  Against the structural-stop control, B1 ≈ 0.
- **No trade survives:**
  - The natural trade (enter on touch, target the leg extreme) is −0.03R against the structural-stop control.
  - The only variant that beats the control (1R target, hard stop, stops ≥1 pt: +0.037R) was picked from 12 or more tried.
  - The median stop is 0.655 pt, so a 0.30 pt spread costs ≈ 0.46R per trade.
  - Even at stops of 3–5 pt, the best book goes from gross +0.052R to net −0.016 / −0.043R.

### What the deep dives teach beyond the five concepts
1. **The matched control rewards any stop placed just beyond a fresh extreme.** M1 noise reaches a
   level that just held less often than it reaches an arbitrary level at the same distance. Every trade EDGE with
   a wick or candle-extreme stop should be re-measured against a *structural* control before anyone believes it.
2. **Stops under ~1 pt are not tradeable on XAUUSD.** A 0.25–0.35 pt spread is 0.3–3R on them. The harness's
   flat 0.04R cost hides this, and because cost cancels in the differential, **no `diff` in this campaign says anything
   about net profitability.**
3. **"Rate EDGE" results need a volatility-matched null.** A null that matches only distance and regime counts
   "price moves more after X" as "price goes where the concept says".

## 5. What the NEGATIVE results say (concepts that hurt)

27 readings came back NEGATIVE: the CI excludes 0 **against** the claim. They were not sent to adversarial verification,
so only the 6 that pass BH should be relied on. Two of those also pass Holm.

| concept | rd | cat / voice | test | n | diff [CI] | q_BH | Holm |
|---|---|---|---|---:|---|---:|:---:|
| `session-open-volume-nyse` | a | time / own | rate | 2,716 | −16.27 [−19.37, −13.18] pp | <0.001 | ✓ |
| `strat-scalping-hour-two-filter` | a | time / guest | gate | 38,886 | −0.044 [−0.061, −0.027] R | <0.001 | ✓ |
| `average-daily-range-targeting` | b | risk / own | rate | 334 | −13.11 [−19.58, −5.75] pp | 0.0043 | – |
| `consolidation-open-whipsaw` | b | model / own | rate | 1,525 | −2.31 [−3.58, −1.00] pp | 0.0093 | – |
| `ten-am-candle-alignment` | b | time / own | rate | 8,966 | −1.78 [−2.85, −0.68] pp | 0.021 | – |
| `liquidity-sweep-vs-consolidation` | – | liquidity / own | gate | 4,020 | −0.057 [−0.096, −0.019] R | 0.046 | – |
| `trend-by-previous-day-extremes` | – | structure / own | rate | 1,328 | −4.22 [−7.29, −1.23] pp | 0.067 | – |
| `range-edge-trading` | – | model / own | gate | 523 | −0.157 [−0.270, −0.041] R | 0.073 | – |
| `orderflow-tight-stop-profile` | – | risk / guest | trade | 97,999 | −0.013 [−0.024, −0.003] R | 0.10 | – |
| `consolidation-avoidance` | b | model / own | gate (claim −) | 7,069 | +0.041 [+0.010, +0.074] R | 0.12 | – |
| `no-draw-no-trade` | b | risk / guest | gate | 3,776 | −0.064 [−0.113, −0.011] R | 0.12 | – |
| `htf-poi-gate-before-ltf` | a | risk / own | gate | 21,022 | −0.034 [−0.061, −0.006] R | 0.13 | – |
| `monday-range-marker` | b | time / guest | trade | 354 | −0.318 [−0.570, −0.043] R | 0.15 | – |
| `htf-narrative-floor-fifteen-minute` | – | time / guest | gate | 6,303 | −0.042 [−0.079, −0.009] R | 0.15 | – |
| `previous-period-high-low` | a | liquidity / own | rate | 5,336 | −1.76 [−3.27, −0.35] pp | 0.15 | – |
| `three-candle-outcomes` | – | structure / own | rate | 2,717 | −1.78 [−3.25, −0.27] pp | 0.15 | – |
| `consolidation-avoidance` | a | model / own | gate (claim −) | 4,982 | +0.044 [+0.005, +0.081] R | 0.16 | – |
| `rr-gated-entry-refinement` | – | entry / own | trade | 22,230 | −0.028 [−0.052, −0.003] R | 0.17 | – |
| `daily-close-only-bias` | – | structure / guest | gate | 1,133 | −0.093 [−0.177, −0.011] R | 0.18 | – |
| `fomc-day-participation` | b | time / own | trade | 1,011 | −0.083 [−0.155, −0.008] R | 0.18 | – |
| `intermediate-timeframe-bridge` | b | structure / own | gate | 148,806 | −0.009 [−0.017, −0.001] R | 0.18 | – |
| `proximity-bias-nearest-extreme` | – | model / own | rate | 1,021 | −7.37 [−13.53, −0.34] pp | 0.18 | – |
| `three-drive-reversal-pattern` | a | structure / guest | trade | 244 | −0.209 [−0.399, −0.016] R | 0.19 | – |
| `trade-away-from-manipulation` | – | structure / guest | gate | 8,384 | −0.030 [−0.058, −0.002] R | 0.20 | – |
| `mechanical-trade-management` | b | risk / guest | trade | 10,304 | −0.012 [−0.023, −0.001] R | 0.22 | – |
| `cross-asset-target-transfer` | a | structure / own | trade | 643 | −0.084 [−0.164, −0.002] R | 0.22 | – |
| `three-drive-reversal-pattern` | b | structure / guest | gate | 244 | −0.180 [−0.360, −0.001] R | 0.24 | – |

**The multiplicity-robust ones:**

- **On gold, 09:30 NY is the volatility step and 08:30 is not the bigger one** (`session-open-volume-nyse a`, Holm).
  A step-up at 08:30 happens 57.4% of the time vs 73.6% at 09:30. The corpus rule "forex-class instruments use 08:30, drop 09:30" is backwards
  for XAUUSD. On NFP days 08:30 does step (97.6%), but that reading had only n=123.
- **Buying the extension hurts** (`strat-scalping-hour-two-filter a`, Holm). A 5m CISD taken while the in-progress hour is
  already a "2" in the trade direction does −0.044R worse than one taken in an inside hour.
- **Volatility clusters** (`average-daily-range-targeting b`). After a day with more than 1.5× ADR, the next day is below ADR only 43% of
  the time vs 56% for matched days. "Expect a smaller day" is wrong.
- **Rotation is rarer than chance** (`consolidation-open-whipsaw b`). Both pre-open extremes are taken on 5.9% of days vs 8.2% under the null.
- **The 4H-flip retracement to the prior body midpoint is *less* likely than the null** (`ten-am-candle-alignment b`, 33.7% vs 35.5%).
- **V-shaped sweeps do worse than lethargic ones** (`liquidity-sweep-vs-consolidation`, −0.057R). This is the opposite of the claim.

**The weaker ones share a theme.** Several "draw on liquidity" claims lean the wrong way:

- PDH/PDL are reached slightly *less* often than an arbitrary level at the same distance
  (`previous-period-high-low a` −1.8pp, `three-candle-outcomes` −1.8pp, `trend-by-previous-day-extremes` −4.2pp).
- The nearer monthly extreme is not taken first (`proximity-bias-nearest-extreme` −7.4pp).

Several confirmation and stacking filters also do worse than their complement:

- `htf-poi-gate-before-ltf`, `no-draw-no-trade b`, `daily-close-only-bias`, `intermediate-timeframe-bridge b`,
  `htf-narrative-floor-fifteen-minute`, `range-edge-trading`.

One verifier-upheld EDGE belongs with these. `no-shorting-below-lows b` (claim −) confirms that shorting a 15m CISD at the running day low
does worse (−0.038R, all 4 blocks negative), but its q is 0.16.

Note that `consolidation-avoidance` a/b is a NEGATIVE because inside-day and inside-4H gates made trades *better*, against the concept's claim. The concept says to avoid those days.

## 6. UNTESTABLE — 59 readings, grouped

| reason | readings |
|---|---:|
| **sizing, capital or prop-firm arithmetic.** R outcomes do not change with size (position-sizing ×2, house-money, incremental-size-scaling, prop-firm ×4, compounding, loss-streak, no-size-reduction, stop-moves-when-adding a/b, stop-size-reduction b) | 14 |
| **definitional, UI or no claim about price** (chart settings, TradingView workspace, contract specs, trading hours, excluded-tooling list, toolkit inventory, trade frequency, the four-candle labelling convention, the "weekly profile is not predicted" posture, SMT two-chart layout) | 10 |
| **another instrument or vehicle** (ES/NQ/BTC, currency futures, DXY/yields, futures-vs-forex fills, futures-vs-stocks gaps, contract rollover) | 10 |
| **n < 30 events in 10.5 years** (consolidation-reversal-week a/b, intraweek-reversal-week a, mmxm-phase-sequence a/b, nfp-week-protocol b, tgif-setup a/b) | 8 |
| **order flow, volume, DOM or footprint** (none of these exists for spot XAUUSD OHLC) | 5 |
| **options pricing** (0DTE strikes, expiry 3× rule, options proxy) | 3 |
| **execution mechanics** (OCO bracket, market vs stop order, stop fill guarantee) | 3 |
| **underspecified or paywalled** (dealing-range fib anchors, market-maker curve phases, TTFM indicator conditions) | 3 |
| **sub-minute bars** (fifteen-second execution b) | 1 |
| **economic calendar** (news-impact-tiering a: first red-folder event of each week) | 1 |
| **tie rule.** Stop-first scoring gives EDGE and 50/50 scoring gives UNDERPOWERED (`lack-of-displacement-entry`, 1m stops, 9.6% vs 12.1% ambiguous) | 1 |

Only the last four groups (calendar, sub-minute, order flow, n < 30) could become testable with data this workspace does not have.
The first three groups make no claim about price that any dataset could decide.

## 7. UNDERPOWERED — the candidates worth more data

223 readings are UNDERPOWERED. Most of them are rare setups with MDEs of 0.2–1.0R. Below are the readings whose CI already
excludes 0 in the claimed direction with both halves agreeing, but which fell short of the power floor.
**None was verified, deep-dived or cost-tested.** Section 4 shows that trade diffs of this size
routinely shrink by 60–85% against a structural control, so treat these as leads only.

| concept | rd | test | n | diff [CI] | q_BH | H1 / H2 | why it is underpowered |
|---|---|---|---:|---|---:|---|---|
| `failure-to-manipulate` | – | trade | 1,400 | +0.129 [+0.044, +0.198] R | 0.017 | +0.170 / +0.072 | MDE 0.110 vs 0.10; needs ~1,700 events |
| `htf-two-entry-opportunities` | a | gate | 467 | +0.232 [+0.087, +0.371] R | 0.021 | +0.262 / +0.205 | 4H: taps 1–2 vs 3+; MDE 0.20 |
| `daily-wick-confirmation-timeframes` | b | trade | 2,514 | +0.133 [+0.027, +0.238] R | 0.12 | +0.145 / +0.122 | MDE 0.151; needs ~5,700 |
| `news-impact-tiering` | b | rate | 195 | +10.6 [+3.4, +17.9] pp | 0.050 | +9.7 / +11.3 | NFP/FOMC days only; needs a calendar |
| `new-york-intraday-time-levels` | b | rate | 2,651 | +6.6 [+5.3, +7.9] pp | <0.001 | +5.4 / +7.5 | the rate threshold shrinks to 1pp at a 4% base rate (harness note); the 09:30–10:00 extreme share is 10.6% vs 4.1%, the same volatility clock as `daily-profile-session-windows` |
| `large-range-day-targeting` | – | rate | 508 | +5.2 [+0.6, +9.4] pp | 0.16 | +7.2 / +3.3 | MDE 6.3pp |
| `order-block-probability-grading` | – | gate | 3,788 | +0.080 [+0.000, +0.154] R | 0.22 | +0.106 / +0.058 | MDE 0.110 |
| `silver-bullet-breaker-requirement` | a | gate | 1,223 | +0.107 [+0.003, +0.212] R | 0.24 | +0.175 / +0.052 | MDE 0.150 |
| `clean-day-criteria` | – | trade | 174 | +0.353 [+0.031, +0.668] R | 0.18 | +0.463 / +0.246 | n=174; MDE 0.46 |
| `tgif-setup` | a | (UNTESTABLE, n=17) | 17 | +0.55R | 0.033 | – | weekly-profile rarity |

Two structural facts limit what more gold data can do:

- **Weekly, TGIF and intraweek profiles give only 4–335 events in 10.5 years.** Another decade of gold does not fix that.
  Only other instruments can (harness note model_own_03a).
- **The corpus's preferred 15m/1m SMT and the ES/NQ concepts need data the workspace does not hold.**
  Every SMT test here was on XAG H1.

The practical ranking is:

1. `failure-to-manipulate` and `htf-two-entry-opportunities a`. Both are cheap to verify (two-lens) and to re-measure against a structural control. Both have
   q < 0.05 already, and stops at the 1h/4H scale, where spread costs little.
2. The news readings, which need an economic calendar before anything else.

## 8. Harness notes — 208, grouped, and how they bound the conclusions

The testers filed 208 notes on the harness. Grouped by theme, with how each theme bears on the conclusions:

| theme | notes | effect on conclusions |
|---|---:|---|
| **no native limit-order entry.** Resting limits are emulated as "first M1 touch, then next M1 open"; fills whose bar trades through the stop are dropped or re-anchored | 8 | Every limit-entry concept (OTE, breaker, unicorn, propulsion, mitigation and order blocks, GB levels) was scored on a proxy. Verification showed this emulation itself **creates** EDGEs (propulsion-block a/b, mitigation-block a, gb-range-return-entry). Limit-entry concepts are neither confirmed nor refuted. |
| **no trade management.** No partial exits, break-even, trailing stops or signal exits; one fixed stop and target per row | 8 | Management concepts (80/20 partials, BE-then-run, trail-market-structure, "cut if the 5m fails") were tested only through premise proxies. `mechanical-trade-management a` was refuted for exactly this reason. |
| **control and null design.** Stop-geometry confound, rate nulls not ToD- or volatility-matched, ties | 13 | The largest source of false EDGEs (§3: 22 of 34 refutations come from control or null design). A NULL can hide an effect that a better control would uncover. An EDGE can be generic. |
| **ctrl_overlap on fixed-clock or frequent books.** A ToD-matched control on once-a-day clock books draws the concept's own trades | 9 | Forces UNDERPOWERED by construction for 18:00 and 17:00 NY decision books and for signals that fire on most bars (swing points, STRAT 2s). |
| **wall-clock holds across halts** (trap 7 exposure reruns) | 7 | Handled with `hold_basis="bars"`, but some reruns cost extra ledger entries. |
| **missing data: economic calendar** | 7 | News concepts used only rule-derived NFP dates and hand-typed FOMC dates (~83–123 days), always below the effective-n floor. |
| **missing data: correlates** (XAG and EURUSD H1 only; no DXY, ES/NQ or GBPUSD; probe cannot see external files) | 16 | Every SMT/PSP result is an **H1 silver** result, not the corpus's 15m/1m, GC-based version. Correlate look-ahead safety rests on construction, not on the probe. |
| **missing data: volume and sub-minute** | 2 | Volume-profile concepts used a TPO stand-in or were declared UNTESTABLE. |
| **rarity and power rules** (n < 30, rate threshold at low base rates, NEGATIVE without a power requirement) | 8 | Rare weekly or news setups cannot reach a verdict on gold. A NEGATIVE with MDE 0.38 (`monday-range-marker b`) is weak. |
| **result schema** (gate `n` is the gated arm only, `gate_firing_rate` naming, p vs widest-CI mismatch in one case) | 21 | Cosmetic. The CSV `n` for a gate row is the gated arm. |
| **probe, timestamp and API traps** (trading_day labels, nominal close_time vs last M1, `open_at` at the query time, µs vs ns, feed noise at candle boundaries in 2016–18, reopen gap artefacts) | 40 | The probe caught these in testers' own code before any verdict. Feed noise at candle boundaries explains `volume-imbalance`, and it bounds every sub-$0.40 stop in 2016–18. |
| **cache fingerprint staleness** (helper-module edits not seen) | 4 | Caught by the probe; no written result affected. |
| **ledger and multiplicity hygiene** (reruns after write refusals, duplicated hypotheses, pre-verdict bug fixes, correlated readings) | 35 | Duplicates inflate the 864-hypothesis family slightly, which is conservative. No tester re-ran a reading to change its verdict. |
| **no fault found / informational** (shared batch helpers, clean batches) | 30 | – |

## 9. Bounds — state these whenever citing this campaign

- **One instrument.** XAUUSD spot (OANDA mid), with nothing out of sample on another market.
- **2016-01 → 2026-07, M1 only.** Pre-2016 data is disqualified. There are no sub-minute bars, no volume and no bid/ask.
- **No sustained bear market** in the span. Gold went from about 1,050 to 5,500 and volatility roughly tripled. No conclusion is validated
  against a gold downtrend.
- **Cost is not modelled realistically.** There is a flat 0.04R, and it cancels in every `diff`. Section 4 shows that realistic spread
  dominates any setup with a stop under ~1–2 pt.
- **Execution is idealised the other way too.** Stop-first ties are pessimistic. Limit orders and management are not modelled.
- **Controls are matched on distance, regime and (optionally) clock, not on stop placement or local volatility.**
  That flatters trade setups with stops behind fresh extremes, and rate claims made right after large moves.
- **One reading per contested interpretation, sometimes two.** A NULL refutes the reading tested, not every possible
  reading of the concept.
- **The phase-3 bounds still apply.** The paywalled C2/C3/C4 conditions mean any TTFM-model result tests a reconstruction.

## 10. Files

| file | content |
|---|---|
| `concept_campaign/concept_verdicts.csv` | one row per reading (663): category, voice, test, verdict, n, diff, CI, p, q_BH, Holm, verification, deep-dive label, one-line summary, result and script paths |
| `concept_campaign/build_concept_verdicts.py` | builds the CSV from the campaign JSON; the post-verification one-liners live here |
| `concept_campaign/campaign_raw.json` / `campaign_adjusted.json` | tester rows, verification votes, harness notes / Holm-BH family |
| `concept_campaign/results/` · `tests/<batch>/` · `verify/` · `deepdive/` | 663 results · 61 batches of scripts · 76 verifier workspaces · 5 deep dives |
| `concept_campaign/review_lookahead/` · `review_statistics/` · `calibration.json` | the harness review (look-ahead attacks, false-EDGE rate, calibration) |
