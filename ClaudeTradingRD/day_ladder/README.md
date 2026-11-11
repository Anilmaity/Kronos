# Day-Ladder gold scalper (lab, 2026-11-11)

Operator brief: a scalper that trades every day, wins 70-80 % of trades, uses averaging and
dynamic size, never loses more than 2-3 % in a day, and can reach +6 % (or more) on a good day.
Profitability was explicitly not the goal. Follows the [XM Real study](../xm_real/).

- `study_daily.py` — daily-movement study, 16 months of M1 (414 days). Median daily range 81 pts;
  busiest hours 00-01, 05 and 12-15 UTC; 31 % of daily highs/lows form in 23:00-01:00 UTC.
  After a 5-minute push, continuation vs reversal changes sign between TRAIN and TEST in most
  hours -> no stable directional rule; the study is used only to pick the trading hours.
- `ladder.py` — the strategy and backtest. `python ladder.py grid` (TRAIN grid),
  `python ladder.py base_pct=1.25 press=1.0 s_atr=6 pull=1.0` (the pick; output in `results_pick.txt`).

## Rules (the pick, chosen on TRAIN = first 60 % of days)
- Entry: with the trend (close vs EMA240 of M1) after a 5-minute pullback of >= 1.0 x ATR30, active hours only.
- Basket: up to 3 legs (40/30/30 %) at 0, S/3, 2S/3 against; one hard stop at S = 6 x ATR30 (6-30 pts);
  lots sized so a full stop loses exactly the risk budget. Target S/3 beyond the average entry.
- Ladder: risk = 1.25 % + 1.0 x (today's profit %), max 3 %; never more than the room left to the floor.
  Day floor -2.5 %; the floor trails 4 % under the day's peak, and 2 % under it once +6 % is reached.
  Risk % shrinks as equity grows above the start. Week +18 % and month +60 % caps.
- Flat for the 08:30 and 10:00 New York releases and at 20:50 UTC; 60-180 min time stop.

## Result (cost 0.6 pt round trip)
| | TRAIN (205 days) | TEST (138 days) | Last 2 weeks (11 days) |
|---|---|---|---|
| Trades per day | 9 | 12 | 10 |
| Win rate | 71.9 % | 74.8 % | 71.4 % |
| Profit factor | 0.75 | 0.83 | 0.67 |
| Worst day | -3.07 % | -2.63 % | -2.61 % |
| Best day | +9.89 % | +8.85 % | +1.88 % |
| Days >= +6 % | 4 % | 6 % | 0 |
| Losing days | 80 % | 78 % | 10 of 11 |
| Total | -87 % | -66 % | -14.9 % |

Met by construction: daily loss cap, daily trading, 70-80 % win rate, scalping holds (median 12 min).
Not met: "+6 % easily". It happens on about 1 day in 20. Trading against the trend gives the same
picture, and at zero cost the TEST result is flat (PF 0.99): the entry has no edge and the spread
(about 30 % of each 2-pt win) is the loss. With a -2.5 % floor and a +6 % target, a no-edge entry can
reach the target on at most ~29 % of days even with zero cost; a 70-80 % win rate makes each win a
third of a loss, so it needs ~7 net wins in a row from the floor's two stops.

## Harder-pressing variant (same day, `grid_press.py`, chosen on TRAIN)
Base risk 2.5 %, press 1.0, per-basket cap 10 %, no trailing floor before the target, 3 % giveback after it.
`python ladder.py base_pct=2.5 press=1.0 max_pct=10 trail=99 giveback=3 pull=1.0` -> `results_press_hard.txt`.

| | TRAIN | TEST | Last 2 weeks |
|---|---|---|---|
| Trades per day | 4 | 5 | 5 |
| Win rate | 73.7 % | 75.9 % | 72.0 % |
| Profit factor | 0.77 | 0.87 | 0.88 |
| Worst day | -2.92 % | -2.81 % | -2.53 % |
| Best day | +14.1 % | +14.0 % | +6.1 % |
| Days >= +6 % | 10 % | 10 % | 1 of 11 |
| Losing days | 79 % | 78 % | 8 of 11 |
| Total | -77 % | -53 % | -5.0 % |

This is the ceiling found in 72 TRAIN cells: about one +6 % day in ten, none at +20 %. A losing day now
ends after one or two stops, so "constant trading" is traded away for the bigger days.

## Bold ladder check (`grid_bold.py`, TRAIN)
Every basket risks the whole room to the day's floor (the play that maximises the chance of reaching a
target inside a loss limit). 12 TRAIN cells: best is 9.6 % of days at +6 %, none at +20 %, PF 0.77 —
identical to the harder-pressing pick, which already risked the whole room on its first basket.
Wider stops (9, 12 x ATR) and a 6 % giveback are worse and let the worst day slip to about -4 %.
Averaging keeps wins small (a one-leg win earns ~0.19 of the risk, not 0.33), so ~10 % is the ceiling
for this brief; the arithmetic limit for any no-edge design is 29 %.

