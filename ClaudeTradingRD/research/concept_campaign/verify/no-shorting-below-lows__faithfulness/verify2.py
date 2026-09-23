import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger_verify.jsonl")
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
import numpy as np, pandas as pd
import concept_lab as cl
spec = importlib.util.spec_from_file_location("orig", '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/no-shorting-below-lows.py')
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
m1 = cl.load_m1()
base = cl.cache_frame("noshort_15m_cisd_rung0_masks", lambda: orig.detect(m1))
ny = pd.DatetimeIndex(base.decision_time).tz_convert("America/New_York")
base["hid"] = ((ny.hour - 18) % 24) + ny.minute / 60
def sub(tag, keep, mask="chase_day", **kw):
    ev_s = base[keep].reset_index(drop=True)
    r = cl.gate_test(ev_s, mask, mask_available_at="decision_time", max_hold="150min", claim="-", **kw)
    h = r.get("halves", {}); b = r.get("blocks", {})
    print(f"{tag:40s} n={r['n']:5d} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']} "
          f"H1={h.get('H1',{}).get('diff',np.nan):+.3f} H2={h.get('H2',{}).get('diff',np.nan):+.3f} B=" + ",".join(f"{b[k]['diff']:+.3f}" for k in sorted(b)) + f" ovl={r.get('ctrl_overlap')}")
    return r
S = base.direction.values == -1
L = base.direction.values == 1
sub("shorts only, tod30", S, ctrl_tod_tol_min=30)
sub("longs only, tod30", L, ctrl_tod_tol_min=30)
sub("both, day>=2h, tod30", base.hid.values >= 2, ctrl_tod_tol_min=30)
sub("shorts, day>=4h", S & (base.hid.values >= 4))
sub("shorts, day>=8h", S & (base.hid.values >= 8))
sub("shorts, day>=4h tod30", S & (base.hid.values >= 4), ctrl_tod_tol_min=30)
sub("both, ctrl_grid=m1", np.ones(len(base), bool), ctrl_grid="m1")
