# Defensive Liquidity Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the cross-venue 15m lock from bleeding money by gating every order on real book depth + arb-at-real-asks, and apply the same gate to the paper account so its P&L mirrors reality.

**Architecture:** Add read-only `book_ask()` readers to both venue data modules. Extract one shared pure gate (`bot/arb_gate.py`) that decides fire/skip + size + price from real asks; call it from BOTH `live_strategy.step()` and `pm_strategy.step()` so paper and live can never diverge. The existing Poly-first never-naked execution block stays intact as the post-gate race backstop.

**Tech Stack:** Python 3.14, `requests`, Kalshi REST (`/trade-api/v2`), Polymarket CLOB REST. Tests are a hand-rolled assert runner (`test_never_naked.py`) — NOT pytest. Run with `.venv/Scripts/python.exe`.

---

## Environment notes (read first)

- **No git in this repo.** The handoff confirms "no git", and `git` is not initialized. So the usual "commit" step is replaced by a **CHECKPOINT**: re-run the full test command and confirm green. Do not run `git` commands.
- **Kill switch must stay ON** for the whole plan: `journal/STOP` exists. No task removes it. All work is dry/read-only.
- **Run tests with:** `DRY_RUN=true .venv/Scripts/python.exe <file>` from the repo root `C:\Projects\ClaudeProjects\ClaudeTradingBot`.
- **Canonical skip reasons** (used verbatim in code AND test asserts): `"no book"`, `"not arb at real asks"`, `"no joint depth"`, `"below Poly $1 min"`.

## File structure

- **Create** `bot/arb_gate.py` — pure gate `evaluate()` + the moved `_legs()`. Single source of truth for entry/size/price. No I/O.
- **Create** `test_arb_gate.py` — direct unit tests for `evaluate()` (table-driven, no mocks) + paper/live parity.
- **Modify** `bot/kalshi.py` — add `book_ask(ticker, side)`.
- **Modify** `bot/polymarket.py` — add `book_ask(token_id)`.
- **Modify** `bot/live_strategy.py` — `step()` calls `arb_gate.evaluate()`; never-naked block unchanged.
- **Modify** `bot/pm_strategy.py` — `step()` calls `arb_gate.evaluate()`; size to `fillable`, price at real asks; drop local `_legs()`.
- **Modify** `dashboard/refresh_live5m.py` — enrich `poly_15m`/`kalshi_15m` with `*_ask` + `*_ask_size`.
- **Modify** `test_never_naked.py` — `_live()` gains ask/size fields; +6 gate scenarios; assert zero orders on skip paths.

---

## Task 1: `book_ask()` readers on both venues

**Files:**
- Modify: `bot/kalshi.py`
- Modify: `bot/polymarket.py`
- Test: `test_arb_gate.py` (create)

- [ ] **Step 1: Write the failing test (book_ask parsing)**

Create `test_arb_gate.py` with ONLY this first block:

```python
"""Unit tests for the shared liquidity gate + venue book_ask readers.
Run: DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py
Hand-rolled asserts (matches test_never_naked.py style), NOT pytest.
"""
import os
os.environ["DRY_RUN"] = "true"

from bot import kalshi, polymarket

PASS, FAIL = [], []
def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  -> " + extra) if extra else ""))

# --- book_ask parsing (pure, with injected book dicts) ---
# Kalshi: orderbook quotes resting BIDS per side. Buying YES fills against the
# best NO bid: yes_ask = 1 - best_no_bid; size = that level's contracts.
k_book = {"orderbook": {"yes": [[40, 12], [39, 30]], "no": [[55, 7], [54, 20]]}}
kp, ks = kalshi._ask_from_book(k_book, "yes")
check("kalshi yes ask price = 1 - best_no_bid(0.55) = 0.45", abs(kp - 0.45) < 1e-9, str(kp))
check("kalshi yes ask size = best_no_bid size = 7", ks == 7, str(ks))
kp2, ks2 = kalshi._ask_from_book(k_book, "no")
check("kalshi no ask price = 1 - best_yes_bid(0.40) = 0.60", abs(kp2 - 0.60) < 1e-9, str(kp2))
check("kalshi no ask size = best_yes_bid size = 12", ks2 == 12, str(ks2))
check("kalshi empty book -> (None, 0)", kalshi._ask_from_book({"orderbook": {"yes": [], "no": []}}, "yes") == (None, 0))

# Polymarket CLOB /book: asks sorted; best ask = lowest price. size in shares.
p_book = {"asks": [{"price": "0.47", "size": "9"}, {"price": "0.48", "size": "100"}]}
pp, ps = polymarket._ask_from_book(p_book)
check("poly best ask price = 0.47", abs(pp - 0.47) < 1e-9, str(pp))
check("poly best ask size = 9", ps == 9, str(ps))
check("poly empty book -> (None, 0)", polymarket._ask_from_book({"asks": []}) == (None, 0))

print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    raise SystemExit(1)
print("ALL GREEN")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: FAIL — `AttributeError: module 'bot.kalshi' has no attribute '_ask_from_book'`.

- [ ] **Step 3: Add the Kalshi reader**

In `bot/kalshi.py`, add near the other helpers (after `_last_trade`):

```python
def _ask_from_book(data, side):
    """Best executable ASK (price 0..1, size contracts) for BUYING `side`
    ('yes'/'no') from a Kalshi orderbook payload. Kalshi quotes resting BIDS per
    side as [price_cents, size]; a YES buy fills against the best NO bid:
    yes_ask = 1 - best_no_bid. Returns (None, 0) if that side has no resting bid."""
    ob = (data or {}).get("orderbook") or {}
    opp = "no" if side == "yes" else "yes"
    levels = ob.get(opp) or []
    if not levels:
        return None, 0
    # Best bid for the opposite side = the level we cross = HIGHEST price.
    best = max(levels, key=lambda lvl: lvl[0])
    price = round(1.0 - best[0] / 100.0, 4)
    return price, int(best[1])


