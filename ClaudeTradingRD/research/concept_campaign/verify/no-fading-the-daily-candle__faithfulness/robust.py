"""Faithfulness/robustness probe of no-fading-the-daily-candle reading a (scratch, not written)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cisd_book, cl, developing_day, np, pd

m1 = cl.load_m1()

def build(tf):
    ev = cisd_book(m1, tf).drop(columns=["extreme_time", "extreme_price"])
    dd = developing_day(m1, ev["decision_time"])
    sgn = np.sign(dd["d_close"].to_numpy() - dd["d_open"].to_numpy())
    d = ev["direction"].to_numpy()
    ev["gate_a"] = (sgn == d) & ~np.isnan(sgn)
    ev["opp"] = (sgn == -d) & ~np.isnan(sgn)
    mo = cl.open_at(ev["decision_time"], "00:00", m1=m1)
    msg = np.sign(dd["d_close"].to_numpy() - mo.iloc[:, 0].to_numpy())
    ev["gate_mid"] = (msg == d) & ~np.isnan(msg)
    ev["mid_avail"] = ~np.isnan(msg)
    # elapsed minutes of trading day (18:00 NY start)
    ny = cl.to_ny(ev["decision_time"])
    mod = ny.hour * 60 + ny.minute
    ev["elapsed"] = (mod - 18 * 60) % 1440
    ev["body_atr"] = np.abs(dd["d_close"].to_numpy() - dd["d_open"].to_numpy())
    return ev

def show(tag, res):
    b = res.get("blocks") or {}
    print(f"{tag:42s} n={res['n']:6d} diff={res['diff']:+.4f} [{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] p={res['p']:.3f} "
          f"{res['verdict']:12s} H1={res['halves']['H1']['diff']:+.3f} H2={res['halves']['H2']['diff']:+.3f} "
          f"blocks={[round(v.get('diff',float('nan')),3) for v in b.values()]} ovl={res.get('ctrl_overlap'):.3f}", flush=True)

def gt(ev, col, **kw):
    return cl.gate_test(ev.reset_index(drop=True), col, mask_available_at="decision_time", max_hold=kw.pop("max_hold", "150min"), **kw)

ev15 = build("15min")
show("15m reading a reproduce", gt(ev15, "gate_a"))
show("15m a, ctrl_tod_tol_min=30", gt(ev15, "gate_a", ctrl_tod_tol_min=30))
show("15m a, hold_basis=bars", gt(ev15, "gate_a", hold_basis="bars"))
nd = ev15[ev15.gate_a | ev15.opp]
show("15m a, dojis dropped (aligned vs opposed)", gt(nd, "gate_a"))
show("15m midnight open (all rows)", gt(ev15, "gate_mid"))
mv = ev15[ev15.mid_avail]
show("15m midnight open (post-midnight rows)", gt(mv, "gate_mid"))
show("15m 18:00 open, post-midnight rows", gt(mv, "gate_a"))
for lo, hi, nm in [(0, 360, "18-24 NY (Asia)"), (360, 840, "00-08 NY (London)"), (840, 1380, "08-17 NY (NY)")]:
    s = ev15[(ev15.elapsed >= lo) & (ev15.elapsed < hi)]
    show(f"15m a, {nm}", gt(s, "gate_a"))
# leave-one-block-out style: exclude B4 span
s = ev15[ev15.decision_time < pd.Timestamp("2023-12-02", tz="UTC")]
show("15m a, excl. B4 (to 2023-12-01)", gt(s, "gate_a"))
ev5 = build("5min")
show("5m reading a (max_hold 50min)", gt(ev5, "gate_a", max_hold="50min"))
show("5m reading a (max_hold 150min)", gt(ev5, "gate_a", max_hold="150min"))
