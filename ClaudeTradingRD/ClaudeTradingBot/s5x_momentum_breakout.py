"""s5x_momentum_breakout.py — CONTROL family: fast momentum-continuation on XAUUSD 2026 S5.

Two sub-variants, both entering WITH the move (taker, next-bar open):
  (A) burst : k-sigma continuation. On M1 closes, ret_W = c[j]-c[j-W] (W = 1/3/5 min).
              z = ret_W / rolling_std(ret_W, 120 M1 bars).shift(1).  Fresh cross of |z|>=k fires
              a trade in the direction of the burst.
  (B) brk   : M1-close breakout of the prior N-bar high/low (N = 60/120/240 M1 bars).
              Fresh breakouts only (previous close was NOT beyond its own prior-N extreme).

SL: fixed 3.0 pts, or ATR-based clip(3*ATR14_M1, 2, 5).  TP = R * SL (R in 1/2/3).
Max hold 2880 S5 bars (4h) -> hard time exit.  Optional session filter 07-17 UTC (London+NY).

Method rules honoured:
  * All features computed on COMPLETED M1 bars (resampled from S5 mid); the signal index is the
    last S5 bar inside that M1 bar, so engine execution (signal_i+1) starts at/after the M1 close.
  * Sweep selection on train_jan_apr ONLY; test read once at the end for the top <=3.
  * Everything runs through eng.simulate at spread_model=0.20; best config re-run once at 'feed'.
"""
from __future__ import annotations

import time as _time

import numpy as np
import pandas as pd

import s5_engine as eng

MAX_HOLD = 2880          # 4 h in S5 bars
SIGMA_LOOKBACK = 120     # M1 bars for burst sigma
ATR_LEN = 14
LOT = 0.10


