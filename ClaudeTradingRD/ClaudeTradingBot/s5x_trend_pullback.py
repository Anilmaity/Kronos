"""s5x_trend_pullback.py — FAMILY trend_pullback

High-WR WITH-trend scalps on 2026 XAUUSD S5 data.

HTF bias : EMA(20) vs EMA(50) on causally-resampled M15 / H1 mid closes.
           A HTF bar is only used after it CLOSES (resample -> shift(1) ->
           map back to S5 by flooring the S5 timestamp to the HTF bucket).
Entry    : S5 bar whose low touches the (shifted) fast EMA — optionally a
           deeper level EMA - 0.25*ATR(M15) — while bias holds and the S5
           bar CLOSES back on the trend side of the level. Shorts mirrored.
Session  : London+NY only (06:00-20:59 UTC) — fixed for the whole sweep.
Exits    : TP = ref + tp_pts (ref = signal-bar mid close), SL = mult*ATR(M15)
           (clamped 2..30 pts) or fixed pts. Max hold 8h (5760 S5 bars).
Costs    : everything through s5_engine.simulate, spread_model=0.20,
           $4.90/lot RT commission, lot=0.10, SL-first same-bar tie-break.

Sweep (TRAIN Jan-Apr only): TF{15min,1h} x depth{touch,deep} x
TP{0.8,1.2,1.8,2.5} x SL{fix3.0, 1.0xATR, 2.0xATR} = 48 configs.
Top 3 by train expectancy (>=100 train trades) -> read test ONCE, verbatim.
Best config also re-run once with spread_model='feed' (worst-case row).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

import s5_engine as eng

T0 = time.time()
df = eng.load_s5()
N = len(df)
mid_l = df["mid_l"].values
mid_h = df["mid_h"].values
mid_c = df["mid_c"].values
hours = df["time"].dt.hour.values
SESSION = (hours >= 6) & (hours <= 20)          # London + NY
MAX_HOLD = 5760                                  # 8h of S5 bars
COOLDOWN = {"15min": 180, "1h": 720}             # one HTF bar, in S5 bars

# ---------------------------------------------------------------- HTF features
def htf_map(rule: str):
    """Return (ema_fast, ema_slow, atr15) mapped to S5 bars, strictly causal."""
    htf = eng.resample(df, rule)                 # completed bars, indexed by bar START
    ema20 = htf["c"].ewm(span=20, adjust=False).mean().shift(1)   # only CLOSED bars
    ema50 = htf["c"].ewm(span=50, adjust=False).mean().shift(1)
    floor = df["time"].dt.floor(rule)
    ef = ema20.reindex(floor).values
    es = ema50.reindex(floor).values
    return ef, es

def atr15_map():
    m15 = eng.resample(df, "15min")
    tr = np.maximum(m15["h"] - m15["l"],
                    np.maximum((m15["h"] - m15["c"].shift()).abs(),
                               (m15["l"] - m15["c"].shift()).abs()))
    atr = tr.rolling(14).mean().shift(1)         # closed bars only
    floor15 = df["time"].dt.floor("15min")
    return atr.reindex(floor15).values

ATR15 = atr15_map()
HTF = {rule: htf_map(rule) for rule in ("15min", "1h")}
print(f"[{time.time()-T0:6.1f}s] features ready")

# ---------------------------------------------------------------- signal sets
def build_signals(rule: str, depth_mult: float):
    """Return (idx, side, ref, atr) arrays of pullback-touch signals."""
    ef, es = HTF[rule]
    valid = ~np.isnan(ef) & ~np.isnan(es) & ~np.isnan(ATR15) & SESSION
    lvl_long = ef - depth_mult * ATR15
    lvl_short = ef + depth_mult * ATR15
    long_sig = valid & (ef > es) & (mid_l <= lvl_long) & (mid_c >= lvl_long)
    short_sig = valid & (ef < es) & (mid_h >= lvl_short) & (mid_c <= lvl_short)
    cand = np.flatnonzero(long_sig | short_sig)
    cd = COOLDOWN[rule]
    keep_i, keep_side = [], []
    last = -10**9
    for i in cand:
        if i - last >= cd:
            keep_i.append(int(i))
            keep_side.append("buy" if long_sig[i] else "sell")
            last = i
    return keep_i, keep_side

SIGSETS = {}
for rule in ("15min", "1h"):
    for depth in (0.0, 0.25):
        k = (rule, depth)
        SIGSETS[k] = build_signals(rule, depth)
        print(f"[{time.time()-T0:6.1f}s] signals {k}: {len(SIGSETS[k][0])}")

# ---------------------------------------------------------------- sweep
TPS = [0.8, 1.2, 1.8, 2.5]
SLS = [("fix", 3.0), ("atr", 1.0), ("atr", 2.0)]

rows = []
for rule in ("15min", "1h"):
    for depth in (0.0, 0.25):
        idxs, sides = SIGSETS[(rule, depth)]
        for tp_pts in TPS:
            for sl_kind, sl_val in SLS:
                tag = f"{rule}_d{depth}_tp{tp_pts}_{sl_kind}{sl_val}"
                intents = []
                for i, side in zip(idxs, sides):
                    ref = mid_c[i]
                    if sl_kind == "atr":
                        sl_pts = float(np.clip(sl_val * ATR15[i], 2.0, 30.0))
                    else:
                        sl_pts = sl_val
                    if side == "buy":
                        tp, sl = ref + tp_pts, ref - sl_pts
                    else:
                        tp, sl = ref - tp_pts, ref + sl_pts
                    intents.append(eng.OrderIntent(
                        signal_i=i, side=side, tp=tp, sl=sl,
                        max_hold_bars=MAX_HOLD, lot=0.10,
                        entry_type="taker", tag=tag))
                fills = eng.simulate(df, intents, spread_model=0.20)
                s = eng.stats(df, fills, tag)
                rows.append({
                    "tf": rule, "depth": depth, "tp": tp_pts,
                    "sl_kind": sl_kind, "sl_val": sl_val,
                    "train": s.get("train_jan_apr", {}),
                    "test": s.get("test_may_jul", {}),
                    "full": s.get("full", {}),
                })
                tr, te = rows[-1]["train"], rows[-1]["test"]
                print(f"[{time.time()-T0:6.1f}s] {tag:34s} "
                      f"train n={tr.get('trades',0):4d} wr={tr.get('win_rate',0):5.1f} "
                      f"net={tr.get('net',0):9.2f} exp={tr.get('expectancy',0):7.3f} | "
                      f"test n={te.get('trades',0):4d} wr={te.get('win_rate',0):5.1f} "
                      f"net={te.get('net',0):9.2f}")

# ------------------------------------------------- pick top 3 on TRAIN only
elig = [r for r in rows if r["train"].get("trades", 0) >= 100]
elig.sort(key=lambda r: r["train"]["expectancy"], reverse=True)
top3 = elig[:3]

print("\n=== TOP 3 BY TRAIN EXPECTANCY (>=100 train trades) — TEST read once ===")
for r in top3:
    print(f"{r['tf']} depth={r['depth']} tp={r['tp']} sl={r['sl_kind']}{r['sl_val']}")
    print("  train:", r["train"])
    print("  test :", r["test"])

# -------------------------------------- feed-spread worst case, best config only
feed_row = None
if top3:
    b = top3[0]
    idxs, sides = SIGSETS[(b["tf"], b["depth"])]
    intents = []
    for i, side in zip(idxs, sides):
        ref = mid_c[i]
        sl_pts = (float(np.clip(b["sl_val"] * ATR15[i], 2.0, 30.0))
                  if b["sl_kind"] == "atr" else b["sl_val"])
        tp = ref + b["tp"] if side == "buy" else ref - b["tp"]
        sl = ref - sl_pts if side == "buy" else ref + sl_pts
        intents.append(eng.OrderIntent(signal_i=i, side=side, tp=tp, sl=sl,
                                       max_hold_bars=MAX_HOLD, lot=0.10,
                                       entry_type="taker", tag="feed"))
    ffills = eng.simulate(df, intents, spread_model="feed")
    feed_row = eng.stats(df, ffills, "best_feed_spread")
    print("\n=== BEST CONFIG, spread_model='feed' (worst case) ===")
    print("  train:", feed_row.get("train_jan_apr"))
    print("  test :", feed_row.get("test_may_jul"))

path = eng.save_result("trend_pullback", {
    "family": "trend_pullback",
    "method": ("HTF EMA20/50 bias (M15/H1, resample->shift(1), causal); S5 pullback "
               "touch of shifted EMA20 (or EMA20 -/+ 0.25*ATR15) with close back on "
               "trend side; London+NY 06-20 UTC; taker entry next bar; TP fixed pts, "
               "SL fixed or ATR15-mult (clamp 2..30); max hold 8h; spread 0.20 + "
               "$4.9/lot; lot 0.10; cooldown 1 HTF bar; max_concurrent=1."),
    "grid": {"tf": ["15min", "1h"], "depth": [0.0, 0.25], "tp": TPS,
             "sl": [f"{k}{v}" for k, v in SLS]},
    "sweep": rows,
    "top3_by_train_expectancy": top3,
    "best_feed_spread": feed_row,
    "runtime_s": round(time.time() - T0, 1),
})
print(f"\nsaved -> {path}  ({time.time()-T0:.1f}s total)")
