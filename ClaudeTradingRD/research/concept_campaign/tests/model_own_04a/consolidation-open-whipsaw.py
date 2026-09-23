"""consolidation-open-whipsaw — rate_test (batch model_own_04a).

Concept: on a no-bias day with price inside a pre-open range, the 09:30 open is
expected to consolidate: the NEARER extreme is swept first, then price rotates back
through the range toward the other extreme. Two measurable claims, each a reading:
  reading a: the nearer pre-open extreme is taken before the farther one
  reading b: both pre-open extremes are taken during the session (the rotation)
Both are geometric (the nearer level is nearer), so the null holds the geometry:
same distances above/below the reference price, same number of M1 bars, at a random
moment on another day within +/-30 days at the same NY clock (+/-15 min).

Declared operationalisation (before run):
  * no HTF bias = the prior completed daily candle (18:00 NY roll) is neither a C2
    closure nor a sequential C3 closure (method_spec §2.8)
  * pre-open range = high/low of the trading day from 18:00 NY to 09:30 NY
  * reference price = the last M1 close before 09:30; decision at 09:30:00 NY
  * horizon = the M1 bars from 09:30 to 16:00 NY that day
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.fractal import c2_events, c3_events

TZ = "America/New_York"
TOD_TOL = 15


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "rh", "rl", "ref", "near_up", "no_bias"]
    ny = m1.index.tz_convert(TZ)
    mod = ny.hour * 60 + ny.minute
    tday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize()     # 18:00 roll
    pre = (mod < 9 * 60 + 30) | (mod >= 18 * 60)
    x = m1[pre]
    g = x.groupby(tday[pre])
    agg = pd.DataFrame({"rh": g["high"].max(), "rl": g["low"].min(), "ref": g["close"].last(),
                        "n": g["close"].size(), "last": g.apply(lambda d: d.index[-1])})
    agg = agg[(agg["n"] >= 600) & (agg.index.dayofweek < 5)]
    dec = pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize(TZ) + pd.Timedelta(hours=9, minutes=30)
                            for d in agg.index]).tz_convert("UTC")
    last = pd.DatetimeIndex(agg["last"]).tz_convert("UTC")
    ok = (dec - last <= pd.Timedelta(minutes=5)) & (dec - last > pd.Timedelta(0))
    agg, dec = agg[np.asarray(ok)], dec[np.asarray(ok)]
    out = pd.DataFrame({"decision_time": dec, "available_at": dec,
                        "rh": agg["rh"].to_numpy(), "rl": agg["rl"].to_numpy(),
                        "ref": agg["ref"].to_numpy()})
    out = out[(out["rh"] > out["ref"]) & (out["rl"] < out["ref"])]
    out["near_up"] = (out["rh"] - out["ref"]) < (out["ref"] - out["rl"])
    # HTF bias from the prior completed daily candle
    d = cl.build_bars(m1, "1D")
    dd = d[["open", "high", "low", "close"]]
    biased = set(pd.DatetimeIndex(c2_events(dd)["time"])) | \
        set(pd.DatetimeIndex(c3_events(dd, mode="sequential")["time"]))
    dct = pd.DatetimeIndex(d["close_time"]).as_unit("ns")
    k = np.searchsorted(dct.asi8, pd.DatetimeIndex(out["decision_time"]).as_unit("ns").asi8,
                        side="right") - 1
    good = k >= 0
    out, k = out[good].copy(), k[good]
    out["no_bias"] = ~pd.Index(d.index[k]).isin(list(biased))
    out = out[out["no_bias"]]
    return out[cols].reset_index(drop=True)


def horizon_bars(times: pd.DatetimeIndex, mkt) -> np.ndarray:
    i0 = mkt.pos_at_or_after(times)
    loc = times.tz_convert(TZ)
    end = pd.DatetimeIndex([pd.Timestamp(t.date()).tz_localize(TZ) + pd.Timedelta(hours=16)
                            for t in loc]).tz_convert("UTC")
    return mkt.pos_at_or_after(end) - i0


def outcomes(t, ref, up_d, dn_d, near_up, hb):
    up = cl.touch(t, ref + up_d, "above", horizon_bars=hb)
    dn = cl.touch(t, ref - dn_d, "below", horizon_bars=hb)
    hu, hd = up["hit"].to_numpy(), dn["hit"].to_numpy()
    tu = np.where(hu, up["minutes"].to_numpy(float), np.inf)
    td = np.where(hd, dn["minutes"].to_numpy(float), np.inf)
    near_first = np.where(near_up, tu < td, td < tu)          # same-minute ties count as 0
    both = hu & hd
    return near_first.astype(float), both.astype(float)


def run():
    mkt = cl.get_market()
    ev = cl.cache_frame("openwhipsaw_nobias_days", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    t = pd.DatetimeIndex(ev["decision_time"])
    hb = horizon_bars(t, mkt)
    ref = ev["ref"].to_numpy()
    up_d = ev["rh"].to_numpy() - ref
    dn_d = ref - ev["rl"].to_numpy()
    near_up = ev["near_up"].to_numpy()
    obs_a, obs_b = outcomes(t, ref, up_d, dn_d, near_up, hb)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)
    cache = {}

    def null_k(k):
        if k not in cache:
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
            okk = ~tk.isna()
            a = np.full(len(t), np.nan)
            b = np.full(len(t), np.nan)
            pos = mkt.pos_at_or_after(tk[okk])
            rref = mkt.c[np.maximum(pos - 1, 0)]                 # last close before the moment
            na, nb = outcomes(tk[okk], rref, up_d[okk], dn_d[okk], near_up[okk], hb[okk])
            a[okk], b[okk] = na, nb
            cache[k] = (a, b)
        return cache[k]

    op_common = [
        "days: weekdays; no HTF bias = the prior completed 18:00-roll daily candle is neither a "
        "C2 closure nor a sequential C3 closure",
        "pre-open range = trading-day high/low from 18:00 NY to 09:30 NY (>=600 M1 bars); "
        "reference = last M1 close before 09:30; decision 09:30 NY",
        "horizon = M1 bars from 09:30 to 16:00 NY that day",
        "null = same distances above/below the reference, same bar count, at a random moment "
        "on another day within +/-30 days at the same NY clock +/-15 min"]
    params = {"range_start": "18:00", "range_end": "09:30", "horizon_end": "16:00",
              "day_open_hour": 18, "bias_rule": "prior daily C2 or sequential C3",
              "null_tod_tol_min": TOD_TOL, "null_window_days": 30}
    src = {"range_start": "method_spec: §1.4 daily candle opens 18:00 NY (canon)",
           "range_end": "corpus: xraklBJHW5k the 9:30 open (pre-open range)",
           "horizon_end": ("declared-before-run: the concept gives no time limit; 16:00 NY ends the "
                           "equity session the 09:30 anchor belongs to"),
           "day_open_hour": "session_window_fit: 18:00 NY roll settled",
           "bias_rule": "method_spec: §2.8 no daily C2/C3 closure -> no bias",
           "null_tod_tol_min": ("declared-before-run: hold the NY clock fixed so the null asks the "
                                "same question at the 09:30 open on other days (trap 9)"),
           "null_window_days": "phase3: locked +/-30-day regime window"}
    for reading, obs, idx, claim_txt in (
            ("a", obs_a, 0, "nearer pre-open extreme taken before the farther one"),
            ("b", obs_b, 1, "both pre-open extremes taken 09:30-16:00 (rotation)")):
        res = cl.rate_test(obs, t, available_at=ev["available_at"], predictors=ev,
                           null_fn=lambda rng, k, i=idx: null_k(k)[i])
        op = {"rules": [f"outcome: {claim_txt}"] + op_common, "params": params}
        p = cl.write_result("consolidation-open-whipsaw", reading, res, operationalization=op,
                            params_source=src, script=__file__, probe=probe,
                            notes="same-minute touches of both levels count as not-first in both arms")
        print(reading, p)
        for kk in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                   "verdict", "verdict_detail", "dependence"):
            print("  ", kk, res.get(kk))


if __name__ == "__main__":
    run()
