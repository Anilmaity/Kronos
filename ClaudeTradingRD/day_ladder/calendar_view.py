"""Calendar of daily profit and loss for each strategy version over the last two calendar months, from $10,000."""
import json
import pandas as pd
from data import load_m1
from range_scalp import prep
import ping_pong, range_dyn, hedge_avg

d = prep(load_m1())                      # features are computed on the full history, so they are warm on day one
MONTHS = 2; last = d.index[-1]; SINCE = (last.to_period("M") - (MONTHS - 1)).start_time.tz_localize("UTC"); d = d[d.index >= SINCE]
RUNS = {
    "Two-sided ping-pong (12-pt targets, 1% loss limit)": lambda: ping_pong.run(d, ping_pong.P(T=12.0, G=8.0, K=5, flip=False, er_max=0.3)),
    "Dynamic range scalper (4-hour limit)": lambda: range_dyn.run(d, range_dyn.P(K=4, step=1.5, tpa=2.0, decay=0.7, er_exit=9)),
    "Dynamic range scalper (10-minute stop)": lambda: range_dyn.run(d, range_dyn.P(K=4, step=1.5, tpa=2.0, decay=0.7, er_exit=9, max_hold=10)),
    "Buy and sell together (hedge-and-average)": lambda: hedge_avg.run(d, hedge_avg.P(be="side", tpa=2.0, step=2.5, K=4, max_hold=60)),
}
out = {}
for name, f in RUNS.items():
    t, dd = f(); n = t.groupby("day").size(); w = t[t.pnl > 0].groupby("day").size()
    out[name] = [dict(d=k, start=round(float(r.start), 2), usd=round(float(r.end - r.start), 2), pct=round(float(r.pct), 2), n=int(n.get(k, 0)), w=int(w.get(k, 0))) for k, r in dd.iterrows() if n.get(k, 0)]
    print(name, len(out[name]), "days", round(sum(x["usd"] for x in out[name])))
# the trader's real account, for comparison (USD only; the balance was swept daily so % is not meaningful)
x = pd.read_csv("../xm_real/trades.csv", parse_dates=["close_time"]); x["day"] = x.close_time.dt.strftime("%Y-%m-%d")
out["XM Real trader (actual, USD)"] = [dict(d=k, usd=round(float(g.net.sum()), 2), pct=None, n=len(g), w=int((g.net > 0).sum())) for k, g in x.groupby("day")]

