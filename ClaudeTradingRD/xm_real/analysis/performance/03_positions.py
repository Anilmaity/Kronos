"""Per-position enrichment and flat-to-flat episodes.

results/positions_enriched.csv  one row per broker position (178) with:
   adj_net / adj_pts / role   close-by pairs re-attributed: the earlier leg is the trade, the later (hedge) leg is its exit
   mae_pts / mfe_pts          worst / best excursion while open, on basis-corrected S5 bid (longs) / ask (shorts)
   decision_id                entries on the same side <= 60 s apart = one decision (the trader taps the button N times)
   ctx                        per decision: fresh_flat | counter_side | add_to_loser | add_to_winner (same-side positions from earlier decisions
                              still open, and whether that basket was losing at the new entry price)
   episode_id                 flat-to-flat episode (gross exposure > 0)
results/episodes.csv            one row per episode
"""
import numpy as np
import pandas as pd
from common import load_positions, load_deals, xm_quotes, OUT, HERE, OZ

pos, d, q = load_positions(), load_deals(), xm_quotes()
g = pd.read_csv(HERE / "equity_curve.csv", parse_dates=["time"]).set_index("time")
p = pos.copy()

# ---- close-by pairs: "#A by #B" -> earlier-opened leg is the trade, later leg is the hedge that closed it
p["role"], p["adj_net"], p["adj_pts"], p["adj_close_time"], p["adj_exit"] = "trade", p.net, p.pts, p.close_time, p.exit
pairs = p[p.closeby].comment.dropna().unique()
ix = p.set_index("position_id").index
for c in pairs:
    a, b = [int(x) for x in c.replace("#", "").split(" by ")]
    ra, rb = p[p.position_id == a].iloc[0], p[p.position_id == b].iloc[0]
    first, second = (ra, rb) if ra.open_time <= rb.open_time else (rb, ra)
    tot = ra.net + rb.net
    i1, i2 = p.index[p.position_id == first.position_id][0], p.index[p.position_id == second.position_id][0]
    p.loc[i1, ["adj_net", "adj_pts", "adj_close_time", "adj_exit"]] = [tot, tot / (first.volume * OZ), second.open_time, second.entry]
    p.loc[i2, ["role", "adj_net", "adj_pts"]] = ["hedge_leg", 0.0, 0.0]

# ---- MAE / MFE on XM-corrected S5 quotes, bars strictly inside the holding period + the realised exit
qs = q.index.values
mae, mfe, under, t_mae = [], [], [], []
for r in p.itertuples():
    a = np.searchsorted(qs, r.open_time.to_datetime64(), side="right")                       # first bar starting after entry
    b = np.searchsorted(qs, (r.close_time - pd.Timedelta(seconds=5)).to_datetime64(), side="right")  # bars ending by exit
    w = q.iloc[a:b]
    if r.sgn > 0:
        adv = r.entry - w.bid_low.values; fav = w.bid_high.values - r.entry; cl = w.bid_close.values - r.entry
    else:
        adv = w.ask_high.values - r.entry; fav = r.entry - w.ask_low.values; cl = r.entry - w.ask_close.values
    adv = np.append(adv, -r.pts); fav = np.append(fav, r.pts)
    mae.append(max(adv.max(), 0)); mfe.append(max(fav.max(), 0))
    under.append(float((cl < 0).mean()) if len(cl) else np.nan)
    t_mae.append((w.index[adv[:-1].argmax()] - r.open_time).total_seconds() if len(w) and adv[:-1].max() >= -r.pts else r.hold_s)
p["mae_pts"], p["mfe_pts"], p["frac_underwater"], p["t_to_mae_s"] = mae, mfe, under, t_mae
p["tp_dist"] = (p.tp - p.entry) * p.sgn

# ---- decisions: same side, <= 60 s after the previous entry (the gap histogram is empty between 60 and 120 s)
p = p.sort_values("open_time").reset_index(drop=True)
did, cur, last_t, last_s = [], -1, None, None
for r in p.itertuples():
    if last_t is None or r.sgn != last_s or (r.open_time - last_t).total_seconds() > 60:
        cur += 1
    did.append(cur); last_t, last_s = r.open_time, r.sgn
