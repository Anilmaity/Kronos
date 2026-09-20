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
# CURRENT API: depth under orderbook_fp.{yes_dollars,no_dollars}, prices in DOLLARS,
# sizes may be fractional. To BUY yes -> cross best NO bid: yes_ask = 1 - best_no_bid.
fp_book = {"orderbook_fp": {
    "yes_dollars": [["0.5600", "301.00"], ["0.5500", "100"]],
    "no_dollars":  [["0.4300", "4092.97"], ["0.4200", "50"]]}}
fkp, fks = kalshi._ask_from_book(fp_book, "yes")
check("fp yes ask = 1 - best_no_bid(0.43) = 0.57", abs(fkp - 0.57) < 1e-9, str(fkp))
check("fp yes ask size = floor(best_no_bid 4092.97) = 4092", fks == 4092, str(fks))
fkp2, fks2 = kalshi._ask_from_book(fp_book, "no")
check("fp no ask = 1 - best_yes_bid(0.56) = 0.44", abs(fkp2 - 0.44) < 1e-9, str(fkp2))
check("fp no ask size = floor(best_yes_bid 301.00) = 301", fks2 == 301, str(fks2))
# orderbook_fp present but that side empty -> (None, 0)
check("fp empty side -> (None,0)", kalshi._ask_from_book({"orderbook_fp": {"yes_dollars": [], "no_dollars": []}}, "yes") == (None, 0))
# precedence: when BOTH present, prefer orderbook_fp (real data) over legacy
both = {"orderbook_fp": {"no_dollars": [["0.4300", "9"]], "yes_dollars": [["0.5600","9"]]},
        "orderbook": {"yes": [[40, 12]], "no": [[55, 7]]}}
bp, bs = kalshi._ask_from_book(both, "yes")
check("fp preferred over legacy: yes ask 0.57 size 9", abs(bp - 0.57) < 1e-9 and bs == 9, f"{bp},{bs}")

# Polymarket CLOB /book: asks sorted; best ask = lowest price. size in shares.
p_book = {"asks": [{"price": "0.47", "size": "9"}, {"price": "0.48", "size": "100"}]}
pp, ps = polymarket._ask_from_book(p_book)
check("poly best ask price = 0.47", abs(pp - 0.47) < 1e-9, str(pp))
check("poly best ask size = 9", ps == 9, str(ps))
check("poly empty book -> (None, 0)", polymarket._ask_from_book({"asks": []}) == (None, 0))

from bot import arb_gate, paper_pm

# Isolate the gate's depth/arb/size logic from the fee MODEL (which lives in and is
# tested by paper_pm): zero the fee for this decision table, mirroring how
# test_never_naked.py wires `paper_pm.fee` to 0.
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

# Upper gross bound: lock_cost 0.90 -> gross 0.10 > MAX_GROSS(0.06) -> not arb.
p15, k15 = snap(0.45, 50, 0.55, 50, 0.55, 50, 0.45, 50)  # c1=0.90 < c2=1.10
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("gross>MAX_GROSS -> not arb", d["fire"] is False and d["reason"] == "not arb at real asks", d["reason"])

# c2 lock selected: UP-Kalshi + DOWN-Poly is the cheaper lock.
p15, k15 = snap(0.55, 50, 0.46, 50, 0.49, 50, 0.55, 50)  # c2=ku+pd=0.95 < c1=1.10
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("c2 lock: Kalshi-UP + Poly-DOWN", d["fire"] is True and [l[0] for l in d["legs"]] == ["Kalshi", "Polymarket"], str(d["legs"]))

# Net-after-fees gate: deep 3c-gross lock but a large fee erodes net below MIN_NET.
_saved_fee = paper_pm.fee
paper_pm.fee = lambda v, s, p: 0.5   # 50c/leg -> per-pair fee dwarfs the 3c edge
p15, k15 = snap(0.46, 50, 0.54, 50, 0.49, 50, 0.51, 50)
d = arb_gate.evaluate(p15, k15, poly_bal=100, kalshi_bal=100, max_notional=10)
check("net<MIN_NET after fees -> not arb", d["fire"] is False and d["reason"] == "not arb at real asks", d["reason"])
paper_pm.fee = _saved_fee   # restore the zero-fee stub for any later tests

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

