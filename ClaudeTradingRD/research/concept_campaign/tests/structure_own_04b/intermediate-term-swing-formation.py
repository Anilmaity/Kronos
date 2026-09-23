"""intermediate-term-swing-formation (structure, mixed voice, contested) — batch structure_own_04b.

Claim (d0x29IO1CQQ, xP-o11jRCyg, CrUfTskOveo): an intermediate-term low/high is the swing that
matters for structure — "while bearish you want intermediate-term lows to be broken and
intermediate-term highs to stay unviolated"; the yaml measurable is "continuation rate after an
intermediate-term low is broken vs after an ordinary swing low is broken". It forms two ways and
the two routes are never reconciled, so two readings:

 a  type 1: a short-term low (three-candle swing low) with a HIGHER short-term low on each side
    (mirrored for highs) — d0x29IO1CQQ.
 b  type 2 "rebalanced": the short-term low printed inside a bullish fair value gap that price
    reached into for the first time and traded away from (mirrored above) — d0x29IO1CQQ,
    CrUfTskOveo.

Baseline book (both readings, 5m — the yaml ltf): the first 5m CLOSE through a confirmed short-term
low (high) formed within the current + previous two 1h candles (the three-HTF-candle look-back,
5m -> 1h pairing), traded in the break direction (short on a low break, long on a high break);
decide at the breaking bar's close, enter next M1 open; stop at the extreme since the swing (the
high between the low and the break); 2R; 50 min (10 x 5m). Gate = the broken swing is an
intermediate-term swing of the reading's type, as known at the decision. claim '+'.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, swing_points, HOLD, RR
from detectors.primitives import fair_value_gaps

TF = "5min"
SW = (1, 1)
WIN_H = 3          # three 1h candles incl. current
FVG_LOOKBACK = 36  # FVG must have formed within the same three-hour window (36 x 5m)


def detect(m1):
    b = cl.build_bars(m1, TF)
    n = len(b)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    hour = (b.index.tz_convert("UTC").floor("h").as_unit("ns").asi8 // 3_600_000_000_000)
    sw = swing_points(b[["high", "low"]], *SW)
    fv = fair_value_gaps(b[["high", "low"]])
    bullf, bearf = fv["bullish_fvg"].to_numpy(), fv["bearish_fvg"].to_numpy()
    glo, ghi = fv["gap_low"].to_numpy(float), fv["gap_high"].to_numpy(float)
    R = SW[1]
    rows = []
    for side in ("low", "high"):
        idx = np.flatnonzero(sw["swing_low" if side == "low" else "swing_high"].to_numpy())
        lv = l if side == "low" else h
        for k, s in enumerate(idx):
            j0 = s + R + 1
            if j0 >= n:
                continue
            j = -1
            for q in range(j0, n):
                if hour[q] - hour[s] > WIN_H - 1:
                    break
                if (c[q] < lv[s]) if side == "low" else (c[q] > lv[s]):
                    j = q
                    break
            if j < 0:
                continue
            # reading a: type-1 neighbours
            t1 = False
            if 0 < k < len(idx) - 1:
                left, right = idx[k - 1], idx[k + 1]
                if right + R <= j:                         # right neighbour confirmed by the break close
                    if side == "low":
                        t1 = lv[left] > lv[s] and lv[right] > lv[s]
                    else:
                        t1 = lv[left] < lv[s] and lv[right] < lv[s]
            # reading b: rebalanced into a first-reach FVG
            t2 = False
            for f in range(max(2, s - FVG_LOOKBACK), s):
                if side == "low" and bullf[f]:
                    if glo[f] <= l[s] <= ghi[f] and (s - f <= 1 or l[f + 1:s].min() > ghi[f]):
                        t2 = True
                        break
                if side == "high" and bearf[f]:
                    if glo[f] <= h[s] <= ghi[f] and (s - f <= 1 or h[f + 1:s].max() < glo[f]):
                        t2 = True
                        break
            if side == "low":
                stop, dirn = h[s:j + 1].max(), -1
            else:
                stop, dirn = l[s:j + 1].min(), 1
            rows.append((ct[j], dirn, stop, bool(t1), bool(t2)))
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "itl_type1", "itl_rebal"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC") if len(ev) else pd.DatetimeIndex([], tz="UTC")
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    ev["direction"] = ev["direction"].astype(int)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr", "itl_type1", "itl_rebal"]]
    return ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"itsf_{TF}_w{WIN_H}_f{FVG_LOOKBACK}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["itl_type1"].mean()), float(ev["itl_rebal"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    base_rules = [
        "baseline: first 5m close through a confirmed three-candle short-term low (high) formed within the current + previous two 1h candles; trade the break (short a low break, long a high break)",
        "decide at the breaking 5m bar's close, enter next M1 open; stop at the extreme since the swing (max high / min low from the swing bar to the break bar); 2R; 50 min wall clock"]
    src = {"tf": "corpus: yaml timeframes ltf 5m (d0x29IO1CQQ diagram generic; 5m is the stated ltf)",
           "swing": "corpus: d0x29IO1CQQ 'A short-term low is when we form a swing low' (a low with a higher low on each side)",
           "win_h": "corpus: HbOeD_JVens three-HTF-candle look-back applied to the 5m -> 1h pairing (method_spec §1.2)",
           "rr": "phase3: 2R rung-0 target",
           "max_hold": "phase3: 10 entry-TF periods"}
    params = {"tf": TF, "swing": "1/1 fractal", "win_h": WIN_H, "rr": RR, "max_hold": HOLD[TF]}
    for reading, col in (("a", "itl_type1"), ("b", "itl_rebal")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                                "exposure_bars", "ties", "ctrl_overlap")})
        if reading == "a":
            gate = ["gate: the broken swing is a type-1 intermediate-term swing — its neighbouring short-term lows on both sides are higher (highs: lower), the right neighbour confirmed by the decision"]
            p2, s2 = dict(params), dict(src)
        else:
            gate = ["gate: the broken swing is a 'rebalanced' intermediate-term swing — its low printed inside a bullish FVG (high inside a bearish FVG) formed within the prior 36 5m bars and not reached before"]
            p2 = dict(params, fvg_lookback=FVG_LOOKBACK, fvg_reach="extreme inside [gap_low, gap_high], first reach")
            s2 = dict(src, fvg_lookback="declared-before-run: FVG inside the same three-1h-candle window (36 x 5m)",
                      fvg_reach="declared-before-run: 'reaching into' = extreme inside the gap (corpus does not quantify: yaml ambiguity)")
        op = {"rules": base_rules + gate + ["claim: breaks of intermediate-term swings continue better than breaks of ordinary short-term swings (control-adjusted R)"],
              "params": p2}
        path = cl.write_result("intermediate-term-swing-formation", reading, res, operationalization=op,
                               params_source=s2, script=__file__, probe=probe,
                               notes=f"gate firing rate {float(ev[col].mean()):.3f} of {len(ev)} short-term swing breaks.")
        print("wrote", path)
