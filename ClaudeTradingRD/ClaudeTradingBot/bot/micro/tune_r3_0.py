"""Fast tuner for strat_m1_r3_0: load train+OOS once, resample to M1 once, evaluate
many env-configs at the EXACT 0.25-taker PF in BOTH windows. Prints a ranked table.

Usage: .venv/Scripts/python.exe -m bot.micro.tune_r3_0
"""
import os
import importlib
import numpy as np
from .engine import Bars, simulate
from .features import resample_bars
from ..oanda_s5 import load

TRAIN = ("2024-01", "2025-07")
OOS = ("2025-08", "2026-06")
TF = 60
GAP = max(30, TF * 2 + 5)
SPREAD = 0.25  # primary judging spread, taker


def _synth(d, s):
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


def _bars_at(draw, s):
    ds = _synth(draw, s)
    ds = resample_bars(ds, TF)
    return Bars(ds)


print("loading data ...", flush=True)
d_tr = load(*TRAIN)
d_oos = load(*OOS)
# pre-build constant-spread M1 bars for the judging spread (taker adds slip=SPREAD)
btr = _bars_at(d_tr, SPREAD)
boos = _bars_at(d_oos, SPREAD)
print(f"train M1 bars={btr.n}  oos M1 bars={boos.n}", flush=True)


def evalcfg(cfg):
    for k, v in cfg.items():
        os.environ[k] = str(v)
    import bot.micro.strat_m1_r3_0 as m
    importlib.reload(m)
    base = dict(m.SIM); base["gap_sec"] = GAP
    tk = dict(base); tk["slippage_pts"] = tk.get("slippage_pts", 0.0) + SPREAD
    res = {}
    for tag, bb in (("tr", btr), ("oos", boos)):
        sig = m.generate(bb)
        rt = simulate(bb, sig, **tk)
        res[tag] = (rt["pf"], rt["net$"], rt["trades"], rt["wr"], rt["trades_per_day"])
    return res


def fmt(r):
    return f"PF={r[0]:.3f} net={r[1]:+7.1f} N={r[2]:4d} wr={r[3]:.0f} t/d={r[4]:.2f}"


def run(cfgs):
    rows = []
    for cfg in cfgs:
        r = evalcfg(cfg)
        rows.append((cfg, r))
        tr, oo = r["tr"], r["oos"]
        tag = "OK" if (tr[0] >= 1.15 and oo[0] >= 1.15 and tr[1] > 0 and oo[1] > 0) else "  "
        print(f"{tag} {str(cfg):70s} | TR {fmt(tr)} | OOS {fmt(oo)}", flush=True)
    return rows


if __name__ == "__main__":
    import sys
    # baseline + coarse sweeps; edit GRID below per round
    GRID = eval(sys.argv[1]) if len(sys.argv) > 1 else [{}]
    run(GRID)
