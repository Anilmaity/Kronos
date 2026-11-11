"""Drawdown episodes, account wipe-outs, withdrawal phases, basis clock check -> results/06_extra.md"""
import numpy as np
import pandas as pd
from common import load_deals, load_s5, OUT, HERE, md

g = pd.read_csv(HERE / "equity_curve.csv", parse_dates=["time"]).set_index("time")
so = pd.read_csv(OUT / "stopouts.csv", parse_dates=["time"])
d = load_deals()
out = []
H = lambda s: out.extend(["", "## " + s, ""])
P = lambda *a: out.append(" ".join(str(x) for x in a))


def dd_episodes(s, top=6):
    pk = s.cummax(); under = s < pk - 1e-9
    grp = (under != under.shift()).cumsum()[under]
    rows = []
    for _, x in s[under].groupby(grp):
        t = x.idxmin(); peak_t = s.loc[:x.index[0]].idxmax()
        nxt = s.index[s.index.get_loc(x.index[-1]) + 1] if x.index[-1] != s.index[-1] else None
        rows.append(dict(peak=peak_t.strftime("%m-%d %H:%M"), trough=t.strftime("%m-%d %H:%M"), recovered=nxt.strftime("%m-%d %H:%M") if nxt is not None else "never",
                         depth_usd=x.min() - pk.loc[t], peak_value=pk.loc[t], hours_under=len(x) * 5 / 3600))
    return pd.DataFrame(rows).sort_values("depth_usd").head(top)


H("Drawdown episodes (cash flows removed): realised P&L vs P&L including floating")
P("realised (balance) curve:"); P(md(dd_episodes(g.realised_pnl).round(2), index=False)); P("")
P("realised + floating (equity) curve, 5 s closes:"); P(md(dd_episodes(g.pnl_incl_floating).round(2), index=False)); P("")
w = g.loc[:"2026-11-10 09:01:10"]
P(f"while the account was still making new highs (to 11-10 09:01): max balance-curve drawdown {(w.realised_pnl - w.realised_pnl.cummax()).min():.2f} USD, "
  f"max equity-curve drawdown {(w.pnl_incl_floating - w.pnl_incl_floating.cummax()).min():.2f} USD")
gap = g.realised_pnl - g.pnl_incl_floating
P(f"gap between the two curves (= open loss the balance does not show): mean {gap.mean():.2f}, p90 {gap.quantile(.9):.2f}, max {gap.max():.2f} USD at {gap.idxmax():%m-%d %H:%M}")

H("Account wipe-outs (equity after each stop-out event, before any new deposit)")
so = so.sort_values("time"); so["event"] = (so.time.diff().dt.total_seconds().fillna(0) > 120).cumsum()
rows = []
bounds = [(s.time.iloc[0], s.time.iloc[-1]) for _, s in so.groupby("event")]
for k, s in so.groupby("event"):
    t0, t1 = bounds[k]
    nxt_ev = bounds[k + 1][0] if k + 1 < len(bounds) else t1 + pd.Timedelta(minutes=30)
    post = g.loc[(t1 + pd.Timedelta(seconds=5)).ceil("5s"):].iloc[0]
    cm = d.comment.fillna("")
    after = d[(d.time > t1) & (d.time < min(nxt_ev, t1 + pd.Timedelta(minutes=30)))]
    nxt_dep = d[(d.time > t1) & cm.str.startswith(("CD-", "Transfer"))]
    rows.append(dict(event=k, first_so=t0.strftime("%m-%d %H:%M:%S"), ist=(t0 + pd.Timedelta(minutes=330)).strftime("%H:%M"), so_deals=len(s),
                     account_before=s.bal_before.iloc[0] + s.credit_before.iloc[0], so_cash=s.cash.sum(), equity_after=post.equity, open_lots_after=post.gross_lots,
                     bonus_burnt_exp06=after[after.comment.fillna("").str.startswith("EXP06")].profit.sum(), broker_reset_exp01=after[after.comment.fillna("").str.startswith("EXP01")].profit.sum(),
                     next_deposit_usd=nxt_dep.profit.iloc[0] if len(nxt_dep) else 0.0,
                     hours_to_redeposit=(nxt_dep.time.iloc[0] - t1).total_seconds() / 3600 if len(nxt_dep) else np.nan))
