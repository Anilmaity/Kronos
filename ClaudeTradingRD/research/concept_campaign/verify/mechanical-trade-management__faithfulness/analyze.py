import numpy as np, pandas as pd
df = pd.read_parquet(__file__.replace("analyze.py", "paired.parquet"))
df["t"] = pd.to_datetime(df.t, utc=True)
def daybs(x, days, B=2000, seed=1):
    # stationary-ish day-block: resample whole trading days
    u, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, x); c = np.bincount(inv)
    rng = np.random.default_rng(seed); m = []
    for _ in range(B):
        i = rng.integers(0, len(u), len(u)); m.append(s[i].sum()/c[i].sum())
    return np.percentile(m, [2.5, 97.5])
for tie in ("stop", "half"):
    d = df[df.tie == tie]
    aff = d[d.tag & (d.Rf != d.Rb)]
    print(f"\n== tie={tie}  all trades n={len(d)}  mean Rf={d.Rf.mean():+.4f} Rb={d.Rb.mean():+.4f}")
    print(f" tagged={d.tag.sum()} affected={len(aff)} retest_hits_stop={d.retest_hits_stop.sum()} retest_with_tgt={d.retest_with_tgt.sum()}")
    days = (aff.t.dt.tz_convert('America/New_York') + pd.Timedelta('6h')).dt.date.astype(str).to_numpy()
    lo, hi = daybs(aff.d.to_numpy(), days)
    print(f" affected mean d={aff.d.mean():+.4f} CI [{lo:+.4f},{hi:+.4f}]  (per all trades {d.d.mean():+.5f})")
    for lab, m in [("H1", aff.t < "2021-01-01"), ("H2", aff.t >= "2021-01-01")]:
        print(f"  {lab} n={m.sum()} d={aff.d[m].mean():+.4f}")
    edges = pd.to_datetime(["2016-01-01", "2018-08-22 11:01", "2021-04-12 08:43", "2023-12-02 06:25", "2027-01-01"], utc=True, format="mixed")
    for b in range(4):
        m = (aff.t >= edges[b]) & (aff.t < edges[b+1]); x = aff[m]
        dd = (x.t.dt.tz_convert('America/New_York') + pd.Timedelta('6h')).dt.date.astype(str).to_numpy()
        l, h = daybs(x.d.to_numpy(), dd, B=1000)
        print(f"  B{b+1} n={m.sum()} d={x.d.mean():+.4f} [{l:+.3f},{h:+.3f}]")
    print("  by year:", aff.groupby(aff.t.dt.year).d.agg(['count','mean']).round(3).to_dict('index'))
