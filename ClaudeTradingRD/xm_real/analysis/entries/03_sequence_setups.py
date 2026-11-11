"""Step 3 - the SEQUENCE of entries (bursts, re-entry, averaging, pyramiding, flips, hedges) and the
setup-type table. Reads entries_features.csv (definitions of role / ctx_type / setup are in 01_features.py).

P&L attribution: MT5 books a close-by pair's whole result on one leg. `net_econ` puts it on the OLDER
leg (the position that was being hedged) so the hedge leg carries ~0; totals are unchanged.

Run: ../../../.venv/bin/python 03_sequence_setups.py
"""
import numpy as np
import pandas as pd

from lib import HERE, load_deals

pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_columns", 50)
e = pd.read_csv(HERE / "entries_features.csv")
for c in ("open_time", "close_time"):
    e[c] = pd.to_datetime(e[c], utc=True, format="ISO8601")
e["s"] = np.where(e.side.eq("BUY"), 1, -1)

# ---- close-by reattribution ----
e["net_econ"] = e.net
cb = e[e.exit_kind.str.endswith("CLOSEBY")]
for i, a in cb.iterrows():
    b = cb[(cb.s == -a.s) & np.isclose(cb.entry, a.exit) & np.isclose(cb.exit, a.entry)]
    assert len(b) == 1, "close-by pair not found"
    j = b.index[0]
    if i < j:                                   # i is the older leg
        e.loc[i, "net_econ"], e.loc[j, "net_econ"] = a.net + b.net.iloc[0], 0.0
assert abs(e.net_econ.sum() - e.net.sum()) < 1e-6
print(f"clicks {len(e)} | net ${e.net.sum():.2f} | click win rate {(e.net > 0).mean():.3f} | close-by legs {len(cb)}")

# ---- equity reconstruction check: at a margin stop-out equity must be ~0 ----
d = load_deals()
d["cash"] = d.profit.fillna(0) + d.commission.fillna(0) + d.swap.fillna(0)
so = d[d.reason.eq("DEAL_REASON_SO")]
chk = []
for tt in so.time.dt.floor("10s").unique():
    first = so[so.time.dt.floor("10s") == tt].iloc[0]
    bal = d[d.time < first.time].cash.sum()
    op = e[(e.open_time < first.time) & (e.close_time >= first.time)]
    flo = (op.s * (first.price - op.entry) * op.volume * 100).sum()
    margin = (op.volume * op.entry * 100 / 1000).sum()
    chk.append(dict(t=first.time.strftime("%m-%d %H:%M:%S"), balance_plus_credit=bal, floating=flo, equity=bal + flo,
                    open_lots=op.volume.sum(), margin_1to1000_unhedged=margin))
print("\nequity at each stop-out cluster (reconstruction check; XM stops out at 20% margin level):")
print(pd.DataFrame(chk).round(1).to_string(index=False))

# ---- events ----
ev = e.groupby("event_id").agg(
    t=("open_time", "first"), side=("side", "first"), s=("s", "first"), clicks=("s", "size"), lots=("volume", "sum"),
    px=("entry", "first"), role=("role", "first"), ctx=("ctx_type", "first"), setup=("setup", "first"), flip=("flip", "first"),
    campaign=("campaign_id", "first"), n_same=("n_same", "first"), lots_same=("lots_same", "first"),
    adv_vwap=("same_adverse_vwap", "first"), adv_last=("same_adverse_last", "first"), adv_first=("same_adverse_first", "first"),
    lots_opp=("lots_opp", "first"), opp_upl=("opp_upl_pts", "first"), since_exit=("secs_since_last_exit", "first"),
    last_exit_reason=("last_exit_reason", "first"), last_exit_same=("last_exit_same_side", "first"),
    equity=("equity_before", "first"), pts_to_zero=("pts_to_zero_equity", "last"), atr5=("atr5", "first"), rng60=("rng60", "first"),
    net=("net_econ", "sum"), hold_min=("hold_s", lambda x: x.median() / 60), any_so=("exit_kind", lambda x: (x == "SO").any()),
    any_tp=("exit_kind", lambda x: (x == "TP").any()), fwd15=("fwd15", "first"), fwd60=("fwd60", "first"),
    touch5=("touch5", "first"), touch10=("touch10", "first"), touch_g1=("touch_g1", "first"), touch_g2=("touch_g2", "first"), day=("open_time", lambda x: x.iloc[0].strftime("%m-%d")))
