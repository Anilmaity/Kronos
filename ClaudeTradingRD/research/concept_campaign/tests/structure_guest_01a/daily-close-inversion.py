"""daily-close-inversion (guest: Jokerszn) -> trade_test, two readings (the concept's own
ambiguity: "close below the gap's mean threshold alone" vs "close below the entire gap").

Declared before the first run:
  * Daily bars: trading day rolling at 18:00 NY (harness default). Daily FVG = three-bar gap
    (detectors.primitives.fair_value_gaps), known at the close of its third bar.
  * Inversion: the FIRST daily close beyond the gap within 40 trading days of its formation.
      reading a: bullish gap -> daily close < gap_low (entire gap); bearish mirrored.
      reading b: bullish gap -> daily close < gap mid (mean threshold); bearish mirrored.
  * Inverted polarity: a bullish gap becomes a sell level (short), a bearish gap a buy level.
  * Entry ("LTF execution when price returns to the inversion level during a kill zone"):
    first M1 bar after the inversion close, within the next 5 trading days, that (i) lies in a
    forex kill zone (London 02-05 or NY AM 07-10 NY) and (ii) trades back to the level
    (a: gap_low for a short; b: gap mid) while closing inside the array (not beyond the stop).
    Decide at that M1 close; harness enters at the next M1 open. The LTF confirmation
    pattern is not modelled (limit-at-level reading).
  * Invalidation: a completed daily close back beyond the far side of the array (gap_high for
    a short) between the inversion and the touch day -> no trade.
  * Stop: the far side of the inverted array (gap_high for a short, gap_low for a long).
  * Target: "old daily highs or lows" -> the low (short) / high (long) of the inversion day.
  * max_hold 5D (wall clock), claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import fair_value_gaps

CID = "daily-close-inversion"
AGE_CAP = 40      # trading days from FVG formation to inversion close
RETEST_DAYS = 5   # trading days after inversion to find the kill-zone retest
MAX_HOLD = "5D"
KZ = ("fx_london", "fx_ny_am")
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "gap_lo", "gap_hi"]


def detect(m1: pd.DataFrame, reading: str) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    if len(d) < 5:
        return pd.DataFrame(columns=COLS)
    f = fair_value_gaps(d[["open", "high", "low", "close"]])
    H, L, C = d["high"].to_numpy(float), d["low"].to_numpy(float), d["close"].to_numpy(float)
    ct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    ct_ns = ct.as_unit("ns").asi8
    mt = m1.index
    mt_ns = mt.tz_convert("UTC").as_unit("ns").asi8
    close_ns = mt_ns + 60_000_000_000
    mh, ml, mc = m1["high"].to_numpy(float), m1["low"].to_numpy(float), m1["close"].to_numpy(float)
    kz = np.zeros(len(mt), bool)
    for k in KZ:
        kz |= cl.in_window(mt, *cl.KILLZONES[k])
    n = len(d)
    rows = []
    for i in np.flatnonzero(f["bullish_fvg"].to_numpy() | f["bearish_fvg"].to_numpy()):
        glo, ghi = f["gap_low"].iat[i], f["gap_high"].iat[i]
        bull = bool(f["bullish_fvg"].iat[i])
        mid = 0.5 * (glo + ghi)
        thr = (glo if bull else ghi) if reading == "a" else mid
        js = np.arange(i + 1, min(n, i + 1 + AGE_CAP))
        hit = js[(C[js] < thr) if bull else (C[js] > thr)]
        if not len(hit):
            continue
        j = hit[0]
        sgn = -1 if bull else 1                       # inverted polarity
        level = thr
        stop = ghi if bull else glo
        target = L[j] if bull else H[j]
        # retest window: M1 bars closing after the inversion close, up to RETEST_DAYS days
        jend = j + RETEST_DAYS
        if jend >= n:
            end_ns = np.iinfo(np.int64).max
        else:
            end_ns = ct_ns[jend]
        a = np.searchsorted(mt_ns, ct_ns[j], side="left")
        b = np.searchsorted(close_ns, end_ns, side="right")
        if b <= a:
            continue
        sl = slice(a, b)
        if sgn < 0:
            touch = kz[sl] & (mh[sl] >= level) & (mc[sl] < stop)
        else:
            touch = kz[sl] & (ml[sl] <= level) & (mc[sl] > stop)
        idx = np.flatnonzero(touch)
        if not len(idx):
            continue
        k = a + idx[0]
        # invalidation: a completed daily close back beyond the far side before this minute
        done = np.arange(j + 1, n)
        done = done[ct_ns[done] <= close_ns[k]]
        if len(done):
            if (sgn < 0 and (C[done] > stop).any()) or (sgn > 0 and (C[done] < stop).any()):
                continue
        rows.append((close_ns[k], sgn, stop, target, glo, ghi))
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px", "gap_lo", "gap_hi"])
    ev["decision_time"] = pd.to_datetime(ev["t"], utc=True)
    ev["available_at"] = ev["decision_time"]
    ev = ev.drop_duplicates(["decision_time", "direction", "stop_px", "target_px"])
    ev = ev.sort_values(["decision_time", "direction", "stop_px"]).reset_index(drop=True)
    return ev[COLS]


def run(reading):
    fn = (lambda m: detect(m, "a")) if reading == "a" else (lambda m: detect(m, "b"))
    ev = cl.cache_frame(f"dci_{reading}_age{AGE_CAP}_rt{RETEST_DAYS}", lambda: fn(cl.load_m1()))
    print(reading, "events", len(ev))
    probe = cl.probe_lookahead(fn, ev, lookback="100D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "dropped", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "daily bars, 18:00 NY roll; daily 3-bar FVG known at its third bar's close",
        "inversion = first daily close beyond the gap within 40 trading days: "
        + ("the ENTIRE gap (reading a)" if reading == "a" else "the gap's mean threshold (reading b)"),
        "bullish gap inverted -> short level; bearish gap inverted -> long level",
        "entry: first M1 in a forex kill zone (London 02-05 / NY AM 07-10 NY) within 5 trading days that "
        "trades back to the level and closes inside the array; decide at that M1 close",
        "invalidated by a completed daily close back beyond the array's far side before the touch",
        "stop = far side of the array; target = inversion day's low (short) / high (long); max_hold 5D"],
        "params": {"age_cap_days": AGE_CAP, "retest_days": RETEST_DAYS, "killzones": list(KZ),
                   "level": "gap_low/high" if reading == "a" else "gap mid", "stop": "array far side",
                   "target": "inversion-day extreme", "max_hold": MAX_HOLD, "grid4h": "n/a (1D)"}}
    src = {"age_cap_days": "declared-before-run: a gap older than ~2 months is not the current daily PD array",
           "retest_days": "declared-before-run: one trading week to return to the level",
           "killzones": "session_window_fit: forex London 02:00-05:00 and NY AM 07:00-10:00 NY (killzones.yaml, verbatim-verified)",
           "level": "corpus: JABOO4LYNjQ ambiguity - close below the entire gap vs below its mean threshold; one reading each",
           "stop": "corpus: JABOO4LYNjQ execution 'Above/below the inversion level'",
           "target": "corpus: JABOO4LYNjQ targets 'old daily highs or lows' (nearest: the inversion day's extreme)",
           "max_hold": "declared-before-run: daily-timeframe setup, one trading week",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="LTF confirmation (1H/15m) not modelled: entry is a kill-zone touch of the "
                              "inversion level. Reading a = close through entire gap, b = close through MT.")
    print(p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
