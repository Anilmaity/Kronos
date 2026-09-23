"""Faithfulness/robustness verification of trend-entry-options EDGE (scratch, not written)."""
import sys, importlib.util
import numpy as np, pandas as pd
D = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b"
sys.path.insert(0, D)
spec = importlib.util.spec_from_file_location("teo", D + "/trend-entry-options.py")
teo = importlib.util.module_from_spec(spec); spec.loader.exec_module(teo)
import _batch_common as bc
from _batch_common import cl

m1 = cl.load_m1()
real = teo.detect(m1)
print("real n", len(real), real.option.value_counts().to_dict())

b = bc.bars(m1)
is_sh, is_sl = bc.swing_arrays(b)
legs = bc.displacement_legs(b, is_sh, is_sl)
tdir, tfire, _ = bc.trend_state(b, legs)
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
rng = (h - l)
atr = pd.Series(rng).rolling(96, min_periods=20).mean().to_numpy()

def mk(idx, d, stop):
    ev = pd.DataFrame({"decision_time": ct[idx], "available_at": ct[idx], "direction": d.astype(int),
                       "stop_px": stop, "rr": 2.0, "sa": (np.abs(c[idx]-stop)/atr[idx])})
    ev = ev.dropna(subset=["sa"])
    return bc.finish(ev)

# B) counter-trend mirror: first WITH-trend candle per episode, fade it (against trend), stop at its close-side extreme
withc = ((tdir == -1) & (c < o)) | ((tdir == 1) & (c > o))
j = np.flatnonzero(withc)
df = pd.DataFrame({"j": j, "ep": tfire[j], "d": tdir[j]}).drop_duplicates(["ep", "d"], keep="first")
jj = df.j.to_numpy(); d = -df.d.to_numpy()
counter = mk(jj, d, np.where(d == -1, h[jj], l[jj]))
# C) fade EVERY 15m candle, no trend: direction = -candle colour, stop at its close-side extreme
jj = np.flatnonzero(c != o); d = np.where(c[jj] > o[jj], -1, 1)
fade_all = mk(jj, d, np.where(d == -1, h[jj], l[jj]))
# D) fade every candle, but only on bars with NO trend in force
jn = jj[tdir[jj] == 0]; dn = np.where(c[jn] > o[jn], -1, 1)
fade_notrend = mk(jn, dn, np.where(dn == -1, h[jn], l[jn]))
# E) first opposing candle per episode (= real minus inducement), recomputed here for stratification
real2 = real.copy(); idx = np.searchsorted(ct, real2.decision_time) ; 

out = {}
for name, ev in [("real", real), ("counter_trend_mirror", counter), ("fade_all", fade_all), ("fade_notrend", fade_notrend)]:
    ev = ev[["decision_time","available_at","direction","stop_px","rr"] + (["sa"] if "sa" in ev else [])]
    r = cl.trade_test(ev.drop(columns=["sa"], errors="ignore"), max_hold="150min", n_boot=500, keep_trades=True)
    print(f"\n== {name}: n={r['n']} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] {r['verdict']}  H1 {r['halves']['H1']['diff']:+.3f} H2 {r['halves']['H2']['diff']:+.3f}")
    print("  blocks", {k: round(v['diff'],3) for k,v in r['blocks'].items()}, "ties", {k: (round(v,3) if isinstance(v,float) else v) for k,v in r['ties'].items()}, "ovl", round(r['ctrl_overlap'],3))
    out[name] = (ev, r)
    t = r.get("_trades")
    if t is not None and name == "real": print("  trades cols", list(t.columns)[:40])
import pickle; pickle.dump({k:(v[0], v[1].get('_trades')) for k,v in out.items()}, open(__file__.replace('.py','.pkl'),'wb'))
