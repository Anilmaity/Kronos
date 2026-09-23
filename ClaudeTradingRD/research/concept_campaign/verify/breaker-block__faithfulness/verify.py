"""Faithfulness/robustness check of breaker-block reading a (EDGE +0.042R). Scratch only.
Ledger disabled (verification runs are not campaign readings)."""
import os, sys, json, importlib.util
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
import numpy as np, pandas as pd
T = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b"
sys.path.insert(0, T); sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from _common import M1, bars_with_swings, first_touch, to_ts, ONE_MIN
spec = importlib.util.spec_from_file_location("bb", T + "/breaker-block.py"); bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)

m1 = cl.load_m1()
MM = M1(m1)
SW = {}
def sw(tf):
    if tf not in SW: SW[tf] = bars_with_swings(m1, tf, 2, 2)
    return SW[tf]

def detect(tf="15min", ll_wait=40, retest_wait=20, rr=2.0, zone="body", stop_mode="block", block="run", ll_close=True):
    b, d = sw(tf)
    o, h, l, c, ct = d["o"], d["h"], d["l"], d["c"], d["ct"]
    n = len(h); m = MM
    bar_ns = np.int64(pd.Timedelta(tf).total_seconds() // 60) * ONE_MIN
    rows = []
    for bear in (True, False):
        piv = np.flatnonzero(d["sh"] if bear else d["sl"])
        for p1, p2 in zip(piv[:-1], piv[1:]):
            if p2 - p1 < 2: continue
            if bear and not h[p2] > h[p1]: continue
            if (not bear) and not l[p2] < l[p1]: continue
            seg = l[p1 + 1:p2] if bear else h[p1 + 1:p2]
            e = p1 + 1 + int(np.argmin(seg) if bear else np.argmax(seg))
            lvl1 = l[e] if bear else h[e]
            if block == "run":
                s, en = bb._run(o, c, e, bull_run_down=bear)
                if s < 0 or s <= p1: continue
                idx = np.arange(s, en + 1)
            else:  # all opposing-close candles from H1 to L1 (first-high-to-first-low reading)
                idx = np.arange(p1, e + 1)
                idx = idx[(c[idx] < o[idx]) if bear else (c[idx] > o[idx])]
                if len(idx) == 0: continue
            k = -1
            for j in range(p2 + 1, min(n, p2 + 1 + ll_wait)):
                if (h[j] > h[p2]) if bear else (l[j] < l[p2]): break
                px = c[j] if ll_close else (l[j] if bear else h[j])
                if (px < lvl1) if bear else (px > lvl1):
                    k = j; break
            if k < 0: continue
            arm = max(k, p2 + 2)
            if arm >= n: continue
            bo, bc_ = o[idx], c[idx]
            if bear:
                bot, top = np.minimum(bo, bc_).min(), np.maximum(bo, bc_).max()
                wick_lo, wick_hi = l[idx].min(), h[idx].max()
                edge = {"body": bot, "wick": wick_lo, "mt": (bot + top) / 2, "far": top}[zone]
                stop = wick_hi if stop_mode == "block" else h[p2]
                if h[k + 1:arm + 1].max(initial=-np.inf) >= edge: continue
            else:
                top, bot = np.maximum(bo, bc_).max(), np.minimum(bo, bc_).min()
                wick_hi, wick_lo = h[idx].max(), l[idx].min()
                edge = {"body": top, "wick": wick_hi, "mt": (bot + top) / 2, "far": bot}[zone]
                stop = wick_lo if stop_mode == "block" else l[p2]
                if l[k + 1:arm + 1].min(initial=np.inf) <= edge: continue
            if (h[p2 + 1:arm + 1].max() > h[p2]) if bear else (l[p2 + 1:arm + 1].min() < l[p2]): continue
            a_ns = ct[arm]
            jj = first_touch(m, a_ns, a_ns + retest_wait * bar_ns, edge, not bear, cancel=None)
            if jj < 0: continue
            if (m.h[jj] >= stop) if bear else (m.l[jj] <= stop): continue
            rows.append((m.t[jj] + ONE_MIN, -1 if bear else 1, float(stop)))
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px"]).drop_duplicates(["t", "direction"]).sort_values("t").reset_index(drop=True)
    dec = to_ts(out["t"])
    return pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": rr})

def run(ev, max_hold="5h", keep=False, **kw):
    r = cl.trade_test(ev, max_hold=max_hold, ctrl_tod_tol_min=30, keep_trades=keep, **kw)
    return r

def summ(tag, r):
    bl = {k: round(v["diff"], 3) for k, v in (r.get("blocks") or {}).items()}
    hv = {k: round(v["diff"], 3) for k, v in r["halves"].items() if isinstance(v, dict)}
    s = dict(tag=tag, n=r["n"], diff=round(r["diff"], 4), ci=[round(r["ci_lo"], 3), round(r["ci_hi"], 3)], p=round(r["p"], 3),
             verdict=r["verdict"], halves=hv, blocks=bl, ties=[round(r["ties"]["real_ambiguous"], 4), round(r["ties"]["control_ambiguous"], 4)],
             ovl=round(r["ctrl_overlap"], 4))
    print(json.dumps(s), flush=True); return s

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = []
    base = detect()
    r0 = run(base, keep=True); res.append(summ("repro", r0))
    tr = r0["_trades"]; tr.to_parquet(os.path.dirname(__file__) + "/base_trades.parquet")
    V = [("ll_wait20", dict(ll_wait=20)), ("ll_wait80", dict(ll_wait=80)),
         ("retest10", dict(retest_wait=10)), ("retest40", dict(retest_wait=40)),
         ("rr1.5", dict(rr=1.5)), ("rr3", dict(rr=3.0)),
         ("zone_wick", dict(zone="wick")), ("zone_meanthreshold", dict(zone="mt")), ("zone_far", dict(zone="far")),
         ("stop_sweptH2", dict(stop_mode="swept")), ("block_H1toL1_all", dict(block="leg")),
         ("ll_wick", dict(ll_close=False)), ("tf5m", dict(tf="5min")), ("tf1h", dict(tf="1h"))]
    for tag, kw in V:
        try:
            res.append(summ(tag, run(detect(**kw))))
        except Exception as ex:
            print(tag, "ERR", ex, flush=True)
    for mh in ("3h", "10h"):
        res.append(summ("hold" + mh, run(base, max_hold=mh)))
    res.append(summ("hold_bars5h", run(base, hold_basis="bars")))
    json.dump(res, open(os.path.dirname(__file__) + "/variants.json", "w"), indent=1)
