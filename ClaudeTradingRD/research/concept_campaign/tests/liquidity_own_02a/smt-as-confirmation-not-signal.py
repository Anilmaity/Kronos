"""smt-as-confirmation-not-signal — the contested SMT role, both readings.

Reading a (q1NmxUTm4n4, later canon): SMT is a confluence to an already existing model,
never the trigger. Test: gate_test on the model book — phase-3 rung-0 1h CISD (stop at
the protected swing, 2R, 10h) — gated on a same-direction hourly gold/silver SMT that
had already printed (decision time within the 3 hours up to and including the CISD
close; "SMT printed prior to the decision candle counts", yud7TpE2AMs). Claim: SMT-
confirmed model trades beat unconfirmed ones.

Reading b (eHQ4nE-TQ2w): SMT traded DIRECTLY — enter on the diverging asset (the one that
HELD its level; here gold), stop at the diverging low/high. Test: trade_test on
gold-held SMTs, stop at gold's held level, 2R target, 10h.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

CID = "smt-as-confirmation-not-signal"
WINDOW = pd.Timedelta(hours=3)   # phase3: smt_gate window=3 bars x 1h
RR_B = 2.0                       # phase3: rung-0 R target 2.0 (§1.13)
MIN_STOP_ATR = 0.25              # declared-before-run: hygiene, drops near-zero stops
MAX_HOLD = "10h"                 # phase3
TOD_TOL = 30                     # declared-before-run (README trap 9)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    ev = c.cisd_1h(m1)
    if ev.empty:
        ev["smt_confirms"] = pd.Series(dtype=bool)
        return ev
    f = c.smt_frame(m1)
    ev["smt_confirms"] = c.prior_match(pd.DatetimeIndex(ev["decision_time"]),
                                       ev["direction"].to_numpy(int),
                                       pd.DatetimeIndex(f["decision_time"]),
                                       f["direction"].to_numpy(int), WINDOW) \
        if len(f) else False
    ev["smt_confirms"] = ev["smt_confirms"].astype(bool)
    return ev.reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    f = c.smt_frame(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    f = f[f["held_by"] == "gold"]
    dist = (f["gold_close"] - f["invalidation"]) * f["direction"]
    f = f[dist >= MIN_STOP_ATR * f["atr"]]
    f = f.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return pd.DataFrame({
        "decision_time": f["decision_time"].to_numpy(),
        "available_at": f["decision_time"].to_numpy(),
        "direction": f["direction"].to_numpy(int),
        "stop_px": f["invalidation"].to_numpy(float),
        "rr": RR_B,
    }).reset_index(drop=True)


COMMON_SRC = {
    "tf": "declared-before-run: SMT is fractal (q1NmxUTm4n4); silver held only at H1",
    "correlate": "corpus: 'they just need to be correlated' (silver is allowed); phase3 load_correlate",
    "smt_lookback": "phase3: detectors.bias.smt_events default used for gate_smt",
    "swing": "phase3: 2/2 swings (§1.8)",
    "max_hold": "phase3: 10 entry-TF bars (§1.13)",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9",
}
SMT_RULE = ("hourly gold/XAG SMT (detectors.bias.smt_events): shared level = a confirmed 2/2 "
            "swing of one asset and the other's extreme on that bar; one trades beyond it "
            "within 20 bars and the other does not; lows bullish, highs bearish; known at "
            "the divergence bar's close")


def run_a():
    ev = cl.cache_frame(f"{CID}_a_cisd1h_smt3h", lambda: detect_a(cl.load_m1()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.gate_test(ev, "smt_confirms", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print("a", res["n"], res.get("gate_rate"), res["diff"], res["ci_lo"], res["ci_hi"],
          res["verdict"], res["verdict_detail"])
    op = {"rules": ["model book: 1h CISD (series_open level, 2/2 swing, max_wait 3), decide "
                    "at the confirming bar close, stop at protected swing, 2R, 10h",
                    SMT_RULE,
                    "gate: a same-direction SMT whose bar closed within the 3h up to and "
                    "including the CISD close (only already-printed SMTs)"],
          "params": {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": 20,
                     "swing": "2/2", "cisd_max_wait": 3, "rr": 2.0, "window": "3h",
                     "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL}}
    src = dict(COMMON_SRC, cisd_max_wait="phase3: locked config (§1.8-1.13)",
               rr="phase3: rung-0 2R",
               window="phase3: detectors.bias.smt_gate window=3 bars (hourly)")
    notes = ("Model simplified to the phase-3 1h CISD (the 'aligned change in state of "
             "delivery'); no C2/C3-at-POI layer. Mask stamped at decision_time: every SMT "
             "it reads closed at or before the CISD close.")
    print("wrote", cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe, notes=notes))


def run_b():
    ev = cl.cache_frame(f"{CID}_b_goldheld_stopinv", lambda: detect_b(cl.load_m1()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print("b", res["n"], res["diff"], res["ci_lo"], res["ci_hi"], res["verdict"],
          res["verdict_detail"], res.get("exposure_bars"), res.get("ties"))
    op = {"rules": [SMT_RULE,
                    "keep SMTs where silver swept and GOLD held (gold is the diverging asset)",
                    "enter gold in the SMT direction at the next M1 open after the bar close",
                    "stop exactly at gold's held low/high (the divergence's invalidation)",
                    "drop setups whose stop is < 0.25 ATR14(1h) from the bar close",
                    "target 2R; exit after 10h"],
          "params": {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": 20,
                     "swing": "2/2", "rr": RR_B, "min_stop_atr": MIN_STOP_ATR,
                     "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL}}
    src = dict(COMMON_SRC,
               rr="phase3: rung-0 2R target (corpus gives no target for the direct entry)",
               min_stop_atr="declared-before-run: hygiene against near-zero stops")
    notes = ("Stop placement per eHQ4nE-TQ2w 'if these lows or highs are broken or taken the "
             "divergence is invalidated' and 'you want to take the one that is diverging'.")
    print("wrote", cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe, notes=notes))


if __name__ == "__main__":
    run_a()
    run_b()
