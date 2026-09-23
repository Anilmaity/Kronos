"""single-cisd-at-swing-point — trade_test.

Concept: one CISD per fractal sequence, at the swing point inside the candle 2, is enough;
the C3 continuation runs off that single confirmation with no CISD of its own.

Book: 4h (forex grid) C2 closure (spec §3.2) carrying a same-direction 15m CISD (phase-3 rule)
whose extreme and confirm bar lie inside the C2 candle. The C3 is traded off that confirmation
alone: decide at the C2 close (= C3 open), enter next M1 open, stop = C2's extreme (the swing the
CISD confirmed), target 2R, exit at the C3 candle's close (4h). No CISD inside C3 is required.
claim '+': the C3 book beats a matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, c2_book, PHASE3_SRC

CID = "single-cisd-at-swing-point"
HOLD = "4h"
RR = 2.0


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    bk = c2_book(m1)
    if bk.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(bk["c2_close"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": bk["sgn"].to_numpy(),
                        "stop_px": np.where(bk["sgn"] > 0, bk["l"], bk["h"]).astype(float), "rr": RR})
    return out[cols]


OP_BASE = ["4h bars on the forex grid; C2 = sweep of the prior candle's extreme with a close back "
           "inside it (bullish: low<prior low & close>prior low), spec §3.2",
           "C2 must carry a same-direction 15m CISD (series_open, 2/2 swing, max_wait 3) whose extreme "
           "and confirming bar are inside the C2 candle; two-sided C2s with both CISDs dropped",
           "trade C3: decide at the C2 close, enter next M1 open, stop at C2's extreme, 2R, exit at C3 close (4h)"]
PARAMS = {"htf": "4h", "grid4h": "forex", "ltf": "15min", "level_rule": "series_open", "swing": "2/2",
          "max_wait": 3, "rr": RR, "max_hold": HOLD, "c2_close_ref": "prior candle extreme"}
SRC = {"htf": "corpus: U4j-fZD-FJk timeframes htf 1D/4H/1H ltf 15m/5m; method_spec §1.3 4H/15m favourite pairing",
       "grid4h": PHASE3_SRC, "ltf": "corpus: single-cisd-at-swing-point.yaml ltf 15m",
       "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
       "rr": "phase3: §1.12 2R fixed",
       "max_hold": "method_spec: §5.5 time-based-exit-htf-close — hold to the close of the HTF candle the trade runs inside",
       "c2_close_ref": "method_spec: §3.2 C2 test (close back inside candle 1's high/low)"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h15m_c3", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.trade_test(ev, max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "avg_R", "win_rate", "exposure_bars", "ctrl_overlap", "ties")})
    p = cl.write_result(CID, None, res, operationalization={"rules": OP_BASE, "params": PARAMS},
                        params_source=SRC, script=__file__, probe=probe,
                        notes="tests that the single C2 CISD suffices to trade C3 (vs random); the "
                              "yaml's own-CISD-vs-none comparison needs an intra-C3 entry and is not run")
    print(p)
