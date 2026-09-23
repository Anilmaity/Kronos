import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger_verify.jsonl")
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
import numpy as np, pandas as pd
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/no-shorting-below-lows.py')
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
m1 = cl.load_m1()
ev = cl.cache_frame("noshort_15m_cisd_rung0_masks", lambda: orig.detect(m1))
print("events", len(ev), "chase_day rate", ev.chase_day.mean())

def run(tag, mask, **kw):
    r = cl.gate_test(ev, mask, mask_available_at="decision_time", max_hold="150min", claim="-", keep_trades=True, **kw)
    h = r.get("halves", {})
    b = r.get("blocks", {})
    print(f"{tag:40s} n={r['n']:5d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']} "
          f"H1={h.get('H1',{}).get('diff',np.nan):+.3f} H2={h.get('H2',{}).get('diff',np.nan):+.3f} "
          f"B=" + ",".join(f"{b[k]['diff']:+.3f}" for k in sorted(b)))
    return r

r0 = run("original chase_day", "chase_day")
tr = r0.get("trades")
print(type(tr), None if tr is None else tr.columns.tolist()[:40])

tr = r0["_trades"].copy()
tr["adj"] = tr["net_R"] - tr["ctrl_mean_R"]
tr["adj5"] = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]
g = tr["gate"].to_numpy(bool)
ok = np.isfinite(tr["adj"])
print("50/50 rescore diff:", tr.adj5[g & ok].mean() - tr.adj5[~g & ok].mean())
yr = pd.DatetimeIndex(tr.decision_time).year
per = pd.DataFrame({"y": yr, "g": g, "a": tr.adj}).groupby(["y", "g"]).a.mean().unstack()
per["diff"] = per[True] - per[False]
per["n_g"] = pd.Series(g).groupby(yr).sum().values
print(per.round(3))
# leave-one-year-out
for y in sorted(set(yr)):
    k = (yr != y) & ok
    print("drop", y, round(tr.adj[g & k].mean() - tr.adj[~g & k].mean(), 4))
# direction split
d = tr["direction"].to_numpy()
for s in (1, -1):
    k = (d == s) & ok
    print("dir", s, "n_g", int((g & k).sum()), "diff", round(tr.adj[g & k].mean() - tr.adj[~g & k].mean(), 4))
# hours into NY trading day
ny = pd.DatetimeIndex(ev.decision_time).tz_convert("America/New_York")
hid = ((ny.hour - 18) % 24) + ny.minute / 60
ev["hid"] = hid
print("gate rate by hours-into-day bucket:")
print(pd.Series(ev.chase_day.values).groupby(pd.cut(hid, [0, 2, 4, 8, 12, 16, 23.1])).agg(["mean", "size"]))

# ToD-held control
run("orig + ctrl_tod_tol_min=30", "chase_day", ctrl_tod_tol_min=30)

base = ev.copy()
def sub(tag, keep, mask="chase_day", **kw):
    global ev
    ev_s = base[keep].reset_index(drop=True)
    r = cl.gate_test(ev_s, mask, mask_available_at="decision_time", max_hold="150min", claim="-", **kw)
    h = r.get("halves", {}); b = r.get("blocks", {})
    print(f"{tag:40s} n={r['n']:5d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']} "
          f"H1={h.get('H1',{}).get('diff',np.nan):+.3f} H2={h.get('H2',{}).get('diff',np.nan):+.3f} B=" + ",".join(f"{b[k]['diff']:+.3f}" for k in sorted(b)))
    return r
sub("shorts only", base.direction.values == -1)
sub("longs only", base.direction.values == 1)
sub("day >=2h old", base.hid.values >= 2)
sub("day >=4h old", base.hid.values >= 4)
sub("day >=8h old (late)", base.hid.values >= 8)
# range-spent clause: running range before bar vs median prior 20 full-day ranges
bo = pd.DatetimeIndex(base.decision_time) - pd.Timedelta("15min")
rh = cl.running_hilo(bo, "1D", m1=m1)
rng = (rh["high"] - rh["low"]).to_numpy(float)
D = cl.bars("1D")
dr = (D["high"] - D["low"]).rolling(20).median().shift(0)
ct = pd.DatetimeIndex(D["close_time"]).tz_convert("UTC")
pos = np.searchsorted(ct.asi8, pd.DatetimeIndex(base.decision_time).tz_convert("UTC").asi8, side="right") - 1
adr = np.where(pos >= 0, dr.to_numpy()[np.clip(pos, 0, None)], np.nan)
spent = rng / adr
base["spent"] = np.nan_to_num(spent, nan=0.0)
print("spent quantiles among gated", np.nanpercentile(spent[base.chase_day.values], [25, 50, 75]))
base["chase_spent"] = base.chase_day.values & (base.spent.values >= 0.5)
base["chase_spent75"] = base.chase_day.values & (base.spent.values >= 0.75)
ev = base
run("chase & range spent>=50% ADR", "chase_spent")
run("chase & range spent>=75% ADR", "chase_spent75")
base["chase_both"] = base.chase_day.values & base.chase_pd.values
ev = base
run("chase_day & beyond PD extreme", "chase_both")
