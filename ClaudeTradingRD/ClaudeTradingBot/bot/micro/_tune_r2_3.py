"""Fast OOS-only spread-grid tuner for strat_mb_r2_3 (mirrors runner._spread_grid).
Loads ONLY the OOS window so a config evaluates in a few seconds."""
import sys, os, importlib, json
import numpy as np
from bot.micro.engine import Bars, simulate
from bot.oanda_s5 import load

OOS = ("2025-08", "2026-06")


def _synth(d, s):
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


def main():
    d = load(*OOS)
    import bot.micro.strat_mb_r2_3 as m
    importlib.reload(m)
    rows = {}
    # practice-feed count
    b0 = Bars(d)
    r0 = simulate(b0, m.generate(b0), **m.SIM)
    for s in (0.20, 0.30):
        b = Bars(_synth(d, s))
        sig = m.generate(b)
        rk = simulate(b, sig, **m.SIM)
        km = dict(m.SIM); km["slippage_pts"] = km.get("slippage_pts", 0.0) + s
        rt = simulate(b, sig, **km)
        rows[f"{s:.2f}"] = dict(mk_pf=round(rk["pf"], 3), tk_pf=round(rt["pf"], 3),
                                tk_net=round(rt["net$"], 1), n=rt["trades"], wr=round(rt["wr"], 1))
    pf25 = (rows["0.20"]["tk_pf"] + rows["0.30"]["tk_pf"]) / 2
    tag = os.environ.get("TAG", "")
    print(json.dumps(dict(tag=tag, oosN=r0["trades"], td=round(r0["trades_per_day"], 2),
                          gridN=rows["0.20"]["n"], pf25=round(pf25, 3),
                          t20=rows["0.20"]["tk_pf"], t30=rows["0.30"]["tk_pf"],
                          t30net=rows["0.30"]["tk_net"], wr20=rows["0.20"]["wr"],
                          mk20=rows["0.20"]["mk_pf"])))


if __name__ == "__main__":
    main()
