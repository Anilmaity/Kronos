"""Faithfulness/robustness grid. Does NOT call rate_test (no ledger pollution); own weekly-block bootstrap."""
import sys, importlib.util, itertools, pickle, os
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("bga", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_guest_01a/breakaway-gap-anticipation.py")
bga = importlib.util.module_from_spec(spec); spec.loader.exec_module(bga)
HERE = os.path.dirname(__file__)
m1 = cl.load_m1()
b = cl.build_bars(m1, "1h")
H, L, C = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy()
ct = pd.DatetimeIndex(b.close_time).as_unit("ns").asi8
N = len(b)

def outcomes(dt, far, d, hz, mode):
    i0 = np.searchsorted(ct, pd.DatetimeIndex(dt).as_unit("ns").asi8) + 1  # first bar after decision close
    out = np.zeros(len(dt), bool)
    for q in range(len(dt)):
        s, e = i0[q], min(N, i0[q] + hz)
        if s >= e: continue
        if mode == "wick":
            x = L[s:e] if d[q] == 1 else H[s:e]
        else:
            x = C[s:e]
        out[q] = (x <= far[q]).any() if d[q] == 1 else (x >= far[q]).any()
    return out

def run(allf, hz, mode, rng_seed=0, extra=None):
    ev = allf[allf.overlap].reset_index(drop=True); base = allf[~allf.overlap].reset_index(drop=True)
    obs = outcomes(ev.decision_time, ev.far_edge.to_numpy(), ev.direction.to_numpy(), hz, mode).astype(float)
    bh = outcomes(base.decision_time, base.far_edge.to_numpy(), base.direction.to_numpy(), hz, mode).astype(float)
    bt = pd.DatetimeIndex(base.decision_time).as_unit("ns").asi8; bd = base.direction.to_numpy()
    key_b = np.log(base.dist_pct.clip(lower=1e-6).to_numpy()); key_e = np.log(ev.dist_pct.clip(lower=1e-6).to_numpy())
    if extra is not None:
        kb2, ke2 = extra(base), extra(ev)
    et = pd.DatetimeIndex(ev.decision_time).as_unit("ns").asi8; ed = ev.direction.to_numpy()
    win = pd.Timedelta(days=30).value
    lo = np.searchsorted(bt, et - win); hi = np.searchsorted(bt, et + win)
    nul = np.full(len(ev), np.nan)
    for q in range(len(ev)):
        c = np.arange(lo[q], hi[q]); c = c[bd[c] == ed[q]]
        if len(c) < 5: continue
        dist = np.abs(key_b[c] - key_e[q])
        if extra is not None: dist = dist + np.abs(kb2[c] - ke2[q])
        nul[q] = bh[c[np.argsort(dist, kind="stable")[:5]]].mean()
    ok = ~np.isnan(nul)
    d = obs[ok] - nul[ok]
    wk = pd.DatetimeIndex(ev.decision_time[ok]).tz_convert(None).to_period("W").astype(str)
    codes, uniq = pd.factorize(wk)
    sums = np.bincount(codes, d); cnts = np.bincount(codes)
    rng = np.random.default_rng(rng_seed); nb = len(uniq)
    # moving block over weeks (block 4 weeks)
    bs = []
    for _ in range(1000):
        starts = rng.integers(0, nb, nb // 4 + 1)
        idx = (starts[:, None] + np.arange(4)).ravel() % nb
        idx = idx[:nb]
        bs.append(sums[idx].sum() / cnts[idx].sum())
    lo_, hi_ = np.percentile(bs, [2.5, 97.5])
    yrs = pd.DatetimeIndex(ev.decision_time[ok]).year
    per = pd.Series(d).groupby(np.asarray(yrs)).mean().round(3).to_dict()
    return dict(n=int(ok.sum()), obs=obs[ok].mean(), null=nul[ok].mean(), diff=d.mean(), lo=lo_, hi=hi_, years=per)

if __name__ == "__main__":
    rows = []
    for lmb, lfv in [(40, 10), (20, 10), (60, 10), (40, 5), (40, 20), (20, 5), (60, 20)]:
        bga.L_MB, bga.L_FV = lmb, lfv
        cp = f"{HERE}/allf_{lmb}_{lfv}.pkl"
        if os.path.exists(cp): allf = pd.read_pickle(cp)
        else: allf = bga.detect_all(m1); allf.to_pickle(cp)
        combos = [(120, "wick"), (24, "wick"), (48, "wick"), (240, "wick"), (120, "close")] if (lmb, lfv) == (40, 10) else [(120, "wick")]
        for hz, mode in combos:
            r = run(allf, hz, mode)
            r.update(lmb=lmb, lfv=lfv, hz=hz, mode=mode, share=allf.overlap.mean())
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "years"}, flush=True)
            if (lmb, lfv, hz, mode) == (40, 10, 120, "wick"): print("years", r["years"])
            rows.append(r)
    pd.DataFrame(rows).to_csv(f"{HERE}/grid.csv", index=False)
