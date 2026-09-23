"""Placebos: same M1 limit-touch fill mechanism, but on (A) the plain phase-3 CISD OB1
(no retrace, no OB2) and (B) a trivial 2-bar 'down bar closed over by next bar' block."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, os.path.dirname(__file__))
from verify import pb, cl, np, pd, M1, show

def fill_events(blocks, arrs_dir, m1, TF):
    pass

def detect_generic(m1, finder, TF="15min", FILL=150):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = b["close_time"].to_numpy()
    ml = m1["low"].to_numpy(float); mh = m1["high"].to_numpy(float); mc = m1["close"].to_numpy(float)
    mt = cl.data.utc_ns(m1.index)
    rows = []
    for d, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for j2, opx, stop in finder(*arrs):
            if not stop < opx: continue
            t_close = cl.data.utc_ns(pd.DatetimeIndex([ct[j2]]))[0]
            i0 = int(np.searchsorted(mt, t_close, side="left")); i1 = min(len(mt), i0 + FILL)
            if i0 >= i1: continue
            seg = ml[i0:i1] if d > 0 else -mh[i0:i1]
            hit = np.flatnonzero(seg <= opx)
            if not len(hit): continue
            k = i0 + int(hit[0]); ck = mc[k] if d > 0 else -mc[k]
            if ck <= stop: continue
            rows.append((mt[k], d, d * stop))
    r = pd.DataFrame(rows, columns=["tk", "d", "stop"])
    dt = cl.data.from_ns(r["tk"].to_numpy()) + pd.Timedelta(minutes=1)
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": r["d"].astype(int).to_numpy(),
                       "stop_px": r["stop"].to_numpy(float), "rr": 2.0})
    return ev.drop_duplicates(["decision_time", "direction"]).sort_values(["decision_time", "direction"]).reset_index(drop=True)

def cisd_ob1(o, h, l, c):
    n = len(o); out = []
    for pos in range(2, n - 2):
        if not ((l[pos] < l[pos-2:pos]).all() and (l[pos] <= l[pos+1:pos+3]).all()): continue
        s1, e1 = pb._run(o, c, pos)
        if s1 < 0: continue
        lvl1 = o[s1]; begin = max(e1, pos + 2) + 1
        for j in range(begin, min(n, begin + pb.MAX_WAIT)):
            if c[j] > lvl1:
                out.append((j, lvl1, l[s1:max(e1, pos) + 1].min())); break
    return out

def two_bar(o, h, l, c):
    out = []
    for j in range(1, len(o)):
        if c[j-1] < o[j-1] and c[j] > o[j-1]:
            out.append((j, o[j-1], min(l[j-1], l[j])))
    return out

evA = detect_generic(M1, cisd_ob1)
show("placebo A: CISD OB1 open, same fill", evA)
show("placebo A + tod30", evA, ctrl_tod_tol_min=30)
evB = detect_generic(M1, two_bar)
show("placebo B: 2-bar closed-over, same fill", evB)
show("placebo B + tod30", evB, ctrl_tod_tol_min=30)
