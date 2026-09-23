"""buyside-sellside-liquidity (TTrades own voice, contested) — batch liquidity_own_01a.

Reading a (definition / measurable "hit rate of an untaken swing pool being traded
through within N bars"): an obvious swing high (low) is a buyside (sellside) pool
where stops rest, so price is DRAWN to it. rate_test: is a freshly confirmed 15m
fractal-2/2 swing extreme traded through within the horizon more often than a level
at the same distance from price at a matched random moment?  claim '+'.

Reading b (execution.bias: "a pool that is taken and then rejected (close back
inside) flips bias to the opposite pool"): trade_test. When a 15m bar trades through
one or more untaken confirmed swing highs and closes back below all of them, go short
at that bar's close, stop = that bar's high, target = the nearest untaken confirmed
swing low below the close (the opposite pool). Mirror for sellside.  claim '+'.

All parameters declared before the first run (see PARAMS / SRC).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

CID = "buyside-sellside-liquidity"
TF = "15min"
LEFT = RIGHT = 2
POOL_WINDOW = pd.Timedelta("7D")      # a pool older than this is no longer tracked
HORIZON_BARS = 360                    # reading a: 6 trading hours of M1 bars
MAX_HOLD = "6h"                       # reading b: same 6h, trading-time basis
SRC_COMMON = {
    "tf": "corpus: source YAML timeframes.htf ['15m'] (education_ict_03 / the_foundation_01)",
    "left": "threshold_fits: short-term high/low = fractal 2/2 (displacement_windows)",
    "right": "threshold_fits: short-term high/low = fractal 2/2 (displacement_windows)",
}


NOTES = {"a": "The rate_test ran twice: the first run's write_result was refused on a "
              "params_source schema error (keys/prefixes only). The detector, null and test "
              "are unchanged between runs, and the run is deterministic, so the numbers "
              "match the first run (diff +0.0036, CI [-0.0002, +0.0075], NULL)."}


def swings(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open", "high", "low", "close"]], LEFT, RIGHT)
    return b, sw


# ── reading a: swing pools as magnets ───────────────────────────────────────
def detect_a(m1):
    b, sw = swings(m1)
    n = len(b)
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for col, side, px in (("swing_high", 1, "high"), ("swing_low", -1, "low")):
        pos = np.flatnonzero(sw[col].to_numpy())
        pos = pos[pos + RIGHT < n]
        t = ct[pos + RIGHT]                            # confirmed at close of bar i+2
        rows.append(pd.DataFrame({"decision_time": t, "available_at": t,
                                  "level": b[px].to_numpy()[pos], "side": side}))
    ev = pd.concat(rows, ignore_index=True)
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)


# ── reading b: sweep-and-reject of a pool -> the opposite pool ──────────────
def detect_b(m1):
    b, sw = swings(m1)
    H, L, C = (b[k].to_numpy() for k in ("high", "low", "close"))
    idx = b.index
    ct = pd.DatetimeIndex(b["close_time"])
    is_h, is_l = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    act_h, act_l = [], []              # (level, swing bar time)
    out = []
    for j in range(len(b)):
        i = j - RIGHT - 1              # swing confirmed at close of bar j-1
        if i >= 0 and is_h[i]:
            act_h.append((H[i], idx[i]))
        if i >= 0 and is_l[i]:
            act_l.append((L[i], idx[i]))
        act_h = [p for p in act_h if idx[j] - p[1] <= POOL_WINDOW]
        act_l = [p for p in act_l if idx[j] - p[1] <= POOL_WINDOW]
        tk_h = [p[0] for p in act_h if H[j] > p[0]]
        tk_l = [p[0] for p in act_l if L[j] < p[0]]
        act_h = [p for p in act_h if H[j] <= p[0]]
        act_l = [p for p in act_l if L[j] >= p[0]]
        if tk_h and tk_l:
            continue                   # took both sides: no side rejected
        if tk_h and C[j] < min(tk_h):
            opp = [p[0] for p in act_l if p[0] < C[j]]
            if opp:
                out.append((ct[j], -1, H[j], max(opp)))
        elif tk_l and C[j] > max(tk_l):
            opp = [p[0] for p in act_h if p[0] > C[j]]
            if opp:
                out.append((ct[j], 1, L[j], min(opp)))
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "target_px"])
    ev.insert(1, "available_at", ev["decision_time"])
    return ev


def run_a():
    ev = cl.cache_frame(f"{CID}_a_{TF}_{LEFT}{RIGHT}", lambda: detect_a(cl.load_m1()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    lvl = ev["level"].to_numpy()
    side = ev["side"].to_numpy()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = lvl - px
    obs = np.full(len(t), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        k = side == s
        obs[k] = cl.touch(t[k], lvl[k], nm, horizon_bars=HORIZON_BARS)["hit"].to_numpy()
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        for s, nm in ((1, "above"), (-1, "below")):
            ok = (~tk.isna()) & (side == s)
            p = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
            out[ok] = cl.touch(tk[ok], p + dist[ok], nm,
                               horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="+")
    op = {"rules": [
        "pool := 15m fractal-2/2 swing high (buyside) / swing low (sellside), known at "
        "the close of the 2nd right-hand bar (untaken by construction)",
        "hit := any M1 high >= swing high (low <= swing low) within the next 360 M1 bars "
        "from the first M1 bar at/after the confirmation",
        "null := level at the same signed distance from the first M1 open, at matched "
        "random moments (+/-30d, 15m grid), same 360-bar horizon"],
        "params": {"tf": TF, "left": LEFT, "right": RIGHT, "horizon_m1_bars": HORIZON_BARS}}
    src = {**SRC_COMMON,
           "horizon_m1_bars": "declared-before-run: 'within N bars' has no N in the "
                              "corpus; N = 24 x 15m bars = 360 trading minutes"}
    return res, op, src, probe


def run_b():
    ev = cl.cache_frame(f"{CID}_b_{TF}_{LEFT}{RIGHT}_{POOL_WINDOW}",
                        lambda: detect_b(cl.load_m1()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", hold_basis="bars",
                        ctrl_tod_tol_min=30)
    op = {"rules": [
        "pools := untaken 15m fractal-2/2 swing highs/lows, usable from the bar after "
        "confirmation, tracked for 7 days after the swing bar",
        "sweep := a 15m bar trades through >=1 untaken pool on one side (not both) and "
        "closes back beyond ALL pools it took",
        "entry: opposite direction at the next M1 open after that bar's close",
        "stop: the sweep bar's extreme; target: nearest untaken opposite pool beyond "
        "the close; time exit after 6h of trading time"],
        "params": {"tf": TF, "left": LEFT, "right": RIGHT, "pool_window": "7D",
                   "max_hold": MAX_HOLD, "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
    src = {**SRC_COMMON,
           "pool_window": "declared-before-run: bounded pool memory (a week of swings) "
                          "so the detector is finite-history",
           "max_hold": "declared-before-run: 24 x 15m bars, same horizon as reading a",
           "hold_basis": "declared-before-run: trading-time hold (README trap 7)",
           "ctrl_tod_tol_min": "declared-before-run: concept is not about timing but "
                               "sweeps cluster in active hours (README trap 9)"}
    return res, op, src, probe


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    import pickle, os
    for r in which:
        pk = os.path.join(cl.CACHE_DIR, f"liquidity_own_01a_{CID}_{r}_result.pkl")
        if os.path.exists(pk):          # a finished run whose write failed: never re-test
            res, op, src, probe = pickle.load(open(pk, "rb"))
        else:
            res, op, src, probe = (run_a if r == "a" else run_b)()
            pickle.dump((res, op, src, probe), open(pk, "wb"))
        keys = ("n", "observed_rate", "null_rate", "avg_R", "diff", "ci_lo", "ci_hi", "p",
                "mde", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap")
        print(f"== reading {r}")
        for k in keys:
            if res.get(k) is not None:
                print(f"  {k:15s} {res[k]}")
        print("  wrote", cl.write_result(CID, r, res, operationalization=op,
                                         params_source=src, script=__file__, probe=probe,
                                         notes=NOTES.get(r, "")))
