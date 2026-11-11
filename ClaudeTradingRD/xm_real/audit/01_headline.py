"""Audit step 1: re-derive the headline numbers from deals_raw.json only (no trades.csv, no analysis code).
Run: ../../.venv/bin/python 01_headline.py   -> prints, and writes out/01_headline.txt
"""
import json, re, sys, os
from collections import defaultdict
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.makedirs(f"{HERE}/out", exist_ok=True)
_lines = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); _lines.append(s)

raw = json.load(open(f"{ROOT}/deals_raw.json"))
deals = sorted(raw["deals"], key=lambda x: (x["time"], int(x["id"])))
T = lambda s: pd.Timestamp(s)

# ---------- positions straight from deals ----------
pos = {}
for x in deals:
    if "symbol" not in x or x.get("symbol") is None:
        continue
    p = pos.setdefault(x["positionId"], dict(pid=x["positionId"], ins=[], outs=[]))
    (p["ins"] if x["entryType"] == "DEAL_ENTRY_IN" else p["outs"]).append(x)
rows = []
for pid, p in pos.items():
    assert len(p["ins"]) == 1, pid
    i = p["ins"][0]; o = p["outs"]
    assert len(o) == 1, (pid, len(o))          # every position: exactly one IN and one OUT deal
    o = o[0]
    assert abs(i["volume"] - o["volume"]) < 1e-9
    side = 1 if i["type"] == "DEAL_TYPE_BUY" else -1
    kind = ("closeby" if o["entryType"] == "DEAL_ENTRY_OUT_BY" else
            {"DEAL_REASON_TP": "tp", "DEAL_REASON_SO": "so", "DEAL_REASON_MOBILE": "hand"}[o["reason"]])
    rows.append(dict(pid=pid, side=side, vol=i["volume"], t_in=T(i["time"]), t_out=T(o["time"]),
                     entry=i["price"], exit=o["price"], profit=i["profit"] + o["profit"],
                     swap=i["swap"] + o["swap"], comm=i["commission"] + o["commission"], kind=kind,
                     tp=o.get("takeProfit"), sl=o.get("stopLoss"), comment=o.get("comment")))
t = pd.DataFrame(rows).sort_values(["t_in", "pid"]).reset_index(drop=True)
t["net"] = t.profit + t.swap + t.comm
t["hold_min"] = (t.t_out - t.t_in).dt.total_seconds() / 60
t["pts_usd"] = t.profit / (t.vol * 100)          # points implied by booked profit (close-by pair counted once)
t.to_csv(f"{HERE}/out/positions_from_deals.csv", index=False)

P("== 1. counts ==")
P("deals", len(deals), "| positions", len(t), "| first deal", deals[0]["time"], "| last", deals[-1]["time"])
P("trading days (UTC dates with a trade deal):", sorted({x['time'][:10] for x in deals if x.get('symbol')}))

P("\n== 2. net / win rate / PF ==")
w, l, z = t[t.net > 0], t[t.net < 0], t[t.net == 0]
P(f"net {t.net.sum():.2f} | gross profit(deal.profit) {t.profit.sum():.2f} | swap {t.swap.sum():.2f} | commission {t.comm.sum():.2f}")
P(f"winners {len(w)} losers {len(l)} zero {len(z)} | win% {len(w)/len(t)*100:.1f} | PF {w.net.sum()/-l.net.sum():.3f}")
P(f"avg win {w.net.mean():.2f} avg loss {l.net.mean():.2f} | breakeven WR at that payoff {(-l.net.mean())/(w.net.mean()-l.net.mean())*100:.1f}%")
P(f"median hold min {t.hold_min.median():.1f} | expectancy/pos {t.net.mean():.2f} sd {t.net.std(ddof=1):.2f} t {t.net.mean()/(t.net.std(ddof=1)/np.sqrt(len(t))):.2f}")
# win rate excluding the 4 zero-profit close-by legs (174 'trades')
P(f"win% on 174 (dropping the 4 zero legs of close-by pairs): {len(w)/(len(t)-len(z))*100:.1f}")

