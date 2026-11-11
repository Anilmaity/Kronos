"""Rebuild the account on a 5-second grid and at every deal.

Outputs (results/ unless noted):
  ../performance/equity_curve.csv   5 s grid: time, balance, credit, floating, equity, net_lots, gross_lots, margin_level, ...
  events.csv                        exact state just BEFORE every trade deal (replay, no price needed)
  stopouts.csv                      the 34 stop-out deals: broker-reported equity/margin (from the deal comment) vs this model
  02_reconstruct.md                 checks

Conventions
  grid row `time` = T: everything with deal time <= T has happened; marks = last S5 close at or before T
  (S5 bar labelled t covers [t, t+5) so its close is stamped t+5), shifted onto XM's quote by the measured basis.
  floating: longs marked on bid, shorts on ask.  equity = balance + credit + floating.
  margin (MT5 retail-hedging, hedged-margin = 0 on this account, verified below):
      |long_lots - short_lots| * 100 oz * VWAP-open-price(of the larger leg) / 1000
  margin_level = equity / margin * 100 (blank when margin = 0).  XM stop-out level is 20 %.
"""
import re
import numpy as np
import pandas as pd
from common import load_deals, load_positions, load_s5, xm_quotes, OUT, HERE, OZ, LEV, md

d, pos, s5 = load_deals(), load_positions(), load_s5()
q = xm_quotes(s5)


def margin_of(ll, sl, lpx, spx):
    """ll/sl = long/short lots, lpx/spx = sum(lots*entry) per leg."""
    net = ll - sl
    vw = np.where(net > 0, lpx / np.where(ll > 0, ll, 1), spx / np.where(sl > 0, sl, 1))
    return np.abs(net) * OZ * vw / LEV


# ---------------------------------------------------------------- exact event replay
entry = pos.set_index("position_id").entry.to_dict()
sgn = pos.set_index("position_id").sgn.to_dict()
bal = cred = 0.0
book = {}                                    # position_id -> (sgn, lots, entry)
ev = []
for r in d.itertuples():
    if r.type == "DEAL_TYPE_CREDIT":
        cred += r.profit; continue
    if r.type == "DEAL_TYPE_BALANCE":
        bal += r.profit; continue
    pid = int(r.positionId)
    L = [v for v in book.values() if v[0] > 0]; S = [v for v in book.values() if v[0] < 0]
    ll, sl = sum(v[1] for v in L), sum(v[1] for v in S)
    lpx, spx = sum(v[1] * v[2] for v in L), sum(v[1] * v[2] for v in S)
    ev.append(dict(deal_id=r.id, time=r.time, position_id=pid, deal_type=r.type, entry_type=r.entryType, reason=r.reason,
                   volume=r.volume, price=r.price, cash=r.cash, comment=r.comment if isinstance(r.comment, str) else "",
                   bal_before=bal, credit_before=cred, n_long=len(L), n_short=len(S), long_lots=ll, short_lots=sl,
                   long_vwap=lpx / ll if ll else np.nan, short_vwap=spx / sl if sl else np.nan,
                   margin_before=float(margin_of(ll, sl, lpx, spx))))
    if r.entryType == "DEAL_ENTRY_IN":
        book[pid] = (sgn[pid], r.volume, r.price)
    else:
        book.pop(pid)
    bal += r.cash
assert not book, "positions left open"
ev = pd.DataFrame(ev)
ev.to_csv(OUT / "events.csv", index=False)
acct_end = dict(balance=round(bal, 2), credit=round(cred, 2))

# ---------------------------------------------------------------- stop-outs vs the broker's own numbers
so = ev[ev.reason == "DEAL_REASON_SO"].copy()
m = so.comment.str.extract(r"\[so (-?[\d.]+)%/(-?[\d.]+)/(-?[\d.]+)\]").astype(float)
so["brk_level"], so["brk_equity"], so["brk_margin"] = m[0], m[1], m[2]
so["brk_floating"] = so.brk_equity - so.bal_before - so.credit_before
so["margin_err"] = so.margin_before - so.brk_margin
so.to_csv(OUT / "stopouts.csv", index=False)

# ---------------------------------------------------------------- 5 s grid
t0 = d.time.min().floor("5s")
t1 = d.time.max().ceil("5s") + pd.Timedelta(seconds=5)
grid = pd.date_range(t0, t1, freq="5s")
qe = q.copy(); qe.index = qe.index + pd.Timedelta(seconds=5)          # stamp bars by their END
px = qe.reindex(grid, method="ffill")
last_bar_end = pd.DatetimeIndex(pd.Series(qe.index, index=qe.index).reindex(grid, method="ffill"))
mkt_open = np.asarray((grid - last_bar_end) <= pd.Timedelta(seconds=60))
has_bar = grid.isin(qe.index)
g = pd.DataFrame(index=grid)
dt = d.time.values
cb = np.concatenate([[0], np.cumsum(np.where(d.type == "DEAL_TYPE_CREDIT", 0, d.cash))])
cc = np.concatenate([[0], np.cumsum(np.where(d.type == "DEAL_TYPE_CREDIT", d.profit, 0))])
istrade = d.symbol.notna().values
cp = np.concatenate([[0], np.cumsum(np.where(istrade, d.cash, 0))])
k = np.searchsorted(dt, grid.values, side="right")
g["balance"], g["credit"], g["realised_pnl"] = cb[k], cc[k], cp[k]

