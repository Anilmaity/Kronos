"""swing-point-stop-hunt (guest: Ash Trades, unicorn step 2) -> gate_test.

Claim: the stop hunt of a three-candle swing point INTO a higher-timeframe area of
interest is the precondition of the setup - "without the stop hunt there is
nothing to displace away from and no setup"; bias opposite the hunted side.
Entry is not taken from the hunt itself, so it is tested as a GATE on a
displacement/reversal baseline book:

  baseline: 5m bare CISD (phase-3 locked config: series_open, 2/2 swing,
    max_wait 3, min_series 1), decide at the confirm-bar close, stop at the
    protected swing, 2R, hold 10 entry bars (50 min).
  gate hunt_into_aoi (bearish CISD, mirrored for bullish):
    * the CISD extreme bar's high trades ABOVE a 5m three-candle swing high
      (high above the candle before and after it; left=1, right=1) that was
      confirmed before the extreme bar and formed within the prior 12 bars (1h);
    * and that extreme bar's high reaches into a 1H bearish FVG (the HTF area of
      interest): the FVG's third 1H bar closed before the extreme bar started,
      it formed within the last 24 1H bars, and no closed 1H bar had traded to
      its far (top) edge before the extreme bar.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import fair_value_gaps

SWING_WIN = 12       # 5m bars
FVG_WIN = 24         # 1H bars


def detect(m1):
    b = cl.build_bars(m1, "5min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "hunt_into_aoi"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    n = len(b)
    # 3-candle swings, confirmed at k+1
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:])
    sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:])
    H = cl.build_bars(m1, "1h")
    fv = fair_value_gaps(H[["open", "high", "low", "close"]])
    Hc = pd.DatetimeIndex(H["close_time"])
    Hh, Hl = H["high"].to_numpy(), H["low"].to_numpy()
    fbull, fbear = fv["bullish_fvg"].to_numpy(), fv["bearish_fvg"].to_numpy()
    glo, ghi = fv["gap_low"].to_numpy(), fv["gap_high"].to_numpy()
    pos = {t: k for k, t in enumerate(b.index)}
    ej = np.array([pos[t] for t in ev["extreme_time"]])
    cj = np.array([pos[t] for t in ev["confirm_time"]])
    bull = (ev["direction"] == "bullish").to_numpy()
    te = b.index[ej]
    nH = np.searchsorted(Hc.as_unit("ns").asi8, pd.DatetimeIndex(te).as_unit("ns").asi8, side="right")  # H bars closed by te
    gate = np.zeros(len(ev), bool)
    for i in range(len(ev)):
        j = ej[i]
        lo = max(0, j - SWING_WIN)
        ks = np.arange(lo, j - 1)          # swing k confirmed at k+1 <= j-1 -> before extreme bar
        if bull[i]:
            ks = ks[sl[ks]]
            if not (len(ks) and (l[j] < l[ks]).any()):
                continue
        else:
            ks = ks[sh[ks]]
            if not (len(ks) and (h[j] > h[ks]).any()):
                continue
        m = nH[i]
        a0 = max(0, m - FVG_WIN)
        ok = False
        for q in range(a0, m):
            if bull[i]:
                if not fbull[q] or np.isnan(glo[q]):
                    continue
                # bullish FVG below: extreme low reaches into it (low <= top), never traded to bottom since
                if l[j] <= ghi[q] and (q + 1 >= m or Hl[q + 1:m].min() > glo[q]):
                    ok = True; break
            else:
                if not fbear[q] or np.isnan(ghi[q]):
                    continue
                if h[j] >= glo[q] and (q + 1 >= m or Hh[q + 1:m].max() < ghi[q]):
                    ok = True; break
        gate[i] = ok
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[cj])
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(bull, 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0,
                         "hunt_into_aoi": gate})


if __name__ == "__main__":
    ev = cl.cache_frame(f"stophunt_5m_cisd_sw{SWING_WIN}_fvg{FVG_WIN}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "gate rate", ev["hunt_into_aoi"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "hunt_into_aoi", mask_available_at="decision_time", max_hold="50min", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": ["baseline: 5m bare CISD (series_open, 2/2 swing, max_wait 3, min_series 1); decide at confirm close, enter next M1 open; stop protected swing; 2R; 50 min hold",
                    "gate: CISD extreme bar trades beyond a 5m three-candle swing (same side) confirmed before it within the prior 12 bars",
                    "AND the extreme bar reaches into a 1H FVG of the opposing side (bearish FVG above for a bearish setup) formed within 24 closed 1H bars and not traded to its far edge before the extreme bar",
                    "gate verdict known at the extreme bar's close <= decision time"],
          "params": {"entry_tf": "5min", "htf": "1h", "level_rule": "series_open", "swing_cisd": "2/2",
                     "max_wait": 3, "min_series": 1, "rr": 2.0, "max_hold": "50min",
                     "swing_hunt": "1/1", "swing_window_bars": SWING_WIN, "aoi": "1H FVG",
                     "fvg_window_1h": FVG_WIN}}
    src = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config; 5m/1H primary stack, hold = 10 entry bars)"
           for k in ("entry_tf", "htf", "level_rule", "swing_cisd", "max_wait", "min_series", "rr", "max_hold")}
    src["swing_hunt"] = "corpus: zXtJSSkiNmo strict three-candle swing (higher than the candle before and after)"
    src["swing_window_bars"] = "declared-before-run: the hunted swing is local - within the prior hour of 5m bars"
    src["aoi"] = "declared-before-run: yaml leaves the HTF area of interest undefined; the unicorn sequence it belongs to uses FVG/breaker arrays -> 1H FVG"
    src["fvg_window_1h"] = "declared-before-run: one day of 1H bars"
    p = cl.write_result("swing-point-stop-hunt", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Tested as the unicorn's precondition gate on a displacement (CISD) baseline, since the concept sets no entry of its own.")
    print(p)
