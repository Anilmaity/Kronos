"""Shared, pure detectors for batch liquidity_own_02a (the SMT family + IRL).

Correlate: XAG_USD H1 (OANDA practice feed, 2010-01-03 -> 2026-07-23), the file the
phase-3 run used for its SMT gate (`backtest_conjunction.load_correlate`, which
prefers `xag_h1_full.parquet`). It is the ONLY correlate resolution the campaign
holds, so every SMT here is an HOURLY SMT (the corpus prefers 15m but calls SMT
fractal; declared in each script).

Every function takes a gold M1 slice and builds its bars from that slice, and the
silver frame is cut to bars that CLOSED by the slice's last M1 close, so
`probe_lookahead` sees exactly what a live reader would have seen.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                       # noqa: E402
from detectors.bias import smt_events          # noqa: E402
from detectors.cisd import cisd_events         # noqa: E402

XAG_PATH = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet")
H1 = pd.Timedelta(hours=1)
OHLC = ["open", "high", "low", "close"]

SMT_LOOKBACK = 20      # phase3: detectors.bias.smt_events default used by the phase-3 SMT gate
SWING = 2              # phase3: 2/2 fractal swings (conjunction pre-registration §1.8)
ATR_N = 14             # declared-before-run

_XAG: pd.DataFrame | None = None


def xag_h1() -> pd.DataFrame:
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        _XAG = x[OHLC].astype("float64").sort_index()
        _XAG = _XAG[~_XAG.index.duplicated(keep="first")]
    return _XAG


def pair_h1(m1: pd.DataFrame, silver_cut: str = "closed"
            ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gold 1h bars from the slice and the silver 1h bars that go with them.

    silver_cut="closed": silver bars whose nominal close <= the slice's last M1 close.
      Too strict at an early venue close (Friday 17:00 NY with the last M1 at 16:58):
      the silver bar closing at the halt is dropped on a cut but kept on the full data.
    silver_cut="gold_last": silver bars starting no later than the slice's last gold
      bar. A silver bar paired with an in-progress gold bar can only produce an event
      stamped at that bar's close (> the cut), never an earlier one, because every
      detector here reads bars <= j for an event at j.
    """
    g = cl.build_bars(m1, "1h")
    if g.empty:
        return g, xag_h1().iloc[:0]
    first = pd.DatetimeIndex(m1.index).tz_convert("UTC")[0].floor("h")
    x = xag_h1()
    if silver_cut == "closed":
        last_close = pd.DatetimeIndex(m1.index).tz_convert("UTC")[-1] + pd.Timedelta(minutes=1)
        x = x[(x.index >= first) & (x.index + H1 <= last_close)]
    elif silver_cut == "gold_last":
        x = x[(x.index >= first) & (x.index <= g.index[-1])]
    else:
        raise ValueError(silver_cut)
    return g, x


def atr(b: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    """Simple-mean true range over the last n bars, known at each bar's close."""
    pc = b["close"].shift(1)
    tr = pd.concat([b["high"] - b["low"], (b["high"] - pc).abs(),
                    (b["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def smt_frame(m1: pd.DataFrame, silver_cut: str = "closed") -> pd.DataFrame:
    """Hourly gold/silver SMTs (bias.smt_events) with the gold context at bar j.

    Columns: time (bar j start), decision_time (= gold bar j close), direction (+1/-1),
    swept_by, held_by, ref_level_swept, ref_level_held, invalidation, gold_close,
    atr, reclaim (the sweeping asset's bar-j close is back beyond its swept level),
    gold_level (gold's own reference level: held level if gold held, swept level if gold swept).
    """
    g, x = pair_h1(m1, silver_cut)
    cols = ["time", "decision_time", "direction", "swept_by", "held_by",
            "ref_level_swept", "ref_level_held", "invalidation", "gold_close",
            "atr", "reclaim", "gold_level"]
    if len(g) < 40 or len(x) < 40:
        return pd.DataFrame(columns=cols)
    ev = smt_events(g[OHLC], x[OHLC], lookback=SMT_LOOKBACK, left=SWING, right=SWING,
                    names=("gold", "xag"))
    if ev.empty:
        return pd.DataFrame(columns=cols)
    a = atr(g)
    t = pd.DatetimeIndex(ev["time"])
    out = pd.DataFrame({
        "time": t,
        "decision_time": pd.DatetimeIndex(g.loc[t, "close_time"]),
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "swept_by": ev["swept_by"].to_numpy(),
        "held_by": ev["held_by"].to_numpy(),
        "ref_level_swept": ev["ref_level_swept"].to_numpy(float),
        "ref_level_held": ev["ref_level_held"].to_numpy(float),
        "invalidation": ev["invalidation"].to_numpy(float),
        "gold_close": g.loc[t, "close"].to_numpy(float),
        "atr": a.loc[t].to_numpy(float),
    })
    # close of the SWEEPING asset on bar j, back beyond its swept level
    sw_close = np.where(out["swept_by"] == "gold", g.loc[t, "close"].to_numpy(float),
                        x.reindex(t)["close"].to_numpy(float))
    bull = out["direction"].to_numpy() == 1
    out["reclaim"] = np.where(bull, sw_close > out["ref_level_swept"],
                              sw_close < out["ref_level_swept"])
    out["gold_level"] = np.where(out["held_by"] == "gold", out["ref_level_held"],
                                 out["ref_level_swept"])
    out = out[np.isfinite(out["atr"]) & (out["atr"] > 0)]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def cisd_1h(m1: pd.DataFrame) -> pd.DataFrame:
    """The phase-3 rung-0 1h CISD book (examples.detect_cisd), as the 'model'."""
    b = cl.build_bars(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[OHLC], level_rule="series_open", left=2, right=2,
                     max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0})


def prior_match(t_book: pd.DatetimeIndex, d_book: np.ndarray,
                t_other: pd.DatetimeIndex, d_other: np.ndarray,
                window: pd.Timedelta) -> np.ndarray:
    """True where an `other` event of the same direction has decision time in
    [t_book - window, t_book] — i.e. was already known when the book decided."""
    out = np.zeros(len(t_book), bool)
    for d in (1, -1):
        o = np.sort(cl.data.utc_ns(t_other[d_other == d]))
        sel = np.flatnonzero(d_book == d)
        if not len(o) or not len(sel):
            continue
        tb = cl.data.utc_ns(t_book[sel])
        hi = np.searchsorted(o, tb, side="right")
        lo = np.searchsorted(o, tb - window.value, side="left")
        out[sel] = hi > lo
    return out
