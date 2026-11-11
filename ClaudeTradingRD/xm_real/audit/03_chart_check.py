"""Audit step 3: do the chart's trade markers, candles, balance step and equity line agree with the ledger?
Fixed rule: every 35th position by open time (#35, #70, #105, #140, #175 of 178), ledger = deals_raw.json.
The chart is read back from the published HTML itself (analysis/chart/xm_real_trades_equity.html), not from its inputs.
Run after 01_headline.py: ../../.venv/bin/python 03_chart_check.py -> out/03_chart_check.txt
"""
import json, base64, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
_L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); _L.append(s)
IST = pd.Timedelta(hours=5, minutes=30)

h = open(f"{ROOT}/analysis/chart/xm_real_trades_equity.html").read()
data, _ = json.JSONDecoder().raw_decode(h, h.find("[", h.find("Plotly.newPlot(")))
def arr(v):
    if isinstance(v, dict) and "bdata" in v: return np.frombuffer(base64.b64decode(v["bdata"]), dtype=np.dtype(v["dtype"]))
    return np.array(v, dtype=float)
utc = lambda xs: pd.to_datetime(pd.Series(xs), format="ISO8601").dt.tz_localize("UTC") - IST          # chart x is IST wall time
ent = pd.concat([pd.DataFrame({"t": utc(tr["x"]), "y": arr(tr["y"]), "text": tr["text"]}) for tr in data if tr.get("name") == "entry"], ignore_index=True)
ext = pd.concat([pd.DataFrame({"t": utc(tr["x"]), "y": arr(tr["y"]), "text": tr["text"]}) for tr in data if tr.get("name") == "exit"], ignore_index=True)
by = {tr["name"]: tr for tr in data if tr.get("name")}
c1 = by["candles 1m"]; cnd = pd.DataFrame({"t": utc(c1["x"]) - pd.Timedelta(seconds=30), "o": arr(c1["open"]), "h": arr(c1["high"]), "l": arr(c1["low"]), "c": arr(c1["close"])})
bal = pd.DataFrame({"t": utc(by["Balance (realised)"]["x"]), "v": arr(by["Balance (realised)"]["y"])})
eqn = [k for k in by if k.startswith("Equity = balance")][0]
eq = pd.DataFrame({"t": utc(by[eqn]["x"]), "v": arr(by[eqn]["y"])})
P(f"chart read back: {len(ent)} entry markers, {len(ext)} exit markers, {len(cnd)} 1m candles, {len(bal)} balance points, {len(eq)} equity points")

# ledger from the raw deals
raw = sorted(json.load(open(f"{ROOT}/deals_raw.json"))["deals"], key=lambda x: (x["time"], int(x["id"])))
pos = pd.read_csv(f"{HERE}/out/positions_from_deals.csv", parse_dates=["t_in", "t_out"])
s5 = pd.read_parquet(f"{ROOT}/xau_s5_2026-11-03_now_ba.parquet"); st = s5.time.values.astype("datetime64[ns]").astype("int64")
m1 = pd.read_parquet(f"{ROOT}/xau_m1_2026-07-16_now_mba.parquet").set_index("time")
BID_B, ASK_B = -0.053, 0.063                                                       # my own basis medians (01_headline.py)

def my_balance(ts):
    return sum(x["profit"] + x.get("swap", 0) + x.get("commission", 0) for x in raw if x["type"] != "DEAL_TYPE_CREDIT" and pd.Timestamp(x["time"]) <= ts)
def my_equity(ts):
    """balance + floating of every position open at ts, marked at the close of the S5 bar ending at ts (longs bid, shorts ask)."""
    i = int(np.searchsorted(st, ts.value - 5 * 10**9, "right") - 1)
    o = pos[(pos.t_in <= ts) & (pos.t_out > ts)]
    px = np.where(o.side > 0, s5.bid_close[i] + BID_B, s5.ask_close[i] + ASK_B)
    return my_balance(ts) + float(((px - o.entry) * o.side * o.vol * 100).sum()), len(o), float(o.vol.sum())

