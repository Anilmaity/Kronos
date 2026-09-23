"""high-vs-low-resistance-liquidity (TTrades own voice, contested) — batch liquidity_own_01a.

Claim: low-resistance liquidity (a failure swing — price turned before reaching the
prior extreme, so its stops were never taken) is run / expanded through more readily
than high-resistance liquidity (an extreme that itself swept the prior one).

Reading a — swing-level sense (the dedicated Shorts): gate_test.
  Book: at the confirmation of every 15m fractal-2/2 swing high S_k, a bracket long
  whose target is S_k and whose stop is the same distance below the confirmation
  close (mirror for swing lows / shorts). A win = the swing's liquidity is run
  before an equal excursion the other way; matched controls remove geometry.
  Gate (low resistance): S_k is lower than the previous swing high S_{k-1}
  ("a high with a lower high next to it" / "a high lower than the previous high =
  a failure swing"). Complement: S_k > S_{k-1} (it swept the prior high = high
  resistance). Equal highs are dropped. claim '+'.

Reading b — daily band sense ("Daily scan for a low-resistance region: runs of
  consecutive daily candles in which no previous day high was ever taken ... Once
  price starts to break through such a band, expect it to continue through and
  expand"): gate_test.
  Book: the first M1 close above the previous day high (below the previous day low)
  in each trading day, long (short) at the next M1 open, stop = the day's running
  low (high) at that moment, target 2R.
  Gate: the two previous days both failed to take their own previous day's high
  (low) — a band of >= 2 stacked unswept daily highs (lows) sits in the path.
  claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

CID = "high-vs-low-resistance-liquidity"
TF = "15min"
LEFT = RIGHT = 2
PREV_WINDOW = pd.Timedelta("7D")   # previous swing must be this recent (finite history)
MAX_HOLD_A = "6h"
BAND_DAYS = 2
RR_B = 2.0
MAX_HOLD_B = "6h"
MIN_BARS = 600


def detect_a(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    n = len(b)
    ct = pd.DatetimeIndex(b["close_time"])
    C = b["close"].to_numpy()
    idx = b.index
    rows = []
    for col, px, s in (("swing_high", "high", 1), ("swing_low", "low", -1)):
        pos = np.flatnonzero(sw[col].to_numpy())
        pos = pos[pos + RIGHT < n]
        lv = b[px].to_numpy()[pos]
        for j in range(1, len(pos)):
            if idx[pos[j]] - idx[pos[j - 1]] > PREV_WINDOW or lv[j] == lv[j - 1]:
                continue
            k = pos[j] + RIGHT
            dist = s * (lv[j] - C[k])
            if dist <= 0:
                continue
            lr = (lv[j] < lv[j - 1]) if s == 1 else (lv[j] > lv[j - 1])
            rows.append((ct[k], ct[k], s, C[k] - s * dist, lv[j], bool(lr)))
    ev = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                     "stop_px", "target_px", "low_resistance"])
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def detect_b(m1):
    d = cl.build_bars(m1, "1D")
    H, L, N = d["high"].to_numpy(), d["low"].to_numpy(), d["n_m1"].to_numpy()
    td_d = cl.trading_day(d.index)
    # per trading day k: PDH/PDL and the band flags from the 3 prior days
    info = {}
    for k in range(3, len(d)):
        if min(N[k - 1], N[k - 2], N[k - 3]) < MIN_BARS:
            continue
        band_h = (H[k - 1] <= H[k - 2]) and (H[k - 2] <= H[k - 3])
        band_l = (L[k - 1] >= L[k - 2]) and (L[k - 2] >= L[k - 3])
        info[td_d[k]] = (H[k - 1], L[k - 1], band_h, band_l)
    if not info:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction",
                                     "stop_px", "rr", "band"])
    td = cl.trading_day(m1.index)
    key = pd.DataFrame(info, index=["pdh", "pdl", "bh", "bl"]).T
    j = key.reindex(td)
    pdh, pdl = j["pdh"].to_numpy(float), j["pdl"].to_numpy(float)
    c = m1["close"].to_numpy()
    g = pd.Series(np.asarray(td))
    run_lo = pd.Series(m1["low"].to_numpy()).groupby(g).cummin().to_numpy()
    run_hi = pd.Series(m1["high"].to_numpy()).groupby(g).cummax().to_numpy()
    close_t = m1.index + pd.Timedelta(minutes=1)
    rows = []
    for s, brk, stop, bcol in ((1, c > pdh, run_lo, "bh"), (-1, c < pdl, run_hi, "bl")):
        f = pd.Series(brk).groupby(g).cumsum().to_numpy() == 1
        f &= brk
        for i in np.flatnonzero(f):
            rows.append((close_t[i], close_t[i], s, stop[i], RR_B,
                         bool(j[bcol].iloc[i])))
    ev = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                     "stop_px", "rr", "band"])
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def run(r):
    if r == "a":
        ev = cl.cache_frame(f"{CID}_a_{TF}", lambda: detect_a(cl.load_m1()))
        probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
        res = cl.gate_test(ev, "low_resistance", mask_available_at="decision_time",
                           max_hold=MAX_HOLD_A, claim="+", hold_basis="bars",
                           ctrl_tod_tol_min=30)
        op = {"rules": [
            "swings: 15m fractal 2/2, decided at the close of the 2nd right-hand bar",
            "book: bracket toward the just-confirmed swing (target = swing extreme, stop = "
            "same distance on the other side of the confirmation close), 6h trading-time hold",
            "gate low_resistance: swing high lower than the previous swing high (swing low "
            "higher than the previous swing low) = failure swing; complement = the swing "
            "exceeded the previous one (swept it) = high resistance; equal levels dropped; "
            "previous swing must lie within 7 days"],
            "params": {"tf": TF, "left": LEFT, "right": RIGHT, "prev_window": "7D",
                       "max_hold": MAX_HOLD_A, "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
        src = {"tf": "corpus: source YAML timeframes.htf includes 15m (shorts_02/03/04)",
               "left": "threshold_fits: short-term high/low = fractal 2/2",
               "right": "threshold_fits: short-term high/low = fractal 2/2",
               "prev_window": "declared-before-run: finite history for the probe",
               "max_hold": "declared-before-run: 24 x 15m bars",
               "hold_basis": "declared-before-run: trading-time hold (README trap 7)",
               "ctrl_tod_tol_min": "declared-before-run: not a timing concept; swings "
                                   "cluster in active hours (README trap 9)"}
    else:
        ev = cl.cache_frame(f"{CID}_b_band{BAND_DAYS}", lambda: detect_b(cl.load_m1()))
        probe = cl.probe_lookahead(detect_b, ev, lookback="15D")
        res = cl.gate_test(ev, "band", mask_available_at="decision_time",
                           max_hold=MAX_HOLD_B, claim="+", hold_basis="bars",
                           ctrl_tod_tol_min=30)
        op = {"rules": [
            "book: first M1 close above PDH (below PDL) in a trading day (18:00 NY roll); "
            "entry next M1 open; stop = the day's running low (high) at that close; "
            "target 2R; 6h trading-time hold",
            "gate band: the previous 2 days each failed to take their own previous day's "
            "high (low) -> >= 2 stacked unswept daily highs (lows) = low-resistance band",
            "days whose 3 prior sessions have < 600 M1 bars are not read"],
            "params": {"band_days": BAND_DAYS, "rr": RR_B, "max_hold": MAX_HOLD_B,
                       "hold_basis": "bars", "ctrl_tod_tol_min": 30, "min_bars": MIN_BARS,
                       "day_open_hour": 18}}
        src = {"band_days": "declared-before-run: 'consecutive candles where no high is "
                            "broken' has no minimum count; 2 = the smallest run that is a band",
               "rr": "method_spec: §5.3 2R is the floor / fixed target",
               "max_hold": "declared-before-run: 6h trading time",
               "hold_basis": "declared-before-run: trading-time hold (README trap 7)",
               "ctrl_tod_tol_min": "declared-before-run: breaks cluster in NY hours "
                                   "(README trap 9)",
               "min_bars": "declared-before-run: README trap 6 stub-session guard",
               "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    return res, op, src, probe


if __name__ == "__main__":
    import os, pickle
    for r in (sys.argv[1:] or ["a", "b"]):
        pk = os.path.join(cl.CACHE_DIR, f"liquidity_own_01a_{CID}_{r}_result.pkl")
        if os.path.exists(pk):
            res, op, src, probe = pickle.load(open(pk, "rb"))
        else:
            res, op, src, probe = run(r)
            pickle.dump((res, op, src, probe), open(pk, "wb"))
        print(f"== reading {r}")
        for k in ("n", "n_gated", "n_complement", "gate_rate", "avg_R", "diff", "ci_lo",
                  "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties",
                  "exposure_bars", "ctrl_overlap", "dropped"):
            if res.get(k) is not None:
                print(f"  {k:15s} {res[k]}")
        print("  wrote", cl.write_result(CID, r, res, operationalization=op,
                                         params_source=src, script=__file__, probe=probe))
