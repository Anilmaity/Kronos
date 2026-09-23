"""smt-requires-framework — model first, SMT second.

Doctrine (-ocfPuD_oqE, 0AYGNc9czYc, NESSCPMzWR0): "SMT means nothing without a framework";
"If my model has not formed, I do not look for SMT yet". Measurable: "expectancy of SMT
signals with a model present vs absent" / "SMT-first entries vs model-first entries".

gate_test. Baseline book = every hourly gold/XAG SMT traded directly in its direction
(the SMT-first trader: next M1 open after the divergence bar, 1 x ATR14(1h) stop, 1R,
10h — the smt-divergence reading-a geometry). Gate = the model already exists: a
same-direction 1h CISD (the phase-3 rung-0 detector, i.e. the "aligned change in the state
of delivery") confirmed at or within 3h before the SMT bar's close. claim '+': SMTs with a
model beat SMTs without one (control-adjusted).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

CID = "smt-requires-framework"
WINDOW = pd.Timedelta(hours=3)   # phase3: smt_gate window = 3 hourly bars
STOP_ATR = 1.0                   # declared-before-run
RR = 1.0                         # declared-before-run
MAX_HOLD = "10h"                 # phase3
TOD_TOL = 30                     # declared-before-run (README trap 9)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr", "model_first"]
    f = c.smt_frame(m1, "gold_last")
    if f.empty:
        return pd.DataFrame(columns=cols)
    f = f.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    out = pd.DataFrame({
        "decision_time": f["decision_time"].to_numpy(),
        "available_at": f["decision_time"].to_numpy(),
        "direction": f["direction"].to_numpy(int),
        "stop_dist": STOP_ATR * f["atr"].to_numpy(float),
        "rr": RR,
    })
    k = c.cisd_1h(m1)
    out["model_first"] = (c.prior_match(pd.DatetimeIndex(out["decision_time"]),
                                        out["direction"].to_numpy(int),
                                        pd.DatetimeIndex(k["decision_time"]),
                                        k["direction"].to_numpy(int), WINDOW)
                          if len(k) else False)
    out["model_first"] = out["model_first"].astype(bool)
    return out.reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"{CID}_smtbook_cisd3h", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("gate firing", ev["model_first"].mean(), len(ev))
    res = cl.gate_test(ev, "model_first", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(res["n"], res["diff"], res["ci_lo"], res["ci_hi"], res["verdict"],
          res["verdict_detail"])
    op = {"rules": ["baseline: every hourly gold/XAG SMT (detectors.bias.smt_events, 2/2 "
                    "swings, 20-bar lookback), traded in gold in its direction at the next "
                    "M1 open after the divergence bar close; stop 1 x ATR14(1h), 1R, 10h",
                    "gate (model first): a same-direction 1h CISD (series_open, 2/2, max_wait "
                    "3) confirmed at or within 3h before the SMT bar close",
                    "complement = SMT-first trades with no model behind them"],
          "params": {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": 20,
                     "swing": "2/2", "cisd_max_wait": 3, "window": "3h",
                     "stop_atr": STOP_ATR, "atr_n": 14, "rr": RR, "max_hold": MAX_HOLD,
                     "ctrl_tod_tol_min": TOD_TOL}}
    src = {"tf": "declared-before-run: SMT is fractal; silver held only at H1 (the "
                 "concept's own htf list includes 1H)",
           "correlate": "corpus: 'they just need to be correlated' (silver is allowed)",
           "smt_lookback": "phase3: detectors.bias.smt_events default",
           "swing": "phase3: 2/2 swings (§1.8)",
           "cisd_max_wait": "phase3: locked rung-0 config",
           "window": "phase3: detectors.bias.smt_gate window=3 bars (hourly)",
           "stop_atr": "declared-before-run: symmetric direction book",
           "atr_n": "declared-before-run",
           "rr": "declared-before-run: symmetric 1R barrier",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9"}
    notes = ("'Model' reduced to the 1h CISD; the C2/C3-closure-at-POI layer is not "
             "applied (phase 3 found no gate load-bearing). Only one reading run: the V-shape "
             "displacement and 'far beyond the level' variants have no stated measure.")
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe, notes=notes))


if __name__ == "__main__":
    main()