P("\n== 3. daily net by close date ==")
for d, g in t.groupby(t.t_out.dt.date):
    P(f"  {d}  n={len(g):3d}  net={g.net.sum():9.2f}")

P("\n== 4. exit kind ==")
for k, g in t.groupby("kind"):
    P(f"  {k:8s} n={len(g):3d} net={g.net.sum():9.2f} win%={100*(g.net>0).mean():5.1f} winners={int((g.net>0).sum())} losers={int((g.net<0).sum())}")
P(f"  gross loss {l.net.sum():.2f}; SO share of gross loss {t[(t.kind=='so')&(t.net<0)].net.sum()/l.net.sum()*100:.1f}%")
P(f"  losers closed by hand: {len(l[l.kind=='hand'])} ({l[l.kind=='hand'].net.sum():.2f})")
P(f"  TP set on {t.tp.notna().sum()} | SL set on {t.sl.notna().sum()}")

P("\n== 5. side ==")
for s, g in t.groupby("side"):
    P(f"  {'BUY' if s>0 else 'SELL'} n={len(g)} net={g.net.sum():.2f} win%={100*(g.net>0).mean():.1f}")

P("\n== 6. lot size ==")
P("  lots:", t.vol.round(2).value_counts().sort_index().to_dict())
a, b, c = t[t.vol.round(2) == 0.04], t[t.vol.round(2) > 0.04], t[t.vol.round(2) < 0.04]
P(f"  0.04: n={len(a)} net={a.net.sum():.2f} | >0.04: n={len(b)} net={b.net.sum():.2f} | <0.04: n={len(c)} net={c.net.sum():.2f}")
P(f"  two worst positions: {t.nsmallest(2,'net')[['t_in','vol','side','net']].values.tolist()}")
P(f"  every position at 0.04 lots: pts {t.pts_usd.sum():.1f} -> USD {t.pts_usd.sum()*4:.2f}  (pts via exit-entry, both close-by legs: {((t.exit-t.entry)*t.side).sum():.1f})")

P("\n== 7. cash ==")
cash = [x for x in deals if x["type"] in ("DEAL_TYPE_BALANCE", "DEAL_TYPE_CREDIT")]
grp = defaultdict(float); cnt = defaultdict(int)
for x in cash:
    c = x.get("comment") or ""
    key = (x["type"][10:], re.split(r"[ \-]", c)[0] if not c.startswith("Credit") and not c.startswith("Transfer") else c.split(" ")[0] + ("-In" if "In" in c else "-Out" if "Out" in c else ""))
    grp[key] += x["profit"]; cnt[key] += 1
for k in sorted(grp): P(f"  {k}: n={cnt[k]} sum={grp[k]:.2f}")
bal = lambda pred: sum(x["profit"] for x in cash if x["type"] == "DEAL_TYPE_BALANCE" and pred(x.get("comment") or ""))
dep_ext = bal(lambda c: c.startswith("CD-")); transfer = bal(lambda c: c.startswith("Transfer"))
wd = bal(lambda c: c.startswith("CW-") and "ERR" not in c); err = bal(lambda c: "ERR" in c)
exp05 = bal(lambda c: c.startswith("EXP05")); exp06 = bal(lambda c: c.startswith("EXP06")); exp01 = bal(lambda c: c.startswith("EXP01"))
P(f"  deposits external {dep_ext:.2f} + transfer {transfer:.2f} = {dep_ext+transfer:.2f} | withdrawals {wd:.2f} | ERR pairs net {err:.2f}")
P(f"  EXP05 deposit top-ups {exp05:.2f} | EXP06 credit->balance (bonus burnt) {exp06:.2f} | EXP01 negative-balance reset {exp01:.2f}")
P(f"  owner net cash = {-wd-(dep_ext+transfer):.2f} ; identity trading+bonus+reset+topup = {t.net.sum()+exp06+exp01+exp05:.2f}")
balance = sum(x["profit"] + x.get("swap", 0) + x.get("commission", 0) for x in deals if x["type"] != "DEAL_TYPE_CREDIT")
credit = sum(x["profit"] for x in deals if x["type"] == "DEAL_TYPE_CREDIT")
P(f"  replayed final balance {balance:.2f} (broker {raw['account_information']['balance']}) | credit {credit:.2f} (broker {raw['account_information']['credit']:.2f})")
wk1 = lambda x: x["time"] < "2026-11-07"
P(f"  phase 11-04..06: deposits {sum(x['profit'] for x in cash if x['type']=='DEAL_TYPE_BALANCE' and (x['comment'].startswith('CD-') or x['comment'].startswith('Transfer')) and wk1(x)):.2f}"
  f" withdrawals {sum(x['profit'] for x in cash if x['type']=='DEAL_TYPE_BALANCE' and x['comment'].startswith('CW-') and 'ERR' not in x['comment'] and wk1(x)):.2f}"
  f" trading {t[t.t_out < pd.Timestamp('2026-11-07', tz='UTC')].net.sum():.2f}")
