"""Independent re-implementation of intraday-reversal (no concept_lab detectors/helpers used for
events, outcomes or null; only load_m1 for the certified data)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
m1 = cl.load_m1()
idx = m1.index; ny = idx.tz_convert("America/New_York")
O,H,L,C = (m1[k].to_numpy(float) for k in ("open","high","low","close"))
tn = idx.as_unit("ns").asi8
# trading day: 18:00 NY roll
nyn = ny.tz_localize(None)
tday = (nyn + pd.Timedelta(hours=6)).normalize().as_unit("ns").asi8
# 4H forex grid bucket start (17,21,01,05,09,13 NY)  -> bucket index = floor(((h-17)%24)/4) within tday
hrs = ny.hour.to_numpy()
b4 = ((hrs - 17) % 24) // 4
key4 = (tday // 10**9) * 10 + b4
key1 = (nyn.floor("h")).as_unit("ns").asi8
def agg(key):
    ch = np.r_[0, np.flatnonzero(key[1:] != key[:-1]) + 1]
    en = np.r_[ch[1:], len(key)]
    return ch, en
def bars(key):
    s, e = agg(key)
    return pd.DataFrame({"s": s, "e": e, "o": O[s], "h": np.maximum.reduceat(H, s), "l": np.minimum.reduceat(L, s),
                         "c": C[e-1], "key": key[s], "td": tday[s]})
B4 = bars(key4); B1 = bars(key1)
# 4H close time: bucket start (NY) + 4h -> UTC
bstart_ny = pd.to_datetime(B4.td.values) - pd.Timedelta(hours=6) + pd.to_timedelta(B4.key.values % 10 * 4 - 1, unit="h")  # tday midnight - 6h = 18:00 prev; bucket0 starts 17:00
# careful: tday normalize is midnight of (ny+6h); day starts at 18:00 NY of previous calendar day; bucket0 = 17:00-21:00
bstart_ny = pd.to_datetime(B4.td.values) - pd.Timedelta(hours=7) + pd.to_timedelta((B4.key.values % 10) * 4, unit="h")
close_ny = (bstart_ny + pd.Timedelta(hours=4))
close_utc = close_ny.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
B4["close_utc"] = close_utc
B4["close_h"] = close_ny.hour
# 1H bars mapped to 4H bar via their first M1 index
b1_of_m1 = np.repeat(np.arange(len(B1)), (B1.e - B1.s).values)
first1 = b1_of_m1[B4.s.values]; last1 = b1_of_m1[B4.e.values - 1]
o1,h1,l1,c1 = B1.o.values,B1.h.values,B1.l.values,B1.c.values

def cisd(a, b, bull, rule="series_open"):
    if b - a + 1 < 2: return False
    seg = np.arange(a, b + 1)
    e = seg[np.argmin(l1[seg])] if bull else seg[np.argmax(h1[seg])]
    down = (lambda k: c1[k] < o1[k]) if bull else (lambda k: c1[k] > o1[k])
    if rule == "series_open":
        k = e
        while k >= a and not down(k) and e - k <= 2: k -= 1
        if k < a or not down(k): return False
        st = k
        while st - 1 >= a and down(st - 1) and k - st + 1 < 10: st -= 1
        lvl = o1[st]
    else:  # extreme-bar high/low reading: close beyond the extreme 1H bar's opposite end
        lvl = h1[e] if bull else l1[e]
    for j in range(e + 1, b + 1):
        if (c1[j] > lvl) if bull else (c1[j] < lvl): return True
    return False

def events(require_c2=True, require_cisd=True, require_dayext=True, rule="series_open"):
    o4,h4,l4,c4,td = B4.o.values,B4.h.values,B4.l.values,B4.c.values,B4.td.values
    rows = []
    for i in range(1, len(B4)):
        if B4.close_h.values[i] == 17 or pd.isna(close_utc[i]): continue
        for bull in (True, False):
            if require_c2:
                if bull and not (l4[i] < l4[i-1] and c4[i] > l4[i-1] and not (h4[i] > h4[i-1] and c4[i] < h4[i-1])): continue
                if (not bull) and not (h4[i] > h4[i-1] and c4[i] < h4[i-1] and not (l4[i] < l4[i-1] and c4[i] > l4[i-1])): continue
            if require_cisd and not cisd(first1[i], last1[i], bull, rule): continue
            # day extreme so far, straight from M1 of this trading day up to 4H close
            ds = np.searchsorted(tday, td[i]); de = B4.e.values[i]
            lv = l4[i] if bull else h4[i]
            if require_dayext:
                if bull and L[ds:de].min() < lv: continue
                if (not bull) and H[ds:de].max() > lv: continue
            rows.append((i, close_utc[i], 1 if bull else -1, lv))
    return pd.DataFrame(rows, columns=["i", "t", "dir", "lvl"])

day_end = np.r_[np.flatnonzero(tday[1:] != tday[:-1]) + 1, len(tday)]
def outcome(t_ns, lvl, bull, nb=None):
    p = np.searchsorted(tn, t_ns)
    if p >= len(tn): return np.nan, 0, np.nan
    if nb is None: nb = day_end[np.searchsorted(day_end, p, side="right")] - p
    q = min(p + nb, len(tn))
    if q <= p: return 1.0, nb, O[p]
    held = (L[p:q].min() > lvl) if bull else (H[p:q].max() < lvl)
    return float(held), nb, O[p]

rng = np.random.default_rng(12345)
NYtz = "America/New_York"
def run(ev, reps=5, label=""):
    t_ns = pd.DatetimeIndex(ev.t).asi8
    ob = np.zeros(len(ev)); nulls = np.full((len(ev), reps), np.nan)
    for r, (tt, lv, d) in enumerate(zip(t_ns, ev.lvl.values, ev.dir.values)):
        h, nb, px = outcome(tt, lv, d > 0)
        ob[r] = h
        dist = lv - px
        loc = pd.Timestamp(tt, tz="UTC").tz_convert(NYtz).tz_localize(None)
        got = 0; tries = 0
        while got < reps and tries < 300:
            tries += 1
            kd = int(rng.integers(-30, 31))
            if kd == 0: continue
            cand = (loc + pd.Timedelta(days=kd))
            try: cu = cand.tz_localize(NYtz).tz_convert("UTC").value
            except Exception: continue
            p = np.searchsorted(tn, cu)
            if p >= len(tn) or tn[p] != cu: continue
            hh, _, px2 = outcome(cu, 0, d > 0, nb=nb) if False else (None, None, O[p])
            q = min(p + nb, len(tn))
            lv2 = px2 + dist
            nulls[r, got] = float((L[p:q].min() > lv2) if d > 0 else (H[p:q].max() < lv2)) if q > p else 1.0
            got += 1
    nm = np.nanmean(nulls, 1)
    ok = np.isfinite(ob) & np.isfinite(nm)
    ob, nm, tt = ob[ok], nm[ok], pd.DatetimeIndex(ev.t)[ok]
    diff = ob.mean() - nm.mean()
    # day-block bootstrap
    days = pd.factorize(tt.tz_convert(NYtz).tz_localize(None).floor("D"))[0]
    dd = pd.DataFrame({"d": days, "x": ob - nm}).groupby("d").x.agg(["sum", "count"])
    s, c = dd["sum"].values, dd["count"].values
    bs = []
    for _ in range(2000):
        k = rng.integers(0, len(s), len(s)); bs.append(s[k].sum() / c[k].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    h1 = tt < pd.Timestamp("2021-01-01", tz="UTC")
    print(f"{label:40s} n={len(ob):5d} obs={ob.mean():.4f} null={nm.mean():.4f} diff={diff:+.4f} [{lo:+.4f},{hi:+.4f}] "
          f"H1={ob[h1].mean()-nm[h1].mean():+.4f} H2={ob[~h1].mean()-nm[~h1].mean():+.4f}")
    return ob, nm, tt

if __name__ == "__main__":
    ev = events(); ev.to_pickle("indep_events.pkl")
    orig = pd.read_pickle("orig_events.pkl")
    a = set(zip(pd.DatetimeIndex(orig.decision_time).asi8, orig.direction)); b = set(zip(pd.DatetimeIndex(ev.t).asi8, ev.dir))
    print("orig", len(a), "indep", len(b), "common", len(a & b))
    run(ev, label="indep: C2+CISD(series_open)+dayext")
    run(events(rule="extreme_bar"), label="indep: C2+CISD(extreme-bar)+dayext")
    run(events(require_cisd=False), label="baseline: C2+dayext (no CISD)")
    run(events(require_c2=False, require_cisd=False), label="baseline: any 4H low=day ext so far")
    run(events(require_dayext=False), label="C2+CISD no dayext")
