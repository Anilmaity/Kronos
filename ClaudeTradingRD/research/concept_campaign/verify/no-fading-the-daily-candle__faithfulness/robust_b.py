"""Faithfulness/robustness probe of no-fading-the-daily-candle reading b (scratch, not written)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cisd_book, cl, developing_day, np, pd

m1 = cl.load_m1()

def build(tf, day_open="18"):
    ev = cisd_book(m1, tf).drop(columns=["extreme_time", "extreme_price"])
    dd = developing_day(m1, ev["decision_time"])
    o, h, l, c = (dd[k].to_numpy() for k in ("d_open", "d_high", "d_low", "d_close"))
    d = ev["direction"].to_numpy()
    sgn = np.sign(c - o)
    ev["aligned"] = (sgn == d) & ~np.isnan(sgn)
    ev["opp"] = (sgn == -d) & ~np.isnan(sgn)
    body = np.abs(c - o)
    opp = np.where(d > 0, o - l, h - o)
    with np.errstate(invalid="ignore", divide="ignore"):
        ev["ratio"] = np.where(body > 0, opp / body, np.inf)
    ev["ratio"] = ev["ratio"].fillna(np.inf)
    for cut in (0.6, 0.8, 1.0, 1.2, 1.6):
        ev[f"gb_{cut}"] = ev["aligned"] & (ev["ratio"] <= cut)
    ny = cl.to_ny(ev["decision_time"])
    ev["elapsed"] = ((ny.hour * 60 + ny.minute) - 18 * 60) % 1440
    return ev

def show(tag, res):
    b = res.get("blocks") or {}
    t = res.get("ties") or {}
    print(f"{tag:46s} n={res['n']:6d} ng={res.get('n_gated')} diff={res['diff']:+.4f} [{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] p={res['p']:.3f} "
          f"{res['verdict']:12s} H1={res['halves']['H1']['diff']:+.3f} H2={res['halves']['H2']['diff']:+.3f} "
          f"blocks={[round(v['diff'],3) for v in b.values()]} ovl={res.get('ctrl_overlap'):.3f} "
          f"gex={t.get('gated_excess')} cex={t.get('complement_excess')}", flush=True)
    return res

def gt(ev, col, **kw):
    return cl.gate_test(ev.reset_index(drop=True), col, mask_available_at="decision_time",
                        max_hold=kw.pop("max_hold", "150min"), **kw)

ev = build("15min")
r = show("15m b reproduce (cut 1.0)", gt(ev, "gb_1.0", keep_trades=True))
tr = r.get("_trades")
if tr is not None:
    print(tr.columns.tolist())
for cut in (0.6, 0.8, 1.2, 1.6):
    show(f"15m b cut {cut}", gt(ev, f"gb_{cut}"))
al = ev[ev.aligned]
show("within aligned: small wick vs large wick", gt(al, "gb_1.0"))
nb = ev[ev["gb_1.0"] | ev.opp]
show("b vs opposed only (aligned-large dropped)", gt(nb, "gb_1.0"))
show("15m b, ctrl_tod_tol_min=30", gt(ev, "gb_1.0", ctrl_tod_tol_min=30))
show("15m b, hold_basis=bars", gt(ev, "gb_1.0", hold_basis="bars"))
for lo, hi, nm in [(0, 360, "18-24 NY (Asia)"), (360, 840, "00-08 NY (London)"), (840, 1380, "08-17 NY (NY)")]:
    s = ev[(ev.elapsed >= lo) & (ev.elapsed < hi)]
    show(f"15m b, {nm}", gt(s, "gb_1.0"))
s = ev[ev.decision_time < pd.Timestamp("2023-12-02", tz="UTC")]
show("15m b, excl. B4", gt(s, "gb_1.0"))
s = ev[ev.decision_time >= pd.Timestamp("2018-08-22", tz="UTC")]
show("15m b, excl. B1", gt(s, "gb_1.0"))
for y in range(2016, 2027):
    s = ev[ev.decision_time.dt.year == y]
    rr = gt(s, "gb_1.0", n_boot=500)
    print(f"  year {y}: n={rr['n']} diff={rr['diff']:+.4f} p={rr['p']:.3f}", flush=True)
ev5 = build("5min")
show("5m b (max_hold 50min)", gt(ev5, "gb_1.0", max_hold="50min"))
show("5m b (max_hold 150min)", gt(ev5, "gb_1.0", max_hold="150min"))
