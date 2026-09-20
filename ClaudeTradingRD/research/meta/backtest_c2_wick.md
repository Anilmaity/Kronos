# C2 sweeping-wick size — a real backtest

Data: `m3_scalper/xau_m1_3y.parquet`, 1,074,472 M1 bars, 2023-07-02 to 2026-07-23, UTC. Offline.

## Methodology

Signal: `detectors.fractal.c2_events(sweep_ref='prior_candle')` — the candle sweeps the prior candle's extreme, closes back inside it, and closes in the reversal direction. Entry is that candle's close, direction is the C2 direction (swept the low -> long).

Stop is the swept extreme itself (the C2 low for a long), which is what the corpus prescribes. Risk `R` = |entry - stop|. Targets: fixed multiples 1R/2R/3R, and `structural` = the prior candle's opposite extreme (sweep the low, deliver to the high); trades whose structural target already sits behind the entry are dropped, not clipped.

**Every trade is resolved on M1 bars**, not on the signal timeframe. The window runs from the first M1 bar after the signal bar closes to 10 wall-clock multiples of the timeframe later; unresolved trades exit at the last M1 close in the window (`time`). **If stop and target are touched inside the same M1 bar the stop is taken** — M1 carries no intrabar order and assuming otherwise manufactures edge. A bar that opens through the stop fills at that open (gap risk paid); a bar that gaps through the target still fills at the level (gap gift refused).

Costs are a round-trip spread in USD/oz charged to P&L (0.0, 0.2, 0.5, 0.04R tested; 0.2 is the base case for XAUUSD). Entry at the exact signal close is optimistic and the cost knob is what absorbs it.

In-sample is everything before **2025-07-02** (two years), out-of-sample is the remainder (~one year). **Wick quintile edges are fitted on the in-sample trades only** and applied unchanged to the holdout, so the bucketing rule cannot see the holdout.

Trades overlap: consecutive bars can each be a C2 and no position cap is applied. That is fine for expectancy but means the drawdown column understates what a single-position account would feel.

**Two controls, because a win rate on its own is not evidence.** Section 6b pairs every C2 trade with five random-entry trades of identical geometry (same direction, same stop distance, same target distance, random entry time within +/-30 days) and reports the difference with a bootstrap CI. Section 6c re-resolves the identical book on signal-timeframe bars instead of M1, so the size of the resolution artefact is a number in this file rather than an assumption.

Both controls are here on the advice of `meta/external_crossref.md`. The relevant priors: a published FVG study (MPM Markets — 7 years, 4 futures markets, 3 timeframes, ~40k occurrences) found a same-family ICT construct real but only ~5 percentage points above a matched random baseline and with no tradeable edge after costs, and found that its one strongly profitable construction was an artefact of resolving exits on hourly bars — roughly 73% win rate at that resolution, about 50% at one minute. Marshall, Young & Rose (2006, *J. Banking & Finance* 30(8)) found candlestick strategies create no value once tested against bootstrapped controls. There is no peer-reviewed literature on ICT/SMC at all, and the C2 wick claim in particular is externally unattested — every outside hit traces back to the channel. This backtest is therefore the deciding test, which is a reason for more conservatism, not less.

## Sample sizes and quintile edges

| TF | C2 trades | IS | OOS | wick quintile edges (fitted IS) |
|---|---:|---:|---:|---|
| 15min | 20,000 | 13,138 | 6,862 | 0.210, 0.332, 0.454, 0.599 |
| 1h | 4,916 | 3,242 | 1,674 | 0.213, 0.334, 0.453, 0.594 |
| 4h | 1,367 | 920 | 447 | 0.208, 0.330, 0.449, 0.590 |
| 1D | 257 | 182 | 75 | 0.175, 0.294, 0.412, 0.556 |

## 0. The old statistic, replicated — and what it is worth

Left half replicates `fractal_reading_comparison.md`: how often the **next candle closed beyond the C2 open**, by wick quintile. Right half is the same trades measured target-free, as maximum favourable and maximum adverse excursion in R over the hold window. MFE/MAE is the honest version of the same question: if small-wick C2s expand, they must travel further in favour and less against, at every target.

`open gap R` is the distance from the entry back to the C2 open, in R — i.e. how much room the delivery test gives the trade before it fails. It is the control the old statistic never had.

| TF | bucket | n | delivered beyond C2 open | open gap R | mean MFE R | mean MAE R | median MFE R | MFE>=2R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 15min | Q1 smallest | 4,074 | 83.4% | 0.790 | 2.974 | 3.019 | 1.599 | 43.1% |
| 15min | Q2 | 3,975 | 77.0% | 0.582 | 3.098 | 2.926 | 1.876 | 47.8% |
| 15min | Q3 | 3,974 | 72.1% | 0.441 | 2.905 | 2.866 | 1.856 | 47.0% |
| 15min | Q4 | 3,991 | 65.4% | 0.308 | 2.770 | 2.740 | 1.797 | 45.8% |
| 15min | Q5 largest | 3,986 | 56.5% | 0.165 | 2.398 | 2.566 | 1.587 | 40.9% |
| 1h | Q1 smallest | 1,008 | 84.1% | 0.793 | 2.954 | 3.028 | 1.635 | 42.4% |
| 1h | Q2 | 990 | 75.7% | 0.569 | 3.252 | 3.404 | 1.749 | 45.7% |
| 1h | Q3 | 967 | 70.0% | 0.414 | 3.222 | 3.197 | 1.818 | 46.8% |
| 1h | Q4 | 1,005 | 64.5% | 0.310 | 2.836 | 2.880 | 1.825 | 47.1% |
| 1h | Q5 largest | 946 | 58.2% | 0.161 | 2.653 | 2.657 | 1.666 | 44.3% |
| 4h | Q1 smallest | 279 | 87.5% | 0.780 | 3.339 | 3.253 | 1.813 | 44.4% |
| 4h | Q2 | 272 | 76.5% | 0.585 | 2.836 | 2.751 | 1.757 | 46.3% |
| 4h | Q3 | 270 | 74.4% | 0.433 | 2.947 | 2.689 | 1.671 | 44.4% |
| 4h | Q4 | 266 | 68.0% | 0.296 | 3.128 | 2.518 | 1.951 | 48.5% |
| 4h | Q5 largest | 280 | 59.3% | 0.159 | 2.455 | 2.784 | 1.640 | 45.4% |
| 1D | Q1 smallest | 52 | 86.5% | 0.838 | 3.255 | 3.150 | 1.796 | 44.2% |
| 1D | Q2 | 55 | 81.8% | 0.613 | 3.126 | 3.217 | 1.989 | 49.1% |
| 1D | Q3 | 51 | 76.5% | 0.470 | 2.402 | 2.488 | 1.952 | 47.1% |
| 1D | Q4 | 52 | 71.2% | 0.350 | 3.280 | 2.334 | 1.996 | 50.0% |
| 1D | Q5 largest | 47 | 53.2% | 0.163 | 2.316 | 3.303 | 1.242 | 34.0% |

## 1. Expectancy in R by wick quintile (cost 0.2, full sample)

Cell = expectancy in R (win rate). A quintile is only interesting if it beats 0 after costs; the corpus predicts Q1 (smallest wick) is the good one and Q5 the bad one.

| TF | bucket | 1R | 2R | 3R | structural |
|---|---|---:|---:|---:|---:|
| 15min | Q1 smallest | -0.153 (48.1%) | -0.145 (35.4%) | -0.149 (30.9%) | -0.179 (49.3%) |
| 15min | Q2 | -0.126 (49.7%) | -0.102 (36.5%) | -0.075 (31.6%) | -0.131 (51.0%) |
| 15min | Q3 | -0.099 (50.8%) | -0.069 (37.4%) | -0.069 (32.1%) | -0.107 (53.0%) |
| 15min | Q4 | -0.105 (50.4%) | -0.108 (35.8%) | -0.098 (30.8%) | -0.125 (52.6%) |
| 15min | Q5 largest | -0.149 (47.7%) | -0.154 (34.2%) | -0.161 (29.6%) | -0.156 (53.6%) |
| 1h | Q1 smallest | -0.066 (49.2%) | -0.063 (36.9%) | -0.093 (31.4%) | -0.148 (51.8%) |
| 1h | Q2 | -0.085 (48.9%) | -0.091 (35.9%) | -0.037 (32.0%) | -0.050 (53.2%) |
| 1h | Q3 | -0.098 (48.2%) | -0.092 (35.1%) | -0.062 (30.6%) | -0.092 (52.0%) |
| 1h | Q4 | -0.056 (50.0%) | -0.085 (35.1%) | -0.115 (29.4%) | -0.076 (55.2%) |
| 1h | Q5 largest | -0.048 (50.8%) | -0.085 (35.6%) | -0.050 (32.0%) | -0.076 (58.0%) |
| 4h | Q1 smallest | 0.074 (54.8%) | 0.161 (44.4%) | 0.156 (38.7%) | 0.047 (56.8%) |
| 4h | Q2 | -0.014 (49.6%) | 0.099 (39.3%) | 0.179 (34.9%) | 0.033 (54.2%) |
| 4h | Q3 | -0.037 (49.3%) | 0.013 (38.5%) | 0.070 (34.8%) | -0.056 (52.8%) |
| 4h | Q4 | 0.073 (54.5%) | 0.154 (42.9%) | 0.130 (38.0%) | 0.044 (60.8%) |
| 4h | Q5 largest | 0.002 (51.1%) | 0.033 (37.1%) | 0.036 (31.8%) | -0.017 (59.9%) |
| 1D | Q1 smallest | -0.007 (50.0%) | 0.043 (38.5%) | 0.113 (36.5%) | -0.234 (38.9%) |
| 1D | Q2 | 0.024 (50.9%) | 0.019 (36.4%) | -0.098 (27.3%) | -0.037 (72.7%) |
| 1D | Q3 | 0.160 (58.8%) | 0.176 (43.1%) | 0.339 (41.2%) | -0.276 (48.0%) |
| 1D | Q4 | 0.144 (57.7%) | 0.306 (46.2%) | 0.412 (40.4%) | -0.011 (63.6%) |
| 1D | Q5 largest | -0.193 (42.6%) | -0.233 (29.8%) | -0.073 (29.8%) | -0.299 (41.5%) |

## 2. Full metrics — median wick split, in-sample vs out-of-sample (cost 0.2)

`small` = wick ratio at or below the in-sample median; `large` = above. `all` is every C2 regardless of wick, i.e. what you get if the wick claim is worthless.

