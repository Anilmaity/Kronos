"""Is there any tradeable slice? Concept book restricted to stop-distance floors, and a
widened-stop variant (stop = candle extreme pushed out to >= f x ATR96 of 15m range), gross and
net of 0.30 pt spread, vs the same filter applied to the S1 structural fade null (all 15m candles, no trend)."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/cheat-code-entry")
exec(open("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/cheat-code-entry/deepdive.py").read().split("# ---------------- candidate pool")[0])
b = bc.bars(m1)
ct = utcns(b["close_time"]); o, h, l, c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
atr = pd.Series(h - l).rolling(96, min_periods=48).mean().to_numpy()
pos = {v: i for i, v in enumerate(ct.tolist())}
cj = np.array([pos.get(v, -1) for v in cdec.tolist()])
# S1 null universe: fade every 15m candle, stop at its extreme
col = np.sign(c - o); sel = np.flatnonzero(col != 0)
nd = -col[sel].astype(int); nstop = np.where(nd == -1, h[sel], l[sel])
res = {}
def summ(B, tag):
    out = {}
    for fl in (0, 1.0, 2.0, 3.0, 5.0):
        m = B.risk >= fl
        out[f"risk>={fl}"] = {"n": int(m.sum()), "gross": round(B.R[m].mean(), 4), "gross5050": round(B.R5[m].mean(), 4),
                              "net0.30": round((B.R[m] - 0.30 / B.risk[m]).mean(), 4)}
    return out
C = book(cdec, csgn, ev["stop_px"].to_numpy(float))
Nb = book(ct[sel], nd, nstop)
res["concept_floor"] = summ(C, "c"); res["S1null_floor"] = summ(Nb, "n")
# widened stops: stop = extreme pushed to at least f*ATR from the next open
for f in (0.25, 0.5, 1.0):
    for tag, dec, sg, st, jj in (("concept", cdec, csgn, ev["stop_px"].to_numpy(float), cj),
                                 ("S1null", ct[sel], nd, nstop, sel)):
        a = atr[jj]; i0 = np.clip(np.searchsorted(mkt.tn, dec), 0, N - 1); e = mkt.o[i0]
        need = e - sg * f * a
        st2 = np.where(sg == 1, np.minimum(st, need), np.maximum(st, need))
        B = book(dec, sg, st2)
        res[f"widen{f}ATR_{tag}"] = {"n": len(B), "median_risk": round(float(B.risk.median()), 3),
            "gross": round(B.R.mean(), 4), "gross5050": round(B.R5.mean(), 4),
            "net0.30": round((B.R - 0.30 / B.risk).mean(), 4),
            "H1": round(B.R[pd.to_datetime(B.dec, utc=True).dt.year.to_numpy() <= 2020].mean(), 4),
            "H2": round(B.R[pd.to_datetime(B.dec, utc=True).dt.year.to_numpy() >= 2021].mean(), 4)}
print(json.dumps(res, indent=1))
json.dump(res, open("tradeable_out.json", "w"), indent=1)
