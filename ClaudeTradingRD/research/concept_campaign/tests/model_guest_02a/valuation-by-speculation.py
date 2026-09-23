"""valuation-by-speculation (guests: Gene nncJGt6j19Q, Nick G44VpidBD_U, Jokerszn JABOO4LYNjQ).

Claim: the early-week (Monday into Tuesday) move away from the weekly opening price is
the FALSE move of the week; the week's real direction is the opposite, and Gene buys
into it at/below the weekly open (sells at/above it when bearish).

Operationalisation (trade_test, claim '+'):
  * weekly open = first M1 open in 00:00-00:05 NY on the Monday session (Gene: "midnight
    New York, not GMT").
  * at the close of the Tuesday session (17:00 NY daily bar close) take the sign of
    (Tuesday close - weekly open); the week-to-date move is the "speculation" leg.
  * trade AGAINST it: long if Tuesday closed below the weekly open (price is then
    below the open -> "buy at or below the opening price"), short if above.
  * stop = the week-to-date extreme made by the counter move (Mon+Tue low for a long,
    high for a short): the weekly higher-low / lower-high the concept says forms there.
  * no fixed target ("the weekly objective" is not defined in the unit); time exit at the
    Friday close = 3 sessions = 69h of trading time (hold_basis="bars").
  The weekly directional expectation and the no-news precondition cannot be supplied
  (the draw method is deferred to an absent part two; no calendar data), so every
  week with a Tuesday close away from the open is taken.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MIN_M1 = 600          # declared: a real session has ~1,380 M1 bars; drop stubs


def weekly_midnight_open(m1):
    loc = m1.index.tz_convert("America/New_York")
    sel = (loc.dayofweek == 0) & (loc.hour == 0) & (loc.minute < 5)
    sub = m1[sel]
    if sub.empty:
        return pd.Series(dtype=float), pd.Series(dtype="datetime64[ns, UTC]")
    key = sub.index.tz_convert("America/New_York").normalize().tz_localize(None)
    g = pd.DataFrame({"px": sub["open"].to_numpy(), "t": sub.index}, index=key)
    g = g.groupby(level=0).first()
    return g["px"], g["t"]           # indexed by the Monday calendar date (naive)


def detect(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_M1].copy()
    sd = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)   # session date
    d["sdate"] = sd
    d["dow"] = sd.dayofweek
    d["monday"] = sd - pd.to_timedelta(sd.dayofweek, unit="D")
    wo_px, wo_t = weekly_midnight_open(m1)
    rows = []
    for mon, g in d.groupby("monday"):
        if mon not in wo_px.index:
            continue
        gm = g[g["dow"] == 0]
        gt = g[g["dow"] == 1]
        if len(gm) != 1 or len(gt) != 1:
            continue
        wopen = float(wo_px.loc[mon])
        tclose = float(gt["close"].iloc[0])
        if tclose == wopen:
            continue
        direction = 1 if tclose < wopen else -1
        lo = float(min(gm["low"].iloc[0], gt["low"].iloc[0]))
        hi = float(max(gm["high"].iloc[0], gt["high"].iloc[0]))
        ct = pd.Timestamp(gt["close_time"].iloc[0])
        rows.append({"decision_time": ct, "available_at": ct, "direction": direction,
                     "stop_px": lo if direction == 1 else hi, "rr": np.nan,
                     "weekly_open": wopen})
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "weekly_open"]
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = pd.DatetimeIndex(out["available_at"]).tz_convert("UTC")
    return out.sort_values("decision_time").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("vbs_tue_close_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold="69h", hold_basis="bars")
    keys = ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
            "exposure_bars", "ties", "ctrl_overlap")
    for k in keys:
        print(k, res.get(k))
    op = {"rules": [
        "weekly open = first M1 open at 00:00-00:05 NY on Monday (session date)",
        "decide at the Tuesday session close (daily bar close_time, 17:00 NY)",
        "direction = against the week-to-date move: long if Tue close < weekly open, "
        "short if >",
        "stop = Mon+Tue session low (long) / high (short); no target",
        "exit at stop or after 69h of trading time (Wed+Thu+Fri sessions)",
        "no weekly-draw or news filter (not operationalisable from the unit / OHLC)"],
        "params": {"weekly_open": "Monday 00:00 NY", "decision": "Tuesday close",
                   "stop": "week-to-date extreme", "target": "none",
                   "max_hold": "69h", "hold_basis": "bars", "min_m1_per_session": MIN_M1}}
    src = {"weekly_open": "corpus: nncJGt6j19Q 'weekly opening price is measured at 00:00 "
                          "New York, not 00:00 GMT'",
           "decision": "corpus: nncJGt6j19Q 'typically Monday into Tuesday' (the false move "
                       "is complete by the Tuesday close)",
           "stop": "corpus: nncJGt6j19Q 'the weekly higher-low forms out of it' "
                   "(declared-before-run: its extreme is the stop)",
           "target": "declared-before-run: 'the weekly objective' is undefined in the unit; "
                     "time exit at the week's close",
           "max_hold": "declared-before-run: to the Friday close = 3 sessions x 23h",
           "hold_basis": "declared-before-run: trading-time hold so controls drawn across "
                         "weekends get the same exposure (README trap 7)",
           "min_m1_per_session": "declared-before-run: drop stub sessions (README trap 6)"}
    p = cl.write_result("valuation-by-speculation", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Unconditional reading: every week with a Tuesday close "
                              "away from the Monday-midnight open; the weekly bias and "
                              "no-news preconditions cannot be supplied.")
    print(p)
