"""consolidation-external-liquidity-only (AM Trades, guest) — trade_test.

Claim (QmGJFxfSHxM): while the daily chart is consolidating / the week has stayed
internal to a prior daily range, only that range's external high and low matter; a run
of one external level is manipulation - fade it back through the range to the opposing
external level. If price closes beyond the external level instead, the read is wrong
and no fade is taken.

Operationalisation:
  * consolidation = the prior trading day(s) are all INSIDE an earlier daily candle
    (the mother, up to 4 days back; the furthest qualifying mother is the external range);
  * on the current trading day, the first 1H bar to trade above the external high:
    if it CLOSES above it the range is broken on that side (no fade that day);
    if it closes back inside, short at that close (mirror for the low);
  * stop = the run's extreme (that bar's high), target = the opposing external level,
    time exit 24h of trading time.
News timing (the release that causes the run) is not modelled - no calendar data.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "consolidation-external-liquidity-only"
P = dict(tf="1h", htf="1D", max_mother_back=5, min_m1=600, max_hold="24h",
         hold_basis="bars", day_open_hour=18)


def detect(m1):
    h1 = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "ext_hi", "ext_lo"]
    if len(d) < 3 or len(h1) < 2:
        return pd.DataFrame(columns=cols)
    dh, dl, dn = (d[k].to_numpy(float) for k in ("high", "low", "n_m1"))
    dct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    dtd = pd.DatetimeIndex(d["trading_day"])
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hct = pd.DatetimeIndex(h1["close_time"])
    starts = pd.DatetimeIndex(h1.index).as_unit("ns").asi8
    td = cl.trading_day(pd.DatetimeIndex(h1.index))
    kpos = np.searchsorted(dtd.asi8, td.as_unit(dtd.unit).asi8, "left")   # current day row
    tdn = td.asi8
    bounds = np.flatnonzero(np.r_[True, tdn[1:] != tdn[:-1], True])
    rows = []
    for s0, s1 in zip(bounds[:-1], bounds[1:]):
        k = kpos[s0]
        if k < 2:
            continue
        mother = -1
        for m in range(k - 2, max(-1, k - 1 - P["max_mother_back"]), -1):
            inside = all(dh[i] <= dh[m] and dl[i] >= dl[m] for i in range(m + 1, k))
            if inside:
                mother = m
            else:
                break            # an older mother must contain every newer day too
        if mother < 0 or dn[mother] < P["min_m1"] or dct[k - 1] > starts[s0]:
            continue
        hi, lo = dh[mother], dl[mother]
        for sgn in (-1, 1):       # -1: run of the external HIGH -> short
            for j in range(s0, s1):
                ran = h[j] > hi if sgn < 0 else l[j] < lo
                if not ran:
                    continue
                broke = c[j] > hi if sgn < 0 else c[j] < lo
                if not broke:
                    rows.append((hct[j], sgn, h[j] if sgn < 0 else l[j],
                                 lo if sgn < 0 else hi, hi, lo))
                break
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                     "ext_hi", "ext_lo"])
    ev["available_at"] = ev["decision_time"]
    return ev[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=P["max_hold"], hold_basis=P["hold_basis"])
    op = {"rules": [
        "daily candles on the 18:00 NY roll; the current day qualifies when every day "
        "between a mother candle (2-5 days back; furthest qualifying) and today is inside "
        "the mother (high <= mother high, low >= mother low); mother must be a full session",
        "external high/low = the mother's high/low; internal structure ignored",
        "on the current day, the first 1H bar to trade beyond an external level: an hourly "
        "close beyond = range broken on that side, no trade; a close back inside = "
        "manipulation, fade at that close (next M1 open)",
        "stop = that bar's extreme (the run); target = the opposing external level; time "
        "exit 24h of trading time (1,440 M1 bars)"],
        "params": P}
    src = {
        "tf": "corpus: QmGJFxfSHxM concept timeframes ltf 1H (hourly close as the run/return test)",
        "htf": "corpus: QmGJFxfSHxM 'the week has remained internal to a prior daily range'",
        "max_mother_back": "declared-before-run: a mother up to 4 inside days back (one week)",
        "min_m1": "declared-before-run: stub sessions excluded (README trap 6)",
        "max_hold": "declared-before-run: one trading day for a range-to-range objective",
        "hold_basis": "declared-before-run: trading-time hold (README trap 7) - a 24h hold "
                      "straddles halts and weekends differently for real and control entries",
        "day_open_hour": "session_window_fit: 18:00 NY daily roll"}
    notes = ("'Daily is consolidating' is read by eye in the corpus; the inside-day chain is "
             "the declared mechanical proxy ('the week has remained internal to a prior daily "
             "range'). 'Decisively beyond' = any 1H close beyond the level. The news trigger, "
             "the 'draw is lower' condition and the worked example's SMT + LTF CISD entry "
             "are not modelled: both external levels are faded at the 1H close back inside. "
             "Stop not stated - the run extreme is used.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "dropped", "verdict", "verdict_detail", "avg_R", "win_rate", "diff", "ci_lo",
              "ci_hi", "p", "ties", "exposure_bars", "halves", "sanity_flags", "exit_mix"):
        print(k, res.get(k))
