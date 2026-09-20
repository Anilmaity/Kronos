"""test_edge_2.py — WITHIN-VENUE Kalshi static / Dutch-book arb: FIX THE FALSE
POSITIVES, then confirm zero.

Context: research_static_arb.py CHECK 2 (vertical) sorts ALL two-sided KXBTC
markets by strike and pairs ask_YES(i) + ask_NO(j) as if every contract were a
monotone THRESHOLD (T). But KXBTC mixes:
  - T contracts ("$X or above" / "$X or below") -> monotone CDF ladder
  - B contracts ("$X to $X+99.99")             -> mutually-exclusive narrow buckets
A B-bucket YES ask (~0.06-0.13, price of BTC landing in a $100 band) summed with
a T-NO ask is NOT a guaranteed >=$1 payout: if BTC settles far away BOTH legs pay
$0 and you lose 100% of stake. That is the fabricated "VERTICAL ARB".

This script:
  1. Reproduces the buggy CHECK 2 on the live KXBTC expiry (shows fake arbs).
  2. Applies the FIX:
       (a) classify each ticker B vs T via floor/cap + ticker pattern;
       (b) vertical check runs ONLY across same-direction PURE-T contracts
           (ask_YES(>X1) + ask_NO(>X2), X1<X2 -> always >=$1, sub-$1 = real arb);
       (c) same-market crossed-book check ask_YES(X)+ask_NO(X) < $1;
       (d) bucket exhaustive set: SELL-ALL Dutch book = sum of real resting
           YES-BIDS across all mutually-exclusive buckets > $1 (you SELL each
           bucket's YES; exactly one settles $1, so collecting > $1 is free money).
           The buy-all version (sum of bucket YES-ASKS < 1) is the mirror; we
           report both but DISCARD the 0.01 placeholder asks with no executable
           size, since those are non-resting phantom levels.
  3. Costs: Kalshi taker fee modeled both as the repo's ~1c/contract convention
     AND Kalshi's real ceil(0.07 * p * (1-p)) formula, plus the spread you cross
     (we already buy at the ASK = cross the spread). Same settlement => NO basis
     risk, so any genuine after-fee sub-$1 set is true free money.

Run:  DRY_RUN=true .venv/Scripts/python.exe test_edge_2.py
"""
import math
import re
from bot import kalshi as K

SERIES = ["KXBTCD", "KXBTC", "KXBTC15M"]
MIN_EDGE = 0.005          # ignore sub-0.5c noise
PLACEHOLDER_ASK = 0.01    # Kalshi seeds a 1c phantom level w/ huge size; not real
MIN_DEPTH = 3             # require a few executable contracts each leg
KALSHI_FLAT_FEE = 0.01    # repo convention: ~1c/contract taker


def kalshi_real_fee(price):
    """Kalshi general taker fee: ceil(0.07 * C * P * (1-P)) cents per contract,
    here per 1 contract -> dollars. (0.07 is the standard tier.)"""
    raw = 0.07 * price * (1.0 - price)
    return math.ceil(raw * 100) / 100.0  # round up to next cent


def classify(m):
    """'T' threshold (monotone), 'B' bucket (mutually exclusive), or '?'."""
    t = m.get("ticker", "")
    fs, cs = m.get("floor_strike"), m.get("cap_strike")
    # bucket: has BOTH a floor and a cap (a finite $100-ish band) or -B in ticker
    if "-B" in t:
        return "B"
    if isinstance(fs, (int, float)) and isinstance(cs, (int, float)):
        return "B"
    # threshold: one-sided (floor-only "or above", or cap-only "or below")
    if re.search(r"-T[\d.]+$", t):
        return "T"
    if "15M" in t:
        return "T"   # up/down vs a single target = a threshold
    return "?"


def t_direction(m):
    """For a T contract, 'above' (floor_strike, YES=BTC>=X) or 'below'
    (cap_strike, YES=BTC<=X). Mixing the two breaks the monotone-ladder logic."""
    if isinstance(m.get("floor_strike"), (int, float)):
        return "above"
    if isinstance(m.get("cap_strike"), (int, float)):
        return "below"
    return None


