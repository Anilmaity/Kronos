"""positional-entry -- enter at the OPEN of the continuation candle (C3) on a
protected swing that already exists from before that open.

Trade test (entry at open, stop on the pre-open protected swing, 2R target).
Model: HTF C2 (method_spec 3.2: bullish low < prior low and close > prior low,
bearish mirror; two-sided dropped). Protected swing = the most recent LTF CISD in the
C2 direction confirmed inside C2 (series_open, 2/2, max_wait 3) whose protected
swing is still intact at the C2 close and lies beyond the C2 close (a real stop).
Entry = decision at the C2 close -> first M1 open of C3.

Contested variants -> two readings, declared before any run:
  a  xMFd_kfmIqI SELECTION TEST (4H / 15m): the protected swing must sit BEYOND the
     EQ of C2 (below 50% of C2's wick-to-wick range for a long); otherwise no trade.
     Hold: C3's length, 240 trading minutes (hold_basis bars).
  b  VtFC9SCnlYM / IzOQmcgLyA0 "invalidation very close to the opening price" (1D /
     1H, the overnight CAD example): the swing must be within 0.25 x C2's range of
     the C2 close. Hold: one trading session, 1380 trading minutes (hold_basis bars).
claim '+' vs matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "positional-entry"
CLOSE_FRAC = 0.25


def detect(m1, htf, ltf, mode):
    H = cl.build_bars(m1, htf)
    L = cl.build_bars(m1, ltf)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    ev = cisd_events(L[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty or len(H) < 3:
        return pd.DataFrame(columns=cols)
    ho, hh, hl, hc = (H[k].to_numpy() for k in ("open", "high", "low", "close"))
    bull = np.r_[False, (hl[1:] < hl[:-1]) & (hc[1:] > hl[:-1])]
    bear = np.r_[False, (hh[1:] > hh[:-1]) & (hc[1:] < hh[:-1])]
    c2dir = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    st = H.index.as_unit("ns").asi8
    en = pd.DatetimeIndex(H["close_time"]).as_unit("ns").asi8
    cst = pd.DatetimeIndex(ev["confirm_time"]).as_unit("ns").asi8
    edir = np.where(ev["direction"] == "bullish", 1, -1)
    k = np.searchsorted(st, cst, side="right") - 1
    ok = (k >= 0) & (cst < en[np.clip(k, 0, None)])
    k = np.where(ok, k, -1)
    lst = L.index.as_unit("ns").asi8
    llo = L["low"].to_numpy(); lhi = L["high"].to_numpy()
    rows = []
    for i in np.flatnonzero(c2dir != 0):
        d = c2dir[i]
        cand = np.flatnonzero((k == i) & (edir == d))
        if len(cand) == 0:
            continue
        j = cand[-1]                                    # most recent aligned CISD in C2
        sw = float(ev["protected_swing"].iloc[j])
        xs = np.searchsorted(lst, pd.Timestamp(ev["extreme_time"].iloc[j]).value)
        xe = np.searchsorted(lst, en[i], side="left")   # LTF bars closed by C2 close
        seg_lo = llo[xs:xe].min(); seg_hi = lhi[xs:xe].max()
        intact = seg_lo >= sw if d == 1 else seg_hi <= sw
        beyond_close = sw < hc[i] if d == 1 else sw > hc[i]
        if not (intact and beyond_close):
            continue
        eq = (hh[i] + hl[i]) / 2.0
        rng = hh[i] - hl[i]
        if mode == "eq":
            sel = sw < eq if d == 1 else sw > eq
        else:
            sel = abs(hc[i] - sw) <= CLOSE_FRAC * rng
        if sel:
            rows.append((en[i], d, sw))
    if not rows:
        return pd.DataFrame(columns=cols)
    dt = pd.to_datetime(np.array([r[0] for r in rows]), utc=True)
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": np.array([r[1] for r in rows]),
                         "stop_px": np.array([r[2] for r in rows], float), "rr": 2.0})


if __name__ == "__main__":
    specs = {
        "a": dict(htf="4h", ltf="15min", mode="eq", hold="240min", look="20D",
                  params={"htf": "4h", "grid4h": "forex", "ltf": "15min",
                          "selection": "protected swing beyond C2 EQ (wick-to-wick 50%)",
                          "rr": 2.0, "max_hold": "240min", "hold_basis": "bars"},
                  src={"htf": "corpus: YAML htf 4H; phase3 15m/4H stack",
                       "grid4h": "session_window_fit: forex grid (knob)",
                       "ltf": "corpus: YAML ltf 15m",
                       "selection": "corpus: xMFd_kfmIqI 'the stop on candle two is above the "
                                    "EQ of candle two'; EQ measured wick high to wick low "
                                    "(IPZjNI1B5a0)",
                       "rr": "corpus: YAML execution targets '2R'",
                       "max_hold": "declared-before-run: hold for the C3 candle (4h of "
                                   "trading time)",
                       "hold_basis": "declared-before-run: decisions sit at HTF closes, "
                                     "including the Friday close before the weekend (trap 7)"}),
        "b": dict(htf="1D", ltf="1h", mode="close", hold="1380min", look="45D",
                  params={"htf": "1D", "day_open_hour": 18, "ltf": "1h",
                          "close_frac_of_c2_range": CLOSE_FRAC, "rr": 2.0,
                          "max_hold": "1380min", "hold_basis": "bars"},
                  src={"htf": "corpus: IzOQmcgLyA0 CAD example 'daily ideal candle 2 closure, "
                              "hourly protected swing'",
                       "day_open_hour": "session_window_fit: settled 18:00 NY roll",
                       "ltf": "corpus: IzOQmcgLyA0 hourly protected swing",
                       "close_frac_of_c2_range": "declared-before-run: 'very close to the "
                                                 "opening price' unquantified; <= 0.25 x C2 range",
                       "rr": "corpus: YAML execution targets '2R'",
                       "max_hold": "declared-before-run: 'let this swing into the next day' = "
                                   "one session (1380 trading minutes)",
                       "hold_basis": "declared-before-run: daily decisions span the halt and "
                                     "weekend (trap 7)"}),
    }
    for reading, s in specs.items():
        det = (lambda m, s=s: detect(m, s["htf"], s["ltf"], s["mode"]))
        ev = cl.cache_frame(f"{CID}_{reading}_v1", lambda d=det: d(cl.load_m1()))
        print(reading, len(ev))
        probe = cl.probe_lookahead(det, ev, lookback=s["look"])
        res = cl.trade_test(ev, max_hold=s["hold"], hold_basis="bars")
        print(reading, {k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p",
                                                  "verdict", "verdict_detail", "exposure_bars",
                                                  "ties", "ctrl_overlap")})
        p = cl.write_result(CID, reading, res, operationalization={"rules": [
            f"{s['htf']} C2 (method_spec 3.2), one-sided; protected swing = most recent "
            f"{s['ltf']} CISD in the C2 direction confirmed inside C2, intact at the C2 close",
            "reading a: swing must lie beyond C2's EQ" if reading == "a" else
            "reading b: swing within 0.25 x C2 range of the C2 close",
            "decision at the C2 close, entry = first M1 open of C3, stop on the swing, 2R",
            f"max hold {s['hold']} of trading time"], "params": s["params"]},
            params_source=s["src"], script=__file__, probe=probe,
            notes="Discretionary 'see price respect the level' trigger not modelled; entry "
                  "is purely positional at the open, as the concept's headline states.")
        print("wrote", p)
