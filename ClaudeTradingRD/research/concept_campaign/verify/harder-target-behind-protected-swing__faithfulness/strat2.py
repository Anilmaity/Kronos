import sys, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ev = pd.read_pickle(sys.argv[1]+".pkl")
ev["day"] = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York").date
ev["ym"] = pd.DatetimeIndex(ev.decision_time).strftime("%Y%m")
ev["rd"] = ev.dist/ev.price
def strat(e, col, keys):
    t = e.groupby(keys+[col]).obs.agg(["mean","count"]).unstack()
    ok = t["count"].notna().all(1)
    w = t["count"][True][ok]; diff = (t["mean"][True]-t["mean"][False])[ok]
    return (diff*w).sum()/w.sum()
def prep(e):
    e = e.copy()
    e["nb"] = pd.qcut(e.null.rank(method="first"), 20, labels=False)
    e["rb"] = pd.qcut(e.rd.rank(method="first"), 10, labels=False)
    e["ab"] = pd.qcut(e.dist.rank(method="first"), 10, labels=False)
    return e
days = np.array(sorted(ev.day.unique())); grp = ev.groupby("day").indices; rng=np.random.default_rng(2)
def run(name, sub, keys):
    f = lambda e: strat(prep(sub(e)), "guarded", keys)
    r=[f(ev.iloc[np.concatenate([grp[d] for d in rng.choice(days,len(days))])]) for _ in range(300)]
    print(f"{name:60s} {f(ev):+.4f} CI {np.round(np.percentile(r,[2.5,97.5]),4)}")
A = lambda e: e; B = lambda e: e[e.behind_any]
run("all: strata null-rate bins", A, ["nb"])
run("all: strata rel-dist x month", A, ["rb","ym"])
run("all: strata same day x side x rel-dist decile", A, ["day","side","rb"])
run("behind-any: strata null-rate bins", B, ["nb"])
run("behind-any: strata rel-dist x month", B, ["rb","ym"])
run("behind-any: strata same day x side x rel-dist decile", B, ["day","side","rb"])
