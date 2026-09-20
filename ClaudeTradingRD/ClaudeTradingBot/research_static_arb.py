"""READ-ONLY research: WITHIN-VENUE static arbitrage on Kalshi BTC threshold ladders.

No basis risk (same market, same settlement). Two free-money checks at EXECUTABLE
prices (real book asks via kalshi.book_ask -> orderbook_fp):

  1. SAME-MARKET both-sides: ask_yes(X) + ask_no(X) < $1.
     Buy YES + buy NO of the SAME market -> exactly one pays $1 at settle.
     If the two asks sum to < $1 you pay < $1 for a guaranteed $1. (Happens only
     when the book is locked/crossed: best_yes_bid + best_no_bid > 1.)

  2. CROSS-STRIKE vertical: for strikes X1 < X2, ask_yes(X1) + ask_no(X2) < $1.
     Buy YES(>X1) + NO(>X2). Payout: $1 below X1, $2 between, $1 above X2 -> ALWAYS
     >= $1. If the cost < $1 it is risk-free. (Fair cost is 1 + P(X1<BTC<X2) >= 1,
     so this only triggers on a real mispricing; the narrowest pair is the best.)

Executable size = min(book depth on each leg). Reports any violation with the
guaranteed profit/contract and the fillable size. Places NOTHING.

Run:  DRY_RUN=true .venv/Scripts/python.exe research_static_arb.py
"""
import sys
from bot import kalshi as K

SERIES = ["KXBTCD", "KXBTC", "KXBTC15M"]
MIN_EDGE = 0.005   # ignore sub-0.5c "edges" (noise / not worth fees)


MIN_SIZE = 5   # ignore phantom/thin books -- need real depth on BOTH legs


def _mkt_type(ticker):
    """Kalshi BTC market type from the ticker tail:
      '-T<strike>'  -> 'T' = cumulative THRESHOLD ("BTC above $X"), YES = above.
      '-B<floor>'   -> 'B' = mutually-exclusive BUCKET ("between $X and $Y").
    The cross-strike vertical arb is only valid across pure THRESHOLDS; running it
    over buckets (or mixing the two) manufactures fake arbs that can settle at $0."""
    if "-T" in ticker:
        return "T"
    if "-B" in ticker:
        return "B"
    return "?"


def ladder(series):
    """[(ticker, type, strike, ask_yes, sz_yes, ask_no, sz_no)] for open markets
    with a two-sided executable book."""
    rows = []
    try:
        ms = K._markets(series)
    except Exception:  # noqa: BLE001
        return rows
    for m in ms:
        t = m["ticker"]
        ay, sy = K.book_ask(t, "yes")
        an, sn = K.book_ask(t, "no")
        if ay is None or an is None:
            continue
        rows.append((t, _mkt_type(t), K._strike(m), ay, sy, an, sn))
    return rows


def _real(ask, sz):
    """A leg is genuinely executable only with real depth AND a non-phantom price
    (a lone 1c/99c resting bid produces a 0.01/0.99 'ask' that usually isn't fillable)."""
    return ask is not None and sz is not None and sz >= MIN_SIZE and 0.02 <= ask <= 0.98


def main():
    found = 0
    for s in SERIES:
        rows = ladder(s)
        twosided = [r for r in rows if r[3] is not None and r[5] is not None]
        nT = sum(1 for r in twosided if r[1] == "T")
        print(f"=== {s}: {len(rows)} markets, {len(twosided)} two-sided ({nT} threshold) ===")

        # CHECK 1: same-market both-sides < $1 (valid for ANY market type; buying
        # YES + NO of ONE market pays exactly $1). Require real depth on both legs.
        for t, ty, strike, ay, sy, an, sn in twosided:
            if not (_real(ay, sy) and _real(an, sn)):
                continue
            cost = ay + an
            if cost < 1.0 - MIN_EDGE:
                size = min(sy, sn)
                print(f"  *** SAME-MKT ARB {t} (strike {strike}): "
                      f"YES ask {ay:.3f} + NO ask {an:.3f} = {cost:.3f} < $1 "
                      f"-> +${(1-cost):.3f}/contract x {size} = +${(1-cost)*size:.2f}")
                found += 1

        # CHECK 2: cross-strike vertical -- THRESHOLDS ONLY. For X1 < X2,
        # YES(>X1) + NO(>X2) pays $1/$2/$1 (always >= $1); cost < $1 is a real arb.
        thr = sorted([r for r in twosided if r[1] == "T" and r[2] is not None],
                     key=lambda r: r[2])
        for i in range(len(thr)):
            _t1, _, x1, ay1, sy1, _an1, _sn1 = thr[i]
            for j in range(i + 1, min(i + 4, len(thr))):
                _t2, _, x2, _ay2, _sy2, an2, sn2 = thr[j]
                if not (_real(ay1, sy1) and _real(an2, sn2)):
                    continue
                cost = ay1 + an2          # YES(>x1) + NO(>x2)
                if cost < 1.0 - MIN_EDGE:
                    size = min(sy1, sn2)
                    print(f"  *** VERTICAL ARB YES>{x1:.0f} ({ay1:.3f}) + NO>{x2:.0f} "
                          f"({an2:.3f}) = {cost:.3f} < $1 -> +${(1-cost):.3f}/ct x {size}")
                    found += 1

        # diagnostics: tightest same-market sum (how close to an arb are we?)
        real_pairs = [r for r in twosided if _real(r[3], r[4]) and _real(r[5], r[6])]
        if real_pairs:
            best = min(real_pairs, key=lambda r: r[3] + r[5])
            print(f"  tightest same-mkt YES+NO ask sum: {best[3]+best[5]:.3f} "
                  f"({best[0]}, strike {best[2]}) -- need < 1.000 for arb")
    print(f"\nRESULT: {found} executable static-arb violation(s) found." if found
          else "\nRESULT: NO executable within-venue static arb (ladder is "
                "monotone/no crossed books at real asks).")


if __name__ == "__main__":
    main()
