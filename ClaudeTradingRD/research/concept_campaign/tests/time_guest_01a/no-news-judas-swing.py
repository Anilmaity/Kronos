"""no-news-judas-swing (guest: Day Trading Rauf, qFtfD09Vv3E).

"you'll usually find that a Judas swing is much likely to occur on 9 30 when we have no
news ... at 9 30 Judas swing usually works better when there is no news because there
is no volatility injection apart from the 930."

gate_test, claim '+', declared before the run:
  baseline  a mechanical 09:30 fade on every NY trading day: Judas leg = 09:30-09:45 NY
            (first 15 M1 bars; >= 10 present); direction = opposite its sign
            (09:44 close - 09:30 open); decide at 09:45 NY, enter the next M1 open;
            stop beyond the Judas leg's extreme (its high for a short, low for a long);
            target 2R; time exit at 16:00 NY (375 min: the 09:30-to-close leg).
  gate      NO-NEWS day. No economic calendar exists in the certified data, so a
            high-impact day = (a) a derived NFP Friday (BLS reference-week rule, same
            rule as risk_guest_02b/pre-event-avoidance-rule) OR (b) an 08:30 NY
            volatility injection: the 08:30 5m candle's range >= 3x the median 5m
            range of the prior 288 5m bars. Both are known by 08:35, before the 09:45
            decision. 10:00 and 14:00 releases cannot be seen before the decision
            without reading future prices, so they stay in the 'no-news' arm
            (attenuates toward 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, show  # noqa: E402

CID = "no-news-judas-swing"
JUDAS_MIN = 15
MIN_COVER = 10
RR = 2.0
MAX_HOLD = "375min"
SPIKE_MULT = 3.0
MED_BARS = 288
TZ = "America/New_York"


def nfp_dates(y0=2015, y1=2026):
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            ry, rm = (y, m - 1) if m > 1 else (y - 1, 12)
            d12 = pd.Timestamp(ry, rm, 12)
            sat = d12 + pd.Timedelta(days=(5 - d12.dayofweek) % 7)
            fri = sat + pd.Timedelta(days=20)
            if fri.month == 7 and fri.day in (3, 4):
                fri = fri - pd.Timedelta(days=1)
            if fri.month == 1 and fri.day == 1:
                fri = fri + pd.Timedelta(days=7)
            out.append(fri.normalize())
    s = set(out)
    for bad in ("2025-10-03", "2025-11-07", "2025-12-05"):
        s.discard(pd.Timestamp(bad))
    s.update({pd.Timestamp("2025-11-20"), pd.Timestamp("2025-12-16")})
    return sorted(s)


NFP_DAYS = frozenset(d.strftime("%Y-%m-%d") for d in nfp_dates())


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "news_known_at", "no_news"]
    empty = pd.DataFrame(columns=cols)
    if len(m1) < 500:
        return empty
    t = pd.DatetimeIndex(m1.index)
    mod = cl.ny_minute_of_day(t)
    # Judas leg 09:30-09:45
    sel = (mod >= 570) & (mod < 570 + JUDAS_MIN)
    if not sel.any():
        return empty
    day = t[sel].tz_convert(TZ).normalize()
    g = pd.DataFrame({"o": m1["open"].to_numpy()[sel], "h": m1["high"].to_numpy()[sel],
                      "l": m1["low"].to_numpy()[sel], "c": m1["close"].to_numpy()[sel]}, index=day)
    J = g.groupby(level=0).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                               n=("o", "size"))
    J = J[J["n"] >= MIN_COVER]
    # 08:30 volatility injection
    F = cl.build_bars(m1, "5min")
    rng = (F["high"] - F["low"]).to_numpy()
    med = pd.Series(rng).shift(1).rolling(MED_BARS, min_periods=MED_BARS // 2).median().to_numpy()
    fst = pd.DatetimeIndex(F.index).tz_convert(TZ)
    f830 = (fst.hour == 8) & (fst.minute == 30)
    spike = pd.Series(rng[f830] >= SPIKE_MULT * med[f830], index=fst[f830].normalize())
    spike_ok = pd.Series(np.isfinite(med[f830]), index=fst[f830].normalize())
    spike = spike[spike_ok.to_numpy()]
    spike = spike[~spike.index.duplicated()]
    J = J[J.index.isin(spike.index)]
    if J.empty:
        return empty
    nfp = np.array([d.strftime("%Y-%m-%d") in NFP_DAYS for d in J.index])
    news = spike.reindex(J.index).to_numpy(bool) | nfp
    dec = (J.index + pd.Timedelta(minutes=570 + JUDAS_MIN)).tz_convert("UTC")
    known = (J.index + pd.Timedelta(minutes=515)).tz_convert("UTC")      # 08:35 NY
    move = np.sign(J["c"].to_numpy() - J["o"].to_numpy())
    out = pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": -move,
                        "stop_px": np.where(move > 0, J["h"].to_numpy(), J["l"].to_numpy()),
                        "rr": RR, "news_known_at": known, "no_news": ~news})
    last_t = t[-1] + pd.Timedelta("1min")
    out = out[(out["direction"] != 0) & (out["decision_time"] <= last_t)]
    return out.reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "no-news share", ev["no_news"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "no_news", mask_available_at="news_known_at", max_hold=MAX_HOLD, claim="+")
    show(res)
    op = {"rules": [
        "each NY trading day: Judas leg = M1 bars 09:30-09:44 NY (>= 10 present); direction = opposite "
        "sign(09:44 close - 09:30 open); decide 09:45 NY, enter the next M1 open",
        "stop at the Judas leg's extreme on the move side (its high for a short, low for a long); target 2R; "
        "time exit 375 min (16:00 NY)",
        "gate (pass) = no-news day; news day = derived NFP Friday OR 08:30 NY 5m candle range >= 3x the median "
        "range of the prior 288 5m bars (known 08:35 NY)",
        "claim '+': the 09:30 fade does better on no-news days than on news days"],
        "params": {"judas_min": JUDAS_MIN, "min_cover": MIN_COVER, "rr": RR, "max_hold": MAX_HOLD,
                   "spike_mult": SPIKE_MULT, "median_bars": MED_BARS, "nfp_rule": "BLS reference-week rule"}}
    src = {"judas_min": "declared-before-run: the corpus gives no duration for the swing; first 15 minutes (three 5m bars) off 09:30",
           "min_cover": "declared-before-run: 2/3 of the leg's M1 bars present",
           "rr": "declared-before-run: no target size stated ('opposite end of the range'); 2R as in the phase-3 books",
           "max_hold": "corpus: concept measurable 'range of the 09:30-to-close leg' -> exit 16:00 NY",
           "spike_mult": "declared-before-run: same 3x 08:30 footprint proxy as entry_own_04a/ignore-news-wick-in-range-fib",
           "median_bars": "declared-before-run: prior 24h of 5m bars (288)",
           "nfp_rule": "declared-before-run: BLS Employment Situation schedule (as risk_guest_02b/pre-event-avoidance-rule)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Gold, not NASDAQ. No calendar data: news days are NFP (derived) plus an "
                        "observed 08:30 volatility injection, which is his own mechanism ('no volatility injection apart "
                        "from the 930'). 10:00/14:00 releases are in the no-news arm (attenuation toward 0).")
    print("wrote", p)
