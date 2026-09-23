"""low-expectation-target-selection (TTrades own voice, specified) — batch liquidity_own_01a.

Rule (live_streams_04): "a high or low that itself swept out a run of previous highs or
lows is harder for price to reach ... On a day where his expectation is low - the
average daily range is largely spent - he does not target that swept extreme" and
takes the failure swing to the right of the protected swing instead.

The testable premise: on a low-expectation day, a swept-series extreme is reached LESS
often than its distance implies. rate_test, claim '-':
  Swept-series extreme (15m, fractal 2/2): a swing low whose down-leg (bars after the
    previous swing high, through the swing bar) took >= 2 untaken confirmed swing lows
    (tracked 7 days). Mirror for highs.
  Decision: the first opposite 15m swing (the protected swing for a trade back toward
    X) confirmed after X, within 24 bars and in the same trading day, while X is still
    untouched — and only if the day is a LOW-EXPECTATION day at that moment: the
    trading day's running range >= 75% of the mean range of the previous 5 sessions.
  Hit: X traded before the trading day ends (the remaining M1 bars of the day).
  Null: a level at the same distance from the first M1 open at matched random moments
    (+/-30d, same NY clock +/-30 min), with the same number of M1 bars of horizon.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

CID = "low-expectation-target-selection"
TF = "15min"
LEFT = RIGHT = 2
POOL_WINDOW = pd.Timedelta("7D")
MIN_SWEPT = 2
MAX_WAIT = 24
ADR_DAYS = 5
SPENT = 0.75
MIN_BARS = 600
NULL_TOD_TOL = 30     # null moments at the same NY clock (+/-30 min): see NOTES


NOTES = ("RE-RUN ONCE after a null-design bug found on seeing the first verdict. Run 1 "
         "drew null moments uniformly in +/-30d with no time-of-day match: n=3455, "
         "observed 39.0% vs null 41.2%, diff -0.021 [-0.039, -0.004], EDGE. The decisions "
         "cluster 10:00-17:00 NY (low-expectation needs the day's range spent), while the "
         "null windows of the same M1-bar count fell in any hour, often in more active "
         "hours. That confound favours the claimed '-' direction (README trap 9). Run 2 "
         "(this result) holds the NY clock within +/-30 min. Nothing else changed. Both "
         "runs are in the ledger.")


def detect(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    idx = b.index
    ct = pd.DatetimeIndex(b["close_time"])
    is_h, is_l = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    n = len(b)
    # 1. how many untaken pools each bar took, per side
    act = {1: [], -1: []}
    took = {1: np.zeros(n, int), -1: np.zeros(n, int)}
    for j in range(n):
        i = j - RIGHT - 1
        if i >= 0 and is_h[i]:
            act[1].append((H[i], idx[i]))
        if i >= 0 and is_l[i]:
            act[-1].append((L[i], idx[i]))
        for s in (1, -1):
            act[s] = [p for p in act[s] if idx[j] - p[1] <= POOL_WINDOW]
        took[1][j] = sum(H[j] > p[0] for p in act[1])
        took[-1][j] = sum(L[j] < p[0] for p in act[-1])
        act[1] = [p for p in act[1] if H[j] <= p[0]]
        act[-1] = [p for p in act[-1] if L[j] >= p[0]]
    # 2. daily context: running range and ADR of the previous sessions
    bday = np.asarray(cl.trading_day(idx))
    g = pd.Series(bday)
    run_rng = (pd.Series(H).groupby(g).cummax() - pd.Series(L).groupby(g).cummin()).to_numpy()
    d = cl.build_bars(m1, "1D")
    rng_d = (d["high"] - d["low"]).where(d["n_m1"] >= MIN_BARS)
    adr = rng_d.shift(1).rolling(ADR_DAYS, min_periods=ADR_DAYS).mean()
    adr.index = cl.trading_day(d.index)
    adr_b = adr.reindex(pd.DatetimeIndex(bday)).to_numpy()
    # 3. swept-series extremes and their decision moments
    out = []
    for s, xs, ts, X_, other in ((-1, is_l, is_h, L, H), (1, is_h, is_l, H, L)):
        # s = side of the target relative to price at decision: -1 below (a swept low)
        prev_t = -1
        for i in range(n):
            if ts[i]:
                prev_t = i
            if not xs[i] or i + RIGHT >= n:
                continue
            cnt = took[s][prev_t + 1:i + 1].sum() if prev_t >= 0 else 0
            if prev_t < 0 or cnt < MIN_SWEPT:
                continue
            X = X_[i]
            for q in range(i + 1, min(n, i + 1 + MAX_WAIT)):
                if (L[q] <= X) if s == -1 else (H[q] >= X):
                    break                      # X reached before any turn
                if bday[q] != bday[i]:
                    break
                c = q - RIGHT                  # turning swing confirmed at close of q
                if c > i and ts[c]:
                    if np.isfinite(adr_b[q]) and run_rng[q] >= SPENT * adr_b[q]:
                        out.append((ct[q], ct[q], s, X))
                    break
    ev = pd.DataFrame(out, columns=["decision_time", "available_at", "side", "level"])
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)


def run():
    ev = cl.cache_frame(f"{CID}_{TF}_s{MIN_SWEPT}_w{MAX_WAIT}_adr{ADR_DAYS}_{SPENT}",
                        lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    lvl, side = ev["level"].to_numpy(), ev["side"].to_numpy()
    p0 = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)
    # remaining M1 bars in the decision's trading day (outcome window, not a predictor)
    mday = np.asarray(cl.trading_day(pd.DatetimeIndex(cl.load_m1().index)))
    last = pd.Series(np.arange(len(mday))).groupby(mday).max()
    end = last.reindex(pd.DatetimeIndex(mday[p0])).to_numpy()
    hb = np.maximum(end - p0 + 1, 1).astype(np.int64)
    dist = lvl - mkt.o[p0]
    obs = np.full(len(t), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        k = side == s
        obs[k] = cl.touch(t[k], lvl[k], nm, horizon_bars=hb[k])["hit"].to_numpy()
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED,
                         tod_tol_min=NULL_TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        o = np.full(len(t), np.nan)
        for s, nm in ((1, "above"), (-1, "below")):
            ok = (~tk.isna()) & (side == s)
            p = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
            o[ok] = cl.touch(tk[ok], p + dist[ok], nm, horizon_bars=hb[ok])["hit"].to_numpy()
        return o

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="-")
    op = {"rules": [
        "pools: untaken 15m fractal-2/2 swing highs/lows, tracked 7 days",
        "swept-series extreme X: a 15m swing low (high) whose leg since the previous "
        "opposite swing took >= 2 pools",
        "decision: first opposite 15m swing confirmed after X, within 24 bars, same "
        "trading day, X untouched; kept only on a low-expectation day: running day range "
        ">= 0.75 x mean range of the previous 5 sessions (sessions < 600 M1 bars are NaN)",
        "hit: X traded in the remaining M1 bars of the trading day; null: same distance "
        "at matched random moments (same NY clock +/-30 min) with the same bar count; "
        "claim '-'"],
        "params": {"tf": TF, "left": LEFT, "right": RIGHT, "pool_window": "7D",
                   "min_swept": MIN_SWEPT, "max_wait_bars": MAX_WAIT, "adr_days": ADR_DAYS,
                   "spent_frac": SPENT, "min_bars": MIN_BARS, "day_open_hour": 18,
                   "null_tod_tol_min": NULL_TOD_TOL}}
    src = {"tf": "corpus: source YAML timeframes.ltf ['15m','5m'] (live_streams_04)",
           "left": "threshold_fits: short-term high/low = fractal 2/2",
           "right": "threshold_fits: short-term high/low = fractal 2/2",
           "pool_window": "declared-before-run: finite pool memory for the probe",
           "min_swept": "declared-before-run: 'a run of previous lows' = at least 2",
           "max_wait_bars": "declared-before-run: the turn must come within 6h",
           "adr_days": "declared-before-run: ADR is eyeballed in the corpus (method_spec "
                       "§5.2, no lookback given); 5 sessions",
           "spent_frac": "declared-before-run: 'most of the average daily range is already "
                         "covered' = 75%",
           "min_bars": "declared-before-run: README trap 6 stub-session guard",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "null_tod_tol_min": "declared-before-run (of this second, corrected run): "
                               "README trap 9 - events cluster 10:00-17:00 NY; see notes"}
    return res, op, src, probe


if __name__ == "__main__":
    import os, pickle
    pk = os.path.join(cl.CACHE_DIR, f"liquidity_own_01a_{CID}_result.pkl")
    if os.path.exists(pk):
        res, op, src, probe = pickle.load(open(pk, "rb"))
    else:
        res, op, src, probe = run()
        pickle.dump((res, op, src, probe), open(pk, "wb"))
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
    print("  wrote", cl.write_result(CID, None, res, operationalization=op,
                                     params_source=src, script=__file__, probe=probe,
                                     notes=NOTES))