def book_ask(ticker, side):
    """Live best ask (price 0..1, size) for buying `side` on a Kalshi market.
    Read-only GET (safe in DRY_RUN / with kill switch on). (None, 0) on error."""
    side = side.lower()
    try:
        data = _get(f"/markets/{ticker}/orderbook")
    except Exception:  # noqa: BLE001
        return None, 0
    return _ask_from_book(data, side)
```

NOTE: confirm `_get` builds the path as `/trade-api/v2/markets/{ticker}/orderbook`. Read `_get` at `bot/kalshi.py:25` first; if it already prefixes the base, pass the path it expects. If the live shape differs from `{"orderbook": {"yes": [...], "no": [...]}}`, adjust `_ask_from_book` (the unit test pins the contract; the live shape is verified in Task 5's dry run).

- [ ] **Step 4: Add the Polymarket reader**

In `bot/polymarket.py`, add after `_clob_buy_price` (line ~318):

```python
def _ask_from_book(data):
    """Best ask (price 0..1, size shares) from a Polymarket CLOB /book payload.
    `asks` is a list of {price, size}; best ask = LOWEST price. (None, 0) if dry."""
    asks = (data or {}).get("asks") or []
    if not asks:
        return None, 0
    best = min(asks, key=lambda a: float(a["price"]))
    return round(float(best["price"]), 4), int(float(best["size"]))


def book_ask(token_id):
    """Live best ask (price 0..1, size shares) for a CLOB token. (None, 0) on error."""
    try:
        r = _S.get(f"{CLOB}/book", params={"token_id": token_id}, timeout=8)
        if r.ok:
            return _ask_from_book(r.json())
    except requests.RequestException:
        pass
    return None, 0
```

- [ ] **Step 5: Run test to verify it passes**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: PASS — `=== RESULT: 8 passed, 0 failed ===`.

- [ ] **Step 6: CHECKPOINT**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py`
Expected: still `20 passed, 0 failed` (no behavior change yet).

---

## Task 2: Shared pure gate `bot/arb_gate.py`

**Files:**
- Create: `bot/arb_gate.py`
- Test: `test_arb_gate.py` (append)

- [ ] **Step 1: Write the failing test (gate decision table)**

Append to `test_arb_gate.py` BEFORE the final `print("=== RESULT")` block (move that result block to the very end):

