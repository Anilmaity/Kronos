"""trade-away-from-manipulation (guest: GxTradez) -> gate_test.

Claim: only trade away from a manipulation (a sweep of a prior high/low) - never away from a
failure swing (a turn that left the prior low/high intact, no sweep). claim '+' = reversal
entries whose turning extreme swept a prior swing do better than those that did not.

Baseline book (declared before the run): the phase-3 rung-0 CISD on 15m bars (series_open,
2/2 swing, max_wait 3, min_series 1), decided at the confirming bar's close, entry next M1
open, stop at the protected swing (the turn's extreme), 2R, max_hold 150min (10 bars).
Gate `manip`: for a bullish CISD, the turn's extreme low traded below the most recent 1h
2/2 swing low that was confirmed (its confirming 1h bar closed) before the extreme 15m bar
opened; mirrored for bearish. Otherwise the turn is a failure swing (complement).
The SMT pairing and the "FVG/OB formed by the manipulation" entry refinement are not
modelled (SMT is demoted to a knob in phase 3).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

TF = "15min"
HTF = "1h"
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "manip"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    h1 = cl.build_bars(m1, HTF)
    h1 = h1[h1["n_m1"] > 0]
    sp = swing_points(h1[["open", "high", "low", "close"]], 2, 2)
    ct1 = h1["close_time"].values
    n1 = len(h1)
    pos = np.arange(n1)
    okc = pos + 2 < n1
    conf = np.full(n1, np.datetime64("NaT", "ns"))
    conf[okc] = ct1[pos[okc] + 2]
    res = {}
    for name, flag, px in (("low", sp["swing_low"].to_numpy(), h1["low"].to_numpy()),
                           ("high", sp["swing_high"].to_numpy(), h1["high"].to_numpy())):
        idx = np.flatnonzero(flag & okc)
        order = np.argsort(conf[idx], kind="stable")
        res[name] = (conf[idx][order], px[idx][order])
    ext_t = pd.DatetimeIndex(ev["extreme_time"]).tz_convert("UTC").as_unit("ns").tz_localize(None).values
    ext_p = ev["extreme_price"].to_numpy(float)
    bull = (ev["direction"] == "bullish").to_numpy()
    manip = np.zeros(len(ev), bool)
    for is_bull, key in ((True, "low"), (False, "high")):
        cf, lv = res[key]
        sel = np.flatnonzero(bull == is_bull)
        k = np.searchsorted(cf, ext_t[sel], side="right") - 1
        ok = k >= 0
        ref = np.where(ok, lv[np.clip(k, 0, None)], np.nan)
        manip[sel] = ok & ((ext_p[sel] < ref) if is_bull else (ext_p[sel] > ref))
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(bull, 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": RR, "manip": manip})
    return out.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"tafm_{TF}_{HTF}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.manip.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "manip", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline: rung-0 CISD on 15m (series_open, 2/2, max_wait 3), protected-swing stop, 2R, 150min",
        "manip: the turn's extreme took out the most recent 1h 2/2 swing low (high) confirmed before the extreme bar opened",
        "complement = failure swing (turn left the prior swing intact)",
        "gate_test manip vs failure swing, control-adjusted"],
        "params": {"tf": TF, "htf_swing": HTF, "swing": "2/2", "max_wait": 3, "rr": RR,
                   "max_hold": MAX_HOLD}}
    src = {"tf": "phase3: 15m rung-0 CISD entry TF (concept ltf includes 15m)",
           "htf_swing": "declared-before-run: 'prior high or low' = most recent confirmed 1h swing (concept ltf 1H)",
           "swing": "phase3: 2/2 fractal swing (locked config)",
           "max_wait": "phase3: rung-0 max_wait 3 (locked config)",
           "rr": "phase3: rung-0 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result("trade-away-from-manipulation", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="SMT pairing and manipulation-formed FVG/OB entry not modelled; tests "
                              "the sweep-vs-failure-swing selection on the rung-0 15m CISD book.")
    print(p)
