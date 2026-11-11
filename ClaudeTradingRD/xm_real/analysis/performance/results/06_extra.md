
## Drawdown episodes (cash flows removed): realised P&L vs P&L including floating

realised (balance) curve:
| peak | trough | recovered | depth_usd | peak_value | hours_under |
|---|---|---|---|---|---|
| 11-10 09:01 | 11-11 07:04 | never | -2652.07 | 3142.90 | 17.74 |
| 11-04 15:13 | 11-04 16:41 | 11-05 14:41 | -294.16 | 266.20 | 22.02 |
| 11-06 16:34 | 11-09 00:34 | 11-09 06:29 | -200.10 | 1836.22 | 5.91 |

realised + floating (equity) curve, 5 s closes:
| peak | trough | recovered | depth_usd | peak_value | hours_under |
|---|---|---|---|---|---|
| 11-10 09:08 | 11-11 07:04 | never | -2292.38 | 2783.21 | 21.92 |
| 11-09 19:11 | 11-09 20:37 | 11-10 09:02 | -1123.44 | 2663.02 | 13.84 |
| 11-09 07:01 | 11-09 07:58 | 11-09 11:19 | -447.62 | 1997.54 | 4.31 |
| 11-04 15:22 | 11-05 05:33 | 11-05 14:41 | -405.74 | 281.32 | 23.32 |
| 11-06 17:43 | 11-09 02:41 | 11-09 06:29 | -332.38 | 1907.99 | 60.76 |
| 11-09 15:07 | 11-09 16:12 | 11-09 16:26 | -309.95 | 2278.25 | 1.31 |

while the account was still making new highs (to 11-10 09:01): max balance-curve drawdown -294.16 USD, max equity-curve drawdown -1123.44 USD
gap between the two curves (= open loss the balance does not show): mean 89.67, p90 212.44, max 1476.33 USD at 11-10 11:08

## Account wipe-outs (equity after each stop-out event, before any new deposit)

| event | first_so | ist | so_deals | account_before | so_cash | equity_after | open_lots_after | bonus_burnt_exp06 | broker_reset_exp01 | next_deposit_usd | hours_to_redeposit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 11-04 16:40:14 | 22:10 | 3 | 296.83 | -302.12 | 2.67 | 0.00 | 35.83 | 0.00 | 75.11 | 11.98 |
| 1 | 11-09 00:34:33 | 06:04 | 2 | 202.15 | -200.10 | 2.05 | 0.00 | 0.00 | 0.00 | 113.68 | 1.94 |
| 2 | 11-10 13:30:03 | 19:00 | 5 | 2032.76 | -2040.72 | -7.96 | 0.00 | 139.99 | 7.96 | 125.65 | 0.17 |
| 3 | 11-10 15:51:39 | 21:21 | 1 | 332.46 | -72.40 | -2.56 | 0.32 | 55.76 | 0.00 | 145.00 | 1.54 |
| 4 | 11-10 16:06:39 | 21:36 | 1 | 10.90 | -4.78 | 1.83 | 0.01 | 8.80 | 0.00 | 145.00 | 1.29 |
| 5 | 11-11 05:37:16 | 11:07 | 19 | 704.24 | -707.72 | 0.00 | 0.00 | 79.02 | 3.48 | 96.67 | 0.54 |
| 6 | 11-11 07:03:29 | 12:33 | 3 | 153.85 | -150.88 | 2.97 | 0.00 | 48.31 | 0.00 | 0.00 |  |
sum of account value (balance + credit) standing just before the 7 events: 3733.19; sum left after: -1.00; EXP06 total 367.71, EXP01 total 11.44

## Two phases of the cash account

phase 1: 11-04 .. 11-06 (withdrawals every day): deposits 126.80 (2), withdrawals 1805.00 (7), trading P&L 1836.22, net cash to owner +1678.20
phase 2: 11-09 .. 11-11 (no withdrawals): deposits 757.94 (6), withdrawals -0.00 (0), trading P&L -1345.39, net cash to owner -757.94

withdrawals vs the balance just before:
| time | withdrawn | balance_before | balance_after | share_pct | open_lots | floating |
|---|---|---|---|---|---|---|
| 11-04 14:19 | 60.00 | 228.03 | 168.03 | 26.31 | 0.06 | 1.95 |
| 11-05 17:56 | 516.00 | 716.00 | 200.00 | 72.07 | 0.00 | 0.00 |
| 11-05 20:32 | 111.00 | 392.72 | 281.72 | 28.26 | 0.00 | 0.00 |
| 11-05 20:53 | 81.00 | 281.72 | 200.72 | 28.75 | 0.08 | -34.27 |
| 11-06 03:01 | 364.00 | 564.22 | 200.22 | 64.51 | 0.00 | 0.00 |
| 11-06 03:15 | 69.00 | 269.98 | 200.98 | 25.56 | 0.00 | 0.00 |
| 11-06 16:48 | 604.00 | 804.62 | 200.62 | 75.07 | 0.08 | -0.79 |

## Basis clock check (does a time offset between XM deal stamps and OANDA bars improve the fit?)