def build_features(df: pd.DataFrame):
    m1 = eng.resample(df, "1min")                      # completed M1 bars, mid price
    m1 = m1.reset_index().rename(columns={"time": "t"})
    c = m1["c"].values
    h = m1["h"].values
    l = m1["l"].values

    # map each M1 close (t + 60s) -> S5 signal index (last S5 bar before the close)
    s5_t = df["time"].values
    close_t = m1["t"].values + np.timedelta64(60, "s")
    entry_start = np.searchsorted(s5_t, close_t, side="left")   # first S5 bar at/after close
    signal_i = entry_start - 1
    valid_map = (entry_start < len(s5_t)) & (signal_i >= 0)

    # ATR14 on M1 (causal: uses completed bars up to and incl. j)
    prev_c = np.roll(c, 1); prev_c[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr = pd.Series(tr).rolling(ATR_LEN).mean().values

    hour = pd.to_datetime(close_t).hour.values          # hour of the M1 CLOSE (decision time)

    feats = {"m1": m1, "c": c, "h": h, "l": l, "atr": atr, "hour": hour,
             "signal_i": signal_i, "valid_map": valid_map}

    # burst z-scores per window
    feats["z"] = {}
    for W in (1, 3, 5):
        ret = pd.Series(c).diff(W)
        sig = ret.rolling(SIGMA_LOOKBACK).std().shift(1)
        z = (ret / sig).values
        feats["z"][W] = z

    # breakout levels per N: prior-N-bar extreme (excluding current bar)
    feats["hi"] = {}; feats["lo"] = {}
    for N in (60, 120, 240):
        feats["hi"][N] = pd.Series(h).rolling(N).max().shift(1).values
        feats["lo"][N] = pd.Series(l).rolling(N).min().shift(1).values
    return feats


def sl_points(mode: str, atr_j: float) -> float:
    if mode == "fix3":
        return 3.0
    return float(np.clip(3.0 * atr_j, 2.0, 5.0))        # 'atr'


def gen_intents(df, F, cfg) -> list:
    c, atr, hour = F["c"], F["atr"], F["hour"]
    sig_i, vmap = F["signal_i"], F["valid_map"]
    n = len(c)
    if cfg["kind"] == "burst":
        z = F["z"][cfg["W"]]
        k = cfg["k"]
        zb = np.nan_to_num(z, nan=0.0)
        buy = (zb >= k) & (np.roll(zb, 1) < k)
        sell = (zb <= -k) & (np.roll(zb, 1) > -k)
    else:
        hi, lo = F["hi"][cfg["N"]], F["lo"][cfg["N"]]
        above = np.nan_to_num(c > hi, nan=False)
        below = np.nan_to_num(c < lo, nan=False)
        buy = above & ~np.roll(above, 1)
        sell = below & ~np.roll(below, 1)
    buy[0] = sell[0] = False

    mask = vmap & ~np.isnan(atr)
    if cfg.get("session"):
        mask &= (hour >= 7) & (hour < 17)

    intents = []
    for j in np.nonzero((buy | sell) & mask)[0]:
        sl_pts = sl_points(cfg["sl"], atr[j])
        px = c[j]
        long = bool(buy[j])
        tp = px + cfg["R"] * sl_pts if long else px - cfg["R"] * sl_pts
        sl = px - sl_pts if long else px + sl_pts
        intents.append(eng.OrderIntent(
            signal_i=int(sig_i[j]), side="buy" if long else "sell",
            tp=round(tp, 3), sl=round(sl, 3), max_hold_bars=MAX_HOLD, lot=LOT,
            entry_type="taker", tag=cfg["name"]))
    return intents


def main():
    t0 = _time.time()
    df = eng.load_s5()
    print(f"loaded {len(df):,} S5 bars in {_time.time()-t0:.1f}s")
    F = build_features(df)
    print(f"features built ({_time.time()-t0:.1f}s)")

    configs = []
    # (B) breakout: 3 N x 2 sl x 3 R = 18
    for N in (60, 120, 240):
        for sl in ("fix3", "atr"):
            for R in (1, 2, 3):
                configs.append({"kind": "brk", "N": N, "sl": sl, "R": R, "session": False,
                                "name": f"brk_N{N}_{sl}_R{R}"})
    # (A) burst: 3 W x 2 k x 3 R (sl fixed 3) = 18
    for W in (1, 3, 5):
        for k in (3.0, 4.0):
            for R in (1, 2, 3):
                configs.append({"kind": "burst", "W": W, "k": k, "sl": "fix3", "R": R,
                                "session": False, "name": f"burst_W{W}_k{k}_R{R}"})
    # session-filtered variants: breakout N=120 (2 sl x 3 R = 6) + burst W=3,k=3 (3 R)
    for sl in ("fix3", "atr"):
        for R in (1, 2, 3):
            configs.append({"kind": "brk", "N": 120, "sl": sl, "R": R, "session": True,
                            "name": f"brk_N120_{sl}_R{R}_sess"})
    for R in (1, 2, 3):
        configs.append({"kind": "burst", "W": 3, "k": 3.0, "sl": "fix3", "R": R,
                        "session": True, "name": f"burst_W3_k3.0_R{R}_sess"})
    print(f"{len(configs)} configs")

    rows = []
    for i, cfg in enumerate(configs):
        intents = gen_intents(df, F, cfg)
        fills = eng.simulate(df, intents, spread_model=0.20)
        s = eng.stats(df, fills, cfg["name"])
        params = {kk: cfg[kk] for kk in cfg if kk != "name"}
        rows.append({"name": cfg["name"], "params": params, "n_intents": len(intents),
                     "full": s.get("full", {}), "train": s.get("train_jan_apr", {}),
                     "test": s.get("test_may_jul", {})})
        tr = s.get("train_jan_apr", {})
        print(f"[{i+1:2d}/{len(configs)}] {cfg['name']:26s} intents={len(intents):5d} "
              f"train: n={tr.get('trades',0):4d} wr={tr.get('win_rate',0):5.1f} "
              f"net={tr.get('net',0):9.2f} exp={tr.get('expectancy',0):7.3f} "
              f"({_time.time()-t0:.0f}s)")

    # ---- TRAIN-only selection: top 3 by train expectancy, >=100 train trades ----
    eligible = [r for r in rows if r["train"].get("trades", 0) >= 100]
    eligible.sort(key=lambda r: r["train"].get("expectancy", -1e9), reverse=True)
    top3 = eligible[:3]
    print("\nTOP-3 by TRAIN expectancy (>=100 train trades) — TEST read once, verbatim:")
    for r in top3:
        print(f"  {r['name']:26s} train exp={r['train']['expectancy']:.3f} "
              f"wr={r['train']['win_rate']} net={r['train']['net']} | "
              f"TEST n={r['test'].get('trades',0)} wr={r['test'].get('win_rate',0)} "
              f"net={r['test'].get('net',0)} exp={r['test'].get('expectancy',0)}")

    # feed-spread worst-case for the single best config only
    feed = None
    if top3:
        best_cfg = next(cconf for cconf in configs if cconf["name"] == top3[0]["name"])
        fills = eng.simulate(df, gen_intents(df, F, best_cfg), spread_model="feed")
        feed = eng.stats(df, fills, top3[0]["name"] + "_feed")
        print(f"\nfeed-spread robustness for {top3[0]['name']}: "
              f"full net={feed['full'].get('net')} test net={feed['test_may_jul'].get('net')}")

    payload = {
        "family": "momentum_breakout",
        "method": {"spread_model": 0.20, "commission_rt": eng.COMMISSION_PER_LOT_RT,
                   "lot": LOT, "max_hold_bars": MAX_HOLD, "entry": "taker next-bar open",
                   "selection": "train expectancy, >=100 train trades",
                   "sigma_lookback_m1": SIGMA_LOOKBACK, "atr_len_m1": ATR_LEN},
        "sweep": rows,
        "top3_train": [r["name"] for r in top3],
        "feed_spread_best": feed,
    }
    path = eng.save_result("momentum_breakout", payload)
    print(f"\nsaved -> {path}  ({_time.time()-t0:.0f}s total)")


if __name__ == "__main__":
    main()