```python
from bot import arb_gate, paper_pm

# Isolate the gate's depth/arb/size logic from the fee MODEL (which lives in and is
# tested by paper_pm): zero the fee for this decision table, mirroring how
# test_never_naked.py wires `paper_pm.fee` to 0. At 3c gross the REAL fee (~3.6c/
# pair) would net-negative the lock, which is correct gate behavior but not what
# these depth/arb/size cases are exercising.
paper_pm.fee = lambda v, s, p: 0.0

def snap(p_up_ask, p_up_sz, p_dn_ask, p_dn_sz, k_up_ask, k_up_sz, k_dn_ask, k_dn_sz):
    p15 = {"up_ask": p_up_ask, "up_ask_size": p_up_sz,
           "down_ask": p_dn_ask, "down_ask_size": p_dn_sz,
           "up_token": "UP", "down_token": "DN"}
    k15 = {"up_ask": k_up_ask, "up_ask_size": k_up_sz,
           "down_ask": k_dn_ask, "down_ask_size": k_dn_sz, "ticker": "T"}
    return p15, k15

# Deep + arb: cheaper lock = UP Poly@0.46 + DOWN Kalshi@0.51 = 0.97, gross 3c.
# Book depth (10 on each chosen leg) is the binding constraint, below the $10/price
# budget cap (~19-21), so fillable == 10.
p15, k15 = snap(0.46, 10, 0.54, 50, 0.49, 50, 0.51, 10)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("gate fires on deep arb", d["fire"] is True, d["reason"])
check("gate picks UP-Poly + DOWN-Kalshi", [l[0] for l in d["legs"]] == ["Polymarket", "Kalshi"], str(d["legs"]))
check("gate fillable = book depth 10 (< $10/price cap)", d["fillable"] == 10, str(d["fillable"]))

# No joint depth: Kalshi down size 0.
p15, k15 = snap(0.46, 50, 0.54, 50, 0.49, 50, 0.51, 0)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("no joint depth -> skip", d["fire"] is False and d["reason"] == "no joint depth", d["reason"])

# Below Poly min: tiny joint depth (1) at 0.46 -> $0.46 < $1.
p15, k15 = snap(0.46, 1, 0.54, 50, 0.49, 50, 0.51, 1)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("below Poly $1 min -> skip", d["fire"] is False and d["reason"] == "below Poly $1 min", d["reason"])

# Not arb at real asks: lock too expensive (gross negative).
p15, k15 = snap(0.60, 50, 0.54, 50, 0.49, 50, 0.55, 50)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("not arb (gross<0) -> skip", d["fire"] is False and d["reason"] == "not arb at real asks", d["reason"])

# Missing ask -> no book.
p15, k15 = snap(None, 50, 0.54, 50, 0.49, 50, 0.51, 50)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("missing ask -> no book", d["fire"] is False and d["reason"] == "no book", d["reason"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.arb_gate'`.

- [ ] **Step 3: Write `bot/arb_gate.py`**

```python
"""Shared pure liquidity gate for the cross-venue 15m lock.

ONE source of truth for the entry/size/price decision, called by BOTH the paper
account (bot/pm_strategy.py) and the live account (bot/live_strategy.py) so they
can never diverge. No I/O: it reads REAL asks + sizes already placed on the
snapshot by the feed, and returns a fire/skip decision sized to what BOTH books
can actually absorb at an arb-preserving price.

Skip reasons are canonical strings (asserted by tests + logged): "no book",
"not arb at real asks", "no joint depth", "below Poly $1 min".
"""
import math

from bot import paper_pm

MIN_NET = 0.003     # >= 0.3c net edge/pair after fees to enter
MAX_GROSS = 0.06    # wider than 6c is basis risk / stale quote, not a real lock
POLY_MIN_USD = 1.0  # Polymarket rejects marketable orders below $1


def _legs(p15, k15):
    """(lock_cost, [(venue, side, ask_price, ask_size), ...]) for the cheaper lock,
    priced at the REAL book asks the feed supplied."""
    pu, pus = p15.get("up_ask"), p15.get("up_ask_size")
    pd, pds = p15.get("down_ask"), p15.get("down_ask_size")
    ku, kus = k15.get("up_ask"), k15.get("up_ask_size")
    kd, kds = k15.get("down_ask"), k15.get("down_ask_size")
    if None in (pu, pd, ku, kd):
        return None, None
    c1 = pu + kd   # UP Polymarket + DOWN Kalshi
    c2 = ku + pd   # UP Kalshi + DOWN Polymarket
    if c1 <= c2:
        return c1, [("Polymarket", "UP", pu, pus or 0), ("Kalshi", "DOWN", kd, kds or 0)]
    return c2, [("Kalshi", "UP", ku, kus or 0), ("Polymarket", "DOWN", pd, pds or 0)]


def _skip(reason):
    return {"fire": False, "reason": reason, "legs": None, "fillable": 0,
            "lock_cost": None, "net": None}


def evaluate(p15, k15, poly_bal, kalshi_bal, max_notional,
             min_net=MIN_NET, max_gross=MAX_GROSS, poly_min_usd=POLY_MIN_USD):
    """Decide whether a FULL hedged lock is executable right now, and at what size.
    Returns {fire, reason, legs:[(venue,side,price,size)], fillable, lock_cost, net}.
    `legs` carries REAL ask prices (use as order limits) and is sized to `fillable`."""
    lock_cost, legs = _legs(p15, k15)
    if legs is None:
        return _skip("no book")

    gross = 1.0 - lock_cost
    if not (0 < gross <= max_gross):
        return _skip("not arb at real asks")

    # Per-venue caps + book depth -> the most BOTH legs can absorb.
    poly_leg = next(l for l in legs if l[0] == "Polymarket")
    kalshi_leg = next(l for l in legs if l[0] == "Kalshi")
    p_price, p_size = poly_leg[2], poly_leg[3]
    k_price, k_size = kalshi_leg[2], kalshi_leg[3]
    cap_poly = min(max_notional, poly_bal) / max(p_price, 0.01)
    cap_kalshi = min(max_notional, kalshi_bal) / max(k_price, 0.01)
    fillable = int(min(p_size, k_size, cap_poly, cap_kalshi))
    if fillable < 1:
        return _skip("no joint depth")

    if fillable * p_price < poly_min_usd:
        return _skip("below Poly $1 min")

    fee_total = sum(paper_pm.fee(v, fillable, pr) for v, _s, pr, _sz in legs)
    net = gross - fee_total / fillable
    if net < min_net:
        return _skip("not arb at real asks")

    sized = [(v, s, pr, fillable) for v, s, pr, _sz in legs]
    return {"fire": True, "reason": "", "legs": sized, "fillable": fillable,
            "lock_cost": round(lock_cost, 4), "net": round(net, 4)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: PASS — `15 passed, 0 failed` (8 from Task 1 + 7 gate checks). The bar is **0 failed**; the exact total may differ if checks were added.

- [ ] **Step 5: CHECKPOINT**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py`
Expected: still `20 passed, 0 failed`.

