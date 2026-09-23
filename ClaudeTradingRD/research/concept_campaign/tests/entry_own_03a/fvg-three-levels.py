"""fvg-three-levels — rate_test with a geometry-matched null.

Claim (+): a fair value gap is respected on its first return: price that reaches
into the gap (near edge -> CE -> full fill, all accepted) continues away — back to
the extreme of the leg that created it — before any 15m candle CLOSES beyond the
gap's far edge (his invalidation: 'closes ... outside the fair value gap').

Detector: 15m three-candle FVGs (wicks). Decision = close of the first M1 bar that
trades into the near edge, within 1440 M1 bars of the gap's third candle closing.
Outcome (race, next 16 x 15m bars): M1 high >= leg extreme (bullish) before a 15m
close < gap far edge. Null: at matched random moments (+/-30 d), the same two
distances from the price there, same 16-bar race.
All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402

TF = "15min"
RETURN_BARS = 1440     # first return must come within ~1 trading day of M1 bars
RACE_BARS = 16         # outcome window: the next 16 x 15m candles (4 trading hours)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    fv = fair_value_gaps(b[["open", "high", "low", "close"]])
    fv["close_time"] = b["close_time"]
    mkt = cl.get_market(m1)
    rows = []
    for bull in (True, False):
        g = fv[fv["bullish_fvg" if bull else "bearish_fvg"]]
        t0 = pd.DatetimeIndex(g["close_time"])
        near = (g["gap_high"] if bull else g["gap_low"]).to_numpy(float)
        far = (g["gap_low"] if bull else g["gap_high"]).to_numpy(float)
        tc = cl.touch(t0, near, "below" if bull else "above",
                      horizon_bars=RETURN_BARS, m1=m1)
        hit = tc["hit"].to_numpy()
        i0 = mkt.pos_at_or_after(t0)
        ih = mkt.pos_at_or_after(pd.DatetimeIndex(tc["hit_time"]))
        for j in np.flatnonzero(hit):
            a, h = i0[j], ih[j]
            if h <= a:                      # touched on the very first bar after the gap
                continue
            leg = mkt.h[a:h].max() if bull else mkt.l[a:h].min()
            rows.append((t0[j], mkt.t[h] + pd.Timedelta(minutes=1),
                         1 if bull else -1, near[j], far[j], leg, mkt.c[h]))
    cols = ["fvg_time", "decision_time", "direction", "near_edge", "far_edge", "leg_extreme",
            "touch_close"]
    ev = pd.DataFrame(rows, columns=cols)
    if ev.empty:
        return ev.assign(available_at=pd.Series(dtype="datetime64[ns, UTC]"))
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    ev["available_at"] = ev["decision_time"]
    d = ev["direction"].to_numpy()
    # the touch bar must close still inside/at the gap side (not already beyond the far edge)
    ok = (d * (ev["touch_close"] - ev["far_edge"]) > 0) & (d * (ev["leg_extreme"] - ev["touch_close"]) > 0)
    ev = ev[ok].sort_values("decision_time").reset_index(drop=True)
    return ev


def race(times, up_dist, dn_dist, direction, m1=None, b15=None) -> np.ndarray:
    """From the first M1 open at/after each time: 1 if price travels `up_dist` in
    `direction` (M1 extreme) before a 15m close beyond `dn_dist` against it, within the
    next RACE_BARS 15m candles closing after the time; 0 otherwise."""
    mkt = cl.get_market(m1)
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    ok = ~t.isna()
    out = np.full(len(t), np.nan)
    tn = cl.data.utc_ns(t[ok])
    i0 = mkt.pos_at_or_after(t[ok])
    good = i0 < len(mkt.o)
    idx = np.flatnonzero(ok)[good]
    tn, i0 = tn[good], i0[good]
    ref = mkt.o[i0]
    dr = np.asarray(direction)[idx]
    tgt = ref + dr * np.asarray(up_dist)[idx]
    inv = ref - dr * np.asarray(dn_dist)[idx]
    ct = cl.data.utc_ns(pd.DatetimeIndex(b15["close_time"]))
    cc = b15["close"].to_numpy(float)
    k0 = np.searchsorted(ct, tn, side="right")            # first 15m close after t
    kend = np.minimum(k0 + RACE_BARS, len(ct)) - 1
    until = pd.DatetimeIndex(cl.data.from_ns(ct[kend]))
    # first 15m close beyond the invalidation
    inv_t = np.full(len(idx), np.iinfo(np.int64).max)
    for r in range(len(idx)):
        seg = cc[k0[r]:kend[r] + 1]
        bad = np.flatnonzero(seg < inv[r]) if dr[r] == 1 else np.flatnonzero(seg > inv[r])
        if len(bad):
            inv_t[r] = ct[k0[r] + bad[0]]
    up = np.where(dr == 1, 1, 0).astype(bool)
    hit_t = np.full(len(idx), np.iinfo(np.int64).max)
    for side, sel in (("above", up), ("below", ~up)):
        if sel.any():
            tc = cl.touch(pd.DatetimeIndex(cl.data.from_ns(tn[sel])), tgt[sel], side,
                          until=until[sel], m1=m1)
            ht = cl.data.utc_ns(pd.DatetimeIndex(tc["hit_time"]))
            h = tc["hit"].to_numpy()
            v = np.full(sel.sum(), np.iinfo(np.int64).max)
            v[h] = ht[h] + 60_000_000_000        # hit known at that M1 bar's close
            hit_t[sel] = v
    res = (hit_t < inv_t) & (hit_t < np.iinfo(np.int64).max)
    out[idx] = res.astype(float)
    return out


if __name__ == "__main__":
    ev = cl.cache_frame(f"fvg3_{TF}_r{RETURN_BARS}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    b15 = cl.bars(TF)
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy()
    # geometry from the touch bar's close (known at the decision); both the real race
    # and the null race apply these distances from the first M1 open at/after the time
    up_dist = d * (ev["leg_extreme"].to_numpy() - ev["touch_close"].to_numpy())
    dn_dist = d * (ev["touch_close"].to_numpy() - ev["far_edge"].to_numpy())
    obs = race(t, up_dist, dn_dist, d, b15=b15)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        return race(tk, up_dist, dn_dist, d, b15=b15)

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "15m bars; FVG = three candles whose 1st and 3rd wicks do not overlap (detectors.primitives.fair_value_gaps)",
        "first return: first M1 bar within 1440 M1 bars after the 3rd candle closes that trades into the near edge "
        "(bullish: low <= gap high); decision = that M1 bar's close; skip if it closes beyond the far edge",
        "leg extreme = most extreme price between the gap's completion and the touch (the move the gap left behind)",
        "outcome = 1 if price then reaches the leg extreme (M1 high/low) before any 15m candle closes beyond the far "
        "edge, within the next 16 15m candles; else 0 (distances measured from the touch close, applied from the "
        "next M1 open)",
        "null = same up/down distances and same 16-candle race from the next M1 open at matched random moments "
        "(+/-30 d, 5 reps, locked seed)"],
        "params": {"tf": TF, "return_bars": RETURN_BARS, "race_bars": RACE_BARS,
                   "invalidation": "15m close beyond far edge", "target": "leg extreme"}}
    src = {"tf": "corpus: ZVUDpCyvxfQ ltf 15m (concept timeframes 1D/4H/1H over 15m/5m/1m)",
           "return_bars": "declared-before-run: a gap's first return counted within about one trading day",
           "race_bars": "declared-before-run: 16 entry-TF candles = 4 trading hours for the reaction to resolve",
           "invalidation": "corpus: ZVUDpCyvxfQ / consequent-encroachment 'closes ... outside the fair value gap' = invalidate; "
                           "all three depths (near edge, CE, full fill) accepted",
           "target": "declared-before-run: 'price continues away' -> back to the extreme of the leg that left the gap"}
    notes = ("Three-level reaction concept tested as one rate: all three accepted depths share the far-edge close "
             "invalidation, so the rate covers near-edge, CE and full-fill returns together. Adjacent gaps are not merged.")
    p = cl.write_result("fvg-three-levels", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("wrote", p)
