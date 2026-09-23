"""smart-money-reversal-breaker-confirmation (guest: DayTradingRauf, wB-fQiT_UDo).

Declared before the first run. Bullish case on 1H bars (bearish mirrored by negating prices):
  1. Structure: a 2/2 swing low L0, then a 2/2 swing high H, then a LOWER low (a bar trades
     below L0) within 24 bars of H.
  2. Breaker block = the contiguous run of up-close candles into H (<= 10 candles); block =
     their bodies: bottom = min(open), top = max(close). "Project them forward."
  3. Trade-through: a 1H BODY close above the block top within 24 bars of the lower low,
     no earlier than H's confirmation (H + 2 bars). L1 = lowest low from H to that close.
  4. Return + fair value: the first later bar (within 24 bars) whose low trades back into the
     block (low <= top) without taking L1 and without closing below the block bottom, AND an
     area of fair value coincides with the block: a bullish FVG of the leg up from L1
     (stamped before the return bar) overlapping [bottom, top], OR the 50% of that leg
     (L1 -> highest high before the return bar) inside [bottom, top].
  5. Long at the next M1 open after the return bar closes; stop at L1 (below the lower low,
     stop not stated in the source); 2R; hold 10 bars (10h, trading time).
The 'at the model's midpoint' precondition has no mechanical rule in the source (located by
eye) and is not applied.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps, swing_points  # noqa: E402

TF = "1h"
WAIT = 24
MAX_SERIES = 10
RR = 2.0
HOLD = "10h"


def _scan(o, h, l, c, sgn, idx):
    tmp = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)
    sw = swing_points(tmp, 2, 2)
    is_h, is_l = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    fg = fair_value_gaps(tmp)
    fbull = fg["bullish_fvg"].to_numpy()
    glo, ghi = fg["gap_low"].to_numpy(), fg["gap_high"].to_numpy()
    n = len(c)
    lows_pos = np.flatnonzero(is_l)
    out = []
    for ph in np.flatnonzero(is_h):
        k0 = np.searchsorted(lows_pos, ph) - 1
        if k0 < 0:
            continue
        p0 = lows_pos[k0]
        L0 = l[p0]
        # up-close run into H
        # the run ends at H's candle, or the candle before it if H's own candle closed down
        if c[ph] > o[ph]:
            e = ph
        elif ph >= 1 and c[ph - 1] > o[ph - 1]:
            e = ph - 1
        else:
            continue
        s = e
        while s - 1 > p0 and c[s - 1] > o[s - 1] and (e - s + 1) < MAX_SERIES:
            s -= 1
        top = float(np.max(c[s:e + 1]))
        bot = float(np.min(o[s:e + 1]))
        # lower low within WAIT bars of H
        j = None
        for i in range(ph + 1, min(n, ph + WAIT + 1)):
            if l[i] < L0:
                j = i
                break
        if j is None:
            continue
        # body close above the block top
        k = None
        for i in range(max(j, ph + 2), min(n, j + WAIT + 1)):
            if c[i] > top:
                k = i
                break
        if k is None:
            continue
        lpos = ph + int(np.argmin(l[ph:k + 1]))
        L1 = l[lpos]
        m = None
        for i in range(k + 1, min(n, k + WAIT + 1)):
            if l[i] <= L1:
                break
            if l[i] <= top:
                if c[i] < bot:
                    break
                m = i
                break
        if m is None:
            continue
        hh = np.max(h[lpos:m])
        mid = (L1 + hh) / 2.0
        fv = any(fbull[i] and glo[i] <= top and ghi[i] >= bot for i in range(lpos + 2, m))
        if not (fv or (bot <= mid <= top)):
            continue
        out.append((m, L1))
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for sgn in (1, -1):
        f = float(sgn)
        o, c = f * b["open"].to_numpy(), f * b["close"].to_numpy()
        if sgn == 1:
            h, l = b["high"].to_numpy(), b["low"].to_numpy()
        else:
            h, l = -b["low"].to_numpy(), -b["high"].to_numpy()
        for m, L1 in _scan(o, h, l, c, sgn, b.index):
            rows.append({"decision_time": ct[m], "available_at": ct[m], "direction": sgn,
                         "stop_px": f * L1, "rr": RR})
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return (pd.DataFrame(rows)[cols].drop_duplicates()
            .sort_values(["decision_time", "direction"]).reset_index(drop=True))


if __name__ == "__main__":
    ev = cl.cache_frame("smr_breaker_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars", claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties", "exposure_bars")})
    op = {"rules": [
        "1H: 2/2 swing low L0, 2/2 swing high H, then a lower low (< L0) within 24 bars",
        "breaker = bodies of the up-close run into H (<=10 candles): [min open, max close]",
        "body close above the block top within 24 bars of the lower low (not before H is confirmed)",
        "first return into the block within 24 bars, not taking L1, not closing below the block; "
        "fair value must coincide: a bullish FVG of the L1 leg overlapping the block, or the leg's 50% inside it",
        "long next M1 open, stop L1, 2R, 10h trading time; bearish mirrored"],
        "params": {"tf": TF, "swing": "2/2", "wait_bars": WAIT, "max_series": MAX_SERIES,
                   "block": "bodies", "rr": RR, "max_hold": HOLD, "hold_basis": "bars",
                   "stop": "lower low (L1)"}}
    src = {"tf": "corpus: wB-fQiT_UDo timeframes ltf 1H (concept yaml)",
           "swing": "phase3: 2/2 fractal swing",
           "wait_bars": "declared-before-run: each structural step within 24 bars (one day)",
           "max_series": "phase3: cisd max_series 10",
           "block": "corpus: wB-fQiT_UDo 'the up-close candles at that structure are the block' + 'require a body close above them'",
           "rr": "phase3: 2R target (source target 'original consolidation' has no mechanical rule)",
           "max_hold": "phase3: 10 entry-TF bars",
           "hold_basis": "declared-before-run: trading-time hold across halts (trap 7)",
           "stop": "declared-before-run: source says stop not stated; below the reversal low"}
    p = cl.write_result("smart-money-reversal-breaker-confirmation", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Midpoint-of-model precondition not applied (located by eye in source).")
    print(p)