ev["pts_per_lot"] = ev.net / (ev.lots * 100)
ev["win"] = ev.net > 0
ev["gap_min"] = ev.t.diff().dt.total_seconds() / 60
ev.to_csv(HERE / "events.csv")
q = lambda s_, qs=(.1, .25, .5, .75, .9): dict(zip([f"p{int(x * 100)}" for x in qs], np.round(s_.quantile(list(qs)).to_numpy(), 2)))

print(f"\n== A. bursts ==  events {len(ev)} from {len(e)} clicks; clicks/event {ev.clicks.value_counts().sort_index().to_dict()}")
print("lots per event:", ev.lots.round(2).value_counts().sort_index().to_dict())
print("lots per CLICK:", e.volume.value_counts().sort_index().to_dict())
print("clicks per decision by role:\n", ev.groupby("role").clicks.value_counts().unstack(fill_value=0).to_string())
print("lots per decision by role (mean / median):", ev.groupby("role").lots.agg(["mean", "median"]).round(3).to_dict("index"))
tpd = (e.tp - e.entry).abs()
print(f"TP attached on {int(e.tp.notna().sum())}/{len(e)} clicks, SL on {int(e.sl.notna().sum())}; |TP - entry| (final TP value) quantiles {q(tpd.dropna())};"
      f" share within 0.1 of 5.06 pt: {((tpd - 5.06).abs() < 0.1).mean():.2f}")
print("TP attached by role:", e.groupby("role").tp.apply(lambda x: round(x.notna().mean(), 2)).to_dict())
fc = e[e.click_in_event == 0]
print("deal-price distance to the nearest $5 / $10 / $50 (uniform expectation 1.25 / 2.5 / 12.5):",
      [round(float(np.abs((fc.entry + m / 2) % m - m / 2).mean()), 2) for m in (5, 10, 50)])
print("events by day:", ev.groupby("day").size().to_dict(), "| side:", ev.side.value_counts().to_dict())
print("events by UTC hour:", ev.t.dt.hour.value_counts().sort_index().to_dict())
print("events by session:", e[e.click_in_event == 0].session.value_counts().to_dict())

print("\n== B. time between decisions (min) ==", q(ev.gap_min.dropna()),
      "| share <5m %.2f, 5-30m %.2f, 30-120m %.2f, >120m %.2f" % tuple(
          ((ev.gap_min >= a) & (ev.gap_min < b)).sum() / ev.gap_min.notna().sum() for a, b in ((0, 5), (5, 30), (30, 120), (120, 1e9))))

print("\n== C. re-entry after an exit ==")
x = ev[ev.since_exit.notna()]
print("secs from the last exit to the decision:", q(x.since_exit), "| <=10s %d, <=60s %d, <=5min %d of %d" % (
    (x.since_exit <= 10).sum(), (x.since_exit <= 60).sum(), (x.since_exit <= 300).sum(), len(x)))
r = x[x.since_exit <= 60]
print("decisions within 60 s of an exit, by that exit's reason and whether the new entry is the SAME side as the closed position:")
print(r.groupby(["last_exit_reason", "last_exit_same"]).agg(n=("net", "size"), win=("win", "mean"), net=("net", "sum")).round(2).to_string())
# from the TP's point of view: what is the next decision after each TP fill cluster?
tp = e[e.exit_kind == "TP"].copy()
tp["cl"] = tp.close_time.dt.floor("5s")
rows = []
for cl, grp in tp.groupby("cl"):
    nxt = ev[ev.t > grp.close_time.max()]
    if len(nxt):
        n0 = nxt.iloc[0]
        rows.append(dict(delay_s=(n0.t - grp.close_time.max()).total_seconds(), same_side=n0.s == grp.s.iloc[0], n_tp=len(grp)))
tpn = pd.DataFrame(rows)
print(f"TP fill clusters {len(tpn)} (from {len(tp)} TP'd clicks): next decision within 60 s {int((tpn.delay_s <= 60).sum())}, within 5 min {int((tpn.delay_s <= 300).sum())};",
      "of those within 5 min: same side as the TP'd position %d, opposite (fade the move that paid) %d" % (
          tpn[tpn.delay_s <= 300].same_side.sum(), (~tpn[tpn.delay_s <= 300].same_side).sum()))

