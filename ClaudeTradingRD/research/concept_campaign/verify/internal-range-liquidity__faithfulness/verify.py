"""Faithfulness/robustness verification of internal-range-liquidity reading b (CE target).
Scratch only; does not write results."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02a")
import concept_lab as cl
from detectors.primitives import swing_points

def detect(m1, tf="1h", grid="forex", range_bars=50, swing=2, consume="touch", keep_sweeps=False):
    b = cl.build_bars(m1, tf, grid4h=grid)
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    sw = swing_points(b, left=swing, right=swing)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    sh, sl, bull, bear, rows, sweeps = [], [], [], [], [], []
    for j in range(len(b)):
        p = j - 1 - swing
        if p >= swing:
            if is_sh[p]: sh.append((p, h[p]))
            if is_sl[p]: sl.append((p, l[p]))
        sh = [s for s in sh if j - s[0] <= range_bars]
        sl = [s for s in sl if j - s[0] <= range_bars]
        buy = any(h[j] > s[1] for s in sh); sell = any(l[j] < s[1] for s in sl)
        sh = [s for s in sh if not h[j] > s[1]]; sl = [s for s in sl if not l[j] < s[1]]
        if consume == "touch":
            bull = [g for g in bull if j - g[0] <= range_bars and l[j] > g[1]]
            bear = [g for g in bear if j - g[0] <= range_bars and h[j] < g[1]]
        else:  # "fill": consumed only when traded through the far edge; near edge tracks partial fill
            nb = []
            for g in bull:
                if j - g[0] <= range_bars and l[j] > g[2]:
                    nb.append((g[0], min(g[1], l[j]) if j > g[0] else g[1], g[2]))
            bull = nb
            nr = []
            for g in bear:
                if j - g[0] <= range_bars and h[j] < g[2]:
                    nr.append((g[0], max(g[1], h[j]) if j > g[0] else g[1], g[2]))
            bear = nr
        if j >= 2:
            if l[j] > h[j-2]: bull.append((j, l[j], h[j-2]))
            if h[j] < l[j-2]: bear.append((j, h[j], l[j-2]))
        if buy == sell: continue
        sweeps.append((j, -1 if buy else 1))
        if buy:
            cand = [g for g in bull if g[1] < c[j]]
            if cand:
                g = max(cand, key=lambda z: z[1]); rows.append((j, -1, g[1], 0.5*(g[1]+g[2])))
        else:
            cand = [g for g in bear if g[1] > c[j]]
            if cand:
                g = min(cand, key=lambda z: z[1]); rows.append((j, 1, g[1], 0.5*(g[1]+g[2])))
    ct = b["close_time"].to_numpy()
    r = np.array(rows, float); pos = r[:, 0].astype(int)
    ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(ct[pos]), "direction": r[:, 1].astype(int),
                       "near_edge": r[:, 2], "ce": r[:, 3]})
    ev["available_at"] = ev["decision_time"]
    s = np.array(sweeps)
    sw_df = pd.DataFrame({"t": pd.DatetimeIndex(ct[s[:, 0]]), "direction": s[:, 1]})
    return ev, sw_df

mkt = cl.get_market()

def hit(times, level, dirs, H):
    out = np.zeros(len(times), bool)
    for s, side in ((1, "above"), (-1, "below")):
        m = dirs == s
        if m.any():
            out[m] = cl.touch(times[m], level[m], side, horizon_bars=H)["hit"].to_numpy()
    return out

def run(label, ev, col="ce", H=600, tod=None, sweeps=None):
    t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy(int)
    px0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o)-1)]
    lvl = ev[col].to_numpy(float); dist = lvl - px0
    obs = hit(t, lvl, d, H)
    if sweeps is None:
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=tod)
        def null_fn(rng, k):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
            out = np.full(len(t), np.nan); p = mkt.o[mkt.pos_at_or_after(tk[ok])]
            out[ok] = hit(tk[ok], p + dist[ok], d[ok], H); return out
    else:
        # placebo: other ERL-purge bars (same direction, +/-30d, FVG or not), same signed distance
        rng0 = np.random.default_rng(cl.rules.SEED)
        rt = np.full((len(t), 5), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
        for s in (1, -1):
            st = sweeps.loc[sweeps.direction == s, "t"].to_numpy().astype("datetime64[ns]")
            idx = np.where(d == s)[0]
            tv = t.tz_convert("UTC").tz_localize(None).to_numpy().astype("datetime64[ns]")
            w = np.timedelta64(30, "D")
            lo = np.searchsorted(st, tv[idx] - w); hi = np.searchsorted(st, tv[idx] + w)
            for ii, a, bb in zip(idx, lo, hi):
                cands = st[a:bb]; cands = cands[cands != tv[ii]]
                if len(cands): rt[ii] = rng0.choice(cands, 5)
        def null_fn(rng, k):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
            out = np.full(len(t), np.nan); p = mkt.o[mkt.pos_at_or_after(tk[ok])]
            out[ok] = hit(tk[ok], p + dist[ok], d[ok], H); return out
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+")
    bl = " ".join(f"{k}:{v['diff']:+.3f}" for k, v in res["blocks"].items())
    hv = " ".join(f"{k}:{v['diff']:+.3f}" for k, v in res["halves"].items() if isinstance(v, dict))
    print(f"{label:38s} n={res['n']:5d} obs={res['observed_rate']:.3f} null={res['null_rate']:.3f} "
          f"diff={res['diff']:+.4f} [{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] {res['verdict']:12s} {hv} | {bl}", flush=True)
    return res

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev, sw = detect(m1)
    run("baseline 1h CE (reproduce)", ev)
    run("baseline 1h near edge", ev, col="near_edge")
    run("1h CE, tod_tol=30", ev, tod=30)
    run("1h CE, sweep-conditioned placebo", ev, sweeps=sw)
    run("1h near, sweep-conditioned placebo", ev, col="near_edge", sweeps=sw)
    run("1h CE, H=300", ev, H=300)
    run("1h CE, H=1200", ev, H=1200)
    evf, swf = detect(m1, consume="fill")
    run("1h CE, unfilled=not traded through", evf)
    run("1h CE fill-def, sweep placebo", evf, sweeps=swf)
    for rb in (20, 100):
        e, _ = detect(m1, range_bars=rb); run(f"1h CE range_bars={rb}", e)
    for g in ("forex", "futures"):
        e, s = detect(m1, tf="4h", grid=g)
        run(f"4h {g} CE (H=2400)", e, H=2400)
        run(f"4h {g} CE sweep placebo", e, H=2400, sweeps=s)
    e, s = detect(m1, tf="15min"); run("15m CE (H=150)", e, H=150)
