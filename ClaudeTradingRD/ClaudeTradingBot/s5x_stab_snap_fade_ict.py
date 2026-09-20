"""s5x_stab_snap_fade_ict.py — ADVERSARIAL VERIFICATION (subperiod stability) of
snap_fade_ict config lb10_k2.0_tf0.5_sf0.9_maker_off0.3.

Re-runs the EXACT config from s5x_snap_fade_ict.py (signal logic copied verbatim,
no parameter changes) and breaks fills down by month, ISO week (test window),
day-of-week and hour-of-day. Does NOT modify the original script or results.
"""
from __future__ import annotations

import json
import time as _time

import numpy as np
import pandas as pd

import s5_engine as eng

D1_PATH = "reports/xau_d1_2022_2026.csv"

# ---- fixed family constants (verbatim from s5x_snap_fade_ict.py) ----
SESSION_H0, SESSION_H1 = 3, 9
W_SD = 12000
RV_WIN = 720
GATE_DAYS = 30
MAX_HOLD = 360
ENTRY_TTL = 120
DEBOUNCE = 60
LOT = 0.10
HALF = 0.10

# ---- the candidate config under verification ----
CFG = dict(lb=10, k=2.0, tf=0.5, sf=0.9, exec="maker", off=0.30, me=False)
TAG = "lb10_k2.0_tf0.5_sf0.9_maker_off0.3"

t0 = _time.time()
print("loading S5 ...", flush=True)
df = eng.load_s5()
n = len(df)
times = df["time"].values
midc = df["mid_c"].values
hours = df["time"].dt.hour.values
dates = times.astype("datetime64[D]")
print(f"  {n} bars, {times[0]} -> {times[-1]}  ({_time.time()-t0:.1f}s)", flush=True)

# ---------------- daily ICT bias (verbatim) ----------------
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
for k in range(M):
    j = k - 1
    if j >= 1:
        if dh[j] > dh[j - 1] and dh[j] > dh[j + 1]:
            last_sh = dh[j]
        if dl[j] < dl[j - 1] and dl[j] < dl[j + 1]:
            last_sl = dl[j]
    if last_sh is not None and dc[k] > last_sh:
        b = +1
    elif last_sl is not None and dc[k] < last_sl:
        b = -1
    bias_d[k] = b

idx = np.searchsorted(d_close, times, side="right") - 1
bias = np.where(idx >= 0, bias_d[np.clip(idx, 0, M - 1)], 0)

# ---------------- low-tempo gate (verbatim) ----------------
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

# ---------------- overshoot features (verbatim) ----------------
def overshoot_features(lb_bars: int):
    mv = np.full(n, np.nan)
    mv[lb_bars:] = midc[lb_bars:] - midc[:-lb_bars]
    mv2 = np.where(np.isfinite(mv), mv * mv, 0.0)
    fin = np.isfinite(mv).astype(float)
    c2 = np.concatenate(([0.0], np.cumsum(mv2)))
    cf = np.concatenate(([0.0], np.cumsum(fin)))
    sd = np.full(n, np.nan)
    kk = cf[W_SD + 1:] - cf[1:n - W_SD + 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        val = np.sqrt((c2[W_SD + 1:] - c2[1:n - W_SD + 1]) / np.maximum(kk, 1.0))
    val[kk < 1000] = np.nan
    sd[W_SD:] = val
    return mv, sd

mv, sd = overshoot_features(CFG["lb"] * 12)

# ---------------- intents (verbatim logic, single config) ----------------
def build_intents(k, tf, sf, exec_type, off, maker_exit, tag):
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
            max_hold_bars=MAX_HOLD, lot=LOT, entry_type=exec_type,
            limit_price=float(lp), maker_exit=maker_exit, entry_ttl_bars=ENTRY_TTL, tag=tag))
    return intents

intents = build_intents(CFG["k"], CFG["tf"], CFG["sf"], CFG["exec"], CFG["off"], CFG["me"], TAG)
fills = eng.simulate(df, intents, spread_model=0.20)
s = eng.stats(df, fills, TAG)
print(f"\nintents={len(intents)}  fills={len(fills)}")
print("FULL :", s["full"])
print("TRAIN:", s["train_jan_apr"])
print("TEST :", s["test_may_jul"])