| TF | target | sample | bucket | n | win | exp R | exp USD/oz | PF | maxDD R | mean R (USD) | time-exit |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15min | 1R | IS | small | 6,569 | 48.9% | -0.171 | -0.20 | 0.85 | 1129.1 | 2.55 | 5.5% |
| 15min | 1R | IS | large | 6,569 | 49.4% | -0.150 | -0.24 | 0.81 | 990.8 | 2.41 | 3.9% |
| 15min | 1R | IS | all | 13,138 | 49.2% | -0.161 | -0.22 | 0.83 | 2117.0 | 2.48 | 4.7% |
| 15min | 1R | OOS | small | 3,487 | 50.1% | -0.053 | -0.24 | 0.93 | 184.4 | 7.53 | 5.5% |
| 15min | 1R | OOS | large | 3,375 | 49.1% | -0.071 | -0.41 | 0.89 | 243.5 | 7.03 | 3.1% |
| 15min | 1R | OOS | all | 6,862 | 49.6% | -0.061 | -0.32 | 0.91 | 424.3 | 7.29 | 4.3% |
| 15min | 2R | IS | small | 6,569 | 36.5% | -0.142 | -0.12 | 0.92 | 979.8 | 2.55 | 13.1% |
| 15min | 2R | IS | large | 6,569 | 35.5% | -0.146 | -0.23 | 0.86 | 964.1 | 2.41 | 11.1% |
| 15min | 2R | IS | all | 13,138 | 36.0% | -0.144 | -0.17 | 0.89 | 1895.8 | 2.48 | 12.1% |
| 15min | 2R | OOS | small | 3,487 | 36.4% | -0.042 | -0.15 | 0.97 | 153.0 | 7.53 | 12.7% |
| 15min | 2R | OOS | large | 3,375 | 34.8% | -0.081 | -0.40 | 0.91 | 278.8 | 7.03 | 10.2% |
| 15min | 2R | OOS | all | 6,862 | 35.6% | -0.061 | -0.27 | 0.94 | 425.9 | 7.29 | 11.5% |
| 15min | 3R | IS | small | 6,569 | 31.7% | -0.129 | -0.08 | 0.95 | 897.6 | 2.55 | 19.0% |
| 15min | 3R | IS | large | 6,569 | 30.5% | -0.150 | -0.25 | 0.85 | 998.7 | 2.41 | 17.6% |
| 15min | 3R | IS | all | 13,138 | 31.1% | -0.139 | -0.17 | 0.90 | 1841.1 | 2.48 | 18.3% |
| 15min | 3R | OOS | small | 3,487 | 31.7% | -0.027 | -0.07 | 0.98 | 168.1 | 7.53 | 18.5% |
| 15min | 3R | OOS | large | 3,375 | 29.8% | -0.085 | -0.33 | 0.93 | 299.3 | 7.03 | 16.1% |
| 15min | 3R | OOS | all | 6,862 | 30.8% | -0.056 | -0.20 | 0.96 | 387.4 | 7.29 | 17.3% |
| 15min | structural | IS | small | 4,717 | 48.7% | -0.179 | -0.18 | 0.78 | 845.4 | 1.99 | 1.0% |
| 15min | structural | IS | large | 5,767 | 51.8% | -0.168 | -0.25 | 0.73 | 969.4 | 2.28 | 1.4% |
| 15min | structural | IS | all | 10,484 | 50.4% | -0.173 | -0.22 | 0.75 | 1814.6 | 2.15 | 1.2% |
| 15min | structural | OOS | small | 2,454 | 55.3% | -0.053 | -0.13 | 0.94 | 133.3 | 5.97 | 1.0% |
| 15min | structural | OOS | large | 2,987 | 55.2% | -0.087 | -0.43 | 0.84 | 265.4 | 6.58 | 1.2% |
| 15min | structural | OOS | all | 5,441 | 55.3% | -0.072 | -0.30 | 0.88 | 395.8 | 6.30 | 1.1% |
| 1h | 1R | IS | small | 1,621 | 47.7% | -0.117 | -0.50 | 0.81 | 190.7 | 5.49 | 8.9% |
| 1h | 1R | IS | large | 1,621 | 50.2% | -0.073 | -0.01 | 0.99 | 129.5 | 4.87 | 6.5% |
| 1h | 1R | IS | all | 3,242 | 49.0% | -0.095 | -0.26 | 0.89 | 316.4 | 5.18 | 7.7% |
| 1h | 1R | OOS | small | 860 | 50.7% | -0.013 | 0.53 | 1.08 | 30.4 | 14.68 | 6.7% |
| 1h | 1R | OOS | large | 814 | 49.9% | -0.034 | -0.59 | 0.92 | 41.0 | 14.46 | 5.5% |
| 1h | 1R | OOS | all | 1,674 | 50.3% | -0.023 | -0.01 | 1.00 | 41.9 | 14.57 | 6.2% |
| 1h | 2R | IS | small | 1,621 | 34.6% | -0.126 | -0.52 | 0.83 | 208.2 | 5.49 | 15.2% |
| 1h | 2R | IS | large | 1,621 | 35.7% | -0.092 | -0.01 | 1.00 | 172.5 | 4.87 | 13.8% |
| 1h | 2R | IS | all | 3,242 | 35.2% | -0.109 | -0.26 | 0.91 | 365.2 | 5.18 | 14.5% |
| 1h | 2R | OOS | small | 860 | 38.6% | 0.003 | 0.64 | 1.08 | 22.7 | 14.68 | 17.0% |
| 1h | 2R | OOS | large | 814 | 34.9% | -0.070 | -0.94 | 0.89 | 68.1 | 14.46 | 12.2% |
| 1h | 2R | OOS | all | 1,674 | 36.8% | -0.032 | -0.13 | 0.98 | 74.6 | 14.57 | 14.6% |
| 1h | 3R | IS | small | 1,621 | 29.5% | -0.126 | -0.49 | 0.85 | 210.6 | 5.49 | 19.3% |
| 1h | 3R | IS | large | 1,621 | 31.3% | -0.073 | 0.11 | 1.04 | 150.2 | 4.87 | 19.0% |
| 1h | 3R | IS | all | 3,242 | 30.4% | -0.100 | -0.19 | 0.94 | 332.9 | 5.18 | 19.2% |
| 1h | 3R | OOS | small | 860 | 34.5% | 0.031 | 1.08 | 1.13 | 30.5 | 14.68 | 22.2% |
| 1h | 3R | OOS | large | 814 | 30.0% | -0.071 | -1.03 | 0.89 | 73.8 | 14.46 | 16.8% |
| 1h | 3R | OOS | all | 1,674 | 32.3% | -0.019 | 0.05 | 1.01 | 77.6 | 14.57 | 19.6% |
| 1h | structural | IS | small | 1,113 | 51.8% | -0.107 | -0.39 | 0.75 | 119.8 | 3.88 | 3.0% |
| 1h | structural | IS | large | 1,369 | 55.8% | -0.088 | -0.09 | 0.94 | 127.5 | 4.43 | 3.7% |
| 1h | structural | IS | all | 2,482 | 54.0% | -0.096 | -0.22 | 0.86 | 240.7 | 4.18 | 3.3% |
| 1h | structural | OOS | small | 593 | 54.0% | -0.072 | -0.63 | 0.86 | 48.1 | 11.18 | 1.9% |
| 1h | structural | OOS | large | 701 | 55.5% | -0.061 | -0.92 | 0.82 | 53.1 | 13.59 | 2.1% |
| 1h | structural | OOS | all | 1,294 | 54.8% | -0.066 | -0.79 | 0.84 | 90.6 | 12.49 | 2.0% |
| 4h | 1R | IS | small | 460 | 48.5% | -0.052 | -0.77 | 0.85 | 30.6 | 11.07 | 12.4% |
| 4h | 1R | IS | large | 460 | 53.5% | 0.044 | -0.01 | 1.00 | 19.5 | 9.69 | 8.7% |
| 4h | 1R | IS | all | 920 | 51.0% | -0.004 | -0.39 | 0.92 | 40.3 | 10.38 | 10.5% |
| 4h | 1R | OOS | small | 226 | 56.6% | 0.128 | 5.38 | 1.45 | 5.6 | 33.33 | 11.1% |
| 4h | 1R | OOS | large | 221 | 50.7% | 0.006 | -0.31 | 0.97 | 13.7 | 26.50 | 8.6% |
| 4h | 1R | OOS | all | 447 | 53.7% | 0.068 | 2.56 | 1.21 | 8.7 | 29.96 | 9.8% |
| 4h | 2R | IS | small | 460 | 39.3% | 0.054 | 0.11 | 1.02 | 21.5 | 11.07 | 18.0% |
| 4h | 2R | IS | large | 460 | 38.5% | 0.040 | -0.20 | 0.96 | 25.6 | 9.69 | 13.9% |
| 4h | 2R | IS | all | 920 | 38.9% | 0.047 | -0.04 | 0.99 | 26.1 | 10.38 | 16.0% |
| 4h | 2R | OOS | small | 226 | 45.6% | 0.226 | 10.74 | 1.77 | 7.5 | 33.33 | 22.1% |
| 4h | 2R | OOS | large | 221 | 41.6% | 0.141 | 1.46 | 1.10 | 18.5 | 26.50 | 14.9% |
| 4h | 2R | OOS | all | 447 | 43.6% | 0.184 | 6.15 | 1.43 | 15.1 | 29.96 | 18.6% |
| 4h | 3R | IS | small | 460 | 34.6% | 0.100 | 0.60 | 1.10 | 24.5 | 11.07 | 22.6% |
| 4h | 3R | IS | large | 460 | 33.7% | 0.040 | -0.41 | 0.93 | 47.4 | 9.69 | 20.4% |
| 4h | 3R | IS | all | 920 | 34.1% | 0.070 | 0.09 | 1.02 | 34.3 | 10.38 | 21.5% |
| 4h | 3R | OOS | small | 226 | 40.7% | 0.268 | 11.03 | 1.73 | 9.3 | 33.33 | 27.4% |
| 4h | 3R | OOS | large | 221 | 36.7% | 0.140 | 1.89 | 1.12 | 16.6 | 26.50 | 22.6% |
| 4h | 3R | OOS | all | 447 | 38.7% | 0.205 | 6.51 | 1.43 | 15.1 | 29.96 | 25.1% |
| 4h | structural | IS | small | 230 | 52.6% | -0.036 | 0.09 | 1.03 | 31.2 | 7.67 | 3.5% |
| 4h | structural | IS | large | 353 | 60.9% | 0.024 | 0.08 | 1.03 | 20.4 | 8.48 | 4.2% |
| 4h | structural | IS | all | 583 | 57.6% | 0.000 | 0.08 | 1.03 | 38.5 | 8.16 | 3.9% |
| 4h | structural | OOS | small | 124 | 58.1% | 0.084 | 2.57 | 1.33 | 10.2 | 25.56 | 4.8% |
| 4h | structural | OOS | large | 191 | 56.0% | -0.025 | -2.84 | 0.74 | 14.1 | 24.83 | 5.2% |
| 4h | structural | OOS | all | 315 | 56.8% | 0.018 | -0.71 | 0.93 | 13.1 | 25.12 | 5.1% |
| 1D | 1R | IS | small | 91 | 50.5% | 0.003 | 3.30 | 1.31 | 9.2 | 28.18 | 6.6% |
| 1D | 1R | IS | large | 91 | 53.8% | 0.054 | 0.69 | 1.06 | 9.3 | 23.59 | 1.1% |
| 1D | 1R | IS | all | 182 | 52.2% | 0.029 | 1.99 | 1.18 | 13.0 | 25.88 | 3.8% |
| 1D | 1R | OOS | small | 44 | 54.5% | 0.091 | 6.51 | 1.26 | 4.6 | 65.22 | 6.8% |
| 1D | 1R | OOS | large | 31 | 48.4% | -0.057 | -4.05 | 0.87 | 5.1 | 64.88 | 3.2% |
| 1D | 1R | OOS | all | 75 | 52.0% | 0.030 | 2.15 | 1.08 | 7.3 | 65.08 | 5.3% |
| 1D | 2R | IS | small | 91 | 37.4% | 0.002 | 1.74 | 1.13 | 8.9 | 28.18 | 13.2% |
| 1D | 2R | IS | large | 91 | 39.6% | 0.111 | 1.59 | 1.12 | 11.9 | 23.59 | 8.8% |
| 1D | 2R | IS | all | 182 | 38.5% | 0.057 | 1.67 | 1.12 | 16.5 | 25.88 | 11.0% |
| 1D | 2R | OOS | small | 44 | 43.2% | 0.198 | 7.69 | 1.24 | 5.5 | 65.22 | 11.4% |
| 1D | 2R | OOS | large | 31 | 35.5% | -0.059 | -3.22 | 0.91 | 7.2 | 64.88 | 9.7% |
| 1D | 2R | OOS | all | 75 | 40.0% | 0.092 | 3.18 | 1.09 | 7.6 | 65.08 | 10.7% |
| 1D | 3R | IS | small | 91 | 30.8% | -0.061 | -0.03 | 1.00 | 13.8 | 28.18 | 19.8% |
| 1D | 3R | IS | large | 91 | 36.3% | 0.225 | 2.33 | 1.16 | 14.0 | 23.59 | 15.4% |
| 1D | 3R | IS | all | 182 | 33.5% | 0.082 | 1.15 | 1.08 | 16.7 | 25.88 | 17.6% |
| 1D | 3R | OOS | small | 44 | 40.9% | 0.359 | 16.99 | 1.51 | 7.5 | 65.22 | 18.2% |
| 1D | 3R | OOS | large | 31 | 35.5% | 0.162 | 7.30 | 1.20 | 6.2 | 64.88 | 12.9% |
| 1D | 3R | OOS | all | 75 | 38.7% | 0.278 | 12.98 | 1.37 | 8.5 | 65.08 | 16.0% |
| 1D | structural | IS | small | 31 | 54.8% | -0.103 | -2.97 | 0.60 | 7.9 | 21.41 | 0.0% |
| 1D | structural | IS | large | 60 | 56.7% | -0.100 | -1.04 | 0.87 | 9.6 | 22.73 | 0.0% |
| 1D | structural | IS | all | 91 | 56.0% | -0.101 | -1.70 | 0.78 | 13.3 | 22.28 | 0.0% |
| 1D | structural | OOS | small | 21 | 42.9% | -0.415 | -19.53 | 0.37 | 8.7 | 63.47 | 0.0% |
| 1D | structural | OOS | large | 27 | 48.1% | -0.247 | -9.13 | 0.64 | 8.2 | 66.65 | 0.0% |
| 1D | structural | OOS | all | 48 | 45.8% | -0.320 | -13.68 | 0.51 | 16.1 | 65.26 | 0.0% |