## Ceiling demonstration and the single-entry "let it run" ladder
`ceiling_demo.py` (output `ceiling_demo.txt`): simulated best play at profit factor 0.70-0.80 inside a -2.5 % floor.
With 70-80 % win-rate scalps the most any strategy can do is +6 % on ~18-22 % of days and +20 % on ~5-7 %.

That showed room above the averaging ladders (10 % / 0 %), so averaging became a setting (`w`) and the grid was re-run
on TRAIN (`grid_bold.py`). Single entry, whole room risked each trade, stop 6 x ATR, target a third of the stop:

| | giveback 3 % after +6 % | floor fixed at -2.5 % ("let it run") |
|---|---|---|
| TEST win rate / PF | 71.5 % / 0.95 | 71.5 % / 0.97 |
| TEST worst day | -2.61 % | -2.64 % |
| TEST days >= +6 % | 15.6 % | 9.0 % |
| TEST days >= +20 % | 0 | 7.2 % (best +34.4 %) |
| TEST losing days | 76 % | 91 % |
| TEST total | -23.5 % | -15.3 % |
| Last 2 weeks | 1 day +9.1 %, 1 day +5.1 %, 9 red, -8.9 % | 1 day +30.7 %, 9 red, +3.8 % |

`python grid_bold.py pick 6 1.0 3 single` / `... 99 single` -> `results_single.txt`.
Caveats: a big day comes from ~9 wins in a row with the whole day's profit re-risked each time (late trades risk
15 %+ of the account on a 6-pt stop, ~3 lots on $10k); a firm that measures daily loss from peak equity instead of
the day's starting balance would count the give-back as a breach; the weekly +18 % cap then stops the week.

## Range Grid Scalper (`range_scalp.py`) — the XM Real trader's three profitable days, codified
What 11-05 / 06 / 09 had in common vs 11-10 / 11: oscillating market (net move 7-20 % of the path vs 34 % on the
trending 11-10), one 0.04 clip throughout (losing days went to 0.12 and 0.20), mostly sells into pushes up, winners
of 5-9 pts held 30-100 min, 0-2 margin stop-outs (7 and 22 on the losing days).
Rules: trade only while the last 120 min oscillate; fade a 5-min push in the outer 30 % of that range; one fixed
clip; add a clip every G pts against up to K; small shared target; hard stop one step past the last clip sized to
0.5 % of equity; day floor -2.5 %; flat for the New York releases.

TRAIN grid (36 cells, `range_grid_train.csv`): the smaller the target the worse — PF ~0.60 at 1.2 pts, ~0.75 at 2 pts,
~0.90 at 4 pts. The 0.6-pt spread is half of a 1.2-pt target.

| cost 0.6 | TP 2 pts (G 6, K 3) TRAIN / TEST / last 2 wks | TP 4 pts (G 6, K 3) TRAIN / TEST / last 2 wks |
|---|---|---|
| Baskets per day | 16 / 16 / 13 | 13 / 12 / 11 |
| Win rate | 89.6 % / 87.8 % / 90.3 % | 81.8 % / 79.6 % / 83.6 % |
| Profit factor | 0.77 / 0.69 / 0.79 | 0.91 / 0.80 / 0.97 |
| Worst day | -1.96 % / -1.34 % / -0.60 % | -1.67 % / -1.33 % / -0.44 % |
| Best day | +0.95 % / +0.77 % / +0.60 % | +1.19 % / +1.39 % / +1.12 % |
| Total | -21.9 % / -22.3 % / -0.9 % | -11.8 % / -19.4 % / -0.2 % |

