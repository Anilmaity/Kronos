import numpy as np, pandas as pd, os
D = os.path.dirname(os.path.abspath(__file__))
df = pd.read_parquet(os.path.join(D, "per_event.parquet")).dropna(subset=["obs", "null"])
df["e"] = df.obs - df.null
df["day"] = pd.DatetimeIndex(df.decision_time).tz_convert("America/New_York").floor("D")
df["absmove"] = df.move3.abs(); df["absdist"] = df.dist_atr.abs()
def strat_gap(d, keys, q=5):
    d = d.copy()
    for k in keys:
        edges = np.unique(np.quantile(d.loc[d.kind == "FVG", k], np.linspace(0, 1, q + 1)))
        d[k + "_b"] = np.clip(np.searchsorted(edges, d[k], side="right") - 1, 0, len(edges) - 2)
    bk = [k + "_b" for k in keys]
    g = d.groupby(bk + ["kind"])["e"].agg(["mean", "size"]).unstack("kind")
    g = g.dropna()
    g = g[g[("size", "PLAC")] >= 30]
    w = g[("size", "FVG")] / g[("size", "FVG")].sum()
    fv = (w * g[("mean", "FVG")]).sum(); pl = (w * g[("mean", "PLAC")]).sum()
    cov = g[("size", "FVG")].sum() / (d.kind == "FVG").sum()
    return fv, pl, fv - pl, cov
print("raw FVG-e", df[df.kind=="FVG"].e.mean(), "PLAC-e", df[df.kind=="PLAC"].e.mean())
for keys in (["absdist"], ["absdist", "rng_i"], ["absdist", "absmove"], ["absdist", "rng_i", "absmove"], ["absdist", "rng_i", "rng_mid"]):
    print(keys, ["%.4f" % x for x in strat_gap(df, keys)])
# day-block bootstrap of the fully matched gap
rng = np.random.default_rng(0)
days = df.day.unique(); idx = {d: i for i, d in enumerate(days)}
df["di"] = df.day.map(idx)
keys = ["absdist", "rng_i", "absmove"]
base = strat_gap(df, keys)[2]
# block bootstrap by 20-day blocks
blk = df.di // 20; ub = blk.unique(); groups = {b: g for b, g in df.groupby(blk)}
bs = []
for _ in range(300):
    pick = rng.choice(ub, len(ub))
    bs.append(strat_gap(pd.concat([groups[p] for p in pick]), keys)[2])
print("matched FVG-minus-placebo gap", round(base, 4), "CI", np.percentile(bs, [2.5, 97.5]).round(4))
# per-block and halves of matched gap
t = pd.DatetimeIndex(df.decision_time)
for name, m in (("H1", t < "2021-01-01"), ("H2", t >= "2021-01-01")):
    print(name, ["%.4f" % x for x in strat_gap(df[m], keys)])
qs = np.quantile(t.asi8, [0, .25, .5, .75, 1])
for i in range(4):
    m = (t.asi8 >= qs[i]) & (t.asi8 <= qs[i+1])
    print("B%d" % (i+1), ["%.4f" % x for x in strat_gap(df[m], keys)])
