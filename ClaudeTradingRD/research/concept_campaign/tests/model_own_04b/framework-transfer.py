"""framework-transfer — trade_test.

Concept (yud7TpE2AMs): import the fractal-model framework seen on one asset onto a
correlated asset that does NOT itself show it, and trade the second asset's candles as
C2/C3 — but still require a retracement and a new continuation (new protected swing) on
the target asset; stop behind that swing; target the target asset's own objectives.

Operationalisation for gold (declared before the run). The source asset is XAG_USD
(silver), the correlate the method sanctions for gold (fetch_correlated.py, spec §2.6);
only OANDA H1 silver exists locally, so the framework timeframe is 1H (yaml htf 4H/1H):
  * hour H: silver's 1H candle is a C2 closure (§3.2) and gold's same 1H candle is NOT a
    C2 closure in either direction -> transfer: treat gold's hour H as C2;
  * hour H+1 is gold's C3: on gold 5m bars inside it, wait for a retracement below the
    C3 open (bullish; mirrored), then a 5m CISD (close through the first open of the
    down-close series that made the running low) = the new continuation / protected swing;
  * decide at that 5m close (must close by the end of hour H+1); stop = the running low;
    target = gold's hour-H (C2) high — the previous candle's extreme, spec §5.2 (skip if
    already beyond it); time exit 60 min.
Silver bars are read only when closed (hour H is used from H+1h on).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _helpers import c2_flags, cisd_after_sweep  # noqa: E402

XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
MAX_HOLD = "60min"
_XAG = {}


def xag_c2() -> pd.Series:
    if "s" not in _XAG:
        x = pd.read_parquet(XAG_PATH).sort_index()
        x.index = pd.DatetimeIndex(x.index).tz_convert("UTC")
        f = c2_flags(*(x[k].to_numpy(float) for k in ("open", "high", "low", "close")))
        _XAG["s"] = pd.Series(f, index=x.index)
    return _XAG["s"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    g = cl.build_bars(m1, "1h")
    go, gh, gl, gc = (g[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    gc2 = c2_flags(go, gh, gl, gc)
    gs = pd.DatetimeIndex(g.index)
    xs = xag_c2().reindex(gs).fillna(0).to_numpy().astype(int)
    f = cl.build_bars(m1, "5min")
    fo, fh, fl, fc = (f[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    fs = pd.DatetimeIndex(f.index)
    fct = pd.DatetimeIndex(f["close_time"])
    rows = []
    for i in np.flatnonzero((xs != 0) & (gc2 == 0)):
        if i + 1 >= len(g) or gs[i + 1] != gs[i] + pd.Timedelta(hours=1):
            continue
        bull = xs[i] > 0
        a = fs.searchsorted(gs[i + 1])
        b = fs.searchsorted(gs[i + 1] + pd.Timedelta(hours=1))
        if b <= a:
            continue
        j, ext = cisd_after_sweep(fo, fh, fl, fc, a, b, fo[a], bull, lo=a)
        if j < 0:
            continue
        tgt = gh[i] if bull else gl[i]
        if (bull and fc[j] >= tgt) or ((not bull) and fc[j] <= tgt):
            continue
        rows.append({"decision_time": fct[j], "available_at": fct[j],
                     "direction": 1 if bull else -1, "stop_px": ext, "target_px": tgt})
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                       "stop_px", "target_px"])


if __name__ == "__main__":
    ev = cl.cache_frame("fw_transfer_xag_v2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="4D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "source = XAG_USD 1H (OANDA, local file); target = XAUUSD",
        "hour H: silver 1H C2 closure while gold's 1H candle is not a C2 in either direction",
        "gold hour H+1 (C3): on 5m, arm on a trade below (above) the C3 open, then 5m CISD "
        "through the first open of the opposing series that made the running extreme",
        "decide at the 5m close inside H+1; stop = running extreme; target = gold hour-H high "
        "(low); skip if already beyond; 60 min"],
        "params": {"source_asset": "XAG_USD", "framework_tf": "1h", "entry_tf": "5min",
                   "max_hold": MAX_HOLD, "target": "previous (C2) candle extreme"}}
    src = {"source_asset": "method_spec: §2.6 correlated asset; fetch_correlated.py 'Silver is the correlate the method would actually sanction for gold'",
           "framework_tf": "corpus: framework-transfer yaml timeframes htf 4H/1H (only H1 silver exists locally)",
           "entry_tf": "method_spec: §1.2 pairing 1-hour -> 5-minute",
           "max_hold": "declared-before-run: the C3 candle's length",
           "target": "method_spec: §5.2 previous candles' unswept extremes, starting with candle 1's / C2's"}
    p = cl.write_result("framework-transfer", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Silver file is outside the M1 slice the probe truncates; it is read "
                              "only at hour H with decisions >= H+1h. One worked example in the corpus.")
    print("wrote", p)
