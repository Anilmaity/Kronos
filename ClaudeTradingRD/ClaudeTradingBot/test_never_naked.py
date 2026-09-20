"""Safety test: live_strategy.step() can NEVER end with one leg unmatched.

POLY-FIRST ordering: Polymarket (the constrained / low-balance / FOK-kill-prone
leg) is committed FIRST; Kalshi (deep balance, thin book) hedges the Poly fill;
the EXCESS Poly is flattened. Invariant after each step: Kalshi held == Poly held
(no naked leg) OR a naked_alert is raised (honest, not silent).

Includes regressions for: the data-api position-endpoint LAG (must reconcile from
returned fills), a hedge that RAISES (must not crash naked), and a partial Kalshi
hedge (must LOCK the matched portion, flattening the Poly excess).

Run:  .venv/Scripts/python.exe test_never_naked.py
"""
import os
os.environ["DRY_RUN"] = "true"

from bot import live_strategy as LS
from bot import paper_pm

WIN0 = "2026-06-15T07:00:00Z"


class FakeKalshi:
    """Net contracts signed +yes / -no. place_ioc reports the REAL fill. May
    raise (API error) or lag its position read."""
    def __init__(self, fill_per_buy, lag=False, raise_on_buy=False):
        self.pos = 0
        self.fill = fill_per_buy
        self.lag = lag
        self.raise_on_buy = raise_on_buy

    def dry_run(self):
        return False

    def balance(self):
        return 5.0

    def place_ioc(self, ticker, side, count, price_cents, cid):
        if self.raise_on_buy:
            raise RuntimeError("kalshi API error")
        a = min(int(count), self.fill)
        self.pos += a if side == "yes" else -a
        return {"order_id": "K" + cid, "status": "executed", "filled": a}

    def position_qty(self, ticker):
        return 0 if self.lag else self.pos

    def flatten(self, ticker, side, count, cid):
        c = int(count)
        if side == "yes":
            self.pos -= min(c, max(0, self.pos))
        else:
            self.pos += min(c, max(0, -self.pos))
        return c


class FakePoly:
    """Placed FIRST. place_fok BUY fills `size` iff capacity >= size (FOK). flatten
    sells up to flatten_cap (model a thin/min-size unwind)."""
    def __init__(self, capacity, lag=False, flatten_cap=10**9):
        self.pos = 0
        self.fill = capacity
        self.lag = lag
        self.flatten_cap = flatten_cap

    def dry_run(self):
        return False

    def balance(self):
        return 5.0

    def place_fok(self, token, price, size, side, cid):
        if str(side).upper() == "BUY":
            f = int(size) if self.fill >= int(size) else 0
            self.pos += f
            return {"order_id": "P" + cid, "filled": f}
        s = min(int(size), self.pos)
        self.pos -= s
        return {"filled": s}

    def position_qty(self, token):
        return 0.0 if self.lag else float(self.pos)

    def flatten(self, token, size, cid=""):
        s = min(int(size), self.flatten_cap, self.pos)
        self.pos -= s
        return s


def _wire(fk, fp, state):
    LS.exec_kalshi = fk
    LS.exec_polymarket = fp
    LS.killed = lambda: False
    LS._load_state = lambda: state
    LS._save_state = lambda s: state.update(s)
    LS._log = lambda r: None
    paper_pm.fee = lambda v, s, p: 0.0


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


def _held(fk, fp):
    return max(0, -fk.pos), int(fp.pos)  # Kalshi leg DOWN ('no') -> held = -pos


PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS " if cond else "  FAIL ") + name + (("  -> " + extra) if extra else ""))


def scenario(name, fp, fk, expect_status, expect_pairs, allow_alert=False):
    state = {"locks": [], "windows_done": []}
    _wire(fk, fp, state)
    res = LS.step(_live())
    kh, ph = _held(fk, fp)
    alert = res.get("naked_alert")
    print(f"[{name}] status={res.get('status')} kalshi_held={kh} poly_held={ph} "
          f"pairs={res.get('pairs')} alert={'Y' if alert else 'N'}")
    check(name + ": NEVER NAKED (matched or alerted)",
          (kh == ph) or (allow_alert and alert is not None),
          f"kalshi={kh} poly={ph} alert={alert}")
    check(name + f": status=={expect_status}", res.get("status") == expect_status,
          str(res.get("status")))
    if expect_pairs is not None:
        check(name + f": pairs=={expect_pairs}",
              (res.get("pairs") or 0) == expect_pairs, str(res.get("pairs")))


print("=== never-naked scenarios (POLY-FIRST, LIVE-mode mocks) ===")
# (a) clean lock: both legs fill full
scenario("a/clean-lock", FakePoly(99), FakeKalshi(99), "locked", 9)
# (b) Kalshi can't hedge at all -> flatten all Poly -> flat
scenario("b/kalshi-nofill", FakePoly(99), FakeKalshi(0), "legged_unwound", None)
# (c) Poly FOK killed -> nothing held, no_fill (Kalshi never touched)
scenario("c/poly-nofill", FakePoly(0), FakeKalshi(99), "no_fill", None)
# (d) NEW CAPABILITY: Kalshi only PARTIALLY hedges -> LOCK the matched 3, flatten
#     the 6 Poly excess. (Kalshi-first could never complete this.)
scenario("d/kalshi-partial-LOCKS", FakePoly(99), FakeKalshi(3), "locked", 3)
# (e) REGRESSION: both fill but position endpoints LAG -> still lock via returns
scenario("e/position-lag", FakePoly(99, lag=True), FakeKalshi(99, lag=True),
         "locked", 9)
# (f) Poly excess unwind can't fill (thin/min) -> honest naked_alert on the excess
scenario("f/poly-excess-underfill", FakePoly(99, flatten_cap=0), FakeKalshi(8),
         "locked", 8, allow_alert=True)
# (g) REGRESSION: the Kalshi hedge RAISES -> swallowed (kf=0) -> Poly flattened
scenario("g/hedge-raises", FakePoly(99), FakeKalshi(99, raise_on_buy=True),
         "legged_unwound", None)

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
# k) not arb at real asks: push the poly UP ask up so the lock leaves the band
_bad = _live(); _bad["poly_15m"]["up_ask"] = 0.62
gate_scenario("k/not-arb", _bad, "skip", "not arb at real asks")
# l) missing ask -> no book
_nb = _live(); _nb["kalshi_15m"]["down_ask"] = None
gate_scenario("l/no-book", _nb, "skip", "no book")

# (h) accumulation guard
print("\n=== accumulation guard ===")
fp, fk = FakePoly(99), FakeKalshi(99)
state = {"locks": [], "windows_done": []}
_wire(fk, fp, state)
r1 = LS.step(_live())
pos1 = (fk.pos, fp.pos)
r2 = LS.step(_live())
pos2 = (fk.pos, fp.pos)
print(f"[h] step1={r1.get('status')} step2={r2.get('status')} {pos1} -> {pos2}")
check("h: 2nd call on same window skipped", r2.get("status") == "skip", str(r2.get("status")))
check("h: no extra contracts on retry", pos1 == pos2, f"{pos1} -> {pos2}")

print(f"\n=== RESULT: {len(PASS)} passed, {len(FAIL)} failed ===")
if FAIL:
    for n in FAIL:
        print("  FAILED:", n)
    raise SystemExit(1)
print("ALL GREEN — POLY-FIRST never-naked holds on every path.")
