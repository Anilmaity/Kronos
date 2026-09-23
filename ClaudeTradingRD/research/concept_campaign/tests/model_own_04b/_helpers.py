"""Shared numpy helpers for batch model_own_04b (one script per concept imports these).

All helpers are pure functions of the arrays they are handed; none reads data on its
own, so a detector built on them stays probe-able on a truncated M1 slice.

CISD convention (method spec §4.2, the adjudicated definition, default reading
`series_open` = open of the FIRST candle of the opposing series that made the extreme,
series up to 10 candles, turn candle may sit up to 2 bars after the series — the
same skeleton as `detectors.cisd._run_into_extreme`).
"""
from __future__ import annotations

import numpy as np

MAX_SERIES = 10


def series_level(o, c, e, bullish, lo=0, max_series=MAX_SERIES):
    """Open of the first candle of the opposing-close run that produced the extreme
    at index e (down-closes for a bullish CISD at a low, up-closes for a bearish one).
    Search never goes below index `lo`. Returns nan if no run within 2 bars."""
    def q(k):
        return (c[k] < o[k]) if bullish else (c[k] > o[k])
    end = e
    while end > lo and not q(end):
        end -= 1
        if e - end > 2:
            return np.nan
    if not q(end):
        return np.nan
    start = end
    while start > lo and q(start - 1) and (end - start + 1) < max_series:
        start -= 1
    return float(o[start])


def cisd_after_sweep(o, h, l, c, j0, j1, swept_level, bullish, lo=0):
    """Scan bars j0..j1-1. The setup arms when a bar trades beyond `swept_level`
    (below it for bullish, above it for bearish). The running extreme since arming
    defines the opposing series; a later bar that CLOSES through that series' first
    open is the CISD. A new extreme re-derives the series (spec §4.2 step 5).
    Returns (j_confirm, extreme_price) or (-1, nan). Uses only bars <= j_confirm."""
    ext = -1
    lvl = np.nan
    for j in range(j0, j1):
        if ext < 0:
            if (l[j] < swept_level) if bullish else (h[j] > swept_level):
                ext = j
                lvl = series_level(o, c, j, bullish, lo)
            continue
        if (l[j] < l[ext]) if bullish else (h[j] > h[ext]):
            ext = j
            lvl = series_level(o, c, j, bullish, lo)
            continue
        if np.isfinite(lvl) and ((c[j] > lvl) if bullish else (c[j] < lvl)):
            return j, float(l[ext] if bullish else h[ext])
    return -1, np.nan


def cisd_in_candle(o, h, l, c, a, b, bullish):
    """§2.4 step 3 on a CLOSED higher-timeframe candle spanning LTF bars a..b-1:
    find the candle's extreme, the opposing series that made it, and require a
    later LTF close through the series' first open before the candle closes.
    Returns (j_confirm, extreme_idx) or (-1, -1). Only valid when read at the HTF
    candle's close (it looks at the whole candle)."""
    if b - a < 3:
        return -1, -1
    e = a + int(np.argmin(l[a:b]) if bullish else np.argmax(h[a:b]))
    lvl = series_level(o, c, e, bullish, lo=a)
    if not np.isfinite(lvl):
        return -1, -1
    for j in range(e + 1, b):
        if (c[j] > lvl) if bullish else (c[j] < lvl):
            return j, e
    return -1, -1


def c2_flags(o, h, l, c):
    """Candle-2 closure per bar vs the previous bar (spec §3.2):
    bull: low < prev low and close > prev low; bear: high > prev high and close <
    prev high. Returns +1/-1/0 (0 also when both fire)."""
    ph = np.r_[np.nan, h[:-1]]
    pl = np.r_[np.nan, l[:-1]]
    bull = (l < pl) & (c > pl)
    bear = (h > ph) & (c < ph)
    out = np.zeros(len(o), int)
    out[bull & ~bear] = 1
    out[bear & ~bull] = -1
    return out


def c3_flags(o, h, l, c, c2):
    """Candle-3 closure, Reading A (spec §3.3): the previous candle took the prior
    extreme but produced no C2 closure, and this candle closes beyond the previous
    candle's open. +1/-1/0."""
    po = np.r_[np.nan, o[:-1]]
    prev_took_low = np.r_[False, False, (l[1:-1] < l[:-2])]
    prev_took_high = np.r_[False, False, (h[1:-1] > h[:-2])]
    prev_c2 = np.r_[0, c2[:-1]]
    bull = (c > po) & (prev_c2 == 0) & prev_took_low
    bear = (c < po) & (prev_c2 == 0) & prev_took_high
    out = np.zeros(len(o), int)
    out[bull & ~bear] = 1
    out[bear & ~bull] = -1
    return out


def fractal_swings(h, l, left=2, right=2):
    """2/2 fractal swing flags (strict on both sides). A swing at i is only KNOWN
    at the close of bar i+right."""
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    for i in range(left, n - right):
        hh = h[i]
        ll = l[i]
        if hh > h[i - left:i].max() and hh > h[i + 1:i + 1 + right].max():
            sh[i] = True
        if ll < l[i - left:i].min() and ll < l[i + 1:i + 1 + right].min():
            sl[i] = True
    return sh, sl


def day_end_bars(m1_index, times, day_open_hour=18):
    """M1 bars from the first bar at/after each time to the end of that time's NY
    trading day (18:00 roll). Outcome horizon only — never a predictor input."""
    import concept_lab as cl
    import pandas as pd
    idx = pd.DatetimeIndex(m1_index)
    td = cl.trading_day(idx, day_open_hour).to_numpy()
    starts = np.r_[0, np.flatnonzero(td[1:] != td[:-1]) + 1, len(td)]
    tn = idx.asi8
    p = np.searchsorted(tn, pd.DatetimeIndex(times).tz_convert("UTC").as_unit(
        idx.unit).asi8, side="left")
    nxt = starts[np.searchsorted(starts, p, side="right")]
    return nxt - p


def matched_touch_null(t, dist, side, hb, tod_tol_min=30, invert=False):
    """null_fn for rate_test: the same signed distance from the first price after a
    matched random moment (+/-30d, NY time of day within tod_tol_min), the same
    horizon in M1 bars. `side` 'above'/'below' per row (array). invert=True scores
    NOT touched (a level-holds claim)."""
    import concept_lab as cl
    import pandas as pd
    mkt = cl.get_market()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=tod_tol_min)
    side = np.asarray(side)
    dist = np.asarray(dist, float)
    hb = np.asarray(hb)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        for sd in ("above", "below"):
            m = ok & (side == sd)
            if not m.any():
                continue
            px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[m]), len(mkt.o) - 1)]
            hit = cl.touch(tk[m], px + dist[m], sd, horizon_bars=hb[m])["hit"].to_numpy()
            out[m] = (~hit) if invert else hit
        return out.astype(float)
    return null_fn