P(f"  phase 11-09..11: deposits {sum(x['profit'] for x in cash if x['type']=='DEAL_TYPE_BALANCE' and (x['comment'].startswith('CD-') or x['comment'].startswith('Transfer')) and not wk1(x)):.2f}"
  f" trading {t[t.t_out >= pd.Timestamp('2026-11-07', tz='UTC')].net.sum():.2f}")

# running balance, peak, balance after each withdrawal
run = 0.0; peak = (-1e9, None); after_wd = []; cum_trade = 0.0; peak_trade = (-1e9, None)
for x in deals:
    if x["type"] == "DEAL_TYPE_CREDIT": continue
    run += x["profit"] + x.get("swap", 0) + x.get("commission", 0)
    if run > peak[0]: peak = (run, x["time"])
    if x.get("symbol"):
        cum_trade += x["profit"] + x.get("swap", 0) + x.get("commission", 0)
        if cum_trade > peak_trade[0]: peak_trade = (cum_trade, x["time"])
    if x["type"] == "DEAL_TYPE_BALANCE" and (x.get("comment") or "").startswith("CW-") and "ERR" not in x["comment"]:
        after_wd.append(round(run, 2))
P(f"  balance peak {peak[0]:.2f} at {peak[1]} | balance after each withdrawal {after_wd}")
P(f"  cumulative trading P&L peak {peak_trade[0]:.2f} at {peak_trade[1]} -> final {cum_trade:.2f}: drawdown {cum_trade-peak_trade[0]:.2f}")

P("\n== 8. stop-outs ==")
so = t[t.kind == "so"].sort_values("t_out")
ev = (so.t_out.diff().dt.total_seconds().fillna(0) > 300).cumsum()
P(f"  SO deals {len(so)} net {so.net.sum():.2f} | events (gap>5min) {ev.nunique()}")
for e, g in so.groupby(ev):
    P(f"    {g.t_out.iloc[0]}  n={len(g):2d} lots={g.vol.sum():.2f} net={g.net.sum():9.2f}  first comment {g.comment.iloc[0]}")

P("\n== 9. flat-to-flat episodes ==")
evs = sorted([(r.t_in, 0, +1, r.pid) for r in t.itertuples()] + [(r.t_out, 1, -1, r.pid) for r in t.itertuples()], key=lambda e: (e[0], e[1]))
# note: at identical timestamps opens are processed before closes (conservative: fewer episodes)
n_open = 0; ep = 0; ep_of = {}; maxpos = 0
for tm, _, dlt, pid in evs:
    if dlt > 0:
        if n_open == 0: ep += 1
        ep_of[pid] = ep
    n_open += dlt; maxpos = max(maxpos, n_open)
