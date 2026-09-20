"""Evaluate a microstructure strategy module across train/OOS cached months,
with a 1.5x-cost stress pass, and print JSON. This is the single scoring path
every candidate strategy is judged by — keeps results comparable & honest.

A strategy module must expose:
    generate(b: Bars) -> Signals
    SIM  = dict(...)     # kwargs forwarded to engine.simulate (commission, maxhold, ...)
    NAME = "label"

Usage:
    python -m bot.micro.runner bot/micro/strat_xyz.py
    python -m bot.micro.runner bot/micro/strat_xyz.py --train 2024-01:2025-12 --oos 2026-01:2026-06
By default: auto-discover cached months, earliest 65% = train, latest 35% = OOS.
"""
import sys
import json
import os
import importlib.util
import numpy as np
from .engine import Bars, simulate, runs
from .features import resample_bars
from ..oanda_s5 import S5_DIR, load


def _prep(mod, d):
    """Build Bars at the strategy's timeframe (TF seconds; default 5 = raw S5) and
    the matching gap threshold so the engine never spans a session break."""
    tf = int(getattr(mod, "TF", 5))
    if tf > 5:
        d = resample_bars(d, tf)
    gap = max(30, tf * 2 + 5)
    return Bars(d), gap


def _cached_months():
    fs = sorted(f for f in os.listdir(S5_DIR) if f.endswith(".npz"))
    return [f[len("xau_s5_"):-len(".npz")] for f in fs]  # 'YYYY-MM'


def _load_strat(path):
    spec = importlib.util.spec_from_file_location("strat_mod", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _synth(d, s):
    """Constant synthetic spread s around the real mid path (for cost sensitivity)."""
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


def _run_window(mod, a, b_, extra_slip=0.0):
    """Run strategy over cached months [a..b_] joined; split into gap-free runs so
    no trade spans a weekend. Returns combined metrics dict."""
    d = load(a, b_)
    bars, gap = _prep(mod, d)
    sim_kw = dict(mod.SIM)
    sim_kw.setdefault("gap_sec", gap)
    if extra_slip:
        sim_kw["slippage_pts"] = sim_kw.get("slippage_pts", 0.0) + extra_slip
    sig = mod.generate(bars)
    return simulate(bars, sig, **sim_kw)


def _spread_grid(mod, a, b_, spreads=(0.20, 0.30)):
    """Re-price OOS at realistic CONSTANT spreads, in maker (as-is) and taker
    (cross the spread) modes. The 0.66 OANDA-practice feed is unrealistically wide;
    this shows whether the edge is real at an achievable broker spread."""
    d = load(a, b_)
    tf = int(getattr(mod, "TF", 5))
    gap = max(30, tf * 2 + 5)
    out = {}
    for s in spreads:
        ds = _synth(d, s)
        if tf > 5:
            ds = resample_bars(ds, tf)
        b = Bars(ds)
        sig = mod.generate(b)
        base = dict(mod.SIM); base.setdefault("gap_sec", gap)
        rk = simulate(b, sig, **base)
        km = dict(base); km["slippage_pts"] = km.get("slippage_pts", 0.0) + s
        rt = simulate(b, sig, **km)
        out[f"{s:.2f}"] = {
            "maker": {"pf": round(rk["pf"], 3), "net$": round(rk["net$"], 1),
                       "wr": round(rk["wr"], 1), "trades": rk["trades"]},
            "taker": {"pf": round(rt["pf"], 3), "net$": round(rt["net$"], 1),
                       "wr": round(rt["wr"], 1), "trades": rt["trades"]},
        }
    return out


def _yearly(b: Bars, res):
    out = {}
    for t in res["tlist"]:
        y = int(__import__("datetime").datetime.utcfromtimestamp(b.ts[t[0]]).year)
        out.setdefault(y, [0, 0.0])
        out[y][0] += 1
        out[y][1] += (t[7])  # pts
    return {k: {"n": v[0], "pts": round(v[1], 1)} for k, v in sorted(out.items())}


def summarize(res):
    keep = ("trades", "wr", "pf", "exp_R", "exp$", "net$", "maxDD$",
            "avgwin$", "avgloss$", "trades_per_day", "days", "avg_min")
    return {k: (round(res[k], 3) if isinstance(res.get(k), float) else res.get(k))
            for k in keep}


def main():
    path = sys.argv[1]
    months = _cached_months()
    train = oos = None
    if "--train" in sys.argv:
        train = sys.argv[sys.argv.index("--train") + 1].split(":")
    if "--oos" in sys.argv:
        oos = sys.argv[sys.argv.index("--oos") + 1].split(":")
    if train is None:
        cut = max(1, int(len(months) * 0.65))
        train = [months[0], months[cut - 1]]
        oos = [months[cut], months[-1]] if cut < len(months) else [months[-1], months[-1]]

    mod = _load_strat(path)
    out = {"name": getattr(mod, "NAME", os.path.basename(path)),
           "train_window": train, "oos_window": oos, "months_cached": len(months)}

    rtr = _run_window(mod, train[0], train[1])
    out["train"] = summarize(rtr)
    if oos:
        roos = _run_window(mod, oos[0], oos[1])
        out["oos"] = summarize(roos)
        rstress = _run_window(mod, oos[0], oos[1], extra_slip=0.33)  # ~1.5x median spread
        out["oos_stress"] = summarize(rstress)
        out["oos_spread_grid"] = _spread_grid(mod, oos[0], oos[1])  # cost-sensitivity 0.20/0.30
        out["train_spread_grid"] = _spread_grid(mod, train[0], train[1])  # regime-robustness check
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
