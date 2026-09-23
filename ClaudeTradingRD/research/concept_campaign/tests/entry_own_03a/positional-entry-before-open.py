"""positional-entry-before-open

Setup ("the same framing" for both readings): a valid 15-minute setup (phase-3 bare
15m CISD) with its protected swing already formed, all timeframes green (last
closed 1D, 4H and 1H candles all closed in the trade direction), a clear target =
previous day high (longs) / low (shorts) that is still >= 2R away, decided between
07:00 and 12:00 New York. Stop = the protected swing, target = PDH/PDL, exit at
16:00 NY at the latest.

reading a (trade_test, claim +): the PRE-OPEN subset (decided 07:00-09:30 NY) beats
                                  a matched random entry.
reading b (gate_test, claim +):   on the 07:00-12:00 book, pre-open (< 09:30) entries
                                  beat post-open (09:30-12:00) entries.
All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, cisd_book, day_context, run_and_print, PHASE3_SRC  # noqa: E402

TF = "15min"
WIN_START, OPEN, WIN_END = "07:00", "09:30", "12:00"
EXIT_NY = "16:00"
MIN_RR = 2.0


def _dir_close(m1, times, tf):
    b = cl.build_bars(m1, tf)
    a = cl.asof(b, times)
    return np.sign(a["close"].to_numpy(float) - a["open"].to_numpy(float))


def detect_all(m1: pd.DataFrame) -> pd.DataFrame:
    ev = cisd_book(m1, TF)
    cols = ["pre_open"]
    if ev.empty:
        return ev.assign(**{c: pd.Series(dtype=bool) for c in cols})
    t = pd.DatetimeIndex(ev["decision_time"])
    ev = ev[cl.in_window(t, WIN_START, WIN_END)].reset_index(drop=True)
    if ev.empty:
        return ev.assign(pre_open=pd.Series(dtype=bool))
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy()
    green = ((_dir_close(m1, t, "1D") == d) & (_dir_close(m1, t, "4h") == d)
             & (_dir_close(m1, t, "1h") == d))
    ctx = day_context(m1, t)
    tgt = np.where(d == 1, ctx["pdh"].to_numpy(), ctx["pdl"].to_numpy())
    px = ev["confirm_close"].to_numpy()
    risk = np.abs(px - ev["stop_px"].to_numpy())
    reward = d * (tgt - px)
    ok = green & np.isfinite(tgt) & (reward >= MIN_RR * risk)
    ev = ev.assign(target_px=tgt)[ok].reset_index(drop=True)
    t = pd.DatetimeIndex(ev["decision_time"])
    ny = cl.to_ny(t)
    hh, mm = map(int, EXIT_NY.split(":"))
    exit_ny = ny.normalize() + pd.Timedelta(hours=hh, minutes=mm)
    ev["max_hold"] = pd.TimedeltaIndex(exit_ny.tz_convert("UTC") - t)
    ev["pre_open"] = cl.in_window(t, WIN_START, OPEN).astype(bool)
    return ev.drop(columns=["rr"])


def detect_pre(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_all(m1)
    return ev[ev["pre_open"]].reset_index(drop=True)


OP_RULES = [
    "15m setup: phase-3 bare 15m CISD (series_open, 2/2 swings, max_wait 3, min_series 1); its protected "
    "swing is formed before the decision by construction; stop = protected swing",
    "all timeframes green: last CLOSED 1D, 4H (forex grid) and 1H candles all closed in the trade direction",
    "target = previous completed trading day's high (long) / low (short); require reward >= 2 x risk "
    "measured from the confirming close, else no trade ('if 2R is not achievable, wait')",
    "decision window 07:00-12:00 NY; pre-open = decided before 09:30 NY",
    "enter next M1 open; exit at target, stop, or 16:00 NY the same day"]
PARAMS = {"tf": TF, "win_start": WIN_START, "open": OPEN, "win_end": WIN_END,
          "exit_ny": EXIT_NY, "min_rr": MIN_RR, "grid4h": "forex", "green": "1D+4H+1H close direction"}
SRC = {"tf": "corpus: U4j-fZD-FJk 'Really only if uh it's a 15-minute valid setup'",
       "open": "corpus: U4j-fZD-FJk 'I need a protected swing I can trust prior to the open' (09:30 equity open)",
       "win_start": "session_window_fit: forex NY AM killzone start 07:00 (killzones.yaml) as the pre-open window start",
       "win_end": "session_window_fit: NY AM session end 12:00 (SESSION_WINDOWS ny_am)",
       "exit_ny": "declared-before-run: hold to the 16:00 NY equity close ('the day's framed objective')",
       "min_rr": "corpus: wM1s7UivQ08 'if 2R is not achievable with that stop, do not take the pre-open entry'",
       "grid4h": "session_window_fit: forex grid (carried as a knob, trap 8)",
       "green": "declared-before-run: 'all timeframes green (daily, 4-hour, hourly supporting the same direction)' "
                "-> last closed candle of each closed in the trade direction"}

if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        ev = cl.cache_frame("peo_pre_v1", lambda: detect_pre(cl.load_m1()))
        print("a n", len(ev))
        probe = cl.probe_lookahead(detect_pre, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=None, ctrl_tod_tol_min=30)
        run_and_print(res)
        src = dict(SRC, ctrl_tod_tol_min="declared-before-run: control held within +/-30 min of the NY clock "
                   "so the setup is judged against the same hours (trap 9); the timing question is reading b")
        p = cl.write_result("positional-entry-before-open", "a", res,
                            operationalization={"rules": OP_RULES + ["trade_test on the pre-open subset only"],
                                                "params": dict(PARAMS, ctrl_tod_tol_min=30)},
                            params_source=src, script=__file__, probe=probe,
                            notes="Indices' 09:30 equity open applied to gold as a clock time.")
        print("wrote", p)
    if "b" in which:
        ev = cl.cache_frame("peo_all_v1", lambda: detect_all(cl.load_m1()))
        print("b n", len(ev), "pre share", round(ev["pre_open"].mean(), 3))
        probe = cl.probe_lookahead(detect_all, ev, lookback="30D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "pre_open", mask_available_at="decision_time", max_hold=None)
        run_and_print(res)
        p = cl.write_result("positional-entry-before-open", "b", res,
                            operationalization={"rules": OP_RULES + ["gate_test: pre-open vs post-open (09:30-12:00)"],
                                                "params": PARAMS},
                            params_source=SRC, script=__file__, probe=probe,
                            notes="Measurable from the concept: 'outcome of pre-open entries versus post-09:30 "
                                  "entries on the same framing'. Clock gate; the mask is a probed column.")
        print("wrote", p)
