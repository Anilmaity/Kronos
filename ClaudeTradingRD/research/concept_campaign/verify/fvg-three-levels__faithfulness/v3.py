import sys, importlib.util, numpy as np, pandas as pd
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a')
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03a/fvg-three-levels.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig); cl=orig.cl
ev=pd.read_pickle("ev.pkl"); b15=cl.bars("15min")
t=pd.DatetimeIndex(ev.decision_time); d=ev.direction.to_numpy()
up=d*(ev.leg_extreme-ev.touch_close).to_numpy(); dn=d*(ev.touch_close-ev.far_edge).to_numpy()
rt=cl.sample_times(t,5,30,seed=cl.rules.SEED,tod_tol_min=30)
day=(t.tz_convert("America/New_York")+pd.Timedelta(hours=6)).normalize(); codes,u=pd.factorize(day)
rng=np.random.default_rng(2)
def ci(x):
    m=~np.isnan(x); s=np.bincount(codes[m],weights=x[m],minlength=len(u)); n=np.bincount(codes[m],minlength=len(u))
    bs=[(w*s).sum()/(w*n).sum() for w in (np.bincount(rng.integers(0,len(u),len(u)),minlength=len(u)) for _ in range(500))]
    return np.nanmean(x)*100, np.percentile(bs,[2.5,97.5])*100
for rb in (8,32):
    orig.RACE_BARS=rb
    o=orig.race(t,up,dn,d,b15=b15)
    nl=np.nanmean(np.vstack([orig.race(pd.DatetimeIndex(rt[:,k]).tz_localize("UTC"),up,dn,d,b15=b15) for k in range(5)]),0)
    print("race",rb,"tod-null", ci(o-nl))
# depth: how deep the touch M1 bar went relative to gap (near edge->far edge)
gap=d*(ev.near_edge-ev.far_edge).to_numpy()
depth=d*(ev.near_edge-ev.touch_close).to_numpy()/gap
print(pd.Series(depth).describe())
