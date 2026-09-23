"""Placebo: same fill mechanics (limit level at the same distance below price, same stop
distance, same 150-M1 window, same 'M1 close above stop' filter, decide at M1 close, enter
next open) but at a RANDOM 15m bar close +/-30 days, same direction. If this also beats
the matched random control, the edge is the fill mechanics, not the propulsion block."""
import sys, importlib.util
spec = importlib.util.spec_from_file_location("pb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/propulsion-block.py")
pb = importlib.util.module_from_spec(spec); spec.loader.exec_module(pb)
cl, np, pd = pb.cl, pb.np, pb.pd
m1 = cl.load_m1()
b = cl.build_bars(m1, "15min")
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"]))
mo, mh, ml, mc = (m1[k].to_numpy(float) for k in ("open","high","low","close"))
mt = cl.data.utc_ns(m1.index)
# real PB rows with their PB close index
base = []
for d, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
    for j2, opx, lowpx, bodyb in pb._bull_blocks(*arrs):
        if not bodyb < opx: continue
        i0 = int(np.searchsorted(mt, ct[j2], side="left"))
        if i0 >= len(mt): continue
        p0 = mo[i0] * d
        base.append((j2, d, p0 - opx, opx - bodyb))
base = pd.DataFrame(base, columns=["j2","d","lvl_dist","stop_dist"])
print("PB rows", len(base), base[["lvl_dist","stop_dist"]].describe().T)

def fill(j, d, lvl_dist, stop_dist):
    i0 = int(np.searchsorted(mt, ct[j], side="left")); i1 = min(len(mt), i0 + 150)
    if i0 >= i1: return None
    p0 = mo[i0]*d; opx = p0 - lvl_dist; stop = opx - stop_dist
    seg = ml[i0:i1] if d > 0 else -mh[i0:i1]
    hit = np.flatnonzero(seg <= opx)
    if not len(hit): return None
    k = i0 + int(hit[0]); ck = mc[k]*d
    if ck <= stop: return None
    return (mt[k], d, d*stop)

def frame(rows):
    r = pd.DataFrame([x for x in rows if x is not None], columns=["tk","d","stop"])
    dt = cl.data.from_ns(r.tk.to_numpy()) + pd.Timedelta(minutes=1)
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": r.d.astype(int).to_numpy(),
                       "stop_px": r.stop.to_numpy(float), "rr": 2.0})
    return ev.drop_duplicates(["decision_time","direction"]).sort_values(["decision_time","direction"]).reset_index(drop=True)

real = frame([fill(*x) for x in base[["j2","d","lvl_dist","stop_dist"]].itertuples(index=False)])
print("real rebuilt", len(real))
rng = np.random.default_rng(11)
ctn = ct
out = {}
for rep in range(3, 15):
    rows = []
    for j, d, ld, sd in base[["j2","d","lvl_dist","stop_dist"]].itertuples(index=False):
        lo = np.searchsorted(ctn, ctn[j] - np.int64(30*86400*10**9)); hi = np.searchsorted(ctn, ctn[j] + np.int64(30*86400*10**9))
        jj = int(rng.integers(lo, max(lo+1, hi)))
        jj = min(jj, len(ctn)-1)
        rows.append(fill(jj, d, ld, sd))
    ev = frame(rows)
    res = cl.trade_test(ev, max_hold="150min", n_boot=500)
    print("placebo rep", rep, len(ev), "diff %.4f [%.4f, %.4f]" % (res["diff"], res["ci_lo"], res["ci_hi"]), res["verdict"], res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"], "avgR", res["avg_R"], "ctrl", res["control"]["avg_R"])