html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily P&L Calendar</title><style>
:root{--bg:#DBDBDB;--card:#ECECEC;--ink:#111;--mute:#555;--up:#089981;--dn:#C62828}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:20px 16px 40px}
h1{font-size:20px;margin:0 0 4px}p.sub{margin:0 0 14px;color:var(--mute)}
.bar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px}select,button{font:inherit;padding:6px 10px;border:1px solid #999;border-radius:6px;background:#fff;color:var(--ink)}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}.kpi{background:var(--card);border-radius:8px;padding:8px 12px;min-width:110px}.kpi b{display:block;font-size:17px;font-variant-numeric:tabular-nums}.kpi span{color:var(--mute);font-size:12px}
.months{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:16px}
.m{background:var(--card);border-radius:10px;padding:10px}.m h2{font-size:14px;margin:0 0 8px;display:flex;justify-content:space-between}.m h2 em{font-style:normal;font-variant-numeric:tabular-nums}
.g{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.h{font-size:11px;color:var(--mute);text-align:center}
.c{min-height:84px;border-radius:6px;padding:5px 6px;font-size:12px;white-space:nowrap;background:#E2E2E2;overflow:hidden;font-variant-numeric:tabular-nums}
.c .n{color:var(--mute)}.c .v{font-weight:700;font-size:15px;margin-top:3px}.c .p{font-size:12.5px;font-weight:600}.c .s{color:var(--mute);font-size:11px;margin-top:2px}.c.x{background:transparent}.c.t{outline:2px solid #111}
.up{color:var(--up)}.dn{color:var(--dn)}.note{color:var(--mute);margin-top:16px;max-width:900px}
</style></head><body>
<h1>Daily profit and loss</h1><p class="sub">Gold strategies run from $10,000 on __CUT__, FundingPips cost (0.25 pt). None of these days were used to choose the settings. Outlined days are the XM Real trader's own trading days.</p>
<div class="bar"><label>Strategy <select id="s"></select></label></div>
<div class="kpis" id="k"></div><div class="months" id="m"></div>
<p class="note">Each cell shows the day's profit or loss in dollars, the same as a percentage of that day's starting balance, and trades won out of trades closed. Dates are UTC days. Sunday cells are the short session after the market reopens.</p>
<script>
const D=__DATA__, TR=new Set(D["XM Real trader (actual, USD)"].map(x=>x.d)), S=document.getElementById("s");
Object.keys(D).forEach(k=>S.add(new Option(k,k)));
const sg=v=>v>0?"+":v<0?"−":"", usd=v=>sg(v)+"$"+Math.abs(v).toLocaleString("en",{minimumFractionDigits:2,maximumFractionDigits:2}), pct=v=>v==null?"":sg(v)+Math.abs(v).toFixed(2)+"%";
function draw(){const r=D[S.value], hasP=r[0].pct!=null, by=Object.fromEntries(r.map(x=>[x.d,x])), key=hasP?"pct":"usd", vals=r.map(x=>x[key]), mx=Math.max(...vals.map(Math.abs))||1;
 const tot=r.reduce((a,x)=>a+x.usd,0), wins=r.filter(x=>x.usd>0).length, tr=r.reduce((a,x)=>a+x.n,0), tw=r.reduce((a,x)=>a+x.w,0), best=r.reduce((a,x)=>x.usd>a.usd?x:a), worst=r.reduce((a,x)=>x.usd<a.usd?x:a);
 const both=x=>usd(x.usd)+(hasP?" ("+pct(x.pct)+")":"");
 document.getElementById("k").innerHTML=[["Net",usd(tot)+(hasP?" ("+pct(tot/100)+")":"")],["Trading days",r.length],["Winning days",wins+" ("+Math.round(wins/r.length*100)+"%)"],["Best day",both(best)],["Worst day",both(worst)],["Trades won",tw+" of "+tr]].map(([a,b])=>`<div class="kpi"><b>${b}</b><span>${a}</span></div>`).join("");
 const ms=[...new Set(r.map(x=>x.d.slice(0,7)))]; let h="";
 for(const m of ms){const [y,mo]=m.split("-").map(Number), first=new Date(Date.UTC(y,mo-1,1)), n=new Date(Date.UTC(y,mo,0)).getUTCDate(), off=(first.getUTCDay()+6)%7;
  const mr=r.filter(x=>x.d.startsWith(m)), mt=mr.reduce((a,x)=>a+x.usd,0), mp=hasP?mt/(mr[0].start||1)*100:null;
  h+=`<div class="m"><h2><span>${first.toLocaleString("en",{month:"long",year:"numeric",timeZone:"UTC"})}</span><em class="${mt>=0?"up":"dn"}">${usd(mt)}${hasP?" ("+pct(mp)+")":""}</em></h2><div class="g">`+["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(x=>`<div class="h">${x}</div>`).join("")+"<div class='c x'></div>".repeat(off);
  for(let d=1;d<=n;d++){const k=m+"-"+String(d).padStart(2,"0"), x=by[k]; if(!x){h+=`<div class="c${TR.has(k)?" t":""}"><div class="n">${d}</div></div>`;continue}
   const v=x[key], a=Math.min(1,Math.abs(v)/mx)*0.7+0.12, col=v>0?`rgba(8,153,129,${a})`:v<0?`rgba(198,40,40,${a})`:"#E2E2E2";
   h+=`<div class="c${TR.has(k)?" t":""}" style="background:${col}"><div class="n" style="color:#222">${d}</div><div class="v">${usd(x.usd)}</div>${hasP?`<div class="p">${pct(x.pct)}</div>`:""}<div class="s" style="color:#222">${x.w} of ${x.n} won</div></div>`}
  h+="</div></div>"} document.getElementById("m").innerHTML=h}
S.onchange=draw; draw();
</script></body></html>"""
open("pnl_calendar.html", "w").write(html.replace("__DATA__", json.dumps(out)).replace("__CUT__", SINCE.strftime("%-d %B %Y")))
print("wrote pnl_calendar.html")
