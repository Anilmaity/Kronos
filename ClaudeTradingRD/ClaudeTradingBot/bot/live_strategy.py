"""LIVE cross-venue 15m lock — REAL-MONEY supervised loop ($10/account smoke test).

This is the real-money mirror of bot/pm_strategy.py. It reuses the SAME edge
filters (MAX_GROSS / MIN_NET) and the SAME _legs() selection, but instead of a
paper ledger it places real orders through bot/exec_kalshi + bot/exec_polymarket.

HONESTY: validate_arb.py measured this lock at ~0.9c/pair net edge with ~15% of
windows exposed to basis risk -> NEGATIVE expected value. This loop exists to
SMOKE-TEST EXECUTION (auth, fills, legging, settlement), not to make money. The
$10/account cap bounds the tuition.

Safety rails:
  * DRY_RUN (default true) -> adapters simulate fills; nothing is sent.
  * MAX_NOTIONAL ($10) hard cap on each account's spend per lock.
  * One lock per window (idempotent via journal/live_account.json).
  * Kill switch: create a file journal/STOP -> no new orders are placed.
  * MIN_SECS_LEFT -> never enter a window about to settle.

Legging (POLY-FIRST): place the UNCERTAIN leg — Polymarket (FOK) — FIRST. It is
the constrained leg (low pUSD balance, FOK-killed when the book moves), so if it
doesn't fill nothing is at risk. Then hedge the Poly fill on the thin Kalshi book
(IOC, partial OK) and LOCK the matched pairs = min(poly_fill, kalshi_fill),
flattening the EXCESS Polymarket on its deep book. Reconciliation uses the
RETURNED fills only (the venue position endpoints lag and must never drive a
flatten). Every order placement is exception-safe, so a crash can't leave a naked
leg; an under-filled unwind raises a loud naked_alert instead.
"""
import csv
import json
import os
from datetime import datetime, timezone

from bot import exec_kalshi, exec_polymarket
# Re-export the gate's edge band so the live drivers (livearb.py / livearb_once.py)
# can read it off live_strategy as their config surface. Single source of truth:
# these ARE arb_gate's constants — the gate owns the entry decision.
from bot.arb_gate import MIN_NET, MAX_GROSS  # noqa: F401  (re-exported for drivers)

MAX_NOTIONAL = float(os.getenv("LIVE_MAX_NOTIONAL", "10"))  # $/account/lock
MIN_SECS_LEFT = int(os.getenv("LIVE_MIN_SECS_LEFT", "90"))
STATE_PATH = "journal/live_account.json"
LOG_PATH = "journal/live_arb_log.csv"
STOP_FLAG = "journal/STOP"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def killed() -> bool:
    return os.path.exists(STOP_FLAG)


_BAL_CACHE = {"ts": 0.0, "poly": None, "kalshi": None,
              "positions": [], "orders": []}


def account_snapshot(max_age=20.0):
    """READ-ONLY view for the dashboard: balances (cached `max_age`s so the
    per-second poll doesn't hammer the venues), config, and recorded locks.
    Does NOT place orders. In DRY_RUN the balances are $10 sentinels."""
    import time
    now = time.time()
    if _BAL_CACHE["poly"] is None or now - _BAL_CACHE["ts"] > max_age:
        try:
            _BAL_CACHE["poly"] = exec_polymarket.balance_detail()
        except Exception as e:  # noqa: BLE001
            _BAL_CACHE["poly"] = {"value": None, "real": False, "note": str(e)[:140]}
        try:
            _BAL_CACHE["kalshi"] = exec_kalshi.balance_detail()
        except Exception as e:  # noqa: BLE001
            _BAL_CACHE["kalshi"] = {"value": None, "real": False, "note": str(e)[:140]}
        try:
            _BAL_CACHE["positions"] = (exec_polymarket.positions() +
                                       exec_kalshi.positions())
        except Exception:  # noqa: BLE001
            _BAL_CACHE["positions"] = []
        try:
            _BAL_CACHE["orders"] = (exec_polymarket.open_orders() +
                                    exec_kalshi.open_orders())
        except Exception:  # noqa: BLE001
            _BAL_CACHE["orders"] = []
        _BAL_CACHE["ts"] = now
    pd = _BAL_CACHE["poly"] or {}
    kd = _BAL_CACHE["kalshi"] or {}
    st = _load_state()
    locks = st.get("locks", [])
    positions = _BAL_CACHE.get("positions", [])
    now = _now_iso()
    hist = [_enrich_lock(l, now) for l in reversed(locks)][:25]
    return {
        "dry_run": exec_kalshi.dry_run(),
        "max_notional": MAX_NOTIONAL,
        "killed": killed(),
        "poly_balance": pd.get("value"), "poly_real": pd.get("real", False),
        "poly_note": pd.get("note", ""),
        "kalshi_balance": kd.get("value"), "kalshi_real": kd.get("real", False),
        "kalshi_note": kd.get("note", ""),
        "positions": positions,
        "orders": _BAL_CACHE.get("orders", []),
        "locks": hist,
        "n_locks": len(locks),
        "pairs_total": sum(l.get("pairs", 0) for l in locks),
        "realized_pnl": round(sum(l["pnl"] for l in hist
                                  if l.get("status") == "settled"), 2),
        # Naked guardian: authoritative alert from the last step() reconciliation
        # + a live read-only heuristic over current positions.
        "naked_alert": st.get("naked_alert"),
        "naked_live": _naked_scan(positions),
    }