---

## Task 3: Wire the gate into `live_strategy.step()`

**Files:**
- Modify: `bot/live_strategy.py:243-290` (the `_legs`/sizing/poly-min section, BEFORE the Poly-first order block)
- Modify: `test_never_naked.py` (`_live()` + new gate scenarios)
- Test: `test_never_naked.py`

The never-naked order block (`live_strategy.py:290-346`) stays UNCHANGED — it is the post-gate race backstop.

- [ ] **Step 1: Update the test snapshot to carry asks + sizes**

In `test_never_naked.py`, replace `_live()` (lines 100-106) with:

```python
def _live(p_up_sz=99, k_dn_sz=99):
    # Asks mirror the old last-trade prices; sizes default DEEP so the existing
    # never-naked scenarios exercise the POST-gate race path (book moves after the
    # gate read -> fake fill < gate size -> flatten). Gate scenarios pass small sizes.
    return {
        "arb15m": {"status": "evaluated"},
        "poly_15m": {"up_cost": 0.46, "down_cost": 0.54,
                     "up_ask": 0.46, "up_ask_size": p_up_sz,
                     "down_ask": 0.54, "down_ask_size": 99,
                     "window_end": WIN0, "seconds_left": 600,
                     "up_token": "UPTOK", "down_token": "DNTOK"},
        "kalshi_15m": {"up_cost": 0.49, "down_cost": 0.51,
                       "up_ask": 0.49, "up_ask_size": 99,
                       "down_ask": 0.51, "down_ask_size": k_dn_sz,
                       "ticker": "KXBTC15M-T"},
    }
```

- [ ] **Step 2: Run the suite to verify it still fails-or-passes pre-change**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py`
Expected: still `20 passed` (step() hasn't changed; `_live()` just has extra fields it ignores).

- [ ] **Step 3: Replace the sizing/edge section of `step()` with the gate call**

In `bot/live_strategy.py`, replace lines **243-288** — from `lock_cost, legs = _legs(p15, k15)` (243) down to and INCLUDING the `if not dry and shares * poly_px < POLY_MIN_USD:` skip block (ends at 288). This range contains the old `_legs`/`_size`/fee recompute AND the `dry`/`_nonce`/`cid` lines (274-276); the replacement below **re-emits `dry`/`_nonce`/`cid`** because the never-naked block at 290+ still uses them. Replace with:

```python
    from bot import arb_gate
    bal_p = exec_polymarket.balance()
    bal_k = exec_kalshi.balance()
    decision = arb_gate.evaluate(p15, k15, poly_bal=bal_p, kalshi_bal=bal_k,
                                 max_notional=MAX_NOTIONAL)
    if not decision["fire"]:
        _log({"ts": _now_iso(), "event": "gate_skip", "window": settles,
              "reason": decision["reason"]})
        return {"status": "skip", "reason": decision["reason"]}

    legs = decision["legs"]              # [(venue, side, ask_price, size)]
    shares = decision["fillable"]
    lock_cost = decision["lock_cost"]
    gross = 1.0 - lock_cost
    kalshi_leg = next(l for l in legs if l[0] == "Kalshi")
    poly_leg = next(l for l in legs if l[0] == "Polymarket")
    k_side = "yes" if kalshi_leg[1] == "UP" else "no"
    poly_token = (p15 or {}).get("up_token" if poly_leg[1] == "UP" else "down_token")
    ticker = (k15 or {}).get("ticker")
    if not (poly_token and ticker):
        return {"status": "idle", "reason": "missing token/ticker"}
    poly_px = poly_leg[2]

    dry = exec_kalshi.dry_run()
    _nonce = datetime.now(timezone.utc).strftime("%H%M%S")
    cid = f"L{settles}{_nonce}".replace(":", "").replace("-", "")[:28]
