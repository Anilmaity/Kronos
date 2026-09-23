"""Shared, pure detectors for batch entry_guest_01b (breaker / unicorn / limit-fill).

Everything here is a pure function of the bars / M1 frame it is given, so
`probe_lookahead` can re-run it on truncated slices.

Breaker (method spec §4.6, `breaker-block`, mirrored for bullish; Rauf's reading in
`breaker-wick-vs-body-invalidation` is the same object):
  bullish: swing low L1 (a) -> swing high H1 (bi) -> a LOWER LOW (below L1) ->
  a CLOSE above H1 (d).  Zone = the up-close candles from L1 to H1 (bodies:
  [min open, max close]).  Swings are three-candle fractals (left=right=1,
  `swing-point-stop-hunt`: "a swing low has higher lows on each side").
Unicorn (`unicorn-model`): a same-direction 3-bar FVG, created by the leg out of the
  lower low (first candle at/after the lower low, third candle <= d+1), that OVERLAPS
  the breaker zone.  Completion bar e = max(d, FVG third bar).
Bearish setups are the exact mirror (prices negated).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ONE_MIN = pd.Timedelta(minutes=1)


def _swings(h, l):
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n >= 3:
        sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] >= h[2:])
        sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] <= l[2:])
    return sh, sl


def _scan_bull(o, h, l, c, W, want_fvg):
    n = len(o)
    sh, sl = _swings(h, l)
    sl_idx = np.flatnonzero(sl)
    rows = []
    for bi in np.flatnonzero(sh):
        if bi + 1 >= n:
            continue
        k = np.searchsorted(sl_idx, bi) - 1
        if k < 0:
            continue
        a = int(sl_idx[k])
        if bi - a + 1 > W or h[bi] < h[a:bi + 1].max():
            continue
        lo_a, hi_b = l[a], h[bi]
        swept = False
        cidx, minlow, d, body_below = -1, np.inf, -1, False
        for j in range(bi + 1, min(n - 1, a + W - 1) + 1):
            if l[j] < lo_a:
                swept = True
            if swept:
                if l[j] < minlow:
                    minlow, cidx = l[j], j
                if c[j] < lo_a:
                    body_below = True
                if c[j] > hi_b:
                    d = j
                    break
            elif c[j] > hi_b:
                break
        if d < 0:
            continue
        seg = np.arange(a, bi + 1)
        up = seg[c[seg] > o[seg]]
        if len(up) == 0:
            continue
        z_lo, z_hi = float(o[up].min()), float(c[up].max())
        row = dict(a=a, bi=bi, cidx=cidx, d=d, zone_low=z_lo, zone_high=z_hi,
                   sweep_px=float(minlow), l1=float(lo_a), h1=float(hi_b),
                   body_below=bool(body_below))
        if want_fvg:
            found = -1
            for kk in range(max(cidx + 2, 2), min(d + 1, n - 1) + 1):
                if l[kk] > h[kk - 2]:
                    g_lo, g_hi = h[kk - 2], l[kk]
                    if g_lo < z_hi and g_hi > z_lo:
                        found = kk
                        break
            if found < 0:
                continue
            row.update(fvg_k=found, gap_low=float(h[found - 2]), gap_high=float(l[found]),
                       e=max(d, found))
        else:
            row["e"] = d
        rows.append(row)
    return rows


def breaker_setups(b: pd.DataFrame, W: int, want_fvg: bool) -> pd.DataFrame:
    """Both directions. Prices in the output are REAL (un-mirrored).

    Columns: direction (+1/-1), t_a (bar start of L1), confirm_time (close_time of e),
    e_start, zone_low/high, gap_low/high (if want_fvg), sweep_px (the lower low /
    higher high), l1 (the breaker's defining extreme), body_below (a body closed
    beyond l1 during the sweep leg), count = e - a + 1 bars.
    """
    cols = ["direction", "t_a", "e_start", "confirm_time", "zone_low", "zone_high",
            "gap_low", "gap_high", "sweep_px", "l1", "h1", "body_below", "count"]
    if len(b) < 5:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = b.index
    ct = pd.DatetimeIndex(b["close_time"])
    out = []
    for sgn, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for r in _scan_bull(*arrs, W, want_fvg):
            def px(v):
                return v * sgn
            if sgn == 1:
                zl, zh = r["zone_low"], r["zone_high"]
                gl, gh = r.get("gap_low", np.nan), r.get("gap_high", np.nan)
            else:   # mirrored: low/high swap
                zl, zh = -r["zone_high"], -r["zone_low"]
                gl, gh = -r.get("gap_high", np.nan), -r.get("gap_low", np.nan)
            out.append(dict(direction=sgn, t_a=idx[r["a"]], e_start=idx[r["e"]],
                            confirm_time=ct[r["e"]], zone_low=zl, zone_high=zh,
                            gap_low=gl, gap_high=gh, sweep_px=px(r["sweep_px"]),
                            l1=px(r["l1"]), h1=px(r["h1"]), body_below=r["body_below"],
                            count=r["e"] - r["a"] + 1, _bi=r["bi"]))
    if not out:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(out).sort_values(["direction", "e_start", "_bi"])
    # one setup per (direction, completion bar): keep the most recent structure
    df = df.drop_duplicates(["direction", "e_start"], keep="last")
    return df.drop(columns="_bi").sort_values(["confirm_time", "direction"]).reset_index(drop=True)


def limit_fill(m1: pd.DataFrame, start, entry, target, sign, deadline):
    """First M1 bar (start >= `start`, start < `deadline`) that trades to the resting
    limit `entry`, provided the target was not reached first (order cancelled when
    price runs away). Returns bar START times (NaT = not filled)."""
    tn = pd.DatetimeIndex(m1.index).tz_convert("UTC").as_unit("ns").asi8
    lo = m1["low"].to_numpy(float)
    hi = m1["high"].to_numpy(float)
    s = pd.DatetimeIndex(start).tz_convert("UTC").as_unit("ns").asi8
    dl = pd.DatetimeIndex(deadline).tz_convert("UTC").as_unit("ns").asi8
    i0 = np.searchsorted(tn, s, "left")
    i1 = np.searchsorted(tn, dl, "left")
    res = np.full(len(s), np.iinfo(np.int64).min, np.int64)
    for k in range(len(s)):
        a, z = i0[k], i1[k]
        if z <= a:
            continue
        if sign[k] > 0:
            f = np.flatnonzero(lo[a:z] <= entry[k])
            t = np.flatnonzero(hi[a:z] >= target[k])
        else:
            f = np.flatnonzero(hi[a:z] >= entry[k])
            t = np.flatnonzero(lo[a:z] <= target[k])
        if len(f) and (len(t) == 0 or f[0] <= t[0]):
            res[k] = tn[a + f[0]]
    out = pd.DatetimeIndex(np.where(res == np.iinfo(np.int64).min,
                                    np.datetime64("NaT", "ns"), res.astype("datetime64[ns]")))
    return out.tz_localize("UTC")


def ny_at(times, hhmm: str) -> pd.DatetimeIndex:
    """Same NY calendar date as `times`, at clock hh:mm (DST-aware), in UTC."""
    loc = pd.DatetimeIndex(times).tz_convert("America/New_York")
    h, m = map(int, hhmm.split(":"))
    naive = loc.tz_localize(None).normalize() + pd.Timedelta(hours=h, minutes=m)
    return naive.tz_localize("America/New_York", ambiguous="NaT",
                             nonexistent="shift_forward").tz_convert("UTC")


def asia_range(m1: pd.DataFrame) -> pd.DataFrame:
    """Asia (20:00-00:00 NY) high/low per trading day (18:00 roll), with the time
    the range is complete (00:00 NY). Index = trading_day."""
    import concept_lab as cl
    t = pd.DatetimeIndex(m1.index)
    mod = cl.ny_minute_of_day(t)
    sel = mod >= 20 * 60
    sub = m1.loc[sel, ["high", "low"]]
    td = cl.trading_day(pd.DatetimeIndex(sub.index))
    g = sub.groupby(td)
    out = pd.DataFrame({"asia_high": g["high"].max(), "asia_low": g["low"].min(),
                        "asia_n": g.size()})
    # trading_day labels the NY date the session OPENED (18:00); Asia ends at the
    # following midnight, i.e. 00:00 NY of label + 1 day.
    end_local = (pd.DatetimeIndex(out.index).tz_localize(None).normalize()
                 + pd.Timedelta(days=1))
    out["asia_done"] = end_local.tz_localize("America/New_York", ambiguous="NaT",
                                             nonexistent="shift_forward").tz_convert("UTC")
    return out


def unicorn_book(m1: pd.DataFrame, *, tf: str = "5min", W: int = 48,
                 fill_min: int = 60, rr: float = 2.0, want_fvg: bool = True,
                 entry_rule: str = "overlap_top", stop_rule: str = "zone_far",
                 deadline_fn=None) -> pd.DataFrame:
    """Limit-order book on breaker / unicorn setups.

    Limit (long): top of the breaker/FVG overlap (unicorn) or top of the breaker zone
    (`entry_rule="zone_top"`). Stop (long): far edge of the breaker zone
    (`stop_rule="zone_far"`) or the lower low (`stop_rule="sweep"`). Target rr x risk.
    The order rests from the completion bar's close for `fill_min` minutes (or until
    `deadline_fn(confirm_time)` if given, whichever is earlier) and is cancelled if the
    target trades first. The harness enters at the open of the M1 bar AFTER the fill
    bar, with the planned stop DISTANCE (stop_dist) — so a fill bar that also pierced
    the stop is kept (not dropped as 'stop on the wrong side')."""
    import concept_lab as cl
    b = cl.build_bars(m1, tf)
    s = breaker_setups(b, W, want_fvg)
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr",
            "confirm_time", "t_a", "count", "sweep_px", "lim_px", "brk_px", "body_below",
            "l1"]
    if s.empty:
        return pd.DataFrame(columns=cols)
    sg = s["direction"].to_numpy()
    if entry_rule == "overlap_top":
        ent = np.where(sg > 0, np.minimum(s.zone_high, s.gap_high),
                       np.maximum(s.zone_low, s.gap_low))
    else:  # zone_top (near edge of the breaker)
        ent = np.where(sg > 0, s.zone_high, s.zone_low)
    if stop_rule == "zone_far":
        stp = np.where(sg > 0, s.zone_low, s.zone_high)
    else:
        stp = s.sweep_px.to_numpy()
    risk = sg * (ent - stp)
    ok = np.isfinite(risk) & (risk > 0)
    s, sg, ent, stp, risk = s[ok].reset_index(drop=True), sg[ok], ent[ok], stp[ok], risk[ok]
    tgt = ent + sg * rr * risk
    start = pd.DatetimeIndex(s["confirm_time"])
    dl = start + pd.Timedelta(minutes=fill_min)
    if deadline_fn is not None:
        d2 = pd.DatetimeIndex(deadline_fn(start)).tz_convert("UTC")
        a1 = dl.tz_convert("UTC").as_unit("ns").asi8
        a2 = d2.as_unit("ns").asi8          # NaT -> int64 min -> deadline in the past
        dl = pd.DatetimeIndex(np.minimum(a1, a2).astype("datetime64[ns]")).tz_localize("UTC")
    fill = limit_fill(m1, start, ent, tgt, sg, dl)
    f = ~pd.isna(fill)
    dec = pd.DatetimeIndex(fill[f]) + ONE_MIN
    out = pd.DataFrame({
        "decision_time": dec, "available_at": dec, "direction": sg[f].astype(int),
        "stop_dist": risk[f], "rr": float(rr),
        "confirm_time": start[f], "t_a": pd.DatetimeIndex(s["t_a"])[f],
        "count": s["count"].to_numpy()[f].astype(int), "sweep_px": s["sweep_px"].to_numpy()[f],
        "lim_px": ent[f], "brk_px": stp[f], "body_below": s["body_below"].to_numpy(bool)[f],
        "l1": s["l1"].to_numpy()[f]})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)
