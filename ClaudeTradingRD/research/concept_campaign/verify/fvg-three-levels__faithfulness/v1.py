import sys, importlib.util, time
import numpy as np, pandas as pd
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a')
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a/fvg-three-levels.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
cl = orig.cl
m1 = cl.load_m1()
t0=time.time()
ev = orig.detect(m1); print(len(ev), time.time()-t0)
ev.to_pickle("ev.pkl")
b15 = cl.bars("15min")
t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
up = d*(ev.leg_extreme.to_numpy()-ev.touch_close.to_numpy())
dn = d*(ev.touch_close.to_numpy()-ev.far_edge.to_numpy())
# modified race returning hit & inv separately
def race2(times):
    mkt = cl.get_market(None)
    tt = pd.DatetimeIndex(times).tz_convert("UTC")
    n=len(tt); H=np.full(n,np.nan); I=np.full(n,np.nan)
    ok=~tt.isna(); tn=cl.data.utc_ns(tt[ok]); i0=mkt.pos_at_or_after(tt[ok]); good=i0<len(mkt.o)
    idx=np.flatnonzero(ok)[good]; tn,i0=tn[good],i0[good]
    ref=mkt.o[i0]; dr=d[idx]; tgt=ref+dr*up[idx]; inv=ref-dr*dn[idx]
    ct=cl.data.utc_ns(pd.DatetimeIndex(b15.close_time)); cc=b15.close.to_numpy(float)
    k0=np.searchsorted(ct,tn,side="right"); kend=np.minimum(k0+orig.RACE_BARS,len(ct))-1
    until=pd.DatetimeIndex(cl.data.from_ns(ct[kend]))
    BIG=np.iinfo(np.int64).max
    inv_t=np.full(len(idx),BIG)
    for r in range(len(idx)):
        seg=cc[k0[r]:kend[r]+1]
        bad=np.flatnonzero(seg<inv[r]) if dr[r]==1 else np.flatnonzero(seg>inv[r])
        if len(bad): inv_t[r]=ct[k0[r]+bad[0]]
    upm=dr==1; hit_t=np.full(len(idx),BIG)
    for side,sel in (("above",upm),("below",~upm)):
        tc=cl.touch(pd.DatetimeIndex(cl.data.from_ns(tn[sel])),tgt[sel],side,until=until[sel])
        ht=cl.data.utc_ns(pd.DatetimeIndex(tc.hit_time)); h=tc.hit.to_numpy()
        v=np.full(sel.sum(),BIG); v[h]=ht[h]+60_000_000_000; hit_t[sel]=v
    H[idx]=((hit_t<inv_t)&(hit_t<BIG)).astype(float)
    I[idx]=((inv_t<=hit_t)&(inv_t<BIG)).astype(float)
    return H,I
Ho,Io=race2(t)
out={"t":t,"d":d,"Ho":Ho,"Io":Io}
for name,kw in (("base",{}),("tod30",{"tod_tol_min":30})):
    rt=cl.sample_times(t,5,30,seed=cl.rules.SEED,**kw)
    Hs=[];Is=[]
    for k in range(5):
        h,i=race2(pd.DatetimeIndex(rt[:,k]).tz_localize("UTC")); Hs.append(h); Is.append(i)
    out[name+"_H"]=np.nanmean(np.vstack(Hs),0); out[name+"_I"]=np.nanmean(np.vstack(Is),0)
pd.to_pickle(out,"races.pkl"); print("done")
