"""silver-bullet-am-backtest-result — does the reported silver-bullet AM result replicate
mechanically on gold?

The concept is a 15-trade, 45-day FX-Replay backtest on NAS100 (+44.4%, avg RR ~5, BE at
3R) with discretionary entry selection. Its own measurable: "re-run of the same window
with a fully mechanical entry rule to separate the model from the discretion" and
"out-of-sample months". The instrument here is gold, the span the certified decade.

Mechanical model (silver-bullet-am-model / silver-bullet-window, same video):
  * mark the high/low of the 09:00 New York hourly candle (known at 10:00 NY);
  * inside 10:00-11:00 NY, price takes ONE side (a sweep): the reversal extreme must sit
    beyond that side and form at/after 10:00;
  * entry model on the 1-minute after the sweep: his usual confirmation, a 1m CISD
    (phase-3 locked CISD rules) in the opposite direction whose extreme is the sweep;
    decision at the confirming M1 bar's close, which must be before 11:00 NY (an order
    unfilled at 11:00 is cancelled);
  * stop at the swept extreme (the protected swing); target = the other side of the 09:00
    candle; first qualifying setup of the session only; no sweep / no entry = no trade.
  * max hold 5h (declared). The break-even-at-3R management cannot be expressed in the
    harness (fixed stop only) and is not applied.
claim '+': the mechanical book beats matched random entries with the same geometry.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, CISD_KW  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "silver-bullet-am-backtest-result"
HOLD = "5h"


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if len(m1) == 0:
        return pd.DataFrame(columns=cols)
    ny = cl.to_ny(m1.index)
    mod = ny.hour.to_numpy() * 60 + ny.minute.to_numpy()
    date = ny.normalize().tz_localize(None).to_numpy()
    rows = []
    o, h, l, c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = m1.index
    # positions grouped by NY calendar date
    starts = np.flatnonzero(np.r_[True, date[1:] != date[:-1]])
    ends = np.r_[starts[1:], len(date)]
    for s0, e0 in zip(starts, ends):
        m = mod[s0:e0]
        h9 = (m >= 540) & (m < 600)
        if h9.sum() < 30:                       # need a real 09:00 candle
            continue
        H9, L9 = h[s0:e0][h9].max(), l[s0:e0][h9].min()
        w = np.flatnonzero((m >= 570) & (m < 660)) + s0   # 09:30-11:00 NY slice
        if len(w) < 20:
            continue
        seg = pd.DataFrame({"open": o[w], "high": h[w], "low": l[w], "close": c[w]},
                           index=idx[w])
        ev = cisd_events(seg, **CISD_KW)
        if ev.empty:
            continue
        ext_ny = cl.to_ny(pd.DatetimeIndex(ev["extreme_time"]))
        ext_mod = ext_ny.hour * 60 + ext_ny.minute
        dec = pd.DatetimeIndex(ev["confirm_time"]) + pd.Timedelta(minutes=1)
        dec_ny = cl.to_ny(dec)
        dec_mod = dec_ny.hour * 60 + dec_ny.minute
        bear = (ev["direction"] == "bearish").to_numpy()
        ep = ev["extreme_price"].to_numpy(float)
        cc = ev["confirm_close"].to_numpy(float)
        ok = (np.asarray(ext_mod) >= 600) & (np.asarray(dec_mod) < 660) & (
            (bear & (ep > H9) & (cc > L9)) | (~bear & (ep < L9) & (cc < H9)))
        # the bar that closes the confirmation must itself be inside the day's slice
        if not ok.any():
            continue
        k = np.flatnonzero(ok)[0]
        rows.append((dec[k], -1 if bear[k] else 1, float(ev["protected_swing"].iloc[k]),
                     L9 if bear[k] else H9))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = out["decision_time"]
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("sb_am_gold_1mcisd_0900range", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", keep_trades=True)
    tr = res.pop("_trades", None)
    rr = float((tr["target"] - tr["entry"]).abs().div(tr["risk"]).median())
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "verdict", "verdict_detail", "ties", "exposure_bars",
                                   "ctrl_overlap")}, "median planned RR", rr)
    op = {"rules": [
        "09:00 NY hourly candle high/low (M1 09:00-09:59 NY, >= 30 bars)",
        "1m CISD (series_open, 2/2 swings, max_wait 3) on M1 09:30-11:00 NY; keep a "
        "bearish CISD whose extreme > 09:00 high (bullish: extreme < 09:00 low), extreme "
        "formed at/after 10:00 NY, decision (confirming bar close) before 11:00 NY",
        "first qualifying setup per NY date; enter next M1 open; stop = the swept extreme "
        "(protected swing); target = the other side of the 09:00 candle; exit by 5h",
        "not modelled: break-even at 3R (harness has fixed stops only)"],
        "params": {"range_candle": "09:00 NY 1h", "window": "10:00-11:00 NY",
                   "entry_tf": "1min", "max_hold": HOLD, "per_session": 1}}
    src = {"range_candle": "corpus: silver-bullet-am-model 'mark the 09:00 hourly candle'",
           "window": "corpus: silver-bullet-window 10:00-11:00 NY, cancel at 11:00",
           "entry_tf": "corpus: silver-bullet-am-model ltf 1m; CISD per method_spec §4.2 "
                       "with phase3 locked parameters",
           "max_hold": "declared-before-run: 5h (rest of the NY session; reported avg "
                       "duration 1h29m)",
           "per_session": "corpus: one setup per session (no trade if none by 11:00)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"Instrument differs from the report (NAS100 -> XAUUSD). "
                              f"Median planned RR of the real arm {rr:.2f} (reported avg "
                              f"~5). Entry discretion in the original cannot be reproduced; "
                              f"this is the mechanical re-run the concept itself names.")
    print("wrote", p)
