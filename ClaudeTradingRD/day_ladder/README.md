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
