"""breaker-continuation -- breaker block used as a continuation entry.

Trade test (a full entry / stop / target is stated). Execution TF 15m, HTF 1D.
Bullish (mirror for bearish), from the YAML detection rules:
  * trend established on the HTF: the previous completed trading day closed up
    (close > open) -- the "daily/HTF closure" precondition;
  * swing low L1 then swing high H (15m 2/2 fractals, L1 within 20 bars before H);
  * after H, price runs L1 out (a low below L1) BEFORE any close above H
    (a close above H first is a plain break, not a breaker) -> low, high, lower low;
  * the breaker forms when a bar then CLOSES above H (the higher high), within 20
    bars of H;
  * breaker zone = the up-close candles from L1 to H, marked on the bodies.
Contested execution ("close through the breaker, or the retest of the zone";
"stop on the low or the other side of the breaker") -> two readings:
  a  enter at the close that prints the higher high; stop on the swept low (L2).
  b  enter on the retest: the first bar within 10 bars after the break that trades
     into the zone top and closes above the zone bottom; stop = zone bottom
     (far side of the breaker). A close below the zone bottom first voids it.
Target 2R (first listed target), 150 min hold. claim '+' vs matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

CID = "breaker-continuation"
TF = "15min"
L1_LOOK = 20
MAX_BREAK = 20
RETEST = 10
PARAMS = {"tf": TF, "htf_gate": "prior trading day close vs open", "swing": "2/2",
          "l1_lookback_bars": L1_LOOK, "max_bars_H_to_break": MAX_BREAK,
          "retest_window_bars": RETEST, "zone": "bodies of up-close (down-close) candles L1..H",
          "rr": 2.0, "max_hold": "150min"}
SRC = {
    "tf": "phase3: 15m entry TF (YAML ltf 15m/5m/1m)",
    "htf_gate": "corpus: xP-o11jRCyg / YAML 'Establish the trend direction first via the "
                "higher timeframe closure' (1D is the YAML htf); declared-before-run: "
                "closure = prior day close beyond its open",
    "swing": "phase3: locked 2/2 fractal swings",
    "l1_lookback_bars": "declared-before-run: L1 must lie within 20 bars before H",
    "max_bars_H_to_break": "declared-before-run: YAML gives no bar limit (ambiguity); 20 bars",
    "retest_window_bars": "declared-before-run: retest must come within 10 bars of the break",
    "zone": "corpus: 8FtjVWZcZN8 'with these wicks kind of everywhere, I will focus on the bodies'",
    "rr": "corpus: YAML execution targets '2R' (xP-o11jRCyg)",
    "max_hold": "phase3: 10 entry-TF bars (s1.13)",
}


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    o = b["open"].to_numpy(); h = b["high"].to_numpy()
    l = b["low"].to_numpy(); c = b["close"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"])
    sw = swing_points(b[["open", "high", "low", "close"]], 2, 2)
    isH = sw["swing_high"].to_numpy(); isL = sw["swing_low"].to_numpy()
    n = len(b)
    rows = []
    for bull in (True, False):
        # bullish: L1 = swing low, H = swing high; bearish: mirror (negate prices)
        if bull:
            P_hi, P_lo, P_c, P_o, piv, anc = h, l, c, o, isH, isL
        else:
            P_hi, P_lo, P_c, P_o, piv, anc = -l, -h, -c, -o, isL, isH
        anc_idx = np.flatnonzero(anc)
        for hp in np.flatnonzero(piv):
            k0 = np.searchsorted(anc_idx, hp) - 1
            if k0 < 0:
                continue
            lp = anc_idx[k0]
            if hp - lp > L1_LOOK or lp >= hp:
                continue
            H = P_hi[hp]; L1 = P_lo[lp]
            swept = False; L2 = np.inf; brk = -1
            for k in range(hp + 1, min(n, hp + 1 + MAX_BREAK)):
                if not swept and P_c[k] > H:
                    break                       # plain break before the sweep
                if P_lo[k] < L1:
                    swept = True
                L2 = min(L2, P_lo[k])
                if swept and P_c[k] > H:
                    brk = k; break
            if brk < 0:
                continue
            up = [j for j in range(lp, hp + 1) if P_c[j] > P_o[j]]
            zhi = max(P_c[j] for j in up) if up else np.nan
            zlo = min(P_o[j] for j in up) if up else np.nan
            sgn = 1 if bull else -1
            rows.append({"reading": "a", "bar": brk, "direction": sgn,
                         "stop_px": sgn * L2, "setup": ct[hp]})
            if up:
                for m in range(brk + 1, min(n, brk + 1 + RETEST)):
                    if P_lo[m] <= zhi:
                        if P_c[m] > zlo:
                            rows.append({"reading": "b", "bar": m, "direction": sgn,
                                         "stop_px": sgn * zlo, "setup": ct[hp]})
                        break
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "reading",
            "setup_time", "prior_day_ok"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows)
    dt = ct[r["bar"].to_numpy()]
    out = pd.DataFrame({"decision_time": dt, "available_at": dt,
                        "direction": r["direction"].to_numpy(),
                        "stop_px": r["stop_px"].to_numpy(float), "rr": 2.0,
                        "reading": r["reading"].to_numpy(),
                        "setup_time": pd.DatetimeIndex(r["setup"])})
    pdc = cl.prior_hilo(out["decision_time"], "1D", m1=m1)
    dcl = np.sign(pdc["close"].to_numpy(float) - pdc["open"].to_numpy(float))
    out["prior_day_ok"] = np.nan_to_num(dcl, nan=0) == out["direction"].to_numpy()
    out = out[out["prior_day_ok"]]
    out = (out.sort_values(["reading", "decision_time", "direction"])
              .drop_duplicates(["reading", "decision_time", "direction"])
              .reset_index(drop=True))
    return out[cols]


def book(m1, reading):
    ev = detect(m1)
    return ev[ev["reading"] == reading].reset_index(drop=True)


if __name__ == "__main__":
    full = cl.cache_frame(f"{CID}_15m_v1", lambda: detect(cl.load_m1()))
    for reading, desc in (
            ("a", "entry at the close of the bar that closes beyond H (breaker formed); "
                  "stop on the swept extreme L2"),
            ("b", "entry at the close of the first bar (<=10 bars after the break) that "
                  "trades back into the body zone and closes beyond its far side; stop = "
                  "far side of the zone")):
        ev = full[full["reading"] == reading].reset_index(drop=True)
        det = (lambda m, r=reading: book(m, r))
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold="150min", cluster="setup_time")
        print(reading, {k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p",
                                                  "verdict", "verdict_detail", "exposure_bars",
                                                  "ties")})
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": [
                                "15m 2/2 swings: L1 (swing low) within 20 bars before H (swing "
                                "high); after H a low below L1 BEFORE any close above H; then a "
                                "close above H within 20 bars = breaker (mirror bearish)",
                                "HTF gate: previous trading day closed in the trade direction",
                                desc, "target 2R, max hold 150 min, next-M1-open entry"],
                                "params": PARAMS},
                            params_source=SRC, script=__file__, probe=probe,
                            notes="SMT substitute for the sweep not modelled (needs a "
                                  "correlated asset rule the corpus leaves open). Cluster = "
                                  "the H swing the breaker is built on.")
        print("wrote", p)
