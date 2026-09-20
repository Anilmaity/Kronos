# Defensive Liquidity Gate for the Cross-Venue 15m Lock

**Date:** 2026-06-15
**Status:** Implemented 2026-06-15 (tests green: test_arb_gate.py 22/0, test_never_naked.py 32/0; feed enrichment verified live; NOT yet run live — kill switch still ON).
**Scope:** `bot/arb_gate.py` (new, shared), `bot/live_strategy.py` (`step()`),
`bot/pm_strategy.py` (`step()`), `bot/kalshi.py`, `bot/polymarket.py`,
`dashboard/refresh_live5m.py`, `test_never_naked.py`

## Problem

The cross-venue 15m BTC Up/Down lock places real orders that bleed small losses
on nearly every controlled attempt. The real-money event log
(`journal/live_arb_log.csv`) shows the cause is **not** budget or leg ordering:

1. **Kalshi orders are priced off last-trade, not the resting ask.** `bot/kalshi.py`
   `updown_live()` returns the last executed trade price (line ~149: *"fills are
   not guaranteed"*). A buy IOC at that price finds no resting ask and fills 0 —
   e.g. the 06:00 window chased 60c→80c on 2-3 contracts, `filled: 0` every time.
2. **The two legs are rarely simultaneously fillable.** The bot commits one leg
   *before* knowing the other can hedge it. Every clean unwind in the log traces
   to one leg fillable and the other not at the same moment:
   - `hedge $0.57 < $1 Poly min` (Kalshi filled 3 @ ~19c, hedge below Poly's $1
     minimum order) → flatten Kalshi → small loss.
   - `FOK orders couldn't be fully filled` (Poly book moved) → flatten → loss.

Poly-first ordering (already implemented + tested 20/20) only converts "Kalshi
won't fill" into "Poly over-bought, flatten excess at spread cost" — different
bleed, same root cause.

**Goal (chosen direction: defensive / "stop the bleed"):** only place orders when
a *full hedged lock is actually executable at an arb-preserving price*. Otherwise
skip cleanly with a logged reason. Turn losses into no-ops. This also surfaces, as
data, whether *any* window qualifies — the honest input to a later strategy
decision.

Non-goal: posting resting maker orders to "win" the thin book (the offensive
route). Deferred.

## Design

Two coupled halves. Repricing off the real book is half the fix; gating on joint
depth is the other half. Neither works alone.

### Part A — Book-aware reads (new, read-only; safe with kill switch on)

- `bot/kalshi.py` → `book_ask(ticker, side) -> (price_float, size_int) | (None, 0)`
  - Fetch `GET /trade-api/v2/markets/{ticker}/orderbook`.
  - Return the **best executable ask** price (0..1) and size for *buying* `side`
    (`"yes"`/`"no"`). Kalshi quotes resting **bids** per side; buying YES fills
    against the NO bids: `yes_ask = 1 - best_no_bid_price`, `size = that level's
    size`. Map carefully and verify against the live endpoint shape during
    implementation.
  - Read-only GET; no auth-state mutation. Return `(None, 0)` on any error.
- `bot/polymarket.py` → `book_ask(token_id) -> (price_float, size_int) | (None, 0)`
  - Fetch CLOB `GET /book?token_id=...`, return best ask price (0..1) + size.
  - Today's `_clob_buy_price()` returns price only; this adds the size at the ask.
  - Return `(None, 0)` on any error.

### Part B — The gate (front of `step()`, before any order is placed)

Replaces the section where `_legs()` prices off last-trade and the bot commits a
leg blind. All steps run **before** a single order. The gate emits exactly one of
four canonical skip reasons (used verbatim by the tests and the log):

1. **Real-ask repricing.** `(k_ask, k_size) = kalshi.book_ask(ticker, k_side)`;
   `(p_ask, p_size) = polymarket.book_ask(poly_token)`. These replace last-trade
   prices for both the edge check and the order limit. If either ask is `None` →
   skip **`"no book"`**.
2. **Arb-at-real-prices check.** `lock_cost = k_ask + p_ask`; `gross = 1 -
   lock_cost`. Require `MIN_NET <= net_after_fees` **and** `gross <= MAX_GROSS` at
   the real asks. Fail (gross too wide *or* net below `MIN_NET`) → skip
   **`"not arb at real asks"`**. (Most bad windows die here: profitable on
   last-trade, not on the real ask.)
3. **Joint-fillable size.** `fillable = floor(min(k_size, p_size, cap/price,
   balance/price))` where price caps use each leg's own ask and the existing
   `MAX_NOTIONAL` / balance limits (reuse `_size()` logic, fed real asks + depth).
   - `fillable < 1` → skip **`"no joint depth"`**
   - `fillable * p_ask < $1` → skip **`"below Poly $1 min"`**
4. **Only if all pass (`fire = True`):** place both legs **sized to `fillable`,
   priced at the real asks**, keeping the existing **Poly-first + exception-safe +
   returned-fills-only never-naked** machinery fully intact as the backstop.

**Logging:** every gated-out window logs its skip reason (`gate_skip` event with
`reason`). The count + distribution of skip reasons is the honest signal for a
later "is any window tradeable?" decision.

### Part D — Shared gate, applied to BOTH paper and live accounts

The paper account (`pm_strategy.step()`) and the live account
(`live_strategy.step()`) consume the **same** `dashboard/live5m.json` snapshot but
today carry **separate copies** of `_legs()` + entry logic. To gate both without
drift, the gate becomes shared.

1. **One shared gate.** New `bot/arb_gate.py`:
   `evaluate(p15, k15, balances, cfg) -> {fire: bool, reason: str,
   legs: [(venue, side, ask_price)], fillable: int, lock_cost: float,
   net: float}`. Pure function, no I/O. `_legs()` moves here. **Both** step
   functions call it, so paper and live make the identical entry / size / price
   decision — paper can never be optimistic where live is strict.

2. **Feed carries real book depth.** `dashboard/refresh_live5m.py` enriches
   `poly_15m` / `kalshi_15m` with `up_ask` / `up_ask_size` / `down_ask` /
   `down_ask_size` from the new `book_ask()` readers (one network read per tick).
   The existing `up_cost` / `down_cost` last-trade fields are kept for display and
   back-compat. Both step functions read the same enriched snapshot.

3. **Paper becomes a real mirror.** `pm_strategy.step()` now:
   - enters **only when the gate fires** (real asks, joint depth, Poly $1 min,
     net-after-fees) — paper skips the same windows live skips;
   - sizes to **`fillable` = min(both book depths)** instead of
     `STAKE_FRAC * balance` (today's `MAX_PAIRS = 4000` fantasy collapses to the
     1-5 contracts the books actually hold);
   - prices legs at the **real asks**, not last-trade.

   Effect: paper P&L moves from "$1 x 4000 pairs" toward "$1 x min(book depth)" —
   near the real outcome, where almost nothing fills.

**Deliberately kept separate:** paper settlement still pays the optimistic $1/pair.
Basis risk stays measured separately by `validate_arb.py` and is **not** folded
into paper. The gate makes *fills, entry, and size* realistic; it does not simulate
the rare both-legs-lose break. Document this so the paper number is not mistaken
for fully risk-adjusted.

### Part C — Testing

Extend `test_never_naked.py` (all 20 existing checks stay green — never-naked
backstop unchanged) with a gate suite driving `step()` over mocked `book_ask`
returns:

1. Both deep + arb at real asks → fires, sized to `min(depth)`, locks.
2. Kalshi shallow (size 0) → skip `"no joint depth"`, **zero orders placed**.
3. Joint size fillable but `* p_ask < $1` → skip `"below Poly $1 min"` (the
   live-log `$0.57` case).
4. Last-trade profitable but real ask isn't → skip `"not arb at real asks"`.
5. Both deep but net `< MIN_NET` after fees → skip `"not arb at real asks"`
   (same canonical reason as #4 — both are "edge doesn't survive at real prices").
6. Passes gate, then book moves so a leg under-fills → never-naked backstop still
   flattens / alerts (gate does not weaken the safety net).

Assert **zero `place_fok`/`place_ioc` calls on every skip path** (mock + count).

**Shared-gate + paper parity** (`bot/arb_gate.py` is pure, so test it directly):
7. Unit-test `arb_gate.evaluate()` for each decision: fire / no-joint-depth /
   below-Poly-min / not-arb-at-real-asks / below-MIN_NET. One table, no mocks.
8. **Parity:** feed one enriched snapshot through both `pm_strategy.step()` and
   `live_strategy.step()` and assert they make the **same** fire/skip decision and
   the **same `fillable` size** — paper cannot diverge from live.
9. Paper sizing: a snapshot with book depth 3 yields a 3-pair paper lock (not the
   old `STAKE_FRAC * balance`), priced at the real asks.

Target: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py` green at
**26 passed**, plus the new gate/parity checks (run via the same file or a small
`test_arb_gate.py` — implementation plan decides).

## Honest limits

- **Not atomic.** The depth read and the order are ~100ms apart; the book can move
  between. Poly-first + IOC/FOK + never-naked cover the residual race. The gate
  reduces bleed *frequency*, it does not make execution atomic.
- **Still negative-EV underneath.** `validate_arb.py` measures the lock as ~0.9c/
  pair net with ~15% basis-risk-exposed windows. The gate stops execution bleed;
  it does not create edge. A completed lock still carries Chainlink-vs-Kalshi
  basis risk. Keep the cap small and supervise any live run.
- The gate may reveal ~no window qualifies. That is a *successful* outcome of this
  work (data for the strategy decision), not a failure.

## Files touched

- `bot/arb_gate.py` — **new.** Shared pure gate `evaluate()` (+ `_legs()` moved
  here). Single source of truth for entry / size / price across paper and live.
- `bot/kalshi.py` — add `book_ask()` (read-only orderbook).
- `bot/polymarket.py` — add `book_ask()` (CLOB book with size).
- `bot/live_strategy.py` — call `arb_gate.evaluate()` at front of `step()`;
  never-naked execution block unchanged.
- `bot/pm_strategy.py` — call `arb_gate.evaluate()` in `step()`; size to
  `fillable`, price at real asks; drop the local `_legs()`.
- `dashboard/refresh_live5m.py` — enrich `poly_15m` / `kalshi_15m` with
  `*_ask` + `*_ask_size` from `book_ask()`.
- `test_never_naked.py` (+ optional `test_arb_gate.py`) — +6 gate checks (zero
  orders on skip), gate unit table, and paper/live parity + paper-sizing checks.

## Out of scope (deferred)

- Resting Kalshi maker orders ("win the thin book").
- Basis-risk window-quality filter (momentum gate on settlement agreement).
- Any change to the read-only edge-signal modules.
