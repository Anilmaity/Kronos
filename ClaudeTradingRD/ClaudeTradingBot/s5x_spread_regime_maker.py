"""s5x_spread_regime_maker.py — FAMILY: spread_regime_maker

Microstructure family, only possible with real bid/ask:
  Step 1: profile the REAL feed spread by UTC hour + its dynamics (bursts/news).
  Step 2: maker-fade gated on LOW real feed spread (cheap, calm book) AND a
          short-horizon reversion z-score; compare the IDENTICAL signal taker.
  Step 3: invert the gate (wide-spread-only) on the best configs to show
          the effect direction.

Costs: fills at spread_model=0.20 (deployment venue) for comparability, but the
GATE reads the REAL feed spread columns (that is the information being tested).
Best config also run at spread_model='feed' as worst-case robustness.

Method rules honoured: signal on close of bar i, execution from i+1 (engine);
all rolling features causal (rolling windows end at bar i); hard SL on every
trade; TRAIN-only selection; test read once for top<=3.
"""
from __future__ import annotations

import itertools
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Projects\ClaudeProjects\ClaudeTradingBot")
import s5_engine as eng

T0 = time.time()
BARS_PER_MIN = 12
MAX_HOLD = 360          # 30 min
MAKER_OFF = 0.15        # limit improvement vs signal-bar mid close
MAKER_TTL = 36          # 3 min unfilled -> cancel
LOT = 0.10
ROLL_W = 720            # 1h rolling window for z-score + spread percentile
GATE_Q_LO, GATE_Q_HI = 0.30, 0.70

df = eng.load_s5()
n = len(df)
mid = df["mid_c"].values
t_hr = df["time"].dt.hour.values
spr = (df["ask_c"] - df["bid_c"]).values          # REAL feed spread (gate input)
spr_s = pd.Series(spr)
print(f"[{time.time()-T0:5.1f}s] loaded {n} bars")

# ───────────────────────── Step 1: spread profile ─────────────────────────
hour_tab = (pd.DataFrame({"hr": t_hr, "spr": spr})
            .groupby("hr")["spr"]
            .agg(median="median", p90=lambda s: s.quantile(0.90), mean="mean", bars="count"))
hour_profile = {int(h): {"median": round(r["median"], 3), "p90": round(r["p90"], 3),
                         "mean": round(r["mean"], 3), "bars": int(r["bars"])}
                for h, r in hour_tab.iterrows()}

mv1 = pd.Series(mid).diff(BARS_PER_MIN).abs()
burst_thr = float(mv1.quantile(0.99))
burst_idx = np.where(mv1.values >= burst_thr)[0]
burst_dyn = {}
for lag_min in [0, 1, 2, 5, 10]:
    j = burst_idx + lag_min * BARS_PER_MIN
    j = j[j < n]
    burst_dyn[f"+{lag_min}min"] = round(float(np.nanmean(spr[j])), 3)
spread_profile = {
    "by_utc_hour": hour_profile,
    "baseline_mean": round(float(np.nanmean(spr)), 3),
    "burst_threshold_pts_1min_p99": round(burst_thr, 3),
    "n_burst_bars": int(len(burst_idx)),
    "spread_after_burst": burst_dyn,
    "notes": ("Feed spread tightest 07-16 UTC (median ~0.71-0.77), widest at the "
              "21-23 UTC rollover (~0.94-1.02) and 00-01. Spread does NOT tighten "
              "after bursts — it more than doubles on a p99 1-min move (1.81 vs "
              "0.84 baseline) and decays slowly (still ~1.67 at +10min). Wide "
              "spread == volatile/news moments; low spread == calm book."),
}
print(f"[{time.time()-T0:5.1f}s] spread profile done")

# ───────────────── causal features: gate + reversion z-scores ─────────────
q_lo = spr_s.rolling(ROLL_W, min_periods=ROLL_W // 2).quantile(GATE_Q_LO).values
q_hi = spr_s.rolling(ROLL_W, min_periods=ROLL_W // 2).quantile(GATE_Q_HI).values
gate_low = spr <= q_lo          # calm, cheap book (NaN q -> False)
gate_high = spr >= q_hi         # wide, stressed book
gate_none = np.ones(n, bool)
gate_low[np.isnan(q_lo)] = False
gate_high[np.isnan(q_hi)] = False

zmap = {}
mid_s = pd.Series(mid)
for k in (1, 3, 5):
    ret = mid_s.diff(k * BARS_PER_MIN)
    m = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).mean()
    sd = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).std()
    zmap[k] = ((ret - m) / sd).values
