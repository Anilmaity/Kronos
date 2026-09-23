"""Shared, pure detector pieces for batch entry_own_01a (TTrades own-voice entry concepts).

Everything here is a pure function of the M1 frame it is given (bars are built with
cl.build_bars from the INPUT), so probe_lookahead can re-run it on truncated slices.
No module state, no reads of the cached full-span bars().

Locked phase-3 CISD configuration (meta/conjunction_preregistration.md §1.8):
  swing 2/2 fractal, level_rule series_open (first candle's open), min_series 1,
  max_wait 3 (the corpus's "1, 2, maybe three" speed preference), stop = protected
  swing (the extreme), target 2R, max hold 10 entry-TF bars.
POI gate (§4.1 / detectors.poi.poi_gate, phase-3 defaults) evaluated on the bars
up to and including the confirming bar ONLY, so its forward-looking 50%-body branch
can never read past the decision.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events      # noqa: E402
from detectors.poi import poi_gate          # noqa: E402

OHLC = ["open", "high", "low", "close"]


def cisd_with_poi(m1: pd.DataFrame, tf: str = "15min", level_rule: str = "series_open",
                  max_wait: int = 3, min_series: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Library CISD events on `tf` bars built from m1, annotated with the §4.1 POI gate.

    Returns (bars, events). events carries positional indices (ext_pos, conf_pos),
    confirm close time, and POI verdict/kind. No rows are dropped here.
    """
    b = cl.build_bars(m1, tf)
    cols = ["direction", "extreme_time", "extreme_price", "series_start", "series_end",
            "series_len", "level", "confirm_time", "confirm_close", "bars_waited",
            "protected_swing", "ext_pos", "conf_pos", "close_time", "poi_passed", "poi_kind"]
    if len(b) < 10:
        return b, pd.DataFrame(columns=cols)
    o = b[OHLC]
    ev = cisd_events(o, level_rule=level_rule, left=2, right=2, max_wait=max_wait,
                     min_series=min_series)
    if ev.empty:
        return b, pd.DataFrame(columns=cols)
    ev = ev.copy()
    ev["ext_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ev["conf_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    ev["close_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["conf_pos"].to_numpy()])
    passed, kind = [], []
    for e, j, d in zip(ev["ext_pos"].to_numpy(), ev["conf_pos"].to_numpy(),
                       ev["direction"].to_numpy()):
        sub = o.iloc[: j + 1]                       # nothing after the confirming bar
        r = poi_gate(sub, int(e), d, timeframe=tf, level_rule=level_rule)
        passed.append(bool(r.passed))
        kind.append(r.kind_used if r.kind_used else "none")
    ev["poi_passed"] = passed
    ev["poi_kind"] = kind
    return b, ev.reset_index(drop=True)


def to_trade_frame(ev: pd.DataFrame, rr: float = 2.0) -> pd.DataFrame:
    """CISD events -> harness trade frame (decide at the confirming bar's close)."""
    close = pd.DatetimeIndex(ev["close_time"])
    return pd.DataFrame({
        "decision_time": close,
        "available_at": close,
        "direction": np.where(ev["direction"].to_numpy() == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(dtype=float),
        "rr": float(rr),
    })


def empty_frame(cols) -> pd.DataFrame:
    out = pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})
    out["decision_time"] = pd.Series(dtype="datetime64[ns, UTC]")
    out["available_at"] = pd.Series(dtype="datetime64[ns, UTC]")
    return out[cols]


def htf_context(b_ltf: pd.DataFrame, m1: pd.DataFrame, htf: str = "4h") -> pd.DataFrame:
    """For every LTF bar: which HTF candle it sits in, that candle's open, and the two
    previous CLOSED HTF candles' OHLC (k-1, k-2), plus the in-candle running low/high
    up to and including this LTF bar. Uses only the HTF bars' own completed data for
    k-1/k-2 (their close_time <= this LTF bar's start) and LTF bars <= this one for
    the running extremes."""
    h = cl.build_bars(m1, htf)
    starts = h.index.to_numpy()
    lt = b_ltf.index.to_numpy()
    k = np.searchsorted(starts, lt, side="right") - 1          # HTF candle containing bar
    out = pd.DataFrame(index=b_ltf.index)
    valid = k >= 2
    kk = np.where(valid, k, 0)
    H = h[OHLC].to_numpy()
    hct = h["close_time"].to_numpy()
    out["htf_k"] = np.where(valid, k, -1)
    out["htf_start"] = pd.DatetimeIndex(starts[kk])
    out["htf_close_time"] = pd.DatetimeIndex(hct[kk])
    out["htf_open"] = np.where(valid, H[kk, 0], np.nan)
    for lag, tag in ((1, "p1"), (2, "p2")):
        idx = np.maximum(kk - lag, 0)
        for c, nm in enumerate(OHLC):
            out[f"{tag}_{nm}"] = np.where(valid, H[idx, c], np.nan)
        out[f"{tag}_close_time"] = pd.DatetimeIndex(hct[idx])
    # running in-candle extremes (LTF bars of the same HTF candle up to this bar)
    grp = pd.Series(k, index=b_ltf.index)
    out["run_low"] = b_ltf["low"].groupby(grp.to_numpy()).cummin().to_numpy()
    out["run_high"] = b_ltf["high"].groupby(grp.to_numpy()).cummax().to_numpy()
    out["valid"] = valid
    return out
