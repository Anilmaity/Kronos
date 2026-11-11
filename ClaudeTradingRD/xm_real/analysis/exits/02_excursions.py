"""Step 2 - per-position excursions, exit-management descriptives, add/hedge flags, stop-out forensics.

Writes trade_excursions.csv (one row per broker position, 178) and results/02_descriptives.txt.
Prices are basis-corrected S5 (see 01_basis.py); a long is marked on bid, a short on ask.
Bars used for a position: those that OPEN at/after the entry and CLOSE at/before the exit (the entry and
exit bars are partial and skipped); the real exit print is added as the last observation.
Run: python 02_excursions.py
"""
import numpy as np
import pandas as pd

from common import BAR_NS, HERE, RES, USD_PER_PT, Quotes, load_deals, load_trades

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60); pd.set_option("display.max_rows", 300)
out = []
P = lambda *a: (print(*a), out.append(" ".join(str(x) for x in a)))
QS = [.05, .25, .5, .75, .95]

ADD_AGE_S, ADD_DEPTH = 60, 1.0      # "add to a loser": same-side position >=60s old and >=1.0 pt under water
BURST_S = 10                        # same-side entries <=10s apart = one decision ("burst")

q, t, d = Quotes(), load_trades(), load_deals()
n = len(t)
exit_side = np.where(t.sgn > 0, "bid", "ask")

# ---- close-by pairs: each long was locked by an opposite position, then the pair netted off ------------
pair = {}
for c in d[d.entryType.eq("DEAL_ENTRY_OUT_BY")].comment.dropna().unique():      # "#A by #B"
    a, b = [int(x.strip("# ")) for x in c.split(" by ")]
    pair[a], pair[b] = b, a
t["closeby_partner"] = t.position_id.map(pair)
t0_of = t.set_index("position_id").t0
# for the leg opened first, the loss was economically fixed when its partner (the lock) opened
t["lock_t"] = [max(t0_of[p], r.t0) if p == p else np.nan for p, r in zip(t.closeby_partner, t.itertuples())]
t["is_lock_leg"] = [(p == p) and r.t0 > t0_of[p] for p, r in zip(t.closeby_partner, t.itertuples())]
# economic points: the pair's locked loss sits on the leg opened first, 0 on the lock leg (broker books it on either)
pair_loss = t[t.closeby].groupby(t[t.closeby][["position_id", "closeby_partner"]].min(axis=1)).pts_real.sum()
t["pts_econ"] = [0.0 if r.is_lock_leg else (pair_loss[min(r.position_id, r.closeby_partner)] if r.closeby else r.pts_real) for r in t.itertuples()]
assert abs(t.pts_econ.sum() - t.pts_real.sum()) < 1e-9

# ---- excursions during the real hold --------------------------------------------------------------------
rows = []
for k, r in enumerate(t.itertuples()):
    i0 = q.first_bar_after(r.t0)
    i1 = int(np.searchsorted(q.T, r.t1 - BAR_NS, side="right"))
    fh, al, op, cl = q.path(r.sgn, r.entry, i0, max(i1, i0))
    # last observation = the exit itself (a real market print; for close-by legs mark at the quote instead)
    x_exit = r.sgn * (q.at(r.t1, exit_side[k]) - r.entry) if r.closeby else r.pts
    fav, adv = np.append(fh, x_exit), np.append(al, x_exit)
    tt = np.append(q.T[i0:max(i1, i0)] + BAR_NS, r.t1)                           # observation time = bar end
    im, ia = int(fav.argmax()), int(adv.argmin())
    prof = np.flatnonzero(fav > 0)
    rows.append(dict(
        mfe_pts=fav[im], t_mfe_s=(tt[im] - r.t0) / 1e9, mae_pts=adv[ia], t_mae_s=(tt[ia] - r.t0) / 1e9,
        t_first_profit_s=(tt[prof[0]] - r.t0) / 1e9 if len(prof) else np.nan,
        frac_time_underwater=float((cl < 0).mean()) if len(cl) else np.nan,
        mae_before_mfe_pts=adv[:im + 1].min(), n_bars=len(fh)))