```

This deletes the old `_legs` call, the `_size()` call, the gross-band check, the `fee_total`/`net_per_pair` recompute, AND the now-redundant `shares*poly_px < POLY_MIN_USD` precheck (the gate enforced all of them) — while preserving `dry`/`_nonce`/`cid`. `_place_leg` slices `poly_leg[:3]` / `kalshi_leg[:3]`, so the extra size element on each leg tuple is harmless. After this edit, verify by reading lines 290+ that the never-naked block (`pf, p_oid, ... = _place_leg(*poly_leg[:3], shares, ...)`) is intact and unmodified.

- [ ] **Step 4: Remove the now-dead `_size` import/usage**

In `bot/live_strategy.py`, the module-level import line `from bot.pm_strategy import _legs, MIN_NET, MAX_GROSS` (line 34) is now only needed for... nothing — delete it. Keep `_size()` definition if unused? It is now unused; delete the `_size` function (lines 185-193) too. Confirm via search that nothing else references `_size` or the imported `_legs`/`MIN_NET`/`MAX_GROSS`.

Run: `DRY_RUN=true .venv/Scripts/python.exe -c "import bot.live_strategy"`
Expected: no ImportError.

- [ ] **Step 5: Run the suite — existing 20 must stay green**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py`
Expected: `20 passed, 0 failed`. (Deep default sizes => gate fires at 9; race fakes drive the rest exactly as before.)

If `a/clean-lock` now reports `pairs` != 9: the gate's `$10/0.46≈21` cap exceeds the fake's 99 size, so fillable is bounded by `min($10/0.46, $10/0.51)≈19`... but the fakes' `balance()` returns 5.0, so `min($5/0.46,$5/0.51)≈9`. Confirm `pairs==9`. If not, recheck `FakeKalshi.balance`/`FakePoly.balance` return 5.0.

- [ ] **Step 6: Add the 6 gate scenarios**

In `test_never_naked.py`, after scenario `g/hedge-raises` (line 157) and before the accumulation guard, add:

```python
print("\n=== gate scenarios (defensive liquidity gate) ===")

def gate_scenario(name, live_dict, expect_status, expect_reason=None):
    fp, fk = FakePoly(99), FakeKalshi(99)
    state = {"locks": [], "windows_done": []}
    _wire(fk, fp, state)
    res = LS.step(live_dict)
    kh, ph = _held(fk, fp)
    print(f"[{name}] status={res.get('status')} reason={res.get('reason')!r} "
          f"kalshi_held={kh} poly_held={ph}")
    check(name + f": status=={expect_status}", res.get("status") == expect_status, str(res.get("status")))
    if expect_reason is not None:
        check(name + f": reason=={expect_reason}", res.get("reason") == expect_reason, str(res.get("reason")))
    check(name + ": NO orders placed on skip", kh == 0 and ph == 0, f"kalshi={kh} poly={ph}")

# i) Kalshi down book empty -> no joint depth, zero orders
gate_scenario("i/no-joint-depth", _live(k_dn_sz=0), "skip", "no joint depth")
# j) tiny joint depth at 0.46 -> below Poly $1 min (1 share * 0.46 = $0.46)
gate_scenario("j/below-poly-min", _live(p_up_sz=1, k_dn_sz=1), "skip", "below Poly $1 min")
# k) not arb at real asks: make the lock cost > MAX_GROSS band
_bad = _live(); _bad["poly_15m"]["up_ask"] = 0.62
gate_scenario("k/not-arb", _bad, "skip", "not arb at real asks")
# l) missing ask -> no book
_nb = _live(); _nb["kalshi_15m"]["down_ask"] = None
gate_scenario("l/no-book", _nb, "skip", "no book")
```

