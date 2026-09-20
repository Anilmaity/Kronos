import sys, json, datetime as dt
import numpy as np
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars
from bot.oanda_s5 import load
from bot.micro.runner import _load_strat

def synth(d, s):
    mo=(d["bo"]+d["ao"])*0.5; mh=(d["bh"]+d["ah"])*0.5
    ml=(d["bl"]+d["al"])*0.5; mc=(d["bc"]+d["ac"])*0.5
    h=s*0.5
    return {"ts":d["ts"],"vol":d["vol"],
            "bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
            "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}

path=sys.argv[1]; spread=float(sys.argv[2]); a=sys.argv[3]; b_=sys.argv[4]
mod=_load_strat(path)
tf=int(getattr(mod,"TF",5))
d=load(a,b_)
ds=synth(d,spread)
if tf>5: ds=resample_bars(ds,tf)
bars=Bars(ds)
gap=max(30,tf*2+5)
sig=mod.generate(bars)
base=dict(mod.SIM); base.setdefault("gap_sec",gap)
base["slippage_pts"]=base.get("slippage_pts",0.0)+spread  # taker
res=simulate(bars,sig,**base)
dpp=base.get("dollars_per_point",1.0); comm=base.get("commission",0.07)
peryear={}
for t in res["tlist"]:
    y=dt.datetime.utcfromtimestamp(bars.ts[t[0]]).year
    pnl=t[7]*dpp-comm
    peryear.setdefault(y,[0,0.0,0.0])
    d_=peryear[y]; d_[0]+=1
    if pnl>0: d_[1]+=pnl
    else: d_[2]+=-pnl
out={}
for y in sorted(peryear):
    n,gw,gl=peryear[y]
    pf=gw/gl if gl>0 else float('inf')
    out[y]={"n":n,"pf":round(pf,3),"net":round(gw-gl,1)}
print(mod.NAME, "spread=%.2f taker"%spread, a,"->",b_)
print(json.dumps(out))
print("TOTAL n=%d pf=%.3f net=%.1f wr=%.1f"%(res["trades"],res["pf"],res["net$"],res["wr"]))
