"""Independent re-implementation: 1h series_open CISD (fractal 2/2, max_wait 3) + §4.1 POI gate,
written from the YAML/method-spec text without importing detectors/*."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

def fractals(h, l, L=2, R=2):
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(L, n - R):
        if h[i] > h[i-L:i].max() and h[i] >= h[i+1:i+1+R].max(): sh[i] = True
        if l[i] < l[i-L:i].min() and l[i] <= l[i+1:i+1+R].min(): sl[i] = True
    return sh, sl

def my_gate(o, h, l, c, e, bull, upto, LB=40, variant="spec"):
    """Evaluate the POI gate for extreme at e using bars [0, upto] only."""
    lo = max(0, e - LB)
    # range start: last opposing swing (swing high for bull) confirmed by e (i+2 <= e)
    s = lo
    for i in range(e - 2, lo + 1, -1):
        if i - 2 < lo: break
        if bull:
            if h[i] > max(h[i-1], h[i-2]) and h[i] >= max(h[i+1], h[i+2]): s = i; break
        else:
            if l[i] < min(l[i-1], l[i-2]) and l[i] <= min(l[i+1], l[i+2]): s = i; break
    if e <= s: 
        return False
    # FVGs stamped at k in [s, e]
    fv = []
    for k in range(max(s, 2), e + 1):
        if k < s: continue
        bu = l[k] > h[k-2]; be = h[k] < l[k-2]
        if bu: fv.append((h[k-2], l[k], k, "bull"))
        if be: fv.append((h[k], l[k-2], k, "bear"))
    if variant == "no_extreme_bar_fvg":
        fv = [g for g in fv if g[2] < e]
    if variant == "aligned":
        fv = [g for g in fv if g[3] == ("bull" if bull else "bear")]
    ext = l[e] if bull else h[e]
    fv_tag = [(ext <= g[1]) if bull else (ext >= g[0]) for g in fv]
    # swings in [s, e) confirmed before e (p+2 < e); window from s-2
    sw_tag = []
    for p in range(s, e):
        if p + 2 >= e or p - 2 < max(0, s - 2): continue
        if bull:
            if l[p] < min(l[p-1], l[p-2]) and l[p] <= min(l[p+1], l[p+2]): sw_tag.append(ext < l[p])
        else:
            if h[p] > max(h[p-1], h[p-2]) and h[p] >= max(h[p+1], h[p+2]): sw_tag.append(ext > h[p])
    if fv and sw_tag: return any(fv_tag) and any(sw_tag)
    if fv: return any(fv_tag)
    if sw_tag: return any(sw_tag)
    if variant == "no_cisd_branch": return False
    # CISD-level branch: opposing series ending at/before e, within (s, e]
    q = (lambda k: c[k] < o[k]) if bull else (lambda k: c[k] > o[k])
    j = e
    while j > s and not q(j): j -= 1
    if j <= s or not q(j): return False
    i0 = j
    while i0 > s and q(i0 - 1) and (j - i0 + 1) < 10: i0 -= 1
    bh = max(max(o[k], c[k]) for k in range(i0, j + 1)); bl = min(min(o[k], c[k]) for k in range(i0, j + 1))
    mid = (bh + bl) / 2
    fwd = c[j+1:min(upto + 1, j + 6)]
    return bool((fwd > mid).any()) if bull else bool((fwd < mid).any())

def detect(m1, variants=("spec",)):
    b = cl.build_bars(m1, "1h")
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(b); sh, sl = fractals(h, l)
    rows = []
    for bull, flag in ((True, sl), (False, sh)):
        q = (lambda k: c[k] < o[k]) if bull else (lambda k: c[k] > o[k])
        for pos in np.flatnonzero(flag):
            end = pos; ok = True
            while end > 0 and not q(end):
                end -= 1
                if pos - end > 2: ok = False; break
            if not ok or not q(end): continue
            st = end
            while st > 0 and q(st - 1) and (end - st + 1) < 10: st -= 1
            lvl = o[st]
            begin = max(end, pos + 2) + 1
            for j in range(begin, min(n, begin + 3)):
                if (c[j] > lvl) if bull else (c[j] < lvl):
                    r = {"cpos": j, "epos": pos, "dir": 1 if bull else -1,
                         "stop_px": l[pos] if bull else h[pos]}
                    for v in variants:
                        r["g_" + v] = my_gate(o, h, l, c, pos, bull, j, variant=v)
                    rows.append(r); break
    df = pd.DataFrame(rows).sort_values("cpos", kind="stable").reset_index(drop=True)
    df["decision_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[df.cpos.to_numpy()])
    last_ok = m1.index[-1] + pd.Timedelta("1min")
    df = df[df.decision_time <= last_ok].reset_index(drop=True)
    df["available_at"] = df["decision_time"]; df["direction"] = df["dir"]; df["rr"] = 2.0
    return df

if __name__ == "__main__":
    V = ("spec", "no_extreme_bar_fvg", "aligned", "no_cisd_branch")
    ev = detect(cl.load_m1(), V)
    ev.to_pickle("indep_events.pkl")
    print(len(ev), {v: ev["g_" + v].mean() for v in V})
    orig = pd.read_pickle("orig_events.pkl")
    m = orig.merge(ev, on=["decision_time", "direction", "stop_px"], how="outer", indicator=True)
    print(m["_merge"].value_counts())
    both = m[m._merge == "both"]
    print("gate agreement", (both.poi_ok.astype(bool) == both.g_spec.astype(bool)).mean())
