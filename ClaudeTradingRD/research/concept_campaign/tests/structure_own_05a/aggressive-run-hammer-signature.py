"""aggressive-run-hammer-signature (TTrades own voice) — batch structure_own_05a.

"[an aggressive move below the range low and an aggressive move back in] will create the
wick of a hammer candle on the [higher] time frame" (yq4Z7q4E6nU); at a range high the
mirror prints a 'shooter'. The equivalence itself is definitional (a run and return inside
one HTF candle IS that candle's wick), so the testable content is the setup it is used to
recognise: a hammer at a range low (shooter at a range high) marks a completed
run-and-return, i.e. a reversal away from the swept edge ("continuation rate after a
hammer at a range low" - yaml measurable).

trade_test on the corpus's shown pair (1m sequence -> 5m candle):
  range edge : the lowest low (highest high) of the 20 prior 5m candles
  hammer     : 5m candle trades below the range low, CLOSES back above it (a wick through,
               not a close beyond - the stated invalidation), and its opposing run
               (open -> low, one-sided) exceeds its body (large wick / reversal candle,
               threshold_fits cut 1.0); mirror 'shooter' at the range high
  trade      : decide at the 5m close, enter next M1 open toward the range (long after a
               hammer), stop = the wick extreme, 2R target, exit after 10 5m bars (50 min)
claim '+' vs the matched random-entry control.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "aggressive-run-hammer-signature"
TF = "5min"
LOOKBACK = 20
WICK_CUT = 1.0
RR = 2.0
MAX_HOLD = "50min"
TOD_TOL = 30


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) <= LOOKBACK + 1:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    lo_prev = pd.Series(l).rolling(LOOKBACK).min().shift(1).to_numpy()
    hi_prev = pd.Series(h).rolling(LOOKBACK).max().shift(1).to_numpy()
    body = np.abs(c - o)
    hammer = (l < lo_prev) & (c > lo_prev) & ((o - l) > WICK_CUT * body)
    shooter = (h > hi_prev) & (c < hi_prev) & ((h - o) > WICK_CUT * body)
    both = hammer & shooter                       # outside bar that did both: no read
    hammer &= ~both
    shooter &= ~both
    ct = pd.DatetimeIndex(b["close_time"])
    ih, is_ = np.flatnonzero(hammer), np.flatnonzero(shooter)
    out = pd.concat([
        pd.DataFrame({"decision_time": ct[ih], "direction": 1, "stop_px": l[ih]}),
        pd.DataFrame({"decision_time": ct[is_], "direction": -1, "stop_px": h[is_]}),
    ]).sort_values("decision_time").reset_index(drop=True)
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out[cols]


def main():
    ev = cl.cache_frame(f"hammer_{TF}_lb{LOOKBACK}_w{WICK_CUT}", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(summary(res))
    op = {"rules": [
        "5m candle trades below the lowest low of the 20 prior 5m candles and closes back above "
        "it, with opposing run (open - low) > body -> hammer -> long; mirror at the highest high "
        "-> shooter -> short; a candle doing both is dropped",
        "decide at the 5m close, enter next M1 open, stop = the wick extreme, 2R, exit after 50 min"],
        "params": {"tf": TF, "range_lookback": LOOKBACK, "wick_cut": WICK_CUT, "rr": RR,
                   "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL}}
    src = {"tf": "corpus: yq4Z7q4E6nU yaml timeframes htf 5m / ltf 1m (the one shown pair)",
           "range_lookback": "phase3: lookback 20 knob (POI / short-term range)",
           "wick_cut": "threshold_fits: large wick / reversal candle = opposing_run/body > 1.0 (grade A)",
           "rr": "phase3: 2R", "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 (not a timing concept)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The LTF->HTF equivalence is true by construction; the test is of the "
                              "setup it identifies. 'Aggressive' on both legs is carried by the "
                              "single-candle wick>body shape (no separate magnitude gate); 'shooter' "
                              "read as the bearish mirror (yaml ambiguity).")
    print("wrote", p)


if __name__ == "__main__":
    main()
