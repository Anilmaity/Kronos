"""continuation-signature (TTrades own voice, contested) -> two readings, 4H forex grid.

The concept: after an expansion, the next price action is classified as consolidation,
retracement, or expansion-met-with-expansion. The first two (the 'small range' between two
'large ranges') are CONTINUATION signatures; the third is the reversal signature. The HTF
consolidation signature is an INSIDE BAR ('current candle takes neither the previous
candle's high nor its low').

Declared before the first run:
  * 4h bars on the forex grid (17/21/01/05/09/13 NY; session_window_fit / trap 8 -- recorded
    as grid4h). Expansion candle i = previous-candle continuation closure (high[i] > high[i-1]
    and close[i] > high[i-1]; mirrored).
  * Baseline book (every candle i+1 that follows an expansion candle i, whatever its shape):
    trade the expansion direction at the close of i+1; stop = the two-candle extreme against
    the trade (min(low[i], low[i+1]) for a long); target 2R; max hold 10 entry-TF bars
    (40h) in trading time.
  reading a: gate = candle i+1 is an INSIDE BAR of i (HTF consolidation signature). claim '+'.
  reading b: gate = candle i+1 CLOSES back inside candle i's range (low[i] <= close[i+1] <=
    high[i]) -- the 'small range' shape covering consolidation AND retracement, vs the
    complement (a further same-direction expansion close, or expansion met with expansion).
    claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, continuation_flags, show

CID = "continuation-signature"
GRID = "forex"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "inside_bar", "close_inside"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "4h", grid4h=GRID)
    if len(b) < 4:
        return pd.DataFrame(columns=COLS)
    up, dn = continuation_flags(b)
    H, L, C = (b[c].to_numpy(float) for c in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    i = np.flatnonzero((up | dn)[:-1])           # expansion candle i, with an i+1
    j = i + 1
    sgn = np.where(up[i], 1, -1)
    stop = np.where(sgn > 0, np.fmin(L[i], L[j]), np.fmax(H[i], H[j]))
    ev = pd.DataFrame({
        "decision_time": ct[j], "available_at": ct[j], "direction": sgn, "stop_px": stop,
        "rr": 2.0,
        "inside_bar": (H[j] <= H[i]) & (L[j] >= L[i]),
        "close_inside": (C[j] >= L[i]) & (C[j] <= H[i]),
    })
    return ev[COLS].reset_index(drop=True)


def main(readings):
    ev = cl.cache_frame(f"contsig_4h_{GRID}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "inside", int(ev["inside_bar"].sum()), "close_inside",
          int(ev["close_inside"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base = ["4h bars, forex grid (17/21/01/05/09/13 NY)",
            "expansion candle i = continuation closure vs i-1 (takes its high/low and closes beyond)",
            "baseline: every candle i+1 after an expansion candle -> trade i's direction at i+1's close; "
            "stop = two-candle extreme; 2R; max hold 40h of trading bars"]
    params = {"tf": "4h", "grid4h": GRID, "stop": "two-candle extreme", "rr": 2.0,
              "max_hold": "40h", "hold_basis": "bars"}
    src = {"tf": "corpus: concept timeframes htf 1D/4H; 4h chosen for sample size (fractal: true)",
           "grid4h": "session_window_fit: forex grid for gold (weakly); carried as a knob",
           "stop": "declared-before-run: beyond the extreme of the expansion + follow-up pair (protected-swing logic, method_spec §5.1)",
           "rr": "method_spec: §5.3 2R floor", "max_hold": "phase3: §1.13 10 entry-TF bars",
           "hold_basis": "declared-before-run: trading-time hold across the weekend (trap 7)"}
    for r in readings:
        col = {"a": "inside_bar", "b": "close_inside"}[r]
        res = cl.gate_test(ev, col, mask_available_at="decision_time", claim="+",
                           max_hold="40h", hold_basis="bars")
        show(res)
        rule = {"a": "gate (reading a): candle i+1 is an inside bar of i -- HTF consolidation signature",
                "b": "gate (reading b): candle i+1 closes back inside i's range -- consolidation or retracement "
                     "(small range) vs further expansion or expansion met with expansion"}[r]
        print(cl.write_result(CID, r, res, operationalization={"rules": base + [rule, "claim '+'"],
                                                              "params": dict(params, gate=col)},
                              params_source=dict(src, gate="corpus: VD4xb9VfMHA / 4Gm8p6O7Ebs large range, small range, large range; "
                                                           "t_talks_02 'HTF consolidation signature: an inside bar'"),
                              script=__file__, probe=probe,
                              notes=f"Reading {r}: {col} as the continuation signature after a 4h expansion candle."))


if __name__ == "__main__":
    main(sys.argv[1:] or ["a", "b"])
