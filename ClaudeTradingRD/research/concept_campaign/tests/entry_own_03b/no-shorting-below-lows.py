"""no-shorting-below-lows — contested; TTrades live streams. A LOCATION FILTER, so
gate_test on a baseline book; the concept says entries located below the lows (shorts)
/ above the highs (longs) are WORSE -> the 'chasing' mask is gated with claim '-'.

Baseline book (stated): 15m bare CISD, phase-3 rung-0 config (series_open, 2/2 swings,
max_wait 3), entered at the next M1 open after the confirming close, stop at the
protected swing, 2R, exit after 150 min, both directions (the mirror rule 'not a fan
of longing over the highs' is stated on air, N3Ml-r0X30o).

reading a (N3Ml-r0X30o 'I don't want to be selling below previous day low'): chasing =
  short whose confirming close is below the PREVIOUS DAY LOW, or long above the
  previous day high (18:00 NY day; stub days < 50% coverage skipped).
reading b (x4sRGuZIqWk 'I'm not looking short here because we're at the low of the
  day' / Je7cd9HJUBE 'short below lows like this'): chasing = short whose confirming
  close is below the CURRENT trading day's low as it stood before that 15m bar opened
  (i.e. it closes at fresh day lows), or long above the day's high so far.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl  # noqa: E402
from detectors.cisd import cisd_events         # noqa: E402

CID = "no-shorting-below-lows"
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "chase_pd", "chase_day"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    cs = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if cs.empty:
        return bc.empty(COLS)
    t = pd.DatetimeIndex(b.loc[cs["confirm_time"], "close_time"]).tz_convert("UTC")
    bar_open = pd.DatetimeIndex(cs["confirm_time"]).tz_convert("UTC")
    d = np.where(cs["direction"] == "bullish", 1, -1)
    px = cs["confirm_close"].to_numpy(float)
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    rh = cl.running_hilo(bar_open, "1D", m1=m1)       # the day so far, before this bar
    dh, dl = rh["high"].to_numpy(float), rh["low"].to_numpy(float)
    ok = np.isfinite(pdh) & np.isfinite(pdl)
    chase_pd = np.where(d == -1, px < pdl, px > pdh)
    # no bar of the day closed before this bar opened -> nothing to chase: not chasing
    chase_day = np.where(np.isfinite(dh), np.where(d == -1, px < dl, px > dh), False)
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                       "stop_px": cs["protected_swing"].to_numpy(float), "rr": RR,
                       "chase_pd": chase_pd.astype(bool), "chase_day": chase_day.astype(bool)})
    ev = ev[ok]
    return bc.finish(ev)


def show(res):
    for k in ["n", "n_gated", "gate_rate", "fire_rate", "diff", "ci_lo", "ci_hi", "p", "gated_vs_own_control",
              "verdict", "verdict_detail", "ties"]:
        if k in res:
            print(" ", k, res.get(k))


if __name__ == "__main__":
    ev = cl.cache_frame("noshort_15m_cisd_rung0_masks", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["chase_pd"].mean(), ev["chase_day"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base_rules = [
        "baseline: 15m CISD (close through the opening price of the opposing-candle series "
        "into a 2/2 swing, within 3 bars), both directions; enter next M1 open after the "
        "confirming close; stop at the protected swing; 2R; exit 150 min"]
    params = {"tf": bc.TF, "cisd": "series_open/2-2/mw3", "rr": RR, "max_hold": MAX_HOLD,
              "day_open_hour": 18}
    src = {"tf": "phase3: primary stack entry TF (concept ltf 5m/3m/1m, htf 1H/15m)",
           "cisd": "phase3: locked rung-0 CISD config",
           "rr": "phase3: rung-0 2R target",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    keys = [k for k in ["n", "diff", "ci_lo", "ci_hi", "verdict"]]
    # reading a
    res = cl.gate_test(ev, "chase_pd", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="-")
    show(res)
    op = {"rules": base_rules + [
        "gate (reading a): chasing = short with confirming close below the previous "
        "trading day's low, or long above its high (prior_hilo 1D, min_coverage 0.5)",
        "claim '-': the chasing trades underperform the rest (control-adjusted)"],
        "params": {**params, "reference": "previous day high/low", "min_coverage": 0.5}}
    print(cl.write_result(CID, "a", res, operationalization=op,
                          params_source={**src, "reference": "corpus: N3Ml-r0X30o 'I don't want to be selling below previous day low'",
                                         "min_coverage": "declared-before-run: skip stub days (README trap 6)"},
                          script=__file__, probe=probe,
                          notes="Gate verdict known at the decision (PDH/PDL of a closed day and "
                                "the confirming close)."))
    # reading b
    res = cl.gate_test(ev, "chase_day", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="-")
    show(res)
    op = {"rules": base_rules + [
        "gate (reading b): chasing = short whose confirming close is below the current "
        "trading day's low as it stood before that 15m bar opened (fresh day lows), or long "
        "above the day's high so far",
        "claim '-'"],
        "params": {**params, "reference": "running day high/low before the signal bar"}}
    print(cl.write_result(CID, "b", res, operationalization=op,
                          params_source={**src, "reference": "corpus: x4sRGuZIqWk 'I'm not looking short here because we're at the low of the day'"},
                          script=__file__, probe=probe,
                          notes="The day-range-spent clause is not quantified in the corpus and is "
                                "not applied."))