| shift_s | n | mad | sd | median_buy | median_sell |
|---|---|---|---|---|---|
| -4 | 209 | 0.21 | 0.36 | 0.11 | 0.03 |
| -2 | 201 | 0.14 | 0.26 | 0.10 | -0.03 |
| -1 | 206 | 0.13 | 0.22 | 0.06 | -0.03 |
| 0 | 212 | 0.13 | 0.20 | 0.07 | -0.04 |
| 1 | 218 | 0.14 | 0.21 | 0.03 | -0.04 |
| 2 | 221 | 0.15 | 0.24 | -0.01 | -0.06 |
| 4 | 234 | 0.23 | 0.34 | -0.09 | -0.11 |

## Entry style: with or against the preceding move (entry decisions, first clip)

| lookback_min | n | against_move_pct | median_prior_move_pts | mean_prior_move_pts | fresh_flat_n | fresh_flat_against_pct | fresh_flat_median |
|---|---|---|---|---|---|---|---|
| 5 | 121 | 75.21 | -2.43 | -2.41 | 27 | 70.37 | -3.40 |
| 15 | 121 | 73.55 | -2.95 | -2.36 | 27 | 74.07 | -3.10 |
| 60 | 121 | 66.12 | -3.20 | -3.51 | 27 | 74.07 | -7.94 |
| 240 | 121 | 64.46 | -10.22 | -8.50 | 27 | 62.96 | -8.30 |

## Exit style

take-profit attached at close: 141 of 178 positions; stop-loss attached: 1 (a hedge leg)
TP distance from entry (pts, n=141): p10 5.1, p25 5.2, median 12.3, p75 14.4, p90 22.5; histogram: (0, 4]: 5, (4, 6]: 37, (6, 9]: 13, (9, 12]: 15, (12, 16]: 40, (16, 25]: 20, (25, 50]: 11
hand-closed winners (n=92): median gain 3.70 pts, median hold 19.9 min; where a TP was set (n=74) they took 53% of the TP distance (median)
TP exits (n=42): median gain 11.01 pts, median hold 111.2 min, median MAE 14.49 pts
close events (closes within 5 s merged): 94; closing 2+ positions at once: 38 events covering 122 positions; winning close events 81 (86.2%)
losing positions (n=39): ended by margin stop-out 33, by hedge + close-by 4, closed by hand 2 (-30.26 USD)

## Headline recomputed from deals_raw.json only (independent of trades.csv)

exit deals 178, entry deals 178; sum cash 490.83; exit deals with cash > 0: 135 (75.8%), = 0: 4, < 0: 39; SO deals 34 sum -3478.72; TP deals 42 sum 2139.16; lots traded (entries) 7.64

## Regime context (OANDA M1 mid, 2026-07-16 .. 2026-11-11)

daily range, trade week (11-04..11-10, n=5 full days): median 93.7, min 77.3, max 151.8 pts; prior 16 weeks (n=79 days): median 80.9, p25 61.0, p75 102.7, p90 129.2; trade-week median is at the 67th percentile of the prior 16 weeks
price level: trade week 3920..4148; week net change +95.4 pts

chance that gold moves at least X pts against a one-directional position within H hours of a random minute (M1 closes, ignores session gaps):
| period | adverse_pts | within_1h_pct | within_4h_pct | within_12h_pct | within_24h_pct |
|---|---|---|---|---|---|
| trade week | 13 | 18.80 | 49.10 | 63.90 | 72.80 |
| trade week | 26 | 5.10 | 25.90 | 48.70 | 59.60 |
| prior 16 weeks | 13 | 16.30 | 47.30 | 70.00 | 78.40 |
| prior 16 weeks | 26 | 2.90 | 19.40 | 45.60 | 59.60 |

## After each stop-out: did price come back to the stopped positions' entries (within the data, to 11-11 13:43 UTC)?

| event | first_so | stopped_side | n | lots | entry_min | entry_max | so_price | came_back_n | hours_to_come_back_median | hours_max | further_adverse_pts_before | hours_of_data_after |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 11-04 16:40 | SELL | 3 | 0.12 | 4031.55 | 4038.62 | 4059.79 | 3 | 44.81 | 45.61 | 88.10 | 165.04 |
| 1 | 11-09 00:34 | SELL | 2 | 0.08 | 4063.41 | 4063.47 | 4088.62 | 2 | 36.92 | 36.93 | 60.81 | 61.15 |
| 2 | 11-10 13:30 | BUY | 5 | 0.36 | 4079.09 | 4118.76 | 4051.20 | 0 |  |  | 38.31 | 24.23 |
| 3 | 11-10 15:51 | BUY | 1 | 0.04 | 4053.04 | 4053.04 | 4034.94 | 1 | 13.37 | 13.37 | 21.65 | 21.87 |
| 4 | 11-10 16:06 | BUY | 1 | 0.01 | 4044.74 | 4044.74 | 4039.96 | 1 | 9.46 | 9.46 | 26.67 | 21.62 |
| 5 | 11-11 05:37 | BUY | 12 | 0.48 | 4061.06 | 4062.29 | 4057.45 | 12 | 0.05 | 0.06 | -0.66 | 8.11 |
| 5 | 11-11 05:37 | SELL | 7 | 0.44 | 4042.55 | 4059.31 | 4058.06 | 7 | 6.34 | 6.93 | 9.40 | 8.11 |
| 6 | 11-11 07:03 | SELL | 3 | 0.20 | 4056.11 | 4058.13 | 4064.30 | 3 | 1.44 | 1.44 | 3.67 | 6.67 |