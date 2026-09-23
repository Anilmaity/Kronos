"""original-consolidation-identification (guest: $niper) -> rate_test.

Claim tested (the concept's second `measurable`): when Asia's low sits together with the
previous daily low in a stretch of chop (buy model; mirrored for highs / sell model),
that block is the "original consolidation" and its extreme is engineered liquidity that
gets targeted later. claim '+' = the block's extreme is taken during the rest of the
trading day more often than a geometry-matched null.

Operationalisation (all declared before the run):
  * Asia = forex Asia killzone 20:00-00:00 NY (killzones.yaml / session_window_fit).
  * Previous daily low/high = last completed 18:00-NY trading day with coverage >= 0.5.
  * Coincide: |Asia low - PDL| <= 0.10 x ATR(20) of completed daily bars (same for highs).
  * Chop: Asia range <= 0.50 x daily ATR(20).
  * Level = min(Asia low, PDL) (buy model) / max(Asia high, PDH) (sell model).
  * Decision = Asia window end (00:00 NY). Hit = any M1 low <= level (high >= level) before
    the trading day ends (17:00 NY), horizon in M1 bars.
  * Null: same distance from price, same M1-bar horizon, at 5 matched random moments +/-30d.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TOL_ATR = 0.10
CHOP_ATR = 0.50
ATR_N = 20
ASIA = ("20:00", "00:00")
COLS = ["decision_time", "available_at", "direction", "level", "side_below", "day_end"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 0]
    if len(d) < ATR_N + 2:
        return pd.DataFrame(columns=COLS)
    pc = d["close"].shift(1)
    tr = np.maximum(d["high"] - d["low"],
                    np.maximum((d["high"] - pc).abs(), (d["low"] - pc).abs()))
    d = d.assign(atr=tr.rolling(ATR_N, min_periods=ATR_N).mean())
    w = cl.window_hilo(ASIA, m1)
    w = w[w["n_m1"] > 0]
    t = pd.DatetimeIndex(w["available_at"]).tz_convert("UTC")
    # decide at the close of the first M1 bar starting at/after the window's nominal end,
    # so the detector itself can see the window has ended (data gaps near the end)
    mi = m1.index
    j = np.searchsorted(mi.values, t.values, side="left")
    keep = j < len(mi)
    w, t, j = w[keep], t[keep], j[keep]
    dec = pd.DatetimeIndex(mi.values[j]).tz_localize("UTC") + pd.Timedelta(minutes=1)
    if len(w) == 0:
        return pd.DataFrame(columns=COLS)
    prev = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    atr = cl.asof(d[["atr", "close_time"]], t)["atr"].to_numpy()
    # trading_day is labelled by the NY date of its 18:00 roll; it ends the next
    # calendar day at 17:00 NY
    tdl = pd.DatetimeIndex(cl.trading_day(t))
    tdl = tdl.tz_localize(None) if tdl.tz is not None else tdl
    end_ny = (tdl.normalize() + pd.Timedelta(days=1, hours=17))
    day_end = end_ny.tz_localize("America/New_York", ambiguous="NaT",
                                 nonexistent="shift_forward").tz_convert("UTC")
    ah, al = w["high"].to_numpy(), w["low"].to_numpy()
    ph, pl = prev["high"].to_numpy(float), prev["low"].to_numpy(float)
    ok = np.isfinite(atr) & np.isfinite(ph) & np.isfinite(pl) & ((ah - al) <= CHOP_ATR * atr)
    rows = []
    for i in np.flatnonzero(ok):
        if abs(al[i] - pl[i]) <= TOL_ATR * atr[i]:
            rows.append((dec[i], t[i], 1, min(al[i], pl[i]), True, day_end[i]))
        if abs(ah[i] - ph[i]) <= TOL_ATR * atr[i]:
            rows.append((dec[i], t[i], -1, max(ah[i], ph[i]), False, day_end[i]))
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=COLS)
    ev = ev[ev["day_end"].notna() & (ev["day_end"] > ev["decision_time"])]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"origcons_tol{TOL_ATR}_chop{CHOP_ATR}_atr{ATR_N}", lambda: detect(m1))
    print(len(ev), ev.side_below.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    i0 = mkt.pos_at_or_after(t)
    i1 = mkt.pos_at_or_after(pd.DatetimeIndex(ev["day_end"]))
    hb = np.maximum(i1 - i0, 0)
    below = ev["side_below"].to_numpy(bool)
    lv = ev["level"].to_numpy(float)

    def hits(times, level, hbars):
        out = np.zeros(len(times), bool)
        for sb in (True, False):
            s = below == sb
            if s.any():
                out[s] = cl.touch(times[s], level[s], "below" if sb else "above",
                                  horizon_bars=hbars[s])["hit"].to_numpy()
        return out

    obs = hits(t, lv, hb).astype(float)
    px0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = lv - px0
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        okk = ~tk.isna()
        out = np.full(len(t), np.nan)
        idx = np.flatnonzero(okk)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[okk]), len(mkt.o) - 1)]
        sub = np.zeros(len(idx), bool)
        for sb in (True, False):
            s = below[idx] == sb
            if s.any():
                sub[s] = cl.touch(tk[okk][s], (px + dist[idx])[s], "below" if sb else "above",
                                  horizon_bars=hb[idx][s])["hit"].to_numpy()
        out[idx] = sub
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "Asia = 20:00-00:00 NY; previous day = last completed 18:00-NY trading day (coverage>=0.5)",
        "buy model: |Asia low - PDL| <= 0.10 daily ATR(20); sell model mirrored on highs",
        "chop: Asia range <= 0.50 daily ATR(20)",
        "level = the block's extreme (min of Asia low, PDL / max of Asia high, PDH)",
        "decide at the close of the first M1 bar at/after 00:00 NY; hit = level traded through before 17:00 NY that trading day",
        "null: same distance from price, same M1-bar horizon, 5 matched random moments +/-30d"],
        "params": {"asia": "20:00-00:00", "tol_atr": TOL_ATR, "chop_atr": CHOP_ATR,
                   "atr_n": ATR_N, "min_coverage": 0.5, "horizon": "to 17:00 NY, M1 bars"}}
    src = {"asia": "session_window_fit: forex Asia killzone 20:00-00:00 (killzones.yaml)",
           "tol_atr": "declared-before-run: 'coincide' never bounded; 0.10 daily ATR",
           "chop_atr": "declared-before-run: 'chop' never bounded; Asia range <= 0.5 daily ATR",
           "atr_n": "declared-before-run: ATR(20), threshold_fits trailing-window convention",
           "min_coverage": "declared-before-run: README trap 6, skip stub sessions",
           "horizon": "declared-before-run: the model completes within the trading day"}
    p = cl.write_result("original-consolidation-identification", None, res,
                        operationalization=op, params_source=src, script=__file__,
                        probe=probe,
                        notes="Tests the level claim only (block extreme gets targeted); "
                              "'chop' and 'coincide' are unbounded in the source and were declared. "
                              "Bug fix: first run had day_end one day early (trading_day label is the "
                              "roll date), which dropped every row (n=0); fixed and re-run once. Second fix before any "
                              "verdict: the probe caught a data-gap ambiguity at the window end; decision "
                              "moved to the close of the first M1 bar after 00:00 NY.")
    print(p)
