"""s5x_stress_spread_regime_maker.py — ADVERSARIAL STRESS (cost & parameter)

Target config (family spread_regime_maker):
  k3_z3.0_tp1.5_sl1.5_maker_low
  {k_min:3, z_thr:3.0, tp:1.5, sl:1.5, gate:low_spread_q30_roll1h,
   maker_offset:0.15, maker_ttl_bars:36, maker_exit:True, max_hold_bars:360, lot:0.1}

Mechanism copied verbatim from s5x_spread_regime_maker.py (not edited there).
Stresses:
  (a) commission x2  = $9.80/lot RT
  (b) sl_slippage_pts = 0.15
  (c) spread_model = 0.30
  (d) spread_model = 'feed'   (labeled worst-case)
  (e) 8 parameter neighbors at +-20-30% on z_thr, tp/sl, maker_offset, ttl

PASS criterion: test expectancy > 0 under (a)-(c) and in the majority of neighbors.
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Projects\ClaudeProjects\ClaudeTradingBot")
import s5_engine as eng

T0 = time.time()
BARS_PER_MIN = 12
ROLL_W = 720
GATE_Q_LO = 0.30
LOT = 0.10

# baseline candidate params
P0 = dict(k=3, zt=3.0, tp=1.5, sl=1.5, maker_off=0.15, ttl=36, max_hold=360)

df = eng.load_s5()
n = len(df)
mid = df["mid_c"].values
spr = (df["ask_c"] - df["bid_c"]).values
spr_s = pd.Series(spr)
mid_s = pd.Series(mid)
print(f"[{time.time()-T0:5.1f}s] loaded {n} bars")

# ── causal gate: real feed spread <= rolling-1h q30 (identical to family) ──
q_lo = spr_s.rolling(ROLL_W, min_periods=ROLL_W // 2).quantile(GATE_Q_LO).values
gate_low = spr <= q_lo
gate_low[np.isnan(q_lo)] = False

# ── causal z-score for k=3 min (identical to family) ──
_zcache: dict = {}
def zscore(k: int) -> np.ndarray:
    if k not in _zcache:
        ret = mid_s.diff(k * BARS_PER_MIN)
        m = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).mean()
        sd = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).std()
        _zcache[k] = ((ret - m) / sd).values
    return _zcache[k]

def signal_indices(k: int, zt: float):
    z = zscore(k)
    zp = np.roll(z, 1); zp[0] = 0.0
    sell = (z > zt) & (zp <= zt)
    buy = (z < -zt) & (zp >= -zt)
    sell[np.isnan(z)] = False; buy[np.isnan(z)] = False
    return np.where(sell)[0], np.where(buy)[0]

def build_intents(k, zt, tp_pts, sl_pts, maker_off, ttl, max_hold, tag):
    sell_i, buy_i = signal_indices(k, zt)
    intents = []
    for side, idxs in (("sell", sell_i), ("buy", buy_i)):
        idxs = idxs[gate_low[idxs]]
        idxs = idxs[(idxs > ROLL_W) & (idxs < n - max_hold - 2)]
        for i in idxs:
            base = mid[i]
            lp = base + maker_off if side == "sell" else base - maker_off
            tp = lp - tp_pts if side == "sell" else lp + tp_pts
            sl = lp + sl_pts if side == "sell" else lp - sl_pts
            intents.append(eng.OrderIntent(
                signal_i=int(i), side=side, tp=tp, sl=sl,
                max_hold_bars=max_hold, lot=LOT, entry_type="maker",
                limit_price=lp, maker_exit=True, entry_ttl_bars=ttl, tag=tag))
    return intents

def run(tag, k=None, zt=None, tp=None, sl=None, maker_off=None, ttl=None,
        max_hold=None, commission=eng.COMMISSION_PER_LOT_RT,
        sl_slip=0.05, spread_model=0.20):
    p = dict(P0)
    for name, v in (("k", k), ("zt", zt), ("tp", tp), ("sl", sl),
                    ("maker_off", maker_off), ("ttl", ttl), ("max_hold", max_hold)):
        if v is not None:
            p[name] = v
    intents = build_intents(p["k"], p["zt"], p["tp"], p["sl"],
                            p["maker_off"], p["ttl"], p["max_hold"], tag)
    fills = eng.simulate(df, intents, commission_per_lot_rt=commission,
                         sl_slippage_pts=sl_slip, spread_model=spread_model)
    s = eng.stats(df, fills, tag)
    s["params"] = p
    s["costs"] = {"commission": commission, "sl_slip": sl_slip, "spread_model": spread_model}
    s["n_intents"] = len(intents); s["n_fills"] = len(fills)
    te = s.get("test_may_jul", {})
    tr = s.get("train_jan_apr", {})
    print(f"[{time.time()-T0:5.1f}s] {tag:34s} "
          f"train n={tr.get('trades',0):4} exp={tr.get('expectancy')} net={tr.get('net')} | "
          f"TEST n={te.get('trades',0):4} wr={te.get('win_rate')} "
          f"exp={te.get('expectancy')} net={te.get('net')} pf={te.get('pf')}")
    return s

results = {}

# 0. baseline reproduction (claimed: test n=391 wr=54.5 net=244.41 exp=0.625 pf=1.086)
results["baseline"] = run("baseline")

# (a) commission x2
results["a_comm_x2"] = run("a_comm_x2_9.80", commission=9.80)

# (b) sl slippage 0.15
results["b_slip_0.15"] = run("b_sl_slip_0.15", sl_slip=0.15)

# (c) spread 0.30
results["c_spread_0.30"] = run("c_spread_0.30", spread_model=0.30)

# (d) feed spread — labeled worst-case
results["d_feed_worstcase"] = run("d_feed_WORSTCASE", spread_model="feed")

# (e) neighbors: +-20-30% on z_thr, tp/sl, maker_offset, ttl (base costs)
neighbors = {
    "n1_z2.4":      dict(zt=2.4),
    "n2_z3.6":      dict(zt=3.6),
    "n3_tpsl1.2":   dict(tp=1.2, sl=1.2),
    "n4_tpsl1.8":   dict(tp=1.8, sl=1.8),
    "n5_off0.11":   dict(maker_off=0.11),
    "n6_off0.19":   dict(maker_off=0.19),
    "n7_ttl26":     dict(ttl=26),
    "n8_ttl47":     dict(ttl=47),
}
for tag, kw in neighbors.items():
    results[tag] = run(tag, **kw)

# ── verdict math ──
def texp(key):
    b = results[key].get("test_may_jul", {})
    return b.get("expectancy") if b.get("trades", 0) > 0 else None

abc_ok = all((texp(k) or -1) > 0 for k in ("a_comm_x2", "b_slip_0.15", "c_spread_0.30"))
nb_exps = [texp(k) for k in neighbors]
nb_pos = sum(1 for e in nb_exps if e is not None and e > 0)
plateau = nb_pos > len(neighbors) / 2
verdict = "pass" if (abc_ok and plateau) else "fail"

summary = {
    "candidate": "spread_regime_maker/k3_z3.0_tp1.5_sl1.5_maker_low",
    "lens": "cost_parameter_stress",
    "baseline_test": results["baseline"]["test_may_jul"],
    "stress_test_expectancy": {k: texp(k) for k in results},
    "abc_all_positive": abc_ok,
    "neighbors_positive": f"{nb_pos}/{len(neighbors)}",
    "verdict": verdict,
}
print("\nSUMMARY:", summary["stress_test_expectancy"])
print(f"abc_ok={abc_ok} neighbors_pos={nb_pos}/{len(neighbors)} -> {verdict}")

payload = {"summary": summary, "results": results}
path = eng.save_result("stress_spread_regime_maker", payload)
print(f"[{time.time()-T0:5.1f}s] saved -> {path}")