def _enrich_lock(lk, now_iso):
    """Add settled-history fields to a recorded lock: cost, fee, P&L, and an
    OPEN/SETTLED status (settled once its window passes). A lock pays $1.00/pair
    at settlement (one leg always wins), so P&L = pairs*gross - fees. For LIVE
    locks this is the EXPECTED result; true venue settlement carries basis risk."""
    pairs = lk.get("pairs", 0) or 0
    lock_cost = lk.get("lock_cost", 0) or 0
    gross = (lk.get("gross_cents", 0) or 0) / 100.0
    kpx = (lk.get("kalshi") or {}).get("px", 0) or 0
    ppx = (lk.get("poly") or {}).get("px", 0) or 0
    try:
        from bot import paper_pm
        fee = round(paper_pm.fee("Kalshi", pairs, kpx)
                    + paper_pm.fee("Polymarket", pairs, ppx), 2)
    except Exception:  # noqa: BLE001
        fee = 0.0
    settles = lk.get("window")
    settled = bool(settles and now_iso and now_iso >= settles)
    out = dict(lk)
    out.update({
        "cost": round(pairs * lock_cost, 2),
        "fee": fee,
        "pnl": round(pairs * gross - fee, 2),
        "settles": settles,
        "status": "settled" if settled else "open",
        "won": True if settled else None,  # lock: one leg always pays $1
    })
    return out


def _naked_scan(positions):
    """READ-ONLY live monitor. A cross-venue lock must hold OFFSETTING positions
    on BOTH venues; flag live exposure that sits on only one venue. Ignores
    already-settled/redeemable dust (e.g. old resolved markets)."""
    # Ignore sub-1-share / sub-25c dust (e.g. an unsellable fractional remnant)
    # and already-settled redeemable positions — only flag a meaningful leg.
    live = [p for p in (positions or [])
            if (p.get("size") or 0) >= 1 and (p.get("value") or 0) >= 0.25
            and not p.get("redeemable")]
    k = [p for p in live if p.get("venue") == "Kalshi"]
    pol = [p for p in live if p.get("venue") == "Polymarket"]
    if k and not pol:
        return {"side": "kalshi", "n": len(k),
                "detail": "Kalshi position(s) with NO Polymarket hedge"}
    if pol and not k:
        return {"side": "poly", "n": len(pol),
                "detail": "Polymarket position(s) with NO Kalshi hedge"}
    return None


def _load_state():
    try:
        with open(STATE_PATH) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"locks": [], "windows_done": []}


def _save_state(st):
    os.makedirs("journal", exist_ok=True)
    with open(STATE_PATH, "w") as fh:
        json.dump(st, fh, indent=1)


def _log(row: dict):
    os.makedirs("journal", exist_ok=True)
    new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)


def _place_leg(venue, side, price, shares, poly15, kalshi15, cid):
    """Place one leg. Returns (filled_shares, order_id, detail).

    EXCEPTION-SAFE: any venue/API error (rejected order, min-size, network) is
    swallowed and reported as filled=0. A raised exception here once crashed
    step() AFTER the first leg filled but BEFORE hedging -> a naked leg. Now a
    failed hedge simply looks like a no-fill, and the caller flattens the other
    leg. NEVER let an order error propagate out of a leg placement."""
    try:
        if venue == "Kalshi":
            ticker = (kalshi15 or {}).get("ticker")
            if not ticker:
                return 0, None, "no kalshi ticker"
            k_side = "yes" if side == "UP" else "no"
            r = exec_kalshi.place_ioc(ticker, k_side, shares,
                                      int(round(price * 100)), cid)
            return int(r.get("filled", 0)), r.get("order_id"), r
        token = (poly15 or {}).get("up_token" if side == "UP" else "down_token")
        if not token:
            return 0, None, "no poly token"
        r = exec_polymarket.place_fok(token, price, shares, "BUY", cid)
        return int(r.get("filled", 0)), r.get("order_id"), r
    except Exception as e:  # noqa: BLE001
        return 0, None, {"error": str(e)[:200], "venue": venue}


