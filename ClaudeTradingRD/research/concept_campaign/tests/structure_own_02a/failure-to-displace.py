"""failure-to-displace (TTrades own voice, contested) — batch structure_own_02a.

The yaml's own formula: bearish_failure_to_displace := high[i] > level AND close[i] < level
AND close[i] inside the previous period's range (bullish mirror); "the lack of
[displacement] on each side leans in the other direction". Execution: bias opposite the
failed level, stop beyond the extreme of the failed probe, target the opposite
previous-period level. Level = the previous period's high/low (the formula's
"previous period's range"); a candle that takes BOTH sides is excluded (method_spec §2.3:
both sides taken -> no bias).
Readings (the two scales the corpus uses):
  a  15m (the yaml's htf 15m): candle i takes candle i-1's high, closes back inside
     i-1's range, does not take i-1's low -> short at the next M1 open, stop = high[i],
     target = low[i-1]; 150-min exit (phase-3 15m).
  b  daily ("He prefers the failure to be measured against a HIGHER-timeframe low/high";
     "At the daily scale the same failure appears"): trading day (18:00 NY) takes the
     previous day's high, closes back inside its range, does not take its low -> short
     at the next M1 open, stop = the day's high, target = the previous day's low; exit
     after 1380 trading minutes (one trading day). Stub days (< 50% of the median M1
     count) are skipped on either side.
Both trade_tests (full entry/stop/target), claim '+'.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "failure-to-displace"


def ftd(b, min_cov=None):
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ph, pl = np.roll(h, 1), np.roll(l, 1)
    bear = (h > ph) & (c < ph) & (c > pl) & (l >= pl)
    bull = (l < pl) & (c > pl) & (c < ph) & (h <= ph)
    ok = np.ones(len(b), bool)
    ok[0] = False
    if min_cov is not None:
        nm = b["n_m1"].to_numpy(float)
        med = np.median(nm)
        good = nm >= min_cov * med
        ok &= good & np.roll(good, 1)
    sel = ok & (bear | bull)
    d = np.where(bull, 1, -1)[sel]
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[sel])
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d.astype(int),
                         "stop_px": np.where(bull, l, h)[sel],
                         "target_px": np.where(bull, ph, pl)[sel]}).reset_index(drop=True)


def detect_a(m1):
    return ftd(cl.build_bars(m1, "15min"))


def detect_b(m1):
    b = cl.build_bars(m1, "1D")
    ev = ftd(b, min_cov=0.5)
    # a day's median-M1 coverage depends on the whole sample; in a probe slice it is
    # computed on the slice — same days pass on real data (median is stable).
    return ev


def main():
    common_src = {"level": "corpus yaml: 'bearish_failure_to_displace := high[i] > level AND close[i] < level AND close[i] inside the previous period's range'",
                  "one_sided": "method_spec: §2.3 'Both sides taken -> no bias'",
                  "target": "corpus yaml execution: targets 'the opposite previous-period level or swing point'"}
    for reading, det, key, hold, hb, xr, xp, xs in (
            ("a", detect_a, "ftd_15m", "150min", "clock",
             ["15m bars: candle takes the prior candle's high, closes below it and above the "
              "prior low, does not take the prior low -> short (bullish mirror)",
              "decide at its close, enter next M1 open, stop = its high, target = prior "
              "candle's low, exit after 150 min"],
             {"tf": "15min", "max_hold": "150min"},
             {"tf": "corpus yaml timeframes: htf 15m/5m", "max_hold": "phase3: 15m book 150-min exit"}),
            ("b", detect_b, "ftd_1d", "1380min", "bars",
             ["trading-day bars (18:00 NY): day takes the previous day's high, closes back "
              "inside its range, does not take its low -> short (bullish mirror)",
              "decide at the day's close, enter next M1 open, stop = the day's high, target = "
              "previous day's low, exit after 1380 trading minutes",
              "skip days (either side) with fewer than 50% of the median M1 count"],
             {"tf": "1D", "max_hold": "1380min", "hold_basis": "bars", "min_coverage": 0.5},
             {"tf": "corpus yaml: 'He prefers the failure to be measured against a HIGHER-timeframe low/high' / 'At the daily scale the same failure appears'",
              "max_hold": "declared-before-run: one trading day (the next-day model)",
              "hold_basis": "declared-before-run: trading time across the daily halt",
              "min_coverage": "declared-before-run: README trap 6 stub sessions"})):
        ev = cl.cache_frame(f"{key}_v1", lambda d=det: d(cl.load_m1()))
        probe = cl.probe_lookahead(det, ev, lookback="60D" if reading == "b" else "10D")
        res = cl.trade_test(ev, max_hold=hold, hold_basis=hb)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res, operationalization={
            "rules": xr, "params": {**xp, "level": "previous period high/low",
                                    "one_sided": True, "target": "opposite previous-period level"}},
            params_source={**common_src, **xs}, script=__file__, probe=probe,
            notes="The premium/discount retrace preference ('a lot of times') and the "
                  "broadening-formation branch are not modelled.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
