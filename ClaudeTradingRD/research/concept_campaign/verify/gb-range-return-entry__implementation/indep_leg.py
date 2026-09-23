"""Independent re-implementation of gb-range-return-entry from the concept YAML.
Written without reusing common01a.  Variants via argv."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl

X, XT = 0.41, 0.7475
N, R, D = 4, 1.5, 0.65
DAY = pd.Timedelta("24h")

def flips(b):
    """own structure: fractal 2/2 swings known at j+2 close; break = close beyond latest
    confirmed unbroken swing; flip = break opposite to previous break."""
    h, l, c = b.high.values, b.low.values, b.close.values
    n = len(h)
    out = []
    last_hi = last_lo = None       # index of active swing
    prev_break = 0; prev_break_bar = None
    for i in range(n):
        # breaks at close of i use swings confirmed by close of i-1
        if last_hi is not None and c[i] > h[last_hi]:
            if prev_break == -1:
                st = min(last_hi, prev_break_bar)
                a = st + int(np.argmin(l[st:i+1]))
                out.append((i, 1, a, l[a], h[a:i+1].max()))
            prev_break, last_hi, prev_break_bar = 1, None, i
        if last_lo is not None and c[i] < l[last_lo]:
            if prev_break == 1:
                st = min(last_lo, prev_break_bar)
                a = st + int(np.argmax(h[st:i+1]))
                out.append((i, -1, a, h[a], l[a:i+1].min()))
            prev_break, last_lo, prev_break_bar = -1, None, i
        j = i - 2
        if j >= 2:
            if h[j] > h[j-1] and h[j] > h[j-2] and h[j] >= h[j+1] and h[j] >= h[j+2]:
                last_hi = j
            if l[j] < l[j-1] and l[j] < l[j-2] and l[j] <= l[j+1] and l[j] <= l[j+2]:
                last_lo = j
    return out

def detect(m1, cancel_on_target=False, abs_levels=False):
    b = cl.build_bars(m1, "15min")
    ct = pd.DatetimeIndex(b.close_time)
    H_, L_, C_ = b.high.values, b.low.values, b.close.values
    mt = m1.index; mh = m1.high.values; ml = m1.low.values
    n = len(b); rows = []
    for (fb, d, ab, A, H0) in flips(b):
        # flip coordinates: y = s*price so flip leg is up; bar "high" = s*high (s=1) or s*low (s=-1)
        s = d
        hi = (lambda k: s*H_[k]) if s == 1 else (lambda k: s*L_[k])
        lo = (lambda k: s*L_[k]) if s == 1 else (lambda k: s*H_[k])
        Hy, Ay = s*H0, s*A
        hbar = fb; wick = np.inf; sig = None
        for i in range(fb+1, n):
            if ct[i] > ct[fb] + DAY: break
            if s*C_[i] < Ay: break
            if hi(i) > Hy: Hy, hbar, wick = hi(i), i, np.inf
            lvl = Hy - X*(Hy-Ay)
            if s*C_[i] < lvl and s*C_[i] < wick:
                sig = i; break
            if i > hbar and lo(i) < lvl: wick = min(wick, lo(i))
        if sig is None or sig < N or sig+N-1 >= n: continue
        lvl = Hy - X*(Hy-Ay)
        pre_hi = max(hi(k) for k in range(sig-N, sig)); pre_lo = min(lo(k) for k in range(sig-N, sig))
        w_hi = max(hi(k) for k in range(sig, sig+N)); w_lo = min(lo(k) for k in range(sig, sig+N))
        pr = pre_hi - pre_lo
        if pr <= 0 or w_hi > Hy: continue
        if (w_hi-w_lo)/pr < R or (lvl-w_lo)/pr < D: continue
        tdec = ct[sig+N-1]
        a = mt.searchsorted(tdec, "left"); z = mt.searchsorted(tdec+DAY, "left")
        px = s*lvl; tgt = s*(Hy - XT*(Hy-Ay)); stop = s*Hy
        if s == 1:   # short into range: fill on rise to px
            hit = np.flatnonzero(mh[a:z] >= px)
        else:
            hit = np.flatnonzero(ml[a:z] <= px)
        if not len(hit): continue
        k = a + hit[0]
        if cancel_on_target:
            pre = ml[a:k] if s == 1 else mh[a:k]
            if len(pre) and ((pre <= tgt).any() if s == 1 else (pre >= tgt).any()): continue
        dt = mt[k] + pd.Timedelta("1min")
        rng = Hy - Ay
        row = dict(decision_time=dt, available_at=dt, direction=-d)
        if abs_levels:
            row.update(stop_px=stop, target_px=tgt)
        else:
            row.update(stop_dist=X*rng, target_dist=(XT-X)*rng)
        rows.append(row)
    ev = pd.DataFrame(rows)
    ev["decision_time"] = pd.DatetimeIndex(ev.decision_time).tz_convert("UTC") if ev.decision_time.dt.tz is not None else pd.DatetimeIndex(ev.decision_time).tz_localize("UTC")
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values("decision_time", kind="stable").reset_index(drop=True)

if __name__ == "__main__":
    cot = "cot" in sys.argv; absl = "abs" in sys.argv
    m1 = cl.load_m1()
    ev = detect(m1, cot, absl)
    print("variant cancel_on_target=%s abs=%s n_ev=%d" % (cot, absl, len(ev)))
    ev.to_pickle(f"indepLeg_{int(cot)}{int(absl)}.pkl")
    res = cl.trade_test(ev, max_hold="24h", ctrl_tod_tol_min=30, n_boot=2000)
    for k in ("n","diff","ci_lo","ci_hi","p","verdict","avg_R","win_rate"): print(k, res.get(k))
    print("H1", res["halves"]["H1"]["diff"], "H2", res["halves"]["H2"]["diff"], res["ties"])
