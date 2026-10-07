"""fractal-model-c2, update_20261007_live_03: daily-C2 targets (EQ -> previous day high),
relabel rule, holiday counting. AUDITED + FIXED 2026-10-07 (vault-context re-run).

Prior readings a/b (4h/1h C2 + LTF CISD trade books, 2026-09-23) are untouched.

Source, rVRk4MLTJSs (New York Open Live Q&A), spoken LIVE during the C2 day itself:
  "on my C2 daily candle, what's our target on this? First target's the EQ. second target,
   previous day high. ... ES is a lot closer to hitting previous day high ... [YM]'s already
   over the high"  -> the C2 is TODAY's candle (it swept yesterday's low and reversed), so
   "previous day high" = C1's high and EQ = C1's 50% ("Our target is half of this and then
   this"), both reached DURING the C2 day.
  "C3 opens up and sweeps it out. This isn't C2 anymore. This is now C2."  (relabel)
  "Thursday, C2 ... Friday is C3, Monday is C4 ... bank holiday Monday. It doesn't count."

AUDIT FIX: the first version scored C2's OWN far extreme during C3 (it read "previous day"
from C3's seat). The speaker stands in C2, so that level is not the one he names (and it put
"first target EQ" behind price, as that version itself noted). Corrected below.

Event (causal, intraday on the C2 day): the first 1h close of the trading day back above C1's
low after the day traded below it (bearish mirror) - the C2 test on the daily's paired 1h.
Kept only if both targets are still ahead (C1 EQ and C1's opposite extreme untaken).
  u1007a  C1's opposite extreme (PDH) reached before the C2 day ends (EQ lies on the way).
  u1007b  ... or, failing that, during C3 (next REAL trading day) before C3 trades through the
          C2 extreme; a sweep first (or same M1 minute) relabels C3 as the new C2 -> miss.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MIN_M1 = 600  # stub/holiday session guard (worked example's value): such days are not candles


def detect(m1):
    d = cl.build_bars(m1, "1D")
    real = d[d["n_m1"] > MIN_M1]                                  # only real trading days count
    rtd = pd.DatetimeIndex(real["trading_day"]).as_unit("ns").asi8
    h = cl.build_bars(m1, "1h")
    td = cl.trading_day(h.index).as_unit("ns").asi8
    j = np.searchsorted(rtd, td, "left") - 1                     # C1 = previous REAL day (closed)
    ok = j >= 0
    h, td, j = h[ok], td[ok], j[ok]
    pdh, pdl = real["high"].to_numpy()[j], real["low"].to_numpy()[j]
    lo = pd.Series(h["low"].to_numpy()).groupby(td).cummin().to_numpy()   # running, closed bars
    hi = pd.Series(h["high"].to_numpy()).groupby(td).cummax().to_numpy()
    c = h["close"].to_numpy()
    trig = ((lo < pdl) & (c > pdl)) | ((hi > pdh) & (c < pdh))   # swept C1 side, 1h close back in
    first = trig & (pd.Series(trig.astype(int)).groupby(td).cumsum().to_numpy() == 1)
    eq = (pdh + pdl) / 2
    bull = first & (lo < pdl) & (c > pdl) & (hi < pdh) & (c < eq)      # EQ and PDH still ahead
    bear = first & (hi > pdh) & (c < pdh) & (lo > pdl) & (c > eq)
    k = bull | bear
    ct = pd.DatetimeIndex(h["close_time"])[k]
    b = bull[k]
    return pd.DataFrame({
        "decision_time": ct, "available_at": ct,
        "direction": np.where(b, 1, -1),
        "target_px": np.where(b, pdh[k], pdl[k]),                # T2 = C1's opposite extreme
        "eq_px": eq[k],                                          # T1 = C1 EQ (on the way)
        "sweep_px": np.where(b, lo[k], hi[k]),                   # C2 extreme so far
    }).reset_index(drop=True)


m1 = cl.load_m1()
ev = cl.cache_frame("fmc2_c2day_1h_reclaim_u1007", lambda: detect(m1))
probe = cl.probe_lookahead(detect, ev, lookback="10D")

mkt = cl.get_market()
NM = len(mkt.tn)
d_all = cl.bars("1D")
day_close = pd.Series(pd.DatetimeIndex(d_all["close_time"]).as_unit("ns").asi8,
                      index=pd.DatetimeIndex(d_all["trading_day"]).as_unit("ns").asi8)
real = d_all[d_all["n_m1"] > MIN_M1]
rtd = pd.DatetimeIndex(real["trading_day"]).as_unit("ns").asi8
rclose = pd.DatetimeIndex(real["close_time"]).as_unit("ns").asi8

t = pd.DatetimeIndex(ev["decision_time"])
etd = cl.trading_day(t - pd.Timedelta(hours=1)).as_unit("ns").asi8   # the 1h bar's day = C2
i0 = mkt.pos_at_or_after(t)
dc = day_close.reindex(etd).to_numpy()
kc3 = np.searchsorted(rtd, etd, "right")                          # C3 = next REAL trading day
has_c3 = kc3 < len(rtd)
c3c = np.where(has_c3, rclose[np.minimum(kc3, len(rtd) - 1)], 0)
n_rest = np.searchsorted(mkt.tn, dc.astype("datetime64[ns]"), "left") - i0
n_tot = np.searchsorted(mkt.tn, c3c.astype("datetime64[ns]"), "left") - i0
last_ns = mkt.tn[-1].astype(np.int64)
ok_a = (n_rest > 0) & (dc < last_ns) & (i0 < NM)
ok_b = ok_a & has_c3 & (c3c < last_ns) & (n_tot > n_rest)
n_c3 = np.where(ok_b, n_tot - n_rest, 0)
n_rest = np.where(ok_a, n_rest, 0)

up = ev["direction"].to_numpy() == 1
p0 = mkt.o[np.minimum(i0, NM - 1)]
d_tgt = ev["target_px"].to_numpy() - p0                 # geometry preserved in the null
d_swp = ev["sweep_px"].to_numpy() - p0


def seg_ext(arr, ii, nn, fn):
    out = np.full(len(ii), np.nan)
    for q, (a, n) in enumerate(zip(ii, nn)):
        if n > 0:
            out[q] = fn(arr[a:a + n])
    return out


def outcome(times, ii, tgt, swp, upm, nr, nc, relabel):
    """T2 reached in the rest of C2 (nr bars); b: else in C3 (nc bars) before C3 trades
    through the C2 extreme = min(sweep so far, rest-of-C2 lows) (mirror for bearish)."""
    times = pd.DatetimeIndex(times)
    hit = np.zeros(len(times), bool)
    for m, side, opp in ((upm, "above", "below"), (~upm, "below", "above")):
        if not m.any():
            continue
        a = cl.touch(times[m], tgt[m], side, horizon_bars=nr[m])["hit"].to_numpy()
        if relabel:
            ext = seg_ext(mkt.l if side == "above" else mkt.h, ii[m], nr[m],
                          np.min if side == "above" else np.max)
            L = np.fmin(swp[m], ext) if side == "above" else np.fmax(swp[m], ext)
            st = pd.DatetimeIndex(mkt.t[np.minimum(ii[m] + nr[m], NM - 1)])
            th = cl.touch(times[m], tgt[m], side, start_after=st, horizon_bars=nc[m])
            sh = cl.touch(times[m], L, opp, start_after=st, horizon_bars=nc[m])
            th_t, sh_t = th["hit_time"].to_numpy(), sh["hit_time"].to_numpy()
            a = a | (th["hit"].to_numpy() & (~sh["hit"].to_numpy() | (th_t < sh_t)))
        hit[m] = a
    return hit


rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)   # same NY hour, +/-30d


def score(which):
    okr = ok_a if which == "a" else ok_b
    rb = which == "b"
    obs = np.full(len(t), np.nan)
    obs[okr] = outcome(t[okr], i0[okr], p0[okr] + d_tgt[okr], p0[okr] + d_swp[okr], up[okr],
                       n_rest[okr], n_c3[okr], rb)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna() & okr
        out = np.full(len(t), np.nan)
        ik = mkt.pos_at_or_after(tk[ok])
        px = mkt.o[ik]
        out[ok] = outcome(tk[ok], ik, px + d_tgt[ok], px + d_swp[ok], up[ok],
                          n_rest[ok], n_c3[ok], rb)
        return out
    return obs, null_fn


# ---- diagnostics (descriptive only; not a test) ----
okd = ok_a
eq_hit = cl.touch(t[okd & up], ev["eq_px"].to_numpy()[okd & up], "above",
                  horizon_bars=n_rest[okd & up])["hit"].mean()
rng_real = (seg_ext(mkt.h, i0[okd], n_rest[okd], np.max) - seg_ext(mkt.l, i0[okd], n_rest[okd], np.min))
tk0 = pd.DatetimeIndex(rt[:, 0]).tz_localize("UTC")
okn = okd & ~tk0.isna()
ik0 = mkt.pos_at_or_after(tk0[okn])
rng_null = seg_ext(mkt.h, ik0, n_rest[okn], np.max) - seg_ext(mkt.l, ik0, n_rest[okn], np.min)
DIAG = {"events": int(len(ev)), "scorable_a": int(ok_a.sum()), "scorable_b": int(ok_b.sum()),
        "bull_share": round(float(up.mean()), 3),
        "eq_hit_rate_bull_rest_of_C2": round(float(eq_hit), 3),
        "median_rest_of_C2_range_real": round(float(np.nanmedian(rng_real)), 2),
        "median_rest_of_C2_range_null_rep0": round(float(np.nanmedian(rng_null)), 2),
        "median_target_dist_over_rest_range_real": round(float(np.nanmedian(np.abs(d_tgt[okd]) / rng_real)), 3)}
print("DIAG", DIAG)

OP_COMMON = [
    "daily candles = NY trading day rolling 18:00; days with <= 600 M1 are not candles (holiday rule): "
    "C1 = the previous REAL trading day, C3 = the next REAL trading day",
    "C2 day, intraday: the first 1h close of the day back above C1's low after the day traded below it "
    "(bullish) / back below C1's high after trading above it (bearish); one event per day",
    "kept only if both targets are still ahead at that close: C1 EQ ((C1 high + C1 low)/2) and C1's "
    "opposite extreme untaken by the day so far",
    "decide at that 1h close_time (all inputs closed: C1 bar, the day's 1h bars); scan M1 from the next bar",
    "T2 = C1's opposite extreme (previous day high for bullish); EQ lies between price and T2 so a T2 touch "
    "passes EQ first (EQ hit rate reported in notes)",
    "null: same signed distances (T2, C2 extreme) from the first M1 open, same M1-bar windows, at 5 random "
    "moments on other days within +/-30d at the same NY clock hour (tod_tol 30 min on the :00 grid), same direction",
    "rows with no M1 bar left in the C2 day are unscored (NaN)",
]
PARAMS = {"tf": "1D", "day_open_hour": 18, "min_m1": MIN_M1, "ltf": "1h",
          "c2_trigger": "first 1h close back inside C1 after sweeping C1's extreme",
          "targets": "T1 = C1 EQ (scope: ahead), T2 = C1 opposite extreme (scored)",
          "horizon_a": "rest of the C2 trading day (M1 bars)",
          "null": "distance + bar-count matched, same NY hour, +/-30d, 5 reps", "null_tod_tol_min": 30}
SRC = {
    "tf": "corpus: rVRk4MLTJSs 'on my C2 daily candle, what's our target on this?'",
    "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
    "min_m1": "corpus: rVRk4MLTJSs 'bank holiday Monday. It doesn't count' -> stub days are not candles; 600 = worked example stub guard",
    "ltf": "corpus: nwbHvFCh0bo 'the daily with the 1 hour' (timeframe-alignment-pairs)",
    "c2_trigger": "corpus: JoFxG1TrnDA 'take out its previous candle's high and then close back below it'; 0fhZ_jpespw 'we can apply it to any time frame'; rVRk4MLTJSs 'form a reversal with a small wick ... trade this back into the right range'",
    "targets": "corpus: rVRk4MLTJSs 'First target's the EQ. second target, previous day high' + 'Our target is half of this and then this' (EQ = 50% of the previous candle); spoken live on the C2 day ('ES is a lot closer to hitting previous day high')",
    "horizon_a": "corpus: rVRk4MLTJSs targets of 'my C2 daily candle' -> delivered within that candle",
    "null": "declared-before-run: README rate_test pattern (same distance, same bars, +/-30d matched moments)",
    "null_tod_tol_min": "declared-before-run: README trap 9 + vault Concept Campaign lesson 3 (rate nulls must match time of day)",
}
READ = {
    "a": ("hit = C1's opposite extreme (T2) touched in the rest of the C2 trading day", {}, {}),
    "b": ("hit = T2 touched in the rest of C2, or during C3 (next REAL trading day) before C3 trades through "
          "the C2 extreme (= min(sweep low so far, rest-of-C2 lows), mirror for bearish); a C3 sweep first or in "
          "the same M1 minute relabels C3 as the new C2 and voids the old C2's target -> miss",
          {"relabel": "C3 sweep of the C2 extreme first = miss", "horizon_b": "rest of C2 + C3 (M1 bars)"},
          {"relabel": "corpus: rVRk4MLTJSs 'C3 opens up and sweeps it out. This isn't C2 anymore. This is now C2.'",
           "horizon_b": "corpus: rVRk4MLTJSs 'Thursday, C2. So then you're assuming that Friday is C3'"}),
}
AUDIT = ("AUDIT 2026-10-07 (vault context): fixed - first version scored C2's own far extreme during C3; "
         "the source names the previous day's (C1's) high as the target of the C2 day itself, spoken live on that day.")
for r in ("a", "b"):
    obs, nf = score(r)
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=nf, predictors=ev,
                       outcome_horizon=("2D" if r == "b" else None))
    rule, xp, xs = READ[r]
    cl.write_result("fractal-model-c2", "u1007" + r, res,
                    operationalization={"rules": OP_COMMON + [rule], "params": {**PARAMS, **xp}},
                    params_source={**SRC, **xs}, script=__file__, probe=probe,
                    notes=AUDIT + " Diagnostics: " + str(DIAG))
    print(r, {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi",
                                       "p", "mde", "verdict", "verdict_detail")})
