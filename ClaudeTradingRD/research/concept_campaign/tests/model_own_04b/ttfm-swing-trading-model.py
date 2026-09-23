"""ttfm-swing-trading-model — trade_test.

Model (9BY-MQRNy-Y): step one is always a weekly bias — a weekly candle 2 closure
implies expansion in weekly candle 3 toward the previous week's high (bullish) / low;
step two is a DAILY candle 2 (or 3) closure forming the daily wick with a change in the
state of delivery inside it; step three is an hourly continuation entry held through
the following days into the weekly draw; stop at the protected swing; 2R minimum.

Operationalisation (declared before the run):
  * weekly bias: the last CLOSED weekly candle is a C2 closure (took the prior week's
    low and closed back above it -> bullish; mirrored). Draw = that candle's high (the
    "previous week's high") for the current week;
  * daily: a daily (18:00 NY) C2 closure in the bias direction during the current week,
    with a 1H CISD inside that daily candle (spec §2.4 step 3: the daily extreme, the
    opposing 1H series, a later 1H close through its first open, before the daily close);
  * entry at the daily close (the hourly continuation is already confirmed inside the
    candle; positional entry at the swing, as the execution field allows); stop at the
    daily C2 extreme; target = the weekly draw, taken only if it is >= 2R away;
    time exit at the weekly close (Friday C2 days are skipped: no week left).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import c2_flags, cisd_in_candle  # noqa: E402

MIN_RR = 2.0


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    w = cl.build_bars(m1, "1W")
    d = cl.build_bars(m1, "1D")
    b1 = cl.build_bars(m1, "1h")
    wo, wh, wl, wc = (w[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    w = w.assign(wbias=c2_flags(wo, wh, wl, wc).astype(float), whi=wh, wlo=wl)
    do, dh, dl, dc = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    dc2 = c2_flags(do, dh, dl, dc)
    o1, h1, l1, c1 = (b1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    i1 = pd.DatetimeIndex(b1.index)
    ds = pd.DatetimeIndex(d.index)
    dct = pd.DatetimeIndex(d["close_time"])
    a = i1.searchsorted(ds)
    b = i1.searchsorted(dct)
    wk = cl.asof(w, ds)                    # last weekly candle CLOSED by the day's open
    # the week the day belongs to: the first weekly bar whose close_time > day open
    wct = pd.DatetimeIndex(w["close_time"])
    cur = np.minimum(wct.searchsorted(ds, side="right"), len(w) - 1)
    rows = []
    for i in range(1, len(d)):
        wb = wk["wbias"].iloc[i]
        if not np.isfinite(wb) or wb == 0 or dc2[i] != wb:
            continue
        bull = wb > 0
        if dct[i] >= wct[cur[i]]:          # Friday: the daily close IS the weekly close
            continue
        j, e = cisd_in_candle(o1, h1, l1, c1, a[i], b[i], bull)
        if j < 0:
            continue
        stop = dl[i] if bull else dh[i]
        tgt = wk["whi"].iloc[i] if bull else wk["wlo"].iloc[i]
        risk = abs(dc[i] - stop)
        reward = (tgt - dc[i]) if bull else (dc[i] - tgt)
        if risk <= 0 or reward < MIN_RR * risk:
            continue
        rows.append({"decision_time": dct[i], "available_at": dct[i],
                     "direction": 1 if bull else -1, "stop_px": stop, "target_px": tgt,
                     "max_hold": wct[cur[i]] - dct[i]})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                       "stop_px", "target_px", "max_hold"])


if __name__ == "__main__":
    ev = cl.cache_frame("ttfm_swing_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, hold_basis="bars")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "weekly bias: last closed weekly candle is a C2 closure; draw = its high (bullish) / low",
        "daily (18:00 NY) C2 closure in the bias direction inside the current week, with a 1H "
        "CISD inside the daily candle (series first open, closed through before the daily close)",
        "decide at the daily close, enter next M1 open; stop = daily C2 extreme; target = weekly "
        "draw, only if >= 2R; time exit at the weekly close; Friday C2s skipped"],
        "params": {"bias_tf": "1W", "swing_tf": "1D", "cisd_tf": "1h", "min_rr": MIN_RR,
                   "exit": "weekly close", "day_open_hour": 18, "hold_basis": "bars"}}
    src = {"bias_tf": "corpus: 9BY-MQRNy-Y 'step one is always going to be getting a weekly bias'",
           "swing_tf": "method_spec: §1.3 named stacks — Swing model: Weekly C2 / Daily C2-C3 + CISD / Hourly",
           "cisd_tf": "method_spec: §2.4 step 3 hourly CISD confirms the daily closure",
           "min_rr": "method_spec: §5.3 2R floor; yaml targets '2R minimum'",
           "exit": "corpus: ttfm-swing-trading-model yaml 'hold through the following days toward the weekly draw'",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily candle",
           "hold_basis": "declared-before-run (README trap 7): clock-basis run showed exposure real 2776 vs control 2080 bars (+33%), multi-day holds span weekends"}
    p = cl.write_result("ttfm-swing-trading-model", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Weekly bias from C2 closure only (the corpus's 'concretely' reading); "
                              "the 4-hour shortcut variant and the upper-half invalidation are not modelled. "
                              "Re-run once with hold_basis='bars' per README trap 7 (clock-basis run: n=39, "
                              "diff +0.76R [+0.09, +1.56], UNDERPOWERED, exposure mismatch 33%).")
    print("wrote", p)