## 3. Is the small-vs-large gap real? Permutation test

One-sided permutation test of `mean_R(small) > mean_R(large)`, 10,000 label shuffles, plus a 2,000-draw bootstrap 95% CI on the difference. Two splits: the median split (comparable to the old conditional-probability table) and the extreme split Q1 vs Q5.

| TF | target | sample | split | diff R | p | 95% CI |
|---|---|---|---|---:|---:|---|
| 15min | 1R | IS | median | -0.021 | 0.8857 | [-0.053, 0.012] |
| 15min | 1R | IS | Q1 vs Q5 | -0.006 | 0.5947 | [-0.061, 0.046] |
| 15min | 1R | OOS | median | 0.018 | 0.2266 | [-0.030, 0.064] |
| 15min | 1R | OOS | Q1 vs Q5 | -0.005 | 0.5565 | [-0.077, 0.064] |
| 15min | 2R | IS | median | 0.004 | 0.4352 | [-0.044, 0.050] |
| 15min | 2R | IS | Q1 vs Q5 | 0.010 | 0.4017 | [-0.060, 0.081] |
| 15min | 2R | OOS | median | 0.039 | 0.1155 | [-0.023, 0.105] |
| 15min | 2R | OOS | Q1 vs Q5 | 0.001 | 0.4899 | [-0.098, 0.091] |
| 15min | 3R | IS | median | 0.021 | 0.2333 | [-0.033, 0.072] |
| 15min | 3R | IS | Q1 vs Q5 | 0.022 | 0.3092 | [-0.059, 0.103] |
| 15min | 3R | OOS | median | 0.058 | 0.0651 | [-0.013, 0.134] |
| 15min | 3R | OOS | Q1 vs Q5 | -0.012 | 0.5800 | [-0.124, 0.093] |
| 15min | structural | IS | median | -0.011 | 0.7174 | [-0.053, 0.029] |
| 15min | structural | IS | Q1 vs Q5 | -0.039 | 0.8792 | [-0.107, 0.028] |
| 15min | structural | OOS | median | 0.035 | 0.1144 | [-0.025, 0.091] |
| 15min | structural | OOS | Q1 vs Q5 | 0.007 | 0.4317 | [-0.083, 0.104] |
| 1h | 1R | IS | median | -0.043 | 0.8940 | [-0.112, 0.021] |
| 1h | 1R | IS | Q1 vs Q5 | -0.089 | 0.9547 | [-0.193, 0.015] |
| 1h | 1R | OOS | median | 0.020 | 0.3326 | [-0.073, 0.111] |
| 1h | 1R | OOS | Q1 vs Q5 | 0.114 | 0.0679 | [-0.029, 0.269] |
| 1h | 2R | IS | median | -0.034 | 0.7693 | [-0.124, 0.054] |
| 1h | 2R | IS | Q1 vs Q5 | -0.079 | 0.8675 | [-0.227, 0.062] |
| 1h | 2R | OOS | median | 0.073 | 0.1225 | [-0.044, 0.194] |
| 1h | 2R | OOS | Q1 vs Q5 | 0.209 | 0.0205 | [0.006, 0.417] |
| 1h | 3R | IS | median | -0.053 | 0.8285 | [-0.157, 0.049] |
| 1h | 3R | IS | Q1 vs Q5 | -0.148 | 0.9639 | [-0.313, 0.015] |
| 1h | 3R | OOS | median | 0.102 | 0.0856 | [-0.046, 0.249] |
| 1h | 3R | OOS | Q1 vs Q5 | 0.147 | 0.1110 | [-0.095, 0.390] |
| 1h | structural | IS | median | -0.019 | 0.6792 | [-0.102, 0.060] |
| 1h | structural | IS | Q1 vs Q5 | -0.087 | 0.9166 | [-0.208, 0.051] |
| 1h | structural | OOS | median | -0.011 | 0.5676 | [-0.119, 0.100] |
| 1h | structural | OOS | Q1 vs Q5 | -0.043 | 0.6939 | [-0.207, 0.129] |
| 4h | 1R | IS | median | -0.096 | 0.9397 | [-0.226, 0.027] |
| 4h | 1R | IS | Q1 vs Q5 | -0.040 | 0.6496 | [-0.236, 0.159] |
| 4h | 1R | OOS | median | 0.122 | 0.0880 | [-0.060, 0.302] |
| 4h | 1R | OOS | Q1 vs Q5 | 0.289 | 0.0181 | [0.026, 0.551] |
| 4h | 2R | IS | median | 0.015 | 0.4338 | [-0.167, 0.186] |
| 4h | 2R | IS | Q1 vs Q5 | 0.137 | 0.1631 | [-0.124, 0.415] |
| 4h | 2R | OOS | median | 0.085 | 0.2503 | [-0.158, 0.334] |
| 4h | 2R | OOS | Q1 vs Q5 | 0.111 | 0.2801 | [-0.254, 0.492] |
| 4h | 3R | IS | median | 0.060 | 0.2885 | [-0.157, 0.264] |
| 4h | 3R | IS | Q1 vs Q5 | 0.124 | 0.2261 | [-0.201, 0.442] |
| 4h | 3R | OOS | median | 0.128 | 0.1948 | [-0.160, 0.429] |
| 4h | 3R | OOS | Q1 vs Q5 | 0.111 | 0.3005 | [-0.313, 0.557] |
| 4h | structural | IS | median | -0.060 | 0.7590 | [-0.229, 0.120] |
| 4h | structural | IS | Q1 vs Q5 | -0.010 | 0.5282 | [-0.269, 0.276] |
| 4h | structural | OOS | median | 0.109 | 0.1841 | [-0.122, 0.351] |
| 4h | structural | OOS | Q1 vs Q5 | 0.198 | 0.1202 | [-0.169, 0.546] |
| 1D | 1R | IS | median | -0.051 | 0.6432 | [-0.321, 0.241] |
| 1D | 1R | IS | Q1 vs Q5 | 0.045 | 0.4198 | [-0.397, 0.479] |
| 1D | 1R | OOS | median | 0.148 | 0.2618 | [-0.294, 0.574] |
| 1D | 1R | OOS | Q1 vs Q5 | 0.622 | 0.0504 | [-0.131, 1.307] |
| 1D | 2R | IS | median | -0.109 | 0.7039 | [-0.493, 0.304] |
| 1D | 2R | IS | Q1 vs Q5 | 0.056 | 0.4234 | [-0.551, 0.637] |
| 1D | 2R | OOS | median | 0.257 | 0.2151 | [-0.363, 0.834] |
| 1D | 2R | OOS | Q1 vs Q5 | 0.928 | 0.0422 | [-0.021, 1.789] |
| 1D | 3R | IS | median | -0.286 | 0.8814 | [-0.766, 0.179] |
| 1D | 3R | IS | Q1 vs Q5 | -0.184 | 0.6989 | [-0.903, 0.498] |
| 1D | 3R | OOS | median | 0.196 | 0.3131 | [-0.546, 0.945] |
| 1D | 3R | OOS | Q1 vs Q5 | 1.228 | 0.0427 | [-0.006, 2.380] |
| 1D | structural | IS | median | -0.003 | 0.4897 | [-0.477, 0.541] |
| 1D | structural | IS | Q1 vs Q5 | 0.133 | 0.3809 | [-0.858, 1.627] |
| 1D | structural | OOS | median | -0.168 | 0.7553 | [-0.630, 0.325] |
| 1D | structural | OOS | Q1 vs Q5 | 0.255 | 0.2561 | [-0.353, 0.946] |

## 4. Cost sensitivity (out-of-sample, median split)

| TF | target | cost | small exp R | large exp R | all exp R |
|---|---|---:|---:|---:|---:|
| 15min | 1R | 0.0 | 0.002 | -0.022 | -0.010 |
| 15min | 1R | 0.2 | -0.053 | -0.071 | -0.061 |
| 15min | 1R | 0.5 | -0.134 | -0.144 | -0.139 |
| 15min | 1R | 0.04R | -0.038 | -0.062 | -0.050 |
| 15min | 2R | 0.0 | 0.012 | -0.032 | -0.010 |
| 15min | 2R | 0.2 | -0.042 | -0.081 | -0.061 |
| 15min | 2R | 0.5 | -0.123 | -0.154 | -0.138 |
| 15min | 2R | 0.04R | -0.028 | -0.072 | -0.050 |
| 15min | 3R | 0.0 | 0.027 | -0.036 | -0.004 |
| 15min | 3R | 0.2 | -0.027 | -0.085 | -0.056 |
| 15min | 3R | 0.5 | -0.109 | -0.158 | -0.133 |
| 15min | 3R | 0.04R | -0.013 | -0.076 | -0.044 |
| 15min | structural | 0.0 | 0.012 | -0.037 | -0.015 |
| 15min | structural | 0.2 | -0.053 | -0.087 | -0.072 |
| 15min | structural | 0.5 | -0.150 | -0.164 | -0.157 |
| 15min | structural | 0.04R | -0.028 | -0.077 | -0.055 |
| 1h | 1R | 0.0 | 0.013 | -0.010 | 0.002 |
| 1h | 1R | 0.2 | -0.013 | -0.034 | -0.023 |
| 1h | 1R | 0.5 | -0.052 | -0.068 | -0.060 |
| 1h | 1R | 0.04R | -0.027 | -0.050 | -0.038 |
| 1h | 2R | 0.0 | 0.029 | -0.047 | -0.008 |
| 1h | 2R | 0.2 | 0.003 | -0.070 | -0.032 |
| 1h | 2R | 0.5 | -0.036 | -0.105 | -0.069 |
| 1h | 2R | 0.04R | -0.011 | -0.087 | -0.048 |
| 1h | 3R | 0.0 | 0.057 | -0.048 | 0.006 |
| 1h | 3R | 0.2 | 0.031 | -0.071 | -0.019 |
| 1h | 3R | 0.5 | -0.008 | -0.106 | -0.056 |
| 1h | 3R | 0.04R | 0.017 | -0.088 | -0.034 |
| 1h | structural | 0.0 | -0.040 | -0.036 | -0.038 |
| 1h | structural | 0.2 | -0.072 | -0.061 | -0.066 |
| 1h | structural | 0.5 | -0.119 | -0.098 | -0.107 |
| 1h | structural | 0.04R | -0.080 | -0.076 | -0.078 |
| 4h | 1R | 0.0 | 0.140 | 0.018 | 0.080 |
| 4h | 1R | 0.2 | 0.128 | 0.006 | 0.068 |
| 4h | 1R | 0.5 | 0.111 | -0.012 | 0.050 |
| 4h | 1R | 0.04R | 0.100 | -0.022 | 0.040 |
| 4h | 2R | 0.0 | 0.237 | 0.153 | 0.196 |
| 4h | 2R | 0.2 | 0.226 | 0.141 | 0.184 |
| 4h | 2R | 0.5 | 0.209 | 0.123 | 0.166 |
| 4h | 2R | 0.04R | 0.197 | 0.113 | 0.156 |
| 4h | 3R | 0.0 | 0.280 | 0.152 | 0.217 |
| 4h | 3R | 0.2 | 0.268 | 0.140 | 0.205 |
| 4h | 3R | 0.5 | 0.251 | 0.122 | 0.187 |
| 4h | 3R | 0.04R | 0.240 | 0.112 | 0.177 |
| 4h | structural | 0.0 | 0.099 | -0.012 | 0.032 |
| 4h | structural | 0.2 | 0.084 | -0.025 | 0.018 |
| 4h | structural | 0.5 | 0.061 | -0.044 | -0.002 |
| 4h | structural | 0.04R | 0.059 | -0.052 | -0.008 |
| 1D | 1R | 0.0 | 0.097 | -0.052 | 0.036 |
| 1D | 1R | 0.2 | 0.091 | -0.057 | 0.030 |
| 1D | 1R | 0.5 | 0.082 | -0.064 | 0.022 |
| 1D | 1R | 0.04R | 0.057 | -0.092 | -0.004 |
| 1D | 2R | 0.0 | 0.204 | -0.054 | 0.097 |
| 1D | 2R | 0.2 | 0.198 | -0.059 | 0.092 |
| 1D | 2R | 0.5 | 0.189 | -0.066 | 0.083 |
| 1D | 2R | 0.04R | 0.164 | -0.094 | 0.057 |
| 1D | 3R | 0.0 | 0.365 | 0.167 | 0.283 |
| 1D | 3R | 0.2 | 0.359 | 0.162 | 0.278 |
| 1D | 3R | 0.5 | 0.350 | 0.155 | 0.269 |
| 1D | 3R | 0.04R | 0.325 | 0.127 | 0.243 |
| 1D | structural | 0.0 | -0.406 | -0.242 | -0.314 |
| 1D | structural | 0.2 | -0.415 | -0.247 | -0.320 |
| 1D | structural | 0.5 | -0.427 | -0.254 | -0.330 |
| 1D | structural | 0.04R | -0.446 | -0.282 | -0.354 |

