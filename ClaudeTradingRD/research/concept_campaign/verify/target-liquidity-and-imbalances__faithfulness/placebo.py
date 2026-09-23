"""Faithfulness verification for target-liquidity-and-imbalances reading b.
Per-event obs and matched-null (same code path as the original run()) for:
  FVG  : the original 15m FVG events (near edge = bar i low/high)
  PLAC : every NON-FVG 15m bar, side from bar-i body (up body -> 'below' at bar-i low)
Then compare diffs, stratified by bar geometry. Ledger disabled (verification, not a reading).
"""
import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
SRC = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02b/target-liquidity-and-imbalances.py"
sys.path.insert(0, os.path.dirname(SRC))
spec = importlib.util.spec_from_file_location("tli", SRC); tli = importlib.util.module_from_spec(spec); spec.loader.exec_module(tli)
import numpy as np, pandas as pd
import concept_lab as cl

OUT = os.path.dirname(os.path.abspath(__file__))
m1 = cl.load_m1()
b = cl.build_bars(m1, "15min")
atr = tli._atr(b)
o, h, l_, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l_[:-2]]
o2 = np.r_[np.nan, np.nan, o[:-2]]
h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l_[:-1]]
bull = l_ > h2; bear = h < l2
ct = pd.DatetimeIndex(b["close_time"])
fin = np.isfinite(atr) & np.isfinite(h2)
up = c > o; dn = c < o
kind = np.where(bull | bear, "FVG", "PLAC")
side = np.where(bull, "below", np.where(bear, "above", np.where(up, "below", "above")))
keep = fin & ((bull | bear) | up | dn)
lev = np.where(side == "below", l_, h)
df = pd.DataFrame({"decision_time": ct[keep], "available_at": ct[keep], "side": side[keep],
                   "level": lev[keep], "atr": atr[keep], "kind": kind[keep],
                   "move3": ((c - o2) / atr)[keep], "rng_i": ((h - l_) / atr)[keep],
                   "rng_mid": ((h1 - l1) / atr)[keep]})
df = df.reset_index(drop=True)

mkt = cl.get_market()
t = pd.DatetimeIndex(df["decision_time"])
sd_arr = df["side"].to_numpy(); lv = df["level"].to_numpy(float)
first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
dist_atr = (lv - first_px) / df["atr"].to_numpy(float)
obs = np.full(len(df), np.nan)
for sd in ("above", "below"):
    m = sd_arr == sd
    obs[m] = cl.touch(t[m], lv[m], sd, horizon_bars=tli.HORIZON)["hit"].to_numpy()
bb = cl.bars("15min"); grid = pd.DatetimeIndex(bb["close_time"])
atr_grid = pd.Series(tli._atr(bb), index=grid); atr_grid = atr_grid[~atr_grid.index.duplicated()]
rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED, grid_times=grid)
nulls = []
for k in range(rt.shape[1]):
    tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); okk = ~tk.isna()
    out = np.full(len(t), np.nan)
    a_k = atr_grid.reindex(tk[okk]).to_numpy(float)
    px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[okk]), len(mkt.o) - 1)]
    lvk = px + dist_atr[okk] * a_k
    hit = np.full(okk.sum(), np.nan); sdk = sd_arr[okk]; f = np.isfinite(lvk)
    for sd in ("above", "below"):
        m = (sdk == sd) & f
        if m.any():
            hit[m] = cl.touch(tk[okk][m], lvk[m], sd, horizon_bars=tli.HORIZON)["hit"].to_numpy()
    out[np.flatnonzero(okk)] = hit
    nulls.append(out)
df["obs"] = obs; df["null"] = np.nanmean(np.vstack(nulls), axis=0); df["dist_atr"] = dist_atr
df.to_parquet(os.path.join(OUT, "per_event.parquet"))
print(df.groupby("kind")[["obs", "null"]].mean().assign(diff=lambda x: x.obs - x.null), df.kind.value_counts())
