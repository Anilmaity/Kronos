"""Step 1 - measure the XM GOLD vs OANDA XAU_USD price basis at the 356 deal instants and write basis.json.

A BUY deal fills on XM ask, a SELL deal on XM bid. basis_side = deal price - OANDA quote of that side at the
deal instant (interpolated inside the 5-second bar). Only manual market deals (reason MOBILE, not close-by)
are used for the estimate: TP fills sit at a bar extreme by construction and stop-outs happen in spikes.
Also checks the clock alignment (dispersion vs time shift) and validates the corrected series against the
42 real TP fills.   Run: python 01_basis.py
"""
import json

import numpy as np
import pandas as pd

from common import HERE, RES, Quotes, load_deals, load_trades

pd.set_option("display.width", 200)
out = []
P = lambda *a: (print(*a), out.append(" ".join(str(x) for x in a)))

d = load_deals()
d = d[d.symbol.notna()].copy()
q = Quotes(basis={"ask": 0.0, "bid": 0.0})          # raw OANDA
d["buy"] = d.type.eq("DEAL_TYPE_BUY")
d["side"] = np.where(d.buy, "ask", "bid")
mkt = d.reason.eq("DEAL_REASON_MOBILE") & d.entryType.ne("DEAL_ENTRY_OUT_BY")


def basis(shift_s=0):
    t = d.t.values + shift_s * 10**9
    return d.price.values - np.where(d.buy, q.at(t, "ask"), q.at(t, "bid"))


P("== clock alignment: dispersion of (deal - OANDA) for manual market deals vs time shift ==")
for s in (-10, -5, -2, 0, 2, 5, 10):
    b = basis(s)[mkt]
    P(f"shift {s:+3d}s  n={mkt.sum()}  median {np.median(b):+.3f}  MAD {np.median(np.abs(b - np.median(b))):.3f}")

d["b"] = basis(0)
d["day"] = d.time.dt.strftime("%m-%d")
m = d[mkt]
est = {side: round(float(m[m.side == side].b.median()), 3) for side in ("ask", "bid")}
P("\n== basis, manual market deals (XM - OANDA, same side) ==")
P(m.groupby("side").b.describe(percentiles=[.05, .25, .5, .75, .95]).round(3).to_string())
P("\nper day:")
P(m.groupby(["day", "side"]).b.agg(["count", "median", "std"]).round(3).unstack().to_string())
spread = pd.read_parquet(HERE.parents[1] / "xau_s5_2026-11-03_now_ba.parquet")
osp = float((spread.ask_close - spread.bid_close).median())
P(f"\nESTIMATE  ask {est['ask']:+.3f}  bid {est['bid']:+.3f}  -> mid basis {(est['ask'] + est['bid']) / 2:+.3f}, "
  f"XM effective spread = OANDA spread {est['ask'] - est['bid']:+.3f} (OANDA median spread {osp:.2f})")
P("other deal kinds (not used):")
P(d[~mkt].groupby(["reason", "entryType", "side"]).b.agg(["count", "median", "min", "max"]).round(2).to_string())

json.dump({**est, "n_ask": int((m.side == "ask").sum()), "n_bid": int((m.side == "bid").sum()),
           "oanda_median_spread": round(osp, 3)}, open(HERE / "basis.json", "w"), indent=1)

# ---- validation of the corrected series against real TP fills ------------------------------------------
q = Quotes()                                         # now basis-corrected
t = load_trades()
rows = []
for r in t[t.tp.notna()].itertuples():
    i0 = q.first_bar_after(r.t0)
    fh, al, op, cl = q.path(r.sgn, r.entry, i0)
    hit = np.flatnonzero(fh >= r.tp_dist)
    t_touch = (q.T[i0 + hit[0]] if len(hit) else np.nan)
    rows.append(dict(position_id=r.position_id, reason=r.reason, tp_dist=r.tp_dist,
                     touch_minus_close_s=(t_touch - r.t1) / 1e9 if len(hit) else np.nan))
v = pd.DataFrame(rows)
tp = v[v.reason == "TP"]
P("\n== validation: first touch of the final TP on corrected S5 vs the real TP fill time (42 TP exits) ==")
P(tp.touch_minus_close_s.describe(percentiles=[.05, .25, .5, .75, .95]).round(1).to_string())
P(f"within +-5s: {(tp.touch_minus_close_s.abs() <= 5).sum()}/{len(tp)}; within +-60s: {(tp.touch_minus_close_s.abs() <= 60).sum()}/{len(tp)}")
P(tp[tp.touch_minus_close_s.abs() > 60].round(2).to_string())
non = v[(v.reason != "TP")]
early = non[non.touch_minus_close_s < -5]
P(f"\nTP-set positions NOT closed by TP: {len(non)}; corrected series touched their final TP >5s before the real close: {len(early)}")
P(early.round(2).to_string())
(RES / "01_basis.txt").write_text("\n".join(out) + "\n")
