"""Faithful paired test: same baseline entries, fixed 2R vs BE-at-+1R, in ORIGINAL R.
diff = fixed_R - be_R per trade (cost identical in both, cancels). Includes retest bars
that also hit the original stop and retest bars that also reach target."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_guest_01a")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl, _book as bk
from concept_lab.data import utc_ns
from concept_lab.engine import Market

m1 = cl.load_m1(); mkt = Market(m1); N = len(mkt.tn)
raw = bk.raw_cisd(m1)
dn = utc_ns(pd.DatetimeIndex(raw.decision_time)); sgn = raw.direction.to_numpy(np.int64)
stop = raw.stop_px.to_numpy(float)
i0 = np.searchsorted(mkt.tn, dn); i1 = np.searchsorted(mkt.tn, dn + bk.MAX_HOLD.value)
ok = (i0 < N) & (i1 > i0); i0c = np.clip(i0, 0, N-1); entry = mkt.o[i0c]
risk = sgn*(entry-stop); ok &= np.isfinite(risk) & (risk > 0)
k = np.flatnonzero(ok); H = 151; ar = np.arange(H)
rec = []
for s in range(0, len(k), 4000):
    kk = k[s:s+4000]
    idx = i0[kk][:, None] + ar; inw = idx < i1[kk][:, None]; idc = np.minimum(idx, N-1)
    g = sgn[kk][:, None]
    up = np.where(g > 0, mkt.h[idc], -mkt.l[idc]); dx = np.where(g > 0, mkt.l[idc], -mkt.h[idc])
    op = g*mkt.o[idc]; cl_ = g*mkt.c[idc]
    e = (sgn[kk]*entry[kk])[:, None]; r = risk[kk][:, None]
    st, tg, one = e-r, e+2*r, e+r
    first = lambda m: np.where(m.any(1), m.argmax(1), H)
    fs = first((dx <= st) & inw); ft = first((up >= tg) & inw); f1 = first((up >= one) & inw)
    last = inw.sum(1) - 1
    rows = np.arange(len(kk))
    def outcome(fs_, ft_, stoplvl, tie):   # tie: 'stop' | 'half' ; returns R
        R = np.empty(len(kk))
        for j in rows:
            a, b = fs_[j], ft_[j]
            if a == H and b == H:
                R[j] = (cl_[j, last[j]] - e[j, 0])/r[j, 0]; continue
            sl = stoplvl[j]
            sfill = min(sl, op[j, a]) if a < H else np.nan
            sR = (sfill - e[j, 0])/r[j, 0] if a < H else np.nan
            if a < b: R[j] = sR
            elif b < a: R[j] = 2.0
            else:
                thru_s = op[j, a] <= sl; thru_t = op[j, a] >= tg[j, 0]
                if thru_s: R[j] = sR
                elif thru_t and tie == 'half': R[j] = 2.0
                elif tie == 'half': R[j] = 0.5*sR + 0.5*2.0
                else: R[j] = sR
        return R
    for tie in ('stop', 'half'):
        Rf = outcome(fs, ft, st[:, 0], tie)
        # BE: after tag bar f1 (tag strictly before fs and ft, as the agent's rule), stop->entry
        tag = (f1 < H) & (f1 < fs) & (f1 < ft)
        bem = (dx <= e) & inw; bem &= ar[None, :] > f1[:, None]
        fb = first(bem)
        fs_be = np.where(tag, np.minimum(fb, fs), fs)
        lvl = np.where(tag[:, None] & (ar[None, :] >= 0), 0, 0)
        # stop level for BE branch = entry when the BE stop is what fires
        Rb = Rf.copy()
        for j in np.flatnonzero(tag):
            a, b = fb[j], ft[j]
            if a >= b and not (a == b and a < H):
                continue       # BE stop never fires before target/time: same as fixed
            if a == H: continue
            of = op[j, a]; sR = (min(0.0, of - e[j, 0]))/r[j, 0]
            if a < b: Rb[j] = sR
            else:  # same bar as target
                if of <= e[j, 0]: Rb[j] = sR
                elif of >= tg[j, 0] and tie == 'half': Rb[j] = 2.0
                elif tie == 'half': Rb[j] = 0.5*sR + 1.0
                else: Rb[j] = sR
        rec.append(pd.DataFrame({"t": dn[kk], "tie": tie, "Rf": Rf, "Rb": Rb, "tag": tag,
                                 "retest_hits_stop": tag & (fb < H) & (fb == fs),
                                 "retest_with_tgt": tag & (fb < H) & (fb == ft)}))
df = pd.concat(rec); df["d"] = df.Rf - df.Rb
df.to_parquet(__file__.replace("paired.py", "paired.parquet"))
print("done", len(df))
