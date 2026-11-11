"""Is there an ENTRY edge, or is the P&L leverage + holding losers?  -> results/05_edge.md

A  fixed-horizon forward return of every entry decision (first clip), signed, net of spread, vs a time-shifted control
B  symmetric bracket (TP = SL = k pts) on the same entries, S5 quote-resolved, same-bar tie = stop, vs the same control
C  the trader's actual trades with a hard stop bolted on (static replay)
D  how much of the gross profit came from positions that were deep under water first
E  sampling error: cluster bootstrap of the total by episode, leave-one-out, flat-lot normalisation
Quotes: OANDA S5 bid/ask shifted onto XM's quote (01_basis.py).  Longs exit on bid, shorts on ask.
Control: for each real decision, 40 fake entries on the same side at a uniformly random time within +/-3 h of the real one
(same day and regime, same long/short mix, no timing information), filled at the quote.
"""
import numpy as np
import pandas as pd
from common import xm_quotes, OUT, OZ, md

rng = np.random.default_rng(11)
q = xm_quotes()
T = (q.index + pd.Timedelta(seconds=5)).values            # bar END times
bid_c, ask_c = q.bid_close.values, q.ask_close.values
bid_h, bid_l, ask_h, ask_l = q.bid_high.values, q.bid_low.values, q.ask_high.values, q.ask_low.values
p = pd.read_csv(OUT / "positions_enriched.csv", parse_dates=["open_time", "close_time"])
dec = p.sort_values("open_time").drop_duplicates("decision_id").reset_index(drop=True)
out = []
H = lambda s: out.extend(["", "## " + s, ""])
P = lambda *a: out.append(" ".join(str(x) for x in a))
S60 = np.timedelta64(60, "s")


def quote_at(t):
    """index of the last bar ended at or before t, and whether it is fresh (<= 60 s old)."""
    i = np.searchsorted(T, t, side="right") - 1
    ok = (i >= 0) & ((t - T[np.clip(i, 0, None)]) <= S60)
    return np.clip(i, 0, None), ok


def fwd(t, sgn, fill, mins):
    i, ok = quote_at(t + np.timedelta64(mins, "m"))
    px = np.where(sgn > 0, bid_c[i], ask_c[i])
    return np.where(ok, sgn * (px - fill), np.nan)


def bracket(t, sgn, fill, k, max_bars=17280):
    """+k / -k / mark-to-quote if unresolved in 24 h of bars. Scans bars that START after the entry."""
    res = np.empty(len(t))
    i0 = np.searchsorted(q.index.values, t, side="right")
    for j in range(len(t)):
        a, b = i0[j], min(i0[j] + max_bars, len(T))
        if sgn[j] > 0:
            stop = bid_l[a:b] <= fill[j] - k; tgt = bid_h[a:b] >= fill[j] + k
        else:
            stop = ask_h[a:b] >= fill[j] + k; tgt = ask_l[a:b] <= fill[j] - k
        hit = stop | tgt
        if not hit.any():
            res[j] = sgn[j] * ((bid_c[b - 1] if sgn[j] > 0 else ask_c[b - 1]) - fill[j]) if b > a else np.nan
        else:
            h = hit.argmax(); res[j] = -k if stop[h] else k
    return res


# ---- real entries and matched control
rt, rs, rf = dec.open_time.values.astype("datetime64[ns]"), dec.sgn.values, dec.entry.values
K = 40
off = rng.uniform(-3 * 3600, 3 * 3600, (len(dec), K))
ct = (rt[:, None] + (off * 1e9).astype("timedelta64[ns]")).ravel()
cs = np.repeat(rs, K)
ci, cok = quote_at(ct)
cf = np.where(cs > 0, ask_c[ci], bid_c[ci])
ct, cs, cf, cgrp = ct[cok], cs[cok], cf[cok], np.repeat(np.arange(len(dec)), K)[cok]
ep = dec.episode_id.values


def cluster_ci(x, groups, stat=np.nanmean, n=4000):
    ug = np.unique(groups); idx = [np.where(groups == g)[0] for g in ug]
    bs = [stat(x[np.concatenate([idx[i] for i in rng.integers(0, len(ug), len(ug))])]) for _ in range(n)]
    return np.nanquantile(bs, .025), np.nanquantile(bs, .975)


