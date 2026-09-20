"""Can a REGIME FILTER rescue the mean-reversion scalp? Tests 'in which situation
to apply'. Adds: (a) efficiency-ratio chop gate (only fade when the market is
range-bound), (b) realized-vol gate (only when there's enough movement to scalp),
(c) a hard stop, (d) a daily loss cap. Sweeps key params for robustness plateaus.
"""
import csv, sys, datetime as dt, statistics

PT = 10.0

def load(path):
    bars=[]
    with open(path,encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bars.append((dt.datetime.strptime(r["time"],"%Y-%m-%d %H:%M:%S"),
                         float(r["o"]),float(r["h"]),float(r["l"]),float(r["c"])))
    return bars

def backtest(bars,*,lookback=3,trigger=1.2,tp=1.0,sl=2.5,time_stop=60,max_pos=3,
             min_gap=1,spread=0.25,commission=0.50,
             eff_win=30,eff_max=0.35,vol_win=30,vol_min=2.5,daily_loss_cap=150.0):
    """eff_max: only enter when efficiency ratio |net|/path over eff_win < eff_max (choppy).
       vol_min: require path over vol_win >= vol_min (enough movement).
       daily_loss_cap: stop trading for the day after this realized loss."""
    closes=[b[4] for b in bars]; n=len(bars)
    trades=[]; open_pos=[]; last_entry_i=-10**9
    day_pnl={}; cur_day=None
    for i in range(n):
        t,o,h,l,c=bars[i]; dk=t.strftime("%Y-%m-%d")
        day_pnl.setdefault(dk,0.0)
        still=[]
        for p in open_pos:
            ex=None;rs=None
            if p["side"]=="sell":
                if p["sl_px"] is not None and h>=p["sl_px"]: ex,rs=p["sl_px"],"sl"
                elif l<=p["tp_px"]: ex,rs=p["tp_px"],"tp"
            else:
                if p["sl_px"] is not None and l<=p["sl_px"]: ex,rs=p["sl_px"],"sl"
                elif h>=p["tp_px"]: ex,rs=p["tp_px"],"tp"
            if ex is None and (i-p["opened_i"])>=time_stop:
                ex=c-spread/2 if p["side"]=="sell" else c+spread/2; rs="time"
            if ex is None: still.append(p); continue
            pts=(p["entry"]-ex) if p["side"]=="sell" else (ex-p["entry"])
            pnl=pts*PT-commission; trades.append({"t_in":p["opened_t"],"t_out":t,"side":p["side"],
                "pnl":pnl,"reason":rs}); day_pnl[dk]+=pnl
        open_pos=still
        if i<max(lookback,eff_win,vol_win) or len(open_pos)>=max_pos or (i-last_entry_i)<min_gap:
            continue
        if day_pnl[dk] <= -daily_loss_cap:   # daily loss cap hit -> no new entries today
            continue
        # regime gates
        seg=closes[i-eff_win:i+1]
        net=abs(seg[-1]-seg[0]); path=sum(abs(seg[j]-seg[j-1]) for j in range(1,len(seg)))
        if path<=0: continue
        eff=net/path
        vseg=closes[i-vol_win:i+1]; vpath=sum(abs(vseg[j]-vseg[j-1]) for j in range(1,len(vseg)))
        if eff>eff_max or vpath<vol_min:   # only fade in choppy + active tape
            continue
        move=closes[i]-closes[i-lookback]
        side="sell" if move>=trigger else ("buy" if move<=-trigger else None)
        if side is None: continue
        entry=c-spread/2 if side=="sell" else c+spread/2
        if side=="sell": tp_px,sl_px=entry-tp,(entry+sl if sl else None)
        else: tp_px,sl_px=entry+tp,(entry-sl if sl else None)
        open_pos.append({"side":side,"entry":entry,"tp_px":tp_px,"sl_px":sl_px,
                         "opened_i":i,"opened_t":t}); last_entry_i=i
    return trades

def stats(trades,label,start=5000.0):
    if not trades: print(f"{label}: no trades"); return None
    n=len(trades); wins=[t for t in trades if t["pnl"]>0]; losses=[t for t in trades if t["pnl"]<=0]
    net=sum(t["pnl"] for t in trades); gw=sum(t["pnl"] for t in wins); gl=sum(t["pnl"] for t in losses)
    wr=100*len(wins)/n; pf=gw/abs(gl) if gl else float("inf")
    eq=start;peak=eq;mdd=0
    for t in sorted(trades,key=lambda x:x["t_out"]): eq+=t["pnl"];peak=max(peak,eq);mdd=min(mdd,eq-peak)
    print(f"{label}: trades {n}  WR {wr:.1f}%  PF {pf:.2f}  net ${net:+.1f}  "
          f"exp ${net/n:+.3f}  maxDD ${mdd:+.0f}  worst ${min(t['pnl'] for t in trades):+.0f}")
    return {"n":n,"wr":wr,"pf":pf,"net":net,"exp":net/n,"mdd":mdd}

if __name__=="__main__":
    bars=load(sys.argv[1] if len(sys.argv)>1 else "reports/xau_m1_2026ytd.csv")
    print(f"Loaded {len(bars)} bars")
    print("\n-- regime-gated GUARDED scalp, baseline --")
    stats(backtest(bars),"  base")
    print("\n-- efficiency gate sensitivity (lower=stricter chop) --")
    for em in (0.20,0.30,0.40,0.50):
        stats(backtest(bars,eff_max=em),f"  eff_max={em}")
    print("\n-- TP/SL sensitivity --")
    for tp,sl in ((0.8,2.0),(1.0,2.5),(1.2,3.0),(1.5,2.0),(1.0,4.0)):
        stats(backtest(bars,tp=tp,sl=sl),f"  tp={tp} sl={sl}")
    print("\n-- trigger sensitivity --")
    for tg in (0.8,1.2,1.6,2.0):
        stats(backtest(bars,trigger=tg),f"  trigger={tg}")
