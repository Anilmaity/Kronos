"""test_edge_3.py — PAPER-TEST: two-sided MAKER / spread-capture on the 15m BTC
up/down tick. Goal: measure whether posting resting bids ~2c inside the live mid
on BOTH UP and DOWN earns the spread, AFTER the adverse-selection kill, fees, the
$1 Poly minimum, and a pro-rata maker rebate.

Run:  DRY_RUN=true .venv/Scripts/python.exe test_edge_3.py

Data: journal/arb15m_log.csv (per-second mids per 15m window).
Settlement: REAL per-venue resolution via bot.polymarket.settled_direction(slug)
(slug reconstructed from window_end), falling back to the logged final mid for
windows the API no longer serves. One live Poly /book pull demonstrates queue depth.
"""
import csv
import collections
import statistics
from datetime import datetime, timezone

import bot.polymarket as pm

CSV = "journal/arb15m_log.csv"
INSIDE = 0.02          # post bid 2c inside the mid (you want to capture this spread)
POLY_TAKER = 0.018     # 1.8% taker fee if you must flatten as a taker
POLY_MIN = 1.00        # $1 Polymarket order minimum
REBATE_TIER = 0.20     # crypto-tier maker rebate = 20% of the taker fee...
YOUR_SHARE = 0.01      # ...times your generous pro-rata share of the pool

# Our real working capital (from memory / pm_account): tiny.
POLY_CAPITAL = 3.53


def load_windows():
    rows = collections.defaultdict(list)
    with open(CSV) as f:
        for r in csv.DictReader(f):
            rows[r["window_end"]].append(r)
    return rows


def col(v, name):
    out = []
    for x in v:
        s = x.get(name)
        if s in ("", "None", None):
            continue
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def real_settlement(window_end):
    """REAL UP/DOWN from Polymarket resolution via reconstructed slug, else None."""
    try:
        end = datetime.fromisoformat(window_end.replace("Z", "+00:00"))
    except ValueError:
        return None
    start = int(end.timestamp()) - 900
    return pm.settled_direction(f"btc-updown-15m-{start}")


