"""Independent re-implementation of breaker-block reading a, from the YAML.
Variants: zone='run' (contiguous opposing-close series at L1), 'all' (every opposing-close
candle between H1 and L1); l1='min' (lowest low between H1,H2) or 'swing' (a confirmed swing low);
hh='higher' (true breaker) or 'lower' (placebo: H2 < H1, no sweep)."""
import os, sys, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

MIN = np.int64(60_000_000_000)

def fractals(h, l, k=2):
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(k, n - k):
        nb = np.r_[i-k:i, i+1:i+k+1]
        sh[i] = h[i] > h[nb].max()
        sl[i] = l[i] < l[nb].min()
    return sh, sl

def detect(m1, zone="run", l1mode="min", hh="higher", ll_wait=40, rt_wait=20):
    b = cl.build_bars(m1, "15min")
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).as_unit("ns").asi8
    mt = pd.DatetimeIndex(m1.index).as_unit("ns").asi8
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    n = len(h)
    sh, sl = fractals(h, l)
    out = []
    for bear in (True, False):
        # work in "bearish" coordinates by negating prices for bullish
        sg = 1.0 if bear else -1.0
        H = h if bear else -l; L = l if bear else -h
        O, C = sg * o, sg * c
        piv = np.flatnonzero(sh if bear else sl)
        lowpiv = sl if bear else sh
        for i1, i2 in zip(piv[:-1], piv[1:]):
            if i2 - i1 < 2: continue
            if hh == "higher" and not H[i2] > H[i1]: continue
            if hh == "lower" and not H[i2] < H[i1]: continue
            e = i1 + 1 + int(np.argmin(L[i1+1:i2]))
            if l1mode == "swing" and not lowpiv[e]: continue
            L1 = L[e]
            down = C < O   # opposing close in bearish coords (down-close for bear, up-close for bull)
            if zone == "run":
                cand = [j for j in range(max(i1+1, e-2), e+1) if down[j]]
                if not cand: continue
                en = cand[-1]; s = en
                while s - 1 > i1 and down[s-1] and en - s + 1 < 10: s -= 1
                idx = np.arange(s, en+1)
            else:
                idx = np.array([j for j in range(i1+1, e+1) if down[j]])
                if len(idx) == 0: continue
            edge = np.minimum(O[idx], C[idx]).min()    # body bottom (bearish coords)
            stop = H[idx].max()
            k = -1
            for j in range(i2+1, min(n, i2+1+ll_wait)):
                if H[j] > H[i2]: break
                if C[j] < L1: k = j; break
            if k < 0: continue
            arm = max(k, i2+2)
            if arm >= n: continue
            if H[i2+1:arm+1].max() > H[i2]: continue
            if arm > k and H[k+1:arm+1].max() >= edge: continue
            a0 = np.searchsorted(mt, ct[arm]); a1 = np.searchsorted(mt, ct[arm] + rt_wait*15*MIN)
            MH = mh[a0:a1] if bear else -ml[a0:a1]
            hit = np.flatnonzero(MH >= edge)
            if len(hit) == 0: continue
            jj = a0 + hit[0]
            if (mh[jj] if bear else -ml[jj]) >= stop: continue
            out.append((mt[jj] + MIN, -1 if bear else 1, sg * stop))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if not out: return pd.DataFrame(columns=cols)
    df = pd.DataFrame(out, columns=["t", "direction", "stop_px"]).drop_duplicates(["t", "direction"]).sort_values(["t","direction"])
    dt = pd.DatetimeIndex(df["t"].to_numpy()).tz_localize("UTC")
    return pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": df["direction"].to_numpy(),
                         "stop_px": df["stop_px"].to_numpy(), "rr": 2.0}).reset_index(drop=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    variants = [dict(), dict(l1mode="swing"), dict(zone="all"), dict(hh="lower")]
    rows = {}
    for v in variants:
        ev = detect(m1, **v)
        name = json.dumps(v) or "base"
        if not v:
            ev.to_pickle("ev_indep.pkl")
            probe = cl.probe_lookahead(lambda x: detect(x), ev, lookback="20D")
            print("probe", probe.get("passed"), probe.get("failures"))
        r = cl.trade_test(ev, max_hold="5h", ctrl_tod_tol_min=30)
        rows[name] = {k: r.get(k) for k in ("n","diff","ci_lo","ci_hi","p","verdict")}
        rows[name]["H1"] = r["halves"]["H1"]["diff"]; rows[name]["H2"] = r["halves"]["H2"]["diff"]
        print(name, rows[name], flush=True)
    json.dump(rows, open("indep_out.json", "w"), indent=1, default=str)
