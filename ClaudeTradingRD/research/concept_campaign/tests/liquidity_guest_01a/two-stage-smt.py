"""two-stage-smt (GxTradez, guest) — gate_test on a 1H gold/silver SMT book.

Claim: one stage of SMT immediately followed and confirmed by a second (a PSP or an
SMT between candle 2 and candle 3) is the higher-probability reversal; a single stage
is only a potential reversal.

Baseline (stated, see _smt_common.smt_next_bar_book): every 1H gold/silver SMT
(stage 1 = SMT at a swing level; fractal 2/2, lookback 20), decided at the close of
the bar after the SMT bar, gold traded in the reversal direction, stop at gold's
extreme since the swing, 2R, 10h hold.
Gate 'stage2' (known at that close): on the very next bar a PSP (gold and silver
close opposite colours) OR an SMT between candle 2 and 3 (exactly one asset trades
beyond its own SMT-bar extreme). 'Immediately' = the next bar (declared).
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
    print(len(ev), ev.stage2.mean(), ev.psp.mean(), ev.smt23.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "stage2", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "exposure_bars", "ties")})
    p = cl.write_result(
        "two-stage-smt", None, res,
        operationalization={"rules": [
            "gold 1H (certified M1) and OANDA XAG_USD H1, inner-joined on hour labels",
            "stage 1 = SMT at bar j at a confirmed fractal(2/2) swing level (either asset's swing, levels at the same bar), lookback 20",
            "decision at close of bar j+1; trade gold in the reversal direction; stop = gold extreme p..j+1; target 2R; max_hold 10h",
            "gate stage2 on bar j+1: PSP (opposite-colour closes) OR candle-2/candle-3 SMT (exactly one asset exceeds its own bar-j extreme on the SMT side)"],
            "params": {"tf": "1h", "fractal": [2, 2], "smt_lookback": 20,
                       "stage2_window_bars": 1, "rr": RR, "max_hold": MAX_HOLD}},
        params_source={
            "tf": "corpus: 3eVxTV_7L2U timeframes htf 4H/1H; 1H is the finest the correlate supports",
            "fractal": "phase3: swing_points left=2 right=2",
            "smt_lookback": "phase3: smt_events lookback=20",
            "stage2_window_bars": "declared-before-run: 'immediately following' read as the next bar",
            "rr": "phase3: bare-CISD book target 2R (corpus worked trade 2.8R, not a rule)",
            "max_hold": "phase3: 1h book max_hold 10h (concept_lab README example)"},
        script=__file__, probe=probe,
        notes=f"gate firing rate {ev.stage2.mean():.3f} (psp {ev.psp.mean():.3f}, smt23 {ev.smt23.mean():.3f}) "
              f"of {len(ev)} SMT events. Silver stands in for the triad (only correlate with full history).")
    print(p)
