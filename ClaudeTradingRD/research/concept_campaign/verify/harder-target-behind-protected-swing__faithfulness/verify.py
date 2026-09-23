import sys, importlib.util, pickle, os
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a/harder-target-behind-protected-swing.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
from _common import *
from detectors.primitives import swing_points
HERE = os.path.dirname(__file__)
RUN = int(os.environ.get("RUN", 2)); LB = int(os.environ.get("LB", 300))
HH, MM = map(int, os.environ.get("DEC", "9:30").split(":"))

def detect_all(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["open","high","low","close"]], 2, 2)
    ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"])); n = len(b)
    hi, lo, c_ = (b[k].to_numpy(float) for k in ("high","low","close"))
    avail = np.full(n, np.datetime64("2262-01-01","ns")); pos = np.arange(n)
    for kind in ("swing_high","swing_low"):
        m = sw[kind].to_numpy() & (pos+2<n); avail[m] = ct[pos[m]+2]
    prot = {}
    for kind, px, lower in (("swing_low",lo,True),("swing_high",hi,False)):
        idx = np.flatnonzero(sw[kind].to_numpy() & (pos+2<n)); p = np.zeros(n,bool)
        for a in range(RUN, len(idx)):
            prev = px[idx[a-RUN:a]]
            p[idx[a]] = (px[idx[a]]<prev).all() if lower else (px[idx[a]]>prev).all()
        prot[kind] = p
    ny = cl.to_ny(pd.DatetimeIndex(b["close_time"]))
    dec = np.flatnonzero((ny.hour==HH)&(ny.minute==MM))
    rows = []
    for j in dec:
        t = ct[j]; P = c_[j]; a0 = max(0, j-LB+1)
        for kind, px, below in (("swing_low",lo,True),("swing_high",hi,False)):
            cand = np.flatnonzero(sw[kind].to_numpy()[a0:j+1]) + a0
            cand = cand[avail[cand] <= t]; keep = []
            for c in cand:
                later = lo[c+1:j+1] if below else hi[c+1:j+1]
                unt = (later>=px[c]).all() if below else (later<=px[c]).all()
                if unt and ((px[c]<P) if below else (px[c]>P)): keep.append(c)
            keep = np.array(keep,int)
            if len(keep) < 2: continue
            pk = keep[prot[kind][keep]]
            # nearest-candidate rank
            d = np.abs(P - px[keep]); rank = d.argsort().argsort()
            for r, c in zip(rank, keep):
                lv = px[c]; s = px[pk[pk!=c]]
                g = ((s>lv)&(s<P)).any() if below else ((s<lv)&(s>P)).any()
                # alt: any swing (not only protected) between -> 'behind another swing'
                s2 = px[keep[keep!=c]]
                g2 = ((s2>lv)&(s2<P)).any() if below else ((s2<lv)&(s2>P)).any()
                rows.append((t, lv, -1 if below else 1, abs(P-lv), P, bool(g), bool(g2),
                             bool(prot[kind][c]), int(r), len(keep), int(j-c)))
    out = pd.DataFrame(rows, columns=["t","level","side","dist","price","guarded","behind_any",
                                      "is_prot","rank","ncand","age"])
    out.insert(0,"decision_time", cl.data.from_ns(out["t"].to_numpy("datetime64[ns]")))
    return out.drop(columns="t")

key = f"all_run{RUN}_lb{LB}_{HH}{MM:02d}"
fp = os.path.join(HERE, key + ".pkl")
m1 = cl.load_m1()
if os.path.exists(fp):
    ev = pd.read_pickle(fp)
else:
    ev = detect_all(m1)
    t = pd.DatetimeIndex(ev["decision_time"]); hb = orig.bars_left_in_day(t, m1)
    side = ev.side.to_numpy(); lvl = ev.level.to_numpy(float); dist = ev.dist.to_numpy(float)
    def hits(times, levels):
        h = np.zeros(len(levels)); tt = pd.DatetimeIndex(times); ok = ~pd.isna(tt)
        for s_, nm in ((1,"above"),(-1,"below")):
            m = (side==s_)&ok
            if m.any(): h[m] = cl.touch(tt[m], levels[m], nm, horizon_bars=hb[m])["hit"].to_numpy()
        h[~ok] = np.nan; return h
    ev["obs"] = hits(t, lvl)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=0)
    nulls = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:,k]).tz_localize("UTC")
        nulls.append(hits(tk, orig.price_at(tk, m1) + side*dist))
    ev["null"] = np.nanmean(np.vstack(nulls), axis=0)
    ev.to_pickle(fp)
print(key, len(ev))
