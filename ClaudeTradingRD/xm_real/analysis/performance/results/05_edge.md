
## A. Fixed-horizon forward return of the entries (pts, signed in the trade direction, net of spread)

unit = entry decision (first clip), n = 121 (42 buys, 79 sells); control n = 4,816; CI = bootstrap over the 27 flat-to-flat episodes
| horizon_min | n | mean | median | pct_pos | ci_lo | ci_hi | ctrl_mean | ctrl_pct_pos | sd | mean_minus_ctrl |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 121 | -0.62 | -0.68 | 28.10 | -0.80 | -0.39 | -0.57 | 31.75 | 1.49 | -0.05 |
| 5 | 121 | -0.52 | -0.68 | 38.84 | -1.04 | 0.01 | -0.67 | 40.64 | 3.38 | 0.15 |
| 15 | 121 | -0.69 | -1.27 | 40.50 | -1.53 | 0.74 | -0.87 | 43.40 | 5.90 | 0.18 |
| 30 | 121 | -0.46 | 0.42 | 54.55 | -1.53 | 1.34 | -1.17 | 44.24 | 8.11 | 0.70 |
| 60 | 119 | -0.82 | -1.89 | 43.70 | -2.03 | 1.57 | -1.41 | 46.10 | 10.95 | 0.59 |
| 120 | 120 | 0.56 | -0.62 | 47.50 | -2.11 | 4.02 | -1.90 | 47.11 | 14.78 | 2.46 |
| 240 | 119 | -0.22 | -1.74 | 48.74 | -6.54 | 3.66 | -2.10 | 46.64 | 18.83 | 1.88 |
| 480 | 106 | 0.23 | -0.13 | 50.00 | -5.52 | 4.47 | -0.87 | 47.31 | 28.31 | 1.10 |

buys (n=42): 5m -0.41 (ctrl -0.82), 30m -4.01 (ctrl -2.07), 60m -5.25 (ctrl -3.20), 240m -6.75 (ctrl -8.27)
sells (n=79): 5m -0.58 (ctrl -0.59), 30m +1.43 (ctrl -0.68), 60m +1.50 (ctrl -0.45), 240m +3.22 (ctrl +1.21)
fresh_flat decisions (n=27): 5m -0.97, 30m +1.16, 60m +2.65, 240m +1.19
add_to_loser decisions (n=68): 5m -0.43, 30m -0.08, 60m -0.30, 240m +1.90
counter_side decisions (n=21): 5m -0.37, 30m -3.31, 60m -5.99, 240m -7.24

## B. Symmetric bracket TP = SL = k pts on the same entries (quote-resolved on S5, same-bar tie = stop)

| k_pts | n_resolved | win_pct | ci_lo | ci_hi | mean_pts | ctrl_n | ctrl_win_pct | ctrl_mean_pts | breakeven_win_pct |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 121 | 37.19 | 28.57 | 46.67 | -0.77 | 4816 | 37.08 | -0.77 | 50.00 |
| 5 | 121 | 41.32 | 34.41 | 51.85 | -0.87 | 4816 | 40.66 | -0.93 | 50.00 |
| 8 | 121 | 42.98 | 36.31 | 57.50 | -1.12 | 4816 | 42.40 | -1.22 | 50.00 |
| 12 | 121 | 45.45 | 37.14 | 58.62 | -1.09 | 4816 | 45.14 | -1.17 | 50.00 |
| 20 | 118 | 49.15 | 33.33 | 57.78 | 0.06 | 4733 | 48.15 | -0.65 | 50.00 |

## C. The actual trades with a hard stop added (static replay: same entries, same exits unless the stop is hit first)

