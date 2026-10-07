"""ic-cisd, update_20261007 (edu_01 + shorts_03): the NEW claims only, as readings u1007a / u1007b.

Prior readings a / b (4H forex grid / 15m IC-CISD, early-in-candle) are untouched; both NULL.

u1007a  edu_01 (cWDnzI3lpUk, RX8vtP3PLYk). "the go-to is always going to be an intra-candle change in the
        state of delivery" inside the DAILY + HOURLY fractal model. New relative to a/b: the D1/H1 pairing
        and the daily bias source, with no early-in-candle filter ("this is really working on any session
        all times of the day").
        Bias for trading day k (18:00 NY roll): day k-1 is a daily C2 or C3 closure (detectors.bias.
        daily_closures, C3 reference = C2 open) confirmed by a same-direction 1h CISD inside day k-1
        ("A candle two or a candle three closure with a change in the state of delivery"). IC-CISD = 1h
        phase-3 CISD (series_open, 2/2, max_wait 3, min_series 1) in the bias direction, POI gate passed,
        extreme bar and confirm bar both inside day k, extreme beyond day k's open on the wick side.
        Decide at the confirming 1h close, enter next M1 open, stop = protected swing, 2R
        ("Put my stop on the high ... and then look for 2R"). Every qualifying IC-CISD in the day.

u1007b  shorts_03 (Kv6Y8IA7jYs), full execution in candle 3 of the daily model. Bullish (mirror bearish):
        day k-1 is a bullish daily C2 closure ("here we have a candle to closure"); in day k, take the
        first 1h IC-CISD (as in u1007a) that
          - is the day's running low at the confirm close: it swept every earlier intraday low, so a
            consolidation-like earlier candidate has had its "another sweep";
          - is followed by an "aggressive move out": the threshold_fits displacement magnitude gate on the
            4 1h bars from the close-through (window range >= 1.5 x and travel beyond the CISD level
            >= 0.65 x the range of the 4 bars before it); grade known at the 4th bar's close;
          - keeps its low intact through that window, and the previous day high (the target) has not traded
            by then. An adverse run that is not a reversal off PDH does NOT cancel the bias; a run through
            PDH ends the day (the target is delivered).
        Then a buy limit priced for exactly 2R to PDH with the stop on the low: L = low + (PDH - low)/3,
        resting from the grade close until 17:00 NY of day k, cancelled if PDH trades first. No fill = no
        trade; one order per day. Fill emulated: decide at the close of the first M1 bar whose low <= L,
        enter next M1 open (harness entry rule), stop = the low, target = PDH.

Both: max hold 600 trading minutes (10 entry-TF bars, hold_basis "bars"), control holds the NY clock
(+/-30 min). Not tested: "prior to 9:30 I want to use the 15-minute candle" (see NOTES).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01a")
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402  (cisd_with_poi: same CISD + POI code as prior readings a/b)
import concept_lab as cl     # noqa: E402
from detectors.bias import daily_closures, hourly_cisd_in_candle   # noqa: E402

OHLC = ["open", "high", "low", "close"]
TF = "1h"
RR = 2.0
MAX_HOLD = "600min"
HOLD_BASIS = "bars"
CTRL_TOD = 30
MIN_DAY_M1 = 600
DISP_N, DISP_R, DISP_D = 4, 1.5, 0.65
NY = "America/New_York"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def _day_end(tday) -> pd.DatetimeIndex:
    """17:00 NY closing trading day `tday` (naive label of the 18:00 roll)."""
    loc = pd.DatetimeIndex(tday) + pd.Timedelta(days=1, hours=17)
    return loc.tz_localize(NY).tz_convert("UTC")


def _candidates(m1, kinds, confirm):
    """1h IC-CISD candidates in day k with day-k context. Returns (h, ev) or (h, None)."""
    h, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    if ev.empty:
        return h, None
    ev = ev[ev["poi_passed"].astype(bool)].reset_index(drop=True)
    d = cl.build_bars(m1, "1D")
    if ev.empty or len(d) < 4:
        return h, None
    cls = daily_closures(d[OHLC], c3_reference="c2_open")
    closure = cls["closure"].to_numpy()
    kind = cls["closure_kind"].to_numpy()
    full = (d["n_m1"] >= MIN_DAY_M1).to_numpy()
    tdays = pd.DatetimeIndex(d["trading_day"])
    q = tdays.get_indexer(cl.trading_day(pd.DatetimeIndex(ev["confirm_time"])))
    qe = tdays.get_indexer(cl.trading_day(pd.DatetimeIndex(ev["extreme_time"])))
    qq = np.where(q >= 3, q, 3)
    ok = (q >= 3) & (q == qe) & full[qq - 1] & full[qq - 2] & full[qq - 3]
    ok &= np.asarray((tdays[qq] - tdays[qq - 1]).days <= 4)
    bias = np.where(ok & np.isin(kind[qq - 1], kinds), closure[qq - 1], "none")
    if confirm:                                   # 1h CISD inside the bias day, same direction
        htd = cl.trading_day(h.index).asi8
        conf = {}
        for p in np.unique(qq[bias != "none"] - 1):
            a, z = np.searchsorted(htd, tdays[p].value, "left"), np.searchsorted(htd, tdays[p].value, "right")
            seg = h.iloc[a:z][OHLC]
            r = None
            if len(seg) >= 3:
                r = hourly_cisd_in_candle(seg, seg.index[0], seg.index[-1], closure[p], scope="range",
                                          level_rule="series_open", htf_open=float(d["open"].iloc[p]))
            conf[p] = r is not None
        bias = np.where([conf.get(p, False) for p in qq - 1], bias, "none")
    is_bull = ev["direction"].to_numpy() == "bullish"
    xp = ev["extreme_price"].to_numpy(float)
    dopen = d["open"].to_numpy(float)[qq]                       # day k's OPEN only (known at its start)
    wick = np.where(is_bull, xp < dopen, xp > dopen)
    sel = (bias == ev["direction"].to_numpy()) & wick
    ev = ev[sel].reset_index(drop=True)
    if ev.empty:
        return h, None
    ev["q"] = qq[sel]
    ev["tday"] = tdays[ev["q"].to_numpy()]
    ev["prev_high"] = d["high"].to_numpy(float)[ev["q"].to_numpy() - 1]
    ev["prev_low"] = d["low"].to_numpy(float)[ev["q"].to_numpy() - 1]
    return h, ev


def detect_a(m1):
    h, ev = _candidates(m1, ["C2", "C3"], confirm=True)
    if ev is None:
        return C.empty_frame(COLS_A)
    out = C.to_trade_frame(ev, RR)
    out = out.sort_values(["decision_time", "direction"], kind="stable")
    return out.drop_duplicates(["decision_time", "direction"]).reset_index(drop=True)[COLS_A]


def detect_b(m1):
    h, ev = _candidates(m1, ["C2"], confirm=False)
    if ev is None:
        return C.empty_frame(COLS_B)
    H, L, Cl = (h[k].to_numpy(float) for k in ("high", "low", "close"))
    htd = cl.trading_day(h.index).asi8
    grp = pd.Series(htd)
    run_lo = h["low"].groupby(grp.to_numpy()).cummin().to_numpy()
    run_hi = h["high"].groupby(grp.to_numpy()).cummax().to_numpy()
    hct = pd.DatetimeIndex(h["close_time"])
    n = len(h)
    rows = []
    for r in ev.itertuples(index=False):
        j = int(r.conf_pos)
        bull = r.direction == "bullish"
        g = j + DISP_N - 1
        if j < DISP_N or g >= n or htd[g] != r.tday.value:
            continue                                              # move-out window must sit in day k
        x = float(r.extreme_price)
        if not np.isclose(x, run_lo[j] if bull else run_hi[j]):
            continue                                              # not the day's wick: no second sweep
        pre = H[j - DISP_N:j].max() - L[j - DISP_N:j].min()
        wh, wl = H[j:g + 1].max(), L[j:g + 1].min()
        dist = (wh - r.level) if bull else (r.level - wl)
        if not (pre > 0 and (wh - wl) / pre >= DISP_R and dist / pre >= DISP_D):
            continue                                              # consolidation-like, not aggressive
        if (bull and wl < x) or (not bull and wh > x):
            continue                                              # protected swing taken in the window
        tgt = r.prev_high if bull else r.prev_low
        if (bull and run_hi[g] >= tgt) or (not bull and run_lo[g] <= tgt):
            continue                                              # PDH/PDL already delivered
        lim = x + (tgt - x) / 3.0
        rows.append((r.tday, hct[g], 1 if bull else -1, x, tgt, lim))
    if not rows:
        return C.empty_frame(COLS_B)
    o = pd.DataFrame(rows, columns=["tday", "t0", "direction", "stop_px", "target_px", "lim"])
    o = o.sort_values("t0", kind="stable").drop_duplicates("tday", keep="first").reset_index(drop=True)
    t0 = pd.DatetimeIndex(o["t0"])
    until = _day_end(pd.DatetimeIndex(o["tday"]))
    keep = np.asarray(t0 < until)
    o, t0, until = o[keep].reset_index(drop=True), t0[keep], until[keep]
    if o.empty:
        return C.empty_frame(COLS_B)
    nat = np.iinfo(np.int64).min
    fill_hit, tgt_hit = np.zeros(len(o), bool), np.zeros(len(o), bool)
    fill_ns, tgt_ns = np.full(len(o), nat, np.int64), np.full(len(o), nat, np.int64)
    for dsgn, fside, tside in ((1, "below", "above"), (-1, "above", "below")):
        s = (o["direction"] == dsgn).to_numpy()
        if not s.any():
            continue
        f = cl.touch(t0[s], o["lim"].to_numpy()[s], fside, until=until[s], m1=m1)
        t = cl.touch(t0[s], o["target_px"].to_numpy()[s], tside, until=until[s], m1=m1)
        fill_hit[s], tgt_hit[s] = f["hit"].to_numpy(), t["hit"].to_numpy()
        fill_ns[s] = pd.DatetimeIndex(f["hit_time"]).as_unit("ns").asi8
        tgt_ns[s] = pd.DatetimeIndex(t["hit_time"]).as_unit("ns").asi8
    ft, tt = pd.to_datetime(fill_ns, utc=True), pd.to_datetime(tgt_ns, utc=True)
    filled = fill_hit & (~tgt_hit | np.asarray(ft < tt))           # same-bar fill+target: no fill
    o = o[filled].reset_index(drop=True)
    dec = ft[filled] + pd.Timedelta(minutes=1)                   # the fill bar's close
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": o["direction"].to_numpy(),
                         "stop_px": o["stop_px"].to_numpy(float),
                         "target_px": o["target_px"].to_numpy(float)})[COLS_B]


SRC_COMMON = {
    "pairing": "corpus: cWDnzI3lpUk 'use the daily and hourly fractal model for an entry' / 'the go-to is "
               "always going to be an intra-candle change'",
    "cisd": "phase3: §1.8 series_open, 2/2, max_wait 3, min_series 1; POI gate per ic-cisd.yaml (same "
            "cisd_with_poi code as prior readings a/b)",
    "wick_side": "corpus: RX8vtP3PLYk 'we let the wick form. Now, we're trying to trade the body' => IC-CISD "
                 "extreme beyond day k's open",
    "day_open": "session_window_fit: NY trading day rolling 18:00 (settled)",
    "stub_filter_min_m1": "declared-before-run: README trap 6, bias source days need >= 600 M1",
    "max_hold": "phase3: §1.13 10 entry-TF bars (600 trading minutes on 1h)",
    "hold_basis": "declared-before-run: README trap 7, the 10-bar hold is trading time; late-day 1h entries "
                  "cross the 17:00 NY halt and the weekend",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 / campaign lesson 3, the concept is not about "
                        "timing but 1h decisions and limit fills cluster on the NY clock",
    "grid4h": "declared-before-run: n/a, no 4H bars read (1D 18:00 NY + 1h only)",
}
SRC_A = dict(SRC_COMMON, **{
    "bias": "corpus: cWDnzI3lpUk 'A candle two or a candle three closure with a change in the state of "
            "delivery'; detectors.bias.daily_closures + hourly_cisd_in_candle (scope range)",
    "c3_reference": "phase3: locked primary C3 reference (Reading A, C2 opening price)",
    "early": "corpus: cWDnzI3lpUk 'this is really working on any session all times of the day' => no "
             "early-in-candle filter",
    "rr": "corpus: cWDnzI3lpUk 'Put my stop on the high or the body and then look for 2R'",
    "per_day": "corpus: ic-cisd.yaml 'New continuations forming later inside the same candle are additional "
               "valid entries' => every qualifying IC-CISD",
})
SRC_B = dict(SRC_COMMON, **{
    "bias": "corpus: Kv6Y8IA7jYs 'here we have a candle to closure' => day k-1 daily C2 closure "
            "(detectors.fractal.c2_events via daily_closures), day k = candle 3",
    "bias_survival": "corpus: Kv6Y8IA7jYs 'I wouldn't invalidate my bias because it's not a reversal off of "
                     "previous' => no adverse-run invalidation; a trade through PDH ends the day",
    "second_sweep": "corpus: Kv6Y8IA7jYs 'Really hard to trust this level here. So, I'd need another sweep.' "
                    "=> the accepted IC-CISD extreme is the day's running extreme at its confirm close",
    "aggressive": "threshold_fits: displacement == aggressive; magnitude gate N=4, r=1.5, d=0.65 from the "
                  "close-through, reference = the CISD level (component a = the close-through itself)",
    "entry": "corpus: Kv6Y8IA7jYs 'putting my stop on the low and being able to get 2R to that high' + "
             "'retest entry' => limit L = low + (PDH - low)/3",
    "order_life": "declared-before-run: the limit rests until 17:00 NY of candle 3 (the daily candle being "
                  "traded); cancelled if PDH trades first (no 2R left to that high)",
    "no_fill": "corpus: Kv6Y8IA7jYs 'we'll see if we get tagged in, and if not, we don't.'",
    "per_day": "corpus: Kv6Y8IA7jYs one setup per candle 3 => one order per day",
    "target": "corpus: Kv6Y8IA7jYs 'What is my target? That daily high there.' => PDH (= candle 2 high)",
    "exec_tf": "corpus: cWDnzI3lpUk daily + hourly model (the Short names no execution TF)",
})
OP_COMMON = [
    "NY trading day (18:00 roll); bias-source day and the two before it need >= 600 M1; day k-1 must be "
    "the previous session (<= 4 calendar days)",
    "1h CISD (series_open, 2/2, mw3, ms1) with POI gate, in the bias direction, extreme bar and confirm "
    "bar inside day k, extreme beyond day k's open (wick side)",
]
OP_A = OP_COMMON[:1] + [
    "bias for day k: day k-1 is a daily C2 or C3 (C2-open ref) closure AND a same-direction 1h CISD "
    "inside day k-1"] + OP_COMMON[1:] + [
    "every qualifying IC-CISD; decide at the confirm close; next M1 open; stop protected swing; 2R; "
    "600 trading minutes; control NY clock +/-30 min"]
OP_B = OP_COMMON[:1] + [
    "bias for day k: day k-1 is a daily C2 closure (no further confirmation)"] + OP_COMMON[1:] + [
    "IC-CISD extreme = day k's running extreme at the confirm close (second sweep of any earlier "
    "candidate)",
    "aggressive move out: 4 1h bars from the close-through, range >= 1.5x and travel beyond the CISD "
    "level >= 0.65x the prior 4-bar range; extreme intact and PDH (PDL) untraded through the 4th bar",
    "first such setup per day: limit at low + (PDH - low)/3 (2R to PDH), live from the 4th bar's close "
    "to 17:00 NY, cancelled if PDH trades first; no fill = no trade",
    "fill emulated: decide at the close of the first M1 bar reaching L; next M1 open; stop = the low; "
    "target = PDH; 600 trading minutes; control NY clock +/-30 min"]
PARAMS_COMMON = {"pairing": "1D/1h", "cisd": "phase3+poi", "wick_side": True, "day_open": "18:00 NY",
                 "stub_filter_min_m1": MIN_DAY_M1, "max_hold": MAX_HOLD, "hold_basis": HOLD_BASIS,
                 "ctrl_tod_tol_min": CTRL_TOD, "grid4h": "n/a"}
PARAMS_A = dict(PARAMS_COMMON, bias="C2|C3 + 1h CISD", c3_reference="c2_open", early=None, rr=RR,
                per_day="all")
PARAMS_B = dict(PARAMS_COMMON, bias="C2", bias_survival="PDH-only", second_sweep="day running extreme",
                aggressive=f"N={DISP_N} r={DISP_R} d={DISP_D}", entry="limit 2R to PDH",
                order_life="to 17:00 NY, cancel on PDH", no_fill="no trade", per_day=1,
                target="PDH/PDL", exec_tf="1h")
NOTES = ("New claims only; prior readings a/b (4H/15m) untouched. NOT tested: 'prior to 9:30, I want to use "
         "the 15-minute candle' (RX8vtP3PLYk). It is said in passing inside an hourly/5-minute indices "
         "example; the draft itself flags whether 15m replaces the HTF candle or the confirmation TF as "
         "undecided, and the corpus's own session-open-volume-nyse maps 9:30 to the NYSE open (forex uses "
         "8:30), so moving it to gold would need an invented parameter. 'Stated origin' (created to "
         "mechanise let-the-wick-form) is not a testable claim. Neighbour, not a repeat: phase-3's 1H swing "
         "stack (1h CISD / 1D / 1W bias) was underpowered at R4 (n=103).")


def show(res):
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap", "dropped", "halves"):
        print(" ", k, res.get(k))


if __name__ == "__main__":
    which = sys.argv[1:] or ["u1007a", "u1007b"]
    kw = dict(max_hold=MAX_HOLD, hold_basis=HOLD_BASIS, ctrl_tod_tol_min=CTRL_TOD)
    for reading in which:
        if reading == "u1007a":
            det, key, op, prm, src = detect_a, "u1007_iccisd_d1h1_a", OP_A, PARAMS_A, SRC_A
        else:
            det, key, op, prm, src = detect_b, "u1007_iccisd_d1h1_b", OP_B, PARAMS_B, SRC_B
        ev = cl.cache_frame(key, lambda: det(cl.load_m1()))
        print(reading, "events", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, **kw)
        show(res)
        p = cl.write_result("ic-cisd", reading, res, operationalization={"rules": op, "params": prm},
                            params_source=src, script=__file__, notes=NOTES, probe=probe)
        print("wrote", p)
