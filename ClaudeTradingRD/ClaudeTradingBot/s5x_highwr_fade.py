"""s5x_highwr_fade.py — FAMILY highwr_fade

The benchmark account's own shape, made honest: fade a recent N-minute extension
with a TINY TP and a REAL hard SL (deliberately asymmetric to buy win rate).

Entry rule (causal): at the close of S5 bar i, move = mid_c[i] - mid_c[i - N*12].
If |move| >= thr and this is a FRESH crossing (condition false on bar i-1),
enter AGAINST the move (move up -> sell, move down -> buy). Gap guard: the
lookback must span <= 1.5x its nominal wall-clock length (skips weekend gaps).

Thresholds: one literal spec value (2.0 pts fixed) kept as a control, but note
2026 XAU trades at 3944-5594 with a MEDIAN 3-min |move| of 1.8 pts, so the
spec's 0.8-2.0 fixed band is below noise. Calibrated fixed thresholds sit at
~q85-q90 of each N's move distribution; plus a vol-scaled variant
(|move| >= k * rolling-std(move, past 1h), floor 1.0 pt).

TP 0.5-1.5 pts / SL 4-8 pts anchored on mid_c[signal]. Session gates and max
hold per the family spec. All fills through s5_engine (spread_model=0.20).

Sweep: 4 signal variants x 3 tp/sl pairs x 4 sessions @ 4h hold = 48 configs,
plus 8 hold-variant rows (30min, 2d for the vol-scaled signal, mid tp/sl,
all 4 sessions) = 56 total. Selection on TRAIN only; test read once at the end.
"""
from __future__ import annotations

import time as _time

import numpy as np
import pandas as pd

import s5_engine as eng

BARS_PER_MIN = 12
HOLD_4H = 2880
HOLD_30M = 360
HOLD_2D = 34560

t0 = _time.time()
df = eng.load_s5()
n = len(df)
mid = df["mid_c"].values
tarr = df["time"].values
hours = df["time"].dt.hour.values
print(f"loaded {n} bars in {_time.time()-t0:.1f}s")

# ── signal variants (computed once, reused across configs) ─────────────────
def signal_candidates(N: int, mode: str, val: float, floor: float = 1.0):
    """Return (indices, sides) of fresh threshold crossings. Fully causal:
    uses only mid closes up to and including bar i."""
    k = N * BARS_PER_MIN
    move = np.full(n, np.nan)
    move[k:] = mid[k:] - mid[:-k]
    # gap guard: lookback wall-clock must be close to nominal
    ok = np.zeros(n, bool)
    dt = (tarr[k:] - tarr[:-k]) / np.timedelta64(1, "s")
    ok[k:] = dt <= N * 60 * 1.5
    if mode == "fixed":
        thr = np.full(n, val)
    else:  # vol-scaled: k * rolling std of the move series over the past hour
        s = pd.Series(move).rolling(720, min_periods=720).std().values
        thr = np.maximum(floor, val * s)
    with np.errstate(invalid="ignore"):
        cond = (np.abs(move) >= thr) & ok
    prev = np.roll(cond, 1)
    prev[0] = True
    fresh = cond & ~prev
    idx = np.where(fresh)[0]
    idx = idx[idx + 1 < n]
    sides = np.where(move[idx] > 0, "sell", "buy")
    return idx, sides

SIGNALS = {
    # name: (N, mode, value)  — f3_2.0 is the literal-spec control (sub-noise)
    "f3_thr2.0":  (3,  "fixed", 2.0),
    "f5_thr6.0":  (5,  "fixed", 6.0),
    "f10_thr10":  (10, "fixed", 10.0),
    "v5_k2.5":    (5,  "vol",   2.5),
}
sig_cache = {}
for name, (N, mode, val) in SIGNALS.items():
    idx, sides = signal_candidates(N, mode, val)
    sig_cache[name] = (idx, sides)
    print(f"signal {name}: {len(idx)} raw candidates")

SESSIONS = {
    "h22_23":          {22, 23},
    "h8_12_13":        {8, 12, 13},
    "h8_12_13_22_23":  {8, 12, 13, 22, 23},
    "all":             None,
}
TPSL = [(0.5, 4.0), (1.0, 6.0), (1.5, 8.0)]

def build_intents(idx, sides, sess_hours, tp_pts, sl_pts, hold, lot=0.10):
    if sess_hours is not None:
        m = np.isin(hours[idx], list(sess_hours))
        idx, sides = idx[m], sides[m]
    intents = []
    for i, sd in zip(idx.tolist(), sides.tolist()):
        px = mid[i]
        if sd == "buy":
            tp, sl = px + tp_pts, px - sl_pts
        else:
            tp, sl = px - tp_pts, px + sl_pts
        intents.append(eng.OrderIntent(signal_i=i, side=sd, tp=tp, sl=sl,
                                       max_hold_bars=hold, lot=lot,
                                       entry_type="taker"))
    return intents

# ── sweep ───────────────────────────────────────────────────────────────────
rows = []

