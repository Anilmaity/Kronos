"""risk_own_02a / daily-range-budget — gate_test on the 15m rung-0 CISD book.

Claim (+): entries taken while the day still has budget beat entries taken in the
direction of the day's move once the bulk of the expected range is already made.
  expected range = median H-L of the last 3 completed real days (his worked example
                   reads three daily candles: 658 / 740 / 540 -> "around 500, 600")
  consumed       = running trading-day high - low (M1 closed by the decision) / expected
  day direction  = sign(price at decision - 18:00 NY day open)
  BLOCKED        = consumed >= 0.80 AND trade direction == day direction
  gate (kept)    = not blocked; complement = the blocked entries.
All params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

LOOKBACK = 3
BULK = 0.80


def detect(m1):
    ev, _, _ = cisd_book(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    ev = ev[cols + ["confirm_close"]].copy()
    if ev.empty:
        return ev[cols].assign(budget_left=pd.Series(dtype=bool))
    d = real_days(m1)
    rng = (d["high"] - d["low"]).rolling(LOOKBACK, min_periods=LOOKBACK).median()
    exp = asof_rows(pd.DataFrame({"exp": rng.to_numpy()}), d["close_time"],
                    ev["decision_time"])["exp"].to_numpy()
    run = cl.running_hilo(ev["decision_time"], "1D", m1=m1)
    covered = run["high"].to_numpy() - run["low"].to_numpy()
    op = cl.open_at(ev["decision_time"], "18:00", m1=m1)["price"].to_numpy(float)
    px = ev["confirm_close"].to_numpy(float)
    day_dir = np.sign(px - op)
    ok = np.isfinite(exp) & np.isfinite(covered) & np.isfinite(op) & (exp > 0)
    ev = ev[ok].reset_index(drop=True)
    cons = covered[ok] / exp[ok]
    blocked = (cons >= BULK) & (ev["direction"].to_numpy() == day_dir[ok])
    out = ev[cols].copy()
    out["consumed"] = cons
    out["budget_left"] = ~blocked
    return out


if __name__ == "__main__":
    ev = cl.cache_frame(f"drb_{TF}_lb{LOOKBACK}_bulk{BULK}_n{MIN_N_M1}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev["budget_left"].mean(), ev["consumed"].describe().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "budget_left", mask_available_at="decision_time",
                       max_hold=HOLD, claim="+")
    show(res)
    params = {**BASE_PARAMS, "expected_range": f"median H-L of last {LOOKBACK} completed real days",
              "lookback_days": LOOKBACK, "bulk_cut": BULK, "day_open": "18:00 NY",
              "stub_day_min_n_m1": MIN_N_M1,
              "covered": "running trading-day high-low from M1 closed by decision"}
    src = {**BASE_SRC,
           "expected_range": "corpus: 0AYGNc9czYc 'from the high to the low, 658 points ... 740 ... 540 ... around 600, 500, 600 points' (typical of the last few candles; median declared-before-run)",
           "lookback_days": "corpus: 0AYGNc9czYc worked example reads three daily candles",
           "bulk_cut": "declared-before-run: 'we're almost already there ... the bulk of this range has already been created' read as >= 80% of expected",
           "day_open": "session_window_fit: settled 18:00 NY daily roll",
           "stub_day_min_n_m1": MIN_N_M1_SRC,
           "covered": "corpus: 0AYGNc9czYc 'how far has this moved, right? It's moved quite a bit'"}
    op = {"rules": [BASE_RULE,
                    "expected range = median H-L of the last 3 completed real trading days (as of decision)",
                    "consumed = today's running H-L / expected; day direction = sign(price - 18:00 NY open)",
                    "blocked = consumed >= 0.80 and trade direction == day direction; gate = not blocked",
                    "claim +: entries with budget left beat same-direction entries after the bulk is made"],
          "params": params}
    p = cl.write_result("daily-range-budget", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("mask_available_at = decision time: running range, day open and "
                               "completed-day ranges are all known at the decision. Distinct from "
                               "average-daily-range (risk_own_01b): 3-day eyeballed budget and the "
                               "block applies only in the direction of the day's move."))
    print("wrote", p)