t = pd.concat([t, pd.DataFrame(rows)], axis=1)
t["capture_of_mfe"] = np.where(t.mfe_pts > 0, t.pts_real / t.mfe_pts, np.nan)
t["frac_of_tp"] = t.pts_real / t.tp_dist

# ---- what happened after the exit (same hypothetical position kept open) --------------------------------
rows = []
for r in t.itertuples():
    i0 = q.first_bar_after(r.t1)
    fh, al, op, cl = q.path(r.sgn, r.entry, i0)
    h = 720                                                                      # 60 min of S5 bars
    base = r.pts
    o = dict(post60_fav_pts=fh[:h].max() - base if len(fh) else np.nan,
             post60_adv_pts=al[:h].min() - base if len(al) else np.nan,
             tp_hit_later=np.nan, t_tp_after_exit_s=np.nan, worst_vs_entry_before_tp_later=np.nan)
    if r.tp_dist == r.tp_dist and r.reason == "MOBILE" and not r.closeby and r.pts < r.tp_dist:
        hit = np.flatnonzero(fh >= r.tp_dist)
        o["tp_hit_later"] = bool(len(hit))
        j = hit[0] if len(hit) else len(fh)
        o["t_tp_after_exit_s"] = (q.T[i0 + j] - r.t1) / 1e9 if len(hit) else np.nan
        o["worst_vs_entry_before_tp_later"] = al[:j + 1].min() if j or len(hit) else np.nan
    rows.append(o)
t = pd.concat([t, pd.DataFrame(rows)], axis=1)

# ---- bursts, adds to a loser, hedges against a loser ------------------------------------------------------
burst, b = [], -1
for k, r in enumerate(t.itertuples()):
    if k == 0 or r.side != t.side[k - 1] or r.t0 - t.t0[k - 1] > BURST_S * 1e9:
        b += 1
    burst.append(b)
t["burst_id"] = burst
rows = []
for k, r in enumerate(t.itertuples()):
    o = t[(t.t0 < r.t0) & (t.t1 > r.t0)]
    unreal = o.sgn.values * (np.array([q.at(r.t0, "bid" if s > 0 else "ask") for s in o.sgn]) - o.entry.values)
    aged = (r.t0 - o.t0.values) >= ADD_AGE_S * 1e9
    same, opp = (o.sgn.values == r.sgn), (o.sgn.values != r.sgn)
    mn = lambda m: float(unreal[m].min()) if m.any() else np.nan
    rows.append(dict(n_same_open=int(same.sum()), n_opp_open=int(opp.sum()),
                     same_open_lots=float(o.volume.values[same].sum()),
                     worst_same_pts=mn(same), worst_same_pts_aged=mn(same & aged), worst_opp_pts_aged=mn(opp & aged)))
f = pd.DataFrame(rows)
f["add_to_loser"] = f.worst_same_pts_aged <= -ADD_DEPTH
f["hedge_vs_loser"] = f.worst_opp_pts_aged <= -ADD_DEPTH
t = pd.concat([t, f], axis=1)
t["fresh"] = ~t.add_to_loser & ~t.hedge_vs_loser

# ---- account context: equity, net exposure and distance to margin stop-out at each entry -----------------
cash = d.type.isin(["DEAL_TYPE_BALANCE"]) | d.symbol.notna()
bal_t, bal = d.t[cash].values, (d.profit + d.swap + d.commission)[cash].cumsum().values
cr_t, cr = d.t[d.type.eq("DEAL_TYPE_CREDIT")].values, d.profit[d.type.eq("DEAL_TYPE_CREDIT")].cumsum().values
at = lambda tt, x, y: y[np.searchsorted(tt, x, side="right") - 1] if np.searchsorted(tt, x, side="right") else 0.0


def account(tm, inclusive=True):
    """(equity, net_lots, mid) just after instant tm, from deals + basis-corrected marks."""
    o = t[(t.t0 <= tm) & (t.t1 > tm)] if inclusive else t[(t.t0 < tm) & (t.t1 >= tm)]
    mark = np.array([q.at(tm, "bid" if s > 0 else "ask") for s in o.sgn])
    flo = (o.sgn.values * (mark - o.entry.values) * o.volume.values * 100).sum()
    return at(bal_t, tm - (0 if inclusive else 1), bal) + at(cr_t, tm - (0 if inclusive else 1), cr) + flo, (o.sgn * o.volume).sum(), (q.at(tm, "bid") + q.at(tm, "ask")) / 2


