"""silver-bullet-breaker-requirement (guest: DayTradingRauf; status contested) -> 2 gate_tests.

Baseline book (both readings; declared before the run), 1h bars (the concept's ltf):
  * Structural Silver Bullet = price TRADES THROUGH A BREAKER. Bullish: H = the most recent
    confirmed 2/2 swing high (formed within the last 48 bars); after it price made a lower
    low L2 than L1, the last swing low before H (the sweep / smart money reversal low);
    bar k is the first 1h close above H's high. Bearish mirrored.
  * Dealing range: from the reversal extreme L2 to the 'original consolidation' = the
    highest high of the 120 bars (5 trading days) ending at the L2 bar (mirrored).
  * Trade: enter with the model at the breaker close (next M1 open), stop beyond L2,
    target = the original consolidation (the stated target), max_hold 48h.
Reading a (the guest's): gate `below50` = the Silver Bullet (the close through the
  breaker) sits below 50% of the dealing range (above 50% for the sell model) -> 'the next
  leg is high probability and price should move fast to the draw'. claim '+'.
Reading b (the conflicting time-window definition, 10:00-11:00 NY): gate `in_sb_window` =
  the breaker bar is the 10:00-11:00 NY hour. claim '+'.
The 0.75 re-accumulation / mitigation-block entry has no stop or block rule and is not built.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

TF = "1h"
MAX_AGE = 48
RANGE_N = 120
MAX_HOLD = "48h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "below50", "in_sb_window"]
    b = cl.build_bars(m1, TF)
    if len(b) < RANGE_N + 10:
        return pd.DataFrame(columns=cols)
    sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
    H, L, C = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    starts = b.index.values
    conf = sw["confirmed_at"].values
    sh = np.flatnonzero(sw["swing_high"].to_numpy())
    sl = np.flatnonzero(sw["swing_low"].to_numpy())
    sh_conf, sl_conf = conf[sh], conf[sl]
    ny_hour = cl.to_ny(b.index).hour
    out = []
    n = len(b)
    for k in range(1, n):
        for d in (1, -1):
            piv, pconf = (sh, sh_conf) if d == 1 else (sl, sl_conf)
            opp = sl if d == 1 else sh
            # most recent pivot confirmed by the start of bar k
            m = np.searchsorted(pconf, starts[k], side="right")   # pconf is increasing with piv
            if m == 0:
                continue
            h = piv[m - 1]
            if k - h > MAX_AGE or h >= k - 1:
                continue
            lvl = H[h] if d == 1 else L[h]
            crossed = (C[k] > lvl and C[k - 1] <= lvl) if d == 1 else (C[k] < lvl and C[k - 1] >= lvl)
            if not crossed:
                continue
            q = np.searchsorted(opp, h, side="left")
            if q == 0:
                continue
            l1 = opp[q - 1]                                         # last opposite swing before H
            seg = slice(h + 1, k + 1)
            if d == 1:
                x = h + 1 + int(np.argmin(L[seg])); ext = L[x]
                if not ext < L[l1]:
                    continue
                if x - RANGE_N + 1 < 0:
                    continue
                top = H[x - RANGE_N + 1:x + 1].max()
                rng = top - ext
                pct = (C[k] - ext) / rng if rng > 0 else np.nan
            else:
                x = h + 1 + int(np.argmax(H[seg])); ext = H[x]
                if not ext > H[l1]:
                    continue
                if x - RANGE_N + 1 < 0:
                    continue
                top = L[x - RANGE_N + 1:x + 1].min()
                rng = ext - top
                pct = (ext - C[k]) / rng if rng > 0 else np.nan
            if not np.isfinite(pct) or pct >= 1.0:                  # target must lie ahead
                continue
            dt = b["close_time"].iloc[k]
            out.append((dt, d, float(ext), float(top), bool(pct < 0.5), bool(ny_hour[k] == 10)))
    if not out:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "target_px",
                                    "below50", "in_sb_window"])
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("sb_breaker_1h_age48_rng120", lambda: detect(cl.load_m1()))
    print(len(ev), ev.below50.mean(), ev.in_sb_window.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base_rules = [
        "1h; structural Silver Bullet = first close through the most recent confirmed 2/2 swing (<=48 bars old) after a lower low than the swing before it (sweep)",
        "dealing range = reversal extreme to the extreme of the 120 bars ending at it ('original consolidation')",
        "enter with the model at the breaker close; stop beyond the reversal extreme; target the original consolidation; max_hold 48h"]
    params = {"tf": TF, "max_age": MAX_AGE, "range_n": RANGE_N, "max_hold": MAX_HOLD, "swing": "2/2"}
    src = {"tf": "corpus: wB-fQiT_UDo timeframes ltf 1H",
           "max_age": "declared-before-run: breaker swing within 48 1h bars",
           "range_n": "declared-before-run: original consolidation = extreme of the prior 5 trading days (120 1h bars)",
           "max_hold": "declared-before-run: 48h for the leg to the draw",
           "swing": "phase3: 2/2 fractal swings (§1.8)"}
    for reading, gate, extra, gsrc in (
            ("a", "below50", "gate: Silver Bullet close below 50% of the dealing range (above for sells)",
             "corpus: wB-fQiT_UDo 'if it forms below 50 percent ... high probability' (reading a)"),
            ("b", "in_sb_window", "gate: breaker bar is the 10:00-11:00 NY hour (time-window Silver Bullet)",
             "method_spec: silver-bullet-window 10:00-11:00 NY (the conflicting definition, reading b)")):
        res = cl.gate_test(ev, gate, mask_available_at="decision_time", max_hold=MAX_HOLD)
        print("== reading", reading)
        for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                  "exposure_bars", "ties"):
            print(k, res.get(k))
        op = {"rules": base_rules + [extra], "params": {**params, "gate": gate}}
        p = cl.write_result("silver-bullet-breaker-requirement", reading, res,
                            operationalization=op, params_source={**src, "gate": gsrc},
                            script=__file__, probe=probe,
                            notes="Contested: a = guest's structural SB graded by dealing-range position; "
                                  "b = time-window SB as a gate on the same structural book.")
        print(p)
