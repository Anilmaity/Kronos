"""high-resistance-target-adjustment (TTrades own voice, specified) — batch liquidity_own_01a.

Rule: "When the level you would otherwise target is HIGH RESISTANCE - price already
swept it before reversing, and in his example took it, closed back inside, then opened
and closed back inside again - do not use that extreme as the target ... the
high-resistance extreme is much harder to break through", so substitute a nearer
level. The testable content is the premise that justifies the substitution: the HR
extreme is HARDER TO REACH than its distance implies. rate_test, claim '-':

  HR extreme (15m): a bar trades through >= 1 untaken confirmed fractal-2/2 swing high
    (tracked 7 days) on one side only, closes back below all of them, and the next bar
    stays at or below that bar's high and also closes back below them. X = the sweep
    bar's high. (Mirror for lows.)
  Decision: the first 15m swing low (fractal 2/2) formed after the sweep bar is
    confirmed while X is still untouched, within 24 bars of the sweep — the moment a
    trader turns long and would look up at X as the target.
  Hit: any M1 high >= X within the next 360 M1 bars.
  Null: a level at the same distance above the first M1 open at matched random
    moments (+/-30d), same 360-bar horizon.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

CID = "high-resistance-target-adjustment"
TF = "15min"
LEFT = RIGHT = 2
POOL_WINDOW = pd.Timedelta("7D")
MAX_WAIT = 24            # bars from the sweep to the turning swing
HORIZON_BARS = 360


def detect(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    H, L, C = (b[k].to_numpy() for k in ("high", "low", "close"))
    idx = b.index
    ct = pd.DatetimeIndex(b["close_time"])
    is_h, is_l = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    act = {1: [], -1: []}           # side -> [(level, swing time)]
    pend = []                       # sweeps awaiting the 2nd close inside: (side, X, lvl, j0)
    hr = []                         # confirmed HR extremes: (side, X, j0)
    out = []
    for j in range(len(b)):
        i = j - RIGHT - 1
        if i >= 0 and is_h[i]:
            act[1].append((H[i], idx[i]))
        if i >= 0 and is_l[i]:
            act[-1].append((L[i], idx[i]))
        for s in (1, -1):
            act[s] = [p for p in act[s] if idx[j] - p[1] <= POOL_WINDOW]
        # 1. existing HR extremes: reached by this bar? expired?
        keep = []
        for (s, X, j0) in hr:
            reached = H[j] >= X if s == 1 else L[j] <= X
            if not reached and j - j0 <= MAX_WAIT:
                keep.append((s, X, j0))
        hr = keep
        # 2. pending sweeps from bar j-1: second bar must stay inside
        for (s, X, lvl, j0) in pend:
            ok = (H[j] <= X and C[j] < lvl) if s == 1 else (L[j] >= X and C[j] > lvl)
            if ok:
                hr.append((s, X, j0))
        pend = []
        # 3. turning swing confirmed at the close of bar j -> event
        ci = j - RIGHT
        keep = []
        for (s, X, j0) in hr:
            turn = (is_l[ci] if s == 1 else is_h[ci]) if ci > j0 + 1 else False
            if turn:
                out.append((ct[j], ct[j], s, X))
            else:
                keep.append((s, X, j0))
        hr = keep
        # 4. new sweeps on this bar
        tk_h = [p[0] for p in act[1] if H[j] > p[0]]
        tk_l = [p[0] for p in act[-1] if L[j] < p[0]]
        act[1] = [p for p in act[1] if H[j] <= p[0]]
        act[-1] = [p for p in act[-1] if L[j] >= p[0]]
        if tk_h and not tk_l and C[j] < min(tk_h):
            pend.append((1, H[j], min(tk_h), j))
        elif tk_l and not tk_h and C[j] > max(tk_l):
            pend.append((-1, L[j], max(tk_l), j))
    ev = pd.DataFrame(out, columns=["decision_time", "available_at", "side", "level"])
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)


def run():
    ev = cl.cache_frame(f"{CID}_{TF}_w{MAX_WAIT}", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    lvl, side = ev["level"].to_numpy(), ev["side"].to_numpy()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = lvl - px
    obs = np.full(len(t), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        k = side == s
        obs[k] = cl.touch(t[k], lvl[k], nm, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        o = np.full(len(t), np.nan)
        for s, nm in ((1, "above"), (-1, "below")):
            ok = (~tk.isna()) & (side == s)
            p = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
            o[ok] = cl.touch(tk[ok], p + dist[ok], nm,
                             horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return o

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="-")
    op = {"rules": [
        "pools: untaken 15m fractal-2/2 swing highs/lows, tracked 7 days",
        "HR extreme: a 15m bar takes >= 1 pool on one side only and closes back beyond "
        "all of them; the next bar stays inside that bar's extreme and closes back "
        "beyond them too; X = the sweep bar's extreme",
        "decision: first opposite 15m swing formed after the sweep, confirmed while X is "
        "untouched and within 24 bars of the sweep",
        "hit: X traded within 360 M1 bars; null: same distance at matched random "
        "moments, same horizon; claim '-' (HR extreme harder to reach)"],
        "params": {"tf": TF, "left": LEFT, "right": RIGHT, "pool_window": "7D",
                   "max_wait_bars": MAX_WAIT, "horizon_m1_bars": HORIZON_BARS}}
    src = {"tf": "corpus: source YAML timeframes.htf ['15m', '5m'] (education_ict_02)",
           "left": "threshold_fits: short-term high/low = fractal 2/2",
           "right": "threshold_fits: short-term high/low = fractal 2/2",
           "pool_window": "declared-before-run: finite pool memory for the probe",
           "max_wait_bars": "declared-before-run: the turn must come within 6h of the sweep",
           "horizon_m1_bars": "declared-before-run: 6 trading hours, same as the batch's "
                              "other 15m level tests"}
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
                                     params_source=src, script=__file__, probe=probe))
