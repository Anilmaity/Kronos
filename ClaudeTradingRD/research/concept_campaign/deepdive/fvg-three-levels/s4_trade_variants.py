"""Step 4: can the rate be traded? Fixed-RR hard-stop books at the far edge (and the
close-invalidation book) on the tradeable stop sizes, vs ToD random-distance and
structural-stop controls, gross and net of a 0.25-0.35 pt spread. Ties 50/50."""
import numpy as np
import pandas as pd
from sim import simulate, pos, boot_ci, day_codes

OUT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/fvg-three-levels/"
S = pd.read_pickle(OUT + "s1.pkl"); R = pd.read_pickle(OUT + "s2.pkl")
ev, up, dn = S["ev"], S["up"], S["dn"]
t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
codes, nd = day_codes(t)
i0 = pos(t)
tod_i0 = R["tod_i0"]; ss = R["sstop_sel"]
REPS = 5
rows = []
blocks = {"H1": t < pd.Timestamp("2021-01-01", tz="UTC"), "H2": t >= pd.Timestamp("2021-01-01", tz="UTC")}
for tgt_name in ("rr1", "rr2", "leg"):
    def tgt(dist, base_up):
        return {"rr1": dist, "rr2": 2 * dist, "leg": base_up}[tgt_name]
    o = simulate(i0, d, tgt(dn, up), dn)
    ct = [simulate(tod_i0[:, k], d, tgt(dn, up), dn) for k in range(REPS)]
    cs = [simulate(np.where(ss["i0"][:, k] >= 0, ss["i0"][:, k], 0), ss["d"][:, k],
                   np.where(ss["i0"][:, k] >= 0, tgt(ss["sd"][:, k], up), np.nan), ss["sd"][:, k]) for k in range(REPS)]
    for key in ("R_hard50", "R_close50"):
        for sp in (0.0, 0.30):
            for lab, m in (("dn>=1pt", dn >= 1), ("dn>=2pt", dn >= 2)):
                ov = o[key] - sp / dn
                with np.errstate(all="ignore"):
                    tv = np.nanmean(np.vstack([c[key] - sp / dn for c in ct]), 0)
                    sv = np.nanmean(np.vstack([c[key] - sp / ss["sd"][:, k] for k, c in enumerate(cs)]), 0)
                net = boot_ci(np.where(m, ov, np.nan), codes, nd)
                dt = boot_ci(np.where(m, ov - tv, np.nan), codes, nd)
                dsv = boot_ci(np.where(m, ov - sv, np.nan), codes, nd)
                hs = [float(np.nanmean(np.where(m & blocks[h], ov - sv, np.nan))) for h in ("H1", "H2")]
                rows.append(dict(target=tgt_name, book=key, spread=sp, subset=lab, n=int(np.isfinite(np.where(m, ov, np.nan)).sum()),
                                 net=round(net[0], 4), net_ci=f"[{net[1]:+.3f},{net[2]:+.3f}]",
                                 d_tod=round(dt[0], 4), d_tod_ci=f"[{dt[1]:+.3f},{dt[2]:+.3f}]",
                                 d_sstop=round(dsv[0], 4), d_sstop_ci=f"[{dsv[1]:+.3f},{dsv[2]:+.3f}]",
                                 d_sstop_H1=round(hs[0], 4), d_sstop_H2=round(hs[1], 4)))
df = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(df.to_string(index=False))
df.to_csv(OUT + "s4_trade_variants.csv", index=False)
