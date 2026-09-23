import sys, numpy as np, pandas as pd
ev = pd.read_pickle(sys.argv[1]+".pkl")
ev["day"] = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York").date
ev["rd"] = ev.dist/ev.price
def strat(e, col, nb=50):
    e = e.copy(); e["b"] = pd.qcut(e.rd.rank(method="first"), nb, labels=False)
    t = e.groupby(["b",col]).obs.agg(["mean","count"]).unstack()
    ok = t["count"].notna().all(1)
    w = t["count"][True][ok]; diff = (t["mean"][True]-t["mean"][False])[ok]
    return (diff*w).sum()/w.sum()
days = np.array(sorted(ev.day.unique())); grp = ev.groupby("day").indices; rng=np.random.default_rng(1)
def boot(f, sub, B=400):
    r=[]
    for _ in range(B):
        dd = rng.choice(days, len(days)); rows = np.concatenate([grp[d] for d in dd])
        e = ev.iloc[rows]; r.append(f(sub(e)))
    return np.round(np.percentile(r,[2.5,97.5]),4)
f = lambda e: strat(e, "guarded")
print("all candidates, guarded vs not, 50 dist bins:", round(f(ev),4), boot(f, lambda e: e))
ba = lambda e: e[e.behind_any]
print("behind-any, protected-guarded vs non-protected, 50 bins:", round(f(ba(ev)),4), boot(f, ba))
g = ev[ev.guarded]
g["yr"]=pd.DatetimeIndex(g.decision_time).year
print((g.groupby("yr").obs.mean()-g.groupby("yr").null.mean()).round(4).to_dict())