def step(live):
    """One tick. Places at most one new lock for the current window."""
    if killed():
        return {"status": "killed", "reason": f"{STOP_FLAG} present"}

    st = _load_state()
    p15, k15 = live.get("poly_15m"), live.get("kalshi_15m")
    arb = live.get("arb15m") or {}
    settles = (p15 or {}).get("window_end")
    secs_left = (p15 or {}).get("seconds_left")

    if not (arb.get("status") == "evaluated" and p15 and k15 and settles):
        return {"status": "idle", "reason": "no evaluated window"}
    if settles in st["windows_done"]:
        return {"status": "skip", "reason": "window already traded"}
    if secs_left is not None and secs_left < MIN_SECS_LEFT:
        return {"status": "skip", "reason": f"only {secs_left}s left"}
    if None in (p15.get("up_cost"), p15.get("down_cost"),
                k15.get("up_cost"), k15.get("down_cost")):
        return {"status": "idle", "reason": "incomplete quotes"}

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
    poly_token = (p15 or {}).get("up_token" if poly_leg[1] == "UP" else "down_token")
    ticker = (k15 or {}).get("ticker")
    if not (poly_token and ticker):
        return {"status": "idle", "reason": "missing token/ticker"}

    dry = exec_kalshi.dry_run()
    _nonce = datetime.now(timezone.utc).strftime("%H%M%S")
    cid = f"L{settles}{_nonce}".replace(":", "").replace("-", "")[:28]

    pf, p_oid, p_det = _place_leg(*poly_leg[:3], shares, p15, k15, cid + "P")
    if pf < 1:
        # Poly didn't fill (FOK killed / balance) -> nothing held; retry later.
        _log({"ts": _now_iso(), "event": "poly_nofill", "window": settles,
              "want": shares, "filled": 0, "detail": str(p_det)[:160]})
        return {"status": "no_fill", "leg": "poly"}

    # 2) Hedge the Poly fill on the thin book (Kalshi IOC). Partial fills are fine
    #    — Kalshi has no $ minimum, just whole contracts.
    kf, k_oid, k_det = _place_leg(*kalshi_leg[:3], pf, p15, k15, cid + "K")

    # 3) NEVER NAKED — lock the pairs BOTH legs filled; flatten the EXCESS POLY on
    #    the deep book. Exception-safe; an under-filled flatten raises a loud alert.
    pairs = min(pf, kf)
    naked_alert = None
    if not dry and pf > pairs:
        want = pf - pairs
        try:
            sold = exec_polymarket.flatten(poly_token, want, cid + "PU")
        except Exception as e:  # noqa: BLE001
            sold = 0
            _log({"ts": _now_iso(), "event": "flatten_error",
                  "window": settles, "detail": str(e)[:160]})
        _log({"ts": _now_iso(), "event": "flatten_poly", "window": settles,
              "want": want, "sold": sold, "reason": str(k_det)[:120]})
        if sold < want:  # couldn't unwind the excess -> real Poly exposure
            naked_alert = {"window": settles, "ticker": ticker,
                           "kalshi": 0, "poly": want - sold,
                           "detail": "Poly excess unwind under-filled — flatten manually"}
            _log({"ts": _now_iso(), "event": "NAKED_ALERT", **naked_alert})

    # Window is DONE the moment real contracts changed hands — never re-attempt,
    # so partial fills can never accumulate across ticks.
    st["windows_done"].append(settles)
    st["naked_alert"] = naked_alert

    if pairs < 1:  # Poly filled but Kalshi couldn't hedge -> Poly flattened -> flat
        _save_state(st)
        _log({"ts": _now_iso(), "event": "legged_unwound", "window": settles,
              "poly_filled": pf, "kalshi_filled": kf})
        return {"status": "legged_unwound", "kalshi_filled": kf,
                "poly_filled": pf, "naked_alert": naked_alert}

    lock = {"window": settles, "pairs": pairs, "lock_cost": round(lock_cost, 4),
            "gross_cents": round(gross * 100, 2),
            "kalshi": {"oid": k_oid, "side": kalshi_leg[1], "px": kalshi_leg[2]},
            "poly": {"oid": p_oid, "side": poly_leg[1], "px": poly_leg[2]},
            "opened": _now_iso(), "dry": dry}
    st["locks"].append(lock)
    _save_state(st)
    _log({"ts": _now_iso(), "event": "lock", "window": settles, "pairs": pairs,
          "lock_cost": round(lock_cost, 4), "gross_cents": round(gross * 100, 2),
          "legs": f"{kalshi_leg[1]} Kalshi@{kalshi_leg[2]:.2f} + "
                  f"{poly_leg[1]} Poly@{poly_leg[2]:.2f}", "dry": dry})
    return {"status": "locked", "pairs": pairs, "lock_cost": lock_cost,
            "gross_cents": round(gross * 100, 2), "dry": dry,
            "naked_alert": naked_alert}
