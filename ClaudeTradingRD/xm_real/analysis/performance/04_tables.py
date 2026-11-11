"""All performance / cash / drawdown / exposure / stop-out tables -> results/04_tables.md (and csv per table)."""
import re
import numpy as np
import pandas as pd
from common import load_deals, OUT, HERE, OZ, md

p = pd.read_csv(OUT / "positions_enriched.csv", parse_dates=["open_time", "close_time", "adj_close_time"])
e = pd.read_csv(OUT / "episodes.csv", parse_dates=["start", "end"])
g = pd.read_csv(HERE / "equity_curve.csv", parse_dates=["time"]).set_index("time")
so = pd.read_csv(OUT / "stopouts.csv", parse_dates=["time"])
d = load_deals()
out = []
H = lambda s: out.extend(["", "## " + s, ""])
P = lambda *a: out.append(" ".join(str(x) for x in a))


def stats(x, net="net", pts="pts"):
    n = len(x); w = x[x[net] > 0]; l = x[x[net] < 0]
    return pd.Series({"n": n, "net_usd": x[net].sum(), "win%": 100 * len(w) / n if n else np.nan,
                      "PF": w[net].sum() / -l[net].sum() if len(l) and l[net].sum() else np.nan,
                      "avg_win": w[net].mean(), "avg_loss": l[net].mean(), "exp_usd": x[net].mean(),
                      "exp_pts": x[pts].mean(), "med_pts": x[pts].median(), "lots": x.volume.sum(),
                      "med_hold_min": x.hold_s.median() / 60, "n_SO": int((x.exit_kind == "SO").sum())})


def tab(by, name, frame=p, **kw):
    t = frame.assign(_k=frame[by]).groupby("_k", sort=True).apply(stats, **kw).round(2).rename_axis(by)
    t["n"] = t["n"].astype(int); t["n_SO"] = t["n_SO"].astype(int)
    t.to_csv(OUT / f"tab_{name}.csv")
    return md(t)


p["close_day"] = p.close_time.dt.strftime("%m-%d")
p["open_day"] = p.open_time.dt.strftime("%m-%d")
p["hour_utc"] = p.open_time.dt.hour
ist = p.open_time + pd.Timedelta(minutes=330)
p["hour_ist"] = ist.dt.hour
p["session_utc"] = pd.cut(p.hour_utc, [-1, 6, 11, 15, 20, 23], labels=["1 Asia 00-07", "2 London 07-12", "3 NY-AM 12-16", "4 NY-PM 16-21", "5 Late 21-24"]).astype(str)
p["hold_bucket"] = pd.cut(p.hold_s / 60, [0, 2, 10, 30, 120, 600, 1e9], labels=["a <2m", "b 2-10m", "c 10-30m", "d 30m-2h", "e 2-10h", "f >10h"]).astype(str)
p["mae_bucket"] = pd.cut(p.mae_pts, [-1, 1, 3, 6, 12, 25, 1e9], labels=["a <=1", "b 1-3", "c 3-6", "d 6-12", "e 12-25", "f >25"]).astype(str)

# ------------------------------------------------------------------ headline
H("1. Headline (all 178 broker positions, USD net of swap; commission is zero)")
t = stats(p).round(2)
P(md(t.to_frame("all").T))
P("")
tr = p[p.role == "trade"]
P(f"close-by adjusted (4 hedge legs are exits, not trades): n={len(tr)}, win% {100 * (tr.adj_net > 0).mean():.1f}, "
  f"avg win {tr.adj_net[tr.adj_net > 0].mean():.2f}, avg loss {tr.adj_net[tr.adj_net < 0].mean():.2f}, "
  f"expectancy {tr.adj_net.mean():.2f} USD / {tr.adj_pts.mean():.2f} pts per position; volume-weighted pts {(tr.adj_net.sum() / (tr.volume.sum() * OZ)):.3f} per oz traded")
