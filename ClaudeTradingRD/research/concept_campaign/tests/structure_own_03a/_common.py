"""Shared helpers for batch structure_own_03a (structure, TTrades own voice).

Every helper is a PURE function of the frame it is given (probe-safe): bars are built
from the M1 slice passed in, never from the cached full-span bars().
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402

PHASE3 = "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)"
BATCH_DIR = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a"


def swings3(b: pd.DataFrame):
    """Strict 3-bar swings (swing-point.yaml): high[i] > high[i-1] and > high[i+1]
    (mirror for lows). Returns bool arrays (is_sh, is_sl). A swing at i is usable only
    once bar i+1 has CLOSED (confirmation = close_time of bar i+1)."""
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    n = len(b)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n >= 3:
        sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:])
        sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:])
    return sh, sl


def summary(res: dict) -> str:
    keys = ("test_type", "n", "n_gated", "avg_R", "observed_rate", "null_rate", "diff",
            "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties",
            "exposure_bars", "gate_rate", "ctrl_overlap", "halves")
    out = []
    for k in keys:
        if res.get(k) is not None:
            v = res[k]
            if isinstance(v, float):
                v = round(v, 4)
            out.append(f"  {k:15s} {v}")
    return "\n".join(out)


def atr(b: pd.DataFrame, n: int = 14) -> np.ndarray:
    """Mean true range of the last n CLOSED bars, value at bar i uses bars <= i."""
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def level_rate(times, level, above, horizon_bars):
    """Observed touch of `level` (side per row: above=True -> any M1 high >= level)
    within `horizon_bars` M1 bars after each time, and a geometry-matched null:
    the same signed distance from the first M1 open after a matched random moment
    (+/-30 d, locked reps/seed), same M1-bar horizon, same side.
    Returns (obs, null_fn)."""
    mkt = cl.get_market()
    t = pd.DatetimeIndex(times)
    level = np.asarray(level, float)
    above = np.asarray(above, bool)
    hb = np.broadcast_to(np.asarray(horizon_bars, np.int64), (len(t),)).copy()
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = level - first_px

    def _touch(tk, lv, ab, h):
        out = np.zeros(len(tk), bool)
        for side, m in (("above", ab), ("below", ~ab)):
            if m.any():
                out[m] = cl.touch(tk[m], lv[m], side, horizon_bars=h[m])["hit"].to_numpy()
        return out

    obs = _touch(t, level, above, hb).astype(float)
    rt = cl.sample_times(t, cl.rules.CTRL_REPS,
                         cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        if tk.tz is None:
            tk = tk.tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        out[ok] = _touch(tk[ok], px + dist[ok], above[ok], hb[ok])
        return out

    return obs, null_fn