def simulate():
    rows = load_windows()
    windows = sorted(rows.keys())

    # --- one live book pull: demonstrate we'd sit BEHIND pros -----------------
    print("=" * 72)
    print("LIVE BOOK REALITY CHECK (queue position)")
    print("=" * 72)
    try:
        live = pm.updown_window_live("15m", 900)
        tok = live["up_token"]
        r = pm._S.get(pm.CLOB + "/book", params={"token_id": tok}, timeout=8).json()
        bids = sorted(r.get("bids") or [], key=lambda x: -float(x["price"]))[:5]
        asks = sorted(r.get("asks") or [], key=lambda x: float(x["price"]))[:5]
        print(f"window: {live['label']}  up_cost={live['up_cost']} down_cost={live['down_cost']}")
        print("top UP bids :", [(b["price"], b["size"]) for b in bids])
        print("top UP asks :", [(a["price"], a["size"]) for a in asks])
        depth = sum(float(b["size"]) for b in bids[:3])
        print(f"-> ~{depth:.0f} shares already resting in top-3 bids. Our ${POLY_CAPITAL:.2f} "
              f"(~{POLY_CAPITAL/0.5:.0f} sh @ 0.50) joins the BACK of that queue.")
    except Exception as e:  # noqa: BLE001
        print("live book unavailable:", e)

    # --- the adverse-selection simulation ------------------------------------
    print("\n" + "=" * 72)
    print("MAKER SPREAD-CAPTURE SIM  (resting bid 2c inside the first-tick mid)")
    print("=" * 72)

    fills = []          # one record per filled leg
    real_used = 0
    proxy_used = 0
    both_filled = 0
    n_eval = 0

    for we in windows:
        v = rows[we]
        ups = col(v, "poly15m_up")
        downs = col(v, "poly15m_down")
        if len(ups) < 5:
            continue
        n_eval += 1

        first_up = ups[0]
        # symmetric: down mid ~= 1 - up mid; use logged down col if present else derive
        first_down = downs[0] if downs else (1 - first_up)

        up_bid = round(first_up - INSIDE, 4)
        down_bid = round(first_down - INSIDE, 4)

        # ADVERSE-SELECTION PROXY: a resting bid fills only when price trades
        # THROUGH it, i.e. intrawindow MIN <= bid. On a coin-flip tick that drives
        # to 0/1, the side that ends up LOSING is exactly the side whose price
        # collapsed through your bid first. So a fill is correlated with a loss.
        up_min = min(ups)
        down_min = min(downs) if downs else min(1 - u for u in ups)
        up_fill = up_min <= up_bid
        down_fill = down_min <= down_bid

        # REAL settlement (per-venue). Fall back to decisive logged final mid.
        direction = real_settlement(we)
        if direction is None:
            f_up = ups[-1]
            if f_up >= 0.90:
                direction = "UP"
            elif f_up <= 0.10:
                direction = "DOWN"
            else:
                direction = "UP" if f_up >= 0.5 else "DOWN"
            proxy_used += 1
        else:
            real_used += 1

        up_win = direction == "UP"
        if up_fill and down_fill:
            both_filled += 1

        # payoff per filled leg: own UP at cost=up_bid -> +(1-up_bid) if UP else -up_bid
        if up_fill:
            fills.append(("UP", up_bid, (1 - up_bid) if up_win else -up_bid))
        if down_fill:
            fills.append(("DOWN", down_bid, (1 - down_bid) if (not up_win) else -down_bid))

    # --- aggregate -----------------------------------------------------------
    n = len(fills)
    gross_pnl = sum(p for _, _, p in fills)             # pure spread-capture P&L
    gross_per = gross_pnl / n if n else 0.0

    # modeled maker rebate income (generous): per filled contract
    rebate_per = REBATE_TIER * POLY_TAKER * YOUR_SHARE
    rebate_total = rebate_per * n

    # taker fee: you must flatten the WINNING-window inventory imbalance as taker
    # when only one leg fills (delta NOT flat). Charge 1.8% of notional on the
    # unmatched single-leg fills. (When both fill you're delta-flat -> no taker.)
    single_leg_fills = n - 2 * both_filled
    taker_cost = POLY_TAKER * 0.5 * max(0, single_leg_fills)  # ~0.5 notional/contract

    net_pnl = gross_pnl + rebate_total - taker_cost
    net_per = net_pnl / n if n else 0.0

    print(f"windows evaluated         : {n_eval}")
    print(f"  settled REAL (API)      : {real_used}")
    print(f"  settled proxy (final mid): {proxy_used}")
    print(f"filled legs (contracts)   : {n}")
    print(f"  windows BOTH sides fill  : {both_filled}  ({both_filled/max(1,n_eval):.1%})")
    print(f"  single-leg (delta-open)  : {single_leg_fills}")
    print()
    print(f"GROSS spread-capture P&L   : ${gross_pnl:+.2f}  ({gross_per*100:+.2f} c / contract)")
    print(f"+ maker rebate (0.20*fee*{YOUR_SHARE} share): ${rebate_total:+.4f}  ({rebate_per*100:+.4f} c/contract)")
    print(f"- taker flatten on single legs (1.8%): ${-taker_cost:+.2f}")
    print(f"= NET P&L                  : ${net_pnl:+.2f}  ({net_per*100:+.2f} c / contract)")
    print()

    # win rate of filled legs
    wins = sum(1 for _, _, p in fills if p > 0)
    print(f"filled-leg win rate        : {wins}/{n} = {wins/max(1,n):.1%}")
    print(f"avg WIN  payoff            : {statistics.mean([p for *_, p in fills if p>0])*100:+.2f} c"
          if wins else "no wins")
    losses = [p for *_, p in fills if p <= 0]
    if losses:
        print(f"avg LOSS payoff            : {statistics.mean(losses)*100:+.2f} c")

    # $1-min reality
    print(f"\n$1 Poly min: at a 0.50 bid, $1 = 2 shares; our ${POLY_CAPITAL:.2f} funds ~"
          f"{int(POLY_CAPITAL//POLY_MIN)} simultaneous resting orders total — cannot quote both "
          f"sides of many concurrent windows.")

    # DEPLOY BAR
    print("\n" + "=" * 72)
    bar_met = net_per > 0 and n >= 200
    print(f"DEPLOY BAR: net edge > 0 over >=200 fills on real settlement -> "
          f"{'PASS' if bar_met else 'FAIL'}")
    print(f"  net/contract = {net_per*100:+.2f}c   fills = {n}")
    print("=" * 72)
    return net_per, n, real_used


if __name__ == "__main__":
    simulate()
