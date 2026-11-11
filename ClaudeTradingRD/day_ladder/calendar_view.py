"""Calendar of daily profit and loss for each strategy version over the last two calendar months, from $10,000.
Click a day to see that day's 1-minute gold candles with every trade drawn on them."""
import json
import warnings
import pandas as pd
from data import load_m1
from range_scalp import prep
import ping_pong, range_dyn, hedge_avg

warnings.simplefilter("ignore")
raw = load_m1(); d = prep(raw)           # features are computed on the full history, so they are warm on day one
MONTHS = 2; SINCE = (d.index[-1].to_period("M") - (MONTHS - 1)).start_time.tz_localize("UTC"); d = d[d.index >= SINCE]; raw = raw[raw.index >= SINCE]
PP = dict(T=12.0, G=8.0, K=5, flip=False, er_max=0.3)
FIT = json.load(open("fit_days_best_twosided.json"))["kw"]
ASIA = json.load(open("fit_asia_best.json"))["kw"]
RUNS = {
    "Asia session only (00-08 UTC), fitted to the trader's Asia results": lambda: ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, **ASIA)),
    "Fitted, $2,000 daily limit + 4-hour time stop": lambda: ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, day_loss_usd=2000, max_hold=240, **FIT)),
    "Fitted, $2,000 daily limit + 10-minute time stop": lambda: ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, day_loss_usd=2000, max_hold=10, **FIT)),
    "Fitted to the trader's 4-9 Nov results, $2,000 daily loss limit": lambda: ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, day_loss_usd=2000, **FIT)),
    "Fitted to the trader's 4-9 Nov results, no loss limit": lambda: ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, **FIT)),
    "Ping-pong, 0.04-lot clips, close all at -$480 open loss": lambda: ping_pong.run(d, ping_pong.P(lot=0.04, risk_pct=4.8, **PP)),
    "Ping-pong, 0.04-lot clips, no loss limit (as the trader traded)": lambda: ping_pong.run(d, ping_pong.P(lot=0.04, stop=False, day_floor=-1e9, **PP)),
    "Ping-pong, 0.01-lot clips (1% loss limit)": lambda: ping_pong.run(d, ping_pong.P(**PP)),
    "Dynamic range scalper (4-hour limit)": lambda: range_dyn.run(d, range_dyn.P(K=4, step=1.5, tpa=2.0, decay=0.7, er_exit=9)),
    "Dynamic range scalper (10-minute stop)": lambda: range_dyn.run(d, range_dyn.P(K=4, step=1.5, tpa=2.0, decay=0.7, er_exit=9, max_hold=10)),
    "Buy and sell together (hedge-and-average)": lambda: hedge_avg.run(d, hedge_avg.P(be="side", tpa=2.0, step=2.5, K=4, max_hold=60)),
}
ts = lambda x: pd.Timestamp(x).tz_convert("UTC").strftime("%Y-%m-%d %H:%M")

def clips(t):
    """One record per clip: open time, close time, side, entry, exit, USD, exit reason, lots."""
    if "e" in t:                                                         # ping_pong
        return [dict(o=ts(r.t), c=ts(r.exit_t), s=int(r.side), e=round(r.e, 2), x=round(r.x, 2), p=round(r.pnl, 2), w=r.why, l=r.lot) for r in t.itertuples()]
    if "fills" in t:                                                     # range_dyn: a basket of fills sharing one exit
        return [dict(o=ts(ft), c=ts(r.exit_t), s=int(r.side), e=round(fp, 2), x=round(r.exit_px, 2), p=round((r.exit_px - fp) * r.side * r.lot * 100, 2), w=r.why, l=r.lot)
                for r in t.itertuples() for ft, fp in zip(r.fill_t, r.fills)]
    return []                                                            # hedge_avg keeps no per-clip prices

out, tr = {}, {}
for name, f in RUNS.items():
    t, dd = f(); n = t.groupby("day").size(); w = t[t.pnl > 0].groupby("day").size()
    out[name] = [dict(d=k, start=round(float(r.start), 2), usd=round(float(r.end - r.start), 2), pct=round(float(r.pct), 2), n=int(n.get(k, 0)), w=int(w.get(k, 0))) for k, r in dd.iterrows() if n.get(k, 0)]
    tr[name] = clips(t)
    print(name, len(out[name]), "days", round(sum(x["usd"] for x in out[name])), "| clips", len(tr[name]))
