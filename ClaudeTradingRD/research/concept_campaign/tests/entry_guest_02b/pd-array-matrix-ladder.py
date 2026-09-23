"""pd-array-matrix-ladder (guest: Ben) -> trade_test (target-rule variant on a fixed entry book).

Claim: price works from one extreme to the other THROUGH the ladder of PD arrays, so the
next PD array between price and the draw is the right take-profit (he uses no projection
multiple). The concept sets no entry and no stop ("Not set by this rule"), so it is
tested as a TARGET rule on a stated baseline entry book: if unfilled PD arrays act as the
ladder's steps (magnets), a target at the first step is reached more often than a matched
random entry with the same stop and target distances.

Reading (declared before the run):
  * Baseline entries: the phase-3 locked 1h CISD (series_open, 2/2 swings, max_wait 3),
    decided at the confirming bar's close, stop at the protected swing. (Rung 0 is null
    vs control at 1h, +0.009 R, so the baseline entry carries no edge of its own.)
  * Ladder step 1 = the nearest UNMITIGATED fair value gap on the same 1h chart in the
    trade direction: for a long, bearish 1h FVGs formed in the last 500 bars that no later
    bar has traded into (every high since < gap low); target = the lowest such gap low
    (the near edge — the first array price must pass through). Short mirrored.
  * FVGs are the first rung of his own worked example (FVG -> OB -> liquidity pool);
    order blocks / breakers / pools are not enumerated. Events with no unmitigated FVG
    in range have no ladder and are dropped.
  * max_hold 10h (phase-3 1h convention).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import fair_value_gaps

TF = "1h"
LOOKBACK_BARS = 500
MAX_HOLD = "10h"
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b = cl.build_bars(m1, TF)
    ohlc = b[["open", "high", "low", "close"]]
    ev = cisd_events(ohlc, **CISD_KW)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    f = fair_value_gaps(ohlc)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    bear_i = np.flatnonzero(f["bearish_fvg"].to_numpy())
    bull_i = np.flatnonzero(f["bullish_fvg"].to_numpy())
    gl, gh = f["gap_low"].to_numpy(), f["gap_high"].to_numpy()
    pos = b.index.get_indexer(ev["confirm_time"])
    out = []
    for k, j in enumerate(pos):
        bull = ev["direction"].iloc[k] == "bullish"
        cand = bear_i if bull else bull_i
        lo_i = np.searchsorted(cand, j - LOOKBACK_BARS, side="left")
        hi_i = np.searchsorted(cand, j, side="right")
        c = cand[lo_i:hi_i]
        if not len(c):
            continue
        start = c[0]
        if bull:
            # suffix max of highs over (i, j]: sm[x] = max(H[start+x+1 .. j])
            seg = H[start + 1:j + 1]
            sm = np.r_[np.maximum.accumulate(seg[::-1])[::-1], -np.inf]
            since = sm[c - start]
            okm = since < gl[c]
            if not okm.any():
                continue
            tgt = gl[c][okm].min()
        else:
            seg = L[start + 1:j + 1]
            sm = np.r_[np.minimum.accumulate(seg[::-1])[::-1], np.inf]
            since = sm[c - start]
            okm = since > gh[c]
            if not okm.any():
                continue
            tgt = gh[c][okm].max()
        out.append((b["close_time"].iloc[j], 1 if bull else -1,
                    float(ev["protected_swing"].iloc[k]), float(tgt)))
    if not out:
        return pd.DataFrame(columns=cols)
    o = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "target_px"])
    o["available_at"] = o["decision_time"]
    return o.sort_values(["decision_time", "direction"]).reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("pdladder_1h_cisd_mw3_fvg500", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="40D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline entry: phase-3 locked 1h CISD, decide at the confirming close, stop at the protected swing",
        "ladder step 1: nearest unmitigated opposite-polarity 1h FVG in the trade direction (formed within 500 bars, never traded into since)",
        "target = that FVG's near edge; events without one dropped; max_hold 10h"],
        "params": {"tf": TF, "cisd": "series_open 2/2 max_wait 3 min_series 1",
                   "lookback_bars": LOOKBACK_BARS, "max_hold": MAX_HOLD}}
    src = {"tf": "declared-before-run: 1h, top of the concept's ltf list",
           "cisd": "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)",
           "lookback_bars": "declared-before-run: FVGs formed within the last 500 1h bars (~1 month)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result("pd-array-matrix-ladder", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Target-rule test on a null baseline entry (1h CISD rung 0). Only FVG rungs; "
                              "OB/breaker/liquidity-pool rungs and per-step partials not built.")
    print(p)
