"""timeframe-alignment-pairs, update_20261007_live_05 (TTrades, 4rNC3QXxC20 New York Open Live Q&A).

Prior readings a (1H->5m) / b (4H->15m) alignment gates are untouched. New claims only:
  "if you have to work a 9 to5, the daily and hourly fractal ... if you're off work trading the
   4 hour and 15 ... You don't really miss moves ... You really only miss moves if you don't
   trade C2 in New York."
  "if I'm going to be trading overnight session, I just use the 15-minute because it's kind of
   sloppy [lower]"
The schedule choice (job vs. off work) is a lifestyle allocation, not a price claim; it is
not scored. Two pre-declared readings, one per remaining price claim:
  u1007a  gate_test on the 4H/15m book: entries taken in the New York 4H candle (forex grid
          09:00-13:00 NY) after that candle has swept the prior 4H candle's extreme against
          the trade (= trading C2 in NY) beat the rest of the 4H/15m book.
  u1007b  trade_test: 15m CISD entries decided in the overnight session (20:00-05:00 NY =
          harness asia start -> london end) beat a matched random entry at the same NY clock.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import PHASE3, cisd_book, cl, np, pd, summary  # noqa: E402

CID = "timeframe-alignment-pairs"
HOLD = "150min"
SRC_VIDEO = "corpus: 4rNC3QXxC20"


def detect_a(m1):
    ev = cisd_book(m1, "15min").drop(columns=["extreme_time", "extreme_price"])
    H = cl.build_bars(m1, "4h", grid4h="forex")
    B = cl.build_bars(m1, "15min", grid4h="forex")
    hs = cl.data.utc_ns(pd.DatetimeIndex(H.index))
    hlo, hhi = H["low"].to_numpy(float), H["high"].to_numpy(float)
    bkey = np.searchsorted(hs, cl.data.utc_ns(pd.DatetimeIndex(B.index)), side="right") - 1
    k_s = pd.Series(bkey)
    blo = pd.Series(B["low"].to_numpy(float)).groupby(k_s).cummin().to_numpy()
    bhi = pd.Series(B["high"].to_numpy(float)).groupby(k_s).cummax().to_numpy()
    bct = cl.data.utc_ns(pd.DatetimeIndex(B["close_time"]))
    t = pd.DatetimeIndex(ev["decision_time"])
    last = t - pd.Timedelta(minutes=1)                      # inside the last closed 15m bar
    k = np.searchsorted(hs, cl.data.utc_ns(last), side="right") - 1   # current 4H candle
    pos = np.searchsorted(bct, cl.data.utc_ns(t), side="right") - 1    # last closed 15m bar
    ok = (k >= 1) & (pos >= 0)
    kc, pc = np.clip(k, 1, None), np.clip(pos, 0, None)
    ok &= bkey[pc] == kc
    plo, phi = hlo[kc - 1], hhi[kc - 1]                     # prior (completed) 4H candle = C1
    rlo, rhi = blo[pc], bhi[pc]                              # current 4H candle so far
    d = ev["direction"].to_numpy()
    swept = np.where(d == 1, rlo < plo, rhi > phi)
    ny = cl.in_window(last, "09:00", "13:00")
    ev["ny_c2"] = np.asarray(ok & swept & ny, dtype=bool)
    return ev


def detect_b(m1):
    ev = cisd_book(m1, "15min").drop(columns=["extreme_time", "extreme_price"])
    keep = cl.in_window(pd.DatetimeIndex(ev["decision_time"]) - pd.Timedelta(minutes=1),
                        "20:00", "05:00")
    return ev[np.asarray(keep)].reset_index(drop=True)


BASE_RULE = ("baseline: 15min bare CISD (series_open, swing 2/2, max_wait 3), decide at the "
             "confirming bar close, enter next M1 open, stop protected swing, 2R, 150min")
BASE_PARAMS = {"htf": "4h", "ltf": "15min", "grid4h": "forex", "level_rule": "series_open",
               "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": HOLD}
BASE_SRC = {"htf": f"{SRC_VIDEO} 'if you're off work trading the 4 hour and 15'",
            "ltf": f"{SRC_VIDEO} 'if you're off work trading the 4 hour and 15'",
            "grid4h": "session_window_fit: forex grid for gold (same as prior reading b)",
            "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
            "max_hold": "phase3: 10 entry-TF bars (§1.13)"}


def main():
    m1 = cl.load_m1()
    # reading u1007a
    ev = cl.cache_frame("tap_u1007a_nyc2_v1", lambda: detect_a(m1))
    probe = cl.probe_lookahead(detect_a, ev, lookback="15D")
    res = cl.gate_test(ev, "ny_c2", mask_available_at="decision_time", max_hold=HOLD)
    print("u1007a\n" + summary(res))
    op = {"rules": [BASE_RULE,
                    "gate (trading C2 in New York): decision falls in the NY 4H candle (forex grid "
                    "09:00-13:00 NY) and that candle's running low (long) / high (short) from closed "
                    "15m bars has already taken the prior completed 4H candle's low / high"],
          "params": {**BASE_PARAMS, "ny_c2_candle": "09:00-13:00 NY", "c2_def": "sweep of C1 extreme against trade"}}
    src = {**BASE_SRC,
           "ny_c2_candle": f"{SRC_VIDEO} 'You really only miss moves if you don't trade C2 in New York' "
                           "+ declared-before-run: the forex-grid 4H candle covering the NY AM session",
           "c2_def": "method_spec: C2 = candle that sweeps C1's extreme (fractal model); LTF CISD supplies the closure"}
    print(" wrote", cl.write_result(CID, "u1007a", res, operationalization=op, params_source=src,
                                    script=__file__, probe=probe))
    # reading u1007b
    evb = cl.cache_frame("tap_u1007b_overnight_v1", lambda: detect_b(m1))
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="15D")
    res_b = cl.trade_test(evb, max_hold=HOLD, ctrl_tod_tol_min=30)
    print("u1007b\n" + summary(res_b))
    op_b = {"rules": [BASE_RULE, "keep only decisions in the overnight session 20:00-05:00 NY"],
            "params": {**BASE_PARAMS, "overnight": "20:00-05:00 NY", "ctrl_tod_tol_min": 30}}
    src_b = {**BASE_SRC,
             "ltf": f"{SRC_VIDEO} 'if I'm going to be trading overnight session, I just use the 15-minute'",
             "overnight": "session_window_fit: harness SESSION_WINDOWS asia start (20:00) to london end (05:00)",
             "ctrl_tod_tol_min": "declared-before-run: trap 9, hold NY clock fixed so the test reads the "
                                 "15m entry, not overnight volatility"}
    print(" wrote", cl.write_result(CID, "u1007b", res_b, operationalization=op_b, params_source=src_b,
                                    script=__file__, probe=probe_b))


if __name__ == "__main__":
    main()
