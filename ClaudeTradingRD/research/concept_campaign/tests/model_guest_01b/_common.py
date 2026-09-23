"""Shared helpers for batch model_guest_01b (guest-voice model concepts).

Everything here is PURE (M1 slice in -> frame out) so probe_lookahead can re-run it
on truncated data. Daily bars are the 18:00-NY trading day (concept_lab default).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from concept_lab.data import utc_ns  # noqa: E402

STUB_MIN_M1 = 600           # a "day" with fewer M1 bars is a data-hole stub (README trap 6)
ATR_N = 20                  # trailing days for the "average daily range"


def daily(m1: pd.DataFrame) -> pd.DataFrame:
    """Completed, non-stub daily bars built from the slice, with derived columns.

    `adr` = mean range of the ATR_N days ending with this day (known at its close).
    `wd` = weekday of the session date (Mon=0), `wk` = session-week id (Monday date).
    """
    d = cl.build_bars(m1, "1D").copy()
    # An in-progress last bar keeps its nominal close_time (> the slice end), so any
    # event stamped at it falls outside every probe window; nothing is read from it.
    d = d[d["n_m1"] >= STUB_MIN_M1]
    d["rng"] = d["high"] - d["low"]
    d["adr"] = d["rng"].rolling(ATR_N, min_periods=ATR_N).mean()
    sd = cl.session_date(d.index)
    d["sdate"] = sd
    d["wd"] = sd.dayofweek
    d["wk"] = sd - pd.to_timedelta(sd.dayofweek, unit="D")
    return d


def swings_confirmed(b: pd.DataFrame, left: int = 2, right: int = 2) -> pd.DataFrame:
    """Fractal swings with the CLOSE time of the confirming bar (not its start)."""
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    n = len(b)
    ish = np.zeros(n, bool)
    isl = np.zeros(n, bool)
    for i in range(left, n - right):
        if (h[i - left:i] < h[i]).all() and (h[i + 1:i + 1 + right] <= h[i]).all():
            ish[i] = True
        if (l[i - left:i] > l[i]).all() and (l[i + 1:i + 1 + right] >= l[i]).all():
            isl[i] = True
    ct = pd.DatetimeIndex(b["close_time"])
    conf = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    idx = np.arange(n)
    ok = idx + right < n
    conf[ok] = ct.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()[idx[ok] + right]
    return pd.DataFrame({"sh": ish, "sl": isl, "high": h, "low": l,
                         "conf": pd.DatetimeIndex(conf).tz_localize("UTC")}, index=b.index)


def regime_null_fn(t_event: pd.DatetimeIndex, t_pool: pd.DatetimeIndex, y_pool: np.ndarray,
                   window_days: float = 30.0, exclude_self: bool = True):
    """Null for a per-day rate: the outcome of a random OTHER pool day within
    +/- window_days of each event (a regime-matched base rate). Returns null_fn."""
    tp = utc_ns(t_pool)
    te = utc_ns(t_event)
    ok = ~np.isnan(y_pool)
    tp, yp = tp[ok], y_pool[ok]
    w = np.int64(window_days * 86400e9)
    lo = np.searchsorted(tp, te - w, side="left")
    hi = np.searchsorted(tp, te + w, side="right")
    self_pos = np.searchsorted(tp, te, side="left")
    has_self = (self_pos < len(tp)) & (tp[np.minimum(self_pos, len(tp) - 1)] == te)

    def null_fn(rng, k):
        span = hi - lo - (has_self & exclude_self).astype(int)
        out = np.full(len(te), np.nan)
        good = span > 0
        r = (rng.random(len(te)) * np.maximum(span, 1)).astype(np.int64)
        j = lo + r
        if exclude_self:
            j = np.where(has_self & (j >= self_pos), j + 1, j)
        out[good] = yp[np.clip(j[good], 0, len(yp) - 1)]
        return out

    return null_fn


def cisd_1h(m1: pd.DataFrame) -> pd.DataFrame:
    """Phase-3 locked rung-0 book: bare 1h CISD (series_open, 2/2 swing, max_wait 3),
    decide at the confirming bar's close, stop at the protected swing, 2R."""
    from detectors.cisd import cisd_events
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})


# ── Jokerszn daily order flow (JABOO4LYNjQ) ──────────────────────────────────────
OF_FVG_LIFE = 60            # trading days an unfilled daily FVG stays a live PD array


def daily_fvgs(d: pd.DataFrame) -> pd.DataFrame:
    """3-bar daily FVGs, stamped at the close of the THIRD bar (positional `k`)."""
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    n = len(d)
    rows = []
    for k in range(2, n):
        if l[k] > h[k - 2]:
            rows.append((k, 1, h[k - 2], l[k]))
        elif h[k] < l[k - 2]:
            rows.append((k, -1, h[k], l[k - 2]))
    return pd.DataFrame(rows, columns=["k", "pol", "lo", "hi"])


