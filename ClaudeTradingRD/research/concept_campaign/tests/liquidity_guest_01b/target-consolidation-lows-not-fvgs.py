"""target-consolidation-lows-not-fvgs (guest: Alex's Options) -> rate_test, 1H.

Claim: when an expansion built from stacked consolidations reverses, the draw is
the lows of those consolidations (the stops of everyone who bought them), not the
FVGs inside the move. Scored: after a confirmed reversal, is the nearest untaken
consolidation low of the prior leg reached more often than a matched null level at
the same distance?

  reversal: 1H bearish CISD (phase-3 locked config: series_open, 2/2 swing,
    max_wait 3, min_series 1) - a close through the up-leg's opening series
    (structure turning down). Bullish mirrored (consolidation highs of a down-leg).
  leg: from the lowest low of the 72 1H bars before the CISD extreme to the extreme.
  consolidation: any 4 consecutive 1H bars inside the leg whose combined high-low
    range <= ATR14(1H) at the 4th bar; its low = min low of the 4 bars.
  target: the highest consolidation low below the confirm bar's low that no bar
    traded through between the consolidation's end and the decision (still
    resting stops). None -> no event.
  decide at the confirm-bar close; hit = M1 low reaches the target within one
    session (1,380 M1 bars). Null: matched random moments (+/-30d, same minute
    grid), same signed distance from the next M1 open, same side and horizon.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

LEG_BARS = 72
CONS_BARS = 4
H_BARS = 1380


def detect(m1):
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "target_px"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    wh = pd.Series(h).rolling(CONS_BARS).max().to_numpy()
    wl = pd.Series(l).rolling(CONS_BARS).min().to_numpy()
    cons = (wh - wl) <= atr          # consolidation ending at k (bars k-3..k)
    pos = {t: k for k, t in enumerate(b.index)}
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for e_t, c_t, dirn in zip(ev["extreme_time"], ev["confirm_time"], ev["direction"]):
        e, cf = pos[e_t], pos[c_t]
        a = e - LEG_BARS
        if a < 0:
            continue
        bear = dirn == "bearish"
        if bear:
            s = a + int(np.argmin(l[a:e + 1]))       # leg start = lowest low
        else:
            s = a + int(np.argmax(h[a:e + 1]))
        ks = np.arange(s + CONS_BARS - 1, e)       # consolidations fully inside the leg, before the extreme
        ks = ks[cons[ks]] if len(ks) else ks
        best = np.nan
        for k in ks:
            if bear:
                lv = wl[k]
                if lv < l[cf] and (k + 1 > cf or l[k + 1:cf + 1].min() > lv):
                    best = lv if np.isnan(best) else max(best, lv)
            else:
                lv = wh[k]
                if lv > h[cf] and (k + 1 > cf or h[k + 1:cf + 1].max() < lv):
                    best = lv if np.isnan(best) else min(best, lv)
        if np.isnan(best):
            continue
        rows.append((ct[cf], -1 if bear else 1, float(best)))
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "target_px"])
    out["available_at"] = out["decision_time"]
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"consol_lows_1h_leg{LEG_BARS}_c{CONS_BARS}", lambda: detect(cl.load_m1())).reset_index(drop=True)
    print("events", len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    tgt = ev["target_px"].to_numpy()
    up = ev["direction"].to_numpy() == 1
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = tgt - first_px

    def hits(times, levels, upmask):
        o = np.zeros(len(times), bool)
        if upmask.any():
            o[upmask] = cl.touch(times[upmask], levels[upmask], "above", horizon_bars=H_BARS)["hit"].to_numpy()
        if (~upmask).any():
            o[~upmask] = cl.touch(times[~upmask], levels[~upmask], "below", horizon_bars=H_BARS)["hit"].to_numpy()
        return o

    obs = hits(t, tgt, up).astype(float)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        out[ok] = hits(tk[ok], px + dist[ok], up[ok])
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": ["reversal = 1H CISD (series_open, 2/2 swing, max_wait 3, min_series 1); decide at confirm-bar close",
                    "leg = lowest low (bearish) / highest high (bullish) of the 72 1H bars before the extreme, to the extreme",
                    "consolidation = 4 consecutive 1H bars in the leg with combined range <= ATR14(1H); level = their low (high)",
                    "target = nearest consolidation low below the confirm bar's low not traded through since it formed",
                    "hit = M1 reaches target within 1,380 M1 bars; null = matched random moments +/-30d on the same minute grid, same signed distance from next M1 open"],
          "params": {"tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "min_series": 1,
                     "leg_bars": LEG_BARS, "consolidation_bars": CONS_BARS, "consolidation_range_atr": 1.0,
                     "atr_len": 14, "horizon_m1_bars": H_BARS}}
    src = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked CISD config) as the reversal confirmation"
           for k in ("level_rule", "swing", "max_wait", "min_series")}
    src["tf"] = "corpus: V8P6lNIisvc yaml timeframes htf 1D/1H - 1H analysis"
    src["leg_bars"] = "declared-before-run: yaml ambiguity 'how far back to enumerate' -> 3 trading days of 1H"
    src["consolidation_bars"] = "declared-before-run: consolidation not sized in corpus -> 4 bars"
    src["consolidation_range_atr"] = "declared-before-run: 4-bar range within one 1H ATR = sideways"
    src["atr_len"] = "declared-before-run: standard 14"
    src["horizon_m1_bars"] = "declared-before-run: one trading session"
    p = cl.write_result("target-consolidation-lows-not-fvgs", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Scores the positive half (consolidation lows are the draw) against a geometry-matched null; the FVG-vs-consolidation comparison is not scored head-to-head because target distance confounds it (trap 4).")
    print(p)
