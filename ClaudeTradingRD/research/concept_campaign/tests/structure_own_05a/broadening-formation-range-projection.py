"""broadening-formation-range-projection (TTrades' own restatement) — batch structure_own_05a.

"I essentially just look for a range ... we're likely to reach for the other side of the
range" (1XWyy6Q-_8Q): mark a range, its high = buyside, its low = sellside; a run on one
side that FAILS and falls back inside makes the opposite side the objective; drop to a
lower timeframe for the entry toward it. Stuck inside = no trade.

rate_test (the yaml's first measurable; see notes for why not a trade_test):
  range     : the previous trading day (18:00 NY roll; stub sessions skipped, coverage>=0.5)
              - the yaml's first htf (1D) and the corpus's standard previous-candle range
  failed run: on the 15m (first listed ltf), during today, the running high has traded
              above PDH while today's low has NOT taken PDL, and a 15m candle CLOSES back
              below PDH (first such close of the day) -> short. Mirror for PDL -> long.
  hit       : the opposite side of the range trades within 720 M1 bars (12 trading hours)
  null      : same distance, same direction, matched random moments (+/-30d, NY ToD +/-30m)
  claim '+': the opposite side is reached more often than an equally distant level.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "broadening-formation-range-projection"
LTF = "15min"
HORIZON_BARS = 720
TOD_TOL = 30
MIN_COV = 0.5


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, LTF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(b["close_time"])
    lv = cl.prior_hilo(ct, "1D", m1=m1, min_coverage=MIN_COV)
    pdh, pdl = lv["high"].to_numpy(float), lv["low"].to_numpy(float)
    lv_av = pd.DatetimeIndex(lv["available_at"])
    td = cl.trading_day(b.index)
    rh = b["high"].groupby(td).cummax().to_numpy(float)
    rl = b["low"].groupby(td).cummin().to_numpy(float)
    c = b["close"].to_numpy(float)
    ok = np.isfinite(pdh) & np.isfinite(pdl)
    # the level must belong to the trading day just before this bar's day
    lvl_day = cl.trading_day(pd.DatetimeIndex(lv["period_start"]).tz_convert("UTC")
                             .fillna(pd.Timestamp("1970-01-01", tz="UTC")))
    ok &= np.asarray(lvl_day < td)
    short = ok & (rh > pdh) & (rl > pdl) & (c < pdh)
    long_ = ok & (rl < pdl) & (rh < pdh) & (c > pdl)
    rows = []
    for sel, d in ((short, -1), (long_, 1)):
        idx = np.flatnonzero(sel)
        if len(idx) == 0:
            continue
        f = pd.DataFrame({"i": idx, "td": td[idx]}).drop_duplicates("td", keep="first")
        i = f["i"].to_numpy()
        rows.append(pd.DataFrame({
            "decision_time": ct[i], "available_at": ct[i],
            "direction": d,
            "stop_px": (rh if d < 0 else rl)[i],
            "target_px": (pdl if d < 0 else pdh)[i],
            "lvl_avail": lv_av[i]}))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.concat(rows).sort_values(["decision_time", "direction"]).reset_index(drop=True)
    assert (pd.DatetimeIndex(out["lvl_avail"]) <= pd.DatetimeIndex(out["decision_time"])).all()
    return out[cols]


def main():
    mkt = cl.get_market()
    ev = cl.cache_frame(f"bfrp_{LTF}_cov{MIN_COV}", lambda: detect(cl.load_m1()))
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy(int)
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    tgt = ev["target_px"].to_numpy(float)
    dist = np.abs(tgt - px)                      # geometry the null must preserve
    print("events", len(ev), "target dist / stop dist quantiles",
          np.nanquantile(dist / np.abs(px - ev["stop_px"].to_numpy(float)), [.1, .5, .9]).round(2))

    def hit_at(times, level, dirs):
        out = np.zeros(len(times), bool)
        for dd, side in ((1, "above"), (-1, "below")):
            m = dirs == dd
            if m.any():
                out[m] = cl.touch(times[m], level[m], side, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    obs = hit_at(t, tgt, d).astype(float)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        pk = mkt.o[mkt.pos_at_or_after(tk[ok])]
        out[ok] = hit_at(tk[ok], pk + d[ok] * dist[ok], d[ok])
        return out

    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev, claim="+")
    print(summary(res))
    op = {"rules": [
        "range = previous trading day's high/low (18:00 NY roll; sessions with coverage < 0.5 skipped)",
        "failed run (short case): today's running high has traded above PDH, today's low has not "
        "taken PDL, and a 15m candle closes back below PDH (first such close of the day); mirror "
        "for PDL (long case)",
        "hit = the opposite side of the range (PDL for a failed buyside run, PDH for a failed "
        "sellside run) trades within the next 720 M1 bars (12 trading hours) from the 15m close",
        "null = a level at the same distance in the same direction from the price at matched "
        "random moments (+/-30d, NY time-of-day within 30 min), same bar horizon"],
        "params": {"range": "1D previous trading day", "ltf": LTF, "min_coverage": MIN_COV,
                   "horizon_bars": HORIZON_BARS, "null_tod_tol_min": TOD_TOL}}
    src = {"range": "corpus: 1XWyy6Q-_8Q 'I essentially just look for a range'; yaml htf 1D first; method_spec §2.3 previous-candle range",
           "ltf": "corpus yaml ltf 15m (first listed); 'drop to a lower timeframe to find the entry'",
           "min_coverage": "declared-before-run: README trap 6 stub-session guard",
           "horizon_bars": "declared-before-run: same-session objective, 12 trading hours",
           "null_tod_tol_min": "declared-before-run: README trap 9 (events cluster in session hours)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Tested as the yaml's first measurable (hit rate of the opposite range "
                              "extreme after a failed sweep and return) with a geometry-matched null, "
                              "because no stop is stated: with a stop at the run's extreme the "
                              "target/stop ratio has median ~7.5 (p90 ~28), so an R book would be "
                              "a lottery-ticket book decided by the stop choice, not the claim. This "
                              "choice was made after looking only at that geometry, before any outcome. "
                              "Boundary expansion and the continuation branch are not modelled.")
    print("wrote", p)


if __name__ == "__main__":
    main()
