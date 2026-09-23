"""three-drive-reversal-pattern (guest: Day Trading Rauf) -> two readings.

Claim: price that takes liquidity three times above the same high (below the same low),
then prints a candle that wicks and returns back into the range, is "usually a reversal"
toward the opposite side's stops.

Detection (declared before the run), 1h UTC-aligned bars:
  * Level = a 2/2 fractal 1h swing high (low), tracked from the bar after its confirming bar
    for at most 120 bars.
  * A drive = a 1h candle whose high trades above the level and closes back at/below it,
    where the previous candle did not trade above the level (a distinct excursion).
  * The level dies on any 1h close above it (acceptance), on any high more than 0.5 x
    ATR(20) above it (expanded away, not "the same area"), or after the third drive.
  * Event at each drive candle's close: short (long for lows) at the next M1 open; stop =
    the highest high of the drives so far (lowest low); target 2R; max_hold 10h.
Reading a (trade_test, claim '+'): third-drive entries vs matched random control.
Reading b (gate_test, claim '+'): the concept's measurable "reversal rate after the 3rd run
vs the 1st and 2nd" - all drive entries, gate `third` = drive number 3; clustered by level.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

TF = "1h"
TOL_ATR = 0.5
ATR_N = 20
AGE = 120
RR = 2.0
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "drive", "third", "level_id"]


def detect_all(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    if len(b) < ATR_N + 6:
        return pd.DataFrame(columns=COLS)
    ohlc = b[["open", "high", "low", "close"]]
    sp = swing_points(ohlc, 2, 2)
    h, l, c = (b[k].to_numpy() for k in ("high", "low", "close"))
    pc = b["close"].shift(1)
    tr = np.maximum(b["high"] - b["low"],
                    np.maximum((b["high"] - pc).abs(), (b["low"] - pc).abs()))
    atr = tr.rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    ct = pd.DatetimeIndex(b["close_time"])
    n = len(b)
    rows = []
    for side, flags in ((-1, sp["swing_high"].to_numpy()), (1, sp["swing_low"].to_numpy())):
        for s in np.flatnonzero(flags):
            if s + 3 >= n or not np.isfinite(atr[s]):
                continue
            lvl = h[s] if side == -1 else l[s]
            tol = TOL_ATR * atr[s]
            drives, ext = 0, lvl
            for j in range(s + 3, min(n, s + 3 + AGE)):
                if side == -1:
                    if h[j] > lvl + tol or c[j] > lvl:
                        break
                    above, prev_above = h[j] > lvl, h[j - 1] > lvl
                    if above and not prev_above:
                        drives += 1
                        ext = max(ext, h[j])
                    elif above:
                        ext = max(ext, h[j])
                        continue
                    else:
                        continue
                else:
                    if l[j] < lvl - tol or c[j] < lvl:
                        break
                    below, prev_below = l[j] < lvl, l[j - 1] < lvl
                    if below and not prev_below:
                        drives += 1
                        ext = min(ext, l[j])
                    elif below:
                        ext = min(ext, l[j])
                        continue
                    else:
                        continue
                rows.append((ct[j], ct[j], side, ext, RR, drives, drives == 3,
                             f"{side}_{int(ct[s].value)}"))
                if drives == 3:
                    break
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=COLS)
    return ev.sort_values(["decision_time", "direction", "level_id"]).reset_index(drop=True)


def detect_third(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_all(m1)
    return ev[ev["third"].astype(bool)].reset_index(drop=True)


if __name__ == "__main__":
    reading = sys.argv[1] if len(sys.argv) > 1 else "a"
    fn = detect_third if reading == "a" else detect_all
    ev = cl.cache_frame(f"threedrive_{reading}_{TF}_tol{TOL_ATR}_age{AGE}", lambda: fn(cl.load_m1()))
    print(len(ev), ev.drive.value_counts().to_dict())
    probe = cl.probe_lookahead(fn, ev, lookback="15D")
    print("probe", probe.get("passed"))
    if reading == "a":
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
    else:
        res = cl.gate_test(ev, "third", mask_available_at="decision_time", max_hold=MAX_HOLD,
                           cluster="level_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "level = 1h 2/2 swing high (low), tracked <=120 bars after confirmation",
        "drive = candle trading beyond the level and closing back, previous candle not beyond",
        "level dies on a close beyond it, a high > level + 0.5 ATR20, or after drive 3",
        "entry at next M1 open after the drive candle closes, reversal direction; stop = extreme of the drives; 2R; 10h",
        "reading a: 3rd drives vs matched control" if reading == "a" else
        "reading b: all drives, gate = 3rd drive vs 1st/2nd, clustered by level"],
        "params": {"tf": TF, "tol_atr": TOL_ATR, "atr_n": ATR_N, "age_bars": AGE, "rr": RR,
                   "max_hold": MAX_HOLD, "swing": "2/2"}}
    src = {"tf": "corpus: qFtfD09Vv3E live 1h walk-through (concept ltf 1H)",
           "tol_atr": "declared-before-run: 'the same area' has no tolerance; within 0.5 ATR(20)",
           "atr_n": "declared-before-run: ATR(20), threshold_fits trailing-window convention",
           "age_bars": "declared-before-run: level tracked for 120 1h bars (5 days)",
           "rr": "declared-before-run: target 'the opposite stops' unquantified; 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "swing": "phase3: 2/2 fractal swing (locked config)"}
    p = cl.write_result("three-drive-reversal-pattern", reading, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("third drive as a reversal trade" if reading == "a" else
                               "third drive vs first/second drives on the same levels"))
    print(p)
