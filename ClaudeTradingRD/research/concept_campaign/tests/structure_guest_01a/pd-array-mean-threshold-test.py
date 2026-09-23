"""pd-array-mean-threshold-test (guest: Jokerszn) -> gate_test, two readings for the
concept's own stated ambiguity (the timeframe of the 'close' is not fixed):
  reading a: daily arrays and daily closes (the worked examples)
  reading b: 1H arrays and 1H closes (the rule is also applied to H1 arrays)

Declared before the first run:
  * PD array = three-bar FVG (detectors.primitives.fair_value_gaps), known at its third bar's
    close. Mean threshold MT = gap midpoint.
  * Baseline book: the FIRST bar within 10 bars after formation that trades into the array
    (low <= gap_high for a bullish gap; high >= gap_low for a bearish gap). If that bar closes
    fully beyond the array (below gap_low for bullish) the array is invalidated -> no trade.
    Otherwise trade WITH the array at that bar's close: long for bullish, short for bearish;
    stop = the array's far side (gap_low / gap_high); target 2R; hold 10 bars (clock).
  * Gate (claim '+'): the retest bar did NOT close beyond the MT (bullish: close >= MT).
    Complement: it closed beyond MT but inside the array ("early indication the array will fail").
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import fair_value_gaps

CID = "pd-array-mean-threshold-test"
WAIT = 10
RR = 2.0
CFG = {"a": {"tf": "1D", "hold": "10D", "lookback": "40D"},
       "b": {"tf": "1h", "hold": "10h", "lookback": "5D"}}
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "held_mt"]


def detect(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    b = cl.build_bars(m1, tf)
    if len(b) < 4:
        return pd.DataFrame(columns=COLS)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    H, L, C = b["high"].to_numpy(float), b["low"].to_numpy(float), b["close"].to_numpy(float)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    bull_i = f["bullish_fvg"].to_numpy()
    bear_i = f["bearish_fvg"].to_numpy()
    glo_a, ghi_a = f["gap_low"].to_numpy(float), f["gap_high"].to_numpy(float)
    n = len(b)
    out = []
    for i in np.flatnonzero(bull_i | bear_i):
        bull = bool(bull_i[i])
        glo, ghi = glo_a[i], ghi_a[i]
        mid = 0.5 * (glo + ghi)
        ks = np.arange(i + 1, min(n, i + 1 + WAIT))
        if not len(ks):
            continue
        tch = (L[ks] <= ghi) if bull else (H[ks] >= glo)
        if not tch.any():
            continue
        k = ks[np.argmax(tch)]
        if bull:
            if C[k] < glo:
                continue
            out.append((ct[k], 1, glo, bool(C[k] >= mid)))
        else:
            if C[k] > ghi:
                continue
            out.append((ct[k], -1, ghi, bool(C[k] <= mid)))
    if not out:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "held_mt"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    ev["held_mt"] = ev["held_mt"].astype(bool)
    ev = ev.sort_values(["decision_time", "direction", "stop_px"]).reset_index(drop=True)
    return ev[COLS]


def run(reading):
    c = CFG[reading]
    tf = c["tf"]
    fn = (lambda m: detect(m, "1D")) if tf == "1D" else (lambda m: detect(m, "1h"))
    ev = cl.cache_frame(f"pdamt_{tf}_w{WAIT}", lambda: fn(cl.load_m1()))
    print(reading, len(ev), ev["held_mt"].mean())
    probe = cl.probe_lookahead(fn, ev, lookback=c["lookback"])
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "held_mt", mask_available_at="decision_time", max_hold=c["hold"])
    for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "dropped"):
        print(" ", k, res.get(k))
    op = {"rules": [
        f"{tf} bars (18:00 NY day roll); PD array = 3-bar FVG, MT = gap midpoint",
        "baseline: first bar within 10 bars after formation trading into the array; skip if it closes fully beyond the array",
        "trade with the array at that bar's close; stop = array far side; 2R; hold 10 bars",
        "gate: retest bar did not close beyond MT (bullish close >= MT, bearish close <= MT); complement closed beyond MT inside the array"],
        "params": {"tf": tf, "wait_bars": WAIT, "rr": RR, "max_hold": c["hold"], "stop": "array far side",
                   "array": "3-bar FVG", "grid4h": "n/a"}}
    src = {"tf": "corpus: JABOO4LYNjQ ambiguity - daily in the worked examples (a), also applied to H1 arrays (b)",
           "wait_bars": "phase3: 10 entry-TF bars (§1.13) as the retest window",
           "rr": "phase3: 2R target (rung-0 convention)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "stop": "declared-before-run: the array's far side ('invalidation: a close fully beyond the array')",
           "array": "declared-before-run: FVG is the array the guest's worked example uses",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe)
    print(p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
