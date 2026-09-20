"""s5x_snap_fade_ict.py — snap-fade + ICT daily-bias scalper ported to S5 with real spread handling.

Model (port of the previously validated M5 snap-fade maker study, s5_snap_ict.py):
  * Session 03:00-09:00 UTC only.
  * Overshoot: the last `lb_min`-minute move mv = mid_c[i] - mid_c[i-LB] exceeds k x its own
    trailing RMS (W = 12000 S5 bars ~ 16.7h, matching the M5 study's W=200).  FADE it.
  * Target = tf x overshoot toward the mean; stop = sf x overshoot beyond entry
    (prior study: 0.9 optimal, 1.5 was a cliff — grid stays in the 0.8-1.0 plateau).
  * Low-tempo gate (CAUSAL, unlike the old full-sample median): rv = trailing 1h mean |1-bar ret|;
    per-day median of rv; gate threshold for day D = median of the previous <=30 daily medians
    (min 10, shifted so day D itself is excluded).  Trade only when rv < gate.
  * Daily ICT bias from reports/xau_d1_2022_2026.csv: 3-bar swing fractals (confirmed one bar
    later), BOS/CHoCH body-close state machine.  Bias state after bar k is usable only from bar
    k's CLOSE time (= next bar's open).  Only fade in the bias direction: up-overshoot -> sell
    requires bearish daily bias; down-overshoot -> buy requires bullish bias.
  * Signals emitted on the rising edge of the condition, 60-bar (5-min) debounce; engine
    max_concurrent=1 prevents overlap.  Max hold 360 S5 bars (30 min); maker entry TTL 120 bars.
  * Execution swept: taker vs maker (limit posted `off` x sd DEEPER into the overshoot),
    maker_exit True/False.

All fills/costs via s5_engine (spread_model=0.20 primary; 'feed' once for the best config).
Sweep <= 48 configs, TRAIN-only selection, test read once at the end.
"""
from __future__ import annotations

import sys
import time as _time

import numpy as np
import pandas as pd

import s5_engine as eng

D1_PATH = "reports/xau_d1_2022_2026.csv"

SESSION_H0, SESSION_H1 = 3, 9          # 03:00 <= hour < 09:00 UTC
W_SD = 12000                           # trailing RMS window for the overshoot std (S5 bars)
RV_WIN = 720                           # 1h realized-vol window (S5 bars)
GATE_DAYS = 30                         # trailing days for the low-tempo median
MAX_HOLD = 360                         # 30 min
ENTRY_TTL = 120                        # 10 min for maker limits
DEBOUNCE = 60                          # 5 min between emitted signals
LOT = 0.10
HALF = 0.10                            # half of the 0.20 primary spread (taker entry anchor)

t0 = _time.time()
print("loading S5 ...", flush=True)
df = eng.load_s5()
n = len(df)
times = df["time"].values
midc = df["mid_c"].values
hours = df["time"].dt.hour.values
dates = times.astype("datetime64[D]")
print(f"  {n} bars, {times[0]} -> {times[-1]}  ({_time.time()-t0:.1f}s)", flush=True)

# ---------------------------------------------------------------- daily ICT bias (causal)
d1 = pd.read_csv(D1_PATH)
d1["time"] = pd.to_datetime(d1["time"], utc=True).dt.tz_localize(None)
d1 = d1.sort_values("time").reset_index(drop=True)
dh, dl, dc = d1["h"].values, d1["l"].values, d1["c"].values
dt_open = d1["time"].values
M = len(d1)
# close time of daily bar k = open of bar k+1 (last bar: +24h)
d_close = np.empty(M, dtype="datetime64[ns]")
d_close[:-1] = dt_open[1:]
d_close[-1] = dt_open[-1] + np.timedelta64(24, "h")

bias_d = np.zeros(M, dtype=int)
last_sh, last_sl = None, None
b = 0
for k in range(M):
    # 3-bar fractal centered at k-1, confirmed once bar k closes
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

# map to S5 bars: bias of the most recent daily bar whose CLOSE <= bar time
idx = np.searchsorted(d_close, times, side="right") - 1
bias = np.where(idx >= 0, bias_d[np.clip(idx, 0, M - 1)], 0)
print(f"daily bias: bull {np.mean(bias==1)*100:.0f}% / bear {np.mean(bias==-1)*100:.0f}% "
      f"/ flat {np.mean(bias==0)*100:.0f}% of S5 bars", flush=True)