# the trader's real account, for comparison (USD only; the balance was swept daily so % is not meaningful)
x = pd.read_csv("../xm_real/trades.csv", parse_dates=["open_time", "close_time"]); x["day"] = x.close_time.dt.strftime("%Y-%m-%d")
TRADER = "XM Real trader (actual, USD)"
out[TRADER] = [dict(d=k, usd=round(float(g.net.sum()), 2), pct=None, n=len(g), w=int((g.net > 0).sum())) for k, g in x.groupby("day")]
tr[TRADER] = [dict(o=ts(r.open_time), c=ts(r.close_time), s=1 if r.side == "BUY" else -1, e=round(r.entry, 2), x=round(r.exit, 2), p=round(r.net, 2),
                   w={"DEAL_REASON_TP": "target", "DEAL_REASON_SO": "margin stop-out"}.get(r.exit_reason, "closed by hand"), l=r.volume) for r in x.itertuples()]
# 1-minute candles per UTC day: [first-minute epoch ms, minute offsets, open, high, low, close]
candles = {}
for k, g in raw.groupby(raw.index.strftime("%Y-%m-%d")):
    t0 = int(g.index[0].timestamp() * 1000)
    candles[k] = [t0, [int((i.timestamp() * 1000 - t0) // 60000) for i in g.index]] + [[round(float(v), 2) for v in g[c]] for c in ("open", "high", "low", "close")]

html = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily P&L Calendar</title><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>
:root{--bg:#DBDBDB;--card:#ECECEC;--ink:#111;--mute:#555;--up:#089981;--dn:#C62828}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:20px 16px 40px}
h1{font-size:20px;margin:0 0 4px}p.sub{margin:0 0 14px;color:var(--mute)}
.bar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px}select,button{font:inherit;padding:6px 10px;border:1px solid #999;border-radius:6px;background:#fff;color:var(--ink)}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}.kpi{background:var(--card);border-radius:8px;padding:8px 12px;min-width:110px}.kpi b{display:block;font-size:17px;font-variant-numeric:tabular-nums}.kpi span{color:var(--mute);font-size:12px}
.months{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:16px}
.m{background:var(--card);border-radius:10px;padding:10px}.m h2{font-size:14px;margin:0 0 8px;display:flex;justify-content:space-between}.m h2 em{font-style:normal;font-variant-numeric:tabular-nums}
.g{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.h{font-size:11px;color:var(--mute);text-align:center}
.c{min-height:84px;border-radius:6px;padding:5px 6px;font-size:12px;white-space:nowrap;background:#E2E2E2;overflow:hidden;font-variant-numeric:tabular-nums}
.c.k{cursor:pointer}.c.k:hover{filter:brightness(0.93)}.c.sel{box-shadow:0 0 0 3px #1565C0 inset}
.c .n{color:var(--mute)}.c .v{font-weight:700;font-size:15px;margin-top:3px}.c .p{font-size:12.5px;font-weight:600}.c .s{color:var(--mute);font-size:11px;margin-top:2px}.c.x{background:transparent}.c.t{outline:2px solid #111}
.up{color:var(--up)}.dn{color:var(--dn)}.note{color:var(--mute);margin-top:16px;max-width:900px}
#day{background:var(--card);border-radius:10px;padding:12px;margin-top:18px;display:none}#day h2{font-size:15px;margin:0 0 2px}#day p{margin:0 0 6px;color:var(--mute)}#ch{height:600px}
</style></head><body>
<h1>Daily profit and loss</h1><p class="sub">Gold strategies run from $10,000 on __CUT__, FundingPips cost (0.25 pt). None of these days were used to choose the settings, except 4, 5, 6 and 9 Nov for the two "Fitted" versions. Outlined days are the XM Real trader's own trading days. Click a day to see its trades on the chart.</p>
<div class="bar"><label>Strategy <select id="s"></select></label></div>
<div class="kpis" id="k"></div><div class="months" id="m"></div>
<div id="day"><h2 id="dt"></h2><p id="dp"></p><div id="ch"></div></div>
<p class="note">Each cell shows the day's profit or loss in dollars, the same as a percentage of that day's starting balance, and trades won out of trades closed. Dates and chart times are UTC. The day's figure counts trades by the day they closed; the chart also draws trades that were opened that day and closed later.</p>
<script>
const D=__DATA__, T=__TRADES__, C=__CANDLES__, TR=new Set(D["XM Real trader (actual, USD)"].map(x=>x.d)), S=document.getElementById("s");
Object.keys(D).forEach(k=>S.add(new Option(k,k)));
const sg=v=>v>0?"+":v<0?"−":"", usd=v=>sg(v)+"$"+Math.abs(v).toLocaleString("en",{minimumFractionDigits:2,maximumFractionDigits:2}), pct=v=>v==null?"":sg(v)+Math.abs(v).toFixed(2)+"%";
let cur=null;
function draw(){const r=D[S.value], hasP=r[0].pct!=null, by=Object.fromEntries(r.map(x=>[x.d,x])), key=hasP?"pct":"usd", vals=r.map(x=>x[key]), mx=Math.max(...vals.map(Math.abs))||1;
 const tot=r.reduce((a,x)=>a+x.usd,0), wins=r.filter(x=>x.usd>0).length, tr=r.reduce((a,x)=>a+x.n,0), tw=r.reduce((a,x)=>a+x.w,0), best=r.reduce((a,x)=>x.usd>a.usd?x:a), worst=r.reduce((a,x)=>x.usd<a.usd?x:a);
 const both=x=>usd(x.usd)+(hasP?" ("+pct(x.pct)+")":"");
 document.getElementById("k").innerHTML=[["Net",usd(tot)+(hasP?" ("+pct(tot/100)+")":"")],["Trading days",r.length],["Winning days",wins+" ("+Math.round(wins/r.length*100)+"%)"],["Best day",both(best)],["Worst day",both(worst)],["Trades won",tw+" of "+tr]].map(([a,b])=>`<div class="kpi"><b>${b}</b><span>${a}</span></div>`).join("");
 const ms=[...new Set(Object.keys(C).map(x=>x.slice(0,7)))]; let h="";
 for(const m of ms){const [y,mo]=m.split("-").map(Number), first=new Date(Date.UTC(y,mo-1,1)), n=new Date(Date.UTC(y,mo,0)).getUTCDate(), off=(first.getUTCDay()+6)%7;
  const mr=r.filter(x=>x.d.startsWith(m)), mt=mr.reduce((a,x)=>a+x.usd,0), mp=hasP&&mr.length?mt/(mr[0].start||1)*100:null;
  h+=`<div class="m"><h2><span>${first.toLocaleString("en",{month:"long",year:"numeric",timeZone:"UTC"})}</span><em class="${mt>=0?"up":"dn"}">${usd(mt)}${mp!=null?" ("+pct(mp)+")":""}</em></h2><div class="g">`+["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(x=>`<div class="h">${x}</div>`).join("")+"<div class='c x'></div>".repeat(off);
  for(let d=1;d<=n;d++){const k=m+"-"+String(d).padStart(2,"0"), x=by[k], cls=(TR.has(k)?" t":"")+(C[k]?" k":"")+(k==cur?" sel":""), on=C[k]?` onclick="show('${k}')"`:"";
   if(!x){h+=`<div class="c${cls}"${on}><div class="n">${d}</div></div>`;continue}
   const v=x[key], a=Math.min(1,Math.abs(v)/mx)*0.7+0.12, col=v>0?`rgba(8,153,129,${a})`:v<0?`rgba(198,40,40,${a})`:"#E2E2E2";
   h+=`<div class="c${cls}"${on} style="background:${col}"><div class="n" style="color:#222">${d}</div><div class="v">${Math.abs(x.usd)>=1000?sg(x.usd)+"$"+Math.round(Math.abs(x.usd)).toLocaleString("en"):usd(x.usd)}</div>${hasP?`<div class="p">${pct(x.pct)}</div>`:""}<div class="s" style="color:#222">${x.w} of ${x.n} won</div></div>`}
  h+="</div></div>"} document.getElementById("m").innerHTML=h; if(cur) show(cur,true)}
function show(k,keep){cur=k; if(!keep) draw(); const c=C[k]; if(!c) return; const name=S.value, x=c[1].map(m=>new Date(c[0]+m*60000).toISOString().slice(0,16).replace("T"," "));
 const day=(D[name].find(z=>z.d==k)), cl=T[name].filter(z=>z.o.slice(0,10)==k||z.c.slice(0,10)==k), W="#1565C0", L="#C62828";
 const tr=[{type:"candlestick",x,open:c[2],high:c[3],low:c[4],close:c[5],name:"XAUUSD 1m",increasing:{line:{color:"#089981",width:1},fillcolor:"#089981"},decreasing:{line:{color:"#000",width:1},fillcolor:"#000"},hoverinfo:"x+y"}];
 for(const [win,col,nm] of [[true,W,"winning trade"],[false,L,"losing trade"]]){const xs=[],ys=[]; cl.filter(z=>(z.p>0)==win).forEach(z=>{xs.push(z.o,z.c,null);ys.push(z.e,z.x,null)}); tr.push({type:"scatter",mode:"lines",x:xs,y:ys,line:{color:col,width:1.5},name:nm,hoverinfo:"skip"})}
 for(const [s,sym,nm] of [[1,"triangle-up","buy"],[-1,"triangle-down","sell"]]){const g=cl.filter(z=>z.s==s); tr.push({type:"scatter",mode:"markers",name:nm+" entry",x:g.map(z=>z.o),y:g.map(z=>z.e),marker:{symbol:sym,size:11,color:g.map(z=>z.p>0?W:L),line:{color:"#fff",width:1}},text:g.map(z=>`${nm} ${z.l} lots @ ${z.e.toFixed(2)}<br>closed ${z.c.slice(5)} @ ${z.x.toFixed(2)} (${z.w})<br>${usd(z.p)}`),hovertemplate:"%{text}<extra></extra>"})}
 const kinds=[...new Set(cl.map(z=>z.w))], syms=["circle","x","square","diamond","star","cross"];
 kinds.forEach((w,i)=>{const g=cl.filter(z=>z.w==w); tr.push({type:"scatter",mode:"markers",name:"exit: "+w,x:g.map(z=>z.c),y:g.map(z=>z.x),marker:{symbol:syms[i%syms.length],size:8,color:g.map(z=>z.p>0?W:L),line:{color:"#fff",width:1}},text:g.map(z=>`exit (${w}) @ ${z.x.toFixed(2)}<br>${usd(z.p)}`),hovertemplate:"%{text}<extra></extra>"})});
 document.getElementById("day").style.display="block";
 document.getElementById("dt").textContent=new Date(k+"T00:00Z").toLocaleDateString("en",{weekday:"long",day:"numeric",month:"long",year:"numeric",timeZone:"UTC"})+" — "+name;
 document.getElementById("dp").textContent=(day?"Day result "+usd(day.usd)+(day.pct!=null?" ("+pct(day.pct)+")":"")+", "+day.w+" of "+day.n+" trades won. ":"No trades closed this day. ")+(T[name].length?cl.length+" trades drawn.":"This strategy keeps no per-trade prices, so only the candles are shown.");
 Plotly.react("ch",tr,{paper_bgcolor:"#ECECEC",plot_bgcolor:"#DBDBDB",font:{color:"#111"},margin:{l:60,r:20,t:10,b:40},xaxis:{rangeslider:{visible:false},showgrid:false,range:[x[0],x[x.length-1]]},yaxis:{showgrid:false,title:"gold (USD)",range:[Math.min(...c[4])-1,Math.max(...c[3])+1]},legend:{orientation:"h",y:1.02,yanchor:"bottom"},hovermode:"closest",dragmode:"pan"},{scrollZoom:true,displaylogo:false,responsive:true});
 if(!keep) document.getElementById("day").scrollIntoView({behavior:"smooth",block:"start"})}
S.onchange=draw; draw(); if(location.hash&&C[location.hash.slice(1)]) show(location.hash.slice(1));
</script></body></html>"""
open("pnl_calendar.html", "w").write(html.replace("__DATA__", json.dumps(out)).replace("__TRADES__", json.dumps(tr)).replace("__CANDLES__", json.dumps(candles, separators=(",", ":"))).replace("__CUT__", SINCE.strftime("%-d %B %Y")))
print("wrote pnl_calendar.html")
