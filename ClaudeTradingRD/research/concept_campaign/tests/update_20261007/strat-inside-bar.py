"""strat-inside-bar (TTrades update 2026-10-07), the new own-voice claim only.

Source GRc5FVB5tdg (NY open live Q&A): "where are we on the monthly? Like we're just inside
bar inside bar. So, it's more consolidation. So, I favor a reversion back into the range um
over breakouts." He says it while trading intraday. The breakout he is fading is a session
low taken into a target, not the monthly range.

The prior reading (guest/STRAT: trade the break of a daily inside bar, NULL) is untouched.
This script tests the monthly regime, which is the part that is new: in that state, does a
reversion back into the range beat the breakout more than it does outside the state?

Book (every trading day): the first M1 break of the prior session's high (or low). Fade it
back into the range: target = the prior session's midpoint (EQ), stop = the same half-range
beyond the broken level. That makes it a symmetric race of reversion against breakout.
Gate = the monthly state, read at the break bar's close. gate_test, claim '+': the
control-adjusted R in the state beats the complement.

Readings. "Inside bar inside bar" leaves open which two candles are meant:
  u1007a  the draft's own rule. The last completed month sits inside the month before it,
          AND the current month's running high/low (M1 closed by the decision) is still
          inside the last completed month.
  u1007b  two COMPLETED months, each inside its predecessor. This never happens once in
          2016-01 to 2026-07 (n=0), so it is written UNTESTABLE.

Vault-aware re-run (AUDIT 2026-10-07). detect() and every test setting are unchanged from the
first run, so the frame fingerprint and hyp_key are the same and the re-run adds no
multiplicity. Checked against the vault's Backtest Methodology Traps and the Concept Campaign
2026-09-23 lessons:
  T1 geometry: the book is a symmetric race with no cushion, and the comparison is gated vs
     complement (both arms use the same rule) on control-adjusted R. Never a raw win rate.
  T2 exits on M1, stop-first ties: harness. Ties are reported (both arms ~0.04%).
  T3 label=left: decision = break bar index + 1 min (its close); entry next M1 open.
  T4 regime-matched control: harness +/-30 days, plus ctrl_tod_tol_min=30.
  T6 power before interpretation: state months are counted BEFORE the test (pre_power()).
     About 20 single-inside months in 10.5 yr means the gated arm cannot reach n_eff 200.
  T7 never-evaluated != passed: non-contiguous months are dropped, never set False. The
     firing rate is reported.
  T8 certified span only (2016+). Levels are scale-free (prior-session range), not dollars.
  T9 in-progress HTF bar: months M-1/M-2 are completed. The current month is a running hi/lo
     over M1 closed by the decision. The symmetric probe covers it.
  L1 stop placement / L2 spread: same placement in both arms. Stops are half a daily range,
     so spread is negligible.
  L3 volatility: inside months are quiet months. The gate diff is only partly protected
     (+/-30 d control), so the in-state/complement range ratio is printed and disclosed.
  Not a repeat: the prior guest reading (daily inside-bar breakout) and no-shorting-below-lows
  (a CISD chasing gate) test different books. Neither conditions on the monthly state.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "strat-inside-bar"
MIN_BARS = 600          # prior session must be a real session, not a data-hole stub


def _month_frame(m1):
    """Per-M1 month code (calendar month of the session date), plus month hi/lo."""
    mkey = cl.session_date(m1.index).to_period("M")
    mcode, muniq = pd.factorize(mkey, sort=True)
    hi = m1["high"].to_numpy(float)
    lo = m1["low"].to_numpy(float)
    g = pd.Series(hi).groupby(mcode)
    mhi = g.max().to_numpy()
    mlo = pd.Series(lo).groupby(mcode).min().to_numpy()
    run_hi = g.cummax().to_numpy()
    run_lo = pd.Series(lo).groupby(mcode).cummin().to_numpy()
    ords = np.array([p.year * 12 + p.month - 1 for p in muniq])
    return mcode, muniq, mhi, mlo, run_hi, run_lo, ords


def detect(m1):
    idx = m1.index
    hi = m1["high"].to_numpy(float)
    lo = m1["low"].to_numpy(float)
    # days: trading day rolling 18:00 NY
    dcode, _ = pd.factorize(cl.trading_day(idx), sort=True)
    dn = np.bincount(dcode)
    dhi = pd.Series(hi).groupby(dcode).max().to_numpy()
    dlo = pd.Series(lo).groupby(dcode).min().to_numpy()
    pc = dcode - 1                                   # prior session (completed)
    okp = pc >= 0
    pci = np.clip(pc, 0, None)
    okp &= dn[pci] > MIN_BARS
    pdh = np.where(okp, dhi[pci], np.nan)
    pdl = np.where(okp, dlo[pci], np.nan)
    up = okp & (hi > pdh)
    dn_ = okp & (lo < pdl)
    first_up = up & (pd.Series(up).groupby(dcode).cumsum().to_numpy() == 1)
    first_dn = dn_ & (pd.Series(dn_).groupby(dcode).cumsum().to_numpy() == 1)
    both = first_up & first_dn                      # one bar breaks both sides: order unknown
    first_up &= ~both
    first_dn &= ~both
    # monthly state, read at the break bar's close
    mcode, _, mhi, mlo, run_hi, run_lo, ords = _month_frame(m1)
    m_1, m_2 = mcode - 1, mcode - 2
    okm = m_2 >= 0
    a1, a2 = np.clip(m_1, 0, None), np.clip(m_2, 0, None)
    contiguous = okm & (ords[mcode] - ords[a2] == 2)  # no missing month in between
    prev_inside = (mhi[a1] <= mhi[a2]) & (mlo[a1] >= mlo[a2])
    cur_inside = (run_hi <= mhi[a1]) & (run_lo >= mlo[a1])
    cond = prev_inside & cur_inside
    rows = []
    for sel, d in ((first_up, -1), (first_dn, 1)):
        k = sel & contiguous
        mid = (pdh[k] + pdl[k]) / 2.0
        half = (pdh[k] - pdl[k]) / 2.0
        lvl = pdh[k] if d == -1 else pdl[k]
        t = idx[k] + pd.Timedelta(minutes=1)
        rows.append(pd.DataFrame({
            "decision_time": t, "available_at": t, "direction": d,
            "stop_px": lvl - d * half, "target_px": mid,
            "in_state": cond[k], "month": ords[mcode[k]]}))
    ev = pd.concat(rows, ignore_index=True)
    ev = ev[np.isfinite(ev["stop_px"]) & (ev["stop_px"] != ev["target_px"])]
    return ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


def completed_double_inside(m1):
    mcode, muniq, mhi, mlo, *_ = _month_frame(m1)
    # the data ends 2026-07-23: the last month is in progress, not a completed candle
    muniq, mhi, mlo = muniq[:-1], mhi[:-1], mlo[:-1]
    ins = np.zeros(len(mhi), bool)
    ins[1:] = (mhi[1:] <= mhi[:-1]) & (mlo[1:] >= mlo[:-1])
    dbl = np.zeros(len(mhi), bool)
    dbl[1:] = ins[1:] & ins[:-1]
    return [str(p) for p in muniq[ins]], [str(p) for p in muniq[dbl]], len(mhi)


QUOTES = {
    "state": "corpus: GRc5FVB5tdg 'Like we're just inside bar inside bar. So, it's more consolidation.'",
    "prediction": "corpus: GRc5FVB5tdg 'So, I favor a reversion back into the range um over breakouts.'",
}


def run_a():
    ev = cl.cache_frame(f"{CID}_u1007a_pdbreak_monthly_state", lambda: detect(cl.load_m1()))
    # T6: power before interpretation (counted before the test is called)
    st = ev["in_state"].to_numpy(bool)
    n_state_months = ev.loc[st, "month"].nunique()
    # L3: the state selects quiet months; prior-session range relative to price, state vs rest
    rel = (2 * (ev["stop_px"] - ev["target_px"]).abs() / ev["target_px"]).to_numpy()
    vol_ratio = float(np.median(rel[st]) / np.median(rel[~st]))
    print("events", len(ev), "in_state", int(st.sum()), "months in state", n_state_months,
          "median rel range state/rest", round(vol_ratio, 3))
    pre = (f"vault audit 2026-10-07: pre-test power: {int(st.sum())} in-state events in "
           f"{n_state_months} state months (n_eff floor 200 is unreachable on 2016-2026); "
           f"L3 volatility: median prior-session range/price in state / complement = {vol_ratio:.2f}. ")
    probe = cl.probe_lookahead(detect, ev, lookback="100D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "in_state", mask_available_at="decision_time", max_hold="23h",
                       hold_basis="bars", ctrl_tod_tol_min=30, cluster="month", claim="+")
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi",
                                   "p", "mde", "ci_method", "dependence", "ties", "exposure_bars")})
    op = {"rules": [
        "range = the prior NY trading session (18:00 roll) high/low; prior session must have > "
        f"{MIN_BARS} M1 bars",
        "event = the first M1 bar of the trading day whose high > PDH (short) or low < PDL (long); "
        "a bar breaking both sides is dropped; decide at that bar's close, enter next M1 open",
        "reversion trade back into the range: target = prior-session midpoint (EQ); stop = the broken "
        "level +/- half the prior range (symmetric race: reversion to EQ vs breakout by the same "
        "distance); hold one trading day of M1 bars",
        "gate in_state (reading u1007a): last completed calendar month (session dates) inside the "
        "month before it (high <=, low >=) AND the current month's running high/low over M1 bars "
        "closed by the decision still inside the last completed month",
        "gate_test claim '+': control-adjusted R in the state > complement; cluster = session month "
        "(the state is assigned per month)"],
        "params": {"range": "prior session (PDH/PDL)", "event": "first break per side per day",
                   "target": "prior-session midpoint", "stop": "broken level + half prior range",
                   "state": "prev month inside + current month so far inside",
                   "inside": "wick range, non-strict (<=, >=)", "max_hold": "23h",
                   "hold_basis": "bars", "ctrl_tod_tol_min": 30, "cluster": "session month",
                   "day_open_hour": 18, "min_session_bars": MIN_BARS, "grid4h": "n/a (1D/1M)"}}
    src = {"range": "declared-before-run: the source fades a taken intraday low back 'into the range' "
                    "(GRc5FVB5tdg 'favoring a retracement or reversal back into the range'); the "
                    "prior session's range is the method's daily range",
           "event": "corpus: GRc5FVB5tdg 'not at the low after we take out the target' (the breakout = "
                    "a session extreme taken); first break per side declared-before-run",
           "target": "corpus: GRc5FVB5tdg 'kind of respect around the EQ of this area' (EQ = midpoint)",
           "stop": "declared-before-run: equal distance beyond the broken level, so the race is "
                   "reversion vs breakout with no built-in cushion",
           "state": QUOTES["state"] + "; draft rule 'If the current monthly candle (and the prior) "
                    "are inside bars'",
           "inside": "corpus: library strat-inside-bar 'inside_bar := candle.high <= prev.high AND "
                     "candle.low >= prev.low'",
           "max_hold": "declared-before-run: one trading day, as the prior strat-inside-bar reading",
           "hold_basis": "declared-before-run: trading-time hold across halts/weekends (README trap 7)",
           "ctrl_tod_tol_min": "declared-before-run: breaks cluster at session opens; concept is not "
                               "about timing (README trap 9)",
           "cluster": "declared-before-run: the state is a per-month assignment (README trap 11)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "min_session_bars": "declared-before-run: harness example_rate stub-day filter n_m1 > 600",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, "u1007a", res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=pre + "TTrades update 2026-10-07 (own voice, GRc5FVB5tdg): the monthly "
                              "inside-inside state as a gate on daily-range reversion. Prior guest "
                              "reading (daily inside-bar breakout trade) untouched. "
                              + QUOTES["prediction"])
    print(p)


def run_b():
    ins, dbl, nm = completed_double_inside(cl.load_m1())
    print("months", nm, "inside", len(ins), "completed double-inside", len(dbl), dbl)
    if dbl:
        raise SystemExit("completed double-inside months exist; reading b needs a real test")
    reason = (f"n=0: no two consecutive COMPLETED monthly inside bars in the certified span "
              f"({nm} completed session months 2016-01..2026-06, {len(ins)} single inside months, 0 inside-"
              f"after-inside); pre-2016 data is disqualified (calendar change)")
    op = {"rules": ["state = month M-1 inside M-2 AND month M-2 inside M-3, both completed "
                    "(calendar month of session dates, high <= and low >= the predecessor)",
                    "would gate the same daily-range reversion book as reading u1007a",
                    "not runnable: " + reason],
          "params": {"state": "two completed inside months", "inside": "wick range, non-strict"}}
    src = {"state": QUOTES["state"] + " (read as two completed monthly candles)",
           "inside": "corpus: library strat-inside-bar 'inside_bar := candle.high <= prev.high AND "
                     "candle.low >= prev.low'"}
    p = cl.write_untestable(CID, reason, reading="u1007b", operationalization=op,
                            params_source=src, script=__file__,
                            notes="Companion reading to u1007a. Inside months: " + ", ".join(ins))
    print(p)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("u1007b", "all"):
        run_b()
    if which in ("u1007a", "all"):
        run_a()
