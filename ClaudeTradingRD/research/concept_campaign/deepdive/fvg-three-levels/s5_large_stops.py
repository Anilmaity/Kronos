"""Step 5: is the rr1/rr2 hard-stop book net-positive anywhere cost is small (large gaps)?"""
import numpy as np, pandas as pd
from sim import simulate, pos, boot_ci, day_codes
OUT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/fvg-three-levels/"
S = pd.read_pickle(OUT + "s1.pkl"); R = pd.read_pickle(OUT + "s2.pkl")
ev, up, dn = S["ev"], S["up"], S["dn"]
t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
codes, nd = day_codes(t); ss = R["sstop_sel"]
for rr in (1, 2):
    o = simulate(pos(t), d, rr * dn, dn)
    cs = [simulate(np.where(ss["i0"][:, k] >= 0, ss["i0"][:, k], 0), ss["d"][:, k],
                   np.where(ss["i0"][:, k] >= 0, rr * ss["sd"][:, k], np.nan), ss["sd"][:, k]) for k in range(5)]
    for lo_, hi_ in ((3, 5), (5, 1e9), (4, 1e9)):
        m = (dn >= lo_) & (dn < hi_)
        for sp in (0.0, 0.25, 0.35):
            ov = o["R_hard50"] - sp / dn
            with np.errstate(all="ignore"):
                sv = np.nanmean(np.vstack([c["R_hard50"] - sp / ss["sd"][:, k] for k, c in enumerate(cs)]), 0)
            a = boot_ci(np.where(m, ov, np.nan), codes, nd); b = boot_ci(np.where(m, ov - sv, np.nan), codes, nd)
            print(f"rr{rr} dn[{lo_},{hi_}) n={m.sum():5d} spread {sp:.2f} net {a[0]:+.4f} [{a[1]:+.3f},{a[2]:+.3f}]  diff vs sstop {b[0]:+.4f} [{b[1]:+.3f},{b[2]:+.3f}]"
                  f"  share 2024+ {(t[m] >= pd.Timestamp('2024-01-01', tz='UTC')).mean():.2f}")
