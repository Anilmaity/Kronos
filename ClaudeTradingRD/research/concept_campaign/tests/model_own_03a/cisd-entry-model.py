"""cisd-entry-model — Manipulation -> CISD -> Projection Entry Model, TTrades own voice.

Operationalisation (`specified`, one reading), on 15m bars:
  1. Manipulation: the CISD's swing extreme trades beyond the range of the previous
     RANGE_N bars (bearish: above their highest high) — a sweep out of the range;
  2. CISD: close through the opening price of the first candle of the opposing series that
     made the extreme (detectors.cisd, series_open, 2/2 swing, max_wait 3 — phase-3 lock),
     and that close is back inside the range (bearish: below the swept range high);
  3. Projection: fib 1 = the extreme, 0 = the CISD level (series open); target = the -2
     standard deviation (bearish: level - 2 x (extreme - level));
  4. Entry AT THE CISD LEVEL (the order block): after the CISD bar closes, the first M1 bar
     that trades back to the level within ENTRY_WINDOW decides; entry = next M1 open.
     Invalid if price first trades through the extreme or reaches the target. Only in the
     premium of the dealing range for shorts / discount for longs (level vs the EQ of
     range-opposite-extreme .. manipulation extreme);
  5. Stop on the manipulation extreme;
  6. The 2R minimum: with entry at the level and the fib anchored level->extreme, the -2 SD
     target is exactly 2R — the corpus's own "use the -2 deviation instead" when a
     structural target gives < 2R. No extra filter.
Design note (before any test ran): a first draft entered at the CISD close and skipped
trades under 2R; that is arithmetically empty (reward/risk = (2L-x)/(L+x) < 2), which
showed the draft had mis-read the entry — the corpus enters AT the level.
Test: trade_test vs matched random entry, claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from detectors.cisd import cisd_events                              # noqa: E402

CID = "cisd-entry-model"
TF = "15min"
RANGE_N = 20
SD = 2.0
ENTRY_WINDOW = "150min"
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < RANGE_N + 10:
        return pd.DataFrame(columns=COLS)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    rh = b["high"].rolling(RANGE_N, min_periods=RANGE_N).max().shift(1).to_numpy()
    rl = b["low"].rolling(RANGE_N, min_periods=RANGE_N).min().shift(1).to_numpy()
    p = b.index.get_indexer(ev["extreme_time"])
    bull = (ev["direction"] == "bullish").to_numpy()
    ext = ev["extreme_price"].to_numpy(float)
    lvl = ev["level"].to_numpy(float)
    cc = ev["confirm_close"].to_numpy(float)
    rhp, rlp = rh[p], rl[p]
    sweep = np.where(bull, ext < rlp, ext > rhp)
    inside = np.where(bull, cc > rlp, cc < rhp)
    eq = np.where(bull, (rhp + ext) / 2.0, (rlp + ext) / 2.0)
    pd_ok = np.where(bull, lvl < eq, lvl > eq)
    L = np.abs(ext - lvl)
    tgt = np.where(bull, lvl + SD * L, lvl - SD * L)
    keep = sweep & inside & pd_ok & np.isfinite(rhp) & np.isfinite(rlp) & (L > 0)
    ct = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    tn = m1.index.as_unit("ns").asi8
    H, Lo = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    win = pd.Timedelta(ENTRY_WINDOW).value
    rows = []
    for k in np.flatnonzero(keep):
        t0 = ct[k].value
        i0 = np.searchsorted(tn, t0, side="left")
        i1 = np.searchsorted(tn, t0 + win, side="left")
        if i1 <= i0:
            continue
        h, lo = H[i0:i1], Lo[i0:i1]
        if bull[k]:
            touch, inval, done = lo <= lvl[k], lo <= ext[k], h >= tgt[k]
        else:
            touch, inval, done = h >= lvl[k], h >= ext[k], lo <= tgt[k]
        tj = np.flatnonzero(touch)
        if not len(tj):
            continue
        j = tj[0]
        if inval[:j + 1].any() or done[:j + 1].any():
            continue
        dec = pd.Timestamp(tn[i0 + j] + 60_000_000_000, tz="UTC")
        rows.append({"decision_time": dec, "available_at": dec,
                     "direction": 1 if bull[k] else -1,
                     "stop_px": ext[k], "target_px": tgt[k]})
    return pd.DataFrame(rows, columns=COLS)


OP = {"rules": [
    "15m bars; CISD = close through the opening price of the first candle of the opposing "
    "series into a 2/2 swing extreme, within 3 bars (detectors.cisd series_open)",
    "manipulation: that extreme is beyond the prior 20 bars' high (bearish) / low (bullish), "
    "and the CISD close is back inside that range",
    "dealing range = prior-range opposite extreme .. manipulation extreme; shorts only above "
    "its EQ, longs only below",
    "target = -2 SD projection of the leg (fib 1 = extreme, 0 = CISD level) = 2R from the level",
    "entry: first M1 bar within 150 min of the CISD close that trades back to the CISD level "
    "(not after touching the extreme or the target); enter the next M1 open; stop at the "
    "manipulation extreme; exit 150 min after entry"],
    "params": {"tf": TF, "range_n": RANGE_N, "sd_target": -SD, "entry": "retest of CISD level",
               "entry_window": ENTRY_WINDOW,
               "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
               "premium_discount": "both sides", "max_hold": MAX_HOLD}}
SRC = {"tf": "corpus: CHIK5oBRKiw — ltf list 15m/5m/2m/1m; phase3: 15m is the entry TF of "
             "the primary stack",
       "range_n": "declared-before-run: the 'range' swept = previous 20 bars (no lookback is "
                  "stated)",
       "sd_target": "corpus: CHIK5oBRKiw — 'mark -2 to -2.5 and -4 to -4.5 standard "
                    "deviations'; method_spec §5.2 the -2/-2.5 band is the first target; "
                    "anchor on the CISD level per the indicator's body anchoring",
       "entry": "corpus: CHIK5oBRKiw — 'Entry: at the CISD level (order block) or an "
                "overlapping fair value gap'",
       "entry_window": "declared-before-run: no validity window is stated; 10 entry-TF bars "
                       "(the phase-3 hold length)",
       "level_rule": "method_spec: §4.2 first-candle-open default",
       "swing": "phase3: locked CISD config (2/2 swing)",
       "max_wait": "phase3: locked CISD config (max_wait 3) / method_spec §4.2 '1, 2, maybe 3'",
       "premium_discount": "declared-before-run: stated for shorts (premium); mirrored for "
                           "longs (discount); tested on the entry level",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "dropped"):
        print(k, res.get(k))
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe)
    print(p)
