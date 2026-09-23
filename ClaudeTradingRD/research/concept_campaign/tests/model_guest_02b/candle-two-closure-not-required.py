"""candle-two-closure-not-required (guest: GxTradez, J_EeS2_2CAM) - contested.

The guest relaxes the fractal model's C2-closure requirement on the daily and
4-hour. Two distinct readings, each a full trade (the relaxed swing is traded as
the fractal model trades a C2: stop at the swing extreme, 2R target):

 a  Variant B - "candle 3 confirming the reversal with a CISD": C2 takes C1's
    low (high) and does NOT close back inside (closes beyond C1's extreme); C3 then
    closes through the opening price of the opposing-candle series ending at C2
    (CISD, series_open reading). Enter at the C3 close, stop = the C2/C3 extreme.
 b  Variant A - "accept a lower-timeframe reversal inside candle 2": while the
    HTF C2 is still open (no HTF closure known), a lower-timeframe CISD forms
    whose protected swing is inside C2 and beyond C1's extreme. Enter at the LTF
    CISD close, stop = that protected swing. HTF/LTF pairs 4H/15m and 1D/1H (a 2/2-swing
    1H CISD cannot confirm inside one 4H candle: first attempt used 4H/1H + 1D/4H
    and produced zero 4H/1H events before any test was run).

Both pooled over the two HTFs the guest allows (1D, 4H forex grid).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

RR = 2.0
HOLD_BARS = 10
GRID = "forex"
PAIRS = (("4h", "15min"), ("1D", "1h"))
TFD = {"15min": pd.Timedelta("15min"), "1h": pd.Timedelta("1h"), "4h": pd.Timedelta("4h"),
       "1D": pd.Timedelta("1D")}


def _bars(m1, tf):
    b = cl.build_bars(m1, tf, grid4h=GRID)
    return b[b["n_m1"] > 0]


def detect_a(m1):
    out = []
    for tf in ("4h", "1D"):
        b = _bars(m1, tf)
        o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
        n = len(b)
        ct = pd.DatetimeIndex(b["close_time"])
        for i in range(2, n):
            for bull in (True, False):
                if bull:
                    c2 = l[i - 1] < l[i - 2] and c[i - 1] < l[i - 2]
                else:
                    c2 = h[i - 1] > h[i - 2] and c[i - 1] > h[i - 2]
                if not c2:
                    continue
                # opposing-candle series ending at C2 (max 10), its open
                j = i - 1
                lvl = o[i - 1]
                while j >= 0 and i - 1 - j < 10 and ((c[j] < o[j]) if bull else (c[j] > o[j])):
                    lvl = o[j]
                    j -= 1
                if bull and c[i] > lvl:
                    stop = min(l[i - 1], l[i])
                elif (not bull) and c[i] < lvl:
                    stop = max(h[i - 1], h[i])
                else:
                    continue
                if (bull and stop >= c[i]) or ((not bull) and stop <= c[i]):
                    continue
                out.append((ct[i], 1 if bull else -1, stop, tf, HOLD_BARS * TFD[tf]))
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "tf", "max_hold"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    return ev.sort_values(["decision_time", "tf"]).reset_index(drop=True)


def detect_b(m1):
    out = []
    for htf, ltf in PAIRS:
        H = _bars(m1, htf)
        L = _bars(m1, ltf)
        cz = cisd_events(L[["open", "high", "low", "close"]], level_rule="series_open",
                         left=2, right=2, max_wait=3, min_series=1)
        if cz.empty:
            continue
        t = pd.DatetimeIndex(L.loc[cz["confirm_time"], "close_time"])
        ext_first = pd.DatetimeIndex(L.loc[cz["extreme_time"], "first_m1"])
        hf = pd.DatetimeIndex(H["first_m1"])
        hc = pd.DatetimeIndex(H["close_time"])
        k = hf.searchsorted(t, side="left") - 1          # HTF bar whose first M1 < t
        good = k >= 1
        kk = np.where(good, k, 1)
        inside = good & (t < hc[kk]) & (ext_first >= hf[kk])   # C2 still open, swing inside it
        c1_lo = H["low"].to_numpy()[kk - 1]
        c1_hi = H["high"].to_numpy()[kk - 1]
        bull = (cz["direction"] == "bullish").to_numpy()
        px = cz["protected_swing"].to_numpy()
        beyond = np.where(bull, px < c1_lo, px > c1_hi)
        sel = inside & beyond
        if not sel.any():
            continue
        out.append(pd.DataFrame({
            "decision_time": t[sel], "direction": np.where(bull[sel], 1, -1),
            "stop_px": px[sel], "tf": f"{htf}/{ltf}",
            "max_hold": HOLD_BARS * TFD[ltf]}))
    if not out:
        return pd.DataFrame({"decision_time": pd.DatetimeIndex([], tz="UTC"),
                             "direction": pd.Series([], dtype=int),
                             "stop_px": pd.Series([], dtype=float), "tf": pd.Series([], dtype=object),
                             "max_hold": pd.Series([], dtype="timedelta64[ns]"),
                             "available_at": pd.DatetimeIndex([], tz="UTC"),
                             "rr": pd.Series([], dtype=float)})
    ev = pd.concat(out, ignore_index=True)
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    return ev.sort_values(["decision_time", "tf"]).reset_index(drop=True)


def report(res):
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(" ", k, res.get(k))


if __name__ == "__main__":
    common_src = {
        "rr": "method_spec §5.3: 2R is the floor / fixed target",
        "hold_bars": "phase3: 10 entry-TF bars (§1.13)",
        "grid4h": "session_window_fit / data.py: forex grid default for gold (carried as knob)",
        "htfs": "corpus: J_EeS2_2CAM 'Apply only on the daily and 4-hour timeframes'"}
    run_a = "b_only" not in sys.argv
    # ---- reading a
    if run_a:
        ev = cl.cache_frame("c2nr_a_c3cisd", lambda: detect_a(cl.load_m1()))
        print("a", len(ev), ev.tf.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="60D")
        res = cl.trade_test(ev)
        report(res)
        op = {"rules": [
            "HTF in {4H forex grid, 1D 18:00-NY roll}; C1=bar i-2, C2=bar i-1, C3=bar i",
            "bullish: C2 low < C1 low AND C2 close < C1 low (no C2 closure); mirror for bearish",
            "C3 closes above the open of the contiguous bearish-close series ending at C2 "
            "(<=10 candles; C2's own open if C2 closed up) = CISD, series_open reading",
            "enter next M1 open after C3 close; stop = min(C2 low, C3 low); target 2R; "
            "max hold 10 HTF bars (40h / 10D)"],
            "params": {"htfs": ["4h", "1D"], "cisd_level": "series_open", "max_series": 10,
                       "rr": RR, "hold_bars": HOLD_BARS, "grid4h": GRID}}
        src = dict(common_src, cisd_level="phase3: level_rule series_open (§1.8-1.13)",
                   max_series="phase3: cisd_events max_series default 10")
        print(cl.write_result("candle-two-closure-not-required", "a", res, operationalization=op,
                              params_source=src, script=__file__, probe=probe,
                              notes="Variant B: C3 CISD after a C2 that expanded through C1's "
                                    "extreme (no closure)."))
    # ---- reading b
    ev = cl.cache_frame("c2nr_b_ltfcisd", lambda: detect_b(cl.load_m1()))
    print("b", len(ev), ev.tf.value_counts().to_dict())
    probe = cl.probe_lookahead(detect_b, ev, lookback="60D")
    res = cl.trade_test(ev)
    report(res)
    op = {"rules": [
        "pairs HTF/LTF = 4H(forex)/15m and 1D/1H; LTF CISD = phase-3 config "
        "(series_open, 2/2 swing, max_wait 3)",
        "keep an LTF CISD only if it confirms while the HTF candle (C2) is still open, its "
        "protected swing formed inside that C2, and the swing is beyond C1's extreme "
        "(bullish: swing low < C1 low)",
        "enter next M1 open after the LTF confirm close; stop = protected swing; target 2R; "
        "max hold 10 LTF bars"],
        "params": {"pairs": ["4h/15min", "1D/1h"], "cisd_level": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": RR, "hold_bars": HOLD_BARS, "grid4h": GRID}}
    src = dict(common_src, pairs="corpus: J_EeS2_2CAM htf 1D/4H; ltf 1H/15m from the concept's "
                                 "timeframes: 4H->15m, 1D->1H so an LTF CISD fits inside one HTF "
                                 "candle (declared-before-run)",
               cisd_level="phase3: locked CISD config", swing="phase3: 2/2 fractal",
               max_wait="phase3: max_wait=3")
    print(cl.write_result("candle-two-closure-not-required", "b", res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Variant A: LTF reversal inside an unfinished HTF C2. Pairing fixed before "
                                "any test of b: 4H/1H cannot confirm a 2/2-swing CISD "
                                "inside one 4H candle (0 events), so the concept's own "
                                "ltf list is paired 4H->15m, 1D->1H."))
