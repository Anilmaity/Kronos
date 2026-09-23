"""Geometry-matched test: within the book 'fade every 15m candle, stop at its extreme, 2R, 150m',
does the concept's condition (trend alive and the candle opposes it => trade WITH trend) add R?"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
import concept_lab as cl
import _batch_common as bc

m1 = cl.load_m1()
b = bc.bars(m1)
legs = bc.displacement_legs(b)
tdir, _, _ = bc.trend_state(b, legs)
o, h, l, c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
col = np.sign(c - o).astype(int)
sel = col != 0
d = -col
stop = np.where(d == -1, h, l)
ct = pd.DatetimeIndex(b["close_time"].to_numpy()[sel]).tz_convert("UTC")
ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d[sel],
                   "stop_px": stop[sel], "rr": 2.0,
                   "concept": ((tdir != 0) & (col == -tdir))[sel],
                   "in_trend": (tdir != 0)[sel]})
ev = ev.sort_values(["decision_time","direction"]).drop_duplicates(["decision_time","direction"]).reset_index(drop=True)
print("n", len(ev), "concept share", ev.concept.mean())
r = cl.gate_test(ev, "concept", mask_available_at="decision_time", max_hold="150min", n_boot=500, keep_trades=True)
print("GATE concept vs other fades:", json.dumps({k: r.get(k) for k in ("diff","ci_lo","ci_hi","verdict","verdict_detail")}, default=str))
print("halves", json.dumps(r.get("halves"), default=str)[:400])
tr = r["_trades"]
print(tr.columns.tolist())

# ---- stop-size stratified comparison (geometry artefact lives in small stops) ----
rng_ = (b["high"] - b["low"]).rolling(96, min_periods=48).mean().shift(0)
atr = pd.Series(rng_.to_numpy(), index=pd.DatetimeIndex(b["close_time"]).tz_convert("UTC"))
atr = atr[~atr.index.duplicated()]
tr["atr"] = atr.reindex(pd.DatetimeIndex(tr["decision_time"])).to_numpy()
tr = tr.dropna(subset=["atr", "ctrl_mean_R"])
tr["x"] = tr["net_R"] - tr["ctrl_mean_R"]
tr["x5"] = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]
tr["srel"] = tr["risk"] / tr["atr"]
edges = np.quantile(tr["srel"], [0, .2, .4, .6, .8, 1])
tr["q"] = np.clip(np.searchsorted(edges, tr["srel"], side="right") - 1, 0, 4)
g = tr.groupby(["q", "gate"])["x"].agg(["mean", "count"]).unstack()
print(g.round(4))
share = tr.groupby("gate")["q"].value_counts(normalize=True).unstack().round(3)
print("quintile mix by arm\n", share)
# stratified (reweight complement to gated quintile mix) difference + day-block bootstrap
tr["day"] = pd.DatetimeIndex(tr["decision_time"]).tz_convert("America/New_York").normalize()
days = tr["day"].unique()
def strat(df, col="x"):
    m = df.groupby(["q", "gate"])[col].mean().unstack()
    w = df[df.gate].q.value_counts(normalize=True).sort_index()
    return float(((m[True] - m[False]) * w).sum())
print("stratified gated-minus-complement:", round(strat(tr), 4), " tie5050:", round(strat(tr, "x5"), 4))
print("Q4-Q5 only:", round(strat(tr[tr.q >= 3]), 4), " Q1-Q2 only:", round(strat(tr[tr.q <= 1]), 4))
rs = np.random.default_rng(1)
byday = {d_: ix for d_, ix in tr.groupby("day").indices.items()}
keys = list(byday)
bs = []; bs45 = []
for _ in range(300):
    pick = rs.integers(0, len(keys), len(keys))
    ix = np.concatenate([byday[keys[k]] for k in pick])
    s = tr.iloc[ix]
    bs.append(strat(s)); bs45.append(strat(s[s.q >= 3]))
print("strat CI 95%:", np.round(np.quantile(bs, [.025, .975]), 4), " Q4-5 CI:", np.round(np.quantile(bs45, [.025, .975]), 4))
