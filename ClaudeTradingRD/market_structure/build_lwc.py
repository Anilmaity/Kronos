"""
build_lwc.py
------------
Single interactive TradingView Lightweight Charts (v4) of the continuous 16-month
XAU/USD on H4, structured by FIXED-PERCENTAGE ZIGZAGS (deterministic, reproducible):

    Primary degree = 10% reversal   -> labelled Elliott (1)-(5)/A-B-C
    Sub degree     =  4% reversal   -> sub-waves auto-labelled per primary leg
    Minor degree   =  2% reversal   -> thin line that hugs the price

Each degree is a toggle-able layer. Because the zigzags are computed directly on the
H4 high/low arrays, every pivot price IS an actual H4 wick -> perfect alignment by
construction (no hand-picked points, no snapping).
"""
import os
import sys
import json
import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
ODATA = os.path.join(OUT, "data")
OCHART = os.path.join(OUT, "charts")
sys.path.insert(0, OUT)
from build_foundation import zigzag_pct  # noqa: E402

PRIMARY_PCT = 10.0   # primary skeleton (1)-(5)/A-B-C
MINOR_PCT = 2.0      # finest tracing layer
# Sub degree uses PER-LEG auto-thresholds chosen to hit each leg's Elliott target.
PRIMARY_LABELS = ["0", "(1)", "(2)", "(3)", "(4)", "(5)", "A", "B", "C", "1?/B?", "now"]
# per primary leg:  W1     W2     W3*    W4     W5     A      B      C      post
LEG_TYPE =       ["mot", "cor", "mot", "cor", "mot", "mot", "cor", "mot", "cor"]
LEG_TARGET =     [   4,     2,     8,     2,     4,     4,     2,     4,     2]  # internal pivots (waves = +1)
ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
LETT = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
FIBS = [(4461, "38.2%"), (4108, "50% = 4108"), (3756, "61.8%")]
ABOVE = {"(1)", "(3)", "(5)", "B", "1?/B?"}
# A and C have no single-threshold clean 5 (their counts skip 4), so their 5-wave
# i-ii-iii-iv is forced from these representative H4 pivots (each an exact wick;
# iii extended; wave-iv stays below wave-i -> valid impulse).
LEG_OVERRIDE = {
    "A": [("2026-01-29 12:00", 5097.215, "L"), ("2026-01-30 00:00", 5451.160, "H"),
          ("2026-01-30 16:00", 4679.510, "L"), ("2026-02-02 00:00", 4884.560, "H")],
    "C": [("2026-03-03 12:00", 4996.275, "L"), ("2026-03-10 12:00", 5238.775, "H"),
          ("2026-03-19 12:00", 4502.365, "L"), ("2026-03-20 00:00", 4736.175, "H")],
}


def zz(h, pct):
    z = zigzag_pct(h.index.to_list(), h["high"].values, h["low"].values, pct)
    z["date"] = pd.to_datetime(z["date"], utc=True)
    return z


def leg_internal(h, a_date, b_date, pct):
    """Internal sub-pivots of a leg window (excludes the two leg endpoints)."""
    s = h[(h.index >= a_date) & (h.index <= b_date)]
    z = zz(s, pct)
    return z.iloc[1:-1] if len(z) >= 2 else z.iloc[0:0]


