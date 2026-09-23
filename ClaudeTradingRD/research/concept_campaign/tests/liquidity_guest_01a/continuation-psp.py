"""continuation-psp (GxTradez, guest) — trade_test on 1H gold vs silver.

Claim: once a reversal is confirmed (swing formation + SMT) and the draw on liquidity
is still open, a PSP printing against the draw is a CONTINUATION signal: trade it
WITH the draw. Its form: one asset retraces and closes creating a PSP; the other runs
out that PSP candle's extreme (two-stage PSP).

Operationalisation (declared before the first run):
  * reversal = a 1H gold/silver SMT at bar j (phase-3 knobs) whose gold extreme
    R (min low / max high from the swing bar p through j) is not exceeded on bars
    j+1 and j+2 -> a fractal(2) swing formed, confirmed at the close of j+2;
  * draw = the most recent confirmed gold 1H fractal(2/2) swing on the opposite
    side formed before p (the range extreme the reversal came from); it must still
    be open (beyond the close of j+2);
  * scan up to 24 bars: the setup dies when gold trades to the draw (met) or
    beyond R (reversal failed);
  * PSP at bar m (gold and silver close opposite colours); then on bar m+1 either
    asset trades beyond its own bar-m extreme in the draw direction (two-stage);
  * entry at the close of m+1 WITH the draw; stop = R; target = the draw level;
    first qualifying PSP per setup; max_hold 24h.
claim '+': beats the matched random entry.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _smt_common as sc  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

W, MAX_HOLD = 24, "24h"


def detect(m1):
    P = sc.pair_bars(m1, "1h", "xag")
    ev = sc.smt_events(P)
    n = len(P)
    go, gh, gl, gc = (P[c].to_numpy() for c in ("g_open", "g_high", "g_low", "g_close"))
    so, sh, sl, scl = (P[c].to_numpy() for c in ("s_open", "s_high", "s_low", "s_close"))
    ct = pd.DatetimeIndex(P.close_time)
    sw = swing_points(P.rename(columns={"g_high": "high", "g_low": "low"})[["high", "low"]], 2, 2)
    swh = np.flatnonzero(sw.swing_high.to_numpy())
    swl = np.flatnonzero(sw.swing_low.to_numpy())
    rows = []
    for r in ev.itertuples():
        j, p, d = int(r.j), int(r.p), int(r.direction)
        c = j + 2
        if c >= n:
            continue
        if d == 1:
            R = gl[p:j + 1].min()
            if (gl[j + 1:c + 1] < R).any():
                continue
            prior = swh[swh + 2 < p]                 # confirmed before p
            if not len(prior):
                continue
            draw = gh[prior[-1]]
        else:
            R = gh[p:j + 1].max()
            if (gh[j + 1:c + 1] > R).any():
                continue
            prior = swl[swl + 2 < p]
            if not len(prior):
                continue
            draw = gl[prior[-1]]
        if not d * (draw - gc[c]) > 0:
            continue
        # the draw must not have been met between p and c
        if d == 1 and (gh[p:c + 1] >= draw).any():
            continue
        if d == -1 and (gl[p:c + 1] <= draw).any():
            continue
        for m in range(c + 1, min(n - 1, c + 1 + W)):
            k = m + 1
            dead = False
            for b in (m, k):
                if (d == 1 and (gh[b] >= draw or gl[b] < R)) or \
                   (d == -1 and (gl[b] <= draw or gh[b] > R)):
                    dead = True
            if dead:
                break
            if np.sign(gc[m] - go[m]) * np.sign(scl[m] - so[m]) < 0:
                runs = (gh[k] > gh[m] or sh[k] > sh[m]) if d == 1 else \
                       (gl[k] < gl[m] or sl[k] < sl[m])
                if runs and d * (gc[k] - R) > 0 and d * (draw - gc[k]) > 0:
                    rows.append({"decision_time": ct[k], "available_at": ct[k],
                                 "direction": d, "stop_px": float(R),
                                 "target_px": float(draw), "smt_time": ct[j]})
                    break
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "smt_time"]
    out = pd.DataFrame(rows, columns=cols)
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


if __name__ == "__main__":
    ev = cl.cache_frame("continuation_psp_1h_W24", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "exposure_bars", "ties", "avg_R")})
    p = cl.write_result(
        "continuation-psp", None, res,
        operationalization={"rules": [
            "gold 1H (certified M1) and OANDA XAG_USD H1, inner-joined on hour labels",
            "reversal: 1H SMT at bar j (fractal 2/2, lookback 20); gold extreme R from swing bar p..j not exceeded on j+1, j+2 (swing formed), confirmed at close of j+2",
            "draw: most recent confirmed gold fractal swing on the opposite side before p, still unmet at j+2",
            "within 24 bars (setup dies when gold meets the draw or breaks R): PSP bar m (opposite-colour closes) then bar m+1 where either asset exceeds its bar-m extreme in the draw direction",
            "enter with the draw at close of m+1; stop R; target the draw; first PSP per setup; max_hold 24h"],
            "params": {"tf": "1h", "fractal": [2, 2], "smt_lookback": 20,
                       "psp_scan_bars": W, "max_hold": MAX_HOLD,
                       "draw": "prior opposite-side 1H fractal swing", "stop": "reversal extreme R"}},
        params_source={
            "tf": "corpus: 3eVxTV_7L2U timeframes htf 4H/1H; 1H is the finest the correlate supports",
            "fractal": "phase3: swing_points left=2 right=2",
            "smt_lookback": "phase3: smt_events lookback=20",
            "psp_scan_bars": "declared-before-run: one trading day of 1H bars",
            "max_hold": "declared-before-run: 24h, the draw can be a day away",
            "draw": "declared-before-run: draw on liquidity is unquantified in the corpus (ambiguity); range extreme the reversal came from",
            "stop": "declared-before-run: the confirmed reversal extreme (low/high of the move)"},
        script=__file__, probe=probe,
        notes="Continuation PSP traded with the draw; control = matched random entries at the same stop/target distances.")
    print(p)
