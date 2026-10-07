"""Stress tests on the rebuilt u1007a frame (wtt_u1007a_impl_events.pkl).

1. harness gate_test default and with the README trap-9 time-of-day hold (ctrl_tod_tol_min=30)
2. diff by NY session block of the decision hour
3. STRUCTURAL / within-concept matched control: each 'yes' trade vs the concept's own 'no'
   rows at the SAME NY hour, same direction, +-30 days, stop distance within 0.8-1.25x.
   Both arms' stops sit at the day's running extreme, so stop *placement* and clock are held;
   only the CISD confirmation differs.  Day-block bootstrap CI.
4. POI-deep-dive style structural control: stop beyond the prior-k closed 1h bars' extreme
   (k 1..24 best distance match within 0.8-1.25x), same NY hour, +-30 days, same direction.
5. B4 removed; realistic spread in pt.
Ledger redirected to a scratch file.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["CONCEPT_LAB_LEDGER"] = str(HERE / "wtt_u1007a_impl_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402
import concept_lab as cl      # noqa: E402
from concept_lab.engine import resolve_trades  # noqa: E402

rng = np.random.default_rng(7)
ev = pd.read_pickle(HERE / "wtt_u1007a_impl_events.pkl")
K = ("verdict", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p")

r0 = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)
print("default      ", {k: r0[k] for k in K})
r1 = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", ctrl_tod_tol_min=30)
print("tod30        ", {k: r1[k] for k in K}, "blocks", {k: round(v["diff"], 3) for k, v in r1["blocks"].items()},
      "halves", {k: round(r1["halves"][k]["diff"], 3) for k in ("H1", "H2")})

tr = r0["_trades"].copy()
tr["adj"] = tr.net_R - tr.ctrl_mean_R
ny = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York")
tr["hr"] = ny.hour
tr["day"] = np.asarray(cl.trading_day(pd.DatetimeIndex(tr.decision_time)))
tr = tr[np.isfinite(tr.adj)].reset_index(drop=True)
g = tr.gate.to_numpy(bool)


def blockname(h):
    return "asia18-01" if (h >= 18 or h <= 1) else ("ldn02-07" if h <= 7 else "ny08-16")


tr["blk"] = tr.hr.map(blockname)
print("\nshare of rows by session block (yes vs no):")
print(pd.crosstab(tr.blk, tr.gate, normalize="columns").round(3))
print("\nadj R by session block:")
print(tr.groupby(["blk", "gate"]).adj.agg(["mean", "count"]).round(4))


def day_boot(vals, days, nb=2000, seed=11):
    u, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, weights=vals)
    c = np.bincount(inv)
    r = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        k = r.integers(0, len(u), len(u))
        bs.append(s[k].sum() / c[k].sum())
    return vals.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


# ── 3. matched 'no' rows: same NY hour, direction, +-30 d, distance 0.8-1.25x ──
Y = tr[g].reset_index(drop=True)
N = tr[~g].reset_index(drop=True)
Nt = pd.DatetimeIndex(N.decision_time).asi8
order = np.argsort(Nt)
N = N.iloc[order].reset_index(drop=True)
Nt = Nt[order]
W = pd.Timedelta("30D").value
diffs, dd, nm = [], [], []
for r in Y.itertuples(index=False):
    t = pd.Timestamp(r.decision_time).value
    a, b = np.searchsorted(Nt, t - W), np.searchsorted(Nt, t + W)
    sub = N.iloc[a:b]
    m = sub[(sub.hr.to_numpy() == r.hr) & (sub.direction.to_numpy() == r.direction)
            & (sub.risk.to_numpy() >= 0.8 * r.risk) & (sub.risk.to_numpy() <= 1.25 * r.risk)]
    if len(m) == 0:
        continue
    diffs.append(r.net_R - m.net_R.mean())
    dd.append(r.day)
    nm.append(len(m))
diffs = np.array(diffs)
mu, lo, hi = day_boot(diffs, np.array(dd))
print(f"\nMATCHED yes - no (same NY hour, dir, +-30d, risk 0.8-1.25x): n={len(diffs)} of {len(Y)}, "
      f"median matches {np.median(nm):.0f}; diff {mu:+.4f} [{lo:+.4f}, {hi:+.4f}]")
ytime = pd.DatetimeIndex(Y.decision_time)
yr = np.asarray([pd.Timestamp(x).year for x in np.array(dd)])
yd = pd.DatetimeIndex(pd.to_datetime(np.array(dd)))
b4 = yd >= pd.Timestamp("2023-12-02")
mu2, lo2, hi2 = day_boot(diffs[~b4], np.array(dd)[~b4])
print(f"   same, excluding B4 (pre 2023-12-02): n={int((~b4).sum())} diff {mu2:+.4f} [{lo2:+.4f}, {hi2:+.4f}]")
mu3, lo3, hi3 = day_boot(diffs[b4], np.array(dd)[b4])
print(f"   same, B4 only: n={int(b4.sum())} diff {mu3:+.4f} [{lo3:+.4f}, {hi3:+.4f}]")

# ── 4. POI-style structural control for both arms (stop beyond prior-k 1h extreme) ──
mkt = cl.get_market()
h1 = cl.bars("1h")
H, L = h1.high.to_numpy(float), h1.low.to_numpy(float)
bct = pd.DatetimeIndex(h1.close_time).tz_convert("UTC").asi8
bhr = pd.DatetimeIndex(h1.close_time).tz_convert("America/New_York").hour.to_numpy()
valid = h1.n_m1.to_numpy() > 0
TNI = mkt.tn.view("int64")
I0 = np.clip(np.searchsorted(TNI, bct), 0, len(TNI) - 1)
ENT = mkt.o[I0]
KS = np.arange(1, 25)
lowk = np.vstack([pd.Series(L).rolling(k).min().to_numpy() for k in KS])     # (k, bar) incl. the bar itself
highk = np.vstack([pd.Series(H).rolling(k).max().to_numpy() for k in KS])
HOLD = pd.Timedelta("10h").value


def struct_ctrl(rows, reps=5):
    out = np.full(len(rows), np.nan)
    srcs, longs, stops, tgts, i0s, i1s, risks = [], [], [], [], [], [], []
    for n_, r in enumerate(rows.itertuples(index=False)):
        t = pd.Timestamp(r.decision_time).value
        a, b = np.searchsorted(bct, t - W), np.searchsorted(bct, t + W)
        cand = np.arange(a, b)
        cand = cand[(bhr[cand] == r.hr) & valid[cand] & (bct[cand] != t)]
        if len(cand) == 0:
            continue
        pick = rng.choice(cand, size=min(len(cand), reps * 4), replace=False)
        got = 0
        for p in pick:
            e = ENT[p]
            dist = (e - lowk[:, p]) if r.direction == 1 else (highk[:, p] - e)
            okk = np.isfinite(dist) & (dist > 0)
            if not okk.any():
                continue
            kk = np.argmin(np.where(okk, np.abs(np.log(np.where(okk, dist, 1) / r.risk)), np.inf))
            if not (0.8 * r.risk <= dist[kk] <= 1.25 * r.risk):
                continue
            rk = dist[kk]
            i0 = I0[p]
            i1 = np.searchsorted(TNI, bct[p] + HOLD)
            if i1 <= i0:
                continue
            srcs.append(n_); longs.append(r.direction == 1)
            stops.append(e - r.direction * rk); tgts.append(e + r.direction * 2 * rk)
            i0s.append(i0); i1s.append(i1); risks.append((e, rk, r.direction))
            got += 1
            if got == reps:
                break
    res = resolve_trades(mkt, np.array(longs), np.array(stops), np.array(tgts), np.array(i0s), np.array(i1s))
    er = np.array(risks)
    R = er[:, 2] * (res["exit_px"] - er[:, 0]) / er[:, 1] - 0.04
    srcs = np.array(srcs)
    s = np.bincount(srcs, weights=R, minlength=len(rows))
    c = np.bincount(srcs, minlength=len(rows))
    out[c > 0] = s[c > 0] / c[c > 0]
    return out


scY = struct_ctrl(Y)
Ns = N.sample(n=min(len(N), 20000), random_state=3).reset_index(drop=True)
scN = struct_ctrl(Ns)
my = np.isfinite(scY)
mn = np.isfinite(scN)
ay = Y.net_R.to_numpy()[my] - scY[my]
an = Ns.net_R.to_numpy()[mn] - scN[mn]
m_y, l_y, h_y = day_boot(ay, Y.day.to_numpy()[my])
m_n, l_n, h_n = day_boot(an, Ns.day.to_numpy()[mn])
print(f"\nSTRUCTURAL ctrl (prior-k 1h extreme stop, same NY hour): yes-sc {m_y:+.4f} [{l_y:+.4f}, {h_y:+.4f}] "
      f"(n={my.sum()}); no-sc {m_n:+.4f} [{l_n:+.4f}, {h_n:+.4f}] (n={mn.sum()}); gate diff {m_y - m_n:+.4f}")
# day-block CI on the structural gate diff: bootstrap days jointly
dy, dn_ = Y.day.to_numpy()[my], Ns.day.to_numpy()[mn]
ud = np.unique(np.r_[dy, dn_])
iy = np.searchsorted(ud, dy); in_ = np.searchsorted(ud, dn_)
sy, cy = np.bincount(iy, ay, len(ud)), np.bincount(iy, minlength=len(ud))
sn, cn = np.bincount(in_, an, len(ud)), np.bincount(in_, minlength=len(ud))
r_ = np.random.default_rng(5)
bs = []
for _ in range(2000):
    k = r_.integers(0, len(ud), len(ud))
    bs.append(sy[k].sum() / cy[k].sum() - sn[k].sum() / cn[k].sum())
print(f"   structural gate diff CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]")

# ── 5. realistic spread on the gated book ──
for sp in (0.3, 0.45, 0.6):
    net = Y.gross_R.to_numpy() - sp / Y.risk.to_numpy()
    print(f"gated book net at {sp} pt spread: {net.mean():+.4f}R (median stop {Y.risk.median():.2f} pt)")
print("gated gross", round(Y.gross_R.mean(), 4), "net@0.04R", round(Y.net_R.mean(), 4))
