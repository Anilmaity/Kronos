import sys, os, numpy as np, pandas as pd
key = sys.argv[1]
ev = pd.read_pickle(key + ".pkl")
ev["day"] = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York").date
ev["yr"] = pd.DatetimeIndex(ev.decision_time).year
ev["d"] = ev.obs - ev.null
days = np.array(sorted(ev.day.unique())); rng = np.random.default_rng(0)
di = {d:i for i,d in enumerate(days)}; ev["di"] = ev.day.map(di)
def boot(stat, B=1000, L=5):
    # stationary-ish block bootstrap over days (block len L)
    nd = len(days); res=[]
    grp = ev.groupby("di").indices
    for _ in range(B):
        idx=[]; 
        while len(idx)<nd:
            s=rng.integers(nd); idx.extend(range(s, min(s+L, nd)))
        rows = np.concatenate([grp[i] for i in idx[:nd] if i in grp])
        res.append(stat(ev.iloc[rows]))
    return np.percentile(res,[2.5,97.5])
def show(name, stat):
    print(f"{name:55s} {stat(ev):+.4f}  CI {np.round(boot(stat),4)}")
G = lambda e: e[e.guarded]; U = lambda e: e[~e.guarded]
print("n guarded", ev.guarded.sum(), "unguarded", (~ev.guarded).sum())
print("guarded obs/null", G(ev).obs.mean(), G(ev).null.mean())
print("unguarded obs/null", U(ev).obs.mean(), U(ev).null.mean())
show("guarded obs-null", lambda e: G(e).d.mean())
show("unguarded obs-null", lambda e: U(e).d.mean())
show("DiD guarded-unguarded (null adj)", lambda e: G(e).d.mean()-U(e).d.mean())
# behind ANY untaken swing (not protected) vs not
B_ = lambda e: e[e.behind_any & ~e.guarded]
show("behind non-protected swing only: obs-null", lambda e: B_(e).d.mean())
show("DiD guarded - behind-nonprotected-only", lambda e: G(e).d.mean()-B_(e).d.mean())
# within behind_any, protected vs not, distance-bin matched
ba = ev[ev.behind_any].copy()
ba["db"] = pd.qcut(ba.dist/ba.price, 10, labels=False, duplicates="drop")
t = ba.groupby(["db","guarded"]).obs.mean().unstack(); print(t.round(3))
print("years guarded obs-null:"); print(G(ev).groupby("yr").d.agg(["mean","count"]).round(4).T)
print("side guarded obs-null:"); print(G(ev).groupby("side").d.agg(["mean","count"]).round(4))
print("rank guarded:"); print(G(ev).groupby(G(ev)["rank"].clip(upper=5)).d.agg(["mean","count"]).round(4))
