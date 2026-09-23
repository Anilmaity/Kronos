"""breaker-wick-vs-body-invalidation (DayTradingRauf, guest) — gate_test.

Claim (qFtfD09Vv3E): take a bullish breaker (low, high, lower low, with the up-close
candle(s) between the low and the high) and look at what price does to the LOW of that
breaker: if bodies CLOSE below it he does not trust the breaker; if only WICKS go below
it, the breaker holds and returns into it 'trade much better'. Mirror for bearish.

Baseline book: every 5m breaker (swing low L1 -> swing high H1 -> lower low below L1 ->
a close back above H1, i.e. the breaker is confirmed), traded on the return into it:
limit at the breaker zone's near edge (top of the up-close bodies L1..H1), stop at the
zone's far edge, 2R, resting 60 min from the confirming close.
Gate: wick-only = no 5m candle CLOSED below L1 while price was under it (between the
sweep and the close back above H1).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import unicorn_book  # noqa: E402

CID = "breaker-wick-vs-body-invalidation"
P = dict(tf="5min", W=48, fill_min=60, rr=2.0, max_hold="50min", entry="breaker near edge",
         stop="breaker far edge", body="5m close beyond L1 during the lower-low leg")


def detect(m1):
    ev = unicorn_book(m1, tf=P["tf"], W=P["W"], fill_min=P["fill_min"], rr=P["rr"],
                      want_fvg=False, entry_rule="zone_top", stop_rule="zone_far")
    ev["wick_only"] = (~ev["body_below"].astype(bool)).astype(bool)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["wick_only"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "wick_only", mask_available_at="confirm_time",
                       max_hold=P["max_hold"])
    op = {"rules": [
        "5m bars, 3-candle swing points",
        "bullish breaker: swing low L1 -> swing high H1 (highest since L1) -> a lower low "
        "below L1 -> a 5m close above H1, within 48 bars of L1; zone = bodies of the "
        "up-close candles L1..H1 (bearish mirror)",
        "return into the breaker: limit at the zone's near edge from the confirming close for "
        "60 min, cancelled if 2R trades first; entered at the next M1 open after the touch "
        "with the planned stop distance; stop at the zone's far edge; 2R; 50 min time exit",
        "gate wick_only: no 5m close below L1 (above L1 for bearish) between the sweep and "
        "the confirming close; complement = at least one body close beyond L1"],
        "params": P}
    src = {
        "tf": "declared-before-run: he demonstrates on 1m inside an MMXM; 5m (in the concept's "
              "ltf list) used for compute; bodies counted on the execution TF",
        "W": "declared-before-run: breaker formation window 48 bars, as the batch's base book",
        "fill_min": "declared-before-run: limit rests 12 entry-TF bars (60 min)",
        "rr": "declared-before-run: targets 'not stated'; 2R as the batch's other breaker books",
        "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 50 min on 5m",
        "entry": "corpus: qFtfD09Vv3E 'when price trades back into such a breaker'; near edge "
                 "= first touch of the breaker",
        "stop": "declared-before-run: stop 'not stated'; breaker far edge (unicorn-entry-model "
                "G44VpidBD_U 'stop at ... the breaker itself')",
        "body": "corpus: qFtfD09Vv3E 'bodies that close below this low instead of wicks'"}
    notes = ("Reading: 'the low of that breaker' = L1, the breaker's defining low that the "
             "lower low takes; body-close vs wick-only is judged over the lower-low leg, "
             "before the breaker is confirmed. The breaker is his four-point object (method "
             "spec 4.6), not the mainstream failed order block.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "ties",
              "halves", "complement"):
        print(k, res.get(k))