H("A. Fixed-horizon forward return of the entries (pts, signed in the trade direction, net of spread)")
P(f"unit = entry decision (first clip), n = {len(dec)} ({int((rs > 0).sum())} buys, {int((rs < 0).sum())} sells); control n = {len(ct):,}; CI = bootstrap over the 27 flat-to-flat episodes")
rows = []
for m in (1, 5, 15, 30, 60, 120, 240, 480):
    a = fwd(rt, rs, rf, m); c = fwd(ct, cs, cf, m)
    lo, hi = cluster_ci(a, ep)
    rows.append(dict(horizon_min=m, n=int(np.isfinite(a).sum()), mean=np.nanmean(a), median=np.nanmedian(a), pct_pos=100 * np.nanmean(a[np.isfinite(a)] > 0),
                     ci_lo=lo, ci_hi=hi, ctrl_mean=np.nanmean(c), ctrl_pct_pos=100 * np.nanmean(c[np.isfinite(c)] > 0), sd=np.nanstd(a),
                     mean_minus_ctrl=np.nanmean(a) - np.nanmean(c)))
A = pd.DataFrame(rows); A.to_csv(OUT / "tab_edge_forward.csv", index=False)
P(md(A.round(2), index=False))
P("")
for nm, msk in (("buys", rs > 0), ("sells", rs < 0)):
    P(f"{nm} (n={int(msk.sum())}): " + ", ".join(f"{m}m {np.nanmean(fwd(rt[msk], rs[msk], rf[msk], m)):+.2f} (ctrl {np.nanmean(fwd(ct[cs == (1 if nm == 'buys' else -1)], cs[cs == (1 if nm == 'buys' else -1)], cf[cs == (1 if nm == 'buys' else -1)], m)):+.2f})" for m in (5, 30, 60, 240)))
for nm in ("fresh_flat", "add_to_loser", "counter_side"):
    msk = (dec.ctx == nm).values
    P(f"{nm} decisions (n={int(msk.sum())}): " + ", ".join(f"{m}m {np.nanmean(fwd(rt[msk], rs[msk], rf[msk], m)):+.2f}" for m in (5, 30, 60, 240)))

H("B. Symmetric bracket TP = SL = k pts on the same entries (quote-resolved on S5, same-bar tie = stop)")
rows = []
for k in (3, 5, 8, 12, 20):
    a = bracket(rt, rs, rf, k); c = bracket(ct, cs, cf, k)
    res_a, res_c = np.isfinite(a) & (np.abs(a) == k), np.isfinite(c) & (np.abs(c) == k)
    wr, wc = (a[res_a] > 0).mean(), (c[res_c] > 0).mean()
    lo, hi = cluster_ci(np.where(res_a, (a > 0).astype(float), np.nan), ep)
    rows.append(dict(k_pts=k, n_resolved=int(res_a.sum()), win_pct=100 * wr, ci_lo=100 * lo, ci_hi=100 * hi, mean_pts=np.nanmean(a),
                     ctrl_n=int(res_c.sum()), ctrl_win_pct=100 * wc, ctrl_mean_pts=np.nanmean(c), breakeven_win_pct=50.0))
B = pd.DataFrame(rows); B.to_csv(OUT / "tab_edge_bracket.csv", index=False)
P(md(B.round(2), index=False))

H("C. The actual trades with a hard stop added (static replay: same entries, same exits unless the stop is hit first)")
P("stop fills at exactly -X pts (no slippage; optimistic in news bars). 'flat' = every position re-sized to 0.04 lots. Hedge legs of close-by pairs dropped (n=174).")
tr = p[p.role == "trade"].copy()
rows = []
for X in (3, 5, 8, 10, 15, 20, 30, 50, 1e9):
    stopped = tr.mae_pts >= X
    pts = np.where(stopped, -X, tr.adj_pts)
    usd = pts * tr.volume * OZ; flat = pts * 0.04 * OZ
    rows.append(dict(stop_pts="none (actual)" if X > 1e8 else X, n_stopped=int(stopped.sum()), win_pct=100 * (pts > 0).mean(), net_usd=usd.sum(),
                     PF=usd[usd > 0].sum() / -usd[usd < 0].sum(), net_usd_flat004=flat.sum(), exp_pts=pts.mean(),
                     winners_killed=int((stopped & (tr.adj_pts > 0)).sum()), usd_lost_from_killed_winners=(tr.adj_net[stopped & (tr.adj_pts > 0)] + X * tr.volume[stopped & (tr.adj_pts > 0)] * OZ).sum(),
                     usd_saved_on_losers=(-(tr.adj_net[stopped & (tr.adj_pts <= 0)]) - X * tr.volume[stopped & (tr.adj_pts <= 0)] * OZ).sum()))
Cc = pd.DataFrame(rows); Cc.to_csv(OUT / "tab_edge_hardstop.csv", index=False)
P(md(Cc.round(2), index=False))