print("\n== roles (decision level) ==")
print(ev.groupby("role").agg(events=("net", "size"), clicks=("clicks", "sum"), lots=("lots", "sum"), win=("win", "mean"),
                             net=("net", "sum"), exp=("net", "mean"), pts_per_lot=("pts_per_lot", "mean"), so=("any_so", "mean")).round(2).to_string())

print("\n== D. adding to a loser (avg_add) ==")
a = ev[ev.role == "avg_add"]
print(f"n events {len(a)} ({a.clicks.sum()} clicks) = {len(a) / len(ev):.0%} of all decisions")
print("spacing vs previous same-side fill (pts, + = price went against the basket):", q(a.adv_last))
print("  ... in ATR(M5) units:", q(a.adv_last / a.atr5))
print("basket VWAP under water at the add (pts):", q(a.adv_vwap), "| depth below the basket's FIRST fill:", q(a.adv_first))
print("positions already open on that side before the add:", a.n_same.value_counts().sort_index().to_dict())
prev_lots = []
for i, r_ in a.iterrows():                       # lot progression: this add vs the previous same-side decision
    p = ev[(ev.side == r_.side) & (ev.t < r_.t)].iloc[-1]
    prev_lots.append(r_.lots / p.lots)
pl_ = pd.Series(prev_lots)
print("lot ratio add / previous same-side decision:", pl_.round(2).value_counts().sort_index().to_dict(),
      "| share >1x: %.2f, =1x: %.2f, <1x: %.2f" % ((pl_ > 1.01).mean(), ((pl_ - 1).abs() <= 0.01).mean(), (pl_ < 0.99).mean()))
print("spacing regularity: CV of spacing %.2f (a fixed-step grid would be ~0)" % (a.adv_last.std() / a.adv_last.mean()))
print("adds placed while the basket is under water by <5 / 5-10 / 10-20 / >20 pts:",
      [int(((a.adv_first >= lo) & (a.adv_first < hi)).sum()) for lo, hi in ((-99, 5), (5, 10), (10, 20), (20, 999))])
print("outcome of avg_add decisions by depth below first fill:")
a2 = a.assign(depth=pd.cut(a.adv_first, [-99, 5, 10, 20, 999], labels=["<5", "5-10", "10-20", ">20"]))
print(a2.groupby("depth", observed=True).agg(n=("net", "size"), win=("win", "mean"), net=("net", "sum"), exp=("net", "mean"), so=("any_so", "mean")).round(2).to_string())

print("\n== E. adding to a winner (pyramid_add) / same-level add ==")
for r_ in ("pyramid_add", "level_add"):
    p = ev[ev.role == r_]
    print(f"{r_}: n {len(p)}, basket in profit by (pts) {q(-p.adv_vwap)}, win {p.win.mean():.2f}, net {p.net.sum():.2f}")

print("\n== F. flips (flat, last exit <=5 min ago was the opposite side) ==")
f = ev[ev.flip == True]  # noqa: E712
print(f"n {len(f)} of {int((ev.role == 'first').sum())} fresh entries; secs after the exit {q(f.since_exit)}; win {f.win.mean():.2f}; net {f.net.sum():.2f}")
nf = ev[(ev.role == "first") & (ev.flip != True)]  # noqa: E712
print(f"fresh entries that are not flips: n {len(nf)}, win {nf.win.mean():.2f}, net {nf.net.sum():.2f}")

print("\n== G. entries against an open opposite basket ('hedge' role) ==")
h = ev[ev.role == "hedge"].assign(opp_state=lambda z: np.where(z.opp_upl <= -1, "opp_losing", np.where(z.opp_upl >= 1, "opp_winning", "opp_flat")))
print(h.groupby("opp_state").agg(n=("net", "size"), lots=("lots", "sum"), opp_lots=("lots_opp", "mean"), opp_upl=("opp_upl", "median"),
                                 win=("win", "mean"), net=("net", "sum"), hold_min=("hold_min", "median")).round(2).to_string())
both = ev[(ev.lots_opp > 0)]
print(f"decisions taken with ANY opposite position open: {len(both)} of {len(ev)}; close-by legs {len(cb)}; positions with an SL: {int(e.sl.notna().sum())}")

