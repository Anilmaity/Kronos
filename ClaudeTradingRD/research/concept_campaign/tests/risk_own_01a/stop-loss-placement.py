"""stop-loss-placement (contested) — full invalidation (protected-swing wick) vs body stop.

Spec §5.1: "The stop is the protected swing. That is the whole answer." The one documented
modification is the BODY extreme of the opposing-candle series, "with the acknowledged
cost that price will sometimes sweep the wick, stop you out, and then reach the target".
The concept's own measurables: "expectancy of the same signal set under each stop rule",
"realised R distribution under each stop convention on the same trade set".

Test: the same 1h CISD entries (phase-3 locked book), each scored twice with a fixed 2R
target — once with the stop at the protected swing (gated rows, the default) and once at
the body extreme of the opposing series (phase-3 §1.11 declared secondary stop, the same
helper). Only entries where the two stops differ are used. claim '+': the protected-swing
stop is the better stop (control-adjusted, each arm vs its own geometry-matched control).

Only one reading is run: the concept's other variants (Ben's raided-swing rule, candle vs
short-term-swing, long/intermediate-term swings) belong to guest or older-era framings and
the channel's canonical contrast is wick vs body.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_raw, PHASE3_SRC  # noqa: E402

CID = "stop-loss-placement"
HOLD = "10h"


def detect(m1):
    b, ev = cisd_raw(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "swing_stop"]
    if ev is None:
        return pd.DataFrame(columns=cols)
    s = ev["direction"].to_numpy()
    wick, body, close = ev["stop_px"].to_numpy(), ev["body_px"].to_numpy(), ev["close_px"].to_numpy()
    ok = (s * (body - wick) > 0) & (s * (close - body) > 0)   # body strictly inside
    base = ev[ok][["decision_time", "available_at", "direction"]]
    a = base.assign(stop_px=wick[ok], rr=2.0, swing_stop=True)
    c = base.assign(stop_px=body[ok], rr=2.0, swing_stop=False)
    return pd.concat([a, c]).sort_values(["decision_time", "swing_stop"], kind="stable") \
        .reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("slp_cisd1h_wick_vs_body_2r", lambda: detect(cl.load_m1()))
    print("rows", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "swing_stop", mask_available_at="decision_time", max_hold=HOLD,
                       claim="+")
    print({k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap")})
    op = {"rules": [
        "entries: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming "
        "bar close, enter next M1 open, target 2R of the row's own stop, exit at 10h",
        "gated rows: stop at the protected swing (wick extreme)",
        "complement rows: stop at the body extreme of the opposing-candle series "
        "(min/max of open/close over series_start..series_end)",
        "entries whose body stop is not strictly between the wick stop and the close are "
        "dropped (the two rules coincide or the body stop is invalid)"],
        "params": {"tf": "1h", "rr": 2.0, "max_hold": HOLD,
                   "body_stop": "series bodies (phase-3 body_extreme_stops)"}}
    src = {"tf": PHASE3_SRC, "max_hold": PHASE3_SRC,
           "rr": "method_spec §5.3: 2R",
           "body_stop": "phase3: §1.11 declared secondary stop (body extreme of the series)"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Stacked variant rows on identical entries. The body stop has "
                              "a smaller risk so its 2R target is closer; each arm is "
                              "adjusted by its own matched control, so geometry cancels.")
    print("wrote", p)
