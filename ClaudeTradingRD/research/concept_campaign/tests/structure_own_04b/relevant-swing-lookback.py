"""relevant-swing-lookback (structure, TTrades own voice, specified) — batch structure_own_04b.

Claim (HbOeD_JVens): only swing highs/lows inside the look-back window of THREE higher-timeframe
candles (current inclusive) are the relevant ones; on the hourly chart the HTF is daily, so the
window is three days. Older levels "can still be looked at but generally do not give the best
reactions". Measurable (yaml): reaction rate at relevant swings inside vs outside the window.

Gate test on the phase-3 rung-0 1h CISD book (series_open, 2/2 swings, max_wait 3, stop at the
protected swing, 2R, 10h hold, entry next M1 open after the confirming bar closes).
Baseline restricted to reversals whose extreme SWEPT at least one prior, confirmed, still-untaken
1h swing of the same side (three-candle fractal, method spec §1.1) formed within the last
20 trading days (outer bound, declared). Gate = at least one swept swing formed inside the
current + previous two trading days (the three-daily-candle window). Complement = the reversal
swept only older swings. claim '+': in-window sweeps give better control-adjusted R.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, swing_points, HOLD, CISD, RR

TF = "1h"
WINDOW_DAYS = 3        # three HTF (daily) candles incl. the current one
OUTER_DAYS = 20        # declared outer bound for "older" swings
SW = (1, 1)            # three-candle fractal


def detect(m1):
    b, ev, out = cisd_frame(m1, TF)
    if len(out) == 0:
        out["in_window"] = pd.Series(dtype=bool)
        return out
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    sw = swing_points(b[["high", "low"]], *SW)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    td = cl.trading_day(b.index)
    dc = pd.factorize(pd.Series(td.to_numpy()), sort=True)[0]
    first = {}
    for k, d in enumerate(dc):
        first.setdefault(d, k)
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    bull = out["direction"].to_numpy() == 1
    R = SW[1]
    valid = np.zeros(len(ev), bool)
    inw = np.zeros(len(ev), bool)
    for e, p in enumerate(pos):
        d = dc[p]
        if d - (OUTER_DAYS - 1) not in first:
            continue
        w_outer = first[d - (OUTER_DAYS - 1)]
        w_in = first[d - (WINDOW_DAYS - 1)]
        last_s = p - 1 - R                      # swing confirmed (right bar closed) before bar p
        if last_s < w_outer:
            continue
        if bull[e]:
            cand = np.flatnonzero(sl[w_outer:last_s + 1]) + w_outer
            swept = [s for s in cand if l[p] < l[s] and (p - s <= 1 or l[s + 1:p].min() >= l[s])]
        else:
            cand = np.flatnonzero(sh[w_outer:last_s + 1]) + w_outer
            swept = [s for s in cand if h[p] > h[s] and (p - s <= 1 or h[s + 1:p].max() <= h[s])]
        if not swept:
            continue
        valid[e] = True
        inw[e] = any(s >= w_in for s in swept)
    out["in_window"] = inw
    return out[valid].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"rsl_{TF}_w{WINDOW_DAYS}_o{OUTER_DAYS}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["in_window"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "in_window", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "baseline: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open; stop at the protected swing, 2R, 10h wall clock",
        "baseline kept only when the reversal extreme traded beyond >=1 confirmed, untaken same-side 1h three-candle swing formed within the last 20 trading days",
        "gate: at least one swept swing formed in the current or previous two trading days (18:00 NY roll) = the three-daily-candle look-back window",
        "claim: in-window reversals beat reversals that only swept older swings (control-adjusted R)"],
        "params": {"tf": TF, **CISD, "rr": RR, "max_hold": HOLD[TF], "window_days": WINDOW_DAYS,
                   "outer_days": OUTER_DAYS, "swing": "1/1 fractal"}}
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"window_days": "corpus: HbOeD_JVens 'I'm going to look back 3 days because that is my look back' (hourly chart -> three daily candles)",
                "outer_days": "declared-before-run: 20 trading days bounds the 'older levels' comparison arm",
                "swing": "method_spec: §1.1 swing point = three-candle fractal"})
    p = cl.write_result("relevant-swing-lookback", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"gate firing rate {float(ev['in_window'].mean()):.3f} of {len(ev)} sweep-reversals. "
                              "Only the hourly->daily pairing tested (daily->monthly gives too few CISDs). "
                              "The HTF-extreme preference inside the window is not applied.")
    print("wrote", p)
