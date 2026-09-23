"""Shared, pure building blocks for batch entry_own_03b (TTrades own-voice entries).

Every function takes bars built FROM THE INPUT M1 (cl.build_bars) so the detectors
that use them stay probe-able. Nothing here reads the future: an object stamped at
bar i uses bars <= i only, and every "until" window is expressed in wall-clock
from a known close so a truncated slice gives the same events up to its cut.

Parameters fixed here (all declared before any run of this batch):
  TF              15min working timeframe (every concept's htf/ltf list contains 15m;
                  phase-3 primary stack entry TF)
  SWING 2/2       phase3 locked fractal
  DISP_N/R/D      threshold_fits displacement magnitude gate: N=4, r=1.5, d=0.65,
                  plus the structural close-beyond gate (grade A)
  TREND_BARS      24 bars (6h) life of an 'aggressive trend' after its displacement
                  fires (declared-before-run: the corpus never bounds it)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                   # noqa: E402
from detectors.primitives import swing_points, fair_value_gaps   # noqa: E402

TF = "15min"
TF_MIN = 15
SW_L, SW_R = 2, 2
DISP_N, DISP_R, DISP_D = 4, 1.5, 0.65
TREND_BARS = 24


def bars(m1: pd.DataFrame, tf: str = TF) -> pd.DataFrame:
    return cl.build_bars(m1, tf)


def swing_arrays(b: pd.DataFrame):
    sw = swing_points(b[["open", "high", "low", "close"]], left=SW_L, right=SW_R)
    return sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()


def displacement_legs(b: pd.DataFrame, is_sh=None, is_sl=None) -> pd.DataFrame:
    """Every close beyond the latest confirmed, not-yet-broken 2/2 swing, graded by
    the threshold_fits magnitude gate over the N bars from the break.

    Returns one row per break: direction (+1/-1), brk (break bar pos), fire (pos of
    the last window bar, when the grade is known), fired (bool), level (the swing),
    swing_pos, leg_start_px/pos (the extreme the leg launched from: the lowest low
    between the broken swing high and the break, mirrored), leg_end_px (window
    extreme)."""
    if is_sh is None:
        is_sh, is_sl = swing_arrays(b)
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    c = b["close"].to_numpy(float)
    n = len(b)
    rows = []
    sh = None      # (pos, level) latest confirmed unbroken swing high
    sl = None
    for i in range(n):
        p = i - SW_R - 1               # swing at p is confirmed at close of p+R <= i-1
        if p >= 0:
            if is_sh[p]:
                sh = (p, h[p])
            if is_sl[p]:
                sl = (p, l[p])
        for d, sw in ((1, sh), (-1, sl)):
            if sw is None:
                continue
            p0, lvl = sw
            if (d == 1 and c[i] > lvl) or (d == -1 and c[i] < lvl):
                if d == 1:
                    sh = None
                else:
                    sl = None
                f = i + DISP_N - 1
                if f >= n or i < DISP_N:
                    continue
                pre = h[i - DISP_N:i].max() - l[i - DISP_N:i].min()
                wh, wl = h[i:f + 1].max(), l[i:f + 1].min()
                win = wh - wl
                dist = (wh - lvl) if d == 1 else (lvl - wl)
                fired = bool(pre > 0 and win / pre >= DISP_R and dist / pre >= DISP_D)
                if d == 1:
                    seg = l[p0:i + 1]
                    sp = p0 + int(np.argmin(seg))
                    rows.append((d, i, f, fired, lvl, p0, float(seg.min()), sp, float(wh)))
                else:
                    seg = h[p0:i + 1]
                    sp = p0 + int(np.argmax(seg))
                    rows.append((d, i, f, fired, lvl, p0, float(seg.max()), sp, float(wl)))
    cols = ["direction", "brk", "fire", "fired", "level", "swing_pos", "leg_start_px",
            "leg_start_pos", "leg_end_px"]
    return pd.DataFrame(rows, columns=cols)


def trend_state(b: pd.DataFrame, legs: pd.DataFrame):
    """Per bar j: the aggressive trend in force at the CLOSE of j.

    Trend = the latest FIRED displacement whose fire bar < j, alive while
    j - fire <= TREND_BARS and no close in (fire, j] went beyond its leg start
    (the protected origin). A newer fired leg (either direction) replaces it.
    Returns (dir[j] in {-1,0,1}, fire_pos[j] or -1, leg_start_px[j])."""
    n = len(b)
    c = b["close"].to_numpy(float)
    tdir = np.zeros(n, dtype=int)
    tfire = np.full(n, -1, dtype=int)
    tstart = np.full(n, np.nan)
    fl = legs[legs["fired"]].sort_values(["fire", "brk"])
    fires = fl[["fire", "direction", "leg_start_px"]].to_numpy()
    k = 0
    cur = None                    # (fire, dir, start, dead)
    for j in range(n):
        while k < len(fires) and fires[k][0] < j:
            cur = [int(fires[k][0]), int(fires[k][1]), float(fires[k][2]), False]
            k += 1
        if cur is None or cur[3]:
            continue
        f, d, s, _ = cur
        if j - f > TREND_BARS:
            cur[3] = True
            continue
        if (d == 1 and c[j] < s) or (d == -1 and c[j] > s):
            cur[3] = True
            continue
        tdir[j], tfire[j], tstart[j] = d, f, s
    return tdir, tfire, tstart


def first_touch(m1, start_times, levels, side, until):
    """First M1 bar at/after start_times reaching level (side 'above': high >=,
    'below': low <=) strictly before `until`. Returns (hit bool, decision time =
    that M1 bar's close)."""
    if len(start_times) == 0:
        return np.zeros(0, bool), pd.DatetimeIndex([], tz="UTC")
    st = pd.DatetimeIndex(start_times)
    res = cl.touch(st, np.asarray(levels, float), side, until=pd.DatetimeIndex(until),
                   m1=m1)
    hit = res["hit"].to_numpy()
    dt = pd.DatetimeIndex(res["hit_time"]) + pd.Timedelta(minutes=1)
    return hit, dt


def touch_sided(m1, start_times, levels, dirs, until):
    """Retest touch for a limit order: a SHORT limit fills when price rises to the
    level ('above'), a LONG limit when it falls to it ('below')."""
    dirs = np.asarray(dirs)
    st = pd.DatetimeIndex(start_times)
    un = pd.DatetimeIndex(until)
    lv = np.asarray(levels, float)
    hit = np.zeros(len(st), bool)
    dt = np.full(len(st), np.datetime64("NaT", "ns"))
    for d, side in ((-1, "above"), (1, "below")):
        s = dirs == d
        if s.any():
            hh, tt = first_touch(m1, st[s], lv[s], side, un[s])
            hit[s] = hh
            dt[s] = tt.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()
    return hit, pd.DatetimeIndex(dt).tz_localize("UTC")


def empty(cols):
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})


def finish(ev: pd.DataFrame) -> pd.DataFrame:
    """Sort, drop exact duplicate trades (same decision minute and direction; keep the
    first listed), reset the index."""
    if ev.empty:
        return ev.reset_index(drop=True)
    ev = ev.sort_values(["decision_time", "direction"], kind="stable")
    ev = ev.drop_duplicates(["decision_time", "direction"], keep="first")
    return ev.reset_index(drop=True)
