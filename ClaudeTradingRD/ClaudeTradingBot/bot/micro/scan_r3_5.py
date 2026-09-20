"""Fast sweep for strat_m1_r3_5. KEY OPTIMISATION: generate() signals depend only on the
MID path (bias/FVG/atr all from mid), which is identical across synthetic spreads. So we
resample each window's synthetic bid/ask ONCE per spread, and per param combo do just
generate (once) + two cheap simulates (0.20 & 0.30 taker). Prints configs positive at
~0.25 taker in BOTH windows, ranked by min(train,oos) ~0.25 taker PF.
"""
import itertools, numpy as np
import bot.micro.strat_m1_r3_5 as S
from bot.micro.engine import Bars, simulate
from bot.micro.features import resample_bars
from bot.oanda_s5 import load

TF = S.TF
TRAIN = ("2024-01", "2025-07")
OOS = ("2025-08", "2026-06")
GAP = max(30, TF * 2 + 5)


def _synth(d, s):
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


def prep(d):
    out = {}
    for s in (0.20, 0.30):
        out[s] = Bars(resample_bars(_synth(d, s), TF))
    return out


def eval_window(bw, sim_over):
    b20 = bw[0.20]; b30 = bw[0.30]
    sig = S.generate(b20)               # mid identical across spreads -> one generate
    base = dict(S.SIM); base["gap_sec"] = GAP; base.update(sim_over)
    r20 = simulate(b20, sig, **dict(base, slippage_pts=0.20))
    r30 = simulate(b30, sig, **dict(base, slippage_pts=0.30))
    t025 = 0.5 * (r20["pf"] + r30["pf"])
    return {"t025": t025, "pf20": r20["pf"], "pf30": r30["pf"],
            "n": r20["trades"], "wr": r20["wr"], "net20": r20["net$"]}


def main():
    dtr = load(*TRAIN); doos = load(*OOS)
    days_oos = len(np.unique(doos["ts"] // 86400))
    btr = prep(dtr); boos = prep(doos)

    grid = {
        "GAP_MIN": [1.6, 2.2, 2.8],
        "PEN": [0.3, 0.5, 0.7],
        "BUF_ATR": [0.3, 0.5],
        "RR": [0.0],                 # 0 = trail-only exit (the proven edge mechanism)
        "HOURS": [(7, 8, 9, 10, 11, 12, 13, 14), (7, 8, 12, 13, 14)],
        "_TRAIL": [0.8, 1.2, 1.6],
        "_MAXHOLD": [60, 120],
    }
    keys = list(grid)
    results = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        d = dict(zip(keys, combo))
        sim_over = {"trail_pts": d.pop("_TRAIL"), "maxhold": d.pop("_MAXHOLD")}
        S.P = d
        rtr = eval_window(btr, sim_over); roos = eval_window(boos, sim_over)
        P = dict(d); P.update(sim_over)
        results.append((min(rtr["t025"], roos["t025"]), rtr, roos, P))
    results.sort(key=lambda x: -x[0])
    print(f"OOS days~{days_oos}  configs={len(results)}")
    for mintr, rtr, roos, P in results[:20]:
        td = roos["n"] / max(days_oos, 1)
        ok = (rtr["t025"] >= 1.15 and roos["t025"] >= 1.30 and rtr["pf30"] > 1.0 and roos["pf30"] > 1.0)
        print(f"{'PASS' if ok else '    '} tr025={rtr['t025']:.3f} oos025={roos['t025']:.3f} "
              f"| tr20={rtr['pf20']:.2f} tr30={rtr['pf30']:.2f} oos20={roos['pf20']:.2f} oos30={roos['pf30']:.2f} "
              f"| Noos={roos['n']} t/d={td:.2f} wr={roos['wr']:.0f} | {P}")


if __name__ == "__main__":
    main()