Note scenarios (a)-(h) already prove the FIRE path (gate passes, orders place, never-naked holds), and (f) already proves "gate passes then book moves -> backstop alerts". That covers spec test 1 and 6. (i)-(l) cover spec tests 2-5.

- [ ] **Step 7: Run the full suite**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py`
Expected: `RESULT: 32 passed, 0 failed` (20 existing + 12 new asserts across i/j/k/l — each gate_scenario emits up to 3 checks).

- [ ] **Step 8: CHECKPOINT**

Run both: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py` (13 passed) and `test_never_naked.py` (32 passed).

---

## Task 4: Wire the gate into `pm_strategy.step()` (paper mirror)

**Files:**
- Modify: `bot/pm_strategy.py:23-72`
- Modify: `livearb_once.py` (the sole external consumer of the deleted `pm_strategy._legs` — display-line fix, Step 3b)
- Test: `test_arb_gate.py` (append parity + sizing checks)

- [ ] **Step 1: Write the failing parity test**

Append to `test_arb_gate.py` (before the final RESULT block):

```python
# --- paper/live parity: same snapshot -> same fire + same fillable ---
from bot import pm_strategy, paper_pm

def _gate_snap(p_up_sz, k_dn_sz):
    return {
        "arb15m": {"status": "evaluated"}, "generated_at": "2026-06-15T07:14:00Z",
        "poly_15m": {"up_cost": 0.46, "down_cost": 0.54, "up_ask": 0.46,
                     "up_ask_size": p_up_sz, "down_ask": 0.54, "down_ask_size": 99,
                     "up_token": "UP", "down_token": "DN",
                     "window_end": "2026-06-15T07:30:00Z", "seconds_left": 600},
        "kalshi_15m": {"up_cost": 0.49, "down_cost": 0.51, "up_ask": 0.49,
                       "up_ask_size": 99, "down_ask": 0.51, "down_ask_size": k_dn_sz,
                       "ticker": "T"},
    }

# Paper sizes to book depth (3), NOT STAKE_FRAC*balance.
acc = paper_pm._blank()
paper_pm.load = lambda: acc
paper_pm.save = lambda a: None
pm_strategy.step(_gate_snap(p_up_sz=99, k_dn_sz=3))
locks = [p for p in acc["positions"] if p.get("tag") == "arb15m"]
check("paper opens exactly one lock", len(locks) == 1, str(len(locks)))
check("paper lock sized to book depth 3", locks and locks[0]["shares"] == 3, str(locks and locks[0]["shares"]))
check("paper lock priced at real asks (0.97)", locks and abs(locks[0]["price"] - 0.97) < 1e-9, str(locks and locks[0]["price"]))

# Parity: same gate decision drives paper-fire and would-fire-live (gate is shared).
from bot import arb_gate
d = arb_gate.evaluate(_gate_snap(99, 0)["poly_15m"], _gate_snap(99, 0)["kalshi_15m"],
                      poly_bal=1000, kalshi_bal=1000, max_notional=10)
acc2 = paper_pm._blank(); paper_pm.load = lambda: acc2
pm_strategy.step(_gate_snap(p_up_sz=99, k_dn_sz=0))
paper_locks = [p for p in acc2["positions"] if p.get("tag") == "arb15m"]
check("parity: gate skip => paper places nothing", d["fire"] is False and not paper_locks, d["reason"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: FAIL — paper lock sized to `STAKE_FRAC*balance` (hundreds), not 3.

- [ ] **Step 3: Rewrite `pm_strategy.step()` to use the gate**

Replace `bot/pm_strategy.py` lines 23-72 (the local `_legs` AND the new-lock block inside `step`) so that: `_legs` is gone (import from `arb_gate`), and the entry uses `arb_gate.evaluate`. Concretely:

Delete the local `def _legs(...)` (lines 23-31). Change the top imports to:

```python
from bot import paper_pm, arb_gate