P(f"swap total {d.swap.fillna(0).sum():.2f} USD; gross profit {p.net[p.net > 0].sum():.2f}, gross loss {p.net[p.net < 0].sum():.2f}")
dec = p.groupby("decision_id").agg(net=("net", "sum"), n=("net", "size"), lots=("volume", "sum"))
P(f"decisions (same-side entries <= 60 s apart merged): n={len(dec)}, win% {100 * (dec.net > 0).mean():.1f}, mean {dec.net.mean():.2f}, "
  f"clip count per decision: {dec.n.value_counts().sort_index().to_dict()}")
P(f"episodes (flat-to-flat): n={len(e)}, winners {(e.net > 0).sum()}, losers {(e.net < 0).sum()}, sum of winning episodes {e.net[e.net > 0].sum():.2f}, "
  f"sum of losing episodes {e.net[e.net < 0].sum():.2f}, episodes ending in a stop-out {(e.n_so > 0).sum()}")

H("2. Per day (by close date, UTC)")
P(tab("close_day", "day"))
gd = g.assign(day=g.index.strftime("%m-%d"))
dd = gd.groupby("day").agg(bal_start=("balance", "first"), bal_end=("balance", "last"), credit_end=("credit", "last"), min_equity=("equity_low", "min"),
                           min_floating=("floating", "min"), min_margin_level=("margin_level", "min"), max_gross_lots=("gross_lots", "max"),
                           max_abs_net=("net_lots", lambda s: s.abs().max()), max_n_open=("n_long", lambda s: 0))
dd["max_n_open"] = (gd.n_long + gd.n_short).groupby(gd.day).max()
cf = d[d.type == "DEAL_TYPE_BALANCE"].assign(day=lambda x: x.time.dt.strftime("%m-%d"))
dd["deposits"] = cf[cf.comment.str.startswith(("CD-", "Transfer"))].groupby("day").profit.sum()
dd["withdrawals"] = cf[cf.comment.str.startswith("CW-") & ~cf.comment.str.contains("ERR")].groupby("day").profit.sum()
dd.fillna(0).round(2).to_csv(OUT / "tab_day_state.csv")
P(""); P("account state per UTC day (5 s grid):"); P(md(dd.fillna(0).round(2)))

H("3. Per side"); P(tab("side", "side"))
H("4. Per lot size"); P(tab("volume", "lots"))
H("5. Per exit kind"); P(tab("exit_kind", "exit"))
H("6. Per entry hour, UTC"); P(tab("hour_utc", "hour_utc"))
H("7. Per entry hour, IST (UTC+5:30)"); P(tab("hour_ist", "hour_ist"))
H("8. Per session of entry (UTC)"); P(tab("session_utc", "session"))
H("9. Per holding time"); P(tab("hold_bucket", "hold"))
H("10. Per entry context (same-side exposure already open?)"); P(tab("ctx", "ctx"))
H("11. Per adverse excursion (MAE, pts) while the position was open"); P(tab("mae_bucket", "mae"))

# ------------------------------------------------------------------ distribution
H("12. Win / loss distribution")
qs = [0, .05, .1, .25, .5, .75, .9, .95, 1]
dist = pd.DataFrame({"net_usd": p.net.quantile(qs), "pts": p.pts.quantile(qs), "net_per_0.04lot": (p.net / p.volume * 0.04).quantile(qs),
                     "mae_pts": p.mae_pts.quantile(qs), "mfe_pts": p.mfe_pts.quantile(qs), "hold_min": (p.hold_s / 60).quantile(qs)})
dist.index = [f"p{int(q * 100)}" for q in qs]
dist.round(2).rename_axis("quantile").to_csv(OUT / "tab_dist.csv")
P(md(dist.round(2)))
bins = [-1e9, -500, -200, -100, -50, -20, 0, 20, 50, 100, 200, 1e9]
hb = p.groupby(pd.cut(p.net, bins), observed=False).net.agg(["count", "sum"]).round(2)
hb.index = hb.index.astype(str); P(""); P(md(hb))
w, l = p[p.net > 0], p[p.net < 0]
P("")
P(f"winners n={len(w)}: median pts {w.pts.median():.2f}, median MAE {w.mae_pts.median():.2f}, MAE > own gain in {100 * (w.mae_pts > w.pts).mean():.1f}% ; "
  f"MAE >= 10 pts in {100 * (w.mae_pts >= 10).mean():.1f}% ; MAE >= 20 pts in {100 * (w.mae_pts >= 20).mean():.1f}%")
