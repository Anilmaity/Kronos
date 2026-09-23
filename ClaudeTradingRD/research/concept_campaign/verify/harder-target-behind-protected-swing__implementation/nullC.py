import sys; sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd, concept_lab as cl
NY="America/New_York"; rng=np.random.default_rng(11)
ev=pd.read_pickle("ev_indep_atr.pkl"); ev=ev[ev.guarded].reset_index(drop=True)
m1=cl.load_m1()
g=m1.groupby(m1.index.floor("15min")); b=pd.DataFrame({"high":g.high.max(),"low":g.low.min(),"close":g.close.last()})
b["ct"]=b.index+pd.Timedelta("15min"); ctny=b.ct.dt.tz_convert(NY)
dec=np.flatnonzero((ctny.dt.hour==9)&(ctny.dt.minute==30))
H,L,C=b.high.to_numpy(),b.low.to_numpy(),b.close.to_numpy()
mt=m1.index.asi8; mh,ml=m1.high.to_numpy(),m1.low.to_numpy()
# per decision-day info
D=pd.DataFrame({"j":dec,"t":b.ct.iloc[dec].to_numpy()})
D["t"]=pd.to_datetime(D.t,utc=True)
fh=[];fl=[]
for t in D.t:
    tend=(t.tz_convert(NY).normalize()+pd.Timedelta(hours=17)).tz_convert("UTC")
    i0=np.searchsorted(mt,t.value);i1=np.searchsorted(mt,tend.value)
    fh.append(mh[i0:i1].max() if i1>i0 else np.nan); fl.append(ml[i0:i1].min() if i1>i0 else np.nan)
D["fh"]=fh;D["fl"]=fl;D=D.dropna().reset_index(drop=True)
tns=D.t.astype("int64").to_numpy()
# prefix structures for range-min over last k bars: just slice
def draw(e, cond, k=5, tries=60):
    lo=np.searchsorted(tns,(e.t-pd.Timedelta("30D")).value); hi=np.searchsorted(tns,(e.t+pd.Timedelta("30D")).value,"right")
    cand=np.arange(lo,hi); cand=cand[tns[cand]!=e.t.value]
    rng.shuffle(cand); out=[]
    for r in cand[:tries] if cond else cand[:k]:
        j=D.j[r]; P=C[j]; lv=P+e.side*e.dist
        if cond:
            a=max(0,j-e.age)
            ok = (L[a:j+1].min()>=lv) if e.side<0 else (H[a:j+1].max()<=lv)
            if not ok: continue
        out.append((D.fl[r]<=lv) if e.side<0 else (D.fh[r]>=lv))
        if len(out)==k: break
    return np.mean(out) if out else np.nan, len(out)
resA=[draw(e,False) for e in ev.itertuples()]
resC=[draw(e,True) for e in ev.itertuples()]
ev["nA"]=[r[0] for r in resA]; ev["nC"]=[r[0] for r in resC]; ev["kC"]=[r[1] for r in resC]
ev.to_pickle("ev_nullC.pkl")
days=np.array(sorted(ev.day.unique())); gi={d:np.flatnonzero(ev.day.to_numpy()==d) for d in days}
def ci(col):
    f=ev.dropna(subset=[col]); st=lambda x: x.hit.mean()-x[col].mean()
    dd=f.day.to_numpy(); gi2={d:np.flatnonzero(dd==d) for d in np.unique(dd)}; ks=np.array(list(gi2))
    bs=[st(f.iloc[np.concatenate([gi2[x] for x in rng.choice(ks,len(ks))])]) for _ in range(1000)]
    h1=f[f.t<"2021-01-01"];h2=f[f.t>="2021-01-01"]
    return len(f), f.hit.mean(), f[col].mean(), st(f), np.percentile(bs,[2.5,97.5]), st(h1), st(h2)
print("A random-level null (own impl):",ci("nA"))
print("C untaken-matched null      :",ci("nC"), "rows with >=1 accepted draw", ev.kC.gt(0).mean(), "mean draws", ev.kC.mean())
