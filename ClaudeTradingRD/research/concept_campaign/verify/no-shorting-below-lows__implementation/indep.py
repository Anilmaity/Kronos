"""Independent re-implementation: own 15m bars, own swings, own CISD (series_open, 2/2, mw3),
own trading-day running low/high from raw M1 strictly before the signal bar opened."""
import sys; sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import numpy as np, pandas as pd, concept_lab as cl
m1=cl.load_m1()
# 15m bars, left-labelled, only bars with data
g=m1.resample("15min",label="left",closed="left")
b=pd.DataFrame({"open":g["open"].first(),"high":g["high"].max(),"low":g["low"].min(),"close":g["close"].last()}).dropna()
o,h,l,c=(b[k].to_numpy(float) for k in ["open","high","low","close"])
n=len(b); L=R=2
sh=np.zeros(n,bool); sl=np.zeros(n,bool)
for i in range(L,n-R):
    win_h=h[i-L:i+R+1]; win_l=l[i-L:i+R+1]
    sh[i]= h[i]==win_h.max() and (np.sum(win_h==h[i])==1 or True) and h[i]>max(h[i-L:i].max(),h[i+1:i+R+1].max()) if True else False
    sl[i]= l[i]<min(l[i-L:i].min(),l[i+1:i+R+1].min())
rows=[]
for bull,flags in ((True,sl),(False,sh)):
    q = (c<o) if bull else (c>o)
    for p in np.flatnonzero(flags):
        e=p
        while e>0 and not q[e]:
            e-=1
            if p-e>2: e=-1; break
        if e<0 or not q[e]: continue
        s=e
        while s>0 and q[s-1] and (e-s+1)<10: s-=1
        lvl=o[s]
        beg=max(e,p+R)+1
        for j in range(beg,min(n,beg+3)):
            if (c[j]>lvl) if bull else (c[j]<lvl):
                rows.append((j, 1 if bull else -1, c[j], l[p] if bull else h[p])); break
ev=pd.DataFrame(rows,columns=["j","direction","px","stop_px"])
st=b.index[ev.j]
ev["bar_open"]=st
ev["decision_time"]=st+pd.Timedelta(minutes=15)
# trading day: NY time +6h -> date (18:00 NY roll)
def tday(ix): return (ix.tz_convert("America/New_York")+pd.Timedelta(hours=6)).normalize().tz_localize(None)
mt=tday(m1.index)
mdf=pd.DataFrame({"td":mt,"hi":m1["high"].to_numpy(),"lo":m1["low"].to_numpy()},index=m1.index)
mdf["rh"]=mdf.groupby("td")["hi"].cummax(); mdf["rl"]=mdf.groupby("td")["lo"].cummin()
# last M1 bar that CLOSED by bar_open => M1 start <= bar_open-1min
pos=np.searchsorted(m1.index.asi8, (st-pd.Timedelta(minutes=1)).asi8, side="right")-1
ok=(pos>=0)
tdb=tday(st)
same=ok & (mt[np.clip(pos,0,None)]==tdb)
rh=np.where(same,mdf["rh"].to_numpy()[np.clip(pos,0,None)],np.nan)
rl=np.where(same,mdf["rl"].to_numpy()[np.clip(pos,0,None)],np.nan)
d=ev.direction.to_numpy(); px=ev.px.to_numpy()
ev["chase_day"]=np.where(np.isfinite(rh), np.where(d==-1,px<rl,px>rh), False)
# match original: require a real previous day (PD levels) -> use harness prior_hilo only to mirror the row filter
pdh=cl.prior_hilo(pd.DatetimeIndex(ev.decision_time),"1D",m1=m1,min_coverage=0.5)
ev=ev[np.isfinite(pdh["high"].to_numpy())]
ev=ev.assign(available_at=ev.decision_time, rr=2.0)
ev=ev.sort_values(["decision_time","direction"]).drop_duplicates(["decision_time","direction"]).reset_index(drop=True)
ev=ev[["decision_time","available_at","direction","stop_px","rr","chase_day"]]
ev.to_pickle("indep_ev.pkl")
print("events",len(ev),"gate rate",ev.chase_day.mean())
o_=pd.read_pickle("orig_ev.pkl")
k=["decision_time","direction"]
mg=o_.merge(ev,on=k,how="outer",suffixes=("_o","_i"),indicator=True)
print(mg._merge.value_counts())
both=mg[mg._merge=="both"]
print("mask agree",(both.chase_day_o==both.chase_day_i).mean(), "stop agree",np.isclose(both.stop_px_o,both.stop_px_i).mean())
res=cl.gate_test(ev,"chase_day",mask_available_at="decision_time",max_hold="150min",claim="-",keep_trades=True)
for kk in ["n","diff","ci_lo","ci_hi","p","verdict","verdict_detail"]: print(kk,res.get(kk))
print(res["halves"]["H1"]["diff"],res["halves"]["H2"]["diff"],res["ties"]["verdict_stop_first"],res["gated_vs_own_control"])
tr=res["_trades"]; print(tr.columns.tolist()[:30])
tr.to_pickle("indep_trades.pkl")
