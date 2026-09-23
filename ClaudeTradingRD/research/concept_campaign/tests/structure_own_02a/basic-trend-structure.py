"""basic-trend-structure (TTrades own voice, specified) — batch structure_own_02a.

"we're going to have to make higher highs and higher lows" (sgAnVR6RSDg). The read is a
running expectation: "after a higher low he wants a higher high" (mirrored), and the trend
is intact while the opposing swing has not been broken.

The predictive content is that expectation: once a higher low confirms inside an
HH/HL uptrend, price should make the higher high (exceed the prior swing high) before it
breaks that higher low. As a trade (geometry matched by the random-entry control):
  1h bars, 2/2 fractal swings (confirmed 2 bars after the swing bar).
  At the bar that confirms swing low L:  L > previous swing low L' (higher low),
  the most recent swing high H lies between L' and L in time and H > the swing high H'
  before it (higher high), no bar since L' traded below L' (trend intact), and no bar
  since H has traded above H (the next higher high is still pending).
  -> long at the next M1 open, stop = L, target = H (a trade above H is the HH), exit
     after 24 trading hours. Downtrend mirror (LH/LL -> short, stop = LH, target = LL).
claim '+': the with-trend expectation beats a matched random entry with the same stop
and target distances.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, np, pd, summary  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

CID = "basic-trend-structure"
TF, LEFT, RIGHT, HOLD = "1h", 2, 2, "24h"


def detect(m1):
    b = cl.build_bars(m1, TF)
    sw = swing_points(b[["high", "low"]], LEFT, RIGHT)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(b)
    is_h, is_l = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rows = []
    for bull in (True, False):
        # work in bull space: lows are x, highs are y (bearish: negate and swap)
        x, y = (l, h) if bull else (-h, -l)
        sx, sy = (is_l, is_h) if bull else (is_h, is_l)
        cc = c if bull else -c
        lows = np.flatnonzero(sx)
        highs = np.flatnonzero(sy)
        for k in range(1, len(lows)):
            p, p1 = lows[k], lows[k - 1]
            i = p + RIGHT                      # confirmation bar
            if i >= n:
                continue
            if not x[p] > x[p1]:
                continue
            hs = highs[(highs < p) & (highs + RIGHT <= i)]
            if len(hs) < 2:
                continue
            ph, ph1 = hs[-1], hs[-2]
            if not (p1 < ph < p):
                continue
            if not y[ph] > y[ph1]:
                continue
            if (x[p1 + 1:i + 1] < x[p1]).any():
                continue
            if (y[ph + 1:i + 1] >= y[ph]).any() or cc[i] >= y[ph]:
                continue
            rows.append((i, 1 if bull else -1, x[p] if bull else -x[p],
                         y[ph] if bull else -y[ph]))
    ev = pd.DataFrame(rows, columns=["i", "dir", "stop", "target"])
    ev = ev.drop_duplicates(["i", "dir"]).sort_values(["i", "dir"]).reset_index(drop=True)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["i"].to_numpy()])
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": ev["dir"].to_numpy().astype(int),
                         "stop_px": ev["stop"].to_numpy(), "target_px": ev["target"].to_numpy()})


def main():
    ev = cl.cache_frame(f"trendstruct_{TF}_{LEFT}{RIGHT}", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars")
    print(summary(res))
    rules = [f"{TF} bars, fractal {LEFT}/{RIGHT} swings, known {RIGHT} bars after the swing bar",
             "at the confirmation of swing low L: L > previous swing low L'; most recent "
             "confirmed swing high H lies between L' and L and H > the swing high before it; "
             "no trade below L' since L'; no trade at/above H since H",
             "long at the next M1 open, stop = L, target = H (the pending higher high); "
             "downtrend mirror", f"exit after {HOLD} of trading time"]
    params = {"tf": TF, "left": LEFT, "right": RIGHT, "max_hold": HOLD, "hold_basis": "bars"}
    src = {"tf": "corpus yaml timeframes: htf 1D/4H/1H — 1H chosen for sample size",
           "left": "phase3: fractal 2/2 swing knob", "right": "phase3: fractal 2/2 swing knob",
           "max_hold": "declared-before-run: one trading day for a 1h swing leg to resolve",
           "hold_basis": "declared-before-run: trading time, the hold spans the daily halt"}
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Unfiltered 2/2 fractals label more structure than he does (yaml "
                              "ambiguity: minor swings are skipped by eye). Target = touch of "
                              "the prior swing high (the higher high is registered on a trade "
                              "through, not a close).")
    print("  wrote", p)


if __name__ == "__main__":
    main()
