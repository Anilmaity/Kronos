"""ttfm-favorite-daily-4h-15m (model, TTrades own voice, contested).

His favourite pairing: daily bias from a daily candle-2 closure (expansion expected next day,
daily C3); on the traded day a 4-hour candle-2 closure in the same direction (4h C3 is the
leg to trade); inside that 4h C3, a 15-minute change in the state of delivery with the
relevant half of the 4-hour candle respected -> continuation entry at market, stop at the
protected low, 2R.

Operationalisation (bullish; bearish mirrors):
  * yesterday (previous complete session) is a daily C2: low < prior day low, close > it.
  * today: a 4h candle (forex grid) that is a C2 in the same direction (low < previous 4h low,
    close > it), both it and the next 4h candle inside today's session.
  * inside the next 4h candle (C3): the first 15m CISD (phase-3 config) in that direction,
    confirmed within the C3 candle, whose extreme holds the upper half of the 4h C2 range
    (bearish: the lower half) — "the lower half of this 4-hour candle" must be respected.
  * enter next M1 open after the 15m confirming close; stop at the protected swing; 2R;
    exit after 10 entry bars (phase-3 hold).
Single reading. (The futures 2:00/6:00/10:00 grid in one clip is a grid knob; the forex grid
is the recorded choice for gold.)
claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

RR = 2.0
MAX_HOLD = "150min"


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    d = C.daily(m1).reset_index(drop=True)
    pl, ph = d["low"].shift(1), d["high"].shift(1)
    dbull = (d["low"] < pl) & (d["close"] > pl)
    dbear = (d["high"] > ph) & (d["close"] < ph)
    dd = pd.DataFrame({"td": d["td"], "dir": np.where(dbull & ~dbear, 1, np.where(dbear & ~dbull, -1, 0))})
    dmap = dict(zip(dd["td"], dd["dir"]))
    f = C.complete_bars(m1, "4h", grid4h=C.GRID4H).reset_index()
    f["td"] = cl.trading_day(f["time"])
    fp_l, fp_h = f["low"].shift(1), f["high"].shift(1)
    fb = (f["low"] < fp_l) & (f["close"] > fp_l)
    fs = (f["high"] > fp_h) & (f["close"] < fp_h)
    f["c2dir"] = np.where(fb & ~fs, 1, np.where(fs & ~fb, -1, 0))
    f["mid"] = (f["high"] + f["low"]) / 2
    # C3 window = the next 4h bar, same trading day
    nxt_start, nxt_close, nxt_td = f["time"].shift(-1), f["close_time"].shift(-1), f["td"].shift(-1)
    # daily bias for today = direction of the previous complete session's C2
    prev_td = C.prev_day_levels(d.set_index("td", drop=False).rename_axis(None), f["td"])["pd_td"].to_numpy()
    f["bias"] = [dmap.get(pd.Timestamp(x), 0) for x in prev_td]
    sel = (f["c2dir"] != 0) & (f["c2dir"] == f["bias"]) & (nxt_td == f["td"]) & nxt_start.notna()
    w = pd.DataFrame({"c3_start": pd.DatetimeIndex(nxt_start[sel]), "c3_close": pd.DatetimeIndex(nxt_close[sel]),
                      "dir": f.loc[sel, "c2dir"].to_numpy(), "mid": f.loc[sel, "mid"].to_numpy()})
    c15 = C.cisd_table(C.complete_bars(m1, "15min"))
    if w.empty or c15.empty:
        return pd.DataFrame(columns=cols)
    # assign each 15m CISD to the 4h C3 window containing its confirmation
    ws = pd.DatetimeIndex(w["c3_start"]).as_unit("ns").asi8
    order = np.argsort(ws); w = w.iloc[order].reset_index(drop=True); ws = ws[order]
    tt = pd.DatetimeIndex(c15["t"]).as_unit("ns").asi8
    k = np.searchsorted(ws, tt - 1, side="right") - 1        # window with start < t
    ok = k >= 0
    kk = np.clip(k, 0, None)
    inwin = ok & (tt <= pd.DatetimeIndex(w["c3_close"]).as_unit("ns").asi8[kk])
    xs = pd.DatetimeIndex(c15["extreme_start"]).as_unit("ns").asi8
    inwin &= xs >= ws[kk]                                     # extreme formed inside C3
    c = c15[inwin].assign(win=kk[inwin])
    c = c.merge(w[["dir", "mid"]], left_on="win", right_index=True, suffixes=("", "_w"))
    good = (c["dir"] == c["dir_w"]) & np.where(c["dir"] == 1, c["extreme_price"] >= c["mid"],
                                               c["extreme_price"] <= c["mid"])
    q = c[good].sort_values("t").groupby("win", sort=True).head(1).sort_values("t")
    t = pd.DatetimeIndex(q["t"])
    return pd.DataFrame({"decision_time": t, "available_at": t,
                         "direction": q["dir"].astype(int).to_numpy(),
                         "stop_px": q["stop"].to_numpy(float), "rr": RR}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("ttfm_fav_events_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    r = cl.trade_test(ev, max_hold=MAX_HOLD)
    print({k: r.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
    params = {"daily_c2": "previous session: sweep prior day extreme, close back inside",
              "grid4h": C.GRID4H, "h4_c2": "same-direction 4h C2 on the traded day; next 4h bar = C3",
              "half_rule": "15m CISD extreme holds the upper (bull) / lower (bear) half of the 4h C2",
              "cisd": "15m, series_open, swing 2/2, max_wait 3; first per 4h C3",
              "rr": RR, "max_hold": MAX_HOLD}
    src = {"daily_c2": "method_spec: §3.2 C2 test; corpus 5Y-8G9eA35o daily candle 2 closure",
           "grid4h": "session_window_fit: forex grid for gold (knob recorded)",
           "h4_c2": "corpus: 5Y-8G9eA35o '4-hour ... another candle 2 closure, so candle 3 on the 4-hour is the leg to trade'",
           "half_rule": "corpus: zJLaABC_hM8 'The lower half of this 4-hour candle' must be respected",
           "cisd": "phase3: locked CISD config",
           "rr": "corpus: 5Y-8G9eA35o 'I can look for two R'",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    cl.write_result("ttfm-favorite-daily-4h-15m", None, r,
                    operationalization={"rules": [
                        "bias: previous session is a daily C2 (bullish/bearish)",
                        "traded day: a same-direction 4h C2 (forex grid) whose next 4h bar is in "
                        "the same session (4h C3)",
                        "inside 4h C3: first 15m CISD in that direction with extreme formed in C3 "
                        "and holding the relevant half of the 4h C2",
                        "enter next M1 open; stop protected swing; 2R; exit after 150 min"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe,
                    notes="Daily FVG/'bodies respecting' context and the failure-swing ~4R "
                          "target are discretionary and not modelled. Phase 3's 15m/4H/1D R4 "
                          "cell (n=534, -0.028R) is the nearest prior measurement.")
