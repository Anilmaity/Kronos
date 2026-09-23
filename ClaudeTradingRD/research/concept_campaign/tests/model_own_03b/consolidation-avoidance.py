"""consolidation-avoidance — consolidation is a state to avoid; setups taken while the
higher timeframe is consolidating should be worse. Claim '-' (gated = in consolidation).

Baseline book: phase-3 bare 15m CISD (series_open, 2/2, max_wait 3, protected-swing
stop, 2R, 150 min).
Reading a (daily state): the last completed daily candle is an inside day (high <=
  prior high and low >= prior low) — a range with both boundaries marked and no
  displacement out of it.
Reading b (4H state, forex grid): the last three completed 4H candles all CLOSED
  inside the range of the 4H candle before them (no closure out of the range).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "consolidation-avoidance"
HOLD = "150min"


def _base(m1):
    b = cl.build_bars(m1, "15min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    return out


def detect_a(m1):
    out = _base(m1)
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= 600].copy()
    d["inside"] = ((d["high"] <= d["high"].shift(1)) & (d["low"] >= d["low"].shift(1))).astype(float)
    d.loc[d.index[0], "inside"] = np.nan
    y = cl.asof(d, pd.DatetimeIndex(out["decision_time"]))
    ok = ~np.isnan(y["inside"].to_numpy(dtype=float))
    out["in_cons"] = y["inside"].to_numpy(dtype=float) == 1.0
    return out[ok].reset_index(drop=True)


def detect_b(m1):
    out = _base(m1)
    h = cl.build_bars(m1, "4h", grid4h="forex")
    ref_h, ref_l = h["high"].shift(3), h["low"].shift(3)
    ins = pd.Series(True, index=h.index)
    for k in range(3):
        c = h["close"].shift(k)
        ins &= (c <= ref_h) & (c >= ref_l)
    h["cons"] = ins.astype(float)
    h.loc[h.index[:3], "cons"] = np.nan
    y = cl.asof(h, pd.DatetimeIndex(out["decision_time"]))
    v = y["cons"].to_numpy(dtype=float)
    ok = ~np.isnan(v)
    out["in_cons"] = v == 1.0
    return out[ok].reset_index(drop=True)


BASE_RULES = ["baseline: 15m bare CISD (series_open, 2/2 swing, max_wait 3); decide at the confirming bar close; enter next M1 open; stop at the protected swing; 2R; exit after 150 min",
              "claim '-': trades taken while the higher timeframe is in consolidation (gated) are worse than the rest"]
BASE_PARAMS = {"tf": "15min", "cisd": "series_open 2/2 max_wait 3", "rr": 2.0, "max_hold": HOLD}
BASE_SRC = {"tf": "corpus: concept timeframes.ltf 15m; phase3 15m stack",
            "cisd": "phase3: locked bare-CISD config", "rr": "phase3: locked 2R",
            "max_hold": "phase3: 10 entry-TF bars"}


def main():
    ev = cl.cache_frame("cons_a_v1", lambda: detect_a(cl.load_m1()))
    print("a", len(ev), ev["in_cons"].mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.gate_test(ev, "in_cons", mask_available_at="decision_time", max_hold=HOLD, claim="-")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    print(cl.write_result(CID, "a", res, operationalization={
        "rules": BASE_RULES + ["gate: the last completed daily candle (18:00 NY roll, stubs <600 M1 skipped) is an inside day: high <= prior high and low >= prior low (read via asof at decision)"],
        "params": {**BASE_PARAMS, "consolidation": "daily inside day"}},
        params_source={**BASE_SRC, "consolidation": "declared-before-run: no quantitative range definition in corpus; daily inside bar = range with both boundaries and no displacement (method_spec §2.8 no-bias states)"},
        script=__file__, probe=probe))

    evb = cl.cache_frame("cons_b_v1", lambda: detect_b(cl.load_m1()))
    print("b", len(evb), evb["in_cons"].mean())
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="10D")
    resb = cl.gate_test(evb, "in_cons", mask_available_at="decision_time", max_hold=HOLD, claim="-")
    print({k: resb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    print(cl.write_result(CID, "b", resb, operationalization={
        "rules": BASE_RULES + ["gate: the last three completed 4H candles (forex grid 17/21/01/05/09/13 NY) all closed within the high-low range of the 4H candle before them (no closure out of the range)"],
        "params": {**BASE_PARAMS, "consolidation": "3 x 4H closes inside the prior 4H range", "grid4h": "forex"}},
        params_source={**BASE_SRC, "consolidation": "declared-before-run: 'traded between them without displacing' -> no 4H close outside the reference 4H candle's range for 3 candles",
                       "grid4h": "session_window_fit: forex grid for gold (weakly settled; knob)"},
        script=__file__, probe=probe_b))


if __name__ == "__main__":
    main()
