"""READ-ONLY research: is there an executable cross-venue lock between Kalshi
KXBTCD/KXBTC threshold books and Polymarket 'Bitcoin above $X' threshold markets?

A true lock needs the SAME strike AND the SAME settlement instant on both venues
(else it's a basis bet, not an arb). This script pulls executable ASKS on both
sides, matches each Poly threshold to its nearest Kalshi strike at the closest
settlement time, and reports: settlement-time gap, strike gap, and the lock cost
(buy ABOVE on the cheaper venue + BELOW on the other). Places NOTHING."""
from datetime import datetime

from bot import polymarket as P, kalshi as K


def _dt(s):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def poly_levels():
    """[{threshold, yes_ask, no_ask, settle}] with EXECUTABLE asks from the book."""
    cdf = P.btc_threshold_cdf()
    ev = P.event_by_slug(cdf.get("slug")) if cdf.get("slug") else {}
    out = []
    import re
    for m in ev.get("markets", []):
        q = m.get("question") or ""
        mt = re.search(r"\$([\d,]+)", q)
        if not mt:
            continue
        thr = float(mt.group(1).replace(",", ""))
        toks = P._clob_token_ids(m)
        if not toks:
            continue
        yes_tok = toks[0]
        no_tok = toks[1] if len(toks) > 1 else None
        ya, _ = P.book_ask(yes_tok)
        na, _ = (P.book_ask(no_tok) if no_tok else (None, 0))
        out.append({"threshold": thr, "yes_ask": ya, "no_ask": na,
                    "settle": m.get("endDate") or ev.get("endDate")})
    out.sort(key=lambda x: x["threshold"])
    return cdf.get("title"), out


def kalshi_markets(series):
    rows = []
    for s in series:
        try:
            ms = K._markets(s)
        except Exception:  # noqa: BLE001
            ms = []
        for m in ms:
            st = K._strike(m)
            if st is None:
                continue
            rows.append({"ticker": m["ticker"], "strike": st,
                         "close": m.get("close_time"), "series": s})
    return rows


def main():
    title, plevels = poly_levels()
    if not plevels:
        print("No Polymarket threshold markets found.")
        return
    psettle = plevels[0]["settle"]
    pdt = _dt(psettle)
    print(f"POLY event: {title}")
    print(f"  settlement: {psettle}  ({len(plevels)} thresholds)")

    kmkts = kalshi_markets(["KXBTCD", "KXBTC"])
    print(f"KALSHI: {len(kmkts)} KXBTCD+KXBTC markets")
    # closest Kalshi settlement to Poly's
    closes = sorted({m["close"] for m in kmkts if m["close"]},
                    key=lambda c: abs(((_dt(c) - pdt).total_seconds()) if (_dt(c) and pdt) else 9e18))
    if closes:
        best_close = closes[0]
        gap_h = (abs((_dt(best_close) - pdt).total_seconds()) / 3600.0
                 if (_dt(best_close) and pdt) else None)
        print(f"  closest Kalshi settlement to Poly: {best_close}"
              f"  (gap {gap_h:.1f}h)" if gap_h is not None else "")
    else:
        best_close = None

    # restrict Kalshi to that closest settlement bucket
    kpool = [m for m in kmkts if m["close"] == best_close] if best_close else kmkts
    print(f"\n{'thr':>8} | {'poly above/below':<18} | {'kalshi strike':>13} "
          f"| {'kalshi above/below':<18} | {'lock cost':>9} | gross")
    print("-" * 92)
    any_edge = False
    for lv in plevels:
        thr = lv["threshold"]
        # nearest Kalshi strike in the matched-settlement pool
        cand = min(kpool, key=lambda m: abs(m["strike"] - thr)) if kpool else None
        if not cand:
            continue
        kya, _ = K.book_ask(cand["ticker"], "yes")  # above strike
        kna, _ = K.book_ask(cand["ticker"], "no")   # below strike
        pa, pb = lv["yes_ask"], lv["no_ask"]         # poly above / below
        sgap = cand["strike"] - thr
        # lock 'above $thr': buy ABOVE on cheaper venue + BELOW on the other
        lock = None
        if None not in (pa, pb, kya, kna):
            lock = min(pa + kna, kya + pb)
        pab = f"{pa}/{pb}" if None not in (pa, pb) else "—/—"
        kab = f"{kya}/{kna}" if None not in (kya, kna) else "—/—"
        gross = f"{(1-lock)*100:+.1f}c" if lock is not None else "—"
        if lock is not None and (1 - lock) > 0.003:
            any_edge = True
        print(f"{thr:>8.0f} | {pab:<18} | {cand['strike']:>13.2f} "
              f"| {kab:<18} | {('$%.3f'%lock) if lock else '-':>9} | {gross}"
              f"   dStrike ${sgap:+.0f}")
    print("-" * 92)
    print("NOTE: a real LOCK needs SAME strike AND SAME settlement instant. Δstrike"
          " and the settlement gap above are BASIS RISK — any nonzero value means"
          " it is NOT a true arb, just a correlated bet.")
    print("RESULT:", "some window shows >0.3c gross at real asks"
          if any_edge else "NO executable cross-venue edge at real asks.")


if __name__ == "__main__":
    main()
