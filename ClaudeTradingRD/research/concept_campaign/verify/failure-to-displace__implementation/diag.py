import pandas as pd, numpy as np
tr=pd.read_pickle("trades_a.pkl")
tr["rr"]=(tr.direction*(tr.target-tr.entry))/tr.risk
tr["d"]=tr.net_R-tr.ctrl_mean_R
tr["yr"]=pd.DatetimeIndex(tr.decision_time).year
print(tr.risk.describe(percentiles=[.05,.1,.25,.5,.75,.9]))
print(tr.rr.describe(percentiles=[.05,.25,.5,.75,.9,.95,.99]))
for name,col,bins in [("risk$", "risk",[0,.1,.2,.3,.5,1,2,5,1e9]),("rr","rr",[0,.25,.5,1,2,3,5,10,1e9])]:
    g=tr.groupby(pd.cut(tr[col],bins))
    print(name); print(g.agg(n=("d","size"),real=("net_R","mean"),ctrl=("ctrl_mean_R","mean"),diff=("d","mean"),contrib=("d","sum")).assign(contrib=lambda x:x.contrib/len(tr)))
print(tr.groupby("yr").agg(n=("d","size"),diff=("d","mean"),medrisk=("risk","median")))
# trimmed
for q in [0.999,0.99]:
    lim=tr.d.abs().quantile(q); print(q, tr.d[tr.d.abs()<lim].mean())
print("win real",(tr.net_R>0).mean(),"ctrl win",tr.ctrl_win.mean())
print(tr.groupby("reason").agg(n=("d","size"),real=("gross_R","mean"),diff=("d","mean")))
print("sd",tr.gross_R.std(), tr.gross_R.min(), tr.gross_R.max())
print(tr.nsmallest(10,"gross_R")[["decision_time","entry","stop","target","risk","exit_px","reason","gross_R","ctrl_mean_R"]])
print(tr.nlargest(10,"d")[["decision_time","entry","stop","target","risk","exit_px","reason","gross_R","ctrl_mean_R"]])
