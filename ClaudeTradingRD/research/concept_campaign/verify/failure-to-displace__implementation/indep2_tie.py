exec(open("indep_tie.py").read().split('t0=ev.dt.values')[0])
def run(buf_bp=0.0, buf_abs=0.0, seed=7):
    e=ev.copy()
    t0=e.dt.values.astype("datetime64[ns]").astype(np.int64)
    i0=np.searchsorted(T,t0); ok=i0<N
    entry=O[np.minimum(i0,N-1)]; sg=e.dir.values
    stop=e.stop.values - sg*(buf_bp*1e-4*e.close.values+buf_abs)
    risk=sg*(entry-stop); td=sg*(e.tgt.values-entry); ok&=(risk>0)&(td>0)
    i0,t0,entry,sg,risk,td,stop,tg=i0[ok],t0[ok],entry[ok],sg[ok],risk[ok],td[ok],stop[ok],e.tgt.values[ok]
    px,_=resolve(i0,t0,sg,stop,tg); R=sg*(px-entry)/risk
    rng=np.random.default_rng(seed); cR=np.zeros((len(R),5))
    for k in range(5):
        lo_=np.searchsorted(grid,t0-30*86400*10**9); hi_=np.searchsorted(grid,t0+30*86400*10**9)
        ct=np.clip(lo_+(rng.random(len(R))*(hi_-lo_)).astype(np.int64),0,len(grid)-1)
        ctime=grid[ct]; ci_=np.searchsorted(T,ctime); ce=O[ci_]
        cp,_=resolve(ci_,ctime,sg,ce-sg*risk,ce+sg*td); cR[:,k]=sg*(cp-ce)/risk
    return t0,R,cR,risk
def boot(t0,d,nb=1000):
    day=pd.DatetimeIndex(pd.to_datetime(t0,utc=True)).tz_convert("America/New_York")
    dc=pd.factorize((day+pd.Timedelta("6h")).date)[0]; nd=dc.max()+1
    s=np.bincount(dc,d,nd); cnt=np.bincount(dc,None,nd); r=np.random.default_rng(1)
    bs=[(w*s).sum()/(w*cnt).sum() for w in (np.bincount(r.integers(0,nd,nd),minlength=nd) for _ in range(nb))]
    yr=pd.DatetimeIndex(pd.to_datetime(t0,utc=True)).year
    return f"n={len(d)} diff={d.mean():+.4f} CI[{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}] H1={d[yr<2021].mean():+.4f} H2={d[yr>=2021].mean():+.4f}"
grid=T[(T//60_000_000_000)%15==0]
for kw in [dict(),dict(buf_abs=0.10),dict(buf_abs=0.30),dict(buf_bp=1),dict(buf_bp=2)]:
    t0,R,cR,risk=run(**kw)
    print(kw,"raw",boot(t0,R-cR.mean(1)))
    if False:
        for cap in [5,10,20,50]:
            print("  winsor",cap,boot(t0,np.clip(R,-cap,cap)-np.clip(cR,-cap,cap).mean(1)))
