# XM Real — trader profile, edge assessment and strategy specification

Synthesis of the four studies in this folder (`performance/`, `entries/`, `exits/`, `chart/`).
Written 2026-11-11. **This is a pre-registration: none of the three candidates in sections 6-8 has been backtested.**
The only new computation here is a trigger-parity check that reads no P&L (section 4, `synthesis/01_trigger_parity.py`).

Account: XM Global MT5 real account, GOLD (= XAUUSD), leverage 1:1000, hedging mode, all orders from the MT5 mobile app.
Sample: 416 deals, 178 positions, 2026-11-04 10:06 to 2026-11-11 07:04 UTC, six trading days. It is the account's whole life.

Units: 1 point = 1 USD per oz. 0.01 lot = 1 oz = 1 USD per point, so 0.04 lots = 4 USD per point. All times UTC.

---

## 1. Short answer

1. **How he trades.** He fades short moves in gold with a fixed 0.04-lot clip, adds another clip each time price goes a few
   points further against him, attaches a take-profit but never a stop, and closes winners by hand at about +4 points.
   Losers are not closed. The broker's margin stop-out is the only loss exit.
2. **Edge.** None is measurable in the entries. The 75.8% win rate comes from the exit shape (small target, no stop) and
   from holding losers until they come back. The week's +490.83 USD is not statistically different from zero, and the
   +920.26 USD of cash taken out exists because the balance was swept to 200 USD during the three days the method worked.
3. **Candidates.** Three, in order of faithfulness. Candidate 1 codifies what he does, including the averaging and the
   missing stop, so its long-run cost can be seen. Candidates 2 and 3 keep his entry habit and put it inside the
   production rails (25-38 USD risk per trade, -250 USD per day). My prior is that all three fail; section 10 says why.

---

## 2. Trader profile

### 2.1 What he does, step by step

| Step | Behaviour | Evidence |
|---|---|---|
| Direction | Sells after price has risen, buys after it has fallen | Prior 5-minute move was 2.39 pts against the trade on average, against -0.08 for random entries at the same hours (124 decisions, q = 0.0005). 65% of decisions sit in the adverse third of the prior 15-minute range. 22 of 124 were taken beyond the prior 60-minute extreme against the trade (17.7% against 4.9% random). |
| First entry | Two taps of 0.04 lots | 18 of 27 fresh entries are a double tap (0.08 lots); 163 of 178 positions are 0.04 lots. |
| Adds | One more 0.04-lot clip when price is a further ~3.7 pts against the last fill | 68 of 124 decisions add to a losing same-side basket. Spacing median 3.7 pts (IQR 2.0-6.5, about 0.7 x M5 ATR), irregular (CV 1.11). 72% the same size as the previous decision, 4% larger. Up to 13 positions on one side. |
| Target | Take-profit on almost every position, often the basket's first target reused | TP on 141 of 178. Distances cluster at 5.06 (n=21) and 13.85-14.26 (n=29); median 12.3. 51 of 141 share a TP price with another open position. |
| Profit-taking | Closes winners by hand before the target | 92 hand-closed winners, median +3.7 pts after 19.9 minutes. 42 positions reached the TP (median +11.0 pts after 111 minutes). |
| Loss-taking | None | Stop-loss on 1 of 178 positions. 2 of 39 losing positions were closed by hand (-30.26 USD). 33 were closed by margin stop-out, 4 by a hedge lock. |
| Hedging | Opens the other side against a losing basket instead of closing it | 22 decisions with only the opposite side open, net -1,417 USD. Four locked pairs closed by close-by, -249.16 USD. |
| Size | Flat for four days, then irregular size-ups | 10 positions above 0.04 lots, net -1,652.11 USD; 8 of them on the last two days. Two 0.12-lot buys alone lost 1,601.40 USD. |
| Risk held | Close to liquidation, through news and the weekend | Right after an entry the book was a median 26 pts from stop-out at 148x effective leverage. Held through the 13:30 UTC moves on 11-06 (+262 USD) and 11-10 (-2,041 USD), and two shorts over the weekend (-200 USD). |
| Money | Small deposits, profits swept out, re-deposit after a wipe-out | Five of seven withdrawals left 200.00-200.98 USD. A deposit of 75-145 USD followed six of the seven wipe-outs within 0.2-12 hours. |
| Hours | About 01:00-21:00 UTC (07:30-02:45 IST), two busy blocks | 90 of 124 decisions fall in 02-06 or 12-16 UTC; none between 22:00 and 01:00. |

### 2.2 Mapped onto recognised scalping methods

