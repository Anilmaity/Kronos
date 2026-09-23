"""smt-break-reversal-trigger (GxTradez, guest) — trade_test on 4H gold vs silver.

Rule as stated: an SMT exists (one asset failed to reach a shared level the other
took); when the LAGGING asset catches up and trades through its own level, the SMT is
broken and that break is the reversal trigger. With two assets (gold, silver) this is
his second arrangement: "all markets break the SMT and the lagging asset is the
trigger". The triad-only arrangement (middle breaks, third diverges) needs a third
market and is not tested here.

Params declared before the first run (no outcome seen):
  tf 4H forex grid (concept htf lists 1W/1D/4H; only 4H has the sample),
  SMT = phase-3 detector knobs (fractal 2/2, lookback 20 bars),
  catch-up window W = 20 4H bars after the SMT (the concept gives no limit; same
  span as the SMT lookback), direction = the SMT's reversal direction,
  stop = gold's extreme from the swing bar through the break bar, target 2R,
  max_hold 40h (ten 4H bars).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _smt_common as sc  # noqa: E402
import concept_lab as cl  # noqa: E402

W = 20
RR = 2.0
MAX_HOLD = "40h"


def detect(m1):
    P = sc.pair_bars(m1, "4h", "xag")
    ev = sc.smt_events(P)
    n = len(P)
    gh, gl, gc = P.g_high.to_numpy(), P.g_low.to_numpy(), P.g_close.to_numpy()
    sh, sl = P.s_high.to_numpy(), P.s_low.to_numpy()
    ct = pd.DatetimeIndex(P.close_time)
    rows = []
    for r in ev.itertuples():
        hi = r.direction == -1
        sgn = 1.0 if hi else -1.0
        held_g = r.sweeper == "other"
        arr = (gh if hi else gl) if held_g else (sh if hi else sl)
        lvl = r.lvl_g if held_g else r.lvl_s
        for k in range(r.j + 1, min(n, r.j + 1 + W)):
            if sgn * arr[k] > sgn * lvl:
                ext = gh[r.p:k + 1].max() if hi else gl[r.p:k + 1].min()
                if sgn * (ext - gc[k]) > 0:
                    rows.append({"decision_time": ct[k], "available_at": ct[k],
                                 "direction": int(r.direction), "stop_px": float(ext),
                                 "rr": RR, "breaker": "gold" if held_g else "silver",
                                 "smt_time": ct[r.j]})
                break
    out = pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                      "stop_px", "rr", "breaker", "smt_time"])
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


if __name__ == "__main__":
    ev = cl.cache_frame("smt_break_4h_xag_W20_rr2", lambda: detect(cl.load_m1()))
    print(len(ev), ev.breaker.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                   "verdict_detail", "exposure_bars", "ties")})
    p = cl.write_result(
        "smt-break-reversal-trigger", None, res,
        operationalization={"rules": [
            "4H forex-grid bars of gold (from certified M1) and OANDA XAG_USD H1 aggregated into the same buckets",
            "SMT: confirmed fractal(2/2) swing at bar p in either asset; each asset's level = its own extreme at p; first asset to trade beyond its level within 20 bars while the other has not -> SMT (sweeper/held)",
            "break: the HELD asset later trades beyond its own level within W=20 bars of the SMT -> decision at that 4H bar's close",
            "trade gold in the SMT's reversal direction (short at highs, long at lows)",
            "stop = gold's extreme from swing bar p through the break bar; target 2R; max_hold 40h",
            "two-asset form of 'all markets break the SMT and the lagging asset is the trigger'; triad arrangement not testable (no third gold-triad series)"],
            "params": {"tf": "4h", "grid4h": "forex", "fractal": [2, 2], "smt_lookback": 20,
                       "catch_up_window_bars": W, "rr": RR, "max_hold": MAX_HOLD,
                       "correlate": "XAG_USD H1 (m3_scalper/xag_h1_full.parquet)"}},
        params_source={
            "tf": "corpus: 3eVxTV_7L2U timeframes htf 1W/1D/4H — 4H chosen as the only one with sample",
            "grid4h": "phase3: forex grid locked for gold (method_spec §1.4)",
            "fractal": "phase3: smt_events left=2 right=2",
            "smt_lookback": "phase3: smt_events lookback=20",
            "catch_up_window_bars": "declared-before-run: no limit stated (ambiguity); 20 bars = SMT lookback",
            "rr": "phase3: bare-CISD book target 2R",
            "max_hold": "declared-before-run: ten 4H bars",
            "correlate": "phase3: load_correlate() XAG H1 full file"},
        script=__file__, probe=probe,
        notes=f"breaker counts {ev.breaker.value_counts().to_dict()}; the concept's gold triad "
              "(GC/XAUEUR/XAUGBP) is not available in full, silver used as the phase-3 correlate.")
    print(p)
