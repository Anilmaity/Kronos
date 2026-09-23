"""liquidity-sweep (TTrades own voice, specified) — batch liquidity_own_01a.

"A reversal is only available after a relevant swing has actually been run. Drift
toward a level ... without having swept anything, is treated as inducement rather
than as the beginning of a turn." Execution: entry via CISD after the sweep, stop
beyond the sweep extreme, targets previous day high/low.

gate_test, claim '+':
  Baseline book: every 15m bare CISD reversal (phase-3 rung 0 on the 15m entry TF:
    series_open level, fractal 2/2, max_wait 3), stop = protected swing, 2R, 150 min.
  Gate "swept": the reversal's extreme ran a RELEVANT swing — an untaken 1H fractal-2/2
    swing low (bullish) / high (bearish) from the last 7 days (the concept's HTF list is
    1D/4H/1H: a higher-timeframe swing, not "simply any local extreme" on the 15m),
    confirmed and still untaken when the opposing run into the extreme began.
    Complement: reversals whose extreme ran no such swing (the "inducement" turns).
  (Design note, decided before any test ran: a first draft used the previous day's
   high/low as the relevant pool; its gate fired on 1.2% of CISDs on a detector-only
   sanity pass, so it could never be powered. The 1H-swing reading was chosen instead
   without looking at any outcome.)
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

CID = "liquidity-sweep"
TF = "15min"
MAX_WAIT = 3
RR = 2.0
MAX_HOLD = "150min"
HTF = "1h"
POOL_WINDOW = pd.Timedelta("7D")


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAX_WAIT, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "swept"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    # relevant pools: 1H fractal-2/2 swings (the concept's lowest HTF), usable from the
    # close of their 2nd right-hand 1H bar
    h = cl.build_bars(m1, HTF)
    hs = swing_points(h[["open", "high", "low", "close"]], 2, 2)
    hct = pd.DatetimeIndex(h["close_time"])
    pools = {}
    for s, col, px in ((1, "swing_low", "low"), (-1, "swing_high", "high")):
        pos = np.flatnonzero(hs[col].to_numpy())
        pos = pos[pos + 2 < len(h)]
        pools[s] = (h.index[pos], hct[pos + 2], h[px].to_numpy()[pos])
    bt = b.index
    bl, bh = b["low"].to_numpy(), b["high"].to_numpy()
    bull = (ev["direction"] == "bullish").to_numpy()
    ss = pd.DatetimeIndex(ev["series_start"])
    xp = ev["extreme_price"].to_numpy()
    swept = np.zeros(len(ev), dtype=bool)
    for r in range(len(ev)):
        s = 1 if bull[r] else -1
        st, cf, lv = pools[s]
        k = (cf <= ss[r]) & (st >= ss[r] - POOL_WINDOW)
        k &= (lv > xp[r]) if s == 1 else (lv < xp[r])
        for q in np.flatnonzero(k):
            a = bt.searchsorted(cf[q])            # first 15m bar starting at/after confirm
            e = bt.searchsorted(ss[r])            # the run into the extreme starts here
            seg = bl[a:e] if s == 1 else bh[a:e]
            untaken = (len(seg) == 0) or ((seg.min() >= lv[q]) if s == 1 else
                                          (seg.max() <= lv[q]))
            if untaken:
                swept[r] = True
                break
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(bull, 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": RR,
                         "swept": swept})


def run():
    ev = cl.cache_frame(f"{CID}_{TF}_mw{MAX_WAIT}_h1pool", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "swept", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       claim="+", ctrl_tod_tol_min=30)
    op = {"rules": [
        "baseline: 15m bare CISD (series_open level, fractal 2/2, max_wait 3), entry at "
        "the next M1 open after the confirming close, stop = protected swing, 2R, 150 min",
        "gate swept: the CISD extreme traded beyond an untaken 1H fractal-2/2 swing low "
        "(bullish) / high (bearish) formed within 7 days, confirmed before the opposing "
        "run into the extreme started and untaken from its confirmation to that start",
        "complement: reversal with no run of that relevant pool (inducement)"],
        "params": {"tf": TF, "max_wait": MAX_WAIT, "rr": RR, "max_hold": MAX_HOLD,
                   "htf": HTF, "pool_window": "7D", "ctrl_tod_tol_min": 30}}
    src = {"tf": "phase3: 15m entry TF of the 15m/4H/1D stack; concept ltf ['15m','5m']",
           "max_wait": "phase3: locked CISD max_wait=3",
           "rr": "method_spec: §5.3 2R floor/fixed target",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "htf": "corpus: source YAML timeframes.htf ['1D','4H','1H'] "
                  "(sunday_sessions_live_q_a_03); 1H = lowest HTF, fractal 2/2 per "
                  "threshold_fits",
           "pool_window": "declared-before-run: finite pool memory (one week)",
           "ctrl_tod_tol_min": "declared-before-run: not a timing concept; HTF-swing runs "
                               "cluster in London/NY hours (README trap 9)"}
    return res, op, src, probe


if __name__ == "__main__":
    import os, pickle
    pk = os.path.join(cl.CACHE_DIR, f"liquidity_own_01a_{CID}_result.pkl")
    if os.path.exists(pk):
        res, op, src, probe = pickle.load(open(pk, "rb"))
    else:
        res, op, src, probe = run()
        pickle.dump((res, op, src, probe), open(pk, "wb"))
    for k in ("n", "n_complement", "gate_rate", "avg_R", "diff", "ci_lo", "ci_hi", "p",
              "mde", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap"):
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
    print("  wrote", cl.write_result(CID, None, res, operationalization=op,
                                     params_source=src, script=__file__, probe=probe))
