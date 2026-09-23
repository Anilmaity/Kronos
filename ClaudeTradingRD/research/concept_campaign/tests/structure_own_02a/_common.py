"""Shared helpers for batch structure_own_02a (structure, TTrades own voice).

Everything here is PURE in the gold M1 frame it is given (probe-safe): bars are built
from the input frame, and the silver correlate is cut at the input frame's last minute
and inner-joined on gold's own 1h labels.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402,F401

RD = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD")
H1 = pd.Timedelta(hours=1)
_XAG = {}


# ── the CISD-with-speed detector used by several concepts ─────────────────────
def cisd_speed(b: pd.DataFrame, poi_lookback: int = 20, left: int = 2, max_k: int = 10,
               max_series: int = 10) -> pd.DataFrame:
    """Closure through the opening price of the opposing series, with its speed.

    Bullish (mirror for bearish), evaluated bar by bar, decided at the closing bar j:
      extreme pos : low[pos] < low of the `left` bars before it AND low[pos] is the
                    lowest low of the `poi_lookback` bars before it (the reach takes
                    out the short-term range low = the POI / swept liquidity)
      series      : the contiguous run of down-close candles ending at pos (or ending
                    <= 2 bars before pos when pos itself is the turn candle), <= 10 long
      level       : OPEN of the FIRST candle of the series (method_spec §4.2 default)
      closure     : first bar j in (pos, pos+max_k] with close[j] > level; abandoned if
                    any bar in (pos, j] trades below low[pos] (a new extreme)
    Returns one row per closure: j, pos, dir (+1/-1), k = j - pos (candles from the
    extreme to the closing candle, inclusive of the closing candle), approach =
    series length, extreme, level. Rows sharing (j, dir) keep the most extreme.
    """
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(b)
    rows = []
    for bull in (True, False):
        x = l if bull else -h           # work in "low" space: bearish = negated highs
        oo, cc = (o, c) if bull else (-o, -c)
        opp = cc < oo                    # down-close candles (for bull)
        for pos in range(max(left, poi_lookback), n - 1):
            xp = x[pos]
            if not (x[pos - left:pos] > xp).all():
                continue
            if not (x[pos - poi_lookback:pos] > xp).all():
                continue
            end = pos
            while end > 0 and not opp[end]:
                end -= 1
                if pos - end > 2:
                    end = -1
                    break
            if end < 0 or not opp[end]:
                continue
            start = end
            while start > 0 and opp[start - 1] and (end - start + 1) < max_series:
                start -= 1
            lvl = oo[start]
            for j in range(pos + 1, min(n, pos + max_k + 1)):
                if x[j] < xp:
                    break
                if cc[j] > lvl:
                    rows.append((j, pos, 1 if bull else -1, j - pos, end - start + 1,
                                 xp if bull else -xp, lvl if bull else -lvl))
                    break
    ev = pd.DataFrame(rows, columns=["j", "pos", "dir", "k", "approach", "extreme", "level"])
    if ev.empty:
        return ev
    ev["_ord"] = np.where(ev["dir"] > 0, ev["extreme"], -ev["extreme"])
    ev = (ev.sort_values(["j", "dir", "_ord"]).drop_duplicates(["j", "dir"], keep="first")
          .drop(columns="_ord").sort_values(["j", "dir"]).reset_index(drop=True))
    return ev


# ── silver (XAG_USD H1, OANDA) ────────────────────────────────────────────────
def _xag_raw() -> pd.DataFrame:
    if "h1" not in _XAG:
        x = pd.read_parquet(RD / "m3_scalper" / "xag_h1_full.parquet")
        x.index = pd.to_datetime(x.index, utc=True)
        _XAG["h1"] = x[["open", "high", "low", "close"]].astype("float64").sort_index()
    return _XAG["h1"]


def pair_1h(m1: pd.DataFrame) -> pd.DataFrame:
    """Gold 1h bars (built from m1) inner-joined with complete silver H1 bars.

    Columns: open/high/low/close/close_time (gold) and s_open/s_high/s_low/s_close.
    Silver is cut so that no silver bar closes after the last gold minute + 1h.
    """
    g = cl.build_bars(m1, "1h")[["open", "high", "low", "close", "close_time"]]
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = _xag_raw()
    s = s[s.index + H1 <= cutoff + H1]
    idx = g.index.intersection(s.index)
    G, S = g.loc[idx], s.loc[idx]
    out = G.copy()
    for k in ("open", "high", "low", "close"):
        out["s_" + k] = S[k].to_numpy()
    return out


def summary(res: dict) -> str:
    keys = ("test_type", "verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
            "mde", "ties", "ctrl_overlap", "exposure_bars", "halves", "gate_rate")
    out = []
    for k in keys:
        if k in res:
            v = res[k]
            if isinstance(v, float):
                v = round(v, 4)
            out.append(f"  {k}: {v}")
    return "\n".join(out)