rows = []
for r in t.itertuples():
    eq, net, mid = account(r.t0)
    margin = abs(net) * 100 * mid / 1000                                         # 1:1000, margin on NET lots (hedges free)
    rows.append(dict(equity_at_entry=eq, net_lots_after=net, margin_after=margin,
                     pts_to_stopout_est=(eq - 0.2 * margin) / (abs(net) * 100) if abs(net) > 1e-9 else np.nan))
t = pd.concat([t, pd.DataFrame(rows)], axis=1)

t["usd_actual"] = t.profit
t["usd_flat004"] = t.pts_real * USD_PER_PT
keep = ["position_id", "side", "open_time", "close_time", "volume", "entry", "exit", "tp", "sl", "tp_dist", "reason", "closeby",
        "closeby_partner", "is_lock_leg", "lock_t", "hold_s", "pts", "pts_real", "pts_econ", "usd_actual", "usd_flat004",
        "mfe_pts", "t_mfe_s", "mae_pts", "t_mae_s", "mae_before_mfe_pts", "t_first_profit_s", "frac_time_underwater",
        "capture_of_mfe", "frac_of_tp", "post60_fav_pts", "post60_adv_pts", "tp_hit_later", "t_tp_after_exit_s",
        "worst_vs_entry_before_tp_later", "tp_shared_level", "burst_id", "n_same_open", "n_opp_open", "same_open_lots", "worst_same_pts",
        "worst_same_pts_aged", "worst_opp_pts_aged", "add_to_loser", "hedge_vs_loser", "fresh",
        "equity_at_entry", "net_lots_after", "margin_after", "pts_to_stopout_est", "n_bars"]

# =========================================== descriptives ===============================================
qd = lambda s: s.describe(percentiles=QS).round(2)
win, los = t.pts_real > 0, t.pts_real < 0
t["outcome"] = np.where(win, "win", np.where(los, "loss", "flat"))
t["exit_kind"] = np.where(t.closeby, "CLOSE_BY", t.reason)

P("== A. sample ==")
P(f"{n} positions in {t.burst_id.nunique()} bursts (same side, <={BURST_S}s apart); sides {t.side.value_counts().to_dict()}")
P(f"actual net ${t.profit.sum():.2f} (+swap {t.swap.sum():.2f});  realised points (each pair once) {t.pts_real.sum():.1f} "
  f"= ${t.pts_real.sum() * USD_PER_PT:.0f} at flat 0.04;  trades.csv pts sum {t.pts.sum():.1f} double-counts close-by legs")
g = t.groupby("exit_kind").agg(n=("pts_real", "size"), win_pct=("pts_real", lambda s: 100 * (s > 0).mean()), pts=("pts_real", "sum"),
                               usd_actual=("profit", "sum"), usd_flat004=("usd_flat004", "sum"), med_hold_min=("hold_s", lambda s: s.median() / 60),
                               med_mfe=("mfe_pts", "median"), med_mae=("mae_pts", "median"))
P(g.round(1).to_string())
P("\nby volume:"); P(t.groupby("volume").agg(n=("pts_real", "size"), pts=("pts_real", "sum"), usd_actual=("profit", "sum"), usd_flat004=("usd_flat004", "sum")).round(1).to_string())
P("\nby day (entry date):"); P(t.groupby(t.open_time.dt.strftime("%m-%d")).agg(n=("pts_real", "size"), bursts=("burst_id", "nunique"), win_pct=("pts_real", lambda s: 100 * (s > 0).mean()),
      pts=("pts_real", "sum"), usd_actual=("profit", "sum"), n_so=("reason", lambda s: (s == "SO").sum()), adds=("add_to_loser", "sum")).round(1).to_string())