n = len(grid)
z = lambda: np.zeros(n)
ll, sl, lpx, spx, nl, ns = z(), z(), z(), z(), z(), z()
for p in pos.itertuples():
    a = np.searchsorted(grid.values, p.open_time.to_datetime64(), side="left")     # first T >= open
    b = np.searchsorted(grid.values, p.close_time.to_datetime64(), side="left")    # first T >= close (excluded)
    if p.sgn > 0:
        ll[a:b] += p.volume; lpx[a:b] += p.volume * p.entry; nl[a:b] += 1
    else:
        sl[a:b] += p.volume; spx[a:b] += p.volume * p.entry; ns[a:b] += 1
ll, sl = ll.round(4), sl.round(4)
fl = lambda bid, ask: OZ * ((ll * bid - lpx) + (spx - sl * ask))
g["floating"] = fl(px.bid_close.values, px.ask_close.values)
g["equity"] = g.balance + g.credit + g.floating
g["net_lots"], g["gross_lots"] = (ll - sl).round(2), (ll + sl).round(2)
g["margin"] = margin_of(ll, sl, lpx, spx)
g["margin_level"] = np.where(g.margin > 0, g.equity / g.margin.where(g.margin > 0) * 100, np.nan)
g["long_lots"], g["short_lots"], g["n_long"], g["n_short"] = ll, sl, nl.astype(int), ns.astype(int)
g["bid"], g["ask"] = px.bid_close.values, px.ask_close.values
# worst mark inside the bar that ends at T (equity is linear in price -> extreme is at the bar low or the bar high);
# only meaningful where a real bar ends at T
f_lo = fl(px.bid_low.values, px.ask_low.values); f_hi = fl(px.bid_high.values, px.ask_high.values)
worst = np.minimum(np.minimum(f_lo, f_hi), g.floating.values)
g["equity_low"] = g.balance + g.credit + np.where(has_bar, worst, g.floating.values)
g["market_open"] = mkt_open
g["pnl_incl_floating"] = g.realised_pnl + g.floating
g.index.name = "time"
cols = ["balance", "credit", "floating", "equity", "net_lots", "gross_lots", "margin_level", "margin", "long_lots", "short_lots",
        "n_long", "n_short", "bid", "ask", "equity_low", "realised_pnl", "pnl_incl_floating", "market_open"]
g[cols].round(4).to_csv(HERE / "equity_curve.csv")

# ---------------------------------------------------------------- checks
out = ["## Reconstruction checks", "",
       f"grid: {grid[0]} .. {grid[-1]}  ({n:,} rows, {int(mkt_open.sum()):,} with a live quote within 60 s)",
       f"end state from replay: balance {acct_end['balance']}, credit {acct_end['credit']} (broker account_information: balance 0, credit 2.97)",
       f"grid end: balance {g.balance.iloc[-1]:.2f} credit {g.credit.iloc[-1]:.2f} floating {g.floating.iloc[-1]:.2f}",
       f"realised trading P&L (profit+swap+commission over all trade deals): {cp[-1]:.2f}", "",
       "### margin model vs the broker's own stop-out comments `[so level%/equity/margin]` (state just before each SO deal)",
       f"n = {len(so)}; margin error (model - broker): median {so.margin_err.median():.3f}, max |err| {so.margin_err.abs().max():.3f} USD", ""]
# grid equity just before each SO vs the broker's equity
gi = np.searchsorted(grid.values, so.time.values, side="left") - 1
so["grid_time"] = grid[gi]; so["grid_equity"] = g.equity.values[gi]; so["grid_equity_low_next"] = g.equity_low.values[gi + 1]
so["grid_level"] = g.margin_level.values[gi]
so["eq_err"] = so.grid_equity - so.brk_equity
show = so[["time", "position_id", "deal_type", "volume", "price", "cash", "long_lots", "short_lots", "bal_before", "credit_before",
           "brk_equity", "brk_margin", "brk_level", "margin_before", "grid_equity", "grid_equity_low_next", "grid_level"]].copy()
show["time"] = show.time.dt.strftime("%m-%d %H:%M:%S.%f").str[:-3]
out += [md(show, ".2f", index=False), "",
        f"grid equity (last 5 s row before the SO) minus broker equity at the SO: median {so.eq_err.median():.2f}, "
        f"IQR {so.eq_err.quantile(.25):.2f}..{so.eq_err.quantile(.75):.2f}  (news-bar SOs excluded from nothing; see table)"]
so.to_csv(OUT / "stopouts.csv", index=False)
(OUT / "02_reconstruct.md").write_text("\n".join(out))
print("\n".join(out))
assert abs(acct_end["balance"]) < 0.01 and abs(acct_end["credit"] - 2.97) < 0.01
