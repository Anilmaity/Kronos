"""Claude Strategy risk guard — pure functions, no DB, no broker.

Every limit the Claude session trades under lives here; claude_trade.py calls
check_open() before any order and day_lock() on every call. The session on
reaper cannot change these — they run on the box.
Spec: docs/superpowers/specs/2026-10-06-claude-strategy-design.md §3.2
"""
from __future__ import annotations

DAY_TARGET_USD = 100.0
DAY_LOSS_USD = 100.0
RISK_PER_TRADE_USD = 25.0
MIN_SL_PTS = 1.0            # tighter than this is spread noise on gold
USD_PER_PT_PER_LOT = 100.0  # XAU_USD: $1 move x 1 lot = $100
MIN_LOT = 0.01


def day_lock(day_pnl_usd: float) -> str | None:
    """'target_hit' / 'loss_limit_hit' once the UTC day is done, else None."""
    if day_pnl_usd >= DAY_TARGET_USD:
        return "target_hit"
    if day_pnl_usd <= -DAY_LOSS_USD:
        return "loss_limit_hit"
    return None


def size_lots(sl_dist_pts: float, max_lot: float) -> float | None:
    """Lots risking at most RISK_PER_TRADE_USD at the stop; None if even MIN_LOT risks more."""
    raw = RISK_PER_TRADE_USD / (sl_dist_pts * USD_PER_PT_PER_LOT)
    steps = int(round(raw / MIN_LOT, 6))   # round first: 0.29/0.01 is 28.999…
    if steps < 1:
        return None
    return round(min(max_lot, steps * MIN_LOT), 2)


def check_open(side: str, entry: float, sl: float, tp: float,
               day_pnl_usd: float, has_open: bool, max_lot: float) -> tuple[float | None, str]:
    """(lots, reason) for a requested market entry; lots=None means refuse."""
    lock = day_lock(day_pnl_usd)
    if lock:
        return None, f"day_locked:{lock}"
    if has_open:
        return None, "open_position_cap: one trade at a time"
    side = side.upper()
    if side == "BUY":
        levels_ok = sl < entry < tp
    elif side == "SELL":
        levels_ok = tp < entry < sl
    else:
        return None, f"bad_side: {side}"
    if not levels_ok:
        return None, f"bad_levels: {side} needs SL and TP on opposite sides of entry {entry:.2f}"
    dist = abs(entry - sl)
    if dist < MIN_SL_PTS:
        return None, f"sl_too_tight: {dist:.2f} pts < {MIN_SL_PTS}"
    lots = size_lots(dist, max_lot)
    if lots is None:
        return None, (f"sl_too_wide: {MIN_LOT} lot risks "
                      f"{MIN_LOT * dist * USD_PER_PT_PER_LOT:.2f} USD > {RISK_PER_TRADE_USD:.0f}")
    risk = lots * dist * USD_PER_PT_PER_LOT
    worst = day_pnl_usd - risk
    if worst < -DAY_LOSS_USD:
        return None, f"would_breach_loss_limit: worst case day {worst:.2f} USD"
    return lots, f"ok: {lots} lots, risk {risk:.2f} USD"
