"""Placebo block definitions + extra matching on local volatility. Own bootstrap, no ledger."""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from grid import m1, b, run, ct, H, L, C, bga
import concept_lab as cl

o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
allf = pd.read_pickle(os.path.dirname(__file__) + "/allf_40_10.pkl")
idx = np.searchsorted(ct, pd.DatetimeIndex(allf.decision_time).as_unit("ns").asi8)  # bar i
assert (ct[idx] == pd.DatetimeIndex(allf.decision_time).as_unit("ns").asi8).all()

def placebo(need_broken, need_fv, same_color=True, lmb=40, lfv=10):
    up, dn = c > o, c < o
    ov = np.zeros(len(allf), bool)
    for r, i in enumerate(idx):
        isb = allf.direction.iat[r] == 1; glo, ghi = allf.gap_low.iat[r], allf.gap_high.iat[r]
        for u in range(max(lfv + 2, i - 2 - lmb), i - 2):
            if same_color and not (up[u] if isb else dn[u]): continue
            if need_broken:
                if isb and not (l[u+1:i-2] < l[u]).any(): continue
                if (not isb) and not (h[u+1:i-2] > h[u]).any(): continue
            if need_fv:
                ks = np.arange(max(2, u - lfv), u)
                if isb:
                    fv = ks[h[ks] < l[ks-2]]
                    if not (len(fv) and (h[u] >= h[fv]).any()): continue
                else:
                    fv = ks[l[ks] > h[ks-2]]
                    if not (len(fv) and (l[u] <= l[fv]).any()): continue
            if min(h[u], ghi) - max(l[u], glo) > 0: ov[r] = True; break
    return ov

def fmt(tag, r, share):
    print(tag, "share=%.3f n=%d obs=%.4f null=%.4f diff=%+.4f [%+.4f, %+.4f]" % (share, r["n"], r["obs"], r["null"], r["diff"], r["lo"], r["hi"]), flush=True)

# 1) original, re-check
fmt("orig", run(allf, 120, "wick"), allf.overlap.mean())
# 2) extra matching on local volatility (trailing 24 1h-bar range / close) and gap size
rng24 = pd.Series(h).rolling(24).max().to_numpy() - pd.Series(l).rolling(24).min().to_numpy()
allf["vol"] = np.log(rng24[idx] / c[idx]); allf["gsz"] = np.log((allf.gap_high - allf.gap_low) / c[idx])
fmt("match+vol", run(allf, 120, "wick", extra=lambda f: f.vol.to_numpy()), allf.overlap.mean())
fmt("match+gapsize", run(allf, 120, "wick", extra=lambda f: f.gsz.to_numpy()), allf.overlap.mean())
# 3) placebos
for tag, kw in [("placebo_nofv(broken only)", dict(need_broken=True, need_fv=False)),
                ("placebo_nobroken(fv only)", dict(need_broken=False, need_fv=True)),
                ("placebo_any_samecolor", dict(need_broken=False, need_fv=False)),
                ("placebo_oppcolor_broken_fv", dict(need_broken=True, need_fv=True, same_color=False))]:
    f = allf.copy(); f["overlap"] = placebo(**kw)
    fmt(tag, run(f, 120, "wick"), f.overlap.mean())
# 4) residual block-specific: among gaps that overlap a 'broken-only' candle, does the FV condition matter?
f = allf.copy(); pb = placebo(True, False)
g = f[pb].copy()
fmt("within broken-overlap: MB vs not", run(g, 120, "wick"), g.overlap.mean())
