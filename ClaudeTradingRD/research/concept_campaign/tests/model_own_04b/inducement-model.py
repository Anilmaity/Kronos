"""inducement-model — trade_test, two readings (contested).

The model (k3hTgbHBz1U), bullish walk: a low, then a lower high, then the low is run
(sweep), then a high is put in breaking structure, then a low forms "that induces people
to go long" — and THAT internal low is run before the actual move. "Just internal
liquidity in a range that is ran before the actual move." The run of the internal level
is the entry location. He prefers a fair value gap at the inducement.

Operationalisation on 15m bars (the yaml's middle structure timeframe), declared before
the run; bearish is the mirror (prices negated):
  1. a confirmed 2/2 swing low L0; within 40 bars a bar trades below it (the sweep);
  2. the lower high H0 = highest high between L0 and the sweep; within 20 bars of the
     sweep a bar CLOSES above H0 (structure break). E = lowest low from the sweep to that
     close (the protected low);
  3. within 40 bars of the break: the most recent confirmed 2/2 swing low formed after
     the break is the inducement I; the first bar trading below I (while staying above
     E) is the inducement run -> decide at that bar's close;
  4. stop = E; target = the highest high since the break (the range's external
     liquidity); time exit 150 min (10 entry-TF bars, phase-3 convention).
Reading a: no FVG requirement. Reading b: a same-direction 3-bar FVG whose gap overlaps
the inducement candle's range, printed between the sweep and the inducement's
confirmation (the stated preference, made a requirement).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import fractal_swings  # noqa: E402

SWEEP_WIN, MSS_WIN, IND_WIN = 40, 20, 40
MAX_HOLD = "150min"


def _scan(o, h, l, c, sl):
    """Bullish inducement events on (possibly negated) arrays. Returns list of
    (j, stop, target, fvg_ok)."""
    n = len(c)
    out = {}
    for s0 in np.flatnonzero(sl):
        k1 = -1
        for k in range(s0 + 3, min(n, s0 + 3 + SWEEP_WIN)):
            if l[k] < l[s0]:
                k1 = k
                break
        if k1 < 0 or k1 - s0 < 2:
            continue
        H0 = h[s0 + 1:k1].max()
        E = l[k1]
        k2 = -1
        for k in range(k1 + 1, min(n, k1 + 1 + MSS_WIN)):
            E = min(E, l[k])
            if c[k] > H0:
                k2 = k
                break
        if k2 < 0:
            continue
        ind = -1
        top = h[k2]
        for j in range(k2 + 1, min(n, k2 + 1 + IND_WIN)):
            q = j - 3                                   # a swing at q is known at close of q+2
            if q > k2 and sl[q]:
                ind = q
            if l[j] <= E:
                break
            top = max(top, h[j])
            if ind >= 0 and l[j] < l[ind]:
                if top > c[j] and j not in out:
                    zlo, zhi = l[ind], h[ind]
                    fvg = False
                    for m in range(k1 + 2, ind + 3):
                        if l[m] > h[m - 2] and h[m - 2] <= zhi and l[m] >= zlo:
                            fvg = True
                            break
                    out[j] = (E, top, fvg)
                break
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "15min")
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    sh, sl = fractal_swings(h, l, 2, 2)
    rows = []
    for sgn, arrs, sw in ((1, (o, h, l, c), sl), (-1, (-o, -l, -h, -c), sh)):
        for j, (E, top, fvg) in _scan(*arrs, sw).items():
            rows.append({"decision_time": ct[j], "available_at": ct[j], "direction": sgn,
                         "stop_px": sgn * E, "target_px": sgn * top, "fvg": bool(fvg)})
    ev = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                     "stop_px", "target_px", "fvg"])
    return ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


def detect_a(m1):
    return detect(m1).drop(columns="fvg")


def detect_b(m1):
    ev = detect(m1)
    return ev[ev["fvg"]].drop(columns="fvg").reset_index(drop=True)


if __name__ == "__main__":
    base = cl.cache_frame("inducement_15m_v1", lambda: detect(cl.load_m1()))
    print(len(base), base["fvg"].mean(), base["direction"].value_counts().to_dict())
    op_rules = [
        "15m bars, 2/2 fractal swings; bullish: swing low L0 swept within 40 bars",
        "structure break: close above the lower high between L0 and the sweep within 20 bars; "
        "E = lowest low sweep->break",
        "inducement = most recent confirmed swing low formed after the break; first bar trading "
        "below it (above E) within 40 bars = entry decision at its close",
        "stop E; target = highest high since the break; 150 min; bearish mirrored"]
    params = {"tf": "15min", "swing": "2/2", "sweep_win": SWEEP_WIN, "mss_win": MSS_WIN,
              "ind_win": IND_WIN, "max_hold": MAX_HOLD}
    src = {"tf": "corpus: inducement-model yaml timeframes htf 1H/15m/5m (middle)",
           "swing": "method_spec: §4.2 / threshold_fits §2 fractal 2/2",
           "sweep_win": "declared-before-run: bound on the sweep search (unstated)",
           "mss_win": "declared-before-run: bound on the break after the sweep (unstated)",
           "ind_win": "declared-before-run: yaml 'No timing bound between the structure break and the run'",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    for reading, fn in (("a", detect_a), ("b", detect_b)):
        ev = base.drop(columns="fvg") if reading == "a" else \
            base[base["fvg"]].drop(columns="fvg").reset_index(drop=True)
        probe = cl.probe_lookahead(fn, ev, lookback="6D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        print("reading", reading)
        for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
            print(" ", k, res.get(k))
        rules = op_rules + (["no FVG requirement"] if reading == "a" else
                            ["REQUIRE a bullish 3-bar FVG whose gap overlaps the inducement "
                             "candle's range, printed between the sweep and the inducement's "
                             "confirmation"])
        pr = dict(params, fvg_required=(reading == "b"))
        sr = dict(src, fvg_required="corpus: k3hTgbHBz1U 'i do like to see some sort of fair value gap in there'")
        p = cl.write_result("inducement-model", reading, res,
                            operationalization={"rules": rules, "params": pr},
                            params_source=sr, script=__file__, probe=probe,
                            notes="Contested (earlier five-step recording vs later general definition); "
                                  "readings split on the stated FVG preference.")
        print("wrote", p)