p["decision_id"] = did

# ---- context at entry, judged once per decision (first clip) against positions of EARLIER decisions
C = {}
for k, m in p.groupby("decision_id"):
    r = m.iloc[0]
    o = p[(p.open_time < r.open_time) & (p.close_time > r.open_time)]
    s_, x_ = o[o.sgn == r.sgn], o[o.sgn != r.sgn]
    c = dict(same_n=len(s_), opp_n=len(x_), same_lots=s_.volume.sum(), opp_lots=x_.volume.sum(), basket_pts=np.nan, gap_prev_pts=np.nan,
             ctx="fresh_flat" if not len(x_) else "counter_side")     # counter_side: only opposite-side positions are open (a hedge / flip)
    if len(s_):
        vw = (s_.entry * s_.volume).sum() / s_.volume.sum()
        c["basket_pts"] = (r.entry - vw) * r.sgn          # > 0: the same-side basket already open is in profit at the new entry price
        c["ctx"] = "add_to_winner" if c["basket_pts"] > 0 else "add_to_loser"
        c["gap_prev_pts"] = (s_.sort_values("open_time").iloc[-1].entry - r.entry) * r.sgn
    C[k] = c
for col in ("ctx", "same_n", "opp_n", "same_lots", "opp_lots", "basket_pts", "gap_prev_pts"):
    p[col] = p.decision_id.map(lambda k: C[k][col])
p["clip_no"] = p.groupby("decision_id").cumcount() + 1
p["clips"] = p.groupby("decision_id").position_id.transform("size")

# ---- flat-to-flat episodes
ev = [(r.open_time, 1) for r in p.itertuples()] + [(r.close_time, -1) for r in p.itertuples()]
ev.sort(key=lambda e: (e[0], -e[1]))   # opens before closes on a tie: stay in the episode
n_open, start, eps = 0, None, []
for t, k in ev:
    if n_open == 0 and k == 1:
        start = t
    n_open += k
    if n_open == 0:
        eps.append((start, t))
p["episode_id"] = [next(i for i, (a, b) in enumerate(eps) if a <= r.open_time <= b) for r in p.itertuples()]
rows = []
for i, (a, b) in enumerate(eps):
    m = p[p.episode_id == i]
    w = g.loc[a.ceil("5s"):b.floor("5s")]
    rows.append(dict(episode_id=i, start=a, end=b, hours=(b - a).total_seconds() / 3600, n_pos=len(m), n_decisions=m.decision_id.nunique(),
                     net=m.net.sum(), wins=int((m.net > 0).sum()), n_so=int((m.exit_kind == "SO").sum()), n_tp=int((m.exit_kind == "TP").sum()),
                     so_cash=m.net[m.exit_kind == "SO"].sum(), buys=int((m.sgn > 0).sum()), sells=int((m.sgn < 0).sum()),
                     max_gross=w.gross_lots.max() if len(w) else m.volume.max(), max_abs_net=w.net_lots.abs().max() if len(w) else m.volume.max(),
                     max_n_open=(w.n_long + w.n_short).max() if len(w) else 1, min_floating=min(w.floating.min(), 0) if len(w) else 0.0,
                     min_margin_level=w.margin_level.min() if len(w) else np.nan,
                     equity_at_start=g.equity.asof(a), adds_to_loser=int((m.ctx == "add_to_loser").sum())))
e = pd.DataFrame(rows)
e.to_csv(OUT / "episodes.csv", index=False)
p.to_csv(OUT / "positions_enriched.csv", index=False)
print(len(p), "positions |", int((p.role == "hedge_leg").sum()), "hedge legs |", p.decision_id.nunique(), "decisions |", len(e), "episodes")
print("sum net", round(p.net.sum(), 2), "sum adj_net", round(p.adj_net.sum(), 2), "episodes net", round(e.net.sum(), 2))
assert abs(p.net.sum() - p.adj_net.sum()) < 1e-6 and abs(e.net.sum() - p.net.sum()) < 1e-6
print(p.ctx.value_counts().to_dict())