| Recognised method | Does he use it? | Basis |
|---|---|---|
| Counter-trend fade (mean-reversion or "rubber-band" scalp) | **Yes.** This is the entry habit. | Section 2.1, direction row. Holds for the 27 fresh entries alone (prior 5-minute move -2.92 pts against -0.07 random, q = 0.002). |
| Flat-lot averaging down (a discretionary grid) | **Yes.** This is the core of the method. | 55% of decisions are adds to a loser, flat size, no fixed step. |
| Martingale (size multiplies after a loss) | No, with late exceptions | Adds are the same size or smaller 96% of the time. The size-ups on 11-10 and 11-11 are the exceptions and the largest losers. |
| Basket take-profit with scalp-outs | **Yes** | Shared TP prices; winners closed by hand at about half the target distance. |
| No stop, the deposit is the stop | **Yes** | 34 margin stop-outs in 7 events cost 3,478.72 USD, 92.4% of gross loss. Equity after each was 2.97 USD or less. |
| Hedge lock instead of a stop | Yes, under pressure | Section 2.1, hedging row. |
| Bankroll rotation (small deposit, bonus credit, sweep, re-deposit) | **Yes** | Section 2.1, money row. 379.15 USD of losses were absorbed by XM bonus credit and negative-balance resets. |
| Momentum or breakout scalping | No | 0 of 27 fresh entries are breakouts, 1 is a momentum entry. |
| ICT / SMC (sweeps, fair-value gaps, displacement, session levels) | No | All occur at random-entry rates (q > 0.2). Entries are not timed to candle closes. |
| News trading | No | He does not target releases. He is simply exposed when they happen. |
| Order-flow or spread scalping (seconds) | No | Median hold 30.5 minutes. |

In one line: **a no-stop, flat-lot averaging fade run on a small, highly leveraged account that is refilled when it dies.**
It is the same family as the "90% win rate" account autopsied in the vault note `MetaAPI Account 5216074f`, with averaging and
1:1000 leverage added.

---

## 3. Edge assessment

### 3.1 Where the profit came from

| Component | USD | n |
|---|---|---|
| Winners closed by hand | +2,109.81 | 92 |
| Take-profit fills | +2,139.16 | 42 |
| Margin stop-outs | -3,478.72 | 34 (33 losers -3,484.00, 1 winner +5.28) |
| Hedge locks (close-by) | -249.16 | 8 legs, 4 pairs |
| Losers closed by hand | -30.26 | 2 |
| **Trading net** | **+490.83** | 178 |

Checked against `trades.csv` in this synthesis: net 490.83, 135 winners / 39 losers / 4 zero, PF 1.13, average win 31.51,
average loss -96.50, daily nets as in the headline.

The same total cut two other ways:
- By size: the 163 positions at 0.04 lots made +2,132.58 USD. The 10 above 0.04 lots lost 1,652.11 USD.
- By side: sells +1,650.78 USD (n=104), buys -1,159.95 USD (n=74). This reflects which days the big positions fell on.

Cash: 884.74 USD deposited, 1,805.00 withdrawn, 0.00 left. Net +920.26 USD = trading 490.83 + bonus credit that covered
losses 367.71 + broker negative-balance resets 11.44 + deposit top-ups 50.28. All of it was banked on 11-04 to 11-06.
On 11-09 to 11-11 nothing was withdrawn and 757.94 USD of fresh deposits was lost.

### 3.2 What the tests say

| Question | Result | Reading |
|---|---|---|
| Do the entries predict direction? | Forward return net of spread, 121 decisions against 4,816 time-shifted controls: -0.52 vs -0.67 pts at 5 min, -0.46 vs -1.17 at 30 min, -0.82 vs -1.41 at 60 min. Confidence intervals span zero from 5 minutes on. | No measurable entry edge. |
| Do they win more than random under a fixed exit? | First touch of +-5 pts: 43.5% real vs 44.6% random (124 decisions, p = 0.83). Symmetric brackets of 3-20 pts: 37-49%, the same as random. | No. |
| Where does the 75.8% come from? | Random entries given his own shape (take 5 pts, no stop until about 28) win 83.5%. His entries under the same shape win 87.9% (p = 0.17). | The win rate is geometry. |
| Does the profit need the deep holding? | 37 of 135 winners were 10 or more points under water first and supplied 45.6% of gross profit. Any hard stop of 3-20 pts laid over his real trades turns the week negative (-651 to -1,130 USD). | Yes. It is deferred loss, and the deferral worked in 20 of 27 episodes. |
| Is the result different from zero? | 27 flat-to-flat episodes: 20 winners +2,216.06, 7 losers -1,725.23 (all 7 ended in a stop-out). t = 0.47. Bootstrap 95% interval of the total: -1,633 to +2,417 USD. 30.9% of resamples are at or below zero. | No. |
| Most favourable honest reading | Every position re-sized to 0.04 lots: +1,608.20 USD (402.0 pts over 174 trades), episode t = 1.69. | Still not a clean estimate: the losing exits are stop-outs whose distance was set by how little money was in the account. |

