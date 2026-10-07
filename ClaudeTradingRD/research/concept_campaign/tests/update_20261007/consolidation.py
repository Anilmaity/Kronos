"""consolidation (TTrades update 2026-10-07) — rate_test, two readings.

New claim (not the prior no-displacement gate): an inside day — a daily candle that fails to take
out the previous day's range — IS consolidation; the market is "rangebound" (9YVBe-20Hdg).
Prediction tested: the NEXT session stays inside the inside day's range (takes neither its high
nor its low), more often than a geometry-matched null.
  hit = no M1 high >= D.high and no M1 low <= D.low during session D+1 (its M1-bar count).
  null = same distance up AND down from the first M1 open, same bar count, at 5 matched random
  OTHER SESSION CLOSES (+/-30d) not flagged by the reading — session-anchored. claim '+'.
AUDIT 2026-10-07 (vault context): the first run drew null moments at any M1 minute, but every event
sits at the 17:00 NY day close and is scored over exactly the next session (README trap 9; vault
Concept Campaign lesson 3: rate nulls must hold the clock). That null is offset on EVERY day: the
2026-09-23 three-candle-outcomes reading (all days, same null) came back NEGATIVE -1.78pp for
"takes PDH or PDL", i.e. any next session stays inside ~1.8pp more than a random window — the size
of the first run's +1.5pp. Fix: null drawn from the complement's session closes (grid_times).
Reading u1007a: single inside day (D.high <= D-1.high and D.low >= D-1.low) — ES-R3ByDYrY.
Reading u1007b: nested inside days (D inside D-1, D-1 inside D-2) — 9YVBe-20Hdg.
Monthly variant not tested (a few dozen months, n far below power).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "consolidation"
MIN_BARS = 600   # skip stub/holiday sessions (harness example convention)


def _detect(m1, nested):
    d = cl.build_bars(m1, "1D")
    h, l, n = d["high"].to_numpy(float), d["low"].to_numpy(float), d["n_m1"].to_numpy()
    full = n > MIN_BARS
    ins = np.zeros(len(d), bool)
    ins[1:] = (h[1:] <= h[:-1]) & (l[1:] >= l[:-1]) & full[1:] & full[:-1]
    keep = ins.copy()
    if nested:
        keep[1:] = ins[1:] & ins[:-1]
        keep[0] = False
    t = pd.DatetimeIndex(d["close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "hi": h, "lo": l})
    return out[keep].reset_index(drop=True)


def detect_a(m1):
    return _detect(m1, False)


def detect_b(m1):
    return _detect(m1, True)


def run(which):
    det = detect_a if which == "u1007a" else detect_b
    ev = cl.cache_frame(f"{CID}_{which}_inside1D", lambda: det(cl.load_m1()))
    probe = cl.probe_lookahead(det, ev, lookback="20D")
    print(which, len(ev), "probe", probe["passed"], probe["events_compared"])
    mkt = cl.get_market()
    d = cl.bars("1D")
    t = pd.DatetimeIndex(ev["decision_time"])
    starts = d.index.tz_convert("UTC").as_unit("ns").asi8
    pos = np.searchsorted(starts, t.as_unit("ns").asi8, side="left")   # next session D+1
    ok = pos < len(d)
    nxt = np.where(ok, d["n_m1"].to_numpy()[np.minimum(pos, len(d) - 1)], 0).astype(np.int64)
    ok &= nxt > MIN_BARS
    hi, lo = ev["hi"].to_numpy(float), ev["lo"].to_numpy(float)
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    up, dn = hi - first_px, first_px - lo

    def stays(tt, px, m):
        a = cl.touch(tt, px + up[m], "above", horizon_bars=nxt[m])["hit"].to_numpy()
        b = cl.touch(tt, px - dn[m], "below", horizon_bars=nxt[m])["hit"].to_numpy()
        return (~(a | b)).astype(float)

    obs = np.full(len(ev), np.nan)
    obs[ok] = stays(t[ok], first_px[ok], ok)
    # session-anchored null: closes of other full sessions that this reading does NOT flag
    dct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC").as_unit("ns")
    grid = dct[(d["n_m1"].to_numpy() > MIN_BARS) & ~np.isin(dct.asi8, t.tz_convert("UTC").as_unit("ns").asi8)]
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED,
                         grid_times=grid)
    print("null draws NaT share", float(np.isnat(rt).mean()), "grid days", len(grid))

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        m = (~tk.isna()) & ok
        px = mkt.o[mkt.pos_at_or_after(tk[m])]
        out[m] = stays(tk[m], px, m)
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       claim="+", predictors=ev)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "observed_rate", "null_rate",
                                   "diff", "ci_lo", "ci_hi", "p")})
    pattern = ("D inside D-1 (high <= prior high, low >= prior low)" if which == "u1007a" else
               "D inside D-1 AND D-1 inside D-2 (nested inside days)")
    op = {"rules": [
        f"consolidation day: completed NY trading day {pattern}; all involved sessions > {MIN_BARS} M1 bars",
        "decide at that day's close_time; levels = the inside day's high and low",
        "hit = session D+1 (its M1-bar count) takes neither the high nor the low (stays rangebound)",
        "null: same distances above and below the first M1 open, same bar count, at 5 random OTHER "
        "session closes within +/-30 days (full sessions not flagged by this reading; window starts at "
        "the 18:00 NY reopen like the real one); claim '+'"],
        "params": {"tf": "1D", "day_open_hour": 18, "inside": "wick range, non-strict (<=, >=)",
                   "nested": which == "u1007b", "horizon": "next session, M1 bars",
                   "min_session_bars": MIN_BARS,
                   "null_grid": "closes of full sessions not flagged by the reading (session-anchored)"}}
    src = {"tf": "corpus: ES-R3ByDYrY 'yesterday was a consolidation' (daily candle)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "inside": "corpus: ES-R3ByDYrY 'price fails to take out a previous range'",
           "nested": ("corpus: ES-R3ByDYrY single inside day = consolidation" if which == "u1007a" else
                      "corpus: 9YVBe-20Hdg 'inside day inside day pretty much just a consolidation ... "
                      "we're inside that candle and then we're inside that candle'"),
           "horizon": "corpus: 9YVBe-20Hdg 'we're just rangebound' / ES-R3ByDYrY 'Is price more likely to go "
                      "to previous day high or previous day low' (next session vs the day's range)",
           "min_session_bars": "declared-before-run: harness example_rate stub-day filter n_m1 > 600",
           "null_grid": "declared-before-run (audit): README trap 9 (events all at one NY clock point -> "
                        "hold the clock) + vault Concept Campaign 2026-09-23 lesson 3; the any-minute null "
                        "is offset on all days (three-candle-outcomes NEGATIVE -1.78pp)"}
    p = cl.write_result(CID, which, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="TTrades update 2026-10-07 positive inside-day rule; prior "
                        "no-displacement gate reading untouched. Monthly nested-inside variant not tested. "
                        "AUDIT rerun: null changed from any-minute moments to other session closes. "
                        "Absolute distances kept: lag-1 volatility clustering (quiet day -> quiet next "
                        "day) is NOT removed, so a positive diff would not be inside-bar-specific.")
    print(p)


if __name__ == "__main__":
    run(sys.argv[1])
