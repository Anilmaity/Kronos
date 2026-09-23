"""low-probability-day-checklist (guest: NickDoesFutures, G44VpidBD_U).

Baseline book: 5m bare CISD (phase-3 locked config) decided inside the NY AM session
(08:30-12:00 NY), the session the checklist classifies.

Reading a (claim '-'): the OHLC-decidable skip flags -> 'low probability' session:
  Monday (session date), OR the London window (02:00-05:00 NY) took BOTH the Asia window
  (20:00-00:00 NY) high and low. Flagged trades are claimed worse than unflagged ones.
  NOT covered (need an economic/speech calendar this dataset lacks, or are undefined):
  day before CPI / NFP, session before FOMC, central-bank-chair speech, 'indecisive
  daily bias', 'HTF draw already met'. 'Monday with no news' is tested as Monday.
Reading b (claim '-'): first trading day of the month (quarter starts are a subset) -
  'manipulation-heavy, requires more selectivity and less risk'.
All parameters were fixed before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

TF, MAX_WAIT, RR, HOLD = "5min", 3, 2.0, "50min"       # phase-3 locked 5m CISD book
NY = ("08:30", "12:00")      # method spec §2.5 / SESSION_WINDOWS['ny_am']
ASIA = ("20:00", "00:00")    # SESSION_WINDOWS['asia'] (killzones.yaml)
LONDON = ("02:00", "05:00")  # SESSION_WINDOWS['london'] (killzones.yaml)


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAX_WAIT, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "lowprob",
            "lowprob_av", "first_dom"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR})
    # the confirming bar must lie wholly inside the NY AM window
    start = close - pd.Timedelta(TF)
    out = out[cl.in_window(start, *NY) & cl.in_window(close - pd.Timedelta(minutes=1), *NY)]
    out = out.reset_index(drop=True)
    if out.empty:
        return pd.DataFrame(columns=cols)
    td = cl.trading_day(out["decision_time"])
    asia = cl.window_hilo(ASIA, m1).reindex(td)
    lon = cl.window_hilo(LONDON, m1).reindex(td)
    have = asia["high"].notna().to_numpy() & lon["high"].notna().to_numpy()
    lon_av = pd.DatetimeIndex(lon["available_at"])
    have &= np.asarray(lon_av <= pd.DatetimeIndex(out["decision_time"]))
    out = out[have].reset_index(drop=True)
    asia, lon, td = asia[have], lon[have], td[have]
    sd = cl.session_date(out["decision_time"])
    monday = np.asarray(sd.dayofweek == 0)
    both = (lon["high"].to_numpy() > asia["high"].to_numpy()) & \
           (lon["low"].to_numpy() < asia["low"].to_numpy())
    out["lowprob"] = monday | both
    out["lowprob_av"] = pd.DatetimeIndex(lon["available_at"]).tz_convert("UTC")
    # first trading day of the month: previous trading session (with data) is in another month
    msd = cl.session_date(m1.index)
    days = pd.DatetimeIndex(np.unique(msd.to_numpy()))
    pos = days.searchsorted(sd) - 1
    prev = days[np.clip(pos, 0, None)]
    first = np.asarray((pos >= 0) & (prev.month != sd.month))
    out["first_dom"] = first & (pos >= 0)
    out = out[pos >= 0].reset_index(drop=True)      # need a previous session in the data
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"lowprob_cisd5m_nyam_mw{MAX_WAIT}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "lowprob", ev["lowprob"].mean(), "first_dom", ev["first_dom"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base = {"tf": TF, "max_wait": MAX_WAIT, "rr": RR, "max_hold": HOLD,
            "ny_window": "08:30-12:00", "asia": "20:00-00:00", "london": "02:00-05:00"}
    bsrc = {"tf": "corpus: G44VpidBD_U unicorn model executed on the LTF (5m); phase3 5m cell",
            "max_wait": "phase3: locked CISD config", "rr": "phase3: locked 2R target",
            "max_hold": "phase3: 10 entry-TF bars",
            "ny_window": "method_spec: §2.5 NY AM 08:30-12:00 (SESSION_WINDOWS ny_am)",
            "asia": "session_window_fit: killzones.yaml Asia 20:00-00:00",
            "london": "session_window_fit: killzones.yaml London 02:00-05:00"}
    brules = ["baseline: 5m bare CISD (series_open, 2/2, max_wait 3), confirming 5m bar "
              "inside NY AM 08:30-12:00, enter next M1 open, stop protected swing, 2R, 50min"]
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        res = cl.gate_test(ev, "lowprob", mask_available_at="lowprob_av", max_hold=HOLD,
                           claim="-")
        print("a", {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde",
                                             "verdict", "verdict_detail", "ties")})
        op = {"rules": brules + [
            "flag = session date is Monday OR London 02:00-05:00 high > Asia 20:00-00:00 "
            "high AND London low < Asia low (same trading day); known at London end",
            "claim: flagged (low-probability) trades worse than the rest",
            "untested checklist items: CPI/NFP/FOMC eves, chair speeches (no calendar), "
            "'indecisive bias' and 'HTF draw already met' (undefined)"],
            "params": {**base, "aggressive": "both extremes taken (any amount)"}}
        src = {**bsrc, "aggressive": "declared-before-run: 'aggressively' unquantified; any "
                                     "take of both Asia extremes during London"}
        p = cl.write_result("low-probability-day-checklist", "a", res, operationalization=op,
                            params_source=src, script=__file__, probe=probe,
                            notes="Partial checklist: only the OHLC-decidable items. Monday "
                                  "is not checked for 'no news' (no calendar).")
        print("wrote", p)
    if "b" in which:
        res = cl.gate_test(ev, "first_dom", mask_available_at="decision_time", max_hold=HOLD,
                           claim="-")
        print("b", {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde",
                                             "verdict", "verdict_detail", "ties")})
        op = {"rules": brules + [
            "flag = session date is the first trading session of its calendar month "
            "(quarter starts included) - calendar rule known at the decision",
            "claim: flagged trades worse than the rest"],
            "params": base}
        p = cl.write_result("low-probability-day-checklist", "b", res, operationalization=op,
                            params_source=bsrc, script=__file__, probe=probe)
        print("wrote", p)
