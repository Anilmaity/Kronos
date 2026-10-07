"""intraday-reversal -- update u1007 (two new claims; the library rate reading is untouched).

The library reading (model_own_04b, rate_test) asked whether a 4H C2 + inside-hourly-CISD day
extreme HOLDS for the day. These two readings test only the NEW claim: the TRADE taken off a
confirmed day extreme -- drop to the 15m, enter on a protected swing, stop beyond it, 2R.

u1007a  live_13 (wa9m30UHrm0, New York Open Live Q&A), confirmations as ALTERNATIVES:
  "How do you confirm the high of the day? ... You use either an hourly change in the state
   delivery ... We close through the series of [up] closed candles that made that high ... Or
   you can use a 4-hour candle closure. 4-hour candle closure, candle three closure, ideal
   candle three closure ... Use a 4-hour 15-minute model ... Protected swing right there. So,
   then you can enter on a protected swing. And then you look for this to either hit 2R".
  Confirmation (either suffices; the earliest one per day-extreme is used):
    A  1H CISD (phase-3 detector: series_open, 2/2 swings, max_wait 3) whose extreme is the NY
       trading day's running extreme (18:00 roll) at the confirming 1H close, same day;
    B  forex-grid 4H C2 closure (spec 3.2) or C3 closure (spec 3.3 reading A) whose swept
       extreme is the trading day's running extreme at the 4H close.
  Entry: the FIRST 15m CISD (same detector) in the reversal direction confirmed after the
  confirmation and within 240 min (one 4H candle: the 4H/15m model trades the next 4H candle),
  same trading day, with the day extreme not traded through by its close (library
  invalidation). Decide at that 15m close, next M1 open; stop = its protected swing; 2R.

u1007b  edu_03 (BgVkJf0kMo4, How to Trade Asia Using TTrades Fractal Model), ORDERED:
  "if I have the hourly confirmation, I'm going to want to wait for a 4-hour candle closure.
   On this 4-hour candle closure, I have now confirmed a candle two closure ... We have a new
   continuation that has formed prior to the open of this new higher time frame candle. So, we
   have that reversal. We have a new continuation. That means we can enter. So, our stop on
   that new continuation's low and then look for 2R".
  Forex-grid 4H C2 (one-sided) whose extreme is the trading day's running extreme; a 1H CISD
  inside it at that extreme, confirmed before the 4H close (model_own_04b construct); the most
  recent 15m CISD in the C2 direction confirmed inside C2 whose swing is AFTER the 15m bar of
  the C2 extreme (the new continuation, not the reversal itself), intact through the C2 close
  and beyond the C2 close. Decide at the C2 close, enter at the C3 open, stop on that swing, 2R.

Both: hold to the end of the NY trading day (17:00 NY): "from 6:00 a.m. and on, you expect this
high to be in" and, overnight, "I'm either going to get stopped out or it's going to hit TP".
Not modelled: SMT (live_13: "a little SMT" = supportive; edu_03: required only on an undefined
"reversal day"), and the correlated-asset (YM) exit -- no NQ/YM data; the silver analogue is
cross-asset-target-transfer. Controls hold the NY clock (+/-30 min, README trap 9); u1007b draws
on the 4H close grid (decisions only at 4H closes). Cost cancels in the differential, so the
median stop in points and the R a 0.30 pt spread costs are written to notes (campaign lesson 2).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model_own_04b"))
import concept_lab as cl                                        # noqa: E402
from detectors.cisd import cisd_events                          # noqa: E402
from _helpers import c2_flags, c3_flags, cisd_in_candle         # noqa: E402

CID = "intraday-reversal"
RR = 2.0
WIN = pd.Timedelta(minutes=240)
CTRL_TOD = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
ONE = pd.Timedelta(minutes=1)


def _ohlc(b):
    return [b[k].to_numpy(float) for k in ("open", "high", "low", "close")]


def _running(b):
    """Trading day of each bar (by its first M1) and the day's running high/low through it."""
    td = cl.trading_day(pd.DatetimeIndex(b["first_m1"])).to_numpy()
    g = pd.DataFrame({"td": td, "h": b["high"].to_numpy(float), "l": b["low"].to_numpy(float)})
    return td, g.groupby("td")["h"].cummax().to_numpy(), g.groupby("td")["l"].cummin().to_numpy()


