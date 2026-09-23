"""Independent re-implementation of reading (a) from the YAML; verifier scratch."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl

def frac(h, l, k=2):
    n=len(h); sh=np.zeros(n,bool); sl=np.zeros(n,bool)
    for i in range(k, n-k):
        if h[i] > h[i-k:i].max() and h[i] >= h[i+1:i+k+1].max(): sh[i]=True
        if l[i] < l[i-k:i].min() and l[i] <= l[i+1:i+k+1].min(): sl[i]=True
    return sh, sl

def detect(m1, ret_bars=4, fill_bars=12, life=24, swing=2, entry_frac=0.5):
    b = cl.build_bars(m1, "15min"); h1 = cl.build_bars(m1, "1h"); d1 = cl.build_bars(m1, "1D")
    H,L,C = (b[c].to_numpy() for c in ("high","low","close"))
    bst = b.index.values.astype("datetime64[ns]").astype(np.int64)
    bct = pd.DatetimeIndex(b.close_time).tz_convert("UTC").as_unit("ns").asi8
    # prior completed trading day hi/lo as of 15m bar start
    dct = pd.DatetimeIndex(d1.close_time).tz_convert("UTC").as_unit("ns").asi8
    j = np.searchsorted(dct, bst, side="right") - 1
    pdl = np.where(j>=0, d1.low.to_numpy()[np.clip(j,0,None)], np.nan)
    pdh = np.where(j>=0, d1.high.to_numpy()[np.clip(j,0,None)], np.nan)
    # 1h FVGs
    hH,hL,hC = (h1[c].to_numpy() for c in ("high","low","close"))
    hct = pd.DatetimeIndex(h1.close_time).tz_convert("UTC").as_unit("ns").asi8
    fv = {True: [], False: []}
    for k in range(2, len(h1)):
        if hL[k] > hH[k-2]: bull, top, bot = True, hL[k], hH[k-2]
        elif hH[k] < hL[k-2]: bull, top, bot = False, hL[k-2], hH[k]
        else: continue
        dead = np.iinfo(np.int64).max
        for q in range(k+1, min(len(h1), k+1+life)):
            if (bull and hC[q] < bot) or ((not bull) and hC[q] > top): dead = hct[q]; break
        exp = hct[min(len(h1)-1, k+life)]
        fv[bull].append((hct[k], min(dead, exp), top, bot))
    sh, sl = frac(H, L, swing)
    mt = m1.index.values.astype("datetime64[ns]").astype(np.int64)
    ML, MH = m1.low.to_numpy(), m1.high.to_numpy()
    rows = []
    n = len(b)
    for bull in (True, False):
        piv = sl if bull else sh; lev = L if bull else H
        arr = np.array(fv[bull], dtype=float) if fv[bull] else np.zeros((0,4))
        cur = np.nan
        for i in range(n):
            q = i - swing - 1          # swing at q confirmed by close of q+swing = i-1
            if q >= 0 and piv[q]: cur = lev[q]
            if np.isnan(cur): continue
            if not ((L[i] < cur) if bull else (H[i] > cur)): continue
            level = cur; cur = np.nan     # consumed
            ok = (L[i] <= pdl[i]) if bull else (H[i] >= pdh[i])
            if not ok and len(arr):
                a = arr
                live = (a[:,0] <= bst[i]) & (a[:,1] > bst[i])
                if bull: ov = live & (L[i] <= a[:,2]) & (H[i] >= a[:,3])
                else:    ov = live & (H[i] >= a[:,3]) & (L[i] <= a[:,2])
                ok = ov.any()
            if not ok: continue
            back = False; got = None
            for k in range(i, min(n, i+ret_bars+1)):
                if (C[k] > level) if bull else (C[k] < level): back = True
                if back and k >= i+2:
                    if bull and L[k] > H[k-2]: got = (k, L[k], H[k-2]); break
                    if (not bull) and H[k] < L[k-2]: got = (k, L[k-2], H[k]); break
            if got is None: continue
            k, top, bot = got
            stop = L[i:k+1].min() if bull else H[i:k+1].max()
            px = bot + entry_frac*(top-bot) if bull else top - entry_frac*(top-bot)
            a0 = np.searchsorted(mt, bct[k]); a1 = np.searchsorted(mt, bct[min(n-1,k+fill_bars)])
            for m in range(a0, a1):
                if bull:
                    if ML[m] <= stop: break
                    if ML[m] <= px: rows.append((mt[m]+60_000_000_000, 1, stop, i, k, m, px)); break
                else:
                    if MH[m] >= stop: break
                    if MH[m] >= px: rows.append((mt[m]+60_000_000_000, -1, stop, i, k, m, px)); break
    ev = pd.DataFrame(rows, columns=["decision_time","direction","stop_px","i","k","m","limit_px"])
    ev["decision_time"] = pd.to_datetime(ev.decision_time, utc=True)
    ev["available_at"] = ev.decision_time; ev["rr"] = 2.0
    return ev.sort_values(["decision_time","direction"]).reset_index(drop=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1); ev.to_parquet("indep_events.parquet")
    o = pd.read_parquet("orig_events.parquet")
    print("indep", len(ev), "orig", len(o))
    key = lambda d: set(zip(pd.DatetimeIndex(d.decision_time).asi8, d.direction))
    ki, ko = key(ev), key(o); print("overlap", len(ki & ko), "only indep", len(ki-ko), "only orig", len(ko-ki))
    r = cl.trade_test(ev[["decision_time","available_at","direction","stop_px","rr"]], max_hold="150min")
    for kk in ("n","avg_R","diff","ci_lo","ci_hi","p","verdict","verdict_detail","ties"): print(kk, r.get(kk))
