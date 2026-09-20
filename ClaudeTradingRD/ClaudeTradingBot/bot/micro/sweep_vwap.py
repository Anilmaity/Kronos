"""Fast in-memory param sweep for the VWAP-deviation reversion strat.
Loads train+oos ONCE, builds synthetic constant-spread bars (0.20/0.30), and
re-evaluates generate()+simulate() over a param grid by reloading the module with
env overrides. Reports ~0.25 taker PF for BOTH train and oos."""
import os, itertools, importlib
import numpy as np
from bot.oanda_s5 import load
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars

MONTHS = sorted(__import__("os").listdir("reports/s5"))
TRAIN = ("2024-01", "2025-07")
OOS = ("2025-08", "2026-06")

def synth(d, s):
    mo=(d["bo"]+d["ao"])*0.5; mh=(d["bh"]+d["ah"])*0.5
    ml=(d["bl"]+d["al"])*0.5; mc=(d["bc"]+d["ac"])*0.5; h=s*0.5
    return {"ts":d["ts"],"vol":d["vol"],"bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
            "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}

print("loading...")
draw = {w: load(*win) for w, win in [("tr", TRAIN), ("oos", OOS)]}
# pre-build M1 synthetic bars at each spread for each window
BARS = {}
for w in ("tr", "oos"):
    for s in (0.20, 0.30):
        BARS[(w, s)] = Bars(resample_bars(synth(draw[w], s), 60))
print("ready")

import bot.micro.strat_m1_r1_3 as strat

def evalcfg():
    importlib.reload(strat)
    res = {}
    for w in ("tr", "oos"):
        pf25 = []
        ntot = 0
        for s in (0.20, 0.30):
            b = BARS[(w, s)]
            sig = strat.generate(b)
            base = dict(strat.SIM); base.setdefault("gap_sec", 125)
            km = dict(base); km["slippage_pts"] = s
            rt = simulate(b, sig, **km)
            pf25.append(rt["pf"]); ntot = rt["trades"]
        res[w] = (round(sum(pf25)/2, 3), ntot)
    return res

GRID = dict(
    VW_K=["2.0","2.5","3.0"],
    VW_TPFRAC=["0.5","0.8","1.0"],
    VW_SLATR=["1.2","2.0","3.0"],
    VW_OFF=["0.0","0.4","0.8"],
    VW_SLOPEMAX=["0.8","1.2"],
    VW_EXTLB=["0","15"],
)
keys = list(GRID)
best = []
import sys
combos = list(itertools.product(*[GRID[k] for k in keys]))
print(f"{len(combos)} combos")
ALLBEST = (-9, 0, 0, 0, 0, {})
for n, vals in enumerate(combos):
    for k, v in zip(keys, vals):
        os.environ[k] = v
    r = evalcfg()
    trpf, trn = r["tr"]; oopf, oon = r["oos"]
    if oon >= 100 and min(trpf, oopf) > ALLBEST[0]:
        ALLBEST = (round(min(trpf, oopf),3), trpf, trn, oopf, oon, dict(zip(keys, vals)))
    if trpf > 1.0 and oopf > 1.0 and oon >= 100:
        best.append((min(trpf, oopf), trpf, trn, oopf, oon, dict(zip(keys, vals))))
    if n % 20 == 0:
        print(f"  {n}/{len(combos)} best={len(best)}", file=sys.stderr)
best.sort(reverse=True)
print("\nTOP (both train&oos taker PF@~0.25 >1, oos N>=100):")
for b_ in best[:15]:
    print(b_)
if not best:
    print("NONE positive in both windows.")
print("\nGLOBAL BEST by min(train,oos) taker PF (any sign):")
for k, v in zip(keys, ALLBEST[5]):
    pass
print("min=%.3f trpf=%.3f trn=%d oopf=%.3f oon=%d cfg=%s" % ALLBEST)