def collect(series):
    """[(m, type, dir, strike, ask_yes, sz_yes, ask_no, sz_no,
        yes_bid, yes_bid_sz)] for open markets. Pulls raw book once per market
    so we get real resting BIDS for the sell-all check (not just derived asks)."""
    out = []
    try:
        ms = K._markets(series)
    except Exception as e:  # noqa: BLE001
        print(f"  [{series}] _markets error: {e}")
        return out
    for m in ms:
        t = m["ticker"]
        ay, sy = K.book_ask(t, "yes")
        an, sn = K.book_ask(t, "no")
        # raw book for real YES bids (yes_dollars levels)
        yes_bid, yes_bid_sz = None, 0
        try:
            d = K._get(f"/markets/{t}/orderbook") or {}
            fp = (d.get("orderbook_fp") or {})
            yl = fp.get("yes_dollars") or []
            real = [lvl for lvl in yl if float(lvl[0]) > PLACEHOLDER_ASK + 1e-9]
            if real:
                best = max(real, key=lambda lvl: float(lvl[0]))
                yes_bid, yes_bid_sz = float(best[0]), int(float(best[1]))
        except Exception:  # noqa: BLE001
            pass
        out.append((m, classify(m), t_direction(m), K._strike(m),
                    ay, sy, an, sn, yes_bid, yes_bid_sz))
    return out


def is_real_ask(ask, sz):
    """A genuinely executable ask: priced above the 1c placeholder OR, if at 1c,
    only count it (it can be real deep-ITM). We require depth >= MIN_DEPTH and
    treat a lone 0.01-with-huge-size as suspect but still test it — the point is
    it never makes a SUB-$1 SET unless paired correctly."""
    return ask is not None and sz is not None and sz >= MIN_DEPTH


def buggy_vertical(rows):
    """Reproduce research_static_arb.py CHECK 2 verbatim: sort ALL two-sided by
    strike, pair ask_YES(i)+ask_NO(j). Counts fabricated arbs."""
    ws = sorted([r for r in rows if r[3] is not None
                 and r[4] is not None and r[6] is not None],
                key=lambda r: r[3])
    fakes = []
    for i in range(len(ws)):
        _, ty1, _, x1, ay1, sy1, _, _, _, _ = ws[i]
        for j in range(i + 1, min(i + 4, len(ws))):
            _, ty2, _, x2, _, _, an2, sn2, _, _ = ws[j]
            cost = ay1 + an2
            if cost < 1.0 - MIN_EDGE:
                fakes.append((x1, ty1, ay1, x2, ty2, an2, cost, min(sy1, sn2)))
    return fakes


def fixed_vertical(rows):
    """CORRECT vertical: only across PURE-T, SAME-DIRECTION contracts. For 'above'
    thresholds X1<X2: YES(>=X1)+NO(>=X2) pays $1 below X1, $2 in [X1,X2), $1 above
    -> always >=$1. Sub-$1 after fees = real arb."""
    ts = [r for r in rows if r[1] == "T" and r[2] == "above"
          and r[3] is not None and is_real_ask(r[4], r[5]) and is_real_ask(r[6], r[7])]
    ts.sort(key=lambda r: r[3])
    hits = []
    for i in range(len(ts)):
        _, _, _, x1, ay1, sy1, _, _, _, _ = ts[i]
        for j in range(i + 1, len(ts)):
            _, _, _, x2, _, _, an2, sn2, _, _ = ts[j]
            gross = ay1 + an2
            fee = kalshi_real_fee(ay1) + kalshi_real_fee(an2)
            net = gross + fee
            if net < 1.0 - MIN_EDGE:
                hits.append((x1, ay1, x2, an2, gross, net, min(sy1, sn2)))
    return hits


def same_market_crossed(rows):
    """ask_YES(X) + ask_NO(X) < $1 on the SAME market (locked/crossed book)."""
    hits = []
    for (m, ty, dr, strike, ay, sy, an, sn, _, _) in rows:
        if not (is_real_ask(ay, sy) and is_real_ask(an, sn)):
            continue
        gross = ay + an
        net = gross + kalshi_real_fee(ay) + kalshi_real_fee(an)
        if net < 1.0 - MIN_EDGE:
            hits.append((m["ticker"], strike, ay, an, gross, net, min(sy, sn)))
    return hits


def bucket_sell_all(rows):
    """SELL-ALL Dutch book on the mutually-exclusive B buckets of one expiry:
    sum of REAL resting YES-BIDS (placeholder 0.01 discarded) across every bucket.
    You SELL YES on each bucket; exactly one settles $1. If you collect > $1 you
    keep the difference risk-free. Size = min bid depth across buckets."""
    bs = [r for r in rows if r[1] == "B" and r[8] is not None and r[9] >= MIN_DEPTH]
    if not bs:
        return None
    total_bid = sum(r[8] for r in bs)
    min_sz = min(r[9] for r in bs)
    # selling pays a taker fee too
    fee = sum(kalshi_real_fee(r[8]) for r in bs)
    net = total_bid - fee
    return (len(bs), total_bid, fee, net, min_sz)