P(f"losers  n={len(l)}: median pts {l.pts.median():.2f}, median MAE {l.mae_pts.median():.2f}, median MFE {l.mfe_pts.median():.2f}, "
  f"had been >= 3 pts in profit first: {100 * (l.mfe_pts >= 3).mean():.1f}%")
top = p.sort_values("net")[["position_id", "side", "open_time", "close_time", "volume", "entry", "exit", "pts", "net", "exit_kind", "mae_pts", "ctx"]]
P(""); P("ten worst positions:"); P(md(top.head(10).round(2), index=False))
P(""); P("ten best positions:"); P(md(top.tail(10).iloc[::-1].round(2), index=False))
P(""); P(f"worst 5 positions = {top.head(5).net.sum():.2f} USD = {100 * top.head(5).net.sum() / l.net.sum():.1f}% of gross loss; "
         f"all SO = {p.net[p.exit_kind == 'SO'].sum():.2f} ({100 * p.net[p.exit_kind == 'SO'].sum() / l.net.sum():.1f}% of gross loss); "
         f"P&L excluding SO exits = {p.net[p.exit_kind != 'SO'].sum():.2f}")

# ------------------------------------------------------------------ streaks
H("13. Streaks (positions ordered by close time)")
c = p.sort_values(["close_time", "position_id"]); s = np.sign(c.net.values)
runs, cur, k = [], s[0], 0
for i, v in enumerate(s):
    if v != cur:
        runs.append((cur, k, c.net.values[i - k:i].sum(), c.close_time.iloc[i - k], c.close_time.iloc[i - 1])); cur, k = v, 0
    k += 1
runs.append((cur, k, c.net.values[len(s) - k:].sum(), c.close_time.iloc[len(s) - k], c.close_time.iloc[-1]))
R = pd.DataFrame(runs, columns=["sign", "len", "usd", "from", "to"])
for sg, nm in ((1, "win"), (-1, "loss")):
    r = R[R.sign == sg].sort_values("len", ascending=False)
    P(f"{nm} streaks: n={len(r)}, mean length {r.len.mean():.1f}, median {r.len.median():.0f}; longest: " +
      "; ".join(f"{int(x.len)} ({x.usd:+.0f} USD, {x['from']:%m-%d %H:%M}..{x['to']:%m-%d %H:%M})" for _, x in r.head(4).iterrows()))
P(f"zero-P&L positions (close-by counter-legs): {(s == 0).sum()}")
P(f"first {int(R.len.iloc[0])} positions were all winners" if R.sign.iloc[0] == 1 else "")

# ------------------------------------------------------------------ cash
H("14. Cash: money in, money out, what is left")
b = d[d.type.isin(["DEAL_TYPE_BALANCE", "DEAL_TYPE_CREDIT"])].copy()
def kind(r):
    c = r.comment
    if r.type == "DEAL_TYPE_CREDIT":
        return "credit: bonus granted" if c.startswith("Credit-In") else ("credit: reinstated after failed withdrawal" if c == "Credit In" else "credit: removed (Credit Out)")
    if "ERR" in c: return "failed withdrawal + reversal (nets to 0)"
    if c.startswith("CD-"): return "deposit (external)"
    if c.startswith("Transfer"): return "deposit (transfer from another XM account)"
    if c.startswith("CW-"): return "withdrawal"
    if c.startswith("EXP05"): return "EXP05 broker top-up booked with each deposit (fee/FX rebate)"
    if c.startswith("EXP06"): return "EXP06 bonus credit converted to balance after a stop-out (matches a Credit Out)"
    if c.startswith("EXP01"): return "EXP01 negative-balance reset paid by broker"
    return "other"
