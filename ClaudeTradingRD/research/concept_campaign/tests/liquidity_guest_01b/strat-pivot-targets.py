"""strat-pivot-targets (guest: Alex's Options, TheSTRAT) -> rate_test.

Claim: after a consolidation (inside bar) breaks out on the analysis timeframe,
the highs (lows) of the previous candles are the ordered targets and price works
through them. Tested on the first (nearest) unhit pivot target:

  * analysis TF 1D (18:00 NY roll). Inside bar at i-1: high <= mother high and
    low >= mother low (mother = i-2). Breakout bar i trades beyond the inside bar
    on exactly one side and CLOSES beyond it (a close back inside the consolidation
    is the stated invalidation, known at the close -> no event).
  * target list = highs (bullish) / lows (bearish) of the N=10 candles before the
    breakout bar that lie beyond the breakout bar's own extreme (not yet taken);
    first target = the nearest. No target in the list -> no event.
  * decide at the breakout bar's close; hit = any M1 trades through the target
    within H = 5 sessions (5 x 1380 M1 bars, trading time).
  * null: matched random daily-close moments (+/-30 days), same signed distance
    from the next M1 open, same side, same M1-bar horizon.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

N_PRIOR = 10
H_BARS = 5 * 1380
MIN_M1 = 600


def detect(m1):
    d = cl.build_bars(m1, "1D")
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    nm = d["n_m1"].to_numpy()
    ct = pd.DatetimeIndex(d["close_time"])
    rows = []
    for i in range(N_PRIOR + 1, len(d)):
        if min(nm[i], nm[i - 1], nm[i - 2]) < MIN_M1:
            continue
        if not (h[i - 1] <= h[i - 2] and l[i - 1] >= l[i - 2]):
            continue
        up, dn = h[i] > h[i - 1], l[i] < l[i - 1]
        if up == dn:
            continue
        lo_j = i - N_PRIOR
        if up:
            if c[i] <= h[i - 1]:
                continue
            cand = h[lo_j:i][h[lo_j:i] > h[i]]
            if len(cand) == 0:
                continue
            tgt, dirn = cand.min(), 1
        else:
            if c[i] >= l[i - 1]:
                continue
            cand = l[lo_j:i][l[lo_j:i] < l[i]]
            if len(cand) == 0:
                continue
            tgt, dirn = cand.max(), -1
        rows.append((ct[i], dirn, float(tgt)))
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "target_px"])
    out["available_at"] = out["decision_time"]
    return out[["decision_time", "available_at", "direction", "target_px"]]


if __name__ == "__main__":
    ev = cl.cache_frame(f"strat_pivot_1d_n{N_PRIOR}", lambda: detect(cl.load_m1()))
    ev = ev.reset_index(drop=True)
    print("events", len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
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
    grid = pd.DatetimeIndex(cl.bars("1D")["close_time"])
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, grid_times=grid)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        out[ok] = hits(tk[ok], px + dist[ok], up[ok])
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev,
                       outcome_horizon="7D", claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": ["1D bars, 18:00 NY roll; inside bar = high<=mother high and low>=mother low",
                    "breakout bar trades beyond the inside bar on one side only and closes beyond it",
                    "targets = highs (lows) of the 10 candles before the breakout bar beyond the breakout bar's extreme; first = nearest",
                    "decide at breakout close; hit = M1 trades through target within 5 sessions (6,900 M1 bars)",
                    "null = matched random daily-close moments +/-30d, same signed distance from next M1 open, same horizon"],
          "params": {"tf": "1D", "day_open_hour": 18, "n_prior_candles": N_PRIOR,
                     "horizon_m1_bars": H_BARS, "min_session_m1": MIN_M1,
                     "outcome_horizon": "7D"}}
    src = {"tf": "corpus: V8P6lNIisvc worked example is monthly with daily reaction; 1D is the lowest listed htf analysis TF (yaml timeframes.htf)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "n_prior_candles": "declared-before-run: corpus never states how many prior candles enter the list (yaml ambiguity); 10",
           "horizon_m1_bars": "declared-before-run: one trading week (5 x 1380 M1 bars)",
           "min_session_m1": "declared-before-run: skip stub sessions (README trap 6)",
           "outcome_horizon": "declared-before-run: 5 sessions span ~7 calendar days"}
    p = cl.write_result("strat-pivot-targets", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="First (nearest unhit) pivot target only; the sequential and FVG-coincidence sub-claims are not scored.")
    print(p)
