"""intraday-bias-three-inputs — rate_test (reading a: the three-input procedure).

Claim (xdm_OexQWJY): use the 4H/1H as the daily timeframe; the bias comes from exactly
three inputs — DISPLACEMENT, STRUCTURE and IMBALANCES — and the draw is the liquidity on
the far side ("aggressive move down + relatively equal lows + a fair value gap left
behind gives a bearish read whose draw is those lows"). Measurable (yaml): hit rate of
the identified draw being reached the same session.

Operationalisation on 1H bars (declared before the run):
  * displacement = threshold_fits §2: a 1H candle CLOSES beyond the most recent
    confirmed 2/2 swing low (structural gate), and the N=4 window from the break has
    win_range/pre_range >= 1.5 and distance-beyond-level/pre_range >= 0.65;
  * imbalance = a same-direction 3-bar FVG printed inside that window;
  * structure / draw = the nearest confirmed, still-untaken 1H swing low below the close
    of the window's last bar (last 120 bars); mirrored for bullish;
  * decision at the close of the 4th window bar; outcome = the draw is traded through
    before the NY trading day ends (18:00 roll, M1 bars);
  * null = same signed distance from the first price after a matched random moment
    (+/-30 d, NY time of day +/-30 min), same M1-bar horizon.
Reading b (the London/Asia narrative framing) gives no session boundaries or rule and is
not operationalised; "relatively equal" lows are not required (no tolerance stated).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import day_end_bars, fractal_swings, matched_touch_null  # noqa: E402

N_WIN, R_MIN, D_MIN = 4, 1.5, 0.65
LOOKBACK = 120


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "1h")
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    sh, sl = fractal_swings(h, l, 2, 2)
    n = len(b)
    rows = []
    for k in range(N_WIN + 3, n - N_WIN + 1):
        e = k + N_WIN - 1                                   # last window bar
        pre = slice(k - N_WIN, k)
        win = slice(k, e + 1)
        pre_rng = h[pre].max() - l[pre].min()
        if pre_rng <= 0:
            continue
        win_rng = h[win].max() - l[win].min()
        for bull in (False, True):
            sw = sh if bull else sl
            # most recent swing confirmed by the close of bar k-1 (index <= k-3)
            cand = np.flatnonzero(sw[max(0, k - LOOKBACK):k - 2]) + max(0, k - LOOKBACK)
            if len(cand) == 0:
                continue
            s = cand[-1]
            lvl = h[s] if bull else l[s]
            if bull:
                brk = c[k] > lvl and c[k - 1] <= lvl
                dist = h[win].max() - lvl
            else:
                brk = c[k] < lvl and c[k - 1] >= lvl
                dist = lvl - l[win].min()
            if not brk or win_rng / pre_rng < R_MIN or dist / pre_rng < D_MIN:
                continue
            fvg = False
            for m in range(k + 1, e + 1):
                if (l[m] > h[m - 2]) if bull else (h[m] < l[m - 2]):
                    fvg = True
                    break
            if not fvg:
                continue
            # draw: nearest untaken confirmed swing on the far side (index <= e-2)
            osw = sh if bull else sl
            lo_i = max(0, e - LOOKBACK)
            cands = np.flatnonzero(osw[lo_i:e - 1]) + lo_i
            best = np.nan
            for q in cands[::-1]:
                lv = h[q] if bull else l[q]
                after = slice(q + 1, e + 1)
                if bull:
                    if lv <= c[e] or h[after].max() >= lv:
                        continue
                    best = lv if not np.isfinite(best) else min(best, lv)
                else:
                    if lv >= c[e] or l[after].min() <= lv:
                        continue
                    best = lv if not np.isfinite(best) else max(best, lv)
            if not np.isfinite(best):
                continue
            rows.append({"decision_time": ct[e], "available_at": ct[e],
                         "direction": 1 if bull else -1, "draw": best})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction", "draw"])


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame("ib3_1h_v1", lambda: detect(cl.load_m1()))
    ev = ev.sort_values("decision_time", kind="stable").reset_index(drop=True)
    print(len(ev), ev["direction"].value_counts().to_dict())

    def detect_sorted(m):
        return detect(m).sort_values("decision_time", kind="stable").reset_index(drop=True)
    probe = cl.probe_lookahead(detect_sorted, ev, lookback="12D")
    t = pd.DatetimeIndex(ev["decision_time"])
    hb = day_end_bars(m1.index, t)
    mkt = cl.get_market()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    lvl = ev["draw"].to_numpy()
    side = np.where(ev["direction"].to_numpy() > 0, "above", "below")
    obs = np.zeros(len(ev), bool)
    for sd in ("above", "below"):
        m = side == sd
        obs[m] = cl.touch(t[m], lvl[m], sd, horizon_bars=hb[m])["hit"].to_numpy()
    null_fn = matched_touch_null(t, lvl - px, side, hb, tod_tol_min=30)
    res = cl.rate_test(obs.astype(float), t, available_at=ev["available_at"],
                       null_fn=null_fn, predictors=ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "1H bars; displacement = close beyond the most recent confirmed 2/2 swing, N=4 window "
        "from the break with win_range/pre_range>=1.5 and distance/pre_range>=0.65",
        "imbalance = same-direction 3-bar FVG inside the window",
        "draw = nearest confirmed, untaken 1H swing on the far side of the window close (<=120 bars)",
        "decide at the 4th window bar's close; hit = draw traded through before the NY trading day ends",
        "null = same signed distance from first price after a matched random moment (+/-30d, "
        "NY time of day +/-30 min), same M1-bar horizon"],
        "params": {"tf": "1h", "N": N_WIN, "r": R_MIN, "d": D_MIN, "swing": "2/2",
                   "draw_lookback_bars": LOOKBACK, "horizon": "rest of NY trading day",
                   "null_tod_tol_min": 30}}
    src = {"tf": "corpus: xdm_OexQWJY 'how to use the four hour and one hour chart as your daily time frame'",
           "N": "threshold_fits: displacement magnitude default N=4",
           "r": "threshold_fits: displacement magnitude default r=1.5",
           "d": "threshold_fits: displacement magnitude default d=0.65",
           "swing": "method_spec: §4.2 / threshold_fits §2 fractal 2/2 short-term high/low",
           "draw_lookback_bars": "declared-before-run: five trading days of 1H structure",
           "horizon": "corpus: intraday-bias-three-inputs yaml measurable 'reached the same session'",
           "null_tod_tol_min": "declared-before-run: README trap 9 — hold NY clock fixed in the null"}
    p = cl.write_result("intraday-bias-three-inputs", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Reading a = the named three-input procedure. The London/Asia narrative "
                              "construction (reading b) has no session bounds or rule and was not run.")
    print("wrote", p)
