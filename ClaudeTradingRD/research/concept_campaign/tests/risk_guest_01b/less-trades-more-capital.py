"""less-trades-more-capital (guests: NickDoesFutures G44VpidBD_U, Gene nncJGt6j19Q).

Rule: cap trades at 0-3 per week; after two winning trades in a week, stop for the week.
Measurable named by the concept: 'expectancy of trades 1-3 in a week vs trades 4+'.

Operationalisation (gate_test, claim '+'): baseline = the phase-3 rung-0 1h bare CISD book
(every signal of a mechanical model). Walking each trading week in time order, a signal is
'taken' (gate True) if fewer than 3 signals have been taken that week and fewer than 2 of
the taken ones are already known winners (target hit before stop, by the decision time).
Everything else (the 4th+ signal, or anything after two wins) is the complement.
All parameters were fixed before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CAP, WIN_STOP = 3, 2                 # corpus G44VpidBD_U '0 to 3 trades a week', 2 winners
TF, MAX_WAIT, RR, HOLD = "1h", 3, 2.0, "10h"     # phase-3 locked rung-0 1h book


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAX_WAIT, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "taken"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR})
    out = out.sort_values("decision_time", kind="stable").reset_index(drop=True)
    # own resolution of each signal (only used for 'known winner by a later decision')
    o = m1["open"].to_numpy()
    i0 = m1.index.searchsorted(out["decision_time"], "left")
    ok = i0 < len(m1)
    entry = np.where(ok, o[np.clip(i0, 0, len(o) - 1)], np.nan)
    d = out["direction"].to_numpy()
    risk = (entry - out["stop_px"].to_numpy()) * d
    tgt = entry + d * RR * risk
    win_t = np.full(len(out), np.iinfo(np.int64).max, np.int64)
    for dd, up, dn in ((1, "above", "below"), (-1, "below", "above")):
        sel = np.flatnonzero(ok & (d == dd) & (risk > 0))
        if not len(sel):
            continue
        t = pd.DatetimeIndex(out["decision_time"].iloc[sel])
        tg = cl.touch(t, tgt[sel], up, horizon=pd.Timedelta(HOLD), m1=m1)
        st = cl.touch(t, out["stop_px"].to_numpy()[sel], dn, horizon=pd.Timedelta(HOLD), m1=m1)
        tt = pd.DatetimeIndex(tg["hit_time"])
        ss = pd.DatetimeIndex(st["hit_time"])
        win = tg["hit"].to_numpy() & (~st["hit"].to_numpy() | (tt < ss))
        known = (tt + pd.Timedelta(minutes=1)).asi8
        win_t[sel] = np.where(win, known, np.iinfo(np.int64).max)
    sd = cl.session_date(out["decision_time"])
    week = (sd - pd.to_timedelta(sd.dayofweek, unit="D")).to_numpy()
    dt = pd.DatetimeIndex(out["decision_time"]).asi8
    taken = np.zeros(len(out), bool)
    cur, tk = None, []
    for n in range(len(out)):
        if week[n] != cur:
            cur, tk = week[n], []
        wins = sum(1 for j in tk if win_t[j] <= dt[n])
        if len(tk) < CAP and wins < WIN_STOP:
            taken[n] = True
            tk.append(n)
    out["taken"] = taken
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"lesstrades_cisd1h_cap{CAP}_w{WIN_STOP}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "taken share", ev["taken"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "taken", mask_available_at="decision_time", max_hold=HOLD,
                       claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                   "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "baseline: 1h bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
        "confirming close, enter next M1 open, stop at protected swing, 2R, 10h",
        "week = trading week by session date (Mon-Fri, Sunday-evening open counts as Monday)",
        "in decision order per week: taken if < 3 taken so far and < 2 of the taken are "
        "known winners (own M1 resolution: 2R target before stop within 10h, target-hit "
        "close <= this decision)",
        "gate taken=True vs the rest (4th+ signals / after two wins)"],
        "params": {"cap": CAP, "win_stop": WIN_STOP, "tf": TF, "max_wait": MAX_WAIT,
                   "rr": RR, "max_hold": HOLD}}
    src = {"cap": "corpus: G44VpidBD_U '0 to 3 trades a week'",
           "win_stop": "corpus: t_talks_02 / G44VpidBD_U week ended after two winners",
           "tf": "phase3: rung-0 1h stack", "max_wait": "phase3: locked CISD config",
           "rr": "phase3: locked 2R target", "max_hold": "phase3: 10 entry-TF bars"}
    p = cl.write_result("less-trades-more-capital", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="The concept's mechanism is discretionary A+ selection, which a "
                              "mechanical book cannot reproduce; what is testable is its "
                              "measurable (trades 1-3 of a week vs 4+). The speakers frame the "
                              "number as personal, not an edge claim.")
    print("wrote", p)
