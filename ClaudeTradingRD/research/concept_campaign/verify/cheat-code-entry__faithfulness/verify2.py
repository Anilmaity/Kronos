exec(open("verify.py").read().split("# 1. original")[0])
import json
ev0 = cce.detect(m1)
r0, tr0 = run("ORIG", ev0)
wt = ((tdir == -1) & (c < o)) | ((tdir == 1) & (c > o))
jw = np.flatnonzero(wt)
rc, trc = run("COUNTERFADE_samegeom", mk(b, jw, -tdir[jw]))
jn = np.flatnonzero((c != o) & (tdir == 0))
rn, trn = run("NOTREND_FADECANDLE", mk(b, jn, np.where(c[jn] > o[jn], -1, 1)))
# stratify by risk/ATR96 using common edges from ORIG
atr = pd.Series(rngs, index=pd.DatetimeIndex(b["close_time"]).tz_convert("UTC"))
def strat(tr, edges):
    a = atr.reindex(pd.DatetimeIndex(tr["decision_time"])).to_numpy()
    x = tr["risk"].to_numpy()/a
    q = np.digitize(x, edges)
    t = tr.assign(q=q, d5=tr["net_R_5050"]-tr["ctrl_mean_R_5050"])
    return t.groupby("q").agg(n=("dd","size"), dd=("dd","mean"), d5=("d5","mean")).round(3)
a0 = atr.reindex(pd.DatetimeIndex(tr0["decision_time"])).to_numpy()
edges = np.nanquantile(tr0["risk"].to_numpy()/a0, [.2,.4,.6,.8])
print("edges", edges)
for nm, t in (("ORIG",tr0),("COUNTERFADE",trc),("NOTREND",trn)):
    print(nm); print(strat(t, edges))
# 5m timeframe
b5 = bc.bars(m1, "5min"); legs5 = bc.displacement_legs(b5); td5, _, _ = bc.trend_state(b5, legs5)
o5,c5 = b5["open"].to_numpy(float), b5["close"].to_numpy(float)
j5 = np.flatnonzero(((td5 == -1) & (c5 > o5)) | ((td5 == 1) & (c5 < o5)))
run("TF5m_hold50", mk(b5, j5, td5[j5]), hold="50min")
run("TF5m_hold150", mk(b5, j5, td5[j5]), hold="150min")
