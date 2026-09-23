"""Harness re-runs: tie 50/50, realistic XAUUSD spread (price-unit cost), ToD control,
calendar blocks, halves, per-year, absolute gated-book economics."""
from common import *

ev, an = load_events()


def run(name, mask="poi_a", **kw):
    r = cl.gate_test(ev, mask, mask_available_at="decision_time", max_hold="10h", keep_trades=True, **kw)
    bl = {k: round(v["diff"], 3) for k, v in r["blocks"].items()}
    tr = r["_trades"]; g = tr[tr.gate]
    print(f"{name:26s} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.4f} "
          f"H1={r['halves']['H1']['diff']:+.3f} H2={r['halves']['H2']['diff']:+.3f} blocks={bl} {r['verdict']}")
    print(f"{'':26s} gated net avgR={g.net_R.mean():+.4f} gross={g.gross_R.mean():+.4f} "
          f"gated-vs-ownctrl={r['gated_vs_own_control']['diff']:+.4f} "
          f"[{r['gated_vs_own_control']['ci_lo']:+.4f},{r['gated_vs_own_control']['ci_hi']:+.4f}] "
          f"compl-vs-ownctrl={r['complement']['vs_own_control']['diff']:+.4f} "
          f"ties5050 diff={r['ties'].get('diff_5050')} v5050={r['ties'].get('verdict_5050')}")
    return r


r0 = run("primary (0.04R)")
tr = r0["_trades"]
print("\nrisk ($) quantiles:", tr.risk.quantile([.1, .25, .5, .75, .9]).round(2).to_dict())
for c in (0.25, 0.30, 0.35):
    print(f"spread {c}: mean cost in R = {(c / tr.risk).mean():.4f}  median = {(c / tr.risk).median():.4f}")
for c in (0.25, 0.30, 0.35):
    run(f"cost {c} pt", cost=c)
run("cost 0.30 pt, ToD ctrl", cost=0.30, ctrl_tod_tol_min=30)
run("cost 0.30 pt, bars hold", cost=0.30, hold_basis="bars")

# absolute economics of the gated book, net of realistic spread, with day-block CIs
tr = tr.copy(); tr["day"] = cl.trading_day(tr.decision_time)
g = tr[tr.gate]; c = tr[~tr.gate]
print("\nAbsolute book economics (gated arm), day-block CI:")
for cost in (0.0, 0.25, 0.30, 0.35):
    net = g.gross_R - cost / g.risk
    m, lo, hi, n = day_boot_ci(net, g.day)
    print(f"  cost {cost:.2f} pt: gated avg net R {m:+.4f} [{lo:+.4f},{hi:+.4f}] n={n}   "
          f"win={((net > 0).mean()):.3f}")
    netc = c.gross_R - cost / c.risk
    print(f"               complement avg net R {netc.mean():+.4f}  all-events {(tr.gross_R - cost / tr.risk).mean():+.4f}")

# per-year
tr["yr"] = tr.decision_time.dt.year
tr["adj"] = tr.net_R - tr.ctrl_mean_R
py = tr.groupby("yr").apply(lambda d: pd.Series({
    "n_g": d.gate.sum(), "n_c": (~d.gate).sum(),
    "g_adj": d[d.gate].adj.mean(), "c_adj": d[~d.gate].adj.mean(),
    "diff": d[d.gate].adj.mean() - d[~d.gate].adj.mean(),
    "g_gross": d[d.gate].gross_R.mean()})).round(3)
print("\nper-year:\n", py)
# stop-size terciles (cost realism depends on risk)
tr["rq"] = pd.qcut(tr.risk, 3, labels=["small", "mid", "large"])
print("\nby stop-size tercile (gross R, gated vs complement, adj diff):")
print(tr.groupby("rq").apply(lambda d: pd.Series({
    "n": len(d), "g_gross": d[d.gate].gross_R.mean(), "c_gross": d[~d.gate].gross_R.mean(),
    "diff_adj": d[d.gate].adj.mean() - d[~d.gate].adj.mean(),
    "cost0.30R": (0.30 / d.risk).mean()})).round(3))
tr.to_pickle(DD + "/trades_primary.pkl")
