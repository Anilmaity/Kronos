"""consolidation-phase (TTrades own voice, contested) -> two readings.

The concept: a consolidation is price remaining internal to a marked high and low for a
period of time; do not trade inside it; wait for one side to be taken, then trade to the
other side of the range (entry "after the sweep, on the closure through the opposing
candles into the level"; target "the opposite side of the range"). CONTESTED: which side
supplies the direction -- (a) the side taken FIRST (yfj10dtkRKY: 'If the low of the range
gets taken out first, that is generally bullish'), or (b) the side chosen BY BIAS (WFqLwOp2pXw:
bullish requires the low to be run out).

Declared before the first run:
  * Range (1h structure, 5m execution -- method_spec §1.2 pairing 1H -> 5m): a 1h "mother"
    bar followed by 3 consecutive 1h bars that stay entirely inside it (take neither its high
    nor its low: 'price hasn't traded below this low, and price hasn't traded above this
    high'; 3 bars = the shortest example in the corpus). Range = mother high/low, known at
    the close of the 3rd inside bar.
  * Side taken first: the first M1 bar after that close that trades beyond the range high or
    low, searched within the next 1380 M1 bars (one trading day); an M1 bar taking both
    sides is skipped.
  * Entry: the first 5m close back inside the range beyond the taken level (low taken -> a
    5m close above the range low) within 12 5m bars (one hour) of the sweep, provided the
    opposite side has not been taken first. Decide at that 5m close.
  * Stop: the sweep extreme (lowest M1 low from the sweep to the decision, for a long).
    Target: the opposite side of the range. max_hold 24h of trading bars.
  reading a: trade_test of that book (direction = away from the side taken first), claim '+';
    control drawn at the same NY time of day +/-30 min (not a timing concept, trap 9).
  reading b: gate_test on the same book: gate = the trade direction agrees with the daily
    previous-candle bias (last completed 18:00 daily candle: continuation closure up or a
    swept-low-and-closed-back-inside reversal closure -> bullish; mirrored; both/neither ->
    no bias). claim '+' (bias-aligned side selection is better).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, daily, show

CID = "consolidation-phase"
N_INSIDE = 3
SEARCH_M1 = 1380
RECLAIM_5M = 12
MAX_HOLD = "24h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px",
        "range_hi", "range_lo", "bias_aligned", "bias_avail"]
NS_MIN = 60_000_000_000


def daily_bias(d: pd.DataFrame) -> np.ndarray:
    """+1/-1/0 previous-candle bias carried by each completed daily candle."""
    H, L, C = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    took_h, took_l = H > ph, L < pl
    bull = (took_h & ~took_l & (C > ph)) | (took_l & ~took_h & (C >= pl))
    bear = (took_l & ~took_h & (C < pl)) | (took_h & ~took_l & (C <= ph))
    return np.where(bull, 1, np.where(bear, -1, 0))


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    h = cl.build_bars(m1, "1h")
    if len(h) < N_INSIDE + 2:
        return pd.DataFrame(columns=COLS)
    H, L = h["high"].to_numpy(float), h["low"].to_numpy(float)
    hct = cl.data.utc_ns(pd.DatetimeIndex(h["close_time"]))
    n = len(h)
    inside = np.ones(n - N_INSIDE, bool)
    for k in range(1, N_INSIDE + 1):
        inside &= (H[k:n - N_INSIDE + k] <= H[:n - N_INSIDE]) & (L[k:n - N_INSIDE + k] >= L[:n - N_INSIDE])
    moms = np.flatnonzero(inside)

    mt = cl.data.utc_ns(pd.DatetimeIndex(m1.index))
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    f5 = cl.build_bars(m1, "5min")
    f5t = cl.data.utc_ns(pd.DatetimeIndex(f5.index))
    f5ct = cl.data.utc_ns(pd.DatetimeIndex(f5["close_time"]))
    f5c = f5["close"].to_numpy(float)

    d = daily(m1)
    bias = daily_bias(d)
    dct = cl.data.utc_ns(pd.DatetimeIndex(d["close_time"]))

    rows = []
    for m in moms:
        rh, rl = H[m], L[m]
        t0 = hct[m + N_INSIDE]                     # range known at this close
        a = np.searchsorted(mt, t0, side="left")
        b = min(len(mt), a + SEARCH_M1)
        if b <= a:
            continue
        up = mh[a:b] > rh
        dn = ml[a:b] < rl
        hit = np.flatnonzero(up | dn)
        if not len(hit):
            continue
        s = a + hit[0]
        if up[hit[0]] and dn[hit[0]]:
            continue
        sgn = 1 if dn[hit[0]] else -1               # low taken first -> long
        # 5m bars whose close is after the sweep minute's close, within RECLAIM_5M bars
        k0 = np.searchsorted(f5t, mt[s], side="right") - 1   # 5m bar containing the sweep
        k1 = min(len(f5c), k0 + RECLAIM_5M)
        if k0 < 0 or k1 <= k0:
            continue
        cc = f5c[k0:k1]
        ok = np.flatnonzero((cc > rl) if sgn > 0 else (cc < rh))
        if not len(ok):
            continue
        k = k0 + ok[0]
        dec = f5ct[k]
        if sgn > 0 and f5c[k] >= rh or sgn < 0 and f5c[k] <= rl:
            continue
        e = np.searchsorted(mt, dec, side="left")        # M1 bars strictly before decision
        seg = slice(s, e)
        if e <= s:
            continue
        if sgn > 0:
            if (mh[seg] > rh).any():                    # opposite side taken before entry
                continue
            stop = ml[seg].min()
        else:
            if (ml[seg] < rl).any():
                continue
            stop = mh[seg].max()
        target = rh if sgn > 0 else rl
        # daily bias from the last completed daily candle at the decision
        p = np.searchsorted(dct, dec, side="right") - 1
        bv = bias[p] if p >= 0 else 0
        bav = dct[p] if p >= 0 else dec
        rows.append((dec, sgn, stop, target, rh, rl, bool(bv == sgn), bav))
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px", "range_hi",
                                     "range_lo", "bias_aligned", "bav"])
    ev["decision_time"] = pd.to_datetime(ev["t"], utc=True)
    ev["available_at"] = ev["decision_time"]
    ev["bias_avail"] = pd.to_datetime(ev["bav"], utc=True)
    ev = ev.drop_duplicates(["decision_time", "direction", "stop_px", "target_px"])
    ev = ev.sort_values(["decision_time", "direction", "target_px"]).reset_index(drop=True)
    return ev[COLS]


def op_params():
    params = {"structure_tf": "1h", "entry_tf": "5min", "n_inside": N_INSIDE,
              "search_m1": SEARCH_M1, "reclaim_5m_bars": RECLAIM_5M,
              "stop": "sweep extreme", "target": "opposite side of the range",
              "max_hold": MAX_HOLD, "hold_basis": "bars", "grid4h": "n/a"}
    src = {"structure_tf": "method_spec: §1.2 timeframe pairing 1H structure -> 5m execution",
           "entry_tf": "method_spec: §1.2 timeframe pairing 1H -> 5m",
           "n_inside": "corpus: -YZBFoNfeUA 'price hasn't traded below this low, and price hasn't traded above this high'; 3 bars = shortest corpus example (ambiguities)",
           "search_m1": "declared-before-run: the range stays live for one trading day",
           "reclaim_5m_bars": "declared-before-run: the closure back into the range within one hour of the sweep",
           "stop": "declared-before-run: stop not restated in the concept; beyond the manipulation extreme (protected-swing logic, method_spec §5.1)",
           "target": "corpus: yfj10dtkRKY trade to the other side of the range",
           "max_hold": "declared-before-run: one trading day for range-to-range delivery",
           "hold_basis": "declared-before-run: trading-time hold (trap 7)",
           "grid4h": "declared-before-run: not used"}
    return params, src


def main(readings):
    ev = cl.cache_frame(f"consphase_1h_in{N_INSIDE}_rc{RECLAIM_5M}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "bias aligned", int(ev["bias_aligned"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    params, src = op_params()
    base_rules = [
        "range: a 1h mother bar followed by 3 consecutive 1h bars entirely inside it; known at the 3rd inside bar's close",
        "side taken first: first M1 beyond the range high or low within one trading day (both in one M1 -> skip)",
        "entry: first 5m close back inside the range beyond the taken level within 12 5m bars, opposite side not yet taken; decide at that close",
        "stop = sweep extreme; target = opposite side of the range; max hold 24h of trading bars"]
    if "a" in readings:
        res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis="bars", ctrl_tod_tol_min=30)
        show(res)
        p = dict(params, ctrl_tod_tol_min=30)
        s = dict(src, ctrl_tod_tol_min="declared-before-run: not a timing concept; hold NY clock fixed (trap 9)")
        print(cl.write_result(CID, "a", res, operationalization={
            "rules": base_rules + ["reading a: direction = away from the side taken FIRST (low first -> long)"],
            "params": p}, params_source=s, script=__file__, probe=probe,
            notes="Reading a: the side taken first supplies the direction (yfj10dtkRKY)."))
    if "b" in readings:
        res = cl.gate_test(ev, "bias_aligned", mask_available_at="bias_avail", claim="+",
                           max_hold=MAX_HOLD, hold_basis="bars")
        show(res)
        p = dict(params, bias="daily previous-candle bias")
        s = dict(src, bias="method_spec: §2.3 previous-candle engine (continuation closure / swept-and-closed-back-inside) on the last completed 18:00 daily candle")
        print(cl.write_result(CID, "b", res, operationalization={
            "rules": base_rules + ["reading b: gate = trade direction equals the daily previous-candle bias "
                                   "(bias chooses which side must be run); claim '+'"],
            "params": p}, params_source=s, script=__file__, probe=probe,
            notes="Reading b: bias selects the manipulated side (WFqLwOp2pXw); tested as a gate "
                  "on the reading-a book."))


if __name__ == "__main__":
    main(sys.argv[1:] or ["a", "b"])
