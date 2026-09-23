"""ignore-news-wick-in-range-fib — "Exclude the news wick when fibbing the range" (0R61Y6Pn74Q).

Batch entry_own_04a. trade_test, claim '+': the entry the rule produces (premium of the
wick-EXCLUDED range after an 08:30 NY release spike, invalidated only if the excluded wick is
retaken) beats a matched random entry.

No release calendar exists in the certified data. The scheduled-release proxy is the clock
plus the footprint: the 5m candle opening 08:30 New York (the example's CPI slot and the US
data slot generally) with a range >= 3x the median 5m range of the prior 24h.

Operationalisation (declared BEFORE the first run):
  spike S = the 08:30 NY 5m candle, range >= 3 x median 5m range of the prior 288 candles.
  bearish case (the source trade): S's upper wick >= 0.5 of its range and S.high is the highest
    high of S and the 12 5m candles before it (the spike made the range extreme).
    WH = S.high (the excluded wick), AH = max(S.open, S.close) (the body, adjusted anchor).
  bullish case mirrors it on the lower wick.
  after S closes, on M1 until 12:00 NY: L = lowest low so far (the reversal low). Once
    AH - L >= S's range, the first M1 candle whose high reaches the adjusted range's 0.5
    (AH - 0.5*(AH-L), L as of the previous candle) -> short at its close. Cancel if WH trades
    first or that candle closes above WH.
  stop = WH (the rule's own invalidation); target = L (the reversal low); max_hold 6h.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "ignore-news-wick-in-range-fib"
P = {"spike_tf": "5min", "spike_clock_ny": "08:30", "spike_mult": 3.0, "median_bars": 288,
     "wick_share": 0.5, "extreme_lookback_bars": 12, "adjusted_anchor": "spike body",
     "min_range_spike_mult": 1.0, "fib_level": 0.5, "cutoff_ny": "12:00",
     "stop": "excluded wick extreme", "target": "reversal low/high", "max_hold": "6h"}


def detect(m1):
    b5 = cl.build_bars(m1, P["spike_tf"])
    o, h, l, c = (b5[k].to_numpy() for k in ("open", "high", "low", "close"))
    rng = h - l
    med = pd.Series(rng).rolling(P["median_bars"]).median().shift(1).to_numpy()
    ny = cl.to_ny(b5.index)
    is_slot = (ny.hour == 8) & (ny.minute == 30) & (ny.dayofweek < 5)
    b1 = cl.build_bars(m1, "1min")
    h1, l1, c1 = (b1[k].to_numpy() for k in ("high", "low", "close"))
    st1 = b1.index.asi8
    ct1 = pd.DatetimeIndex(b1["close_time"])
    ct5 = pd.DatetimeIndex(b5["close_time"])
    LB = P["extreme_lookback_bars"]
    rows = []
    for i in np.flatnonzero(is_slot):
        if i < LB or not np.isfinite(med[i]) or rng[i] <= 0:
            continue
        if rng[i] < P["spike_mult"] * med[i]:
            continue
        up_w = h[i] - max(o[i], c[i])
        dn_w = min(o[i], c[i]) - l[i]
        bear = up_w >= P["wick_share"] * rng[i] and h[i] > h[i - LB:i].max()
        bull = dn_w >= P["wick_share"] * rng[i] and l[i] < l[i - LB:i].min()
        if bear == bull:
            continue
        d = -1 if bear else 1
        WH = h[i] if bear else l[i]
        AH = max(o[i], c[i]) if bear else min(o[i], c[i])
        t0 = ct5[i]
        day_ny = cl.to_ny(pd.DatetimeIndex([t0]))[0]
        cut = (day_ny.normalize() + pd.Timedelta(P["cutoff_ny"] + ":00")).tz_convert("UTC")
        a = np.searchsorted(st1, t0.value, "left")
        z = np.searchsorted(st1, cut.value, "left")
        L = None
        for j in range(a, z):
            if (bear and h1[j] >= WH) or (bull and l1[j] <= WH):
                break                                   # excluded wick retaken: invalid
            if L is not None and abs(AH - L) >= P["min_range_spike_mult"] * rng[i]:
                eq = AH + P["fib_level"] * (L - AH)
                if (bear and h1[j] >= eq) or (bull and l1[j] <= eq):
                    rows.append((ct1[j], d, WH, L, t0))
                    break
            if bear:
                L = l1[j] if L is None else min(L, l1[j])
            else:
                L = h1[j] if L is None else max(L, h1[j])
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "t0"])
    ev["decision_time"] = pd.to_datetime(ev["decision_time"], utc=True)
    ev["available_at"] = ev["decision_time"]
    return ev[cols].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("news_wick_fib_0830_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "release proxy: the 08:30 NY 5m candle with range >= 3x the prior-24h median 5m range",
        "bearish: its upper wick >= half its range and its high tops the prior hour; bullish "
        "mirror on the lower wick",
        "adjusted anchor = spike body extreme (wick excluded); reversal extreme L tracked on M1 "
        "until 12:00 NY; once the adjusted range >= the spike range, enter on the first M1 "
        "touch of its 0.5 (premium for shorts)",
        "cancel if the excluded wick trades first; stop at the wick extreme; target L; 6h"],
        "params": P}
    src = {"spike_tf": "corpus: concept timeframes.ltf [5m] (0R61Y6Pn74Q)",
           "spike_clock_ny": "corpus: 0R61Y6Pn74Q release at 8:30 (CPI)",
           "spike_mult": "declared-before-run: no calendar in the data; a >=3x median 5m "
                         "range at 08:30 NY marks a release footprint",
           "median_bars": "declared-before-run: prior 24h of 5m candles",
           "wick_share": "threshold_fits: 0.5-of-range is the corpus's large-wick ceiling "
                         "(3eVxTV_7L2U 'a mechanical way to measure wick size')",
           "extreme_lookback_bars": "declared-before-run: the spike must top the prior hour",
           "adjusted_anchor": "corpus: 0R61Y6Pn74Q anchor on the body, ignoring the wick",
           "min_range_spike_mult": "declared-before-run: the reversal leg must be at least the "
                                   "spike's own size before the fib is drawn",
           "fib_level": "method_spec: §3.7 EQ 0.5 premium/discount divide",
           "cutoff_ny": "session_window_fit: NY AM block ends 12:00 NY",
           "stop": "corpus: invalidation 'Price trades back above the excluded wick'",
           "target": "declared-before-run: the reversal low (range extreme drawn to)",
           "max_hold": "declared-before-run: 6h (through the NY session)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Stated once in one trade. No economic calendar exists in the "
                              "certified data, so scheduled releases are proxied by the 08:30 "
                              "NY clock plus a >=3x range footprint (weekly claims and other "
                              "08:30 data qualify, not only CPI).")
    print(p)
