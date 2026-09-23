"""Score the original events as a TRUE limit at open_px (fill at opx on bar k, stop can hit in bar k)."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd, concept_lab as cl
m1 = cl.load_m1(); mkt = cl.get_market()
ev = pd.read_pickle("orig_ev_low.pkl"); tr = pd.read_pickle("orig_trades_low.pkl")
mt = cl.data.utc_ns(m1.index)
k = np.searchsorted(mt, cl.data.utc_ns(pd.DatetimeIndex(ev.decision_time))) - 1   # fill bar
d = ev.direction.to_numpy(); opx = ev.open_px.to_numpy(); stp = ev.stop_px.to_numpy()
lo = m1.low.to_numpy()[k]; hi = m1.high.to_numpy()[k]; op = m1.open.to_numpy()[k]
inbar_stop = np.where(d > 0, lo <= stp, hi >= stp)
print("events", len(ev), "fill-bar also crosses stop (limit would be stopped in-bar, script skips the loss or enters later):", inbar_stop.sum(), inbar_stop.mean())
# where would script entry vs opx be
tr = tr.set_index("ev_id")
ent = tr.entry.reindex(range(len(ev))).to_numpy()
imp = d * (opx - ent)   # positive = script entry better than the limit
print("script entry better than limit (in $): mean", np.nanmean(imp), "median", np.nanmedian(imp))
risk_l = d * (opx - stp)
print("risk at limit median", np.median(risk_l), " script entry improvement in R of limit risk: mean", np.nanmean(imp / risk_l))
# true limit book: entry at max/min(opx, bar open) on bar k, resolve from bar k (inclusive) ; stop-first
fill = np.where(d > 0, np.minimum(opx, op), np.maximum(opx, op))
risk = d * (fill - stp)
ok = risk > 0
tgt = fill + d * 2 * risk
i0 = k; i1 = np.searchsorted(mkt.tn, mt[k] + np.timedelta64(150, 'm').astype('timedelta64[ns]').astype(np.int64), side="left")
r = cl.resolve_trades(mkt, d[ok] > 0, stp[ok], tgt[ok], i0[ok], i1[ok])
g = d[ok] * (r["exit_px"] - fill[ok]) / risk[ok]
print("TRUE-limit book n", ok.sum(), "gross avg R", g.mean(), "(script gross", tr.gross_R.mean(), ")")
# note: within bar k we can't know if low hit opx before stop; resolve_trades treats bar k range as after entry
# compare with script book restricted to same events
sg = tr.gross_R.reindex(np.flatnonzero(ok)).to_numpy()
print("script gross on same events", np.nanmean(sg), " ctrl mean gross≈", (tr.ctrl_mean_R + 0.04).mean())
print("in-bar-stop events: script mean net R", tr.net_R.reindex(np.flatnonzero(inbar_stop)).mean(), " ctrl", tr.ctrl_mean_R.reindex(np.flatnonzero(inbar_stop)).mean())
print("non-inbar events: script diff", (tr.net_R - tr.ctrl_mean_R).reindex(np.flatnonzero(~inbar_stop)).mean())