W = pd.DataFrame(rows); W.to_csv(OUT / "tab_wipeouts.csv", index=False)
P(md(W.round(2), index=False))
P(f"sum of account value (balance + credit) standing just before the 7 events: {W.account_before.sum():.2f}; sum left after: {W.equity_after.sum():.2f}; "
  f"EXP06 total {W.bonus_burnt_exp06.sum():.2f}, EXP01 total {W.broker_reset_exp01.sum():.2f}")

H("Two phases of the cash account")
b = d[d.type == "DEAL_TYPE_BALANCE"].copy(); c = b.comment.fillna("")
dep = b[c.str.startswith(("CD-", "Transfer"))]; wd = b[c.str.startswith("CW-") & ~c.str.contains("ERR")]
tr = d[d.symbol.notna()]
for nm, a, z in (("phase 1: 11-04 .. 11-06 (withdrawals every day)", "2026-11-04", "2026-11-07"), ("phase 2: 11-09 .. 11-11 (no withdrawals)", "2026-11-07", "2026-11-12")):
    f = lambda x: x[(x.time >= a) & (x.time < z)]
    P(f"{nm}: deposits {f(dep).profit.sum():.2f} ({len(f(dep))}), withdrawals {-f(wd).profit.sum():.2f} ({len(f(wd))}), trading P&L {f(tr).cash.sum():.2f}, "
      f"net cash to owner {-f(wd).profit.sum() - f(dep).profit.sum():+.2f}")
P(""); P("withdrawals vs the balance just before:")
rows = []
for r in wd.itertuples():
    pre = g.iloc[g.index.searchsorted(r.time, side="left") - 1]          # last grid row strictly before the withdrawal
    rows.append(dict(time=r.time.strftime("%m-%d %H:%M"), withdrawn=-r.profit, balance_before=pre.balance, balance_after=pre.balance + r.profit, share_pct=100 * -r.profit / pre.balance, open_lots=pre.gross_lots, floating=pre.floating))
P(md(pd.DataFrame(rows).round(2), index=False))

H("Basis clock check (does a time offset between XM deal stamps and OANDA bars improve the fit?)")
s5 = load_s5(); x = d[(d.reason == "DEAL_REASON_MOBILE") & (d.entryType != "DEAL_ENTRY_OUT_BY")]
buy = (x.type == "DEAL_TYPE_BUY").values
rows = []
for lag in (-4, -2, -1, 0, 1, 2, 4):
    t = x.time + pd.Timedelta(seconds=lag)
    i = s5.index.searchsorted(t, side="right") - 1; bar = s5.iloc[i]
    f = ((t.values - bar.index.values) / np.timedelta64(1, "s") / 5).clip(0, 1)
    ref = np.where(buy, bar.ask_open.values + (bar.ask_close.values - bar.ask_open.values) * f, bar.bid_open.values + (bar.bid_close.values - bar.bid_open.values) * f)
    e = x.price.values - ref; calm = (bar.ask_high.values - bar.ask_low.values) <= 1.0
    rows.append(dict(shift_s=lag, n=int(calm.sum()), mad=np.median(np.abs(e[calm] - np.median(e[calm]))), sd=e[calm].std(), median_buy=np.median(e[calm & buy]), median_sell=np.median(e[calm & ~buy])))
P(md(pd.DataFrame(rows).round(3), index=False))

H("Entry style: with or against the preceding move (entry decisions, first clip)")
from common import xm_quotes
q = xm_quotes(); mid = ((q.bid_close + q.ask_close) / 2); mt = (q.index + pd.Timedelta(seconds=5)).values; mv = mid.values
p = pd.read_csv(OUT / "positions_enriched.csv", parse_dates=["open_time", "close_time"])
dec = p.sort_values("open_time").drop_duplicates("decision_id")
at = lambda t: mv[np.clip(np.searchsorted(mt, t, side="right") - 1, 0, None)]
t0 = dec.open_time.values.astype("datetime64[ns]")
rows = []
for mnt in (5, 15, 60, 240):
    prior = (at(t0) - at(t0 - np.timedelta64(mnt, "m"))) * dec.sgn.values       # > 0: entering WITH the preceding move
    fresh = (dec.ctx == "fresh_flat").values
    rows.append(dict(lookback_min=mnt, n=len(dec), against_move_pct=100 * (prior < 0).mean(), median_prior_move_pts=np.median(prior), mean_prior_move_pts=prior.mean(),
                     fresh_flat_n=int(fresh.sum()), fresh_flat_against_pct=100 * (prior[fresh] < 0).mean(), fresh_flat_median=np.median(prior[fresh])))
