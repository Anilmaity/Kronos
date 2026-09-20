"""Fast frontier scan for the retest-family freq push. Monkeypatches the strat
globals, reuses loaded OOS bars, prints OOS trades + 0.20/0.30 taker PF per config.
Not part of the deliverable; a scan tool only."""
import itertools
import numpy as np
from bot.micro.engine import Bars, simulate
from bot.oanda_s5 import load
import bot.micro.strat_mb_r2_2 as S

OOS = ("2025-08", "2026-06")
draw = load(*OOS)


def synth(d, s):
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


bars = {s: Bars(synth(draw, s)) for s in (0.20, 0.30)}


def evaluate(**params):
    for k, v in params.items():
        setattr(S, k, v)
    row = {}
    for s in (0.20, 0.30):
        b = bars[s]
        sig = S.generate(b)
        km = dict(S.SIM); km["slippage_pts"] = km.get("slippage_pts", 0.0) + s
        rt = simulate(b, sig, **km)
        row[s] = (rt["trades"], round(rt["pf"], 3), round(rt["net$"], 1), round(rt["wr"], 1))
    return row


def show(tag, **p):
    r = evaluate(**p)
    n20, pf20, net20, wr20 = r[0.20]
    n30, pf30, net30, wr30 = r[0.30]
    pf25 = round((pf20 + pf30) / 2, 3)
    flag = "PASS" if (n20 >= 100 and pf25 >= 1.3 and pf30 > 1.0) else ""
    print(f"{tag:42s} N20={n20:4d} pf20={pf20:5.3f} pf30={pf30:5.3f} ~pf25={pf25:5.3f} "
          f"net20={net20:7.1f} wr20={wr20:4.1f} {flag}")


if __name__ == "__main__":
    SESS_WIDE = tuple(range(6, 17))
    SESS_ALL = tuple(range(0, 24))
    base_sess = (7,8,9,10,11,12,13,14,15)
    show("base MULTI(80) K1.8 sess7-15", MULTI_LB=(80,), K_DISP=1.8, LADDER=False, SESSION_HOURS=base_sess)
    print("-- multi-lookback union @K1.8 (quality fixed) --")
    for mlb in [(40,80,160), (40,80,160,320), (30,60,120,240), (50,100,200), (40,120), (60,180)]:
        show(f"MULTI{mlb} K1.8", MULTI_LB=mlb, K_DISP=1.8, LADDER=False, SESSION_HOURS=base_sess)
    print("-- multi-lb + wider sessions --")
    for mlb in [(40,80,160), (30,60,120,240)]:
        show(f"MULTI{mlb} K1.8 sess6-16", MULTI_LB=mlb, K_DISP=1.8, LADDER=False, SESSION_HOURS=SESS_WIDE)
        show(f"MULTI{mlb} K1.8 sessALL", MULTI_LB=mlb, K_DISP=1.8, LADDER=False, SESSION_HOURS=SESS_ALL)
    print("-- multi-lb + ladder --")
    for mlb in [(40,80,160), (30,60,120,240)]:
        show(f"MULTI{mlb} K1.8 ladder", MULTI_LB=mlb, K_DISP=1.8, LADDER=True, SESSION_HOURS=base_sess)
    print("-- higher K confirm edge concentration --")
    for k in (1.8, 2.0, 2.3, 2.6):
        show(f"MULTI(40,80,160) K{k}", MULTI_LB=(40,80,160), K_DISP=k, LADDER=False, SESSION_HOURS=base_sess)
    print("-- (K, RETR-depth) grid LB80: lower K + deeper breaker entry --")
    for k in (1.8, 1.5, 1.2, 1.0):
        for rr in (0.30, 0.55, 0.80, 1.00, 1.20):
            show(f"K{k} RETR{rr}", MULTI_LB=(80,), K_DISP=k, RETR1=rr, LADDER=False, SESSION_HOURS=base_sess)
    print("-- best deep-entry + tighter SL (deeper entry => tighter invalidation) --")
    for k in (1.4, 1.2):
        for sl in (3.0, 4.0):
            show(f"K{k} RETR1.0 SL{sl}", MULTI_LB=(80,), K_DISP=k, RETR1=1.0, SL_PTS=sl, LADDER=False, SESSION_HOURS=base_sess)
