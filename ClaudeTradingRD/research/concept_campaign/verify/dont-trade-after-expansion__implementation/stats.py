import numpy as np, pandas as pd
ev = pd.read_parquet("ev_R.parquet")
ev["day"] = (pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York") + pd.Timedelta("6h")).date
ev["H1"] = pd.DatetimeIndex(ev.decision_time) < pd.Timestamp("2021-01-01", tz="UTC")
rng = np.random.default_rng(1)
def test(e, col, name):
    m = e[col].to_numpy(bool); R = e.R.to_numpy()
    df = pd.DataFrame({"day": e.day.to_numpy(), "gs": np.where(m, R, 0), "gn": m*1, "cs": np.where(~m, R, 0), "cn": (~m)*1})
    S = df.groupby("day").sum().to_numpy(); tot = S.sum(0)
    bs = [ (k:=S[rng.integers(0,len(S),len(S))].sum(0))[0]/k[1]-k[2]/k[3] for _ in range(1000)]
    print(f"{name:10s} n_g={int(tot[1]):6d} g={tot[0]/tot[1]:+.4f} c={tot[2]/tot[3]:+.4f} diff={tot[0]/tot[1]-tot[2]/tot[3]:+.4f} CI[{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]")
print("n", len(ev))
for col in ["mine20","late10","late30","late40","exp_any","late","early_exp"]: test(ev, col, col)
test(ev[ev.exp_any], "late", "late|exp")
test(ev[~ev.exp_any], "late", "late|noexp")
test(ev[ev.H1], "mine20", "H1"); test(ev[~ev.H1], "mine20", "H2")