## 5. Threshold sweep (1h, cost 0.2) — in-sample beside holdout

Rather than trusting one split point, every threshold: trade only C2s with `wick_ratio <= t`. If the concept is real the curve should be monotone (tighter threshold, better expectancy) **and it should have the same shape in both periods**. The two `exp R <=t` columns side by side are the whole test.

| target | t | IS n | IS exp R <=t | IS exp R >t | OOS n | OOS exp R <=t | OOS exp R >t |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1R | 0.15 | 383 | -0.117 | -0.092 | 194 | 0.043 | -0.032 |
| 1R | 0.20 | 601 | -0.108 | -0.092 | 324 | 0.076 | -0.047 |
| 1R | 0.25 | 848 | -0.124 | -0.085 | 471 | 0.040 | -0.048 |
| 1R | 0.30 | 1,106 | -0.131 | -0.076 | 603 | 0.029 | -0.052 |
| 1R | 0.35 | 1,365 | -0.120 | -0.077 | 738 | 0.011 | -0.050 |
| 1R | 0.40 | 1,634 | -0.118 | -0.072 | 862 | -0.014 | -0.033 |
| 1R | 0.45 | 1,930 | -0.118 | -0.061 | 1,008 | -0.014 | -0.036 |
| 1R | 0.50 | 2,173 | -0.109 | -0.067 | 1,166 | -0.009 | -0.056 |
| 1R | 0.55 | 2,423 | -0.104 | -0.069 | 1,278 | -0.015 | -0.050 |
| 1R | 0.60 | 2,623 | -0.106 | -0.050 | 1,389 | -0.011 | -0.084 |
| 1R | 0.65 | 2,798 | -0.103 | -0.048 | 1,472 | -0.014 | -0.087 |
| 1R | 0.70 | 2,942 | -0.104 | -0.008 | 1,543 | -0.020 | -0.057 |
| 1R | 0.75 | 3,041 | -0.103 | 0.023 | 1,585 | -0.018 | -0.108 |
| 2R | 0.15 | 383 | -0.142 | -0.105 | 194 | 0.011 | -0.038 |
| 2R | 0.20 | 601 | -0.127 | -0.105 | 324 | 0.107 | -0.066 |
| 2R | 0.25 | 848 | -0.132 | -0.101 | 471 | 0.097 | -0.083 |
| 2R | 0.30 | 1,106 | -0.144 | -0.091 | 603 | 0.066 | -0.088 |
| 2R | 0.35 | 1,365 | -0.135 | -0.091 | 738 | 0.047 | -0.095 |
| 2R | 0.40 | 1,634 | -0.127 | -0.091 | 862 | 0.003 | -0.070 |
| 2R | 0.45 | 1,930 | -0.122 | -0.090 | 1,008 | -0.008 | -0.070 |
| 2R | 0.50 | 2,173 | -0.112 | -0.104 | 1,166 | -0.012 | -0.080 |
| 2R | 0.55 | 2,423 | -0.107 | -0.116 | 1,278 | -0.014 | -0.094 |
| 2R | 0.60 | 2,623 | -0.114 | -0.089 | 1,389 | -0.013 | -0.127 |
| 2R | 0.65 | 2,798 | -0.108 | -0.114 | 1,472 | -0.020 | -0.127 |
| 2R | 0.70 | 2,942 | -0.112 | -0.076 | 1,543 | -0.024 | -0.138 |
| 2R | 0.75 | 3,041 | -0.113 | -0.048 | 1,585 | -0.023 | -0.207 |
| 3R | 0.15 | 383 | -0.183 | -0.088 | 194 | 0.012 | -0.023 |
| 3R | 0.20 | 601 | -0.171 | -0.083 | 324 | 0.116 | -0.051 |
| 3R | 0.25 | 848 | -0.151 | -0.081 | 471 | 0.133 | -0.078 |
| 3R | 0.30 | 1,106 | -0.148 | -0.075 | 603 | 0.106 | -0.089 |
| 3R | 0.35 | 1,365 | -0.137 | -0.072 | 738 | 0.072 | -0.090 |
| 3R | 0.40 | 1,634 | -0.127 | -0.072 | 862 | 0.030 | -0.071 |
| 3R | 0.45 | 1,930 | -0.116 | -0.075 | 1,008 | 0.026 | -0.087 |
| 3R | 0.50 | 2,173 | -0.098 | -0.102 | 1,166 | 0.002 | -0.066 |
| 3R | 0.55 | 2,423 | -0.095 | -0.113 | 1,278 | -0.008 | -0.052 |
| 3R | 0.60 | 2,623 | -0.105 | -0.075 | 1,389 | -0.009 | -0.066 |
| 3R | 0.65 | 2,798 | -0.102 | -0.084 | 1,472 | -0.017 | -0.030 |
| 3R | 0.70 | 2,942 | -0.103 | -0.070 | 1,543 | -0.020 | -0.007 |
| 3R | 0.75 | 3,041 | -0.101 | -0.077 | 1,585 | -0.015 | -0.091 |
| structural | 0.15 | 222 | -0.198 | -0.086 | 112 | -0.112 | -0.061 |
| structural | 0.20 | 365 | -0.177 | -0.083 | 190 | -0.116 | -0.057 |
| structural | 0.25 | 520 | -0.160 | -0.080 | 295 | -0.064 | -0.066 |
| structural | 0.30 | 719 | -0.155 | -0.072 | 399 | -0.035 | -0.080 |
| structural | 0.35 | 907 | -0.115 | -0.086 | 496 | -0.043 | -0.080 |
| structural | 0.40 | 1,123 | -0.109 | -0.086 | 595 | -0.073 | -0.060 |
| structural | 0.45 | 1,358 | -0.110 | -0.080 | 716 | -0.058 | -0.076 |
| structural | 0.50 | 1,556 | -0.107 | -0.079 | 843 | -0.063 | -0.071 |
| structural | 0.55 | 1,761 | -0.096 | -0.097 | 937 | -0.063 | -0.072 |
| structural | 0.60 | 1,926 | -0.102 | -0.076 | 1,034 | -0.060 | -0.090 |
| structural | 0.65 | 2,080 | -0.101 | -0.072 | 1,110 | -0.066 | -0.067 |
| structural | 0.70 | 2,204 | -0.100 | -0.067 | 1,176 | -0.070 | -0.020 |
| structural | 0.75 | 2,293 | -0.097 | -0.086 | 1,214 | -0.066 | -0.066 |

## 5b. The fitted small-wick cuts (2R, cost 0.2)

`meta/threshold_fits.md` fits the small-wick cut independently of this backtest: **`opposing_run/body <= 1.0`** (grade A, plateau 0.6-1.6) with a range form **`opposing_run/range <= 0.3`** (grade C). The numerator is the *opposing run* — opening price to the extreme against the direction — which is exactly what this module's `wick_ratio` numerator already is (see `build_trades`). Below, both forms, at the fitted value and across the fitted sweep.

The bar to clear is **3-4 percentage points**, not the ~15 the delivery table implies, and the barrier test that produced it found the effect **only on 4h and 1D** (+4.0pp and +3.2pp) with **approximately zero on 15m and 1h**. A null at 15m/1h here is therefore a *confirmation* of that result, not a failed replication.

| TF | form | cut | n pass | pass rate | pass exp R | fail exp R | diff R | pass win | fail win | win diff |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15min | run/body | 0.6 | 5,980 | 29.9% | -0.104 | -0.121 | 0.017 | 36.3% | 35.7% | 0.6% |
| 15min | run/body | 0.8 | 7,623 | 38.1% | -0.105 | -0.122 | 0.018 | 36.3% | 35.6% | 0.8% |
| 15min | run/body | **1.0** | 8,933 | 44.7% | -0.095 | -0.132 | 0.037 | 36.6% | 35.2% | 1.4% |
| 15min | run/body | 1.2 | 10,018 | 50.1% | -0.086 | -0.145 | 0.059 | 37.0% | 34.7% | 2.2% |
| 15min | run/body | 1.6 | 11,688 | 58.4% | -0.086 | -0.158 | 0.072 | 36.9% | 34.3% | 2.6% |
| 15min | run/range | 0.2 | 3,770 | 18.9% | -0.142 | -0.110 | -0.032 | 35.5% | 35.9% | -0.4% |
| 15min | run/range | 0.25 | 5,303 | 26.5% | -0.137 | -0.108 | -0.029 | 35.6% | 35.9% | -0.3% |
| 15min | run/range | **0.3** | 7,009 | 35.0% | -0.132 | -0.107 | -0.025 | 35.7% | 35.9% | -0.3% |
| 15min | run/range | 0.4 | 10,314 | 51.6% | -0.109 | -0.123 | 0.015 | 36.4% | 35.3% | 1.1% |
| 15min | run/range | 0.5 | 13,410 | 67.0% | -0.108 | -0.132 | 0.024 | 36.3% | 34.9% | 1.5% |
| 1h | run/body | 0.6 | 1,417 | 28.8% | -0.075 | -0.086 | 0.012 | 36.7% | 35.3% | 1.4% |
| 1h | run/body | 0.8 | 1,812 | 36.9% | -0.090 | -0.079 | -0.011 | 36.1% | 35.5% | 0.7% |
| 1h | run/body | **1.0** | 2,132 | 43.4% | -0.087 | -0.080 | -0.007 | 36.2% | 35.3% | 0.9% |
| 1h | run/body | 1.2 | 2,414 | 49.1% | -0.077 | -0.089 | 0.011 | 36.5% | 34.9% | 1.6% |
| 1h | run/body | 1.6 | 2,812 | 57.2% | -0.067 | -0.104 | 0.038 | 36.7% | 34.4% | 2.4% |
| 1h | run/range | 0.2 | 925 | 18.8% | -0.045 | -0.092 | 0.047 | 37.5% | 35.3% | 2.2% |
| 1h | run/range | 0.25 | 1,319 | 26.8% | -0.050 | -0.095 | 0.045 | 37.4% | 35.1% | 2.3% |
| 1h | run/range | **0.3** | 1,709 | 34.8% | -0.070 | -0.090 | 0.020 | 36.7% | 35.2% | 1.6% |
| 1h | run/range | 0.4 | 2,496 | 50.8% | -0.082 | -0.084 | 0.002 | 36.0% | 35.5% | 0.5% |
| 1h | run/range | 0.5 | 3,339 | 67.9% | -0.077 | -0.096 | 0.019 | 36.1% | 34.9% | 1.1% |
| 4h | run/body | 0.6 | 405 | 29.6% | 0.151 | 0.067 | 0.084 | 43.5% | 39.2% | 4.3% |
| 4h | run/body | 0.8 | 519 | 38.0% | 0.176 | 0.040 | 0.136 | 44.1% | 38.2% | 5.9% |
| 4h | run/body | **1.0** | 597 | 43.7% | 0.152 | 0.045 | 0.108 | 43.0% | 38.4% | 4.6% |
| 4h | run/body | 1.2 | 677 | 49.5% | 0.168 | 0.017 | 0.150 | 43.7% | 37.2% | 6.5% |
| 4h | run/body | 1.6 | 788 | 57.6% | 0.145 | 0.019 | 0.127 | 42.6% | 37.5% | 5.2% |
| 4h | run/range | 0.2 | 266 | 19.5% | 0.168 | 0.073 | 0.094 | 44.7% | 39.4% | 5.3% |
| 4h | run/range | 0.25 | 364 | 26.6% | 0.178 | 0.061 | 0.117 | 44.2% | 39.1% | 5.1% |
| 4h | run/range | **0.3** | 483 | 35.3% | 0.161 | 0.054 | 0.108 | 43.3% | 38.9% | 4.4% |
| 4h | run/range | 0.4 | 720 | 52.7% | 0.094 | 0.090 | 0.004 | 40.7% | 40.2% | 0.5% |
| 4h | run/range | 0.5 | 934 | 68.3% | 0.100 | 0.074 | 0.026 | 41.0% | 39.3% | 1.7% |
| 1D | run/body | 0.6 | 93 | 36.2% | 0.065 | 0.068 | -0.003 | 39.8% | 38.4% | 1.4% |
| 1D | run/body | 0.8 | 109 | 42.4% | 0.073 | 0.063 | 0.010 | 40.4% | 37.8% | 2.5% |
| 1D | run/body | **1.0** | 126 | 49.0% | 0.109 | 0.026 | 0.083 | 41.3% | 36.6% | 4.6% |
| 1D | run/body | 1.2 | 144 | 56.0% | 0.136 | -0.021 | 0.156 | 41.7% | 35.4% | 6.3% |
| 1D | run/body | 1.6 | 164 | 63.8% | 0.133 | -0.050 | 0.183 | 41.5% | 34.4% | 7.1% |
| 1D | run/range | 0.2 | 65 | 25.3% | 0.213 | 0.017 | 0.196 | 44.6% | 37.0% | 7.6% |
| 1D | run/range | 0.25 | 83 | 32.3% | 0.128 | 0.038 | 0.091 | 41.0% | 37.9% | 3.0% |
| 1D | run/range | **0.3** | 110 | 42.8% | 0.057 | 0.075 | -0.018 | 38.2% | 39.5% | -1.3% |
| 1D | run/range | 0.4 | 150 | 58.4% | 0.076 | 0.055 | 0.021 | 39.3% | 38.3% | 1.0% |
| 1D | run/range | 0.5 | 197 | 76.7% | 0.120 | -0.108 | 0.229 | 40.6% | 33.3% | 7.3% |

