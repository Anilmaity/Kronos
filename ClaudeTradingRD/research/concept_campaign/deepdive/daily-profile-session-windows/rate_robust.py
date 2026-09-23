"""Deep-dive 1: robustness + a VOLATILITY-ONLY null for the rate result.

Question: is "the day high/low forms in London 02-05 / NY 08:30-12" anything beyond
"extremes form where the volatility is"? Null = the same day's M1 close-to-close moves with
randomised signs (keeps each minute's absolute move = the day's own volatility clock,
destroys direction/structure). Extremes are measured on the close path in both arms.
Also: calendar blocks, halves, per-window decomposition, per-year.
No harness writes; the harness is used only for load_m1 / trading_day / ny_minute_of_day.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

m1 = cl.load_m1(); idx = m1.index
td = np.asarray(cl.trading_day(idx, 18))
msr = (np.asarray(cl.ny_minute_of_day(idx)) - 1080) % 1440
W = [(480, 660), (870, 1080)]  # 02:00-05:00, 08:30-12:00 NY as minutes since 18:00

df = pd.DataFrame({"td": td, "c": m1.close.to_numpy(), "h": m1.high.to_numpy(),
                   "l": m1.low.to_numpy(), "msr": msr})
cnt = df.groupby("td").size()
keep = cnt[cnt >= 600].index
df = df[df.td.isin(keep)].reset_index(drop=True)
codes, uniq = pd.factorize(df.td, sort=True)
df["k"] = codes
start = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
dc = np.diff(df.c.to_numpy(), prepend=np.nan); dc[start] = 0.0


def ins(x, shift=0):
    r = np.zeros(len(x), bool)
    for a, z in W:
        r |= (x >= a + shift) & (x < z + shift)
    return r


def extremes(path):
    s = pd.Series(path)
    g = s.groupby(codes)
    return df.msr.to_numpy()[g.idxmax().to_numpy()], df.msr.to_numpy()[g.idxmin().to_numpy()]


def rate(xh, xl, shift=0):
    return (ins(xh, shift).astype(float) + ins(xl, shift)) / 2

# observed on M1 high/low (as the campaign) and on the close path (comparable to the vol null)
g = df.groupby("k")
xh_hl = df.msr.to_numpy()[g.h.idxmax().to_numpy()]; xl_hl = df.msr.to_numpy()[g.l.idxmin().to_numpy()]
obs_hl = rate(xh_hl, xl_hl)
cpath = df.c.to_numpy()
xh_c, xl_c = extremes(cpath)
obs_c = rate(xh_c, xl_c)

rng = np.random.default_rng(20260923)
vn = []
for r in range(20):
    sg = rng.choice([-1.0, 1.0], size=len(dc))
    p = pd.Series(dc * sg).groupby(codes).cumsum().to_numpy()
    a, b = extremes(p)
    vn.append(rate(a, b))
vn = np.mean(vn, axis=0)
# the campaign's block-shift null for reference (on HL extremes)
bs = np.mean([rate(xh_hl, xl_hl, rng.integers(-480, 1380 - 1080 + 1, len(obs_hl))) for _ in range(20)], axis=0)

t = pd.DatetimeIndex(uniq)
def boot(d, n=2000):
    # day-block stationary-ish: moving blocks of 20 days
    L = 20; m = len(d); nb = m // L + 1
    out = []
    for _ in range(n):
        st = rng.integers(0, m - L, nb)
        ii = (st[:, None] + np.arange(L)).ravel()[:m]
        out.append(d[ii].mean())
    return np.percentile(out, [2.5, 97.5])

print(f"days={len(obs_hl)}")
print(f"observed (M1 H/L) {obs_hl.mean():.4f}  block-shift null {bs.mean():.4f}  diff {obs_hl.mean()-bs.mean():+.4f}")
print(f"observed (close path) {obs_c.mean():.4f}")
d = obs_c - vn
lo, hi = boot(d)
print(f"VOL-ONLY null (sign-randomised own-day M1 moves, 20 reps) {vn.mean():.4f}  "
      f"obs-vol diff {d.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}]  -> share of block-shift lift explained by vol: "
      f"{(vn.mean()-bs.mean())/(obs_c.mean()-bs.mean()):.2f}")
blk = np.array_split(np.arange(len(d)), 4)
print("4 blocks obs-vol:", [round(d[b].mean(), 4) for b in blk], " obs-blockshift:", [round((obs_hl-bs)[b].mean(), 4) for b in blk])
h1 = t < pd.Timestamp("2021-01-01", tz=t.tz)
print(f"H1 obs-vol {d[h1].mean():+.4f}  H2 {d[~h1].mean():+.4f}")
print("per-year obs-vol:", pd.Series(d, index=t.year).groupby(level=0).mean().round(3).to_dict())
# per window decomposition
for nm, ww in (("London 02-05", [W[0]]), ("NY 08:30-12", [W[1]])):
    def ins1(x):
        r = np.zeros(len(x), bool)
        for a, z in ww: r |= (x >= a) & (x < z)
        return r
    o = (ins1(xh_c).astype(float) + ins1(xl_c)) / 2
    vv = []
    rng2 = np.random.default_rng(7)
    for r in range(10):
        sg = rng2.choice([-1.0, 1.0], size=len(dc))
        p = pd.Series(dc * sg).groupby(codes).cumsum().to_numpy()
        a, b = extremes(p); vv.append((ins1(a).astype(float) + ins1(b)) / 2)
    vv = np.mean(vv, axis=0)
    print(f"  {nm}: obs {o.mean():.4f} vol-null {vv.mean():.4f} diff {o.mean()-vv.mean():+.4f}")
# hourly: share of extremes vs share of abs-move (variance proxy)
hr = (df.msr.to_numpy() // 60)
absm = pd.Series(np.abs(dc)).groupby(hr).sum(); absm /= absm.sum()
ex = pd.Series(np.r_[xh_c, xl_c] // 60).value_counts(normalize=True).sort_index()
vol_ex = pd.Series(np.r_[extremes(pd.Series(dc*rng.choice([-1.,1.],len(dc))).groupby(codes).cumsum().to_numpy())] ).explode()
print("hour since 18:00 | NY hour | extreme share | vol-null share(1 rep) | abs-move share")
a, b = extremes(pd.Series(dc * rng.choice([-1., 1.], len(dc))).groupby(codes).cumsum().to_numpy())
vx = pd.Series(np.r_[a, b] // 60).value_counts(normalize=True).sort_index()
for h in range(23):
    print(f"  {h:2d} | {(18+h)%24:02d} | {ex.get(h,0):.3f} | {vx.get(h,0):.3f} | {absm.get(h,0):.3f}")
