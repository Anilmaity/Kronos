"""gold-daily-gap-reaction (ttrades, live_02) — rate_test, reading u1007a.

Claim (+): 'usually gold has been very very good about ... pulling back to daily gaps
and ... moving away from them'; after reaching into the daily gap, 'target this high up
here', 'probably tomorrow or maybe tonight in Asia'.  Measurable (draft): rate at which
XAUUSD reverses from a first touch of a daily FVG vs closes through it.

Detector: daily (18:00 NY roll) three-candle wick FVGs. Decision = close of the first M1
bar that trades into the gap's near edge, within RETURN_BARS M1 bars of the 3rd daily
candle closing (touch bar must not already close beyond the far edge).
Outcome: price reaches the swing high above (bullish; mirror for bearish) = the extreme
of the leg between gap completion and the touch, before any 1h candle closes beyond the
gap's far edge, within the next RACE_BARS 1h candles.  Null: same two distances from the
next M1 open at matched random moments (+/-30 d, 5 reps, locked seed), same race,
same NY time of day (+/-30 min).
All parameters declared before the first run.

AUDIT 2026-10-07 (vault context): the first run's null drew random moments without
holding the NY clock fixed, while the touches cluster 2.1-2.5x in 08:00-11:00 NY.
README trap 9 / vault 'Concept Campaign 2026-09-23' lesson 3 require a time-of-day
matched rate null for a non-timing concept -> NULL_TOD_TOL added. Nothing else changed.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                  # noqa: E402
from detectors.primitives import fair_value_gaps          # noqa: E402

CID, READING = "gold-daily-gap-reaction", "u1007a"
RETURN_BARS = 10 * 1380   # first return counted within ~10 trading days of M1 bars
RACE_TF = "1h"
RACE_BARS = 46            # ~2 trading days of 1h candles ('tonight in Asia' or 'tomorrow')
MIN_M1 = 600              # skip gaps built from stub sessions (trap 6)
NULL_TOD_TOL = 30         # null holds NY time of day +/-30 min (README trap 9)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    fv = fair_value_gaps(d[["open", "high", "low", "close"]])
    fv["close_time"] = d["close_time"]
    full = (d["n_m1"] >= MIN_M1)
    fv["ok"] = full & full.shift(1, fill_value=False) & full.shift(2, fill_value=False)
    mkt = cl.get_market(m1)
    rows = []
    for bull in (True, False):
        g = fv[fv["bullish_fvg" if bull else "bearish_fvg"] & fv["ok"]]
        if g.empty:
            continue
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
            if h <= a:
                continue
            leg = mkt.h[a:h].max() if bull else mkt.l[a:h].min()
            rows.append((t0[j], mkt.t[h] + pd.Timedelta(minutes=1),
                         1 if bull else -1, near[j], far[j], leg, mkt.c[h]))
    cols = ["fvg_time", "decision_time", "direction", "near_edge", "far_edge",
            "leg_extreme", "touch_close"]
    ev = pd.DataFrame(rows, columns=cols)
    if ev.empty:
        return ev.assign(available_at=pd.Series(dtype="datetime64[ns, UTC]"))
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    ev["available_at"] = ev["decision_time"]
    dr = ev["direction"].to_numpy()
    ok = (dr * (ev["touch_close"] - ev["far_edge"]) > 0) & \
         (dr * (ev["leg_extreme"] - ev["touch_close"]) > 0)
    return ev[ok].sort_values("decision_time").reset_index(drop=True)


def race(times, up_dist, dn_dist, direction, bx, m1=None) -> np.ndarray:
    """1 if price travels up_dist in `direction` (M1 extreme, from the first M1 open at/after
    t) before a RACE_TF close beyond dn_dist against it, within RACE_BARS closes; else 0."""
    mkt = cl.get_market(m1)
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    out = np.full(len(t), np.nan)
    ok = ~t.isna()
    tn = cl.data.utc_ns(t[ok])
    i0 = mkt.pos_at_or_after(t[ok])
    good = i0 < len(mkt.o)
    idx = np.flatnonzero(ok)[good]
    tn, i0 = tn[good], i0[good]
    ref = mkt.o[i0]
    dr = np.asarray(direction)[idx]
    tgt = ref + dr * np.asarray(up_dist)[idx]
    inv = ref - dr * np.asarray(dn_dist)[idx]
    ct = cl.data.utc_ns(pd.DatetimeIndex(bx["close_time"]))
    cc = bx["close"].to_numpy(float)
    k0 = np.searchsorted(ct, tn, side="right")
    kend = np.minimum(k0 + RACE_BARS, len(ct)) - 1
    until = pd.DatetimeIndex(cl.data.from_ns(ct[kend]))
    BIG = np.iinfo(np.int64).max
    inv_t = np.full(len(idx), BIG)
    for r in range(len(idx)):
        seg = cc[k0[r]:kend[r] + 1]
        bad = np.flatnonzero(seg < inv[r]) if dr[r] == 1 else np.flatnonzero(seg > inv[r])
        if len(bad):
            inv_t[r] = ct[k0[r] + bad[0]]
    up = dr == 1
    hit_t = np.full(len(idx), BIG)
    for side, sel in (("above", up), ("below", ~up)):
        if sel.any():
            tc = cl.touch(pd.DatetimeIndex(cl.data.from_ns(tn[sel])), tgt[sel], side,
                          until=until[sel], m1=m1)
            ht = cl.data.utc_ns(pd.DatetimeIndex(tc["hit_time"]))
            h = tc["hit"].to_numpy()
            v = np.full(sel.sum(), BIG)
            v[h] = ht[h] + 60_000_000_000
            hit_t[sel] = v
    out[idx] = ((hit_t < inv_t) & (hit_t < BIG)).astype(float)
    return out


if __name__ == "__main__":
    ev = cl.cache_frame(f"gdgr_1D_r{RETURN_BARS}_m{MIN_M1}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev)          # default 45D lookback > 10-day return + 3 days
    print("probe", probe.get("passed"))
    bx = cl.bars(RACE_TF)
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy()
    up_dist = d * (ev["leg_extreme"].to_numpy() - ev["touch_close"].to_numpy())
    dn_dist = d * (ev["touch_close"].to_numpy() - ev["far_edge"].to_numpy())
    obs = race(t, up_dist, dn_dist, d, bx)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=NULL_TOD_TOL)

    def null_fn(rng, k):
        return race(pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"), up_dist, dn_dist, d, bx)

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev, claim="+",
                       cluster=ev["fvg_time"].astype(str).to_numpy())
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "1D bars (18:00 NY roll); daily FVG = three candles whose 1st and 3rd wicks do not overlap "
        "(detectors.primitives.fair_value_gaps); all three days need >= 600 M1 bars",
        "first touch: first M1 bar within 13,800 M1 bars (~10 trading days) after the 3rd daily candle closes that "
        "trades into the near edge (bullish gap below: low <= gap high); decision = that M1 bar's close; skip if it "
        "closes beyond the far edge",
        "swing high above (bullish) / low below (bearish) = extreme of the leg between gap completion and the touch",
        "outcome = 1 if price reaches that extreme (M1 high/low) before any 1h candle closes beyond the gap's far edge, "
        "within the next 46 1h candles; else 0 (distances from the touch close, applied from the next M1 open)",
        "null = same two distances, same 46-candle race, at matched random moments (+/-30 d, 5 reps, locked seed) "
        "at the same NY time of day (+/-30 min); clustered by gap"],
        "params": {"fvg_tf": "1D", "day_roll": "18:00 NY", "return_bars": RETURN_BARS, "race_tf": RACE_TF,
                   "race_bars": RACE_BARS, "min_m1": MIN_M1, "invalidation": "1h close beyond far edge",
                   "target": "leg extreme (swing high above)", "cluster": "fvg_time",
                   "null_tod_tol_min": NULL_TOD_TOL}}
    src = {"fvg_tf": "corpus: h1ZQWWQDhKA 'gold did reach into that weekly that daily gap' / 'we reach down to this daily imbalance'",
           "day_roll": "method_spec: concept_lab default 1D bars roll at 18:00 NY (README trap 8)",
           "return_bars": "declared-before-run: source gives no recency window; a gap's first return counted within ~10 trading days",
           "race_tf": "corpus: h1ZQWWQDhKA 'the hourly chart. If we can get some nice displacement out of this daily gap'",
           "race_bars": "corpus: h1ZQWWQDhKA 'probably tomorrow or maybe tonight in Asia could look to target this high' -> ~2 trading days",
           "min_m1": "method_spec: README trap 6 stub sessions; skip gaps built on days with < 600 M1 bars",
           "invalidation": "corpus: draft invalidation 'price closes through it', read on his hourly execution chart",
           "target": "corpus: h1ZQWWQDhKA 'target this high up here' -> the swing high the pullback came from",
           "cluster": "declared-before-run: one gap is one setup",
           "null_tod_tol_min": "declared-before-run: README trap 9 + vault Concept Campaign 2026-09-23 lesson 3 (rate nulls must match time of day); not a timing concept, touches cluster 2.1-2.5x in 08-11 NY"}
    notes = ("Tests the draft's measurable (first-touch reaction rate of daily FVGs on XAUUSD) over the full certified "
             "span; the 'has been lately' recency qualifier cannot be pinned to a period. Displacement-confirmed entry "
             "is not separately tested (entry model unstated). AUDIT 2026-10-07: null now holds NY time of day +/-30 min "
             "(first run did not). Overlaps the 2026-09-23 internal-external-range-liquidity IRL->ERL leg "
             "(daily FVG first tag -> swing high, pooled, UNDERPOWERED); that reading was not refuted.")
    kw = dict(operationalization=op, params_source=src, script=__file__, probe=probe, notes=notes)
    try:
        p = cl.write_result(CID, READING, res, **kw)
    except Exception as e:  # new update concept not yet in batches.json
        print("write_result refused:", e)
        p = cl.write_result(CID, READING, res, allow_unknown_id=True, **kw)
    print("wrote", p)
