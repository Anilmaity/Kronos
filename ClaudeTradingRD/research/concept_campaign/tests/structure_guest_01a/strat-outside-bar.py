"""strat-outside-bar (guest: Alex's Options, TheSTRAT / 'power of three') -> trade_test.

The guest's worked rule (weekly): "the weekly open is traded above, the high of the week is set
on Monday or Tuesday, structure shifts, and the trade is to target last week's low so that the
current weekly candle completes as an outside bar." Declared before the first run:
  * Weekly bars (week opens Sunday 18:00 NY). PWH/PWL = previous week's high/low.
  * First side: the week's running high first exceeds PWH (or running low first breaks PWL)
    during a Monday or Tuesday trading day, while the other side is still untaken.
  * Structure shift: the first 1h CISD (detectors.cisd, series_open level, max_wait=3,
    swings 2/2 - the phase-3 rung-0 detector) AGAINST the taken side, confirmed after the
    side was taken, within the same week, while the opposite side is still untaken.
    Decide at the CISD bar's close; harness enters next M1 open.
  * Target: the opposite side of the previous week (PWL for a short) - completes the outside bar.
  * Stop: the week's extreme so far at the decision (the high of the week for a short).
  * Deadline: the end of the current week (per-row max_hold = week close - decision).
  * One trade per week. claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "strat-outside-bar"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    w = cl.build_bars(m1, "1W")
    h = cl.build_bars(m1, "1h")
    if len(w) < 2 or len(h) < 10:
        return pd.DataFrame(columns=COLS)
    WH, WL = w["high"].to_numpy(float), w["low"].to_numpy(float)
    wct = pd.DatetimeIndex(w["close_time"]).tz_convert("UTC")
    mt = m1.index
    mt_ns = mt.tz_convert("UTC").as_unit("ns").asi8
    wpos = np.searchsorted(w.index.values, mt.values, side="right") - 1
    wposc = np.clip(wpos, 0, None)
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    g = pd.Series(wposc)
    cmax = pd.Series(mh).groupby(g).cummax().to_numpy()
    cmin = pd.Series(ml).groupby(g).cummin().to_numpy()
    pwh = np.where(wposc >= 1, WH[np.clip(wposc - 1, 0, None)], np.nan)
    pwl = np.where(wposc >= 1, WL[np.clip(wposc - 1, 0, None)], np.nan)
    valid = (wpos >= 1)
    wd = pd.DatetimeIndex(cl.trading_day(mt)).weekday           # 0 = Monday
    up_t = valid & (cmax > pwh)
    dn_t = valid & (cmin < pwl)
    # first-taken side per week (and its minute)
    first = {}
    for arr, side in ((up_t, 1), (dn_t, -1)):
        idx = np.flatnonzero(arr)
        if len(idx):
            s = pd.Series(idx).groupby(wposc[idx]).min()
            for r, i in s.items():
                first.setdefault(r, []).append((i, side))
    cis = cisd_events(h[["open", "high", "low", "close"]], level_rule="series_open",
                      left=2, right=2, max_wait=3, min_series=1)
    if cis.empty:
        return pd.DataFrame(columns=COLS)
    cct = pd.DatetimeIndex(h.loc[cis["confirm_time"], "close_time"]).tz_convert("UTC")
    cdir = np.where(cis["direction"].to_numpy() == "bullish", 1, -1)
    cct_ns = cct.as_unit("ns").asi8
    cstart_ns = pd.DatetimeIndex(cis["confirm_time"]).tz_convert("UTC").as_unit("ns").asi8
    rows = []
    done_weeks = set()
    order = np.argsort(cct_ns, kind="stable")
    for q in order:
        tq = cct_ns[q]
        k = np.searchsorted(mt_ns, tq - 60_000_000_000, side="right") - 1   # last M1 closed by tq
        if k < 0 or mt_ns[k] + 60_000_000_000 > tq:
            continue
        r = wposc[k]
        if not valid[k] or r in done_weeks or r not in first:
            continue
        ev_sides = sorted(first[r])
        i0, side = ev_sides[0]
        if len(ev_sides) > 1 and ev_sides[1][0] == i0:
            continue                                    # both sides in the same minute
        if wd[i0] not in (0, 1) or i0 > k:
            continue                                    # first side not taken on Mon/Tue, or not yet
        if cdir[q] != -side:
            continue
        # opposite side must still be untaken at the decision
        if side == 1 and cmin[k] < pwl[k]:
            continue
        if side == -1 and cmax[k] > pwh[k]:
            continue
        # the CISD bar must itself start after the side was taken
        if cstart_ns[q] < mt_ns[i0]:
            continue
        stop = cmax[k] if side == 1 else cmin[k]
        target = pwl[k] if side == 1 else pwh[k]
        hold = wct[r] - pd.Timestamp(tq, tz="UTC")
        if hold <= pd.Timedelta(0):
            continue
        done_weeks.add(r)
        rows.append((pd.Timestamp(tq, tz="UTC"), -side, stop, target, hold))
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "max_hold"])
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values("decision_time").reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame("strat_ob_week_cisd1h", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, hold_basis="bars")
    for k in ("n", "dropped", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "exit_mix"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "weekly bars (Sunday 18:00 NY open); PWH/PWL = previous week's high/low",
        "first side of the previous week taken on a Monday or Tuesday trading day, other side untaken",
        "structure shift = first 1h CISD (series_open, max_wait 3, swings 2/2) against the taken side, after the take, same week, other side still untaken",
        "short after a PWH take (long after PWL); target = opposite side of the previous week; stop = week's extreme so far",
        "hold until the week's close (per-row max_hold); one trade per week"],
        "params": {"htf": "1W", "shift_tf": "1h", "cisd_max_wait": 3, "take_days": "Mon/Tue",
                   "target": "opposite previous-week extreme", "stop": "week extreme so far",
                   "max_hold": "to week close", "hold_basis": "bars", "grid4h": "n/a"}}
    src = {"htf": "corpus: V8P6lNIisvc weekly worked example ('target last week's low so that the current weekly candle completes as an outside bar')",
           "shift_tf": "declared-before-run: 1h as the intraday execution chart for a weekly bar",
           "cisd_max_wait": "phase3: rung-0 CISD (series_open, max_wait 3, swings 2/2) as 'structure shifts'",
           "take_days": "corpus: V8P6lNIisvc 'the high of the week is set on Monday or Tuesday'",
           "target": "corpus: V8P6lNIisvc 'target last week's low' (completes the outside bar)",
           "stop": "declared-before-run: the week's high so far (the Monday/Tuesday high being protected)",
           "max_hold": "corpus: V8P6lNIisvc outside bar completes within the candle's own period (end of week)",
           "hold_basis": "declared-before-run: README trap 7 - first (clock) run had exposure real 3289 vs control 2522 bars (>10%); re-run on bars",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Re-run once with hold_basis='bars' per README trap 7 (clock run: exposure 30% apart; "
                              "clock verdict UNDERPOWERED, diff -0.113 [-0.345, +0.137]).")
    print(p)
