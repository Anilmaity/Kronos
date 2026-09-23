"""Every bar: first_m1 >= label, last_m1+1min <= close_time, and each M1 minute maps to
exactly one bar; bars never overlap (close_time <= next label). Checks all tfs/grids
over the certified span (includes ~21 DST switches)."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
one = pd.Timedelta("1min")
for tf, g in [("5min","forex"),("15min","forex"),("1h","forex"),("2h","forex"),("4h","forex"),("4h","futures"),("4h","utc"),("1D","forex"),("1W","forex"),("1M","forex")]:
    b = cl.bars(tf, grid4h=g)
    lab = pd.DatetimeIndex(b.index); ct = pd.DatetimeIndex(b.close_time)
    f = pd.DatetimeIndex(b.first_m1); l = pd.DatetimeIndex(b.last_m1)
    v1 = int((f < lab).sum()); v2 = int((l + one > ct).sum())
    ov = int((ct[:-1] > lab[1:]).sum())
    tot = int(b.n_m1.sum())
    print(f"{tf:6s} {g:8s} bars={len(b):7d} first<label={v1} last>close={v2} overlaps={ov} m1_total={tot} (m1={len(m1)})")
    if ov:
        k = np.flatnonzero(ct[:-1] > lab[1:])[:3]
        for i in k: print("   overlap:", lab[i], ct[i], "next label", lab[i+1], "next first_m1", f[i+1])