t["ep"] = t.pid.map(ep_of)
e = t.groupby("ep").agg(net=("net", "sum"), n=("pid", "size"), so=("kind", lambda s: (s == "so").any()), start=("t_in", "min"))
P(f"  episodes {len(e)} | winners {int((e.net>0).sum())} (+{e.net[e.net>0].sum():.2f}) | losers {int((e.net<0).sum())} ({e.net[e.net<0].sum():.2f}) | losers that include a stop-out {int(e.so[e.net<0].sum())}")
P(f"  mean {e.net.mean():.2f} sd {e.net.std(ddof=1):.2f} t {e.net.mean()/(e.net.std(ddof=1)/np.sqrt(len(e))):.2f}")
rng = np.random.default_rng(7); v = e.net.values
bs = rng.choice(v, (20000, len(v))).sum(1)
P(f"  bootstrap total 95% CI {np.percentile(bs,2.5):.0f}..{np.percentile(bs,97.5):.0f} | P(total<=0) {100*(bs<=0).mean():.1f}%")
# same at flat 0.04 lots
e4 = t.assign(u=t.pts_usd * 4).groupby("ep").u.sum(); v4 = e4.values
bs4 = rng.choice(v4, (20000, len(v4))).sum(1)
P(f"  flat 0.04 lots: total {v4.sum():.2f} episode t {v4.mean()/(v4.std(ddof=1)/np.sqrt(len(v4))):.2f} P(<=0) {100*(bs4<=0).mean():.1f}%")
# day-level view (6 obs)
dn = t.groupby(t.t_out.dt.date).net.sum().values
P(f"  by day (n=6): mean {dn.mean():.2f} sd {dn.std(ddof=1):.2f} t {dn.mean()/(dn.std(ddof=1)/np.sqrt(6)):.2f}")

P("\n== 10. exposure ==")
gross = netl = 0.0; mg = mn = 0.0; nb = ns = 0; mb = ms = 0; n_open = 0
vol = dict(zip(t.pid, t.vol * t.side))
for tm, _, dlt, pid in evs:
    gross += dlt * abs(vol[pid]); netl += dlt * vol[pid]
    if vol[pid] > 0: nb += dlt
    else: ns += dlt
    mg = max(mg, gross); mn = max(mn, abs(netl)); mb = max(mb, nb); ms = max(ms, ns)
P(f"  max positions {maxpos} | max gross lots {mg:.2f} | max |net| lots {mn:.2f} | max buys {mb} max sells {ms}")

# ---------- price-relative: basis first, then MAE ----------
s5 = pd.read_parquet(f"{ROOT}/xau_s5_2026-11-03_now_ba.parquet")
st = s5.time.values.astype("datetime64[ns]").astype("int64")
def bar_at(ts):                       # index of the S5 bar containing ts (or last before)
    return int(np.searchsorted(st, ts.value, "right") - 1)

P("\n== 11. basis XM vs OANDA (manual market deals only; quote = S5 bar containing the deal: close of that bar) ==")
res = defaultdict(list)
for x in deals:
    if not x.get("symbol") or x["reason"] != "DEAL_REASON_MOBILE" or x["entryType"] == "DEAL_ENTRY_OUT_BY": continue
    ts = T(x["time"]); i = bar_at(ts)
    if ts.value - st[i] > 5e9: continue                       # no bar covering this instant
    frac = (ts.value - st[i]) / 5e9
    if x["type"] == "DEAL_TYPE_BUY":                            # buy fills at XM ask
        q = s5.ask_open[i] + frac * (s5.ask_close[i] - s5.ask_open[i]); res["ask"].append(x["price"] - q)
        res["ask_inbar"].append(s5.ask_low[i] - 0.5 <= x["price"] <= s5.ask_high[i] + 0.5)
    else:
        q = s5.bid_open[i] + frac * (s5.bid_close[i] - s5.bid_open[i]); res["bid"].append(x["price"] - q)
        res["bid_inbar"].append(s5.bid_low[i] - 0.5 <= x["price"] <= s5.bid_high[i] + 0.5)