## 5c. Can this data even see a 3-4 point effect?

Before reading any of the differences above as real or absent, the question of whether they are resolvable at all. Minimum detectable win-rate difference between two equal buckets, two-sided alpha=0.05, 80% power, at the win rate each timeframe actually shows at 2R — and the total trades that would be needed to detect the 4-point effect `threshold_fits.md` reports on 4h.

| TF | sample | n | win rate | min detectable diff | n needed for 4pp | years of data implied |
|---|---|---:|---:|---:|---:|---:|
| 15min | IS | 13,138 | 36.0% | 2.3% | 4,520 | 0.7 |
| 15min | OOS | 6,862 | 35.6% | 3.2% | 4,498 | 0.7 |
| 15min | all | 20,000 | 35.8% | 1.9% | 4,512 | 0.7 |
| 1h | IS | 3,242 | 35.2% | 4.7% | 4,474 | 2.8 |
| 1h | OOS | 1,674 | 36.8% | 6.6% | 4,564 | 2.8 |
| 1h | all | 4,916 | 35.7% | 3.8% | 4,505 | 2.8 |
| 4h | IS | 920 | 38.9% | 9.0% | 4,664 | 10.4 |
| 4h | OOS | 447 | 43.6% | 13.1% | 4,826 | 10.8 |
| 4h | all | 1,367 | 40.5% | 7.4% | 4,727 | 10.6 |
| 1D | IS | 182 | 38.5% | 20.2% | 4,644 | 55.1 |
| 1D | OOS | 75 | 40.0% | 31.7% | 4,709 | 55.8 |
| 1D | all | 257 | 38.9% | 17.0% | 4,664 | 55.3 |

## 6. The null — the same trade taken on every bar

`primitive_base_rates.md` records that 40-44% of candles sweep the prior candle's range, so being a C2 is ordinary. This table takes the identical trade (enter at the bar close, stop at that bar's opposite extreme) on **every** bar in both directions. Taking both directions everywhere makes the directional edge zero by construction, so what this measures is the **friction of the mechanism itself** — the stop-first tie-break, gap fills and spread. Both cost 0.0 and cost 0.2 are shown because the null's stops are tighter than the C2 stops, so a flat spread taxes it harder.

| TF | target | cost | sample | n | win | exp R | exp USD/oz | PF | maxDD R | mean R (USD) | time-exit |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15min | 1R | 0.0 | IS | 93,472 | 47.2% | -0.082 | -0.02 | 0.97 | 7644.1 | 1.59 | 2.2% |
| 15min | 1R | 0.0 | OOS | 48,811 | 46.6% | -0.116 | -0.06 | 0.97 | 5661.5 | 4.80 | 2.1% |
| 15min | 1R | 0.2 | IS | 93,472 | 43.5% | -0.787 | -0.22 | 0.75 | 73554.9 | 1.59 | 2.2% |
| 15min | 1R | 0.2 | OOS | 48,811 | 46.0% | -0.373 | -0.26 | 0.89 | 18189.1 | 4.80 | 2.1% |
| 15min | 2R | 0.0 | IS | 93,472 | 34.5% | -0.036 | 0.00 | 1.00 | 3343.2 | 1.59 | 6.0% |
| 15min | 2R | 0.0 | OOS | 48,811 | 33.7% | -0.079 | -0.04 | 0.99 | 3897.0 | 4.80 | 5.7% |
| 15min | 2R | 0.2 | IS | 93,472 | 32.9% | -0.741 | -0.20 | 0.82 | 69244.4 | 1.59 | 6.0% |
| 15min | 2R | 0.2 | OOS | 48,811 | 33.4% | -0.336 | -0.24 | 0.92 | 16411.1 | 4.80 | 5.7% |
| 15min | 3R | 0.0 | IS | 93,472 | 28.6% | -0.012 | 0.01 | 1.01 | 1571.6 | 1.59 | 9.2% |
| 15min | 3R | 0.0 | OOS | 48,811 | 27.9% | -0.058 | -0.00 | 1.00 | 2886.8 | 4.80 | 8.9% |
| 15min | 3R | 0.2 | IS | 93,472 | 27.5% | -0.717 | -0.19 | 0.84 | 67009.5 | 1.59 | 9.2% |
| 15min | 3R | 0.2 | OOS | 48,811 | 27.7% | -0.315 | -0.20 | 0.94 | 15391.2 | 4.80 | 8.9% |
| 1h | 1R | 0.0 | IS | 23,381 | 48.3% | -0.058 | 0.01 | 1.01 | 1358.1 | 3.25 | 3.6% |
| 1h | 1R | 0.0 | OOS | 12,156 | 48.0% | -0.179 | -0.05 | 0.99 | 2181.3 | 9.78 | 3.1% |
| 1h | 1R | 0.2 | IS | 23,381 | 46.9% | -0.379 | -0.19 | 0.88 | 8872.6 | 3.25 | 3.6% |
| 1h | 1R | 0.2 | OOS | 12,156 | 47.8% | -0.297 | -0.25 | 0.95 | 3616.3 | 9.78 | 3.1% |
| 1h | 2R | 0.0 | IS | 23,381 | 35.0% | -0.024 | 0.07 | 1.04 | 572.6 | 3.25 | 7.3% |
| 1h | 2R | 0.0 | OOS | 12,156 | 34.5% | -0.155 | 0.02 | 1.00 | 2000.9 | 9.78 | 7.0% |
| 1h | 2R | 0.2 | IS | 23,381 | 34.3% | -0.345 | -0.13 | 0.93 | 8088.7 | 3.25 | 7.3% |
| 1h | 2R | 0.2 | OOS | 12,156 | 34.4% | -0.273 | -0.18 | 0.97 | 3323.5 | 9.78 | 7.0% |
| 1h | 3R | 0.0 | IS | 23,381 | 28.9% | -0.006 | 0.13 | 1.06 | 254.0 | 3.25 | 10.3% |
| 1h | 3R | 0.0 | OOS | 12,156 | 28.5% | -0.136 | 0.11 | 1.02 | 1887.4 | 9.78 | 10.0% |
| 1h | 3R | 0.2 | IS | 23,381 | 28.4% | -0.328 | -0.07 | 0.96 | 7684.2 | 3.25 | 10.3% |
| 1h | 3R | 0.2 | OOS | 12,156 | 28.5% | -0.254 | -0.09 | 0.99 | 3088.7 | 9.78 | 10.0% |
| 4h | 1R | 0.0 | IS | 6,185 | 49.9% | -0.007 | 0.31 | 1.11 | 79.7 | 6.44 | 5.7% |
| 4h | 1R | 0.0 | OOS | 3,208 | 50.0% | -0.006 | 0.48 | 1.05 | 96.2 | 19.55 | 5.7% |
| 4h | 1R | 0.2 | IS | 6,185 | 49.3% | -0.169 | 0.11 | 1.04 | 1051.1 | 6.44 | 5.7% |
| 4h | 1R | 0.2 | OOS | 3,208 | 49.9% | -0.060 | 0.28 | 1.03 | 198.8 | 19.55 | 5.7% |
| 4h | 2R | 0.0 | IS | 6,185 | 35.6% | 0.002 | 0.40 | 1.11 | 100.2 | 6.44 | 9.1% |
| 4h | 2R | 0.0 | OOS | 3,208 | 36.9% | 0.036 | 1.42 | 1.13 | 59.7 | 19.55 | 10.3% |
| 4h | 2R | 0.2 | IS | 6,185 | 35.2% | -0.160 | 0.20 | 1.06 | 1003.9 | 6.44 | 9.1% |
| 4h | 2R | 0.2 | OOS | 3,208 | 36.9% | -0.018 | 1.22 | 1.11 | 117.5 | 19.55 | 10.3% |
| 4h | 3R | 0.0 | IS | 6,185 | 29.9% | 0.029 | 0.56 | 1.15 | 81.4 | 6.44 | 12.1% |
| 4h | 3R | 0.0 | OOS | 3,208 | 31.3% | 0.072 | 1.88 | 1.17 | 56.9 | 19.55 | 13.4% |
| 4h | 3R | 0.2 | IS | 6,185 | 29.6% | -0.133 | 0.36 | 1.09 | 861.0 | 6.44 | 12.1% |
| 4h | 3R | 0.2 | OOS | 3,208 | 31.3% | 0.018 | 1.68 | 1.15 | 73.4 | 19.55 | 13.4% |
| 1D | 1R | 0.0 | IS | 1,246 | 51.4% | 0.010 | 0.76 | 1.11 | 24.7 | 15.33 | 1.8% |
| 1D | 1R | 0.0 | OOS | 650 | 49.8% | -0.122 | -1.55 | 0.93 | 90.9 | 44.97 | 2.6% |
| 1D | 1R | 0.2 | IS | 1,246 | 51.2% | -0.056 | 0.56 | 1.08 | 82.8 | 15.33 | 1.8% |
| 1D | 1R | 0.2 | OOS | 650 | 49.8% | -0.142 | -1.75 | 0.92 | 97.1 | 44.97 | 2.6% |
| 1D | 2R | 0.0 | IS | 1,246 | 36.5% | 0.041 | 1.47 | 1.17 | 27.9 | 15.33 | 5.6% |
| 1D | 2R | 0.0 | OOS | 650 | 37.4% | -0.033 | 1.47 | 1.06 | 69.9 | 44.97 | 4.9% |
| 1D | 2R | 0.2 | IS | 1,246 | 36.4% | -0.025 | 1.27 | 1.15 | 59.4 | 15.33 | 5.6% |
| 1D | 2R | 0.2 | OOS | 650 | 37.4% | -0.052 | 1.27 | 1.05 | 74.5 | 44.97 | 4.9% |
| 1D | 3R | 0.0 | IS | 1,246 | 30.2% | 0.065 | 1.39 | 1.15 | 28.1 | 15.33 | 9.1% |
| 1D | 3R | 0.0 | OOS | 650 | 33.1% | 0.084 | 4.76 | 1.17 | 39.4 | 44.97 | 8.5% |
| 1D | 3R | 0.2 | IS | 1,246 | 30.1% | -0.000 | 1.19 | 1.13 | 53.3 | 15.33 | 9.1% |
| 1D | 3R | 0.2 | OOS | 650 | 33.1% | 0.065 | 4.56 | 1.17 | 40.0 | 44.97 | 8.5% |

