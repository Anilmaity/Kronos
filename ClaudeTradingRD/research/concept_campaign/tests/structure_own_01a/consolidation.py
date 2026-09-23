"""consolidation (TTrades own voice, underspecified) -> gate_test, claim '-'.

The concept's only test is negative: a stretch with no displacement around the swings is
consolidation, "we don't know where price is wanting to go", so you let it play out rather
than trade (sgAnVR6RSDg). Displacement's structural component is a CLOSE beyond the
reference swing (threshold_fits §2(a), grade A, no knob).

Declared before the first run:
  * Baseline book: the locked phase-3 1h CISD (swing 2/2, series_open, max_wait 3, stop at
    the protected swing, 2R, max hold 10h) -- the corpus's own entry trigger.
  * 1h swings = fractal 2/2, known at the close of the 2nd right-hand bar.
  * displacement close at 1h bar k = close[k] above the most recent swing high known by
    bar k, or below the most recent swing low known by bar k.
  * gate "consolidating" = NO displacement close in the 24 1h bars ending at the CISD's
    confirming bar (one trading day). Known at the confirming bar's close = decision.
  * claim '-': CISD trades taken while consolidating are worse than the rest.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, cisd_1h, show
from detectors.primitives import swing_points

CID = "consolidation"
WIN = 24
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "consolidating"]


def displacement_close(b: pd.DataFrame) -> np.ndarray:
    """Bool per bar: close beyond the latest swing high/low known at that bar's close."""
    sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
    n = len(b)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    hi_pos = np.flatnonzero(sw["swing_high"].to_numpy())
    lo_pos = np.flatnonzero(sw["swing_low"].to_numpy())
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    for p in hi_pos:
        if p + 2 < n:
            sh[p + 2] = H[p]          # known at the close of bar p+2
    for p in lo_pos:
        if p + 2 < n:
            sl[p + 2] = L[p]
    sh = pd.Series(sh).ffill().to_numpy()
    sl = pd.Series(sl).ffill().to_numpy()
    C = b["close"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        return (C > sh) | (C < sl)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b, ev = cisd_1h(m1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    disp = displacement_close(b).astype(int)
    cnt = pd.Series(disp).rolling(WIN, min_periods=WIN).sum().to_numpy()
    j = ev["conf_pos"].to_numpy()
    c = cnt[j]
    keep = np.isfinite(c)
    ev = ev[keep].reset_index(drop=True)
    c = c[keep]
    out = pd.DataFrame({
        "decision_time": pd.DatetimeIndex(ev["decision_time"]),
        "available_at": pd.DatetimeIndex(ev["decision_time"]),
        "direction": np.where(ev["direction"].to_numpy() == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
        "consolidating": (c == 0),
    })
    return out[COLS]


def main():
    ev = cl.cache_frame(f"consolidation_cisd1h_nodisp{WIN}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "gated", int(ev["consolidating"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "consolidating", mask_available_at="decision_time", claim="-",
                       max_hold="10h")
    show(res)
    op = {"rules": [
        "baseline: locked phase-3 1h CISD (swing 2/2, close through the series_open level within 3 bars; "
        "decide at the confirming 1h close; stop = protected swing; 2R; max hold 10h)",
        "displacement close = a 1h close beyond the latest confirmed 2/2 swing high or swing low",
        "gate 'consolidating' = no displacement close in the 24 1h bars ending at the confirming bar",
        "claim '-': CISD trades taken while consolidating are worse than those taken after displacement"],
        "params": {"tf": "1h", "cisd": "series_open/max_wait 3/swing 2-2", "rr": 2.0,
                   "max_hold": "10h", "window_bars": WIN, "displacement": "close beyond swing"}}
    src = {"tf": "phase3: meta/conjunction_preregistration.md §1.8 locked 1h CISD",
           "cisd": "phase3: §1.8 locked config",
           "rr": "phase3: §1.8 2R",
           "max_hold": "phase3: §1.13 10 entry-TF bars",
           "window_bars": "declared-before-run: one trading day of 1h bars as the stretch being classified",
           "displacement": "threshold_fits: §2(a) displacement = a CLOSE beyond the reference level (grade A, no knob)"}
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Consolidation operationalised as the absence of displacement closes "
                                "(its only corpus test); gate on the phase-3 1h CISD book."))


if __name__ == "__main__":
    main()
