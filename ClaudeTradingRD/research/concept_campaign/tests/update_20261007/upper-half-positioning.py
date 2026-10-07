"""upper-half-positioning (TTrades update 2026-10-07, dealing-range video yb3Te7tiGRk) - gate_test, 1 reading.

New claim only. The prior reading (results/upper-half-positioning.json, 1h CISD -> PDH/PDL book) tested
the 50% rule and came back NULL; it is not repeated here. The update adds a numeric REJECTION FLOOR:
"As I get to 25% of the range or lower, that is where I'm not really looking for shorts", with the
EQ itself tolerated ("It's okay if I'm entering right around that EQ point") and 25%-50% a grey zone
that is worse but not forbidden. So the rule tested is the floor: entries more than 25% of the dealing
range away from its target end (pass) vs entries at or within the last 25% (reject).

u1007a
  Dealing range, built the way the video builds it, on 1h (HTF) swings (2/2 fractal, phase-3 lock):
    short: A = the latest confirmed 1h swing high (the swing traded away from); its origin = the last
           1h swing low before it ("the swing low that made that swing high"); T = lowest low from that
           swing low through A's bar (= the swing low itself in the normal case). Target = T.
    long : mirror (A = latest confirmed 1h swing low; T = highest high back to the prior swing high).
    The range is live only while A is unbroken and T untaken on every complete 5m bar from A's bar
    through the entry bar ("We just took out the target. It doesn't make sense.").
  Entry book: phase-3 locked 5m CISD (series_open, 2/2, max_wait 3) whose direction trades away from A,
    decided at the confirming bar's close, entered next M1 open, stop = the 5m protected swing ("Put my
    stop on that protected high"), target 2R ("I can get 2 R prior to my target"), hold 10 x 5m.
    Kept only when T < entry < stop <= A (short; mirror long).
  frac = |T - entry| / |T - A| (0 = at the target, 1 = at the swing). Gate above_floor: frac > 0.25.
claim '+': gated (above the floor) beats the complement (at/below 25%), control-adjusted.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

CID = "upper-half-positioning"
READING = "u1007a"
HTF, LTF = "1h", "5min"
FLOOR = 0.25
RR = 2.0
HOLD = "50min"
TOD_TOL = 30
OHLC = ["open", "high", "low", "close"]
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "frac", "dr_id", "above_floor"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def _empty():
    return pd.DataFrame({"decision_time": pd.DatetimeIndex([], tz="UTC"),
                         "available_at": pd.DatetimeIndex([], tz="UTC"),
                         "direction": pd.Series(dtype=int), "stop_px": pd.Series(dtype=float),
                         "rr": pd.Series(dtype=float), "frac": pd.Series(dtype=float),
                         "dr_id": pd.Series(dtype="int64"), "above_floor": pd.Series(dtype=bool)})[COLS]


def _ranges(b1, sw, d):
    """Dealing ranges for direction d (-1 short: anchor = swing high, +1 long: anchor = swing low).
    Returns anchor bar start (ns), confirmation time (close of anchor+2, ns), anchor price A, target T."""
    h, l = b1["high"].to_numpy(float), b1["low"].to_numpy(float)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    anchor, origin = (is_sh, is_sl) if d < 0 else (is_sl, is_sh)
    P = np.flatnonzero(anchor)
    P = P[P + 2 < len(b1)]
    Q = np.flatnonzero(origin)
    k = np.searchsorted(Q, P, "left") - 1            # last origin swing strictly before the anchor
    P, q = P[k >= 0], Q[k[k >= 0]]
    if d < 0:
        A = h[P]
        T = np.array([l[a:p + 1].min() for a, p in zip(q, P)], float)
    else:
        A = l[P]
        T = np.array([h[a:p + 1].max() for a, p in zip(q, P)], float)
    return _ns(b1.index)[P], _ns(b1["close_time"])[P + 2], A, T


def detect(m1):
    # no completeness filter: an in-progress bar at the slice end only feeds swings/CISDs/ranges whose
    # stamps (confirm close, anchor+2 close) lie after the cut; a filter keyed on the last M1 minute
    # wrongly drops a closed bar whose final minute has no print (probe 2019-02-20 11:35)
    b1 = cl.build_bars(m1, HTF)
    b5 = cl.build_bars(m1, LTF)
    if len(b1) < 10 or len(b5) < 10:
        return _empty()
    ev = cisd_events(b5[OHLC], **CISD_KW)
    if ev.empty:
        return _empty()
    pos = b5.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    t = _ns(b5["close_time"])[pos]
    sgn = np.where(ev["direction"] == "bullish", 1, -1)
    entry = ev["confirm_close"].to_numpy(float)
    stop = ev["protected_swing"].to_numpy(float)
    st5, h5, l5 = _ns(b5.index), b5["high"].to_numpy(float), b5["low"].to_numpy(float)
    sw = swing_points(b1[OHLC], left=2, right=2)
    rows = []
    for d in (-1, 1):
        rst, rconf, A, T = _ranges(b1, sw, d)
        sel = np.flatnonzero(sgn == d)
        ks = np.searchsorted(rconf, t[sel], "right") - 1     # latest range confirmed by the decision
        for i, k in zip(sel, ks):
            if k < 0:
                continue
            a, tg, e, s = A[k], T[k], entry[i], stop[i]
            i0, i1 = np.searchsorted(st5, rst[k], "left"), pos[i] + 1
            if i1 <= i0:
                continue
            hi, lo = h5[i0:i1].max(), l5[i0:i1].min()
            if d < 0:
                if hi > a or lo <= tg or not (tg < e < s <= a):
                    continue
                frac = (e - tg) / (a - tg)
            else:
                if lo < a or hi >= tg or not (a <= s < e < tg):
                    continue
                frac = (tg - e) / (tg - a)
            rows.append((t[i], d, s, frac, int(rst[k]) * 2 + (d > 0)))
    if not rows:
        return _empty()
    r = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "frac", "dr_id"])
    r = r.sort_values(["t", "direction", "stop_px"], kind="stable").drop_duplicates(["t", "direction"])
    dt = pd.DatetimeIndex(pd.to_datetime(r["t"].to_numpy(), utc=True))
    out = pd.DataFrame({"decision_time": dt, "available_at": dt,
                        "direction": r["direction"].to_numpy(int), "stop_px": r["stop_px"].to_numpy(float),
                        "rr": RR, "frac": r["frac"].to_numpy(float), "dr_id": r["dr_id"].to_numpy("int64"),
                        "above_floor": r["frac"].to_numpy(float) > FLOOR})
    return out[COLS].reset_index(drop=True)


def _selfcheck():
    """Synthetic: a 1h rally from a swing low to a swing high, then a decline; frac must be measured from
    the target (the swing low) and the floor must split at 0.25."""
    a, tg = 110.0, 100.0
    for e, want in ((107.5, True), (102.5, False), (102.4, False), (105.0, True)):
        assert ((e - tg) / (a - tg) > FLOOR) == want, e


ROP = {"rules": [
    "dealing range on 1h bars (2/2 fractal swings): short = latest confirmed 1h swing high A (confirmed at close of "
    "A+2) and the 1h swing low that made it (last swing low before A); target T = lowest low from that swing low "
    "through A's bar. Long = mirror",
    "range live only if no complete 5m bar from A's bar through the entry bar trades beyond A or reaches T",
    "entry book: phase-3 locked 5m CISD (series_open, 2/2, max_wait 3) trading away from A; decide at the confirm "
    "bar close, enter next M1 open; stop = 5m protected swing; kept only if T < entry < stop <= A (mirror long)",
    "target 2R, exit at target/stop/50min; same-bar tie = stop",
    "frac = |T - entry| / |T - A| (0 at target, 1 at swing); gate above_floor: frac > 0.25 (complement = at or "
    "within the last 25% of the range toward the target); grey zone 25-50% and EQ sit in the gated arm",
    "control: matched random entries (same direction, stop distance, 2R, +-30 days), clock held within +-30 min NY "
    "time; CI clustered by dealing range"],
    "params": {"htf": HTF, "ltf": LTF, "swing": "2/2", "dealing_range": "anchor swing + origin swing (see rules)",
               "floor": FLOOR, "eq_tolerance": "EQ inside the gated arm", "entry": "CISD series_open, max_wait 3",
               "stop": "5m protected swing", "rr": RR, "max_hold": HOLD, "range_live": "anchor unbroken, target untaken",
               "mirror_long": True, "ctrl_tod_tol_min": TOD_TOL}}

SRC = {
    "htf": "corpus: yb3Te7tiGRk 'but on the hourly and 5 minute' (nested dealing ranges example); 1h = the HTF the range is marked on",
    "ltf": "corpus: yb3Te7tiGRk 'but on the hourly and 5 minute'; 5m = entry TF, stop on its protected high",
    "swing": "phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked 2/2 fractal swing)",
    "dealing_range": "corpus: yb3Te7tiGRk 'Then I'm going to find the swing low that made that swing high' + "
                     "'on the higher time frame candles, I'm going to go higher and find the swing high'",
    "floor": "corpus: yb3Te7tiGRk 'As I get to 25% of the range or lower, that is where I'm not really looking for shorts'",
    "eq_tolerance": "corpus: yb3Te7tiGRk 'It's okay if I'm entering right around that EQ point' -> EQ and the 25-50% grey "
                    "zone are not rejected (draft ambiguity: 'worse but not forbidden'); declared-before-run",
    "entry": "phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked CISD); source leaves entry open "
             "('I can take any sort of entry or retest in here')",
    "stop": "corpus: yb3Te7tiGRk 'Put my stop on that protected high'",
    "rr": "corpus: yb3Te7tiGRk 'I can get 2 R prior to my target'; draft measurable '2R hit rate of shorts by entry location'",
    "max_hold": "phase3: §1.13 10 entry-TF periods = 10 x 5m",
    "range_live": "corpus: yb3Te7tiGRk 'We just took out the target. It doesn't make sense.' -> declared-before-run: a range "
                  "whose target is taken or whose anchor is broken is no longer the range traded",
    "mirror_long": "corpus: yb3Te7tiGRk 'I want to be looking to long in a discount or below the EQ around it'; the 25% "
                   "number is stated for shorts only, long mirror inferred (draft)",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 / vault Session Timing on Gold - the concept is positional, not "
                        "timing, so the control holds the NY clock (+-30 min) to keep hour-of-day out of the gate diff",
}


if __name__ == "__main__":
    _selfcheck()
    ev = cl.cache_frame(f"{CID}_{READING}_dr1h_cisd5m", lambda: detect(cl.load_m1()))
    fr = ev["above_floor"].mean()
    print(len(ev), "gate rate", round(fr, 3), "frac q", ev["frac"].quantile([.1, .25, .5, .75, .9]).round(3).tolist())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "above_floor", mask_available_at="decision_time", max_hold=HOLD,
                       ctrl_tod_tol_min=TOD_TOL, cluster="dr_id")
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap", "dependence")})
    p = cl.write_result(CID, READING, res, operationalization=ROP, params_source=SRC, script=__file__, probe=probe,
                        notes=f"TTrades dealing-range video yb3Te7tiGRk, 25% rejection floor only (50% rule = prior "
                              f"reading, NULL, untouched). gate firing rate {fr:.3f} on {len(ev)} events.")
    print(p)
