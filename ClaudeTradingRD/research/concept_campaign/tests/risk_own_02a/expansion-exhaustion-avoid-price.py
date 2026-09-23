"""risk_own_02a / expansion-exhaustion-avoid-price (contested) — gate_test on the 15m rung-0 CISD book.

Claim (+): entries NOT taken after an expansion run in the same direction beat the
entries that chase it ("after three consecutive days of expansion he stops taking
trades in that direction ... further entries are chasing").
  expansion day   = completed real trading day whose opposing run (open -> extreme
                    against the close direction) / |body| <= 1.0 (threshold_fits small
                    wick / expansion candle, grade A); its direction = sign(close - open)
  streak          = number of consecutive expansion days of one direction ending with
                    the last completed real day (stub days skipped; not reset at the week)
  reading a: blocked = streak >= 3 and trade direction == streak direction
             ("Count consecutive expansion days. At three, stop taking new entries in that direction.")
  reading b: blocked = streak >= 2 and same direction
             ("after two days of expansion he is 'more so interested in waiting to see a new phase'")
  gate (kept) = not blocked; complement = the blocked entries.
The 'two very large days', 'HTF objective reached' and 'conflicting ideas' triggers are
not quantified in the corpus and are not tested here. Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

OPP_CUT = 1.0


def daily_streak(m1):
    d = real_days(m1)
    o, c, h, l_ = (d[k].to_numpy(float) for k in ("open", "close", "high", "low"))
    body = np.abs(c - o)
    opp = np.where(c >= o, o - l_, h - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        is_exp = (body > 0) & (opp / np.where(body > 0, body, np.nan) <= OPP_CUT)
    sgn = np.where(is_exp, np.sign(c - o), 0).astype(int)
    streak = np.zeros(len(d), int)
    for i in range(len(d)):
        if sgn[i] == 0:
            streak[i] = 0
        elif i > 0 and sgn[i - 1] == sgn[i]:
            streak[i] = streak[i - 1] + 1
        else:
            streak[i] = 1
    return pd.DataFrame({"streak": streak, "sdir": sgn}), d["close_time"]


def detect(m1):
    ev, _, _ = cisd_book(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    ev = ev[cols].copy()
    if ev.empty:
        return ev.assign(no_chase3=pd.Series(dtype=bool), no_chase2=pd.Series(dtype=bool))
    st, avail = daily_streak(m1)
    r = asof_rows(st, avail, ev["decision_time"])
    ok = np.isfinite(r["streak"].to_numpy())
    ev = ev[ok].reset_index(drop=True)
    s = r["streak"].to_numpy()[ok]
    same = ev["direction"].to_numpy() == r["sdir"].to_numpy()[ok]
    ev["streak"] = s
    ev["no_chase3"] = ~((s >= 3) & same)
    ev["no_chase2"] = ~((s >= 2) & same)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"exh_{TF}_opp{OPP_CUT}_n{MIN_N_M1}", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["no_chase3", "no_chase2"]].mean().to_dict(),
          ev["streak"].value_counts().sort_index().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    params = {**BASE_PARAMS, "expansion_cut_opp_over_body": OPP_CUT, "stub_day_min_n_m1": MIN_N_M1,
              "day_roll": "18:00 NY", "streak_reset": "any non-expansion or opposite-direction day; not at week boundary"}
    src = {**BASE_SRC,
           "expansion_cut_opp_over_body": "threshold_fits: small wick / expansion candle opposing_run/|body| <= 1.0 (grade A)",
           "stub_day_min_n_m1": MIN_N_M1_SRC,
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "streak_reset": "declared-before-run: corpus leaves the reset rule open ('Whether the three-day count resets on a single non-expansion day ... is not stated')"}
    for reading, col, k, q in (
            ("a", "no_chase3", 3, "corpus: expansion-exhaustion-avoid-price shorts_04 'After three consecutive days of expansion he stops taking trades in that direction'"),
            ("b", "no_chase2", 2, "corpus: sunday_sessions_live_q_a_03 'after two days of expansion he is more so interested in waiting to see a new phase'")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD, claim="+")
        show(res)
        op = {"rules": [BASE_RULE,
                        "expansion day: completed real day with opposing_run/|body| <= 1.0, direction sign(close-open)",
                        f"streak = consecutive same-direction expansion days ending at the last completed day",
                        f"blocked = streak >= {k} and trade direction == streak direction; gate = not blocked",
                        "claim +: non-chasing entries beat entries that chase the expansion run"],
              "params": {**params, "streak_min": k}}
        s2 = dict(src); s2["streak_min"] = q
        p = cl.write_result("expansion-exhaustion-avoid-price", reading, res, operationalization=op,
                            params_source=s2, script=__file__, probe=probe,
                            notes=("Only the day-count triggers are decidable; 'very large' days, "
                                   "HTF objective reached, stacked-FVG closure and the 'conflicting "
                                   "ideas' trigger are unquantified/discretionary and not tested. "
                                   "mask_available_at = decision time (completed days only)."))
        print("wrote", p)