# ---------------- breakdowns ----------------
t = df["time"].values
recs = []
for f in fills:
    et = pd.Timestamp(t[f.entry_i])
    recs.append({
        "entry_time": et, "pnl": f.pnl, "reason": f.exit_reason,
        "month": et.strftime("%Y-%m"),
        "week": f"{et.isocalendar().year}-W{et.isocalendar().week:02d}",
        "dow": et.strftime("%a"), "hour": et.hour,
        "is_test": et >= pd.Timestamp("2026-05-01"),
    })
fr = pd.DataFrame(recs)

def agg(g):
    p = g["pnl"]
    return pd.Series({
        "trades": len(p), "net": round(p.sum(), 2),
        "win_rate": round((p > 0).mean() * 100, 1),
        "worst": round(p.min(), 2), "best": round(p.max(), 2),
    })

monthly = fr.groupby("month").apply(agg, include_groups=False)
print("\n=== MONTHLY (full period) ===")
print(monthly.to_string())
full_net = fr["pnl"].sum()
print(f"\nfull net = {full_net:.2f}")
for m, r in monthly.iterrows():
    share = r["net"] / full_net * 100 if full_net != 0 else float("nan")
    print(f"  {m}: net {r['net']:+8.2f}  = {share:6.1f}% of full net")

test = fr[fr["is_test"]].copy()
weekly_test = test.groupby("week").apply(agg, include_groups=False)
print("\n=== WEEKLY (test window, May 1 ->) ===")
print(weekly_test.to_string())
tnet = test["pnl"].sum()
if len(weekly_test):
    best_week = weekly_test["net"].idxmax()
    bw_net = weekly_test.loc[best_week, "net"]
    print(f"\ntest net = {tnet:.2f}; best week {best_week} net {bw_net:+.2f}; "
          f"test net ex-best-week = {tnet - bw_net:.2f}")

# test split into halves (distinct chunks check)
test_sorted = test.sort_values("entry_time")
mid_t = pd.Timestamp("2026-06-01")
h1 = test_sorted[test_sorted["entry_time"] < mid_t]["pnl"].sum()
h2 = test_sorted[test_sorted["entry_time"] >= mid_t]["pnl"].sum()
print(f"test chunks: May net {h1:.2f} ({(test_sorted['entry_time'] < mid_t).sum()} trades), "
      f"Jun-Jul net {h2:.2f} ({(test_sorted['entry_time'] >= mid_t).sum()} trades)")

print("\n=== DAY-OF-WEEK (full) ===")
print(fr.groupby("dow").apply(agg, include_groups=False)
        .reindex(["Mon", "Tue", "Wed", "Thu", "Fri"]).to_string())
print("\n=== HOUR-OF-DAY UTC (full) ===")
print(fr.groupby("hour").apply(agg, include_groups=False).to_string())

print("\n=== DAY-OF-WEEK (test only) ===")
print(test.groupby("dow").apply(agg, include_groups=False).to_string())
print("\n=== HOUR-OF-DAY UTC (test only) ===")
print(test.groupby("hour").apply(agg, include_groups=False).to_string())

# per-trade dump for the test window
print("\n=== TEST TRADES ===")
for _, r in test_sorted.iterrows():
    print(f"  {r['entry_time']}  {r['reason']:4s}  {r['pnl']:+8.2f}")

eng.save_result("stab_snap_fade_ict", {
    "family": "snap_fade_ict",
    "config": TAG,
    "params": CFG,
    "reproduced": {"full": s["full"], "train": s["train_jan_apr"], "test": s["test_may_jul"]},
    "monthly": monthly.reset_index().to_dict("records"),
    "weekly_test": weekly_test.reset_index().to_dict("records"),
    "test_ex_best_week": round(float(tnet - bw_net), 2) if len(weekly_test) else None,
    "test_chunks": {"may": round(float(h1), 2), "jun_jul": round(float(h2), 2)},
    "dow_full": fr.groupby("dow").apply(agg, include_groups=False).reset_index().to_dict("records"),
    "hour_full": fr.groupby("hour").apply(agg, include_groups=False).reset_index().to_dict("records"),
    "test_trades": [{"t": str(r["entry_time"]), "pnl": float(r["pnl"]), "reason": r["reason"]}
                    for _, r in test_sorted.iterrows()],
})
print(f"\ndone in {_time.time()-t0:.0f}s")