### 3.3 Verdict

- **Repeatable:** the high win rate (it is produced by the exit shape for any entry) and the wipe-outs (seven in six days).
- **Not shown to be repeatable:** the net profit. With no entry edge the expected result of this shape is roughly minus the
  spread on every lot traded. Spread paid in the week was about 450 USD, the size of the net profit.
- **Not a trading edge at all:** 379.15 USD of the cash result was broker money (bonus credit and negative-balance resets),
  and the rest was kept only because of the sweep-to-200 habit during a favourable three days.
- The week was a volatile two-way range (3,920-4,149, daily ranges 77-152 pts). That is the regime that suits averaging into
  fades. A one-way week is the regime that ends it, and this sample contains one such day (11-10, -1,510 USD).

What six days can and cannot support: the mechanics are measured and reproducible. An entry edge large enough to explain a
76% win rate is excluded. A small one (below roughly 1.5 pts per decision, or 9-12 percentage points of win rate) is not
excluded, and this sample cannot establish profitability in either direction. That is the question the backtests below answer.

---

## 4. What can be codified, and how well it fits

### 4.1 Trigger parity (new in this synthesis, no outcome data read)

The fade habit was written as a closed-M1-bar rule (section 5.3) and compared with the real decisions. A click at time T
is compared with the last M1 bar that had already closed at T (median 30 s earlier, maximum 60 s). Script:
`synthesis/01_trigger_parity.py`, output `synthesis/trigger_parity.csv`.

| K_FADE | Fresh entries (n=27) with the trigger on | All decisions (n=124) | Averaging adds (n=68) | Entries against an opposite basket (n=22) | Base rate per side, in-session M1 bars of the trade week | Trigger onsets per day, Jul-Nov 2026 (median) |
|---|---|---|---|---|---|---|
| 0.4 | 48% | 43% | 50% | 23% | 19.4% | 155 |
| **0.6** | **41% (11 of 27)** | 31% (39 of 124) | 37% | 9% | 13.2% | 122 |
| 0.8 | 26% | 22% | 28% | 5% | 8.3% | 88 |
| 1.0 | 19% | 15% | 19% | 5% | 4.9% | 56 |

Reading:
- At the default K_FADE = 0.6 the rule is on for 11 of his 27 fresh entries, three times the base rate. **The other 16 are
  not explained by this rule or by any other price feature the entries study tested.** The fade is a tendency, not a rule he follows.
- The opposite trigger was on for 1 of 27 fresh entries (3.7%), so he rarely goes with the move.
- The rule fires about 120 times a day. He opened about 4.5 fresh baskets a day. The rule is therefore a superset of his
  entries; in the candidates the position state, not the signal, limits how often a trade opens.
- The add rule (price at least max(0.7 x ATR5, 2.0 pts) beyond the previous same-side fill) covers 50% of his 68 averaging
  adds by construction (it is set at his median spacing).
- M5 ATR(14) at his decisions: median 4.97 pts (IQR 3.98-6.04, minimum 2.87). It was at least 3.0 at 27 of 27 fresh entries.

Because the entry studies found real and random entries indistinguishable, the exact form of the trigger should matter
little to the result. The backtests include a random-entry control to confirm that.

### 4.2 Not codified, and which way the omission leans

| Observed behaviour | Why left out | Effect on Candidate 1 |
|---|---|---|
| Irregular size-ups (10 positions, -1,652 USD) | No rule found; they follow balance highs, deposits and losses | Favours the candidate |
| Hedge-lock and close-by (-249 USD) | Discretionary | Favours the candidate. Opposite-side entries still occur because the two sides run independently. |
| Top-up deposits into an open losing book (2 of 8) | Discretionary | Neutral to unfavourable |
| XM bonus credit and negative-balance resets (379 USD) | Promotional, not repeatable | Hurts the candidate. Reported separately as "loss absorbed by broker". |
| Hand-closing at about half the target | No timing rule found | Approximated by the small-target cell (TP = 1.0 x ATR5, about 5 pts) |
| The 16 of 27 fresh entries the trigger does not explain | Unknown input (chart, signal source, discretion) | Unknown |

---

## 5. Common framework for all candidates

### 5.1 Bars, time and look-ahead

- M1 bars, UTC, stamped by open time. Bar `t` closes at `open(t) + 60 s`; call that `c(t)`.
- Every indicator at bar `t` uses only bars whose close is at or before `c(t)`.
- A decision taken at `c(t)` is filled at the **open of the next existing M1 bar**. The harness must assert that the entry
  bar index is strictly greater than the signal bar index.