for k in ("bid", "ask"):
    v = np.array(res[k]); se = v.std(ddof=1) / np.sqrt(len(v))
    P(f"  XM {k} - OANDA {k}: n={len(v)} mean {v.mean():+.3f} median {np.median(v):+.3f} sd {v.std(ddof=1):.3f} 95% CI {v.mean()-1.96*se:+.3f}..{v.mean()+1.96*se:+.3f} | within bar+-0.5: {np.mean(res[k+'_inbar'])*100:.0f}%")
BID_B, ASK_B = float(np.median(res["bid"])), float(np.median(res["ask"]))
P(f"  OANDA median spread at those instants ~ {np.median(s5.ask_close-s5.bid_close):.2f}; implied XM spread ~ {np.median(s5.ask_close-s5.bid_close)+ASK_B-BID_B:.2f}")
# stop-out fills vs OANDA 5-s bar on 11-10 13:30
for x in deals:
    if x.get("reason") == "DEAL_REASON_SO" and x["time"].startswith("2026-11-10T13:30"):
        i = bar_at(T(x["time"])); P(f"  SO fill {x['time']} price {x['price']} | OANDA bar {s5.time[i]} bid low {s5.bid_low[i]} high {s5.bid_high[i]} -> fill - bid_low = {x['price']-s5.bid_low[i]:+.2f}")

P("\n== 12. MAE / loss deferral on basis-corrected S5 (XM bid = OANDA bid + b_bid, XM ask = OANDA ask + b_ask) ==")
mae = []
for r in t.itertuples():
    i0, i1 = bar_at(r.t_in), bar_at(r.t_out)
    sl = slice(i0, i1 + 1)
    if r.side > 0: worst = (s5.bid_low.values[sl] + BID_B).min() - r.entry            # long marked at bid
    else:          worst = r.entry - (s5.ask_high.values[sl] + ASK_B).max()           # short marked at ask
    mae.append(min(worst, 0.0))
t["mae"] = mae
W = t[t.net > 0]
for thr in (5, 10, 20, 30):
    g = W[W.mae <= -thr]
    P(f"  winners first >= {thr} pts under water: {len(g)} of {len(W)} ({100*len(g)/len(W):.1f}%) = {100*g.net.sum()/W.net.sum():.1f}% of gross profit")
P(f"  winners: median gain pts {((W.exit-W.entry)*W.side).median():.2f}, median MAE {W.mae.median():.2f}")
P("  NOTE: MAE uses the whole first and last 5-s bar, so it is an upper bound on adverse excursion by up to one bar each end.")

P("\n== 13. hard stop laid over the real trades (stop at entry-X on the corrected S5 path; fill at the stop, no slippage; real lots) ==")
for X in (3, 5, 8, 10, 15, 20, 25, 30, 50):
    stopped = t.mae <= -X
    usd = np.where(stopped, -X * t.vol * 100, t.profit).sum()
    P(f"  SL {X:2d} pts: net USD {usd:9.2f} | stopped {int(stopped.sum())} of which real winners {int((stopped & (t.net>0)).sum())}")
P("  (close-by legs: the zero leg keeps profit 0 unless stopped; this is a simplification the analysis also had to make)")

P("\n== 14. fade habit: prior 5-min move signed by trade side (first click of each decision; decision = same side within 30 s) ==")
m1 = s5.set_index("time").bid_close.resample("1min").last().dropna()
dec = t[(t.t_in.diff().dt.total_seconds().fillna(1e9) > 30) | (t.side != t.side.shift())]
sig = []
for r in dec.itertuples():
    i = bar_at(r.t_in) - 1                                   # last S5 bar closed before the click
    j = int(np.searchsorted(st, st[i] - 300 * 10**9, "right") - 1)
    sig.append(r.side * (s5.bid_close[i] - s5.bid_close[j]))
sig = np.array(sig)
P(f"  decisions {len(dec)} | mean signed prior 5-min move {sig.mean():+.2f} pts | share against the move (fade) {100*(sig<0).mean():.1f}%")

open(f"{HERE}/out/01_headline.txt", "w").write("\n".join(_lines) + "\n")
