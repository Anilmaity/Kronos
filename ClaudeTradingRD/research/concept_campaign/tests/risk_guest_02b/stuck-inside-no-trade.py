"""stuck-inside-no-trade (Alex's Options, guest, TheSTRAT): when price has taken neither the
high nor the low of the formation / previous range and trades inside it, stand aside.

Formation = the previous completed trading day's range (the 1D 'previous range'; a day that
has not yet taken either side is an in-progress Strat '1' / inside bar -- the concept's own
candle expression of the condition). Gate on the baseline 1h CISD book:
allowed = by the decision time the current trading day has already traded beyond PDH or PDL.
claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE


def detect(m1):
    ev = cisd_book(m1)
    t = ev["decision_time"]
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(t, "1D", m1=m1)
    ok = ~(np.isnan(pd_["high"].to_numpy(float)) | np.isnan(run["high"].to_numpy(float)))
    taken = (run["high"].to_numpy(float) > pd_["high"].to_numpy(float)) | \
            (run["low"].to_numpy(float) < pd_["low"].to_numpy(float))
    ev["allowed"] = taken
    ev = ev[ok].reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_stuck_inside_1hcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; allowed share", ev["allowed"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [BASE_RULE,
                    "formation = previous completed trading day's high/low (prior_hilo 1D, min_coverage 0.5 skips stub sessions)",
                    "stuck = the current trading day's running high/low (M1 closed by the decision) has taken neither PDH nor PDL",
                    "allowed = at least one side taken by the decision time; blocked = stuck inside"],
          "params": {**BASE_PARAMS, "formation": "previous trading day range", "min_coverage": 0.5,
                     "day_open_hour": 18}}
    src = {**BASE_SRC,
           "formation": "declared-before-run: the concept's 'previous range'/'a timeframe going inside (a 1)' read at the 1D HTF it lists",
           "min_coverage": "declared-before-run: skip data-hole stub sessions (README trap 6)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result("stuck-inside-no-trade", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Drawn broadening formations are chart-reading; the daily inside-state is the concept's own mechanical expression (a '1').")
    print(p)