H("D. How much of the profit was rescued from deep adverse excursion")
w = tr[tr.adj_net > 0]; gp = w.adj_net.sum()
rows = [dict(mae_at_least=X, winners=int((w.mae_pts >= X).sum()), share_of_winners_pct=100 * (w.mae_pts >= X).mean(), usd=w.adj_net[w.mae_pts >= X].sum(),
             share_of_gross_profit_pct=100 * w.adj_net[w.mae_pts >= X].sum() / gp, median_hold_min=w.hold_s[w.mae_pts >= X].median() / 60) for X in (0, 3, 5, 10, 15, 20, 30)]
P(md(pd.DataFrame(rows).round(2), index=False))
P("")
P(f"winners: median gain {w.adj_pts.median():.2f} pts vs median MAE {w.mae_pts.median():.2f}; mean gain {w.adj_pts.mean():.2f} vs mean MAE {w.mae_pts.mean():.2f}; "
  f"MAE/gain ratio median {(w.mae_pts / w.adj_pts).median():.2f}")
l = tr[tr.adj_net < 0]
P(f"losers (n={len(l)}): mean loss {l.adj_pts.mean():.2f} pts, median {l.adj_pts.median():.2f}; exit kinds {l.exit_kind.value_counts().to_dict()}; "
  f"voluntary (MOBILE) losing exits: {int((l.exit_kind == 'MOBILE').sum())} for {l.adj_net[l.exit_kind == 'MOBILE'].sum():.2f} USD")
P(f"break-even win rate implied by avg win {w.adj_net.mean():.2f} / avg loss {l.adj_net.mean():.2f}: {100 * -l.adj_net.mean() / (w.adj_net.mean() - l.adj_net.mean()):.1f}% (actual {100 * len(w) / len(tr):.1f}%)")
P(f"in points: avg win {w.adj_pts.mean():.2f} / avg loss {l.adj_pts.mean():.2f} -> break-even {100 * -l.adj_pts.mean() / (w.adj_pts.mean() - l.adj_pts.mean()):.1f}%")
P(f"underwater share of holding time: winners median {100 * w.frac_underwater.median():.0f}%, losers median {100 * l.frac_underwater.median():.0f}%")
hw, hl_ = w.hold_s.median() / 60, l.hold_s.median() / 60
P(f"median hold: winners {hw:.1f} min, losers {hl_:.1f} min; mean hold: winners {w.hold_s.mean() / 60:.1f}, losers {l.hold_s.mean() / 60:.1f}")

H("E. Sampling error")
e = pd.read_csv(OUT / "episodes.csv")
tr["flat_usd"] = tr.adj_pts * 0.04 * OZ
ef = tr.groupby("episode_id").flat_usd.sum()
for nm, x in (("actual USD", e.net.values), ("flat 0.04-lot USD", ef.reindex(e.episode_id).fillna(0).values)):
    bs = np.array([x[rng.integers(0, len(x), len(x))].sum() for _ in range(20000)])
    P(f"{nm}: total {x.sum():.2f} over {len(x)} episodes; episode mean {x.mean():.2f}, sd {x.std(ddof=1):.2f}, t = {x.mean() / (x.std(ddof=1) / np.sqrt(len(x))):.2f}; "
      f"bootstrap 95% CI of the total [{np.quantile(bs, .025):.0f}, {np.quantile(bs, .975):.0f}], P(total <= 0) = {100 * (bs <= 0).mean():.1f}%; "
      f"without best episode {x.sum() - x.max():.2f}, without worst {x.sum() - x.min():.2f}")
x = p.net.values
P(f"per position (treated as independent, which they are not): mean {x.mean():.2f}, sd {x.std(ddof=1):.2f}, t = {x.mean() / (x.std(ddof=1) / np.sqrt(len(x))):.2f}")
big = p[p.volume > 0.04]
P(f"lot-size effect: the {len(big)} positions above 0.04 lots net {big.net.sum():.2f} USD; the {int((p.volume <= 0.04).sum())} positions at <= 0.04 lots net {p.net[p.volume <= 0.04].sum():.2f}; "
  f"everything re-sized to 0.04 lots: {tr.flat_usd.sum():.2f} USD ({tr.adj_pts.sum():.1f} pts over {len(tr)} positions)")
dd = p.assign(day=p.close_time.dt.strftime("%m-%d")).groupby("day").net.sum()
P(f"days: {len(dd)} ({(dd > 0).sum()} up / {(dd < 0).sum()} down), day mean {dd.mean():.2f}, sd {dd.std(ddof=1):.2f}, t = {dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd))):.2f}")
P(f"minimum detectable per-position edge at n=178, sd {x.std(ddof=1):.0f} USD (80% power, 5% two-sided, iid): {2.8 * x.std(ddof=1) / np.sqrt(len(x)):.1f} USD per position vs observed {x.mean():.2f}")

(OUT / "05_edge.md").write_text("\n".join(out))
print("\n".join(out))
