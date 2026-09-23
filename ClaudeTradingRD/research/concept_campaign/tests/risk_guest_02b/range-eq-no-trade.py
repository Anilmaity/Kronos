"""range-eq-no-trade (Jokerszn, guest): never trade at the EQ (50%) of a dealing range.

Dealing range = previous completed trading day's high/low (1D HTF listed by the concept).
Baseline = bare 15m CISD book (the concept's LTF; phase-3 locked config, 150min hold).
blocked = the decision close sits within +/-10% of range of the 0.5 (0.40-0.60 of the range);
allowed = the rest. claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE

BAND = 0.10


def detect(m1):
    ev = cisd_book(m1, "15min")
    t = ev["decision_time"]
    r = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    hi, lo = r["high"].to_numpy(float), r["low"].to_numpy(float)
    ok = ~np.isnan(hi) & (hi > lo)
    pos = (ev["entry_ref"].to_numpy(float) - lo) / np.where(ok, hi - lo, np.nan)
    ev["range_pos"] = pos
    ev["allowed"] = ~((pos >= 0.5 - BAND) & (pos <= 0.5 + BAND))
    ev = ev[ok].reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_rangeeq_15mcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; allowed share", ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="150min", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    params = {**BASE_PARAMS, "baseline_tf": "15min", "max_hold": "150min",
              "dealing_range": "previous trading day high/low", "eq_band": BAND,
              "min_coverage": 0.5, "day_open_hour": 18}
    op = {"rules": ["baseline book: phase-3 bare 15m CISD (series_open, 2/2 swings, max_wait 3), stop at protected swing, 2R, 150min hold",
                    "dealing range = previous completed trading day's high/low (prior_hilo 1D, min_coverage 0.5)",
                    "location = (decision close - PDL)/(PDH - PDL)",
                    "blocked = location within 0.40-0.60 (the EQ +/- 10% of range); allowed = elsewhere incl. outside the range"],
          "params": params}
    src = {**BASE_SRC,
           "baseline_tf": "phase3: primary stack entry TF (15m); concept LTF list 15m/5m",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "dealing_range": "declared-before-run: the 1D range, the concept's first-listed HTF",
           "eq_band": "declared-before-run: 'near' the EQ unquantified in corpus; +/-0.10 of range",
           "min_coverage": "declared-before-run: skip data-hole stub sessions (README trap 6)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result("range-eq-no-trade", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe)
    print(p)
