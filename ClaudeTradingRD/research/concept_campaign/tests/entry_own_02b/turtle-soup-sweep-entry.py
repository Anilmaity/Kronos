"""turtle-soup-sweep-entry (contested) — batch entry_own_02b.

NgFIza9qsGQ: inside a bearish trend, price reaches up into a marked high.
  reading a (confident): short INTO the raid, above the high, with a FIXED stop.
  reading b (conservative): wait for the close back into the range, enter on that
            close with the stop on the high (the sweep extreme).
Both target the opposing side (the last confirmed swing low). Bullish mirrors.

Trend (15m, fractal 2/2 swings confirmed): last two swing highs descending AND last
two swing lows descending (bearish); mirror for bullish. The marked high is the most
recent confirmed swing high, not yet traded through. One attempt per marked level.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from _common import M1, bars_with_swings, to_ts, ONE_MIN     # noqa: E402

TF = "15min"
ATR_N = 14
FIXED_STOP_ATR = 0.5
MAX_HOLD = "5h"
COLS_A = ["decision_time", "available_at", "direction", "stop_dist", "target_px"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def _events(m1: pd.DataFrame, mode: str) -> pd.DataFrame:
    cols = COLS_A if mode == "a" else COLS_B
    if len(m1) < 500:
        return pd.DataFrame(columns=cols)
    b, d = bars_with_swings(m1, TF, 2, 2)
    o, h, l, c, ct, st = d["o"], d["h"], d["l"], d["c"], d["ct"], d["st"]
    n = len(h)
    tr = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    tr = np.concatenate([[h[0] - l[0]], tr])
    atr = pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    m = M1(m1)
    rows = []
    sh_list, sl_list = [], []          # confirmed swings (price) in order
    live_hi = live_lo = None           # marked level still untouched
    for j in range(n):
        # 1) the bar j trades against the currently marked levels (known before j)
        if len(sh_list) >= 2 and len(sl_list) >= 2:
            bear = sh_list[-1] < sh_list[-2] and sl_list[-1] < sl_list[-2]
            bull = sh_list[-1] > sh_list[-2] and sl_list[-1] > sl_list[-2]
        else:
            bear = bull = False
        for side in ("hi", "lo"):
            lvl = live_hi if side == "hi" else live_lo
            if lvl is None:
                continue
            raided = h[j] > lvl if side == "hi" else l[j] < lvl
            if not raided:
                continue
            trend_ok = bear if side == "hi" else bull
            direction = -1 if side == "hi" else 1
            target = (sl_list[-1] if side == "hi" else sh_list[-1]) if trend_ok else np.nan
            geom_ok = trend_ok and ((target < lvl) if side == "hi" else (target > lvl))
            if trend_ok and geom_ok and j >= 1 and np.isfinite(atr[j - 1]):
                if mode == "a":
                    i0 = int(np.searchsorted(m.t, st[j], "left"))
                    i1 = int(np.searchsorted(m.t, ct[j], "left"))
                    seg = (m.h[i0:i1] > lvl) if side == "hi" else (m.l[i0:i1] < lvl)
                    if seg.any():
                        k = i0 + int(np.argmax(seg))
                        rows.append((m.t[k] + ONE_MIN, direction, FIXED_STOP_ATR * atr[j - 1], target))
                else:
                    back_in = c[j] <= lvl if side == "hi" else c[j] >= lvl
                    if back_in and ct[j] <= (m.t[-1] + ONE_MIN):
                        rows.append((ct[j], direction, h[j] if side == "hi" else l[j], target))
            if side == "hi":
                live_hi = None
            else:
                live_lo = None
        # 2) swings confirmed by bar j's close become known after it
        q = j - 2
        if q >= 0 and d["sh"][q]:
            sh_list.append(h[q])
            live_hi = h[q] if h[q] >= h[q + 1:j + 1].max() else None
        if q >= 0 and d["sl"][q]:
            sl_list.append(l[q])
            live_lo = l[q] if l[q] <= l[q + 1:j + 1].min() else None
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["t", "direction", "x", "target_px"])
    out = out.drop_duplicates(["t", "direction"]).sort_values("t").reset_index(drop=True)
    dec = to_ts(out["t"])
    res = pd.DataFrame({"decision_time": dec, "available_at": dec,
                        "direction": out["direction"].to_numpy()})
    res["stop_dist" if mode == "a" else "stop_px"] = out["x"].to_numpy()
    res["target_px"] = out["target_px"].to_numpy()
    return res


def detect_a(m1):
    return _events(m1, "a")


def detect_b(m1):
    return _events(m1, "b")


OP_COMMON = [
    "15m bars; fractal swings 2/2, known at the 2nd right bar's close",
    "trend: bearish = last two confirmed swing highs AND lows descending (bullish mirror)",
    "marked level = most recent confirmed swing high (bearish trend) not yet traded through; one attempt per level",
    "target = the last confirmed swing low (opposing side), required to lie beyond the marked level; max hold 5h"]
OP_A = {"rules": OP_COMMON + [
    "reading a: short INTO the raid — decide at the first M1 bar trading above the marked high, enter next M1 open",
    "fixed stop = 0.5 x ATR(14) of the last completed 15m bar from entry"],
    "params": {"tf": TF, "swing": "2/2", "fixed_stop_atr": FIXED_STOP_ATR, "atr_n": ATR_N,
               "max_hold": MAX_HOLD, "ctrl_tod_tol_min": 30}}
OP_B = {"rules": OP_COMMON + [
    "reading b: the 15m bar that raided the high must CLOSE back below it (a close beyond = break, no trade); "
    "decide at that close, stop on that bar's high (the sweep extreme)"],
    "params": {"tf": TF, "swing": "2/2", "max_hold": MAX_HOLD, "ctrl_tod_tol_min": 30}}
SRC = {"tf": "corpus: YAML timeframes htf [15m, 5m]",
       "swing": "phase3: locked fractal 2/2",
       "fixed_stop_atr": "declared-before-run: corpus gives only 'a FIXED stop loss' / 'tight' with no distance",
       "atr_n": "declared-before-run: conventional ATR(14)",
       "max_hold": "declared-before-run: 20 structure bars",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9"}

if __name__ == "__main__":
    for rd, fn, op in (("a", detect_a, OP_A), ("b", detect_b, OP_B)):
        ev = cl.cache_frame(f"turtle_15m_{rd}", lambda fn=fn: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="20D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                       "exposure_bars", "ties", "ctrl_overlap", "sanity")})
        src = {k: v for k, v in SRC.items() if k in op["params"]}
        cl.write_result("turtle-soup-sweep-entry", rd, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=("Reading a: confident variant, sell into the raid with a fixed 0.5 ATR stop."
                               if rd == "a" else
                               "Reading b: conservative variant, enter on the close back inside, stop on the raid high.")
                        + " 'All timeframes aligned' approximated by the 15m trend only.")
