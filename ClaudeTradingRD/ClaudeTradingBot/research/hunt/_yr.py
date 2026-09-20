"""Fast per-year + per-window audit at a chosen CONSTANT taker spread.
Usage: python -m research.hunt._yr research/hunt/strat_m1_fvg_cont.py [spread]
Runs generate() once over all cached months on a synth constant-spread feed,
simulates with taker slip = spread, and buckets trades by calendar year and by
train/oos window. Not a substitute for the runner — just a fast iteration lens.
"""
import sys, os, importlib.util, datetime as dt
import numpy as np
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars
from bot.oanda_s5 import load, S5_DIR

def _months():
    fs = sorted(f for f in os.listdir(S5_DIR) if f.endswith(".npz"))
    return [f[len("xau_s5_"):-len(".npz")] for f in fs]

def _synth(d, s):
    mo=(d["bo"]+d["ao"])*0.5; mh=(d["bh"]+d["ah"])*0.5
    ml=(d["bl"]+d["al"])*0.5; mc=(d["bc"]+d["ac"])*0.5; h=s*0.5
    return {"ts":d["ts"],"vol":d["vol"],"bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
            "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}

def main():
    path=sys.argv[1]; spread=float(sys.argv[2]) if len(sys.argv)>2 else 0.25
    spec=importlib.util.spec_from_file_location("m",path); m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    months=_months(); tf=int(getattr(m,"TF",5)); gap=max(30,tf*2+5)
    d=load(months[0],months[-1]); ds=_synth(d,spread)
    if tf>5: ds=resample_bars(ds,tf)
    b=Bars(ds); sig=m.generate(b)
    kw=dict(m.SIM); kw.setdefault("gap_sec",gap); kw["slippage_pts"]=kw.get("slippage_pts",0.0)+spread
    r=simulate(b,sig,**kw)
    tl=r["tlist"]
    # per-year
    yr={}
    for t in tl:
        y=dt.datetime.utcfromtimestamp(int(b.ts[t[0]])).year
        pnl=t[7]*kw["dollars_per_point"]-kw["commission"]
        yr.setdefault(y,[]).append(pnl)
    cut=max(1,int(len(months)*0.65)); oos_start=months[cut]
    print(f"# {m.NAME}  spread={spread} taker  N={r['trades']} WR={r['wr']:.1f} PF={r['pf']:.3f} net=${r['net$']:.1f} tpd={r['trades_per_day']:.2f} maxDD=${r['maxDD$']:.1f}")
    for y in sorted(yr):
        a=np.array(yr[y]); gw=a[a>0].sum(); gl=-a[a<=0].sum()
        pf=gw/gl if gl>0 else float('inf')
        print(f"  {y}: n={len(a):4d} net=${a.sum():7.1f} PF={pf:.3f} wr={100*(a>0).mean():.1f}")
if __name__=="__main__":
    main()