def daily_orderflow(d: pd.DataFrame, life: int = OF_FVG_LIFE) -> pd.DataFrame:
    """Order-flow state at each daily close, from daily CLOSES reacting to daily FVGs.

    bullish event on day i: a live bearish FVG is closed ABOVE (disrespected/inverted),
      or a live bullish FVG is traded into (low <= its top) and the close holds at or
      above its mean threshold (respected).
    bearish event: the mirror. An FVG closed through is retired.
    state_i = sign of the latest day with a one-sided net event (conflicting days =
    'stuck', no update); 0 if none within `life` days.
    """
    f = daily_fvgs(d)
    n = len(d)
    c, h, l = d["close"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy()
    live = []                    # [k, pol, lo, hi]
    fi = 0
    fv = f.to_numpy() if len(f) else np.zeros((0, 4))
    state = np.zeros(n)
    bull_ev = np.zeros(n, bool)
    bear_ev = np.zeros(n, bool)
    cur = 0.0
    last = -10**9
    for i in range(n):
        # FVGs whose third bar is before i are live for day i's reaction
        while fi < len(fv) and fv[fi, 0] < i:
            live.append(list(fv[fi]))
            fi += 1
        keep = []
        b_ev = s_ev = False
        for g in live:
            k, pol, lo, hi = g
            if i - k > life:
                continue
            mt = 0.5 * (lo + hi)
            if pol < 0:          # bearish FVG (above price when formed)
                if c[i] > hi:
                    b_ev = True
                    continue     # inverted -> retired
                if h[i] >= lo and c[i] <= mt:
                    s_ev = True
            else:                # bullish FVG
                if c[i] < lo:
                    s_ev = True
                    continue
                if l[i] <= hi and c[i] >= mt:
                    b_ev = True
            keep.append(g)
        live = keep
        bull_ev[i], bear_ev[i] = b_ev, s_ev
        if b_ev and not s_ev:
            cur, last = 1.0, i
        elif s_ev and not b_ev:
            cur, last = -1.0, i
        state[i] = cur if i - last <= life else 0.0   # bounded memory
    return pd.DataFrame({"of_state": state, "of_bull_ev": bull_ev, "of_bear_ev": bear_ev},
                        index=d.index)


def consolidation_conditions(m1: pd.DataFrame, d: pd.DataFrame, overext_mult: float = 1.5,
                             eq_band: float = 0.10) -> pd.DataFrame:
    """Jokerszn's three consolidation triggers per completed day (same logic as
    consolidation-profile-conditions.py, returned for EVERY day)."""
    w = cl.build_bars(m1, "1W")
    pw = cl.asof(w, pd.DatetimeIndex(d["first_m1"]))
    pwh, pwl = pw["high"].to_numpy(), pw["low"].to_numpy()
    prev_hi_wk = d.groupby("wk")["high"].transform(lambda s: s.shift(1).cummax()).to_numpy()
    prev_lo_wk = d.groupby("wk")["low"].transform(lambda s: s.shift(1).cummin()).to_numpy()
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    took_h = (h > pwh) & ~(np.nan_to_num(prev_hi_wk, nan=-np.inf) > pwh)
    took_l = (l < pwl) & ~(np.nan_to_num(prev_lo_wk, nan=np.inf) < pwl)
    cond_htf = (took_h | took_l) & ~np.isnan(pwh)
    s = pd.Series(np.sign(d["close"].to_numpy() - d["open"].to_numpy()))
    three = ((s == s.shift(1)) & (s == s.shift(2)) & (s != 0)).to_numpy()
    rng = d["rng"].to_numpy()
    adr_before = pd.Series(rng).rolling(20, min_periods=20).mean().shift(2).to_numpy()
    big2 = (rng >= overext_mult * adr_before) & (np.roll(rng, 1) >= overext_mult * adr_before)
    big2[:1] = False
    cond_over = three | big2
    sw = swings_confirmed(d)
    ct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    conf = pd.DatetimeIndex(sw["conf"]).as_unit("ns").asi8
    H = np.full(len(d), np.nan)
    L = np.full(len(d), np.nan)
    for arr, flag, col in ((H, "sh", "high"), (L, "sl", "low")):
        idx = np.flatnonzero(sw[flag].to_numpy())
        if len(idx):
            cn = conf[idx]
            o = np.argsort(cn, kind="stable")
            p = np.searchsorted(cn[o], ct, side="right") - 1
            vals = sw[col].to_numpy()[idx][o]
            arr[:] = np.where(p >= 0, vals[np.clip(p, 0, None)], np.nan)
    width = H - L
    pos = (d["close"].to_numpy() - L) / np.where(width > 0, width, np.nan)
    cond_eq = (np.abs(pos - 0.5) <= eq_band) & (width > 0)
    return pd.DataFrame({"cond_htf": cond_htf, "cond_overext": cond_over, "cond_eq": cond_eq},
                        index=d.index)