print("\n== H. distance to wipe-out at entry ==")
print("adverse move (pts) on the net position that takes equity to zero, right after the decision:", q(ev.pts_to_zero.replace(np.inf, np.nan).dropna()))
z = (ev.pts_to_zero / ev.rng60).replace(np.inf, np.nan).dropna()
print("  as a multiple of the prior 60-min range:", q(z), "| share of decisions with < one 60-min range of room: %.2f" % (z < 1).mean())
print("equity (balance+credit+floating) before the decision, $:", q(ev.equity))

# ---- same-side baskets and flat-to-flat campaigns ----
e = e.sort_values(["open_time", "position_id"]).reset_index(drop=True)
bid_ = np.zeros(len(e), int)
for sd in (1, -1):
    end, k = pd.Timestamp("2000-01-01", tz="UTC"), 0
    for i in e.index[e.s == sd]:
        if e.open_time[i] > end:
            k += 1
        end = max(end, e.close_time[i])
        bid_[i] = k * sd
e["basket"] = bid_
bk = e.groupby("basket").agg(start=("open_time", "first"), side=("side", "first"), clicks=("s", "size"), events=("event_id", "nunique"),
                             lots=("volume", "sum"), n_avg=("role", lambda x: 0), net=("net_econ", "sum"), so=("exit_kind", lambda x: (x == "SO").any()),
                             dur_h=("close_time", "max"))
bk["n_avg"] = e[e.click_in_event == 0].groupby("basket").role.apply(lambda x: (x == "avg_add").sum()).reindex(bk.index).fillna(0).astype(int)
bk["dur_h"] = (bk.dur_h - bk.start).dt.total_seconds() / 3600
bk["adds"] = pd.cut(bk.n_avg, [-1, 0, 1, 3, 99], labels=["0", "1", "2-3", "4+"])
print("\n== I. same-side baskets (side goes from 0 open positions back to 0) by number of averaging adds ==")
print(bk.groupby("adds", observed=True).agg(baskets=("net", "size"), clicks=("clicks", "sum"), win=("net", lambda x: (x > 0).mean()), net=("net", "sum"),
                                            mean=("net", "mean"), worst=("net", "min"), best=("net", "max"), so=("so", "mean"), dur_h=("dur_h", "median")).round(2).to_string())
cp = e.groupby("campaign_id").agg(start=("open_time", "first"), end=("close_time", "max"), clicks=("s", "size"), events=("event_id", "nunique"),
                                  lots=("volume", "sum"), net=("net", "sum"), so=("exit_kind", lambda x: (x == "SO").sum()))
cp["dur_h"] = (cp.end - cp.start).dt.total_seconds() / 3600
cp["start"] = cp.start.dt.strftime("%m-%d %H:%M")
print(f"\nflat-to-flat campaigns: {len(cp)}, winners {int((cp.net > 0).sum())}, net of winners {cp.net[cp.net > 0].sum():.0f}, of losers {cp.net[cp.net <= 0].sum():.0f}")
print(cp.drop(columns="end").round(2).to_string())

# ---- setup tables ----
rng = np.random.default_rng(3)
def table(grp):
    def ci(x):
        b = rng.choice(x.to_numpy(), (5000, len(x))).mean(1)
        return f"[{np.quantile(b, .025):.0f}, {np.quantile(b, .975):.0f}]"
    t = grp.agg(events=("net", "size"), clicks=("clicks", "sum"), lots=("lots", "sum"), win=("win", "mean"), net=("net", "sum"),
                exp=("net", "mean"), median=("net", "median"), worst=("net", "min"), so=("any_so", "mean"), hold_min=("hold_min", "median"),
                fwd15=("fwd15", "mean"), fwd60=("fwd60", "mean"), touch5=("touch5", "mean"), touch_g1=("touch_g1", "mean"))
    t["pts_per_lot"] = grp.net.sum() / (grp.lots.sum() * 100)
    t["exp_ci95"] = grp.net.apply(ci)
    return t.round(2)
