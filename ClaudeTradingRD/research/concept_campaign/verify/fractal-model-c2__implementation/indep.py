"""Independent re-implementation of fractal-model-c2 reading a from the concept YAML."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np
m1 = cl.load_m1()[["open", "high", "low", "close"]]
print(m1.index[:3], m1.index.tz)
ny = m1.index.tz_convert("America/New_York")
# 4H forex grid: NY hours 17,21,1,5,9,13 -> floor((ny-1h),4h)+1h
naive = ny.tz_localize(None)
start_ny = (naive - pd.Timedelta(hours=1)).floor("4h") + pd.Timedelta(hours=1)
g = pd.Series(start_ny, index=m1.index)
agg = m1.groupby(start_ny.values).agg(open=("open", "first"), high=("high", "max"),
                                      low=("low", "min"), close=("close", "last"))
agg["n"] = m1.groupby(start_ny.values).size()
agg.index = pd.DatetimeIndex(agg.index)
st_utc = agg.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
en_utc = (agg.index + pd.Timedelta(hours=4)).tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
H = agg.assign(start=st_utc, close_time=en_utc).reset_index(drop=True)
H = H[H.start.notna() & H.close_time.notna() & (H.n >= 60)].reset_index(drop=True)
# 15m bars, UTC-floored
f = m1.groupby(m1.index.floor("15min")).agg(open=("open", "first"), high=("high", "max"),
                                             low=("low", "min"), close=("close", "last"))
fi = f.index.asi8; fo, fh, fl, fc = (f[c].to_numpy() for c in ["open", "high", "low", "close"])

def cisd_inside(a, b, bull):
    """Change of state of delivery inside [a,b): find the C2 extreme on 15m, take the
    run of opposing-close 15m candles that delivered into it (ending at the extreme bar,
    or the bar right before if the extreme bar already closed the other way), level =
    the open of the first candle of that run; confirmed if a LATER 15m close inside C2
    closes through it."""
    if b - a < 3: return False
    lo, hi, op, cl_ = fl[a:b], fh[a:b], fo[a:b], fc[a:b]
    k = int(np.argmin(lo)) if bull else int(np.argmax(hi))
    opp = (cl_ < op) if bull else (cl_ > op)
    e = k
    while e >= 0 and not opp[e] and k - e <= 1:
        e -= 1
    if e < 0 or not opp[e]: return False
    s = e
    while s > 0 and opp[s - 1]: s -= 1
    lvl = op[s]
    later = cl_[e + 1:]
    return bool(np.any(later > lvl) if bull else np.any(later < lvl))

rows = []
O, Hh, L, C = (H[c].to_numpy() for c in ["open", "high", "low", "close"])
for i in range(1, len(H)):
    bull = L[i] < L[i-1] and C[i] > L[i-1] and C[i] > O[i]
    bear = Hh[i] > Hh[i-1] and C[i] < Hh[i-1] and C[i] < O[i]
    if not (bull or bear): continue
    # (both sides possible: an outside candle -- the closing direction picks it)
    a = int(np.searchsorted(fi, H.start[i].value)); b = int(np.searchsorted(fi, H.close_time[i].value))
    conf = cisd_inside(a, b, bull)
    rows.append(dict(decision_time=H.close_time[i], direction=1 if bull else -1,
                     stop_px=L[i] if bull else Hh[i],
                     tgt_max=max(Hh[i-1], Hh[i]) if bull else min(L[i-1], L[i]),
                     tgt_c2=Hh[i] if bull else L[i],
                     tgt_c1=Hh[i-1] if bull else L[i-1], conf=conf, entry_ref=C[i]))
E = pd.DataFrame(rows)
E["available_at"] = E["decision_time"]
E.to_pickle("indep_events.pkl")
print("C2s", len(E), "confirmed", int(E.conf.sum()))
orig = pd.read_pickle("allc2_orig.pkl"); orig = orig[orig.conf & orig.posok]
mine = E[E.conf]
j = pd.merge(orig[["decision_time", "direction"]], mine[["decision_time", "direction"]], how="outer", indicator=True, on=["decision_time", "direction"])
print(j["_merge"].value_counts())
def run(name, e, tcol, **kw):
    x = e[["decision_time", "available_at", "direction", "stop_px"]].assign(target_px=e[tcol].to_numpy()).reset_index(drop=True)
    r = cl.trade_test(x, max_hold="240min", hold_basis="bars", **kw)
    print(f"{name:34s} n={r['n']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} {r['verdict']}", flush=True)
run("indep, target max(C1,C2)", mine, "tgt_max")
run("indep, target C2 far extreme", mine, "tgt_c2")
run("indep, target C1 far extreme", mine[(mine.tgt_c1 - mine.entry_ref) * mine.direction > 0], "tgt_c1")
run("indep, all C2 no CISD, tgt max", E, "tgt_max")
