"""c3-with-ic-highest-winrate -- "C3 entered with an intracandle CISD is the highest
win-rate part of my strategy".

Gate test inside the model (the claim is comparative: C3+IC vs all other entries of
the same model). Stack 4H (HTF) / 15m (LTF), YAML htf 1D/4H, ltf 1H/15m.

Model (method_spec 3.2-3.5):
  * HTF C2 on 4H forex grid: bullish low < prior low and close > prior low
    (bearish mirror); two-sided C2 candles dropped.
  * valid model: at least one 15m CISD in the C2 direction confirmed inside the C2
    candle (gate 2, "LTF CISD inside C2").
Baseline book = every 15m CISD (series_open, 2/2, max_wait 3) in the C2 direction
whose confirming bar starts inside C3 (the next 4H candle) or C4 (the one after);
stop = protected swing, 2R, 150 min.
Gate = the entry is in C3 AND intracandle (the CISD extreme bar starts at/after the
C3 open, i.e. the wick formed inside C3). Complement = C4 entries and C3 entries
whose extreme predates the C3 open.
claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "c3-with-ic-highest-winrate"
PARAMS = {"htf": "4h", "grid4h": "forex", "ltf": "15min", "c2_test": "method_spec 3.2",
          "require_ltf_cisd_in_c2": True, "level_rule": "series_open", "max_wait": 3,
          "rr": 2.0, "max_hold": "150min", "windows": "C3 and C4"}
SRC = {"htf": "corpus: YAML timeframes htf 4H (1D also listed); phase3 15m/4H/1D stack",
       "grid4h": "session_window_fit: forex grid for gold (carried as a knob)",
       "ltf": "corpus: YAML ltf 15m; phase3 15m/4H/1D stack",
       "c2_test": "method_spec: 3.2 C2 test",
       "require_ltf_cisd_in_c2": "method_spec: 3.5 a model = closure + aligned LTF CISD",
       "level_rule": "phase3: locked series_open", "max_wait": "phase3: locked 3",
       "rr": "phase3: locked 2R", "max_hold": "phase3: 10 entry-TF bars",
       "windows": "method_spec: 3.3/3.4 C3 then C4 are the model's continuation candles"}


def detect(m1):
    h4 = cl.build_bars(m1, "4h")
    lt = cl.build_bars(m1, "15min")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "c3_ic",
            "c2_id"]
    ev = cisd_events(lt[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty or len(h4) < 4:
        return pd.DataFrame(columns=cols)
    ho, hh, hl, hc = (h4[k].to_numpy() for k in ("open", "high", "low", "close"))
    bull = np.r_[False, (hl[1:] < hl[:-1]) & (hc[1:] > hl[:-1])]
    bear = np.r_[False, (hh[1:] > hh[:-1]) & (hc[1:] < hh[:-1])]
    c2dir = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    st = h4.index.as_unit("ns").asi8
    en = pd.DatetimeIndex(h4["close_time"]).as_unit("ns").asi8
    cst = ev["confirm_time"].pipe(pd.DatetimeIndex).as_unit("ns").asi8
    xst = ev["extreme_time"].pipe(pd.DatetimeIndex).as_unit("ns").asi8
    edir = np.where(ev["direction"] == "bullish", 1, -1)
    # which 4H candle each confirming 15m bar starts in
    k = np.searchsorted(st, cst, side="right") - 1
    ok = (k >= 0) & (cst < en[np.clip(k, 0, None)])
    k = np.where(ok, k, -1)
    # model validity: an aligned CISD confirmed inside the C2 candle
    valid = np.zeros(len(h4), bool)
    for i in np.flatnonzero(c2dir != 0):
        valid[i] = bool(((k == i) & (edir == c2dir[i])).any())
    rows = []
    for j in range(len(ev)):
        kj = k[j]
        if kj < 1:
            continue
        for lag, is_c3 in ((1, True), (2, False)):
            i = kj - lag
            if i >= 0 and c2dir[i] != 0 and valid[i] and edir[j] == c2dir[i]:
                ic = xst[j] >= st[kj]
                rows.append((j, is_c3 and ic, st[i]))
                break
    if not rows:
        return pd.DataFrame(columns=cols)
    jj = np.array([r[0] for r in rows])
    e = ev.iloc[jj]
    dt = pd.DatetimeIndex(lt.loc[e["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": edir[jj],
                         "stop_px": e["protected_swing"].to_numpy(float), "rr": 2.0,
                         "c3_ic": np.array([r[1] for r in rows], bool),
                         "c2_id": pd.to_datetime(np.array([r[2] for r in rows]), utc=True)})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h15m_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["c3_ic"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "c3_ic", mask_available_at="decision_time", max_hold="150min",
                       cluster="c2_id")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "ties")})
    p = cl.write_result(CID, None, res, operationalization={"rules": [
        "4H forex-grid C2 (method_spec 3.2), one-sided only, with >=1 aligned 15m CISD "
        "confirmed inside C2",
        "baseline: aligned 15m CISDs (series_open, 2/2, max_wait 3) whose confirming bar "
        "starts in C3 or C4; next-M1-open entry, stop = protected swing, 2R, 150 min",
        "gate: in C3 and intracandle (CISD extreme bar starts at/after C3 open)",
        "claim '+': gated beats complement (C4 entries + non-IC C3 entries) on "
        "control-adjusted R; clustered by the C2 candle"], "params": PARAMS},
        params_source=SRC, script=__file__, probe=probe,
        notes="The claim is about win rate; the harness reads control-adjusted R (raw win "
              "rate is geometry-confounded, trap 3). POI gate on C2 not applied (phase 3: inert).")
    print("wrote", p)