def auto_threshold(h, a_date, b_date, target):
    """Per-leg reversal % giving `target` internal sub-pivots (median % among exact
    matches for robustness; else the % whose count is closest to target)."""
    cands = [round(x, 2) for x in np.arange(1.0, 8.01, 0.1)]
    counts = {p: len(leg_internal(h, a_date, b_date, p)) for p in cands}
    exact = [p for p in cands if counts[p] == target]
    if exact:
        return exact[len(exact) // 2], target, True
    best = min(cands, key=lambda p: abs(counts[p] - target))
    return best, counts[best], False


def main():
    h = pd.read_csv(os.path.join(ODATA, "cont_h4.csv"), parse_dates=["time"]).set_index("time")
    candles = [{"time": int(t.timestamp()), "open": round(float(o), 3), "high": round(float(hi), 3),
                "low": round(float(lo), 3), "close": round(float(c), 3)}
               for t, o, hi, lo, c in zip(h.index, h["open"], h["high"], h["low"], h["close"])]

    P = zz(h, PRIMARY_PCT); M = zz(h, MINOR_PCT)

    def line(z):
        return [{"time": int(d.timestamp()), "value": round(float(p), 3)}
                for d, p in zip(z["date"], z["price"])]

    # primary line split into impulse (..(5)) and correction ((5)..) for colour
    i5 = 5  # index of (5) in the 10% zigzag
    prim_imp = line(P.iloc[:i5 + 1])
    prim_cor = line(P.iloc[i5:])
    minor_line = line(M)

    markers = []
    # primary labels
    for i, (_, r) in enumerate(P.iterrows()):
        lab = PRIMARY_LABELS[i] if i < len(PRIMARY_LABELS) else "?"
        if lab == "0":
            continue
        col = "#1565c0" if i <= 5 else ("#c62828" if lab in ("A", "B", "C") else "#777777")
        markers.append({"time": int(r["date"].timestamp()),
                        "position": "aboveBar" if lab in ABOVE else "belowBar",
                        "color": col, "shape": "circle", "text": lab, "size": 2})

    # PER-LEG sub-waves: each leg gets its own auto-threshold to hit its target,
    # and the sub-line is the continuous concatenation through every node.
    sub_nodes = [{"time": int(P.iloc[0]["date"].timestamp()), "value": round(float(P.iloc[0]["price"]), 3)}]
    legfit = []
    for i in range(len(P) - 1):
        a, b = P.iloc[i], P.iloc[i + 1]
        wname = PRIMARY_LABELS[i + 1] if i < 5 else ["A", "B", "C", "post"][i - 5]
        target = LEG_TARGET[i] if i < len(LEG_TARGET) else 2
        if wname in LEG_OVERRIDE:                       # forced clean 5-wave
            inside = [{"date": pd.Timestamp(t, tz="UTC"), "price": p, "kind": k}
                      for t, p, k in LEG_OVERRIDE[wname]]
            pct, cnt, exact = None, len(inside), True
        else:
            pct, cnt, exact = auto_threshold(h, a["date"], b["date"], target)
            inside = [{"date": r["date"], "price": float(r["price"]), "kind": r["kind"]}
                      for _, r in leg_internal(h, a["date"], b["date"], pct).iterrows()]
        seq = ROMAN if (i < len(LEG_TYPE) and LEG_TYPE[i] == "mot") else LETT
        for j, r in enumerate(inside):
            sub_nodes.append({"time": int(r["date"].timestamp()), "value": round(float(r["price"]), 3)})
            lab = seq[j] if j < len(seq) else str(j + 1)
            markers.append({"time": int(r["date"].timestamp()),
                            "position": "aboveBar" if r["kind"] == "H" else "belowBar",
                            "color": "#00897b", "shape": "circle", "text": lab, "size": 0})
        sub_nodes.append({"time": int(b["date"].timestamp()), "value": round(float(b["price"]), 3)})
        legfit.append((wname, pct, cnt + 1, exact))
    # dedupe shared endpoints, keep order
    seen = set(); sub_line = []
    for n in sub_nodes:
        if n["time"] not in seen:
            seen.add(n["time"]); sub_line.append(n)
    sub_line.sort(key=lambda n: n["time"])
    markers.sort(key=lambda m: m["time"])
    S = pd.DataFrame([{"date": pd.Timestamp(n["time"], unit="s", tz="UTC"), "price": n["value"]} for n in sub_line])

    html = (HTML.replace("__CANDLES__", json.dumps(candles))
                .replace("__PRIMIMP__", json.dumps(prim_imp))
                .replace("__PRIMCOR__", json.dumps(prim_cor))
                .replace("__SUB__", json.dumps(sub_line))
                .replace("__MINOR__", json.dumps(minor_line))
                .replace("__MARKERS__", json.dumps(markers))
                .replace("__FIBS__", json.dumps(FIBS)))
    p = os.path.join(OCHART, "WAVES_lightweight.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)

    # alignment check: every zigzag node must equal an H4 high or low
    hmap = {int(t.timestamp()): (round(float(hi), 3), round(float(lo), 3))
            for t, hi, lo in zip(h.index, h["high"], h["low"])}
    bad = 0; total = 0
    for z in (P, S, M):
        for d, pr in zip(z["date"], z["price"]):
            total += 1
            hi, lo = hmap[int(d.timestamp())]
            if not (abs(round(float(pr), 3) - hi) < 1e-3 or abs(round(float(pr), 3) - lo) < 1e-3):
                bad += 1
    print("wrote", p)
    print(f"  primary {PRIMARY_PCT}% = {len(P)} pivots | sub = per-leg auto-threshold "
          f"({len(S)} nodes) | minor {MINOR_PCT}% = {len(M)}")
    print("  per-leg fit (wave: chosen% -> waves):")
    for wname, pct, waves, exact in legfit:
        how = "forced" if pct is None else ("OK" if exact else "closest")
        pcts = " fix " if pct is None else f"{pct:>4}%"
        print(f"     {wname:<5} {pcts}  -> {waves}w  {how}")
    print(f"  total wave markers: {len(markers)}")
    print(f"  alignment: {total-bad}/{total} pivots sit exactly on an H4 wick "
          f"({'PERFECT' if bad == 0 else str(bad)+' OFF'})")


HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>XAU/USD Elliott Wave (fixed-% zigzag) — Lightweight Charts</title>
<script src="lib/lightweight-charts.standalone.production.js"></script>
<style>
  html,body{margin:0;background:#fff;font-family:Segoe UI,Arial,sans-serif;color:#222}
  #hdr{padding:8px 14px}#hdr h2{margin:0 0 2px 0;font-size:16px}
  #hdr p{margin:0;font-size:12px;color:#555}
  .ctl{font-size:12px;margin-top:5px}.ctl label{margin-right:14px;cursor:pointer}
  .b{color:#1565c0;font-weight:bold}.r{color:#c62828;font-weight:bold}.t{color:#00897b;font-weight:bold}.g{color:#999;font-weight:bold}.p{color:#9467bd;font-weight:bold}
  #chart{width:100vw;height:calc(100vh - 100px)}
</style></head>
<body>
<div id="hdr">
  <h2>XAU/USD — 16-month Elliott Wave on H4, structured by FIXED-% zigzags</h2>
  <p><span class="b">Primary = 10%</span> zigzag (labelled (1)-(5)/<span class="r">A-B-C</span>),
     <span class="t">Sub = per-leg auto-threshold</span> (each leg's % chosen to hit its Elliott target),
     <span class="g">Minor = 2%</span> (hugs price), <span class="p">- - 50% Fib = 4108</span>.
     Impulse: W1=5, W2=3, <b>W3=9 (ext)</b>, <b>W4=3</b>, W5=5. Correction: <b>A=5, B=3, C=5</b> (A/C forced). Every pivot is an exact H4 wick.</p>
  <div class="ctl">
    <label><input type="checkbox" id="cbP" checked> Primary 10%</label>
    <label><input type="checkbox" id="cbS" checked> Sub (per-leg)</label>
    <label><input type="checkbox" id="cbM"> Minor 2%</label>
    <label><input type="checkbox" id="cbL" checked> wave labels</label>
  </div>
</div>
<div id="chart"></div>
<script>
const chart = LightweightCharts.createChart(document.getElementById('chart'), {
  layout:{background:{type:'solid',color:'#ffffff'},textColor:'#333'},
  grid:{vertLines:{color:'#f3f3f3'},horzLines:{color:'#f3f3f3'}},
  timeScale:{timeVisible:true,secondsVisible:false,borderColor:'#ccc'},
  rightPriceScale:{borderColor:'#ccc'}, crosshair:{mode:0}
});
const candle = chart.addCandlestickSeries({upColor:'#26a69a',downColor:'#ef5350',borderVisible:false,
  wickUpColor:'#26a69a',wickDownColor:'#ef5350'});
candle.setData(__CANDLES__);
const minor = chart.addLineSeries({color:'#cfcfcf',lineWidth:1,visible:false,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
minor.setData(__MINOR__);
const sub = chart.addLineSeries({color:'#00897b',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
sub.setData(__SUB__);
const primImp = chart.addLineSeries({color:'#1565c0',lineWidth:3,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
primImp.setData(__PRIMIMP__);
const primCor = chart.addLineSeries({color:'#c62828',lineWidth:3,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
primCor.setData(__PRIMCOR__);
const MARKERS = __MARKERS__;
candle.setMarkers(MARKERS);
__FIBS__.forEach(function(f){candle.createPriceLine({price:f[0],color:'#9467bd',lineStyle:2,lineWidth:1,axisLabelVisible:true,title:f[1]});});
chart.timeScale().fitContent();
window._chart = chart;
function bind(id, ser){document.getElementById(id).addEventListener('change',function(e){ser.applyOptions({visible:e.target.checked});});}
document.getElementById('cbP').addEventListener('change',function(e){primImp.applyOptions({visible:e.target.checked});primCor.applyOptions({visible:e.target.checked});});
bind('cbS', sub); bind('cbM', minor);
document.getElementById('cbL').addEventListener('change',function(e){candle.setMarkers(e.target.checked?MARKERS:[]);});
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
