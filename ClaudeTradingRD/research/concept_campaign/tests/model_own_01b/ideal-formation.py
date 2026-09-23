"""ideal-formation (TTrades own voice, contested) — batch model_own_01b.

Claim: a candle 2 closure is IDEAL only when the same bar also closes beyond the
opening price of the series of opposing candles that traded into the point of
interest (creating the protected swing in the same bar); closing over candle 1's
body alone is explicitly not ideal. Ideal formations are the high-probability
swing points.

Baseline book: every HTF C2 closure (method_spec §3.2: bullish low<prev low and
close>prev low; bearish mirrored; two-sided bars dropped). Trade C3 as in the
model: decide at C2's close, enter next M1 open in the reversal direction, stop at
C2's extreme, 2R, hold two HTF candles (C3, C4) in trading time.
Gate = ideal: the series of opposing-close candles that made C2's extreme (the
harness CISD definition, detectors.cisd._run_into_extreme, max 10 candles) exists and
C2's close is beyond the OPEN of the series' first candle (bullish: above). No
series found -> not ideal.
Reading a: 4H (forex grid).   Reading b: 1D (18:00 NY day).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cl, np, pd, summary  # noqa: E402
from detectors.cisd import _run_into_extreme  # noqa: E402

CID = "ideal-formation"
TFS = {"a": ("4h", 480, "480min"), "b": ("1D", 2760, "2760min")}
MIN_NM1_1D = 600


def make_detect(tf: str):
    def detect(m1):
        H = cl.build_bars(m1, tf, grid4h="forex")
        if tf == "1D":
            H = H[H["n_m1"] >= MIN_NM1_1D]
        o, lo, hi, c = (H[k].to_numpy() for k in ("open", "low", "high", "close"))
        plo, phi = np.r_[np.nan, lo[:-1]], np.r_[np.nan, hi[:-1]]
        bull = (lo < plo) & (c > plo)
        bear = (hi > phi) & (c < phi)
        sel = np.flatnonzero(bull ^ bear)
        d = np.where(bull[sel], 1, -1)
        ohlc = H[["open", "high", "low", "close"]]
        ideal = np.zeros(len(sel), bool)
        for k, (i, dd) in enumerate(zip(sel, d)):
            s, e = _run_into_extreme(ohlc, int(i), dd > 0, max_len=10)
            if s < 0:
                continue
            ideal[k] = (c[i] > o[s]) if dd > 0 else (c[i] < o[s])
        ct = pd.DatetimeIndex(H["close_time"].to_numpy()[sel])
        return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d,
                             "stop_px": np.where(d > 0, lo[sel], hi[sel]), "rr": 2.0,
                             "ideal": ideal}).reset_index(drop=True)
    return detect


def main():
    for reading, (tf, hold_bars, hold) in TFS.items():
        detect = make_detect(tf)
        ev = cl.cache_frame(f"ideal_{tf}_v1", lambda: detect(cl.load_m1()))
        probe = cl.probe_lookahead(detect, ev, lookback="40D" if tf == "1D" else "20D")
        res = cl.gate_test(ev, "ideal", mask_available_at="decision_time", max_hold=hold,
                           hold_basis="bars")
        print(f"reading {reading} ({tf}) n={len(ev)} ideal={ev['ideal'].mean():.3f}\n"
              + summary(res))
        op = {"rules": [
            f"{tf} C2 closure: bullish low<prev low and close>prev low; bearish mirrored; "
            "two-sided bars dropped",
            "trade C3: decide at C2 close, enter next M1 open in the reversal direction, "
            "stop at C2's extreme, 2R, hold two HTF candles (trading time)",
            "gate ideal: opposing-close series into C2's extreme exists and C2 closes beyond "
            "the open of its first candle"],
            "params": {"tf": tf, "grid4h": "forex", "rr": 2.0, "max_hold": hold,
                       "hold_basis": "bars", "max_series": 10,
                       **({"min_nm1": MIN_NM1_1D} if tf == "1D" else {})}}
        src = {"tf": "corpus: ideal-formation.yaml timeframes htf ['1D','4H']",
               "grid4h": "session_window_fit: forex grid for gold (weak; recorded)",
               "rr": "method_spec: §5.3 2R default",
               "max_hold": "declared-before-run: C3 and C4, the two continuation candles (method_spec §3.1)",
               "hold_basis": "declared-before-run: trading time (weekends/halts)",
               "max_series": "method_spec: §4.2 series procedure (detectors.cisd default max_series 10)"}
        if tf == "1D":
            src["min_nm1"] = "declared-before-run: drop stub sessions (README trap 6)"
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="'close beyond the opening price of that series' is the "
                                  "yaml's second detection-rule wording (series_open); body "
                                  "close assumed (all worked examples are body closes).")
        print("  wrote", p)


if __name__ == "__main__":
    main()
