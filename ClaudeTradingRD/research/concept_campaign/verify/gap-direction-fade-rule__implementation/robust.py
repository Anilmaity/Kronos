import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
a = pd.read_csv("events_a.csv", parse_dates=["t"])
mkt = cl.get_market(); tn = mkt.t
t = pd.DatetimeIndex(a.t).tz_convert("UTC") if pd.DatetimeIndex(a.t).tz else pd.DatetimeIndex(a.t).tz_localize("UTC")
up = a.up.to_numpy(); px = a.px.to_numpy(); pc = a.pc.to_numpy(); i0 = a.i0.to_numpy()
dist = pc - px
def hit(i, lvl, u, H, skip=0):
    o = np.zeros(len(i), bool)
    for k in range(len(i)):
        s = slice(i[k]+skip, min(i[k]+H, len(tn)))
        o[k] = (mkt.l[s] <= lvl[k]).any() if u[k] else (mkt.h[s] >= lvl[k]).any()
    return o
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=0)
P = []
for k in range(5):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
    p = np.full(len(t), -1); p[ok] = mkt.pos_at_or_after(tk[ok]); P.append(p)
def run(H, cushion=0.0, skip=0, label=""):
    sgn = np.where(up, -1, 1)           # direction toward fill
    lvl = pc + sgn*cushion
    ob = hit(i0, lvl, up, H, skip)
    nr = []
    for p in P:
        ok = p >= 0; r = np.full(len(t), np.nan)
        r[ok] = hit(p[ok], mkt.o[p[ok]] + dist[ok] + sgn[ok]*cushion, up[ok], H, skip); nr.append(r)
    nr = np.nanmean(nr, 0); d = ob - nr
    rng = np.random.default_rng(1); b = [rng.choice(d, len(d)).mean() for _ in range(1000)]
    h1 = t < pd.Timestamp("2021-01-01", tz="UTC")
    print(f"{label:28s} obs={ob.mean():.3f} null={nr.mean():.3f} diff={d.mean():+.4f} CI=[{np.percentile(b,2.5):+.4f},{np.percentile(b,97.5):+.4f}] up={d[up].mean():+.4f} dn={d[~up].mean():+.4f} H1={d[h1].mean():+.4f} H2={d[~h1].mean():+.4f}")
run(60, label="baseline tol0 H60")
run(5, label="H5")
run(60, skip=5, label="H60 skip first 5 bars")
run(60, skip=10, label="H60 skip first 10 bars")
for c in (0.1, 0.3, 0.5):
    run(60, cushion=c, label=f"H60 cushion ${c}")
# gap >= $1 only
