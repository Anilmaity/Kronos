"""dollar-gate-for-fx — (batch model_own_04a). Contested; two readings.

reading a (gate_test) — the dollar-first gate as applied to GOLD (Rauf's variant:
  "analyse DXY before EURUSD or gold ... bullish dollar, so gold lower"; Ben's veto:
  "if the dollar doesn't agree with my position I am not interested"). Gold trades
  are taken only when the dollar's higher-timeframe read points the opposite way.
  Dollar proxy: EURUSD (the largest DXY component, ~58% weight; the campaign holds no
  DXY series) inverted. Dollar direction = direction of the last COMPLETED weekly
  EURUSD candle (Rauf: "Confirm on the DXY weekly which side the week is likely to
  expand toward"), read as-of its close. EURUSD up week = dollar bearish = gold long.
  Baseline book: bare 1h CISD (phase-3 rung 0), both directions, 2R, 10h hold.
  claim '+': dollar-agreeing gold setups beat dollar-opposed ones.
reading b — UNTESTABLE: the forex pair-selection procedure (rank currency futures,
  pair the strongest against the weakest, trade crosses while the dollar consolidates).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

EUR_H1 = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/eur_h1_full.parquet"
MAX_HOLD = "10h"
_EURW = None


def eur_weekly() -> pd.DataFrame:
    """EURUSD weekly candles on the forex week (Sunday 17:00 NY -> Friday 17:00 NY),
    built from H1; close_time = last H1 bar's end. Only complete weeks are usable
    because they are read strictly as-of close_time."""
    global _EURW
    if _EURW is None:
        h = pd.read_parquet(EUR_H1).sort_index()
        ny = h.index.tz_convert("America/New_York")
        tday = (ny + pd.Timedelta(hours=7)).tz_localize(None).normalize()   # 17:00 NY roll
        wk = tday.to_period("W-FRI")
        g = h.assign(end=h.index + pd.Timedelta(hours=1)).groupby(wk.values)
        w = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(),
                          "close_time": g["end"].max(), "n_h1": g["open"].size()})
        _EURW = w[w["n_h1"] >= 60].sort_values("close_time").reset_index(drop=True)
    return _EURW


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "usd_dir", "usd_avail", "agree"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    w = eur_weekly()
    ct = pd.DatetimeIndex(w["close_time"]).as_unit("ns").asi8
    k = np.searchsorted(ct, pd.DatetimeIndex(out["decision_time"]).as_unit("ns").asi8,
                        side="right") - 1
    ok = k >= 0
    out, k = out[ok].copy(), k[ok]
    eur_sign = np.sign(w["close"].to_numpy() - w["open"].to_numpy())[k]
    # stale guard: the governing week must be the one that just ended (<= 8 days old)
    age = pd.DatetimeIndex(out["decision_time"]) - pd.DatetimeIndex(w["close_time"].to_numpy()[k])
    keep = (eur_sign != 0) & (np.asarray(age <= pd.Timedelta(days=8)))
    out, eur_sign, k = out[keep].copy(), eur_sign[keep], k[keep]
    out["usd_dir"] = (-eur_sign).astype(int)              # EURUSD up = dollar down
    out["usd_avail"] = pd.DatetimeIndex(w["close_time"].to_numpy()[k])
    out["agree"] = out["direction"].to_numpy() == -out["usd_dir"].to_numpy()
    return out.reset_index(drop=True)


REASON_B = ("The forex pair-selection procedure (read DXY; if trending, pair it against the "
            "weakest/strongest currency future; if consolidating, drop dollar pairs and trade the "
            "cross of the strongest vs weakest non-dollar currency; exclude same-direction "
            "currencies) chooses WHICH FX pair to trade. The campaign trades one instrument, "
            "XAUUSD, and holds no DXY series, no currency futures and no FX crosses (only EURUSD "
            "H1/D1), so neither the ranking nor the cross/exotic trades can be formed; 'clean' vs "
            "'consolidating' dollar and 'how bullish' a currency is are also judged by eye.")


def run_a():
    ev = cl.cache_frame("dollargate_1h_cisd_eurw", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "agree", mask_available_at="usd_avail", max_hold=MAX_HOLD)
    op = {"rules": [
        "baseline: bare 1h CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming "
        "bar's close, enter next M1 open, stop at the protected swing, 2R, 10h max hold",
        "dollar direction = -sign(close - open) of the last COMPLETED EURUSD weekly candle "
        "(forex week, 17:00 NY roll, built from OANDA EURUSD H1), read as-of its close_time; "
        "doji weeks and weeks older than 8 days dropped",
        "gate: gold trade direction opposes the dollar (dollar bearish -> long gold); "
        "complement = trades the dollar veto removes"],
        "params": {"baseline_tf": "1h", "level_rule": "series_open", "swing": "2/2",
                   "max_wait": 3, "rr": 2.0, "max_hold": MAX_HOLD,
                   "dollar_proxy": "EURUSD inverted", "dollar_tf": "1W",
                   "dollar_rule": "last completed weekly candle body direction"}}
    src = {"baseline_tf": "phase3: rung-0 1h CISD book (calibrated)",
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config", "rr": "phase3: 2R (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "dollar_proxy": ("declared-before-run: no DXY series in the campaign; EURUSD is DXY's "
                            "largest component and the corpus's own proxy pair ('Your USD' = EURUSD)"),
           "dollar_tf": ("corpus: qFtfD09Vv3E 'monthly charts are monthly and weekly charts are "
                         "your most important to frame trading setups'"),
           "dollar_rule": ("declared-before-run: 'which way is it delivering' read from the "
                           "higher-timeframe candle; the corpus never mechanises 'agree'")}
    notes = ("EURUSD H1 read from m3_scalper/eur_h1_full.parquet (2010-2026-07-23), outside the "
             "probe's truncation but consumed only through close_time <= decision. The method spec "
             "(§2.6) records that TTrades himself does NOT use DXY for gold; this reading tests the "
             "guest (Rauf/Ben) variant that does.")
    p = cl.write_result("dollar-gate-for-fx", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties"):
        print("  ", k, res.get(k))


if __name__ == "__main__":
    what = sys.argv[1:] or ["a", "b"]
    if "a" in what:
        run_a()
    if "b" in what:
        print(cl.write_untestable("dollar-gate-for-fx", REASON_B, reading="b", script=__file__))
