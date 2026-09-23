"""Shared, pure helpers for batch model_own_02b (no harness edits; every helper builds
from the M1 frame it is given so probe_lookahead sees exactly what the detectors read)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

TZ = "America/New_York"
# phase-3 locked CISD configuration (meta/conjunction_preregistration.md §1.8-1.13)
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
MIN_DAY_M1 = 600          # stub-session floor (README trap 6; the worked example uses >600)
GRID4H = "forex"


def complete_bars(m1, tf, grid4h=GRID4H):
    """Bars built from m1. A trailing in-progress bar is kept: anything decided on it is
    stamped at its nominal close_time (> the cut), which the probe window excludes."""
    return cl.build_bars(m1, tf, grid4h=grid4h).copy()


def daily(m1):
    d = complete_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1].copy()
    d["td"] = pd.DatetimeIndex(d["trading_day"])
    return d


def prev_day_levels(d, tds):
    """For each trading-day label, the last COMPLETE (non-stub) day strictly before it."""
    dtd = d["td"].to_numpy()
    q = pd.DatetimeIndex(tds).to_numpy()
    pos = np.searchsorted(dtd, q, side="left") - 1
    ok = pos >= 0
    p = np.clip(pos, 0, None)
    out = pd.DataFrame({"pdh": d["high"].to_numpy()[p], "pdl": d["low"].to_numpy()[p],
                        "pd_td": dtd[p]}, index=pd.DatetimeIndex(tds))
    out.loc[~ok, ["pdh", "pdl"]] = np.nan
    return out


def cisd_table(b):
    """CISD events on bars b with close-time stamps. dir +1/-1."""
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD_KW)
    cols = ["dir", "extreme_start", "extreme_close", "extreme_price", "t", "stop", "level",
            "confirm_close"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    ct = b["close_time"]
    out = pd.DataFrame({
        "dir": np.where(ev["direction"] == "bullish", 1, -1),
        "extreme_start": pd.DatetimeIndex(ev["extreme_time"]),
        "extreme_close": pd.DatetimeIndex(ct.loc[pd.DatetimeIndex(ev["extreme_time"])].to_numpy()),
        "extreme_price": ev["extreme_price"].astype(float).to_numpy(),
        "t": pd.DatetimeIndex(ct.loc[pd.DatetimeIndex(ev["confirm_time"])].to_numpy()),
        "stop": ev["protected_swing"].astype(float).to_numpy(),
        "level": ev["level"].astype(float).to_numpy(),
        "confirm_close": ev["confirm_close"].astype(float).to_numpy(),
    })
    for c in ("extreme_start", "extreme_close", "t"):
        out[c] = pd.DatetimeIndex(out[c]).tz_convert("UTC") if pd.DatetimeIndex(out[c]).tz \
            else pd.DatetimeIndex(out[c]).tz_localize("UTC")
    return out.sort_values("t", kind="stable").reset_index(drop=True)


def window_stats(m1, a, b, min_n=1):
    """Per trading day: o/h/l/c, n, last minute of M1 bars with NY clock in [a, b)."""
    mask = cl.in_window(m1.index, a, b)
    sub = m1[mask]
    td = cl.trading_day(sub.index)
    df = pd.DataFrame({"o": sub["open"].to_numpy(), "h": sub["high"].to_numpy(),
                       "l": sub["low"].to_numpy(), "c": sub["close"].to_numpy(),
                       "t": sub.index}, index=td)
    g = df.groupby(level=0, sort=True)
    out = g.agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                n=("o", "size"), first=("t", "min"), last=("t", "max"))
    return out[out["n"] >= min_n]


def ny_local(td, hhmm_minutes, day_offset=0):
    """UTC timestamp of NY wall clock `hhmm_minutes` on trading-day label td (+offset days)."""
    loc = pd.DatetimeIndex(td) + pd.Timedelta(days=day_offset) + pd.Timedelta(minutes=hhmm_minutes)
    return loc.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")


def session_end(times):
    """17:00 NY close of the trading day each time belongs to (day rolls at 18:00)."""
    td = cl.trading_day(times)
    return ny_local(td, 17 * 60, day_offset=1)


def mod(times):
    return cl.ny_minute_of_day(times)


def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)