P("\n== B. MAE / MFE (points, exit-side quote) ==")
P("MFE by outcome:"); P(t.groupby("outcome").mfe_pts.describe(percentiles=QS).round(2).to_string())
P("MAE by outcome:"); P(t.groupby("outcome").mae_pts.describe(percentiles=QS).round(2).to_string())
P("MAE by exit kind:"); P(t.groupby("exit_kind").mae_pts.describe(percentiles=QS).round(2).to_string())
P("time to MFE (min) by outcome:"); P((t.t_mfe_s / 60).groupby(t.outcome).describe(percentiles=QS).round(1).to_string())
P("time to MAE (min) by outcome:"); P((t.t_mae_s / 60).groupby(t.outcome).describe(percentiles=QS).round(1).to_string())
w = t[win]
P(f"\nwinners (n={len(w)}) that were first under water by >=X pts:  " + "  ".join(f">={x}: {(w.mae_pts <= -x).sum()} ({100 * (w.mae_pts <= -x).mean():.0f}%, ${w.profit[w.mae_pts <= -x].sum():.0f})" for x in (2, 3, 5, 10, 15, 20, 30)))
l = t[los]
P(f"losers  (n={len(l)}) that were at some point in profit by >=X pts: " + "  ".join(f">={x}: {(l.mfe_pts >= x).sum()}" for x in (0.01, 1, 2, 3, 5, 10)))
P(f"winners' profit earned by positions with MAE <= -10: ${w.profit[w.mae_pts <= -10].sum():.0f} of ${w.profit.sum():.0f} total gross wins")

P("\n== C. time to first profit (s) ==")
P(f"never in profit on the exit-side quote: {t.t_first_profit_s.isna().sum()} of {n} ({t[t.t_first_profit_s.isna()].outcome.value_counts().to_dict()})")
P(t.t_first_profit_s.describe(percentiles=[.25, .5, .75, .9, .95]).round(0).to_string())
P("by outcome:"); P(t.groupby("outcome").t_first_profit_s.describe(percentiles=QS).round(0).to_string())
P(f"in profit within 60s: {(t.t_first_profit_s <= 60).sum()}; within 5 min: {(t.t_first_profit_s <= 300).sum()}; took >30 min: {(t.t_first_profit_s > 1800).sum()}")

P("\n== D. take-profit distance actually set (final TP on the closing deal; 16 also known at entry) ==")
tp = t[t.tp.notna()]
P(f"TP set on {len(tp)} of {n}; SL set on {t.sl.notna().sum()} (a lock leg). No TP: {n - len(tp)} "
  f"({t[t.tp.isna()].exit_kind.value_counts().to_dict()})")
P(qd(tp.tp_dist).to_string())
P("most common distances (pts: count): " + str(tp.tp_dist.round(2).value_counts().head(8).to_dict()))
bins = [0, 3, 4.5, 5.6, 9, 12, 13.5, 14.6, 17, 22, 30, 50]
P("histogram:"); P(pd.cut(tp.tp_dist, bins).value_counts().sort_index().to_string())
P("by entry day (median, n):"); P(tp.groupby(tp.open_time.dt.strftime("%m-%d")).tp_dist.agg(["count", "median", "min", "max"]).round(2).to_string())
sticky = [5.06, 10.92, 13.85, 14.26]
P(f"at one of the four repeated distances {sticky} (+-0.02): {int(sum((tp.tp_dist - v).abs().le(0.02).sum() for v in sticky))} of {len(tp)}")
shared = []
for r in tp.itertuples():
    o = tp[(tp.side == r.side) & (tp.burst_id != r.burst_id) & (tp.t0 < r.t1) & (tp.t1 > r.t0) & ((tp.tp - r.tp).abs() <= 0.5)]
    shared.append(len(o))
t["tp_shared_level"] = False
t.loc[tp.index, "tp_shared_level"] = np.array(shared) > 0
tp = t[t.tp.notna()]
P(f"basket TPs (TP price within 0.5 of an overlapping same-side position opened in another burst): {int(tp.tp_shared_level.sum())} of {len(tp)}")
P(tp.groupby("tp_shared_level").agg(n=("tp", "size"), med_tp_dist=("tp_dist", "median"), max_tp_dist=("tp_dist", "max"), adds=("add_to_loser", "sum"),
                                    pts=("pts_real", "sum"), usd=("profit", "sum"), exits=("exit_kind", lambda s: s.value_counts().to_dict())).round(1).to_string())
