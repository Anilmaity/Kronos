"""old-fvg-across-the-curve — TTrades (the_foundation_01: uDJI2AbyyCs, bbWPoajy2MY).

After a smart money reversal, fair value gaps left on the previous side of the curve
are dragged forward; once price closes beyond such a gap in the new direction, a
return to it is reaccumulation (long) / redistribution (short) and the reaction there
is the entry. Full entry (the retest) + stop/target declared -> trade_test, claim '+'.

Operationalised (bullish; bearish mirrors):
  reversal = a 15m CISD (phase-3 rung-0 config: series_open, 2/2, max_wait 3) at the
  swing low e; prior sell-side leg = from the latest 2/2 swing high before e to e;
  old gaps = bearish FVGs stamped in that leg; a gap qualifies once a candle after e
  CLOSES above its top (within 16 bars of the CISD); entry = limit at the gap top on
  the first M1 retest after max(close-above, CISD) close, live 16 bars; stop = the
  reversal's protected swing (the CISD extreme, method_spec §5.1); target 2R.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl, fair_value_gaps  # noqa: E402
from detectors.cisd import cisd_events         # noqa: E402

CID = "old-fvg-across-the-curve"
RR = 2.0
MAX_HOLD = "150min"
CLOSE_BARS = 16
LIVE_BARS = 16
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
TD = pd.Timedelta(minutes=bc.TF_MIN)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    ohlc = b[["open", "high", "low", "close"]]
    cs = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3,
                     min_series=1)
    if cs.empty:
        return bc.empty(COLS)
    is_sh, is_sl = bc.swing_arrays(b)
    fv = fair_value_gaps(ohlc)
    bull, bear = fv["bullish_fvg"].to_numpy(), fv["bearish_fvg"].to_numpy()
    glo, ghi = fv["gap_low"].to_numpy(), fv["gap_high"].to_numpy()
    c = b["close"].to_numpy(float)
    n = len(b)
    pos_of = pd.Series(np.arange(n), index=b.index)
    sh_pos, sl_pos = np.flatnonzero(is_sh), np.flatnonzero(is_sl)
    rows = []
    for _, r in cs.iterrows():
        e = int(pos_of[r["extreme_time"]])
        cf = int(pos_of[r["confirm_time"]])
        d = 1 if r["direction"] == "bullish" else -1
        opp = sh_pos if d == 1 else sl_pos
        i = np.searchsorted(opp, e) - 1
        if i < 0:
            continue
        p = int(opp[i])
        gaps = np.flatnonzero((bear if d == 1 else bull)[p + 2:e + 1]) + p + 2
        for g in gaps:
            edge = ghi[g] if d == 1 else glo[g]     # the side facing the new direction
            end = min(n, cf + 1 + CLOSE_BARS)
            seg = c[e + 1:end]
            a = np.flatnonzero(seg > edge) if d == 1 else np.flatnonzero(seg < edge)
            if len(a) == 0:
                continue
            ka = e + 1 + int(a[0])
            rows.append((max(ka, cf), d, edge, float(r["protected_swing"])))
    if not rows:
        return bc.empty(COLS)
    s = pd.DataFrame(rows, columns=["k", "d", "lvl", "stop"])
    s = s[(s["d"] == 1) & (s["lvl"] > s["stop"]) | (s["d"] == -1) & (s["lvl"] < s["stop"])]
    start = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")[s["k"].to_numpy()]
    hit, dt = bc.touch_sided(m1, start, s["lvl"].to_numpy(), s["d"].to_numpy(),
                             start + LIVE_BARS * TD)
    s, dt = s[hit], dt[hit]
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt,
                       "direction": s["d"].to_numpy(), "stop_px": s["stop"].to_numpy(),
                       "rr": RR})
    return bc.finish(ev)


if __name__ == "__main__":
    ev = cl.cache_frame("oldfvg_15m_cisd_mw3_retest", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"]:
        print(" ", k, res.get(k))
    op = {"rules": [
        "15m bars. Smart money reversal = CISD (close through the opening price of the "
        "opposing-candle series into a 2/2 swing, within 3 bars)",
        "prior leg (bullish case) = latest 2/2 swing high before the reversal low to that low; "
        "old gaps = bearish FVGs stamped in that leg",
        "a gap is carried across the curve once a candle after the low CLOSES above its top "
        "(within 16 bars of the CISD)",
        "entry: limit at the gap top, first M1 retest after the later of that close and the "
        "CISD close, live 16 bars; decide at that M1 close",
        "stop at the reversal extreme (protected swing); target 2R; exit 150 min; bearish mirrors"],
        "params": {"tf": bc.TF, "cisd_level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "close_bars": CLOSE_BARS, "live_bars": LIVE_BARS,
                   "stop": "protected swing", "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: old-fvg-across-the-curve.yaml ltf 15m/5m; phase3 primary entry TF",
           "cisd_level_rule": "phase3: locked CISD reading (series_open)",
           "swing": "phase3: locked 2/2 fractal",
           "max_wait": "phase3: locked max_wait=3",
           "close_bars": "declared-before-run: the close beyond the old gap must come within 16 bars of the CISD",
           "live_bars": "declared-before-run: the retest limit is live 16 bars (4h)",
           "stop": "method_spec: §5.1 'The stop is the protected swing' (concept states no stop)",
           "rr": "method_spec: §5.3 2R floor (concept states no target beyond 'buyside liquidity above')",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Status underspecified: 'smart money reversal' operationalised as "
                              "CISD only; stop/target borrowed from the method spec. Each "
                              "qualifying gap fills separately; same-minute fills deduplicated.")
    print(p)
