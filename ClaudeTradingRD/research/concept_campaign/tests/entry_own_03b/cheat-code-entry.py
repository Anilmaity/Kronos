"""cheat-code-entry — TTrades (NgFIza9qsGQ, credited to 'Austin').

In an aggressive trend, when an OPPOSING candle closes (up-close in a down trend),
enter at the open of the very next candle, stop one point beyond that candle's
extreme, target the trend's objective. Full entry/stop/target -> trade_test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl  # noqa: E402

CID = "cheat-code-entry"
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    legs = bc.displacement_legs(b)
    tdir, tfire, _ = bc.trend_state(b, legs)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    opp = ((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o))
    j = np.flatnonzero(opp)
    if len(j) == 0:
        return bc.empty(COLS)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[j]).tz_convert("UTC")
    d = tdir[j]
    stop = np.where(d == -1, h[j], l[j])           # beyond the opposing candle
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d,
                       "stop_px": stop, "rr": RR})
    return bc.finish(ev)


if __name__ == "__main__":
    ev = cl.cache_frame("cheatcode_15m_disp4_trend24", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    keys = ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
            "ties", "exposure_bars", "ctrl_overlap", "dropped", "halves"]
    for k in keys:
        print(k, res.get(k))
    op = {"rules": [
        "15m bars. Aggressive trend = latest FIRED displacement: a close beyond the latest "
        "confirmed unbroken 2/2 swing whose 4-bar window from the break has range >= 1.5x and "
        "travel beyond the level >= 0.65x the prior 4-bar range; trend lives 24 bars after "
        "the grade is known and dies on a close beyond the leg's origin extreme",
        "signal: an opposing-close candle (up-close in a bearish trend, down-close in a "
        "bullish one) closes while the trend is alive and after the fire bar",
        "enter with the trend at the next M1 open after that candle's close (= open of the "
        "next candle)",
        "stop at the opposing candle's extreme (high for shorts, low for longs), no buffer",
        "target 2R; time exit 150 min"],
        "params": {"tf": bc.TF, "swing": "2/2", "disp_N": bc.DISP_N, "disp_r": bc.DISP_R,
                   "disp_d": bc.DISP_D, "trend_bars": bc.TREND_BARS, "stop_buffer": 0.0,
                   "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: NgFIza9qsGQ timeframes htf 15m/5m (cheat-code-entry.yaml); phase3 primary entry TF",
           "swing": "phase3: locked 2/2 fractal",
           "disp_N": "threshold_fits: displacement magnitude gate default N=4",
           "disp_r": "threshold_fits: displacement magnitude gate default r=1.5",
           "disp_d": "threshold_fits: displacement magnitude gate default d=0.65",
           "trend_bars": "declared-before-run: aggressive trend lifetime 24 bars (corpus never bounds it)",
           "stop_buffer": "declared-before-run: 'one point' is an index-futures tick; gold uses the extreme itself",
           "rr": "method_spec: §5.3 2R floor/fixed target stands in for 'the objective the trend is reaching for'",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Single reading (status specified). Every qualifying opposing candle "
                              "is taken; the corpus gives no filter for which one." + " CAVEAT (post-verdict diagnostic, verdict NOT changed): the differential is concentrated in the smallest stops. By stop/ATR96(15m range) quintile the diff was Q1..Q5 +0.227/+0.095/+0.062/+0.006/+0.004R (Q5 stop ~0.6 ATR). A pure-noise book (random direction at random 15m closes, stop at the just-closed candle's extreme, 2R, 150 min; n=58,539, n_boot=500, not written) also came back EDGE (+0.026R [+0.013,+0.039]), +0.14R in its smallest-stop quintile: the matched control places the same stop DISTANCE at an arbitrary level, while these books put it at a recent candle extreme, which M1 noise reaches less often. Treat this EDGE as a stop-geometry artefact candidate, not a trend-entry edge.")
    print(p)