# Parity: gate-skip snapshot => paper places nothing (same gate as live).
from bot import arb_gate
_s = _gate_snap(99, 0)
d = arb_gate.evaluate(_s["poly_15m"], _s["kalshi_15m"], poly_bal=1000, kalshi_bal=1000, max_notional=10)
acc2 = paper_pm._blank(); paper_pm.load = lambda: acc2
pm_strategy.step(_gate_snap(p_up_sz=99, k_dn_sz=0))
paper_locks = [p for p in acc2["positions"] if p.get("tag") == "arb15m"]
check("parity: gate skip => paper places nothing", d["fire"] is False and not paper_locks, d["reason"])

# --- real-settlement paper model: lock settles on per-venue outcomes (0/1/2) ---
from bot import kalshi as _Kd, polymarket as _Pd

def _lockpos(side_k, side_p, shares=10, cost_pp=0.96):
    return {"id": 1, "tag": "arb15m", "shares": shares,
            "settles": "2026-06-15T20:30:00Z", "cost": round(shares * cost_pp, 4),
            "fee": 0.0, "status": "open",
            "resolve": {"kalshi_ticker": "T", "kalshi_side": side_k,
                        "poly_slug": "S", "poly_side": side_p}}

def _settle(kdir, pdir, now="2026-06-15T20:31:00Z", side_k="UP", side_p="DOWN"):
    _Kd.settled_direction = lambda t: kdir
    _Pd.settled_direction = lambda s: pdir
    acc = {"balance": 100.0, "positions": [], "history": []}
    pos = _lockpos(side_k, side_p); acc["positions"].append(pos)
    done = pm_strategy._settle_lock(acc, pos, now)
    return done, acc, pos

# BASIS BREAK: lock UP-Kalshi + DOWN-Poly, but Kalshi=DOWN & Poly=UP -> both lose
done, acc, _ = _settle("DOWN", "UP")
h = acc["history"][-1]
check("basis break -> payout 0", done and h["payout_per_unit"] == 0.0, str(h.get("payout_per_unit")))
check("basis break -> full-stake loss pnl -9.6", abs(h["pnl"] - (-9.6)) < 1e-6, str(h["pnl"]))
# NORMAL (venues agree UP): UP-Kalshi wins, DOWN-Poly loses -> payout 1
done, acc, _ = _settle("UP", "UP")
h = acc["history"][-1]
check("normal agree -> payout 1", h["payout_per_unit"] == 1.0, str(h["payout_per_unit"]))
check("normal -> pnl = shares - cost = +0.4", abs(h["pnl"] - 0.4) < 1e-6, str(h["pnl"]))
# NORMAL (venues agree DOWN): UP-Kalshi loses, DOWN-Poly wins -> payout 1
done, acc, _ = _settle("DOWN", "DOWN")
check("agree DOWN -> payout 1", acc["history"][-1]["payout_per_unit"] == 1.0, str(acc["history"][-1]["payout_per_unit"]))
# WINDFALL: Kalshi=UP & Poly=DOWN -> both legs win -> payout 2
done, acc, _ = _settle("UP", "DOWN")
check("windfall -> payout 2", acc["history"][-1]["payout_per_unit"] == 2.0, str(acc["history"][-1]["payout_per_unit"]))
# UNRESOLVED: one venue None -> leave OPEN, nothing settled
done, acc, pos = _settle(None, "UP")
check("unresolved -> left open", (not done) and pos["status"] == "open" and not acc["history"], str(done))
# STALE unresolved (>3h past close) -> optimistic fallback settle
done, acc, pos = _settle(None, "UP", now="2026-06-16T00:00:00Z")
check("stale unresolved -> optimistic settle", done and len(acc["history"]) == 1, str(done))

print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    raise SystemExit(1)
print("ALL GREEN")
