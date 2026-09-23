"""market-curve-side (TTrades, E6bpY4dQvlE / xvqsLTpmpsI) — gate_test.

Claim: trades taken against the curve (a reversal sought on the side of the curve that is
still seeking liquidity the other way) get run through; trades with the curve are better.
'+' = with-curve trades beat against-curve trades of the same book.

The corpus gives NO rule that locates the curve (status underspecified). Its detection rule
is "moving up = one side of the curve, moving down = the other". Declared stand-in, before
the first run: the side of the curve is the direction of the latest DISPLACED structure
break on the structure timeframe paired with the entry (4H for a 15m entry):
  * 4H bars (forex grid); latest confirmed 2/2 swing high (low) not yet broken;
  * break = first 4H CLOSE beyond it (displacement's structural gate, threshold_fits §2a);
  * magnitude gate (threshold_fits §2b): over N=4 candles from the break, window range /
    pre-break 4-candle range >= 1.5 AND distance travelled beyond the level / pre range
    >= 0.65; known at the close of the 4th window candle;
  * side = +1 after an up displacement, -1 after a down one, held until the opposite.
Baseline: phase-3 rung-0 15m CISD (2R, protected-swing stop, 150min). Gate: CISD direction
== side of the curve. Events before the first side exists are dropped.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

MAX_HOLD = "150min"
N, R_MIN, D_MIN = 4, 1.5, 0.65


def curve_side_events(b: pd.DataFrame) -> pd.DataFrame:
    """Displaced structure breaks on bars b: (known_at close_time, side)."""
    sw = swing_points(b[["high", "low"]], 2, 2)
    o, h, lo, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    ish, isl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    n = len(b)
    rows = []
    hi_lvl = lo_lvl = np.nan
    for j in range(n):
        # a swing at i is confirmed at the close of i+2: usable from bar i+3 on
        i = j - 3
        if i >= 0 and ish[i]:
            hi_lvl = h[i]
        if i >= 0 and isl[i]:
            lo_lvl = lo[i]
        for side, lvl in ((1, hi_lvl), (-1, lo_lvl)):
            if np.isnan(lvl):
                continue
            if (side == 1 and c[j] > lvl) or (side == -1 and c[j] < lvl):
                if side == 1:
                    hi_lvl = np.nan
                else:
                    lo_lvl = np.nan
                if j - N < 0 or j + N - 1 >= n:
                    continue
                pre = h[j - N:j].max() - lo[j - N:j].min()
                win_h, win_l = h[j:j + N].max(), lo[j:j + N].min()
                dist = (win_h - lvl) if side == 1 else (lvl - win_l)
                if pre > 0 and (win_h - win_l) / pre >= R_MIN and dist / pre >= D_MIN:
                    rows.append({"known_at": ct[j + N - 1], "side": side})
    return pd.DataFrame(rows, columns=["known_at", "side"])


def detect(m1):
    ev, _ = C.cisd_book(m1, "15min")
    b4 = cl.build_bars(m1, "4h", grid4h="forex")
    cs = curve_side_events(b4).sort_values("known_at", kind="stable")
    kn = cl.data.utc_ns(pd.DatetimeIndex(cs["known_at"]))
    tn = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"]))
    pos = np.searchsorted(kn, tn, side="right") - 1
    ok = pos >= 0
    ev = ev[ok].reset_index(drop=True)
    side = cs["side"].to_numpy()[pos[ok]]
    ev["curve_side"] = side
    ev["side_known_at"] = pd.DatetimeIndex(cs["known_at"]).to_numpy()[pos[ok]]
    ev["with_curve"] = ev["direction"].to_numpy() == side
    return ev.drop(columns=["bar_pos"])


if __name__ == "__main__":
    ev = cl.cache_frame("curve_side_cisd15_4h_disp", lambda: detect(cl.load_m1()))
    print(len(ev), ev.with_curve.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="120D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "with_curve", mask_available_at="decision_time", max_hold=MAX_HOLD)
    C.show(res)
    p = cl.write_result(
        "market-curve-side", None, res,
        operationalization={"rules": [
            "side of the curve = direction of the latest displaced 4H (forex grid) structure break: first 4H close beyond the latest confirmed unbroken 2/2 swing, with N=4 window range/pre-range >= 1.5 and distance beyond the level/pre-range >= 0.65; known at the 4th window candle's close; held until the opposite",
            "baseline: 15m rung-0 CISD (series_open, 2/2, max_wait 3), stop protected swing, 2R, 150min exit",
            "gate: CISD direction equals the side of the curve (not fading the direction price is seeking)"],
            "params": {"structure_tf": "4h", "grid4h": "forex", "swing": "2/2", "N": N,
                       "r": R_MIN, "d": D_MIN, "baseline_tf": "15min", "max_wait": 3,
                       "rr": 2.0, "max_hold": MAX_HOLD}},
        params_source={
            "structure_tf": "method_spec: §1.2 pairing 4-hour structure / 15-minute entry",
            "grid4h": "phase3: forex grid for gold (carried as a knob)",
            "swing": "phase3: swing_points left=2 right=2",
            "N": "threshold_fits: displacement N-window default N=4",
            "r": "threshold_fits: displacement win_range/pre_range default 1.5",
            "d": "threshold_fits: displacement dist/pre_range default 0.65",
            "baseline_tf": "phase3: primary stack entry TF",
            "max_wait": "phase3: locked CISD config max_wait=3",
            "rr": "phase3: locked 2R target",
            "max_hold": "phase3: 10 entry-TF bars"},
        script=__file__, probe=probe,
        notes="Concept is underspecified: no rule locates the curve. Tested under a declared stand-in (latest displaced 4H structure break = the direction price is seeking); a NULL here speaks to that operationalisation, not to an undefined curve.")
    print(p)
