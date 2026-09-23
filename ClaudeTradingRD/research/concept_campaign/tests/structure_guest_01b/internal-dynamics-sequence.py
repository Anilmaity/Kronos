"""internal-dynamics-sequence (guest: DexterLab, wWIHS_dxbEY) -> gate_test.

Reading (declared before the run), bullish case (bearish mirrored):
  * PO3 candle = the 4H candle (forex grid, measurable: 'inside a 4H candle'); internal
    dynamics read on 15m (listed LTF).  O = the 4H candle's opening price.
  * Baseline book = the BREAKER at the opening price: the first 15m close back above O
    in a 4H candle whose earlier 15m closes were all at/below O (so price has traded
    below O first).  Long at that close (harness: next M1 open); stop = the candle's
    lowest low so far (the manipulation wick); 2R; max_hold 4h (one PO3 candle).
    At most one event per 4H candle (the first 15m close fixes the side).
  * Gate seq_ok = the full ordered sequence preceded the breaker inside the candle:
      1. turtle soup: a 15m bar whose low takes the most recent confirmed 15m fractal
         (2/2) swing low and which closes back above that level;
      2. order block: the last down-close 15m bar at or before the candle's low bar
         (searched inside the candle), confirmed by a later close above its high at or
         after the turtle-soup bar;
      3. the breaker close (the event itself); OB confirmation may be the breaker bar.
  * Claim '+': breakers delivered after the full turtle-soup -> OB sequence carry the
    continuation leg better than breakers without it.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_guest_01b")
from common01b import cl, bars_arr, swing_flags, to_utc  # noqa: E402

HTF = "4h"
LTF = "15min"
SWING = (2, 2)
RR = 2.0
MAX_HOLD = "4h"


def _last_confirmed(flag: np.ndarray, level: np.ndarray, right: int) -> np.ndarray:
    """level of the most recent swing confirmed at or before the close of bar k-1."""
    n = len(flag)
    conf_at = np.full(n, np.nan)
    j = np.flatnonzero(flag)
    ci = j + right
    ok = ci < n
    conf_at[ci[ok]] = level[j[ok]]
    s = pd.Series(conf_at).ffill().to_numpy()
    return np.r_[np.nan, s[:-1]]


def _bull(o, h, l, c, O, prev_sw_low):
    """o,h,l,c = 15m arrays of ONE 4H candle; returns (k, stop, seq_ok) or None."""
    m = len(c)
    if m < 2 or not c[0] < O:
        return None
    above = np.flatnonzero(c > O)
    if not len(above):
        return None
    k = int(above[0])
    stop = float(l[:k + 1].min())
    if not stop < O:
        return None
    # 1. turtle soup
    sw = prev_sw_low[:k + 1]
    ts = np.flatnonzero((l[:k + 1] < sw) & (c[:k + 1] > sw))
    seq = False
    if len(ts):
        t0 = int(ts[0])
        low_bar = int(np.argmin(l[:k + 1]))
        dn = np.flatnonzero(c[:low_bar + 1] < o[:low_bar + 1])
        if len(dn):
            ob = int(dn[-1])
            conf = np.flatnonzero(c[ob + 1:k + 1] > h[ob])
            if len(conf):
                ci = ob + 1 + int(conf[0])
                seq = ci >= t0
    return k, stop, seq


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    H = cl.build_bars(m1, HTF)
    b = bars_arr(cl.build_bars(m1, LTF))
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]
    sh, sl = swing_flags(h, l, *SWING)
    sw_lo = _last_confirmed(sl, l, SWING[1])
    sw_hi = _last_confirmed(sh, h, SWING[1])
    hs = cl.data.utc_ns(H.index).view("int64")
    he = cl.data.utc_ns(H["close_time"]).view("int64")
    Ho = H["open"].to_numpy(float)
    a = np.searchsorted(b["start"], hs, "left")
    z = np.searchsorted(b["start"], he, "left")
    rows = []
    for q in range(len(H)):
        i0, i1 = a[q], z[q]
        if i1 - i0 < 2 or i1 > len(c):
            continue
        # the 15m bars must all have closed inside the slice
        O = Ho[q]
        r = _bull(o[i0:i1], h[i0:i1], l[i0:i1], c[i0:i1], O, sw_lo[i0:i1])
        if r is not None:
            k, stop, seq = r
            rows.append((i0 + k, 1, stop, seq))
            continue
        r = _bull(-o[i0:i1], -l[i0:i1], -h[i0:i1], -c[i0:i1], -O, -sw_hi[i0:i1])
        if r is not None:
            k, stop, seq = r
            rows.append((i0 + k, -1, -stop, seq))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "seq_ok"]
    if not rows:
        return pd.DataFrame(columns=cols)
    f = pd.DataFrame(rows, columns=["bar", "direction", "stop_px", "seq_ok"])
    f["decision_time"] = to_utc(b["close_t"][f["bar"].to_numpy()])
    f["available_at"] = f["decision_time"]
    f["rr"] = RR
    f["seq_ok"] = f["seq_ok"].astype(bool)
    return f[cols].sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"ids_{HTF}_{LTF}_{SWING}_{RR}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.seq_ok.mean(), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "seq_ok", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "ctrl_overlap", "exposure_bars", "control"):
        print(k, res.get(k))
    op = {"rules": [
        "PO3 candle = 4H (forex grid); internal dynamics on 15m; O = 4H open.",
        "Event (breaker): first 15m close back through O after all earlier 15m closes in the candle were on the other side; trade the crossing direction; stop = candle extreme so far; 2R; max_hold 4h.",
        "Gate seq_ok: a turtle soup (15m bar taking the last confirmed 2/2 swing low and closing back above it) and then an OB confirmation (close above the last down-close bar at/before the candle low) occurred before/at the breaker.",
        "Claim '+': the ordered sequence improves the breaker continuation."],
        "params": {"htf": HTF, "ltf": LTF, "swing_left_right": SWING, "rr": RR, "max_hold": MAX_HOLD,
                   "grid4h": "forex"}}
    ps = {"htf": "corpus-derived: internal-dynamics-sequence.yaml measurable 'inside a 4H candle'",
          "ltf": "declared-before-run: 15m (listed LTF; the speaker shows 15m and 5m)",
          "swing_left_right": "declared-before-run: fractal 2/2 short-term swing for the turtle soup",
          "rr": "phase3: 2R target of the locked conjunction book",
          "max_hold": "declared-before-run: 4h (one PO3 candle)",
          "grid4h": "session_window_fit: forex grid (carried as a knob)"}
    notes = ("The FVG/OTE final leg is the trade outcome itself, not a gate. The 2/2.5-deviation opening "
             "classification is a separate concept (opening-location-vs-previous-range).")
    print(cl.write_result("internal-dynamics-sequence", None, res, operationalization=op, params_source=ps,
                          script=__file__, probe=probe, notes=notes))
