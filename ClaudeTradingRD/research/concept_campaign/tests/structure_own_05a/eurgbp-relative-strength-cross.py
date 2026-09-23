"""eurgbp-relative-strength-cross (TTrades own voice, contested) — batch structure_own_05a.

Mechanical asset selection: only when the dollar is NOT consolidating, read the cross of
the two candidate instruments (EURGBP for EU vs GU): bullish cross = numerator stronger.
Bullish dollar -> short the WEAKER instrument; bearish dollar -> long the STRONGER one;
"if you trade the wrong asset, you're going to be caught off sides" (nWHint4Yano).
The yaml's measurable: "R outcome of trading the cross-selected leg vs the other".

Transfer: the harness trades XAUUSD only and the campaign holds no GBP series, so the pair
is gold vs silver (the method's sanctioned gold correlate) and the cross is the XAU/XAG line
(the corpus: "the same logic is asserted to transfer" to other pairs). Gold trades that
the cross SELECTS are compared with gold trades taken when the cross says silver was the
right vehicle.

Baseline book (both readings): bare 1h CISD trades (see _fx.py) taken WITH the dollar -
dollar read = -(EURUSD's last completed daily closure), directional; trade direction
opposite the dollar (dollar consolidating -> no trade, the concept's gate).
reading a (primary: the cross): keep days where the XAU/XAG line's last completed daily
  closure is directional. Gate: cross agrees with the trade (long & gold stronger, short &
  gold weaker). Complement: cross selects silver.
reading b (the Shorts' variant: individual closures): keep days where exactly ONE of gold
  and silver made a daily closure through the prior day in the trade direction ('the
  weaker one closes more decisively through its opposing candles'). Gate: gold made it,
  silver did not. Complement: silver made it, gold did not.
claim '+': the selected instrument's trades beat the rejected instrument's.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402
import _fx  # noqa: E402

CID = "eurgbp-relative-strength-cross"


def detect(m1: pd.DataFrame, reading: str) -> pd.DataFrame:
    ev = _fx.book_with_reads(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "usd",
            "ratio", "gold", "xag", "read_avail", "selected"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    d = ev["direction"].to_numpy()
    ev = ev[(ev["usd"].to_numpy() != 0) & (d == -ev["usd"].to_numpy())].copy()
    d = ev["direction"].to_numpy()
    if reading == "a":
        r = ev["ratio"].to_numpy()
        ev = ev[r != 0].copy()
        ev["selected"] = ev["ratio"].to_numpy() == ev["direction"].to_numpy()
    else:
        gm = ev["gold"].to_numpy() == d
        xm = ev["xag"].to_numpy() == d
        ev = ev[gm ^ xm].copy()
        ev["selected"] = ev["gold"].to_numpy() == ev["direction"].to_numpy()
    return ev[cols].reset_index(drop=True)


def main():
    base_rules = [
        "baseline: bare 1h CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming "
        "bar's close, enter next M1 open, stop at the protected swing, 2R, 10h max hold",
        "reads = previous-candle closure (close above prior day's high = +1, below its low = -1, "
        "else 0) of the last completed 18:00-NY trading day before the CISD bar's day",
        "dollar = -(EURUSD read); keep trades opposite a directional dollar (consolidating dollar "
        "-> no trade)"]
    extra = {
        "a": ["cross = XAU/XAG hourly-close line's daily read; keep directional-cross days",
              "gate: cross == trade direction (long when gold is the stronger, short when gold is "
              "the weaker); complement: the cross selects silver"],
        "b": ["individual closures: keep trades where exactly one of gold / XAG_USD made a daily "
              "closure through the prior day in the trade direction",
              "gate: gold made it (gold is the selected instrument); complement: silver made it"]}
    src = {"baseline_tf": "phase3: rung-0 1h CISD book (calibrated)",
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config", "rr": "phase3: 2R (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "dollar_proxy": "declared-before-run: no DXY series; EURUSD is DXY's largest component (as dollar-gate-for-fx a)",
           "cross": "declared-before-run: transfer EU/GU -> XAU/XAG; silver is the method's sanctioned gold correlate (method_spec §2.6)",
           "strength_read": "corpus: nWHint4Yano / 25V-sGyMj_M 'Read EURGBP direction using a daily C2/C3 closure'; method_spec §2.3 closure class",
           "min_h1_per_day": "declared-before-run: stub-day guard"}
    for reading in ("a", "b"):
        fn = lambda m, r=reading: detect(m, r)   # noqa: E731
        ev = cl.cache_frame(f"eurgbp_{reading}_cisd1h", lambda r=reading: detect(cl.load_m1(), r))
        print("reading", reading, "book", len(ev), "gated", int(ev["selected"].sum()))
        probe = cl.probe_lookahead(fn, ev, lookback="30D")
        res = cl.gate_test(ev, "selected", mask_available_at="read_avail",
                           max_hold=_fx.MAX_HOLD, claim="+")
        print(summary(res))
        op = {"rules": base_rules + extra[reading],
              "params": {"baseline_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                         "max_wait": 3, "rr": 2.0, "max_hold": _fx.MAX_HOLD,
                         "dollar_proxy": "EURUSD inverted",
                         "cross": "XAU/XAG line" if reading == "a" else "gold vs XAG own closures",
                         "strength_read": "daily previous-candle closure class",
                         "min_h1_per_day": _fx.MIN_H1}}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="Transfer EURUSD/GBPUSD/EURGBP -> XAUUSD/XAGUSD/XAU-XAG: the "
                                  "campaign has no GBP series and the harness resolves XAUUSD only, "
                                  "so the comparison is gold trades the cross selects vs gold trades "
                                  "where silver was the selected vehicle. The hourly-CISD half of the "
                                  "cross read is not applied (the daily closure is the read).")
        print("wrote", p)


if __name__ == "__main__":
    main()