b["kind"] = b.apply(kind, axis=1)
ct = b.groupby(["type", "kind"]).profit.agg(["count", "sum"]).round(2)
ct.to_csv(OUT / "tab_cash.csv"); P(md(ct))
bs = lambda k: b[b.kind.str.startswith(k)].profit.sum()
dep_ext, dep_tr, wd, e5, e6, e1 = bs("deposit (external"), bs("deposit (transfer"), -bs("withdrawal"), bs("EXP05"), bs("EXP06"), bs("EXP01")
pnl = p.net.sum(); dep = dep_ext + dep_tr
P("")
P(f"identity: deposits {dep:.2f} + EXP05 {e5:.2f} + EXP06 {e6:.2f} + EXP01 {e1:.2f} + trading P&L {pnl:.2f} - withdrawals {wd:.2f} = {dep + e5 + e6 + e1 + pnl - wd:.2f} (final balance 0.00)")
P(f"money in: {dep:.2f} USD ({dep_ext:.2f} external in {int((b.kind == 'deposit (external)').sum())} deposits + {dep_tr:.2f} transfer); money out: {wd:.2f} in {int((b.kind == 'withdrawal').sum())} withdrawals; "
  f"left: balance 0.00, non-withdrawable credit {b[b.type == 'DEAL_TYPE_CREDIT'].profit.sum():.2f}")
P(f"net cash to the owner: {wd - dep:+.2f} USD = {100 * (wd - dep) / dep:+.1f}% of total deposited; of which trading P&L {pnl:.2f}, bonus credit consumed by losses {e6:.2f}, "
  f"broker negative-balance resets {e1:.2f}, deposit top-ups {e5:.2f}")
cr = b[b.type == "DEAL_TYPE_CREDIT"]
P(f"bonus credit: granted {cr[cr.kind == 'credit: bonus granted'].profit.sum():.2f}, removed {cr[cr.kind.str.contains('removed')].profit.sum():.2f}, "
  f"reinstated {cr[cr.kind.str.contains('reinstated')].profit.sum():.2f}; of the removals {e6:.2f} were loss cover (EXP06) and the rest was clawed back on withdrawals")
# time-weighted capital
mk = g[g.market_open]
P(f"capital in the account: time-avg balance {g.balance.mean():.2f}, time-avg equity {g.equity.mean():.2f}, max balance {g.balance.max():.2f} ({g.balance.idxmax():%m-%d %H:%M})")
cumdep = b[b.kind.str.startswith("deposit")].set_index("time").profit.cumsum()
cumnet = b[b.kind.str.startswith(("deposit", "withdrawal"))].set_index("time").profit.cumsum()
P(f"cumulative own money net in the account: max {cumnet.max():.2f} at {cumnet.idxmax():%m-%d %H:%M}; min {cumnet.min():.2f} at {cumnet.idxmin():%m-%d %H:%M} (negative = already withdrew more than deposited)")
P(""); P("cash ledger:"); 
led = b[["time", "type", "profit", "comment", "kind"]].copy(); led["time"] = led.time.dt.strftime("%m-%d %H:%M:%S"); led["type"] = led.type.str.replace("DEAL_TYPE_", "")
led.to_csv(OUT / "cash_ledger.csv", index=False)

# ------------------------------------------------------------------ drawdown
H("15. Drawdown: balance (realised) vs equity (realised + floating), cash flows removed")
def maxdd(s):
    pk = s.cummax(); ddv = s - pk; t = ddv.idxmin(); return ddv.min(), pk.loc[:t].idxmax(), t, pk.loc[t]
