"""CORRECT-semantics fast scan: first bias-ALIGNED poke per session (matches strat).
Precompute pokes per (buf,ema); selector picks first aligned for direction; vary sl/tp."""
import numpy as np, itertools, time
from bot.micro.engine import Bars, simulate, atr, Signals
from bot.micro.features import ema
from bot.oanda_s5 import load
from bot.micro.runner import _synth
from bot.micro.features import resample_bars

TF=60
def synth_bars(a,bm,s):
    d=load(a,bm); ds=_synth(d,s); ds=resample_bars(ds,TF); return Bars(ds)
SESSIONS=[(420,30,660),(750,30,960)]
SIMBASE=dict(maxhold=240,dollars_per_point=1.0,commission=0.07,cooldown=0,gap_sec=125)

def pokes(b, buf_frac, ef_p, es_p, min_or=1.0):
    """Per session/day, ordered list of pokes: (j, poke_dir(+1 up/-1 dn), orr, bias_j)."""
    mid=b.mid; hi=(b.ah+b.bh)*0.5; lo=(b.al+b.bl)*0.5
    minute=b.minute; day=b.day
    ef=ema(mid,ef_p); es=ema(mid,es_p); bias=np.sign(ef-es)
    out=[]
    for dy in np.unique(day):
        didx=np.where(day==dy)[0]
        if len(didx)==0: continue
        dmin=minute[didx]
        for (start,ormin,tend) in SESSIONS:
            orw=didx[(dmin>=start)&(dmin<start+ormin)]
            if len(orw)<3: continue
            or_hi=hi[orw].max(); or_lo=lo[orw].min(); orr=or_hi-or_lo
            if orr<min_or: continue
            buf=buf_frac*orr
            seq=[]
            for j in didx[(dmin>=start+ormin)&(dmin<tend)]:
                c=mid[j]
                if c>or_hi+buf: seq.append((j,1,orr,bias[j] if np.isfinite(bias[j]) else 0.0))
                elif c<or_lo-buf: seq.append((j,-1,orr,bias[j] if np.isfinite(bias[j]) else 0.0))
            out.append(seq)
    return out

def select(seqs, direction):
    """Pick first bias-aligned poke per session -> (j, trade_side, orr)."""
    picks=[]
    for seq in seqs:
        for (j,pd,orr,bs) in seq:
            if direction=='fade':
                if pd>0 and bs<0: picks.append((j,-1,orr)); break   # up-poke downtrend -> short
                if pd<0 and bs>0: picks.append((j,1,orr)); break
            elif direction=='cont':
                if pd>0 and bs>0: picks.append((j,1,orr)); break
                if pd<0 and bs<0: picks.append((j,-1,orr)); break
            elif direction=='fade_nb':
                picks.append((j,-pd,orr)); break
            elif direction=='cont_nb':
                picks.append((j,pd,orr)); break
    return picks

def build(b,picks,sl_k,tp_k):
    if not picks: return None
    I=np.array([p[0] for p in picks],np.int64)
    SIDE=np.array([p[1] for p in picks],np.int8)
    ORR=np.array([p[2] for p in picks],np.float64)
    o=np.argsort(I,kind='stable'); I=I[o];SIDE=SIDE[o];ORR=ORR[o]
    SLP=sl_k*ORR; TPP=(tp_k*ORR if tp_k>0 else np.full(len(I),np.inf))
    m=len(I)
    return Signals(i=I,side=SIDE,kind=np.zeros(m,int),level=b.mid[I],sl_pts=SLP,tp_pts=TPP,ttl=np.zeros(m,np.int64))

def pf(b,sig,trail=0.0):
    if sig is None: return (0,0,0,0)
    km=dict(SIMBASE); km['slippage_pts']=0.25
    if trail>0: km['trail_pts']=trail
    r=simulate(b,sig,**km); return (r['trades'],round(r['pf'],3),round(r['net$'],1),round(r['trades_per_day'],2))

t0=time.time()
btr=synth_bars('2024-01','2025-07',0.25); boos=synth_bars('2025-08','2026-06',0.25)
print('loaded',round(time.time()-t0,1),flush=True)
res=[]
for buf,(ef,es) in itertools.product([0.1,0.15,0.2,0.25,0.3],[(50,200),(30,150),(20,100)]):
    pt=pokes(btr,buf,ef,es); po=pokes(boos,buf,ef,es)
    for dirn in ['fade','cont']:
        st=select(pt,dirn); so=select(po,dirn)
        for sl,tp in itertools.product([0.75,1.0,1.25,1.5],[1.5,2.0,2.5,3.0]):
            rt=pf(btr,build(btr,st,sl,tp)); ro=pf(boos,build(boos,so,sl,tp))
            res.append((buf,(ef,es),dirn,sl,tp,rt,ro))
    print('done buf',buf,'ema',(ef,es),round(time.time()-t0,1),flush=True)
def sc(r):
    t,o=r[5],r[6]
    if t[0]<100 or o[0]<100: return -9
    return min(t[1]-1.15, o[1]-1.30)  # how far past BOTH thresholds
res.sort(key=sc,reverse=True)
print('=== TOP correct-semantics (ranked by clearing train>=1.15 & OOS>=1.30) ===',flush=True)
for r in res[:30]:
    print('buf',r[0],'ema',r[1],r[2],'sl',r[3],'tp',r[4],'| TR',r[5],'| OOS',r[6],flush=True)
