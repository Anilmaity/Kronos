"""thursday-counter-week — Thursday Counter weekly profile (TTrades own voice).

Reading a (Friday branch, the default in `execution.entry`):
  Tue and Wed are expansion days away from the weekly open with no internal
  counter-swing; Thursday prints a daily C2 counter (sweeps Wed's extreme, closes
  back inside) confirmed by an hourly CISD inside Thursday; trade Friday back
  toward the weekly open, stop beyond Thursday's extreme.
Reading b (Thursday-intraday branch, "continuation inside the reversal day"):
  same Mon-Wed run; on Thursday, once Wednesday's extreme has been swept, enter at
  the close of the first hourly CISD against the run; stop beyond Thursday's
  extreme so far; target the weekly open; hold through Friday's close.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.bias import hourly_cisd_in_candle

CID = "thursday-counter-week"
HOLD_A = "23h"          # Friday session: Thu 18:00 NY -> Fri 17:00 NY


def _days(m1):
    d = cl.build_bars(m1, "1D")
    d = d.copy()
    d["sdate"] = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)
    d["dow"] = pd.DatetimeIndex(d["sdate"]).dayofweek
    d["week"] = pd.DatetimeIndex(d["sdate"]) - pd.to_timedelta(d["dow"], unit="D")
    return d


def _weeks(d):
    """Yield (week, rows dict by dow) for weeks with Mon..Thu present."""
    for wk, g in d.groupby("week", sort=True):
        byd = {int(r.dow): (idx, r) for idx, r in g.iterrows()}
        if not all(k in byd for k in (0, 1, 2, 3)):
            continue
        yield wk, byd


def _run_dir(byd):
    """+1 = bullish run (Tue & Wed expand up, ascending lows, Wed close > weekly open),
    -1 = bearish mirror, 0 = none."""
    mon, tue, wed = byd[0][1], byd[1][1], byd[2][1]
    wo = mon.open
    up = all(x.close > x.open and x.high > p.high and x.low > p.low
             for p, x in ((mon, tue), (tue, wed))) and wed.close > wo
    dn = all(x.close < x.open and x.low < p.low and x.high < p.high
             for p, x in ((mon, tue), (tue, wed))) and wed.close < wo
    return 1 if up and not dn else (-1 if dn and not up else 0)


def detect_a(m1):
    d = _days(m1)
    h = cl.build_bars(m1, "1h")
    rows = []
    for wk, byd in _weeks(d):
        run = _run_dir(byd)
        if run == 0:
            continue
        mon, wed = byd[0][1], byd[2][1]
        tidx, thu = byd[3]
        if thu.n_m1 < 600:
            continue
        if run == 1:   # bearish counter: sweep Wed high, close back below it
            c2 = thu.high > wed.high and thu.close < wed.high
            cdir, stop = "bearish", thu.high
        else:
            c2 = thu.low < wed.low and thu.close > wed.low
            cdir, stop = "bullish", thu.low
        if not c2:
            continue
        seg_end = pd.Timestamp(thu.close_time) - pd.Timedelta(hours=1)
        cis = hourly_cisd_in_candle(h[["open", "high", "low", "close"]], tidx, seg_end,
                                    cdir, scope="range", level_rule="series_open")
        if cis is None:
            continue
        wo = mon.open
        # target must still lie ahead of Thursday's close
        if (run == 1 and not wo < thu.close) or (run == -1 and not wo > thu.close):
            continue
        rows.append({"decision_time": pd.Timestamp(thu.close_time),
                     "available_at": pd.Timestamp(thu.close_time),
                     "direction": -run, "stop_px": float(stop),
                     "target_px": float(wo)})
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    return pd.DataFrame(rows, columns=cols)


def detect_b(m1):
    d = _days(m1)
    h = cl.build_bars(m1, "1h")[["open", "high", "low", "close", "close_time"]]
    rows = []
    for wk, byd in _weeks(d):
        run = _run_dir(byd)
        if run == 0:
            continue
        mon, wed = byd[0][1], byd[2][1]
        tidx, thu = byd[3]
        seg = h[(h.index >= tidx) & (h["close_time"] <= pd.Timestamp(thu.close_time))]
        cdir = "bearish" if run == 1 else "bullish"
        wo = mon.open
        for j in range(2, len(seg)):
            sub = seg.iloc[:j + 1]
            ext = sub["high"].max() if run == 1 else sub["low"].min()
            swept = ext > wed.high if run == 1 else ext < wed.low
            if not swept:
                continue
            cis = hourly_cisd_in_candle(sub[["open", "high", "low", "close"]],
                                        sub.index[0], sub.index[-1], cdir,
                                        scope="range", level_rule="series_open")
            if cis is None:
                continue
            px = float(sub["close"].iloc[-1])
            if (run == 1 and not wo < px) or (run == -1 and not wo > px):
                break
            t = pd.Timestamp(sub["close_time"].iloc[-1])
            fri_end = pd.Timestamp(thu.close_time) + pd.Timedelta(hours=23)
            rows.append({"decision_time": t, "available_at": t, "direction": -run,
                         "stop_px": float(ext), "target_px": float(wo),
                         "max_hold": fri_end - t})
            break
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "max_hold"]
    out = pd.DataFrame(rows, columns=cols)
    out["max_hold"] = pd.to_timedelta(out["max_hold"])
    return out


RULES_COMMON = [
    "daily bars roll at 18:00 NY; session weekday = trading_day + 1 (Mon..Fri); weekly open = Monday session open",
    "run (bullish): Tue and Wed each close > open, make a higher high AND a higher low than the prior day (no internal low), Wed close > weekly open; Monday need not expand (speaker's relaxation); bearish mirror",
    "'relevant level' reached by Wed is undefined in the corpus and NOT required",
    "SMT is not required (no correlated gold-EUR/GBP series in the harness)",
]
PARAMS_COMMON = {"day_open_hour": 18, "expansion_day": "close beyond open + higher high + higher low vs prior day",
                 "days_required": "Tue+Wed (Mon optional)", "cisd_level_rule": "series_open",
                 "cisd_tf": "1h", "hold_basis": "bars"}
SRC_COMMON = {
    "day_open_hour": "method_spec: §1.4 daily open 18:00 NY canon",
    "expansion_day": "declared-before-run: 'expand away without creating a significant low' -> each day makes a higher high and a higher low and closes up",
    "days_required": "corpus: uPUNOi_R9fA relaxation 'Monday need not expand (Tue and Wed suffices)' (yaml detection_rules)",
    "cisd_level_rule": "method_spec: §4.2 default first-candle-open of the series",
    "cisd_tf": "corpus: oBkh-__IL-I 'drop to the hourly' ; method_spec §2.4 hourly CISD confirmation",
    "hold_basis": "declared-before-run: README trap 7 - clock runs showed real/control exposure gaps of 14% (a) and 18% (b), so rerun in trading time as prescribed",
}


def main():
    m1 = cl.load_m1()
    # ---- reading a
    ev = cl.cache_frame("tcw_a_v1", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="40D", recent="1D")
    res = cl.trade_test(ev, max_hold=HOLD_A, claim="+", hold_basis="bars")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars")})
    op = {"rules": RULES_COMMON + [
        "Thursday is a daily C2 against the run: sweeps Wednesday's high (bull run) and closes back below it; mirror",
        "an hourly CISD (close through the first open of the opposing up-close series that made Thursday's high) exists inside Thursday",
        "decide at Thursday's close (Friday session open 18:00 NY); enter next M1 open, direction back toward the weekly open",
        "stop beyond Thursday's extreme; target the weekly open (skip if already reached by Thursday's close); exit at Friday 17:00 NY"],
        "params": {**PARAMS_COMMON, "stop": "Thursday extreme", "target": "weekly open",
                   "max_hold": HOLD_A}}
    src = {**SRC_COMMON,
           "stop": "corpus: execution.stop 'Beyond the Thursday extreme' (oBkh-__IL-I / uPUNOi_R9fA)",
           "target": "corpus: _VquvUgdQmA 'anticipate Friday back into the range'; execution.targets first = weekly open",
           "max_hold": "declared-before-run: the Friday session (Thu 18:00 -> Fri 17:00 NY)"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Friday-branch reading. The 'relevant level' precondition is dropped (undefined). Rerun once with hold_basis='bars' per README trap 7 (clock run: n=34 diff +0.023 [-0.358,+0.449] UNDERPOWERED).")
    print(p)
    # ---- reading b
    evb = cl.cache_frame("tcw_b_v1", lambda: detect_b(cl.load_m1()))
    print("b events", len(evb))
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="40D", recent="1D")
    resb = cl.trade_test(evb, claim="+", hold_basis="bars")
    print({k: resb.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars")})
    opb = {"rules": RULES_COMMON + [
        "on Thursday, at each hourly close: Thursday's extreme so far has swept Wednesday's extreme",
        "and an hourly CISD against the run exists inside Thursday so far -> decide at that hourly close (first one only)",
        "enter next M1 open toward the weekly open; stop at Thursday's extreme so far; target weekly open (skip if price already beyond it)",
        "hold until Friday 17:00 NY (max_hold column)"],
        "params": {**PARAMS_COMMON, "stop": "Thursday extreme so far", "target": "weekly open",
                   "max_hold": "to Friday 17:00 NY"}}
    srcb = {**SRC_COMMON,
            "stop": "corpus: execution.stop 'Beyond the Thursday extreme'",
            "target": "corpus: execution.targets first = weekly open",
            "max_hold": "declared-before-run: through the Friday continuation day"}
    p = cl.write_result(CID, "b", resb, operationalization=opb, params_source=srcb,
                        script=__file__, probe=probe_b,
                        notes="Thursday-intraday branch. Small-wick+SMT exception not applied (wick unknowable before the close; no SMT series). Rerun once with hold_basis='bars' per README trap 7 (clock run: n=52 diff +0.105 [-0.411,+0.709] UNDERPOWERED).")
    print(p)


if __name__ == "__main__":
    main()