# ---------------------------------------------------------------- low-tempo gate (causal)
ret = np.diff(midc, prepend=midc[0])
aret = np.abs(ret)
cs = np.concatenate(([0.0], np.cumsum(aret)))
rv = np.full(n, np.nan)
rv[RV_WIN:] = (cs[RV_WIN + 1:] - cs[1:n - RV_WIN + 1]) / RV_WIN

rv_s = pd.Series(rv, index=pd.Index(dates, name="d"))
daily_med = rv_s.groupby(level=0).median()
gate_thr = daily_med.rolling(GATE_DAYS, min_periods=10).median().shift(1)  # excludes current day
gate_per_bar = gate_thr.reindex(dates).values
low_tempo = np.isfinite(rv) & np.isfinite(gate_per_bar) & (rv < gate_per_bar)
print(f"low-tempo gate on {low_tempo.mean()*100:.0f}% of bars "
      f"(first gated day {daily_med.index[min(10, len(daily_med)-1)]})", flush=True)

session = (hours >= SESSION_H0) & (hours < SESSION_H1)

# ---------------------------------------------------------------- overshoot features per lookback
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

FEAT = {lb: overshoot_features(lb * 12) for lb in (2, 5, 10)}

# ---------------------------------------------------------------- signal -> intents
def build_intents(lb_min, k, tf, sf, exec_type, off=0.0, maker_exit=False, tag=""):
    mv, sd = FEAT[lb_min]
    with np.errstate(invalid="ignore"):
        hot = session & low_tempo & np.isfinite(mv) & np.isfinite(sd) & (sd > 0) \
              & (np.abs(mv) >= k * sd)
    up = mv > 0
    # fade must agree with the daily bias
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
            e = midc[i] - HALF if sell else midc[i] + HALF   # expected next-open fill incl. spread
            lp = 0.0
        else:
            lp = midc[i] + off * sd[i] if sell else midc[i] - off * sd[i]  # deeper into overshoot
            e = lp
        tp = e - tf * ov if sell else e + tf * ov
        sl = e + sf * ov if sell else e - sf * ov
        intents.append(eng.OrderIntent(
            signal_i=int(i), side=side, tp=float(tp), sl=float(sl),
            max_hold_bars=MAX_HOLD, lot=LOT, entry_type=exec_type,
            limit_price=float(lp), maker_exit=maker_exit, entry_ttl_bars=ENTRY_TTL, tag=tag))
    return intents

# ---------------------------------------------------------------- config grid (<=48)
CONFIGS = []
TS_PAIRS = [(0.4, 0.9), (0.5, 0.9), (0.6, 0.9), (0.5, 0.8), (0.5, 1.0)]
for k in (1.2, 1.6, 2.0):
    for tf, sf in TS_PAIRS:
        CONFIGS.append(dict(lb=10, k=k, tf=tf, sf=sf, exec="taker", off=0.0, me=False))
for lb in (2, 5):  # lookback variants at the center config
    CONFIGS.append(dict(lb=lb, k=1.6, tf=0.5, sf=0.9, exec="taker", off=0.0, me=False))
for k in (1.2, 1.6, 2.0):
    for off in (0.15, 0.30):
        for tf, sf in [(0.4, 0.9), (0.5, 0.9), (0.6, 0.9)]:
            CONFIGS.append(dict(lb=10, k=k, tf=tf, sf=sf, exec="maker", off=off, me=False))
for k in (1.2, 1.6, 2.0):
    for off in (0.15, 0.30):
        CONFIGS.append(dict(lb=10, k=k, tf=0.5, sf=0.9, exec="maker", off=off, me=True))
print(f"{len(CONFIGS)} configs", flush=True)

