"""What is the complement? Geometry of fail vs pass events (stop placement vs the leg's true extreme)."""
from common import *
ev, an = load_events()
tr = pd.read_pickle(DD + "/trades_primary.pkl")
a = an.reset_index(drop=True); a["ev_id"] = np.arange(len(a))
t = tr.merge(a[["ev_id", "is_range_ext", "range_len", "n_sw", "n_sw_tagged", "fb_branch"]], on="ev_id")
t["grp"] = np.where(t.fb_branch, "fallback", np.where(t.gate, "fvg/swing pass", "fail"))
print(t.groupby("grp").agg(n=("adj", "size"), adj=("adj", "mean"), gross=("gross_R", "mean"),
      stop_rate=("reason", lambda r: (r == "stop").mean()), risk=("risk", "median"),
      range_ext=("is_range_ext", "mean"), range_len=("range_len", "median")).round(3))
# within the non-fallback universe: does 'extreme is the leg's true extreme' explain the gate?
nf = t[~t.fb_branch]
print(nf.groupby(["is_range_ext", "gate"]).agg(n=("adj", "size"), adj=("adj", "mean")).round(3))
# OLS adj ~ gate + is_range_ext + log(risk) + range_len, day-clustered SE
nf = nf.assign(g=nf.gate.astype(float), re=nf.is_range_ext.astype(float), lr=np.log(nf.risk))
X = np.column_stack([np.ones(len(nf)), nf.g, nf.re, nf.lr, nf.range_len]); y = nf.adj.to_numpy()
beta, *_ = np.linalg.lstsq(X, y, rcond=None); u = y - X @ beta
cid = pd.factorize(cl.trading_day(nf.decision_time))[0]
XtXi = np.linalg.inv(X.T @ X); S = np.zeros((5, 5))
for c in np.unique(cid):
    sc = X[cid == c].T @ u[cid == c]; S += np.outer(sc, sc)
se = np.sqrt(np.diag(XtXi @ S @ XtXi))
for nm, b_, s_ in zip(["const", "gate", "is_range_ext", "log_risk", "range_len"], beta, se):
    print(f"{nm:13s} {b_:+.4f}  se {s_:.4f}  t {b_/s_:+.2f}")
