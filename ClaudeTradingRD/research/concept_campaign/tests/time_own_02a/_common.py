"""Shared pieces for batch time_own_02a (TTrades own-voice time concepts).

Baseline books = the phase-3 locked bare CISD book (series_open level, 2/2 swings,
max_wait 3, decide at the confirming bar's close, enter next M1 open, stop at the
protected swing, 2R), on the entry timeframe the concept names; max_hold = 10
entry-TF bars (phase-3 §1.13).  Clock gates are emitted as columns by `detect`.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402
import concept_lab as cl      # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

HOLD = {"5min": "50min", "15min": "150min", "1h": "10h"}


def base_params(tf):
    return {"baseline": "bare CISD", "baseline_tf": tf, "level_rule": "series_open",
            "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": HOLD[tf]}


def base_src(tf, tf_src):
    s = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked rung-0 config)"
         for k in base_params(tf)}
    s["baseline_tf"] = tf_src
    s["max_hold"] = "phase3: 10 entry-TF bars (§1.13)"
    return s


def base_rule(tf):
    return (f"baseline book: phase-3 bare {tf} CISD (series_open level, 2/2 swings, max_wait 3), "
            f"decide at the confirming {tf} bar's close, enter next M1 open, stop at the protected "
            f"swing, 2R, {HOLD[tf]} hold")


def cisd_book(m1, tf):
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "entry_ref"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
        "entry_ref": ev["confirm_close"].to_numpy(float),
    })


def nfp_dates(y0=2015, y1=2026):
    """NFP (BLS Employment Situation) dates by the reference-week rule: the third Friday
    after the Saturday ending the week containing the 12th of the prior month; Jul 3/4 ->
    the day before; Jan 1 -> a week later.  2025 shutdown releases special-cased from the
    public record (Sep report 2025-11-20; Oct none; Nov report 2025-12-16)."""
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            ry, rm = (y, m - 1) if m > 1 else (y - 1, 12)
            d12 = pd.Timestamp(ry, rm, 12)
            sat = d12 + pd.Timedelta(days=(5 - d12.dayofweek) % 7)
            fri = sat + pd.Timedelta(days=20)
            if fri.month == 7 and fri.day in (3, 4):
                fri = fri - pd.Timedelta(days=1)
            if fri.month == 1 and fri.day == 1:
                fri = fri + pd.Timedelta(days=7)
            out.append(fri.normalize())
    s = set(out)
    for bad in ("2025-10-03", "2025-11-07", "2025-12-05"):
        s.discard(pd.Timestamp(bad))
    s.update({pd.Timestamp("2025-11-20"), pd.Timestamp("2025-12-16")})
    return sorted(s)


def show(res):
    keys = ("n", "avg_R", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
            "verdict", "verdict_detail", "ties", "ctrl_overlap", "exposure_bars", "control")
    for k in keys:
        if res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