P(md(pd.DataFrame(rows).round(2), index=False))

H("Exit style")
t = p[p.role == "trade"]
tp = t[t.tp.notna()]
P(f"take-profit attached at close: {int(p.tp.notna().sum())} of {len(p)} positions; stop-loss attached: {int(p.sl.notna().sum())} (a hedge leg)")
P(f"TP distance from entry (pts, n={len(tp)}): p10 {tp.tp_dist.quantile(.1):.1f}, p25 {tp.tp_dist.quantile(.25):.1f}, median {tp.tp_dist.median():.1f}, p75 {tp.tp_dist.quantile(.75):.1f}, p90 {tp.tp_dist.quantile(.9):.1f}; "
   + "histogram: " + ", ".join(f"{k}: {v}" for k, v in pd.cut(tp.tp_dist, [0, 4, 6, 9, 12, 16, 25, 50]).value_counts(sort=False).items()))
mw = t[(t.exit_kind == "MOBILE") & (t.adj_pts > 0)]
mwt = mw[mw.tp.notna()]
P(f"hand-closed winners (n={len(mw)}): median gain {mw.adj_pts.median():.2f} pts, median hold {mw.hold_s.median() / 60:.1f} min; where a TP was set (n={len(mwt)}) they took "
  f"{100 * (mwt.adj_pts / mwt.tp_dist).median():.0f}% of the TP distance (median)")
tpw = t[t.exit_kind == "TP"]
P(f"TP exits (n={len(tpw)}): median gain {tpw.adj_pts.median():.2f} pts, median hold {tpw.hold_s.median() / 60:.1f} min, median MAE {tpw.mae_pts.median():.2f} pts")
cl = p.sort_values("close_time"); grp = (cl.close_time.diff().dt.total_seconds() > 5).cumsum()
ce = cl.groupby(grp).agg(n=("net", "size"), net=("net", "sum"))
P(f"close events (closes within 5 s merged): {len(ce)}; closing 2+ positions at once: {int((ce.n >= 2).sum())} events covering {int(ce.n[ce.n >= 2].sum())} positions; "
  f"winning close events {int((ce.net > 0).sum())} ({100 * (ce.net > 0).mean():.1f}%)")
ls = t[t.adj_net < 0]
P(f"losing positions (n={len(ls)}): ended by margin stop-out {int((ls.exit_kind == 'SO').sum())}, by hedge + close-by {int((ls.exit_kind == 'CLOSE_BY').sum())}, closed by hand {int((ls.exit_kind == 'MOBILE').sum())} "
  f"({ls.adj_net[ls.exit_kind == 'MOBILE'].sum():.2f} USD)")

H("Headline recomputed from deals_raw.json only (independent of trades.csv)")
x = d[d.symbol.notna()]; o = x[x.entryType != "DEAL_ENTRY_IN"]
P(f"exit deals {len(o)}, entry deals {int((x.entryType == 'DEAL_ENTRY_IN').sum())}; sum cash {x.cash.sum():.2f}; exit deals with cash > 0: {int((o.cash > 0).sum())} ({100 * (o.cash > 0).mean():.1f}%), "
  f"= 0: {int((o.cash == 0).sum())}, < 0: {int((o.cash < 0).sum())}; SO deals {int((o.reason == 'DEAL_REASON_SO').sum())} sum {o.cash[o.reason == 'DEAL_REASON_SO'].sum():.2f}; "
  f"TP deals {int((o.reason == 'DEAL_REASON_TP').sum())} sum {o.cash[o.reason == 'DEAL_REASON_TP'].sum():.2f}; lots traded (entries) {x.volume[x.entryType == 'DEAL_ENTRY_IN'].sum():.2f}")

