"""update_20261007 / daily-profile-confirmation — NEW claim only (draft live_12).

Source rTomJ8URFnw (New York Open Live Q&A), indices worked live: "NASDAQ into all-time
highs, multiple days of expansion ... on the hour, right? Kind of just failure swings up
mostly. Yeah, that's not quite bullish in terms of daily profile", "normally on a day like
this, you either consolidate or you have a reversal. That's why I'm favoring the downside
inside the daily profile because we just have failure swings. Usually, you have 930 some
sort of manipulation and a move lower", "I can't trade long when my daily profile looks
like this and we've already expanded right over previous highs".

Claim: after an OVERNIGHT expansion over previous highs with only failure swings up on
the hourly, do not frame longs (expect a reversal lower or consolidation). Mirror applied.

Book (one event per trading day, 18:00 NY roll): decision 09:30 NY. Universe = days whose
overnight hourly bars (closed by 09:30) include a CLOSE beyond the prior real session's
high (upside expansion -> continuation LONG) or low (-> SHORT); days with both are dropped.
After the first expansion close, every later hourly bar that prints a new session extreme
is a swing attempt: SUCCESS if it closes beyond the prior session extreme, FAILURE swing if
it closes back inside. Days with no attempt after the expansion are dropped (no swing to
read). Continuation trade: stop = the day's running opposite extreme at 09:30, 2R target,
exit 17:00 NY. Drop risk < 0.10 x prior-day range.

Gates (claim '-': gated continuation trades are WORSE than the complement):
  u1007l12a  "only failure swings" (draft wording): no SUCCESS after the expansion.
  u1007l12b  "failure swings ... mostly" (source wording): the LATEST attempt is a failure.
Prior reading (no label, profile-confirmation gate on the bias book) is untouched. Reading
labels carry 'l12' so the sibling live_04/05/08 drafts of this concept cannot collide.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

CID = "daily-profile-confirmation"
NY = "America/New_York"
DEC = (9, 30)            # decision 09:30 NY
MIN_H1 = 12              # of the 15 overnight 1h bars 18:00 -> 09:00
MIN_DAY_M1 = 600         # stub-session filter for the prior day (README trap 6)
MIN_RISK_FRAC = 0.10
RR = 2.0
MAX_HOLD = "450min"      # 09:30 -> 17:00 NY, no halt inside
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr",
        "only_fail", "last_fail", "x_nfail", "x_nsucc"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    h = cl.build_bars(m1, "1h")
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1]
    if h.empty or d.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    td = cl.trading_day(h.index)
    days = pd.DatetimeIndex(np.unique(td.to_numpy()))
    dec = (days + pd.Timedelta(days=1, hours=DEC[0], minutes=DEC[1])).tz_localize(NY).tz_convert("UTC")
    prev = cl.asof(d[["high", "low", "close_time", "trading_day"]], dec)
    gap = (days - pd.DatetimeIndex(prev["trading_day"])).days.to_numpy()
    pdh, pdl = prev["high"].to_numpy(float), prev["low"].to_numpy(float)

    hi, lo, cl_ = (h[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(h["close_time"]).tz_convert("UTC").asi8
    tdn = td.asi8
    m1_close = pd.Series(m1["close"].to_numpy(float), index=pd.DatetimeIndex(m1.index).tz_convert("UTC"))
    rows = []
    for k, day in enumerate(days):
        if not (1 <= gap[k] <= 4) or not np.isfinite(pdh[k]):
            continue
        idx = np.flatnonzero((tdn == day.value) & (ct <= dec[k].value))
        if len(idx) < MIN_H1:
            continue
        H, L, C = hi[idx], lo[idx], cl_[idx]
        up = np.flatnonzero(C > pdh[k])
        dn = np.flatnonzero(C < pdl[k])
        if (len(up) > 0) == (len(dn) > 0):        # neither, or both sides expanded
            continue
        s = 1 if len(up) else -1
        e = (up if s == 1 else dn)[0]
        ext = H[:e + 1].max() if s == 1 else L[:e + 1].min()
        nf = ns = 0
        last = 0
        for j in range(e + 1, len(idx)):
            new = H[j] > ext if s == 1 else L[j] < ext
            if new:
                ok = C[j] > ext if s == 1 else C[j] < ext
                ns, nf, last = (ns + 1, nf, 1) if ok else (ns, nf + 1, -1)
                ext = H[j] if s == 1 else L[j]
        if nf + ns == 0:
            continue
        rows.append((dec[k], s, nf, ns, last, pdh[k] - pdl[k]))
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    r = pd.DataFrame(rows, columns=["t", "s", "nf", "ns", "last", "rng"])
    t = pd.DatetimeIndex(r["t"])
    ref = m1_close.reindex(t - pd.Timedelta(minutes=1)).to_numpy()   # 09:29 bar, closed at 09:30
    run = cl.running_hilo(t, "1D", m1=m1)
    s = r["s"].to_numpy()
    stop = np.where(s == 1, run["low"].to_numpy(float), run["high"].to_numpy(float))
    risk = s * (ref - stop)
    keep = np.isfinite(ref) & np.isfinite(stop) & (risk > 0) & (risk >= MIN_RISK_FRAC * r["rng"].to_numpy())
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": s, "stop_px": stop, "rr": RR,
                       "only_fail": r["ns"].to_numpy() == 0, "last_fail": r["last"].to_numpy() == -1,
                       "x_nfail": r["nf"].to_numpy(), "x_nsucc": r["ns"].to_numpy()})
    return ev[keep].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("dpc_u1007l12_overnight_exp_failswing", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict(),
          "only_fail", int(ev["only_fail"].sum()), "last_fail", int(ev["last_fail"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base_rules = [
        "trading day rolls 18:00 NY; decision 09:30 NY (one event per day); available_at = decision "
        "(1h bars closed by 09:00, M1 closed by 09:30)",
        "prior day = last completed 18:00-NY session with >= 600 M1 bars, 1-4 calendar days back; PDH/PDL its high/low",
        "overnight = the day's 1h bars closed by 09:30 (>= 12 of 15 required)",
        "expansion: first overnight 1h CLOSE above PDH (long continuation) or below PDL (short); days with "
        "both or neither are dropped",
        "after the expansion bar, each 1h bar printing a new session extreme is a swing attempt: success if it "
        "closes beyond the prior session extreme, failure swing if it closes back inside; days with no attempt dropped",
        "trade: continuation direction, entry next M1 open at/after 09:30, stop = day's running opposite extreme "
        "(M1 closed by 09:30), 2R target, time exit 17:00 NY (450 min); drop risk < 0.10 x prior-day range",
        "claim '-': continuation trades on gated days do worse than on complement days (control-adjusted)"]
    params = {"decision": "09:30 NY", "overnight_min_h1": MIN_H1, "stub_day_min_n_m1": MIN_DAY_M1,
              "expansion": "1h close beyond PDH/PDL", "swing_tf": "1h", "mirror": True,
              "stop": "day running opposite extreme", "rr": RR, "max_hold": MAX_HOLD,
              "min_risk_frac": MIN_RISK_FRAC, "day_roll": "18:00 NY", "grid4h": "n/a"}
    src = {"decision": "corpus: rTomJ8URFnw 'Usually, you have 930 some sort of manipulation and a move lower'",
           "overnight_min_h1": "declared-before-run: data-hole guard on the overnight hourly sequence",
           "stub_day_min_n_m1": "declared-before-run: README trap 6 stub sessions (same cut as model_own_01a/_common)",
           "expansion": "corpus: rTomJ8URFnw 'we've already expanded right over previous highs' (closure = expansion; "
                        "'previous highs' read as the prior session high; the all-time-high variant is index-specific "
                        "and not probe-able)",
           "swing_tf": "corpus: rTomJ8URFnw 'on the hour, right? Kind of just failure swings up mostly'",
           "mirror": "declared-before-run: source shows the upside case only; mirror applied",
           "stop": "method_spec: stop is the protected swing; day's running opposite extreme as in model_own_01a baseline",
           "rr": "method_spec: §5.3 2R fixed target (no target named for the vetoed long)",
           "max_hold": "corpus: rTomJ8URFnw 'normally on a day like this, you either consolidate or you have a "
                       "reversal' (the rest of the daily candle, to the 17:00 NY halt)",
           "min_risk_frac": "declared-before-run: degenerate-stop guard, model_own_01a/_common.MIN_RISK_FRAC",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll",
           "grid4h": "declared-before-run: no 4h bars used"}
    readings = {
        "u1007l12a": ("only_fail", "gate only_fail: >= 1 failure swing and NO successful swing after the expansion",
                      "corpus: rTomJ8URFnw 'because we just have failure swings' (draft: 'only failure swings up')"),
        "u1007l12b": ("last_fail", "gate last_fail: the most recent swing attempt after the expansion is a failure",
                      "corpus: rTomJ8URFnw 'Kind of just failure swings up mostly' (current state of the profile)"),
    }
    for rd, (gate, rule, gsrc) in readings.items():
        res = cl.gate_test(ev, gate, mask_available_at="decision_time", max_hold=MAX_HOLD, claim="-")
        for k in ("n", "n_gated", "gate_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "halves"):
            print(rd, k, res.get(k))
        p = cl.write_result(CID, rd, res, operationalization={"rules": base_rules + [rule],
                                                                "params": {**params, "gate": gate}},
                            params_source={**src, "gate": gsrc}, script=__file__, probe=probe,
                            notes="New claim from draft live_12 (rTomJ8URFnw, indices example). The source's "
                                  "own outcome contradicted the framing (indices bullish after 10:00). "
                                  "Two pre-declared readings of 'only ... mostly'; both are run and ledgered.")
        print("wrote", p)
