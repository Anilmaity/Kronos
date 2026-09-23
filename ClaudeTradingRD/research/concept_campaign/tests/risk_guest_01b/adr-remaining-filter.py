"""adr-remaining-filter (guest: DTR, 07lOxv39LdY).

Reading a (gate): take a trade only if the distance to its target fits inside the ADR the
  day has left (tolerance: the corpus's accepted '$22 target against $17 remaining').
  Baseline book = the phase-3 5m bare CISD (entry unchanged: 'this filter only gates the
  target'). claim '+': target-fits trades beat the rest.
Reading b (trade): 'a day that has already travelled beyond its full ADR is a reversal
  candidate'. At the first M1 close of each trading day at which the day's range reaches
  the ADR, fade the side that just extended. claim '+': beats a matched random entry.

All parameters below were fixed before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

ADR_DAYS = 126          # corpus 07lOxv39LdY: 'last 6 months' (~126 trading days)
TOL = 1.3               # corpus 07lOxv39LdY: $22 target accepted against $17 remaining (1.29x)
MIN_DAY_M1 = 600        # declared: a trading day with < 600 M1 bars is a stub, not a day
TF, MAX_WAIT, RR, HOLD_A = "5min", 3, 2.0, "50min"      # phase-3 locked 5m CISD book
STOP_ADR_B, RR_B, HOLD_B = 0.25, 1.0, "4h"              # declared-before-run (reading b)


def adr_frame(m1):
    """Mean range of the last ADR_DAYS completed non-stub trading days, stamped at the
    close of the last of them. NaN until the full window exists."""
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1]
    rng = (d["high"] - d["low"]).rolling(ADR_DAYS, min_periods=ADR_DAYS).mean()
    return pd.DataFrame({"adr": rng.to_numpy(), "close_time": d["close_time"].to_numpy()},
                        index=d.index)


def last_close(m1, t):
    idx = m1.index.searchsorted(pd.DatetimeIndex(t) - pd.Timedelta(minutes=1), "right") - 1
    return m1["close"].to_numpy()[idx]


def detect_a(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAX_WAIT, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "fits_adr"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR})
    adr = cl.asof(adr_frame(m1), close)["adr"].to_numpy()
    run = cl.running_hilo(close, "1D", m1=m1)
    travelled = (run["high"] - run["low"]).to_numpy()
    px = last_close(m1, close)
    dist = RR * np.abs(px - out["stop_px"].to_numpy())
    remaining = adr - travelled
    ok = np.isfinite(adr) & np.isfinite(travelled)
    out = out[ok].copy()
    out["fits_adr"] = (dist[ok] <= TOL * remaining[ok])
    out = out[(out["stop_px"] - px[ok]) * out["direction"] < 0]   # stop on the right side
    return out.reset_index(drop=True)


def detect_b(m1):
    td = cl.trading_day(m1.index)
    k = pd.Series(td.to_numpy())
    hi = pd.Series(m1["high"].to_numpy()).groupby(k).cummax().to_numpy()
    lo = pd.Series(m1["low"].to_numpy()).groupby(k).cummin().to_numpy()
    close_t = m1.index + pd.Timedelta(minutes=1)
    adr = cl.asof(adr_frame(m1), close_t)["adr"].to_numpy()
    hit = np.isfinite(adr) & ((hi - lo) >= adr)
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr"]
    if not hit.any():
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame({"td": td.to_numpy(), "hit": hit, "pos": np.arange(len(m1))})
    first = df[df["hit"]].groupby("td")["pos"].first().to_numpy()
    new_high = m1["high"].to_numpy()[first] >= hi[first]
    t = pd.DatetimeIndex(close_t[first])
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": np.where(new_high, -1, 1),
                        "stop_dist": STOP_ADR_B * adr[first], "rr": RR_B})
    return out.reset_index(drop=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    src_adr = {"adr_days": "corpus: 07lOxv39LdY 'last 6 months' ADR lookback (NQ example)",
               "min_day_m1": "declared-before-run: days with <600 M1 bars are data-hole stubs"}
    if "a" in which:
        ev = cl.cache_frame(f"adr_a_cisd5m_mw{MAX_WAIT}_adr{ADR_DAYS}_tol{TOL}",
                            lambda: detect_a(cl.load_m1()))
        print("events", len(ev), "fits share", ev["fits_adr"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="230D")
        res = cl.gate_test(ev, "fits_adr", mask_available_at="decision_time",
                           max_hold=HOLD_A, claim="+")
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                       "verdict_detail", "gate_rate", "exposure_bars")})
        op = {"rules": [
            "baseline: 5m bare CISD (series_open level, 2/2 swings, max_wait 3), decide at "
            "the confirming 5m close, enter next M1 open, stop at protected swing, 2R, 50min",
            "ADR = mean (high-low) of the last 126 completed trading days (18:00 NY roll) "
            "with >=600 M1 bars, read asof the decision",
            "travelled = running high - running low of the current trading day (M1 closed "
            "by the decision); remaining = ADR - travelled",
            "gate passes when target distance (2 x |last close - stop|) <= 1.3 x remaining "
            "(remaining <= 0, i.e. day already beyond ADR, fails)"],
            "params": {"tf": TF, "max_wait": MAX_WAIT, "rr": RR, "max_hold": HOLD_A,
                       "adr_days": ADR_DAYS, "tol": TOL, "min_day_m1": MIN_DAY_M1}}
        src = {"tf": "corpus: 07lOxv39LdY execution timeframe 5m (yaml timeframes.ltf)",
               "max_wait": "phase3: locked CISD config", "rr": "phase3: locked 2R target",
               "max_hold": "phase3: 10 entry-TF bars (§1.13)",
               "tol": "corpus: 07lOxv39LdY '$22 target against $17 remaining' accepted",
               **src_adr}
        p = cl.write_result("adr-remaining-filter", "a", res, operationalization=op,
                            params_source=src, script=__file__, probe=probe,
                            notes="Baseline book is the phase-3 5m CISD because the concept "
                                  "leaves entry unchanged and gives no stop.")
        print("wrote", p)
    if "b" in which:
        ev = cl.cache_frame(f"adr_b_exceed_adr{ADR_DAYS}_s{STOP_ADR_B}_rr{RR_B}",
                            lambda: detect_b(cl.load_m1()))
        print("events", len(ev))
        probe = cl.probe_lookahead(detect_b, ev, lookback="230D")
        res = cl.trade_test(ev, max_hold=HOLD_B, claim="+", ctrl_tod_tol_min=30)
        print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi",
                                       "p", "mde", "verdict", "verdict_detail",
                                       "exposure_bars", "ties")})
        op = {"rules": [
            "ADR as reading a",
            "event: first M1 close of each trading day at which running day range >= ADR",
            "direction: fade the side that just extended (new day high -> short, new low -> "
            "long)",
            "stop 0.25 x ADR from entry, target 1R, time exit 4h; control matched on NY "
            "time of day +/-30 min (exceedances cluster in the NY morning; the concept is "
            "not a timing claim)"],
            "params": {"adr_days": ADR_DAYS, "min_day_m1": MIN_DAY_M1,
                       "stop_adr": STOP_ADR_B, "rr": RR_B, "max_hold": HOLD_B,
                       "ctrl_tod_tol_min": 30}}
        src = {"stop_adr": "declared-before-run: concept gives no stop",
               "rr": "declared-before-run: concept gives no target for the reversal",
               "max_hold": "declared-before-run: rest of the session, capped 4h",
               "ctrl_tod_tol_min": "declared-before-run: README trap 9 (events cluster in NY AM)",
               **src_adr}
        p = cl.write_result("adr-remaining-filter", "b", res, operationalization=op,
                            params_source=src, script=__file__, probe=probe)
        print("wrote", p)
