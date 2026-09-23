"""hourly-cisd-manipulation-confirmation (AM Trades, guest, contested) — trade_test x 2.

Three-step confirmation (wGYde-h84cs / QmGJFxfSHxM): (1) price engages a HTF PD array -
the previous day's high/low ('previous day high/low or above; not intra-session
liquidity'); (2) on the day the weekly profile calls for; (3) find the LAST up-close
candle that engaged the array and require an HOURLY close below that candle (mirror for
bullish). Bias opposite the swept side; he trades only in New York; targets are the
standard-deviation projections of the manipulation leg (2 / 2.5 SD first).

Readings (the contested point: what 'close below that candle' means):
  a  close below the candle's LOW  ('below that candle' - the whole candle)
  b  close below the candle's OPEN ('close through the opposing candle' - its body)

Stop: not stated -> the manipulation extreme (the high of the run, from first
engagement to the confirming close). Target: the -2 SD projection of the manipulation
leg anchored from its extreme (1) to the CISD level (0): level - 2 x (extreme - level).
Step (2) is omitted: the weekly-profile day is a discretionary hypothesis with no rule.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "hourly-cisd-manipulation-confirmation"
BASE = dict(tf="1h", pd_array="previous trading day high/low (18:00 NY roll)",
            window=("08:30", "12:01"), sd_target=2.0, max_hold="10h", min_prev_m1=600,
            hold_basis="bars")


def detect_reading(m1, reading):
    h1 = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "level"]
    if len(h1) < 3 or len(d) < 2:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hct = pd.DatetimeIndex(h1["close_time"])
    td = cl.trading_day(pd.DatetimeIndex(h1.index))
    dtd = pd.DatetimeIndex(d["trading_day"])
    dpos = np.searchsorted(dtd.asi8, td.as_unit(dtd.unit).asi8, "left") - 1
    dh, dl, dn = d["high"].to_numpy(), d["low"].to_numpy(), d["n_m1"].to_numpy()
    dct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    starts = pd.DatetimeIndex(h1.index).as_unit("ns").asi8
    inwin = cl.in_window(hct, *BASE["window"])
    rows = []
    tdn = td.asi8
    bounds = np.flatnonzero(np.r_[True, tdn[1:] != tdn[:-1], True])
    for s0, s1 in zip(bounds[:-1], bounds[1:]):
        p = dpos[s0]
        if p < 0 or dn[p] < BASE["min_prev_m1"] or dct[p] > starts[s0]:
            continue
        for sgn in (-1, 1):                 # -1: bearish (buy-side run), +1 bullish
            if sgn < 0:
                lvl_pd, H, L, O, C = dh[p], h, l, o, c
            else:                           # mirror
                lvl_pd, H, L, O, C = -dl[p], -l, -h, -o, -c
            engaged, ext, last = False, -np.inf, -1
            for j in range(s0, s1):
                if H[j] > lvl_pd:
                    engaged = True
                if engaged:
                    ext = max(ext, H[j])
                if last >= 0:
                    X = L[last] if reading == "a" else O[last]
                    if C[j] < X:
                        if inwin[j]:
                            lev = X * (-sgn)          # un-mirror
                            ex = ext * (-sgn)
                            rows.append((hct[j], sgn, ex, np.nan, lev))
                        break
                if H[j] > lvl_pd and C[j] > O[j]:
                    last = j
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                     "level"])
    # target: bearish lev - 2*(ex - lev); bullish lev + 2*(lev - ex)  == lev - 2*(ex - lev)
    ev["target_px"] = ev["level"] - BASE["sd_target"] * (ev["stop_px"] - ev["level"])
    ev["available_at"] = ev["decision_time"]
    return ev[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    for reading, desc in (("a", "hourly close below the LOW of the last up-close candle that "
                                "engaged the PD array (mirror: above the HIGH of the last "
                                "down-close candle)"),
                          ("b", "hourly close below the OPEN of that candle (mirror: above "
                                "its open)")):
        def detect(m1, _r=reading):
            return detect_reading(m1, _r)
        P = dict(BASE, reading=reading)
        ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
        print(reading, len(ev), ev.direction.value_counts().to_dict())
        probe = cl.probe_lookahead(detect, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=BASE["max_hold"], hold_basis=BASE["hold_basis"])
        op = {"rules": [
            "1h UTC-aligned bars; trading day rolls 18:00 NY; PD array = previous trading "
            "day's high (low); previous day must be a full session (>= 600 M1 bars)",
            "engagement: an hourly bar trades above PDH (bearish case); track the LAST "
            "up-close hourly bar whose high is above PDH",
            "CISD: a later hourly bar of the same trading day closes " + desc,
            "only the first CISD per day and side; kept only if its close is in 08:30-12:00 NY",
            "entry next M1 open after the confirming close; stop = the highest high from "
            "first engagement to the confirming bar; target = level - 2 x (extreme - level) "
            "(-2 SD of the manipulation leg); time exit 10h"],
            "params": P}
        src = {
            "tf": "corpus: wGYde-h84cs AM Trades 'uses the HOURLY for the change in state of "
                  "delivery' (concept definition)",
            "pd_array": "corpus: wGYde-h84cs 'previous day high/low or above; not intra-session "
                        "or internal liquidity' (detection rule 1)",
            "window": "corpus: execution.entry 'New York session only'; clock = concept_lab "
                      "SESSION_WINDOWS ny_am 08:30-12:00 (method_spec 2.5), 12:00 close included",
            "sd_target": "corpus: standard-deviation-projection (AM Trades) 'the 2 and 2.5 "
                         "deviations are a good first target' - the 2",
            "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 10h on 1h",
            "min_prev_m1": "declared-before-run: skip stub prior sessions (README trap 6)",
            "hold_basis": "declared-before-run (README trap 7): the clock-basis run showed "
                          "exposure_bars real 498 vs control 547-549 (10-11%, entries at "
                          "09:00-12:00 NY whose 10h hold spans the 17:00 halt); rerun in "
                          "trading time as the README directs",
            "reading": "declared-before-run: contested 'close below that candle' - a low / b open"}
        notes = ("Step 2 (weekday matched to a weekly-profile hypothesis) and the 'aggressive, "
                 "fast, convincing' qualifier are not mechanical and are omitted; news "
                 "coincidence (preferred, not required) omitted. Stop not stated in the corpus: "
                 "the manipulation extreme is used, which is the anchor of his own projection. "
                 "RERUN NOTE: first run used hold_basis='clock' (a: diff +0.073 [-0.005,+0.151] "
                 "UNDERPOWERED; b: +0.053 [-0.029,+0.129] UNDERPOWERED) but real/control "
                 "exposure differed by ~10-11% (trap 7), so both readings were rerun once with "
                 "hold_basis='bars'; this file is that rerun. Both runs are in the ledger.")
        path = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                               script=__file__, probe=probe, notes=notes)
        print(path)
        for k in ("n", "verdict", "verdict_detail", "avg_R", "win_rate", "diff", "ci_lo",
                  "ci_hi", "p", "ties", "exposure_bars", "halves"):
            print(k, res.get(k))
