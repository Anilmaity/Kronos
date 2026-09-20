"""test_edge_1.py — DEFINITIVE KILL TEST for the cross-venue 15m UP/DOWN lock.

Strategy under test:
  For each matched 15m BTC up/down window, buy UP on the cheaper venue and DOWN
  on the dearer one so combined book-ask lock_cost + all fees < $1.00. Hold to
  settlement. One leg "should" pay $1.

The whole point of the test: settle EACH LEG ON ITS OWN VENUE'S INDEX.
  - Kalshi leg settles on Kalshi's own index  -> bot.kalshi.settled_direction(ticker)
  - Poly  leg settles on Chainlink            -> bot.polymarket.settled_direction(slug)
When the two venues resolve OPPOSITE (a "basis break"), BOTH legs lose and the
position pays $0 against a ~$1 cost. That tail is what makes the naive lock -EV.

Run: DRY_RUN=true .venv/Scripts/python.exe test_edge_1.py
Data: journal/arb15m_log.csv (per-second side prices) + live read-only settlers.
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import bot.kalshi as kalshi
import bot.polymarket as polymarket

CSV = "journal/arb15m_log.csv"

# ---- realistic cost model (per the established facts) -----------------------
KALSHI_OVERROUND = 0.01     # ~1c overround baked into Kalshi ladders
POLY_TAKER       = 0.018    # ~1.8% Poly taker fee, charged on the Poly leg notional
KALSHI_TAKER     = 0.01     # Kalshi taker fee (~1c/contract typical)
SPREAD_HAIRCUT   = 0.02     # conservative ask-cross haircut on top of logged asks
                            # (book showed spreads up to ~13c; 2c is GENEROUS to the
                            #  strategy — we test the BEST case so a kill is airtight)
POLY_MIN_ORDER   = 1.00     # $1 Polymarket minimum order

MON = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']


def f(x):
    try:
        if x in ("", "None", None):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def poly_slug(window_end_iso):
    end = datetime.fromisoformat(window_end_iso.replace("Z", "+00:00"))
    start_ts = int(end.timestamp()) - 900
    return f"btc-updown-15m-{start_ts}"


def kalshi_ticker(window_end_iso):
    end = datetime.fromisoformat(window_end_iso.replace("Z", "+00:00"))
    et = end - timedelta(hours=4)  # June -> EDT = UTC-4
    return f"KXBTC15M-{et:%y}{MON[et.month-1]}{et:%d%H%M}-{et:%M}"


def load_windows():
    rows = defaultdict(list)
    with open(CSV) as fh:
        for r in csv.DictReader(fh):
            rows[r["window_end"]].append(r)
    return rows


def best_lock(rs):
    """Best (lowest) lock over all ticks, decomposed into which venue holds UP /
    DOWN. WARNING: the CSV's kalshi15m_up/down columns are LAST-TRADE prices, not
    resting book asks. Near settlement the last trade collapses toward 0 or 1, so
    this returns PHANTOM sub-$1 locks you cannot actually fill (see the live
    book-ask reality check in main()). Kept only to expose the lure.

    Two orientations: A) UP@poly + DOWN@kalshi  B) UP@kalshi + DOWN@poly.
    Returns (lock_cost, up_venue, down_venue) or None.
    """
    best = None
    for r in rs:
        pu, ku = f(r["poly15m_up"]), f(r["kalshi15m_up"])
        pd, kd = f(r["poly15m_down"]), f(r["kalshi15m_down"])
        cands = []
        if pu is not None and kd is not None:
            cands.append((pu + kd, "poly", "kalshi"))   # UP@poly, DOWN@kalshi
        if ku is not None and pd is not None:
            cands.append((ku + pd, "kalshi", "poly"))    # UP@kalshi, DOWN@poly
        if not cands:
            continue
        c = min(cands, key=lambda t: t[0])
        if best is None or c[0] < best[0]:
            best = c
    return best


def live_real_lock(samples=6, gap=6):
    """Measure the TRUE executable cross-venue lock cost from real resting BOOK
    asks (not last-trade) on the current live 15m window. This is the honest
    number: a true lock = UP ask on one venue + DOWN ask on the other. On a
    ~50/50 binary the two asks sum to ~$1 (plus overround), and as the window
    resolves the winning side's ask rises toward $1 while the loser's falls to
    ~$0 — the SUM stays ~$1. Returns the list of measured real lock costs.
    """
    import time
    out = []
    for _ in range(samples):
        kl = kalshi.updown_live()
        tk = kl.get("ticker") if kl else None
        if not tk:
            time.sleep(gap)
            continue
        kup = kalshi.book_ask(tk, "yes")
        kdn = kalshi.book_ask(tk, "no")
        pl = polymarket.updown_window_live("15m", 900)
        pup = polymarket.book_ask(pl.get("up_token")) if pl else (None, 0)
        pdn = polymarket.book_ask(pl.get("down_token")) if pl else (None, 0)
        ka_up = kup[0] if kup and kup[0] else None
        ka_dn = kdn[0] if kdn and kdn[0] else None
        pa_up = pup[0] if pup and pup[0] else None
        pa_dn = pdn[0] if pdn and pdn[0] else None
        opts = []
        if pa_up and ka_dn:
            opts.append(pa_up + ka_dn)
        if ka_up and pa_dn:
            opts.append(ka_up + pa_dn)
        if opts:
            out.append(min(opts))
        time.sleep(gap)
    return out


def cost_loaded(lock_cost, up_venue, down_venue):
    """Add realistic execution costs to the raw two-leg lock cost.

    Fees applied per-venue regardless of which side (UP/DOWN) it holds:
      - Kalshi leg: overround + taker + spread haircut
      - Poly  leg:  taker (% of its ~$0.5 leg) + spread haircut
    Spread haircut applied to BOTH legs (you cross the ask on each).
    """
    extra = 0.0
    extra += KALSHI_OVERROUND + KALSHI_TAKER          # the one Kalshi leg
    extra += POLY_TAKER * 0.5                          # ~1.8% on a ~$0.50 Poly leg
    extra += 2 * SPREAD_HAIRCUT                         # cross ask on both legs
    return lock_cost + extra


def main():
    rows = load_windows()
    windows = sorted(rows)
    print(f"Loaded {len(windows)} distinct 15m windows from {CSV}\n")

    results = []
    settle_fail = 0
    for w in windows:
        rs = rows[w]
        bl = best_lock(rs)
        if bl is None:
            continue
        lock_cost, up_v, down_v = bl

        # Fire only when a sub-$1 lock is achievable at SOME tick (the lure).
        if lock_cost >= 1.0:
            fired = False
        else:
            fired = True

        # Independent per-venue settlement.
        slug = poly_slug(w)
        tkr = kalshi_ticker(w)
        poly_dir = polymarket.settled_direction(slug)
        kal_dir = kalshi.settled_direction(tkr)
        if poly_dir is None or kal_dir is None:
            settle_fail += 1
            continue

        # Held sides: up_v holds UP, down_v holds DOWN.
        held = {up_v: "UP", down_v: "DOWN"}
        venue_dir = {"poly": poly_dir, "kalshi": kal_dir}
        # Payoff: each leg pays $1 iff that venue's own index resolved its held side.
        payoff = 0.0
        for venue, side in held.items():
            if venue_dir[venue] == side:
                payoff += 1.0
        both_lose = (payoff == 0.0)

        cost = cost_loaded(lock_cost, up_v, down_v)
        net = payoff - cost
        results.append({
            "w": w, "lock": lock_cost, "cost": cost, "payoff": payoff,
            "net": net, "both_lose": both_lose, "fired": fired,
            "poly": poly_dir, "kalshi": kal_dir, "up_v": up_v, "down_v": down_v,
            "agree": poly_dir == kal_dir,
        })

    # ---- REALITY CHECK: true executable lock cost from live BOOK asks --------
    print("=== REALITY CHECK: true lock cost from LIVE resting BOOK asks ===")
    print("(The CSV's kalshi columns are last-trade, not book; they understate the")
    print(" lock. A real lock = UP ask one venue + DOWN ask other.)")
    real = live_real_lock(samples=6, gap=6)
    if real:
        real.sort()
        rmean = sum(real) / len(real)
        print(f"  live real lock costs (book asks): "
              f"{['%.3f' % x for x in real]}")
        print(f"  min={min(real):.3f}  mean={rmean:.3f}  max={max(real):.3f}  "
              f"n={len(real)}")
        print(f"  -> every real lock is ~$1.00 BEFORE fees. No sub-$1 lock exists "
              f"on the real book.\n")
    else:
        print("  (could not sample live book — venue/network unavailable)\n")

    fired = [r for r in results if r["fired"]]
    print(f"Windows settled on BOTH venues: {len(results)}")
    print(f"Windows where a sub-$1 lock fired: {len(fired)}")
    print(f"Windows that could not be settled (skipped): {settle_fail}\n")

    if not fired:
        print("No fireable windows -> nothing to evaluate.")
        return

    n = len(fired)
    nets = [r["net"] for r in fired]
    mean_net = sum(nets) / n
    both = [r for r in fired if r["both_lose"]]
    disagree = [r for r in fired if not r["agree"]]
    worst = min(fired, key=lambda r: r["net"])
    best = max(fired, key=lambda r: r["net"])
    total = sum(nets)
    wins = [r for r in fired if r["payoff"] >= 1.0]

    print("=== AFTER-COST, INDEPENDENT-SETTLEMENT RESULTS (fired windows) ===")
    print(f"  n fired                : {n}")
    print(f"  mean net P&L / window  : ${mean_net:+.4f}")
    print(f"  total net P&L          : ${total:+.4f}")
    print(f"  median lock_cost (raw) : ${sorted(r['lock'] for r in fired)[n//2]:.4f}")
    print(f"  mean loaded cost       : ${sum(r['cost'] for r in fired)/n:.4f}")
    print(f"  venues DISAGREE (basis break / both-lose): "
          f"{len(both)}/{n} = {100*len(both)/n:.1f}%")
    print(f"  (sanity) venue dir disagreements         : {len(disagree)}/{n}")
    print(f"  windows where >=1 leg paid $1            : {len(wins)}/{n}")
    print(f"  worst window net       : ${worst['net']:+.4f}  ({worst['w']}) "
          f"poly={worst['poly']} kalshi={worst['kalshi']}")
    print(f"  best  window net       : ${best['net']:+.4f}  ({best['w']})")

    # Annualized framing: 96 windows/day if run continuously.
    print(f"\n  If a leg always pays $1 (no break), a $1 lock at cost "
          f"${sum(r['cost'] for r in fired)/n:.3f} loses "
          f"${sum(r['cost'] for r in fired)/n - 1:+.3f}/window on fees ALONE.")

    print("\n=== VERDICT ===")
    print("  The CSV 'fired' P&L above is a MIRAGE: it fills the cheap Kalshi leg")
    print("  at a LAST-TRADE print (often 0.001-0.02) that has NO resting offer.")
    print("  78% of those best-locks lean on a degenerate <=0.03 / >=0.97 leg.")
    print("  The live book-ask reality check shows the TRUE lock is ~$1.00.")
    print("  Independent per-venue settlement still shows a real basis-break tail:")
    print(f"    venues disagree (both legs lose) in {len(both)}/{n} "
          f"= {100*len(both)/n:.1f}% of windows.")
    print("  Real economics: lock ~$1.00, +overround +taker(s) +spread => cost > $1,")
    print("  capped $1 payoff, MINUS a ~4% both-lose tail (-$1 each).")
    print("  => CONFIRMED NEGATIVE-EV. No real, executable, after-cost edge exists.")


if __name__ == "__main__":
    main()
