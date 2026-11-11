"""Account value on the 5-second grid -> equity_5s.parquet, plus the checks that say how far to trust it.

Run:  ../../../.venv/bin/python 02_equity.py     (after 01_basis.py)

balance   = running sum of every BALANCE deal and every trade deal's profit+swap+commission
credit    = running sum of CREDIT deals (XM bonus - tradable as margin, not withdrawable)
floating  = sum over open positions, marked at the XM-equivalent quote
            (longs at OANDA bid + bid_basis, shorts at OANDA ask + ask_basis), 100 oz per lot
equity    = balance + floating                 (own money marked to market)
equity_mt5= balance + credit + floating        (what the MT5 app shows as Equity)
net_lots  = buy lots - sell lots open
Grid instant = close of each OANDA S5 bar (bar start + 5 s). No bar (no ticks / market shut) = no row.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OZ = 100  # XM GOLD contract size; verified below against broker profit
LEVERAGE = 1000

basis = json.loads((HERE / "basis.json").read_text())
d = pd.read_csv(ROOT / "deals.csv")
d["time"] = pd.to_datetime(d["time"], utc=True, format="ISO8601")
d = d.sort_values(["time", "id"]).reset_index(drop=True)
t = pd.read_csv(ROOT / "trades.csv")
for c in ("open_time", "close_time"):
    t[c] = pd.to_datetime(t[c], utc=True, format="ISO8601")
s5 = pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet")
s5 = s5[s5.time >= "2026-11-03 22:00"].reset_index(drop=True)

sgn = t.side.map({"BUY": 1, "SELL": -1}).values
# contract-size check: broker profit == pts * lots * 100 on every position (close-by legs book the pair's P&L on one leg)
_m = (t.exit_entry_type != "DEAL_ENTRY_OUT_BY").values
assert np.allclose(((t.exit - t.entry) * sgn * t.volume * OZ)[_m], t.profit[_m], atol=0.011), "contract size is not 100 oz/lot"

g = (s5.time + pd.Timedelta(seconds=5)).values  # grid instants (bar closes)
xm_bid = s5.bid_close.values + basis["bid_basis"]
xm_ask = s5.ask_close.values + basis["ask_basis"]

cash = (d.profit + d.swap.fillna(0) + d.commission.fillna(0)).values
is_credit = (d.type == "DEAL_TYPE_CREDIT").values
dt = d.time.values
bal_cum, cr_cum = np.cumsum(np.where(is_credit, 0, cash)), np.cumsum(np.where(is_credit, cash, 0))
k = np.searchsorted(dt, g, side="right") - 1  # last deal at or before each grid instant
balance = np.where(k >= 0, bal_cum[k], 0.0)
credit = np.where(k >= 0, cr_cum[k], 0.0)

floating, net_lots, gross_lots = np.zeros(len(g)), np.zeros(len(g)), np.zeros(len(g))
last_float = np.full(len(t), np.nan)  # floating P&L of each position at the last grid instant before it closed
for i, p in t.iterrows():
    a, b = np.searchsorted(g, p.open_time.to_datetime64(), "left"), np.searchsorted(g, p.close_time.to_datetime64(), "left")
    px = xm_bid[a:b] if p.side == "BUY" else xm_ask[a:b]
    f = (px - p.entry) * sgn[i] * p.volume * OZ
    floating[a:b] += f
    net_lots[a:b] += sgn[i] * p.volume
    gross_lots[a:b] += p.volume
    if b > a:
        last_float[i] = f[-1]

eq = pd.DataFrame(dict(
    time=pd.to_datetime(g, utc=True), balance=balance.round(2), credit=credit.round(2), floating=floating.round(2),
    equity=(balance + floating).round(2), equity_mt5=(balance + credit + floating).round(2),
    net_lots=net_lots.round(2), gross_lots=gross_lots.round(2), xm_bid=xm_bid.round(3), xm_ask=xm_ask.round(3),
))
eq.to_parquet(HERE / "equity_5s.parquet", index=False)

# ---------------------------------------------------------------- checks
print(f"grid rows {len(eq)}  {eq.time.iloc[0]} .. {eq.time.iloc[-1]}")
print(f"rows with a position open: {(eq.gross_lots > 0).sum()} ({(eq.gross_lots > 0).mean():.1%} of market time since 11-03 22:00)")
print(f"final balance {bal_cum[-1]:.2f}  final credit {cr_cum[-1]:.2f}  min balance {bal_cum.min():.2f}")
flat = eq[eq.gross_lots == 0]
assert (flat.equity == flat.balance).all()

# 1. reconstruction error: floating P&L one grid step (<=5 s) before the close vs what the broker booked
t["last_float"] = last_float
real = t[t.exit_entry_type != "DEAL_ENTRY_OUT_BY"].copy()
real["err"] = real.last_float - real.profit
print("\n[check 1] floating at last grid instant before close - booked profit (USD per position, close-by legs excluded)")
for name, grp in [("all", real), ("manual", real[real.exit_reason == "DEAL_REASON_MOBILE"]),
                  ("TP", real[real.exit_reason == "DEAL_REASON_TP"]), ("stop-out", real[real.exit_reason == "DEAL_REASON_SO"])]:
    e = grp.err.dropna()
    print(f"  {name:9s} n={len(e):3d}  median {e.median():+6.2f}  mean {e.mean():+6.2f}  MAE {e.abs().mean():5.2f}  p95|err| {e.abs().quantile(.95):6.2f}  worst {e.abs().max():7.2f}")

# 2. margin level just before each stop-out cluster (XM stop-out level is 20% of used margin)
print("\n[check 2] MT5 equity / used margin at the last grid instant before each stop-out cluster")
so = t[t.exit_reason == "DEAL_REASON_SO"].sort_values("close_time")
so["cluster"] = (so.close_time.diff() > pd.Timedelta(minutes=2)).cumsum()
for _, c in so.groupby("cluster"):
    j = np.searchsorted(g, c.close_time.min().to_datetime64(), "left") - 1
    r = eq.iloc[j]
    # ponytail: margin = gross lots * 100 oz * price / leverage, no hedged-margin discount; refine if XM's hedge rule matters
    margin = r.gross_lots * OZ * (r.xm_bid + r.xm_ask) / 2 / LEVERAGE
    print(f"  {c.close_time.min():%m-%d %H:%M:%S}  n={len(c):2d}  booked {c.net.sum():9.2f}  equity_mt5 before {r.equity_mt5:8.2f}"
          f"  gross {r.gross_lots:.2f} net {r.net_lots:+.2f} lots  margin {margin:6.1f}  level {r.equity_mt5 / margin:6.0%}")

# 3. cash vs trading result
cf = d[d.type == "DEAL_TYPE_BALANCE"].copy()
tag = lambda s: cf[cf.comment.str.startswith(s)].profit.sum()
dep, fee, wd = tag("CD-") + tag("Transfer"), tag("EXP05"), tag("CW-") + tag("CN-ERR")
print("\n[check 3] cash accounting (BALANCE deals)")
print(f"  deposits (CD-* + transfer in)        {dep:9.2f}")
print(f"  deposit-fee rebates (EXP05)          {fee:9.2f}")
print(f"  withdrawals net of reversed attempts {wd:9.2f}")
print(f"  bonus credit converted to cover negative balance (EXP06) {tag('EXP06'):8.2f}")
print(f"  negative-balance reset by broker (EXP01)                 {tag('EXP01'):8.2f}")
print(f"  trading net (all positions)          {t.net.sum():9.2f}")
print(f"  sum of everything = final balance    {cf.profit.sum() + t.net.sum():9.2f}")
print(f"  operator cash result = withdrawals - deposits = {-wd - dep:.2f}")
print(f"  peak balance {eq.balance.max():.2f} at {eq.time[eq.balance.idxmax()]}   lowest equity_mt5 {eq.equity_mt5.min():.2f} at {eq.time[eq.equity_mt5.idxmin()]}")