rows = []
for ci, cfg in enumerate(CONFIGS):
    tag = (f"lb{cfg['lb']}_k{cfg['k']}_tf{cfg['tf']}_sf{cfg['sf']}_{cfg['exec']}"
           + (f"_off{cfg['off']}" if cfg["exec"] == "maker" else "")
           + ("_mx" if cfg["me"] else ""))
    intents = build_intents(cfg["lb"], cfg["k"], cfg["tf"], cfg["sf"],
                            cfg["exec"], cfg["off"], cfg["me"], tag)
    fills = eng.simulate(df, intents, spread_model=0.20)
    s = eng.stats(df, fills, tag)
    tr, te = s.get("train_jan_apr", {}), s.get("test_may_jul", {})
    rows.append({"name": tag, "params": cfg, "n_intents": len(intents),
                 "train": tr, "test": te, "full": s.get("full", {})})
    print(f"[{ci+1:2d}/{len(CONFIGS)}] {tag:44s} intents={len(intents):4d} "
          f"| TR n={tr.get('trades',0):3d} wr={tr.get('win_rate',0):5.1f} "
          f"net={tr.get('net',0):+9.2f} exp={tr.get('expectancy',0):+7.3f} "
          f"| TE n={te.get('trades',0):3d} wr={te.get('win_rate',0):5.1f} "
          f"net={te.get('net',0):+9.2f}", flush=True)

# ---------------------------------------------------------------- TRAIN-only selection
MIN_TR = 40  # naturally low-frequency family (session + low-vol + bias gates)
elig = [r for r in rows if r["train"].get("trades", 0) >= MIN_TR]
elig.sort(key=lambda r: r["train"].get("expectancy", -1e9), reverse=True)
best = elig[:3]
print("\n=== TOP-3 BY TRAIN EXPECTANCY (test shown verbatim, read once) ===")
for r in best:
    print(f"  {r['name']}\n    TRAIN {r['train']}\n    TEST  {r['test']}")

# feed-spread worst-case row for the best config only
feed_stats = None
if best:
    b = best[0]["params"]
    intents = build_intents(b["lb"], b["k"], b["tf"], b["sf"], b["exec"], b["off"], b["me"],
                            best[0]["name"] + "_feed")
    fills = eng.simulate(df, intents, spread_model="feed")
    feed_stats = eng.stats(df, fills, best[0]["name"] + "_feed")
    print(f"\nFEED-SPREAD worst case for {best[0]['name']}:")
    print(f"  TRAIN {feed_stats.get('train_jan_apr')}\n  TEST  {feed_stats.get('test_may_jul')}")

# maker-vs-taker gap at matched (k, tf, sf=0.9), 0.20 spread, TRAIN
gap = []
for k in (1.2, 1.6, 2.0):
    for tf in (0.4, 0.5, 0.6):
        tk = next((r for r in rows if r["params"] == dict(lb=10, k=k, tf=tf, sf=0.9,
                                                          exec="taker", off=0.0, me=False)), None)
        for off in (0.15, 0.30):
            mk = next((r for r in rows if r["params"] == dict(lb=10, k=k, tf=tf, sf=0.9,
                                                              exec="maker", off=off, me=False)), None)
            if tk and mk:
                gap.append({"k": k, "tf": tf, "off": off,
                            "taker_train_exp": tk["train"].get("expectancy"),
                            "maker_train_exp": mk["train"].get("expectancy"),
                            "taker_train_n": tk["train"].get("trades"),
                            "maker_train_n": mk["train"].get("trades")})
print("\nmaker-vs-taker TRAIN expectancy gap @0.20 spread:")
for g in gap:
    print(f"  k={g['k']} tf={g['tf']} off={g['off']}: taker {g['taker_train_exp']} (n={g['taker_train_n']})"
          f"  maker {g['maker_train_exp']} (n={g['maker_train_n']})")

path = eng.save_result("snap_fade_ict", {
    "family": "snap_fade_ict",
    "model": "03-09 UTC snap-fade of k*sd overshoots, tf*ov target / sf*ov stop, causal 30d "
             "low-tempo gate, causal D1 fractal BOS/CHoCH bias filter; taker vs maker execution",
    "fixed": {"W_SD": W_SD, "RV_WIN": RV_WIN, "GATE_DAYS": GATE_DAYS, "MAX_HOLD": MAX_HOLD,
              "ENTRY_TTL": ENTRY_TTL, "DEBOUNCE": DEBOUNCE, "lot": LOT, "spread_model": 0.20},
    "sweep": rows,
    "top3_by_train_expectancy": [r["name"] for r in best],
    "feed_spread_best": feed_stats,
    "maker_vs_taker_gap_train": gap,
})
print(f"\nsaved -> {path}   total {_time.time()-t0:.0f}s")
