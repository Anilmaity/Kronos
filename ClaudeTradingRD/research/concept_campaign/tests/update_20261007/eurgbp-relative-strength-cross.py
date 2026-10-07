"""eurgbp-relative-strength-cross — update_20261007, reading u1007a (new claim only).

New claim (shorts_01, N8Wp_7vHYTk): the bearish EURGBP daily read is held "as long as it remains
in respect to 0.5 of this range" — the cross's read stays valid only while price has not closed
back through the 50% level of the cross's daily candle. Everything else (dollar direction, cross
selects the weaker leg, cross-check of individual closures) is the library entry, already run as
readings a/b; it is NOT re-tested here.

Transfer (identical to prior reading a, structure_own_05a): no GBP/EURGBP is tradeable in the
harness, so the pair is gold vs silver and the cross is the XAU/XAG hourly-close line. Universe =
exactly prior reading a's GATED arm: bare 1h CISD gold trades, dollar directional (= -EURUSD
previous-candle closure class), trade opposite the dollar, XAU/XAG line made a directional
daily closure that agrees with the trade (the cross selects gold).
New gate (u1007a): since that cross day closed, no XAU/XAG hourly close (up to the CISD decision)
has gone through 0.5 of the cross day's full range (bearish read: no close above EQ; bullish: none
below). Complement: the cross read was already invalidated by a close through EQ. claim '+'.
Rows whose hold window holds no hourly ratio close are dropped (never evaluated != passed).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import H1, cl, corr_h1, np, pd, summary  # noqa: E402
import _fx  # noqa: E402

CID = "eurgbp-relative-strength-cross"
READING = "u1007a"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "usd", "ratio",
        "read_avail", "eq", "w_ext", "n_hold", "gate_avail", "hold"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ev = _fx.cisd_book(m1)
    rd = _fx.daily_reads(m1)
    if ev.empty or rd.empty:
        return pd.DataFrame(columns=COLS)
    g1 = cl.build_bars(m1, "1h")
    xag = corr_h1("xag", m1, drop_halt_hour=True)
    rt = _fx._line_daily(g1["close"], xag["close"])            # same cross candle prior reading a read
    j = pd.concat([g1["close"].rename("n"), xag["close"].rename("d")], axis=1, join="inner").sort_index()
    line = (j["n"] / j["d"]).to_numpy(float)                  # hourly XAU/XAG closes
    ends = (pd.DatetimeIndex(j.index).tz_convert("UTC") + H1).as_unit("ns").asi8

    # attach the previous completed day's reads exactly as _fx.book_with_reads does, keeping the day
    days = rd.index.to_numpy()
    k = np.searchsorted(days, ev["bar_day"].to_numpy(), side="left") - 1
    ok = k >= 0
    ev, k = ev[ok].reset_index(drop=True), k[ok]
    gap = (ev["bar_day"].to_numpy() - days[k]) / np.timedelta64(1, "D")
    r = rd.iloc[k].reset_index(drop=True)
    cd = rt.reindex(days[k]).reset_index(drop=True)
    ev = pd.concat([ev, r, cd[["high", "low", "close_time"]].rename(
        columns={"high": "x_hi", "low": "x_lo", "close_time": "x_close"})], axis=1)
    ev = ev[gap <= _fx.MAX_GAP_DAYS].reset_index(drop=True)
    ev["read_avail"] = pd.DatetimeIndex(ev["avail"]).tz_convert("UTC")
    ev = ev[pd.DatetimeIndex(ev["read_avail"]) <= pd.DatetimeIndex(ev["decision_time"])]

    # prior reading a's gated arm: directional dollar, trade with it, cross agrees (selects gold)
    d = ev["direction"].to_numpy()
    u = ev["usd"].to_numpy()
    x = ev["ratio"].to_numpy()
    ev = ev[(u != 0) & (d == -u) & (x != 0) & (x == d)].reset_index(drop=True)
    if ev.empty:
        return pd.DataFrame(columns=COLS)

    # hold window: hourly ratio closes ending in (cross day close, decision_time]
    lo = np.searchsorted(ends, pd.DatetimeIndex(ev["x_close"]).tz_convert("UTC").as_unit("ns").asi8, "right")
    hi = np.searchsorted(ends, pd.DatetimeIndex(ev["decision_time"]).as_unit("ns").asi8, "right")
    d = ev["direction"].to_numpy()
    eq = (ev["x_hi"].to_numpy(float) + ev["x_lo"].to_numpy(float)) / 2.0
    n_hold = hi - lo
    w_ext = np.full(len(ev), np.nan)
    last_end = np.full(len(ev), np.iinfo(np.int64).min, dtype=np.int64)
    for i in np.flatnonzero(n_hold > 0):
        seg = line[lo[i]:hi[i]]
        w_ext[i] = seg.max() if d[i] == -1 else seg.min()    # the side that would break the read
        last_end[i] = ends[hi[i] - 1]
    ev["eq"] = eq
    ev["w_ext"] = w_ext
    ev["n_hold"] = n_hold
    ev = ev[n_hold > 0].reset_index(drop=True)
    le = pd.DatetimeIndex(last_end[n_hold > 0], tz="UTC")
    ev["gate_avail"] = pd.DatetimeIndex(np.maximum(
        pd.DatetimeIndex(ev["read_avail"]).as_unit("ns").asi8, le.as_unit("ns").asi8), tz="UTC")
    dd = ev["direction"].to_numpy()
    ev["hold"] = np.where(dd == -1, ev["w_ext"].to_numpy() <= ev["eq"].to_numpy(),
                          ev["w_ext"].to_numpy() >= ev["eq"].to_numpy()).astype(bool)
    return ev[COLS].reset_index(drop=True)


def main():
    ev = cl.cache_frame("eurgbp_u1007a_cisd1h_hold05", lambda: detect(cl.load_m1()))
    fire = float(ev["hold"].mean())
    print("book", len(ev), "gated", int(ev["hold"].sum()), "firing", round(fire, 3),
          "n_hold median", float(ev["n_hold"].median()))
    # independent recount of the gate from raw columns (trap 5)
    chk = np.where(ev["direction"] == -1, ev["w_ext"] <= ev["eq"], ev["w_ext"] >= ev["eq"])
    assert (chk == ev["hold"].to_numpy()).all()
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "hold", mask_available_at="gate_avail", max_hold=_fx.MAX_HOLD,
                       claim="+", ctrl_tod_tol_min=30)
    print(summary(res))
    op = {"rules": [
        "baseline: bare 1h CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming bar's close, "
        "enter next M1 open, stop at the protected swing, 2R, 10h max hold",
        "reads = previous-candle closure class of the last completed 18:00-NY trading day before the CISD bar's day",
        "universe = prior reading a's gated arm: dollar = -(EURUSD read) directional, trade opposite the dollar, "
        "XAU/XAG line daily read directional AND equal to the trade direction (the cross selects gold)",
        "EQ = 0.5 of the cross day's full range on the XAU/XAG hourly-close line: (max + min hourly ratio close) / 2",
        "gate (hold): every XAU/XAG hourly close ending after the cross day closed and at/before the decision "
        "stays on the read's side of EQ (bearish read: <= EQ, bullish: >= EQ); complement: a close through EQ "
        "already invalidated the read; rows with no hourly ratio close in the window dropped",
        "control holds the NY clock (ctrl_tod_tol_min 30)"],
        "params": {"baseline_tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "rr": 2.0, "max_hold": _fx.MAX_HOLD, "dollar_proxy": "EURUSD inverted",
                   "cross": "XAU/XAG line", "strength_read": "daily previous-candle closure class",
                   "min_h1_per_day": _fx.MIN_H1, "eq_level": 0.5, "eq_reference": "full daily range",
                   "respect": "no hourly close through EQ", "ctrl_tod_tol_min": 30}}
    src = {"baseline_tf": "phase3: rung-0 1h CISD book (calibrated)",
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config", "rr": "phase3: 2R (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "dollar_proxy": "declared-before-run: no DXY series; EURUSD is DXY's largest component (as prior readings a/b)",
           "cross": "declared-before-run: transfer EU/GU -> XAU/XAG as prior reading a; silver is the method's sanctioned gold correlate (method_spec §2.6)",
           "strength_read": "corpus: nWHint4Yano / 25V-sGyMj_M 'Read EURGBP direction using a daily C2/C3 closure'; method_spec §2.3 closure class (as prior reading a)",
           "min_h1_per_day": "declared-before-run: stub-day guard (as prior readings)",
           "eq_level": "corpus: N8Wp_7vHYTk 'as long as it remains in respect to 0.5 of this range.'",
           "eq_reference": "threshold_fits: 'Default reference is 50% of the candle' (wick branch only for large wicks); corpus N8Wp_7vHYTk 'this range'",
           "respect": "declared-before-run: disrespect = a close through the level, as half-wick-respect a (corpus yaml 'A close through 0.5 of the wick counts as disrespect'); the cross line only has hourly closes",
           "ctrl_tod_tol_min": "declared-before-run: the hold gate ages with hours elapsed since the cross day closed (more closes, more chances to break EQ), so gated trades sit earlier in the NY day; README trap 9 / vault Session Timing on Gold - hold the NY clock in the control"}
    p = cl.write_result(CID, READING, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"New claim only: the 0.5-of-range hold on the cross. Gate firing rate {fire:.3f} of {len(ev)} "
                              "(universe = prior reading a's selected arm, rows lacking an hourly ratio close in the "
                              "window dropped). Transfer EURGBP -> XAU/XAG line, as prior reading a; the cross's "
                              "daily range is the hourly-close line's range, not a true OHLC range. Not re-tested: "
                              "the EURUSD-bearish / GBPUSD-bullish closure cross-check (prior reading b) and the LTF "
                              "fractal-model execution (no timeframe named). Single reading: threshold_fits settles "
                              "body-vs-range as 50% of the candle.")
    print("wrote", p)


if __name__ == "__main__":
    main()
