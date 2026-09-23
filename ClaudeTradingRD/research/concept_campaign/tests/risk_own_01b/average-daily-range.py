"""risk_own_01b / average-daily-range (contested) — gate_test on the 15m rung-0 CISD book.

Claim (+): entries taken while the day has NOT yet covered its expected daily range
beat entries taken after it has ("once the day has covered that band he stands aside").
  reading a: expected range = plain ADR(20) (mean H-L of the last 20 real days) —
             "I use average daily range. I think it's the same [as ATR]".
  reading b: expected range = the EXPANSION-day band (median H-L of the expansion
             candles among the last 20 days; he ignores quiet days) — "I'm just
             focusing on the expansion ones".
Params declared before the first run (see PARAMS / SRC).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF = "15min"
LOOKBACK = 20
OPP_CUT = 1.0
MIN_N_M1 = 600


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr"]].copy()
    if ev.empty:
        return ev.assign(open_adr=pd.Series(dtype=bool), open_exp=pd.Series(dtype=bool))
    run = cl.running_hilo(ev["decision_time"], "1D", m1=m1)
    ref = asof_ref(daily_ref(m1, LOOKBACK, MIN_N_M1, OPP_CUT), ev["decision_time"])
    covered = run["high"].to_numpy() - run["low"].to_numpy()
    adr = ref["adr"].to_numpy(float)
    exb = ref["exp_band"].to_numpy(float)
    ok = np.isfinite(covered) & np.isfinite(adr) & np.isfinite(exb)
    ev = ev[ok].reset_index(drop=True)
    ev["day_covered"] = covered[ok]
    ev["adr20"] = adr[ok]
    ev["exp_band"] = exb[ok]
    ev["open_adr"] = ev["day_covered"] < ev["adr20"]
    ev["open_exp"] = ev["day_covered"] < ev["exp_band"]
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"adr_gate_{TF}_lb{LOOKBACK}_opp{OPP_CUT}_n{MIN_N_M1}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev[["open_adr", "open_exp"]].mean().to_dict(),
          ev[["adr20", "exp_band"]].median().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    params = {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF], "adr_lookback_days": LOOKBACK,
              "expansion_cut_opp_over_body": OPP_CUT, "stub_day_min_n_m1": MIN_N_M1,
              "day_roll": "18:00 NY", "covered": "running trading-day high - low from M1 closed by decision",
              "grid4h": "n/a"}
    src = {"baseline_tf": "phase3: primary stack entry TF (README gate example)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "adr_lookback_days": "corpus: X4XSsv5CNqg / variants 'a daily chart of the instrument with at least the current month visible' -> ~20 trading days (declared-before-run)",
           "expansion_cut_opp_over_body": "threshold_fits: small wick / expansion candle opposing_run/|body| <= 1.0 (grade A)",
           "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6)",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "covered": "corpus: X4XSsv5CNqg 'we've already made a whole average daily range'",
           "grid4h": "declared-before-run: no 4h bars used"}
    for reading, col, band in (("a", "open_adr", "ADR(20) mean of H-L"),
                               ("b", "open_exp", "median H-L of expansion days in last 20")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
        show(res)
        op = {"rules": [f"baseline: 15m rung-0 CISD book (series_open, 2/2 swings, max_wait 3, stop protected swing, 2R, hold {HOLD[TF]})",
                        f"expected daily range = {band}, from completed trading days only (as of the decision)",
                        "gate (kept): day's range so far < expected range; complement: band already covered",
                        "claim +: entries while range budget remains beat entries after the band is covered"],
              "params": {**params, "band": band}}
        s2 = dict(src); s2["band"] = ("corpus: X4XSsv5CNqg 'I use average daily range'" if reading == "a"
                                      else "corpus: eIPM-D8RrSQ 'I'm just focusing on the expansion ones'")
        p = cl.write_result("average-daily-range", reading, res, operationalization=op,
                            params_source=s2, script=__file__, probe=probe,
                            notes=("the corpus downgrades rather than blocks; tested as the hard "
                                   "'stand aside once covered' rule. mask_available_at = decision "
                                   "time: both the running range and the completed-day band are "
                                   "known at the decision."))
        print("wrote", p)
