"""no-draw-no-trade (contested, guest). Two readings, each a no-trade gate on the baseline
1h CISD book (claim '+': allowed trades beat the blocked ones).

'Clear' draw / expansion read is given a mechanical test only by Jokerszn and Nick: a close
THROUGH the framing level (a daily close through a framing PD array / the opposing FVG).
The framing levels used here are the previous period's high and low (old highs/lows are
Jokerszn's liquidity objectives).

reading a (Rauf: monthly draw + weekly expansion read):
  clear monthly = the last completed month closed above the prior month's high or below its low;
  clear weekly  = the last completed week closed above the prior week's high or below its low;
  allowed = both clear.
reading b (Gene / Jokerszn / Nick: daily draw):
  allowed = the last completed trading day closed above the day-before's high or below its low
  (a directional daily close through a framing level); else 50/50 -> no trade.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE


def _clear(t, kind, m1, cov):
    last = cl.prior_hilo(t, kind, n_back=1, m1=m1, min_coverage=cov)
    prev = cl.prior_hilo(t, kind, n_back=2, m1=m1, min_coverage=cov)
    c = last["close"].to_numpy(float)
    ok = ~(np.isnan(c) | np.isnan(prev["high"].to_numpy(float)))
    clear = (c > prev["high"].to_numpy(float)) | (c < prev["low"].to_numpy(float))
    return clear, ok, pd.DatetimeIndex(last["available_at"])


def detect_a(m1):
    ev = cisd_book(m1)
    t = ev["decision_time"]
    cm, okm, am = _clear(t, "1M", m1, None)
    cw, okw, aw = _clear(t, "1W", m1, None)
    ev["allowed"] = cm & cw
    ev["gate_at"] = am.where(am > aw, aw) if len(ev) else am
    ev["month_key"] = am.strftime("%Y-%m") if len(ev) else pd.Series(dtype=str)
    ev = ev[okm & okw].reset_index(drop=True)
    return ev


def detect_b(m1):
    ev = cisd_book(m1)
    t = ev["decision_time"]
    cd, okd, ad = _clear(t, "1D", m1, 0.5)
    ev["allowed"] = cd
    ev["gate_at"] = ad
    ev = ev[okd].reset_index(drop=True)
    return ev


def show(res):
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(" ", k, res.get(k))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame("rg02b_nodraw_a_1hcisd", lambda: detect_a(cl.load_m1()))
        print("a:", len(ev), "events; allowed share", ev["allowed"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="100D")
        res = cl.gate_test(ev, "allowed", mask_available_at="gate_at", max_hold="10h",
                           claim="+", cluster="month_key")
        show(res)
        op = {"rules": [BASE_RULE,
                        "clear monthly draw = last completed month closed beyond the prior month's high/low",
                        "clear weekly expansion read = last completed week closed beyond the prior week's high/low",
                        "allowed = both clear; blocked = either missing (no trade)",
                        "CI clustered by the month of the gate's monthly input"],
              "params": {**BASE_PARAMS, "framing_levels": "previous period high/low",
                         "clear_test": "period close beyond framing level", "periods": "1M and 1W"}}
        src = {**BASE_SRC,
               "framing_levels": "corpus: JABOO4LYNjQ (liquidity objectives are old highs/lows); declared-before-run for the monthly/weekly scale",
               "clear_test": "corpus: JABOO4LYNjQ / G44VpidBD_U (a close through the framing array establishes direction)",
               "periods": "corpus: qFtfD09Vv3E 'if you don't have a clear draw on the monthly' + weekly expansion"}
        print(cl.write_result("no-draw-no-trade", "a", res, operationalization=op,
                              params_source=src, script=__file__, probe=probe,
                              notes="'clear' is undefined by Rauf; the close-through test is borrowed from the concept's other two sources."))
    if "b" in which:
        ev = cl.cache_frame("rg02b_nodraw_b_1hcisd", lambda: detect_b(cl.load_m1()))
        print("b:", len(ev), "events; allowed share", ev["allowed"].mean())
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        res = cl.gate_test(ev, "allowed", mask_available_at="gate_at", max_hold="10h", claim="+")
        show(res)
        op = {"rules": [BASE_RULE,
                        "clear daily draw = last completed trading day closed above the day-before's high or below its low",
                        "allowed = clear; blocked = close inside the prior range (50/50, no trade)"],
              "params": {**BASE_PARAMS, "framing_levels": "previous day high/low",
                         "clear_test": "daily close beyond framing level", "min_coverage": 0.5,
                         "day_open_hour": 18}}
        src = {**BASE_SRC,
               "framing_levels": "corpus: JABOO4LYNjQ (liquidity objectives are old highs/lows)",
               "clear_test": "corpus: JABOO4LYNjQ / G44VpidBD_U (a daily close through the framing array establishes direction)",
               "min_coverage": "declared-before-run: skip data-hole stub sessions (README trap 6)",
               "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
        print(cl.write_result("no-draw-no-trade", "b", res, operationalization=op,
                              params_source=src, script=__file__, probe=probe,
                              notes="'HTF objective reached -> neutral' clause not operationalised (objective undefined)."))