def run_config(sig_name, sess_name, tp_pts, sl_pts, hold, hold_tag):
    idx, sides = sig_cache[sig_name]
    intents = build_intents(idx, sides, SESSIONS[sess_name], tp_pts, sl_pts, hold)
    name = f"{sig_name}|{sess_name}|tp{tp_pts}|sl{sl_pts}|{hold_tag}"
    fills = eng.simulate(df, intents, spread_model=0.20)
    s = eng.stats(df, fills, name)
    row = {
        "name": name,
        "params": {"signal": sig_name, "N_min": SIGNALS[sig_name][0],
                   "thr_mode": SIGNALS[sig_name][1], "thr_val": SIGNALS[sig_name][2],
                   "session": sess_name, "tp_pts": tp_pts, "sl_pts": sl_pts,
                   "max_hold_bars": hold, "entry": "taker", "lot": 0.10,
                   "spread_model": 0.20},
        "full": s.get("full", {}), "train": s.get("train_jan_apr", {}),
        "test": s.get("test_may_jul", {}),
    }
    rows.append(row)
    tr, te = row["train"], row["test"]
    print(f"{name:55s} train: n={tr.get('trades',0):5d} wr={tr.get('win_rate',0):5.1f} "
          f"exp={tr.get('expectancy',0):8.3f} net={tr.get('net',0):9.2f} | "
          f"test: n={te.get('trades',0):5d} wr={te.get('win_rate',0):5.1f} "
          f"exp={te.get('expectancy',0):8.3f} net={te.get('net',0):9.2f}")
    return row

t1 = _time.time()
# main grid: 4 signals x 4 sessions x 3 tp/sl @ 4h hold = 48
for sig_name in SIGNALS:
    for sess_name in SESSIONS:
        for tp_pts, sl_pts in TPSL:
            run_config(sig_name, sess_name, tp_pts, sl_pts, HOLD_4H, "4h")

# hold variants: vol-scaled signal, mid tp/sl, all sessions x {30min, 2d} = 8
for sess_name in SESSIONS:
    for hold, tag in [(HOLD_30M, "30m"), (HOLD_2D, "2d")]:
        run_config("v5_k2.5", sess_name, 1.0, 6.0, hold, tag)

print(f"\nsweep of {len(rows)} configs done in {_time.time()-t1:.1f}s")

# ── TRAIN-only selection ────────────────────────────────────────────────────
def min_trades(row):
    return 100 if row["params"]["session"] == "all" else 40

eligible = [r for r in rows
            if r["train"].get("trades", 0) >= min_trades(r)
            and r["train"].get("expectancy", -1) > 0]
# family goal: max win rate subject to positive expectancy -> rank eligible by
# train WR, tie-break by train expectancy
eligible.sort(key=lambda r: (r["train"]["win_rate"], r["train"]["expectancy"]),
              reverse=True)
best = eligible[:3]
if not best:  # nothing positive on train — report the least-bad honestly
    fallback = [r for r in rows if r["train"].get("trades", 0) >= min_trades(r)]
    fallback.sort(key=lambda r: r["train"].get("expectancy", -9e9), reverse=True)
    best = fallback[:3]
    print("\nNO config had positive TRAIN expectancy at required trade counts; "
          "reporting least-bad by train expectancy.")

print("\n=== TOP CONFIGS (selected on TRAIN only) ===")
for r in best:
    print(f"{r['name']}\n  TRAIN: {r['train']}\n  TEST : {r['test']}")

# feed-spread worst-case robustness row for the single best config
feed_row = None
if best:
    b = best[0]
    p = b["params"]
    idx, sides = sig_cache[p["signal"]]
    intents = build_intents(idx, sides, SESSIONS[p["session"]],
                            p["tp_pts"], p["sl_pts"], p["max_hold_bars"])
    fills = eng.simulate(df, intents, spread_model="feed")
    s = eng.stats(df, fills, b["name"] + "|FEED")
    feed_row = {"name": b["name"], "full": s.get("full", {}),
                "train": s.get("train_jan_apr", {}),
                "test": s.get("test_may_jul", {})}
    print("\n=== FEED-SPREAD (worst case) for best config ===")
    print(f"  TRAIN: {feed_row['train']}\n  TEST : {feed_row['test']}")

payload = {
    "family": "highwr_fade",
    "description": ("Fade an N-minute extension with tiny TP / big hard SL. "
                    "Signals on S5 close, fresh threshold crossings, "
                    "taker entry, spread_model=0.20, lot=0.10."),
    "notes": ("Spec fixed thresholds 0.8-2.0 pts are below 2026 XAU noise "
              "(median 3-min |move|=1.8 pts at px 3944-5594); f3_thr2.0 kept "
              "as literal-spec control, other fixed thresholds calibrated to "
              "~q85-q90. Move-SL-to-breakeven variant skipped: s5_engine has "
              "no dynamic-SL support."),
    "n_configs": len(rows),
    "sweep": rows,
    "best_by_train": [r["name"] for r in best],
    "feed_spread_best": feed_row,
}
path = eng.save_result("highwr_fade", payload)
print(f"\nsaved -> {path}  total {_time.time()-t0:.1f}s")