def _cisd(b):
    """Phase-3 bare CISD: confirm-bar pos, extreme-bar pos, direction, protected swing."""
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty:
        z = np.zeros(0, int)
        return z, z, z, np.zeros(0)
    p = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    e = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    d = np.where(ev["direction"].to_numpy() == "bullish", 1, -1)
    return p, e, d, ev["protected_swing"].to_numpy(float)


def _frame(rows):
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    t = pd.DatetimeIndex([r[0] for r in rows])
    td = pd.DatetimeIndex([r[3] for r in rows])
    day_end = (td + pd.Timedelta(hours=41)).tz_localize("America/New_York").tz_convert("UTC")
    ev = pd.DataFrame({"decision_time": t, "available_at": t,
                       "direction": np.array([r[1] for r in rows], int),
                       "stop_px": np.array([r[2] for r in rows], float), "rr": RR,
                       "max_hold": day_end - t})
    ev = ev[ev["max_hold"] > pd.Timedelta(0)]
    ev = ev.sort_values(["decision_time", "direction"], kind="stable")
    return ev.drop_duplicates(["decision_time", "direction"]).reset_index(drop=True)


def detect_a(m1):
    b1, b4, b15 = (cl.build_bars(m1, "1h"), cl.build_bars(m1, "4h", grid4h="forex"),
                   cl.build_bars(m1, "15min"))
    if min(len(b1), len(b4), len(b15)) < 5:
        return _frame([])
    last = pd.DatetimeIndex(m1.index)[-1] + ONE
    td1, rmax1, rmin1 = _running(b1)
    ct1 = pd.DatetimeIndex(b1["close_time"])
    conf = []                                    # (time, dir, extreme, trading day)
    p, e, d, x = _cisd(b1)                       # A: hourly CISD at the day extreme
    for k in range(len(p)):
        j = p[k]
        if ct1[j] > last or td1[e[k]] != td1[j]:
            continue
        if x[k] == (rmin1[j] if d[k] > 0 else rmax1[j]):
            conf.append((ct1[j], int(d[k]), float(x[k]), td1[j]))
    o4, h4, l4, c4 = _ohlc(b4)                   # B: 4H C2 / C3 closure at the day extreme
    c2 = c2_flags(o4, h4, l4, c4)
    c3 = c3_flags(o4, h4, l4, c4, c2)
    ct4 = pd.DatetimeIndex(b4["close_time"])
    td4 = cl.trading_day(pd.DatetimeIndex(b4["first_m1"])).to_numpy()
    q = ct1.searchsorted(ct4, side="right") - 1  # last 1H bar closed by the 4H close
    for i in range(1, len(b4)):
        if ct4[i] > last or q[i] < 0 or td1[q[i]] != td4[i]:
            continue
        for dd, xx in ((c2[i], l4[i] if c2[i] > 0 else h4[i]),
                       (c3[i], min(l4[i - 1], l4[i]) if c3[i] > 0 else max(h4[i - 1], h4[i]))):
            if dd != 0 and xx == (rmin1[q[i]] if dd > 0 else rmax1[q[i]]):
                conf.append((ct4[i], int(dd), float(xx), td4[i]))
    conf.sort(key=lambda r: (r[0], r[1]))
    seen, first = set(), []
    for r in conf:                               # either suffices: earliest per day extreme
        if (r[3], r[1], r[2]) not in seen:
            seen.add((r[3], r[1], r[2]))
            first.append(r)
    td15, rmax15, rmin15 = _running(b15)
    ct15 = pd.DatetimeIndex(b15["close_time"])
    p15, _, d15, ps15 = _cisd(b15)
    rows = []
    for dd in (1, -1):
        sel = np.flatnonzero(d15 == dd)
        dt = ct15[p15[sel]]
        for t, _, xx, td in (r for r in first if r[1] == dd):
            k = dt.searchsorted(t, side="right")        # first 15m CISD strictly after
            if k >= len(sel) or dt[k] > t + WIN:
                continue
            j = p15[sel[k]]
            if ct15[j] > last or td15[j] != td:
                continue
            if (rmin15[j] if dd > 0 else rmax15[j]) != xx:   # extreme traded through: void
                continue
            rows.append((ct15[j], dd, ps15[sel[k]], td))
    return _frame(rows)


