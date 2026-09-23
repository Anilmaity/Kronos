"""seven-hour-candle-daily-profile (guest: DTR, 07lOxv39LdY; device credited to AM Trades).

"This candle here is the 1:00 candle, 1:00 a.m. to 8:00 a.m., that is the London candle
... this is a London C2 candle which to me is a London reversal ... since this was a
London reversal we want to see that 50% of the previous candle, which is the 7-hour
candle, 50% of that candle is respected; in this case because it was such a large wick
on that candle I would use 50% of the wick ... New York open ran up to that 50% and then
started to reverse off of that 50%."

Measurable (yaml): "how often the 50 percent of the previous 7-hour candle is respected
on a classified London reversal". rate_test, claim '+', declared before the run:
  7h grid   anchored on the 18:00 NY roll: Asia 18:00-01:00, London 01:00-08:00,
            New York 08:00-15:00 (15:00-17:00 is the remainder before the halt). The
            01:00 London candle is exactly as he states; 18:00 anchoring makes the
            candle before it start at the daily reopen.
  London reversal (C2): bearish = London high > Asia high AND London close < Asia high,
            London low >= Asia low (one side taken only); bullish mirrored. Each 7h
            candle needs >= 210 of its 420 M1 bars.
  reference = 50% of the London candle (the candle previous to New York), or 50% of its
            sweep wick when that wick is large: opposing run (open -> sweep extreme) /
            |body| > 1.0 (threshold_fits grade-A cut). Bearish: wick = [max(o,c), high].
            Row kept only if the London close is on the reversal side of the reference.
  outcome   RESPECTED = no New York M1 CLOSE beyond the reference during 08:00-15:00 NY
            (his invalidation is a close through the 50%).
  null      same distance from the 08:00 open to the level, same side, same number of
            M1 bars, at matched random moments (+/-30d) with the NY clock held within
            30 min of 08:00 (so the null is 'any New York morning', not the London C2).
The 7h FVG context and the NY-reversal branch are not modelled (no thresholds stated).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, show  # noqa: E402

CID = "seven-hour-candle-daily-profile"
TZ = "America/New_York"
MIN_BARS = 210
WICK_CUT = 1.0
NY_BARS_H = 7


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "level", "large_wick"]
    empty = pd.DataFrame(columns=cols)
    if len(m1) < 1000:
        return empty
    t = pd.DatetimeIndex(m1.index)
    mod = cl.ny_minute_of_day(t)
    sd = cl.session_date(t)
    asia = (mod >= 1080) | (mod < 60)
    lon = (mod >= 60) & (mod < 480)
    o, h, l, c = (m1[k].to_numpy() for k in ("open", "high", "low", "close"))

    def agg(sel):
        g = pd.DataFrame({"o": o[sel], "h": h[sel], "l": l[sel], "c": c[sel]}, index=sd[sel])
        return g.groupby(level=0).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"),
                                      c=("c", "last"), n=("o", "size"))
    A, L = agg(asia), agg(lon)
    A, L = A[A["n"] >= MIN_BARS], L[L["n"] >= MIN_BARS]
    j = L.join(A, rsuffix="_a", how="inner")
    if j.empty:
        return empty
    bear = (j["h"] > j["h_a"]) & (j["c"] < j["h_a"]) & (j["l"] >= j["l_a"])
    bull = (j["l"] < j["l_a"]) & (j["c"] > j["l_a"]) & (j["h"] <= j["h_a"])
    j = j[bear | bull].copy()
    j["direction"] = np.where(bear[bear | bull], -1, 1)
    body = (j["c"] - j["o"]).abs()
    opp = np.where(j["direction"] < 0, j["h"] - j["o"], j["o"] - j["l"])
    with np.errstate(divide="ignore", invalid="ignore"):
        large = np.where(body > 0, opp / body.to_numpy() > WICK_CUT, True)
    mid = (j["h"] + j["l"]) / 2
    wick_mid = np.where(j["direction"] < 0, (np.maximum(j["o"], j["c"]) + j["h"]) / 2,
                        (np.minimum(j["o"], j["c"]) + j["l"]) / 2)
    j["level"] = np.where(large, wick_mid, mid)
    j["large_wick"] = large
    ok = np.where(j["direction"] < 0, j["c"] < j["level"], j["c"] > j["level"])
    j = j[ok]
    dec = (pd.DatetimeIndex(j.index).tz_localize(TZ) + pd.Timedelta(hours=8)).tz_convert("UTC")
    out = pd.DataFrame({"decision_time": dec, "available_at": dec,
                        "direction": j["direction"].to_numpy(), "level": j["level"].to_numpy(),
                        "large_wick": j["large_wick"].to_numpy(bool)})
    last_t = t[-1] + pd.Timedelta("1min")
    return out[out["decision_time"] <= last_t].reset_index(drop=True)


def crossed(mkt, i0, nb, level, direction):
    """1.0 if any M1 close in [i0, i0+nb) is beyond level against `direction`."""
    N = len(mkt.c)
    out = np.full(len(i0), np.nan)
    for k in range(len(i0)):
        a, b = int(i0[k]), int(min(i0[k] + nb[k], N))
        if a >= N or b - a < 60 or not np.isfinite(level[k]):
            continue
        seg = mkt.c[a:b]
        out[k] = float((seg > level[k]).any() if direction[k] < 0 else (seg < level[k]).any())
    return out


if __name__ == "__main__":
    mkt = cl.get_market()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "bear share", (ev.direction < 0).mean(), "large wick", ev.large_wick.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    t = pd.DatetimeIndex(ev["decision_time"])
    i0 = mkt.pos_at_or_after(t)
    endt = t + pd.Timedelta(hours=NY_BARS_H)
    nb = (mkt.pos_at_or_after(endt) - i0).astype(np.int64)
    lvl = ev["level"].to_numpy(float)
    dirn = ev["direction"].to_numpy()
    obs = 1.0 - crossed(mkt, i0, nb, lvl, dirn)
    px0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = lvl - px0
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        g = np.flatnonzero(~tk.isna())
        ik = mkt.pos_at_or_after(tk[g])
        ok = ik < len(mkt.o)
        g, ik = g[ok], ik[ok]
        out[g] = 1.0 - crossed(mkt, ik, nb[g], mkt.o[ik] + dist[g], dirn[g])
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn, claim="+", predictors=ev)
    show(res)
    op = {"rules": [
        "7h candles anchored on the 18:00 NY roll: Asia 18:00-01:00, London 01:00-08:00, NY 08:00-15:00 (>= 210 M1 bars each)",
        "London reversal (C2): bearish = London high > Asia high, London close < Asia high, London low >= Asia low; bullish mirrored",
        "reference = 50% of the London candle; 50% of its sweep wick when opposing run (open->sweep extreme)/|body| > 1.0; "
        "kept only if the London close is on the reversal side of it",
        "respected = no NY M1 close beyond the reference 08:00-15:00 NY",
        "null = same distance/side/bar count at matched random moments (+/-30d, NY clock within 30 min)"],
        "params": {"anchor": "18:00 NY", "london": ["01:00", "08:00"], "min_bars": MIN_BARS,
                   "wick_cut": WICK_CUT, "ny_window_h": NY_BARS_H, "null_tod_tol_min": 30}}
    src = {"anchor": "declared-before-run: 18:00 NY roll (session_window_fit) - makes the 01:00 candle's predecessor start at the reopen",
           "london": "corpus: 07lOxv39LdY 'this candle here is the 1:00 candle so it's 1:00 a.m. to 8:00 a.m. that is the London candle'",
           "min_bars": "declared-before-run: half of a 7h candle's M1 bars present",
           "wick_cut": "threshold_fits: large wick = opposing_run/|body| > 1.0 (grade A); 0.5-of-wick branch per 07lOxv39LdY",
           "ny_window_h": "declared-before-run: the New York 7h candle (08:00-15:00)",
           "null_tod_tol_min": "declared-before-run: hold the NY clock near 08:00 so the null is any NY morning"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Underspecified concept (paid-course device). Only the one stated measurable "
                        "is scored: 50% respect on a classified London reversal. 7h FVG context not modelled. Timezone "
                        "assumed NY (the corpus convention).")
    print("wrote", p)
