"""risk_own_01b / trade-frequency-baseline (contested) — gate_test.

The concept is mostly a descriptive cadence (1-2 trades a week, 6-8 daily swing
setups a year). Its one outcome claim (Ben: executing only 1-2 a week gave his
highest win rate; measurable: 'expectancy of the marginal trade beyond the second
in a week') is tested as a gate on a mechanical book whose natural frequency is
close to his stated cadence: the 4h rung-0 CISD book (forex grid), ~3.9 signals a
week (his "one to two, occasionally three or four").
Kept = the signal is one of the first TWO of its trading week; complement = the
3rd and later ("the marginal trade beyond the second"). Claim +.
Descriptive part: the 1D CISD count per year is reported in notes (no test).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF = "4h"
CAP = 2


def week_key(t):
    td = cl.trading_day(pd.DatetimeIndex(t))
    sd = td + pd.Timedelta(days=1)
    return sd - pd.to_timedelta(sd.dayofweek, unit="D")


def detect(m1):
    ev, _, _ = cisd_book(m1, TF)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr"]].copy()
    if ev.empty:
        return ev.assign(first_two=pd.Series(dtype=bool))
    ev = ev.sort_values("decision_time", kind="stable").reset_index(drop=True)
    wk = week_key(ev["decision_time"])
    ev["week"] = wk
    ev["nth_in_week"] = ev.groupby("week").cumcount() + 1
    ev["first_two"] = ev["nth_in_week"] <= CAP
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"freq_{TF}_cap{CAP}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["first_two"].mean(), ev.groupby("week").size().describe().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "first_two", mask_available_at="decision_time", max_hold=HOLD[TF],
                       hold_basis="bars", claim="+")
    show(res)
    m1 = cl.load_m1()
    d_ev, _, _ = cisd_book(m1, "1D")
    yrs = (m1.index[-1] - m1.index[0]).days / 365.25
    per_year = len(d_ev) / yrs
    op = {"rules": ["baseline: 4h rung-0 CISD book, forex 4h grid (series_open, 2/2, max_wait 3, protected-swing stop, 2R, hold 40h in trading bars)",
                    "trading week = harness 1W convention (18:00 NY Sunday open)",
                    "kept: signal is 1st or 2nd of its week; complement: 3rd and later",
                    "claim +: the first two a week beat the marginal ones (control-adjusted)"],
          "params": {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF], "hold_basis": "bars",
                     "weekly_cap": CAP, "grid4h": "forex"}}
    src = {"baseline_tf": "corpus: xraklBJHW5k 'Normally, it's like one to two' (up to three or four) -> the rung-0 TF whose signal rate (~3.9/wk) matches; declared-before-run",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "hold_basis": "declared-before-run: a 40h wall-clock hold crosses weekends unequally (README trap 7)",
           "weekly_cap": "corpus: yRmKkR4CojU 'i'm only averaging about one to two trades a week'",
           "grid4h": "session_window_fit: forex grid (harness default)"}
    notes = (f"descriptive: the 1D rung-0 CISD fires {per_year:.1f}/yr on gold vs his 6-8/yr swing setups; "
             f"the 4h book fires {len(ev)/(yrs*52.18):.2f}/wk. Kept arm is early-week by construction "
             "(first two of the week), so day-of-week is confounded with the rule; that is the rule as stated.")
    p = cl.write_result("trade-frequency-baseline", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p, notes)
