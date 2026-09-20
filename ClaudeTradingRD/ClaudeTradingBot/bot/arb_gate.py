"""Shared pure liquidity gate for the cross-venue 15m lock.

ONE source of truth for the entry/size/price decision, called by BOTH the paper
account (bot/pm_strategy.py) and the live account (bot/live_strategy.py) so they
can never diverge. No I/O: it reads REAL asks + sizes already placed on the
snapshot by the feed, and returns a fire/skip decision sized to what BOTH books
can actually absorb at an arb-preserving price.

Skip reasons are canonical strings (asserted by tests + logged): "no book",
"not arb at real asks", "no joint depth", "below Poly $1 min".
"""
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
