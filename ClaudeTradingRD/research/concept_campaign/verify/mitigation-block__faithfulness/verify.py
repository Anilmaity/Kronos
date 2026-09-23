"""Faithfulness/robustness verification of mitigation-block reading a (EDGE +0.022R).

Scratch only: nothing is written with write_result. Re-implements detect_a with its
knobs exposed (break/live/trend lengths, stop buffer, break-by-close, trend gate on/off)
and runs trade_test on each variant with the same harness defaults.
"""
import importlib.util
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl          # noqa: E402
import _batch_common as bc        # noqa: E402

m1 = cl.load_m1()
b = bc.bars(m1)
o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
n = len(b)
TD = pd.Timedelta(minutes=15)
rng_ = pd.Series(h - l)
atr96 = rng_.rolling(96, min_periods=20).mean().to_numpy()   # past-only incl. bar j

legs = bc.displacement_legs(b)
TREND = {}


def tdir_for(tb):
    if tb not in TREND:
        bc.TREND_BARS = tb
        TREND[tb] = bc.trend_state(b, legs)[0]
        bc.TREND_BARS = 24
    return TREND[tb]


def detect(break_bars=16, live_bars=16, trend_bars=24, buf_atr=0.0, trend=True,
           break_close=False, entry="open", flip=False):
    if trend:
        tdir = tdir_for(trend_bars)
        cand = np.flatnonzero(((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o)))
        dirs = tdir[cand]
    else:   # placebo: every opposing candle, direction = the side its near extreme breaks
        cand = np.flatnonzero(c != o)
        dirs = np.where(c[cand] > o[cand], -1, 1)
    rows = []
    for j, d in zip(cand, dirs):
        end = min(n, j + 1 + break_bars)
        if d == -1:
            ref = c if break_close else l
            brk = np.flatnonzero(ref[j + 1:end] < l[j])
        else:
            ref = c if break_close else h
            brk = np.flatnonzero(ref[j + 1:end] > h[j])
        if len(brk) == 0:
            continue
        k = j + 1 + int(brk[0])
        seg = c[j + 1:k + 1]
        if (d == -1 and (seg > h[j]).any()) or (d == 1 and (seg < l[j]).any()):
            continue
        far = h[j] if d == -1 else l[j]
        a = atr96[j] if np.isfinite(atr96[j]) else 0.0
        stop = far - d * buf_atr * a
        lvl = o[j] if entry == "open" else np.nan
        rows.append((j, k, d, lvl, stop))
    r = pd.DataFrame(rows, columns=["j", "k", "d", "lvl", "stop"])
    if entry == "break":   # "take the break of it with a stop there": enter at the break bar close
        t = ct[r["k"].to_numpy()]
        ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": r["d"].to_numpy(),
                           "stop_px": r["stop"].to_numpy(), "rr": 2.0})
        return bc.finish(ev)
    start = ct[r["k"].to_numpy()]
    until = start + live_bars * TD
    hit, dt = bc.touch_sided(m1, start, r["lvl"].to_numpy(), r["d"].to_numpy(), until)
    r = r[hit].assign(dt=dt[hit])
    dd = r["d"].to_numpy()
    stop = r["stop"].to_numpy()
    if flip:   # opposite direction, same stop distance mirrored (direction placebo)
        dd = -dd
        stop = 2 * r["lvl"].to_numpy() - stop
    ev = pd.DataFrame({"decision_time": pd.DatetimeIndex(r["dt"]),
                       "available_at": pd.DatetimeIndex(r["dt"]),
                       "direction": dd, "stop_px": stop, "rr": 2.0})
    ev = ev.iloc[::-1]
    return bc.finish(ev)


def summarize(name, res):
    tr = res.get("_trades")
    out = {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict")}
    out["H1"] = res["halves"]["H1"]["diff"]
    out["H2"] = res["halves"]["H2"]["diff"]
    out["blocks"] = [round(v["diff"], 4) for v in res["blocks"].values()]
    out["blocks_p"] = [round(v["p"], 3) for v in res["blocks"].values()]
    out["ctrl_overlap"] = res.get("ctrl_overlap")
    out["ties"] = res.get("ties")
    if tr is not None:
        r5 = tr["net_R_5050"].to_numpy() - tr["ctrl_mean_R_5050"].to_numpy()
        out["diff_5050"] = float(np.nanmean(r5))
        dd = tr["net_R"].to_numpy() - tr["ctrl_mean_R"].to_numpy()
        yr = pd.DatetimeIndex(tr["decision_time"]).year
        out["by_year"] = {int(y): round(float(np.nanmean(dd[yr == y])), 4) for y in sorted(set(yr))}
    print(name, json.dumps(out, default=str))
    sys.stdout.flush()
    return out


variants = {
    "repro": dict(),
    "break8": dict(break_bars=8), "break32": dict(break_bars=32),
    "live8": dict(live_bars=8), "live32": dict(live_bars=32),
    "trend12": dict(trend_bars=12), "trend48": dict(trend_bars=48),
    "buf0.1atr": dict(buf_atr=0.1), "buf0.25atr": dict(buf_atr=0.25),
    "break_by_close": dict(break_close=True),
    "entry_at_break": dict(entry="break"),
    "NO_TREND_placebo": dict(trend=False),
    "FLIP_direction": dict(flip=True),
}
which = sys.argv[1:] or list(variants)
results = {}
for name in which:
    ev = detect(**variants[name])
    if name == "repro":
        ref = cl.cache_frame  # noqa
        print("repro fp", cl.frame_fingerprint(ev), "expected 58bb3e63da0c1509", len(ev))
    res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
    results[name] = summarize(name, res)
    if name == "repro":
        res2 = cl.trade_test(ev, max_hold="150min", ctrl_tod_tol_min=30)
        results["repro_tod30"] = summarize("repro_tod30", res2)
        res3 = cl.trade_test(ev, max_hold="150min", hold_basis="bars")
        results["repro_bars"] = summarize("repro_bars", res3)
json.dump(results, open(__file__.replace("verify.py", f"out_{'_'.join(which)[:60]}.json"), "w"),
          default=str, indent=1)
