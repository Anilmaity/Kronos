"""entry-time-window — update_20261007_live_07 / _live_11, new readings only (gate_test).

Prior readings a (08:30-11:00) and b (09:30-10:00) are NOT re-tested. New claims:

  u1007a  live_07, 9YVBe-20Hdg: "some of my favorite trades are like from 6:00 to 8:00 a.m.
          because it's the 15minute time frame position prior to the open."
          Baseline book: 15m bare CISD (phase-3 locked config, 2R, 10 entry-TF bars =
          150 min). Gate: decision time in [06:00, 08:00) New York. Claim '+': pre-open
          06-08 entries beat the rest of the day's 15m entries (control-adjusted).
          (The "9 to 11" limited-time band is not a separate reading: it overlaps the
          prior 08:30-11:00 reading a almost entirely.)

  u1007b  live_11, KBJAGgkXdeI: "no clear direction off the open ... wait five, wait 15
          minutes, wait 30 minutes" / "this is more of a reversal candle on a day where you
          anticipate an expansion. You don't really want to trade this candle. You'd rather
          just wait for 10:00 a.m."
          Baseline book: the batch 5m bare CISD (time_own_01a/_common.py, same as prior
          readings), restricted to decisions in [09:30, 10:30) NY. Gate: decision >= 10:00
          (waited for the 10:00 candle) vs [09:30, 10:00) (traded off the open). Claim '+'.
          The "no direction" / "anticipated expansion day" preconditions are discretionary
          and not modelled: this tests the unconditional deferral.
Declared before any run. Clock: America/New_York with DST.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "time_own_01a"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "entry-time-window"
TZ_SRC = ("session_window_fit: America/New_York with DST (settled, 99.8% of 605 daily "
          "breaks resume at 18:00 NY)")


def cisd15(m1):
    b = cl.build_bars(m1, "15min")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[["open", "high", "low", "close"]], **C.CISD_KW)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": C.BASE_RR})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def detect_a(m1):
    ev = cisd15(m1)
    ev["in_window"] = C.window_mask(ev["decision_time"], [("06:00", "08:00")])
    return ev


def gate_b(ev):
    ev = ev[C.window_mask(ev["decision_time"], [("09:30", "10:30")])].copy()
    ev["in_window"] = C.window_mask(ev["decision_time"], [("10:00", "10:30")])
    return ev.reset_index(drop=True)


def detect_b(m1):
    return gate_b(C.cisd5(m1))


READINGS = {
    "u1007a": dict(
        frame=lambda: cl.cache_frame("etw_u1007a_cisd15", lambda: detect_a(cl.load_m1())),
        detect=detect_a, max_hold="150min", lookback="20D",
        rules=["baseline: 15m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
               "confirming 15m close, enter next M1 open, stop = protected swing, 2R, 150 min exit",
               "gate: decision time in [06:00, 08:00) New York; complement = every other "
               "15m CISD entry of the day"],
        params=dict(baseline_tf="15min", cisd=C.CISD_KW, rr=C.BASE_RR, max_hold="150min",
                    window=[("06:00", "08:00")], tz="America/New_York"),
        src=dict(baseline_tf="corpus: 9YVBe-20Hdg 'because it's the 15minute time frame "
                             "position prior to the open'",
                 cisd=C.BASE_SRC["cisd"], rr=C.BASE_SRC["rr"],
                 max_hold="phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 150 min on 15m",
                 window="corpus: 9YVBe-20Hdg 'some of my favorite trades are like from 6:00 to 8:00 a.m.'",
                 tz=TZ_SRC)),
    "u1007b": dict(
        frame=lambda: gate_b(C.base_cached()),
        detect=detect_b, max_hold=C.BASE_MAX_HOLD, lookback="10D",
        rules=["baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
               "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min "
               "exit; only decisions in [09:30, 10:30) New York",
               "gate: decision in [10:00, 10:30) (waited for the 10:00 candle); complement = "
               "decisions in [09:30, 10:00) (traded off the open)"],
        params=dict(C.BASE_PARAMS, band=[("09:30", "10:30")], window=[("10:00", "10:30")],
                    tz="America/New_York"),
        src=dict(C.BASE_SRC,
                 band="corpus: KBJAGgkXdeI 'wait five, wait 15 minutes, wait 30 minutes' "
                      "(ladder spans 09:30-10:00; band closed at 10:30 = equal 30-min arm)",
                 window="corpus: KBJAGgkXdeI 'You don't really want to trade this candle. "
                        "You'd rather just wait for 10:00 a.m.'",
                 tz=TZ_SRC)),
}


if __name__ == "__main__":
    for rd, s in READINGS.items():
        ev = s["frame"]()
        probe = cl.probe_lookahead(s["detect"], ev, lookback=s["lookback"])
        res = cl.gate_test(ev, "in_window", mask_available_at="decision_time",
                           max_hold=s["max_hold"], claim="+")
        p = cl.write_result(CID, rd, res,
                            operationalization={"rules": s["rules"], "params": s["params"]},
                            params_source=s["src"], script=__file__, probe=probe,
                            notes="New claim only (update_20261007); discretionary "
                                  "'no direction'/'expansion day' preconditions not modelled.")
        print(rd, p)
        for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "ties", "halves"):
            print("  ", k, res.get(k))
