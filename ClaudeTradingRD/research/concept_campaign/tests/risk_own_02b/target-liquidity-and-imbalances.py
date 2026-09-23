"""target-liquidity-and-imbalances — "the two things I use to choose targets is liquidity
and imbalances" (pWAjzKndWXo). A target claim is a prediction that price REACHES the
level, so each half is a rate_test against a geometry-matched null.

Reading a (liquidity: "whenever you see equal lows that should be a target"):
  5m bars (the trading TF in the lesson). Swing = 2/2 fractal (strict left, >= right),
  known at the close of the 2nd right bar. When a new swing high j is confirmed, pair it
  with the most recent earlier confirmed swing high i within 48 bars such that
  |h_i - h_j| <= 0.10 x ATR14(5m) and no high between them exceeds max(h_i, h_j) —
  relatively equal highs, liquidity untaken. Level = max(h_i, h_j); hit = an M1 high
  >= level within 240 M1 bars. Mirror for equal lows.
Reading b (imbalances: FVGs "on the trading timeframe and one timeframe up"):
  15m three-bar FVGs, known at the close of the 3rd bar. The imbalance as a target =
  price trading back to the gap's near edge (bullish gap: the 3rd bar's low, from above;
  bearish: the 3rd bar's high, from below) within 240 M1 bars.
Null (both): matched random 5m (a) / 15m (b) bar closes within +/-30 days (sample_times,
  locked reps/window/seed), level placed at the SAME distance in ATR14 units of that
  timeframe from the next M1 open, same side, same 240-bar horizon. ATR units rather
  than raw price: both detectors fire right after local movement (a fresh swing or a
  displacement bar), so a raw-price null would be easier to reach in quiet moments.
claim '+' (these levels are reached more often than geometry-matched random levels).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, show  # noqa: E402

CID = "target-liquidity-and-imbalances"
HORIZON = 240
EQ_TOL_ATR = 0.10
EQ_LOOKBACK = 48
ATR_N = 14


def _atr(b: pd.DataFrame, n: int = ATR_N) -> np.ndarray:
    h, l_, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l_, np.abs(h - pc), np.abs(l_ - pc)]), axis=0)
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def _swings(h: np.ndarray, left: int = 2, right: int = 2) -> np.ndarray:
    n = len(h)
    ok = np.zeros(n, bool)
    ok[left:n - right] = True
    for k in range(1, left + 1):
        ok[left:n - right] &= h[left - k:n - right - k] < h[left:n - right]
    for k in range(1, right + 1):
        ok[left:n - right] &= h[left + k:n - right + k] <= h[left:n - right]
    return ok


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "side", "level", "atr"]
    b = cl.build_bars(m1, "5min")
    if len(b) < 60:
        return pd.DataFrame(columns=cols)
    atr = _atr(b)
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for side, arr in (("above", b["high"].to_numpy(float)),
                      ("below", -b["low"].to_numpy(float))):
        sw = np.flatnonzero(_swings(arr))
        for a_i in range(1, len(sw)):
            j = sw[a_i]
            conf = j + 2
            if not np.isfinite(atr[conf]):
                continue
            tol = EQ_TOL_ATR * atr[conf]
            for b_i in range(a_i - 1, -1, -1):          # most recent earlier swing first
                i = sw[b_i]
                if j - i > EQ_LOOKBACK:
                    break
                if i + 2 > conf:                          # must be confirmed already
                    continue
                lev = max(arr[i], arr[j])
                if abs(arr[i] - arr[j]) <= tol and arr[i + 1:j].max(initial=-np.inf) <= lev:
                    rows.append((ct[conf], side, lev if side == "above" else -lev,
                                 atr[conf]))
                    break
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "side", "level", "atr"])
    out.insert(1, "available_at", out["decision_time"])
    return out.sort_values(["decision_time", "side"], kind="stable").reset_index(drop=True)[cols]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "side", "level", "atr"]
    b = cl.build_bars(m1, "15min")
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    atr = _atr(b)
    h, l_ = b["high"].to_numpy(float), b["low"].to_numpy(float)
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l_[:-2]]
    bull = l_ > h2
    bear = h < l2
    ct = pd.DatetimeIndex(b["close_time"])
    ok = (bull | bear) & np.isfinite(atr)
    out = pd.DataFrame({"decision_time": ct[ok], "available_at": ct[ok],
                        "side": np.where(bull[ok], "below", "above"),
                        "level": np.where(bull[ok], l_[ok], h[ok]), "atr": atr[ok]})
    return out.reset_index(drop=True)


def run(ev: pd.DataFrame, tf: str):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    side = ev["side"].to_numpy()
    lev = ev["level"].to_numpy(float)
    obs = np.full(len(ev), np.nan)
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist_atr = (lev - first_px) / ev["atr"].to_numpy(float)
    for sd in ("above", "below"):
        m = side == sd
        obs[m] = cl.touch(t[m], lev[m], sd, horizon_bars=HORIZON)["hit"].to_numpy()
    bb = cl.bars(tf)
    grid = pd.DatetimeIndex(bb["close_time"])
    atr_grid = pd.Series(_atr(bb), index=grid)
    atr_grid = atr_grid[~atr_grid.index.duplicated()]
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS,
                         seed=cl.rules.SEED, grid_times=grid)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        okk = ~tk.isna()
        out = np.full(len(t), np.nan)
        a_k = atr_grid.reindex(tk[okk]).to_numpy(float)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[okk]), len(mkt.o) - 1)]
        lv = px + dist_atr[okk] * a_k
        hit = np.full(okk.sum(), np.nan)
        sdk = side[okk]
        fin = np.isfinite(lv)
        for sd in ("above", "below"):
            m = (sdk == sd) & fin
            if m.any():
                hit[m] = cl.touch(tk[okk][m], lv[m], sd, horizon_bars=HORIZON)["hit"].to_numpy()
        out[np.flatnonzero(okk)] = hit
        return out

    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null_fn=null_fn, predictors=ev, claim="+")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    print("CTRL", cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS)
    common_src = {
        "horizon_m1_bars": "declared-before-run: 240 trading minutes (~one session); the "
                           "corpus gives no time limit on a target",
        "atr_n": "declared-before-run: ATR14 of the level's timeframe, used only to scale "
                 "the null's distance (README trap 4: same geometry, same bars)",
        "null": "declared-before-run: matched random bar closes +/-30d (locked reps/window/"
                "seed), same ATR-unit distance and side"}
    if "a" in which:
        ev = cl.cache_frame("tli_a_eq5m_tol0.10_lb48", lambda: detect_a(cl.load_m1()))
        print("a events", len(ev), ev["side"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        res = run(ev, "5min")
        show(res)
        op = {"rules": [
            "5m 2/2 fractal swings, known 2 bars after the swing bar",
            "equal highs: new swing high paired with the latest earlier confirmed swing high "
            "within 48 bars, |diff| <= 0.10 ATR14(5m), no high in between above the level; "
            "level = the higher of the two (mirror for lows)",
            "hit = M1 trades to the level within 240 M1 bars of the confirmation close",
            "null = random 5m closes +/-30d, same ATR-unit distance from next M1 open, same side"],
            "params": {"tf": "5min", "swing": "2/2", "eq_tol_atr": EQ_TOL_ATR,
                       "eq_lookback_bars": EQ_LOOKBACK, "horizon_m1_bars": HORIZON,
                       "atr_n": ATR_N, "null": "ATR-scaled distance"}}
        src = {**common_src,
               "tf": "corpus: pWAjzKndWXo (5-minute trading TF with a 15-minute gap); "
                     "concept timeframes ltf 5m",
               "swing": "phase3: 2/2 swings (§1.8)",
               "eq_tol_atr": "declared-before-run: 'Equal lows has no tolerance' (concept "
                             "ambiguity); 0.10 ATR",
               "eq_lookback_bars": "declared-before-run: pair within 4 hours of 5m bars"}
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe))
    if "b" in which:
        ev = cl.cache_frame("tli_b_fvg15m_near_edge", lambda: detect_b(cl.load_m1()))
        print("b events", len(ev), ev["side"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
        res = run(ev, "15min")
        show(res)
        op = {"rules": [
            "15m three-bar FVG (bullish: low[i] > high[i-2]; bearish: high[i] < low[i-2]), "
            "known at the close of bar i",
            "target = the gap's near edge (bullish: bar i low, approached from above; "
            "bearish: bar i high, from below)",
            "hit = M1 trades to it within 240 M1 bars",
            "null = random 15m closes +/-30d, same ATR-unit distance, same side"],
            "params": {"tf": "15min", "edge": "near", "horizon_m1_bars": HORIZON,
                       "atr_n": ATR_N, "null": "ATR-scaled distance"}}
        src = {**common_src,
               "tf": "corpus: pWAjzKndWXo 'the 15-minute gap' (one timeframe above the 5m)",
               "edge": "declared-before-run: reaching the imbalance = tagging its near edge "
                       "('reached' is undefined in the corpus)"}
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Imbalance half of a two-item target list; order blocks "
                                    "are not scored."))
