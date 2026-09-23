"""c2-unicorn (guest: DTR, 07lOxv39LdY) — the C2 Unicorn, 1H C2 paired with a 5m unicorn.

trade_test, claim '+', vs a matched random-entry control. No daily bias (the model is
explicitly bias-free).

Operationalisation (bullish; bearish mirrored), declared before the first run:
  C2       the current 1h candle trades below the previous 1h candle's low (the sweep);
           the trade is taken INSIDE C2, before the hour closes (no C2 close / C3 wait).
  POI      during C2 the running low L has tagged a point of interest not yet reached
           by C1: a level x with L <= x <= C1 low, among previous-day low, previous-week
           low, the last completed Asia / London / NY-AM session lows, 1h 2/2 swing lows
           confirmed before C2 opened (<= 48h old); or the top of a bullish 1h FVG
           (<= 48h old, completed before C2) with L <= top <= C1 low.
  unicorn  on 5m: the low bar kL = the lowest 5m bar of C2 so far; the breaker candle kb =
           the highest-high 5m bar among the 12 bars before kL, zone = [its body low, its
           high]; confirmation at 5m bar j when close_j > high(kb) AND a bullish 5m FVG
           (low_i > high_{i-2}, i-2 >= kL, i <= j) overlaps the breaker zone; candle
           count j - kb <= 12; j closes inside the C2 hour. First per hour and direction.
  entry    next M1 open after the 5m confirmation close.
  stop     L, the C2 extreme so far (no stop is stated in the video).
  target   2R ('low hanging fruit ... roughly 2 to 2.5R').  hold 4h.
Not modelled: 'opposing range candles' and the daily T-spot (never defined), the 7-hour
context candle, the ADR-remaining check, the large-wick preference.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, swings_confirmed  # noqa: E402

CID = "c2-unicorn"
COUNT_MAX = 12
BREAKER_LOOKBACK = 12
POI_AGE_H = 48
RR = 2.0
MAX_HOLD = "4h"
SESSIONS = ("asia", "london", "ny_am")


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    empty = pd.DataFrame(columns=cols)
    if len(m1) < 3000:
        return empty
    H = cl.build_bars(m1, "1h")
    F = cl.build_bars(m1, "5min")
    if len(H) < 60:
        return empty
    hs = _ns(H.index)
    hct = _ns(H["close_time"])
    Ho, Hh, Hl, Hc = (H[c].to_numpy() for c in ("open", "high", "low", "close"))
    fs = _ns(F.index)
    fct = _ns(F["close_time"])
    o, h, l, c = (F[k].to_numpy().tolist() for k in ("open", "high", "low", "close"))
    # 5m bars grouped into their 1h candle
    hid = np.searchsorted(hs, fs, side="right") - 1
    # level POIs known at each hour's open
    t_open = pd.DatetimeIndex(H.index)
    D = cl.build_bars(m1, "1D")
    W = cl.build_bars(m1, "1W")
    pdd = cl.asof(D, t_open)
    pww = cl.asof(W, t_open)
    lv_lo = [pdd["low"].to_numpy(), pww["low"].to_numpy()]
    lv_hi = [pdd["high"].to_numpy(), pww["high"].to_numpy()]
    for s in SESSIONS:
        ph = cl.prior_hilo(t_open, s, m1=m1)
        lv_lo.append(ph["low"].to_numpy())
        lv_hi.append(ph["high"].to_numpy())
    lv_lo = np.vstack(lv_lo).T
    lv_hi = np.vstack(lv_hi).T
    sw = swings_confirmed(H)
    sw_conf = _ns(sw["conf"].fillna(pd.Timestamp("2100-01-01", tz="UTC")))
    shi = np.flatnonzero(sw["sh"].to_numpy())
    sli = np.flatnonzero(sw["sl"].to_numpy())
    # 1h FVGs (third bar index k, completed at hct[k])
    bull_f = [(k, Hh[k - 2], Hl[k]) for k in range(2, len(H)) if Hl[k] > Hh[k - 2]]
    bear_f = [(k, Hh[k], Hl[k - 2]) for k in range(2, len(H)) if Hh[k] < Hl[k - 2]]
    bull_k = np.array([x[0] for x in bull_f], int)
    bear_k = np.array([x[0] for x in bear_f], int)

    rows = []
    starts = np.searchsorted(hid, np.arange(len(H)), side="left")
    ends = np.searchsorted(hid, np.arange(len(H)), side="right")
    for hi_ in range(1, len(H)):
        s, e = starts[hi_], ends[hi_]
        if e - s < 3:
            continue
        pl, ph_ = Hl[hi_ - 1], Hh[hi_ - 1]
        t0 = hs[hi_]
        # candidate POI levels for this hour
        lows = [x for x in lv_lo[hi_] if not np.isnan(x)]
        highs = [x for x in lv_hi[hi_] if not np.isnan(x)]
        lows += [Hl[j] for j in sli[(sli >= hi_ - POI_AGE_H) & (sli < hi_)] if sw_conf[j] <= t0]
        highs += [Hh[j] for j in shi[(shi >= hi_ - POI_AGE_H) & (shi < hi_)] if sw_conf[j] <= t0]
        fb = [bull_f[q][2] for q in np.flatnonzero((bull_k >= hi_ - POI_AGE_H) & (bull_k < hi_))]
        fr = [bear_f[q][1] for q in np.flatnonzero((bear_k >= hi_ - POI_AGE_H) & (bear_k < hi_))]
        for direc in (1, -1):
            for j in range(s, e):
                if direc == 1:
                    seg = l[s:j + 1]
                    L = min(seg)
                    if not L < pl:
                        continue
                    kL = s + seg.index(L)
                    if j <= kL or kL - BREAKER_LOOKBACK < 0:
                        continue
                    win = h[kL - BREAKER_LOOKBACK:kL]
                    kb = kL - BREAKER_LOOKBACK + win.index(max(win))
                    B = h[kb]
                    if not c[j] > B or j - kb > COUNT_MAX:
                        continue
                    zlo, zhi = min(o[kb], c[kb]), h[kb]
                    fvg = any(l[i] > h[i - 2] and l[i] >= zlo and h[i - 2] <= zhi
                              for i in range(kL + 2, j + 1))
                    if not fvg:
                        continue
                    poi = any(L <= x <= pl for x in lows) or any(L <= x <= pl for x in fb)
                    if not poi:
                        continue
                    rows.append((fct[j], 1, L))
                    break
                else:
                    seg = h[s:j + 1]
                    Hx = max(seg)
                    if not Hx > ph_:
                        continue
                    kH = s + seg.index(Hx)
                    if j <= kH or kH - BREAKER_LOOKBACK < 0:
                        continue
                    win = l[kH - BREAKER_LOOKBACK:kH]
                    kb = kH - BREAKER_LOOKBACK + win.index(min(win))
                    B = l[kb]
                    if not c[j] < B or j - kb > COUNT_MAX:
                        continue
                    zlo, zhi = l[kb], max(o[kb], c[kb])
                    fvg = any(h[i] < l[i - 2] and h[i] <= zhi and l[i - 2] >= zlo
                              for i in range(kH + 2, j + 1))
                    if not fvg:
                        continue
                    poi = any(ph_ <= x <= Hx for x in highs) or any(ph_ <= x <= Hx for x in fr)
                    if not poi:
                        continue
                    rows.append((fct[j], -1, Hx))
                    break
    if not rows:
        return empty
    t = pd.DatetimeIndex(np.array([r[0] for r in rows], dtype="datetime64[ns]")).tz_localize("UTC")
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": [r[1] for r in rows], "stop_px": [r[2] for r in rows], "rr": RR})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "long share", (ev.direction > 0).mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "C2 = the current 1h candle sweeps the previous 1h candle's low (bull) / high (bear); trade inside C2 before it closes",
        "POI: the C2 extreme so far tagged, for the first time vs C1, one of PDL/PWL, last Asia/London/NY-AM session low, a 1h 2/2 swing low"
        " confirmed before C2 (<=48h), or the top of a bullish 1h FVG (<=48h); bearish mirrored",
        "5m unicorn: breaker = highest-high 5m bar in the 12 bars before the C2 low; confirm on a 5m close above it with a bullish 5m FVG"
        " formed after the low overlapping the breaker candle's [body low, high]; breaker-to-confirmation <= 12 bars",
        "entry next M1 open after the confirming 5m close; stop at the C2 extreme so far; target 2R; hold 4h; first setup per hour per direction"],
        "params": {"c2_tf": "1h", "unicorn_tf": "5min", "count_max": COUNT_MAX, "breaker_lookback": BREAKER_LOOKBACK,
                   "poi_age_h": POI_AGE_H, "rr": RR, "max_hold": MAX_HOLD, "swing": "2/2 1h",
                   "sessions": list(SESSIONS)}}
    src = {"c2_tf": "corpus: 07lOxv39LdY '1H C2 with a 5m unicorn' pairing",
           "unicorn_tf": "corpus: 07lOxv39LdY '1H C2 with a 5m unicorn' pairing",
           "count_max": "corpus: 07lOxv39LdY 'the unicorn should form in about 10 to 12 candles or less'",
           "breaker_lookback": "declared-before-run: the down-leg into the low searched over the same 12-bar budget",
           "poi_age_h": "declared-before-run: intraday POIs (swings/FVGs) valid for two days",
           "rr": "corpus: 07lOxv39LdY 'low hanging fruit ... roughly 2 to 2.5R' (lower end)",
           "max_hold": "declared-before-run: intraday session-level target, 4 hours",
           "swing": "declared-before-run: 2/2 fractal swings, as phase-3 locked config",
           "sessions": "session_window_fit: SESSION_WINDOWS asia 20-00, london 02-05, ny_am 08:30-12 (NY)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__, probe=probe,
                        notes="No stop is stated in the video: stop placed at the C2 extreme. T-spot, opposing range "
                        "candles, the 7H context candle and the ADR check are not modelled.")
    print("wrote", p)
