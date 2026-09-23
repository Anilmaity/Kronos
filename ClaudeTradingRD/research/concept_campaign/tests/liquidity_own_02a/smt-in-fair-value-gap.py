"""smt-in-fair-value-gap — one correlated asset trades into its FVG, the other does not.

Corpus (q1NmxUTm4n4, "we have an SMT within a fair value gap"): after an aggressive move
both assets leave a gap; one trades back INTO its gap, the correlated one does not; read it
like an SMT at a high/low — a possible reversal away from the gap (S&P enters its bearish
gap, NASDAQ does not -> move down).

Operationalised on gold vs XAG_USD, 1h (only correlate resolution held):
  * a paired gap = both assets print a same-direction 3-bar FVG on the SAME bar i
    (detectors.primitives.fair_value_gaps rule: bearish high[i] < low[i-2]);
  * scan j = i+1 .. i+20: "trades into the gap" = touches its near edge (bearish: high_j >=
    the gap's lower edge; bullish: low_j <= the gap's upper edge);
  * first bar where exactly ONE asset enters -> SMT-in-gap at j; both on the same bar ->
    no divergence, stop scanning;
  * bearish gaps (above price) -> short gold; bullish gaps (below) -> long gold.
Trade: decide at gold bar j close, next M1 open, stop 1 x ATR14(1h), 1R, 10h — the same
symmetric direction book as smt-divergence reading a, so the two SMT locations compare.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

CID = "smt-in-fair-value-gap"
LOOKBACK = 20          # phase3: the smt_events 20-bar lookback, reused for the gap scan
STOP_ATR = 1.0         # declared-before-run
RR = 1.0               # declared-before-run
MAX_HOLD = "10h"       # phase3
TOD_TOL = 30           # declared-before-run (README trap 9)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr", "entered_by"]
    g, x = c.pair_h1(m1, "gold_last")
    if len(g) < 40 or len(x) < 40:
        return pd.DataFrame(columns=cols)
    a_atr = c.atr(g)
    idx = g.index.intersection(x.index)
    A, B = g.loc[idx], x.loc[idx]
    ah, al = A["high"].to_numpy(), A["low"].to_numpy()
    bh, bl = B["high"].to_numpy(), B["low"].to_numpy()
    n = len(idx)
    rows = []
    for i in range(2, n):
        bear = ah[i] < al[i - 2] and bh[i] < bl[i - 2]
        bull = al[i] > ah[i - 2] and bl[i] > bh[i - 2]
        for is_bear in ((True,) if bear else ()) + ((False,) if bull else ()):
            ea, eb = (ah[i], bh[i]) if is_bear else (al[i], bl[i])   # near edges
            for j in range(i + 1, min(n, i + 1 + LOOKBACK)):
                ina = ah[j] >= ea if is_bear else al[j] <= ea
                inb = bh[j] >= eb if is_bear else bl[j] <= eb
                if ina and inb:
                    break
                if ina or inb:
                    rows.append((idx[j], -1 if is_bear else 1, "gold" if ina else "xag"))
                    break
    if not rows:
        return pd.DataFrame(columns=cols)
    f = pd.DataFrame(rows, columns=["time", "direction", "entered_by"])
    f = f.drop_duplicates(subset=["time", "direction"], keep="first")
    t = pd.DatetimeIndex(f["time"])
    at = a_atr.loc[t].to_numpy(float)
    out = pd.DataFrame({"decision_time": pd.DatetimeIndex(g.loc[t, "close_time"]),
                        "available_at": pd.DatetimeIndex(g.loc[t, "close_time"]),
                        "direction": f["direction"].to_numpy(int),
                        "stop_dist": STOP_ATR * at, "rr": RR,
                        "entered_by": f["entered_by"].to_numpy()})
    out = out[np.isfinite(out["stop_dist"]) & (out["stop_dist"] > 0)]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"{CID}_h1_lb20", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(res["n"], res["diff"], res["ci_lo"], res["ci_hi"], res["verdict"],
          res["verdict_detail"], res.get("exposure_bars"), res.get("ties"))
    print(ev["entered_by"].value_counts().to_dict(), ev["direction"].value_counts().to_dict())
    op = {"rules": ["gold 1h vs XAG_USD 1h on shared bar starts",
                    "paired gap: both assets print a same-direction 3-bar FVG on the same bar i",
                    "within 20 bars, the first bar where exactly one asset touches its gap's "
                    "near edge is the SMT-in-gap; both on one bar = no divergence",
                    "bearish gaps -> short gold, bullish gaps -> long gold",
                    "decide at gold bar close, next M1 open, stop 1 x ATR14(1h), 1R, 10h"],
          "params": {"tf": "1h", "correlate": "XAG_USD H1", "lookback": LOOKBACK,
                     "enter_rule": "near edge", "stop_atr": STOP_ATR, "atr_n": 14,
                     "rr": RR, "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL}}
    src = {"tf": "declared-before-run: SMT is fractal; silver held only at H1",
           "correlate": "corpus: silver allowed as gold's correlate; phase3 load_correlate",
           "lookback": "phase3: detectors.bias.smt_events 20-bar lookback",
           "enter_rule": "declared-before-run: 'trades into the gap' is unspecified (near "
                         "edge / CE / fill); near edge = first entry",
           "stop_atr": "declared-before-run: symmetric direction test",
           "atr_n": "declared-before-run",
           "rr": "declared-before-run: symmetric 1R barrier",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9"}
    notes = ("Gaps are paired by printing on the same bar in both assets; the corpus does "
             "not require identical size or candle position, so this is the strict reading "
             "of 'the same move'. Hourly only.")
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe, notes=notes))


if __name__ == "__main__":
    main()
