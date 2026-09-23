"""Independent propulsion-block implementation from the YAML (bullish; bearish mirrored).
OB1: down-close run (<=10) ending at/<=2 bars before a 2/2 swing low, closed over (close >
run's first open) within 3 bars after the swing confirms. Retrace: low <= OB1 body top within
20 bars, no close < OB1 body bottom. OB2: the most recent contiguous down-close run (started
after OB1's validation) that has a bar trading into OB1 (low <= top1); a close > its first
open within 20 bars after the retrace = PB. Stop = OB2 lowest body (reading b). Limit at the
PB open: first M1 bar within 150 whose low reaches it, M1 close above stop, decide at its
close, enter next M1 open (harness), 2R, 150min hold."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

def blocks(o, h, l, c, variant):
    n = len(o); down = c < o; out = []; seen = set()
    for i in range(2, n - 2):
        if not (l[i] < l[i-1] and l[i] < l[i-2] and l[i] <= l[i+1] and l[i] <= l[i+2]):
            continue
        e = next((k for k in (i, i-1, i-2) if down[k]), None)
        if e is None: continue
        s = e
        while s - 1 >= 0 and down[s-1] and e - s + 1 < 10: s -= 1
        conf = i + 2
        j1 = next((k for k in range(max(conf, e) + 1, min(n, max(conf, e) + 4)) if c[k] > o[s]), None)
        if j1 is None: continue
        top1 = max(o[s], np.maximum(o[s:e+1], c[s:e+1]).max()); bot1 = np.minimum(o[s:e+1], c[s:e+1]).min()
        t0 = None
        for k in range(j1 + 1, min(n, j1 + 21)):
            if c[k] < bot1: break
            if l[k] <= top1: t0 = k; break
        if t0 is None: continue
        # OB2 tracking
        rs = None; re = None; cand = None  # candidate run (start,end) that traded into OB1
        k = j1 + 1
        while k < min(n, t0 + 21):
            if c[k] < bot1: break
            if down[k]:
                if rs is None or re != k - 1: rs = k
                re = k
                if variant == "touch":
                    if l[rs:re+1].min() <= top1: cand = (rs, re)
                else:  # 'lowest': run ending at the lowest low so far
                    cand = (max(rs, re - 9), re) if l[k] <= l[j1+1:k+1].min() else cand
            if k > t0 and cand is not None and c[k] > o[cand[0]] and k > cand[1]:
                if k not in seen:
                    s2, e2 = cand
                    out.append((k, o[s2], np.minimum(o[s2:e2+1], c[s2:e2+1]).min(), l[s2:e2+1].min()))
                    seen.add(k)
                break
            k += 1
    return out

def detect(m1, stop_kind="body", variant="touch"):
    b = cl.build_bars(m1, "15min")
    o, h, l, c = (b[x].to_numpy(float) for x in ("open","high","low","close"))
    ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"]))
    mh, ml, mc = (m1[x].to_numpy(float) for x in ("high","low","close"))
    mt = cl.data.utc_ns(m1.index)
    rows = []
    for d, arr in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for j, opx, body, low in blocks(*arr, variant):
            stop = body if stop_kind == "body" else low
            if not stop < opx: continue
            i0 = int(np.searchsorted(mt, ct[j])); i1 = min(len(mt), i0 + 150)
            if i0 >= i1: continue
            seg = ml[i0:i1] if d > 0 else -mh[i0:i1]
            hit = np.flatnonzero(seg <= opx)
            if not len(hit): continue
            k = i0 + int(hit[0])
            if (mc[k] if d > 0 else -mc[k]) <= stop: continue
            rows.append((mt[k], d, d * stop))
    r = pd.DataFrame(rows, columns=["tk","d","stop"])
    dt = cl.data.from_ns(r.tk.to_numpy()) + pd.Timedelta(minutes=1)
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": r.d.astype(int).to_numpy(),
                       "stop_px": r.stop.to_numpy(float), "rr": 2.0})
    return ev.drop_duplicates(["decision_time","direction"]).sort_values(["decision_time","direction"]).reset_index(drop=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    for variant in ("touch", "lowest"):
        for sk in ("body", "low"):
            ev = detect(m1, sk, variant)
            if variant == "touch" and sk == "body":
                pr = cl.probe_lookahead(lambda m: detect(m, sk, variant), ev, lookback="10D")
                print("probe passed", pr["passed"] if isinstance(pr, dict) else pr)
            res = cl.trade_test(ev, max_hold="150min")
            print(variant, sk, len(ev), res["n"], "diff %.4f [%.4f, %.4f]" % (res["diff"], res["ci_lo"], res["ci_hi"]),
                  res["verdict"], "H1 %.4f H2 %.4f" % (res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"]),
                  "ties", round(res["ties"]["real_ambiguous"]-res["ties"]["control_ambiguous"],4), res["ties"].get("verdict_stop_first"))
