"""displacement-range-re-anchor-ladder — TTrades (YmdC_LKT-Pk).

After displacement, draw the range from where the displacement STARTED to where it
ENDED and look for a PD array in its discount (long). If price does not reach the
level, do not chase: wait for the next displacement leg, MOVE the anchors to it, and
look again; repeat until the objective. Full entry/stop/target -> trade_test on the
book the loop produces (every fill, first or re-anchored), claim '+'.

Operationalised (bullish; bearish mirrors), 15m:
  displacement leg = a FIRED break (close beyond the latest 2/2 swing high + the
    threshold_fits 4-bar magnitude gate); start = the lowest low between the broken
    swing and the break bar; end = the highest high of the 4-bar window;
  PD array in discount = the highest bullish FVG stamped inside the leg whose bottom
    lies below the leg's 50% level; entry = limit at min(gap top, 50% level);
  the order is live from the fire until the NEXT fired leg in either direction (a
    same-direction leg = re-anchor: cancel and re-place on the new leg) or 24 bars;
  stop = the leg start; target 2R (the fixed HTF objective is not recoverable); exit
    150 min.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl, fair_value_gaps  # noqa: E402

CID = "displacement-range-re-anchor-ladder"
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
TD = pd.Timedelta(minutes=bc.TF_MIN)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    legs = bc.displacement_legs(b)
    fl = legs[legs["fired"]].sort_values(["fire", "brk"]).reset_index(drop=True)
    if fl.empty:
        return bc.empty(COLS)
    fv = fair_value_gaps(b[["open", "high", "low", "close"]])
    bull, bear = fv["bullish_fvg"].to_numpy(), fv["bearish_fvg"].to_numpy()
    glo, ghi = fv["gap_low"].to_numpy(), fv["gap_high"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    fires = fl["fire"].to_numpy()
    rows = []
    for i, r in fl.iterrows():
        d = int(r["direction"])
        s, f = int(r["leg_start_pos"]), int(r["fire"])
        st, en = float(r["leg_start_px"]), float(r["leg_end_px"])
        eq = (st + en) / 2.0
        lo_ = max(s + 2, 0)
        if d == 1:
            g = np.flatnonzero(bull[lo_:f + 1]) + lo_
            g = g[glo[g] < eq]
            if len(g) == 0:
                continue
            gi = g[np.argmax(ghi[g])]
            lvl = min(ghi[gi], eq)
        else:
            g = np.flatnonzero(bear[lo_:f + 1]) + lo_
            g = g[ghi[g] > eq]
            if len(g) == 0:
                continue
            gi = g[np.argmin(glo[g])]
            lvl = max(glo[gi], eq)
        if (d == 1 and not lvl > st) or (d == -1 and not lvl < st):
            continue
        start = ct[f]
        # cancel at the next fired leg's grade (either direction) or after 24 bars
        later = fires[(fires > f)]
        cancel = ct[int(later[0])] if len(later) else start + bc.TREND_BARS * TD
        cancel = min(cancel, start + bc.TREND_BARS * TD)
        rows.append((start, cancel, d, lvl, st))
    if not rows:
        return bc.empty(COLS)
    o = pd.DataFrame(rows, columns=["start", "cancel", "d", "lvl", "stop"])
    hit, dt = bc.touch_sided(m1, pd.DatetimeIndex(o["start"]), o["lvl"].to_numpy(),
                             o["d"].to_numpy(), pd.DatetimeIndex(o["cancel"]))
    o, dt = o[hit], dt[hit]
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt,
                       "direction": o["d"].to_numpy(), "stop_px": o["stop"].to_numpy(),
                       "rr": RR})
    return bc.finish(ev)


if __name__ == "__main__":
    ev = cl.cache_frame("reanchor_ladder_15m_fvg_discount", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"]:
        print(" ", k, res.get(k))
    op = {"rules": [
        "15m bars; displacement leg = fired break of the latest 2/2 swing (close beyond + "
        "threshold_fits magnitude gate N=4, r=1.5, d=0.65); leg start = extreme between the "
        "broken swing and the break; leg end = the 4-bar window extreme",
        "PD array in discount (long) = highest bullish FVG stamped inside the leg whose bottom "
        "is below the leg 50%; limit at min(gap top, 50%); bearish mirrors in premium",
        "order live from the leg's grade until the next fired leg (same direction = re-anchor "
        "to the new leg; opposite = abandon) or 24 bars; fill = first M1 touch, decide at "
        "that M1 close",
        "stop at the leg start; target 2R; exit 150 min"],
        "params": {"tf": bc.TF, "swing": "2/2", "disp_N": bc.DISP_N, "disp_r": bc.DISP_R,
                   "disp_d": bc.DISP_D, "pd_array": "FVG in discount", "eq": 0.5,
                   "order_life_bars": bc.TREND_BARS, "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: YmdC_LKT-Pk timeframes htf 15m (ladder yaml)",
           "swing": "phase3: locked 2/2 fractal",
           "disp_N": "threshold_fits: displacement magnitude gate default N=4",
           "disp_r": "threshold_fits: displacement magnitude gate default r=1.5",
           "disp_d": "threshold_fits: displacement magnitude gate default d=0.65",
           "pd_array": "corpus: YmdC_LKT-Pk 'draw out your OTE from where your displacement range started to where it ended' (PD array: order block / FVG per yaml; FVG chosen)",
           "eq": "method_spec: discount = below the leg's 0.5 (EQ)",
           "order_life_bars": "declared-before-run: an unfilled order lives 24 bars",
           "rr": "method_spec: §5.3 2R floor/fixed target stands in for the HTF objective",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The internal-liquidity-sweep expectation and the 'failure to "
                              "displace lower' confirmation are not applied (no threshold in the "
                              "corpus); the ltf 1m refinement is not applied. The book is every "
                              "fill the loop produces, first leg or re-anchored.")
    print(p)
