"""Per-year honesty check: run the AMD strat over ALL cached months at a constant
0.25 TAKER spread and bucket trades by calendar year. Env-configured like the runner."""
import datetime as dt
import sys, os
sys.path.insert(0, os.getcwd())
import numpy as np
from bot.oanda_s5 import S5_DIR, load
from bot.micro.features import resample_bars
from bot.micro.engine import Bars, simulate
import importlib.util, os

spec = importlib.util.spec_from_file_location("m", "research/hunt/strat_m1_asian_amd.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

months = sorted(f[7:-4] for f in os.listdir(S5_DIR) if f.endswith(".npz"))
d = load(months[0], months[-1])
# constant 0.25 spread around mid, then taker = cross it via slippage
mo=(d["bo"]+d["ao"])*.5; mh=(d["bh"]+d["ah"])*.5; ml=(d["bl"]+d["al"])*.5; mc=(d["bc"]+d["ac"])*.5
s=0.25; h=s/2
ds={"ts":d["ts"],"vol":d["vol"],"bo":mo-h,"bh":mh-h,"bl":ml-h,"bc":mc-h,
    "ao":mo+h,"ah":mh+h,"al":ml+h,"ac":mc+h}
tf=int(getattr(m,"TF",5))
if tf>5: ds=resample_bars(ds,tf)
b=Bars(ds); gap=max(30,tf*2+5)
sig=m.generate(b)
sim=dict(m.SIM); sim.setdefault("gap_sec",gap); sim["slippage_pts"]=sim.get("slippage_pts",0.0)+s
res=simulate(b,sig,**sim)
yr={}
for t in res["tlist"]:
    y=dt.datetime.utcfromtimestamp(int(b.ts[t[0]])).year
    yr.setdefault(y,[]).append(t[7])  # pts
print("NAME",m.NAME,"KIND",os.environ.get("AMD_KIND","limit"),"SIDE",os.environ.get("AMD_SIDE","dflt"),"EXIT",os.environ.get("AMD_EXIT","dflt"))
tot=0; totn=0
for y in sorted(yr):
    p=np.array(yr[y]); pnl=p*1.0-0.07
    gw=pnl[pnl>0].sum(); gl=-pnl[pnl<=0].sum()
    pf=gw/gl if gl>0 else float('inf')
    print("  %d  n=%3d  net$=%7.1f  pf=%.2f  wr=%.1f"%(y,len(p),pnl.sum(),pf,(pnl>0).mean()*100))
    tot+=pnl.sum(); totn+=len(p)
print("  ALL n=%d net$=%.1f"%(totn,tot))
