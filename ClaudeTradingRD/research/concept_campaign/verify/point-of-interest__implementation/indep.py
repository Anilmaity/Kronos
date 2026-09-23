"""Independent implementation of the 1h CISD book + §4.1 POI gate (reading a), numpy only.
Written from concepts/entry/cisd.yaml + point-of-interest.yaml + method_spec §4.1, not from detectors/."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "verify_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

def swings(h, l, L=2, R=2):
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(L, n - R):
        sh[i] = h[i] > h[i-L:i].max() and h[i] >= h[i+1:i+1+R].max()
        sl[i] = l[i] < l[i-L:i].min() and l[i] <= l[i+1:i+1+R].min()
    return sh, sl

def detect(m1, polarity="any", fallback=True, both=True):
    b = cl.build_bars(m1, "1h")
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    n = len(b); sh, sl = swings(h, l)
    up, dn = c > o, c < o
    bullfvg = np.zeros(n, bool); bearfvg = np.zeros(n, bool)
    bullfvg[2:] = l[2:] > h[:-2]; bearfvg[2:] = h[2:] < l[:-2]
    rows = []
    for sgn, piv in ((1, sl), (-1, sh)):
        opp = dn if sgn > 0 else up
        for p in np.flatnonzero(piv):
            # opposing run producing the extreme (end within 2 bars before p, or p itself)
            end = p
            while end > 0 and not opp[end] and p - end <= 2:
                end -= 1
            if not opp[end] or p - end > 2:
                continue
            st = end
            while st > 0 and opp[st-1] and end - st + 1 < 10:
                st -= 1
            lvl = o[st]
            j0 = max(end, p + 2) + 1
            conf = -1
            for j in range(j0, min(n, j0 + 3)):
                if (c[j] > lvl) if sgn > 0 else (c[j] < lvl):
                    conf = j; break
            if conf < 0:
                continue
            ext = l[p] if sgn > 0 else h[p]
            # --- POI: range = last opposing swing (confirmable by p) within 40 bars -> p
            lo = max(0, p - 40)
            cand = [q for q in range(lo, p + 1) if (sh[q] if sgn > 0 else sl[q]) and q + 2 <= p and q - 2 >= lo]
            s = cand[-1] if cand else lo
            # FVGs stamped in [s, p]
            fv = []
            for i in range(max(s, 2), p + 1):
                if polarity in ("any", "aligned" if sgn > 0 else "x") and bullfvg[i] or \
                   (polarity == "aligned" and sgn < 0 and bullfvg[i]) or \
                   (polarity == "any" and bearfvg[i]) or (polarity == "aligned" and sgn < 0 and False):
                    pass
            fv = []
            for i in range(max(s, 2), p + 1):
                kinds = []
                if bullfvg[i] and (polarity == "any" or (polarity == "aligned") == (sgn > 0)):
                    kinds.append((h[i-2], l[i]))
                if bearfvg[i] and (polarity == "any" or (polarity == "aligned") == (sgn < 0)):
                    kinds.append((h[i], l[i-2]))
                for glo, ghi in kinds:
                    fv.append(ext <= ghi if sgn > 0 else ext >= glo)
            # same-side swings in [s, p) confirmed before p
            sw = []
            for q in range(s, p):
                if (sl[q] if sgn > 0 else sh[q]) and q + 2 < p and q - 2 >= max(0, s - 2):
                    sw.append(ext < l[q] if sgn > 0 else ext > h[q])
            if fv and sw:
                ok = (any(fv) and any(sw)) if both else (any(fv) or any(sw))
                br = "both"
            elif fv:
                ok, br = any(fv), "fvg"
            elif sw:
                ok, br = any(sw), "swing"
            elif fallback:
                br = "cisd"
                e2 = p
                while e2 > s and not opp[e2]:
                    e2 -= 1
                if e2 <= s:
                    ok = False
                else:
                    s2 = e2
                    while s2 > s and opp[s2-1] and e2 - s2 + 1 < 10:
                        s2 -= 1
                    bh = max(o[s2:e2+1].max(), c[s2:e2+1].max()); bl = min(o[s2:e2+1].min(), c[s2:e2+1].min())
                    mid = (bh + bl) / 2
                    fwd = c[e2+1:conf+1]
                    ok = bool((fwd > mid).any() if sgn > 0 else (fwd < mid).any())
            else:
                ok, br = False, "none"
            rows.append((ct[conf], sgn, ext, ok, br, p))
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "gate", "branch", "p"])
    ev = ev.sort_values(["decision_time"], kind="stable").reset_index(drop=True)
    ev["available_at"] = ev["decision_time"]; ev["rr"] = 2.0
    return ev

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1)
    ev.to_pickle(os.path.join(HERE, "indep_events.pkl"))
    print(len(ev), ev.gate.mean()); print(ev.groupby("branch").gate.agg(["size", "mean"]))
    orig = pd.read_pickle(os.path.join(HERE, "orig_events.pkl"))
    k = ["decision_time", "direction", "stop_px"]
    mg = orig.merge(ev, on=k, how="outer", indicator=True)
    print(mg["_merge"].value_counts())
    both_ = mg[mg._merge == "both"]
    print("gate agreement", (both_.poi_a == both_.gate).mean(), "disagree n", (both_.poi_a != both_.gate).sum())
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate"]
    res = cl.gate_test(ev[cols], "gate", mask_available_at="decision_time", max_hold="10h")
    print({k: res.get(k) for k in ("verdict", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p")},
          res["halves"]["H1"]["diff"], res["halves"]["H2"]["diff"])
