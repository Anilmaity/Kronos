"""Shared helpers for batch entry_own_01b (TTrades own-voice entry concepts).

Everything here is PURE: M1 slice in -> frames out, so every detector that uses it
can be re-run by probe_lookahead on truncated data.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import concept_lab as cl      # noqa: E402
from detectors.cisd import cisd_events          # noqa: E402

OHLC = ["open", "high", "low", "close"]

# phase-3 locked CISD (conjunction_preregistration §1.8 / §1.16)
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
PHASE3_SRC = "phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked primary config)"


def cisd_frame(b: pd.DataFrame, **kw) -> pd.DataFrame:
    """cisd_events on a bar frame plus positional indices and the confirm bar close_time."""
    ev = cisd_events(b[OHLC], **{**CISD_KW, **kw})
    if ev.empty:
        return ev.assign(conf_pos=pd.Series(dtype=int), ext_pos=pd.Series(dtype=int),
                         s_pos=pd.Series(dtype=int), e_pos=pd.Series(dtype=int),
                         conf_close_time=pd.Series(dtype="datetime64[ns, UTC]"),
                         sgn=pd.Series(dtype=int))
    idx = b.index
    ev = ev.copy()
    ev["conf_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    ev["ext_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ev["s_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    ev["e_pos"] = idx.get_indexer(pd.DatetimeIndex(ev["series_end"]))
    ev["conf_close_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["conf_pos"].to_numpy()])
    ev["sgn"] = np.where(ev["direction"] == "bullish", 1, -1)
    return ev.reset_index(drop=True)


def complete_bars(b: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    """Drop bars whose nominal close is after the last M1 minute of the slice
    (a bar still in progress at the cut)."""
    if b.empty or m1.empty:
        return b
    end = pd.Timestamp(m1.index[-1]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    return b[pd.DatetimeIndex(b["close_time"]).tz_convert("UTC") <= end]


def m1_arrays(m1: pd.DataFrame):
    t = pd.DatetimeIndex(m1.index).tz_convert("UTC").as_unit("ns").asi8
    return t, m1["high"].to_numpy(float), m1["low"].to_numpy(float), m1["close"].to_numpy(float)


def first_touch(m1_t, m1_h, m1_l, start_ns, end_ns, level, side):
    """Per row: index of the first M1 bar starting in [start, end) whose high >= level
    (side='above') or low <= level (side='below'); -1 if none."""
    i0 = np.searchsorted(m1_t, np.asarray(start_ns, np.int64), side="left")
    i1 = np.searchsorted(m1_t, np.asarray(end_ns, np.int64), side="left")
    out = np.full(len(i0), -1, np.int64)
    for k in range(len(i0)):
        a, z = i0[k], i1[k]
        if z <= a or not np.isfinite(level[k]):
            continue
        seg = m1_h[a:z] >= level[k] if side[k] == "above" else m1_l[a:z] <= level[k]
        j = np.flatnonzero(seg)
        if len(j):
            out[k] = a + j[0]
    return out


# ── 4h C2 + 15m CISD book (used by single-cisd-at-swing-point, c2-confirmation-scaling, t-spot) ──
C2_HTF = "4h"          # forex grid (build_bars default, phase-3 §1.16)
C2_LTF = "15min"


def c2_book(m1: pd.DataFrame) -> pd.DataFrame:
    """HTF C2 closures (spec §3.2: sweep of the prior candle's extreme, close back inside)
    that carry a same-direction LTF CISD (phase-3 rule) whose extreme AND confirm bar lie
    inside the C2 candle. One row per C2 (two-sided C2s carrying both CISDs are dropped).
    Columns: c2 start/close, direction, C2 OHLC, prior candle (C1) OHLC, the first matching
    CISD's series-body MT, and C1's opposing-series first open (for the ideal-closure test).
    """
    from detectors.fractal import c2_events
    b = cl.build_bars(m1, C2_HTF)
    cols = ["c2_start", "c2_close", "sgn", "o", "h", "l", "c", "c1_o", "c1_h", "c1_l", "c1_c",
            "series_open", "cisd_mt", "cisd_close_time"]
    if len(b) < 3:
        return pd.DataFrame(columns=cols)
    c2 = c2_events(b[OHLC], sweep_ref="prior_candle", require_close_inside=True,
                   require_reversal_close=False)
    if c2.empty:
        return pd.DataFrame(columns=cols)
    b15 = cl.build_bars(m1, C2_LTF)
    ce = cisd_frame(b15)
    if ce.empty:
        return pd.DataFrame(columns=cols)
    o15 = b15["open"].to_numpy(float)
    c15 = b15["close"].to_numpy(float)
    ce_conf = pd.DatetimeIndex(ce["confirm_time"]).asi8
    ce_ext = pd.DatetimeIndex(ce["extreme_time"]).asi8
    ce_cct = pd.DatetimeIndex(ce["conf_close_time"]).asi8
    ce_sgn = ce["sgn"].to_numpy()
    order = np.argsort(ce_conf, kind="stable")
    bo, bc = b["open"].to_numpy(float), b["close"].to_numpy(float)
    bct = pd.DatetimeIndex(b["close_time"])
    pos_of = b.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    rows = []
    for r, p in zip(c2.itertuples(index=False), pos_of):
        if p < 1:
            continue
        s = sgn = 1 if r.direction == "bullish" else -1
        S = b.index[p].value
        E = bct[p].value
        lo = np.searchsorted(ce_conf[order], S, side="left")
        hi = np.searchsorted(ce_conf[order], E, side="left")
        cand = order[lo:hi]
        cand = cand[(ce_sgn[cand] == s) & (ce_ext[cand] >= S) & (ce_cct[cand] <= E)]
        if not len(cand):
            continue
        j = cand[np.argmin(ce_cct[cand])]
        sp, ep = int(ce["s_pos"].iloc[j]), int(ce["e_pos"].iloc[j])
        bh = max(o15[sp:ep + 1].max(), c15[sp:ep + 1].max())
        bl = min(o15[sp:ep + 1].min(), c15[sp:ep + 1].min())
        # C1's opposing series (down-close for a bullish C2) ending at C1
        k = p - 1
        opp = (lambda q: bc[q] < bo[q]) if sgn > 0 else (lambda q: bc[q] > bo[q])
        series_open = np.nan
        if opp(k):
            st = k
            while st > 0 and opp(st - 1) and (k - st + 1) < 10:
                st -= 1
            series_open = bo[st]
        rows.append((b.index[p], bct[p], sgn, r.open, r.high, r.low, r.close,
                     bo[k], float(b["high"].iloc[k]), float(b["low"].iloc[k]), bc[k],
                     series_open, (bh + bl) / 2.0, pd.Timestamp(ce_cct[j], tz="UTC")))
    out = pd.DataFrame(rows, columns=cols)
    if out.empty:
        return out
    dup = out.duplicated("c2_start", keep=False)          # two-sided C2 with both CISDs
    return out[~dup].reset_index(drop=True)
