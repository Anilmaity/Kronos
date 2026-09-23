"""mitigation-block-nested-pd — The MMXM Trader: a mitigation block alone is not the entry;
trade it only when a new PD array (FVG) has formed inside the block's range.

Test: gate_test. Baseline book = every retrace into an extended mitigation block on the buy
side of the curve (the block alone). gate = a same-direction FVG formed on the buy side whose
range overlaps the block's range. claim '+': nested blocks beat bare blocks.

Buy model on 1h (sell model = the same on negated prices):
  curve low SL = a confirmed 2/2 swing low; range top SH = the highest high of the W bars
  before SL; sell side of the curve = bars strictly between SH and SL.
  mitigation blocks = up-close candles (close > open) on the sell side, range [low, high],
  extended right.
  buy side = the W bars after SL is confirmed; a block is 'passed' once a bar closes above its
  high; the first later bar whose low <= block high and whose close > block low is the tap.
  Price trading below SL ends the curve.
  trade: long at the tap bar close (next M1 open), stop = block low, target = SH (the opposing
  extreme of the range), 10 x 1h max hold. One row per (bar, direction): the highest tapped block.
  nested = a bullish 3-bar FVG, third bar after SL and before the tap bar, overlapping [low, high]
  of that block.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "mitigation-block-nested-pd"
TF = "1h"
W = 48
MAX_HOLD = "10h"


def swing_lows(l, left=2, right=2):
    ls = pd.Series(l)
    prev_l = ls.shift(1).rolling(left).min()
    next_l = ls[::-1].shift(1).rolling(right).min()[::-1]
    return ((ls < prev_l) & (ls <= next_l)).to_numpy()


def buy_events(o, h, l, c):
    n = len(h)
    piv = np.where(swing_lows(l))[0]
    fvg = np.r_[False, False, l[2:] > h[:-2]]
    glo = np.r_[np.nan, np.nan, h[:-2]]
    ghi = l
    ev = {}                                          # bar -> (block_high, stop, target, nested)
    for sl in piv:
        if sl < W or sl + 2 >= n:
            continue
        win = slice(sl - W, sl)
        sh = sl - W + int(np.argmax(h[win]))
        top = h[sh]
        blocks = [b for b in range(sh + 1, sl) if c[b] > o[b]]
        if not blocks:
            continue
        start, end = sl + 3, min(n, sl + 3 + W)      # first bar after confirmation (sl+2)
        passed = {b: False for b in blocks}
        done = set()
        for i in range(start, end):
            if l[i] < l[sl]:
                break
            tapped = []
            for b in blocks:
                if b in done:
                    continue
                if passed[b] and l[i] <= h[b]:
                    done.add(b)
                    if c[i] > l[b]:
                        tapped.append(b)
            for b in blocks:
                if not passed[b] and c[i] > h[b]:
                    passed[b] = True
            if tapped and c[i] < top:
                b = max(tapped, key=lambda x: h[x])
                ks = np.where(fvg[sl + 1:i])[0] + sl + 1
                nested = bool(((glo[ks] <= h[b]) & (ghi[ks] >= l[b])).any()) if len(ks) else False
                prev = ev.get(i)
                if prev is None or h[b] > prev[0]:
                    ev[i] = (h[b], l[b], top, nested)
    return ev


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for sgn, arr in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for i, (_, stop, tgt, nested) in buy_events(*arr).items():
            rows.append((ct[i], sgn, sgn * stop, sgn * tgt, nested))
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "nested"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "nested"])
    df = df.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.decision_time, "available_at": df.decision_time,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "target_px": df.target_px, "nested": df.nested.astype(bool).to_numpy()})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_W{W}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.nested.mean(), ev.direction.value_counts().to_dict())
    if "--dry" in sys.argv:
        print(ev.head()); raise SystemExit
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "nested", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "1h bars; curve low = confirmed 2/2 swing low; range top = highest high of the 48 bars before it",
        "mitigation blocks = up-close candles between range top and curve low, [low, high], extended right",
        "buy side = 48 bars after the curve low confirms; block passed = a close above its high; "
        "tap = first later bar with low <= block high and close > block low; below curve low ends it",
        "long at tap close (next M1 open); stop block low; target range top; 10h max hold; one row per bar "
        "(highest tapped block); sell model mirrored",
        "gate nested = a same-direction 3-bar FVG formed after the curve low and before the tap, "
        "overlapping the block's range"],
        "params": {"tf": TF, "curve_window_bars": W, "swing": "2/2", "stop": "block low",
                   "target": "range top", "max_hold": MAX_HOLD, "nested_array": "FVG"}}
    src = {"tf": "corpus: Ibw4saRtYMk MMXM timeframes (concept yaml ltf 1H/15m/5m); 1h chosen",
           "curve_window_bars": "declared-before-run: 48 bars (two days of 1h) either side of the curve low",
           "swing": "phase3: meta/conjunction_preregistration.md §1.8 left=2,right=2",
           "stop": "declared-before-run: stop not stated in source; beyond the block (its low)",
           "target": "corpus: Ibw4saRtYMk execution target 'the opposing extreme of the range'",
           "max_hold": "phase3: §1.13 10 entry-TF periods",
           "nested_array": "corpus: Ibw4saRtYMk 'typically a fair value gap or an opposing order block' (FVG branch)"}
    notes = ("Only the FVG branch of the nested PD array is tested (the opposing-order-block branch "
             "is left out: any down-close candle inside the block would qualify, which does not "
             "separate anything). Entry is at the block tap in both arms, so the gate isolates "
             "whether the nested FVG's presence selects better block taps.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes, probe=probe)
    print(p)
