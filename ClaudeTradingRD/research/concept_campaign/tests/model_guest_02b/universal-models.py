"""universal-models (guest: GxTradez, 3eVxTV_7L2U).

Of the three frameworks, the order-pairing / manipulation-range model is the one
whose key level and target are both mechanically named: key level = a range
high/low, target = the opposing side of the range. The concept says a framework
alone is NOT a trade: it must be confirmed by a swing formation (candle-2
closure) AND by SMT. All three pieces are operationalised:

  range      = the prior trading day's high/low (18:00 NY roll)
  key level  = first 1h candle of the day to trade through PDH (PDL)
  swing      = that 1h candle is a C2: takes the prior 1h candle's high and closes
               back inside it, and also closes back below PDH (above PDL)
  SMT        = silver (XAG_USD H1) has NOT taken its own prior-day high (low)
               by the close of that same hour
  trade      = enter at the C2 close, stop at the C2 extreme, target = PDL (PDH)

The two FVG-based frameworks (internal->external, external->internal) have no
rule for choosing among gaps and are not separately tested (see notes).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
MIN_PRIOR_DAY_M1 = 600
MAX_HOLD = "24h"

_XAG = pd.read_parquet(XAG_PATH)
_XAG = _XAG[_XAG.index >= "2015-12-01"]
_XAG_TD = cl.trading_day(_XAG.index)
_XAG_CLOSE = _XAG.index + pd.Timedelta("1h")


def _xag_state(times):
    """For each decision time t (a 1h close): XAG's trading-day running high/low
    through the last XAG hour closed by t, and XAG's prior-trading-day high/low."""
    x = _XAG.copy()
    x["td"] = _XAG_TD
    x["close_time"] = _XAG_CLOSE
    x["run_hi"] = x.groupby("td")["high"].cummax()
    x["run_lo"] = x.groupby("td")["low"].cummin()
    day = x.groupby("td").agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"))
    day["pdh"] = day["hi"].shift(1)
    day["pdl"] = day["lo"].shift(1)
    day["pn"] = day["n"].shift(1)
    x = x.join(day[["pdh", "pdl", "pn"]], on="td")
    # the XAG row that closes exactly at t (same hour as the gold candle)
    ct = pd.DatetimeIndex(x["close_time"])
    pos = ct.get_indexer(pd.DatetimeIndex(times))
    out = pd.DataFrame(index=range(len(times)),
                       columns=["run_hi", "run_lo", "pdh", "pdl", "pn"], dtype=float)
    ok = pos >= 0
    out.loc[ok, :] = x.iloc[pos[ok]][["run_hi", "run_lo", "pdh", "pdl", "pn"]].to_numpy()
    return out


def detect(m1):
    h = cl.build_bars(m1, "1h")
    h = h[h["n_m1"] > 0].copy()
    h["td"] = cl.trading_day(h.index)
    day = h.groupby("td").agg(hi=("high", "max"), lo=("low", "min"), n=("n_m1", "sum"))
    day["pdh"], day["pdl"], day["pn"] = day["hi"].shift(1), day["lo"].shift(1), day["n"].shift(1)
    h = h.join(day[["pdh", "pdl", "pn"]], on="td")
    h["prev_run_hi"] = h.groupby("td")["high"].cummax().groupby(h["td"]).shift(1)
    h["prev_run_lo"] = h.groupby("td")["low"].cummin().groupby(h["td"]).shift(1)
    h["prev_run_hi"] = h["prev_run_hi"].fillna(-np.inf)
    h["prev_run_lo"] = h["prev_run_lo"].fillna(np.inf)
    ph, pl = h["high"].shift(1), h["low"].shift(1)
    okday = h["pn"] >= MIN_PRIOR_DAY_M1
    bear = (okday & (h["high"] > h["pdh"]) & (h["prev_run_hi"] <= h["pdh"])
            & (h["high"] > ph) & (h["close"] < ph) & (h["close"] < h["pdh"])
            & (h["close"] > h["pdl"]))
    bull = (okday & (h["low"] < h["pdl"]) & (h["prev_run_lo"] >= h["pdl"])
            & (h["low"] < pl) & (h["close"] > pl) & (h["close"] > h["pdl"])
            & (h["close"] < h["pdh"]))
    rows = []
    for d, m in ((-1, bear), (1, bull)):
        s = h[m.fillna(False)]
        rows.append(pd.DataFrame({
            "decision_time": pd.DatetimeIndex(s["close_time"]),
            "available_at": pd.DatetimeIndex(s["close_time"]),
            "direction": d,
            "stop_px": (s["high"] if d == -1 else s["low"]).to_numpy(),
            "target_px": (s["pdl"] if d == -1 else s["pdh"]).to_numpy(),
        }))
    ev = pd.concat(rows, ignore_index=True)
    xs = _xag_state(ev["decision_time"])
    smt_bear = (xs["run_hi"] <= xs["pdh"]) & (xs["pn"] >= 10)
    smt_bull = (xs["run_lo"] >= xs["pdl"]) & (xs["pn"] >= 10)
    smt = np.where(ev["direction"] == -1, smt_bear, smt_bull)
    smt = np.where(xs["run_hi"].isna().to_numpy() | xs["pdh"].isna().to_numpy(), False, smt)
    ev = ev[smt.astype(bool)].sort_values("decision_time").reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("univ_opr_pdhl_c2_smt_1h", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "range = prior trading day's high/low (18:00 NY roll); prior day needs >= 600 M1 bars",
        "key level: first 1h candle (UTC hourly) of the trading day whose high > PDH (low < PDL)",
        "swing formation: that candle is a C2 - high > prior 1h high and close back below it "
        "(mirror for lows) - and closes back inside the range (below PDH / above PDL)",
        "SMT: XAG_USD H1 running high of the same trading day through that hour <= XAG's "
        "prior-day high (bearish); mirror for bullish; missing XAG hour -> no event",
        "enter next M1 open after the C2 close; stop = C2 extreme; target = opposing side of "
        "the range (PDL for shorts, PDH for longs); exit after 24h wall clock",
        "control matched on NY time of day +/-30 min (sweeps cluster in session hours)"],
        "params": {"range": "prior trading day", "swing_tf": "1h", "smt_asset": "XAG_USD",
                   "min_prior_day_m1": MIN_PRIOR_DAY_M1, "max_hold": MAX_HOLD,
                   "ctrl_tod_tol_min": 30}}
    src = {"range": "corpus: 3eVxTV_7L2U order-pairing ranges 'key level = a range high or "
                    "range low; target = the opposing side of the range'; prior day chosen "
                    "(declared-before-run) as the mechanical range",
           "swing_tf": "corpus: 3eVxTV_7L2U 'It is simply when candle 2 closes back inside of "
                       "candle 1's range'; 1h from the concept's ltf list (declared-before-run)",
           "smt_asset": "declared-before-run: XAG_USD, the standard gold correlate "
                        "(method_spec §2.6)",
           "min_prior_day_m1": "declared-before-run: skip stub sessions (README trap 6)",
           "max_hold": "declared-before-run: one day; the target is a daily-range side",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 - concept is not about "
                               "timing but PDH/PDL sweeps cluster in session hours"}
    p = cl.write_result("universal-models", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Tested the order-pairing-range framework with both required "
                              "confirmations (C2 closure + XAG SMT). The internal->external "
                              "and external->internal FVG frameworks give no rule for which "
                              "gap is the key level, so they were not run.")
    print(p)
