"""Is the 5s wall COST or SIGNAL? Re-price the closest candidates under a range
of synthetic CONSTANT spreads (keeping the real mid path) and report OOS PF/net.

If PF crosses >=1.3 at some achievable spread, the edge exists and the problem is
broker cost (fixable). If PF stays <1 even at near-zero spread, the signal itself
has no edge (unfixable).

Synthetic spread s: mid_x=(bid_x+ask_x)/2 preserved; bid=mid-s/2, ask=mid+s/2.
"""
import sys, json, importlib.util
import numpy as np
from bot.oanda_s5 import load
from bot.micro.engine import Bars, simulate

OOS = ("2025-08", "2026-06")
SPREADS = [0.00, 0.10, 0.20, 0.30, 0.45, 0.66]
CANDS = [
    ("bot/micro/strat_r2_5.py", "fvg_htf_reclaim_origin"),
    ("bot/micro/strat_r2_0.py", "asian_amd_maker_revert"),
    ("bot/micro/strat_r3_1.py", "micro_bos_cont_maker"),
]


def load_mod(path):
    spec = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def synth(d, s):
    """Return a dict-like with constant spread s around the real mid OHLC."""
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


d = load(*OOS)
print(f"OOS {OOS[0]}..{OOS[1]}  spread sensitivity (constant synthetic spread around real mid)\n")
for path, name in CANDS:
    mod = load_mod(path)
    # real variable-spread baseline
    rb = simulate(Bars(d), mod.generate(Bars(d)), **mod.SIM)
    print(f"{name}   [real variable spread: PF {rb['pf']:.2f} net ${rb['net$']:+.0f} "
          f"WR {rb['wr']:.0f}% n={rb['trades']} t/day {rb['trades_per_day']:.1f}]")
    print(f"  {'spread':>7} {'PF':>6} {'net$':>8} {'WR%':>5} {'trades':>7} {'exp$':>7}")
    for s in SPREADS:
        b = Bars(synth(d, s))
        r = simulate(b, mod.generate(b), **mod.SIM)
        flag = "  <-- PF>=1.3" if r["pf"] >= 1.3 else ("  break-even" if r["pf"] >= 1.0 else "")
        print(f"  {s:>7.2f} {r['pf']:>6.2f} {r['net$']:>+8.0f} {r['wr']:>5.0f} {r['trades']:>7} {r['exp$']:>+7.3f}{flag}")
    print()
