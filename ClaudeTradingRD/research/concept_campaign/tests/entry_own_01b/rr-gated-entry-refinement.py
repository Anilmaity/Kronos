"""rr-gated-entry-refinement — trade_test.

Fix the target first; compute R at the current timeframe; if R < 2, step down
(15m -> 5m -> 1m) and take a CONFIRMED lower-timeframe setup whose R to the SAME target
is >= 2; never move the target; if no refinement qualifies before the target (or the
HTF invalidation) is reached, skip.

Operationalisation (declared before the run):
  * HTF idea = phase-3 CISD on 15m (series_open, 2/2 swing, max_wait 3), direction of the CISD,
    stop = its protected swing, decided at the confirm bar close.
  * Fixed target = prior NY trading day's extreme in the trade direction (PDH/PDL), untaken
    today, beyond the entry (method_spec §5.2 #1). Never moved.
  * R15 >= 2 -> trade the 15m CISD itself.
  * Else refinement window = from the 15m decision until the first of: 150 min, the first M1
    bar touching the target, the first M1 bar touching the 15m protected swing. Candidates =
    same-direction CISDs (same phase-3 rule) on 5m and on 1m bars confirming inside the window
    with R >= 2 to the fixed target (stop = their own protected swing). Real-time order: the
    EARLIEST qualifying candidate is taken (5m wins a tie). None -> no trade.
  * Exit: target (fixed PDH/PDL) / stop / 150 min after the entry decision.
claim '+': the refined book beats a matched random entry.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, cisd_frame, m1_arrays, first_touch, PHASE3_SRC

CID = "rr-gated-entry-refinement"
HTF = "15min"
LTFS = ("5min", "1min")
MIN_R = 2.0
WIN = pd.Timedelta("150min")
HOLD = "150min"
PAD = pd.Timedelta("150min")


def _r(sgn, entry, stop, tgt):
    risk = (entry - stop) * sgn
    rew = (tgt - entry) * sgn
    return np.where(risk > 0, rew / np.where(risk > 0, risk, 1.0), -np.inf)


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "tf_used"]
    b = cl.build_bars(m1, HTF)
    ev = cisd_frame(b)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["conf_close_time"])
    pdl = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(t, "1D", m1=m1)
    sgn = ev["sgn"].to_numpy()
    entry = ev["confirm_close"].to_numpy(float)
    stop = ev["protected_swing"].to_numpy(float)
    tgt = np.where(sgn > 0, pdl["high"].to_numpy(float), pdl["low"].to_numpy(float))
    today = np.where(sgn > 0, run["high"].to_numpy(float), run["low"].to_numpy(float))
    keep = np.isfinite(tgt) & np.isfinite(today) & (np.where(sgn > 0, today < tgt, today > tgt)) \
        & ((tgt - entry) * sgn > 0) & ((entry - stop) * sgn > 0)
    ev, t, sgn, entry, stop, tgt = ev[keep].reset_index(drop=True), t[keep], sgn[keep], entry[keep], stop[keep], tgt[keep]
    r15 = _r(sgn, entry, stop, tgt)
    rows = []
    for k in np.flatnonzero(r15 >= MIN_R):
        rows.append((t[k], sgn[k], stop[k], tgt[k], HTF))
    ref = np.flatnonzero(r15 < MIN_R)
    if len(ref):
        mt, mh, ml, _ = m1_arrays(m1)
        t_ns = t.tz_convert("UTC").as_unit("ns").asi8
        end_ns = t_ns + WIN.value
        side_t = np.where(sgn > 0, "above", "below")
        side_s = np.where(sgn > 0, "below", "above")
        kt = first_touch(mt, mh, ml, t_ns[ref], end_ns[ref], tgt[ref], side_t[ref])
        ks = first_touch(mt, mh, ml, t_ns[ref], end_ns[ref], stop[ref], side_s[ref])
        idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
        for n, k in enumerate(ref):
            w_end = t[k] + WIN
            if kt[n] >= 0:
                w_end = min(w_end, idx[kt[n]])
            if ks[n] >= 0:
                w_end = min(w_end, idx[ks[n]])
            sl = m1[(idx >= t[k] - PAD) & (idx < w_end)]
            best = None
            for tf in LTFS:
                bb = cl.build_bars(sl, tf)
                ce = cisd_frame(bb)
                if ce.empty:
                    continue
                ct = pd.DatetimeIndex(ce["conf_close_time"])
                ok = (ce["sgn"].to_numpy() == sgn[k]) & (pd.DatetimeIndex(ce["confirm_time"]) >= t[k]) \
                    & (ct <= w_end)
                rr = _r(sgn[k], ce["confirm_close"].to_numpy(float), ce["protected_swing"].to_numpy(float), tgt[k])
                ok &= rr >= MIN_R
                if ok.any():
                    j = np.flatnonzero(ok)[np.argmin(ct[ok].asi8)]
                    cand = (ct[j], sgn[k], float(ce["protected_swing"].iloc[j]), tgt[k], tf)
                    if best is None or cand[0] < best[0]:
                        best = cand
            if best is not None:
                rows.append(best)
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "tf_used"])
    out["available_at"] = out["decision_time"]
    out = out.sort_values(["decision_time", "direction", "stop_px"], kind="stable")
    out = out.drop_duplicates(["decision_time", "direction", "stop_px", "target_px"]).reset_index(drop=True)
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_15m_5m_1m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["tf_used"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.trade_test(ev, max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "avg_R", "win_rate", "exposure_bars", "ctrl_overlap", "ties")})
    op = {"rules": [
        "HTF idea: 15m CISD (series_open, 2/2 swing, max_wait 3); stop = protected swing; decide at confirm close",
        "fixed target = prior NY trading day high (long) / low (short), prior_hilo 1D min_coverage 0.5, "
        "untaken today (running_hilo) and beyond the entry; never moved",
        "R = (target - entry)/(entry - stop) with entry = confirm close; R >= 2 on 15m -> trade 15m",
        "else: window from the 15m decision to the first of +150min / M1 touch of target / M1 touch of "
        "the 15m protected swing; earliest same-direction 5m or 1m CISD (same rule) confirming in the "
        "window with R >= 2 to the fixed target is taken (5m wins ties); none -> skip",
        "enter next M1 open after the chosen decision; exit at fixed target / own stop / 150 min"],
        "params": {"htf": HTF, "ltfs": "5min,1min", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "min_r": MIN_R, "target": "prior day extreme (PDH/PDL), untaken",
                   "refine_window": "150min", "max_hold": HOLD, "min_coverage": 0.5}}
    src = {"htf": "corpus: FXNLGYxfbDc 'moving from a 15 minute chart down to a five to a one minute chart'",
           "ltfs": "corpus: FXNLGYxfbDc 15m -> 5m -> 1m ladder (rr-gated-entry-refinement.yaml)",
           "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "min_r": "method_spec: §5.3 2R is the floor (risk-reward-minimum), inferred minimum in this concept",
           "target": "method_spec: §5.2 #1 previous candles' unswept extremes; corpus FXNLGYxfbDc fixes the "
                     "previous day's low as the target",
           "refine_window": "declared-before-run: refinement allowed for 10 HTF (15m) bars, cut short by target "
                            "or HTF invalidation (yaml invalidation: target reached first -> missed)",
           "max_hold": "phase3: §1.13 10 entry-TF periods, taken at the setup's 15m timeframe",
           "min_coverage": "declared-before-run: skip stub sessions per README trap 6"}
    vc = ev["tf_used"].value_counts().to_dict()
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=f"trades by timeframe used: {vc}")
    print(p)
