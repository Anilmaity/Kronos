"""smt-divergence — is an SMT at a shared swing a directional (reversal) signal on gold?

Two readings of the contested concept (both run once, locked before the first run):
  a  bare SMT: the divergence itself is the signal ("The divergence itself is the SMT -
     no additional confirmation is defined", 4ZP1dm-ktFE).
  b  SMT + reversal closure: "Require a reversal closure on the asset that took the level
     before acting" / "wait for the diverging asset's candle to close" (live_streams_05):
     the sweeping asset's bar-j close is back beyond the level it swept.
Trade: gold, in the SMT's direction (lows -> long, highs -> short), entered at the next M1
open after the divergence bar closes, symmetric 1 x ATR14(1h) stop and 1R target — a pure
"does the direction come true" book; the matched control holds direction/stop/target.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

CID = "smt-divergence"
STOP_ATR = 1.0          # declared-before-run
RR = 1.0                # declared-before-run
MAX_HOLD = "10h"        # phase3: 10 entry-TF bars (§1.13)
TOD_TOL = 30            # declared-before-run (README trap 9)


def detect(m1: pd.DataFrame, reading: str) -> pd.DataFrame:
    f = c.smt_frame(m1)
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr", "swept_by"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    if reading == "b":
        f = f[f["reclaim"].astype(bool)]
    # one trade per bar close and direction (several swings can diverge on one bar)
    f = f.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return pd.DataFrame({
        "decision_time": f["decision_time"].to_numpy(),
        "available_at": f["decision_time"].to_numpy(),
        "direction": f["direction"].to_numpy(int),
        "stop_dist": STOP_ATR * f["atr"].to_numpy(float),
        "rr": RR,
        "swept_by": f["swept_by"].to_numpy(),
    }).reset_index(drop=True)


def main():
    for reading in ("a", "b"):
        fn = lambda m, r=reading: detect(m, r)   # noqa: E731
        ev = cl.cache_frame(f"{CID}_{reading}_h1_lb20", lambda r=reading: detect(cl.load_m1(), r))
        probe = cl.probe_lookahead(fn, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
        print(reading, res["n"], res["diff"], res["ci_lo"], res["ci_hi"], res["verdict"],
              res["verdict_detail"], res.get("exposure_bars"), res.get("ties"))
        rules = [
            "gold 1h bars (UTC hours) vs XAG_USD 1h (OANDA), compared on shared bar starts",
            "shared level = a confirmed 2/2 swing extreme of one asset and the other asset's "
            "extreme on that same bar; SMT at bar j (<= 20 bars later) when one asset trades "
            "beyond its level and the other does not (first break wins; both beyond = none)",
            "lows -> bullish, highs -> bearish (detectors.bias.smt_events)",
        ]
        if reading == "b":
            rules.append("reversal closure: the sweeping asset's bar-j close is back beyond "
                         "the level it swept")
        rules += ["decide at gold bar j close; enter next M1 open; one trade per bar/direction",
                  "stop 1.0 x ATR14(1h); target 1R; exit after 10h wall clock"]
        op = {"rules": rules,
              "params": {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": 20,
                         "swing": "2/2", "stop_atr": STOP_ATR, "atr_n": 14, "rr": RR,
                         "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL,
                         **({"reclaim": "sweeping asset closes back beyond level"}
                            if reading == "b" else {})}}
        src = {
            "tf": "declared-before-run: corpus prefers 15m ('i prefer the 15 minute chart', "
                  "eHQ4nE-TQ2w) and calls SMT fractal; the campaign holds silver only at H1",
            "correlate": "corpus: smt-requires-framework ambiguity 'they just need to be "
                         "correlated' (silver is allowed); phase3 load_correlate",
            "smt_lookback": "phase3: detectors.bias.smt_events default used for gate_smt",
            "swing": "phase3: 2/2 swings (conjunction pre-registration §1.8)",
            "stop_atr": "declared-before-run: symmetric direction test, stop unspecified "
                        "('Per the entry model')",
            "atr_n": "declared-before-run",
            "rr": "declared-before-run: symmetric 1R barrier",
            "max_hold": "phase3: 10 entry-TF bars (§1.13)",
            "ctrl_tod_tol_min": "declared-before-run: README trap 9, SMT is not a timing concept",
        }
        if reading == "b":
            src["reclaim"] = ("corpus: live_streams_05 'Require a reversal closure on the "
                              "asset that took the level before acting'")
        notes = ("Hourly SMT only (no sub-hourly correlate data). Direct trade of the "
                 "divergence in gold; the corpus's own execution says SMT is not an entry by "
                 "itself — the confluence use is tested under smt-as-confirmation-not-signal "
                 "(reading a) and smt-requires-framework.")
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe, notes=notes)
        print("wrote", p)


if __name__ == "__main__":
    main()
