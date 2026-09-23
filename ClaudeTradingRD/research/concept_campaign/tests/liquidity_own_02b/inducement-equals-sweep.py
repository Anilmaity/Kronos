"""inducement-equals-sweep — two readings of 'Inducement' (contested), both trade_tests.

Fixed BEFORE the first run.
Common: 15m bars (ltf list 15m/5m); short-term high/low = 2/2 fractal swing, usable once
confirmed (2 bars later). One event per swing level (its first sweep).

Reading a — inducement WITH ORDER FLOW (-GkOTMYoJT4: "with bullish order flow I want lows to
be run to position long"). Order flow = the previous-candle engine (method_spec §2.3) on the
last CLOSED 4H candle (forex grid): continuation closure (took prior high & closed above it)
-> bullish; reversal closure (took prior low & closed back inside) -> bullish; mirrored for
bearish; both sides / neither -> no order flow, no trade.
  bullish event: a 15m bar trades below the latest confirmed swing low and CLOSES back above it
  (invalidation: 'closes beyond the induced level rather than a wick' -> not inducement),
  while order flow is bullish. Enter at that bar's close (next M1 open), long; stop at the
  bar's low (beyond the sweep); target = the latest confirmed swing high ("the high the
  inducement was engineered from"); dropped if that high is not above the close.
Reading b — 'inducement is just a sweep; preferred form = sweep of a short-term high/low
followed by a fair value gap' (variant). No order-flow condition.
  bullish event: a 15m bar trades below the latest confirmed swing low; within that bar and the
  next 3 (N=4) a bullish 3-bar FVG prints (low[k] > high[k-2]) before any lower low. Enter at
  the FVG bar's close, long; stop at the lowest low since the sweep; target = latest confirmed
  swing high known at the sweep; dropped if not above the FVG bar close.
Both mirrored for bearish. max_hold 10 bars (150 min) trading time.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import swings, last_confirmed_level

CID = "inducement-equals-sweep"
TF = "15min"
HTF = "4h"
N_FVG = 4
HOLD = "150min"


def order_flow(m1, times):
    """+1/-1/0 from the last 4H candle with close_time <= t (previous-candle engine)."""
    h4 = cl.build_bars(m1, HTF)
    o, h, l, c = (h4[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    took_h, took_l = h > ph, l < pl
    st = np.zeros(len(h4), int)
    only_h, only_l = took_h & ~took_l, took_l & ~took_h
    st[only_h & (c > ph)] = 1          # continuation closure up
    st[only_h & (c <= ph)] = -1        # reversal closure at the high
    st[only_l & (c < pl)] = -1         # continuation closure down
    st[only_l & (c >= pl)] = 1         # reversal closure at the low
    ct = cl.data.utc_ns(pd.DatetimeIndex(h4["close_time"]))
    pos = np.searchsorted(ct, cl.data.utc_ns(pd.DatetimeIndex(times)), side="right") - 1
    return np.where(pos >= 0, st[np.maximum(pos, 0)], 0)


def _frame(b, idx, d, stop, tgt):
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[idx]).tz_convert("UTC") if len(idx) \
        else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": d.astype(int), "stop_px": stop, "target_px": tgt})


def detect_a(m1):
    b = cl.build_bars(m1, TF)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ish, isl = swings(b)
    sl_lvl, sl_id = last_confirmed_level(isl, l)
    sh_lvl, sh_id = last_confirmed_level(ish, h)
    of = order_flow(m1, pd.DatetimeIndex(b["close_time"]))
    bull = (l < sl_lvl) & (c > sl_lvl) & (of == 1) & (sh_lvl > c)
    bear = (h > sh_lvl) & (c < sh_lvl) & (of == -1) & (sl_lvl < c)
    rows = []
    for mask, d, sid in ((bull, 1, sl_id), (bear, -1, sh_id)):
        # first sweep of each swing: bars where the swing is traded through at all
        through = (l < sl_lvl) if d == 1 else (h > sh_lvl)
        j_all = np.flatnonzero(through & (sid >= 0))
        first = pd.Series(j_all).groupby(sid[j_all]).min().to_numpy() if len(j_all) else np.array([], int)
        j = first[mask[first]] if len(first) else first
        rows.append((j, np.full(len(j), d)))
    j = np.concatenate([r[0] for r in rows]).astype(int)
    d = np.concatenate([r[1] for r in rows]).astype(int)
    o = np.argsort(j, kind="stable")
    j, d = j[o], d[o]
    stop = np.where(d > 0, l[j], h[j])
    tgt = np.where(d > 0, sh_lvl[j], sl_lvl[j])
    return _frame(b, j, d, stop, tgt)


def detect_b(m1):
    b = cl.build_bars(m1, TF)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(b)
    ish, isl = swings(b)
    sl_lvl, sl_id = last_confirmed_level(isl, l)
    sh_lvl, sh_id = last_confirmed_level(ish, h)
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l[:-2]]
    bull_fvg = l > h2
    bear_fvg = h < l2
    out_j, out_d, out_stop, out_tgt = [], [], [], []
    for d in (1, -1):
        through = (l < sl_lvl) if d == 1 else (h > sh_lvl)
        sid = sl_id if d == 1 else sh_id
        j_all = np.flatnonzero(through & (sid >= 0))
        if not len(j_all):
            continue
        first = pd.Series(j_all).groupby(sid[j_all]).min().to_numpy()
        for j in first:
            tgt = sh_lvl[j] if d == 1 else sl_lvl[j]
            ext = l[j] if d == 1 else h[j]
            for k in range(j, min(n, j + N_FVG)):
                if k > j:
                    if (d == 1 and l[k] < ext) or (d == -1 and h[k] > ext):
                        break                      # new extreme beyond the sweep: not yet reversing
                if (d == 1 and bull_fvg[k]) or (d == -1 and bear_fvg[k]):
                    if (d == 1 and tgt > c[k]) or (d == -1 and tgt < c[k]):
                        out_j.append(k); out_d.append(d); out_stop.append(ext); out_tgt.append(tgt)
                    break
    j = np.asarray(out_j, int)
    o = np.argsort(j, kind="stable")
    return _frame(b, j[o], np.asarray(out_d)[o] if len(o) else np.array([], int),
                  np.asarray(out_stop, float)[o], np.asarray(out_tgt, float)[o])


SRC = {"tf": "declared-before-run: 15m, the first ltf listed by the concept",
       "swing": "phase3: 2/2 fractal swings (conjunction_preregistration locked swing definition)",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)",
       "hold_basis": "declared-before-run: trading-time holds (trap 7)",
       "target": "corpus: -GkOTMYoJT4 execution 'targets: the high/low the inducement was engineered from'",
       "stop": "corpus: execution 'stop: beyond the sweep'"}


def run(reading):
    det = detect_a if reading == "a" else detect_b
    ev = cl.cache_frame(f"{CID}_{reading}_{TF}", lambda: det(cl.load_m1()))
    print(reading, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars")
    params = {"tf": TF, "swing": "2/2", "max_hold": HOLD, "hold_basis": "bars",
              "target": "latest confirmed opposite swing", "stop": "sweep extreme"}
    src = dict(SRC)
    if reading == "a":
        rules = ["15m bars; latest confirmed 2/2 swing low/high",
                 "order flow = previous-candle engine on the last closed 4H candle (forex grid): continuation or reversal closure; else none",
                 "bullish: bar trades below the swing low and closes back above it, order flow bullish; bearish mirrored",
                 "first sweep of each swing only; enter next M1 open; stop at the sweep bar extreme; target latest confirmed opposite swing (must be beyond the close)"]
        params.update({"order_flow": "4H previous-candle engine", "grid4h": "forex"})
        src.update({"order_flow": "method_spec: §2.3 previous-candle engine (continuation / reversal closure)",
                    "grid4h": "session_window_fit: forex grid is the gold default (carried as a knob)"})
        notes = "PD-array preference ('I prefer these to occur within PD arrays') not applied: a preference, not a condition."
    else:
        rules = ["15m bars; latest confirmed 2/2 swing low/high",
                 "bullish: a bar trades below the swing low; a bullish 3-bar FVG prints within that bar + next 3 before any lower low",
                 "enter at the FVG bar close (next M1 open); stop at the lowest low since the sweep; target latest confirmed swing high at the sweep",
                 "first sweep of each swing only; no order-flow condition; bearish mirrored"]
        params.update({"fvg_window": N_FVG})
        src.update({"fvg_window": "threshold_fits: displacement N-window N=4"})
        notes = "Variant reading: 'His preferred form of it is a sweep of a short-term high or low followed by a fair value gap.'"
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars")})
    print(p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
