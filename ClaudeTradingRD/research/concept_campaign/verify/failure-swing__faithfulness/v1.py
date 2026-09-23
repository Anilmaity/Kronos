import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
D = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a"
sys.path.insert(0, D); sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
from _common import atr, swings3
import importlib.util
spec = importlib.util.spec_from_file_location("fs", D + "/failure-swing.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m1 = cl.load_m1()
mkt = cl.get_market()

def detect(b, mode):
    h = b["high"].to_numpy(float); l = b["low"].to_numpy(float)
    a = atr(b, 14); sh, sl = swings3(b); rows = []
    for bull in (False, True):
        x = -l if bull else h
        pts = np.flatnonzero(sl if bull else sh)
        for k in range(1, len(pts)):
            p0, p1 = pts[k-1], pts[k]; conf = p1 + 1
            if conf >= len(b) or not np.isfinite(a[conf]): continue
            between = x[p0+1:p1].max() if p1 - p0 > 1 else -np.inf
            fail = (x[p1] < x[p0]) and not (between >= x[p0])
            if mode == "fail" and not fail: continue
            if mode == "genuine" and not (x[p1] > x[p0]): continue
            lvl = x[p1]
            if x[conf] >= lvl: continue
            rows.append((conf, -lvl if bull else lvl, not bull, (x[p1]-x[p0])/a[conf]))
    r = pd.DataFrame(rows, columns=["conf", "level", "above", "rel"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[r["conf"].to_numpy()])
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "level": r.level.to_numpy(float),
                       "above": r.above.to_numpy(bool), "rel": r.rel.to_numpy()})
    return ev.sort_values(["decision_time", "above"]).reset_index(drop=True)

def level_rate_tod(times, level, above, hb, tod=None):
    t = pd.DatetimeIndex(times); level = np.asarray(level, float); above = np.asarray(above, bool)
    hb = np.full(len(t), hb, np.int64)
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o)-1)]
    dist = level - first_px
    def _touch(tk, lv, ab, h):
        out = np.zeros(len(tk), bool)
        for side, mm in (("above", ab), ("below", ~ab)):
            if mm.any(): out[mm] = cl.touch(tk[mm], lv[mm], side, horizon_bars=h[mm])["hit"].to_numpy()
        return out
    obs = _touch(t, level, above, hb).astype(float)
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED, tod_tol_min=tod)
    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        if tk.tz is None: tk = tk.tz_localize("UTC")
        ok = ~tk.isna(); out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o)-1)]
        out[ok] = _touch(tk[ok], px + dist[ok], above[ok], hb[ok]); return out
    return obs, null_fn, dist

def run(tag, ev, hzn=300, tod=None, yearly=False):
    obs, nf, dist = level_rate_tod(ev.decision_time, ev.level, ev.above, hzn, tod)
    r = cl.rate_test(obs, ev.decision_time, available_at=ev.available_at, null_fn=nf, claim="+", n_boot=500)
    print(f"{tag:34s} n={r['n']:6d} obs={r['observed_rate']:.4f} null={r['null_rate']:.4f} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {r['verdict']} H1={r['halves']['H1']['diff']:+.4f} H2={r['halves']['H2']['diff']:+.4f} ov={r.get('ctrl_overlap')}", flush=True)
    if r.get("blocks"): print("    blocks", {k: round(v.get('diff') or 0, 4) for k, v in r['blocks'].items() if isinstance(v, dict)})
    if yearly:
        nulls = np.column_stack([nf(None, k) for k in range(5)])
        d = obs - np.nanmean(nulls, 1)
        yr = pd.DatetimeIndex(ev.decision_time).year
        print(pd.Series(d).groupby(yr).agg(["mean", "count"]).round(4).T.to_string())
    return r

b15 = cl.build_bars(m1, "15min")
evb = detect(b15, "fail")
ref = cl.cache_frame("fs_b_15min_0.25", lambda: m.detect(cl.load_m1(), "b"))
print("repro frame equal:", len(evb), len(ref), np.allclose(evb.level.values, ref.level.values) if len(evb)==len(ref) else None)
run("b repro 15m h300", evb, yearly=True)
run("b tod30", evb, tod=30)
run("genuine (higher high) 15m", detect(b15, "genuine"))
run("all swings 15m", detect(b15, "all"))
for hz in (120, 600): run(f"b 15m h{hz}", evb, hzn=hz)
b1h = cl.build_bars(m1, "1h")
run("b 1h h300", detect(b1h, "fail"))
run("b 1h h1200", detect(b1h, "fail"), hzn=1200)
run("genuine 1h h1200", detect(b1h, "genuine"), hzn=1200)