def bucket_buy_all(rows):
    """BUY-ALL: sum of executable bucket YES-ASKS (placeholder 0.01 discarded).
    If < $1 you own every bucket -> guaranteed $1 -> free money. Reports the sum
    using ONLY asks priced above the placeholder with real depth."""
    bs = [r for r in rows if r[1] == "B" and r[4] is not None
          and r[4] > PLACEHOLDER_ASK + 1e-9 and r[5] >= MIN_DEPTH]
    if not bs:
        return None
    total_ask = sum(r[4] for r in bs)
    fee = sum(kalshi_real_fee(r[4]) for r in bs)
    return (len(bs), total_ask, total_ask + fee, min(r[5] for r in bs))


def main():
    grand_real = 0
    for s in SERIES:
        rows = collect(s)
        twosided = [r for r in rows if r[4] is not None and r[6] is not None]
        nB = sum(1 for r in rows if r[1] == "B")
        nT = sum(1 for r in rows if r[1] == "T")
        print(f"\n=== {s}: {len(rows)} mkts | {nT} T | {nB} B | "
              f"{len(twosided)} two-sided ===")

        fakes = buggy_vertical(rows)
        print(f"  [OLD BUGGY LOGIC] fabricated vertical 'arbs': {len(fakes)}")
        for (x1, ty1, ay1, x2, ty2, an2, cost, sz) in fakes[:6]:
            tag = "B-bucket YES x T-NO (FAKE)" if (ty1 == "B" or ty2 == "B") \
                  else "T x T"
            print(f"      strike {x1:.0f}({ty1}) YES {ay1:.3f} + "
                  f"{x2:.0f}({ty2}) NO {an2:.3f} = {cost:.3f}  [{tag}]")

        sm = same_market_crossed(rows)
        fv = fixed_vertical(rows)
        print(f"  [FIXED] same-market crossed-book arbs (net<$1): {len(sm)}")
        for h in sm:
            print(f"      *** {h[0]} YES {h[2]:.3f}+NO {h[3]:.3f} "
                  f"gross {h[4]:.3f} net {h[5]:.3f} x{h[6]}")
        print(f"  [FIXED] pure-T same-direction vertical arbs (net<$1): {len(fv)}")
        for h in fv:
            print(f"      *** >{h[0]:.0f} YES {h[1]:.3f} + >{h[2]:.0f} NO {h[3]:.3f} "
                  f"gross {h[4]:.3f} net {h[5]:.3f} x{h[6]}")

        ba = bucket_buy_all(rows)
        if ba:
            n, ta, taf, sz = ba
            verdict = "ARB" if taf < 1.0 - MIN_EDGE else "no arb"
            print(f"  [FIXED] buy-all {n} buckets (real asks): sum_ask {ta:.3f}, "
                  f"+fee {taf:.3f}  -> {verdict} (need <1.000), minsz {sz}")
        else:
            print("  [FIXED] buy-all buckets: no buckets with real (non-0.01) "
                  "asks + depth")

        sa = bucket_sell_all(rows)
        if sa:
            n, tb, fee, net, sz = sa
            verdict = "ARB" if net > 1.0 + MIN_EDGE else "no arb"
            print(f"  [FIXED] sell-all {n} buckets (real bids): sum_bid {tb:.3f}, "
                  f"-fee {fee:.3f} -> net {net:.3f}  -> {verdict} "
                  f"(need >1.000), minsz {sz}")
        else:
            print("  [FIXED] sell-all buckets: no buckets with real resting "
                  "YES-bids + depth")

        # tightest monotone T ladder same-market sum (overround gauge)
        tt = [r for r in rows if r[1] == "T" and is_real_ask(r[4], r[5])
              and is_real_ask(r[6], r[7])]
        if tt:
            best = min(tt, key=lambda r: r[4] + r[6])
            print(f"  T-ladder tightest same-mkt YES+NO ask: "
                  f"{best[4] + best[6]:.3f} ({best[0]['ticker']}) "
                  f"-- ~1.0x = overround, need <1.000 for arb")

        grand_real += len(sm) + len(fv)
        if ba and ba[2] < 1.0 - MIN_EDGE:
            grand_real += 1
        if sa and sa[3] > 1.0 + MIN_EDGE:
            grand_real += 1

    print(f"\n================ RESULT ================")
    print(f"REAL after-fee within-venue static arbs (all structurally sound "
          f"checks, all series): {grand_real}")
    if grand_real == 0:
        print("=> ZERO. The old script's 'arbs' were B-bucket-vs-T false "
              "positives. The monotone T ladder prices at/above $1 (overround); "
              "no crossed book; bucket sets do not Dutch-book. No free money.")


if __name__ == "__main__":
    main()
