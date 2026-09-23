"""Independent re-implementation + robustness for breakaway-gap-anticipation (verification only; no write_result)."""
import sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

m1 = cl.load_m1()
b = cl.bars("1h")
o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
start = b.index; ct = pd.DatetimeIndex(b.close_time); n = len(b)
# consecutive hourly bars
gap_ok = np.r_[False, False, (np.diff(start.asi8 if start.asi8.dtype else start)[1:] == 3600e9) & (np.diff(start.asi8)[:-1] == 3600e9)] if False else None
s_ns = start.as_unit("ns").asi8
cons = np.zeros(n, bool); cons[2:] = (s_ns[2:] - s_ns[1:-1] == 3600*10**9) & (s_ns[1:-1] - s_ns[:-2] == 3600*10**9)

# prior bearish/bullish FVG arrays (stamped at bar k: bearish gap [h[k], l[k-2]], bullish gap [h[k-2], l[k]])
bearF = np.zeros(n, bool); bullF = np.zeros(n, bool)
bearF[2:] = h[2:] < l[:-2]; bullF[2:] = l[2:] > h[:-2]
# ATR(14) of 1h (known at bar close)
tr = np.maximum(h - l, np.maximum(abs(h - np.r_[np.nan, c[:-1]]), abs(l - np.r_[np.nan, c[:-1]])))
atr = pd.Series(tr).rolling(14).mean().to_numpy()

LMB, LFV = 40, 10
rows = []
for i in np.flatnonzero((bullF | bearF) & cons):
    isb = bullF[i]
    glo, ghi = (h[i-2], l[i]) if isb else (h[i], l[i-2])
    ov = False
    # my own mitigation-block search: candle u in [i-2-LMB, i-3]
    for u in range(max(LFV + 2, i - 2 - LMB), i - 2):
        if isb:
            if c[u] <= o[u]: continue
            # low broken after u but before gap first candle i-2
            if l[u+1:i-2].size == 0 or l[u+1:i-2].min() >= l[u]: continue
            # traded into fair value: high reached into a bearish FVG formed in prior 10 bars
            ks = [k for k in range(max(2, u - LFV), u) if bearF[k] and h[u] >= h[k]]
            if not ks: continue
            if min(h[u], ghi) > max(l[u], glo): ov = True; break
        else:
            if c[u] >= o[u]: continue
            if h[u+1:i-2].size == 0 or h[u+1:i-2].max() <= h[u]: continue
            ks = [k for k in range(max(2, u - LFV), u) if bullF[k] and l[u] <= l[k]]
            if not ks: continue
            if min(h[u], ghi) > max(l[u], glo): ov = True; break
    far = glo if isb else ghi
    rows.append((ct[i], 1 if isb else -1, far, abs(c[i]-far)/c[i], (ghi-glo)/c[i], (ghi-glo)/atr[i] if atr[i] > 0 else np.nan, ov, start[i].hour))
A = pd.DataFrame(rows, columns=["t", "dir", "far", "dist", "size", "size_atr", "ov", "hr"])
print("FVGs", len(A), "overlap share", A.ov.mean())

# independent fill: own M1 scan over next 7200 M1 bars starting at first M1 >= t
mt = m1.index.as_unit("ns").asi8 if isinstance(m1.index, pd.DatetimeIndex) else pd.DatetimeIndex(m1["time"]).asi8
mh = m1["high"].to_numpy(); ml = m1["low"].to_numpy()
i0 = np.searchsorted(mt, pd.DatetimeIndex(A.t).as_unit("ns").asi8, side="left")
H = 7200
fillv = np.zeros(len(A), bool)
for j in range(len(A)):
    a, e = i0[j], min(i0[j] + H, len(mt))
    if A.dir[j] == 1: fillv[j] = (ml[a:e] <= A.far[j]).any()
    else: fillv[j] = (mh[a:e] >= A.far[j]).any()
A["fill"] = fillv
print("raw fill rate overlap", A.fill[A.ov].mean(), "non", A.fill[~A.ov].mean())
print("size medians ov/non", A["size"][A.ov].median(), A["size"][~A.ov].median(), " dist medians", A.dist[A.ov].median(), A.dist[~A.ov].median())
A.to_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/breakaway-gap-anticipation__implementation/A.pkl")

def matched(A, keys, win_d=30, k=5, tod=None):
    ev = A[A.ov].reset_index(drop=True); base = A[~A.ov].reset_index(drop=True)
    bt = pd.DatetimeIndex(base.t).as_unit("ns").asi8; et = pd.DatetimeIndex(ev.t).as_unit("ns").asi8
    W = pd.Timedelta(days=win_d).value
    lo = np.searchsorted(bt, et - W); hi = np.searchsorted(bt, et + W)
    X = np.column_stack([np.log(base[kk].clip(lower=1e-6)) for kk in keys]); Y = np.column_stack([np.log(ev[kk].clip(lower=1e-6)) for kk in keys])
    sd = X.std(0)
    M = np.full((len(ev), k), -1)
    for q in range(len(ev)):
        cand = np.arange(lo[q], hi[q]); cand = cand[base.dir.values[cand] == ev.dir.values[q]]
        if tod is not None:
            dh = np.abs(base.hr.values[cand] - ev.hr.values[q]); dh = np.minimum(dh, 24 - dh); cand = cand[dh <= tod]
        if len(cand) < k: continue
        d = np.sqrt((((X[cand] - Y[q]) / sd) ** 2).sum(1))
        M[q] = cand[np.argsort(d, kind="stable")[:k]]
    ok = (M >= 0).all(1)
    obs = ev.fill.values.astype(float); obs[~ok] = np.nan
    bh = base.fill.values.astype(float)
    def null_fn(rng, kk):
        out = np.full(len(ev), np.nan); out[ok] = bh[M[ok, kk]]; return out
    return ev, obs, null_fn, ok

for name, keys, tod in [("dist only (orig)", ["dist"], None), ("dist+size", ["dist", "size"], None),
                        ("dist+size_atr", ["dist", "size_atr"], None), ("dist, tod+-2h", ["dist"], 2),
                        ("dist+size, tod+-2h", ["dist", "size"], 2)]:
    B = A.dropna(subset=keys)
    ev, obs, nf, ok = matched(B, keys, tod=tod)
    res = cl.rate_test(obs, ev.t, available_at=ev.t, null_fn=nf, claim="-", outcome_horizon="5D", n_boot=2000)
    print(f"{name:22s} n={res['n']} obs={res['observed_rate']:.4f} null={res['null_rate']:.4f} diff={res['diff']:+.4f} CI[{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] p={res['p']:.3f} H1={res['halves']['H1']['diff']:+.4f} H2={res['halves']['H2']['diff']:+.4f} -> {res['verdict']}")
