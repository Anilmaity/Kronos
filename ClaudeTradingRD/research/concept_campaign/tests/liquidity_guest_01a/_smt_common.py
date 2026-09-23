"""Shared helpers for batch liquidity_guest_01a (SMT / PSP concepts, GxTradez).

Correlate data: OANDA XAG_USD H1 (and EUR_USD H1 for the XAU/EUR triad member),
from m3_scalper/*_full.parquet — the same files phase 3 used via
backtest_conjunction.load_correlate(). Both series are UTC-hour left-labelled.

Everything here is PURE in the gold M1 frame it is given: the correlate is inner-joined on
the gold H1 labels built from that frame, so a probe that truncates M1 truncates
the correlate too. Every event is stamped at a bar close_time.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

RD = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD")
_RAW: dict = {}
H1 = pd.Timedelta(hours=1)


def _raw(name: str) -> pd.DataFrame:
    if name not in _RAW:
        x = pd.read_parquet(RD / "m3_scalper" / name)
        if "time" in x.columns:
            x = x.set_index("time")
        x.index = pd.to_datetime(x.index, utc=True)
        _RAW[name] = x[["open", "high", "low", "close"]].astype("float64").sort_index()
    return _RAW[name]


def correlate_h1(which: str, cutoff: pd.Timestamp) -> pd.DataFrame:
    x = _raw({"xag": "xag_h1_full.parquet", "eur": "eur_h1_full.parquet"}[which])
    return x[x.index + H1 <= cutoff]


def pair_bars(m1: pd.DataFrame, tf: str = "1h", other: str = "xag") -> pd.DataFrame:
    """Gold and a correlate on one grid. Columns g_* (gold), s_* (other), close_time.

    tf '1h': inner join of complete gold H1 bars and complete correlate H1 bars.
    tf '4h': the joined H1 bars aggregated into the gold FOREX-grid 4H buckets
    (17/21/01/05/09/13 NY); only buckets whose close <= cutoff are kept.
    other: 'xag' (silver) or 'xaueur' (gold/EURUSD, see xaueur_h1).
    """
    # No completeness cut: the last gold bar of a truncated slice may be partial,
    # but anything computed on it is stamped at its close_time (> the cut), so it
    # never enters an in-window event. The correlate is joined on gold's labels,
    # so it never extends past gold's last bar either.
    cutoff = m1.index[-1] + H1
    g = cl.build_bars(m1, "1h")[["open", "high", "low", "close", "close_time"]]
    if other == "xag":
        s = correlate_h1("xag", cutoff)
    elif other == "xaueur":
        s = xaueur_h1(g, correlate_h1("eur", cutoff))
    else:
        raise ValueError(other)
    idx = g.index.intersection(s.index)
    G, S = g.loc[idx], s.loc[idx]
    out = pd.DataFrame({"g_open": G.open, "g_high": G.high, "g_low": G.low, "g_close": G.close,
                        "s_open": S.open, "s_high": S.high, "s_low": S.low, "s_close": S.close,
                        "close_time": G.close_time}, index=idx)
    if tf == "1h":
        return out
    if tf != "4h":
        raise ValueError(tf)
    b4 = cl.build_bars(m1, "4h")          # forex grid (default), left-labelled
    starts, ends = b4.index, b4["close_time"].to_numpy()
    pos = starts.searchsorted(out.index, side="right") - 1
    ok = pos >= 0
    ok[ok] = out.index[ok] < ends[pos[ok]]
    o = out[ok].copy()
    o["bucket"] = pos[ok]
    agg = o.groupby("bucket").agg(
        g_open=("g_open", "first"), g_high=("g_high", "max"), g_low=("g_low", "min"),
        g_close=("g_close", "last"), s_open=("s_open", "first"), s_high=("s_high", "max"),
        s_low=("s_low", "min"), s_close=("s_close", "last"))
    agg.index = starts[agg.index.to_numpy()]
    agg["close_time"] = b4["close_time"].reindex(agg.index).to_numpy()
    return agg


def xaueur_h1(gold_h1: pd.DataFrame, eur_h1: pd.DataFrame) -> pd.DataFrame:
    """XAU/EUR on H1 from gold H1 and EURUSD H1 (declared approximation).

    open = g_open/e_open, close = g_close/e_close; the intrabar extremes use the
    EUR bar's mid ((e_high+e_low)/2) because the within-hour timing of the two
    extremes is unknown: high = max(open, close, g_high/e_mid), low likewise.
    """
    idx = gold_h1.index.intersection(eur_h1.index)
    g, e = gold_h1.loc[idx], eur_h1.loc[idx]
    mid = (e.high + e.low) / 2
    o, c = g.open / e.open, g.close / e.close
    h = np.maximum(np.maximum(o, c), g.high / mid)
    lo = np.minimum(np.minimum(o, c), g.low / mid)
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=idx)


def smt_events(P: pd.DataFrame, lookback: int = 20, left: int = 2, right: int = 2
               ) -> pd.DataFrame:
    """SMT at a shared swing moment (phase-3 knobs: lookback 20, fractal 2/2).

    For every bar p that is a confirmed fractal swing high (low) in EITHER asset,
    each asset's level is its own high (low) at p. Scanning forward, the first
    asset to trade beyond its level while the other's running extreme since p has
    not is the SWEEPER; the other HELD -> SMT at that bar j. Both beyond on the
    same bar -> no SMT. Events are only emitted at j >= p+right+1 (the swing is
    confirmed); if either asset trades beyond during p+1..p+right the swing is
    skipped. direction = reversal direction: -1 at highs (bearish), +1 at lows.
    """
    n = len(P)
    rows = []
    gs = swing_points(P.rename(columns={"g_high": "high", "g_low": "low"})[["high", "low"]],
                      left, right)
    ss = swing_points(P.rename(columns={"s_high": "high", "s_low": "low"})[["high", "low"]],
                      left, right)
    for hi_side in (True, False):
        col = "swing_high" if hi_side else "swing_low"
        cand = np.flatnonzero(gs[col].to_numpy() | ss[col].to_numpy())
        ga = P["g_high" if hi_side else "g_low"].to_numpy()
        sa = P["s_high" if hi_side else "s_low"].to_numpy()
        sgn = 1.0 if hi_side else -1.0            # compare sgn*x > sgn*level
        for p in cand:
            lg, ls = ga[p], sa[p]
            pre_end = min(n, p + right + 1)
            if (sgn * ga[p + 1:pre_end] > sgn * lg).any() or \
               (sgn * sa[p + 1:pre_end] > sgn * ls).any():
                continue
            for j in range(p + right + 1, min(n, p + right + 1 + lookback)):
                bg = sgn * ga[j] > sgn * lg
                bs = sgn * sa[j] > sgn * ls
                if bg and bs:
                    break
                if bg or bs:
                    rows.append({"j": j, "p": p, "direction": -1 if hi_side else 1,
                                 "sweeper": "gold" if bg else "other",
                                 "lvl_g": lg, "lvl_s": ls})
                    break
    if not rows:
        return pd.DataFrame(columns=["j", "p", "direction", "sweeper", "lvl_g", "lvl_s"])
    ev = pd.DataFrame(rows).drop_duplicates(subset=["j", "direction"])
    return ev.sort_values(["j", "direction"]).reset_index(drop=True)


def smt_next_bar_book(m1: pd.DataFrame, tf: str = "1h", rr: float = 2.0) -> pd.DataFrame:
    """Baseline for fake-smt-strength-switch and two-stage-smt (gold vs silver, 1H).

    An SMT prints at bar j (see smt_events); every event is DECIDED at the close
    of bar j+1, so both the 'genuine' and the 'stage-2' flags are known for every
    row at the same moment and the two arms share one entry convention.
    Trade gold in the SMT's reversal direction; stop = gold's extreme from the
    swing bar p through j+1; target rr.

      genuine   the sweeping asset has closed back inside its level by j+1 (close
                of j or j+1 on the reversal side of its level) AND the held asset
                has not traded beyond its own level through j+1 (the SMT is
                intact, no catch-up) -> fake-smt-strength-switch's 'genuine'.
      stage2    immediately-following confirmation on bar j+1: a PSP (gold and
                silver close opposite colours on j+1) OR an SMT between candle 2
                (bar j) and candle 3 (bar j+1): exactly one asset trades beyond its
                own bar-j extreme on the SMT side -> two-stage-smt.
    """
    P = pair_bars(m1, tf, "xag")
    ev = smt_events(P)
    n = len(P)
    A = {k: P[k].to_numpy() for k in ("g_open", "g_high", "g_low", "g_close",
                                        "s_open", "s_high", "s_low", "s_close")}
    ct = pd.DatetimeIndex(P.close_time)
    rows = []
    for r in ev.itertuples():
        j, p = int(r.j), int(r.p)
        k = j + 1
        if k >= n:
            continue
        hi = r.direction == -1
        sgn = 1.0 if hi else -1.0
        side = "high" if hi else "low"
        gx, sx = A["g_" + side], A["s_" + side]
        ext = gx[p:k + 1].max() if hi else gx[p:k + 1].min()
        if not sgn * (ext - A["g_close"][k]) > 0:
            continue
        if r.sweeper == "gold":
            sw_close, sw_lvl, held_x, held_lvl = A["g_close"], r.lvl_g, sx, r.lvl_s
        else:
            sw_close, sw_lvl, held_x, held_lvl = A["s_close"], r.lvl_s, gx, r.lvl_g
        back_inside = (sgn * (sw_close[j:k + 1] - sw_lvl) < 0).any()
        held_intact = not (sgn * held_x[p + 1:k + 1] > sgn * held_lvl).any()
        dg = np.sign(A["g_close"][k] - A["g_open"][k])
        ds = np.sign(A["s_close"][k] - A["s_open"][k])
        psp = bool(dg * ds < 0)
        g_beyond = sgn * gx[k] > sgn * gx[j]
        s_beyond = sgn * sx[k] > sgn * sx[j]
        smt23 = bool(g_beyond != s_beyond)
        rows.append({"decision_time": ct[k], "available_at": ct[k],
                     "direction": int(r.direction), "stop_px": float(ext), "rr": rr,
                     "sweeper": r.sweeper, "genuine": bool(back_inside and held_intact),
                     "stage2": bool(psp or smt23), "psp": psp, "smt23": smt23})
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "sweeper",
            "genuine", "stage2", "psp", "smt23"]
    out = pd.DataFrame(rows, columns=cols)
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))
