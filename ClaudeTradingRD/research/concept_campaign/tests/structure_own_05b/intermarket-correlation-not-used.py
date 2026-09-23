"""intermarket-correlation-not-used (contested) -> gate_test.

Concept (bMkRomKEunU / u8bnmaih_hA): he does NOT derive bias from the dollar against gold -
"the dollar no longer correlates usefully with gold"; the correlation is not strong enough
to act on. measurable: "whether adding a DXY filter changes outcomes on the same trade set".

Test: the dollar filter he rejects, applied to a fixed gold book. claim '+' is the
mainstream-ICT claim ("dollar-agreeing gold trades do better"); THIS concept predicts NULL.
So NULL = concept supported, EDGE = concept refuted (the filter helps), NEGATIVE = the
filter hurts (also contradicts 'no usable correlation', in the other direction).

Operationalisation (declared before the first run):
  * Baseline book: bare 1h CISD (phase-3 rung 0: series_open level, 2/2 swings,
    max_wait 3, stop at the protected swing, 2R, 10h hold).
  * Dollar proxy: EURUSD INVERTED (no DXY series exists in the campaign data; EURUSD is
    ~57% of the DXY basket). Daily EURUSD candles on the 17:00 NY forex roll, built from
    OANDA H1 (index = bar start); a day is usable only when complete (>= 18 H1 bars) and
    is read strictly as-of its close (last H1 start + 1h).
  * Dollar bias = direction of the last COMPLETED EURUSD daily candle (EURUSD up = dollar
    down = gold long). Rows whose EURUSD day is a doji or unavailable are dropped.
  * Gate = gold trade direction agrees with the dollar-implied gold direction.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from _common import show  # noqa: E402

CID = "intermarket-correlation-not-used"
EUR_H1 = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/eur_h1_full.parquet"
MAX_HOLD = "10h"
_EURD = None
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "usd_avail", "agree"]


def eur_daily() -> pd.DataFrame:
    global _EURD
    if _EURD is None:
        h = pd.read_parquet(EUR_H1).sort_index()
        ny = h.index.tz_convert("America/New_York")
        day = (ny + pd.Timedelta(hours=7)).tz_localize(None).normalize()   # 17:00 NY roll
        g = h.assign(end=h.index + pd.Timedelta(hours=1)).groupby(day.values)
        d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(),
                          "close_time": g["end"].max(), "n_h1": g["open"].size()})
        _EURD = d[d["n_h1"] >= 18].sort_values("close_time").reset_index(drop=True)
    return _EURD


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=COLS)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    w = eur_daily()
    ct = pd.DatetimeIndex(w["close_time"]).as_unit("ns").asi8
    k = np.searchsorted(ct, close.as_unit("ns").asi8, side="right") - 1
    ok = k >= 0
    kk = np.clip(k, 0, None)
    chg = (w["close"].to_numpy() - w["open"].to_numpy())[kk]
    ok &= chg != 0
    gold_dir = np.where(chg > 0, 1, -1)          # EURUSD up -> dollar down -> gold up
    out["usd_avail"] = pd.DatetimeIndex(w["close_time"].to_numpy()[kk]).tz_convert("UTC") \
        if pd.DatetimeIndex(w["close_time"]).tz is not None else \
        pd.DatetimeIndex(w["close_time"].to_numpy()[kk]).tz_localize("UTC")
    out["agree"] = (gold_dir == out["direction"].to_numpy())
    out = out[ok].copy()
    out["available_at"] = out["decision_time"]
    return out.reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_cisd1h_eurD", lambda: detect(cl.load_m1()))
    print(len(ev), ev["agree"].mean(), (ev["usd_avail"] <= ev["decision_time"]).all())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "agree", mask_available_at="usd_avail", max_hold=MAX_HOLD)
    show(res)
    op = {"rules": [
        "baseline: bare 1h CISD (series_open level, 2/2 swings, max_wait 3), stop at the "
        "protected swing, 2R, 10h hold",
        "dollar proxy: EURUSD inverted; daily candles on the 17:00 NY roll from H1, complete "
        "days only (>= 18 H1 bars), read as-of close",
        "gate: gold trade direction == direction implied by the last completed EURUSD day "
        "(EURUSD up -> gold long); doji / missing days dropped",
        "claim '+' = the dollar filter helps (mainstream ICT); the concept predicts NULL"],
        "params": {"baseline": "cisd_1h_mw3", "rr": 2.0, "max_hold": MAX_HOLD,
                   "proxy": "EURUSD inverted", "dollar_tf": "1D (17:00 NY roll)"}}
    src = {"baseline": "phase3: rung-0 1h CISD locked config (conjunction_preregistration "
                       "1.8-1.13)",
           "rr": "phase3: 2R primary target", "max_hold": "phase3: 10 entry-TF bars",
           "proxy": "declared-before-run: no DXY series in the campaign data; EURUSD "
                    "(~57% of DXY) inverted, per fetch_correlated.py",
           "dollar_tf": "declared-before-run: he rejects the dollar as a DAILY-bias input "
                        "('do not derive bias from DXY against gold'); last completed day"}
    notes = ("Concept asserts no usable dollar-gold correlation, so NULL supports it and "
             "EDGE/NEGATIVE contradict it. Proxy caveat: EURUSD-inverted, not DXY. The weekly "
             "dollar gate was already tested under dollar-gate-for-fx (reading a).")
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe, notes=notes))