- M5 bars are built from M1 in clock-aligned 5-minute buckets. An M5 bar opened at `T5` may be used at M1 bar `t` only if
  `T5 + 5 min <= c(t)` (vault trap 9: never the bar in progress).
- References such as `t-5` count existing M1 bars. **Gap guard:** no signal at bar `t` if bar `t-14` opened more than
  30 minutes before bar `t`.

### 5.2 Prices and costs

| Item | Base | Stress |
|---|---|---|
| Quote data (bid/ask M1, 2026-07-16 onward) | XM bid = OANDA bid - 0.05; XM ask = OANDA ask + 0.06 (three studies measured bid -0.04 to -0.05 and ask +0.06 to +0.07 on 211-272 fills; the entries study, on entry fills only, measured -0.03 and -0.01; the scatter is 0.19-0.29 pts, so all of these are noise-level) | a further 0.20 on each side |
| Mid-only data (before 2026-07-16) | bid = mid - 0.30, ask = mid + 0.30 (XM median spread at his fills 0.58-0.60) | bid = mid - 0.50, ask = mid + 0.50 |
| Stop and stop-out slippage | 0.30 pts against the position | 0.60 pts |
| Commission, swap | 0 (commission was zero; swap was -2.73 USD in the week and is ignored) | same |

Longs open at the ask and close at the bid. Shorts open at the bid and close at the ask. The signal series is the bid
(on mid-only data the mid; the constant offset cancels in every indicator).

### 5.3 Indicators and the fade trigger (closed bars only)

```
ret5[t]  = close[t] - close[t-5]
ATR5[t]  = Wilder ATR(14) on closed M5 bars (true range; recursive smoothing with alpha = 1/14;
           valid after 14 true ranges; discard the first 100 M5 bars of the dataset as warm-up)
hi15[t]  = max(high[t-14 .. t])        lo15[t] = min(low[t-14 .. t])
pos15[t] = (close[t] - lo15[t]) / (hi15[t] - lo15[t])        undefined if hi15 = lo15

SELL_SIG[t] = ret5[t] >= +K_FADE * ATR5[t]  and  pos15[t] >= 2/3
BUY_SIG[t]  = ret5[t] <= -K_FADE * ATR5[t]  and  pos15[t] <= 1/3
```

Both signals are false when the gap guard fails, ATR5 is not yet valid, or `ATR5[t] < MIN_ATR5` (3.0 pts: below that the
distances used here are within a few spreads; his own entries were all taken above it).

### 5.4 Session

A fresh entry or an add may be decided only when `c(t)` falls in **[01:00, 21:00) UTC, Monday to Friday**.

### 5.5 Exit resolution on M1

| Order | Long position | Short position |
|---|---|---|
| Take-profit at price P | hit when `bid_high >= P`; filled at P (no favourable slippage, even on a gap) | hit when `ask_low <= P`; filled at P |
| Stop at price P | hit when `bid_low <= P`; filled at `min(P, bid_open) - slippage` | hit when `ask_high >= P`; filled at `max(P, ask_open) + slippage` |
| Market close (time, end of day, news, brake) | at the next bar's `bid_open` | at the next bar's `ask_open` |

- Stop and target touched in the same bar: **the stop wins.**
- The entry bar is checked for exits (the entry is at its open).
- Within a bar, stops are processed before targets.

---

## 6. Candidate 1 — XMR-1 "deposit-as-stop averaging fade" (most faithful)

**Purpose.** Show the true long-run result of what he does. It has no stop and breaks every production rail by design.
**It is a risk exhibit and is not a deployment candidate under any outcome.**

**Hypothesis.** A no-stop, flat-clip averaging fade on a 200 USD account at 1:1000 wins at least 75% of its positions
through geometry alone and loses the deposit often enough that the owner's cash is negative over 16 months.

### 6.1 Rules

1. **Two independent books**, LONG and SHORT, as on a hedging account. Each side follows rules 2-4 without regard to the other.
2. **Fresh entry.** At `c(t)`, if side S has no open position, `SIG_S[t]` is true, the session rule holds and the account
   is funded: open `FRESH_CLIPS` positions of `CLIP` lots on side S at the next open.
3. **Add.** At `c(t)`, if side S has between 1 and `N_MAX - 1` open positions and the session rule holds, let `last` be
   the entry price of the most recently opened position on side S that is still open, and
   `STEP[t] = max(K_STEP * ATR5[t], STEP_FLOOR)`.
   LONG: add if `last - ask_close[t] >= STEP[t]`. SHORT: add if `bid_close[t] - last >= STEP[t]`.
   Open one position of `CLIP` lots at the next open. At most one order per side per bar.
