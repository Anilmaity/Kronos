# XM Real — trades on the gold chart, with account value

Study 4 of the XM Real account study. Every trade of the account (2026-11-04 → 11-11, 178 positions,
symbol GOLD) drawn on the XAUUSD candles, with balance, equity and net open lots underneath.
All inputs are the local files in `../../` — nothing here touches production or a broker.

## Open this first

| file | what it is |
|---|---|
| `xm_real_trades_equity.html` | Interactive chart (7 MB, self-contained, opens offline). Buttons top right: jump to the week or a day, switch 1m / 5m / 15m candles. Mouse wheel zooms time, drag pans; the three panels refit their own scales. Hover a marker for lots, points, net USD, hold time, exit reason, TP/SL, in IST and UTC. |
| `xm_real_week_overview.png` | The whole week, 15m candles, 4800×3000. |
| `xm_real_day_2026-11-04.png` … `-11-11.png` | One per trading day (04, 05, 06, 09, 10, 11 Nov). Cropped to the active part of the session ±45 min; 1m candles when that is ≤10 h (04 and 11 Nov), else 5m. |

## How to read it

- **Top panel** — candles in the house style (green `#089981` up, black down, `#DBDBDB`, no grid, no indicators).
  ▲ buy entry, ▼ sell entry; exit ● manual, ◆ take-profit, ✕ margin stop-out, ■ close-by hedge.
  The line from entry to exit is blue for a profit, orange for a loss closed by hand, thick magenta for a stop-out.
  Stop-out clusters carry a label with the count and the booked loss.
- **Middle panel** — black step = balance (realised). Green = equity = balance + floating P&L, i.e. own money
  marked to market. Dotted grey = the same plus XM's bonus credit, which is what the MT5 app calls "Equity".
  △ deposit, ▼ withdrawal, ◆ bonus credit used up to cover a negative balance after a stop-out.
- **Bottom panel** — net open lots, long above zero, short below.
- Time axis is IST (UTC+5:30). The daily 22:00–23:00 UTC close and the weekend are cut out.

## Scripts (run in this order, from this folder)

```
../../../.venv/bin/python 01_basis.py    # XM vs OANDA price basis            -> basis.json
../../../.venv/bin/python 02_equity.py   # balance / equity / lots, 5 s grid  -> equity_5s.parquet
../../../.venv/bin/python 03_chart.py    # HTML + 7 PNGs, marker-on-candle check
../../../.venv/bin/python 04_facts.py    # the numbers quoted below, from the raw ledgers
```

`run_log.txt` is the full output of the last run of all four. `plotly` and `kaleido` were installed into
`ClaudeTradingRD/.venv` for this (kaleido uses the Chrome already on the Mac).

## What was measured, and how far to trust it

**Price basis** (272 manual market fills; close-by, TP and stop-out fills left out). XM's deal clock matches
OANDA's to within a second. XM ask = OANDA ask + 0.06, XM bid = OANDA bid − 0.05, so the mid basis is +0.004
USD/oz and XM's spread is about 0.58 against OANDA's 0.47. The candles are OANDA M1 mid shifted by that
+0.004 — the shift is invisible; what matters is that it was measured, not assumed.

**Markers on candles.** All 348 entry and exit markers were checked against the 1m candle they fall in: 316
inside its high–low range, 32 outside by at most 0.31 (half a spread, because a buy fills at the ask and the
candle is mid), none further. Two day charts were also inspected at full resolution.

**Equity.** Rebuilt from `trades.csv` and the basis-corrected 5-second bid/ask (longs marked at the bid,
shorts at the ask, 100 oz per lot). For the 94 positions closed by hand, floating P&L one grid step before the
close differs from the booked profit by $1.15 on average (worst $6.71). In the seconds around the 13:30 UTC
news releases a 5-second bar spans 10–30 USD and the same comparison is off by up to $232 on one position,
so the equity line is not reliable inside those seconds. The plotted line is sampled once a minute; the
5-second series is in `equity_5s.parquet`.

**Stop-out level.** One 5-second step before four of the seven stop-out clusters, MT5 equity was 35–50 % of
used margin — consistent with XM's 20 % stop-out level seen through a 5-second grid. The 10 Nov 13:30 UTC
news stop-out went from 474 % to liquidated inside a single step, and the other two were hedged books, where
the simple margin formula used here does not apply.

## What the chart shows

- **Losses are not closed, they are waited out.** 2 of 178 positions were closed by hand at a loss (−$30).
  33 losers ended in a margin stop-out (−$3,484) and 8 more positions (4 pairs) were locked with an opposite
  position and closed-by (−$249). A stop-loss was set on 1 position. Winners: 92 closed by hand, 42 by
  take-profit, 1 stop-out.
- **Balance and equity come apart.** With a position open, floating P&L was negative 71.6 % of the time
  (median −$48, worst −$1,477). At the balance peak of $1,919.01 (10 Nov 11:54 UTC) equity was $554: the
  account was long 0.44 lots and $1,365 under water. Ninety-six minutes later a news candle stopped out five
  longs (0.36 lots) for −$2,041.
- **Entries are stacked.** 129 of 178 entries were made with a same-side position already open, and in 110 of
  those the existing stack was under water (median 3.1 USD/oz). Up to 13 buys or 11 sells open at once, 19
  positions in all; gross exposure peaked at 0.92 lots.
- **The account was emptied repeatedly.** Five minutes after each of the 7 stop-out clusters the balance was
  within a dollar of zero. Of the 8 deposits, 1 opened the account, 5 refilled it from zero (10 minutes to 12
  hours after a stop-out) and 2 were added while open positions were under water (−$183 and −$1,365 floating).
- **Profits were swept out early.** 7 withdrawals, $1,805 in total; five of them left $200–201 on the account.
- **Cash versus trading result.** Trading net is +$490.83. Cash out minus cash in is +$920.26 (withdrawals
  $1,805.00, deposits $884.74). The difference is $379.15 of losses that XM's bonus credit and negative-balance
  reset absorbed, plus $50.28 of deposit-fee rebates.

## Caveats

- Six trading days, one market regime, one account. The chart describes what happened; it does not show that
  the method has an edge.
- A close-by pair is drawn as one round trip, from the first position's entry to the hedge's entry — the real
  fill that fixed the loss. The broker's close-by "price" is the other leg's open price and sits up to 10 USD
  off the market. So 174 round trips are drawn for 178 positions.
- Two withdrawal attempts on 05 Nov were reversed within a second (`CW-ERR` / `CN-ERR`). They show as two
  spikes on the balance line and carry no marker.
- Day charts crop to the active hours; a position opened before the window shows as a line entering from the left.
- In the HTML at week zoom, two date labels collide at the weekend cut and a few cash labels overlap; both
  clear on zooming in.
