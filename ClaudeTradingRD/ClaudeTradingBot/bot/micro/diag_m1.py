"""Fast diagnostic for the M1 FVG strategy: per-year taker PF at constant spread,
side split, and MFE/MAE. Loads all months once."""
import sys, os, datetime as dt
import numpy as np
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars
from bot.oanda_s5 import load
import importlib.util


def _load(path):
    spec = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _synth(d, s):
    mo=(d["bo"]+d["ao"])*.5; mh=(d["bh"]+d["ah"])*.5; ml=(d["bl"]+d["al"])*.5; mc=(d["bc"]+d["ac"])*.5
    h=s*.5
    return {"ts":d["ts"],"vol":d["vol"],"bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
            "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}


def main():
    path = sys.argv[1]; spread = float(sys.argv[2]) if len(sys.argv)>2 else 0.25
    mod = _load(path); tf=int(getattr(mod,"TF",5))
    d = load("2024-01","2026-06")
    ds = _synth(d, spread)
    if tf>5: ds = resample_bars(ds, tf)
    b = Bars(ds)
    sig = mod.generate(b)
    base = dict(mod.SIM); base["gap_sec"]=max(30,tf*2+5)
    base["slippage_pts"]=base.get("slippage_pts",0.0)+spread  # taker
    res = simulate(b, sig, **base)
    tl = res["tlist"]
    # per year
    yr = {}
    for t in tl:
        y = dt.datetime.utcfromtimestamp(int(b.ts[t[0]])).year
        mo = dt.datetime.utcfromtimestamp(int(b.ts[t[0]])).month
        half = "H1" if (y<2025 or (y==2025 and mo<=7)) else "H2"  # train vs oos boundary
        pnl = t[7]*base.get("dollars_per_point",1.0)-base.get("commission",0.07)
        for key in (y, half):
            yr.setdefault(key,[0,0.0,0.0,0])  # n, gw, gl, wins
            yr[key][0]+=1
            if pnl>0: yr[key][1]+=pnl; yr[key][3]+=1
            else: yr[key][2]+=-pnl
    print(f"taker spread={spread}  total trades={len(tl)}")
    for k in sorted(yr, key=lambda x:str(x)):
        n,gw,gl,w = yr[k]
        pf = gw/gl if gl>0 else 99
        print(f"  {k}: n={n:4d} wr={100*w/max(n,1):4.1f}% pf={pf:5.2f} net=${gw-gl:8.1f}")
    # side split overall
    for sd,lab in ((1,"long"),(-1,"short")):
        sub=[t for t in tl if t[2]==sd]
        if not sub: continue
        pnl=np.array([t[7]-base.get("commission",0.07) for t in sub])
        gw=pnl[pnl>0].sum(); gl=-pnl[pnl<=0].sum()
        print(f"  {lab}: n={len(sub)} wr={100*(pnl>0).mean():.1f}% pf={gw/gl if gl>0 else 99:.2f}")


if __name__=="__main__":
    main()
