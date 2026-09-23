"""external-range-liquidity (liquidity, TTrades own voice, contested) — batch liquidity_own_01b.

Claim (3OivsP1j_UE, TfHlNgAZ_II): external range liquidity is a swing high or swing low;
"after internal liquidity [an FVG] is reached and respected, bias is toward external
liquidity in the direction of the respect" — ERL is the draw. Measurable named in the
concept: "hit rate of external liquidity being reached after an FVG is respected".

The two variants differ only in wording (both: ERL = a swing high/low, the outer target
of the range), so ONE reading is tested.

Rate test on 1h bars:
  * FVG: bullish when low[i] > high[i-2] (zone [high[i-2], low[i]]), mirrored bearish.
  * reached and respected: the first later bar (within 20 bars) that trades into the zone
    (low <= top) closes above the zone bottom (bearish mirrored); if that first tag closes
    through the zone the FVG failed and there is no event. Decision at the tag bar's close.
  * ERL: the nearest confirmed (2/2 fractal) swing high above (bullish) that formed within
    the last 72 1h bars (three days) and has not been traded through up to the decision.
  * hit: price trades to the ERL within three trading days (4,140 M1 bars).
  * null: the same signed distance from the next M1 open, at a random other day's same NY
    minute (+/-30 min) within +/-30 days, same bar count, 5 reps.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

TF = "1h"
LEFT, RIGHT = 2, 2
TAG_WAIT = 20
SWING_LOOKBACK = 72
HORIZON_BARS = 3 * 1380
TOD_TOL = 30


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rows = []
    for i in range(2, n):
        for bull in (True, False):
            if bull:
                if not l[i] > h[i - 2]:
                    continue
                bot, top = h[i - 2], l[i]
            else:
                if not h[i] < l[i - 2]:
                    continue
                bot, top = h[i], l[i - 2]            # zone [h[i], l[i-2]]
            j = None
            for k in range(i + 1, min(n, i + 1 + TAG_WAIT)):
                if bull and l[k] <= top:
                    j = k
                    break
                if (not bull) and h[k] >= bot:
                    j = k
                    break
            if j is None:
                continue
            if bull and not c[j] > bot:
                continue
            if (not bull) and not c[j] < top:
                continue
            lo_s = max(0, j - SWING_LOOKBACK)
            hi_s = j - RIGHT                           # confirmed by j's close
            if hi_s <= lo_s:
                continue
            if bull:
                cand = np.flatnonzero(sh[lo_s:hi_s + 1]) + lo_s
                lv = [h[s] for s in cand if h[s + 1:j + 1].max() <= h[s] and h[s] > c[j]]
                if not lv:
                    continue
                rows.append((ct[j], min(lv), 1))
            else:
                cand = np.flatnonzero(sl[lo_s:hi_s + 1]) + lo_s
                lv = [l[s] for s in cand if l[s + 1:j + 1].min() >= l[s] and l[s] < c[j]]
                if not lv:
                    continue
                rows.append((ct[j], max(lv), -1))
    out = pd.DataFrame(rows, columns=["decision_time", "level", "side"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"], tz="UTC") if len(out) else \
        pd.DatetimeIndex([], tz="UTC")
    out["available_at"] = out["decision_time"]
    out = out[["decision_time", "available_at", "level", "side"]]
    # one FVG tag bar can serve several FVGs with the same ERL: keep distinct rows
    out = out.drop_duplicates().sort_values(["decision_time", "side", "level"])
    return out.reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"erl_{TF}_{TAG_WAIT}_{SWING_LOOKBACK}", lambda: detect(m1))
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    mkt = cl.get_market()
    N = len(mkt.o)
    t = pd.DatetimeIndex(ev["decision_time"])
    i0 = mkt.pos_at_or_after(t)
    ok = i0 + HORIZON_BARS <= N
    first_px = mkt.o[np.minimum(i0, N - 1)]
    lvl, side = ev["level"].to_numpy(), ev["side"].to_numpy()
    dist = lvl - first_px
    ok &= np.sign(dist) == side
    obs = np.full(len(ev), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        r = ok & (side == s)
        obs[r] = cl.touch(t[r], lvl[r], nm, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(ev), np.nan)
        good = ok & ~tk.isna()
        for s, nm in ((1, "above"), (-1, "below")):
            r = good & (side == s)
            if r.any():
                px = mkt.o[mkt.pos_at_or_after(tk[r])]
                out[r] = cl.touch(tk[r], px + dist[r], nm, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn, predictors=ev,
                       outcome_horizon="3D", claim="+")
    print(len(ev), {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    op = {"rules": ["1h FVG (3-candle gap); first tag within 20 bars must close back on the respect side of the zone (else failed, no event)",
                    "decision at the respecting tag bar's close",
                    "ERL = nearest confirmed 2/2 swing high above (bullish) / swing low below (bearish), formed in the last 72 1h bars, untaken up to the decision",
                    "hit = price trades to the ERL within 3 trading days (4,140 M1 bars); row kept only if ERL is still beyond the next M1 open",
                    "claim: after IRL is respected, ERL is reached more often than an arbitrary level at the same distance"],
          "params": {"tf": TF, "swing": "2/2", "tag_wait_bars": TAG_WAIT, "swing_lookback_bars": SWING_LOOKBACK,
                     "respect": "first tag closes beyond the zone's far edge on the respect side", "horizon_bars": HORIZON_BARS,
                     "null": "distance-matched, NY clock +/-30min, +/-30d, 5 reps, same bar count"}}
    src = {"tf": "declared-before-run: 1h, one of the concept's listed htf timeframes, chosen for sample size",
           "swing": "phase3: 2/2 fractal swings (locked config)",
           "tag_wait_bars": "declared-before-run: FVG must be reached within 20 bars of forming (else stale)",
           "swing_lookback_bars": "method_spec: §1.1 relevant-swing look-back = three HTF candles; hourly chart -> three days (72 bars)",
           "respect": "declared-before-run: 'respected' = the first tag does not close through the gap (corpus gives no closure rule)",
           "horizon_bars": "declared-before-run: three trading days, matching the hourly relevant-swing look-back",
           "null": "declared-before-run: same signed distance from the open at a random other day's same NY minute (+/-30 min, +/-30 d), same M1-bar count, 5 reps"}
    p = cl.write_result("external-range-liquidity", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Single reading: the variant only restates ERL = swing high/low; no distinct claim to split. Tested as the IRL->ERL rotation's second leg.")
    print("wrote", p)