rows = []
for nm, s in (("realised P&L (balance, ex cash flows)", g.realised_pnl), ("P&L incl. floating, 5 s closes (equity, ex cash flows)", g.pnl_incl_floating),
              ("P&L incl. floating, worst intrabar mark", g.realised_pnl + (g.equity_low - g.balance - g.credit))):
    v, a, t, pk = maxdd(s)
    rows.append(dict(curve=nm, max_dd_usd=v, peak_time=a.strftime("%m-%d %H:%M"), trough_time=t.strftime("%m-%d %H:%M"), peak_value=pk, trough_value=s.loc[t], final=s.iloc[-1], high=s.max()))
P(md(pd.DataFrame(rows).round(2), index=False))
P("")
fmin = g.floating.idxmin()
P(f"largest floating loss on 5 s closes: {g.floating.min():.2f} USD at {fmin:%m-%d %H:%M:%S} (balance {g.balance.loc[fmin]:.2f}, credit {g.credit.loc[fmin]:.2f}, "
  f"equity {g.equity.loc[fmin]:.2f}, net lots {g.net_lots.loc[fmin]:.2f})")
P(f"lowest equity (intrabar): {g.equity_low.min():.2f} at {g.equity_low.idxmin():%m-%d %H:%M:%S}; lowest balance {g.balance.min():.2f} at {g.balance.idxmin():%m-%d %H:%M:%S}")
op = mk[mk.gross_lots > 0]
P(f"while exposed with a live quote (n={len(op):,} 5 s rows = {len(op) * 5 / 3600:.1f} h): floating < 0 in {100 * (op.floating < 0).mean():.1f}% of the time, "
  f"median floating {op.floating.median():.2f}, mean {op.floating.mean():.2f}; floating worse than -100 USD {100 * (op.floating < -100).mean():.1f}%, worse than -500 USD {100 * (op.floating < -500).mean():.1f}%")
P(f"floating as a share of (balance+credit) while exposed: median {100 * (op.floating / (op.balance + op.credit)).median():.1f}%, p10 {100 * (op.floating / (op.balance + op.credit)).quantile(.1):.1f}%, "
  f"min {100 * (op.floating / (op.balance + op.credit)).min():.1f}%")
ml = op.margin_level.dropna()
P(f"margin level while net-exposed (n={len(ml):,} rows): median {ml.median():.0f}%, p10 {ml.quantile(.1):.0f}%, p1 {ml.quantile(.01):.0f}%; "
  f"below 100% {100 * (ml < 100).mean():.2f}% of the time, below 50% {100 * (ml < 50).mean():.2f}% (stop-out at 20%)")
lev = (op.net_lots.abs() * OZ * op.bid / op.equity.where(op.equity > 0))
P(f"effective leverage |net notional| / equity while exposed: median {lev.median():.0f}x, p90 {lev.quantile(.9):.0f}x, p99 {lev.quantile(.99):.0f}x; "
  f"gross notional/equity median {(op.gross_lots * OZ * op.bid / op.equity.where(op.equity > 0)).median():.0f}x")
adv = (op.equity - op.margin * 0.2) / (op.net_lots.abs() * OZ).where(op.net_lots != 0)
P(f"distance to stop-out (pts of adverse move the net book could absorb before margin level hits 20%): median {adv.median():.1f}, p25 {adv.quantile(.25):.1f}, p10 {adv.quantile(.1):.1f}, p1 {adv.quantile(.01):.1f}")

