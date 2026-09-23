"""relative-strength-weakness (TTrades, Gpp8vicZo10 / c_mh19e3mhI / yud7TpE2AMs) — gate_test, 2 readings.

Claim: take longs on the relatively STRONGER asset and shorts on the WEAKER one. With gold
as the traded asset and silver as its correlate: gold longs taken when gold is stronger
than silver, gold shorts when gold is weaker, beat gold trades taken the other way round.
'+'.

Operationalisation (declared before the first run):
  * gold/silver on the inner-joined H1 grid (OANDA XAG_USD H1); prior-day high/low/range
    per asset from the joined bars grouped by trading day (18:00 NY roll); points are not
    comparable across the two instruments, so every distance is divided by that asset's
    own prior-day range.
  * baseline = gold 1H rung-0 CISD (series_open, 2/2, max_wait 3), decide at the
    confirming bar close, stop protected swing, 2R, 10h. CISD direction = the side.
  * reading a (SEPARATION, Gpp8vicZo10 "How close are we to that high"): for a long, the
    asset whose close sits closer to its own PDH is stronger -> gate if gold's
    (PDH - close)/PDR < silver's. For a short, the asset closer to its PDL is weaker ->
    gate if gold's (close - PDL)/PDR < silver's.
  * reading b (SWING POINTS, c_mh19e3mhI "the asset that takes out the shared swing
    point is relatively stronger"): shared swing = the prior-day high (low). Reach = how
    far today's running high has gone beyond PDH, / PDR (negative if not reached). Long
    gated if gold's reach > silver's; short gated if gold's reach beyond PDL > silver's.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

MAX_HOLD = "10h"


def detect(m1):
    ev, _ = C.cisd_book(m1, "1h")
    P = C.pair_h1(m1)
    td = cl.trading_day(P.index)
    P = P.assign(td=td)
    day = P.groupby("td").agg(g_h=("g_high", "max"), g_l=("g_low", "min"),
                              s_h=("s_high", "max"), s_l=("s_low", "min"))
    prev = day.shift(1)                               # prior trading day (complete)
    k = pd.Series(td.to_numpy())
    run = pd.DataFrame({
        "g_rh": P["g_high"].groupby(k.to_numpy()).cummax().to_numpy(),
        "g_rl": P["g_low"].groupby(k.to_numpy()).cummin().to_numpy(),
        "s_rh": P["s_high"].groupby(k.to_numpy()).cummax().to_numpy(),
        "s_rl": P["s_low"].groupby(k.to_numpy()).cummin().to_numpy()}, index=P.index)
    pr = prev.reindex(td).set_axis(P.index)
    ct = cl.data.utc_ns(pd.DatetimeIndex(P["close_time"]))
    tn = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"]))
    j = np.searchsorted(ct, tn)
    j = np.minimum(j, len(ct) - 1)
    hit = ct[j] == tn                                  # the joined bar that closes at t
    ev = ev[hit].reset_index(drop=True)
    j = j[hit]
    g_c, s_c = P["g_close"].to_numpy()[j], P["s_close"].to_numpy()[j]
    gh, gl = pr["g_h"].to_numpy()[j], pr["g_l"].to_numpy()[j]
    sh, sl = pr["s_h"].to_numpy()[j], pr["s_l"].to_numpy()[j]
    ok = ~np.isnan(gh) & ~np.isnan(sh) & (gh > gl) & (sh > sl)
    ev = ev[ok].reset_index(drop=True)
    j, g_c, s_c, gh, gl, sh, sl = (x[ok] for x in (j, g_c, s_c, gh, gl, sh, sl))
    gr, sr = gh - gl, sh - sl
    d = ev["direction"].to_numpy()
    sep_g = np.where(d == 1, (gh - g_c) / gr, (g_c - gl) / gr)
    sep_s = np.where(d == 1, (sh - s_c) / sr, (s_c - sl) / sr)
    reach_g = np.where(d == 1, (run["g_rh"].to_numpy()[j] - gh) / gr,
                       (gl - run["g_rl"].to_numpy()[j]) / gr)
    reach_s = np.where(d == 1, (run["s_rh"].to_numpy()[j] - sh) / sr,
                       (sl - run["s_rl"].to_numpy()[j]) / sr)
    ev["sep_g"], ev["sep_s"], ev["reach_g"], ev["reach_s"] = sep_g, sep_s, reach_g, reach_s
    ev["rs_sep"] = sep_g < sep_s
    ev["rs_reach"] = reach_g > reach_s
    return ev.drop(columns=["bar_pos", "px"])


if __name__ == "__main__":
    ev = cl.cache_frame("rsw_cisd1h_xag", lambda: detect(cl.load_m1()))
    print(len(ev), ev.rs_sep.mean(), ev.rs_reach.mean(), (ev.rs_sep == ev.rs_reach).mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    base = ["gold/silver (OANDA XAG_USD H1) inner-joined on gold 1H labels; prior-day high/low per asset from the joined bars by trading day (18:00 NY); distances / that asset's own prior-day range",
            "baseline: gold 1H rung-0 CISD (series_open, 2/2, max_wait 3), stop protected swing, 2R, 10h; CISD direction = the side"]
    params = {"baseline_tf": "1h", "correlate": "XAG_USD", "reference": "prior-day high/low",
              "normalisation": "own prior-day range", "max_wait": 3, "rr": 2.0,
              "max_hold": MAX_HOLD}
    src = {"baseline_tf": "phase3: rung-0 1h CISD book; 1H is the finest the correlate supports",
           "correlate": "corpus: gold-correlated-assets (silver); phase3 load_correlate XAG_USD",
           "reference": "corpus: relative-strength-weakness precondition 'A shared reference level exists across the assets (e.g. previous day high/low)'",
           "normalisation": "declared-before-run: points are not comparable across assets (concept ambiguity); divide by each asset's prior-day range",
           "max_wait": "phase3: locked CISD config max_wait=3",
           "rr": "phase3: locked 2R target",
           "max_hold": "phase3: 10 entry-TF bars"}
    for rd, col, rule in (
            ("a", "rs_sep", "gate a (separation): long if gold's (PDH-close)/PDR < silver's; short if gold's (close-PDL)/PDR < silver's"),
            ("b", "rs_reach", "gate b (swing point taken): long if gold's (today's running high - PDH)/PDR > silver's; short if gold's (PDL - running low)/PDR > silver's")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=MAX_HOLD)
        print("reading", rd)
        C.show(res)
        p = cl.write_result(
            "relative-strength-weakness", rd, res,
            operationalization={"rules": base + [rule], "params": params},
            params_source=src, script=__file__, probe=probe,
            notes="Taught on ES/NQ/YM; applied to the gold/silver pair with gold as the only traded asset. Readings = two of the three named inputs (separation; swing points); SMT and candle closures are covered by other concepts.")
        print(p)