4. **Take-profit.** Let `D = max(TP_ATR * ATR5, 3.0 pts)` at the signal bar of that order.
   - `TP_MODE = per_leg`: each position's TP is its own fill price plus or minus D.
   - `TP_MODE = shared_first`: the first positions of a book get fill plus or minus D; every add takes the TP price of the
     oldest open position on that side, so the whole book closes together.
5. **No stop-loss, no time exit, no news rule, no weekend rule.** Positions are carried across the daily break and the weekend.
6. **Order accepted** only if, at `c(t)` quotes, equity is greater than the margin the book would need after the order,
   or the order reduces net lots.

### 6.2 Account model (this is the stop)

- Balance starts at `DEPOSIT` = 200 USD. No bonus credit.
- Margin = `|long lots - short lots| * 100 * mid_close / LEVERAGE`. A hedged pair carries zero margin (this reproduced all
  34 of the broker's stop-out margin figures within 0.02 USD).
- **Worst-case equity in bar u**: `E_min = min(E_low, E_high)`, where `E_low` marks every long at `bid_low[u]` and every
  short at `ask_low[u]`, and `E_high` marks them at `bid_high[u]` and `ask_high[u]`.
- **Stop-out**: if `E_min <= 0.20 * margin` (or `E_min <= 0` when margin is zero), every open position is closed, pending
  orders are cancelled and the balance is set to 0. Count one wipe-out. Record `max(0, -E_min)` as loss absorbed by the
  broker (an upper bound). The stop-out check comes before any take-profit in the same bar.
- **Re-deposit**: 60 minutes after a wipe-out the balance is set to `DEPOSIT` and trading resumes (his re-deposits came
  0.2-12 hours after six of seven wipe-outs).
- **Sweep** (`SWEEP = on`): at any bar close with both books empty and balance above `DEPOSIT`, withdraw the excess.
  `SWEEP = off`: never withdraw; the balance compounds and a wipe-out loses all of it. Clip size stays at `CLIP` either way.

### 6.3 Parameters

| Parameter | Value | Source |
|---|---|---|
| CLIP | 0.04 lots | 163 of 178 positions |
| FRESH_CLIPS | 2 | 18 of 27 fresh entries are a double tap |
| K_FADE | 0.6 | median fresh entry: prior 5-minute move 0.6 x ATR against the trade |
| MIN_ATR5 | 3.0 pts | section 5.3 |
| K_STEP, STEP_FLOOR | 0.7, 2.0 pts | median add spacing 0.69 x ATR; 25th percentile 2.0 pts |
| N_MAX | 10 positions per side | up to 10 already open before an add; 13 at the peak |
| DEPOSIT, LEVERAGE, stop-out level | 200 USD, 1000, 20% | sweep target; verified against broker comments |
| **Grid: TP_ATR** | **1.0** (about 5 pts at his ATR; his modal TP 5.06 and median winner 4.7), 2.5 (about 12 pts; his median set TP 12.3) | |
| **Grid: TP_MODE** | **per_leg**, shared_first | 51 of 141 TPs shared a price |
| **Grid: SWEEP** | **on** (his week 1), off (his week 2) | |

Eight cells. Default in bold. No other value is to be tried.

### 6.4 Required output

- Owner cash = withdrawals + final equity - deposits, in total and per week; share of weeks positive; worst week.
- Wipe-outs: count, per week, money lost in each, longest run; loss absorbed by the broker.
- Position win rate, PF, average win and loss; time flat; maximum positions and lots.
- **Shadow run**: same rules with unlimited balance (no stop-out, no deposits). Report the worst floating loss in USD and
  points, and the longest time under water. This is the tail the margin stop-out hides.
- **Random control**: same machine with the trigger replaced by a random signal firing at the trigger's own rate per UTC
  hour and month, per side. 100 draws.
- **Trade-week check**: run the default cell on 2026-11-04 to 11-11 and put positions opened, time flat, wipe-outs and
  position win rate next to the real 178 / 17.4% / 7 / 75.8%. Same order of magnitude is the expectation; it is a
  sanity check, not a pass mark.

---

## 7. Candidate 2 — XMR-2 "capped fade basket" (his shape inside the rails)

**What it keeps:** the fade trigger, flat-size averaging (at most three legs), the small basket target, his hours.
**What it adds:** a hard basket stop in dollars, one side at a time, flat before news and overnight, daily brakes.

**Hypothesis.** The fade trigger with at most three flat legs, closed at VWAP plus one ATR or at a basket loss capped
at 30 USD, earns more than a random-timing control under identical management, and enough to cover costs.

### 7.1 Rules

1. **One basket at a time, one side.** While a basket is open the opposite signal is ignored. No hedging.
2. **Fresh entry.** At `c(t)`, if no basket is open, `SIG_S[t]` is true, the session rule holds, `c(t)` is not inside a
   news window, the cooldown has elapsed and no brake is active:
   `atr0 = ATR5[t]` and `RISK_B = min(RISK_USD, 100 * LOT * SL_ATR * atr0)`, both frozen for the life of the basket.
   Open one leg of `LOT` on side S at the next open.
3. **Add.** At `c(t)`, if the basket has fewer than `N_MAX` legs, the session rule holds and `c(t)` is not inside a news
   window: with `last` = entry price of the most recent leg and `STEP[t] = max(K_STEP * ATR5[t], STEP_FLOOR)`,
   LONG adds if `last - ask_close[t] >= STEP[t]`, SHORT if `bid_close[t] - last >= STEP[t]`,
   **and** the stop that would result (rule 4, computed with a hypothetical leg at `ask_close[t]` or `bid_close[t]`)
   is at least `MIN_STOP_GAP` points beyond that hypothetical fill. Add one leg of `LOT` at the next open.
4. **Basket stop (hard, resting at the broker on every leg).** With n legs and volume-weighted entry `VWAP`:
   LONG `P_stop = VWAP - RISK_B / (100 * LOT * n)`; SHORT `P_stop = VWAP + RISK_B / (100 * LOT * n)`.
   Recomputed after every fill. The loss at the stop is `RISK_B` for any number of legs, plus slippage.
   At his ATR (about 5 pts) `RISK_B` is 30 USD: the stop is 30 pts from one leg, 15 pts from the VWAP of two, 10 pts
   from the VWAP of three. At ATR 3 pts it is 18 USD (18, 9 and 6 pts). Above ATR 5 the 30 USD rail binds.
5. **Basket target.** LONG `P_tp = VWAP + TP_ATR * atr0`; SHORT `P_tp = VWAP - TP_ATR * atr0`. All legs close together.
6. **End of day.** At the first `c(t) >= 21:00` the basket is closed at the next open. Nothing is held overnight or over the weekend.
7. **News.** Windows 12:25-12:45 and 13:25-13:45 UTC on weekdays (08:30 New York in summer and winter time). No entry or
   add is decided inside a window. An open basket is closed at the open of the first bar that opens at or after the window start.
   Live, use the production calendar gate as well.
8. **Brakes.** (a) After `DAILY_STOPS` basket stop-outs in a UTC day, no new basket until the next UTC day.
   (b) If the strategy's realised plus floating P&L for the UTC day is at or below `KILL_USD`, close everything and halt
   until the next UTC day. (c) No fresh entry for `COOLDOWN_MIN` minutes after any basket close.

### 7.2 Parameters

| Parameter | Value | Source |
|---|---|---|
| K_FADE, MIN_ATR5, K_STEP, STEP_FLOOR | 0.6, 3.0, 0.7, 2.0 | as Candidate 1 |
| LOT | 0.01 per leg (venue minimum) | exposure cap: at most 0.03 lots open |
| RISK_USD | 30 per basket, the ceiling | middle of the 25-38 USD rail |
| SL_ATR | 6.0 | his median distance to stop-out, 26-28 pts, at ATR 4.97. Sets the basket risk below the ceiling when ATR is under 5 pts |
| MIN_STOP_GAP | 3.0 pts | production broker stop floor |
| COOLDOWN_MIN | 20 | his median time between decisions, 21 minutes |
| DAILY_STOPS, KILL_USD | 3, -250 | three stopped baskets is about -90 USD; -250 is the account rail |
| **Grid: N_MAX** | 1, 2, **3** | 1 = no averaging, the ablation |
| **Grid: TP_ATR** | **1.0**, 2.5 | as Candidate 1 |

Six cells. Default in bold. Worst case per basket: 30 USD plus slippage (at most 0.90 USD at base cost) plus any gap
through the stop. Break-even win rate of the default with one leg is about 86%; random entries with this shape won 83.5%
in the entries study, so the trigger must add roughly 2-3 percentage points.

---

## 8. Candidate 3 — XMR-3 "single-shot fade, balanced bracket" (least faithful, cleanest test)

**What it keeps:** only the fade trigger and his hours. **What it removes:** averaging, hedging, the small-target shape.
With target equal to stop, profit cannot come from deferring losses, so this is the direct test of whether the fade has
any directional content.

**Hypothesis.** After a 5-minute move of at least 0.6 ATR into the outer third of the 15-minute range, gold reverts by
1.5 ATR before it extends by 1.5 ATR more often than chance, by enough to pay the spread (about 51% needed against
about 46% for a random entry).

### 8.1 Rules

1. **One position at a time.**
2. **Entry.** At `c(t)`, if flat, `SIG_S[t]` is true, the session rule holds, `c(t)` is not inside a news window (as in
   7.1 rule 7), the cooldown has elapsed and no brake is active:
   `SL_pts = SL_ATR * ATR5[t]`, `TP_pts = TP_ATR * ATR5[t]`,
   `LOT = floor_to_0.01(RISK_MAX / (100 * (SL_pts + 0.30)))`. Skip if `LOT < 0.01`.
   Open at the next open. Stop and target are anchored to the fill price and rest at the broker.
3. **Exits.** Stop; target; **time stop**: at the first `c(t)` at least `T_MAX` minutes after the fill, close at the next
   open; end of day and news exactly as 7.1 rules 6 and 7.
4. **Brakes.** As 7.1 rule 8, with "basket" read as "trade".

### 8.2 Parameters

| Parameter | Value | Source |
|---|---|---|
| MIN_ATR5 | 3.0 | section 5.3 (so the stop is never below 4.5 pts) |
| RISK_MAX | 38 USD per trade | top of the rail. Rounding down to 0.01 lots puts the actual risk between about 19 and 38 USD, never above. Largest possible size is 0.07 lots (at ATR 3.0) |
| T_MAX | 60 minutes | the only horizon at which fresh entries looked better than random (+2.57 vs -0.16 pts, n=27, not significant) |
| COOLDOWN_MIN, DAILY_STOPS, KILL_USD | 20, 3, -250 | as Candidate 2 |
| **Grid: (TP_ATR, SL_ATR)** | **(1.5, 1.5)**, (2.5, 2.5), (1.5, 2.5) | about 7.5 and 12.5 pts at his ATR |
| **Grid: K_FADE** | **0.6**, 1.0 | dose-response: if the fade is real, a larger stretch should revert more |

Six cells. Default in bold. Distances are in ATR units because M5 ATR ran from about 2 pts (Jul-Aug 2025) to 8 pts
(Mar 2026) across the test window; fixed points would not be comparable (vault trap 8).

---

## 9. Validation protocol (fixed before any run)

### 9.1 Data

| Window | File | Use |
|---|---|---|
| 2025-07-16 to 2026-03-31 | `../xau_m1_oanda.parquet` (mid) | TRAIN |
| 2026-04-01 to 2026-11-03 | same file to 2026-07-15, then `xau_m1_2026-07-16_now_mba.parquet` (bid/ask) | TEST |
| 2026-11-04 to 2026-11-11 | bid/ask M1 and S5 | Parity only. Never part of a pass or fail. |
| 2019-01-01 to 2025-07-15 | `../m3_scalper/xau_m1_full.parquet` (mid; 5.77 M rows from 2010, columns time/open/high/low/close) | Secondary, report only. File coverage was read here; its quality was not checked. Use a spread of 1.5 bp of price (base) and 2.5 bp (stress). |

Both cost levels are run on every window.

### 9.2 Harness checks that must pass before any result is read

1. Entry bar index is strictly after the signal bar (assert on every trade).
2. Closed-bar probe: `(last M5 open + 5 min) - c(t)` is never positive.
3. Trigger parity: at K_FADE = 0.6 the harness's trigger is on at the last closed bar for exactly 11 of the 27 fresh
   entries and 39 of the 124 decisions (`synthesis/trigger_parity.log`; decisions are the first click of each event in
   `entries/entries_features.csv`; bid series of the quote file). A different count means the harness and this
   specification disagree.
4. Same-bar stop and target resolves as the stop.
5. A win rate near 0% or 100%, or an implausible expectancy, is treated as a harness fault to diagnose.
6. Where S5 bid/ask data exists, re-resolve the default cells on S5 quotes and report the difference from M1.

### 9.3 Pass marks for Candidates 2 and 3

The **default cell is the hypothesis**. The other cells are neighbours for robustness, not a search. A candidate passes
only if its default cell meets all of the following:

| # | Gate |
|---|---|
| 1 | PF at least 1.15 at base cost and at least 1.00 at stress cost, on TRAIN and on TEST separately |
| 2 | Total points above the 95th percentile of 200 random-control draws on TEST. Control: the trigger replaced by a random signal with the trigger's own firing rate per UTC hour and calendar month, per side; identical management, costs and brakes |
| 3 | Net positive in at least 60% of TEST calendar months, and no single month supplies more than 40% of TEST net |
| 4 | At least half of the neighbouring cells have TEST PF above 1.00 at base cost (a plateau, not a spike) |
| 5 | Candidate 3 only: the K_FADE = 1.0 cell has a higher win rate than the 0.6 cell on TRAIN and on TEST |
| 6 | At least 300 trades (or baskets) in TEST |

Confidence intervals use a bootstrap over UTC days, not over trades. A pass leads to paper trading under the live fill
model, not to live money. If the default cell fails, the candidate is closed. A neighbouring cell that happens to pass
does not reopen it.

### 9.4 Candidate 1

No pass mark. It is reported in full (section 6.4) whatever it shows. If owner cash is positive, report how much of it is
loss absorbed by the broker and how it is distributed across weeks before drawing any conclusion.

---

## 10. Priors, stated before the runs

- **Candidate 1:** position win rate 75-90%; wipe-outs most weeks; owner cash negative at both cost levels; the random
  control indistinguishable. Basis: random entries under his shape lose 0.45-1.06 pts per trade in the entries study,
  and the real account took eight deposits in six days.
- **Candidate 2:** fails gate 1 or 2. Basis: the best capped cell found on his own entries (take 4, stop 25) was
  +0.87 +- 0.83 pts per decision, the best of 154 correlated cells, and the random control explains most of it.
- **Candidate 3:** fails gate 1. Basis: symmetric brackets on his entries win 37-49%, the same as random.
- House history points the same way: the vault's 258-configuration S5 study found no deployable high-win-rate scalp, and
  the S5 programme found that after a sweep and reclaim of a level, gold tended to continue rather than reverse.

If these priors are right, the useful output of this work is the Candidate 1 exhibit and the guardrails in section 11.

---

## 11. Guardrails, each tied to a behaviour that preceded a stop-out

| Guardrail | Behaviour it removes | What that behaviour cost |
|---|---|---|
| A hard stop on every position or basket | Holding losers to the margin call | 33 of 39 losers, -3,484 USD |
| One fixed size; no size-up after a deposit, a loss or a balance high | Irregular size-ups | -1,652 USD on 10 positions |
| No opposite-side hedge against a losing position | Hedge-lock | -1,417 USD on 22 decisions |
| Flat before scheduled releases and over the weekend | Unmanaged scheduled risk | -2,041 USD and -200 USD (and +262 USD once) |
| A daily loss limit and a stop count | Re-deposit and re-entry within minutes of a wipe-out | 6 of 7 wipe-outs were followed by a deposit |

One production item to check: the news blackout default in `KronosStrategies/strategies/shared/gate_rules.py` is
`12:25-12:45` UTC. From 2026-11-01 (US winter time) the 08:30 New York releases are at 13:30 UTC, where both large moves
of this week happened. I did not look at the box's own setting.

---

## 12. Caveats

- Six trading days, one regime, one account. One deposit was a 134.78 USD transfer from a second XM account whose history
  is not in the data, and the account was chosen for study because its statement looked good.
- Take-profit values are the ones attached at close. Order modifications are not in the deal history, so the TP distance
  at entry is unknown for 125 of 141 positions.
- OANDA is a proxy for XM's quote. The basis is under 0.1 pt in calm bars, but at the two 13:30 UTC moves XM filled
  13-25 pts away from OANDA's 5-second bar (stop-outs worse, take-profits better). Candidate 1's stop-outs are therefore
  modelled as a total loss of the balance, not as a fill price.
- The four studies use slightly different definitions. Decisions: 121, 124 or 126 for burst windows of 60, 30 or 10 s.
  Stop-outs: 7 events (5-minute clustering; 34 deals). "Fresh" means account flat in the performance and entries studies
  (27 decisions, 45 positions) and "no losing position open" in the exits study (38 decisions, 59 positions).
  Points: +402.0 with each close-by pair counted once; `trades.csv` `pts` sums to +339.8 because it counts both legs.
- The candidate parameters were set from this account's medians and from the trade week's ATR. They describe him.
  Nothing about them has been optimised, and nothing about them has been shown to make money.
- The M1 history before 2026-07-16 is mid-only, so spread there is modelled, not observed.

---

## 13. Files

| File | What |
|---|---|
| `STRATEGY_SPEC.md` | this document |
| `synthesis/01_trigger_parity.py` | trigger recall on the real decisions and base rate on M1 bars; reads no outcome |
| `synthesis/trigger_parity.csv`, `synthesis/trigger_parity.log` | its output |
| `performance/REPORT.md` and `performance/results/` | account rebuild, performance, risk, cash |
| `entries/` (`02_baseline.log`, `03_sequence_setups.log`, `entries_features.csv`) | entry context against random baselines |
| `exits/results/06_tables.txt`, `exits/trade_excursions.csv` | excursions and exit counterfactuals |
| `chart/xm_real_trades_equity.html`, `chart/README.md` | every trade on the gold chart with balance and equity |

No production system, box or broker API was touched. Nothing was committed and the vault was not updated.
