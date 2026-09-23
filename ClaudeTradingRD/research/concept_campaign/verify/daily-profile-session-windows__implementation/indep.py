"""Independent re-implementation (no harness helpers except the M1 loader)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

m1 = cl.load_m1()
ny = m1.index.tz_convert("America/New_York")
mins = ny.hour * 60 + ny.minute
# trading day: bars at/after 18:00 NY belong to next calendar day's session label
lbl = (ny.normalize().tz_localize(None) + pd.to_timedelta((mins >= 18 * 60).astype(int), unit="D"))
msr = (np.asarray(mins) - 1080) % 1440
print("bars in halt hour 17:00-18:00 NY:", int(((mins >= 1020) & (mins < 1080)).sum()), "of", len(mins))
df = pd.DataFrame({"d": lbl, "h": m1["high"].to_numpy(), "l": m1["low"].to_numpy(), "msr": msr})
out = []
for d, g in df.groupby("d", sort=True):
    if len(g) < 600: continue
    h = g["h"].to_numpy(); l = g["l"].to_numpy(); m = g["msr"].to_numpy()
    out.append((d, m[np.argmax(h)], m[np.argmax(h[::-1]) and len(h)-1-np.argmax(h[::-1])], m[np.argmin(l)],
                m[len(l)-1-np.argmin(l[::-1])], len(g)))
R = pd.DataFrame(out, columns=["d", "hi", "hi_last", "lo", "lo_last", "n"])
print("days", len(R))
W = [(480, 660), (870, 1080)]   # 02:00-05:00, 08:30-12:00 as minutes since 18:00
def ins(x, s):
    r = np.zeros(len(x), bool)
    for a, z in W: r |= (x >= a + s) & (x < z + s)
    return r
def score(s, hi="hi", lo="lo"):
    return (ins(R[hi].to_numpy(), s).astype(float) + ins(R[lo].to_numpy(), s)) / 2
obs = score(0)
print("observed %.4f" % obs.mean(), " last-occurrence variant %.4f" % score(0, "hi_last", "lo_last").mean())
shifts = np.arange(-480, 300 + 1)
nulls = np.array([score(s).mean() for s in shifts])
print("exhaustive block-shift null mean %.4f ; rank of s=0: %d of %d ; max %.4f at shift %d"
      % (nulls.mean(), (nulls >= nulls[shifts == 0][0]).sum(), len(shifts), nulls.max(), shifts[nulls.argmax()]))
for s in (-60, -30, 0, 30, 60, 90): print("  shift", s, "%.4f" % nulls[shifts == s][0])
# null excluding shifts overlapping the true windows (|s|>=210)
far = np.abs(shifts) >= 210
print("null over non-overlapping shifts %.4f" % nulls[far].mean())
# independent placement of each window anywhere in the 23h day
rng = np.random.default_rng(1)
acc = []
for _ in range(200):
    a1 = rng.integers(0, 1380 - 180 + 1); a2 = rng.integers(0, 1380 - 210 + 1)
    ww = [(a1, a1 + 180), (a2, a2 + 210)]
    def ins2(x):
        r = np.zeros(len(x), bool)
        for a, z in ww: r |= (x >= a) & (x < z)
        return r
    acc.append(((ins2(R.hi.to_numpy()) + 0.0 + ins2(R.lo.to_numpy())) / 2).mean())
print("independent-placement null %.4f" % np.mean(acc))
# per-day paired diff vs exhaustive null, block bootstrap by day (block 20 days)
nd = np.mean([score(s) for s in shifts[::10]], axis=0)
d = obs - nd
n = len(d); B = 2000; bs = []
for _ in range(B):
    idx = []
    while len(idx) < n:
        st = rng.integers(0, n); L = rng.geometric(1/20); idx.extend(((st + np.arange(L)) % n).tolist())
    bs.append(d[np.array(idx[:n])].mean())
print("diff %.4f CI [%.4f, %.4f]" % (d.mean(), *np.percentile(bs, [2.5, 97.5])))
half = R.d < "2021-01-01"
print("H1 %.4f H2 %.4f" % (d[half].mean(), d[~half].mean()))
# component rates
print("high in London %.3f, high in NYAM %.3f, low in London %.3f, low in NYAM %.3f" % (
    ((R.hi>=480)&(R.hi<660)).mean(), ((R.hi>=870)&(R.hi<1080)).mean(),
    ((R.lo>=480)&(R.lo<660)).mean(), ((R.lo>=870)&(R.lo<1080)).mean()))
# 30-min histogram of extremes
h = np.histogram(np.r_[R.hi, R.lo], bins=np.arange(0, 1441, 60))[0]
print("extremes per hour since 18:00:", h.tolist())
