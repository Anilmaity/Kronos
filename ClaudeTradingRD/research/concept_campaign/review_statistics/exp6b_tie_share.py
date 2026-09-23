"""How much of exp6's NEGATIVE is the stop-first tie convention / gap fills?"""
from common import *
h = M1["high"].to_numpy(); l = M1["low"].to_numpy(); o = M1["open"].to_numpy()
rg = h - l
thr = np.nanpercentile(rg, 99)
cand = np.flatnonzero(rg[:-1] >= thr) + 1
print("99th pct M1 range $", round(thr, 2))
for stop in (0.5, 1.0, 2.0):
    rng = np.random.default_rng(0)
    pos = np.sort(rng.choice(cand, 8000, replace=False))
    ev = events_from_pos(pos, rng.choice([-1, 1], len(pos)), stop, 1.0)
    r = cl.trade_test(ev, max_hold="1h", n_boot=500, blocks=False, seed=100, keep_trades=True)
    tr = r["_trades"]
    xi = np.searchsorted(TN, pd.DatetimeIndex(tr.exit_time).tz_convert("UTC").tz_localize(None).values.astype("datetime64[ns]"))
    lo_ = np.minimum(tr.stop, tr.target); hi_ = np.maximum(tr.stop, tr.target)
    tie = (tr.reason == "stop") & (l[xi] <= lo_) & (h[xi] >= hi_)
    gap = tr.gross_R < -1.001
    # 50/50 tie re-scoring: a tie is a coin flip between -1R and +1R -> expected 0
    adj = tr.gross_R.copy(); adj[tie] = 0.0
    print(f"stop ${stop}: real gross {tr.gross_R.mean():+.3f}R, ties(stop-first) {tie.mean():.1%}, "
          f"gap fills {gap.mean():.1%} (mean gap loss {tr.gross_R[gap].mean() if gap.any() else 0:+.2f}R), "
          f"gross with ties at 0 {adj.mean():+.3f}R | control gross {r['control']['avg_R_gross']:+.3f}R, diff {r['diff']:+.3f} {r['verdict']}")