MIN_NET = arb_gate.MIN_NET
MAX_GROSS = arb_gate.MAX_GROSS
PAPER_MAX_NOTIONAL = 10.0   # mirror the live cap so paper size == real size
```

Replace the "2) Consider a new lock" block (old lines 47-72) with:

```python
    # 2) Consider a new lock for the current window — SAME gate as live.
    arb = live.get("arb15m") or {}
    p15, k15 = live.get("poly_15m"), live.get("kalshi_15m")
    settles = (p15 or {}).get("window_end")
    if arb.get("status") == "evaluated" and p15 and k15 and settles:
        already = any(p.get("settles") == settles and p.get("tag") == "arb15m"
                      for p in acc["positions"])
        if not already:
            d = arb_gate.evaluate(p15, k15, poly_bal=acc["balance"],
                                  kalshi_bal=acc["balance"],
                                  max_notional=PAPER_MAX_NOTIONAL)
            if d["fire"]:
                shares = d["fillable"]
                lock_cost = d["lock_cost"]
                legs = d["legs"]
                fee_total = sum(paper_pm.fee(v, shares, pr) for v, _s, pr, _sz in legs)
                legs_str = " + ".join(f"{s} {v} @ {pr*100:.0f}c" for v, s, pr, _sz in legs)
                purpose = (f"Gated cross-venue 15m lock: BUY {legs_str} = "
                           f"{lock_cost*100:.0f}c -> $1.00 at settle. Net "
                           f"+{d['net']*100:.1f}c/pair on {shares} pairs "
                           f"(sized to book depth).")
                pos = paper_pm.buy_lock(acc, shares, lock_cost, round(fee_total, 4),
                                        settles, legs_str, purpose)
                if pos:
                    changed = True
```

Keep the settle loop (old lines 41-45) and the `if changed: save` tail unchanged.

- [ ] **Step 3b: Fix the one external consumer of the deleted `_legs`**

`livearb_once.py:57` does `from bot.pm_strategy import _legs` and uses it ONLY for a display-line `gross` (informational console output, off last-trade `up_cost`/`down_cost`). Make that display self-contained so deleting `pm_strategy._legs` doesn't break it. In `livearb_once.py`, replace:

```python
        from bot.pm_strategy import _legs
        k15 = live.get("kalshi_15m") or {}
        if None not in (p15.get("up_cost"), p15.get("down_cost"),
                        k15.get("up_cost"), k15.get("down_cost")):
            lc, _ = _legs(p15, k15)
            gross = (1 - lc) * 100
```

with (compute the cheaper-lock cost inline — same semantics, no dependency):

```python
        k15 = live.get("kalshi_15m") or {}
        if None not in (p15.get("up_cost"), p15.get("down_cost"),
                        k15.get("up_cost"), k15.get("down_cost")):
            lc = min(p15["up_cost"] + k15["down_cost"],
                     k15["up_cost"] + p15["down_cost"])
            gross = (1 - lc) * 100
```

This keeps the last-trade-based gross indicator identical (the actual trade decision is unaffected — that lives in `live_strategy.step()` → gate). No other file imports `pm_strategy._legs` (verified by grep).

- [ ] **Step 4: Run the parity test to verify it passes**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py`
Expected: PASS — `19 passed, 0 failed` (15 + 4 parity/sizing checks). The bar is **0 failed**.

- [ ] **Step 5: Confirm nothing imports the removed `pm_strategy._legs`**

Run: `DRY_RUN=true .venv/Scripts/python.exe -c "import bot.pm_strategy, bot.live_strategy, dashboard.refresh_live5m"`
Expected: no ImportError. (If `refresh_live5m` import triggers the per-second loop, instead run the two bot imports only.)

- [ ] **Step 6: CHECKPOINT**

Run: `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py` (32 passed) and `test_arb_gate.py` (19 passed). Bar is **0 failed** on both.

---

## Task 5: Enrich the live feed with real book depth

**Files:**
- Modify: `dashboard/refresh_live5m.py:66-85` (`write_once`)

- [ ] **Step 1: Add ask-enrichment in `write_once`**

In `dashboard/refresh_live5m.py`, immediately after `live["arb15m"] = arb` (line 81), add:

```python
    # Enrich the 15m legs with REAL book asks + sizes (price+depth) so the shared
    # gate sees what can actually fill — not the last-trade quote. Read-only.
    def _enrich_poly(p15):
        if not p15:
            return
        for side, tok in (("up", p15.get("up_token")), ("down", p15.get("down_token"))):
            if tok:
                px, sz = _safe(lambda: polymarket.book_ask(tok)) or (None, 0)
                p15[f"{side}_ask"], p15[f"{side}_ask_size"] = px, sz
    def _enrich_kalshi(k15):
        if not k15 or not k15.get("ticker"):
            return
        for side in ("up", "down"):
            kside = "yes" if side == "up" else "no"
            px, sz = _safe(lambda: kalshi.book_ask(k15["ticker"], kside)) or (None, 0)
            k15[f"{side}_ask"], k15[f"{side}_ask_size"] = px, sz
    _safe(lambda: _enrich_poly(live.get("poly_15m")))
    _safe(lambda: _enrich_kalshi(live.get("kalshi_15m")))
```