## 6b. Matched random-entry control

The decisive control, and the one the external cross-reference (`meta/external_crossref.md`) says to copy. Every C2 trade is paired with **five** random trades carrying the *same direction, the same stop distance and the same target distance*, entered at the close of a random bar within +/-30 days of the original. Local sampling keeps the volatility regime matched, which a whole-period draw would not: gold ran 1,800 -> 5,500 across this data.

A win rate means nothing against 50%. It only means something against this. Differences carry a 2,000-draw bootstrap 95% CI; a CI that straddles zero is no effect.

| TF | target | sample | C2 bucket | n | C2 win | ctrl win | win diff (95% CI) | C2 exp R | ctrl exp R | exp R diff (95% CI) |
|---|---|---|---|---:|---:|---:|---|---:|---:|---|
| 15min | 1R | IS | small | 6,569 | 48.9% | 49.0% | -0.0% [-1.2%, 1.2%] | -0.171 | -0.161 | -0.010 [-0.035, 0.015] |
| 15min | 1R | IS | all | 13,138 | 49.2% | 49.0% | 0.2% [-0.7%, 1.1%] | -0.161 | -0.161 | 0.000 [-0.018, 0.019] |
| 15min | 1R | OOS | small | 3,487 | 50.1% | 50.0% | 0.1% [-1.7%, 1.8%] | -0.053 | -0.053 | 0.001 [-0.033, 0.036] |
| 15min | 1R | OOS | all | 6,862 | 49.6% | 50.0% | -0.4% [-1.7%, 0.9%] | -0.061 | -0.053 | -0.008 [-0.035, 0.016] |
| 15min | 2R | IS | small | 6,569 | 36.5% | 36.5% | 0.0% [-1.2%, 1.2%] | -0.142 | -0.153 | 0.010 [-0.024, 0.044] |
| 15min | 2R | IS | all | 13,138 | 36.0% | 36.5% | -0.5% [-1.3%, 0.4%] | -0.144 | -0.153 | 0.009 [-0.015, 0.034] |
| 15min | 2R | OOS | small | 3,487 | 36.4% | 37.3% | -1.0% [-2.6%, 0.8%] | -0.042 | -0.045 | 0.003 [-0.045, 0.052] |
| 15min | 2R | OOS | all | 6,862 | 35.6% | 37.3% | -1.7% [-3.0%, -0.5%] | -0.061 | -0.045 | -0.016 [-0.051, 0.017] |
| 15min | 3R | IS | small | 6,569 | 31.7% | 31.7% | 0.0% [-1.1%, 1.2%] | -0.129 | -0.151 | 0.022 [-0.018, 0.062] |
| 15min | 3R | IS | all | 13,138 | 31.1% | 31.7% | -0.6% [-1.4%, 0.3%] | -0.139 | -0.151 | 0.011 [-0.017, 0.041] |
| 15min | 3R | OOS | small | 3,487 | 31.7% | 32.6% | -0.9% [-2.5%, 0.8%] | -0.027 | -0.040 | 0.012 [-0.041, 0.069] |
| 15min | 3R | OOS | all | 6,862 | 30.8% | 32.6% | -1.8% [-3.0%, -0.6%] | -0.056 | -0.040 | -0.016 [-0.055, 0.025] |
| 15min | structural | IS | small | 4,717 | 48.7% | 49.9% | -1.3% [-2.8%, 0.2%] | -0.179 | -0.177 | -0.002 [-0.036, 0.033] |
| 15min | structural | IS | all | 10,484 | 50.4% | 49.9% | 0.4% [-0.6%, 1.5%] | -0.173 | -0.177 | 0.004 [-0.017, 0.024] |
| 15min | structural | OOS | small | 2,454 | 55.3% | 55.2% | 0.1% [-1.9%, 2.3%] | -0.053 | -0.067 | 0.015 [-0.032, 0.062] |
| 15min | structural | OOS | all | 5,441 | 55.3% | 55.2% | 0.1% [-1.3%, 1.6%] | -0.072 | -0.067 | -0.004 [-0.033, 0.026] |
| 1h | 1R | IS | small | 1,621 | 47.7% | 49.4% | -1.7% [-4.2%, 0.9%] | -0.117 | -0.083 | -0.034 [-0.084, 0.014] |
| 1h | 1R | IS | all | 3,242 | 49.0% | 49.4% | -0.5% [-2.3%, 1.4%] | -0.095 | -0.083 | -0.012 [-0.049, 0.023] |
| 1h | 1R | OOS | small | 860 | 50.7% | 50.2% | 0.5% [-2.9%, 4.0%] | -0.013 | -0.025 | 0.011 [-0.057, 0.078] |
| 1h | 1R | OOS | all | 1,674 | 50.3% | 50.2% | 0.1% [-2.5%, 2.8%] | -0.023 | -0.025 | 0.001 [-0.049, 0.056] |
| 1h | 2R | IS | small | 1,621 | 34.6% | 36.1% | -1.5% [-4.0%, 0.9%] | -0.126 | -0.082 | -0.044 [-0.111, 0.022] |
| 1h | 2R | IS | all | 3,242 | 35.2% | 36.1% | -0.9% [-2.7%, 0.9%] | -0.109 | -0.082 | -0.027 [-0.075, 0.022] |
| 1h | 2R | OOS | small | 860 | 38.6% | 37.8% | 0.8% [-2.7%, 4.3%] | 0.003 | -0.003 | 0.006 [-0.087, 0.101] |
| 1h | 2R | OOS | all | 1,674 | 36.8% | 37.8% | -1.0% [-3.5%, 1.7%] | -0.032 | -0.003 | -0.030 [-0.098, 0.041] |
| 1h | 3R | IS | small | 1,621 | 29.5% | 31.2% | -1.7% [-4.0%, 0.7%] | -0.126 | -0.076 | -0.050 [-0.128, 0.025] |
| 1h | 3R | IS | all | 3,242 | 30.4% | 31.2% | -0.8% [-2.5%, 1.0%] | -0.100 | -0.076 | -0.023 [-0.082, 0.039] |
| 1h | 3R | OOS | small | 860 | 34.5% | 33.3% | 1.2% [-2.1%, 4.5%] | 0.031 | 0.010 | 0.021 [-0.088, 0.129] |
| 1h | 3R | OOS | all | 1,674 | 32.3% | 33.3% | -1.0% [-3.5%, 1.5%] | -0.019 | 0.010 | -0.028 [-0.105, 0.056] |
| 1h | structural | IS | small | 1,113 | 51.8% | 53.2% | -1.4% [-4.3%, 1.6%] | -0.107 | -0.109 | 0.002 [-0.062, 0.069] |
| 1h | structural | IS | all | 2,482 | 54.0% | 53.2% | 0.8% [-1.4%, 3.1%] | -0.096 | -0.109 | 0.013 [-0.030, 0.057] |
| 1h | structural | OOS | small | 593 | 54.0% | 57.2% | -3.3% [-7.3%, 1.0%] | -0.072 | -0.024 | -0.048 [-0.134, 0.045] |
| 1h | structural | OOS | all | 1,294 | 54.8% | 57.2% | -2.4% [-5.3%, 0.4%] | -0.066 | -0.024 | -0.042 [-0.099, 0.016] |
| 4h | 1R | IS | small | 460 | 48.5% | 50.8% | -2.3% [-7.3%, 2.6%] | -0.052 | -0.019 | -0.033 [-0.125, 0.062] |
| 4h | 1R | IS | all | 920 | 51.0% | 50.8% | 0.2% [-3.2%, 3.6%] | -0.004 | -0.019 | 0.015 [-0.052, 0.079] |
| 4h | 1R | OOS | small | 226 | 56.6% | 50.6% | 6.1% [-0.7%, 12.7%] | 0.128 | -0.002 | 0.130 [0.000, 0.258] |
| 4h | 1R | OOS | all | 447 | 53.7% | 50.6% | 3.1% [-1.9%, 8.1%] | 0.068 | -0.002 | 0.070 [-0.025, 0.162] |
| 4h | 2R | IS | small | 460 | 39.3% | 38.1% | 1.2% [-3.6%, 5.7%] | 0.054 | -0.006 | 0.060 [-0.072, 0.187] |
| 4h | 2R | IS | all | 920 | 38.9% | 38.1% | 0.8% [-2.5%, 4.1%] | 0.047 | -0.006 | 0.053 [-0.041, 0.143] |
| 4h | 2R | OOS | small | 226 | 45.6% | 37.7% | 7.8% [1.0%, 14.4%] | 0.226 | -0.010 | 0.236 [0.054, 0.414] |
| 4h | 2R | OOS | all | 447 | 43.6% | 37.7% | 5.9% [0.9%, 11.0%] | 0.184 | -0.010 | 0.194 [0.062, 0.329] |
| 4h | 3R | IS | small | 460 | 34.6% | 33.8% | 0.8% [-3.9%, 5.1%] | 0.100 | 0.020 | 0.079 [-0.081, 0.230] |
| 4h | 3R | IS | all | 920 | 34.1% | 33.8% | 0.4% [-2.9%, 3.5%] | 0.070 | 0.020 | 0.050 [-0.060, 0.155] |
| 4h | 3R | OOS | small | 226 | 40.7% | 33.2% | 7.5% [0.7%, 13.9%] | 0.268 | -0.026 | 0.294 [0.074, 0.513] |
| 4h | 3R | OOS | all | 447 | 38.7% | 33.2% | 5.5% [0.6%, 10.5%] | 0.205 | -0.026 | 0.231 [0.075, 0.394] |
| 4h | structural | IS | small | 230 | 52.6% | 53.8% | -1.2% [-7.7%, 5.7%] | -0.036 | -0.068 | 0.031 [-0.110, 0.190] |
| 4h | structural | IS | all | 583 | 57.6% | 53.8% | 3.8% [-0.9%, 7.9%] | 0.000 | -0.068 | 0.068 [-0.026, 0.158] |
| 4h | structural | OOS | small | 124 | 58.1% | 56.0% | 2.0% [-6.9%, 11.0%] | 0.084 | -0.023 | 0.107 [-0.082, 0.299] |
| 4h | structural | OOS | all | 315 | 56.8% | 56.0% | 0.8% [-5.0%, 6.7%] | 0.018 | -0.023 | 0.041 [-0.083, 0.174] |
| 1D | 1R | IS | small | 91 | 50.5% | 50.7% | -0.1% [-11.1%, 10.3%] | 0.003 | 0.006 | -0.002 [-0.213, 0.201] |
| 1D | 1R | IS | all | 182 | 52.2% | 50.7% | 1.5% [-6.0%, 9.9%] | 0.029 | 0.006 | 0.023 [-0.122, 0.183] |
| 1D | 1R | OOS | small | 44 | 54.5% | 50.7% | 3.9% [-11.5%, 19.2%] | 0.091 | 0.004 | 0.087 [-0.207, 0.379] |
| 1D | 1R | OOS | all | 75 | 52.0% | 50.7% | 1.3% [-10.5%, 13.3%] | 0.030 | 0.004 | 0.026 [-0.205, 0.262] |
| 1D | 2R | IS | small | 91 | 37.4% | 38.3% | -1.0% [-11.5%, 9.1%] | 0.002 | 0.063 | -0.061 [-0.354, 0.220] |
| 1D | 2R | IS | all | 182 | 38.5% | 38.3% | 0.1% [-7.4%, 7.7%] | 0.057 | 0.063 | -0.006 [-0.216, 0.218] |
| 1D | 2R | OOS | small | 44 | 43.2% | 37.6% | 5.6% [-9.4%, 21.0%] | 0.198 | 0.042 | 0.155 [-0.268, 0.596] |
| 1D | 2R | OOS | all | 75 | 40.0% | 37.6% | 2.4% [-9.6%, 13.9%] | 0.092 | 0.042 | 0.049 [-0.286, 0.379] |
| 1D | 3R | IS | small | 91 | 30.8% | 34.4% | -3.7% [-13.8%, 6.3%] | -0.061 | 0.123 | -0.184 [-0.516, 0.164] |
| 1D | 3R | IS | all | 182 | 33.5% | 34.4% | -0.9% [-8.2%, 6.6%] | 0.082 | 0.123 | -0.041 [-0.283, 0.230] |
| 1D | 3R | OOS | small | 44 | 40.9% | 33.8% | 7.1% [-8.3%, 23.1%] | 0.359 | 0.096 | 0.263 [-0.272, 0.834] |
| 1D | 3R | OOS | all | 75 | 38.7% | 33.8% | 4.9% [-7.7%, 16.2%] | 0.278 | 0.096 | 0.182 [-0.250, 0.583] |
| 1D | structural | IS | small | 31 | 54.8% | 60.6% | -5.8% [-23.7%, 12.8%] | -0.103 | -0.007 | -0.096 [-0.495, 0.423] |
| 1D | structural | IS | all | 91 | 56.0% | 60.6% | -4.6% [-15.4%, 6.7%] | -0.101 | -0.007 | -0.094 [-0.320, 0.163] |
| 1D | structural | OOS | small | 21 | 42.9% | 47.1% | -4.2% [-26.2%, 18.6%] | -0.415 | -0.242 | -0.172 [-0.535, 0.223] |
| 1D | structural | OOS | all | 48 | 45.8% | 47.1% | -1.2% [-17.5%, 14.6%] | -0.320 | -0.242 | -0.078 [-0.356, 0.201] |

