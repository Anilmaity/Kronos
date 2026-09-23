"""proximity-bias-nearest-extreme — rate_test.

Claim (X4XSsv5CNqg, worked live on gold): "Are we closer to previous month's low or
previous month's high? ... That's your bias, which you can have for the whole month",
held until that level is taken. Measurable (yaml): hit rate of the nearer previous-
month extreme being reached before the far one.

Operationalisation:
  * decision at every NY trading-day close (18:00 roll) while the bias is live: price
    strictly inside the previous month's range and neither the previous-month high nor
    low taken yet this month;
  * prediction: the NEARER of PMH / PML is reached first (before the far one) by the
    end of the current month (horizon in M1 bars). Neither reached = miss;
  * null (geometry): a random walk also reaches the nearer level first more often, so
    the null puts two levels at the SAME signed distances from the first price after a
    matched random moment (+/-30 d, NY time of day +/-30 min) with the same M1-bar
    horizon, scored the same way. Anything above the null is information, not geometry;
  * rows within a month share their levels -> cluster = month (one id per level pair).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    M = cl.build_bars(m1, "1M")
    Mi = pd.DatetimeIndex(M.index)
    ds = pd.DatetimeIndex(d.index)
    mpos = Mi.searchsorted(ds, side="right") - 1             # month row of each day
    mct = pd.DatetimeIndex(M["close_time"])
    dct = pd.DatetimeIndex(d["close_time"])
    dh, dl, dc = (d[k].to_numpy(float) for k in ("high", "low", "close"))
    Mh, Ml = M["high"].to_numpy(float), M["low"].to_numpy(float)
    # month-to-date extremes including day i
    key = pd.Series(mpos)
    mtd_h = pd.Series(dh).groupby(key).cummax().to_numpy()
    mtd_l = pd.Series(dl).groupby(key).cummin().to_numpy()
    rows = []
    for i in range(len(d)):
        k = mpos[i]
        if k < 0:
            continue
        if mct[k] <= dct[i]:
            # day i closed its month: next month starts, nothing taken yet
            prev, hi_td, lo_td = k, -np.inf, np.inf
        else:
            prev, hi_td, lo_td = k - 1, mtd_h[i], mtd_l[i]
        if prev < 0 or mct[prev] > dct[i]:
            continue
        if Mi[0] == Mi[prev] and pd.DatetimeIndex(m1.index)[0] > Mi[prev]:
            continue                                         # previous month is partial
        H, L, px = Mh[prev], Ml[prev], dc[i]
        if not (L < px < H) or hi_td >= H or lo_td <= L:
            continue
        near_high = (H - px) < (px - L)
        rows.append({"decision_time": dct[i], "available_at": dct[i],
                     "month_id": str(Mi[prev].date()),
                     "pmh": H, "pml": L, "near": 1 if near_high else -1})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "month_id", "pmh",
                                       "pml", "near"])


def first_hits(t, lvl_hi, lvl_lo, hb):
    a = cl.touch(t, lvl_hi, "above", horizon_bars=hb)
    b = cl.touch(t, lvl_lo, "below", horizon_bars=hb)
    return a, b


def score(near, a, b):
    ta = a["hit_time"].to_numpy()
    tb = b["hit_time"].to_numpy()
    ha, hb_ = a["hit"].to_numpy(), b["hit"].to_numpy()
    far_na = np.where(near > 0, ~hb_, ~ha)
    near_hit = np.where(near > 0, ha, hb_)
    near_first = np.where(near > 0, ta < tb, tb < ta)
    return (near_hit & (far_na | near_first)).astype(float)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame("prox_pm_v3", lambda: detect(cl.load_m1()))
    print(len(ev), ev["month_id"].nunique(), ev["near"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="75D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    p0 = mkt.pos_at_or_after(t)
    # outcome horizon only (not a predictor): end of the month in progress at t
    Mct = pd.DatetimeIndex(cl.bars("1M")["close_time"])
    k_end = np.minimum(Mct.searchsorted(t, side="right"), len(Mct) - 1)
    p1 = mkt.pos_at_or_after(Mct[k_end])
    hb = np.maximum(p1 - p0, 0)
    near = ev["near"].to_numpy()
    a, b = first_hits(t, ev["pmh"].to_numpy(), ev["pml"].to_numpy(), hb)
    obs = score(near, a, b)
    px = mkt.o[np.minimum(p0, len(mkt.o) - 1)]
    d_hi = ev["pmh"].to_numpy() - px
    d_lo = ev["pml"].to_numpy() - px
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        pxk = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        ak, bk = first_hits(tk[ok], pxk + d_hi[ok], pxk + d_lo[ok], hb[ok])
        out[ok] = score(near[ok], ak, bk)
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, cluster="month_id")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "dependence"):
        print(k, res.get(k))
    op = {"rules": [
        "at each NY trading-day close: previous calendar month's high/low (session-date months)",
        "live only while price is strictly inside that range and neither extreme has been "
        "taken month-to-date",
        "prediction: the nearer extreme is reached first by the end of the current month "
        "(M1-bar horizon); neither reached = miss",
        "null: same two signed distances from the first price after a matched random moment "
        "(+/-30 d, on-the-hour M1 grid), same M1 horizon, same scoring",
        "cluster = previous-month id (rows in a month share their levels)"],
        "params": {"period": "1M", "horizon": "to the current month's close",
                   "decision_grid": "daily close (18:00 NY)", "null_tod_tol_min": None,
                   "tie_rule": "strict nearer; equal distances -> low side"}}
    src = {"period": "corpus: X4XSsv5CNqg 'Are we closer to previous month's low or previous month's high?'",
           "horizon": "corpus: X4XSsv5CNqg 'That's your bias, which you can have for the whole month'",
           "decision_grid": "declared-before-run: one read per trading day while the bias is live",
           "null_tod_tol_min": "declared-before-run (re-run after bug fix): month-long horizon, time of day immaterial; exact-18:00 ToD matching found no bars after 2021 (reopen prints at 18:01+)",
           "tie_rule": "declared-before-run: no tie-break stated; exact ties are measure-zero"}
    p = cl.write_result("proximity-bias-nearest-extreme", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Monthly only, as demonstrated; the daily/weekly extension is not stated in the unit. "
                              "RE-RUN ONCE after a bug fix: the first run matched the null's NY time of day "
                              "(+/-30 min around 18:00) and silently lost 520/1021 rows after 2021 because "
                              "the reopen bar prints at 18:01+; that run read diff -0.087 [-0.184, +0.026] "
                              "UNDERPOWERED on n=501. ToD matching dropped (monthly horizon).")
    print("wrote", p)
