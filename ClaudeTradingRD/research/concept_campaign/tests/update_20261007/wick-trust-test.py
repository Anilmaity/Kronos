"""wick-trust-test — update u1007 (TTrades, RX8vtP3PLYk "Let The Wick Form, Trade The Body").

NEW claims only. Readings a/b (structure_own_02b) already tested the early+shallow trust gate
on wick-confirming CISDs (4h/15m NULL, 1D/1h UNDERPOWERED). This file tests what the draft adds:

  u1007a  PER-CLOSURE LOOP. "After each closure, I'm going to ask myself, do I think that this
          wick has formed?" -- yes only once an LTF CISD has made the HTF candle's running
          extreme a protected swing. "if we try to [enter before the wick forms] ... we are going
          to get stopped out, and we're going to be the liquidity for the wick to form."
          gate_test on every LTF closure inside the HTF candle, both directions:
            trusted  = the closure where an LTF CISD confirms the candle's running extreme
                       (the 'yes'); stop = that protected swing
            complement = every closure where the answer is still 'no' (no confirmed extreme,
                       or the confirmed one has since been exceeded); stop = the current wick
                       (the running extreme), as in "putting my stop right on this current wick"
          claim '+': the 'yes' entries beat the 'no' entries, control-adjusted.
  u1007b  GIVE-UP RULE. "generally want to see one more high, and this would be kind of our last
          chance before I give up on the idea ... I can just look for the next day."
          gate_test on the 'yes' rows only: allowed = attempt 1 or 2 in this candle/direction
          (attempt = a 'yes'; a new attempt only after the previous protected swing was exceeded:
          the first try plus ONE more), complement = attempt >= 3 (past the last chance).
          claim '+': confirmations inside the allowance beat the ones he would have skipped.

Fixed BEFORE the first run (no parameter was searched):
  * HTF 1D (NY 18:00 roll), LTF 1h: the lesson's main worked example asks the question of the
    daily candle on hourly closures.
  * LTF CISD = phase-3 rung 0 (series_open, swing 2/2, max_wait 3), via structure_own_02b
    _common.cisd_frame (same construct as readings a/b). "wick-confirming" = extreme bar inside
    the HTF candle and protected swing == the candle's running extreme at the confirming close.
  * No bias input: both directions at every closure. The bias rung was refuted in phase 3
    (Conjunction Test) and is not part of the new claim; both arms carry the same construction.
  * Rows only at closures before the candle's final hour (the 16:00-17:00 NY bar closes into
    the halt; entering then trades the NEXT candle). The first HTF candle of the input is
    skipped (it may be partial in a truncated slice).
  * Entry next M1 open, 2R, hold 10 LTF bars (10h, phase 3), M1 exits, stop-first ties.
NOT tested (see notes): the counter-trend protected-swing filter (a bias/alignment gate; the
bias rung and timeframe-alignment were already tested and refuted), single-candle vs series
selection ("shown, not defined"), the 30-minute timeframe adjustment (discretionary).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "structure_own_02b"))
from _common import cl, np, pd, ns, empty, cisd_frame, PHASE3_SRC  # noqa: E402

CID = "wick-trust-test"
HTF, LTF, HOLD = "1D", "1h", "10h"
RR = 2.0
ALLOW = 2                      # first attempt + "one more"
HALT_NS = pd.Timedelta("1h").value
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "trusted", "attempt"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "attempt", "allowed"]


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    hb = cl.build_bars(m1, HTF)
    lb = cl.build_bars(m1, LTF)
    if len(hb) < 2 or len(lb) < 20:
        return empty(COLS_A)
    hst, hct = ns(hb.index), ns(hb["close_time"])
    lst, lct = ns(lb.index), ns(lb["close_time"])
    lo, hi = lb["low"].to_numpy(float), lb["high"].to_numpy(float)
    conf: dict = {}                                    # (confirm bar pos, sign) -> [(ps, extreme pos)]
    for r in cisd_frame(lb).itertuples(index=False):
        conf.setdefault((int(r.conf_pos), int(r.sgn)), []).append((float(r.protected_swing), int(r.ext_pos)))
    kof = np.searchsorted(hst, lst, "right") - 1       # HTF candle each LTF bar starts in
    rows = []
    for k in range(1, len(hst)):                       # skip k=0: may be partial in a slice
        js = np.flatnonzero((kof == k) & (lct <= hct[k]))
        for d in (1, -1):
            state, ps, att, run = False, np.nan, 0, np.nan
            for j in js:
                x = lo[j] if d == 1 else hi[j]
                run = x if np.isnan(run) else (min(run, x) if d == 1 else max(run, x))
                if state and ((run < ps) if d == 1 else (run > ps)):
                    state = False                      # the trusted wick was exceeded: back to 'no'
                if state:
                    continue                           # already answered 'yes' and holding
                yes = any(abs(p - run) <= 1e-9 and e >= 0 and lst[e] >= hst[k]
                          for p, e in conf.get((int(j), d), ()))
                if yes:
                    state, ps, att = True, run, att + 1
                if lct[j] < hct[k] - HALT_NS:
                    rows.append((lct[j], d, run, yes, att if yes else 0))
    if not rows:
        return empty(COLS_A)
    a = np.array(rows, dtype=object)
    t = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype(np.int64), utc=True))
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": a[:, 1].astype(int),
                        "stop_px": a[:, 2].astype(float), "rr": RR, "trusted": a[:, 3].astype(bool),
                        "attempt": a[:, 4].astype(int)})
    return out.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)[COLS_A]


def to_b(ev: pd.DataFrame) -> pd.DataFrame:
    b = ev[ev["trusted"]].copy()
    b["allowed"] = b["attempt"] <= ALLOW
    return b.reset_index(drop=True)[COLS_B]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    return to_b(detect_a(m1))


SRC = {
    "htf": "corpus: RX8vtP3PLYk 'Do I think that this is the wick of the daily candle' (asked on hourly closures)",
    "ltf": "corpus: RX8vtP3PLYk 'even here just on the hourly, I could look to take an entry'",
    "per_closure": "corpus: RX8vtP3PLYk 'After each closure, I'm going to ask myself, do I think that this wick has formed?'",
    "yes_rule": "corpus: RX8vtP3PLYk 'I'm going to wait for an intra-candle change in the state of delivery'; "
                "wick-confirming = protected swing == HTF running extreme (structure_own_02b readings a/b construct)",
    "cisd": PHASE3_SRC,
    "stop_yes": "corpus: RX8vtP3PLYk 'put my stop on that wick because if the wick is formed, that stop shouldn't get taken out'",
    "stop_no": "corpus: RX8vtP3PLYk 'Would I trust taking any sort of entry in here and putting my stop right on this current wick'",
    "rr": "corpus: RX8vtP3PLYk 'And I can look for two R.'",
    "max_hold": PHASE3_SRC,
    "direction": "declared-before-run: both directions, no bias input (phase-3 bias rung refuted; not part of the new claim)",
    "last_closure": "declared-before-run: no rows at the HTF candle's final LTF closure (entry would fall in the next candle)",
    "allow_attempts": "corpus: RX8vtP3PLYk 'generally want to see one more high, and this would be kind of our last "
                      "chance before I give up on the idea'; declared-before-run: attempt = a confirmed wick, a new "
                      "attempt only after the previous one was exceeded; allowed = first + one more (<= 2)",
    "grid4h": "session_window_fit: forex grid for gold (unused by 1D/1h; day rolls 18:00 NY)",
    "day_open_hour": "session_window_fit: NY 18:00 venue day roll",
}

PARAMS = {"htf": HTF, "ltf": LTF, "cisd": "series_open 2/2 max_wait 3", "rr": RR, "max_hold": HOLD,
          "direction": "both, no bias", "last_closure": "excluded", "grid4h": "forex", "day_open_hour": 18}


def stop_pts(ev: pd.DataFrame) -> np.ndarray:
    mkt = cl.get_market()
    i = np.minimum(mkt.pos_at_or_after(pd.DatetimeIndex(ev["decision_time"])), len(mkt.o) - 1)
    return np.abs(mkt.o[i] - ev["stop_px"].to_numpy(float))


def summary(res):
    return {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi",
                                    "p", "mde", "gate_firing_rate", "exposure_bars", "ties", "ctrl_overlap", "dropped")}


if __name__ == "__main__":
    ev = cl.cache_frame(f"u1007_wtt_{HTF}_{LTF}_loop", lambda: detect_a(cl.load_m1()))
    evb = to_b(ev)
    sp = stop_pts(ev)
    tr = ev["trusted"].to_numpy()
    att = evb["attempt"].value_counts().sort_index().to_dict()
    diag_a = (f"{len(ev)} closures, trusted {tr.sum()} ({tr.mean():.4f}); median stop pts yes "
              f"{np.median(sp[tr]):.2f} vs no {np.median(sp[~tr]):.2f}; "
              f"(day,dir) pairs with >=1 yes {evb.assign(d=evb.decision_time.dt.date).groupby(['d', 'direction']).ngroups}")
    diag_b = f"yes rows by attempt {att}; allowed {int(evb['allowed'].sum())}, past last chance {int((~evb['allowed']).sum())}"
    print(diag_a); print(diag_b)

    probe_a = cl.probe_lookahead(detect_a, ev, lookback="30D")
    print("probe a", probe_a["passed"])
    res_a = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold=HOLD)
    print("u1007a", summary(res_a))
    # POST-VERDICT DIAGNOSTIC (added after the first run; verdict NOT changed): the 'yes' rows cluster
    # in 22:00-01:00 NY (~38% vs ~21% of the 'no' rows), so README trap 9 calls for a control that
    # holds the NY clock. Run it, report it in notes, do not write it as the reading.
    tod = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold=HOLD, ctrl_tod_tol_min=30)
    print("u1007a tod30", summary(tod))
    hr = cl.to_ny(pd.DatetimeIndex(ev["decision_time"])).hour
    asia = lambda m: float(np.isin(hr[m], [22, 23, 0, 1]).mean())  # noqa: E731
    blk = {k: round(v["diff"], 3) for k, v in res_a["blocks"].items()}
    caveat = (f" CAVEAT (post-verdict diagnostics, verdict NOT changed): yes rows cluster at 22-01 NY "
              f"({asia(tr):.2f} vs {asia(~tr):.2f} of no rows); with ctrl_tod_tol_min=30 (trap 9, not pre-declared) "
              f"the diff is {tod['diff']:+.4f} [{tod['ci_lo']:+.4f}, {tod['ci_hi']:+.4f}] -> {tod['verdict']}. "
              f"Regime blocks {blk}: the effect sits mostly in B4 (2023-26). ctrl_overlap {res_a['ctrl_overlap']:.2f}: "
              f"'no' rows fire at every 1h close, so most control draws coincide with complement trades.")
    op_a = {"rules": [
        "1D candles (NY 18:00 roll); 1h CISD = phase-3 rung 0 (series_open, 2/2, max_wait 3)",
        "per (daily candle, direction), walk every 1h closure: 'yes' at the closure where a CISD whose extreme "
        "bar is inside the candle confirms the candle's running extreme as a protected swing; 'no' at every other "
        "closure while no confirmed extreme holds; after a 'yes', closures are skipped until the running extreme "
        "exceeds that protected swing (then back to 'no')",
        "row = each 'yes' (trusted, stop = the protected swing) and each 'no' (stop = the current running extreme); "
        "both directions; no rows at the candle's final 1h closure",
        "decide at the 1h close; enter next M1 open; 2R; hold 10h; gate = trusted"],
        "params": PARAMS}
    print(cl.write_result(CID, "u1007a", res_a, operationalization=op_a, params_source=SRC, script=__file__,
                          probe=probe_a,
                          notes="Tests only the new per-closure claim (wait for the yes vs enter on a no). " + diag_a +
                                ". NOT tested: counter-trend protected-swing filter (bias/alignment gate, already "
                                "refuted in phase 3), single-candle vs series (shown, not defined), 30m adjustment."
                                + caveat))

    probe_b = cl.probe_lookahead(detect_b, evb, lookback="30D")
    print("probe b", probe_b["passed"])
    res_b = cl.gate_test(evb, "allowed", mask_available_at="decision_time", max_hold=HOLD)
    print("u1007b", summary(res_b))
    op_b = {"rules": op_a["rules"][:2] + [
        "rows = the 'yes' closures only (stop = protected swing); attempt = 1 + earlier 'yes' answers in the same "
        "candle and direction whose protected swing was later exceeded",
        f"gate allowed = attempt <= {ALLOW} (first + 'one more'); complement = attempt >= {ALLOW + 1} (past the last chance)",
        "decide at the 1h close; enter next M1 open; 2R; hold 10h"],
        "params": {**PARAMS, "allow_attempts": ALLOW}}
    print(cl.write_result(CID, "u1007b", res_b, operationalization=op_b, params_source=SRC, script=__file__,
                          probe=probe_b, notes="Tests only the give-up rule. " + diag_b))
