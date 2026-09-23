"""Independent re-implementation of advanced-market-structure-labeling reading a from the YAML:
STH = strict 3-bar swing high on 5m; ITH = STH higher than the previous and the next STH.
Confirmed at the close of the bar after the right-hand STH; skip if the ITH was traded
through before then. Short at next M1 open, stop at ITH high, 2R, 50 min wall clock. Mirror.
Own bar builder, own streaming detector, own M1 resolver and own random control."""
import os, sys, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
# own 5m bars
g = pd.DataFrame({"h": m1["high"].to_numpy(float), "l": m1["low"].to_numpy(float), "t": idx}, index=idx)
b = g.resample("5min", label="left", closed="left").agg({"h": "max", "l": "min", "t": "max"}).dropna()
start = b.index
close = np.maximum(start + pd.Timedelta("5min"), pd.DatetimeIndex(b["t"]) + pd.Timedelta("1min"))
H, L = b["h"].to_numpy(), b["l"].to_numpy()
n = len(H)

def stream(x, sgn):
    out = []
    sw = []                     # confirmed swing indices
    for i in range(2, n):       # at close of bar i, bar i-1 can be confirmed
        j = i - 1
        if x[j] > x[j - 1] and x[j] > x[i]:
            sw.append(j)
            if len(sw) >= 3:
                p0, p1, p2 = sw[-3], sw[-2], sw[-1]
                if x[p1] > x[p0] and x[p1] > x[p2] and x[p1 + 1:i + 1].max() < x[p1]:
                    out.append((close[i], sgn, sgn * -1 * 0 + (x[p1] if sgn == -1 else -x[p1])))
    return out

rows = stream(H, -1) + stream(-L, +1)
ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px"])
ev["available_at"] = ev["decision_time"]; ev["rr"] = 2.0
ev = ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)
ev.to_pickle("ev_indep.pkl")
orig = pd.read_pickle("ev_orig.pkl")
k = lambda d: set(zip(pd.DatetimeIndex(d.decision_time).asi8, d.direction.astype(int), np.round(d.stop_px.astype(float), 4)))
a, o = k(ev), k(orig)
print("indep", len(ev), "orig", len(orig), "common", len(a & o), "only_indep", len(a - o), "only_orig", len(o - a))

res = cl.trade_test(ev[["decision_time","available_at","direction","stop_px","rr"]], max_hold="50min")
print("harness on indep events:", {k2: res.get(k2) for k2 in ("n","diff","ci_lo","ci_hi","p","verdict","verdict_detail")})
json.dump({k2: res.get(k2) for k2 in ("n","diff","ci_lo","ci_hi","p","verdict","verdict_detail","ci_components")}, open("indep_out.json","w"), default=str, indent=1)

# ---- own resolver + own random control (no harness engine) ----
mt = idx.asi8; O = m1["open"].to_numpy(float); MH = m1["high"].to_numpy(float); ML = m1["low"].to_numpy(float); MC = m1["close"].to_numpy(float)
W = 50
def resolve(t_dec, d, sd):
    """entry next M1 open at/after t_dec; stop dist sd; 2R; 50min clock; stop-first; gap fills at open."""
    p = np.searchsorted(mt, t_dec)
    ok = p < len(mt) - W
    p = np.where(ok, p, 0)
    e = O[p]
    stop = e - d * sd; tgt = e + d * 2 * sd
    lim = t_dec + np.int64(50 * 60e9)
    R = np.full(len(p), np.nan)
    done = np.zeros(len(p), bool)
    for k2 in range(W):
        q = p + k2
        inb = (mt[q] < lim) & ~done & ok
        hi, lo, op = MH[q], ML[q], O[q]
        adv = np.where(d > 0, lo <= stop, hi >= stop)
        fav = np.where(d > 0, hi >= tgt, lo <= tgt)
        gap = np.where(d > 0, op <= stop, op >= stop) & (k2 > 0)
        hitS = inb & adv
        R[hitS] = np.where(gap[hitS], d[hitS] * (op[hitS] - e[hitS]) / sd[hitS], -1.0)
        hitT = inb & ~adv & fav
        R[hitT] = 2.0
        done |= hitS | hitT
        last = inb & ~done
        R[last] = d[last] * (MC[q[last]] - e[last]) / sd[last]   # provisional time exit
    return R, ok, e

t = pd.DatetimeIndex(orig.decision_time).asi8; d = orig.direction.to_numpy(int)
p = np.searchsorted(mt, t); e0 = O[np.minimum(p, len(O)-1)]
sd = d * (e0 - orig.stop_px.to_numpy(float))   # stop distance from actual entry
valid = sd > 0
Rr, ok, _ = resolve(t[valid], d[valid], sd[valid])
rng = np.random.default_rng(7)
grid = np.asarray(pd.DatetimeIndex(b["t"]).floor("5min").asi8 + np.int64(5*60e9))  # 5m grid closes where data exists
grid = np.unique(grid)
Rc = []
for rep in range(5):
    off = rng.integers(-30*288, 30*288, valid.sum())
    gi = np.clip(np.searchsorted(grid, t[valid]) + off, 0, len(grid)-1)
    rc, okc, _ = resolve(grid[gi], d[valid], sd[valid]); rc[~okc] = np.nan
    Rc.append(rc)
Rc = np.nanmean(np.vstack(Rc), axis=0)
m = ok & ~np.isnan(Rr) & ~np.isnan(Rc)
diff = Rr[m] - Rc[m]
days = pd.DatetimeIndex(t[valid][m]).floor("D").asi8
# day-cluster bootstrap
ud, inv = np.unique(days, return_inverse=True)
s = np.bincount(inv, diff); c = np.bincount(inv)
bs = []
r2 = np.random.default_rng(1)
for _ in range(1000):
    w = np.bincount(r2.integers(0, len(ud), len(ud)), minlength=len(ud))
    bs.append((w * s).sum() / (w * c).sum())
yr = pd.DatetimeIndex(t[valid][m]).year
print("own engine: n", m.sum(), "real avgR gross", Rr[m].mean(), "ctrl", Rc[m].mean(), "diff", diff.mean(), "CI", np.percentile(bs, [2.5, 97.5]))
print("H1", diff[yr < 2021].mean(), "H2", diff[yr >= 2021].mean())
print(pd.Series(diff).groupby(yr).mean().round(4).to_dict())
