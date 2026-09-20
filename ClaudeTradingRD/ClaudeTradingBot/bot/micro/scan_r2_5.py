"""Fast param scan for OR breakout family. Precompute break events; vary sl/tp/dir."""
import numpy as np, itertools, sys, time
from bot.micro.engine import Bars, simulate, atr, Signals
from bot.micro.features import ema
from bot.oanda_s5 import load
from bot.micro.runner import _synth
from bot.micro.features import resample_bars

TF=60
def synth_bars(a,bm,s):
    d=load(a,bm); ds=_synth(d,s); ds=resample_bars(ds,TF); return Bars(ds)

SESS_SETS={
 'L+NY':[(420,30,660),(750,30,960)],
 'L+NY15':[(420,15,660),(750,15,960)],
 'L+NY60':[(420,60,660),(750,60,960)],
}
SIM=dict(maxhold=240,dollars_per_point=1.0,commission=0.07,cooldown=0,gap_sec=125)

def break_events(b, sess, buf_frac, ef_p, es_p, max_or_atr=12.0, min_or=1.0, maxbreaks=1):
    """Return list of (j, dir(+1 up/-1 dn), orr, bias_sign)."""
    n=b.n; mid=b.mid; hi=(b.ah+b.bh)*0.5; lo=(b.al+b.bl)*0.5
    minute=b.minute; day=b.day; at=atr(b,14)
    ef=ema(mid,ef_p); es=ema(mid,es_p); bias=np.sign(ef-es)
    ev=[]
    for dy in np.unique(day):
        didx=np.where(day==dy)[0]
        if len(didx)==0: continue
        dmin=minute[didx]
        for (start,ormin,tend) in sess:
            orw=didx[(dmin>=start)&(dmin<start+ormin)]
            if len(orw)<3: continue
            or_hi=hi[orw].max(); or_lo=lo[orw].min(); orr=or_hi-or_lo
            if orr<min_or: continue
            if max_or_atr>0 and orr>max_or_atr*at[orw[-1]]: continue
            buf=buf_frac*orr; nb=0
            for j in didx[(dmin>=start+ormin)&(dmin<tend)]:
                if nb>=maxbreaks: break
                c=mid[j]
                if c>or_hi+buf:
                    ev.append((j,1,orr,bias[j] if np.isfinite(bias[j]) else 0.0)); nb+=1
                elif c<or_lo-buf:
                    ev.append((j,-1,orr,bias[j] if np.isfinite(bias[j]) else 0.0)); nb+=1
    return ev

def build_sig(b, ev, direction, sl_k, tp_k):
    I,SIDE,SLP,TPP=[],[],[],[]
    for (j,d,orr,bs) in ev:
        if direction=='cont':
            if d>0 and bs>0: side=1
            elif d<0 and bs<0: side=-1
            else: continue
        elif direction=='fade':
            if d>0 and bs<0: side=-1
            elif d<0 and bs>0: side=1
            else: continue
        elif direction=='cont_nb':
            side=d
        elif direction=='fade_nb':
            side=-d
        I.append(j);SIDE.append(side);SLP.append(sl_k*orr);TPP.append(tp_k*orr)
    if not I: return None
    I=np.array(I,np.int64); o=np.argsort(I,kind='stable'); I=I[o]
    SIDE=np.array(SIDE,np.int8)[o];SLP=np.array(SLP,np.float64)[o];TPP=np.array(TPP,np.float64)[o]
    m=len(I)
    return Signals(i=I,side=SIDE,kind=np.zeros(m,int),level=b.mid[I],sl_pts=SLP,tp_pts=TPP,ttl=np.zeros(m,np.int64))

def ev_pf(b,sig):
    if sig is None: return (0,0,0,0)
    km=dict(SIM); km['slippage_pts']=0.25
    r=simulate(b,sig,**km)
    return (r['trades'], round(r['pf'],3), round(r['net$'],1), round(r['trades_per_day'],2))

t0=time.time()
btr=synth_bars('2024-01','2025-07',0.25)
boos=synth_bars('2025-08','2026-06',0.25)
print('loaded',round(time.time()-t0,1),'s',flush=True)

results=[]
for sess_n,buf,(efp,esp) in itertools.product(['L+NY','L+NY15','L+NY60'],[0.05,0.1,0.2],[(50,200),(20,100)]):
    sess=SESS_SETS[sess_n]
    evt=break_events(btr,sess,buf,efp,esp); evo=break_events(boos,sess,buf,efp,esp)
    for dirn,sl,tp in itertools.product(['cont','fade','cont_nb','fade_nb'],[0.75,1.0,1.5],[1.0,1.5,2.0]):
        rt=ev_pf(btr,build_sig(btr,evt,dirn,sl,tp))
        ro=ev_pf(boos,build_sig(boos,evo,dirn,sl,tp))
        results.append((sess_n,buf,(efp,esp),dirn,sl,tp,rt,ro))
    print('done',sess_n,buf,(efp,esp),round(time.time()-t0,1),'s',flush=True)

def score(r):
    t,o=r[6],r[7]
    if t[0]<80 or o[0]<80: return -9
    return min(t[1],o[1])
results.sort(key=score,reverse=True)
print('=== TOP (both N>=80, ranked by min(train_pf,oos_pf) @0.25 taker) ===',flush=True)
for r in results[:25]:
    print(r[0],'buf',r[1],'ema',r[2],r[3],'sl',r[4],'tp',r[5],'| TRAIN',r[6],'| OOS',r[7],flush=True)
