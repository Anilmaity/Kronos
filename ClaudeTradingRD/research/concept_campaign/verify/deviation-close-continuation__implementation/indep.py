"""Independent re-implementation of deviation-close-continuation reading a (verify only)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
H = m1["high"].to_numpy(float); L = m1["low"].to_numpy(float)
O = m1["open"].to_numpy(float); C = m1["close"].to_numpy(float)
b4 = cl.build_bars(m1, "4h", grid4h="forex")
starts = pd.DatetimeIndex(b4.index).tz_convert("UTC")
bid = np.searchsorted(starts.asi8, idx.asi8, side="right") - 1
bounds = np.searchsorted(bid, np.arange(len(b4) + 1))  # m1 slice per 4h bar
closes4 = pd.DatetimeIndex(b4["close_time"]).tz_convert("UTC")

rows = []
for k in range(1, len(b4)):
    a0, a1 = bounds[k-1], bounds[k]
    if a1 - a0 < 2: continue
    h, l = H[a0:a1], L[a0:a1]
    o, c = O[a0], C[a1-1]
    rng = h.max() - l.min()
    if c < o:   # bearish prev: leg low-before-high -> high, project down from low
        ih = int(np.argmax(h)); base = l[:ih+1].min(); leg = h[ih] - base; d = -1
    elif c > o:
        il = int(np.argmin(l)); base = h[:il+1].max(); leg = base - l[il]; d = 1
    else: continue
    if leg < 0.10 * rng or leg <= 0: continue
    trig = base + d * 2.5 * leg; tgt = base + d * 4.0 * leg
    s0, s1 = bounds[k], bounds[k+1] if k + 1 < len(bounds) else len(idx)
    if s1 <= s0: continue
    ti = idx[s0:s1]
    q = pd.DataFrame({"h": H[s0:s1], "l": L[s0:s1], "c": C[s0:s1]}, index=ti)
    qb = q.resample("15min", label="left").agg({"h": "max", "l": "min", "c": "last"}).dropna()
    touched = False
    for t0, r in qb.iterrows():
        ct = t0 + pd.Timedelta("15min")
        if ct > closes4[k]: break
        # -4 touched at or before this bar close?
        if (d == -1 and r.l <= tgt) or (d == 1 and r.h >= tgt): touched = True
        beyond = (r.c < trig) if d == -1 else (r.c > trig)
        if beyond:
            if not touched:
                rows.append((ct, d, trig, tgt))
            break   # only the first close beyond
ev = pd.DataFrame(rows, columns=["decision_time", "direction", "trigger_px", "target_px"])
print("indep n", len(ev))
import importlib.util as iu
sp=iu.spec_from_file_location("orig","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_guest_02a/deviation-close-continuation.py"); om=iu.module_from_spec(sp); sp.loader.exec_module(om)
ref = om.detect_a(m1)
print("orig n", len(ref))
ev["decision_time"]=pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
mk = pd.merge(ev, ref, on="decision_time", how="outer", indicator=True)
both=mk[mk._merge=="both"]; print("max tgt diff", np.abs(both.target_px_x-both.target_px_y).max(), "dir agree", (both.direction_x==both.direction_y).mean())
print(mk["_merge"].value_counts())

mkt = cl.get_market()
t = pd.DatetimeIndex(ev["decision_time"])
pos = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)
px = mkt.o[pos]; tgt = ev["target_px"].to_numpy(); d = ev["direction"].to_numpy()
dist = tgt - px
def hit(times, lv, dirs):
    out = np.zeros(len(times), bool)
    for s, sd in ((1, "above"), (-1, "below")):
        m = dirs == s
        if m.any(): out[m] = cl.touch(times[m], lv[m], sd, horizon_bars=240)["hit"].to_numpy()
    return out
obs = hit(t, tgt, d)
opp = hit(t, px - dist, -d)
print("dist/leg share already beyond target at entry:", np.mean(np.sign(dist) != d))
print("observed", obs.mean(), "opposite-same-moment", opp.mean())
# paired day-block bootstrap of obs-opp
day = t.tz_convert("America/New_York").normalize()
df = pd.DataFrame({"d": obs.astype(float) - opp.astype(float), "day": day})
g = df.groupby("day")["d"].agg(["sum", "count"])
rng = np.random.default_rng(0)
bs = []
S, N = g["sum"].to_numpy(), g["count"].to_numpy()
for _ in range(2000):
    i = rng.integers(0, len(g), len(g)); bs.append(S[i].sum() / N[i].sum())
print("obs-opp diff", df["d"].mean(), "CI", np.percentile(bs, [2.5, 97.5]))
# halves
for nm, m in (("H1", t < pd.Timestamp("2021-01-01", tz="UTC")), ("H2", t >= pd.Timestamp("2021-01-01", tz="UTC"))):
    print(nm, obs[m].mean(), opp[m].mean(), (obs[m].astype(float)-opp[m]).mean())