print(f"[{time.time()-T0:5.1f}s] features done (gate_low frac={gate_low.mean():.3f})")


def signal_indices(k: int, zt: float):
    """First bar where |z| crosses the threshold (causal, close of bar i)."""
    z = zmap[k]
    zp = np.roll(z, 1); zp[0] = 0.0
    sell = (z > zt) & (zp <= zt)          # spike up -> fade short
    buy = (z < -zt) & (zp >= -zt)         # spike down -> fade long
    sell[np.isnan(z)] = False; buy[np.isnan(z)] = False
    return np.where(sell)[0], np.where(buy)[0]


def build_intents(k, zt, tp_pts, sl_pts, exec_mode, gate_mask, tag):
    sell_i, buy_i = signal_indices(k, zt)
    intents = []
    for side, idxs in (("sell", sell_i), ("buy", buy_i)):
        idxs = idxs[gate_mask[idxs]]
        idxs = idxs[(idxs > ROLL_W) & (idxs < len(df) - MAX_HOLD - 2)]
        for i in idxs:
            base = mid[i]
            if exec_mode == "maker":
                lp = base + MAKER_OFF if side == "sell" else base - MAKER_OFF
                tp = lp - tp_pts if side == "sell" else lp + tp_pts
                sl = lp + sl_pts if side == "sell" else lp - sl_pts
                intents.append(eng.OrderIntent(
                    signal_i=int(i), side=side, tp=tp, sl=sl,
                    max_hold_bars=MAX_HOLD, lot=LOT, entry_type="maker",
                    limit_price=lp, maker_exit=True, entry_ttl_bars=MAKER_TTL, tag=tag))
            else:
                tp = base - tp_pts if side == "sell" else base + tp_pts
                sl = base + sl_pts if side == "sell" else base - sl_pts
                intents.append(eng.OrderIntent(
                    signal_i=int(i), side=side, tp=tp, sl=sl,
                    max_hold_bars=MAX_HOLD, lot=LOT, entry_type="taker", tag=tag))
    return intents


def run(k, zt, tp, sl, exec_mode, gate_name, spread_model=0.20):
    gm = {"low": gate_low, "none": gate_none, "high": gate_high}[gate_name]
    tag = f"k{k}_z{zt}_tp{tp}_sl{sl}_{exec_mode}_{gate_name}"
    intents = build_intents(k, zt, tp, sl, exec_mode, gm, tag)
    fills = eng.simulate(df, intents, spread_model=spread_model)
    s = eng.stats(df, fills, tag)
    s["n_intents"] = len(intents)
    s["n_fills"] = len(fills)
    return s


def row(params, s):
    def blk(b):
        if not b or b.get("trades", 0) == 0:
            return {"trades": 0, "win_rate": None, "net": None, "expectancy": None, "pf": None}
        return {kk: b.get(kk) for kk in ("trades", "win_rate", "net", "expectancy", "pf")}
    return {**params, "n_intents": s["n_intents"], "n_fills": s["n_fills"],
            "train": blk(s.get("train_jan_apr", {})), "test": blk(s.get("test_may_jul", {})),
            "full_net": (s.get("full") or {}).get("net")}

# ───────────────────────── Step 2 sweep (gate=low) ────────────────────────
KS = (1, 3, 5)
ZTS = (2.0, 3.0)
TPSL = ((1.0, 1.0), (1.5, 1.5), (0.8, 1.6))
EXECS = ("maker", "taker")

sweep = []
full_stats = {}
for k, zt, (tp, sl), ex in itertools.product(KS, ZTS, TPSL, EXECS):
    params = {"k_min": k, "z_thr": zt, "tp": tp, "sl": sl, "exec": ex, "gate": "low"}
    s = run(k, zt, tp, sl, ex, "low")
    sweep.append(row(params, s))
    full_stats[s["label"]] = s
    tr = sweep[-1]["train"]
    print(f"[{time.time()-T0:5.1f}s] {s['label']:38s} train: n={tr['trades']:4} "
          f"wr={tr['win_rate']} exp={tr['expectancy']} net={tr['net']}")

