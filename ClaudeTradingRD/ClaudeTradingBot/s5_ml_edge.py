"""Can a model LEARN a profitable entry edge from the 5-second data?

Rich microstructure features at each 5s bar (past-only) -> predict forward return ->
trade on the prediction with realistic TP/SL/costs -> measure OUT-OF-SAMPLE expectancy.
Temporal split + embargo (no leakage). If the model's confident calls clear costs OOS,
that's a real machine-learned edge; if not, it confirms there's none.
"""
import json, glob, datetime as dt
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

CACHE = "C:/Projects/PycharmProjects/personal/KronosStrategies/tick_data_collector/Tick_Data_Generator/cache_data/XAU_USD"
SPREAD = 0.25
COMMISSION = 0.05
USD = 10.0   # $/pt at 0.1 lot


def load():
    bars = []
    for fp in sorted(glob.glob(CACHE + "/*.json")):
        for g in json.load(open(fp, encoding="utf-8")):
            t = dt.datetime.fromisoformat(g[0]["time"])
            path = [float(p["price"]) for p in g]
            bars.append((t.timestamp(), t.hour, path[0], max(path), min(path), path[-1]))
    bars.sort(key=lambda x: x[0])
    return bars


def build(bars, horizon_bars=18):
    ts = np.array([b[0] for b in bars]); hour = np.array([b[1] for b in bars])
    c = np.array([b[5] for b in bars]); hi = np.array([b[3] for b in bars]); lo = np.array([b[4] for b in bars])
    n = len(c)
    # gap mask: bar i valid only if the preceding 180 bars are contiguous (<=30s steps)
    dts = np.diff(ts, prepend=ts[0])
    gap = dts > 30
    # rolling-contiguity: cumulative count since last gap
    contig = np.zeros(n, dtype=int)
    run = 0
    for i in range(n):
        run = 0 if gap[i] else run + 1
        contig[i] = run

    def ret(k):
        r = np.full(n, np.nan); r[k:] = c[k:] - c[:-k]; return r
    def vol(k):
        d = np.diff(c, prepend=c[0])
        v = np.full(n, np.nan)
        cs2 = np.cumsum(d * d)
        v[k:] = np.sqrt((cs2[k:] - cs2[:-k]) / k); return v
    def rng_pos(k):
        # position of close within last-k high/low (0..1); needs rolling max/min
        p = np.full(n, np.nan)
        for i in range(k, n):
            w_hi = hi[i - k:i].max(); w_lo = lo[i - k:i].min()
            p[i] = (c[i] - w_lo) / (w_hi - w_lo) if w_hi > w_lo else 0.5
        return p

    feats = {
        "r_5s": ret(1), "r_30s": ret(6), "r_1m": ret(12), "r_2m": ret(24),
        "r_5m": ret(60), "r_15m": ret(180),
        "vol_1m": vol(12), "vol_5m": vol(60), "vol_15m": vol(180),
        "accel": ret(12) - ret(60) / 5.0,         # 1m vs 5m-pace
        "rngpos_5m": rng_pos(60), "rngpos_15m": rng_pos(180),
        "hour_sin": np.sin(2 * np.pi * hour / 24), "hour_cos": np.cos(2 * np.pi * hour / 24),
    }
    X = np.column_stack([feats[k] for k in feats])
    fnames = list(feats)
    # label: forward return over horizon (raw mid move, points)
    y = np.full(n, np.nan); y[:-horizon_bars] = c[horizon_bars:] - c[:-horizon_bars]
    # valid rows: contiguous history (>=180) AND contiguous forward window AND finite
    fwd_ok = np.zeros(n, dtype=bool)
    for i in range(n - horizon_bars):
        fwd_ok[i] = (ts[i + horizon_bars] - ts[i]) <= (horizon_bars * 5 + 30)
    valid = (contig >= 180) & fwd_ok & np.isfinite(y) & np.isfinite(X).all(axis=1)
    return X, y, ts, c, valid, fnames, horizon_bars


