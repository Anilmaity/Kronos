"""Relative-strength reads for the pair-selection concepts of batch structure_own_05a
(currency-pairing-opposition, eurgbp-relative-strength-cross). Pure in the gold M1 slice.

Baseline book (the 'ordinary fractal model on the selected instrument' stand-in, exactly the
book dollar-gate-for-fx reading a used): bare 1h CISD - series_open level, 2/2 swing,
max_wait 3, decided at the confirming bar's close, stop at the protected swing, 2R, 10h.

Daily reads, each the previous-candle engine (method_spec §2.3) on the last COMPLETED
trading day (18:00-NY roll) before the CISD bar's own trading day:
  +1 = the day closed above the previous day's high, -1 = below its low, 0 = inside
       (consolidating / no directional read)
  usd      : -(EURUSD class)  (dollar proxy; the campaign holds no DXY - EURUSD is its
             largest component and the corpus's own 'your USD' pair)
  goldleg  : class of the XAU/EUR line (gold H1 close / EURUSD H1 close) - gold's own
             strength with the dollar factored out
  ratio    : class of the XAU/XAG line (gold H1 close / silver H1 close) - the metals
             'cross', bullish = gold stronger than silver
  gold, xag: the two instruments' own daily classes
Correlate H1 bars in the 17:00-NY hour (gold's halt) are dropped so a correlate day ends
when gold's does.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import H1, cl, closure_class, corr_h1, daily_from_h1, np, pd  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

MAX_HOLD = "10h"
MIN_H1 = 18          # a correlate / ratio day needs >= 18 hourly bars to be read
MAX_GAP_DAYS = 4     # the read must come from the session just before (weekend allowed)


def _line_daily(num_close: pd.Series, den_close: pd.Series) -> pd.DataFrame:
    j = pd.concat([num_close.rename("n"), den_close.rename("d")], axis=1, join="inner")
    r = (j["n"] / j["d"]).to_frame("open")
    r["high"] = r["low"] = r["close"] = r["open"]
    return daily_from_h1(r)


def daily_reads(m1: pd.DataFrame) -> pd.DataFrame:
    g1 = cl.build_bars(m1, "1h")
    eur = corr_h1("eur", m1, drop_halt_hour=True)
    xag = corr_h1("xag", m1, drop_halt_hour=True)
    gd = cl.build_bars(m1, "1D").set_index("trading_day")
    gd = gd[gd["n_m1"] > 600]
    ed = daily_from_h1(eur)
    ed = ed[ed["n_h1"] >= MIN_H1]
    xd = daily_from_h1(xag)
    xd = xd[xd["n_h1"] >= MIN_H1]
    gl = _line_daily(g1["close"], eur["close"])
    gl = gl[gl["n_h1"] >= MIN_H1]
    rt = _line_daily(g1["close"], xag["close"])
    rt = rt[rt["n_h1"] >= MIN_H1]
    out = pd.concat({
        "usd": -closure_class(ed), "goldleg": closure_class(gl), "ratio": closure_class(rt),
        "gold": closure_class(gd), "xag": closure_class(xd)}, axis=1, join="inner")
    # every read's availability = the latest close among its inputs that day
    ct = pd.concat([pd.to_datetime(ed["close_time"]), pd.to_datetime(xd["close_time"]),
                    pd.to_datetime(gl["close_time"]), pd.to_datetime(rt["close_time"]),
                    pd.to_datetime(gd["close_time"])], axis=1, join="inner").max(axis=1)
    out["avail"] = ct.reindex(out.index)
    return out.dropna().sort_index()


def cisd_book(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction",
                                     "stop_px", "rr", "bar_day"])
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0,
                         "bar_day": cl.trading_day(pd.DatetimeIndex(ev["confirm_time"]))})


def book_with_reads(m1: pd.DataFrame) -> pd.DataFrame:
    """CISD book with the previous completed day's reads attached (rows without a read
    from the immediately preceding session are dropped - never evaluated != passed)."""
    ev = cisd_book(m1)
    rd = daily_reads(m1)
    if ev.empty or rd.empty:
        return pd.DataFrame()
    days = rd.index.to_numpy()
    k = np.searchsorted(days, ev["bar_day"].to_numpy(), side="left") - 1   # strictly earlier day
    ok = k >= 0
    ev, k = ev[ok].reset_index(drop=True), k[ok]
    gap = (ev["bar_day"].to_numpy() - days[k]) / np.timedelta64(1, "D")
    r = rd.iloc[k].reset_index(drop=True)
    ev = pd.concat([ev, r], axis=1)
    ev = ev[(gap <= MAX_GAP_DAYS)].reset_index(drop=True)
    ev["read_avail"] = pd.DatetimeIndex(ev["avail"]).tz_convert("UTC")
    ev = ev[pd.DatetimeIndex(ev["read_avail"]) <= pd.DatetimeIndex(ev["decision_time"])]
    return ev.drop(columns=["avail", "bar_day"]).reset_index(drop=True)