## 6c. The resolution artefact — M1 exits vs signal-timeframe exits

The identical book, resolved twice: once bar-by-bar on M1 (everything above) and once on the signal timeframe's own OHLC. The coarse version cannot see the order of events inside a bar, so a bar that touched both the stop and the target is one event to it rather than two — and the tie-break has to guess. Two coarse variants are shown: `tf/stop-first` keeps the conservative rule, `tf/target-first` is the optimistic one a careless backtest falls into.

This is the failure mode the external cross-reference flags as having turned a ~73% win rate into ~50% in a published FVG study. The gap between the columns below is the size of that artefact on this book.

| TF | target | sample | M1 win | M1 exp R | tf/stop-first win | tf/stop-first exp R | tf/target-first win | tf/target-first exp R |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 15min | 1R | IS | 49.2% | -0.161 | 47.1% | -0.203 | 51.4% | -0.115 |
| 15min | 1R | OOS | 49.6% | -0.061 | 47.1% | -0.111 | 51.9% | -0.015 |
| 15min | 2R | IS | 36.0% | -0.144 | 35.4% | -0.161 | 37.0% | -0.113 |
| 15min | 2R | OOS | 35.6% | -0.061 | 34.8% | -0.084 | 36.7% | -0.026 |
| 15min | 3R | IS | 31.1% | -0.139 | 30.9% | -0.147 | 31.6% | -0.119 |
| 15min | 3R | OOS | 30.8% | -0.056 | 30.5% | -0.067 | 31.4% | -0.030 |
| 15min | structural | IS | 50.4% | -0.173 | 47.6% | -0.228 | 52.0% | -0.132 |
| 15min | structural | OOS | 55.3% | -0.072 | 51.7% | -0.133 | 57.0% | -0.026 |
| 1h | 1R | IS | 49.0% | -0.095 | 45.8% | -0.158 | 52.1% | -0.032 |
| 1h | 1R | OOS | 50.3% | -0.023 | 47.2% | -0.085 | 53.5% | 0.041 |
| 1h | 2R | IS | 35.2% | -0.109 | 34.2% | -0.138 | 37.3% | -0.046 |
| 1h | 2R | OOS | 36.8% | -0.032 | 36.0% | -0.056 | 38.3% | 0.013 |
| 1h | 3R | IS | 30.4% | -0.100 | 30.0% | -0.115 | 31.5% | -0.056 |
| 1h | 3R | OOS | 32.3% | -0.019 | 32.1% | -0.028 | 33.3% | 0.022 |
| 1h | structural | IS | 54.0% | -0.096 | 48.9% | -0.189 | 57.1% | -0.025 |
| 1h | structural | OOS | 54.8% | -0.066 | 49.0% | -0.157 | 58.0% | 0.018 |
| 4h | 1R | IS | 51.0% | -0.004 | 46.5% | -0.093 | 55.4% | 0.085 |
| 4h | 1R | OOS | 53.7% | 0.068 | 51.2% | 0.019 | 56.4% | 0.121 |
| 4h | 2R | IS | 38.9% | 0.047 | 36.8% | -0.015 | 41.5% | 0.125 |
| 4h | 2R | OOS | 43.6% | 0.184 | 43.0% | 0.164 | 45.2% | 0.231 |
| 4h | 3R | IS | 34.1% | 0.070 | 32.4% | 0.000 | 36.0% | 0.144 |
| 4h | 3R | OOS | 38.7% | 0.205 | 38.7% | 0.205 | 39.8% | 0.250 |
| 4h | structural | IS | 57.6% | 0.000 | 48.7% | -0.140 | 62.4% | 0.105 |
| 4h | structural | OOS | 56.8% | 0.018 | 53.3% | -0.037 | 60.0% | 0.087 |
| 1D | 1R | IS | 52.2% | 0.029 | 48.4% | -0.048 | 56.0% | 0.106 |
| 1D | 1R | OOS | 52.0% | 0.030 | 49.3% | -0.023 | 54.7% | 0.083 |
| 1D | 2R | IS | 38.5% | 0.057 | 38.5% | 0.057 | 41.2% | 0.139 |
| 1D | 2R | OOS | 40.0% | 0.092 | 38.7% | 0.052 | 41.3% | 0.132 |
| 1D | 3R | IS | 33.5% | 0.082 | 33.5% | 0.082 | 34.6% | 0.126 |
| 1D | 3R | OOS | 38.7% | 0.278 | 37.3% | 0.224 | 40.0% | 0.331 |
| 1D | structural | IS | 56.0% | -0.101 | 45.1% | -0.244 | 57.1% | -0.086 |
| 1D | structural | OOS | 45.8% | -0.320 | 39.6% | -0.393 | 47.9% | -0.295 |

## 6d. Do the results depend on walking M1 across a session break?

XAUUSD stops trading 17:00-18:04 New York daily (zero bars in NY hour 17) and over weekends, so a 10-period hold window can contain a hole. Walking straight through one lets a stop or target be 'hit' on the far side of a gap the position could not have been managed across. The fills are already conservative about this — a bar opening beyond the stop fills at that open, so the gap is paid — but the honest check is to re-run the whole book flat over the break and compare. `truncated` ends every window at the first gap longer than 70 minutes and exits at the last price before it.

**Read the low timeframes only.** At 15m and 1h a hold window rarely reaches a break, so truncation is a genuine robustness check — and it changes nothing. At 4h and especially 1D a multi-period hold *must* span weekends, so the truncated column there is not a robustness check at all: it is a different, much shorter strategy, and its difference should not be read as an artefact estimate.

| TF | target | sample | windows spanning a break | full exp R | truncated exp R | diff |
|---|---|---|---:|---:|---:|---:|
| 15min | 1R | IS | 0.0% | -0.161 | -0.161 | 0.000 |
| 15min | 1R | OOS | 0.0% | -0.061 | -0.061 | 0.000 |
| 15min | 2R | IS | 0.0% | -0.144 | -0.144 | 0.000 |
| 15min | 2R | OOS | 0.0% | -0.061 | -0.061 | 0.000 |
| 15min | 3R | IS | 0.0% | -0.139 | -0.139 | 0.000 |
| 15min | 3R | OOS | 0.0% | -0.056 | -0.056 | 0.000 |
| 15min | structural | IS | 0.0% | -0.173 | -0.173 | 0.000 |
| 15min | structural | OOS | 0.0% | -0.072 | -0.072 | 0.000 |
| 1h | 1R | IS | 0.7% | -0.095 | -0.094 | -0.001 |
| 1h | 1R | OOS | 0.7% | -0.023 | -0.023 | 0.000 |
| 1h | 2R | IS | 0.7% | -0.109 | -0.108 | -0.002 |
| 1h | 2R | OOS | 0.7% | -0.032 | -0.033 | 0.001 |
| 1h | 3R | IS | 0.7% | -0.100 | -0.098 | -0.001 |
| 1h | 3R | OOS | 0.7% | -0.019 | -0.019 | 0.001 |
| 1h | structural | IS | 0.7% | -0.096 | -0.095 | -0.002 |
| 1h | structural | OOS | 0.7% | -0.066 | -0.066 | 0.000 |
| 4h | 1R | IS | 2.9% | -0.004 | -0.004 | 0.001 |
| 4h | 1R | OOS | 2.9% | 0.068 | 0.065 | 0.003 |
| 4h | 2R | IS | 2.9% | 0.047 | 0.048 | -0.001 |
| 4h | 2R | OOS | 2.9% | 0.184 | 0.183 | 0.001 |
| 4h | 3R | IS | 2.9% | 0.070 | 0.070 | -0.001 |
| 4h | 3R | OOS | 2.9% | 0.205 | 0.200 | 0.005 |
| 4h | structural | IS | 2.9% | 0.000 | 0.004 | -0.003 |
| 4h | structural | OOS | 2.9% | 0.018 | 0.011 | 0.007 |
| 1D | 1R | IS | 99.2% | 0.029 | -0.008 | 0.036 |
| 1D | 1R | OOS | 99.2% | 0.030 | 0.092 | -0.062 |
| 1D | 2R | IS | 99.2% | 0.057 | 0.037 | 0.019 |
| 1D | 2R | OOS | 99.2% | 0.092 | 0.162 | -0.071 |
| 1D | 3R | IS | 99.2% | 0.082 | 0.070 | 0.013 |
| 1D | 3R | OOS | 99.2% | 0.278 | 0.217 | 0.060 |
| 1D | structural | IS | 99.2% | -0.101 | -0.096 | -0.005 |
| 1D | structural | OOS | 99.2% | -0.320 | -0.152 | -0.169 |

## 6e. What is deliberately *not* in this backtest

**No session or kill-zone filter is applied anywhere in this file.** That is a decision, not an omission. `meta/session_window_fit.md` measures the corpus's own forex NY AM window (07:00-10:00 New York) at **-0.057R versus the rest of the day (t = -3.11, 7,835 events)** — the only session result that survives multiple-testing correction, and it is negative. Gating on time of day would have made these results worse for a reason unrelated to the wick claim, and would have confounded the test. If a session knob is swept later it should be swept, not applied.

The same document settles the timezone as `America/New_York` **with DST**. Nothing here depends on it: every window is defined in elapsed wall-clock time from the signal bar's close, and no rule in this module references a local hour.

**Which outcome metrics are safe, and which are not.** `threshold_fits.md` warns that the two metrics most literally encoding the corpus's wording — 'continued' beyond the extreme and 'reverted' to the open — are geometrically confounded by the very quantity being bucketed, since `range = opposing_run + body + far_wick` means a large opposing run forces a small body. That is the same defect this file independently diagnoses in table 0 via the `open gap R` column, arrived at from the other direction.

- **`delivered beyond C2 open` (table 0) is CONFOUNDED** and is reported only to show why. It reduces to where the candle closed relative to its own open.

- **R-multiple and structural targets resolved on M1 are safe.** The target and stop are absolute prices fixed at entry, and the outcome is decided by bars strictly after the signal candle closed. No part of the signal candle's own geometry can satisfy them.

- **MFE / MAE (table 0, right half) are safe** for the same reason: they measure forward travel over bars the signal candle cannot influence mechanically. They are the target-free cross-check on the confounded column beside them, and they disagree with it.

## 7. Summary — every cell, out-of-sample

| TF | target | OOS small exp R | OOS large exp R | OOS all exp R | OOS small PF | positive after cost 0.2? |
|---|---|---:|---:|---:|---:|---|
| 15min | 1R | -0.053 | -0.071 | -0.061 | 0.93 | no |
| 15min | 2R | -0.042 | -0.081 | -0.061 | 0.97 | no |
| 15min | 3R | -0.027 | -0.085 | -0.056 | 0.98 | no |
| 15min | structural | -0.053 | -0.087 | -0.072 | 0.94 | no |
| 1h | 1R | -0.013 | -0.034 | -0.023 | 1.08 | no |
| 1h | 2R | 0.003 | -0.070 | -0.032 | 1.08 | yes |
| 1h | 3R | 0.031 | -0.071 | -0.019 | 1.13 | yes |
| 1h | structural | -0.072 | -0.061 | -0.066 | 0.86 | no |
| 4h | 1R | 0.128 | 0.006 | 0.068 | 1.45 | yes |
| 4h | 2R | 0.226 | 0.141 | 0.184 | 1.77 | yes |
| 4h | 3R | 0.268 | 0.140 | 0.205 | 1.73 | yes |
| 4h | structural | 0.084 | -0.025 | 0.018 | 1.33 | yes |
| 1D | 1R | 0.091 | -0.057 | 0.030 | 1.26 | yes |
| 1D | 2R | 0.198 | -0.059 | 0.092 | 1.24 | yes |
| 1D | 3R | 0.359 | 0.162 | 0.278 | 1.51 | yes |
| 1D | structural | -0.415 | -0.247 | -0.320 | 0.37 | no |

