"""Shared detectors for batch entry_guest_01a (AP's GB levels; $niper / Trader T entries).

Every function is pure: M1 slice in -> frame out, bars built from the slice, and
every decision uses only bars whose close is <= the decision time.  Fills of resting
limits are resolved on M1: the order is live from the first M1 bar starting at or
after the moment it could be placed, and the fill bar's CLOSE is the decision time
(the harness enters at the next M1 open).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

NS_MIN = np.int64(60 * 10 ** 9)


# ── primitives ────────────────────────────────────────────────────────────────
def swing_flags(h: np.ndarray, l: np.ndarray, left: int = 2, right: int = 2):
    """Fractal swings: high[j] > the `left` highs before and >= the `right` after.
    Known at the close of bar j+right."""
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n < left + right + 1:
        return sh, sl
    core = slice(left, n - right)
    okh = np.ones(n - left - right, bool)
    okl = np.ones(n - left - right, bool)
    hc, lc = h[core], l[core]
    for k in range(1, left + 1):
        okh &= hc > h[left - k:n - right - k]
        okl &= lc < l[left - k:n - right - k]
    for k in range(1, right + 1):
        okh &= hc >= h[left + k:n - right + k]
        okl &= lc <= l[left + k:n - right + k]
    sh[core] = okh
    sl[core] = okl
    return sh, sl


def m1_arrays(m1: pd.DataFrame) -> dict:
    return {"t": cl.data.utc_ns(m1.index).view("int64"), "o": m1["open"].to_numpy(float),
            "h": m1["high"].to_numpy(float), "l": m1["low"].to_numpy(float),
            "c": m1["close"].to_numpy(float)}


def bars_arr(b: pd.DataFrame) -> dict:
    return {"start": cl.data.utc_ns(b.index).view("int64"),
            "close_t": cl.data.utc_ns(b["close_time"]).view("int64"),
            "o": b["open"].to_numpy(float), "h": b["high"].to_numpy(float),
            "l": b["low"].to_numpy(float), "c": b["close"].to_numpy(float)}


def to_utc(ns) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(ns, "int64").astype("datetime64[ns]")).tz_localize("UTC")


# ── AP: valid structure flips ─────────────────────────────────────────────────
def structure_flips(b: dict, left: int = 2, right: int = 2) -> pd.DataFrame:
    """Close beyond the most recent confirmed, unbroken swing.  A FLIP is such a
    break against the direction of the previous break.  Strong extreme = the most
    extreme price between the broken swing and the flip bar; opposing extreme at
    the flip = the flip-leg extreme from the strong extreme through the flip bar.
    `cancel_t` = close time of the next opposite flip (or int64 max)."""
    h, l, c = b["h"], b["l"], b["c"]
    n = len(h)
    sh, sl = swing_flags(h, l, left, right)
    act_h = act_l = -1          # bar index of the active swing
    state = 0
    rows = []
    for i in range(n):
        if act_h >= 0 and c[i] > h[act_h]:
            if state == -1:
                seg = l[act_h + 1:i + 1]
                li = act_h + 1 + int(np.argmin(seg))
                rows.append((i, 1, li, l[li], float(h[li:i + 1].max())))
            state = 1
            act_h = -1
        if act_l >= 0 and c[i] < l[act_l]:
            if state == 1:
                seg = h[act_l + 1:i + 1]
                hi = act_l + 1 + int(np.argmax(seg))
                rows.append((i, -1, hi, h[hi], float(l[hi:i + 1].min())))
            state = -1
            act_l = -1
        j = i - right                     # swing confirmed at this bar's close
        if j >= left:
            if sh[j]:
                act_h = j
            if sl[j]:
                act_l = j
    fl = pd.DataFrame(rows, columns=["bar", "dir", "anchor_bar", "anchor", "opp0"])
    fl["flip_t"] = b["close_t"][fl["bar"].to_numpy()] if len(fl) else np.array([], "int64")
    canc = np.full(len(fl), np.iinfo(np.int64).max, np.int64)
    d = fl["dir"].to_numpy()
    ft = fl["flip_t"].to_numpy()
    for k in range(len(fl) - 1):
        # the next flip is always opposite (state machine alternates)
        if d[k + 1] != d[k]:
            canc[k] = ft[k + 1]
    fl["cancel_t"] = canc
    return fl


def gb_limit_fill(m: dict, t_from: int, t_to: int, direction: int, anchor: float,
                  opp0: float, x: float):
    """Resting limit at retracement `x` of the range anchor -> running opposing extreme.
    Long: level = H - x (H - L), H = max(opp0, highs of M1 bars BEFORE the bar tested).
    Returns (k, level, opp_at_fill, k_of_opp) or None."""
    t = m["t"]
    a = np.searchsorted(t, t_from, "left")
    z = np.searchsorted(t, t_to, "left")          # bars starting before t_to
    if z <= a:
        return None
    if direction == 1:
        hh = m["h"][a:z]
        run = np.maximum.accumulate(np.concatenate([[opp0], hh[:-1]]))
        run = np.maximum(run, opp0)
        lvl = run - x * (run - anchor)
        hit = np.flatnonzero(m["l"][a:z] <= lvl)
    else:
        ll = m["l"][a:z]
        run = np.minimum.accumulate(np.concatenate([[opp0], ll[:-1]]))
        run = np.minimum(run, opp0)
        lvl = run + x * (anchor - run)
        hit = np.flatnonzero(m["h"][a:z] >= lvl)
    if not len(hit):
        return None
    k = int(hit[0])
    # M1 index whose extreme set the running opposing extreme (or -1 = flip leg)
    seg = (m["h"][a:a + k] if direction == 1 else -m["l"][a:a + k])
    ref = opp0 if direction == 1 else -opp0
    k_opp = -1
    if k > 0 and seg.max() > ref:
        k_opp = a + int(np.argmax(seg))
    return a + k, float(lvl[k]), float(run[k]), k_opp


def fvgs(b: dict) -> pd.DataFrame:
    """Three-bar FVGs stamped on the third bar (known at its close)."""
    h, l = b["h"], b["l"]
    n = len(h)
    rows = []
    if n >= 3:
        bull = np.flatnonzero(l[2:] > h[:-2]) + 2
        bear = np.flatnonzero(h[2:] < l[:-2]) + 2
        for i in bull:
            rows.append((i, 1, h[i - 2], l[i]))
        for i in bear:
            rows.append((i, -1, h[i], l[i - 2]))
    f = pd.DataFrame(rows, columns=["bar", "dir", "lo", "hi"]).sort_values("bar", kind="stable")
    f["t"] = b["close_t"][f["bar"].to_numpy()] if len(f) else np.array([], "int64")
    return f.reset_index(drop=True)


# ── $niper / Trader T: HTF level reaction -> LTF structure break -> retrace entry ──
def _last_confirmed(flags: np.ndarray, right: int) -> np.ndarray:
    """For each bar i: index of the latest swing j with j + right <= i - 1 (known by
    the close of bar i-1), else -1."""
    n = len(flags)
    # swing j becomes known at bar j+right; usable from bar j+right+1
    src = np.full(n, -1)
    js = np.flatnonzero(flags)
    pos = js + right + 1
    ok = pos < n
    src[pos[ok]] = js[ok]
    return np.maximum.accumulate(src)


def _first_true(mask: np.ndarray) -> int:
    w = np.flatnonzero(mask)
    return int(w[0]) if len(w) else -1


def trader_t_setups(m1: pd.DataFrame, htf="1h", ltf="5min", swing=(2, 2), sweep_window_ns=None,
                    bos_bars=72, expiry_ns=None, rr=2.0) -> pd.DataFrame:
    """Trader T: an HTF fractal swing high/low is swept (first LTF bar trading beyond it
    after it is confirmed, within `sweep_window_ns`); LTF close through the relative
    fractal extreme that existed PRIOR to the sweep, within `bos_bars`; block = most
    recent LTF FVG in the displacement (stamped between the sweep bar and the break bar);
    limit at the FVG's near edge; stop = the sweep extreme; target = rr x risk.
    Fill resolved on M1 within `expiry_ns`; `ran_first` = the target price traded before
    the fill (strictly earlier M1 bars)."""
    left, right = swing
    H = bars_arr(cl.build_bars(m1, htf))
    L = bars_arr(cl.build_bars(m1, ltf))
    m = m1_arrays(m1)
    hsh, hsl = swing_flags(H["h"], H["l"], left, right)
    lsh, lsl = swing_flags(L["h"], L["l"], left, right)
    rel_low = _last_confirmed(lsl, right)
    rel_high = _last_confirmed(lsh, right)
    fv = fvgs(L)
    n = len(L["h"])
    seen = set()
    rows = []
    for d, flags, lvl_arr in ((-1, hsh, H["h"]), (1, hsl, H["l"])):
        for j in np.flatnonzero(flags):
            if j + right >= len(H["h"]):
                continue
            tc = H["close_t"][j + right]
            level = lvl_arr[j]
            a = np.searchsorted(L["start"], tc, "left")
            z = np.searchsorted(L["start"], tc + sweep_window_ns, "left")
            if z <= a:
                continue
            s = _first_true(L["h"][a:z] > level) if d == -1 else _first_true(L["l"][a:z] < level)
            if s < 0:
                continue
            s += a
            if (s, d) in seen:
                continue
            seen.add((s, d))
            ref_i = rel_low[s] if d == -1 else rel_high[s]
            if ref_i < 0:
                continue
            R = L["l"][ref_i] if d == -1 else L["h"][ref_i]
            e = min(n, s + bos_bars)
            i = _first_true(L["c"][s:e] < R) if d == -1 else _first_true(L["c"][s:e] > R)
            if i < 0:
                continue
            i += s
            E = L["h"][s:i + 1].max() if d == -1 else L["l"][s:i + 1].min()
            fb = fv[(fv["dir"].to_numpy() == d) & (fv["bar"].to_numpy() >= s) & (fv["bar"].to_numpy() <= i)]
            if not len(fb):
                continue
            g = fb.iloc[-1]
            px = float(g["lo"]) if d == -1 else float(g["hi"])
            risk = (E - px) if d == -1 else (px - E)
            if not risk > 0:
                continue
            tgt = px + d * rr * risk
            t_dec = int(L["close_t"][i])
            ma = np.searchsorted(m["t"], t_dec, "left")
            mz = np.searchsorted(m["t"], t_dec + expiry_ns, "left")
            k = _first_true(m["h"][ma:mz] >= px) if d == -1 else _first_true(m["l"][ma:mz] <= px)
            if k < 0:
                continue
            ran = (bool((m["l"][ma:ma + k] <= tgt).any()) if d == -1
                   else bool((m["h"][ma:ma + k] >= tgt).any()))
            k += ma
            rows.append((int(m["t"][k]) + NS_MIN, d, risk, rr * risk, px, float(E), float(level),
                         int(L["close_t"][s]), t_dec, ran))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "limit_px", "extreme",
                                     "htf_level", "sweep_t", "bos_t", "ran_first"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    for c_ in ("sweep_t", "bos_t"):
        ev[c_] = to_utc(ev[c_].to_numpy())
    return ev.drop(columns="dt").sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


def niper_pdhl_setups(m1: pd.DataFrame, ltf="15min", swing=(2, 2), mss_bars=24,
                      expiry_ns=None) -> pd.DataFrame:
    """$niper: liquidity taken = the previous trading day's high (short) / low (long)
    traded through (first LTF bar of the day beyond it); LTF close through the latest
    confirmed fractal swing (MSS) within `mss_bars` and the same trading day; the MSS leg
    must leave an FVG (stamped between sweep bar and MSS bar) -> limit at its near edge;
    stop = sweep extreme; target = the opposing previous-day extreme (must lie beyond
    the entry).  Missed if the target trades before the fill.  Emits the two location
    flags for discount-requirement-before-entry, measured at the fill:
      prem_leg = limit on the correct side of 50% of the MSS leg (sweep extreme -> leg
                 extreme through the last M1 bar before the fill);
      prem_day = limit on the correct side of 50% of the trading day's range so far."""
    left, right = swing
    bdf = cl.build_bars(m1, ltf)
    B = bars_arr(bdf)
    m = m1_arrays(m1)
    day = cl.trading_day(bdf.index)
    dcode = pd.factorize(day)[0]
    n = len(B["h"])
    sh, sl = swing_flags(B["h"], B["l"], left, right)
    last_sl = _last_confirmed(sl, right)
    last_sh = _last_confirmed(sh, right)
    fv = fvgs(B)
    # day boundaries
    starts = np.flatnonzero(np.r_[True, dcode[1:] != dcode[:-1]])
    ends = np.r_[starts[1:], n]
    rows = []
    for q in range(1, len(starts)):
        p0, p1 = starts[q - 1], ends[q - 1]
        d0, d1 = starts[q], ends[q]
        pdh, pdl = B["h"][p0:p1].max(), B["l"][p0:p1].min()
        for d in (-1, 1):
            s = _first_true(B["h"][d0:d1] > pdh) if d == -1 else _first_true(B["l"][d0:d1] < pdl)
            if s < 0:
                continue
            s += d0
            e = min(d1, s + mss_bars)
            i = -1
            for ii in range(s, e):
                ref = last_sl[ii] if d == -1 else last_sh[ii]
                if ref < 0:
                    continue
                if (d == -1 and B["c"][ii] < B["l"][ref]) or (d == 1 and B["c"][ii] > B["h"][ref]):
                    i = ii
                    break
            if i < 0:
                continue
            E = B["h"][s:i + 1].max() if d == -1 else B["l"][s:i + 1].min()
            fb = fv[(fv["dir"].to_numpy() == d) & (fv["bar"].to_numpy() >= s) & (fv["bar"].to_numpy() <= i)]
            if not len(fb):
                continue
            g = fb.iloc[-1]
            px = float(g["lo"]) if d == -1 else float(g["hi"])
            tgt = pdl if d == -1 else pdh
            risk = (E - px) if d == -1 else (px - E)
            tdist = (px - tgt) if d == -1 else (tgt - px)
            if not (risk > 0 and tdist > 0):
                continue
            t_dec = int(B["close_t"][i])
            ma = np.searchsorted(m["t"], t_dec, "left")
            mz = np.searchsorted(m["t"], t_dec + expiry_ns, "left")
            k = _first_true(m["h"][ma:mz] >= px) if d == -1 else _first_true(m["l"][ma:mz] <= px)
            if k < 0:
                continue
            pre_h, pre_l = m["h"][ma:ma + k], m["l"][ma:ma + k]
            if (d == -1 and (pre_l <= tgt).any()) or (d == 1 and (pre_h >= tgt).any()):
                continue                                   # objective reached first: missed
            k += ma
            if d == -1:
                legx = min(B["l"][s:i + 1].min(), pre_l.min() if len(pre_l) else np.inf)
                eq_leg = 0.5 * (E + legx)
                prem_leg = px > eq_leg
                dh = max(B["h"][d0:i + 1].max(), pre_h.max() if len(pre_h) else -np.inf)
                dl = min(B["l"][d0:i + 1].min(), pre_l.min() if len(pre_l) else np.inf)
                prem_day = px > 0.5 * (dh + dl)
            else:
                legx = max(B["h"][s:i + 1].max(), pre_h.max() if len(pre_h) else -np.inf)
                eq_leg = 0.5 * (E + legx)
                prem_leg = px < eq_leg
                dh = max(B["h"][d0:i + 1].max(), pre_h.max() if len(pre_h) else -np.inf)
                dl = min(B["l"][d0:i + 1].min(), pre_l.min() if len(pre_l) else np.inf)
                prem_day = px < 0.5 * (dh + dl)
            rows.append((int(m["t"][k]) + NS_MIN, d, risk, tdist, px, float(E), float(tgt),
                         int(B["close_t"][s]), t_dec, bool(prem_leg), bool(prem_day)))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "limit_px", "extreme",
                                     "target_px_ref", "sweep_t", "mss_t", "prem_leg", "prem_day"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    for c_ in ("sweep_t", "mss_t"):
        ev[c_] = to_utc(ev[c_].to_numpy())
    return ev.drop(columns="dt").sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)