stop fills at exactly -X pts (no slippage; optimistic in news bars). 'flat' = every position re-sized to 0.04 lots. Hedge legs of close-by pairs dropped (n=174).
| stop_pts | n_stopped | win_pct | net_usd | PF | net_usd_flat004 | exp_pts | winners_killed | usd_lost_from_killed_winners | usd_saved_on_losers |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 122 | 29.89 | -780.52 | 0.51 | -637.60 | -0.92 | 83 | 4452.77 | 3181.42 |
| 5 | 87 | 41.95 | -816.00 | 0.63 | -621.80 | -0.89 | 62 | 4139.33 | 2832.50 |
| 8 | 67 | 51.15 | -650.80 | 0.77 | -606.08 | -0.87 | 46 | 3598.44 | 2447.38 |
| 10 | 58 | 56.32 | -704.96 | 0.77 | -570.08 | -0.82 | 37 | 3420.60 | 2215.38 |
| 15 | 48 | 62.07 | -920.24 | 0.75 | -625.36 | -0.90 | 27 | 3055.88 | 1635.38 |
| 20 | 36 | 66.09 | -1129.80 | 0.73 | -674.92 | -0.97 | 20 | 2853.68 | 1223.62 |
| 30 | 11 | 73.56 | 296.08 | 1.08 | 823.12 | 1.18 | 7 | 1167.96 | 967.80 |
| 50 | 2 | 77.59 | 894.96 | 1.27 | 1742.00 | 2.50 | 0 | 0.00 | 401.40 |
| none (actual) | 0 | 77.59 | 493.56 | 1.13 | 1608.20 | 2.31 | 0 | 0.00 | 0.00 |

## D. How much of the profit was rescued from deep adverse excursion

| mae_at_least | winners | share_of_winners_pct | usd | share_of_gross_profit_pct | median_hold_min |
|---|---|---|---|---|---|
| 0 | 135 | 100.00 | 4254.25 | 100.00 | 28.63 |
| 3 | 83 | 61.48 | 3426.77 | 80.55 | 90.92 |
| 5 | 62 | 45.93 | 2869.33 | 67.45 | 146.74 |
| 10 | 37 | 27.41 | 1940.60 | 45.62 | 258.77 |
| 15 | 27 | 20.00 | 1435.88 | 33.75 | 314.61 |
| 20 | 20 | 14.81 | 1253.68 | 29.47 | 346.86 |
| 30 | 7 | 5.19 | 327.96 | 7.71 | 869.28 |

winners: median gain 4.70 pts vs median MAE 4.34; mean gain 7.45 vs mean MAE 8.53; MAE/gain ratio median 0.81
losers (n=39): mean loss -15.49 pts, median -9.51; exit kinds {'SO': 33, 'CLOSE_BY': 4, 'MOBILE': 2}; voluntary (MOBILE) losing exits: 2 for -30.26 USD
break-even win rate implied by avg win 31.51 / avg loss -96.50: 75.4% (actual 77.6%)
in points: avg win 7.45 / avg loss -15.49 -> break-even 67.5%
underwater share of holding time: winners median 54%, losers median 81%
median hold: winners 28.6 min, losers 53.6 min; mean hold: winners 125.4, losers 246.9

## E. Sampling error

actual USD: total 490.83 over 27 episodes; episode mean 18.18, sd 199.76, t = 0.47; bootstrap 95% CI of the total [-1633, 2417], P(total <= 0) = 30.9%; without best episode 57.23, without worst 1051.01
flat 0.04-lot USD: total 1608.20 over 27 episodes; episode mean 59.56, sd 183.49, t = 1.69; bootstrap 95% CI of the total [-205, 3451], P(total <= 0) = 4.2%; without best episode 1091.68, without worst 1902.36
per position (treated as independent, which they are not): mean 2.76, sd 101.66, t = 0.36
lot-size effect: the 10 positions above 0.04 lots net -1652.11 USD; the 168 positions at <= 0.04 lots net 2142.94; everything re-sized to 0.04 lots: 1608.20 USD (402.0 pts over 174 positions)
days: 6 (3 up / 3 down), day mean 81.80, sd 941.91, t = 0.21
minimum detectable per-position edge at n=178, sd 102 USD (80% power, 5% two-sided, iid): 21.3 USD per position vs observed 2.76