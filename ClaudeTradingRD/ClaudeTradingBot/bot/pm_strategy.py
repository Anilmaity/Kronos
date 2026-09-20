"""Paper PM auto-strategy: trade the cross-venue 15-min LOCK when net edge > 0.

Buys UP on the cheaper venue + DOWN on the other (same 15-min window). Enters via
the SAME gate as the live account (bot/arb_gate), sized to real book depth.

REAL-SETTLEMENT model: at window close the lock is settled on EACH venue's ACTUAL
resolution — Kalshi's own index (kalshi.settled_direction) and Polymarket's
Chainlink (polymarket.settled_direction). A pair pays $1 for every leg that won, so
the payout per pair is 0 (BASIS BREAK — the venues resolved OPPOSITE, both legs
lose the stake), 1 (normal — they agree, one leg pays), or 2 (windfall — they
disagree the other way, both legs win). This makes paper P&L mirror live INCLUDING
the basis-risk tail that the old optimistic "always pays $1" model hid. A lock whose
venues haven't both resolved yet is left OPEN until they do (or optimistically
settled after STALE_HOURS if a venue never reports).
"""
import os
from datetime import datetime, timedelta

from bot import paper_pm, arb_gate, kalshi, polymarket

MIN_NET = arb_gate.MIN_NET
MAX_GROSS = arb_gate.MAX_GROSS
# Mirror the live cap by reading the SAME env var live_strategy reads, so paper
# size tracks real size automatically (no drift if LIVE_MAX_NOTIONAL is set).
PAPER_MAX_NOTIONAL = float(os.getenv("LIVE_MAX_NOTIONAL", "10"))
STALE_HOURS = 3.0  # if a venue never reports a resolution, optimistically settle


def _dt(s):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _settle_lock(acc, pos, now_iso):
    """Settle ONE open position whose window has closed. For an arb15m lock with
    resolution metadata, settle on the REAL per-venue outcomes (payout 0/1/2);
    return False (leave OPEN) if the venues haven't both resolved yet and the window
    isn't stale. Legacy/non-lock positions fall back to the old binary settle."""
    rv = pos.get("resolve")
    if pos.get("tag") != "arb15m" or not rv:
        paper_pm.settle(acc, pos, won=True)  # legacy: no per-venue info to resolve on
        return True
    kdir = kalshi.settled_direction(rv.get("kalshi_ticker"))
    pdir = polymarket.settled_direction(rv.get("poly_slug"))
    if kdir is not None and pdir is not None:
        payout = ((1.0 if kdir == rv.get("kalshi_side") else 0.0)
                  + (1.0 if pdir == rv.get("poly_side") else 0.0))
        pos["settle_note"] = f"kalshi={kdir} poly={pdir}"
        paper_pm.settle(acc, pos, payout_per_unit=payout)
        return True
    # Not both resolved yet -> wait. Only if the window is very stale (a venue read
    # is persistently failing) fall back to an optimistic settle so it can't sit
    # open forever; flag it honestly.
    st, nw = _dt(pos.get("settles")), _dt(now_iso)
    try:
        stale = bool(st and nw and (nw - st) > timedelta(hours=STALE_HOURS))
    except TypeError:  # naive/aware mismatch if feed formats ever drift -> not stale
        stale = False
    if stale:
        pos["settle_note"] = f"stale-optimistic (kalshi={kdir} poly={pdir})"
        paper_pm.settle(acc, pos, won=True)
        return True
    return False


def step(live):
    """Advance the paper account one tick from a live5m snapshot. Returns the
    account summary (also persists on any change)."""
    acc = paper_pm.load()
    now = live.get("generated_at") or ""
    changed = False

    # 1) Settle any open lock whose window has closed, on REAL per-venue outcomes.
    for pos in list(acc["positions"]):
        if pos.get("settles") and now and now >= pos["settles"]:
            if _settle_lock(acc, pos, now):
                changed = True

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
                           f"{lock_cost*100:.0f}c -> settle on REAL per-venue outcome. "
                           f"Net +{d['net']*100:.1f}c/pair on {shares} pairs.")
                pos = paper_pm.buy_lock(acc, shares, lock_cost, round(fee_total, 4),
                                        settles, legs_str, purpose)
                if pos:
                    # Store what each leg needs to settle on its venue's REAL result.
                    kalshi_leg = next(l for l in legs if l[0] == "Kalshi")
                    poly_leg = next(l for l in legs if l[0] == "Polymarket")
                    pos["resolve"] = {
                        "kalshi_ticker": (k15 or {}).get("ticker"),
                        "kalshi_side": kalshi_leg[1],
                        "poly_slug": (p15 or {}).get("slug"),
                        "poly_side": poly_leg[1],
                    }
                    changed = True

    if changed:
        paper_pm.save(acc)
    return paper_pm.account(acc)