# ─────────────── selection: top<=3 by TRAIN expectancy (n>=100) ───────────
cand = [r for r in sweep if r["train"]["trades"] >= 100 and r["train"]["expectancy"] is not None]
min_n = 100
if not cand:
    cand = [r for r in sweep if r["train"]["trades"] >= 40]
    min_n = 40
cand.sort(key=lambda r: r["train"]["expectancy"], reverse=True)
top3 = cand[:3]
print(f"\n[{time.time()-T0:5.1f}s] TOP-3 by train expectancy (min {min_n} train trades):")
for r in top3:
    print(f"  {r['k_min']}m z{r['z_thr']} tp{r['tp']}/sl{r['sl']} {r['exec']}  "
          f"train exp={r['train']['expectancy']} | TEST n={r['test']['trades']} "
          f"wr={r['test']['win_rate']} exp={r['test']['expectancy']} net={r['test']['net']}")

# ───────── Step 3 diagnostics on top-3: gate inversion + no gate ──────────
diagnostics = []
for r in top3:
    for g in ("none", "high"):
        params = {"k_min": r["k_min"], "z_thr": r["z_thr"], "tp": r["tp"], "sl": r["sl"],
                  "exec": r["exec"], "gate": g}
        s = run(r["k_min"], r["z_thr"], r["tp"], r["sl"], r["exec"], g)
        diagnostics.append(row(params, s))
        full_stats[s["label"]] = s
        tr = diagnostics[-1]["train"]
        print(f"[{time.time()-T0:5.1f}s] DIAG {s['label']:38s} train: n={tr['trades']:4} "
              f"wr={tr['win_rate']} exp={tr['expectancy']} net={tr['net']}")

# ───────── worst-case robustness: best config at spread_model='feed' ──────
feed_rows = []
for r in top3[:1] + [x for x in top3[1:] if x["exec"] != top3[0]["exec"]][:1]:
    params = {"k_min": r["k_min"], "z_thr": r["z_thr"], "tp": r["tp"], "sl": r["sl"],
              "exec": r["exec"], "gate": "low", "spread_model": "feed"}
    s = run(r["k_min"], r["z_thr"], r["tp"], r["sl"], r["exec"], "low", spread_model="feed")
    feed_rows.append(row(params, s))
    full_stats[s["label"] + "_FEED"] = s
    print(f"[{time.time()-T0:5.1f}s] FEED {s['label']:38s} "
          f"train net={feed_rows[-1]['train']['net']} test net={feed_rows[-1]['test']['net']}")

payload = {
    "family": "spread_regime_maker",
    "method": {
        "signal": "z-score of k-min mid move over rolling 1h (mean/std), fires on "
                  "threshold cross; fade direction (sell spikes up, buy spikes down)",
        "gate": f"REAL feed spread <= rolling-1h q{int(GATE_Q_LO*100)} (low) / "
                f">= q{int(GATE_Q_HI*100)} (high inversion); fills at spread_model=0.20",
        "maker": f"limit {MAKER_OFF} pts inside vs signal mid close, ttl {MAKER_TTL} bars, "
                 "maker_exit=True; taker arm identical signal at market",
        "fixed": {"max_hold_bars": MAX_HOLD, "lot": LOT, "roll_window_bars": ROLL_W},
        "selection": f"top<=3 by TRAIN expectancy, min {min_n} train trades; "
                     "test read once after selection",
    },
    "spread_profile": spread_profile,
    "sweep": sweep,
    "diagnostics_gate_inversion": diagnostics,
    "feed_spread_robustness": feed_rows,
    "top3": top3,
    "full_stats_top3": [full_stats[f"k{r['k_min']}_z{r['z_thr']}_tp{r['tp']}_sl{r['sl']}_{r['exec']}_low"]
                        for r in top3],
}
path = eng.save_result("spread_regime_maker", payload)
print(f"\n[{time.time()-T0:5.1f}s] saved -> {path}")
