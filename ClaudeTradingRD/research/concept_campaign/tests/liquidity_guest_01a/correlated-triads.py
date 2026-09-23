"""correlated-triads (GxTradez, guest) — gate_test on 1H gold swing-sweep reversals.

The concept is an asset map: for gold, compare the same swing across the triad
GC / XAU-EUR / XAU-GBP for SMT. The testable content is that divergence against the
NAMED gold triad carries information. XAU-GBP needs GBPUSD, which the lab does not
hold; XAU-EUR is built from gold H1 and OANDA EUR_USD H1 (declared approximation in
_smt_common.xaueur_h1). So this tests the one available triad member.

Baseline book (stated): gold trades beyond a confirmed 1H fractal(2/2) swing within
20 bars -> reversal trade at the sweep bar's close, stop at the sweep extreme, 2R,
10h hold. Gate: at the sweep bar's close XAU/EUR has NOT traded beyond its own
extreme at the swing bar (a triad SMT). claim '+': SMT-confirmed sweeps do better.

Params declared before the first run; fractal/lookback/2R are phase-3 values.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _smt_common as sc  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

LOOKBACK, LEFT, RIGHT, RR, MAX_HOLD = 20, 2, 2, 2.0, "10h"


def detect(m1):
    P = sc.pair_bars(m1, "1h", "xaueur")
    n = len(P)
    sw = swing_points(P.rename(columns={"g_high": "high", "g_low": "low"})[["high", "low"]],
                      LEFT, RIGHT)
    gc = P.g_close.to_numpy()
    ct = pd.DatetimeIndex(P.close_time)
    rows = []
    for hi_side in (True, False):
        g = P.g_high.to_numpy() if hi_side else P.g_low.to_numpy()
        s = P.s_high.to_numpy() if hi_side else P.s_low.to_numpy()
        sgn = 1.0 if hi_side else -1.0
        for p in np.flatnonzero(sw["swing_high" if hi_side else "swing_low"].to_numpy()):
            lg, ls = g[p], s[p]
            if (sgn * g[p + 1:min(n, p + RIGHT + 1)] > sgn * lg).any():
                continue
            for j in range(p + RIGHT + 1, min(n, p + RIGHT + 1 + LOOKBACK)):
                if sgn * g[j] > sgn * lg:
                    ext = g[j]
                    if sgn * (ext - gc[j]) > 0:
                        held = not (sgn * s[p + 1:j + 1] > sgn * ls).any()
                        rows.append({"decision_time": ct[j], "available_at": ct[j],
                                     "direction": -1 if hi_side else 1,
                                     "stop_px": float(ext), "rr": RR,
                                     "triad_smt": bool(held)})
                    break
    out = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                      "stop_px", "rr", "triad_smt"])
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


if __name__ == "__main__":
    ev = cl.cache_frame("triad_xaueur_sweep_1h", lambda: detect(cl.load_m1()))
    print(len(ev), ev.triad_smt.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "triad_smt", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "exposure_bars", "ties")})
    p = cl.write_result(
        "correlated-triads", None, res,
        operationalization={"rules": [
            "gold 1H bars from certified M1; XAU/EUR 1H = gold/EURUSD (OANDA EUR_USD H1), extremes via EUR bar mid",
            "baseline: gold trades beyond a confirmed fractal(2/2) 1H swing extreme within 20 bars (skip if taken before confirmation)",
            "trade gold reversal at the sweep bar close; stop = sweep-bar extreme; target 2R; max_hold 10h",
            "gate triad_smt: XAU/EUR's own extreme at the swing bar was NOT exceeded from p+1 through the sweep bar (SMT against the named gold triad member), known at the sweep bar close",
            "XAU/GBP (third triad member) unavailable: no GBPUSD series in the lab"],
            "params": {"tf": "1h", "fractal": [LEFT, RIGHT], "sweep_lookback": LOOKBACK,
                       "rr": RR, "max_hold": MAX_HOLD, "triad_member": "XAU/EUR",
                       "xaueur_extremes": "gold high/low divided by EUR (high+low)/2"}},
        params_source={
            "tf": "corpus: 3eVxTV_7L2U ltf/htf list includes 4H..1m; 1H is the finest grid the correlate supports",
            "fractal": "phase3: swing_points left=2 right=2",
            "sweep_lookback": "phase3: smt_events lookback=20",
            "rr": "phase3: bare-CISD book target 2R",
            "max_hold": "phase3: 1h book max_hold 10h (concept_lab README example)",
            "triad_member": "corpus: 3eVxTV_7L2U 'For gold we have gold or GC X AU Euro and X AU GBP'",
            "xaueur_extremes": "declared-before-run: H1 approximation, intrabar timing of the two extremes unknown"},
        script=__file__, probe=probe,
        notes=f"gate firing rate {ev.triad_smt.mean():.3f}. Tests only the XAU/EUR leg of the stated "
              "gold triad; the 18:00-open data-feed remark is satisfied by construction (NY 18:00 day roll).")
    print(p)
