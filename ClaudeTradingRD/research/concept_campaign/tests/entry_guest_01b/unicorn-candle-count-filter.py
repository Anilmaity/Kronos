"""unicorn-candle-count-filter (DTR, guest) — gate_test.

Claim: a unicorn that completes within ~10-12 candles trades better than one that
took longer (built over hours / with consolidation inside).

Baseline book: every 5m unicorn (breaker + overlapping same-direction FVG, see
_common.py), traded as a resting limit at the top (long) / bottom (short) of the
breaker/FVG overlap, stop at the breaker's far edge, 2R target.
Gate: formation count (bars from the breaker's first swing point L1 to the unicorn's
completion bar, inclusive) <= 12.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import unicorn_book  # noqa: E402

CID = "unicorn-candle-count-filter"
P = dict(tf="5min", W=48, fill_min=60, rr=2.0, cut=12, max_hold="50min")


def detect(m1):
    ev = unicorn_book(m1, tf=P["tf"], W=P["W"], fill_min=P["fill_min"], rr=P["rr"])
    ev["fast"] = (ev["count"] <= P["cut"]).astype(bool)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["fast"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "fast", mask_available_at="confirm_time", max_hold=P["max_hold"])
    op = {"rules": [
        "5m bars; 3-candle swing points (left=right=1)",
        "breaker (method spec 4.6, mirrored): swing low L1 -> swing high H1 -> lower low "
        "below L1 -> a 5m CLOSE above H1, all within W bars of L1; zone = bodies of the "
        "up-close candles L1..H1 (bearish mirror)",
        "unicorn = a same-direction 3-bar FVG from the leg out of the lower low (third "
        "candle <= break bar + 1) that overlaps the breaker zone; completion = later of "
        "break bar and FVG bar",
        "resting limit at the top (long) / bottom (short) of the breaker/FVG overlap from "
        "the completion close for 60 min; cancelled if 2R trades first; filled = first M1 "
        "touch, entered at the next M1 open with the planned stop distance",
        "stop = far edge of the breaker zone; target 2R; time exit 50 min",
        "gate: count = bars from L1 to completion (inclusive) <= 12"],
        "params": P}
    src = {
        "tf": "corpus: 07lOxv39LdY DTR C2U - hourly POI, 'drop to the 5-minute, look for a "
              "unicorn' (guest_methods_appendix DTR)",
        "W": "declared-before-run: base formation window 48 bars (4h) so the complement "
             "(13-48 bars, 'built over several hours') is populated",
        "fill_min": "declared-before-run: limit rests 12 entry-TF bars (60 min)",
        "rr": "corpus: 07lOxv39LdY low-hanging-fruit target 2-2.5R (worked example ~2.25R); "
              "G44VpidBD_U 80% at 2R",
        "cut": "corpus: 07lOxv39LdY 'roughly 10 to 12 candles or fewer' - upper bound 12",
        "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 50 min on 5m"}
    notes = ("Count start point is unstated in the corpus; declared as the breaker's first "
             "swing point L1 (the whole formation). Stop is 'not stated' for this concept; "
             "the unicorn-model / unicorn-entry-model breaker-edge stop is used. Limit fill is "
             "emulated (entry at the next M1 open after the touch). Swing 1/1 per "
             "swing-point-stop-hunt / unicorn-model ('a swing high has a lower high on each "
             "side').")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "ties",
              "exposure_bars", "ctrl_overlap"):
        print(k, res.get(k))
    print({k: res.get(k) for k in res if k.startswith("n_") or k in ("gated", "complement")})