# ------------------------------------------------------------------ exposure
H("16. Exposure stacking (time-weighted on 5 s rows with a live quote)")
n_open = mk.n_long + mk.n_short
tot = len(mk)
P(f"rows {tot:,} = {tot * 5 / 3600:.1f} h of open market between first and last deal; flat {100 * (n_open == 0).mean():.1f}% of that time")
vc = pd.cut(n_open, [-1, 0, 1, 2, 3, 5, 10, 100], labels=["0", "1", "2", "3", "4-5", "6-10", ">10"]).value_counts(sort=False)
P(md(pd.DataFrame({"hours": (vc * 5 / 3600).round(1), "share_%": (100 * vc / tot).round(1)}).rename_axis("positions_open")))
ex = mk[n_open > 0]
same = np.maximum(ex.n_long, ex.n_short)
P("")
P(f"while exposed ({len(ex) * 5 / 3600:.1f} h): >= 2 positions on the same side {100 * (same >= 2).mean():.1f}% of the time, >= 3 {100 * (same >= 3).mean():.1f}%, >= 5 {100 * (same >= 5).mean():.1f}%; max same-side positions {int(same.max())}")
both = (ex.n_long > 0) & (ex.n_short > 0)
P(f"hedged both ways (long and short open together) {100 * both.mean():.1f}% of exposed time ({both.sum() * 5 / 3600:.1f} h); fully locked (net 0, gross > 0) {100 * (ex.net_lots == 0).mean():.1f}% ({(ex.net_lots == 0).sum() * 5 / 3600:.2f} h)")
P(f"max gross lots {g.gross_lots.max():.2f} at {g.gross_lots.idxmax():%m-%d %H:%M:%S}; max |net| lots {g.net_lots.abs().max():.2f} at {g.net_lots.abs().idxmax():%m-%d %H:%M:%S}; "
  f"max positions open {int((g.n_long + g.n_short).max())}; time-avg |net| lots while exposed {ex.net_lots.abs().mean():.3f}, gross {ex.gross_lots.mean():.3f}")
P(f"net long {100 * (ex.net_lots > 0).mean():.1f}% / net short {100 * (ex.net_lots < 0).mean():.1f}% of exposed time")
dc = p.drop_duplicates("decision_id")
P(f"entry decisions (n={len(dc)}): " + ", ".join(f"{k} {v}" for k, v in dc.ctx.value_counts().items()) + f"; positions: " + ", ".join(f"{k} {v}" for k, v in p.ctx.value_counts().items()))
al = dc[dc.ctx == "add_to_loser"]
P(f"add-to-loser decisions (n={len(al)}): basket was {(-al.basket_pts).median():.2f} pts under water at the add (median; p75 {(-al.basket_pts).quantile(.75):.2f}, max {(-al.basket_pts).max():.2f}); "
  f"distance from the previous same-side entry {al.gap_prev_pts.abs().median():.2f} pts median")
P(f"lot-size escalation: positions above 0.04 lots: {int((p.volume > 0.04).sum())} -> " + "; ".join(f"{r.open_time:%m-%d %H:%M} {r.side} {r.volume} ({r.ctx}, net {r.net:+.0f})" for r in p[p.volume > 0.04].itertuples()))
P(f"weekend / overnight: positions held across the 21:59-23:05 UTC daily break: {int(((p.close_time.dt.floor('D') > p.open_time.dt.floor('D')) | ((p.open_time.dt.hour < 22) & (p.close_time.dt.hour >= 23) )).sum())}; across the weekend: {int(((p.open_time < '2026-11-07') & (p.close_time > '2026-11-08')).sum())}")
P(""); P("episodes (flat-to-flat):")
es = e.copy(); es["start"] = es.start.dt.strftime("%m-%d %H:%M"); es["end"] = es.end.dt.strftime("%m-%d %H:%M")
es.round(2).to_csv(OUT / "tab_episodes.csv", index=False)
P(md(es[["episode_id", "start", "end", "hours", "n_pos", "buys", "sells", "adds_to_loser", "max_n_open", "max_gross", "max_abs_net", "min_floating", "min_margin_level", "equity_at_start", "n_tp", "n_so", "net"]].round(2), index=False))

