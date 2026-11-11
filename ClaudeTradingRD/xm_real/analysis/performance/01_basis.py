"""Measure the XM GOLD vs OANDA XAU_USD price basis at the exact deal instants.

A BUY deal fills on XM's ask, a SELL deal on XM's bid. Reference = OANDA bid/ask inside the S5 bar that
contains the deal timestamp (linear open->close interpolation by position inside the bar).
Only market (MOBILE) deals are used: TP/SO fills and close-by legs are not free-market quotes.
Fast bars (ask range > 1.0 pt in the 5 s) are dropped: the within-bar position is unknowable there.
Writes results/basis.json  {"bid": XMbid-OANDAbid, "ask": XMask-OANDAask}  (medians).
"""
import json
import numpy as np
import pandas as pd
from common import load_deals, load_s5, OUT, md

d, s5 = load_deals(), load_s5()
x = d[d.symbol.notna()].copy()
i = s5.index.searchsorted(x.time, side="right") - 1
bar = s5.iloc[i]
x["lag"] = (x.time.values - bar.index.values) / np.timedelta64(1, "s")
f = (x.lag / 5).clip(0, 1).values
buy = (x.type == "DEAL_TYPE_BUY").values
o_bid = bar.bid_open.values + (bar.bid_close.values - bar.bid_open.values) * f
o_ask = bar.ask_open.values + (bar.ask_close.values - bar.ask_open.values) * f
x["ref"] = np.where(buy, o_ask, o_bid)
x["basis"] = x.price - x.ref
x["bar_rng"] = bar.ask_high.values - bar.ask_low.values
x["oanda_spread"] = o_ask - o_bid
x["side"] = np.where(buy, "ask (BUY deals)", "bid (SELL deals)")
x["day"] = x.time.dt.strftime("%m-%d")

mkt = x[(x.reason == "DEAL_REASON_MOBILE") & (x.entryType != "DEAL_ENTRY_OUT_BY") & (x.lag <= 5)]
calm = mkt[mkt.bar_rng <= 1.0]
q = lambda s: pd.Series({"n": len(s), "median": s.median(), "mean": s.mean(), "sd": s.std(),
                         "p10": s.quantile(.1), "p90": s.quantile(.9)})
allt = calm.groupby("side").basis.apply(q).unstack()
byday = calm.groupby(["day", "side"]).basis.apply(q).unstack()[["n", "median", "sd"]]
bid, ask = float(allt.loc["bid (SELL deals)", "median"]), float(allt.loc["ask (BUY deals)", "median"])
# bootstrap CI of the two medians
rng = np.random.default_rng(7)
ci = {}
for k, g in calm.groupby("side"):
    v = g.basis.values
    bs = np.median(rng.choice(v, (4000, len(v))), axis=1)
    ci[k] = (float(np.quantile(bs, .025)), float(np.quantile(bs, .975)))
res = dict(bid=round(bid, 3), ask=round(ask, 3), mid=round((bid + ask) / 2, 3),
           xm_minus_oanda_spread=round(ask - bid, 3), oanda_spread_median_at_deals=round(float(calm.oanda_spread.median()), 3),
           n_bid=int(allt.loc["bid (SELL deals)", "n"]), n_ask=int(allt.loc["ask (BUY deals)", "n"]),
           ci95_bid=[round(v, 3) for v in ci["bid (SELL deals)"]], ci95_ask=[round(v, 3) for v in ci["ask (BUY deals)"]],
           n_market_deals=len(mkt), n_calm=len(calm))
json.dump(res, open(OUT / "basis.json", "w"), indent=1)

out = ["## Basis: XM GOLD fill minus OANDA XAU_USD quote on the same side (points = USD/oz)", "",
       f"market (MOBILE, non close-by) deals: {len(mkt)}; calm-bar subset used (S5 ask range <= 1.0): {len(calm)}", "",
       md(allt, ".3f"), "", "bootstrap 95% CI of the medians: " + json.dumps(ci), "", "### by day", md(byday, ".3f"), "",
       "### all deal kinds (not used for the estimate; TP/SO in news bars are interpolation artefacts)",
       md(x.groupby(["reason", "entryType", "side"]).basis.apply(q).unstack()[["n", "median", "mean", "sd"]], ".3f"), "",
       "result: " + json.dumps(res)]
(OUT / "01_basis.md").write_text("\n".join(out))
print("\n".join(out))
