"""update_20261007 / dont-trade-after-expansion — NEW claim only (reading u1007a).

Source uW55Tuk-ngY (New York Open Live Q&A), on a C2 reversal day: "Early into candle
generally before ADR created near the open ... Those are the ideal things for a reversal
day" and "We've already made a lot of a daily range ... I would not be looking short here"
even though "the structure there is honestly perfect".

Book: 15m rung-0 CISD (same baseline as average-daily-range__a), restricted to REVERSAL-DAY
entries: at the decision the current trading day (18:00 NY roll) has already traded beyond
the prior day's extreme AGAINST the trade (short after running above PDH, long after running
below PDL) — the C2 sweep-and-reverse.
Gate (kept): the day's range so far < ADR(20); complement: the ADR is already made.
claim '+'. One reading: the source gives no % of ADR, so the literal "before ADR created"
(100%) is used; "near the open" has no number and is not separately gated.
The generic ADR gate on all CISD trades is average-daily-range__a; not retested here.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa  (cl, np, pd, cisd_book, daily_ref, asof_ref, show, BASE_*, HOLD*)

TF = "15min"
LOOKBACK = 20
MIN_N_M1 = 600
MIN_COV = 0.5


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr"]].copy()
    if ev.empty:
        return ev.assign(before_adr=pd.Series(dtype=bool))
    t = ev["decision_time"]
    run = cl.running_hilo(t, "1D", m1=m1)
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=MIN_COV)
    ref = asof_ref(daily_ref(m1, LOOKBACK, MIN_N_M1), t)
    rh, rl = run["high"].to_numpy(float), run["low"].to_numpy(float)
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    adr = ref["adr"].to_numpy(float)
    d = ev["direction"].to_numpy()
    ok = np.isfinite(rh) & np.isfinite(rl) & np.isfinite(pdh) & np.isfinite(pdl) & np.isfinite(adr)
    reversal = np.where(d == -1, rh > pdh, rl < pdl)
    keep = ok & reversal
    ev = ev[keep].reset_index(drop=True)
    ev["before_adr"] = ((rh - rl) < adr)[keep]
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"dtae_u1007a_{TF}_lb{LOOKBACK}_n{MIN_N_M1}_cov{MIN_COV}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev["before_adr"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "before_adr", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    show(res)
    params = {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF], "adr_lookback_days": LOOKBACK,
              "stub_day_min_n_m1": MIN_N_M1, "pdhl_min_coverage": MIN_COV, "adr_fraction": 1.0,
              "reversal_day": "day running high > PDH for shorts / running low < PDL for longs, at decision",
              "day_roll": "18:00 NY", "grid4h": "n/a"}
    src = {"baseline_tf": "phase3: primary stack entry TF (same book as average-daily-range__a)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "adr_lookback_days": "corpus: X4XSsv5CNqg ~current month of daily candles (as in average-daily-range__a; declared-before-run)",
           "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6)",
           "pdhl_min_coverage": "declared-before-run: README trap 6 min_coverage=0.5",
           "adr_fraction": "corpus: uW55Tuk-ngY 'Early into candle generally before ADR created near the open' (no % given -> literal 100%)",
           "reversal_day": "corpus: uW55Tuk-ngY 'C2 reversal ... Once we've already gone through the EQ, ran out some lows' (C2 = prior-day extreme taken, then reverse)",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "grid4h": "declared-before-run: no 4h bars used"}
    op = {"rules": [f"baseline: 15m rung-0 CISD book (series_open, 2/2, max_wait 3, stop protected swing, 2R, hold {HOLD[TF]})",
                    "reversal-day subset: at the decision the trading day has already traded beyond the prior day's extreme against the trade (short above PDH / long below PDL)",
                    "ADR = mean H-L of last 20 completed real days (as of decision); covered = running day high - low from M1 closed by decision",
                    "gate (kept): covered < ADR (entry before ADR created); complement: ADR already made",
                    "claim +: reversal-day entries before the ADR is made beat those after"],
          "params": params}
    p = cl.write_result("dont-trade-after-expansion", "u1007a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="New claim from uW55Tuk-ngY (reversal-day timing). 'near the open' and 'stop trading after target hit' not separately tested (no number / needs per-trader target).")
    print("wrote", p)
