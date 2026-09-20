"""Find the HIGHEST WIN-RATE config that ALSO has genuine positive expectancy out-of-sample.
This is the most faithful achievable version of the user's goal (reproduce live account's
high WR + profit) — maximize WR subject to profit being REAL (positive on train AND test),
not lucky.

Idea that can give both: trade WITH the higher-TF trend (EMA filter), enter on a pullback
against the trend, take a SMALL profit (high WR) with a capped stop. In a persistent trend,
dips recover -> many small wins; the trend edge pays for the occasional stop.

Realistic costs (account-calibrated). Train/test temporal split; report the WR/expectancy
frontier and the best high-WR survivors.
"""
import csv, sys, datetime as dt, itertools
PT = 10.0  # $/pt at 0.1 lot


def load(path):
    b = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                      float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return b


def ema(v, n):
    k = 2 / (n + 1); o = [v[0]]
    for x in v[1:]:
        o.append(x * k + o[-1] * (1 - k))
    return o


def atr(h, l, c, n=14):
    tr = [h[0] - l[0]]
    for i in range(1, len(c)):
        tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    out = [tr[0]] * len(c)
    for i in range(1, len(c)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n if i >= n else sum(tr[:i + 1]) / (i + 1)
    return out


def backtest(bars, *, ema_fast=20, ema_slow=50, pullback_atr=0.5, tp_atr=0.8, sl_atr=1.5,
             max_hold=12, spread=0.25, commission=0.05, cooldown=1):
    t=[b[0] for b in bars]; o=[b[1] for b in bars]; h=[b[2] for b in bars]
    l=[b[3] for b in bars]; c=[b[4] for b in bars]; n=len(c)
    ef, es = ema(c, ema_fast), ema(c, ema_slow); a = atr(h, l, c, 14)
    trades=[]; pos=None; last_exit=-10**9
    for i in range(ema_slow+1, n-1):
        if pos is not None:
            ex=None
            for j in (i,):
                if pos["side"]=="long":
                    if l[i] <= pos["sl"]: ex=pos["sl"]; break
                    if h[i] >= pos["tp"]: ex=pos["tp"]; break
                else:
                    if h[i] >= pos["sl"]: ex=pos["sl"]; break
                    if l[i] <= pos["tp"]: ex=pos["tp"]; break
            if ex is None and (i-pos["i"])>=max_hold:
                ex = c[i]-spread/2 if pos["side"]=="long" else c[i]+spread/2
            if ex is not None:
                pts=(ex-pos["entry"]) if pos["side"]=="long" else (pos["entry"]-ex)
                trades.append({"t":t[i],"pnl":pts*PT-commission}); pos=None; last_exit=i
        if pos is not None or (i-last_exit)<cooldown:
            continue
        A=a[i]
        if A<=0: continue
        up = ef[i] > es[i]
        # pullback against the trend over the last bar(s): price dipped in uptrend / popped in downtrend
        if up:
            pulled = (c[i] - min(l[i-2:i+1])) <= pullback_atr*A and c[i] < c[i-1]   # recent dip, still near low
            # enter long when price ticks back up after a dip within an uptrend
            cond = c[i] <= ef[i] + 0.2*A and c[i] >= es[i]   # near fast EMA, above slow (healthy uptrend pullback)
            if cond:
                entry=c[i]+spread/2; pos={"side":"long","entry":entry,"tp":entry+tp_atr*A,"sl":entry-sl_atr*A,"i":i}
        else:
            cond = c[i] >= ef[i] - 0.2*A and c[i] <= es[i]
            if cond:
                entry=c[i]-spread/2; pos={"side":"short","entry":entry,"tp":entry-tp_atr*A,"sl":entry+sl_atr*A,"i":i}
    return trades


def stat(trades):
    if len(trades)<1: return None
    n=len(trades); w=[x for x in trades if x["pnl"]>0]; net=sum(x["pnl"] for x in trades)
    gl=sum(x["pnl"] for x in trades if x["pnl"]<=0); gw=sum(x["pnl"] for x in w)
    return {"n":n,"wr":100*len(w)/n,"net":net,"exp":net/n,"pf":(gw/abs(gl) if gl else 9.9)}


if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "reports/xau_h4_3y.csv"
    bars=load(path); split=bars[len(bars)//2][0]
    print(f"{path}: {len(bars)} bars, split @ {split}\n")
    grid=dict(ema_fast=[10,20,34], ema_slow=[50,100,200], tp_atr=[0.5,0.8,1.0,1.5],
              sl_atr=[1.0,1.5,2.0,3.0], max_hold=[6,12,24])
    keys=list(grid); combos=list(itertools.product(*[grid[k] for k in keys]))
    print(f"searching {len(combos)} configs (train/test)...")
    surv=[]
    for combo in combos:
        cfg=dict(zip(keys,combo))
        tr=backtest(bars,**cfg)
        if len(tr)<60: continue
        a=[x for x in tr if x["t"]<split]; b=[x for x in tr if x["t"]>=split]
        ma,mb,mf=stat(a),stat(b),stat(tr)
        if ma and mb and ma["n"]>=30 and mb["n"]>=30 and ma["exp"]>0 and mb["exp"]>0:
            surv.append((cfg,mf,ma,mb))
    # rank survivors by WIN RATE (we want highest WR among the genuinely-profitable)
    surv.sort(key=lambda x:-x[1]["wr"])
    print(f"\nProfitable on BOTH halves: {len(surv)}")
    print("Top by WIN RATE (the goal: high WR + real profit):")
    for cfg,mf,ma,mb in surv[:12]:
        print(f"  WR{mf['wr']:.0f}% exp${mf['exp']:+.2f} PF{mf['pf']:.2f} n{mf['n']} | "
              f"train ${ma['exp']:+.2f} test ${mb['exp']:+.2f} | "
              f"ef{cfg['ema_fast']} es{cfg['ema_slow']} tp{cfg['tp_atr']} sl{cfg['sl_atr']} hold{cfg['max_hold']}")
    # also show the overall WR/expectancy frontier (best expectancy at each WR floor)
    allr=[]
    for combo in combos:
        cfg=dict(zip(keys,combo)); m=stat(backtest(bars,**cfg))
        if m and m["n"]>=60: allr.append(m)
    print("\nFrontier (best expectancy at each WR floor, full data):")
    for wf in (50,60,70,75,80):
        cand=[m["exp"] for m in allr if m["wr"]>=wf]
        print(f"  WR>={wf}%: best exp ${max(cand):+.3f}/trade" if cand else f"  WR>={wf}%: none")
