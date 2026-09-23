"""risk_own_02a / harder-target-behind-protected-swing — rate_test (claim '-').

"This is a protected swing ... it's going to be a lot harder to get to this low" (U4j-fZD-FJk).
Claim: a liquidity target that sits BEHIND a protected swing (a swing that itself took
out a run of prior swings) is reached less often than a level at the same distance.
  bars           15m (the concept's LTF), 2/2 fractal swings, a swing known only once
                 its confirming (right) bar has closed
  decision       each trading day at 09:30 NY (NY-open live Q&A context), price = close
                 of the 15m bar ending 09:30
  candidates     untaken swing lows below price / untaken swing highs above price, formed
                 in the last 300 closed 15m bars (~3 trading days); 'untaken' = no later
                 closed 15m bar traded beyond it
  protected      a swing low below BOTH of the two preceding swing lows (it took out a run
                 of prior lows); mirrored for highs
  guarded        a candidate with an untaken protected swing strictly between it and price
  observed       each guarded candidate: touched before the trading day ends (17:00 NY)
  null           same distance, same side, same number of M1 bars, from price at 09:30 NY
                 on random days within +/-30 days (sample_times, time of day held fixed)
The 50%-of-bodies reaction zone is explicitly eyeballed and is not tested.
Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

DEC_HHMM = (9, 30)
LB_BARS = 300
RUN = 2


def detect(m1):
    cols = ["decision_time", "available_at", "level", "side", "dist", "price"]
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    sw = swing_points(b[["open", "high", "low", "close"]], 2, 2)
    ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"]))
    n = len(b)
    hi, lo, cl_ = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    avail = np.full(n, np.datetime64("2262-01-01", "ns"))
    pos = np.arange(n)
    for kind in ("swing_high", "swing_low"):
        m = sw[kind].to_numpy() & (pos + 2 < n)
        avail[m] = ct[pos[m] + 2]
    prot = {}
    for kind, px, lower in (("swing_low", lo, True), ("swing_high", hi, False)):
        idx = np.flatnonzero(sw[kind].to_numpy() & (pos + 2 < n))
        p = np.zeros(n, bool)
        for a in range(RUN, len(idx)):
            prev = px[idx[a - RUN:a]]
            p[idx[a]] = (px[idx[a]] < prev).all() if lower else (px[idx[a]] > prev).all()
        prot[kind] = p
    # decision times: 15m bars ending at 09:30 NY
    ny = cl.to_ny(pd.DatetimeIndex(b["close_time"]))
    dec = np.flatnonzero((ny.hour == DEC_HHMM[0]) & (ny.minute == DEC_HHMM[1]))
    rows = []
    for j in dec:                       # j = the 15m bar that closes at 09:30
        t = ct[j]
        P = cl_[j]
        a0 = max(0, j - LB_BARS + 1)
        for kind, px, below in (("swing_low", lo, True), ("swing_high", hi, False)):
            cand = np.flatnonzero(sw[kind].to_numpy()[a0:j + 1]) + a0
            cand = cand[avail[cand] <= t]
            keep = []
            for c in cand:
                later = lo[c + 1:j + 1] if below else hi[c + 1:j + 1]
                untaken = (later >= px[c]).all() if below else (later <= px[c]).all()
                if untaken and ((px[c] < P) if below else (px[c] > P)):
                    keep.append(c)
            keep = np.array(keep, int)
            if len(keep) < 2:
                continue
            pk = keep[prot[kind][keep]]
            for c in keep:
                lv = px[c]
                s = px[pk[pk != c]]
                guarded = ((s > lv) & (s < P)).any() if below else ((s < lv) & (s > P)).any()
                if guarded:
                    rows.append((t, lv, -1 if below else 1, abs(P - lv), P))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["t", "level", "side", "dist", "price"])
    dt = cl.data.from_ns(out["t"].to_numpy("datetime64[ns]"))
    out.insert(0, "decision_time", dt)
    out.insert(1, "available_at", dt)
    out = out.drop(columns="t").sort_values(["decision_time", "side", "level"]).reset_index(drop=True)
    return out


def price_at(times, m1):
    tn = cl.data.utc_ns(m1.index) + np.timedelta64(60, "s")       # M1 close times
    q = cl.data.utc_ns(pd.DatetimeIndex(times))
    p = np.searchsorted(tn, q, "right") - 1
    return np.where(p >= 0, m1["close"].to_numpy(float)[np.clip(p, 0, None)], np.nan)


def bars_left_in_day(times, m1):
    tn = cl.data.utc_ns(m1.index)
    td = cl.trading_day(m1.index)
    last = pd.Series(np.arange(len(tn))).groupby(td.to_numpy()).max()
    q = pd.DatetimeIndex(times)
    i0 = np.searchsorted(tn, cl.data.utc_ns(q), "left")
    end = last.reindex(cl.trading_day(q).to_numpy()).to_numpy()
    return (end - i0 + 1).astype(np.int64)


if __name__ == "__main__":
    ev = cl.cache_frame(f"hbps_{TF}_{DEC_HHMM}_lb{LB_BARS}_run{RUN}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["decision_time"].dt.date.nunique(), ev["side"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    m1 = cl.load_m1()
    t = pd.DatetimeIndex(ev["decision_time"])
    hb = bars_left_in_day(t, m1)
    side = ev["side"].to_numpy()
    lvl = ev["level"].to_numpy(float)
    dist = ev["dist"].to_numpy(float)
    assert np.allclose(price_at(t, m1), ev["price"].to_numpy()), "price convention mismatch"

    def hits(times, levels):
        h = np.zeros(len(levels), float)
        tt = pd.DatetimeIndex(times)
        ok = ~pd.isna(tt)
        for s_, nm in ((1, "above"), (-1, "below")):
            m = (side == s_) & ok
            if m.any():
                h[m] = cl.touch(tt[m], levels[m], nm, horizon_bars=hb[m])["hit"].to_numpy()
        h[~ok] = np.nan
        return h

    obs = hits(t, lvl)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=0)
    print("NaT draws", int(pd.isna(rt).sum()))

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        pk = price_at(tk, m1)
        return hits(tk, pk + side * dist)

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn, claim="-",
                       predictors=ev)
    show(res)
    params = {"ltf": TF, "swing": "2/2 fractal, known at confirming bar close",
              "decision_time_ny": "09:30", "candidate_lookback_15m_bars": LB_BARS,
              "protected_run": RUN, "untaken": "no later closed 15m bar beyond the level",
              "horizon": "until the trading day ends (17:00 NY), in M1 bars",
              "null": "sample_times +/-30d, tod_tol_min=0, same distance/side/bars from price at the draw",
              "grid4h": "n/a"}
    src = {"ltf": "corpus: harder-target-behind-protected-swing timeframes ltf 15m/5m",
           "swing": "phase3: locked 2/2 swing definition",
           "decision_time_ny": "declared-before-run: New York Open Live Q&A context (U4j-fZD-FJk), NY equity open",
           "candidate_lookback_15m_bars": "declared-before-run: ~3 trading days of 15m structure",
           "protected_run": "corpus: U4j-fZD-FJk protected swing = 'a low that took out a run of prior lows' (run = 2 preceding swings, declared-before-run)",
           "untaken": "declared-before-run: a target must still be resting liquidity",
           "horizon": "corpus: 'hit rate of targets ... on the same day' (measurable)",
           "null": "declared-before-run: geometry-matched null (README rate_test)",
           "grid4h": "declared-before-run: no 4h bars used"}
    op = {"rules": ["15m 2/2 swings; protected swing = swing beyond both of its 2 preceding same-side swings",
                    "at 09:30 NY each day: untaken swing lows below / highs above price from the last 300 closed 15m bars",
                    "guarded target = an untaken protected swing lies strictly between it and price",
                    "observed: guarded target touched before the trading day ends",
                    "null: same distance/side/M1-bar horizon from price at 09:30 NY on random days within +/-30d",
                    "claim -: targets behind a protected swing are reached less often"],
          "params": params}
    p = cl.write_result("harder-target-behind-protected-swing", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("Many rows share a day; the day-block CI handles it. The eyeballed "
                               "50%-of-bodies zone is not operationalisable and is not tested."))
    print("wrote", p)
