# Re-run of the original pipeline, importing its functions, WITHOUT write_result.
import sys, importlib.util
p="/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a/harder-target-behind-protected-swing.py"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
spec=importlib.util.spec_from_file_location("orig", p); orig=importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
cl=orig.cl; np=orig.np; pd=orig.pd
ev = orig.detect(cl.load_m1())
print(len(ev), cl.frame_fingerprint(ev) if hasattr(cl,'frame_fingerprint') else '')
m1=cl.load_m1(); t=pd.DatetimeIndex(ev.decision_time); hb=orig.bars_left_in_day(t,m1)
side=ev.side.to_numpy(); lvl=ev.level.to_numpy(float); dist=ev.dist.to_numpy(float)
def hits(times, levels, side=side, hb=hb):
    h=np.zeros(len(levels)); tt=pd.DatetimeIndex(times); ok=~pd.isna(tt)
    for s_,nm in ((1,"above"),(-1,"below")):
        m=(side==s_)&ok
        if m.any(): h[m]=cl.touch(tt[m],levels[m],nm,horizon_bars=hb[m])["hit"].to_numpy()
    h[~ok]=np.nan; return h
obs=hits(t,lvl)
rt=cl.sample_times(t,5,30,seed=cl.rules.SEED,tod_tol_min=0)
nulls=[]
for k in range(5):
    tk=pd.DatetimeIndex(rt[:,k]).tz_localize("UTC"); pk=orig.price_at(tk,m1); nulls.append(hits(tk,pk+side*dist))
nulls=np.array(nulls)
print("obs",obs.mean(),"null",np.nanmean(nulls),"diff",obs.mean()-np.nanmean(nulls))
ev.assign(obs=obs, hb=hb, **{f"n{k}":nulls[k] for k in range(5)}).to_pickle("ev_orig.pkl")
