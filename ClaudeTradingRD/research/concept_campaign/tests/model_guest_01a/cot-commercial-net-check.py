"""cot-commercial-net-check — COT commercial net position vs its 12-month midpoint,
read at each new quarter, as a directional filter (guest: The MMXM Trader, Ibw4saRtYMk).

Operationalisation (declared before the first run):
  * Data: CFTC legacy futures-only COT, COMEX gold (contract 088691) — "the individual
    futures contract, never the dollar index / cross". Downloaded 2026-09-23 from
    https://www.cftc.gov/files/dea/history/deacotYYYY.zip into data/ (see data/raw).
  * At each quarter start (first calendar day of Jan/Apr/Jul/Oct), take the reports
    whose as-of date is <= quarter start - 10 days (release latency: Tuesday data are
    published Friday; 10 days also clears the Dec-2018 shutdown backlog), take the last
    52 weeks of commercial NET (long - short), split its range in half: latest net above
    the midpoint = net long -> bullish quarter, below -> bearish.
  * Baseline book (direction-neutral): every NY trading day, one LONG and one SHORT row
    decided at the prior daily close (18:00 NY roll), stop 1.0 x ATR14(1D), 2R target,
    hold one trading day (1380 M1 bars, hold_basis="bars" so weekends do not eat it).
  * Gate: row direction == the quarter's COT reading. gated - complement = twice the
    directional value of the reading. Cluster = quarter (the reading is one decision per
    quarter), so effective n is the number of quarters.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

HERE = Path(__file__).resolve().parent
COT = pd.read_csv(HERE / "data" / "cot_gold_088691_legacy_futures_only.csv", parse_dates=["as_of"])

LAG_DAYS = 10
WINDOW_DAYS = 365
ATR_N = 14
STOP_ATR = 1.0
RR = 2.0
HOLD = "1380min"


def quarter_reading(qstart: pd.Timestamp):
    ref = qstart - pd.Timedelta(days=LAG_DAYS)
    w = COT[(COT.as_of <= ref) & (COT.as_of > ref - pd.Timedelta(days=WINDOW_DAYS))]
    last = w.iloc[-1]
    mid = (w.comm_net.max() + w.comm_net.min()) / 2.0
    # release estimate: as-of Tuesday + 3 days, 15:30 New York
    rel = (pd.Timestamp(last.as_of) + pd.Timedelta(days=3, hours=15, minutes=30)).tz_localize(
        "America/New_York").tz_convert("UTC")
    return (1 if last.comm_net > mid else -1), rel, float(last.comm_net), float(mid)


def next_trading_date(dec_utc: pd.DatetimeIndex) -> pd.DatetimeIndex:
    d = (cl.to_ny(dec_utc) + pd.Timedelta(hours=7)).tz_localize(None).normalize()
    wd = d.weekday
    return d + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    pc = d["close"].shift(1)
    tr = np.maximum(d["high"] - d["low"], np.maximum((d["high"] - pc).abs(), (d["low"] - pc).abs()))
    atr = tr.rolling(ATR_N, min_periods=ATR_N).mean()
    ok = atr.notna().to_numpy()
    dec = pd.DatetimeIndex(d["close_time"])[ok]
    atr = atr.to_numpy()[ok]
    nd = next_trading_date(dec)
    qstart = pd.DatetimeIndex([pd.Timestamp(x.year, 3 * ((x.month - 1) // 3) + 1, 1) for x in nd])
    cache = {q: quarter_reading(q) for q in qstart.unique()}
    qdir = np.array([cache[q][0] for q in qstart])
    rel = pd.DatetimeIndex([cache[q][1] for q in qstart])
    qid = np.array([f"{q.year}Q{(q.month - 1) // 3 + 1}" for q in qstart])
    rows = []
    for sgn in (1, -1):
        rows.append(pd.DataFrame({
            "decision_time": dec,
            "available_at": pd.DatetimeIndex(np.maximum(dec.asi8, rel.asi8), tz="UTC"),
            "direction": sgn, "stop_dist": STOP_ATR * atr, "rr": RR,
            "quarter": qid, "cot_dir": qdir, "cot_aligned": qdir == sgn,
            "cot_known_at": rel,
        }))
    ev = pd.concat(rows).sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("cot_net_check_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.quarter.nunique(), ev.groupby("quarter").cot_dir.first().value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "cot_aligned", mask_available_at="cot_known_at", max_hold=HOLD,
                       hold_basis="bars", cluster="quarter", claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
    op = {"rules": [
        "COMEX gold COT (CFTC legacy futures-only, code 088691), commercial net = long - short",
        "at each quarter start: reports with as-of <= quarter start - 10d; last 52 weeks; "
        "midpoint = (max+min)/2; latest net > midpoint -> bullish quarter else bearish",
        "baseline: every trading day a long AND a short row at the prior daily close, "
        "stop 1.0 x ATR14(1D), target 2R, hold 1380 M1 bars (one trading day)",
        "gate: row direction == quarter's COT reading; clustered by quarter"],
        "params": {"lag_days": LAG_DAYS, "window": "52 weeks", "atr_n": ATR_N,
                   "stop_atr": STOP_ATR, "rr": RR, "max_hold": HOLD, "hold_basis": "bars",
                   "contract": "088691 COMEX gold, legacy futures-only"}}
    src = {"lag_days": "declared-before-run: CFTC publishes Tuesday data on Friday; 10 days covers the Dec-2018 shutdown delay",
           "window": "corpus: Ibw4saRtYMk 'take the last twelve months of COT data, split that range in half'",
           "atr_n": "declared-before-run: standard 14-day ATR for a volatility-scaled stop",
           "stop_atr": "declared-before-run: 1 daily ATR stop for a one-day directional hold",
           "rr": "declared-before-run: 2R, the campaign's phase-3 default target",
           "max_hold": "declared-before-run: one trading day per daily decision",
           "hold_basis": "declared-before-run: trading-time hold so Friday decisions are not eaten by the weekend (trap 7)",
           "contract": "corpus: Ibw4saRtYMk 'individual currency futures contract ... never the dollar index'"}
    notes = ("Quarterly reading => ~42 independent decisions 2016-2026; clustered by quarter, so "
             "effective n is the quarter count and the test cannot reach the 200 floor. "
             "The pairing with 'an old low in HTF discount as the smart money reversal' is not "
             "added: tested here is the COT filter alone, as a directional bias on a "
             "direction-neutral daily book. COT data file lives beside this script.")
    p = cl.write_result("cot-commercial-net-check", None, res, operationalization=op,
                        params_source=src, script=__file__, notes=notes, probe=probe)
    print(p)