print("\n== J. setup types, decision level (win = decision's summed net > 0; exp = $ per decision; fwd/touch = exit-independent) ==")
print(table(ev.groupby("setup")).to_string())
ev["kind"] = np.where(ev.role.eq("first"), "FIRST", np.where(ev.role.eq("hedge"), "vs_opp_basket", "ADD"))
print("\ncontext type x FIRST entry of a sequence / ADD to a same-side basket / entry against an opposite basket:")
print(table(ev.groupby(["kind", "ctx"])).to_string())
print("\ncontext type, all decisions:")
print(table(ev.groupby("ctx")).to_string())
print("\nsetup x day, net $:")
print(ev.pivot_table(index="setup", columns="day", values="net", aggfunc="sum", fill_value=0).round(0).to_string())
print("\nclick-level check: setup -> n clicks, click win rate, net")
print(e.groupby("setup").agg(n=("net_econ", "size"), win=("net_econ", lambda x: (x > 0).mean()), net=("net_econ", "sum")).round(2).to_string())

# sensitivity of the burst threshold
T = e.open_time.astype("int64").to_numpy() if False else (e.open_time - e.open_time.min()).dt.total_seconds().to_numpy()
for th in (5, 10, 30, 60, 120):
    new = (np.r_[np.inf, np.diff(T)] > th) | (np.r_[0, e.s.to_numpy()[:-1]] != e.s.to_numpy())
    print(f"burst threshold {th:>3}s -> {int(new.sum())} decision events")

# ---- post hoc (NOT pre-registered): what the unclassified 'other' decisions look like, and side vs the day ----
o = fc[fc.ctx_type == "other"]
print(f"\npost hoc - 'other' context (n {len(o)}): 5-min move against the trade {(o.ret5_dir < 0).mean():.2f}, adverse third of the 15-min range {(o.pos15_dir <= 1 / 3).mean():.2f},"
      f" median position in the 60-min range {o.pos60_dir.median():.2f}")
print("share of decisions that fade (by subset): 5-min move against the trade / adverse third of 15-min range / price on the counter-trend side of EMA20(M1) / of EMA20(M5)")
for nm, x in (("all", fc), ("first", fc[fc.role == "first"]), ("avg_add", fc[fc.role == "avg_add"]), ("hedge", fc[fc.role == "hedge"])):
    print(f"  {nm:8s} n {len(x):3d}: {(x.ret5_dir < 0).mean():.2f} / {(x.pos15_dir <= 1 / 3).mean():.2f} / {(x.ema20_m1_side < 0).mean():.2f} / {(x.ema20_m5_side < 0).mean():.2f}")
print("side by day (decisions) and lots:")
print(ev.pivot_table(index="day", columns="side", values="lots", aggfunc=["size", "sum"], fill_value=0).round(2).to_string())
fc = fc.assign(day=fc.open_time.dt.strftime("%m-%d"))
print("\nis the fade signature one day's artefact? per-day mean over decisions (random entries: ret5_dir ~ 0, pos15_dir ~ 0.5)")
print(fc.groupby("day").agg(n=("ret5_dir", "size"), ret5_dir=("ret5_dir", "mean"), pos15_dir=("pos15_dir", "mean"),
                            ema20_m1_against=("ema20_m1_side", lambda x: (x < 0).mean()), fade_brk60=("fade_brk60", "mean")).round(2).to_string())
fx = fc[fc.role == "first"]
print("FIRST entries only:")
print(fx.groupby("day").agg(n=("ret5_dir", "size"), ret5_dir=("ret5_dir", "mean"), pos15_dir=("pos15_dir", "mean")).round(2).to_string())

# ---- how the behaviour changed across the six days ----
e["day"] = e.open_time.dt.strftime("%m-%d")
e["gross_after"] = e.lots_same + e.lots_opp + e.volume
dd = ev.groupby("day").agg(decisions=("net", "size"), fresh=("role", lambda x: (x == "first").sum()), avg_adds=("role", lambda x: (x == "avg_add").sum()),
                           vs_opp=("role", lambda x: (x == "hedge").sum()), lots_mean=("lots", "mean"), lots_max=("lots", "max"),
                           equity_med=("equity", "median"), pts_to_zero_med=("pts_to_zero", "median"), net=("net", "sum"))
dd["gross_lots_max"] = e.groupby("day").gross_after.max()
dd["positions_open_max"] = e.groupby("day").apply(lambda x: (x.n_same + x.n_opp + 1).max(), include_groups=False)
print("\n== K. by day ==")
print(dd.round(2).to_string())
