"""wick-to-body-order-block-zone (guest: Finessee_Fx) -> gate_test.

Claim: the wick-to-body band of an order block (wick extreme to the near body edge) is
the most sensitive part of the block and a better entry than waiting deeper at the mean
threshold (50% of the block), which he explicitly declines to use.

Reading (declared before the run):
  * Order blocks: the phase-3 locked 1h CISD (series_open level, 2/2 swings, max_wait 3,
    min_series 1); the block is the opposing-candle series into the protected swing
    (consecutive same-direction candles are merged, as he says). Valid from the CISD
    confirming bar's close.
  * Bullish block (price returns from above): band = [max body top of the series, series
    high]. The limit goes "slightly before the zone" -> filled at the first touch of the
    series high (the wick extreme). Bearish mirrored.
  * Comparison arm on the SAME blocks: a limit at the mean threshold = 50% of the series'
    full range (wick high to wick low).
  * Both arms: search window 48h after the CISD close; stop "always below the order
    block" = the series low (high for bearish); target 2R; max_hold 10h. A touch minute
    that also trades through the stop is not entered (either arm).
  * One baseline book holds both arms (two rows per block when the MT is reached);
    gate column `band` marks the wick-to-body entries; control-adjusted R, band vs MT.
    cluster = block id.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.blocks import order_blocks

TF = "1h"
WINDOW = pd.Timedelta("48h")
RR = 2.0
MAX_HOLD = "10h"
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "band", "block_id"]
    b = cl.build_bars(m1, TF)
    ob = order_blocks(b[["open", "high", "low", "close"]], zone="wick", **CISD_KW)
    if ob.empty:
        return pd.DataFrame(columns=cols)
    bo, bc = b["open"], b["close"]
    btop = np.maximum(bo, bc)
    bbot = np.minimum(bo, bc)
    ct = b["close_time"]
    mt = m1.index.values
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    out = []
    for _, r in ob.iterrows():
        seg = slice(r["series_start"], r["series_end"])
        hi, lo = r["zone_high"], r["zone_low"]
        mtl = (hi + lo) / 2.0
        bull = r["direction"] == "bullish"
        band_px = hi if bull else lo                     # wick extreme approached first
        stop = lo if bull else hi
        t0 = ct.loc[r["valid_from"]]
        a = np.searchsorted(mt, t0.to_datetime64(), side="left")
        e = np.searchsorted(mt, (t0 + WINDOW).to_datetime64(), side="left")
        if a >= e:
            continue
        hh, ll = MH[a:e], ML[a:e]
        bid = f"{r['valid_from'].value}_{int(bull)}"
        for is_band, px in ((True, band_px), (False, mtl)):
            touch = (ll <= px) if bull else (hh >= px)
            beyond = (ll < stop) if bull else (hh > stop)
            if not touch.any():
                continue
            k = int(np.argmax(touch))
            if beyond[:k + 1].any():
                continue
            dt = pd.Timestamp(mt[a + k]).tz_localize("UTC") + pd.Timedelta("1min")
            out.append((dt, 1 if bull else -1, stop, is_band, bid))
    if not out:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "band", "block_id"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    ev = ev.sort_values(["decision_time", "block_id", "band"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("w2b_ob_1h_cisd_mw3_48h", lambda: detect(cl.load_m1()))
    print(len(ev), ev.band.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "band", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       cluster="block_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "gate"):
        print(k, res.get(k))
    op = {"rules": [
        "order blocks = opposing-candle series of the phase-3 1h CISD (series_open, 2/2, max_wait 3), valid from the CISD close",
        "wick-to-body arm: limit at the series wick extreme on the approach side (first touch), i.e. the start of the wick-to-body band",
        "comparison arm: limit at the mean threshold, 50% of the series' full range, same blocks",
        "48h search window; stop beyond the block (series low/high); 2R; max_hold 10h; touch minute through the stop skipped",
        "gate_test: band rows vs MT rows, control-adjusted, clustered by block"],
        "params": {"tf": TF, "cisd": "series_open 2/2 max_wait 3 min_series 1", "window": "48h",
                   "rr": RR, "max_hold": MAX_HOLD, "mt": "50% of full wick range"}}
    src = {"tf": "declared-before-run: 1h, top of the concept's ltf list (1H/15m)",
           "cisd": "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)",
           "window": "declared-before-run: 48 execution bars to return to the block",
           "rr": "declared-before-run: target 'old highs / old lows' not mechanical; 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "mt": "declared-before-run: mean threshold = 50% of the block's wick range"}
    p = cl.write_result("wick-to-body-order-block-zone", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Gate reading: wick-to-body band entry vs mean-threshold entry on the same blocks (his stated contrast).")
    print(p)
