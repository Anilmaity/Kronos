import sys, importlib.util
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b")
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05b/old-high-low-three-outcomes.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)

def detect_v(m1, TF="15min", K=3, level="1D", grid4h="forex", day_open_hour=18, pd_filter=False):
    b = cl.build_bars(m1, TF, grid4h=grid4h, day_open_hour=day_open_hour)
    start = pd.DatetimeIndex(b.index)
    lv = cl.prior_hilo(start, level, m1=m1, grid4h=grid4h, day_open_hour=day_open_hour)
    PH, PL = lv["high"].to_numpy(float), lv["low"].to_numpy(float)
    key = cl.trading_day(start).asi8 if level == "1D" else PH  # first interaction per level
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ctime = pd.DatetimeIndex(b["close_time"]); n = len(b); out = []
    for side in (1, -1):
        L = PH if side > 0 else PL
        bw = (h > L) if side > 0 else (l < L)
        oi = (o <= L) if side > 0 else (o >= L)
        seen = set()
        for i in np.flatnonzero(bw & oi & np.isfinite(L)):
            k = (key[i], L[i]) if level != "1D" else key[i]
            if k in seen: continue
            seen.add(k); lvl = L[i]
            co = (c[i] > lvl) if side > 0 else (c[i] < lvl)
            if not co:
                if pd_filter:  # branch 3 refinement: close in premium (bear) / discount (bull) of prior range
                    mid = 0.5 * (PH[i] + PL[i])
                    if not ((c[i] > mid) if side > 0 else (c[i] < mid)):
                        continue
                out.append((i, -side, h[i] if side > 0 else l[i], 3, side)); continue
            back = None
            for m in range(i + 1, min(i + K + 1, n)):
                if (c[m] < lvl) if side > 0 else (c[m] > lvl): back = m; break
            if back is not None:
                stop = h[i:back+1].max() if side > 0 else l[i:back+1].min()
                out.append((back, -side, stop, 2, side))
            elif i + K < n:
                m = i + K
                stop = l[i+1:m+1].min() if side > 0 else h[i+1:m+1].max()
                if (stop < c[m]) if side > 0 else (stop > c[m]):
                    out.append((m, side, stop, 1, side))
    o_ = pd.DataFrame(out, columns=["i", "direction", "stop_px", "branch", "side"])
    dec = ctime[o_["i"].to_numpy()]
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": o_["direction"].astype(int).to_numpy(),
        "stop_px": o_["stop_px"].to_numpy(float), "rr": 2.0, "branch": o_["branch"].astype(int).to_numpy(),
        "side": o_["side"].astype(int).to_numpy()})
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)

def run(tag, ev, **kw):
    kw.setdefault("max_hold", "150min")
    r = cl.trade_test(ev, n_boot=500, keep_trades=True, **kw)
    tr = r["_trades"]
    d5 = (tr["net_R_5050"] - tr["ctrl_mean_R_5050"]).mean()
    bl = {k: round(v["diff"], 3) for k, v in (r.get("blocks") or {}).items()}
    print(f"{tag:38s} n={r['n']:5d} diff={r['diff']:+.4f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p']:.3f} "
          f"H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {r['verdict']:12s} "
          f"5050={d5:+.4f} ovl={r['ctrl_overlap']:.3f} blocks={bl}", flush=True)
    return r

m1 = cl.load_m1()
base = orig.detect(m1)
r = run("baseline (orig detect)", base)
tr = r["_trades"]; tr = tr.merge(base.reset_index().rename(columns={"index": "ev_id"})[["ev_id", "branch", "side"]], on="ev_id", how="left")
tr["d"] = tr["net_R"] - tr["ctrl_mean_R"]
tr["yr"] = tr["decision_time"].dt.year
print(tr.groupby("branch")["d"].agg(["count", "mean"]))
print(tr.groupby("yr")["d"].agg(["count", "mean", "sum"]).round(3))
# concentration: drop best year
for b in (1, 2, 3):
    run(f"branch {b} only", base[base.branch == b].reset_index(drop=True))
run("ctrl_tod_tol 30", base, ctrl_tod_tol_min=30)
run("hold_basis bars", base, hold_basis="bars")
run("max_hold 10h", base, max_hold="10h")
run("max_hold 60min", base, max_hold="60min")
for K in (2, 4, 5):
    run(f"K={K}", detect_v(m1, K=K))
run("TF 5m (hold 50min)", detect_v(m1, TF="5min"), max_hold="50min")
run("TF 5m (hold 150min)", detect_v(m1, TF="5min"))
run("TF 1h (hold 10h)", detect_v(m1, TF="1h"), max_hold="10h")
run("day roll midnight NY", detect_v(m1, day_open_hour=0))
run("branch3 premium/discount refinement", detect_v(m1, pd_filter=True))
run("4H levels forex grid", detect_v(m1, level="4h", grid4h="forex"))
run("4H levels futures grid", detect_v(m1, level="4h", grid4h="futures"))