def detect_b(m1):
    b1, b4, b15 = (cl.build_bars(m1, "1h"), cl.build_bars(m1, "4h", grid4h="forex"),
                   cl.build_bars(m1, "15min"))
    if min(len(b1), len(b4), len(b15)) < 5:
        return _frame([])
    last = pd.DatetimeIndex(m1.index)[-1] + ONE
    o4, h4, l4, c4 = _ohlc(b4)
    o1, h1, l1, c1 = _ohlc(b1)
    _, h15, l15, _ = _ohlc(b15)
    c2 = c2_flags(o4, h4, l4, c4)
    td4, rmax4, rmin4 = _running(b4)
    st4, ct4 = pd.DatetimeIndex(b4.index), pd.DatetimeIndex(b4["close_time"])
    i1 = pd.DatetimeIndex(b1.index)
    a1, z1 = i1.searchsorted(st4), i1.searchsorted(ct4)
    i15 = pd.DatetimeIndex(b15.index)
    a15, z15 = i15.searchsorted(st4), i15.searchsorted(ct4)
    p15, e15, d15, ps15 = _cisd(b15)             # sorted by confirm bar
    rows = []
    for i in np.flatnonzero(c2 != 0):
        bull = c2[i] > 0
        if ct4[i] > last or (l4[i] != rmin4[i] if bull else h4[i] != rmax4[i]):
            continue
        if cisd_in_candle(o1, h1, l1, c1, a1[i], z1[i], bull)[0] < 0:
            continue
        s, z = a15[i], z15[i]
        if z - s < 3:
            continue
        ex = s + int(np.argmin(l15[s:z]) if bull else np.argmax(h15[s:z]))
        lo, hi = np.searchsorted(p15, s), np.searchsorted(p15, z)
        cand = [k for k in range(lo, hi) if d15[k] == c2[i] and e15[k] > ex]
        if not cand:
            continue
        k = cand[-1]
        sw = ps15[k]
        if bull and (l15[e15[k]:z].min() < sw or sw >= c4[i]):
            continue
        if (not bull) and (h15[e15[k]:z].max() > sw or sw <= c4[i]):
            continue
        rows.append((ct4[i], int(c2[i]), sw, td4[i]))
    return _frame(rows)


