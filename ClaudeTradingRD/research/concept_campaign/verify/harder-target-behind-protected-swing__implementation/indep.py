# Independent implementation from the concept YAML (own bars, swings, candidates, outcomes).
# Emits ALL untaken swing candidates at 09:30 NY with a 'guarded' flag, so guarded can be
# compared against unguarded targets (the YAML's own 'measurable'), not only a random-level null.
import sys; sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd, concept_lab as cl
m1 = cl.load_m1()                              # data only
NY="America/New_York"
# own 15m bars: bar start = floor(M1 start, 15min); close time = start+15m; empty bars dropped
g = m1.groupby(m1.index.floor("15min"))
b = pd.DataFrame({"high":g.high.max(),"low":g.low.min(),"close":g.close.last()})
b["ct"] = b.index + pd.Timedelta("15min")
H,L,C = b.high.to_numpy(), b.low.to_numpy(), b.close.to_numpy(); n=len(b)
sh=np.zeros(n,bool); sl=np.zeros(n,bool)
for i in range(2,n-2):
    sh[i] = H[i]>H[i-1] and H[i]>H[i-2] and H[i]>=H[i+1] and H[i]>=H[i+2]
    sl[i] = L[i]<L[i-1] and L[i]<L[i-2] and L[i]<=L[i+1] and L[i]<=L[i+2]
def protected(mask, px, low):
    idx=np.flatnonzero(mask); p=np.zeros(n,bool)
    for a in range(2,len(idx)):
        v=px[idx[a]]; pr=px[idx[a-2:a]]
        p[idx[a]] = (v<pr).all() if low else (v>pr).all()
    return p
pl, ph = protected(sl,L,True), protected(sh,H,False)
ctny = b.ct.dt.tz_convert(NY)
dec = np.flatnonzero((ctny.dt.hour==9)&(ctny.dt.minute==30))
# M1 arrays for outcomes
mt = m1.index; mny = mt.tz_convert(NY)
mh, ml, mc = m1.high.to_numpy(), m1.low.to_numpy(), m1.close.to_numpy()
mt_ns = mt.asi8
rows=[]
for j in dec:
    t = b.ct.iloc[j]; P=C[j]
    # day end: 17:00 NY same NY calendar date
    tend = (t.tz_convert(NY).normalize()+pd.Timedelta(hours=17)).tz_convert("UTC")
    i0 = np.searchsorted(mt_ns, t.value, "left"); i1 = np.searchsorted(mt_ns, tend.value, "left")
    if i1<=i0: continue
    fut_hi, fut_lo = mh[i0:i1].max(), ml[i0:i1].min()
    a0=max(0,j-299)
    for low in (True, False):
        msk = sl if low else sh; px = L if low else H; prot = pl if low else ph
        cands=[c for c in np.flatnonzero(msk[a0:j+1])+a0 if c+2<=j]   # confirmed by bar j close
        keep=[]
        for c in cands:
            if low:
                if px[c]<P and (L[c+1:j+1]>=px[c]).all(): keep.append(c)
            else:
                if px[c]>P and (H[c+1:j+1]<=px[c]).all(): keep.append(c)
        if len(keep)<2: continue
        pk=[c for c in keep if prot[c]]
        for c in keep:
            lv=px[c]
            gd = any((px[q]>lv and px[q]<P) if low else (px[q]<lv and px[q]>P) for q in pk if q!=c)
            hit = (fut_lo<=lv) if low else (fut_hi>=lv)
            rows.append((t, -1 if low else 1, lv, abs(P-lv), P, gd, hit, j-c, i1-i0, len(keep)))
ev=pd.DataFrame(rows,columns=["t","side","level","dist","price","guarded","hit","age","nbars","nkeep"])
ev.to_pickle("ev_indep.pkl")
g=ev[ev.guarded]
print("all cands",len(ev),"guarded",len(g),"guarded hit",g.hit.mean(),"unguarded hit",ev[~ev.guarded].hit.mean())