H("Regime context (OANDA M1 mid, 2026-07-16 .. 2026-11-11)")
from common import SRC
m1 = pd.read_parquet(SRC / "xau_m1_2026-07-16_now_mba.parquet").set_index("time")
dr = m1.resample("1D").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"), n=("close", "size")).dropna()
dr = dr[dr.n > 600]; dr["range"] = dr.high - dr.low
wk = dr.loc["2026-11-04":"2026-11-10"]; prior = dr.loc[:"2026-11-03"]
P(f"daily range, trade week (11-04..11-10, n={len(wk)} full days): median {wk.range.median():.1f}, min {wk.range.min():.1f}, max {wk.range.max():.1f} pts; "
  f"prior 16 weeks (n={len(prior)} days): median {prior.range.median():.1f}, p25 {prior.range.quantile(.25):.1f}, p75 {prior.range.quantile(.75):.1f}, p90 {prior.range.quantile(.9):.1f}; "
  f"trade-week median is at the {100 * (prior.range < wk.range.median()).mean():.0f}th percentile of the prior 16 weeks")
P(f"price level: trade week {m1.loc['2026-11-04':'2026-11-11'].close.min():.0f}..{m1.loc['2026-11-04':'2026-11-11'].close.max():.0f}; "
  f"week net change {m1.loc['2026-11-11'].close.iloc[-1] - m1.loc['2026-11-04'].open.iloc[0]:+.1f} pts")
def adverse_prob(x, pts, hours):
    c = x.close.values; n = hours * 60; idx = np.arange(0, len(c) - n, 7)
    up = np.array([c[i:i + n].max() - c[i] for i in idx]); dn = np.array([c[i] - c[i:i + n].min() for i in idx])
    return 100 * ((up >= pts).mean() + (dn >= pts).mean()) / 2
rows = []
for nm, x in (("trade week", m1.loc["2026-11-04":"2026-11-11"]), ("prior 16 weeks", m1.loc[:"2026-11-03"])):
    for pts in (13, 26):
        rows.append(dict(period=nm, adverse_pts=pts, **{f"within_{h}h_pct": adverse_prob(x, pts, h) for h in (1, 4, 12, 24)}))
P(""); P("chance that gold moves at least X pts against a one-directional position within H hours of a random minute (M1 closes, ignores session gaps):")
P(md(pd.DataFrame(rows).round(1), index=False))

H("After each stop-out: did price come back to the stopped positions' entries (within the data, to 11-11 13:43 UTC)?")
s5 = load_s5(); pe = p.copy()
so2 = so.merge(pe[["position_id", "sgn", "entry", "volume", "side"]], on="position_id")
rows = []
for k, s_ in so2.groupby("event"):
    for side, z in s_.groupby("side"):
        rec, adv = [], []
        for r in z.itertuples():
            a = s5.loc[r.time:]
            hit = a.index[a.bid_high >= r.entry] if r.sgn > 0 else a.index[a.ask_low <= r.entry]
            upto = a.loc[:hit[0]] if len(hit) else a
            rec.append((hit[0] - r.time).total_seconds() / 3600 if len(hit) else np.nan)
            adv.append((r.price - upto.bid_low.min()) if r.sgn > 0 else (upto.ask_high.max() - r.price))
        rows.append(dict(event=k, first_so=z.time.min().strftime("%m-%d %H:%M"), stopped_side=side, n=len(z), lots=z.volume_y.sum() if "volume_y" in z else z.volume.sum(),
                         entry_min=z.entry.min(), entry_max=z.entry.max(), so_price=z.price.mean(), came_back_n=int(np.isfinite(rec).sum()),
                         hours_to_come_back_median=np.nanmedian(rec) if np.isfinite(rec).any() else np.nan, hours_max=np.nanmax(rec) if np.isfinite(rec).any() else np.nan,
                         further_adverse_pts_before=np.max(adv), hours_of_data_after=(s5.index[-1] - z.time.max()).total_seconds() / 3600))
R = pd.DataFrame(rows); R.to_csv(OUT / "tab_stopout_recovery.csv", index=False)
P(md(R.round(2), index=False))
(OUT / "06_extra.md").write_text("\n".join(out)); print("\n".join(out))
