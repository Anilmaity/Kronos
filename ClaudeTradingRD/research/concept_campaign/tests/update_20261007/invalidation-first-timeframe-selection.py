"""update_20261007 / invalidation-first-timeframe-selection — NEW claim only.

Prior readings 'a' (1H vs 5m execution) and 'b' (1H invalidation vs 5m habit stop) are
untouched. The new claim (live_12, rTomJ8URFnw, New York Open Live Q&A):

  "one thing about here on the 5m minute is if we don't really form a gap here, it means
   should be a lower time frame gap ... it's just going to be a continuation"
  "Watch the 5m minute for the closure, right? But we know there's no gap here. And I
   wouldn't want to put a stop all the way up there. So you go to the 3 minute, which is
   your next lower time frame. ... Something where there's no gap, right? So they have to
   go down one more time frame and then you have a gap right now."

Operationalization (one pre-declared reading, u1007a, trade_test):
  * 5m continuation leg = a FIRED threshold_fits displacement (close beyond the latest
    confirmed unbroken 2/2 swing, 4-bar magnitude gate), as in batch entry_own_03b.
  * no-gap trigger: no same-direction 5m FVG formed inside the leg (stamped on bars
    leg_start+2 .. fire). The only 5m gap is then before the leg origin, i.e. "all the
    way up there".
  * step down: the most recent same-direction 3m FVG formed inside the leg (first bar
    starts at/after the 5m leg-start bar, third bar closes <= the 5m fire close) whose far
    edge is still untouched and beyond the 5m close. No such 3m gap -> no trade.
  * decide at the 5m fire-bar close ("watch the 5m for the closure"), enter next M1 open,
    stop at the 3m gap's far edge (bearish: gap high; bullish: gap low; no buffer),
    target 2R, time exit 10 x 5m = 50 min.

Rerun 2026-10-07 with the KronosVault preloaded (Backtest Methodology Traps, Concept
Campaign 2026-09-23 lessons). Rules are the SAME pre-declared reading -- changing them after
the first run's UNDERPOWERED would be a forking path. Audit: trap 3/9 (5m decision at the
fire bar's close_time, 3m gap only if its third bar closed <= that; symmetric probe), trap 7
(exposure_bars real vs control printed), trap 6 (MDE read before diff), campaign lesson 2
(spread hidden by the 0.04R cost that cancels in diff: stop distance in pt printed and put
in notes). Campaign lesson 1 (stop placement != stop distance) has no harness control; it
can only inflate a diff, so it bites an EDGE, not this reading.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
import _batch_common as bc                                  # noqa: E402
from _batch_common import cl                                # noqa: E402
from detectors.primitives import fair_value_gaps            # noqa: E402

CID = "invalidation-first-timeframe-selection"
EXEC_TF, LOWER_TF = "5min", "3min"
RR = 2.0
HOLD = "50min"
TOD = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
OHLC = ["open", "high", "low", "close"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").asi8


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b5 = cl.build_bars(m1, EXEC_TF)
    b3 = cl.build_bars(m1, LOWER_TF)
    if len(b5) < 50 or len(b3) < 10:
        return bc.empty(COLS)
    legs = bc.displacement_legs(b5)
    legs = legs[legs["fired"]]
    if legs.empty:
        return bc.empty(COLS)

    f5 = fair_value_gaps(b5[OHLC])
    cum5 = {1: np.concatenate([[0], np.cumsum(f5["bullish_fvg"].to_numpy(int))]),
            -1: np.concatenate([[0], np.cumsum(f5["bearish_fvg"].to_numpy(int))])}
    s5, c5t = _ns(b5.index), _ns(b5["close_time"])
    c5 = b5["close"].to_numpy(float)

    f3 = fair_value_gaps(b3[OHLC])
    s3, c3t = _ns(b3.index), _ns(b3["close_time"])
    first3 = np.full(len(b3), np.iinfo(np.int64).min)       # start of the gap's first bar
    first3[2:] = s3[:-2]
    gap3 = {1: (np.flatnonzero(f3["bullish_fvg"].to_numpy()), f3["gap_low"].to_numpy(float)),
            -1: (np.flatnonzero(f3["bearish_fvg"].to_numpy()), f3["gap_high"].to_numpy(float))}

    mt = _ns(m1.index)
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)

    rows = []
    for d, sp, f in legs[["direction", "leg_start_pos", "fire"]].to_numpy(int):
        lo = sp + 2
        if lo <= f and cum5[d][f + 1] - cum5[d][lo] > 0:
            continue                                          # 5m gap inside the leg
        T, t0 = c5t[f], s5[sp]
        ks, edge = gap3[d]
        hi_k = np.searchsorted(c3t[ks], T, "right")          # third bar closed <= T
        for k in ks[:hi_k][::-1]:
            if first3[k] < t0:
                break                                         # older gaps predate the leg
            e = edge[k]
            if not d * (c5[f] - e) > 0:
                continue
            a, z = np.searchsorted(mt, c3t[k], "left"), np.searchsorted(mt, T, "left")
            if a < z and ((d == 1 and ml[a:z].min() <= e) or (d == -1 and mh[a:z].max() >= e)):
                continue                                      # far edge already traded
            rows.append((T, d, e))
            break
    if not rows:
        return bc.empty(COLS)
    t = pd.to_datetime(np.array([r[0] for r in rows], dtype="int64"), utc=True)
    ev = pd.DataFrame({"decision_time": t, "available_at": t,
                       "direction": np.array([r[1] for r in rows], int),
                       "stop_px": np.array([r[2] for r in rows], float), "rr": RR})
    return bc.finish(ev)


RULES = [
    "5m bars. Continuation leg = FIRED displacement: a close beyond the latest confirmed "
    "unbroken 2/2 swing whose 4-bar window from the break has range >= 1.5x and travel "
    "beyond the level >= 0.65x the prior 4-bar range; leg origin = extreme between the "
    "broken swing and the break",
    "no-gap trigger: no same-direction 5m FVG stamped on bars leg_origin+2 .. fire bar",
    "step down to 3m: most recent same-direction 3m FVG whose first bar starts at/after the "
    "5m leg-origin bar and whose third bar closes <= the 5m fire close, with far edge beyond "
    "the 5m close and not touched by any M1 bar since the gap formed; none -> no trade",
    "decide at the 5m fire-bar close, enter next M1 open (harness), stop = 3m gap far edge "
    "(gap low long / gap high short), no buffer",
    "target 2R; time exit 50 min; test: trade_test vs matched random entries (same "
    "direction, stop and target distance, +/-30 days, NY time of day +/-30 min), claim +",
]
PARAMS = {"exec_tf": EXEC_TF, "lower_tf": LOWER_TF, "swing": "2/2", "disp_N": bc.DISP_N,
          "disp_r": bc.DISP_R, "disp_d": bc.DISP_D, "no_gap_window": "leg_origin+2..fire",
          "gap_pick": "most recent untouched 3m gap inside the leg", "stop_buffer": 0.0,
          "rr": RR, "max_hold": HOLD, "ctrl_tod_tol_min": TOD,
          "grid4h": "n/a (no 4h bars)"}
SRC = {"exec_tf": "corpus: rTomJ8URFnw 'Watch the 5m minute for the closure' / 'here on the 5m minute'",
       "lower_tf": "corpus: rTomJ8URFnw 'So you go to the 3 minute, which is your next lower time frame.'",
       "swing": "phase3: locked 2/2 fractal",
       "disp_N": "threshold_fits: displacement magnitude gate default N=4",
       "disp_r": "threshold_fits: displacement magnitude gate default r=1.5",
       "disp_d": "threshold_fits: displacement magnitude gate default d=0.65",
       "no_gap_window": "declared-before-run: 'we know there's no gap here' read as no 5m FVG inside the current leg; the source gives no distance rule for 'too far' (draft ambiguity), so the nearest 5m gap is then beyond the leg origin",
       "gap_pick": "corpus: rTomJ8URFnw 'then you have a gap right now' + 'that high should remain' (gap edge must still hold); declared-before-run: most recent such gap",
       "stop_buffer": "corpus: rTomJ8URFnw 'I wouldn't want to put a stop all the way up there' (stop at the gap; no buffer stated)",
       "rr": "method_spec: §5 2R normal (library execution.targets 'Sized in R from that stop; 2R described as normal')",
       "max_hold": "phase3: 10 entry-TF bars (§1.13) -> 10 x 5m = 50 min",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9, displacement events cluster in hours and the concept is not about timing",
       "grid4h": "declared-before-run: no 4h bars used"}


if __name__ == "__main__":
    ev = cl.cache_frame("iftfs_u1007_5m_nogap_3mgap", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=TOD, keep_trades=True)
    tr = res.pop("_trades")
    sd = tr["risk"]                                          # entry-to-stop distance, pt
    q = {f"q{int(k * 100)}": v for k, v in sd.quantile([.1, .5, .9]).round(3).items()}
    spread_R = float((0.30 / sd).median())
    print("stop pt q10/50/90", q, "median R cost of a 0.30pt spread", round(spread_R, 3))
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped", "halves"):
        print(k, res.get(k))
    print("wrote", cl.write_result(CID, "u1007a", res,
          operationalization={"rules": RULES, "params": PARAMS}, params_source=SRC,
          script=__file__, probe=probe,
          notes="New claim only (5m no-gap -> 3m gap stop). Prior readings a/b untouched. "
                "Market entry at the 5m closure; the source took no trade, so entry is framing. "
                "Source example is NASDAQ, not gold. Rerun with vault context (same rules). "
                f"Stop distance pt q10/50/90 {q}; a 0.30pt spread costs a median "
                f"{spread_R:.2f}R per trade, which the 0.04R modelled cost understates "
                "(cancels in diff, not in avg_R)."))