fails = 0
for k in (34, 69, 104, 139, 174):
    r = pos.iloc[k]
    P(f"\n#{k+1} position {r.pid} {'BUY' if r.side>0 else 'SELL'} {r.vol} lots | in {r.t_in} @ {r.entry} | out {r.t_out} @ {r.exit} | {r.kind} | profit {r.profit:.2f}")
    e = ent[(abs((ent.t - r.t_in).dt.total_seconds()) < 0.002) & (abs(ent.y - r.entry) < 0.006)]
    x = ext[(abs((ext.t - r.t_out).dt.total_seconds()) < 0.002) & (abs(ext.y - r.exit) < 0.006)]
    ok_e, ok_x = len(e) >= 1, len(x) >= 1
    txt = (e.text.iloc[0] if ok_e else "")
    ok_txt = (f"#{r.pid}" in txt) and (f"{r.net:,.2f}".replace("-", "") in txt.replace("−", ""))
    P(f"  entry marker at the deal time and price: {'OK' if ok_e else 'MISSING'} | exit marker: {'OK' if ok_x else 'MISSING'} | hover text names the position and its net: {'OK' if ok_txt else 'NO'}")
    cb = cnd[cnd.t == r.t_in.floor("1min")]
    if len(cb):
        cc = cb.iloc[0]; mm = m1.loc[r.t_in.floor("1min")]
        inside = cc.l - 0.35 <= r.entry <= cc.h + 0.35
        same = abs(cc.h - mm.high) < 0.02 and abs(cc.l - mm.low) < 0.02 and abs(cc.c - mm.close) < 0.02
        P(f"  1m candle under the entry: chart L {cc.l:.2f} H {cc.h:.2f} | OANDA M1 mid L {mm.low:.2f} H {mm.high:.2f} -> candle is the data: {'OK' if same else 'NO'}; entry inside candle +-0.35: {'OK' if inside else 'NO'}")
    else:
        inside = same = False; P("  1m candle under the entry: NOT FOUND")
    cb_ = bal[bal.t <= r.t_out].v.iloc[-1]; mb = my_balance(r.t_out)
    ok_b = abs(cb_ - mb) < 0.011
    P(f"  balance step at the close: chart {cb_:.2f} | ledger replay {mb:.2f} -> {'OK' if ok_b else 'MISMATCH'}")
    mid = (r.t_in + (r.t_out - r.t_in) / 2).ceil("1min")
    if not (r.t_in <= mid < r.t_out): mid = r.t_in.ceil("1min")
    ce = eq[eq.t == mid]
    if len(ce) and r.t_in <= mid < r.t_out:
        me, npos, lots = my_equity(mid); tol = 1.0 + 0.6 * lots * 100 * 0.05      # 1 USD + 3 cents/oz of basis and bar-pick slack
        ok_q = abs(ce.v.iloc[0] - me) <= tol
        P(f"  equity line at {mid} ({npos} positions, {lots:.2f} lots open): chart {ce.v.iloc[0]:.2f} | my rebuild {me:.2f} | diff {ce.v.iloc[0]-me:+.2f} (tolerance {tol:.2f}) -> {'OK' if ok_q else 'MISMATCH'}")
    else:
        ok_q = True; P(f"  equity line: no chart sample on a minute boundary while this position was open (held {(r.t_out-r.t_in).total_seconds():.0f} s) - not checked")
    fails += not (ok_e and ok_x and ok_txt and inside and same and ok_b and ok_q)

P("\n== whole-chart checks ==")
m_e = sum(((abs((ent.t - r.t_in).dt.total_seconds()) < 0.002) & (abs(ent.y - r.entry) < 0.006)).any() for r in pos.itertuples())
m_x = sum(((abs((ext.t - r.t_out).dt.total_seconds()) < 0.002) & (abs(ext.y - r.exit) < 0.006)).any() for r in pos.itertuples())
P(f"positions with an entry marker at their own deal time/price: {m_e} of {len(pos)} | with an exit marker at their own close time/price: {m_x} of {len(pos)}")
P("  (the 8 close-by legs are drawn as 4 pairs: entry = first leg's open, 'exit' square = the hedge leg's OPEN time and price, i.e. the moment the loss was locked, not the close-by deal)")
P(f"final chart balance {bal.v.iloc[-1]:.2f} (ledger 0.00) | chart balance max {bal.v.max():.2f} (ledger peak 1919.01)")
d = np.array([eq.v[i] - my_equity(eq.t[i])[0] for i in range(0, len(eq), 97)])
P(f"equity line vs my rebuild on every 97th plotted minute (n={len(d)}): median |diff| {np.median(abs(d)):.2f} USD, p95 {np.percentile(abs(d),95):.2f}, max {abs(d).max():.2f}")
P(f"\nRESULT: {5 - fails} of 5 sampled positions agree on every check")
open(f"{HERE}/out/03_chart_check.txt", "w").write("\n".join(_L) + "\n")
