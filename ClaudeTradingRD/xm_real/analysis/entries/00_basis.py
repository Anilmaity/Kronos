"""Step 0 - XM GOLD vs OANDA XAU_USD price basis and clock check.

A BUY deal fills at XM ask, a SELL deal at XM bid. For each of the 356 trade deals
compare the fill with OANDA's same-side quote in the 5-second bar that contains the
deal instant. basis = XM - OANDA.  Writes basis.json (used by every later script).

Run: ../../../.venv/bin/python 00_basis.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

s5 = pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet").set_index("time").sort_index()
d = pd.read_csv(ROOT / "deals.csv")
d["time"] = pd.to_datetime(d.time, utc=True, format="ISO8601")
d = d[d.symbol.notna()].copy()
d["buy"] = d.type.eq("DEAL_TYPE_BUY")


def oanda_quote(times, buy, shift_s=0.0):
    """OANDA same-side quote for each deal: linear interp open->close inside the containing S5 bar,
    plus the bar's low/high so we can say whether the XM fill is inside OANDA's traded range."""
    t = times + pd.to_timedelta(shift_s, unit="s")
    i = s5.index.searchsorted(t, side="right") - 1
    bar_t = s5.index[i]
    age = (t - bar_t).dt.total_seconds().to_numpy()
    side = np.where(buy, "ask", "bid")
    o = np.where(buy, s5.ask_open.to_numpy()[i], s5.bid_open.to_numpy()[i])
    c = np.where(buy, s5.ask_close.to_numpy()[i], s5.bid_close.to_numpy()[i])
    lo = np.where(buy, s5.ask_low.to_numpy()[i], s5.bid_low.to_numpy()[i])
    hi = np.where(buy, s5.ask_high.to_numpy()[i], s5.bid_high.to_numpy()[i])
    frac = np.clip(age / 5.0, 0, 1)
    return o + (c - o) * frac, lo, hi, age, side


ref, lo, hi, age, _ = oanda_quote(d.time, d.buy.to_numpy())
d["age_s"] = age
d["basis"] = d.price - ref
d["outside"] = np.where(d.price > hi, d.price - hi, np.where(d.price < lo, d.price - lo, 0.0))
ok = d[d.age_s < 5]  # deal inside an existing S5 bar (no data gap)
print(f"deals {len(d)}, inside an S5 bar {len(ok)} (gap deals dropped: {len(d) - len(ok)})")

q = lambda s: {k: round(float(v), 3) for k, v in zip(
    ["n", "mean", "median", "sd", "p05", "p95"],
    [len(s), s.mean(), s.median(), s.std(), s.quantile(.05), s.quantile(.95)])}
out = {"all": q(ok.basis), "sell_at_bid": q(ok[~ok.buy].basis), "buy_at_ask": q(ok[ok.buy].basis)}
for k, v in out.items():
    print(f"{k:12s} {v}")
print("share of fills inside OANDA same-side bar range:", round((ok.outside == 0).mean(), 3),
      "| median |excess| when outside:", round(ok.outside[ok.outside != 0].abs().median(), 3))

# XM spread vs OANDA spread: basis_ask - basis_bid = XM spread - OANDA spread
i = s5.index.searchsorted(ok.time, side="right") - 1
osp = (s5.ask_close.to_numpy()[i] - s5.bid_close.to_numpy()[i])
print("OANDA spread at deal instants: median", round(float(np.median(osp)), 3), "p90", round(float(np.quantile(osp, .9)), 3))
d_sp = out["buy_at_ask"]["median"] - out["sell_at_bid"]["median"]
print("XM spread - OANDA spread (median basis_ask - median basis_bid):", round(d_sp, 3),
      "=> XM spread ~", round(float(np.median(osp)) + d_sp, 3))

# stability by day / by deal kind
ok = ok.assign(day=ok.time.dt.strftime("%m-%d"), kind=ok.entryType.str.replace("DEAL_ENTRY_", "") + "/" + ok.reason.str.replace("DEAL_REASON_", ""))
print(ok.groupby(["day", "buy"]).basis.agg(["count", "median", "std"]).round(3).to_string())
print(ok.groupby(["kind", "buy"]).basis.agg(["count", "median", "std"]).round(3).to_string())

# clock check: which time shift of the deal stamps minimises |basis - median| ?  (0 => stamps are UTC-exact)
print("clock check: median abs deviation of basis vs assumed deal-clock shift")
best = None
for sh in [-7200, -3600, -60, -30, -15, -10, -5, -2, -1, 0, 1, 2, 5, 10, 15, 30, 60, 3600, 7200]:
    r, _, _, a, _ = oanda_quote(d.time, d.buy.to_numpy(), sh)
    b = (d.price - r)[a < 5]
    mad = float((b - b.median()).abs().median())
    best = min(best or (9e9, 0), (mad, sh))
    print(f"  shift {sh:+6d}s  MAD {mad:.3f}  n {len(b)}")
print("best shift:", best[1], "s")

# OUT_BY deals are booked at the opposite position's open price (not a market fill) and stop-outs /
# TPs fill in fast markets, so the basis used downstream comes from the 178 ENTRY deals only.
ent = ok[ok.entryType.eq("DEAL_ENTRY_IN")]
eb, es = ent[ent.buy].basis, ent[~ent.buy].basis
print("ENTRY deals only: sell@bid", q(es), "| buy@ask", q(eb))
big = ok[(ok.basis.abs() > 1.5) & ~ok.entryType.eq("DEAL_ENTRY_OUT_BY")]
print(f"market fills more than 1.5 pt from OANDA (n={len(big)}):")
print(big[["time", "kind", "buy", "price", "basis", "outside"]].round(2).to_string())

res = {"basis_bid": round(float(es.median()), 3), "basis_ask": round(float(eb.median()), 3),
       "entry_basis_sd": round(float(ent.basis.std()), 3), "n_entry": len(ent),
       "xm_minus_oanda_spread": round(float(eb.median() - es.median()), 3),
       "oanda_spread_median": round(float(np.median(osp)), 3), "best_clock_shift_s": best[1]}
(HERE / "basis.json").write_text(json.dumps(res, indent=1))
print(res)
