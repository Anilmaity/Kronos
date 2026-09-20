"""s5x_stress_snap_fade_ict.py — adversarial cost & parameter stress of ONE frozen config.

Candidate: family snap_fade_ict, config lb10_k2.0_tf0.5_sf0.9_maker_off0.3
  params: lb_min=10, k=2.0, target_frac=0.5, stop_frac=0.9, entry_type=maker,
          maker_offset_sd=0.3, maker_exit=False, max_hold_bars=360, entry_ttl_bars=120,
          session 03-09 UTC, lot=0.1.

Signal mechanism is copied VERBATIM from s5x_snap_fade_ict.py (not imported, original
untouched). This script does NOT re-select anything: it re-runs the single frozen config
under (a) commission x2, (b) sl slippage 0.15, (c) spread 0.30, (d) feed spread
(worst case), and (e) 8 parameter neighbors at +/-20-30% under baseline costs.
"""
from __future__ import annotations

import time as _time

import numpy as np
import pandas as pd

import s5_engine as eng

D1_PATH = "reports/xau_d1_2022_2026.csv"

# ── fixed family constants (verbatim from s5x_snap_fade_ict.py) ──
SESSION_H0, SESSION_H1 = 3, 9
W_SD = 12000
RV_WIN = 720
GATE_DAYS = 30
MAX_HOLD = 360
ENTRY_TTL = 120
DEBOUNCE = 60
LOT = 0.10
HALF = 0.10

t0 = _time.time()
print("loading S5 ...", flush=True)
df = eng.load_s5()
n = len(df)
times = df["time"].values
midc = df["mid_c"].values
hours = df["time"].dt.hour.values
dates = times.astype("datetime64[D]")
print(f"  {n} bars, {times[0]} -> {times[-1]}  ({_time.time()-t0:.1f}s)", flush=True)

# ── daily ICT bias (causal) — verbatim ──
d1 = pd.read_csv(D1_PATH)
d1["time"] = pd.to_datetime(d1["time"], utc=True).dt.tz_localize(None)
d1 = d1.sort_values("time").reset_index(drop=True)
dh, dl, dc = d1["h"].values, d1["l"].values, d1["c"].values
dt_open = d1["time"].values
M = len(d1)
d_close = np.empty(M, dtype="datetime64[ns]")
d_close[:-1] = dt_open[1:]
d_close[-1] = dt_open[-1] + np.timedelta64(24, "h")

bias_d = np.zeros(M, dtype=int)
last_sh, last_sl = None, None
b = 0
for kk in range(M):
    j = kk - 1
    if j >= 1:
        if dh[j] > dh[j - 1] and dh[j] > dh[j + 1]:
            last_sh = dh[j]
        if dl[j] < dl[j - 1] and dl[j] < dl[j + 1]:
            last_sl = dl[j]
    if last_sh is not None and dc[kk] > last_sh:
        b = +1
    elif last_sl is not None and dc[kk] < last_sl:
        b = -1
    bias_d[kk] = b

idx = np.searchsorted(d_close, times, side="right") - 1
bias = np.where(idx >= 0, bias_d[np.clip(idx, 0, M - 1)], 0)

# ── low-tempo gate (causal) — verbatim ──
ret = np.diff(midc, prepend=midc[0])
aret = np.abs(ret)
cs = np.concatenate(([0.0], np.cumsum(aret)))
rv = np.full(n, np.nan)
rv[RV_WIN:] = (cs[RV_WIN + 1:] - cs[1:n - RV_WIN + 1]) / RV_WIN

rv_s = pd.Series(rv, index=pd.Index(dates, name="d"))
daily_med = rv_s.groupby(level=0).median()
gate_thr = daily_med.rolling(GATE_DAYS, min_periods=10).median().shift(1)
gate_per_bar = gate_thr.reindex(dates).values
low_tempo = np.isfinite(rv) & np.isfinite(gate_per_bar) & (rv < gate_per_bar)

session = (hours >= SESSION_H0) & (hours < SESSION_H1)

