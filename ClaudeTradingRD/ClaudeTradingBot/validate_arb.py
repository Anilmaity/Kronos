"""Honest validation of the cross-venue 15m Up/Down lock from arb15m_log.csv.

The PM paper account (paper_pm.py) is OPTIMISTIC: it assumes every lock pays
exactly $1 at settlement (one leg wins, one loses). That is only true under a
SINGLE settlement reference. In reality Polymarket settles on Chainlink and
Kalshi on its own index, so near-flat windows can split:

    payout = 1{A=UP} + 1{B=DOWN}   (lock = own UP@A + DOWN@B)
      A=UP , B=DOWN -> $2 (windfall)
      A=UP , B=UP   -> $1
      A=DOWN,B=DOWN -> $1
      A=DOWN,B=UP   -> $0 (total loss of the ~96c stake)

A break needs the two venues to DISAGREE on direction, which is only plausible
when the window settles very close to its open (the "basis-risk zone"). This
script reconstructs each window's settlement from the logged BTC spot, measures
how many profitable locks landed in that danger zone, and contrasts the
optimistic P&L with a basis-risk-stressed P&L.

Usage: python validate_arb.py [basis_usd]   (default danger zone = $15)
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime

LOG = "journal/arb15m_log.csv"
WINDOW_SECS = 900
# Kalshi: ceil(0.07*C*P*(1-P)); Polymarket ~0.072*shares*P*(1-P). At lock level
# the per-pair fee is already baked into net_edge in the log, so we trust
# net_edge for "was this flagged profitable" and use lock_cost for stake.


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ts(s):
    return datetime.fromisoformat(s)


def load_windows():
    """Group per-second rows by their 15m window_end."""
    wins = defaultdict(list)
    with open(LOG, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            we = r.get("window_end")
            if not we:
                continue
            wins[we].append(r)
    return wins


def main():
    basis = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    wins = load_windows()

    # Mirror pm_strategy.py exactly: enter the FIRST tick where the lock is a
    # plausible same-reference arb (gross <= 6c) with net edge >= 0.3c/pair.
    MIN_NET, MAX_GROSS = 0.003, 0.06

    n_win = 0
    n_tradeable = 0          # windows where a STRATEGY-VALID lock existed
    n_danger = 0            # tradeable windows that settled inside the basis zone
    opt_pnl = 0.0            # optimistic: every taken lock pays $1 (paper model)
    worst_pnl = 0.0          # adversarial: every danger-zone lock BREAKS ($0)
    edges = []
    margins = []
    PAIRS = 450              # representative pairs/lock, matching the paper sizing

    for we, rows in sorted(wins.items()):
        n_win += 1
        end = _ts(we.replace("Z", "+00:00"))
        spots = [(_ts(r["ts"]), _f(r["spot"])) for r in rows if _f(r["spot"])]
        if len(spots) < 2:
            continue
        spots.sort()
        open_spot, settle_spot = spots[0][1], spots[-1][1]
        gap = (end - spots[-1][0]).total_seconds()
        margin = settle_spot - open_spot
        margins.append(margin)

        # FIRST strategy-valid tick (chronological), not the cherry-picked min.
        entry = None
        for r in sorted(rows, key=lambda x: x["ts"]):
            ne, lc = _f(r["net_edge"]), _f(r["lock_cost"])
            if ne is None or lc is None:
                continue
            gross = 1.0 - lc
            if ne >= MIN_NET and 0 < gross <= MAX_GROSS:
                entry = (lc, ne)
                break
        if entry is None:
            continue
        lock_cost, net_pair = entry
        n_tradeable += 1
        edges.append(net_pair)

        in_danger = abs(margin) < basis and gap < 120
        if in_danger:
            n_danger += 1
            worst_pnl += (-lock_cost) * PAIRS   # paid stake, collected $0
        else:
            worst_pnl += net_pair * PAIRS
        opt_pnl += net_pair * PAIRS

    print(f"=== CROSS-VENUE 15m LOCK — VALIDATION (basis zone = ${basis:.0f}) ===")
    print(f"data: {LOG}")
    print(f"windows observed:          {n_win}")
    print(f"  tradeable (net>0 lock):  {n_tradeable}  "
          f"({100*n_tradeable/max(n_win,1):.0f}% of windows)")
    print(f"  of those, near-flat:     {n_danger}  "
          f"({100*n_danger/max(n_tradeable,1):.0f}% of tradeable = basis-risk exposed)")
    if edges:
        edges.sort()
        print(f"net edge/pair after fees: mean {sum(edges)/len(edges)*100:.2f}c  "
              f"median {edges[len(edges)//2]*100:.2f}c  max {edges[-1]*100:.2f}c")
    if margins:
        am = sorted(abs(m) for m in margins)
        print(f"|settle-open| move:      median ${am[len(am)//2]:.0f}  "
              f"p25 ${am[len(am)//4]:.0f}  (smaller = more basis risk)")
    print(f"\nP&L @ {PAIRS} pairs/lock across {n_tradeable} locks:")
    print(f"  OPTIMISTIC (paper model, every lock pays $1):  ${opt_pnl:+,.0f}")
    print(f"  ADVERSARIAL (every danger-zone lock breaks):   ${worst_pnl:+,.0f}")
    print("\nREAD: the optimistic number is what paper_pm.py reports. The gap to")
    print("the stressed/adversarial numbers IS the basis risk the paper ignores.")
    print("A real deployment also needs funded accounts on BOTH venues (the")
    print("legal/practical blocker) — this validates the EDGE, not executability.")


if __name__ == "__main__":
    main()
