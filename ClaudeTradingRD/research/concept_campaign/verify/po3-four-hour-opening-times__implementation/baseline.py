"""Does the random-time control flatter any 10:00-NY entry with a 06:00-candle stop?"""
import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
m1 = cl.load_m1()
b = cl.build_bars(m1, "4h", grid4h="futures")
st = pd.DatetimeIndex(b.index); hr = cl.to_ny(st).hour.to_numpy()
pos = np.flatnonzero(hr == 6); pos = pos[pos >= 1]; prev = pos - 1
ok = (st[pos] - st[prev]) == pd.Timedelta("4h"); pos, prev = pos[ok], prev[ok]
H, L, C, O = (b[k].to_numpy() for k in ("high", "low", "close", "open"))
bull = (L[pos] < L[prev]) & (C[pos] > L[prev]); bear = (H[pos] > H[prev]) & (C[pos] < H[prev])
sig = bull ^ bear
ct = pd.DatetimeIndex(b["close_time"].iloc[pos]).tz_convert("UTC")
def run(name, mask, dirs):
    ev = pd.DataFrame({"decision_time": ct[mask], "available_at": ct[mask], "direction": dirs[mask],
                       "stop_px": np.where(dirs[mask] == 1, L[pos][mask], H[pos][mask]).astype(float), "rr": 2.0})
    r = cl.trade_test(ev.reset_index(drop=True), max_hold="4h")
    print(f"{name:40s} n={r['n']:5d} avgR={r['avg_R']:+.3f} ctrl={r['control']['avg_R']:+.3f} diff={r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] {r['verdict']}")
rng = np.random.default_rng(7)
allm = np.ones(len(pos), bool)
for s in range(3):
    run(f"all days, random dir (seed {s})", allm, rng.choice([-1, 1], len(pos)))
run("non-C2 days, random dir", ~sig, rng.choice([-1, 1], len(pos)))
run("C2 days, random dir", sig, rng.choice([-1, 1], len(pos)))
run("C2 days, OPPOSITE dir", sig, np.where(bull, -1, 1))
run("all days, 06:00 candle body dir", allm & (C[pos] != O[pos]), np.where(C[pos] > O[pos], 1, -1))
run("all days, 06:00 body dir REVERSED", allm & (C[pos] != O[pos]), np.where(C[pos] > O[pos], -1, 1))