Zero cost is flat in both (PF 0.98-1.06): the fade has no edge, the spread is the loss. Fading vs following the push
makes no consistent difference; dropping the oscillation filter triples the trade count and the loss.
On the trader's own three profitable days the 2-pt version made -0.60 %, -0.30 %, -0.10 %: his profit came from
5-9-pt winners held through deep drawdowns without a stop, which a hard-stopped small-target scalper does not reproduce.
`results_range.txt` has the full output.

### Range scalper at a 0.2-pt spread (operator's figure; `results_range_spread02.txt`)
The study measured 0.59 pt on the XM Real fills and 0.48 pt on OANDA; 0.2 pt is a raw-spread account before commission.
TRAIN grid re-run at 0.2: PF 0.75-0.82 at 1.2 pts, 0.89-0.94 at 2 pts, 0.96-1.05 at 4 pts.
- 2-pt target (G 6, K 3): TRAIN / TEST / last 2 wks — win 91.4 / 89.6 / 91.8 %, PF 0.94 / 0.80 / 0.95, worst day -1.59 / -1.12 / -0.51 %, total -5.5 / -13.2 / -0.2 %.
- 1.2-pt target (G 4, K 4): win 94.1 / 94.1 / 95.1 %, PF 0.82 / 0.84 / 0.99, total -16.3 / -9.3 / 0.0 %.
- Best on TRAIN (4 pts, G 3, K 3): PF 1.05 on TRAIN (+23.9 %) but 0.89 on TEST (-28.1 %) — did not hold out of sample.

## Dynamic Range Scalper (`range_dyn.py`) — more clips, volatility-based averaging, adaptive exit, FundingPips cost
Cost 0.25 pt = the operator's 0.2-pt FundingPips spread + $2.50/lot per side commission measured from the account's
own deals (`broker_deals`, FundingPips2). Adds: step = STEP x ATR30, a clip only when price is a step beyond the last
fill and the last closed minute turned back; target = TPA x ATR30 shrinking 30 % per extra clip; hard stop (K+1) steps out.

TRAIN (54 + 64 cells, `dyn_grid_train.csv`, `dyn_grid2_train.csv`):
- reversal-bar rule for adds helps (PF 0.98 vs 0.93 without);
- closing when the 2-hour range breaks hurts (PF 0.86 vs 0.98): it books losses that otherwise come back;
- more clips do not help: K 4 > 6 > 8 (0.98 / 0.94 / 0.90); deep grids with wide steps barely trade;
- longer holds (240 -> 600 min) change nothing.

Pick K 4, step 1.5 ATR, target 2 ATR, decay 0.7, no range-break exit (`results_dyn.txt`):
| cost 0.25 | TRAIN | TEST | Last 2 weeks |
|---|---|---|---|
| Baskets per day | 14.7 | 14.7 | 12.5 |
| Win rate | 83.1 % | 81.5 % | 81.9 % |
| Profit factor | 0.98 | 0.84 | 0.76 |
| Worst / best day | -1.50 / +1.44 % | -1.80 / +1.22 % | -1.08 / +0.75 % |
| Total | -3.0 % | -16.2 % | -2.0 % |

At zero cost TEST is PF 0.91 (TRAIN 1.12): the TRAIN near-break-even does not hold out of sample, and on unseen data the
dynamic version loses even before costs. Fading vs following the push is again indistinguishable (TEST 0.84 vs 0.89).

## Time stop and stop-and-reverse (2026-11-12; `results_timestop.txt`, `results_reverse.txt`)
Operator's ideas: close every trade within 5 or 10 minutes (re-entry allowed), and open the opposite side when a trade fails.
Base: the dynamic pick (K 4, step 1.5 ATR, target 2 ATR, cost 0.25).

Holding time in the 4-hour-limit baseline (TRAIN): 0-5 min +$2,461 (92 % wins), 6-10 min +$1,209, 11-20 min flat,
21-40 min -$1,187, 41-80 min -$1,997, 80+ min -$788. So long holds are where the money goes — but that is a selection
effect: a trade is "short" because it reached its target quickly.

Forcing the exit:
| | 5-min stop | 10-min stop | 4-hour limit |
|---|---|---|---|
| TRAIN win / PF / total | 49.4 % / 0.78 / -18.1 % | 55.3 % / 0.81 / -17.6 % | 83.1 % / 0.98 / -3.0 % |
| TEST win / PF / total | 49.7 % / 0.77 / -13.2 % | 53.6 % / 0.79 / -13.6 % | 81.5 % / 0.84 / -16.2 % |
| TEST worst day | -0.82 % | -0.72 % | -1.80 % |
| Last 2 weeks PF / total | 0.66 / -1.6 % | 0.75 / -1.4 % | 0.76 / -2.0 % |
| Exits at the time stop | 79 % | 63-64 % | 4-5 % |