SRC_COMMON = {
    "rr": "corpus: wa9m30UHrm0 'And then you look for this to either hit 2R'; BgVkJf0kMo4 "
          "'our stop on that new continuation's low and then look for 2R'",
    "stop": "corpus: wa9m30UHrm0 'So, then you can enter on a protected swing.' (draft execution.stop "
            "'Beyond the protected swing.')",
    "entry_tf": "corpus: wa9m30UHrm0 'Use a 4-hour 15-minute model.'",
    "cisd_detector": "phase3: detectors.cisd series_open (method_spec 4.2 default), 2/2 swings, "
                     "max_wait 3 -- the bare-CISD rung-0 detector, on 1h and 15min",
    "day_extreme": "corpus: wa9m30UHrm0 'How do you confirm the high of the day?'; library "
                   "intraday-reversal.yaml 'That extreme is then treated as the low of the day'",
    "max_hold": "corpus: wa9m30UHrm0 'So, then from 6:00 a.m. and on, you expect this high to be' "
                "[in]; BgVkJf0kMo4 'either going to get stopped out or it's going to hit TP' -> hold "
                "to the end of the NY trading day (17:00 NY), per-row wall clock, no halt inside",
    "grid4h": "method_spec: forex 4H grid 17/21/01/05/09/13 NY (README trap 8 default; vault: the "
              "grid is a knob, recorded here)",
    "day_open_hour": "session_window_fit: 18:00 NY daily candle (settled)",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 / vault Concept Campaign lesson 3 -- not a "
                        "timing concept but events cluster at 4H/1H closes and in session hours, so the "
                        "control holds the NY clock +/-30 min (also keeps the rest-of-day hold comparable)",
    "smt": "declared-before-run: not required -- wa9m30UHrm0 'We have a little SMT on this previous "
           "high' is supportive; BgVkJf0kMo4 needs it only on a 'reversal day', which is not defined",
    "correlated_target": "declared-before-run: the YM-target exit needs NQ/YM; 2R only (silver analogue "
                         "tested as cross-asset-target-transfer)",
}
SRC_A = dict(SRC_COMMON, **{
    "either_or": "corpus: wa9m30UHrm0 'You use either an hourly change in the state delivery' / "
                 "'Or you can use a 4-hour candle closure.' -> earliest of A or B per day extreme",
    "confirm_1h": "corpus: wa9m30UHrm0 'Hourly change in the state delivery. We have a consolidation.' "
                  "-> 1H CISD whose extreme is the day's running extreme",
    "confirm_4h": "corpus: wa9m30UHrm0 'candle three closure, ideal candle three closure' -> C3 (spec 3.3 "
                  "reading A) preferred but not required: C2 (spec 3.2) also counts",
    "entry_window": "declared-before-run: 240 min = one 4H candle (the 4H/15m model trades the next 4H "
                    "candle on the 15m); one value, not searched",
    "entry_rule": "declared-before-run: the FIRST 15m CISD in the reversal direction after the "
                  "confirmation ('Protected swing right there.'), same trading day",
    "invalidation": "corpus: library intraday-reversal.yaml 'The declared low of the day is traded "
                    "through.' -> void if the day extreme is exceeded before the 15m close",
})
SRC_B = dict(SRC_COMMON, **{
    "ordering": "corpus: BgVkJf0kMo4 'I'm going to want to wait for a 4-hour candle closure' (after "
                "the hourly confirmation) -> 1H CISD confirmed inside C2 before its close",
    "c2": "corpus: BgVkJf0kMo4 'On this 4-hour candle closure, I have now confirmed a candle two "
          "closure.' (method_spec 3.2, one-sided)",
    "confirm_1h": "phase3/model_own_04b: _helpers.cisd_in_candle (C2 extreme, opposing 1H series, "
                  "close through the series' first open before the 4H close)",
    "continuation": "corpus: BgVkJf0kMo4 'formed prior to the open of this new higher time frame "
                    "candle'; 'So, we have that reversal. We have a new continuation.' -> most "
                    "recent 15m CISD inside C2 with its swing after the C2-extreme 15m bar, intact "
                    "and beyond the C2 close",
    "entry": "corpus: BgVkJf0kMo4 'That means we can enter.' -> decide at the C2 close, enter C3 open",
    "ctrl_grid": "declared-before-run: decisions occur only at 4H closes, so controls are drawn on "
                 "the 4H forex close grid (positional-entry u1007a precedent)",
})


def _spread_note(ev):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    risk = np.abs(px - ev["stop_px"].to_numpy(float))
    med = float(np.median(risk))
    return med, (f"median stop {med:.2f} pt (p25 {np.percentile(risk, 25):.2f}, p75 "
                 f"{np.percentile(risk, 75):.2f}); a 0.30 pt spread costs ~{0.30 / med:.2f}R at the "
                 f"median stop (cost cancels in diff; vault Concept Campaign lesson 2)")


