"""currency-pairing-opposition (mixed voice, contested) — batch structure_own_05a.

Claim: expansion comes from pairing OPPOSITE directions - numerator up and denominator
down is the strong trend; pairing a directional currency with a CONSOLIDATING one (or two
legs moving the same way) gives a weak trend or a consolidation, so reject it.

reading a (the host's dollar-first version, applied to the one pair the campaign trades):
  XAUUSD is itself a fraction - numerator gold, denominator the dollar. Dollar first:
  the book is the ordinary model's trades taken WITH the dollar read (trade direction =
  opposite the dollar's last completed daily closure; dollar consolidating -> no trade).
  Gate: the numerator leg (gold's own strength, XAU/EUR line) closed directionally the
  same way as the trade on the last completed day = 'strongest against weakest'.
  Complement: the numerator leg consolidated (inside) or moved with the dollar (same-way
  legs -> consolidation) - the pairings the rule rejects.
  Baseline book: bare 1h CISD (see _fx.py), 2R, 10h. claim '+': gated beats complement.
reading b (the guest's currency-futures version): UNTESTABLE - see REASON_B.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402
import _fx  # noqa: E402

CID = "currency-pairing-opposition"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = _fx.book_with_reads(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "usd",
            "goldleg", "read_avail", "opposed"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    d = ev["direction"].to_numpy()
    ev = ev[(ev["usd"].to_numpy() != 0) & (d == -ev["usd"].to_numpy())].copy()
    ev["opposed"] = ev["goldleg"].to_numpy() == ev["direction"].to_numpy()
    return ev[cols].reset_index(drop=True)


REASON_B = ("Reading b (Rauf's method): chart the individual currency FUTURES (6E, 6B, 6A, 6C, "
            "6N...), grade each as strong/weak/consolidating by eye, and trade the FX pair or cross "
            "made of the weakest against the strongest (e.g. EURUSD not GBPUSD because 6B is in "
            "deeper discount). The outcome being claimed is the realised trend/range of the "
            "SELECTED FX pair versus the rejected ones. The campaign holds no currency futures and "
            "no FX crosses (only EURUSD H1 and XAG H1 besides XAUUSD M1), and the harness resolves "
            "trades on XAUUSD only, so neither the ranking nor the selected pairs' outcomes can be "
            "formed; the grading itself is 'eyeballed off the futures chart' with no measure given. "
            "The one piece that transfers to gold (numerator vs denominator opposition) is reading a.")


def run_a():
    ev = cl.cache_frame("cpo_a_cisd1h_usd_goldleg", lambda: detect(cl.load_m1()))
    print("book", len(ev), "gated", int(ev["opposed"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "opposed", mask_available_at="read_avail", max_hold=_fx.MAX_HOLD,
                       claim="+")
    print(summary(res))
    op = {"rules": [
        "baseline: bare 1h CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming "
        "bar's close, enter next M1 open, stop at the protected swing, 2R, 10h max hold",
        "reads = previous-candle closure (close above prior day's high = +1, below its low = -1, "
        "else 0) of the last completed 18:00-NY trading day before the CISD bar's day",
        "dollar = -(EURUSD read) (EURUSD H1 -> daily, 17:00-NY hour dropped); book keeps only "
        "trades opposite a directional dollar (dollar consolidating -> no trade)",
        "gate (strong vs weak): gold leg = XAU/EUR hourly-close line's daily read equals the trade "
        "direction; complement: gold leg inside (consolidating) or with the dollar"],
        "params": {"baseline_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": _fx.MAX_HOLD,
                   "dollar_proxy": "EURUSD inverted", "gold_leg": "XAU/EUR line",
                   "strength_read": "daily previous-candle closure class",
                   "min_h1_per_day": _fx.MIN_H1}}
    src = {"baseline_tf": "phase3: rung-0 1h CISD book (calibrated)",
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config", "rr": "phase3: 2R (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "dollar_proxy": "declared-before-run: no DXY series; EURUSD is DXY's largest component (as dollar-gate-for-fx a)",
           "gold_leg": "declared-before-run: gold's strength with the dollar removed = XAUUSD / EURUSD",
           "strength_read": "corpus: HrjYoxAUb3s ranking 'done off daily candle appearance'; method_spec §2.3 continuation closure = directional, inside = consolidating",
           "min_h1_per_day": "declared-before-run: stub-day guard"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Transfer of the fraction rule to XAUUSD (numerator gold, denominator "
                              "USD); the gold leg is proxied by XAU/EUR, i.e. gold against the dollar's "
                              "largest counterpart. Correlates: m3_scalper eur_h1_full / xag_h1_full, "
                              "consumed only through completed days before the decision.")
    print("wrote", p)


if __name__ == "__main__":
    what = sys.argv[1:] or ["a", "b"]
    if "a" in what:
        run_a()
    if "b" in what:
        print(cl.write_untestable(CID, REASON_B, reading="b", script=__file__))