P("\n== E. TP hit vs closed early by hand ==")
P(f"of {len(tp)} TP-set positions: {tp.exit_kind.value_counts().to_dict()}")
man = tp[(tp.exit_kind == "MOBILE")]
P(f"manual closes with a TP set: n={len(man)}; in profit {int((man.pts_real > 0).sum())}, at a loss {int((man.pts_real < 0).sum())}")
P("fraction of the TP distance banked at the manual close:"); P(qd(man.frac_of_tp).to_string())
P("fraction of the available MFE banked (all profitable manual closes, n=%d):" % (t.exit_kind.eq("MOBILE") & win).sum()); P(qd(t[t.exit_kind.eq("MOBILE") & win].capture_of_mfe).to_string())
P("TP exits: realised / TP distance:"); P(qd(t[t.exit_kind == "TP"].frac_of_tp).to_string())
P(f"TP exits filled >1 pt better than the TP level (gap through): {((t.exit_kind == 'TP') & (t.pts_real - t.tp_dist > 1)).sum()}, worth {((t.pts_real - t.tp_dist)[(t.exit_kind == 'TP') & (t.pts_real - t.tp_dist > 1)]).sum():.1f} pts")
hl = man[man.tp_hit_later.notna()]
P(f"early manual closes (n={len(hl)}): TP would have been reached later (before data end) in {int(hl.tp_hit_later.sum())} "
  f"({100 * hl.tp_hit_later.mean():.0f}%)")
h1 = hl[hl.tp_hit_later == True]
P("  time from manual close to that TP touch (min):"); P((h1.t_tp_after_exit_s / 60).describe(percentiles=QS).round(0).to_string())
P("  worst excursion vs entry on the way to that later TP (pts):"); P(qd(h1.worst_vs_entry_before_tp_later).to_string())
P(f"  ... of which price first went >=10 pts against entry: {(h1.worst_vs_entry_before_tp_later <= -10).sum()}, >=20: {(h1.worst_vs_entry_before_tp_later <= -20).sum()}")
P(f"  points given up by closing early = sum(tp_dist - realised) over those {len(h1)}: {(h1.tp_dist - h1.pts_real).sum():.0f} pts; "
  f"never reached TP: {int((hl.tp_hit_later == False).sum())}, their realised {hl.pts_real[hl.tp_hit_later == False].sum():.0f} pts, "
  f"mark-to-market at data end had they been held: {sum(q.path(r.sgn, r.entry, q.n - 1)[3][0] for r in hl[hl.tp_hit_later == False].itertuples()):.0f} pts")
P("next 60 min after a manual profitable close (pts vs exit price): further favourable / adverse:")
mp = t[t.exit_kind.eq("MOBILE") & win]
P(pd.DataFrame({"fav": qd(mp.post60_fav_pts), "adv": qd(mp.post60_adv_pts)}).to_string())
P("manual-close size (pts) of profitable manual exits:"); P(qd(mp.pts_real).to_string())

P("\n== F. hold time (min) ==")
P((t.hold_s / 60).groupby(t.outcome).describe(percentiles=QS).round(1).to_string())
P("by exit kind:"); P((t.hold_s / 60).groupby(t.exit_kind).describe(percentiles=QS).round(1).to_string())

P("\n== G. how deep losers were allowed to go ==")
P(f"losing positions: {len(l)}; closed by: {l.exit_kind.value_counts().to_dict()}")
P("realised loss (pts):"); P(qd(l.pts_real).to_string())
P("MAE of losers (pts):"); P(qd(l.mae_pts).to_string())
vol_man = t[(t.exit_kind == "MOBILE") & los]
P(f"voluntary manual closes at a loss: {len(vol_man)}  -> " + vol_man[["position_id", "volume", "pts_real", "profit", "mae_pts", "hold_s"]].round(2).to_dict("records").__str__())
P(f"positions under water >=10 pts at some point: {(t.mae_pts <= -10).sum()}, of which ended as winners {((t.mae_pts <= -10) & win).sum()}, losers {((t.mae_pts <= -10) & los).sum()}")
P(f"positions under water >=20 pts at some point: {(t.mae_pts <= -20).sum()}, of which ended as winners {((t.mae_pts <= -20) & win).sum()}, losers {((t.mae_pts <= -20) & los).sum()}")
P("estimated distance to margin stop-out at entry (pts, net exposure, equity incl. bonus credit):"); P(qd(t.pts_to_stopout_est).to_string())