Reverse after a losing time stop or hard stop (TRAIN, `reverse` = max flips in a row): reverse entries win 47-52 % and
lose money in all six cells (-$585 to -$1,253 on top of the first entries); PF 0.76-0.79 vs 0.78-0.81 without.
Best TRAIN cell is no reversal, so nothing new went to TEST. Consistent with the earlier controls: fading and following
the push are indistinguishable, so the opposite side has no edge either and each flip pays the cost again.

## Hedge-and-average scalper (`hedge_avg.py`, `hedge_test.py`, 2026-11-12)
Operator's idea: open a buy and a sell together; close whichever reaches its target; average into the other; exit that
side at no profit / no loss. Two readings were coded: `be="side"` (the averaged side exits at its own average entry, so a
clean cycle keeps the banked target) and `be="cycle"` (the whole cycle exits at zero).

TRAIN grid, 48 cells (`hedge_grid_train.csv`), cost 0.25:
- `be="cycle"` can never win — its best outcome is zero and every stop or time exit is a loss (PF 0 in all cells).
- `be="side"` best cell: target 2 ATR, step 2.5 ATR, 4 adds, 60-min limit.

| be="side" pick | TRAIN | TEST | Last 2 weeks |
|---|---|---|---|
| Cycles per day | 17.3 | 19.3 | 19.3 |
| Win rate | 78.1 % | 78.6 % | 79.2 % |
| Profit factor | 0.77 | 0.72 | 0.78 |
| Worst day | -1.58 % | -2.58 % | -0.80 % |
| Total | -23.3 % | -28.4 % | -1.7 % |
| Zero-cost PF | 0.94 | 0.92 | 1.01 |

Worse than the one-sided dynamic scalper (TEST PF 0.84). A buy and a sell held together are a flat position that pays
two spreads; after the first target the cycle is exactly "a fade entered one target later", with its profit capped at
that target and its loss at the hard stop.

## Two-sided ping-pong scalper (`ping_pong.py`, 2026-11-12) — the closest replica of the profitable days
Read from the 11-05 trade sequence and measured on all six days: each clip has its own 11-14-pt target (median winner
captured 5-9 pts), an opposite clip is opened seconds after a target is hit (7 times on 11-05), buys and sells are open
together part of the time (20 % on 11-05, 1 % on 11-06, 9 % on 11-09 — and 72 % on the losing 11-11), clips come in
fixed-size pairs, and no loss is ever taken. Rail added: close everything when the floating loss reaches 1 % of equity.

TRAIN grid, 32 cells (`pingpong_grid_train.csv`), cost 0.25: best PF 0.99 at target 12 / step 8 / 5 clips per side,
oscillation filter on, flip OFF. Flipping after a win lowers PF (0.93), as does dropping the filter (0.93).

| pick | TRAIN | TEST | Last 2 weeks |
|---|---|---|---|
| Clips per day | 14.1 | 12.5 | 11.3 |
| Win rate | 64.7 % | 57.4 % | 62.1 % |
| Profit factor | 0.99 | 0.81 | 0.98 |
| Worst / best day | -2.86 / +3.17 % | -3.01 / +1.90 % | -1.47 / +0.95 % |
| Total | -2.8 % | -23.9 % | -0.2 % |
| Exits: target / equity stop / flat | 57 / 19 / 24 % | 47 / 21 / 33 % | 49 / 21 / 30 % |

On his own days: 11-05 +0.93 %, 11-06 -0.29 %, 11-09 +0.10 %, 11-10 -0.77 %, 11-11 +0.30 %. Same sign as his on
11-05 and 11-09 and far smaller on both sides: his +$1,191 on 11-05 came from 0.08-0.16 lots on a ~$200 balance with
nothing to stop a loss, which is exactly what the 1 % equity stop removes.

