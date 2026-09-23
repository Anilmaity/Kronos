"""Independent re-implementation of order-block reading b (series_open validation)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

L = R = 2; MAXRUN = 10; MAXWAIT = 3; WAIT_H = 24; RR = 2.0

def detect(m1, touch_mode="next_open", require_raid=True):
    b = cl.build_bars(m1, "1h")
    o, h, l, c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    n = len(b)
    mt = m1.index.tz_convert("UTC").as_unit("ns").asi8
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    # swings
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(L, n - R):
        sh[i] = h[i] > h[i-L:i].max() and h[i] >= h[i+1:i+1+R].max()
        sl[i] = l[i] < l[i-L:i].min() and l[i] <= l[i+1:i+1+R].min()
    rows = []
    for bull in (True, False):
        piv = np.flatnonzero(sl if bull else sh)
        opp = (c < o) if bull else (c > o)       # opposing close
        for x in piv:
            # raid: last swing confirmed (piv+R) at or before x-1
            if require_raid:
                prev = piv[piv + R <= x - 1]
                if len(prev) == 0: continue
                p = prev[-1]
                if bull and not (l[x] < l[p]): continue
                if (not bull) and not (h[x] > h[p]): continue
            # run: ending at x or within 2 bars before
            e = None
            for k in (x, x-1, x-2):
                if k >= 0 and opp[k]:
                    e = k; break
            if e is None: continue
            s = e
            while s > 0 and opp[s-1] and (e - s + 1) < MAXRUN: s -= 1
            lvl = o[s]; ext = l[x] if bull else h[x]
            first = max(e, x + R) + 1
            cp = -1
            for j in range(first, min(n, first + MAXWAIT)):
                if (c[j] > lvl) if bull else (c[j] < lvl):
                    cp = j; break
            if cp < 0: continue
            if not ((ext < lvl) if bull else (ext > lvl)): continue
            t0 = ct[cp]; t1 = ct[min(cp + WAIT_H, n - 1)]
            i0 = np.searchsorted(mt, t0, "left"); i1 = np.searchsorted(mt, t1, "left")
            if i1 <= i0: continue
            if bull:
                hit = ml[i0:i1] <= lvl; bad = ml[i0:i1] <= ext
            else:
                hit = mh[i0:i1] >= lvl; bad = mh[i0:i1] >= ext
            anyv = hit | bad
            if not anyv.any(): continue
            k = int(np.argmax(anyv))
            if bad[k]: continue
            j = i0 + k
            rows.append((mt[j] + 60_000_000_000, 1 if bull else -1, ext))
    out = pd.DataFrame(rows, columns=["t","direction","stop_px"])
    t = pd.DatetimeIndex(pd.to_datetime(out.t.to_numpy(np.int64), utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out.direction.to_numpy(),
                         "stop_px": out.stop_px.to_numpy(), "rr": RR}).sort_values(
                         ["decision_time","direction"], kind="stable").reset_index(drop=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1)
    ev.to_parquet("ev_indep_b.parquet")
    orig = pd.read_parquet("ev_orig_b.parquet")
    print("indep", len(ev), "orig", len(orig))
    key = lambda d: set(zip(d.decision_time.astype("int64"), d.direction, d.stop_px.round(4)))
    a, o_ = key(ev), key(orig)
    print("common", len(a & o_), "only_indep", len(a - o_), "only_orig", len(o_ - a))
    res = cl.trade_test(ev, max_hold="10h")
    print({k: res.get(k) for k in ("verdict","verdict_detail","n","diff","ci_lo","ci_hi","p")})
    print(res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"], res["ties"], res["exposure_bars"], res["control"]["avg_R"], res["avg_R"])
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"], probe.get("failures"))
