"""Deep-dive: aggressive-run-hammer-signature vs STRUCTURE-placed stop controls.

The campaign control (harness) draws random entries with the same stop DISTANCE; this script
asks whether the edge survives when the control's stop is ALSO placed at a fresh structural
extreme (own 5m bar wick / prior 1-3 bar extreme), matched on year x stop-distance decile x
NY 3h bucket x direction by cell reweighting. Also: 50/50 tie re-score, calendar blocks,
halves, and absolute net R at a realistic XAUUSD spread (0.25/0.30/0.35 pt).

Read-only use of concept_lab (ledger disabled). Outputs -> out/*.pkl + stdout.
"""
import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
from pathlib import Path
import numpy as np, pandas as pd
import concept_lab as cl
import importlib.util

OUT = Path(__file__).parent / "out"; OUT.mkdir(exist_ok=True)
COST = 0.04
spec = importlib.util.spec_from_file_location(
    "orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a/aggressive-run-hammer-signature.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)

m1 = cl.load_m1()
b = cl.build_bars(m1, "5min")
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
ct = pd.DatetimeIndex(b["close_time"])
N = len(b)
rng = np.random.default_rng(7)


def run(name, ev, reps=1):
    p = OUT / f"{name}.pkl"
    if p.exists():
        return pd.read_pickle(p)
    r = cl.trade_test(ev, max_hold="50min", claim="+", ctrl_tod_tol_min=30, keep_trades=True, reps=reps)
    tr = r["_trades"].copy()
    tr["gross_5050"] = tr["net_R_5050"] + COST
    tr.to_pickle(p)
    print(f"{name}: n={r['n']} harness diff={r['diff']:+.4f} avg_R_gross={r['avg_R_gross']:+.4f}", flush=True)
    return tr


def mk(idx, direction, stop):
    ev = pd.DataFrame({"decision_time": ct[idx], "direction": direction.astype(int), "stop_px": stop})
    ev["available_at"] = ev["decision_time"]; ev["rr"] = 2.0
    return ev.sort_values("decision_time").reset_index(drop=True)


# ── concept book (exact original detector) ──
ev0 = cl.cache_frame(f"hammer_{orig.TF}_lb{orig.LOOKBACK}_w{orig.WICK_CUT}", lambda: orig.detect(m1))
T0 = run("concept", ev0, reps=5)
concept_bars = set(np.searchsorted(ct.values, ev0["decision_time"].values))

# eligible bars: not a concept bar, have 3 bars of history
elig = np.array([i for i in range(3, N) if i not in concept_bars])

# S1: random 5m bar, random direction, stop at the bar's own wick extreme
i1 = np.sort(rng.choice(elig, 300_000, replace=False)); d1 = rng.choice([-1, 1], len(i1))
ev1 = mk(i1, d1, np.where(d1 == 1, l[i1], h[i1]))
# S2: random bar, random direction, stop beyond the extreme of the last k bars (k=1..3, incl. current)
i2 = np.sort(rng.choice(elig, 300_000, replace=False)); d2 = rng.choice([-1, 1], len(i2)); k2 = rng.integers(1, 4, len(i2))
lo_k = np.stack([l, np.minimum(l, np.r_[np.nan, l[:-1]]), np.minimum.reduce([l, np.r_[np.nan, l[:-1]], np.r_[np.nan, np.nan, l[:-2]]])])
hi_k = np.stack([h, np.maximum(h, np.r_[np.nan, h[:-1]]), np.maximum.reduce([h, np.r_[np.nan, h[:-1]], np.r_[np.nan, np.nan, h[:-2]]])])
ev2 = mk(i2, d2, np.where(d2 == 1, lo_k[k2 - 1, i2], hi_k[k2 - 1, i2]))
# S3: mini-sweep of the prior 1-3 bars' extreme that closes back inside (no range, no shape), fade it,
#     stop at the wick; concept bars excluded
k = 3
plo = pd.Series(l).rolling(k).min().shift(1).to_numpy(); phi = pd.Series(h).rolling(k).max().shift(1).to_numpy()
hm = (l < plo) & (c > plo); sh = (h > phi) & (c < phi); both = hm & sh; hm &= ~both; sh &= ~both
mask = np.zeros(N, bool); mask[list(concept_bars)] = True
hm &= ~mask; sh &= ~mask
ih, is_ = np.flatnonzero(hm), np.flatnonzero(sh)
i3 = np.r_[ih, is_]; d3 = np.r_[np.ones(len(ih)), -np.ones(len(is_))]; s3 = np.r_[l[ih], h[is_]]
sel = rng.choice(len(i3), min(300_000, len(i3)), replace=False)
ev3 = mk(i3[sel], d3[sel], s3[sel])
# S4: same mini-sweep but TRADED WITH the break (continuation), stop at the bar's opposite extreme? no:
#     keep stop at the swept wick but random direction -> isolates direction info of the sweep
d4 = rng.choice([-1, 1], len(sel))
ev4 = mk(i3[sel], d4, np.where(d4 == 1, l[i3[sel]], h[i3[sel]]))

books = {"S1_ownwick_randdir": run("S1", ev1), "S2_prior1to3_randdir": run("S2", ev2),
         "S3_minisweep3_fade": run("S3", ev3), "S4_minisweep3_randdir": run("S4", ev4)}


def cells(tr, edges):
    t = pd.DatetimeIndex(tr["decision_time"])
    yr = t.year.to_numpy()
    rb = np.clip(np.searchsorted(edges, tr["risk"].to_numpy(), side="right") - 1, 0, len(edges) - 2)
    hb = t.tz_convert("America/New_York").hour.to_numpy() // 3
    return pd.Series(list(zip(yr, rb, hb, tr["direction"].to_numpy())), index=tr.index)


edges = np.r_[0, np.quantile(T0["risk"], np.linspace(0.1, 0.9, 9)), np.inf]
T0 = T0.assign(cell=cells(T0, edges), day=pd.DatetimeIndex(T0["decision_time"]).tz_convert("America/New_York").date)


def matched_diff(T, col, sub=None, nboot=500):
    A = T0 if sub is None else T0[sub(T0)]
    B = T.assign(cell=cells(T, edges), day=pd.DatetimeIndex(T["decision_time"]).tz_convert("America/New_York").date)
    B = B[B["cell"].isin(set(A["cell"]))]
    ca = A.groupby("cell").size(); cbm = B.groupby("cell")[col].mean()
    common = ca.index.intersection(cbm.index)
    A = A[A["cell"].isin(common)]
    w = (ca[common] / ca[common].sum())
    ctrl = float((w * cbm[common]).sum())
    diff = A[col].mean() - ctrl
    # day bootstrap: resample concept days; control cell means fixed (control n >> concept)
    B["cm"] = B["cell"].map(cbm)
    A = A.assign(cm=A["cell"].map(cbm))
    g = A.assign(d=A[col] - A["cm"]).groupby("day")["d"].agg(["sum", "count"])
    s, n_ = g["sum"].to_numpy(), g["count"].to_numpy()
    r = np.random.default_rng(1); bs = []
    for _ in range(nboot):
        ix = r.integers(0, len(g), len(g)); bs.append(s[ix].sum() / n_[ix].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return len(A), A[col].mean(), ctrl, diff, lo, hi, len(common) / len(ca)


print("\n== concept vs harness random control (same stop distance) ==")
print(f"n={len(T0)} gross={T0.gross_R.mean():+.4f} ctrl_gross={T0.ctrl_mean_R.mean()+COST:+.4f} diff={T0.gross_R.mean()-T0.ctrl_mean_R.mean()-COST:+.4f}"
      f" | 5050: {T0.gross_5050.mean():+.4f} vs {T0.ctrl_mean_R_5050.mean()+COST:+.4f} diff={T0.net_R_5050.mean()-T0.ctrl_mean_R_5050.mean():+.4f}")
print("\n== concept vs STRUCTURAL controls (cell-matched: year x risk decile x NY3h x dir) ==")
for nm, T in books.items():
    print(f"  {nm:24s} ctrl n={len(T):7d} ctrl gross mean={T.gross_R.mean():+.4f}")
    for col in ("gross_R", "gross_5050"):
        n, a, cc, d, lo, hi, cov = matched_diff(T, col)
        print(f"     {col:10s} concept={a:+.4f} ctrl={cc:+.4f} diff={d:+.4f} [{lo:+.4f},{hi:+.4f}] cells covered={cov:.2f}")

# robustness of the best structural comparisons
t0 = pd.DatetimeIndex(T0["decision_time"])
periods = {"H1 2016-20": lambda A: pd.DatetimeIndex(A.decision_time).year <= 2020,
           "H2 2021-26": lambda A: pd.DatetimeIndex(A.decision_time).year >= 2021}
qs = pd.DatetimeIndex(T0.decision_time).sort_values()
bnds = [qs[int(len(qs) * f)] for f in (0.25, 0.5, 0.75)]
for j, (a_, b_) in enumerate(zip([qs[0]] + bnds, bnds + [qs[-1] + pd.Timedelta(1, 'm')])):
    periods[f"B{j+1} {a_.date()}"] = (lambda a_, b_: lambda A: (pd.DatetimeIndex(A.decision_time) >= a_) & (pd.DatetimeIndex(A.decision_time) < b_))(a_, b_)
print("\n== period robustness, gross_R diff vs harness random ctrl / S1 / S3 ==")
for pn, f in periods.items():
    sub = T0[f(T0)]
    dr = (sub.gross_R - sub.ctrl_mean_R - COST).mean()
    r1 = matched_diff(books["S1_ownwick_randdir"], "gross_R", sub=f, nboot=300)
    r3 = matched_diff(books["S3_minisweep3_fade"], "gross_R", sub=f, nboot=300)
    print(f"  {pn:18s} n={len(sub):6d} vsRand={dr:+.4f}  vsS1={r1[3]:+.4f} [{r1[4]:+.4f},{r1[5]:+.4f}]  vsS3={r3[3]:+.4f} [{r3[4]:+.4f},{r3[5]:+.4f}]")

print("\n== by stop-distance decile (points): concept gross, diff vs S1/S3, spread cost @0.30pt ==")
rb = np.clip(np.searchsorted(edges, T0["risk"].to_numpy(), side="right") - 1, 0, 9)
for q in range(10):
    f = (lambda q: lambda A: np.clip(np.searchsorted(edges, A["risk"].to_numpy(), side="right") - 1, 0, 9) == q)(q)
    sub = T0[f(T0)]
    r1 = matched_diff(books["S1_ownwick_randdir"], "gross_R", sub=f, nboot=200)
    r3 = matched_diff(books["S3_minisweep3_fade"], "gross_R", sub=f, nboot=200)
    sc = (0.30 / sub.risk).mean()
    print(f"  D{q} risk {edges[q]:6.2f}-{edges[q+1]:6.2f}pt n={len(sub):5d} gross={sub.gross_R.mean():+.4f} vsRand={(sub.gross_R-sub.ctrl_mean_R-COST).mean():+.4f}"
          f" vsS1={r1[3]:+.4f} vsS3={r3[3]:+.4f} medSpreadR={np.median(0.30/sub.risk):.3f} net@0.30={(sub.gross_R-0.30/sub.risk).mean():+.4f}")

print("\n== absolute net avg_R at realistic spread ==")
for s in (0.0, 0.25, 0.30, 0.35):
    net = T0.gross_R - s / T0.risk
    net5 = T0.gross_5050 - s / T0.risk
    big = T0.risk >= 2.0
    print(f"  spread {s:.2f}pt: all mean={net.mean():+.4f} (5050 {net5.mean():+.4f}) median cost={np.median(s/T0.risk):.3f}R"
          f" | risk>=2pt n={big.sum()} mean={net[big].mean():+.4f} | risk>=1pt n={(T0.risk>=1).sum()} mean={net[T0.risk>=1].mean():+.4f}")
print("risk quantiles (pt):", np.round(np.quantile(T0.risk, [.1, .25, .5, .75, .9]), 3))
print("by year: n, median risk, gross, net@0.30")
for y, g in T0.groupby(t0.year):
    print(f"  {y} n={len(g):5d} medrisk={g.risk.median():.2f} gross={g.gross_R.mean():+.4f} vsRand={(g.gross_R-g.ctrl_mean_R-COST).mean():+.4f} net@0.30={(g.gross_R-0.30/g.risk).mean():+.4f}")