# ------------------------------------------------------------------ stop-outs
H("17. Margin stop-outs (34 deals) grouped into events (deals < 2 min apart)")
so = so.sort_values("time").reset_index(drop=True)
so["event"] = (so.time.diff().dt.total_seconds().fillna(0) > 120).cumsum()
q5 = pd.read_parquet(HERE.parent.parent / "xau_s5_2026-11-03_now_ba.parquet").set_index("time")
lvl = lambda t: g.margin_level.iloc[g.index.searchsorted(t, side="right") - 1]     # blank when flat or fully locked (margin 0)
rows = []
for k, s in so.groupby("event"):
    f = s.iloc[0]; t0 = f.time
    closed = p[p.position_id.isin(s.position_id)]
    w = g.loc[:t0.floor("5s")]
    ep = int(closed.episode_id.iloc[0]); est = e.start[ep]
    win = g.loc[est:t0.floor("5s")]
    below100 = win.index[(win.margin_level < 100)]
    net_before = f.long_lots - f.short_lots
    side = "long" if net_before > 0 else ("short" if net_before < 0 else "locked")
    vwap = f.long_vwap if net_before > 0 else f.short_vwap
    los = closed.sort_values("open_time")
    after = q5.loc[t0:]
    mid_after = (after.bid_close + after.ask_close) / 2
    # per stopped position: did price come back to its entry (break-even) later, within the data?
    rec = []
    for r in closed.itertuples():
        a = after.loc[r.close_time:]
        hit = a.index[(a.bid_high >= r.entry)] if r.sgn > 0 else a.index[(a.ask_low <= r.entry)]
        rec.append((hit[0] - r.close_time).total_seconds() / 3600 if len(hit) else np.nan)
    worse = (f.price - after.bid_low.min()) if net_before > 0 else ((after.ask_high.max() - f.price) if net_before < 0 else np.nan)
    rows.append(dict(event=k, first_so=t0.strftime("%m-%d %H:%M:%S"), ist=(t0 + pd.Timedelta(minutes=330)).strftime("%H:%M"), n_deals=len(s), so_cash=s.cash.sum(),
                     book_before=f"{f.long_lots:.2f}L/{f.short_lots:.2f}S", net_side=side, n_pos_before=int(f.n_long + f.n_short),
                     bal_plus_credit=f.bal_before + f.credit_before, brk_equity=f.brk_equity, brk_margin=f.brk_margin, brk_level=f.brk_level,
                     level_60m_before=lvl(t0 - pd.Timedelta(minutes=60)), level_5m_before=lvl(t0 - pd.Timedelta(minutes=5)),
                     level_10s_before=lvl(t0 - pd.Timedelta(seconds=10)), level_at_last_entry=lvl(los.open_time.max() + pd.Timedelta(seconds=10)),
                     min_under_100=(t0 - below100[0]).total_seconds() / 60 if len(below100) else 0.0,
                     oldest_pos_h=(t0 - los.open_time.min()).total_seconds() / 3600, adds_to_loser=int((closed.ctx == "add_to_loser").sum()),
                     worst_pos_pts=closed.pts.min(), recovered_n=int(np.isfinite(rec).sum()), recov_h_median=np.nanmedian(rec) if np.isfinite(rec).any() else np.nan,
                     further_adverse_pts=worse, episode=ep, episode_net=e.net[ep]))
S = pd.DataFrame(rows)
S.to_csv(OUT / "tab_stopout_events.csv", index=False)
P(md(S.round(2), index=False))
P("")
P(f"total stop-out cash {so.cash.sum():.2f} USD over {len(so)} deals / {S.shape[0]} events; winners inside SO deals: {(so.cash > 0).sum()}; "
  f"SO on a book that was hedged both ways just before: {int(((so.long_lots > 0) & (so.short_lots > 0)).sum())} deals")
P(f"bonus credit burnt covering negative balance after stop-outs (EXP06): {e6:.2f}; broker negative-balance resets (EXP01): {e1:.2f}")
hl = p[p.closeby]
P(""); P("### close-by (hedge) exits: 8 positions = 4 locked pairs, all closed 11-10 15:54:54-55")
P(md(hl[["position_id", "side", "open_time", "close_time", "volume", "entry", "exit", "net", "role", "adj_net", "comment"]].round(2), index=False))
P(f"locked loss realised by the 4 close-bys: {hl.net.sum():.2f} USD")

(OUT / "04_tables.md").write_text("\n".join(out))
print("\n".join(out))
