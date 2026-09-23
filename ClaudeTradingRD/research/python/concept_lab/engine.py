"""The M1 execution engine: vectorised exit resolution, control sampling, touches.

Resolution rules are exactly those of `backtest_c2_wick.resolve` (the phase-2/3
resolver) — `tests/test_engine.py` checks bar-for-bar equality against it on random
books — but vectorised, because the campaign resolves millions of trades:

  * walk M1 bars [i0, i1): i0 = the entry bar (its range is AFTER the entry, which
    is at its open), i1 = first bar at/after decision_time + max_hold;
  * stop and target touched in the same M1 bar -> the STOP (M1 has no intrabar
    order; the optimistic tie is how backtests lie);
  * a bar that opens through the stop fills at that open (gap paid); a target
    fills at its level;
  * neither touched -> exit at the close of bar i1-1 ("time").

Speed: the first bar satisfying `x >= thr` inside [i0, i1) is found with 64-bar
block maxima (head scan, block scan, one in-block refine, tail scan), so cost per
trade is ~O(64 + hold/64) instead of O(hold), in memory-bounded chunks.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .data import load_m1, TZ, utc_ns, from_ns

BLOCK = 64
CHUNK = 20_000

_MARKETS: dict = {}


class Market:
    """Numpy views of an M1 frame plus the block maxima the resolver needs."""

    def __init__(self, m1: pd.DataFrame):
        if not m1.index.is_monotonic_increasing:
            raise ValueError("M1 index must be sorted")
        self.m1 = m1
        self.t = pd.DatetimeIndex(m1.index).tz_convert("UTC").as_unit("ns")
        self.tn = utc_ns(self.t)
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)
        self.nl = -self.l
        self.hb = _block_max(self.h)
        self.nlb = _block_max(self.nl)
        self.moh = self.t.minute.to_numpy()                   # UTC minute == NY minute
        self._nymod = None

    @property
    def nymod(self) -> np.ndarray:
        if self._nymod is None:
            loc = self.t.tz_convert(TZ)
            self._nymod = (loc.hour * 60 + loc.minute).to_numpy()
        return self._nymod

    def pos_at_or_after(self, times) -> np.ndarray:
        return np.searchsorted(self.tn, utc_ns(times), side="left")


def get_market(m1: pd.DataFrame | None = None) -> Market:
    m = load_m1() if m1 is None else m1
    k = id(m)
    mk = _MARKETS.get(k)
    if mk is None or mk.m1 is not m:
        mk = Market(m)
        _MARKETS[k] = mk
    return mk


def _block_max(x: np.ndarray) -> np.ndarray:
    n = len(x)
    nb = (n + BLOCK - 1) // BLOCK
    pad = np.full(nb * BLOCK, -np.inf)
    pad[:n] = x
    return pad.reshape(nb, BLOCK).max(axis=1)


def _first_ge(X: np.ndarray, XB: np.ndarray, i0: np.ndarray, i1: np.ndarray,
              thr: np.ndarray) -> np.ndarray:
    """First index k in [i0, i1) with X[k] >= thr, else -1. Vectorised."""
    n = len(i0)
    res = np.full(n, -1, dtype=np.int64)
    if n == 0:
        return res
    B = BLOCK
    nX = len(X)
    ar = np.arange(B)
    ok = np.isfinite(thr) & (i1 > i0)
    head_end = np.minimum(i1, ((i0 + B - 1) // B) * B)
    for s in range(0, n, CHUNK):
        sl = slice(s, min(n, s + CHUNK))
        a, b, he, th, okc = i0[sl], i1[sl], head_end[sl], thr[sl], ok[sl]
        r = np.full(len(a), -1, dtype=np.int64)
        # head: [i0, he)
        idx = a[:, None] + ar[None, :]
        hit = (X[np.minimum(idx, nX - 1)] >= th[:, None]) & (idx < he[:, None]) & okc[:, None]
        anyh = hit.any(axis=1)
        r[anyh] = a[anyh] + hit[anyh].argmax(axis=1)
        # whole blocks: [bs, be)
        bs, be = he // B, b // B
        nb = np.where(he % B == 0, be - bs, 0)
        todo = (~anyh) & okc & (nb > 0)
        if todo.any():
            ti = np.flatnonzero(todo)
            mx = int(nb[ti].max())
            bar_ = np.arange(mx)
            bidx = bs[ti][:, None] + bar_[None, :]
            bh = (XB[np.minimum(bidx, len(XB) - 1)] >= th[ti][:, None]) & \
                 (bar_[None, :] < nb[ti][:, None])
            anyb = bh.any(axis=1)
            if anyb.any():
                tj = ti[anyb]
                fb = bs[tj] + bh[anyb].argmax(axis=1)
                ridx = fb[:, None] * B + ar[None, :]
                rv = X[np.minimum(ridx, nX - 1)] >= th[tj][:, None]
                r[tj] = fb * B + rv.argmax(axis=1)
        # tail: [max(be*B, he), i1)
        todo = (r < 0) & okc
        if todo.any():
            ti = np.flatnonzero(todo)
            ts = np.maximum(be[ti] * B, he[ti])
            idx = ts[:, None] + ar[None, :]
            hit = (X[np.minimum(idx, nX - 1)] >= th[ti][:, None]) & (idx < b[ti][:, None])
            anyt = hit.any(axis=1)
            r[ti[anyt]] = ts[anyt] + hit[anyt].argmax(axis=1)
        res[sl] = r
    return res


def resolve_trades(mkt: Market, long: np.ndarray, stop: np.ndarray,
                   target: np.ndarray, i0: np.ndarray, i1: np.ndarray) -> dict:
    """Resolve a book on M1. `target` may be NaN (no target: stop or time only).

    Returns dict of arrays: exit_pos, exit_px, reason (0 stop, 1 target, 2 time),
    plus the tie diagnostics (rules-2):
      ambiguous  stop AND target inside the exit bar's range and the bar did not
                 OPEN through either — the order is unknowable on M1. The locked
                 convention scores it as the stop; `tie_target_px` lets a caller
                 re-score it as a 50/50 coin flip.
      open_tgt   the exit bar OPENED through the target while its range also hit the
                 stop — the target was genuinely first (still scored as the stop by
                 the locked convention; the 50/50 re-scoring scores it as the target).
      gap_stop   stop filled at a bar open beyond the stop (gap paid).
    Requires i1 > i0 for every trade.
    """
    long = np.asarray(long, bool)
    stop = np.asarray(stop, float)
    target = np.asarray(target, float)
    i0 = np.asarray(i0, np.int64)
    i1 = np.asarray(i1, np.int64)
    if (i1 <= i0).any():
        raise ValueError("every trade needs i1 > i0")
    n = len(i0)
    si = np.full(n, -1, np.int64)
    ti = np.full(n, -1, np.int64)
    L, S = np.flatnonzero(long), np.flatnonzero(~long)
    if len(L):
        si[L] = _first_ge(mkt.nl, mkt.nlb, i0[L], i1[L], -stop[L])
        ti[L] = _first_ge(mkt.h, mkt.hb, i0[L], i1[L], target[L])
    if len(S):
        si[S] = _first_ge(mkt.h, mkt.hb, i0[S], i1[S], stop[S])
        ti[S] = _first_ge(mkt.nl, mkt.nlb, i0[S], i1[S], -target[S])
    stop_first = (si >= 0) & ((ti < 0) | (si <= ti))
    tgt_first = (ti >= 0) & ~stop_first
    reason = np.full(n, 2, np.int8)
    reason[stop_first] = 0
    reason[tgt_first] = 1
    exit_pos = np.where(stop_first, si, np.where(tgt_first, ti, i1 - 1))
    op = mkt.o[exit_pos]
    stop_fill = np.where(long, np.minimum(stop, op), np.maximum(stop, op))
    exit_px = np.where(stop_first, stop_fill,
                       np.where(tgt_first, target, mkt.c[exit_pos]))
    same = stop_first & (ti >= 0) & (si == ti)
    thru_stop = np.where(long, op <= stop, op >= stop)
    with np.errstate(invalid="ignore"):
        thru_tgt = np.where(long, op >= target, op <= target)
    ambiguous = same & ~thru_stop & ~thru_tgt
    open_tgt = same & ~thru_stop & thru_tgt
    gap_stop = stop_first & thru_stop & (stop_fill != stop)
    return {"exit_pos": exit_pos, "exit_px": exit_px, "reason": reason,
            "ambiguous": ambiguous, "open_tgt": open_tgt, "gap_stop": gap_stop}


# ══ control / null sampling ═══════════════════════════════════════════════════
def _auto_align(times: pd.DatetimeIndex) -> int:
    mins = np.unique(pd.DatetimeIndex(times).minute.to_numpy())
    g = 60
    for m in mins:
        g = math.gcd(g, int(m))
    return max(1, g)


def sample_times(decision_times, reps: int, window_days: float, seed: int,
                 align="auto", tod_tol_min: int | None = None,
                 grid_times=None, m1: pd.DataFrame | None = None,
                 max_tries: int = 200) -> np.ndarray:
    """Random matched moments: for each decision time, `reps` draws uniformly from
    the candidate moments within +/- `window_days` (the locked +/-30-day regime
    window of phase 3).

    Candidates:
      * default: M1 bar starts (so every draw is a tradable minute). With
        align="auto" they are restricted to the same minute-of-hour residue as
        the event grid (events on :00 -> draws on :00; on :00/:15/:30/:45 -> any
        quarter mark), so a bar-close book is not compared with mid-bar entries
        (vault trap 9: "edges" concentrated at minute offset 0). align=1 lifts it.
      * grid_times: an explicit sorted array of candidate decision moments, e.g.
        `bars('1h').close_time` — draws land exactly on that grid (phase-3 style).
    tod_tol_min: additionally require the NY time-of-day within +/- tol minutes of
      the event's (circular) — use it to hold time-of-day fixed when the concept
      is NOT about timing.
    Returns datetime64[ns] UTC array of shape (n, reps); NaT where no candidate.
    """
    mkt = get_market(m1)
    d = pd.DatetimeIndex(decision_times).tz_convert("UTC").as_unit("ns")
    dn = utc_ns(d)
    n = len(d)
    out = np.full((n, reps), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    if n == 0:
        return out
    rng = np.random.default_rng(seed)
    w = np.timedelta64(int(window_days * 86400), "s").astype("timedelta64[ns]")
    if grid_times is not None:
        G = np.sort(utc_ns(grid_times))
        loc = from_ns(G).tz_convert(TZ)
        groups = [(np.arange(n), G, (loc.hour * 60 + loc.minute).to_numpy())]
    else:
        g = _auto_align(d) if align == "auto" else int(align or 1)
        groups = []
        if tod_tol_min is None:
            res = (d.minute.to_numpy() % g)
            for r in np.unique(res):
                P = np.flatnonzero(mkt.moh % g == r)
                groups.append((np.flatnonzero(res == r), mkt.tn[P], mkt.nymod[P]))
    if tod_tol_min is not None and grid_times is None:
        # Same NY wall-clock minute (+/- tol, on the align grid) on a random OTHER
        # day in the window: shift by whole days on the LOCAL clock so DST does not
        # move the time of day, then keep the draw only if a bar exists there.
        loc = d.tz_convert(TZ).tz_localize(None)
        W = int(window_days)
        tol = int(tod_tol_min)
        for k in range(reps):
            pend = np.arange(n)
            for _ in range(max_tries):
                if len(pend) == 0:
                    break
                kd = rng.integers(-W, W + 1, len(pend))
                jm = g * rng.integers(-(tol // g), tol // g + 1, len(pend))
                tgt_local = loc[pend] + pd.to_timedelta(kd, unit="D") + \
                    pd.to_timedelta(jm, unit="min")
                tu = tgt_local.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT")
                okk = ~pd.isna(tu)
                tn_ = np.full(len(pend), np.datetime64("NaT", "ns"))
                tn_[okk] = utc_ns(tu[okk])
                pos = np.searchsorted(mkt.tn, tn_, side="left")
                posc = np.minimum(pos, len(mkt.tn) - 1)
                acc = okk & (mkt.tn[posc] == tn_) & (tn_ != dn[pend])
                out[pend[acc], k] = tn_[acc]
                pend = pend[~acc]
        return out
    ev_mod = None
    if tod_tol_min is not None:
        loc = d.tz_convert(TZ)
        ev_mod = (loc.hour * 60 + loc.minute).to_numpy()
    for rows, T, Tmod in groups:
        if len(rows) == 0 or len(T) == 0:
            continue
        lo = np.searchsorted(T, dn[rows] - w, side="left")
        hi = np.searchsorted(T, dn[rows] + w, side="right")
        has = hi > lo
        for k in range(reps):
            if tod_tol_min is None:
                u = rng.integers(lo, np.maximum(hi, lo + 1))
                v = np.where(has, T[np.minimum(u, len(T) - 1)], np.datetime64("NaT", "ns"))
                out[rows, k] = v
            else:                                   # grid mode: rejection on the grid
                pend = np.flatnonzero(has)
                for _ in range(max_tries):
                    if len(pend) == 0:
                        break
                    u = rng.integers(lo[pend], hi[pend])
                    dm = np.abs(Tmod[u] - ev_mod[rows[pend]])
                    dm = np.minimum(dm, 1440 - dm)
                    acc = dm <= tod_tol_min
                    out[rows[pend[acc]], k] = T[u[acc]]
                    pend = pend[~acc]
    return out


def touch(times, level, side: str, horizon=None, m1: pd.DataFrame | None = None,
          start_after=None, horizon_bars=None, until=None) -> pd.DataFrame:
    """Does price reach `level` within a horizon after each time?

    side='above': any M1 high >= level; side='below': any M1 low <= level. The scan
    starts at the first M1 bar starting at/after `start_after` (default: `times`
    — i.e. never inside a bar that began before t).
    Give exactly ONE horizon:
      horizon       wall-clock Timedelta (scalar)  — CAREFUL: across the daily halt
                    and weekends a wall-clock window holds fewer tradable minutes;
                    a Friday-close + 23h window holds none at all
      horizon_bars  number of M1 bars (scalar or per-row array) — TRADING time;
                    use it when real and null windows sit differently vs halts
      until         per-row end times (exclusive)
    Returns DataFrame(hit: bool, hit_time, minutes) indexed like `times`.
    """
    mkt = get_market(m1)
    tt = pd.DatetimeIndex(times).tz_convert("UTC").as_unit("ns")
    st = tt if start_after is None else pd.DatetimeIndex(start_after).tz_convert("UTC")
    i0 = mkt.pos_at_or_after(st)
    if sum(x is not None for x in (horizon, horizon_bars, until)) != 1:
        raise ValueError("give exactly one of horizon / horizon_bars / until")
    if horizon is not None:
        i1 = mkt.pos_at_or_after(tt + pd.Timedelta(horizon))
    elif until is not None:
        i1 = mkt.pos_at_or_after(until)
    else:
        i1 = np.minimum(i0 + np.asarray(horizon_bars, np.int64), len(mkt.tn))
    lv = np.broadcast_to(np.asarray(level, float), (len(tt),)).copy()
    if side == "above":
        k = _first_ge(mkt.h, mkt.hb, i0, i1, lv)
    elif side == "below":
        k = _first_ge(mkt.nl, mkt.nlb, i0, i1, -lv)
    else:
        raise ValueError("side must be 'above' or 'below'")
    hit = k >= 0
    ht = from_ns(np.where(hit, mkt.tn[np.maximum(k, 0)], np.datetime64("NaT", "ns")))
    return pd.DataFrame({"hit": hit, "hit_time": ht,
                         "minutes": ((ht - tt).total_seconds() / 60).to_numpy()},
                        index=tt)
