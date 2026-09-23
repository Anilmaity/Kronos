import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
spec = importlib.util.spec_from_file_location("g", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_02a/gap-direction-fade-rule.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
f = g.build(); f = f[~f["through"]].reset_index(drop=True)
t = pd.DatetimeIndex(f.decision_time); up = f.up.to_numpy(); lvl = f.prev_close.to_numpy()
dist = lvl - f.px.to_numpy(); mkt = cl.get_market()
def hits(tt, level, upm, H=60, flip=False):
    out = np.full(len(tt), np.nan)
    for m, side in ((upm, "below"), (~upm, "above")):
        if flip: side = "above" if side=="below" else "below"
        if m.any(): out[m] = cl.touch(tt[m], level[m], side, horizon_bars=H)["hit"].to_numpy()
    return out
obs = hits(t, lvl, up)
print("n", len(t), "obs", np.nanmean(obs))
ny = t.tz_convert("America/New_York"); print("NY tod counts", pd.Series(ny.strftime("%H:%M")).value_counts().head(5).to_dict())
# gap size stats
d14 = cl.bars("1D"); 
print("abs dist quantiles $", np.quantile(np.abs(dist), [.1,.25,.5,.75,.9]))
# within-event symmetric control: opposite side, same distance (continuation touch)
opp = hits(t, f.px.to_numpy() - dist, up, flip=True)
print("fill-side", np.nanmean(obs), "away-side same dist", np.nanmean(opp), "diff", np.nanmean(obs)-np.nanmean(opp))
# nulls with different tod tolerance
for tol in (30, 5, 0):
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=tol)
    rs=[]; tods=[]
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:,k]).tz_localize("UTC"); ok = ~tk.isna()
        pk = np.full(len(t), np.nan); pk[ok] = mkt.o[mkt.pos_at_or_after(tk[ok])]
        h = np.full(len(t), np.nan)
        for m, side in ((up,"below"),(~up,"above")):
            mm = m & ok
            if mm.any(): h[mm] = cl.touch(tk[mm], pk[mm]+dist[mm], side, horizon_bars=60)["hit"].to_numpy()
        rs.append(np.nanmean(h)); tods += list(tk[ok].tz_convert("America/New_York").strftime("%H:%M"))
    ts = pd.Series(tods)
    print(f"tol {tol}: null {np.mean(rs):.4f} diff {np.nanmean(obs)-np.mean(rs):+.4f}; share at 18:00 {np.mean(ts=='18:00'):.2f} 18:01 {np.mean(ts=='18:01'):.2f}")
# hit timing
tb = []
for m, side in ((up,"below"),(~up,"above")):
    r = cl.touch(t[m], lvl[m], side, horizon_bars=60)
    tb.append(r)
r = pd.concat(tb); print(r.columns.tolist()); print(r.head())
np.save("obs.npy", obs); f.to_pickle("f.pkl")
