"""fomc-week-protocol (AM Trades, guest).

Claim: in a week with an FOMC press conference, avoid Monday, Tuesday and Wednesday before
14:30 ET; observe the 14:30 release; trade Thursday and Friday.

Test: gate_test on the phase-3 locked bare 1h CISD book restricted to FOMC press-conference
weeks (dates: _common.FOMC_PRESSER, the Fed's published schedule, verified against a
14:00 NY M1 volatility spike on all 69 dates before any test ran).
  gated      = decisions on session dates AFTER the press-conference day, same week
               (Thursday and Friday for a Wednesday presser)
  complement = decisions in the same week before 14:30 ET on the presser day
               (Mon, Tue, Wed pre-14:30)
  dropped    = presser day at/after 14:30 ET (the 'observe' window), and non-FOMC weeks.
The post-event directional read ('how the release enters the market') is not operational
in the source (yaml ambiguity) and is not tested; the gate tests the day-selection rule.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, FOMC_PRESSER, ny_to_utc

PRESS_UTC = ny_to_utc(FOMC_PRESSER, 14, 30)


def detect(m1):
    ev = cisd_book(m1, "1h")
    cols = list(ev.columns) + ["after_event"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["decision_time"])
    sd = pd.DatetimeIndex(cl.session_date(t))
    wk = sd - pd.to_timedelta(sd.dayofweek, unit="D")
    pdates = pd.DatetimeIndex(FOMC_PRESSER)
    pwk = pdates - pd.to_timedelta(pdates.dayofweek, unit="D")
    wmap = dict(zip(pwk, range(len(pdates))))
    idx = np.array([wmap.get(w, -1) for w in wk])
    inweek = idx >= 0
    ii = np.clip(idx, 0, None)
    pday = pdates[ii]
    ptime = PRESS_UTC[ii]
    before = inweek & (t.asi8 < ptime.asi8)
    after = inweek & (sd > pday)
    keep = before | after
    out = ev[keep].copy()
    out["after_event"] = after[keep]
    return out.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_fomcweek_1hcisd_v2", lambda: detect(cl.load_m1()))
    print(len(ev), "events; after share", ev["after_event"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "after_event", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "ctrl_overlap", "dependence"):
        print(k, res.get(k))
    bp, bs = base_params("1h", "10h")
    op = {"rules": ["baseline: phase-3 bare 1h CISD (series_open, swing 2/2, max_wait 3), decide at confirming 1h close, enter next M1 open, stop protected swing, 2R, 10h",
                    "universe: decisions in weeks (session-date Mon-Fri) containing a scheduled FOMC press conference (2016-2018 SEP meetings only; every meeting from 2019; emergency actions excluded; 2026 through March)",
                    "gated = session dates after the presser day in that week (Thu/Fri); complement = before 14:30 ET on the presser day (Mon, Tue, Wed pre-14:30)",
                    "presser day at/after 14:30 ET dropped (observation window)"],
          "params": {**bp, "presser_time": "14:30 ET", "calendar": "FOMC press-conference dates 2016-01..2026-03 (69)"}}
    src = {**bs,
           "presser_time": "corpus: QmGJFxfSHxM yaml 'press conference is at 14:30 ET on a Wednesday'",
           "calendar": "declared-before-run: Federal Reserve published FOMC schedule; each date verified by a >=2.8x 14:00 NY M1-range spike vs its 40-day median before testing"}
    p = cl.write_result("fomc-week-protocol", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Re-run once after fixing an own-code bug: the presser timestamps were microsecond-resolution while decision times were ns, so the first run compared asi8 values 1000x apart and put every event in the after arm (UNTESTABLE, other arm 0). Tests the day-selection rule only; the post-event bias read is unspecified in the source. Two Thursday pressers (2020-11-05, 2024-11-07) keep the same before/after logic.")
    print(p)
