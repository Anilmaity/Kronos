"""relatively-equal-highs-lows (liquidity, TTrades own voice, contested) — batch liquidity_own_01b.

Two distinct readings in the concept's own variants:

 a  TARGET reading (Njs-eRpeP9Q "They become targets for later"; U8xH2dEgH5A): consecutive
    swing lows L1, L2 with |L1 - L2| <= TOL form one sellside pool at min(L1, L2) (mirror
    for highs); once formed and untaken it is carried forward as a target. Rate test: the
    pool is traded through within three trading days of L2's confirmation more often than
    an arbitrary level at the same distance (same NY clock, +/-30 d, same M1-bar count).

 b  DO-NOT-TRADE-AWAY reading (m8xcjkOuBHU "I'm not trading away from three equal highs"):
    "Do not take a reversal whose invalidation sits behind equal highs" — the level is
    expected to be run again. Gate test on the phase-3 rung-0 1h CISD book: gate = the
    reversal's extreme (the protected swing = the stop) is relatively equal to the
    previous same-side swing (|diff| <= TOL). claim '-': those reversals do WORSE.

TOL is not given by the source (the blocking gap). Declared before the first run:
TOL = 0.10 x ATR(14) of the 1h bars, read on the bar before the later swing.
Timeframe 1h (one of the concept's htf list; the most data of those).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

TF = "1h"
LEFT, RIGHT = 2, 2
TOL_ATR = 0.10
ATR_N = 14
HORIZON_BARS = 3 * 1380          # three trading days of M1 bars (23h x 60)
TOD_TOL = 30
CISD = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
RR, MAX_HOLD = 2.0, "10h"


def atr(b):
    h, l, c = b["high"].to_numpy(float), b["low"].to_numpy(float), b["close"].to_numpy(float)
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()


def detect_pools(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    a = atr(b)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b)
    rows = []
    for side, col in ((-1, "swing_low"), (1, "swing_high")):
        idx = np.flatnonzero(sw[col].to_numpy())
        idx = idx[idx + RIGHT < n]
        x = l if side == -1 else h
        for s1, s2 in zip(idx[:-1], idx[1:]):
            tol = TOL_ATR * a[s2 - 1]
            if not np.isfinite(tol) or abs(x[s1] - x[s2]) > tol:
                continue
            dpos = s2 + RIGHT                                   # L2 confirmed at this bar's close
            seg = x[s1 + 1:dpos + 1]
            if side == -1:
                pool = min(x[s1], x[s2])
                if (seg < pool).any():
                    continue
            else:
                pool = max(x[s1], x[s2])
                if (seg > pool).any():
                    continue
            rows.append((ct[dpos], pool, side))
    out = pd.DataFrame(rows, columns=["decision_time", "level", "side"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"], tz="UTC") if len(out) else \
        pd.DatetimeIndex([], tz="UTC")
    out["available_at"] = out["decision_time"]
    out = out[["decision_time", "available_at", "level", "side"]]
    return out.sort_values(["decision_time", "side"]).reset_index(drop=True)


def detect_gate(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR})
    if len(out) == 0:
        out["eq_extreme"] = pd.Series(dtype=bool)
        return out
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    a = atr(b)
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    bull = out["direction"].to_numpy() == 1
    eq = np.zeros(len(out), bool)
    valid = np.zeros(len(out), bool)
    for e, p in enumerate(pos):
        tol = TOL_ATR * a[p - 1] if p >= 1 else np.nan
        if not np.isfinite(tol):
            continue
        valid[e] = True
        flags = sl if bull[e] else sh
        prev = np.flatnonzero(flags[:p - RIGHT])        # swings confirmed before the extreme bar
        if len(prev) == 0:
            continue
        s = prev[-1]                                    # the previous same-side swing (consecutive)
        x = l if bull[e] else h
        eq[e] = abs(x[s] - x[p]) <= tol
    out["eq_extreme"] = eq
    return out[valid].reset_index(drop=True)


def rate_run(m1):
    ev = cl.cache_frame(f"eqhl_pools_{TF}_{TOL_ATR}_{ATR_N}", lambda: detect_pools(m1))
    probe = cl.probe_lookahead(detect_pools, ev, lookback="15D")
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
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, outcome_horizon="3D", claim="+")
    return ev, res, probe


if __name__ == "__main__":
    m1 = cl.load_m1()
    tol_src = "declared-before-run: TOL = 0.10 x ATR(14) on the 1h bars (source gives no tolerance; ambiguity 'relatively equal has no numeric tolerance')"
    # reading a
    ev, res, probe = rate_run(m1)
    print("a", len(ev), {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    op = {"rules": ["1h 2/2 fractal swings; consecutive same-side swings with |L1-L2| <= 0.10 x ATR14(1h) form one pool at min (lows) / max (highs)",
                    "decision at the close of the bar that confirms L2; pool must be untaken from L1 to the decision and still beyond the next M1 open",
                    "hit = price trades to the pool within 3 trading days (4,140 M1 bars)",
                    "claim: equal-high/low pools are reached more often than an arbitrary level at the same distance"],
          "params": {"tf": TF, "swing": "2/2", "tol_atr": TOL_ATR, "atr_n": ATR_N, "horizon_bars": HORIZON_BARS,
                     "null": "distance-matched, NY clock +/-30min, +/-30d, 5 reps, same bar count"}}
    src = {"tf": "declared-before-run: 1h, one of the concept's listed htf timeframes (1D/4H/1H), chosen for sample size",
           "swing": "phase3: 2/2 fractal swings (locked config)", "tol_atr": tol_src,
           "atr_n": "declared-before-run: standard 14-bar ATR",
           "horizon_bars": "method_spec: §1.1 relevant-swing look-back on the hourly chart is three days; used as the carry-forward horizon ('later' is not bounded)",
           "null": "declared-before-run: same signed distance from the open at a random other day's same NY minute (+/-30 min, +/-30 d), same M1-bar count, 5 reps"}
    p = cl.write_result("relatively-equal-highs-lows", "a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Target reading. Detection rule 1 (|L1-L2|<=TOL, pool = min/max). Consecutive swings only; clusters of 3+ are subsumed as overlapping pairs.")
    print("wrote", p)
    # reading b
    evg = cl.cache_frame(f"eqhl_gate_{TF}_{TOL_ATR}_{ATR_N}", lambda: detect_gate(m1))
    probe = cl.probe_lookahead(detect_gate, evg, lookback="20D")
    res = cl.gate_test(evg, "eq_extreme", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="-")
    print("b fire", float(evg["eq_extreme"].mean()), {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": ["baseline: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open, stop at the protected swing, 2R, 10h",
                    "gate: the reversal's extreme (= the stop's swing) is within 0.10 x ATR14(1h) of the previous confirmed same-side 1h swing (a relatively-equal pair)",
                    "claim '-': reversals traded away from equal highs/lows do worse than the rest (control-adjusted R)"],
          "params": {"tf": TF, **CISD, "rr": RR, "max_hold": MAX_HOLD, "tol_atr": TOL_ATR, "atr_n": ATR_N}}
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"tol_atr": tol_src, "atr_n": "declared-before-run: standard 14-bar ATR"})
    p = cl.write_result("relatively-equal-highs-lows", "b", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Do-not-trade-away reading (m8xcjkOuBHU). Two equal swings, not three: the source treats two equal lows the same way (ambiguity list).")
    print("wrote", p)