## 8. Verdict

**The claim is refuted where this data can see, and unresolvable where it cannot.** That distinction is the main finding and it is stated first because it is the one that is easy to get wrong in both directions.

### Start with power, because it decides what the rest can mean

An independent barrier test (`meta/threshold_fits.md`) puts the true small-wick advantage at **+4.0pp on 4h and +3.2pp on 1D, and approximately zero on 15m and 1h**. That is the effect size this backtest has to be able to see. Table 5c says it can only see it on two timeframes, and they are the wrong two:

| TF | C2 trades, 3 years | min detectable diff | verdict |
|---|---:|---:|---|
| 15min | 20,000 | 1.9% | can resolve a 3-4pp effect |
| 1h | 4,916 | 3.8% | marginal — can see 4pp, not 3pp |
| 4h | 1,367 | 7.4% | **cannot resolve a 3-4pp effect** |
| 1D | 257 | 17.0% | **cannot resolve a 3-4pp effect** |

Detecting a 4-point difference needs roughly 4,512 C2s in total, split evenly between the two wick buckets. Three years of XAUUSD supplies 1,367 C2s on 4h and 257 on 1D — about 10 and 55 years of data short respectively. **So this file cannot falsify the claim on 4h or 1D, and does not claim to.** Any 4h/1D number below, in either direction, is inside the noise floor.

What it *can* do is test the timeframes with the sample: 15m (n=20,000, min detectable 1.9%) and 1h (n=4,916, 3.8%).

### On the timeframes with enough data, the effect is absent — as predicted

At the grade-A fitted cut `opposing_run/body <= 1.0` the small-wick win-rate advantage is **1.4% at 15m** and **0.9% at 1h** (table 5b), both below their own detection floors and both far below the ~15 points the delivery table implies. Every cut across the fitted plateau 0.6-1.6 stays inside 3 points at both timeframes.

**This is a confirmation, not a failed replication.** The independent barrier test predicted approximately zero at 15m and 1h from a completely different measurement (a scale-free +/-1 ATR race, no stop, no target, no costs). Two unrelated methods agreeing that the effect is absent on the low timeframes is the strongest positive statement in this file — it is just a statement about where the claim does *not* live.

One caveat on the imported cut: it does not price the same way here. `opposing_run/body <= 1.0` sits at about the 65th percentile of *all* XAUUSD candles per `threshold_fits.md`, but admits only 43.4% of 1h **C2s**. Requiring a close back inside the prior range and a reversal close already selects on wick size, so the fitted percentile does not transfer to this event set. The sweep is reported for that reason rather than a single cut.

### C2 entries are indistinguishable from random entries of the same shape

This is the decisive test and it is the one the claim has never faced. Give a random entry the same direction, the same stop distance and the same target distance at a random moment in the same month, and at 1h it performs as well as the C2. In-sample the small-wick C2 book is 0.044 R *worse* than its random twin (95% CI [-0.111, 0.022]); out-of-sample it is 0.006 R better (CI [-0.087, 0.101]). Both intervals contain zero, and no win-rate difference at 1h on an R-multiple target exceeds 1.7% in either direction (the structural target is worse still, reaching 3.3% *against* the C2). Of the 64 C2-vs-control comparisons in table 6b, 5 have a confidence interval that clears zero — and none of those are at 1h, the timeframe with by far the most trades.

The tightest measurement in the file is at 15m, where the sample is largest: the small-wick C2 book beats its random twin by 0.0% in-sample and -1.0% out-of-sample, with confidence intervals about one percentage point wide. That is a well-powered zero.

The published FVG study cited in `meta/external_crossref.md` found its construct about five percentage points above a matched random baseline and still had no tradeable edge after costs. The C2 wick split does not reach five points anywhere it can be measured.

### The old statistic is real but measures the wrong thing

Table 0 replicates it exactly: at 1h the smallest-wick quintile delivers beyond the C2 open 84.1% of the time and the largest 58.2%, monotone across all five buckets and repeated at 4h and 1D. But the `open gap R` column moves in perfect lockstep: the C2 open sits 0.79R below the entry in the smallest-wick bucket and only 0.16R below it in the largest. **The delivery test is asking the small-wick bucket an easier question.** A small sweeping wick means a proportionally larger body, which puts the C2 open further from the close, which gives the next candle more room to fail to reach it. The gap measures the geometry of the signal candle, not the behaviour of the one after it.

On the measure that cannot be gamed this way — maximum favourable excursion, which needs no target and no arbitrary reference price — the ordering **reverses**. At 1h, the fraction of C2s that ever travel 2R in favour is 42.4% for the smallest-wick quintile against 47.1% for Q4. Small-wick C2s expand *less* often, not more. Mean MFE tells the same story: the smallest bucket is not the largest on any timeframe.

### The backtested effect changes sign between the fit and the holdout

At 1h/2R with a 0.2 spread, the median-split difference `mean_R(small) - mean_R(large)` is **-0.034 R in-sample** (n=3,242, two years, one-sided p=0.769 — the data leans the *other* way) and **0.073 R out-of-sample** (n=1,674, one year, p=0.122). The larger sample contradicts the smaller one. The same flip appears at 1R and 3R. That is what noise looks like, not an edge with a bad year.

Across all 64 permutation tests run here, 4 came in under p=0.05 — against 3.2 expected by chance alone — and 0 survive a Bonferroni threshold of 0.0008. None of them are in-sample, which is the wrong way round: a real effect should show up most clearly in the *larger* sample, not only in the smaller one.

The threshold sweep (table 5) makes the same point without any split point to argue about. Out-of-sample the curve does slope the predicted way, peaking around t=0.20. In-sample, over twice the trades, the same curve is flat and negative at every threshold. The shape the holdout shows simply is not present in the fit window.

### What is left is smaller than the spread

At 1h the entire measured out-of-sample effect lives inside the bid-ask. The small-wick bucket at 2R goes: 0.0 -> 0.029 R; 0.2 -> 0.003 R; 0.5 -> -0.036 R; 0.04R -> -0.011 R. A 0.2-0.3 USD/oz round trip — the realistic base case for XAUUSD — consumes essentially all of it, and the risk-proportional cost puts it back underwater.

There is also a confound in the flat-cost columns worth naming: gold ran from roughly 1,800 to 5,500 over this sample, so the mean 1h R nearly triples between the fit and the holdout (5.18 -> 14.57 USD). A flat 0.2 USD spread is therefore a 3.9% tax in-sample and a 1.4% tax out-of-sample. Part of why the holdout looks kinder than the fit has nothing to do with the signal at all — which is why the `0.04R` proportional column exists.

### How this compares to the null

`primitive_base_rates.md` records that 40-44% of candles sweep the prior candle's range. C2s are 27% of 1h bars here — this is an ordinary event, and sorting ordinary events by a wick ratio does not stop them being ordinary. Table 6 takes the identical trade on every bar in both directions, which zeroes the directional edge by construction and leaves only mechanism friction. At zero cost that friction is about -0.02 R at 1h in-sample and -0.16 R out-of-sample. The C2 book as a whole lands at -0.037 R in-sample (worse than an arbitrary bar) and -0.008 R out-of-sample (better). So even **C2 selection itself**, never mind the wick, has no stable sign at 1h.

### 4h: the one place the claim is still alive, and why that is not a result yet

4h is where this file and `threshold_fits.md` are most nearly consistent, and it deserves stating plainly rather than being buried. At the fitted cut the small-wick win-rate advantage is 4.6%, and every cut across the fitted plateau gives between +4.3 and +6.5 points — the right sign and roughly the right size against the independent +4.0pp barrier result. Expectancy differences run +0.08 to +0.15 R the same way.

Three reasons it is not yet a finding. First, power: 4h's minimum detectable difference is 7.4%, so an effect of this size is not distinguishable from zero here however suggestive it looks. Second, it does not hold up across the split — against the matched random control the whole 4h/2R C2 book is 0.194 R out-of-sample (CI [0.062, 0.329], clears zero) but only 0.053 R in-sample (CI [-0.041, 0.143], does not), on twice the data. Third, most of it is not about wicks: the whole 4h C2 book beats the random control by 5.9 points out-of-sample against 7.8 for the small-wick subset, and the quintiles are non-monotone (Q4 scores as well as Q1 on every target). **Whatever is at 4h is mostly C2-ness, not wick size.**

The correct next step for 4h is more data — other instruments, or a longer XAUUSD history — not more analysis of these 1,367 trades.

### A coarse backtest would have got the opposite answer

Table 6c re-resolves the identical book on signal-timeframe bars. The artefact is real and it points exactly the way the FVG study warned. At 1h/2R out-of-sample, M1 resolution gives 36.8% win rate and -0.032 R; the same trades resolved on 1h bars with an optimistic same-bar tie-break give 38.3% and 0.013 R — a sign flip. The same flip happens at 1R, 3R and structural, and at 4h/structural in-sample a flat 0.000 R becomes +0.105 R. The effect here is smaller than the 73%-to-50% collapse MPM reported, because an R-multiple target on XAUUSD usually takes many bars to reach, but it is large enough to manufacture a positive result out of a negative one. Any C2 backtest resolved on its own signal timeframe should be assumed wrong.

### The model's own target is the worst one

Worth recording separately, because it is the target the fractal model actually implies: `structural` — sweep the low, deliver to the prior candle's high — is the only target that loses money in every period on every timeframe (1h OOS -0.066 R, 1D OOS -0.320 R). It also cannot express the whole signal: at 1h, 1,140 of 4,916 C2s closed beyond the prior candle's far extreme, leaving no target to aim at. The R multiples that score better are ones the corpus never specifies.

### Bottom line

The C2 sweeping-wick asymmetry should be **retired as a trade signal on 15m and 1h, and treated as untested on 4h and 1D.**

The 78-83% vs 63-66% figure in `fractal_reading_comparison.md` is not wrong, but it is not evidence of expansion — it is evidence that the C2 open sits further from the close when the wick is small, which an independent workstream flagged as a geometric confound from the other direction. Corrected for it, small-wick C2s reach a 2R target slightly *less* often than large-wick ones. Under a stop, a target, path-dependent M1 resolution and a realistic spread, the effect has the wrong sign in the two-year fit window, an unremarkable positive sign in the one-year holdout, no cell that survives correction for the number of cells tested, and — decisively — no measurable advantage over a random entry of identical geometry on either timeframe where the sample is big enough to say so.

The real effect size in play was never 15 points. It is 3-4, and at that size three years of XAUUSD is simply not enough data on 4h or 1D. Reporting that honestly is worth more than a verdict the sample cannot support in either direction.

This closes item 1 of the RESUME.md next-steps list, and it agrees with the two external priors: Marshall, Young & Rose found candlestick shapes create no value against bootstrapped controls, and the one quantitative study of a same-family ICT construct found ~5 points over random and nothing after costs. The corpus's best falsifiable prediction has now been tested on its own terms where it could be, and the honest verdict is split: **refuted on 15m and 1h, underpowered on 4h and 1D.** Given the claim is externally unattested — every outside search hit traced back to the channel — this file is currently the only independent test of it that exists, and knowing exactly which half of it remains open is more useful than another conditional probability.

**RESUME.md finding 4 should be amended.** It currently reads that the claim 'still survives testing' and calls it the best backtest candidate. It survives *counting*; it does not survive testing at 15m or 1h, and at 4h and 1D it has not been tested — the data cannot carry the test. `fractal_reading_comparison.md` was already careful to say the delivery rate is not an edge; that caution was correct and should now be strengthened.

### What would actually settle it

Not more analysis of this sample. Specifically:

1. **More 4h/1D observations** — other instruments (the FVG study used four futures markets for exactly this reason) or a longer XAUUSD history. About 4,727 4h C2s are needed; three years gives 1,367.

2. **Test C2-ness separately from wick size.** The 4h signal here is mostly the former, and it is the cheaper hypothesis to check.

3. **Do not re-test on 15m or 1h.** Two independent methods now agree there is nothing there, and a third look at the same data is p-hacking, not replication.

