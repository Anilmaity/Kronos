import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1(); ev = pd.read_parquet("ev_mine.parquet")
t = m1.index.as_unit("ns").asi8; o=m1.open.to_numpy(); h=m1.high.to_numpy(); l=m1.low.to_numpy(); c=m1.close.to_numpy()
dec = pd.DatetimeIndex(ev.decision_time).as_unit("ns").asi8
print("dec minute%5:", pd.Series((dec//60_000_000_000)%5).value_counts().to_dict())
i0 = np.searchsorted(t, dec, "left"); iend = np.searchsorted(t, dec + 50*60_000_000_000, "left")
R = np.full(len(ev), np.nan); d = ev.direction.to_numpy(); sp = ev.stop_px.to_numpy()
for j in range(len(ev)):
    a, b = i0[j], iend[j]
    if a >= len(t) or b <= a: continue
    e = o[a]; risk = (e - sp[j]) * d[j]
    if risk <= 0: continue
    tp = e + d[j]*2*risk; r = None
    for k in range(a, b):
        if d[j] == 1:
            if l[k] <= sp[j]: r = (min(o[k], sp[j]) - e)/risk; break
            if h[k] >= tp: r = 2.0; break
        else:
            if h[k] >= sp[j]: r = (e - max(o[k], sp[j]))/risk; break
            if l[k] <= tp: r = 2.0; break
    if r is None: r = (c[b-1] - e)*d[j]/risk
    R[j] = r - 0.04
ev["R"] = R; ev = ev[~np.isnan(R)]; ev.to_parquet("ev_R.parquet")
day = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York") + pd.Timedelta("6h")
ev["day"] = day.date
rng = np.random.default_rng(1)
def test(mask, name, sub=None):
    e = ev if sub is None else ev[sub]
    m = e[mask] if isinstance(mask,str) else e[mask[e.index] if False else mask]
    gm = e[mask].R.mean(); cm_ = e[~e[mask]].R.mean() if isinstance(mask,str) else None
    # day-block bootstrap
    days = e.day.unique(); gd = e.groupby("day")
    s = gd.apply(lambda x: pd.Series({"gs": x.R[x[mask]].sum(), "gn": x[mask].sum(), "cs": x.R[~x[mask]].sum(), "cn": (~x[mask]).sum()}))
    S = s.to_numpy(); bs=[]
    for _ in range(1000):
        k = S[rng.integers(0, len(S), len(S))].sum(0); bs.append(k[0]/k[1]-k[2]/k[3])
    tot = S.sum(0); print(f"{name:12s} n_g={int(tot[1])} g={tot[0]/tot[1]:+.4f} c={tot[2]/tot[3]:+.4f} diff={tot[0]/tot[1]-tot[2]/tot[3]:+.4f} CI[{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]")
ev["H1"] = pd.DatetimeIndex(ev.decision_time) < pd.Timestamp("2021-01-01", tz="UTC")
for col in ["mine20", "late10", "late30", "late40", "exp_any", "late", "early_exp"]:
    test(col, col)
e_exp = ev[ev.exp_any]
ev_backup = ev; ev = e_exp; test("late", "late|exp"); ev = ev_backup
for hlf in (True, False):
    ev = ev_backup[ev_backup.H1 == hlf]; test("mine20", "H1" if hlf else "H2")
ev = ev_backup
