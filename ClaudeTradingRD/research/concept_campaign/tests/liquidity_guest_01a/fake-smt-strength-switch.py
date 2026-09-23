"""fake-smt-strength-switch (GxTradez, guest) — gate_test on a 1H gold/silver SMT book.

Claim: an SMT is FAKE when the asset that swept the level fails to reverse (and the
lagging asset then catches up and takes the level too); a genuine SMT shows the
sweeper reversing. Trading implication: SMT reversals where the sweeper reversed
beat those where it did not.

Baseline (stated, see _smt_common.smt_next_bar_book): every 1H gold/silver SMT
(fractal 2/2, lookback 20), decided at the close of the bar after the SMT bar,
gold traded in the reversal direction, stop at gold's extreme since the swing,
2R, 10h hold.
Gate 'genuine' (known at that close): the sweeper closed back inside its level on
the SMT bar or the next one AND the held asset still has not taken its own level.
The complement is the fake arm (sweeper still beyond, or the lagging asset caught
up). The visual strength-switch cues (candle colour, run depth, FVG size) have no
ranking or threshold and are not separately operationalised.
claim '+'. All params declared before the first run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _smt_common as sc  # noqa: E402
import concept_lab as cl  # noqa: E402

RR, MAX_HOLD = 2.0, "10h"


def detect(m1):
    return sc.smt_next_bar_book(m1, "1h", RR)


if __name__ == "__main__":
    ev = cl.cache_frame("smt_next_bar_book_1h_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev.genuine.mean(), ev.stage2.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "genuine", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "exposure_bars", "ties")})
    p = cl.write_result(
        "fake-smt-strength-switch", None, res,
        operationalization={"rules": [
            "gold 1H (certified M1) and OANDA XAG_USD H1, inner-joined on hour labels",
            "SMT at bar j: confirmed fractal(2/2) swing at p in either asset, levels = each asset's own extreme at p; first asset beyond its level within 20 bars while the other is not",
            "decision at close of bar j+1; trade gold in the reversal direction; stop = gold extreme p..j+1; target 2R; max_hold 10h",
            "gate genuine: sweeping asset closed back inside its level on bar j or j+1 AND held asset has not exceeded its own level through j+1; complement = fake SMT"],
            "params": {"tf": "1h", "fractal": [2, 2], "smt_lookback": 20,
                       "reversal_check_bars": 2, "rr": RR, "max_hold": MAX_HOLD}},
        params_source={
            "tf": "corpus: J_EeS2_2CAM timeframes ltf 1H/15m/5m; 1H is the finest the correlate supports",
            "fractal": "phase3: swing_points left=2 right=2",
            "smt_lookback": "phase3: smt_events lookback=20",
            "reversal_check_bars": "declared-before-run: the SMT bar and the one after it",
            "rr": "phase3: bare-CISD book target 2R",
            "max_hold": "phase3: 1h book max_hold 10h (concept_lab README example)"},
        script=__file__, probe=probe,
        notes=f"gate firing rate {ev.genuine.mean():.3f} of {len(ev)} SMT events; gold/silver pair "
              "(the concept names gold/silver among its correlated sets).")
    print(p)