P("\n== H. stop-outs and locks ==")
so = t[(t.reason == "SO") | t.closeby].copy()
so["cluster"] = (so.t1.diff().fillna(0) > 15 * 60 * 1e9).cumsum()
dep = d[d.type.eq("DEAL_TYPE_BALANCE") & d.comment.fillna("").str.startswith(("CD-", "Transfer"))]
rows = []
for c, gdf in so.groupby("cluster"):
    t_end = gdf.t1.max()
    nd = dep[dep.t > t_end].head(1)
    ne = t[t.t0 > t_end].head(1)
    eq, net, _ = account(gdf.t1.min(), inclusive=False)
    rows.append(dict(first_close=gdf.close_time.min().strftime("%m-%d %H:%M:%S"), n_pos=len(gdf), n_so=int((gdf.reason == "SO").sum()), n_closeby=int(gdf.closeby.sum()),
                     sides=gdf.side.value_counts().to_dict(), lots=round(gdf.volume.sum(), 2), usd=round(gdf.profit.sum(), 0),
                     worst_pts=round(gdf.pts_real.min(), 1), max_hold_h=round(gdf.hold_s.max() / 3600, 1), n_adds=int(gdf.add_to_loser.sum()),
                     recon_equity_before=round(eq, 0), net_lots_before=round(net, 2),
                     redeposit_min=round((nd.t.iloc[0] - t_end) / 6e10, 0) if len(nd) else np.nan, redeposit_usd=nd.profit.iloc[0] if len(nd) else np.nan,
                     next_entry_min=round((ne.t0.iloc[0] - t_end) / 6e10, 0) if len(ne) else np.nan, next_lots=ne.volume.iloc[0] if len(ne) else np.nan))
P(pd.DataFrame(rows).to_string())
P(f"stop-out positions n={int((t.reason == 'SO').sum())}: ${t.profit[t.reason == 'SO'].sum():.0f}; close-by pairs: ${t.profit[t.closeby].sum():.0f}; "
  f"all other exits: ${t.profit[(t.reason != 'SO') & ~t.closeby].sum():.0f}")
rows = []
for r in dep.itertuples():                                                    # was each deposit a top-up into an open drawdown?
    o = t[(t.t0 < r.t) & (t.t1 > r.t)]
    mark = np.array([q.at(r.t, "bid" if s_ > 0 else "ask") for s_ in o.sgn])
    flo_ = (o.sgn.values * (mark - o.entry.values) * o.volume.values * 100).sum()
    eq_, net_, _ = account(r.t - 1)
    last_so = t.t1[(t.reason == "SO") & (t.t1 < r.t)].max()
    rows.append(dict(time=r.time.strftime("%m-%d %H:%M"), usd=r.profit, open_positions=len(o), floating_usd=round(flo_), equity_before=round(eq_),
                     worst_open_pts=round(float((o.sgn.values * (mark - o.entry.values)).min()), 1) if len(o) else np.nan,
                     min_since_stopout=round((r.t - last_so) / 6e10) if last_so == last_so else np.nan))
P("cash deposits (CD-* and the internal transfer) and the book they landed on:"); P(pd.DataFrame(rows).to_string(index=False))
bonus = d[d.comment.fillna("").isin(["EXP06", "EXP01"])].groupby("comment").profit.agg(["count", "sum"])
P("balance credits that refilled the account after wipe-outs (EXP06 = bonus credit converted, EXP01 = negative-balance reset):"); P(bonus.to_string())
# sanity: reconstructed equity just before each stop-out deal vs the broker's own figure in the deal comment
chk = []
for r in d[d.reason.eq("DEAL_REASON_SO")].itertuples():
    eq, net, _ = account(r.t, inclusive=False)
    chk.append((eq - float(r.comment.strip("[]").split("/")[1])))