def run(reading, detect, key, ctrl_grid, rules, params, src, note):
    ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
    print(reading, "events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, ctrl_grid=ctrl_grid, ctrl_tod_tol_min=CTRL_TOD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "halves"):
        print(" ", k, res.get(k))
    med, sn = _spread_note(ev)
    print(" ", sn)
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=note + " " + sn)
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["u1007a", "u1007b"]
    if "u1007a" in which:
        run("u1007a", detect_a, "u1007_ir_either_15m_ps", "auto", [
            "confirmation A: 1H CISD (series_open, 2/2, max_wait 3) whose extreme is the NY trading "
            "day's running extreme (18:00 roll) at the confirming 1H close",
            "confirmation B: forex-grid 4H C2 (spec 3.2) or C3 (spec 3.3 reading A) closure whose swept "
            "extreme is the day's running extreme at the 4H close",
            "either suffices: the earliest confirmation per (day, direction, extreme)",
            "entry: first 15m CISD (same detector) in the reversal direction confirmed after the "
            "confirmation, within 240 min, same trading day, day extreme not traded through by its close",
            "decide at the 15m close, next M1 open; stop = 15m protected swing; 2R; exit at 17:00 NY "
            "(end of the trading day)"],
            {"either_or": "earliest of A/B per day extreme", "confirm_1h": "1h CISD at day extreme",
             "confirm_4h": "4h C2 or C3 at day extreme", "cisd_detector": "series_open,2/2,max_wait3",
             "day_extreme": "running NY-day extreme", "entry_tf": "15min", "entry_window": "240min",
             "entry_rule": "first 15m CISD after confirmation", "invalidation": "day extreme intact",
             "stop": "15m protected swing", "rr": RR, "max_hold": "to 17:00 NY day end",
             "grid4h": "forex", "day_open_hour": 18, "smt": "not required",
             "correlated_target": "not modelled", "ctrl_tod_tol_min": CTRL_TOD},
            SRC_A, "live_13 (wa9m30UHrm0): either-or confirmation, then 15m protected-swing entry, 2R. "
                   "Library rate reading (4H C2 + 1H CISD extreme holds) untouched.")
    if "u1007b" in which:
        run("u1007b", detect_b, "u1007_ir_ordered_c2_15m_cont", "4h", [
            "forex-grid 4H C2 (spec 3.2, one-sided) whose extreme is the NY trading day's running "
            "extreme (18:00 roll)",
            "a 1H CISD inside C2 at its extreme, confirmed before the 4H close (hourly first, then the "
            "4H closure)",
            "15m continuation: most recent 15m CISD (series_open, 2/2, max_wait 3) in the C2 direction "
            "confirmed inside C2, swing after the C2-extreme 15m bar, intact through and beyond the C2 close",
            "decide at the C2 close, enter at the C3 open (next M1 open); stop on that 15m swing; 2R; "
            "exit at 17:00 NY (end of the trading day; C2s closing at 17:00 have no session left)"],
            {"c2": "4h forex one-sided", "ordering": "1h CISD before 4H close",
             "confirm_1h": "cisd_in_candle series_open", "day_extreme": "running NY-day extreme",
             "cisd_detector": "series_open,2/2,max_wait3", "entry_tf": "15min",
             "continuation": "swing after C2 extreme, intact, beyond C2 close",
             "entry": "C3 open", "stop": "15m continuation swing", "rr": RR,
             "max_hold": "to 17:00 NY day end", "grid4h": "forex", "day_open_hour": 18,
             "smt": "not required", "correlated_target": "not modelled", "ctrl_grid": "4h",
             "ctrl_tod_tol_min": CTRL_TOD},
            SRC_B, "edu_03 (BgVkJf0kMo4): ordered hourly CISD -> 4H C2 closure -> 15m continuation "
                   "before the next 4H open, enter, 2R. Subset of positional-entry__a's book (4H C2 + "
                   "15m CISD, C3-open entry, 2R) plus the 1H-CISD and day-extreme gates.")