NOTE: `_safe` returns `None` on exception; `book_ask` already returns `(None, 0)` on error, so the `or (None, 0)` guards the `_safe`-returned-None case. `_enrich_*` mutate the dicts in place; their `_safe` wrappers just swallow any unexpected error.

- [ ] **Step 2: Smoke-test one feed tick against the LIVE books (read-only, kill switch ON)**

Run: `DRY_RUN=true .venv/Scripts/python.exe dashboard/refresh_live5m.py --once`
Then inspect the written asks:

Run: `DRY_RUN=true .venv/Scripts/python.exe -c "import json; d=json.load(open('dashboard/live5m.json')); k=d.get('kalshi_15m') or {}; p=d.get('poly_15m') or {}; print('kalshi up_ask', k.get('up_ask'), 'sz', k.get('up_ask_size'), 'down_ask', k.get('down_ask'), 'sz', k.get('down_ask_size')); print('poly up_ask', p.get('up_ask'), 'sz', p.get('up_ask_size'), 'down_ask', p.get('down_ask'), 'sz', p.get('down_ask_size'))"`

Expected: numeric asks in (0,1) and integer sizes (or `None`/`0` if a side has no resting book). **This is where the Kalshi orderbook shape from Task 1 is verified against reality** — if `up_ask`/`down_ask` are `None` while the dashboard shows live Kalshi prices, the `_ask_from_book` yes/no mapping is inverted or the payload key differs; fix `bot/kalshi.py:_ask_from_book` and re-run.

- [ ] **Step 3: Verify the gate now sees the asks end-to-end**

Run: `DRY_RUN=true .venv/Scripts/python.exe -c "import json; from bot import arb_gate; d=json.load(open('dashboard/live5m.json')); print(arb_gate.evaluate(d['poly_15m'], d['kalshi_15m'], poly_bal=3.53, kalshi_bal=12.21, max_notional=3))"`

Expected: a decision dict. Most likely `{'fire': False, 'reason': 'no joint depth' or 'below Poly $1 min' or 'not arb at real asks', ...}` — which is the whole point: it tells the truth about whether this window is tradeable. Record the reason; a run of these reasons over time is the input to the deferred "is any window tradeable?" decision.

- [ ] **Step 4: CHECKPOINT — full regression**

Run all three:
- `DRY_RUN=true .venv/Scripts/python.exe test_arb_gate.py` -> 19 passed (bar: 0 failed)
- `DRY_RUN=true .venv/Scripts/python.exe test_never_naked.py` -> 32 passed
- `DRY_RUN=true .venv/Scripts/python.exe -c "import bot.live_strategy, bot.pm_strategy, bot.arb_gate"` -> no error

---

## Task 6: Update the handoff + spec status

**Files:**
- Modify: `ARBITRAGE_SESSION_HANDOFF.txt`
- Modify: `docs/superpowers/specs/2026-06-15-liquidity-gate-design.md` (status line)

- [ ] **Step 1: Append a "LIQUIDITY GATE" section to the handoff**

Add, under "WHAT WAS BUILT / FIXED", a short block noting: `bot/arb_gate.py` shared gate; `book_ask()` on both venues; paper now mirrors live via the same gate; feed carries `*_ask`/`*_ask_size`; new skip reasons logged as `gate_skip`; tests `test_arb_gate.py` (19) + `test_never_naked.py` (32). State that NO live run has been done with the gate yet and the kill switch is still ON.

- [ ] **Step 2: Flip the spec status**

In the spec, change `**Status:** Approved design, ready for implementation plan` to `**Status:** Implemented 2026-06-15 (tests green; not yet run live).`

- [ ] **Step 3: Final CHECKPOINT**

Re-run `test_arb_gate.py` and `test_never_naked.py`; confirm both green. Stop here — going live is a separate, explicitly-authorized step (kill switch stays ON).

---

## Done criteria

- `test_arb_gate.py` green (gate unit table + book_ask parsing + paper/live parity + paper sizing).
- `test_never_naked.py` green at 32 (20 never-naked unchanged + 12 gate-skip asserts).
- One live feed tick writes real `*_ask`/`*_ask_size`; the gate returns an honest fire/skip with a canonical reason against real books.
- Kill switch (`journal/STOP`) still present; no real orders placed at any point.
