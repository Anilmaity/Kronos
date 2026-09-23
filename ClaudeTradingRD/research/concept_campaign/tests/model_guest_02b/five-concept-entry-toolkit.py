"""five-concept-entry-toolkit (guest: Finessee_Fx, eK_6wgNpNh0).

The method is a scope rule with an execution: "entries come from one of the
arrays; exits come from an opposing array (enter on a bullish order block, exit
at an old high)"; stop "beyond the array used for entry"; no projections, no
structure-shift trigger (he excludes MSS). Operationalised with the array the
guest equates across four names - the fair value gap (= liquidity void = BISI/SIBI):

  array   = 1h three-candle FVG (wick-to-wick), known at its third candle's close
  entry   = the first return into the gap (first M1 that trades into it, within
            120 1h bars), decided at that M1's close if it is still inside/above
            the far edge; enter at the next M1 open, in the gap's direction
  stop    = beyond the array: the gap's far edge
  target  = the opposing array "old high/low": the most recent confirmed 1h
            2/2 swing high (low) above (below) the entry price at the decision
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
import concept_lab as cl
from detectors.primitives import fair_value_gaps, swing_points

TF = "1h"
MAX_AGE = 120
MAX_HOLD = "10h"
TGT_LOOKBACK = pd.Timedelta("20D")


def detect(m1):
    H = cl.build_bars(m1, TF)
    H = H[H["n_m1"] > 0]
    n = len(H)
    g = fair_value_gaps(H)
    hi, lo = H["high"].to_numpy(), H["low"].to_numpy()
    first = pd.DatetimeIndex(H["first_m1"])
    last = pd.DatetimeIndex(H["last_m1"])
    ctime = pd.DatetimeIndex(H["close_time"])
    sw = swing_points(H, 2, 2)
    conf_pos = np.full(n, -1)
    pos = np.arange(n)
    conf_pos[(sw.swing_high | sw.swing_low).to_numpy() & (pos + 2 < n)] = \
        pos[(sw.swing_high | sw.swing_low).to_numpy() & (pos + 2 < n)] + 2
    sh_idx = np.where(sw.swing_high.to_numpy() & (conf_pos >= 0))[0]
    sl_idx = np.where(sw.swing_low.to_numpy() & (conf_pos >= 0))[0]
    sh_avail = ctime[conf_pos[sh_idx]] if len(sh_idx) else pd.DatetimeIndex([], tz="UTC")
    sl_avail = ctime[conf_pos[sl_idx]] if len(sl_idx) else pd.DatetimeIndex([], tz="UTC")

    m1t = m1.index
    m1l, m1h, m1c = m1["low"].to_numpy(), m1["high"].to_numpy(), m1["close"].to_numpy()
    pad = np.full(MAX_AGE, np.nan)
    Lw = sliding_window_view(np.concatenate([lo, pad]), MAX_AGE + 1)[:n, 1:]
    Hw = sliding_window_view(np.concatenate([hi, pad]), MAX_AGE + 1)[:n, 1:]
    rows = []
    for bull in (True, False):
        gi = np.where(g["bullish_fvg" if bull else "bearish_fvg"].to_numpy())[0]
        if not len(gi):
            continue
        ghi, glo = g["gap_high"].to_numpy()[gi], g["gap_low"].to_numpy()[gi]
        if bull:
            hitm = Lw[gi] <= ghi[:, None]
        else:
            hitm = Hw[gi] >= glo[:, None]
        has = hitm.any(axis=1)
        k = np.argmax(hitm, axis=1) + 1
        for a, i in enumerate(gi):
            if not has[a]:
                continue
            j = i + k[a]
            s = m1t.searchsorted(first[j])
            e = m1t.searchsorted(last[j], side="right")
            if bull:
                w = np.where(m1l[s:e] <= ghi[a])[0]
            else:
                w = np.where(m1h[s:e] >= glo[a])[0]
            if not len(w):
                continue
            q = s + w[0]
            cl_px = m1c[q]
            if bull and cl_px <= glo[a]:
                continue
            if (not bull) and cl_px >= ghi[a]:
                continue
            dt = m1t[q] + pd.Timedelta("1min")
            # most recent confirmed opposing swing beyond the close
            if bull:
                idxs, av, px = sh_idx, sh_avail, hi
            else:
                idxs, av, px = sl_idx, sl_avail, lo
            cand = np.where((av <= dt) & (av > dt - TGT_LOOKBACK))[0]
            tgt = np.nan
            for c in cand[::-1]:
                v = px[idxs[c]]
                if (bull and v > cl_px) or ((not bull) and v < cl_px):
                    tgt = v
                    break
            if np.isnan(tgt):
                continue
            rows.append((dt, 1 if bull else -1, glo[a] if bull else ghi[a], tgt, ctime[i]))
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                     "gap_time"])
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"fct_fvg_{TF}_{MAX_AGE}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "array: 1h three-candle FVG (bull: low[i] > high[i-2]); known at bar i close",
        "entry: first M1 that trades back into the gap within the next 120 1h bars; decide "
        "at that M1's close if it has not closed beyond the far edge; enter next M1 open "
        "in the gap's direction",
        "stop: the gap's far edge (beyond the array)",
        "target: most recent 1h 2/2 swing high (low), confirmed by the decision, beyond the "
        "decision close (searched back 20 days) = the opposing 'old high/low'; no projections",
        "exit after 10h"],
        "params": {"tf": TF, "max_age_bars": MAX_AGE, "swing": "2/2", "max_hold": MAX_HOLD,
                   "target_lookback": "20D"}}
    src = {"tf": "declared-before-run: 1h from the concept's ltf list (1M..1m 'every timeframe')",
           "max_age_bars": "declared-before-run: a gap stays live 5 days of 1h bars",
           "swing": "phase3: 2/2 fractal swing",
           "target_lookback": "declared-before-run: old highs/lows searched back 20 days",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    print(cl.write_result("five-concept-entry-toolkit", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Tested with the FVG array (the one he names four ways); order "
                                "blocks/breakers use the same entry/exit logic and are covered "
                                "by their own concept tests."))
