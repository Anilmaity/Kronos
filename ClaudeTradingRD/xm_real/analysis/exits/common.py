"""Shared loaders for the XM Real exits study. All times UTC.

Prices: OANDA XAU_USD S5 bid/ask shifted by the measured XM basis (basis.json, written by
01_basis.py) so they are XM-GOLD-equivalent quotes. Longs exit on bid, shorts on ask.
Read-only on the shared inputs in xm_real/.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
XM = HERE.parents[1]
RES = HERE / "results"
RES.mkdir(exist_ok=True)
USD_PER_PT = 4.0          # 0.04 lots x 100 oz: 1.00 of price = $4 (check: 3.82 pts -> $15.28 in deals)
BAR_NS = 5 * 10**9
PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python"


def ns(s):
    """tz-aware datetime Series -> int64 nanoseconds."""
    return pd.to_datetime(s, utc=True, format="ISO8601").dt.tz_convert(None).values.astype("datetime64[ns]").astype("int64")


def load_deals():
    d = pd.read_csv(XM / "deals.csv")
    d["time"] = pd.to_datetime(d.time, utc=True, format="ISO8601")
    d["t"] = ns(d.time)
    return d.sort_values("t").reset_index(drop=True)


def load_trades():
    t = pd.read_csv(XM / "trades.csv")
    for c in ("open_time", "close_time"):
        t[c] = pd.to_datetime(t[c], utc=True, format="ISO8601")
    t["t0"], t["t1"] = ns(t.open_time), ns(t.close_time)
    t["sgn"] = t.side.map({"BUY": 1, "SELL": -1})
    t["reason"] = t.exit_reason.str.replace("DEAL_REASON_", "")
    t["closeby"] = t.exit_entry_type.eq("DEAL_ENTRY_OUT_BY")
    # true realised points: trades.csv `pts` double-counts the 4 close-by pairs (each leg's "exit" is the
    # other leg's entry). profit/(volume*100) books each pair's locked loss once.
    t["pts_real"] = t.profit / (t.volume * 100)
    t["tp_dist"] = (t.tp - t.entry) * t.sgn
    return t.sort_values("t0").reset_index(drop=True)


def load_basis():
    f = HERE / "basis.json"
    return json.load(open(f)) if f.exists() else {"ask": 0.0, "bid": 0.0}


class Quotes:
    """XM-equivalent S5 quotes as numpy arrays. T = bar OPEN time (ns); a bar covers [T, T+5s)."""

    def __init__(self, basis=None):
        b = load_basis() if basis is None else basis
        s = pd.read_parquet(XM / "xau_s5_2026-11-03_now_ba.parquet")
        self.T = ns(s.time)
        self.px = {side: {k: s[f"{side}_{n}"].values + b[side] for k, n in zip("ohlc", ("open", "high", "low", "close"))}
                   for side in ("bid", "ask")}
        self.n = len(self.T)

    def at(self, t, side):
        """Quote at instant t: linear interpolation open->close inside the bar containing t."""
        i = np.clip(np.searchsorted(self.T, t, side="right") - 1, 0, self.n - 1)
        f = np.clip((t - self.T[i]) / BAR_NS, 0, 1)
        o, c = self.px[side]["o"][i], self.px[side]["c"][i]
        return o + (c - o) * f

    def path(self, sgn, entry, i0, i1=None):
        """Signed excursions (pts, + = favourable) of a position on its EXIT-side quote over bars [i0, i1).
        Returns fav_hi, adv_lo, open, close."""
        p = self.px["bid" if sgn > 0 else "ask"]
        sl = slice(i0, i1)
        if sgn > 0:
            return p["h"][sl] - entry, p["l"][sl] - entry, p["o"][sl] - entry, p["c"][sl] - entry
        return entry - p["l"][sl], entry - p["h"][sl], entry - p["o"][sl], entry - p["c"][sl]

    def first_bar_after(self, t):
        """Index of the first bar that OPENS at or after t (the entry bar itself is skipped: its high/low
        contain pre-entry ticks)."""
        return int(np.searchsorted(self.T, t, side="left"))


def stats(pts):
    """Summary of an array of per-trade points (flat 0.04 lots)."""
    pts = np.asarray(pts, float)
    w, l = pts[pts > 0], pts[pts < 0]
    return dict(n=len(pts), total_pts=round(pts.sum(), 1), usd_004=round(pts.sum() * USD_PER_PT),
                win_pct=round(100 * (pts > 0).mean(), 1) if len(pts) else np.nan,
                pf=round(w.sum() / -l.sum(), 2) if len(l) and l.sum() < 0 else np.inf,
                avg_win=round(w.mean(), 2) if len(w) else 0.0, avg_loss=round(l.mean(), 2) if len(l) else 0.0,
                worst_trade=round(pts.min(), 1) if len(pts) else np.nan)
