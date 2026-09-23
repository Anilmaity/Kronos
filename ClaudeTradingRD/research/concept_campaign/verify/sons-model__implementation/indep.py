"""Independent re-implementation of sons-model from the YAML (verification only; never writes results)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl

H12 = pd.Timedelta(hours=12).value; H72 = pd.Timedelta(hours=72).value
W30 = pd.Timedelta(minutes=30).value; ONE = pd.Timedelta(minutes=1).value

def mybars(m1, tf):
    g = m1.resample(tf, label="left", closed="left")
    b = g.agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    b["ct"] = b.index + pd.Timedelta(tf)
    return b

def fract(h, l):
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:])
    sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:])
    return sh, sl

def first_take(H, L, sh, sl):
    """index of first later bar (>= i+2) whose high >= H[i] (swing high) / low <= L[i]."""
    n = len(H); th = np.full(n, n, np.int64); tl = np.full(n, n, np.int64)
    for i in np.flatnonzero(sh):
        j = np.flatnonzero(H[i + 2:] >= H[i]); th[i] = i + 2 + j[0] if len(j) else n
    for i in np.flatnonzero(sl):
        j = np.flatnonzero(L[i + 2:] <= L[i]); tl[i] = i + 2 + j[0] if len(j) else n
    return th, tl

def first_take_strict(H, L, sh, sl):
    n = len(H); th = np.full(n, n, np.int64); tl = np.full(n, n, np.int64)
    for i in np.flatnonzero(sh):
        j = np.flatnonzero(H[i + 2:] > H[i]); th[i] = i + 2 + j[0] if len(j) else n
    for i in np.flatnonzero(sl):
        j = np.flatnonzero(L[i + 2:] < L[i]); tl[i] = i + 2 + j[0] if len(j) else n
    return th, tl

def detect(m1):
    b15 = mybars(m1, "15min"); b1 = mybars(m1, "1h")
    s15 = b15.index.asi8; c15 = pd.DatetimeIndex(b15.ct).asi8
    O, H, L, C = (b15[k].to_numpy() for k in ("open", "high", "low", "close"))
    s1 = b1.index.asi8; c1 = pd.DatetimeIndex(b1.ct).asi8
    H1, L1 = b1.high.to_numpy(), b1.low.to_numpy()
    sh, sl = fract(H, L); sh1, sl1 = fract(H1, L1)
    # raid: strict exceed; draw untaken: a touch (>=) counts as taken
    rh, rl = first_take_strict(H, L, sh, sl)
    dh, dl = first_take(H, L, sh, sl)
    mt = m1.index.asi8; mh = m1.high.to_numpy(); ml = m1.low.to_numpy()
    # draw "taken" for 1h swings measured on M1 highs after the 1h swing bar closes
    def taken_by(t_from, t_to, lvl, high):
        a = np.searchsorted(mt, t_from); z = np.searchsorted(mt, t_to)
        if z <= a: return False
        return (mh[a:z].max() >= lvl) if high else (ml[a:z].min() <= lvl)
    sw1_hi = np.flatnonzero(sh1); sw1_lo = np.flatnonzero(sl1)
    sw15_hi = np.flatnonzero(sh); sw15_lo = np.flatnonzero(sl)

    def draw_side(t, px):
        def near(sw, S, CT, X, lb, high):
            best = np.nan
            ok = sw[(sw + 1 < len(CT))]
            ok = ok[(CT[np.minimum(ok + 1, len(CT) - 1)] <= t) & (S[ok] >= t - lb)]
            for i in ok[::-1]:
                lvl = X[i]
                if high and lvl > px and not taken_by(CT[i], t, lvl, True):
                    best = lvl if np.isnan(best) else min(best, lvl)
                if (not high) and lvl < px and not taken_by(CT[i], t, lvl, False):
                    best = lvl if np.isnan(best) else max(best, lvl)
            return best
        up = near(sw1_hi, s1, c1, H1, H72, True); dn = near(sw1_lo, s1, c1, L1, H72, False)
        if np.isnan(up) and np.isnan(dn):
            up = near(sw15_hi, s15, c15, H, H12, True); dn = near(sw15_lo, s15, c15, L, H12, False)
        if np.isnan(up) and np.isnan(dn): return 0
        if np.isnan(dn): return 1
        if np.isnan(up): return -1
        return 1 if up - px <= px - dn else -1

    # raids: for each bar r, swings j with j<=r-2, s15[j] >= s15[r]-12h, first strict take == r
    raids = {}
    for j in sw15_lo:
        r = rl[j]
        if r < len(H) and s15[j] >= s15[r] - H12:
            raids.setdefault((r, 1), []).append(L[j])
    for j in sw15_hi:
        r = rh[j]
        if r < len(H) and s15[j] >= s15[r] - H12:
            raids.setdefault((r, -1), []).append(H[j])
    rows = []
    for (r0, d) in sorted(raids):
        lvl = min(raids[(r0, d)]) if d == 1 else max(raids[(r0, d)])
        for r in range(r0, min(r0 + 3, len(H))):
            ext = L[r0:r + 1].min() if d == 1 else H[r0:r + 1].max()
            if (d == 1 and C[r] > lvl and C[r] > O[r]) or (d == -1 and C[r] < lvl and C[r] < O[r]):
                t0 = c15[r]
                if draw_side(t0, C[r]) == d:
                    e = entry(t0, d, ext, mt, mh, ml)
                    if e is not None: rows.append((e, d, ext))
                break
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px"])
    out["decision_time"] = pd.to_datetime(out.decision_time, utc=True)
    out["available_at"] = out.decision_time; out["rr"] = 1.0
    out = out.sort_values("decision_time", kind="stable").drop_duplicates("decision_time")
    return out[["decision_time", "available_at", "direction", "stop_px", "rr"]].reset_index(drop=True)

def entry(t0, d, stop, mt, mh, ml):
    a = np.searchsorted(mt, t0); z = np.searchsorted(mt, t0 + W30)
    for k in range(a + 2, min(z, len(mt))):
        if d == 1 and ml[k] > mh[k - 2]: top = ml[k]
        elif d == -1 and mh[k] < ml[k - 2]: top = mh[k]
        else: continue
        z2 = np.searchsorted(mt, mt[k] + ONE + W30)
        for u in range(k + 1, min(z2, len(mt))):
            if (d == 1 and ml[u] <= stop) or (d == -1 and mh[u] >= stop): return None
            if (d == 1 and ml[u] <= top) or (d == -1 and mh[u] >= top): return mt[u] + ONE
        return None
    return None

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1)
    ev.to_parquet("indep_events.parquet")
    orig = pd.read_parquet("orig_events.parquet")
    print("indep", len(ev), "orig", len(orig))
    j = orig.merge(ev, on=["decision_time", "direction"], how="outer", indicator=True, suffixes=("_o", "_i"))
    print(j._merge.value_counts())
    both = j[j._merge == "both"]; print("stop mismatch", (np.abs(both.stop_px_o - both.stop_px_i) > 1e-9).sum())
    res = cl.trade_test(ev, max_hold="150min")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "verdict", "verdict_detail"): print(k, res[k])
    print("ctrl", res["control"]["avg_R"], "H1", res["halves"]["H1"]["diff"], "H2", res["halves"]["H2"]["diff"])
