"""fractal-model-c4 (TTrades own voice, contested) — batch model_own_01b.

Candle 4 = the second continuation. Preconditions: a completed three-candle swing
(C2's low below C1's and C3's lows — bullish; mirrored bearish), C3 closed beyond
C2's extreme ("Candle 3 closed beyond candle 2's extreme") and closed STRONG
(close_position >= 0.85, threshold_fits 'strong' — it grades the close). The one
numeric filter: C4's low must form in the upper half of C3's range (bullish).

Trade: decide at C3's close, enter at C4's open (next M1 open) in the swing
direction, stop at 0.5 of C3's range (the upper-half rule's invalidation: a C4 wick
below C3's EQ means expansion is not in play), 2R, exit at C4's end (one candle,
trading time).
Reading a: daily candles (the '4th day of a swing', Te9jUijPXZo).
Reading b: 4H candles, forex grid (fractal; yaml timeframes htf 4H).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import cl, np, pd, summary  # noqa: E402

CID = "fractal-model-c4"
STRONG = 0.85
TFS = {"a": ("1D", 1380, "1380min"), "b": ("4h", 240, "240min")}
MIN_NM1_1D = 600


def make_detect(tf: str):
    def detect(m1):
        B = cl.build_bars(m1, tf, grid4h="forex")
        if tf == "1D":
            B = B[B["n_m1"] >= MIN_NM1_1D]
        o, h, l, c = (B[k].to_numpy() for k in ("open", "high", "low", "close"))
        n = len(B)
        rows = []
        rng = h - l
        cp = np.where(rng > 0, (c - l) / np.where(rng > 0, rng, 1), np.nan)
        for i in range(2, n):                      # i = C3, i-1 = C2, i-2 = C1
            bull = (l[i - 1] < l[i - 2]) and (l[i - 1] < l[i]) and (c[i] > h[i - 1]) \
                and cp[i] >= STRONG
            bear = (h[i - 1] > h[i - 2]) and (h[i - 1] > h[i]) and (c[i] < l[i - 1]) \
                and (1 - cp[i]) >= STRONG
            if bull == bear:
                continue
            rows.append((i, 1 if bull else -1))
        if not rows:
            return pd.DataFrame(columns=["decision_time", "available_at", "direction",
                                         "stop_px", "rr"])
        ii = np.array([r[0] for r in rows]); dd = np.array([r[1] for r in rows])
        ct = pd.DatetimeIndex(B["close_time"].to_numpy()[ii])
        eq = (h[ii] + l[ii]) / 2.0
        return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": dd,
                             "stop_px": eq, "rr": 2.0}).reset_index(drop=True)
    return detect


def main():
    for reading, (tf, hold_bars, hold) in TFS.items():
        detect = make_detect(tf)
        ev = cl.cache_frame(f"c4_{tf}_v1", lambda: detect(cl.load_m1()))
        probe = cl.probe_lookahead(detect, ev, lookback="40D" if tf == "1D" else "20D")
        res = cl.trade_test(ev, max_hold=hold, hold_basis="bars")
        print(f"reading {reading} ({tf}) n_events={len(ev)}\n" + summary(res))
        op = {"rules": [
            f"{tf} candles; C1-C2-C3 swing: C2 low < C1 low and < C3 low (bullish; mirrored)",
            "C3 closes beyond C2's high (bullish) and strong: (close-low)/(high-low) >= 0.85",
            "decide at C3 close, enter next M1 open (C4 open) in the swing direction",
            "stop at 0.5 of C3's range (upper-half rule invalidation); 2R; exit at C4's end"],
            "params": {"tf": tf, "grid4h": "forex", "strong_close": STRONG,
                       "half_level": "0.5 of C3 high-low range", "rr": 2.0,
                       "max_hold": hold, "hold_basis": "bars",
                       **({"min_nm1": MIN_NM1_1D} if tf == "1D" else {})}}
        src = {"tf": "corpus: fractal-model-c4.yaml timeframes htf ['1D','4H','1H']; Te9jUijPXZo '4th day of a swing'",
               "grid4h": "session_window_fit: forex grid for gold (weak; recorded)",
               "strong_close": "threshold_fits: §4 strong = close_position >= 0.85 (grade D)",
               "half_level": "method_spec: §3.4 'mark 0.5 of C3's range. Bullish: C4's low must form in the upper half'",
               "rr": "method_spec: §5.3 2R default",
               "max_hold": "declared-before-run: the trade is candle 4 only (one candle)",
               "hold_basis": "declared-before-run: trading time (weekends/halts)"}
        if tf == "1D":
            src["min_nm1"] = "declared-before-run: drop stub sessions (README trap 6)"
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe,
                            notes="'both C2 and C3 already expanded -> avoid C4' not applied "
                                  "(no quantitative definition in the corpus).")
        print("  wrote", p)


if __name__ == "__main__":
    main()
