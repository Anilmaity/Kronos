"""Step 3: paired event-vs-control comparisons, robustness blocks, cost realism."""
import json
import numpy as np
import pandas as pd
from sim import boot_ci, day_codes

OUT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/deepdive/fvg-three-levels/"
S = pd.read_pickle(OUT + "s1.pkl"); R = pd.read_pickle(OUT + "s2.pkl")
ev, up, dn = S["ev"], S["up"], S["dn"]
t = pd.DatetimeIndex(ev["decision_time"])
codes, nd = day_codes(t)
obs = R["obs"]
ARMS = ["base", "tod", "sstop", "sstop_rd", "sboth"]
SPREADS = (0.0, 0.25, 0.35)
summary = {}


def arm_mean(arm, key, cost=0.0, dist=None):
    X = []
    for k, a in enumerate(R[arm]):
        v = a[key].copy()
        if cost:
            dd = dn if dist is None else dist[:, k]
            v = v - cost / dd
        X.append(v)
    with np.errstate(all="ignore"):
        return np.nanmean(np.vstack(X), 0)


def ctrl_dn(arm):
    return R[arm + "_dist"][0] if arm + "_dist" in R else None


def fmt(m, lo, hi, p, scale=100, u="pp"):
    return f"{m*scale:+.3f}{u} [{lo*scale:+.3f},{hi*scale:+.3f}] p={p:.4f}"


blocks = {"B1": ("2016-01-01", "2018-08-22 11:01"), "B2": ("2018-08-22 11:01", "2021-04-12 08:43"),
          "B3": ("2021-04-12 08:43", "2023-12-02 06:25"), "B4": ("2023-12-02 06:25", "2026-12-31"),
          "H1": ("2016-01-01", "2021-01-01"), "H2": ("2021-01-01", "2026-12-31")}
bmask = {k: (t >= pd.Timestamp(a, tz="UTC")) & (t < pd.Timestamp(b, tz="UTC")) for k, (a, b) in blocks.items()}


def compare(key, arm, cost=0.0, mask=None, scale=100, u="pp"):
    o = obs[key].copy()
    if cost:
        o = o - cost / dn
    c = arm_mean(arm, key, cost, ctrl_dn(arm) if arm in ("sstop", "sstop_rd", "sboth") else None)
    x = o - c
    m = np.isfinite(x) & (np.ones(len(x), bool) if mask is None else mask)
    xx = np.where(m, x, np.nan)
    mean, lo, hi, p = boot_ci(xx, codes, nd)
    return dict(n=int(m.sum()), obs=float(np.nanmean(np.where(m, o, np.nan))),
                ctrl=float(np.nanmean(np.where(m, c, np.nan))), diff=mean, lo=lo, hi=hi, p=p)


print("=== ties: race tie share obs %.5f; hard-stop same-bar ties obs %.4f" %
      (np.nanmean(obs["tie"]), np.nanmean(obs["tie_hard"])))
for arm in ARMS:
    print(f"   {arm:9s} race-tie {np.nanmean(arm_mean(arm,'tie')):.5f}  hard-tie {np.nanmean(arm_mean(arm,'tie_hard')):.4f}")

print("\n=== 1. HIT RATE (the campaign statistic) vs each control")
for arm in ARMS:
    r = compare("hit", arm)
    summary[f"hit_vs_{arm}"] = r
    print(f"  {arm:9s} n={r['n']:6d} obs {r['obs']:.4f} ctrl {r['ctrl']:.4f}  diff {fmt(r['diff'],r['lo'],r['hi'],r['p'])}")
# event rate on the matched subset only vs full
print("\n=== 1b. invalidation-first rate vs control")
for arm in ARMS:
    r = compare("inv", arm)
    print(f"  {arm:9s} obs {r['obs']:.4f} ctrl {r['ctrl']:.4f}  diff {fmt(r['diff'],r['lo'],r['hi'],r['p'])}")

print("\n=== 2. TRADE: entry next M1 open, target = leg extreme, stop variants; R in units of dn")
for key in ("R_close", "R_close50", "R_hard", "R_hard50"):
    for arm in ARMS:
        r = compare(key, arm, scale=1, u="R")
        summary[f"{key}_vs_{arm}"] = r
        print(f"  {key:9s} {arm:9s} obs {r['obs']:+.4f}R ctrl {r['ctrl']:+.4f}R diff {fmt(r['diff'],r['lo'],r['hi'],r['p'],1,'R')}")

print("\n=== 3. BLOCKS / HALVES (hit diff vs tod and sboth; R_hard50 diff vs sstop)")
for b, m in bmask.items():
    line = f"  {b}: n={m.sum():5d}"
    for key, arm, sc, u in (("hit", "tod", 100, "pp"), ("hit", "sstop", 100, "pp"), ("hit", "sboth", 100, "pp"),
                            ("R_hard50", "sstop", 1, "R")):
        r = compare(key, arm, mask=np.asarray(m), scale=sc, u=u)
        summary[f"{b}_{key}_{arm}"] = r
        line += f" | {key}/{arm} {r['diff']*sc:+.3f}{u} [{r['lo']*sc:+.3f},{r['hi']*sc:+.3f}]"
    print(line)

print("\n=== 4. COST REALISM: net avg R of the concept trade itself (spread in points / dn)")
print("   dn (points) quantiles:", np.round(np.nanpercentile(dn, [10, 25, 50, 75, 90]), 3))
for key in ("R_close", "R_hard50"):
    for sp in SPREADS:
        for lab, m in (("all", np.ones(len(dn), bool)), ("dn>=1pt", dn >= 1), ("dn>=2pt", dn >= 2),
                       ("dn>=3pt", dn >= 3)):
            o = obs[key] - sp / dn
            oo = np.where(m, o, np.nan)
            mean, lo, hi, p = boot_ci(oo, codes, nd)
            r2 = compare(key, "sstop", cost=sp, mask=m, scale=1, u="R")
            summary[f"net_{key}_{sp}_{lab}"] = dict(n=int(np.isfinite(oo).sum()), net=mean, lo=lo, hi=hi,
                                                   diff_vs_sstop=r2["diff"], dlo=r2["lo"], dhi=r2["hi"])
            print(f"  {key:9s} spread {sp:.2f} {lab:8s} n={np.isfinite(oo).sum():6d} net {mean:+.4f}R [{lo:+.4f},{hi:+.4f}]"
                  f"   diff vs sstop {r2['diff']:+.4f} [{r2['lo']:+.4f},{r2['hi']:+.4f}]")

print("\n=== 5. hit diff by stop-size bucket (does it live where it is tradeable?)")
for lab, m in (("dn<0.3", dn < 0.3), ("0.3-1", (dn >= 0.3) & (dn < 1)), ("1-2", (dn >= 1) & (dn < 2)),
               (">=2", dn >= 2)):
    r = compare("hit", "tod", mask=m); r2 = compare("hit", "sstop", mask=m)
    print(f"  {lab:7s} n={m.sum():6d} vs tod {fmt(r['diff'],r['lo'],r['hi'],r['p'])} | vs sstop {fmt(r2['diff'],r2['lo'],r2['hi'],r2['p'])}")

json.dump(summary, open(OUT + "summary.json", "w"), indent=1, default=float)
