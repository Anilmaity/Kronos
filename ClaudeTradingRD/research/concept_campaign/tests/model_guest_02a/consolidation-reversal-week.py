"""consolidation-reversal-week (guest: AM Trades wGYde-h84cs; variant McJflkKuvrI).
status: contested -> two readings, differing in WHICH levels Thursday must manipulate.

Shared rules (declared before the first run):
  * daily candles on the 18:00 NY roll; weekday = session date; stub sessions (< 600
    M1 bars) break the week (skipped).
  * Mon-Wed consolidation = "no expansion through Wednesday": Tuesday closes inside
    Monday's high-low and Wednesday closes inside Tuesday's high-low (a doji or a
    retracement day still qualifies).
  * Thursday must manipulate ONE side and close back inside (a two-sided Thursday is
    skipped: no rule for it) and close inside the Mon-Wed range.
  * confirmation: an hourly CISD in the reversal direction inside Thursday's session
    (phase-3 locked 1h CISD: series_open, 2/2 swings, max_wait 3), extreme and confirming
    close both inside Thursday.
  * trade Friday (the preferred day): decide at the Thursday close, stop beyond the
    Thursday extreme, target the other side of the Mon-Wed consolidation range, exit at
    the Friday close (23h of trading time).
Readings:
  a (AM Trades, definition): Thursday sweeps the EXTERNAL high/low of the Mon-Wed range.
  b (variant, McJflkKuvrI): Thursday takes out MONDAY's extreme AND the previous day's
    (Wednesday's) extreme and closes back beyond both.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

MIN_M1 = 600
MAX_HOLD = "23h"


def make_detect(reading):
    def detect(m1):
        cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
        d = cl.build_bars(m1, "1D")
        d = d[d["n_m1"] >= MIN_M1].copy()
        sd = pd.DatetimeIndex(d["trading_day"]) + pd.Timedelta(days=1)
        d["dow"] = sd.dayofweek
        d["monday"] = sd - pd.to_timedelta(sd.dayofweek, unit="D")
        d["open_t"] = pd.DatetimeIndex(d.index).tz_convert("UTC")
        b = cl.build_bars(m1, "1h")
        ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                         left=2, right=2, max_wait=3, min_series=1)
        if not ev.empty:
            cc = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
            xt = pd.DatetimeIndex(ev["extreme_time"]).tz_convert("UTC")
            cdir = np.where(ev["direction"] == "bullish", 1, -1)
        rows = []
        for mon, g in d.groupby("monday"):
            days = {int(k): r for k, r in zip(g["dow"], g.itertuples())}
            if not all(k in days for k in (0, 1, 2, 3)):
                continue
            M, T, W, R = days[0], days[1], days[2], days[3]
            if not (M.low <= T.close <= M.high and T.low <= W.close <= T.high):
                continue
            rhi, rlo = max(M.high, T.high, W.high), min(M.low, T.low, W.low)
            if reading == "a":
                up_lvls, dn_lvls = [rhi], [rlo]
            else:
                up_lvls, dn_lvls = [M.high, W.high], [M.low, W.low]
            took_hi = all(R.high > x for x in up_lvls) and all(R.close < x for x in up_lvls)
            took_lo = all(R.low < x for x in dn_lvls) and all(R.close > x for x in dn_lvls)
            swept_hi_any, swept_lo_any = R.high > rhi, R.low < rlo
            if took_hi == took_lo:
                continue
            if (took_hi and swept_lo_any) or (took_lo and swept_hi_any):
                continue                          # two-sided Thursday: no rule
            if not (rlo < R.close < rhi):
                continue
            direction = -1 if took_hi else 1
            if ev.empty:
                continue
            t0, t1 = R.open_t, pd.Timestamp(R.close_time).tz_convert("UTC")
            ok = (cdir == direction) & (cc > t0) & (cc <= t1) & (xt >= t0)
            if not ok.any():
                continue
            rows.append({"decision_time": t1, "available_at": t1, "direction": direction,
                         "stop_px": R.low if direction == 1 else R.high,
                         "target_px": rhi if direction == 1 else rlo})
        if not rows:
            return pd.DataFrame(columns=cols)
        out = pd.DataFrame(rows, columns=cols)
        for c in ("decision_time", "available_at"):
            out[c] = pd.DatetimeIndex(out[c]).tz_convert("UTC")
        return out.sort_values("decision_time").reset_index(drop=True)
    return detect


if __name__ == "__main__":
    for reading in sys.argv[1:] or ["a", "b"]:
        fn = make_detect(reading)
        ev = cl.cache_frame(f"consrev_{reading}_v1", lambda fn=fn: fn(cl.load_m1()))
        print(reading, len(ev), ev["direction"].value_counts().to_dict() if len(ev) else {})
        probe = cl.probe_lookahead(fn, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis="bars")
        for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "exposure_bars"):
            print(" ", k, res.get(k))
        sweep = ("Thursday sweeps the Mon-Wed external high (bearish) / low (bullish) and "
                 "closes back inside" if reading == "a" else
                 "Thursday takes out Monday's AND Wednesday's high (bearish) / low (bullish) "
                 "and closes back beyond both")
        op = {"rules": [
            "daily candles on the 18:00 NY roll; sessions < 600 M1 bars skipped",
            "consolidation: Tue close inside Mon range and Wed close inside Tue range",
            sweep, "one-sided Thursday only; Thursday close inside the Mon-Wed range",
            "confirmation: 1h CISD (phase-3 locked config) in the reversal direction with "
            "extreme and confirming close inside Thursday's session",
            "enter at the Thursday close (Friday trade); stop beyond Thursday's extreme; "
            "target the other side of the Mon-Wed range; exit after 23h of trading time"],
            "params": {"consolidation": "Tue close in Mon range & Wed close in Tue range",
                       "sweep_levels": "Mon-Wed external" if reading == "a"
                       else "Monday + previous day",
                       "cisd": "1h series_open 2/2 max_wait 3", "entry_day": "Friday",
                       "stop": "Thursday extreme", "target": "opposite side of Mon-Wed range",
                       "max_hold": MAX_HOLD, "hold_basis": "bars",
                       "min_m1_per_session": MIN_M1}}
        src = {"consolidation": "corpus: McJflkKuvrI 'consolidation Monday, Tuesday and "
                                "Wednesday' / 'no expansion through Wednesday' "
                                "(declared-before-run: expansion = a close beyond the "
                                "previous day's range)",
               "sweep_levels": ("corpus: wGYde-h84cs 'I'm marking out the external high and "
                                "low'" if reading == "a" else
                                "corpus: McJflkKuvrI Thursday takes out Monday's high and the "
                                "previous day's high and closes back below both"),
               "cisd": "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked 1h "
                       "CISD); corpus: McJflkKuvrI hourly change in state of delivery",
               "entry_day": "corpus: McJflkKuvrI Friday is the continuation day he prefers",
               "stop": "corpus: YAML execution.stop 'beyond the Thursday extreme'",
               "target": "corpus: McJflkKuvrI 'the other side of the consolidation range'",
               "max_hold": "declared-before-run: the Friday session (18:00-17:00 NY = 23h)",
               "hold_basis": "declared-before-run: trading-time hold so weekend-straddling "
                             "controls get the same exposure (README trap 7)",
               "min_m1_per_session": "declared-before-run: drop stub sessions (trap 6)"}
        p = cl.write_result("consolidation-reversal-week", reading, res,
                            operationalization=op, params_source=src, script=__file__,
                            probe=probe,
                            notes="HTF PD-array non-engagement precondition and the weekly "
                                  "bias are not operationalised (no rule in the unit).")
        print(" ", p)