def simulate_dir(pred_dir, c, idxs, tp=0.8, sl=2.0, horizon=18, allbars=None):
    """Trade in predicted direction at each idx with TP/SL/time exit; return PnL list."""
    pnls = []
    for k, i in enumerate(idxs):
        side = pred_dir[k]
        if side == 0:
            continue
        entry = c[i] + SPREAD / 2 if side > 0 else c[i] - SPREAD / 2
        tp_px = entry + tp if side > 0 else entry - tp
        sl_px = entry - sl if side > 0 else entry + sl
        exit_px = None
        for j in range(i + 1, min(i + 1 + horizon, len(c))):
            hi = allbars[j][3]; lo = allbars[j][4]
            if side > 0:
                if lo <= sl_px: exit_px = sl_px; break
                if hi >= tp_px: exit_px = tp_px; break
            else:
                if hi >= sl_px: exit_px = sl_px; break
                if lo <= tp_px: exit_px = tp_px; break
        if exit_px is None:
            cc = c[min(i + horizon, len(c) - 1)]
            exit_px = cc - SPREAD / 2 if side > 0 else cc + SPREAD / 2
        pts = (exit_px - entry) if side > 0 else (entry - exit_px)
        pnls.append(pts * USD - COMMISSION)
    return pnls


if __name__ == "__main__":
    bars = load()
    X, y, ts, c, valid, fnames, H = build(bars)
    idx_all = np.where(valid)[0]
    # subsample every 6 bars (30s) to cut overlapping-window autocorrelation
    idx_all = idx_all[::6]
    split = int(len(idx_all) * 0.6)
    tr, te = idx_all[:split], idx_all[split:]
    # embargo: drop test rows within H bars of the split boundary
    boundary = tr[-1]
    te = te[ts[te] > ts[boundary] + (H * 5 + 60)]
    print(f"samples: train {len(tr)}  test {len(te)}  features {len(fnames)}  horizon {H*5}s")

    Xtr, ytr = X[tr], y[tr]; Xte, yte = X[te], y[te]
    model = HistGradientBoostingRegressor(max_iter=300, max_depth=4,
                                          learning_rate=0.05, l2_regularization=1.0,
                                          min_samples_leaf=200, random_state=0)
    model.fit(Xtr, ytr)
    pred_te = model.predict(Xte)
    # directional accuracy OOS
    da = np.mean(np.sign(pred_te) == np.sign(yte))
    corr = np.corrcoef(pred_te, yte)[0, 1]
    print(f"\nOOS directional accuracy: {100*da:.1f}%  (50% = no skill)")
    print(f"OOS pred-vs-actual correlation: {corr:+.4f}  (0 = no signal)")

    # Act on the model's CONFIDENT calls only (top/bottom quantiles of prediction)
    print("\n=== OOS expectancy of TRADING the model's calls (TP0.8/SL2.0, real costs) ===")
    for q in (0.5, 0.8, 0.9, 0.95):
        hi_thr = np.quantile(pred_te, q); lo_thr = np.quantile(pred_te, 1 - q)
        pdir = np.where(pred_te >= hi_thr, 1, np.where(pred_te <= lo_thr, -1, 0))
        pnls = simulate_dir(pdir, c, te, allbars=bars)
        if pnls:
            arr = np.array(pnls)
            print(f"  top/bottom {int((1-q)*100)}% conf: n={len(arr):4d}  "
                  f"WR={100*np.mean(arr>0):.0f}%  exp=${arr.mean():+.3f}  net=${arr.sum():+.0f}")

    imp = sorted(zip(fnames, model.feature_importances_ if hasattr(model, "feature_importances_")
                     else [0]*len(fnames)), key=lambda x: -x[1]) \
        if hasattr(model, "feature_importances_") else None
    # HistGBR has no feature_importances_; use permutation-free proxy: skip if absent
    print("\n(HistGBR: feature importance via permutation omitted for speed; "
          "signal verdict is the OOS expectancy above.)")