# ── overshoot features — verbatim ──
def overshoot_features(lb_bars: int):
    mv = np.full(n, np.nan)
    mv[lb_bars:] = midc[lb_bars:] - midc[:-lb_bars]
    mv2 = np.where(np.isfinite(mv), mv * mv, 0.0)
    fin = np.isfinite(mv).astype(float)
    c2 = np.concatenate(([0.0], np.cumsum(mv2)))
    cf = np.concatenate(([0.0], np.cumsum(fin)))
    sd = np.full(n, np.nan)
    k = cf[W_SD + 1:] - cf[1:n - W_SD + 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        val = np.sqrt((c2[W_SD + 1:] - c2[1:n - W_SD + 1]) / np.maximum(k, 1.0))
    val[k < 1000] = np.nan
    sd[W_SD:] = val
    return mv, sd

_feat_cache: dict = {}
def feat(lb_min: int):
    if lb_min not in _feat_cache:
        _feat_cache[lb_min] = overshoot_features(lb_min * 12)
    return _feat_cache[lb_min]

# ── intent builder — verbatim mechanism, parametrized max_hold ──
def build_intents(lb_min, k, tf, sf, exec_type, off=0.0, maker_exit=False, tag="",
                  max_hold=MAX_HOLD):
    mv, sd = feat(lb_min)
    with np.errstate(invalid="ignore"):
        hot = session & low_tempo & np.isfinite(mv) & np.isfinite(sd) & (sd > 0) \
              & (np.abs(mv) >= k * sd)
    up = mv > 0
    ok = hot & (((up) & (bias == -1)) | ((~up) & (bias == +1)))
    edge = ok & ~np.roll(ok, 1)
    edge[0] = False
    sig = np.flatnonzero(edge)
    intents, last = [], -10**9
    for i in sig:
        if i - last < DEBOUNCE or i + 2 >= n:
            continue
        last = i
        ov = abs(mv[i])
        sell = up[i]
        side = "sell" if sell else "buy"
        if exec_type == "taker":
            e = midc[i] - HALF if sell else midc[i] + HALF
            lp = 0.0
        else:
            lp = midc[i] + off * sd[i] if sell else midc[i] - off * sd[i]
            e = lp
        tp = e - tf * ov if sell else e + tf * ov
        sl = e + sf * ov if sell else e - sf * ov
        intents.append(eng.OrderIntent(
            signal_i=int(i), side=side, tp=float(tp), sl=float(sl),
            max_hold_bars=max_hold, lot=LOT, entry_type=exec_type,
            limit_price=float(lp), maker_exit=maker_exit, entry_ttl_bars=ENTRY_TTL, tag=tag))
    return intents

# ── the frozen candidate ──
BASE = dict(lb=10, k=2.0, tf=0.5, sf=0.9, off=0.30, max_hold=360)

def run(tag, lb, k, tf, sf, off, max_hold, commission=eng.COMMISSION_PER_LOT_RT,
        slip=0.05, spread=0.20):
    intents = build_intents(lb, k, tf, sf, "maker", off, False, tag, max_hold)
    fills = eng.simulate(df, intents, commission_per_lot_rt=commission,
                         sl_slippage_pts=slip, spread_model=spread)
    s = eng.stats(df, fills, tag)
    tr, te = s.get("train_jan_apr", {}), s.get("test_may_jul", {})
    print(f"{tag:38s} | TR n={tr.get('trades',0):3d} wr={tr.get('win_rate',0):5.1f} "
          f"net={tr.get('net',0):+8.2f} exp={tr.get('expectancy',0):+7.3f} "
          f"| TE n={te.get('trades',0):3d} wr={te.get('win_rate',0):5.1f} "
          f"net={te.get('net',0):+8.2f} exp={te.get('expectancy',0):+7.3f} "
          f"pf={te.get('pf',0)}", flush=True)
    return {"tag": tag, "params": dict(lb=lb, k=k, tf=tf, sf=sf, off=off, max_hold=max_hold),
            "costs": dict(commission=commission, sl_slippage=slip, spread=str(spread)),
            "train": tr, "test": te, "full": s.get("full", {})}

results = []
b = BASE
print("\n--- baseline reproduction (spread 0.20, comm 4.90, slip 0.05) ---")
results.append(run("baseline", b["lb"], b["k"], b["tf"], b["sf"], b["off"], b["max_hold"]))

print("\n--- cost stresses on the frozen config ---")
results.append(run("a_comm_x2_9.80", b["lb"], b["k"], b["tf"], b["sf"], b["off"], b["max_hold"],
                   commission=9.80))
results.append(run("b_slip_0.15", b["lb"], b["k"], b["tf"], b["sf"], b["off"], b["max_hold"],
                   slip=0.15))
results.append(run("c_spread_0.30", b["lb"], b["k"], b["tf"], b["sf"], b["off"], b["max_hold"],
                   spread=0.30))
results.append(run("d_spread_feed_worstcase", b["lb"], b["k"], b["tf"], b["sf"], b["off"],
                   b["max_hold"], spread="feed"))
print("\n--- combined stress (a+b+c together, extra pessimism row) ---")
results.append(run("abc_combined", b["lb"], b["k"], b["tf"], b["sf"], b["off"], b["max_hold"],
                   commission=9.80, slip=0.15, spread=0.30))

print("\n--- parameter neighbors (+/-20-30%, baseline costs) ---")
NEIGHBORS = [
    ("n_k1.6",    dict(k=1.6)),
    ("n_k2.4",    dict(k=2.4)),
    ("n_tf0.4",   dict(tf=0.4)),
    ("n_tf0.6",   dict(tf=0.6)),
    ("n_sf0.72",  dict(sf=0.72)),
    ("n_sf1.08",  dict(sf=1.08)),
    ("n_off0.21", dict(off=0.21)),
    ("n_off0.39", dict(off=0.39)),
]
for tag, delta in NEIGHBORS:
    p = {**BASE, **delta}
    results.append(run(tag, p["lb"], p["k"], p["tf"], p["sf"], p["off"], p["max_hold"]))

path = eng.save_result("stress_snap_fade_ict", {
    "family": "snap_fade_ict",
    "candidate": "lb10_k2.0_tf0.5_sf0.9_maker_off0.3",
    "lens": "cost & parameter stress",
    "claimed_test": {"trades": 26, "win_rate": 61.5, "net": 110.94, "expectancy": 4.267,
                     "pf": 1.176},
    "rows": results,
})
print(f"\nsaved -> {path}   total {_time.time()-t0:.0f}s")