## Fit to the trader's four days (`fit_days.py`, 2026-11-12) — operator's goal, an in-sample fit by design
Goal: make the strategy's daily result match the XM Real trader's on 11-04 / 05 / 06 / 09 (10th and 11th ignored).
`ping_pong.py` gained the behaviours read from his trade lists: side bias (`sides`), hand profit-taking (`take`),
entry hours (`h0`/`h1`), optional news/end-of-day flat, fixed lot, no equity stop. Random search (4,000-5,000 draws) plus
hill-climbs, objective = total absolute error on the four daily results (by the day a position was opened).

Best two-sided fit (`fit_days_best_twosided.json`): 0.10-lot clips, 6-pt target, hand-take at +2 pts when the minute turns,
adds every 8 pts up to 5 per side (no reversal-bar wait), flip to the other side after a target, entries 08-19 UTC on a
0.5-ATR push in the outer 30 % of the 2-hour range, no oscillation filter, held through news and overnight, NO loss limit.

| | 4 Nov | 5 Nov | 6 Nov | 9 Nov | total |
|---|---|---|---|---|---|
| Trader | -$28 | +$1,191 | +$473 | +$1,187 | +$2,823 |
| Fitted strategy | -$24 | +$1,057 | +$361 | +$1,219 | +$2,613 |

Outside the four days, same settings (`results_fit_days.txt`): 10-11 Nov -$2,171; October +$3,735 (PF 1.30, worst day
-$1,976); September -$2,581; August -$7,121 (worst day -$7,202); full 16 months -$37,504, win rate 88 %, PF 0.92,
worst day -$9,475, deepest fall in closed balance -$41,988 — on a $10,000 account that is ruin several times over.
An unrestricted search found a buy-only setting that fits about as well (`fit_days_best_buyonly.json`); it is a hindsight
artefact of that week's direction and loses $33,765 over 16 months.
Fifteen settings were tuned to four numbers: the match shows the trader's results CAN be produced by rules of this
shape at this leverage, not that the rules will produce them again.

### Fitted strategy with a $2,000 daily loss limit (`day_loss_usd`, `results_fit_daylimit.txt`)
When the day is down $2,000 (closed + open, measured from the day's opening value) everything is closed and trading stops
until the next UTC day. The four fitted days are unchanged (the limit never triggers on them).
| | no limit | $2,000 limit |
|---|---|---|
| 10-11 Nov | -$2,171 | -$2,122 (hit on 1 day) |
| October 2026 | +$3,735 | +$1,342 (2 days) |
| September 2026 | -$2,581 | -$4,393 (5 days) |
| August 2026 | -$7,121 | +$998 (4 days) |
| Full 16 months | -$37,504, worst day -$9,475 | -$27,283, worst day -$3,115, limit hit on 74 days |
The closed result of a limit day can exceed $2,000 because positions carried from the day before bring their open loss with
them and the exit is taken at the bar's extreme. On $10,000, a $2,000 day is 20 %.

### Time stop on the fitted strategy (`max_hold`, `hold_mode`; `results_fit_timestop.txt`)
Operator: trending days lose a lot, so close trades after a set time. Tested on top of the $2,000 daily limit, three ways:
every clip, losing clips only, and losing clips only while the 2-hour move is one-way.

| Time stop (all clips) | 4 / 5 / 6 / 9 Nov | Oct 2026 | Sep 2026 | Aug 2026 | 16 months | Win rate | Days at -$1,000 or worse |
|---|---|---|---|---|---|---|---|
| none | -24 / +1,057 / +361 / +1,219 | +1,342 | -4,393 | +998 | -27,283 | 87 % | 87 |
| 10 min | +133 / +216 / +130 / -56 | +235 | -287 | -2,510 | -29,238 | 60 % | 15 |
| 30 min | +225 / -218 / -175 / +111 | +567 | -3,369 | -3,034 | -36,506 | 71 % | 41 |
| 60 min | +187 / -154 / +39 / +55 | +1,809 | -5,614 | -653 | -34,881 | 77 % | 46 |
| 4 hours | +477 / +923 / +359 / +890 | +215 | -7,058 | -282 | -24,429 | 86 % | 76 |

A short time stop does what was asked on trending days — big losing days fall from 87 to 15 — but the 16-month total does
not improve (-24k to -37k in every row) and the match to the trader's four days is lost, because his profit on those days
came from positions held 30-300 minutes. Losers-only and trend-only variants are no better (-22k to -43k).
The worst day stays near -$3,100 in every row: that is the daily limit day, not a slow trend day.
