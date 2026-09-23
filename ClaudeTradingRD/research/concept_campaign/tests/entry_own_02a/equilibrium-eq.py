"""equilibrium-eq -- the 50% (EQ) of the previous candle / range governs the next.

Contested (three 50% levels share the name). Two readings, declared before any run.
EQ is measured wick high to wick low, whole candle (IPZjNI1B5a0 dedicated video,
aqnY1yZvfYs direct answer); the large-wick switch is not applied (unquantified).

  a  BIAS INVALIDATOR, previous-day EQ (BmTJEWru_9U, HMYcwQwaWm0, jKuXaC84Qx4,
     -KKuZb5Z5aU): after a bullish day (close > open), the first 1H CLOSE of the next
     trading day below that day's EQ "makes the previous day low the likely draw"
     (bearish mirror: close above EQ -> previous day high). Rate test.
     hit = the previous day's low (high) trades before the end of the trading day.
     null = same signed distance from the next M1 open, same number of trading
     minutes, at matched random moments. claim '+'.
  b  EXPANSION FILTER, previous 4H candle EQ (CRaMFN6di6U, 5fnFOh5YuM0,
     upper-half-eq-expansion-filter): "while 0.5 continues to be respected, expansion
     continues". Gate test. Baseline: 15m CISD (series_open, 2/2, max_wait 3) in the
     direction of the previous completed 4H candle (close vs open), stop = protected
     swing, 2R, 150 min. Gate: at the decision, the current 4H candle's extreme
     against the trade (its running low for a long) has stayed beyond the previous
     4H candle's EQ (upper half for a long). claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "equilibrium-eq"
MIN_DAY_M1 = 600


def detect_a(m1):
    h1 = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    cols = ["decision_time", "available_at", "direction", "level", "side", "day_end",
            "eq"]
    if len(h1) == 0 or len(d) < 2:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(h1["close_time"])
    st = h1.index
    # which trading day each 1H bar belongs to (by its start)
    dst = d.index.as_unit("ns").asi8
    den = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    k = np.searchsorted(dst, st.as_unit("ns").asi8, side="right") - 1
    ok = (k >= 1) & (st.as_unit("ns").asi8 < den[np.clip(k, 0, None)])
    do, dh, dl, dc, dn = (d[x].to_numpy() for x in ("open", "high", "low", "close", "n_m1"))
    c = h1["close"].to_numpy()
    rows = []
    seen = set()
    for j in np.flatnonzero(ok):
        kd = k[j]
        if kd in seen:
            continue
        p = kd - 1
        if dn[p] < MIN_DAY_M1 or dc[p] == do[p]:
            seen.add(kd); continue
        eq = (dh[p] + dl[p]) / 2.0
        if dc[p] > do[p] and c[j] < eq:
            rows.append((ct[j], -1, dl[p], "below", den[kd], eq)); seen.add(kd)
        elif dc[p] < do[p] and c[j] > eq:
            rows.append((ct[j], 1, dh[p], "above", den[kd], eq)); seen.add(kd)
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["decision_time", "direction", "level", "side",
                                    "day_end", "eq"])
    r["day_end"] = pd.to_datetime(r["day_end"].to_numpy(), utc=True)
    r["available_at"] = r["decision_time"]
    return r[cols]


def detect_b(m1):
    L = cl.build_bars(m1, "15min")
    H = cl.build_bars(m1, "4h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "eq_held"]
    ev = cisd_events(L[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty or len(H) < 2:
        return pd.DataFrame(columns=cols)
    hst = H.index.as_unit("ns").asi8
    hen = pd.DatetimeIndex(H["close_time"]).as_unit("ns").asi8
    lst = L.index.as_unit("ns").asi8
    kl = np.searchsorted(hst, lst, side="right") - 1
    okl = (kl >= 0) & (lst < hen[np.clip(kl, 0, None)])
    grp = np.where(okl, kl, -1 - np.arange(len(kl)))        # unique id if outside
    run_lo = pd.Series(L["low"].to_numpy()).groupby(grp).cummin().to_numpy()
    run_hi = pd.Series(L["high"].to_numpy()).groupby(grp).cummax().to_numpy()
    pos = pd.Series(np.arange(len(L)), index=L.index)
    j = pos.loc[ev["confirm_time"]].to_numpy()
    kj = kl[j]
    good = okl[j] & (kj >= 1)
    ho, hh, hl, hc = (H[x].to_numpy() for x in ("open", "high", "low", "close"))
    p = np.clip(kj - 1, 0, None)
    pdir = np.sign(hc[p] - ho[p])
    d = np.where(ev["direction"] == "bullish", 1, -1)
    eq = (hh[p] + hl[p]) / 2.0
    held = np.where(d == 1, run_lo[j] > eq, run_hi[j] < eq)
    keep = good & (pdir == d)
    dt = pd.DatetimeIndex(L.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": d,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "eq_held": held.astype(bool)})
    return out[keep].reset_index(drop=True)[cols]


if __name__ == "__main__":
    # ---- reading a: rate test
    mkt = cl.get_market()
    ev = cl.cache_frame(f"{CID}_a_v1", lambda: detect_a(cl.load_m1()))
    print("a", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    t = pd.DatetimeIndex(ev["decision_time"])
    lvl = ev["level"].to_numpy(float)
    up = (ev["side"] == "above").to_numpy()
    i0 = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)
    i1 = mkt.pos_at_or_after(pd.DatetimeIndex(ev["day_end"]))
    hb = np.maximum(i1 - i0, 0)
    dist = lvl - mkt.o[i0]
    obs = np.zeros(len(t))
    for sd, msk in (("above", up), ("below", ~up)):
        obs[msk] = cl.touch(t[msk], lvl[msk], sd, horizon_bars=hb[msk])["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        out = np.full(len(tk), np.nan)
        ok = ~tk.isna()
        for sd, msk in (("above", up), ("below", ~up)):
            sel = ok & msk
            if sel.any():
                px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[sel]), len(mkt.o) - 1)]
                out[sel] = cl.touch(tk[sel], px + dist[sel], sd,
                                    horizon_bars=hb[sel])["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev)
    print("a", {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo",
                                         "ci_hi", "p", "verdict", "verdict_detail")})
    print("wrote", cl.write_result(CID, "a", res, operationalization={"rules": [
        "previous trading day (18:00 NY roll, >=600 M1 bars) closed up (down)",
        "event: first 1H close of the next day below (above) that day's EQ = 50% of its "
        "wick high-to-low range",
        "hit: previous day low (high) traded before the end of the trading day",
        "null: same signed distance from the next M1 open, same trading-minute horizon, "
        "matched random moments; claim '+'"],
        "params": {"eq": "whole-candle wick-to-wick 50%", "closure_tf": "1h",
                   "bias": "previous day close vs open", "day_open_hour": 18,
                   "min_day_m1": MIN_DAY_M1, "horizon": "to end of the trading day",
                   "null_tod_tol_min": 30}},
        params_source={"eq": "corpus: IPZjNI1B5a0 'I'm always going to measure the candles "
                             "from Wick High to Wick low'",
                       "closure_tf": "corpus: -KKuZb5Z5aU 'it's not ideal to have closures on "
                                     "the hourly chart below that'",
                       "bias": "declared-before-run: the day's direction = close vs open "
                               "(BmTJEWru_9U bullish C2 day simplified)",
                       "day_open_hour": "session_window_fit: settled 18:00 NY roll",
                       "min_day_m1": "declared-before-run: skip stub sessions (trap 6)",
                       "horizon": "corpus: HMYcwQwaWm0 'Closing below the EQ here means that "
                                  "we could be looking for price' (the day's low as draw)",
                       "null_tod_tol_min": "session_window_fit: time-of-day buys opportunity on gold (README trap 9), added in the corrected re-run (see notes); events cluster at 19:00 NY (first "
                                           "1H close of the day), so the null holds the NY "
                                           "clock within +/-30 min"},
        script=__file__, probe=probe,
        notes="Tests the EQ-as-bias-invalidator branch (previous-day range EQ). RE-RUN NOTE: "
              "the first locked run used a null WITHOUT time-of-day matching and returned "
              "EDGE (obs 0.494 vs null 0.461, diff +0.033 [+0.006, +0.061], p=0.017). After "
              "that run I found 28% of events sit in the 19:00 NY hour (first 1H close of the "
              "session), which trap 9 says requires a time-of-day-matched null; this is the "
              "single corrected re-run with sample_times(tod_tol_min=30). Both runs are in the "
              "ledger."))

    # ---- reading b: gate test
    ev = cl.cache_frame(f"{CID}_b_v1", lambda: detect_b(cl.load_m1()))
    print("b", len(ev), ev["eq_held"].mean())
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.gate_test(ev, "eq_held", mask_available_at="decision_time", max_hold="150min")
    print("b", {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                         "verdict_detail", "ties")})
    print("wrote", cl.write_result(CID, "b", res, operationalization={"rules": [
        "baseline: 15m CISD (series_open, 2/2, max_wait 3) in the direction of the previous "
        "completed 4H (forex grid) candle; stop = protected swing, 2R, 150 min",
        "gate: the current 4H candle's running low (long) / high (short), from 15m bars "
        "closed by the decision, is still beyond the previous 4H candle's EQ",
        "claim '+': gated beats complement on control-adjusted R"],
        "params": {"htf": "4h", "grid4h": "forex", "ltf": "15min",
                   "eq": "whole-candle wick-to-wick 50%", "rr": 2.0, "max_hold": "150min"}},
        params_source={"htf": "corpus: CRaMFN6di6U 'fractally on the 4-hour: 0.5 respected'",
                       "grid4h": "session_window_fit: forex grid (knob)",
                       "ltf": "phase3: 15m/4H stack entry TF",
                       "eq": "corpus: IPZjNI1B5a0 wick high to wick low",
                       "rr": "phase3: locked 2R", "max_hold": "phase3: 10 entry-TF bars"},
        script=__file__, probe=probe,
        notes="Tests the EQ-respect expansion filter (upper-half rule) on the previous "
              "4H candle."))