P(f"check: reconstructed equity minus broker equity in the {len(chk)} stop-out comments: median {np.median(chk):+.1f} USD, "
  f"IQR {np.percentile(chk, 25):+.1f}..{np.percentile(chk, 75):+.1f}, max abs {np.abs(chk).max():.0f} (S5 interpolation x lots in a spike)")
P(f"check: final balance + credit = {bal[-1]:.2f} + {cr[-1]:.2f}")

P("\n== I. adds to an existing loser / hedges against a loser ==")
P(f"definition: a same-side position >= {ADD_AGE_S}s old is >= {ADD_DEPTH} pt under water at this entry (opposite side => hedge)")
g = t.assign(kind=np.where(t.add_to_loser, "add_to_loser", np.where(t.hedge_vs_loser, "hedge_vs_loser", "fresh"))).groupby("kind").agg(
    n=("pts_real", "size"), bursts=("burst_id", "nunique"), win_pct=("pts_real", lambda s: 100 * (s > 0).mean()), pts=("pts_real", "sum"),
    usd_actual=("profit", "sum"), usd_flat004=("usd_flat004", "sum"), n_so=("reason", lambda s: (s == "SO").sum()), med_mae=("mae_pts", "median"),
    worst=("pts_real", "min"), med_depth_of_existing=("worst_same_pts_aged", "median"))
P(g.round(1).to_string())
P("sensitivity of the add flag to the depth threshold (n flagged / their realised pts / USD actual):")
for dep_ in (0.0, 1.0, 3.0, 5.0, 10.0):
    m = t.worst_same_pts_aged <= -dep_
    P(f"  >= {dep_:4.1f} pt under water: n={int(m.sum()):3d}  pts {t.pts_real[m].sum():8.1f}  usd {t.profit[m].sum():9.0f}  win% {100 * (t.pts_real[m] > 0).mean():.0f}")
P(f"positions with any same-side position already open: {(t.n_same_open > 0).sum()}; any opposite-side open: {(t.n_opp_open > 0).sum()}")

P("\n== J. size and concurrency ==")
big = t[t.volume > 0.04].copy()
last_dep = [dep.t[dep.t < r.t0].max() for r in big.itertuples()]
prev_entry = [t.t0[t.t0 < r.t0].max() for r in big.itertuples()]
big["first_trade_after_deposit"] = [ld > pe for ld, pe in zip(last_dep, prev_entry)]
big["open"] = big.open_time.dt.strftime("%m-%d %H:%M")
P(f"positions above 0.04 lots: {len(big)}; actual ${big.profit.sum():.0f} vs ${big.usd_flat004.sum():.0f} had they been 0.04; "
  f"all other positions ${t.profit[t.volume <= 0.04].sum():.0f}")
P(big[["open", "side", "volume", "pts_real", "profit", "exit_kind", "first_trade_after_deposit", "add_to_loser", "hedge_vs_loser", "pts_to_stopout_est"]].round(2).to_string(index=False))
ev = pd.concat([pd.DataFrame({"t": t.t0, "d": 1, "lots": t.volume, "net": t.sgn * t.volume}), pd.DataFrame({"t": t.t1, "d": -1, "lots": -t.volume, "net": -t.sgn * t.volume})]).sort_values(["t", "d"])
P(f"max positions open at once: {int(ev.d.cumsum().max())}; max gross lots {ev.lots.cumsum().max():.2f}; max net long {ev.net.cumsum().max():.2f}, max net short {ev.net.cumsum().min():.2f}")
P(f"positions opened with nothing else open: {int(((t.n_same_open + t.n_opp_open) == 0).sum())} of {n}")
sop = t[t.reason == "SO"]
P("stop-out fills, realised points per position:"); P(qd(sop.pts_real).to_string())
P("estimated distance to stop-out at entry (pts) by how the position ended:"); P(t.groupby("exit_kind").pts_to_stopout_est.describe(percentiles=[.25, .5, .75]).round(1).to_string())
t[keep].to_csv(HERE / "trade_excursions.csv", index=False, float_format="%.3f")
(RES / "02_descriptives.txt").write_text("\n".join(out) + "\n")
