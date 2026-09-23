"""monday-range-marker (guest: Jokerszn) -> two readings.

"The Monday high and low are marked every week and used as liquidity references for the
rest of the week ... bearish week: price trades above the Monday high, rejects, and runs
to the Monday low ... use the Monday low/high as the first take-profit reference."

Declared before the run:
  * Monday = the trading session whose session date is a Monday (Sunday 18:00 NY ->
    Monday 17:00 NY, the settled 18:00 roll). Weeks whose Monday is a stub (< 600 M1
    bars) are skipped. Week end = Friday 17:00 NY.
  reading a (rate_test, "liquidity references"): at the Monday close, is the Monday high
    (resp. low) traded through before the week ends? Null: the same signed distance from
    price at matched random moments (+/-30 d, locked), same number of tradable M1 bars —
    so the test asks whether Monday's extremes are special versus any level at the same
    distance. Two rows per week, clustered by week, outcome horizon 5D.
  reading b (trade_test, the sweep-reject-run pattern): Tue-Fri, the FIRST 1h candle
    (whole NY hours) that trades above the Monday high; if it closes back below the
    Monday high (sweep + rejection) -> short at its close; if it closes above, the side
    is invalidated for the week ("closes decisively beyond the Monday range"). Stop =
    that candle's high; target = the Monday low (the stated first take-profit).
    Bullish mirror on the Monday low. At most one trade per side per week; a candle that
    already trades through the opposite Monday extreme is skipped. Hold to the Friday
    17:00 NY close, measured in tradable minutes (hold_basis='bars', declared) so the
    controls get the same exposure across the daily halts.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import cl, np, pd, summary  # noqa: E402

CID = "monday-range-marker"
MIN_M1 = 600
TZ = "America/New_York"


def mondays(d: pd.DataFrame) -> pd.DataFrame:
    sd = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)
    mon = d[(sd.dayofweek == 0) & (d["n_m1"].to_numpy() >= MIN_M1)].copy()
    msd = pd.DatetimeIndex(mon["trading_day"]) + pd.Timedelta(days=1)
    fri = (msd + pd.Timedelta(days=4)).strftime("%Y-%m-%d")
    week_end = pd.DatetimeIndex([pd.Timestamp(f + " 17:00").tz_localize(TZ) for f in fri]).tz_convert("UTC")
    mon["week_end"] = week_end
    mon["week_id"] = msd.strftime("%Y-%m-%d")
    return mon


def tradable_minutes(t0: pd.DatetimeIndex, t1: pd.DatetimeIndex) -> np.ndarray:
    """Wall-clock minutes from t0 to t1 minus one hour per 17:00-NY halt in between
    (a calendar computation, independent of the data)."""
    wall = (t1 - t0).total_seconds().to_numpy() / 60.0
    a, b = t0.tz_convert(TZ), t1.tz_convert(TZ)
    # number of 17:00 NY moments in (a, b): count calendar days whose 17:00 lies inside
    first = a.normalize() + pd.Timedelta(hours=17)
    first = first.where(first > a, first + pd.Timedelta(days=1))
    k = np.floor(((b - first).total_seconds().to_numpy()) / 86400.0) + 1
    k = np.where(b > first, k, 0)
    # Friday 17:00 itself is the end (exclusive) — do not count it
    k = np.where((b.hour == 17) & (b.minute == 0) & (b > first), k - 1, k)
    return np.maximum(wall - 60.0 * np.maximum(k, 0), 1.0)


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    d = cl.build_bars(m1, "1D")
    h1 = cl.build_bars(m1, "1h")
    if len(d) < 2 or len(h1) < 2:
        return pd.DataFrame(columns=cols)
    mon = mondays(d)
    hs = cl.data.utc_ns(pd.DatetimeIndex(h1.index))
    hc = pd.DatetimeIndex(h1["close_time"])
    H, L, C = (h1[k].to_numpy() for k in ("high", "low", "close"))
    rows = []
    for _, r in mon.iterrows():
        mc = cl.data.utc_ns(pd.DatetimeIndex([r["close_time"]]))[0]
        we = cl.data.utc_ns(pd.DatetimeIndex([r["week_end"]]))[0]
        i0 = np.searchsorted(hs, mc, side="left")
        i1 = np.searchsorted(hs, we, side="left")
        if i1 <= i0:
            continue
        mh, ml = r["high"], r["low"]
        seg = slice(i0, i1)
        # bearish: first hour above Monday high
        up = np.flatnonzero(H[seg] > mh)
        if len(up):
            j = i0 + up[0]
            if C[j] < mh and L[j] > ml:
                rows.append((hc[j], -1, H[j], ml, r["week_end"]))
        dn = np.flatnonzero(L[seg] < ml)
        if len(dn):
            j = i0 + dn[0]
            if C[j] > ml and H[j] < mh:
                rows.append((hc[j], 1, L[j], mh, r["week_end"]))
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "week_end"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"])
    ev = ev[pd.DatetimeIndex(ev["decision_time"]) < pd.DatetimeIndex(ev["week_end"])]
    ev["available_at"] = ev["decision_time"]
    mins = tradable_minutes(pd.DatetimeIndex(ev["decision_time"]), pd.DatetimeIndex(ev["week_end"]))
    ev["max_hold"] = pd.to_timedelta(np.round(mins), unit="min")
    ev["direction"] = ev["direction"].astype(int)
    ev = ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return ev[cols]


def reading_a():
    mkt = cl.get_market()
    mon = mondays(cl.bars("1D"))
    t = pd.DatetimeIndex(mon["close_time"])
    we = pd.DatetimeIndex(mon["week_end"])
    i0 = mkt.pos_at_or_after(t)
    nb = mkt.pos_at_or_after(we) - i0
    ok = nb > 0
    mon, t, nb, i0 = mon[ok], t[ok], nb[ok], i0[ok]
    first_px = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    T = t.append(t)
    lvl = np.r_[mon["high"].to_numpy(), mon["low"].to_numpy()]
    side = np.r_[np.full(len(t), "above"), np.full(len(t), "below")]
    NB = np.r_[nb, nb]
    FP = np.r_[first_px, first_px]
    wid = np.r_[mon["week_id"].to_numpy(), mon["week_id"].to_numpy()]
    obs = np.empty(len(T))
    for s in ("above", "below"):
        m = side == s
        obs[m] = cl.touch(T[m], lvl[m], s, horizon_bars=NB[m])["hit"].to_numpy()
    dist = lvl - FP
    rt = cl.sample_times(T, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(T), np.nan)
        for s in ("above", "below"):
            m = (side == s) & ~tk.isna()
            px = mkt.o[mkt.pos_at_or_after(tk[m])]
            out[m] = cl.touch(tk[m], px + dist[m], s, horizon_bars=NB[m])["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, T, available_at=T, null_fn=null_fn, cluster=wid,
                       outcome_horizon="5D", claim="+")
    print("a", summary(res))
    op = {"rules": [
        "Monday = session dated Monday (18:00 NY roll), stubs < 600 M1 skipped",
        "at the Monday close: hit = Monday high (low) traded through before Friday 17:00 NY",
        "null = same signed distance from price at matched random moments (+/-30 d), same "
        "count of tradable M1 bars; two rows per week clustered by week"],
        "params": {"min_m1": MIN_M1, "week_end": "Fri 17:00 NY", "day_open_hour": 18}}
    src = {"min_m1": "declared-before-run: README trap 6 stub sessions",
           "week_end": "declared-before-run: the venue's weekly close",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src, script=__file__,
                        no_detector="pure level rule: Monday's high/low from bars('1D') at the "
                                    "Monday bar's close_time; no detector")
    print(p)


def reading_b():
    ev = cl.cache_frame("tg01c_monday_sweep_reject", lambda: detect(cl.load_m1()))
    print("b events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, hold_basis="bars")
    print("b", summary(res))
    op = {"rules": [
        "Monday range from the Monday session (18:00 NY roll); stubs skipped",
        "Tue-Fri: first 1h candle trading above the Monday high; if it closes back below it "
        "(and has not traded below the Monday low) -> short at its close; if it closes above, "
        "the side is invalidated for the week; bullish mirrored on the Monday low",
        "stop = that 1h candle's extreme; target = the opposite Monday extreme",
        "hold to Friday 17:00 NY in tradable minutes (hold_basis='bars')"],
        "params": {"trigger_tf": "1h", "stop": "sweep candle extreme",
                   "target": "opposite Monday extreme", "hold": "to Fri 17:00 NY",
                   "hold_basis": "bars", "min_m1": MIN_M1, "grid4h": "n/a"}}
    src = {"trigger_tf": "declared-before-run: 1h, the concept's first ltf",
           "stop": "declared-before-run: guest gives no stop; beyond the sweep candle",
           "target": "corpus: JABOO4LYNjQ Monday low/high as the first take-profit reference (concept detection rule 4)",
           "hold": "declared-before-run: the pattern is intraweek",
           "hold_basis": "declared-before-run: multi-day holds cross daily halts; bars basis gives controls equal tradable exposure",
           "min_m1": "declared-before-run: README trap 6 stub sessions",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Daily-order-flow context (which side the week is) is not "
                              "applied: both mirrored sides are traded.")
    print(p)


if __name__ == "__main__":
    reading_a()
    reading_b()
