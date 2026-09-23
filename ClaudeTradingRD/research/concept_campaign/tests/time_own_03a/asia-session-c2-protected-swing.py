"""asia-session-c2-protected-swing — The only Asia-session condition: daily C2 plus a
protected swing before the open (TTrades own voice, specified: one reading).

egV_gABTQks: "The only time I trade during Asia session is when I have a candle two
closure on the daily ... inside this candle two ... I have a reversal. And then prior to
the open of the next candle, I have a protected swing. So I can anticipate that this low
should hold inside this next candle and it should trade higher."
Claim ('+'): a positional entry at the next daily open (the Asian session) in the C2's
direction, stopped just beyond that protected swing, beats a matched random entry.

Operationalisation:
  * day D is a one-sided daily C2 closure (spec §3.2: low < prev low & close > prev low,
    bullish; mirror bearish) on the 18:00 NY roll, stubs dropped;
  * the reversal / protected swing inside D: the LATEST same-direction 1h CISD
    (detectors.cisd, series_open, 2/2 swing, max_wait 3) whose extreme lies inside D and
    whose confirming bar closed by D's close; its extreme is the protected swing
    ("each new protected swing supersedes the last", spec §3.8);
  * it must still be intact at D's close (no M1 low below it after the confirmation) —
    'a protected swing exists prior to the next open';
  * decide at D's close; enter the first M1 open of the next session (18:00 NY, Asia);
    stop = the protected swing; target = D's bias-side extreme (C3 expansion takes C2's
    extreme, execution.targets); no-room rows dropped; exit after one session (1380
    trading M1 bars).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, OHLC, daily, cisd_frame, show, MIN_DAY_M1   # noqa: E402

CID = "asia-session-c2-protected-swing"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS)
    b_c2 = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).to_numpy()
    s_c2 = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).to_numpy()
    ok = d["p_ok"].to_numpy(bool) & (b_c2 ^ s_c2)
    ev = cisd_frame(m1, "1h")
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    ev = ev.sort_values("decision_time").reset_index(drop=True)
    e_dec = pd.DatetimeIndex(ev["decision_time"]).asi8
    e_ext = pd.DatetimeIndex(ev["extreme_time"]).asi8
    e_dir = ev["direction"].to_numpy()
    e_px = ev["extreme_price"].to_numpy(float)
    tn = m1.index.asi8
    lo, hi = m1["low"].to_numpy(float), m1["high"].to_numpy(float)
    rows = []
    for i in np.flatnonzero(ok):
        r = d.iloc[i]
        s = 1 if b_c2[i] else -1
        start, close = d.index[i].value, pd.Timestamp(r["close_time"]).value
        a = np.searchsorted(e_dec, start, side="left")
        b = np.searchsorted(e_dec, close, side="right")
        want = "bullish" if s > 0 else "bearish"
        cand = [k for k in range(a, b) if e_dir[k] == want and e_ext[k] >= start]
        if not cand:
            continue
        k = cand[-1]
        swing = float(e_px[k])
        j0 = np.searchsorted(tn, e_dec[k], side="left")
        j1 = np.searchsorted(tn, close, side="left")
        if j1 > j0:
            if s > 0 and lo[j0:j1].min() < swing:
                continue
            if s < 0 and hi[j0:j1].max() > swing:
                continue
        tgt = float(r["high"] if s > 0 else r["low"])
        if s * (tgt - float(r["close"])) <= 0 or s * (float(r["close"]) - swing) <= 0:
            continue
        ct = pd.Timestamp(r["close_time"])
        rows.append({"decision_time": ct, "available_at": ct, "direction": s,
                     "stop_px": swing, "target_px": tgt})
    return pd.DataFrame(rows, columns=COLS)


OP = {"rules": [
    "daily candles on the 18:00 NY roll; stub days (<600 M1) dropped; previous day = the "
    "preceding real session",
    "day D = one-sided daily C2 closure (spec §3.2)",
    "protected swing = extreme of the latest same-direction 1h CISD (series_open, 2/2, "
    "max_wait 3) with extreme inside D and confirmation closed by D's close; it must be "
    "intact (not traded through on M1) at D's close",
    "decide at D's close; enter next M1 open (18:00 NY, Asia) in D's direction; stop = the "
    "protected swing; target = D's bias-side extreme; no-room rows dropped; exit after 1380 "
    "trading M1 bars (hold_basis='bars'); control holds the NY clock (+/-30 min)"],
    "params": {"stub_filter_min_m1": MIN_DAY_M1, "ltf": "1h", "level_rule": "series_open",
               "swing": "2/2", "max_wait": 3, "min_series": 1, "swing_pick": "latest",
               "target": "D bias-side extreme", "max_hold": "1380min", "hold_basis": "bars",
               "ctrl_tod_tol_min": 30}}
SRC = {"stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
       "ltf": "corpus: timeframes.ltf [1H, 15m]; 1H first listed; method_spec §2.4 hourly CISD",
       "level_rule": "phase3: locked CISD level rule (first-candle open), method_spec §4.2",
       "swing": "phase3: locked swing fractal left=2,right=2",
       "max_wait": "phase3: locked max_wait=3",
       "min_series": "phase3: locked min_series=1",
       "swing_pick": "method_spec: §3.8 'Each new protected swing supersedes the last as the "
                     "invalidation'",
       "target": "corpus: execution.targets 'Expansion of the following daily candle (candle 3)'",
       "max_hold": "declared-before-run: the following daily candle only",
       "hold_basis": "declared-before-run: README trap 7 — holds cross the halt/weekend",
       "ctrl_tod_tol_min": "declared-before-run: every entry sits at the 18:00 reopen; hold "
                           "the NY clock fixed (README trap 9)"}

if __name__ == "__main__":
    ev = cl.cache_frame("asia_c2_protected_v1", lambda: detect(cl.load_m1()))
    ev = ev[pd.DatetimeIndex(ev["decision_time"]) <= cl.load_m1().index[-1]].reset_index(drop=True)  # the data\'s last, unfinished day
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="1380min", hold_basis="bars", ctrl_tod_tol_min=30)
    show(res)
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="Entry at the next daily open by market order (execution 'at or "
                              "near the protected swing before or around the next daily open'); "
                              "no FVG requirement (not stated).")
    print(p)
