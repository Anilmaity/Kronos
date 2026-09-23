"""htf-wick-formation — a higher-timeframe wick built from two aggressive legs (contested).

Concept: concepts/structure/htf-wick-formation.yaml.

"when we have expansion met with expansion forming a higher time frame wick" (yku6idnLqSo);
"A higher time frame wick is a lower time frame reversal" (rTnu3ZEb2ZE). Execution: bias away
from the wick's extreme, entry inside the T-spot built from 0.5 of the wick, stop beyond the
wick extreme, target the higher-timeframe draw.

Operationalisation (trade_test), daily candle / 5m legs:
  * HTF candle = a trading day (18:00 NY roll, >= 600 M1 bars) whose lower wick
    (min(open,close) - low) is larger than its body AND than its upper wick (reversal
    candle: wick > body, threshold_fits §1 crossover 1.0) — mirror for an upper wick;
  * the wick is two aggressive legs on the lower timeframe: inside that day a bearish 5m
    expansion event (threshold_fits §2) is followed by a bullish 5m expansion event whose
    break comes after it, both decided before the day closes (mirror for bearish);
  * next trading day: enter long at the first M1 touch of the 0.5 level (decision = close of
    the touching M1 bar, entry next M1 open), unless the day's high was already taken first;
    stop = the wick's low; target = the day's high (the previous-candle draw);
    hold 23h of trading time.
The contested clause (ambiguities): which 0.5 —
  reading a: 0.5 of the distance from the low to the CLOSE ("a candle whose distance from its
             low to its closing price is very large", rTnu3ZEb2ZE);
  reading b: 0.5 of the WICK itself, low to the body (half-wick-respect, "Mark 0.5 of the
             resulting wick as a level to be respected").
All parameters declared before the first run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402

CID = "htf-wick-formation"
HOLD = "23h"
LTF = "5min"      # concept ltf list: 5m, 1m (first run used 1h in error; see notes)
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def make_detect(reading: str):
    def detect(m1):
        day = cl.build_bars(m1, "1D")
        b1 = cl.build_bars(m1, LTF)
        ex = C.expansions(b1)
        if len(day) < 3 or ex.empty:
            return C.empty_frame(COLS)
        E_dir = ex["dir"].to_numpy()
        E_brk = ex["break_pos"].to_numpy()
        E_dec = ex["dec_pos"].to_numpy()
        E_dt = pd.DatetimeIndex(ex["dec_time"]).as_unit("ns").asi8
        b1st = b1.index.as_unit("ns").asi8
        dst = day.index.as_unit("ns").asi8
        dct = pd.DatetimeIndex(day["close_time"]).as_unit("ns").asi8
        mt = pd.DatetimeIndex(m1.index).as_unit("ns").asi8
        mh, ml = m1["high"].to_numpy(), m1["low"].to_numpy()
        O, H, L, Cc = (day[x].to_numpy() for x in ("open", "high", "low", "close"))
        nm = day["n_m1"].to_numpy()
        rows = []
        for i in range(len(day) - 1):
            if nm[i] < 600:
                continue
            body = abs(Cc[i] - O[i])
            lw = min(O[i], Cc[i]) - L[i]
            uw = H[i] - max(O[i], Cc[i])
            if lw > body and lw > uw:
                d = 1
            elif uw > body and uw > lw:
                d = -1
            else:
                continue
            # LTF: expansion against, then expansion back, both decided inside the day
            inday = (E_dt > dst[i]) & (E_dt <= dct[i]) & (b1st[E_brk] >= dst[i])
            first = np.flatnonzero(inday & (E_dir == -d))
            if first.size == 0:
                continue
            f0 = first[0]
            second = inday & (E_dir == d) & (E_brk > E_dec[f0])
            if not second.any():
                continue
            if d == 1:
                lvl = (L[i] + Cc[i]) / 2 if reading == "a" else L[i] + 0.5 * lw
                stop, tgt = L[i], H[i]
            else:
                lvl = (H[i] + Cc[i]) / 2 if reading == "a" else H[i] - 0.5 * uw
                stop, tgt = H[i], L[i]
            a0 = np.searchsorted(mt, dct[i], side="left")
            a1 = np.searchsorted(mt, dct[i + 1], side="left")
            if a1 <= a0:
                continue
            seg_l, seg_h = ml[a0:a1], mh[a0:a1]
            touch = np.flatnonzero(seg_l <= lvl) if d == 1 else np.flatnonzero(seg_h >= lvl)
            if touch.size == 0:
                continue
            k = touch[0]
            drawn = (seg_h[:k + 1] >= tgt).any() if d == 1 else (seg_l[:k + 1] <= tgt).any()
            if drawn:
                continue
            tdec = pd.Timestamp(mt[a0 + k] + 60_000_000_000, tz="UTC")
            rows.append({"decision_time": tdec, "available_at": tdec, "direction": d,
                         "stop_px": float(stop), "target_px": float(tgt)})
        if not rows:
            return C.empty_frame(COLS)
        out = pd.DataFrame(rows)
        out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
        out["available_at"] = pd.DatetimeIndex(out["available_at"])
        return out[COLS]
    return detect


EXP_SRC = ("threshold_fits: §2 displacement=aggressive, close-beyond gate (grade A) + N=4 "
           "window r>=1.5, d>=0.65 vs the pre-break 4-bar range (grade B); 2/2 fractal swings")
PARAMS_SOURCE = {
    "htf": "corpus: htf-wick-formation timeframes htf 1D ('on the daily he shows an aggressive "
           "move lower followed by an aggressive move higher')",
    "ltf": "corpus: htf-wick-formation timeframes.ltf [5m, 1m] — 5m legs inside the daily candle",
    "large_wick": "threshold_fits: §1 reversal candle = wick > body (crossover 1.0, grade A); "
                  "and the dominant wick",
    "exp_n": EXP_SRC, "exp_r": EXP_SRC, "exp_d": EXP_SRC,
    "level": "corpus: rTnu3ZEb2ZE 'distance from its low to its closing price' (a) vs "
             "half-wick-respect 0.5 of the wick (b)",
    "entry": "corpus: execution.entry 'Inside the T-spot built from 0.5 of the wick' — first "
             "touch on the next trading day",
    "stop": "corpus: execution.stop 'Beyond the wick extreme'",
    "target": "method_spec: §2.3 previous-candle engine — the prior day's opposite extreme "
              "as the HTF draw",
    "min_day_m1": "declared-before-run: trap 6 stub sessions skipped",
    "max_hold": "declared-before-run: 23h of trading time (one session)",
    "hold_basis": "declared-before-run: trading time (trap 7)",
    "ctrl_tod_tol_min": "declared-before-run: trap 9, not a timing concept",
}


def run(reading: str):
    detect = make_detect(reading)
    ev = cl.cache_frame(f"so01b_htfwick_{reading}_{LTF}", lambda: detect(cl.load_m1()))
    print(reading, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars", ctrl_tod_tol_min=30)
    C.show(res)
    op = {"rules": [
        "trading day (18:00 NY, >= 600 M1 bars) with lower wick > body and > upper wick "
        "(mirror); inside it a bearish 5m expansion then a later-breaking bullish 5m "
        "expansion, both decided before the day closes (mirror)",
        ("level = (low + close)/2" if reading == "a" else
         "level = low + 0.5 x (min(open,close) - low)") + " (mirror for upper wicks)",
        "next trading day: first M1 touch of the level, unless the day's high was taken "
        "first; decide at the touching bar's close, enter next M1 open",
        "stop = the wick extreme; target = the day's opposite extreme; 23h trading time; "
        "control NY clock +/-30 min"],
        "params": {"htf": "1D", "ltf": LTF, "large_wick": "wick>body & wick>other wick",
                   "exp_n": 4, "exp_r": 1.5, "exp_d": 0.65,
                   "level": "low-close mid" if reading == "a" else "wick mid",
                   "entry": "first touch next day", "stop": "wick extreme",
                   "target": "candle opposite extreme", "min_day_m1": 600,
                   "max_hold": HOLD, "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=PARAMS_SOURCE,
                        script=__file__, probe=probe,
                        notes="RE-RUN ONCE after a spec bug: the first run built the lower-"
                              "timeframe legs on 1h, outside the concept's own ltf list "
                              "(5m, 1m); it returned n=29/26 (UNTESTABLE, n<30). Fixed to 5m "
                              "legs and re-run once; nothing else changed.")
    print("wrote", p)


if __name__ == "__main__":
    for r in (sys.argv[1:] or ["a", "b"]):
        run(r)
