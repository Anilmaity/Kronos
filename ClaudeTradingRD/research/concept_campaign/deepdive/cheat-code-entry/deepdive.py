"""Deep dive: cheat-code-entry EDGE (+0.078R vs harness control). Scratch; never writes results.

Books are resolved with the harness's own M1 resolver (concept_lab.engine.resolve_trades):
entry = open of first M1 at/after decision, stop-first ties (plus 50/50 re-score), 2R, 150 min clock.

Controls (all matched on stop DISTANCE, within the same 30-day period, own trades excluded):
  H   harness-like: random 15m close, SAME direction as the concept trade, stop placed at
      that distance from entry (arbitrary level)                       -> reproduces the harness null
  S   STRUCTURAL: random 15m close, random direction, stop AT the extreme of the prior
      k in {1,2,3} closed 15m candles (the extreme beyond entry), distance-matched
  S1  STRUCTURAL k=1 fade: random 15m close, fade that candle's colour, stop at its
      extreme  (= the concept's exact geometry minus the trend condition), distance-matched
  S1h S1 additionally matched on NY hour-of-day
Cost realism: net R = gross R - spread/risk, spread in {0.25, 0.30, 0.35} pt.
"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
import concept_lab as cl
from concept_lab.engine import get_market, resolve_trades
import importlib.util
spec = importlib.util.spec_from_file_location(
    "cce", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/cheat-code-entry.py")
cce = importlib.util.module_from_spec(spec); spec.loader.exec_module(cce)
import _batch_common as bc

RS = np.random.default_rng(20260923)
REPS = 5
HOLD = np.timedelta64(150, "m").astype("timedelta64[ns]")
m1 = cl.load_m1(); mkt = get_market(m1); N = len(mkt.tn)

def utcns(t):
    return pd.DatetimeIndex(t).tz_convert("UTC").as_unit("ns").asi8

def book(dec_ns, sgn, stop):
    """Resolve; returns DataFrame with gross R stop-first, 50/50 R, risk, ok mask."""
    i0 = np.searchsorted(mkt.tn, dec_ns, side="left")
    ok = i0 < N
    i0c = np.clip(i0, 0, N - 1)
    entry = mkt.o[i0c]
    risk = sgn * (entry - stop)
    i1 = np.searchsorted(mkt.tn, dec_ns + HOLD.astype(np.int64), side="left")
    ok &= np.isfinite(risk) & (risk > 0) & (i1 > i0)
    idx = np.flatnonzero(ok)
    e, s, r, a, b = entry[idx], stop[idx], risk[idx], i0[idx], i1[idx]
    g = sgn[idx]; tgt = e + g * 2 * r
    res = resolve_trades(mkt, g > 0, s, tgt, a, b)
    gross = g * (res["exit_px"] - e) / r
    rt, rs_ = 2.0, g * (s - e) / r
    g5 = np.where(res["ambiguous"], 0.5 * rs_ + 0.5 * rt, np.where(res["open_tgt"], rt, gross))
    return pd.DataFrame({"row": idx, "dec": dec_ns[idx], "sgn": g, "risk": r, "R": gross, "R5": g5,
                         "amb": res["ambiguous"] | res["open_tgt"]})

# ---------------- concept book ----------------
ev = cl.cache_frame("cheatcode_15m_disp4_trend24", lambda: cce.detect(cl.load_m1()))
cdec = utcns(ev["decision_time"]); csgn = ev["direction"].to_numpy().astype(int)
C = book(cdec, csgn, ev["stop_px"].to_numpy(float))
print("concept n", len(C), "gross avgR", C.R.mean().round(4), "5050", C.R5.mean().round(4),
      "median risk pt", C.risk.median().round(3), "risk quantiles", np.quantile(C.risk, [.1,.25,.5,.75,.9]).round(3))

# ---------------- candidate pool on every 15m close ----------------
b = bc.bars(m1)
ct = utcns(b["close_time"]); o, h, l, c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
nb = len(b)
nxt_i0 = np.clip(np.searchsorted(mkt.tn, ct, side="left"), 0, N - 1)
nxt_open = mkt.o[nxt_i0]
concept_keys = set(zip(cdec.tolist(), csgn.tolist()))
rows = []
for k in (1, 2, 3):
    hk = pd.Series(h).rolling(k).max().to_numpy(); lk = pd.Series(l).rolling(k).min().to_numpy()
    for d in (1, -1):
        stop = lk if d == 1 else hk
        risk = d * (nxt_open - stop)
        col = np.sign(c - o)
        rows.append(pd.DataFrame({"dec": ct, "sgn": d, "k": k, "stop": stop, "risk": risk,
                                  "fade": (col == -d), "nyh": pd.DatetimeIndex(b["close_time"]).tz_convert("America/New_York").hour}))
P = pd.concat(rows, ignore_index=True)
P = P[np.isfinite(P.risk) & (P.risk > 0)].reset_index(drop=True)
P = P[[ (a, s) not in concept_keys for a, s in zip(P.dec.tolist(), P.sgn.tolist())]].reset_index(drop=True)
print("pool", len(P))

PER = np.int64(30 * 86400 * 10**9)
def rbin(r): return np.floor(np.log(r) / np.log(1.10)).astype(np.int64)   # 10% distance bins

C["per"] = C.dec // PER; C["rb"] = rbin(C.risk.to_numpy())
C["nyh"] = pd.DatetimeIndex(pd.to_datetime(C.dec, utc=True)).tz_convert("America/New_York").hour
P["per"] = P.dec // PER; P["rb"] = rbin(P.risk.to_numpy())

def draw(pool, keys_c, keys_p):
    """For each concept row, REPS random pool rows with the same key. Returns (concept_idx, pool_idx)."""
    kp = pd.MultiIndex.from_frame(pool[keys_p]); order = np.argsort(kp.codes[0] * 0) if False else None
    g = pool.groupby(keys_p).indices
    ci, pi = [], []
    kc = C[keys_c].to_numpy()
    for j, key in enumerate(map(tuple, kc)):
        ix = g.get(key if len(key) > 1 else key[0])
        if ix is None: continue
        pick = ix[RS.integers(0, len(ix), REPS)]
        ci.extend([j] * REPS); pi.extend(pick.tolist())
    return np.array(ci), np.array(pi)

def run_ctrl(name, pool, keys, mode):
    ci, pi = draw(pool, keys, keys)
    sub = pool.iloc[pi]
    dec = sub.dec.to_numpy()
    if mode == "harness":      # same direction as concept, stop at same distance, arbitrary level
        sg = C.sgn.to_numpy()[ci]
        i0 = np.clip(np.searchsorted(mkt.tn, dec, side="left"), 0, N - 1)
        stop = mkt.o[i0] - sg * C.risk.to_numpy()[ci]
    else:                      # structural: pool row's own direction and stop
        sg = sub.sgn.to_numpy(); stop = sub.stop.to_numpy()
    K = book(dec, sg, stop)
    K["ci"] = ci[K.row.to_numpy()]
    cm = K.groupby("ci")[["R", "R5", "risk"]].mean()
    cov = len(cm) / len(C)
    return name, K, cm, cov

def boot_day(x, day, nb=1000):
    ud, inv = np.unique(day, return_inverse=True)
    s = np.bincount(inv, weights=x); n_ = np.bincount(inv)
    bs = []
    for _ in range(nb):
        pk = RS.integers(0, len(ud), len(ud))
        bs.append(s[pk].sum() / n_[pk].sum())
    return np.quantile(bs, [.025, .975])

day = (C.dec.to_numpy() - 5 * 3600 * 10**9) // (86400 * 10**9)
yr = pd.DatetimeIndex(pd.to_datetime(C.dec, utc=True)).year.to_numpy()
q = pd.qcut(C.risk.rank(method="first"), 5, labels=False).to_numpy()
blk = pd.qcut(C.dec.rank(method="first"), 4, labels=False).to_numpy()
out = {"concept": {"n": len(C), "gross_avgR": C.R.mean(), "gross_avgR_5050": C.R5.mean(),
                   "risk_pt_quantiles_10_25_50_75_90": np.quantile(C.risk, [.1,.25,.5,.75,.9]).tolist(),
                   "amb_share": C.amb.mean()}}
for sp in (0.25, 0.30, 0.35):
    net = C.R - sp / C.risk
    out["concept"][f"net_avgR_spread{sp}"] = net.mean()
    out["concept"][f"net_avgR_spread{sp}_byQ"] = [net[q == i].mean() for i in range(5)]
out["concept"]["gross_byQ"] = [C.R[q == i].mean() for i in range(5)]
out["concept"]["riskQ_median_pt"] = [float(np.median(C.risk[q == i])) for i in range(5)]

ctrls = [("H_harnesslike", P[P.k == 1], ["per", "rb"], "harness"),
         ("S_struct_k123_randdir", P, ["per", "rb"], "struct"),
         ("S1_struct_k1_fade", P[(P.k == 1) & P.fade], ["per", "rb"], "struct"),
         ("S1h_struct_k1_fade_hour", P[(P.k == 1) & P.fade], ["per", "rb", "nyh"], "struct"),
         ("Sk23_struct_k2or3_randdir", P[P.k >= 2], ["per", "rb"], "struct")]
for name, pool, keys, mode in ctrls:
    pool = pool.reset_index(drop=True)
    nm, K, cm, cov = run_ctrl(name, pool, keys, mode)
    j = cm.index.to_numpy()
    x = C.R.to_numpy()[j] - cm.R.to_numpy(); x5 = C.R5.to_numpy()[j] - cm.R5.to_numpy()
    d_, y_, q_, b_ = day[j], yr[j], q[j], blk[j]
    r = {"coverage": cov, "ctrl_n": len(K), "ctrl_avgR": K.R.mean(), "ctrl_amb": K.amb.mean(),
         "diff": x.mean(), "ci": boot_day(x, d_).tolist(), "diff_5050": x5.mean(), "ci_5050": boot_day(x5, d_).tolist(),
         "H1_2016_2020": x[y_ <= 2020].mean(), "H2_2021_2026": x[y_ >= 2021].mean(),
         "H1_5050": x5[y_ <= 2020].mean(), "H2_5050": x5[y_ >= 2021].mean(),
         "blocks": [x[b_ == i].mean() for i in range(4)], "blocks_5050": [x5[b_ == i].mean() for i in range(4)],
         "byQ": [x[q_ == i].mean() for i in range(5)], "byQ_5050": [x5[q_ == i].mean() for i in range(5)],
         "by_year": {int(Y): round(float(x[y_ == Y].mean()), 4) for Y in np.unique(y_)}}
    out[nm] = r
    print(nm, json.dumps({k: (np.round(v, 4).tolist() if isinstance(v, (list, np.ndarray)) else (round(v, 4) if isinstance(v, float) else v)) for k, v in r.items()}, default=float))
print(json.dumps(out["concept"], default=float, indent=0))
json.dump(out, open("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/cheat-code-entry/deepdive_out.json", "w"), default=float, indent=1)
