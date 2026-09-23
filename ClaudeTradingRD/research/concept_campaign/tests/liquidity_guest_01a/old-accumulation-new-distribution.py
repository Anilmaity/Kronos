"""old-accumulation-new-distribution (Finessee_Fx / DayTradingRauf, guest, CONTESTED).

Two readings, one result each (parameters declared before the first run):

(a) Finessee_Fx's mirrored curve — trade_test on 4H structure, 1H entries.
    A confirmed 4H fractal(2/2) swing high s is the reversal. On its LEFT side (the
    30 4H bars before s) every bullish order block that was RESPECTED: a down-close
    candle b followed within 3 bars by a close above its high, zone = [low_b, open_b],
    and a later bar before s wicked into the zone (low <= open_b) while closing
    above low_b (wick-to-body respect). On the RIGHT side (after s is confirmed)
    the band must first be broken — a 4H close below low_b within 60 days — and the
    first 1H retrace into it (high >= low_b) that closes back at or below open_b is
    the re-polarised bearish block: short at that 1H close, stop = open_b (beyond the
    zone), target 2R, max_hold 48h. Swing lows mirror (bearish OBs, long).
    The 'reversal at a HTF PD array' precondition is not operationalised.

(b) Rauf's 'old gaps' variant — gate_test on 4H FVG retests.
    Baseline book: every 4H FVG retest traded as a reaction off the gap, from the
    side price approaches (prior close above the gap -> long, stop at the gap's
    bottom; below -> short, stop at its top), decided at the touching bar's close
    (skipped if that close is already through the far side), 2R, 48h.
    Two kinds of retest: FRESH = the gap's first touch after creation (within 60
    days); OLD = after the gap was traded into, 'accumulated' (>= 2 consecutive 4H
    bars overlapping it) and then departed (a bar entirely outside it), the next
    touch within 60 days of that departure. Gate = OLD. claim '+': old gaps react
    better than fresh ones ('fresh gaps with no accumulation history are not mapped').
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

L_LEFT, DISP_BARS, WAIT_D, RR, MAX_HOLD, ACC = 30, 3, 60, 2.0, "48h", 2
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "swing_time"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "old"]


def detect_a(m1):
    b = cl.build_bars(m1, "4h")                     # forex grid
    h1 = cl.build_bars(m1, "1h")
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b.close_time)
    t4 = pd.DatetimeIndex(b.index)
    H1h, H1l, H1c = h1.high.to_numpy(), h1.low.to_numpy(), h1.close.to_numpy()
    h1t = pd.DatetimeIndex(h1.index)
    h1ct = pd.DatetimeIndex(h1.close_time)
    sw = swing_points(b[["high", "low"]], 2, 2)
    n = len(b)
    rows = []
    wait = pd.Timedelta(days=WAIT_D)
    for hi_side in (True, False):
        d = -1 if hi_side else 1                  # trade direction on the return leg
        for s in np.flatnonzero(sw["swing_high" if hi_side else "swing_low"].to_numpy()):
            conf = s + 2
            if conf >= n:
                continue
            for bb in range(max(0, s - L_LEFT), s):
                if hi_side:            # bullish OB on the left of a swing high
                    if not c[bb] < o[bb]:
                        continue
                    e = min(s, bb + 1 + DISP_BARS)
                    if not (c[bb + 1:e] > h[bb]).any():
                        continue
                    zlo, zhi = l[bb], o[bb]
                    k0 = bb + 1 + int(np.argmax(c[bb + 1:e] > h[bb]))
                    seg = slice(k0 + 1, s)
                    if not ((l[seg] <= zhi) & (c[seg] > zlo)).any():
                        continue
                    if (c[k0 + 1:conf + 1] < zlo).any():
                        continue        # broken before the swing was confirmed
                else:                  # bearish OB on the left of a swing low
                    if not c[bb] > o[bb]:
                        continue
                    e = min(s, bb + 1 + DISP_BARS)
                    if not (c[bb + 1:e] < l[bb]).any():
                        continue
                    zlo, zhi = o[bb], h[bb]
                    k0 = bb + 1 + int(np.argmax(c[bb + 1:e] < l[bb]))
                    seg = slice(k0 + 1, s)
                    if not ((h[seg] >= zlo) & (c[seg] < zhi)).any():
                        continue
                    if (c[k0 + 1:conf + 1] > zhi).any():
                        continue
                # right side: band broken by a 4H close within WAIT_D of confirmation
                end_t = ct[conf] + wait
                r_hi = t4.searchsorted(end_t, side="left")
                rng = np.arange(conf + 1, min(n, r_hi))
                brk = rng[(c[rng] < zlo) if hi_side else (c[rng] > zhi)]
                if not len(brk):
                    continue
                r = brk[0]
                j0 = h1t.searchsorted(ct[r], side="left")
                j1 = h1t.searchsorted(end_t, side="left")
                if j0 >= j1:
                    continue
                if hi_side:
                    tch = np.flatnonzero(H1h[j0:j1] >= zlo)
                else:
                    tch = np.flatnonzero(H1l[j0:j1] <= zhi)
                if not len(tch):
                    continue
                q = j0 + tch[0]
                ok = (H1c[q] <= zhi) if hi_side else (H1c[q] >= zlo)
                stop = zhi if hi_side else zlo
                if ok and d * (H1c[q] - stop) > 0:
                    rows.append({"decision_time": h1ct[q], "available_at": h1ct[q],
                                 "direction": d, "stop_px": float(stop), "rr": RR,
                                 "swing_time": ct[s]})
    out = pd.DataFrame(rows, columns=COLS_A)
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


def detect_b(m1):
    b = cl.build_bars(m1, "4h")
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b.close_time)
    t4 = pd.DatetimeIndex(b.index)
    n = len(b)
    bull = np.zeros(n, bool); bear = np.zeros(n, bool)
    bull[2:] = l[2:] > h[:-2]
    bear[2:] = h[2:] < l[:-2]
    wait = pd.Timedelta(days=WAIT_D)
    rows = []

    def emit(k, glo, ghi, old):
        pc = c[k - 1]
        if pc > ghi:
            d, stop = 1, glo
        elif pc < glo:
            d, stop = -1, ghi
        else:
            return
        if d * (c[k] - stop) > 0:
            rows.append({"decision_time": ct[k], "available_at": ct[k], "direction": d,
                         "stop_px": float(stop), "rr": RR, "old": old})

    for i in np.flatnonzero(bull | bear):
        glo, ghi = (h[i - 2], l[i]) if bull[i] else (h[i], l[i - 2])
        end = t4.searchsorted(ct[i] + wait, side="left")
        k = i + 1
        inside = (l <= ghi) & (h >= glo)
        # fresh: first touch
        while k < min(n, end) and not inside[k]:
            k += 1
        if k >= min(n, end):
            continue
        emit(k, glo, ghi, False)
        # accumulation run starting at the first touch, then departure
        run, dep = 0, -1
        while k < n:
            if inside[k]:
                run += 1
            else:
                if run >= ACC:
                    dep = k
                    break
                run = 0
                # left without accumulating: wait for the next visit (within the window)
                if t4[k] >= ct[i] + wait:
                    break
            k += 1
        if dep < 0:
            continue
        end2 = t4.searchsorted(ct[dep] + wait, side="left")
        k = dep + 1
        while k < min(n, end2) and not inside[k]:
            k += 1
        if k < min(n, end2):
            emit(k, glo, ghi, True)
    out = pd.DataFrame(rows, columns=COLS_B)
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


COMMON_SRC = {
    "grid4h": "phase3: forex grid locked for gold (method_spec §1.4)",
    "fractal": "phase3: swing_points left=2 right=2",
    "rr": "phase3: bare-CISD book target 2R",
    "max_hold": "declared-before-run: twelve 4H bars",
    "wait_days": "corpus: eK_6wgNpNh0/wB-fQiT_UDo variant 'return to them for roughly the next 60 days'",
}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "a"
    if which == "a":
        ev = cl.cache_frame("oand_a_curve_4h1h", lambda: detect_a(cl.load_m1()))
        print(len(ev), ev.direction.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="80D")
        print("probe", probe["passed"])
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                       "verdict_detail", "exposure_bars", "ties")})
        p = cl.write_result(
            "old-accumulation-new-distribution", "a", res,
            operationalization={"rules": [
                "4H forex-grid swing high s (fractal 2/2) = reversal; left side = 30 4H bars before s",
                "left-side bullish OB: down-close candle followed within 3 bars by a close above its high; zone [low, open]; respected = a later bar before s wicked into the zone and closed above its low; not closed through before s is confirmed",
                "right side: a 4H close below the zone low within 60 days of confirmation; then the first 1H bar whose high re-enters the zone and closes at/below the zone top -> short at that close",
                "stop = zone top (beyond the zone); target 2R; max_hold 48h; swing lows mirror (bearish OB, long)",
                "HTF-PD-array precondition for the reversal not operationalised"],
                "params": {"grid4h": "forex", "fractal": [2, 2], "left_bars": L_LEFT,
                           "disp_bars": DISP_BARS, "ob_zone": "[low, open] of the opposing candle",
                           "wait_days": WAIT_D, "rr": RR, "max_hold": MAX_HOLD}},
            params_source={**COMMON_SRC,
                           "left_bars": "declared-before-run: the leg into the swing, 30 4H bars (~one week)",
                           "disp_bars": "declared-before-run: the OB must be followed by a close beyond it within 3 bars",
                           "ob_zone": "corpus: wick-to-body-order-block-zone (guest) — wick extreme to body; open used as the body edge that bounds the block"},
            script=__file__, probe=probe,
            notes="Reading (a): the mirrored-curve re-polarised order block, traded at the first return into the band.")
    else:
        ev = cl.cache_frame("oand_b_oldgaps_4h", lambda: detect_b(cl.load_m1()))
        print(len(ev), ev.old.mean())
        probe = cl.probe_lookahead(detect_b, ev, lookback="130D")
        print("probe", probe["passed"])
        res = cl.gate_test(ev, "old", mask_available_at="decision_time", max_hold=MAX_HOLD)
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                       "verdict_detail", "exposure_bars", "ties")})
        p = cl.write_result(
            "old-accumulation-new-distribution", "b", res,
            operationalization={"rules": [
                "4H forex-grid 3-bar FVGs",
                "fresh retest: first bar touching the gap within 60 days of creation",
                "old retest: after >= 2 consecutive bars overlapping the gap (accumulation) and a bar entirely outside it (departure), the next touch within 60 days of departure",
                "trade the reaction from the approach side (prior close above -> long, stop gap bottom; below -> short, stop gap top) at the touching bar's close; skip if already closed through; target 2R; max_hold 48h",
                "gate old vs fresh; claim '+'"],
                "params": {"grid4h": "forex", "accumulation_bars": ACC, "wait_days": WAIT_D,
                           "rr": RR, "max_hold": MAX_HOLD}},
            params_source={**COMMON_SRC,
                           "accumulation_bars": "declared-before-run: 'accumulated inside' has no dwell threshold (ambiguity); two consecutive 4H bars"},
            script=__file__, probe=probe,
            notes=f"Reading (b): old vs fresh FVG retests; gate firing rate {ev.old.mean():.3f}.")
    print(p)
