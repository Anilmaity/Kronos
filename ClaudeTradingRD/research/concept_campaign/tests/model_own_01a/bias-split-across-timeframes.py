"""bias-split-across-timeframes — Bias Can Be Opposite On Higher And Lower Timeframes (specified).

Claim ('+'): with an overall (higher-timeframe) bias toward a target, price first runs the
untaken liquidity on the OPPOSITE side; the tradeable bias is opposite until that
liquidity is grabbed and with the HTF bias immediately after. Conservative variant
(detection rule 5, execution): "skip the first leg entirely and wait for the grab" — so
HTF-direction entries taken AFTER the intervening liquidity is taken should beat the
same entries taken BEFORE it.

Test: gate_test on a baseline book (state it): on the session after a confirmed daily
bias (daily C2/C3 + H1 CISD; the 'overall target' = the prior day's bias-side extreme,
PDH for bullish), at every 1h close from 19:00 to 12:00 NY, go in the HTF-bias
direction toward that target, stop at the session's running opposite extreme
(execution.stop 'beyond the liquidity being grabbed'), exit 17:00 NY
(_common.intraday_bias_book).

Intervening liquidity (known at the session open): the NEAREST confirmed 1h 2/2 swing low
below the session's 18:00 open (bullish; swing high above for bearish) formed within
the prior 72 hours (relevant-swing-lookback: 'hourly chart -> three days') and confirmed
(its right-hand bar closed) before the session opened. Days without one have no
intervening liquidity and are not in the book.
Gate (known at the 1h close, pass or fail): the session's running low has traded below
that swing low (bullish) — the grab has happened.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import (cl, np, pd, OHLC, intraday_bias_book, swing_points,  # noqa: E402
                     MIN_RISK_FRAC, MIN_DAY_M1)

WIN = ("19:00", "12:00")
LOOKBACK_H = 72


def pools(m1):
    """Per trading day: nearest confirmed 1h swing low below / swing high above the day open."""
    h = cl.build_bars(m1, "1h")
    sw = swing_points(h[OHLC], left=2, right=2)
    one = pd.Timedelta(hours=1)
    lo = sw[sw["swing_low"] & sw["confirmed_at"].notna()]
    hi = sw[sw["swing_high"] & sw["confirmed_at"].notna()]
    lo_t, lo_k, lo_p = lo.index.asi8, (pd.DatetimeIndex(lo["confirmed_at"]) + one).asi8, lo["low"].to_numpy(float)
    hi_t, hi_k, hi_p = hi.index.asi8, (pd.DatetimeIndex(hi["confirmed_at"]) + one).asi8, hi["high"].to_numpy(float)
    td = cl.trading_day(h.index)
    first = pd.Series(h.index, index=td).groupby(level=0).min()
    dopen = pd.Series(h["open"].to_numpy(), index=td).groupby(level=0).first()
    rows = {}
    for day, s in first.items():
        sn, o = s.value, float(dopen.loc[day])
        w0 = sn - LOOKBACK_H * 3600 * 10**9
        m = (lo_k <= sn) & (lo_t >= w0) & (lo_p < o)
        pl = lo_p[m].max() if m.any() else np.nan
        m = (hi_k <= sn) & (hi_t >= w0) & (hi_p > o)
        ph = hi_p[m].min() if m.any() else np.nan
        rows[day] = (pl, ph)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["pool_low", "pool_high"])


def detect(m1):
    ev = intraday_bias_book(m1, WIN)
    pl = pools(m1).reindex(pd.DatetimeIndex(ev["x_tday"]))
    bull = ev["direction"].to_numpy() > 0
    pool = np.where(bull, pl["pool_low"].to_numpy(), pl["pool_high"].to_numpy())
    ev["x_pool"] = pool
    ev = ev[np.isfinite(pool)].reset_index(drop=True)
    bull = ev["direction"].to_numpy() > 0
    ev["grab_done"] = np.where(bull, ev["x_run_low"] < ev["x_pool"], ev["x_run_high"] > ev["x_pool"])
    return ev


ev = cl.cache_frame("bsplit_grab_gate", lambda: detect(cl.load_m1()))
print("events", len(ev), "gated", int(ev["grab_done"].sum()), "days", ev["x_tday"].nunique())
probe = cl.probe_lookahead(detect, ev, lookback="20D")
print("probe", probe.get("passed"))
res = cl.gate_test(ev, "grab_done", mask_available_at="decision_time", hold_basis="bars")
for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
          "ties", "exposure_bars", "ctrl_overlap", "halves", "dependence"):
    print(k, res.get(k))

op = {"rules": [
    "HTF bias: daily C2/C3 (C2-open ref) closure + same-direction 1h CISD inside that day; "
    "overall target = that day's bias-side extreme",
    "baseline: next session, every 1h close with NY close time 19:00-12:00; direction = HTF "
    "bias; stop = session running opposite extreme; target = the overall target; exit "
    "17:00 NY; drop rows with the target already reached / not beyond price / stop "
    "distance < 0.10 x prior-day range",
    "intervening liquidity: nearest 2/2 1h swing low below the session open (bullish; "
    "swing high above for bearish), swing bar within 72h before the session start and "
    "confirmed (right bar closed) by the session start; no such swing -> day not in book",
    "gate: session running low < that swing low (bullish) by the decision 1h close"],
    "params": {"window": "19:00-12:00 NY (1h closes)", "swing": "2/2", "pool_lookback_h": LOOKBACK_H,
               "min_risk_frac": MIN_RISK_FRAC, "stub_filter_min_m1": MIN_DAY_M1,
               "cisd_scope": "range", "c3_reference": "c2_open", "hold_basis": "bars"}}
src = {"window": "declared-before-run: whole session up to the NY-AM end (method_spec §2.5 window end 12:00)",
       "swing": "phase3: locked swing fractal left=2,right=2",
       "pool_lookback_h": "corpus: relevant-swing-lookback 'hourly chart -> three days' (method_spec §1.1)",
       "min_risk_frac": "declared-before-run: degenerate-stop guard, _common.MIN_RISK_FRAC",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions",
       "cisd_scope": "phase3: locked primary cisd_scope=range",
       "c3_reference": "phase3: locked primary C3 reference (Reading A)",
       "hold_basis": "declared-before-run: README trap 7 procedure — clock-basis run showed real/control exposure 774/702 bars (+10.3%), rerun with bars"}
p = cl.write_result("bias-split-across-timeframes", None, res, operationalization=op,
                    params_source=src, script=__file__, probe=probe,
                    notes="Tests the stated conservative variant (wait for the grab, then trade "
                          "the HTF leg) against entering the HTF leg before the grab. The "
                          "counter-leg itself has no stated entry/stop and is not traded. RE-RUN NOTE: the "
                          "first run (hold_basis=clock) gave diff +0.165 [+0.022,+0.318], "
                          "UNDERPOWERED (halves disagree H1 +0.364 / H2 -0.045) with real/control "
                          "exposure 774/702 bars (>10%); re-run once with hold_basis='bars' per "
                          "README trap 7. Both runs are in the ledger.")
print(p)
