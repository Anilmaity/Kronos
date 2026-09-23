"""range-edge-trading — gate test: inside a consolidation, edge entries back into the range
beat every other entry in the range.

Consolidation (method_spec §2.7 signature 'price staying inside one prior candle's range;
an inside bar'): the previous completed daily candle is an INSIDE bar of the one before it
(its mother). The range = the mother candle's high/low. Scope = 15m CISD events on the day
after the inside day whose confirming close is inside that range.

Baseline book (stated): phase-3 rung-0 15m CISD — series_open, 2/2 swing, max_wait 3, next
M1 open entry, stop = protected swing, 2R, 150min — restricted to that scope.
Gate: the event is at an EDGE directed back INTO the range: long with the confirming close
in the bottom 25% of the range, or short in the top 25% (declared-before-run: 'edge' is
unbounded in the source). Complement: mid-range entries and edge entries pointing out of
the range (the breakout trades he refuses).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, in_progress  # noqa: E402

CID = "range-edge-trading"
EDGE_FRAC = 0.25


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "edge_inward"]
    b15 = cl.build_bars(m1, "15min")
    bd = cl.build_bars(m1, "1D")
    ev = cisd(b15, max_wait=3)
    if ev.empty or len(bd) < 3:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    pday = in_progress(bd, t)
    pc = np.clip(pday, 2, None)
    H, L = bd["high"].to_numpy(), bd["low"].to_numpy()
    inside = (H[pc - 1] <= H[pc - 2]) & (L[pc - 1] >= L[pc - 2])
    rh, rl = H[pc - 2], L[pc - 2]
    ok = (pday >= 2) & inside & (px > rl) & (px < rh) & (rh > rl)
    pos = (px - rl) / np.where(rh > rl, rh - rl, np.nan)
    edge_in = np.where(d > 0, pos <= EDGE_FRAC, pos >= 1 - EDGE_FRAC)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ev["stop_px"].to_numpy(), "rr": 2.0,
                        "edge_inward": edge_in.astype(bool)})
    return out[ok].reset_index(drop=True)


def main():
    ev = cl.cache_frame("range_edge_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["edge_inward"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "edge_inward", mask_available_at="decision_time", max_hold="150min")
    print({k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p",
                                    "verdict", "verdict_detail", "gate_firing_rate")})
    op = {"rules": [
        "consolidation: the previous completed daily candle (18:00 NY day) is an inside bar of "
        "the day before it; range = that mother candle's high/low",
        "scope: 15m CISD (series_open, 2/2, max_wait 3) events on the next day whose confirming "
        "close is strictly inside the range; enter next M1 open; stop = protected swing; 2R; "
        "150min",
        "gate: long with confirming close in the bottom 25% of the range, or short in the top 25% "
        "(edge, directed back into the range); complement = all other in-range events"],
        "params": {"consolidation": "inside day (mother-candle range)", "edge_frac": EDGE_FRAC,
                   "baseline_tf": "15min", "level_rule": "series_open", "max_wait": 3,
                   "rr": 2.0, "max_hold": "150min", "day_open_hour": 18}}
    src = {"consolidation": "method_spec: §2.7 consolidation signature 'price staying inside one "
                            "prior candle's range; an inside bar'",
           "edge_frac": "declared-before-run: outer quarter of the range = edge (source gives no "
                        "boundary; EQ is the target so the edge must sit well away from it)",
           "baseline_tf": "phase3: 15m rung-0 book (concept timeframes ltf include 15m)",
           "level_rule": "method_spec: §4.2 first-candle-open default",
           "max_wait": "phase3: locked config max_wait=3",
           "rr": "method_spec: §5.3 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "day_open_hour": "method_spec: §1.4 18:00 canon"}
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="gate_test, claim '+': inward edge entries vs every "
                                         "other entry inside a consolidation range."))


if __name__ == "__main__":
    main()
