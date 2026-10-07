"""pdh-pdl-continuation-adr-gate — update_20261007_edu_03, new concept (gate_test).

Source 3OIq9HmckH8 ("How to Use ADR with PDH / PDL — No More Fakeouts", ttrades voice).
Claim: after PDH (PDL) is taken, continuation is expected only if much of the ADR is
still unused (measured from the day's opposite extreme), an open target lies within it,
and the HTF target was not already taken on a late (candle 4) expansion day; otherwise
expect consolidation / retrace / reversal and wait for the next daily open.

Baseline book (both readings): every FIRST in-session take of the prior real day's high
(long) / low (short), decided at the close of the M1 bar that traded through it. Trade
= continuation in the break direction, a symmetric race of 0.5 x ADR each way from the
entry (rr 1), held to the trading-day close (17:00 NY). The symmetric race makes the
book volatility-neutral: a random-direction entry scores ~0 R whatever the day's
volatility, so 'big days stay big' (vault: volatility clusters; daily-range-budget
u1007a NEGATIVE) cannot pose as continuation.

u1007a: gate = the ADR clause alone: range used at the break <= 0.5 x ADR.
u1007b: gate = all three clauses: ADR clause AND an open prior daily high (low) beyond
        the break within the ADR projected from the day's low (high) AND NOT (late
        expansion day AND the HTF target = previous week high (low) already taken).

Every parameter declared before the first run; nothing was searched.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                  # noqa: E402

CID = "pdh-pdl-continuation-adr-gate"
ADR_DAYS = 14          # completed real days in the ADR mean
MIN_N_M1 = 600         # a day with fewer M1 bars is a data-hole stub, not a real day
USED_CUT = 0.5         # gate passes when range used <= this fraction of ADR
X_ADR = 0.5            # stop distance = target distance = X_ADR x ADR (rr 1)
TGT_LOOKBACK = 20      # real days searched for an open old high / low
LATE_N = 2             # prior consecutive expansion closes that make today 'candle 4'
TOD_TOL = 30           # control holds the NY clock within +/- 30 min
NY = "America/New_York"
COLS = ["decision_time", "available_at", "direction", "stop_dist", "rr", "max_hold",
        "adr", "frac_used", "has_target", "late", "htf_taken", "gate_adr", "gate_full"]


def _empty():
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) == 0:
        return _empty()
    idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    h = m1["high"].to_numpy(float)
    l = m1["low"].to_numpy(float)
    c = m1["close"].to_numpy(float)
    td = cl.trading_day(idx)                       # naive session-open date (18:00 roll)
    days, code = np.unique(td.asi8, return_inverse=True)
    nd = len(days)
    sh, sl = pd.Series(h), pd.Series(l)
    dh = sh.groupby(code).max().to_numpy()
    dl = sl.groupby(code).min().to_numpy()
    dc = pd.Series(c).groupby(code).last().to_numpy()
    nbar = np.bincount(code, minlength=nd)
    first_pos = np.searchsorted(code, np.arange(nd))
    run_hi = sh.groupby(code).cummax().to_numpy()   # day's extremes THROUGH each bar
    run_lo = sl.groupby(code).cummin().to_numpy()

    # ── per-day levels from COMPLETED real days strictly before the day ──
    rpos = np.flatnonzero(nbar >= MIN_N_M1)
    k = np.searchsorted(rpos, np.arange(nd), side="left") - 1
    need = max(ADR_DAYS, TGT_LOOKBACK, LATE_N + 1) - 1
    okd = k >= need
    kk = np.clip(k, 0, None)
    cs = np.concatenate([[0.0], np.cumsum((dh - dl)[rpos])]) if len(rpos) else np.zeros(1)
    adr = np.full(nd, np.nan)
    pdh = np.full(nd, np.nan)
    pdl = np.full(nd, np.nan)
    if len(rpos):
        adr[okd] = (cs[kk[okd] + 1] - cs[kk[okd] + 1 - ADR_DAYS]) / ADR_DAYS
        pdh[okd] = dh[rpos[kk[okd]]]
        pdl[okd] = dl[rpos[kk[okd]]]
    late_up = np.zeros(nd, bool)
    late_dn = np.zeros(nd, bool)
    win_start = np.zeros(nd, int)
    if len(rpos):
        up = np.ones(nd, bool)
        dn = np.ones(nd, bool)
        for m in range(LATE_N):                    # day r_m closed beyond day r_{m+1}
            a = rpos[np.clip(kk - m, 0, None)]
            b = rpos[np.clip(kk - m - 1, 0, None)]
            up &= dc[a] > dh[b]
            dn &= dc[a] < dl[b]
        late_up, late_dn = okd & up, okd & dn
        win_start = rpos[np.clip(kk - TGT_LOOKBACK + 1, 0, None)]

    # ── weeks (ISO week of the session date) for the HTF target ──
    sdate = td + pd.Timedelta(days=1)
    monday = (sdate - pd.to_timedelta(sdate.dayofweek, unit="D")).asi8
    _, wcode = np.unique(monday, return_inverse=True)
    wk_hi = sh.groupby(wcode).max().to_numpy()
    wk_lo = sl.groupby(wcode).min().to_numpy()
    wrun_hi = sh.groupby(wcode).cummax().to_numpy()
    wrun_lo = sl.groupby(wcode).cummin().to_numpy()
    pw = wcode - 1
    pwh = np.where(pw >= 0, wk_hi[np.clip(pw, 0, None)], np.nan)
    pwl = np.where(pw >= 0, wk_lo[np.clip(pw, 0, None)], np.nan)

    day_close = (pd.DatetimeIndex(days) + pd.Timedelta(days=1, hours=17)
                 ).tz_localize(NY).tz_convert("UTC")
    rows = []
    for d, lvl, cmp in ((1, pdh, np.greater), (-1, pdl, np.less)):
        lv = lvl[code]
        with np.errstate(invalid="ignore"):
            hit = cmp(h if d == 1 else l, lv) & np.isfinite(lv)
        pos = np.flatnonzero(hit)
        if len(pos) == 0:
            continue
        keep = np.r_[True, code[pos][1:] != code[pos][:-1]]
        j = pos[keep]                                   # first take of each day
        j = j[j != first_pos[code[j]]]                  # a gap open is not an in-session take
        for jj in j:
            i = code[jj]
            a = adr[i]
            used = run_hi[jj] - run_lo[jj]
            if d == 1:
                reach = run_lo[jj] + a                  # ADR projected from the day's low
                tgt = np.nan
                for q in range(i - 1, win_start[i] - 1, -1):
                    if dh[q] > run_hi[jj]:
                        tgt = dh[q]
                        break
                has_t = bool(np.isfinite(tgt) and tgt <= reach)
                late = bool(late_up[i])
                htf = bool(np.isfinite(pwh[jj]) and wrun_hi[jj] > pwh[jj])
            else:
                reach = run_hi[jj] - a
                tgt = np.nan
                for q in range(i - 1, win_start[i] - 1, -1):
                    if dl[q] < run_lo[jj]:
                        tgt = dl[q]
                        break
                has_t = bool(np.isfinite(tgt) and tgt >= reach)
                late = bool(late_dn[i])
                htf = bool(np.isfinite(pwl[jj]) and wrun_lo[jj] < pwl[jj])
            dec = idx[jj] + pd.Timedelta(minutes=1)
            frac = used / a
            g_adr = bool(frac <= USED_CUT)
            rows.append((dec, d, X_ADR * a, day_close[i] - dec, a, frac, has_t, late, htf,
                         g_adr, bool(g_adr and has_t and not (late and htf))))
    if not rows:
        return _empty()
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_dist", "max_hold",
                                     "adr", "frac_used", "has_target", "late", "htf_taken",
                                     "gate_adr", "gate_full"])
    ev = ev[ev["max_hold"] > pd.Timedelta(0)]
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = 1.0
    ev = ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)
    return ev[COLS]


PARAMS = {"event": "first in-session M1 take of the prior real day's high (long) / low (short)",
          "day_open": "18:00 NY", "min_day_m1": MIN_N_M1, "gap_open_take": "excluded",
          "adr": f"mean H-L of last {ADR_DAYS} completed real days", "adr_days": ADR_DAYS,
          "range_used": "running day high - running day low through the break bar",
          "used_cut": USED_CUT, "stop_target": f"symmetric {X_ADR} x ADR from entry, rr 1",
          "max_hold": "to the trading-day close (17:00 NY), per row",
          "ctrl_tod_tol_min": TOD_TOL}
SRC = {
    "event": "corpus: 3OIq9HmckH8 'when can I actually trade after previous day high is taken out?'",
    "day_open": "session_window_fit: settled 18:00 NY daily roll",
    "min_day_m1": "declared-before-run: days with < 600 M1 bars are data-hole stubs (README trap 6); PDH/PDL and ADR read from real days only",
    "gap_open_take": "declared-before-run: a day that OPENS beyond PDH/PDL has no in-session take; the reopen is a gap artefact (vault Session Timing on Gold)",
    "adr": "corpus: 3OIq9HmckH8 'You get the total range divided by the total days' (mean H-L)",
    "adr_days": "declared-before-run: 3OIq9HmckH8 slide uses three days and adds 'Ideally, you use a few more'; he reads a chart ADR indicator ('just average daily range under technicals'), taken at its common default length 14",
    "range_used": "corpus: 3OIq9HmckH8 'If this is the high, where does our 115 lie?' (ADR projected from the day's opposite extreme)",
    "used_cut": "corpus: 3OIq9HmckH8 'We've gone 50. That's half of the daily range' = continuation valid; failing cases ~78-100% used ('the range is 900 and we've already gone 700'); 'most of the daily range' read literally as more than half",
    "stop_target": "declared-before-run: stop 'Not specified in this video'; 0.5 ADR is the further move the gate-boundary case expects ('We've gone 50 ... What can we go reach for? Around 100'); symmetric stop keeps the book volatility-neutral (vault: volatility clusters)",
    "max_hold": "corpus: 3OIq9HmckH8 'That's when I'd want to wait for a new daily candle, so I have new range'",
    "ctrl_tod_tol_min": "declared-before-run: range used grows through the day, so the gate correlates with NY clock; README trap 9 / vault 'rate nulls must match time of day'",
}
PARAMS_B = {**PARAMS, "target_lookback_days": TGT_LOOKBACK,
            "open_target": "nearest prior daily high (low) above (below) the day's running high (low), i.e. the lowest untraded old high, within the lookback",
            "target_within": "target <= day running low + ADR (long), >= running high - ADR (short); no tolerance",
            "late_day": f"prior {LATE_N} real days each closed beyond its predecessor's high (long) / low (short) -> today is candle 4+",
            "htf_target": "previous ISO week high (long) / low (short); taken = week's running extreme through the break bar beyond it"}
SRC_B = {**SRC,
         "target_lookback_days": "declared-before-run: 'open targets to the left' on the daily chart read as one month (20 real days) of daily candles",
         "open_target": "corpus: 3OIq9HmckH8 'Do we have open targets?' / 'looking at our previous highs over here'",
         "target_within": "corpus: 3OIq9HmckH8 'It's within the daily range'; the one 'beyond reach' slide gives no tolerance (draft ambiguity) -> none",
         "late_day": "corpus: 3OIq9HmckH8 'in candle four here after we've had multiple days of expansion' -> two prior expansion closes",
         "htf_target": "declared-before-run: 'higher time frame target' relative to the daily = the weekly level; previous-period-high-low lists PWH/PWL as draws; at the PDH/PDL break a daily open target cannot already be taken, so the weekly reading is the only decidable one"}


def summarize(ev):
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    for col in ("gate_adr", "has_target", "late", "htf_taken", "gate_full"):
        print(f"  {col:10s} rate {ev[col].mean():.3f}")
    print("  frac_used quantiles", ev["frac_used"].quantile([.1, .25, .5, .75, .9]).round(3).tolist())
    print("  hold median", ev["max_hold"].median())


if __name__ == "__main__":
    ev = cl.cache_frame("pdhpdl_adrgate_u1007_adr14_cut05_x05_tl20_late2", lambda: detect(cl.load_m1()))
    summarize(ev)
    if "--detect-only" in sys.argv:
        raise SystemExit(0)
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    rules_a = [
        "trading day rolls 18:00 NY; real day = >= 600 M1 bars; PDH/PDL = last completed real day's high/low",
        "event: first M1 bar of the session whose high > PDH (long) / low < PDL (short), not the session's first bar; decide at its close, enter next M1 open",
        "ADR = mean H-L of the last 14 completed real days; range used = running day high - low through the break bar",
        "trade: continuation in the break direction, stop and target 0.5 x ADR each side of entry (rr 1), exit at the trading-day close (17:00 NY)",
        "control: same direction/distances/hold, +/-30 d, NY clock +/-30 min; statistic = control-adjusted R, gated - complement",
    ]
    readings = [
        ("u1007a", "gate_adr", rules_a + ["gate: range used <= 0.5 x ADR (ADR clause alone)"], PARAMS, SRC),
        ("u1007b", "gate_full", rules_a + [
            "gate: range used <= 0.5 x ADR AND an open target (nearest untraded prior daily high above the running high / low below the running low, within 20 real days) lying within the ADR projected from the day's low (high)",
            "AND NOT (late expansion day: prior 2 real days each closed beyond the predecessor's high/low in the break direction, AND the previous week's high/low already traded through by the break bar)"],
         PARAMS_B, SRC_B),
    ]
    for rd, col, rules, params, src in readings:
        res = cl.gate_test(ev, col, mask_available_at="decision_time", claim="+",
                           ctrl_tod_tol_min=TOD_TOL)
        for key in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                    "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"):
            print(f"  {rd} {key}: {res.get(key)}")
        p = cl.write_result(CID, rd, res, operationalization={"rules": rules, "params": params},
                            params_source=src, script=__file__, probe=probe,
                            allow_unknown_id=True,
                            notes=("New concept from _inbox update_20261007_edu_03 (not in batches.json, "
                                   "allow_unknown_id). Both readings share one baseline frame and one probe. "
                                   "Daily-bias precondition not modelled: it affects both arms of the gate. "
                                   "Clause 3 evaluated at the break moment with the weekly level as HTF target."))
        print("wrote", p)
