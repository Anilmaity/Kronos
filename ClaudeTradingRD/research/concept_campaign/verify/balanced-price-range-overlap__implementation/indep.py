"""Independent re-implementation of BPR reading a from the concept YAML (not reusing the
original detect or detectors.primitives)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl

def detect(m1, tf="15min", pair=20, window="24h", skip_stop_touch=True, contiguous=False):
    b = cl.build_bars(m1, tf)
    H, L = b.high.values, b.low.values
    ct = b.close_time.values.astype("datetime64[ns]").astype(np.int64)
    st = b.index.values.astype("datetime64[ns]").astype(np.int64)
    n = len(b)
    gaps = []  # (idx, dir, lo, hi)
    tfns = pd.Timedelta(tf).value
    for i in range(2, n):
        if contiguous and (st[i] - st[i-2] != 2*tfns):
            continue
        if L[i] > H[i-2]:
            gaps.append((i, 1, H[i-2], L[i]))
        elif H[i] < L[i-2]:
            gaps.append((i, -1, H[i], L[i-2]))
    mt = m1.index.values.astype("datetime64[ns]").astype(np.int64)
    mh, ml = m1.high.values, m1.low.values
    W = pd.Timedelta(window).value
    rows = []
    for k, (j, d, lo2, hi2) in enumerate(gaps):
        partner = None
        for kk in range(k-1, -1, -1):
            i, d1, lo1, hi1 = gaps[kk]
            if j - i > pair:
                break
            if d1 == -d and max(lo1, lo2) < min(hi1, hi2):
                partner = gaps[kk]; break
        if partner is None:
            continue
        i = partner[0]
        zlo, zhi = max(partner[2], lo2), min(partner[3], hi2)
        seg = slice(max(i-2, 0), j+1)
        stop = L[seg].min() if d == 1 else H[seg].max()
        a, e = np.searchsorted(mt, [ct[j], ct[j] + W])
        if d == 1:
            hit = np.flatnonzero(ml[a:e] <= zhi)
        else:
            hit = np.flatnonzero(mh[a:e] >= zlo)
        if not len(hit):
            continue
        t = a + hit[0]
        if skip_stop_touch and ((ml[t] <= stop) if d == 1 else (mh[t] >= stop)):
            continue
        rows.append((mt[t] + 60_000_000_000, d, stop, ct[j]))
    o = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "bpr_id"])
    dt = pd.to_datetime(o.t, utc=True)
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": o.direction,
                       "stop_px": o.stop_px, "rr": 2.0, "bpr_id": o.bpr_id})
    return ev.sort_values(["decision_time", "bpr_id"]).reset_index(drop=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1)
    orig = pd.read_parquet("orig_events.parquet")
    print("indep n", len(ev), "orig n", len(orig))
    mg = ev.merge(orig, on=["decision_time", "bpr_id"], how="outer", suffixes=("", "_o"), indicator=True)
    print(mg._merge.value_counts())
    both = mg[mg._merge == "both"]
    print("dir mismatch", (both.direction != both.direction_o).sum(), "stop mismatch", (~np.isclose(both.stop_px, both.stop_px_o)).sum())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"), probe.get("failures"))
    def run(tag, e, **kw):
        r = cl.trade_test(e, max_hold="150min", cluster="bpr_id", **kw)
        h = r["halves"]
        print(f"{tag:28s} n={r['n']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] H1={h['H1']['diff']:+.4f} H2={h['H2']['diff']:+.4f} {r['verdict']} exp={r['exposure_bars']['real_mean']:.0f}/{r['exposure_bars']['control_mean']:.0f}")
    run("indep base", ev)
    run("indep ctrl_tod30", ev, ctrl_tod_tol_min=30)
    run("indep hold bars", ev, hold_basis="bars")
    run("indep no stop-skip", detect(m1, skip_stop_touch=False))
    run("indep contiguous", detect(m1, contiguous=True))
    run("indep pair10", detect(m1, pair=10))
    run("indep pair40", detect(m1, pair=40))
    run("indep window8h", detect(m1, window="8h"))
