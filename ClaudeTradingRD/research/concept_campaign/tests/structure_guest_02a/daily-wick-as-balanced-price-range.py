"""daily-wick-as-balanced-price-range (guest: Jokerszn, JABOO4LYNjQ) -> trade_test.

Claim: a large daily wick is a balanced price range; mark it base->extreme, expect the
reaction from its near half (lower half of an upper wick), refine with an H1 FVG inside
that half, stop above the wick's EQ, target prior lows. claim '+': the trade beats a
matched random entry.

Reading (declared before the first run):
  * Daily candles on the 18:00 NY roll; the wick day must be a full session (>= 600 M1).
  * Large upper (bearish) wick := upper wick > body AND upper wick > lower wick
    (threshold_fits: wick vs body crossover 1.0 = reversal candle). Base = the body top
    max(open, close) (ambiguity 'body edge or open/close' -> body edge). EQ = (base+high)/2.
    Bullish mirror on the lower wick.
  * Next trading day only: the first H1 bearish three-bar FVG (all three bars inside that
    day) whose gap overlaps the wick's lower half [base, EQ], with no H1 close above EQ
    (the stated invalidation) from the wick day's close through the FVG bar.
  * Short at the next M1 open after the FVG's third H1 bar closes; stop = the wick EQ
    (stated); target = the wick day's low ('daily lows'); hold 10 H1 bars = 10 h.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402
from _common import from_ns  # noqa: E402

CID = "daily-wick-as-balanced-price-range"
MIN_M1 = 600
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "wick_day",
        "eq_px", "base_px"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    hb = cl.build_bars(m1, "1h")
    if len(d) < 2 or len(hb) < 3:
        return pd.DataFrame(columns=COLS)
    f = fair_value_gaps(hb[["open", "high", "low", "close"]])
    hst = hb.index.values.astype("datetime64[ns]").astype(np.int64)
    hct = hb["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    hc = hb["close"].to_numpy(float)
    gl, gh = f["gap_low"].to_numpy(float), f["gap_high"].to_numpy(float)
    fb, fs = f["bullish_fvg"].to_numpy(bool), f["bearish_fvg"].to_numpy(bool)
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    dct = d["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    nm = d["n_m1"].to_numpy()
    out = []
    for i in range(len(d) - 1):
        if nm[i] < MIN_M1:
            continue
        body = abs(c[i] - o[i])
        top, bot = max(o[i], c[i]), min(o[i], c[i])
        uw, lw = h[i] - top, bot - l[i]
        if uw > body and uw > lw:
            sgn, base, eq, tgt = -1, top, (top + h[i]) / 2.0, l[i]
        elif lw > body and lw > uw:
            sgn, base, eq, tgt = 1, bot, (bot + l[i]) / 2.0, h[i]
        else:
            continue
        a = np.searchsorted(hst, dct[i], "left")          # first H1 bar of the next day
        e = np.searchsorted(hct, dct[i + 1], "right")      # H1 bars closing by next day's close
        for k in range(a, e):
            # invalidation: an H1 close beyond EQ (above for bearish)
            if (sgn == -1 and hc[k] > eq) or (sgn == 1 and hc[k] < eq):
                break
            if k < a + 2:
                continue
            if sgn == -1 and fs[k] and gl[k] < eq and gh[k] > base:
                out.append((int(hct[k]), -1, eq, tgt, int(dct[i]), eq, base))
                break
            if sgn == 1 and fb[k] and gh[k] > eq and gl[k] < base:
                out.append((int(hct[k]), 1, eq, tgt, int(dct[i]), eq, base))
                break
    if not out:
        return pd.DataFrame(columns=COLS)
    o_ = pd.DataFrame(out, columns=["t", "direction", "stop_px", "target_px", "wd", "eq", "base"])
    dec = from_ns(o_["t"].to_numpy())
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o_["direction"].astype(int).to_numpy(),
                       "stop_px": o_["stop_px"].to_numpy(float),
                       "target_px": o_["target_px"].to_numpy(float),
                       "wick_day": from_ns(o_["wd"].to_numpy()),
                       "eq_px": o_["eq"].to_numpy(float), "base_px": o_["base"].to_numpy(float)})
    return ev.sort_values("decision_time").reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "drops", "halves"):
        print(k, res.get(k))
    op = {"rules": [
        "daily candles (18:00 NY roll), wick day >= 600 M1 bars",
        "large upper wick: upper wick > body and > lower wick; band = body top -> high; "
        "EQ = midpoint (bullish mirror on the lower wick)",
        "next trading day: first H1 bearish FVG (3 bars inside the day) overlapping [base, EQ], "
        "with no H1 close above EQ first",
        "short at next M1 open after the FVG bar close; stop = wick EQ; target = the wick "
        "day's low; hold 10h"],
        "params": {"wick_rule": "wick > body and wick > other wick", "base": "body edge",
                   "search": "next trading day", "target": "wick day's opposite extreme",
                   "max_hold": MAX_HOLD, "min_m1": MIN_M1}}
    src = {"wick_rule": "threshold_fits: large wick / reversal candle = wick larger than body "
                        "(crossover 1.0, grade A; TND1aTpnq5c 'the wick is larger than the body')",
           "base": "declared-before-run: ambiguity 'body edge or open/close' -> body edge",
           "search": "declared-before-run: refinement window not stated; the next session",
           "target": "corpus: JABOO4LYNjQ targets 'prior session lows, daily lows' -> the wick "
                     "day's low (declared-before-run)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) on H1",
           "min_m1": "declared-before-run: stub-session filter as in the concept_lab rate example"}
    notes = ("Stop at the wick EQ is the concept's own stop; entry is the H1 FVG refinement "
             "inside the near half. Target distance is often large relative to the stop, so "
             "many trades time out; the matched control shares stop and target distance.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
