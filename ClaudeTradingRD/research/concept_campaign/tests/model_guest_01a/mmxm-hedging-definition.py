"""mmxm-hedging-definition (guest: DayTradingRauf, wB-fQiT_UDo) — declared before the first run.

The facilitation/hedging narrative is not observable; its price prediction is: after the
smart money reversal, price works back and CLEARS the original consolidation. Built on the
DAILY chart, as the source instructs. Buy model (sell model mirrored):
  * original consolidation: 5 consecutive daily bars whose total range <= 1.5 x ATR14(1D)
    (ATR at the consolidation's last bar); CH / CL its high / low.
  * breakout: a daily close below CL after the consolidation.
  * smart money reversal: a bullish daily CISD (series_open, 2/2, max_wait 3) whose extreme is
    below CL, is the lowest low since the consolidation, and sits within 40 daily bars of the
    consolidation's end, with the breakout close before the extreme. The most recent
    qualifying consolidation is used; one prediction per CISD.
  * prediction, made at the CISD bar's close: price trades ABOVE CH (clears the original
    consolidation) within 20 trading days (20 x 1380 M1 bars).
  * null: the same distance above the entry price, same M1-bar horizon, at matched random
    moments (+/-30 days, locked sample_times).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CONS_N = 5
CONS_ATR = 1.5
ATR_N = 14
LOOKBACK = 40
HORIZON_BARS = 20 * 1380


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 0]
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(d)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    rh = pd.Series(h).rolling(CONS_N).max().to_numpy()
    rl = pd.Series(l).rolling(CONS_N).min().to_numpy()
    cons_end = np.flatnonzero((rh - rl) <= CONS_ATR * atr)          # NaN compares False
    ev = cisd_events(d[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    ct = pd.DatetimeIndex(d["close_time"])
    pos_of = pd.Series(np.arange(n), index=d.index)
    rows = []
    for k in range(len(ev)):
        bull = ev["direction"].iat[k] == "bullish"
        x = int(pos_of[ev["extreme_time"].iat[k]])
        cf = int(pos_of[ev["confirm_time"].iat[k]])
        ext = ev["extreme_price"].iat[k]
        cand = cons_end[(cons_end < x) & (cons_end >= x - LOOKBACK)]
        for ce in cand[::-1]:                       # most recent consolidation first
            CH, CL = rh[ce], rl[ce]
            seg = slice(ce + 1, x + 1)
            if bull:
                if not ext < CL or l[seg].min() < ext:
                    continue
                if not (c[ce + 1:x + 1] < CL).any():
                    continue
                lvl = CH
            else:
                if not ext > CH or h[seg].max() > ext:
                    continue
                if not (c[ce + 1:x + 1] > CH).any():
                    continue
                lvl = CL
            rows.append({"decision_time": ct[cf], "available_at": ct[cf],
                         "direction": 1 if bull else -1, "level": float(lvl),
                         "cons_end": ct[ce], "extreme": float(ext)})
            break
    cols = ["decision_time", "available_at", "direction", "level", "cons_end", "extreme"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("mmxm_hedging_def_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="150D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    lvl = ev["level"].to_numpy()
    sgn = ev["direction"].to_numpy()
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = lvl - first_px                        # >0 for bull (CH above), <0 for bear
    obs = np.full(len(t), np.nan)
    for s, side in ((1, "above"), (-1, "below")):
        sel = sgn == s
        obs[sel] = cl.touch(t[sel], lvl[sel], side, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC") if pd.DatetimeIndex(rt[:, k]).tz is None \
            else pd.DatetimeIndex(rt[:, k])
        out = np.full(len(t), np.nan)
        for s, side in ((1, "above"), (-1, "below")):
            sel = (sgn == s) & ~tk.isna()
            if not sel.any():
                continue
            px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[sel]), len(mkt.o) - 1)]
            out[sel] = cl.touch(tk[sel], px + dist[sel], side,
                                horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev,
                       outcome_horizon="28D", claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "obs_rate", "null_rate")})
    op = {"rules": [
        "daily bars (18:00 NY roll): original consolidation = 5 bars with range <= 1.5 x ATR14",
        "breakout close beyond the consolidation, then a daily CISD (series_open 2/2 mw3) whose "
        "extreme is beyond it and the most extreme price since, within 40 bars of the consolidation",
        "prediction at the CISD close: price trades back through the far side of the consolidation "
        "(CH for a buy model, CL for a sell model) within 20 x 1380 M1 bars",
        "null: same signed distance from the entry price, same M1-bar horizon, matched random "
        "moments (sample_times reps 5, +/-30d)"],
        "params": {"cons_bars": CONS_N, "cons_atr": CONS_ATR, "atr_n": ATR_N,
                   "lookback_bars": LOOKBACK, "horizon": "20 trading days (27600 M1 bars)",
                   "cisd": "series_open 2/2 max_wait 3"}}
    src = {"cons_bars": "declared-before-run: source gives no size/duration test for the consolidation",
           "cons_atr": "declared-before-run: a tight range = under 1.5 daily ATR over 5 days",
           "atr_n": "declared-before-run: standard 14-bar ATR",
           "lookback_bars": "declared-before-run: the sell side of the curve spans at most two months",
           "horizon": "declared-before-run: one month to clear the consolidation",
           "cisd": "phase3: locked CISD config as the reversal confirmation"}
    p = cl.write_result("mmxm-hedging-definition", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Hedging/facilitation mechanism unobservable; tested its price "
                              "prediction (return through the original consolidation) on the daily "
                              "chart the source prescribes. Invalidation (return to 50%) not applied: "
                              "ambiguous direction in the source.")
    print(p)
