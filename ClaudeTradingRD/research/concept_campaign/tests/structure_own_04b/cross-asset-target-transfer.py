"""cross-asset-target-transfer (structure, TTrades own voice, contested) — batch structure_own_04b.

Claim: "you can take profit on one asset because the other asset hits a target" (Je7cd9HJUBE);
"sometimes I will use Nasdaq hitting price targets as my price target for ES" (q1NmxUTm4n4).
The exit is justified only if the correlated asset's tag marks the END of the traded asset's
move — i.e. after the tag the traded asset turns rather than continues. yaml measurable: "how
often the traded asset turns within N bars of the correlated asset tagging its level".

Traded asset = gold; correlated asset = silver (OANDA XAG_USD H1 joined on gold's 1h labels).
Level = each asset's own previous-trading-day high/low (18:00 NY roll) — the draw he names in both
sources is the other asset's unswept prior extreme. The two sources describe different states of
the traded asset, so two readings:

 a  Je7cd9HJUBE: gold has ALREADY taken its own PDH (PDL) in an earlier 1h bar of the day (no
    level left on its own chart); silver then tags its PDH (PDL) for the first time that day.
 b  q1NmxUTm4n4: silver tags its PDH (PDL) while gold has NOT taken its own (an SMT at the level).

Event at the close of silver's tagging 1h bar: the transferred exit says gold's move is done, so
trade gold AGAINST the move (short at a high tag, long at a low tag) with a symmetric barrier —
stop 1.0 x ATR14(gold 1h), target 1R, 10h. trade_test vs the matched random-entry control (same
direction, same distances). claim '+': gold turns more than a random moment at the same geometry.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, pair_h1, atr, HOLD

TF = "1h"
STOP_ATR = 1.0
RR1 = 1.0


def detect(m1):
    g1 = cl.build_bars(m1, TF)
    g1 = g1.assign(td=cl.trading_day(g1.index).to_numpy())
    g_rh = g1.groupby("td")["high"].cummax()
    g_rl = g1.groupby("td")["low"].cummin()
    g_atr = pd.Series(atr(g1), index=g1.index)
    P = pair_h1(m1)
    P = P.assign(td=cl.trading_day(P.index).to_numpy())
    pl = cl.prior_hilo(P.index, "1D", m1=m1, min_coverage=0.5)
    gph, gpl = pl["high"].to_numpy(float), pl["low"].to_numpy(float)
    # silver previous-day extremes from the joined bars
    sd = P.groupby("td").agg(sh=("s_high", "max"), sl=("s_low", "min"))
    sd_prev = sd.shift(1)
    sph = sd_prev["sh"].reindex(P["td"]).to_numpy(float)
    spl = sd_prev["sl"].reindex(P["td"]).to_numpy(float)
    s_rh = P.groupby("td")["s_high"].cummax().to_numpy(float)
    s_rl = P.groupby("td")["s_low"].cummin().to_numpy(float)
    same_day_prev = np.r_[False, P["td"].to_numpy()[1:] == P["td"].to_numpy()[:-1]]
    s_rh_prev = np.where(same_day_prev, np.r_[np.nan, s_rh[:-1]], -np.inf)
    s_rl_prev = np.where(same_day_prev, np.r_[np.nan, s_rl[:-1]], np.inf)
    # gold running extremes through the previous gold bar of the same day, and through this bar
    grh_now = g_rh.reindex(P.index).to_numpy(float)
    grl_now = g_rl.reindex(P.index).to_numpy(float)
    gpos = g1.index.get_indexer(P.index)
    prev_ok = (gpos > 0) & (g1["td"].to_numpy()[np.maximum(gpos - 1, 0)] == P["td"].to_numpy())
    grh_prev = np.where(prev_ok, g_rh.to_numpy(float)[np.maximum(gpos - 1, 0)], -np.inf)
    grl_prev = np.where(prev_ok, g_rl.to_numpy(float)[np.maximum(gpos - 1, 0)], np.inf)
    a1 = g_atr.reindex(P.index).to_numpy(float)
    ok = np.isfinite(gph) & np.isfinite(gpl) & np.isfinite(sph) & np.isfinite(spl) & np.isfinite(a1)
    tag_hi = ok & (s_rh >= sph) & (s_rh_prev < sph)
    tag_lo = ok & (s_rl <= spl) & (s_rl_prev > spl)
    rows = []
    for reading in ("a", "b"):
        if reading == "a":
            hi = tag_hi & (grh_prev >= gph)
            lo = tag_lo & (grl_prev <= gpl)
        else:
            hi = tag_hi & (grh_now < gph)
            lo = tag_lo & (grl_now > gpl)
        for mask, dirn in ((hi, -1), (lo, 1)):
            k = np.flatnonzero(mask)
            rows.append(pd.DataFrame({"decision_time": pd.DatetimeIndex(P["close_time"].iloc[k]).tz_convert("UTC"),
                                      "direction": dirn, "stop_dist": STOP_ATR * a1[k],
                                      "rr": RR1, "reading": reading}))
    ev = pd.concat(rows, ignore_index=True)
    ev["available_at"] = ev["decision_time"]
    ev["direction"] = ev["direction"].astype(int)
    ev = ev[["decision_time", "available_at", "direction", "stop_dist", "rr", "reading"]]
    return ev.sort_values(["reading", "decision_time", "direction"], kind="stable").reset_index(drop=True)


def detect_a(m1):
    e = detect(m1)
    return e[e["reading"] == "a"].drop(columns="reading").reset_index(drop=True)


def detect_b(m1):
    e = detect(m1)
    return e[e["reading"] == "b"].drop(columns="reading").reset_index(drop=True)


if __name__ == "__main__":
    src = {"tf": "phase3: 1h rung-0 timeframe; silver correlate exists only at H1",
           "level": "corpus: Je7cd9HJUBE 'ES still has an unswept low' / q1NmxUTm4n4 'NASDAQ takes the lows' — the correlated asset's own prior-day extreme (previous day high/low, method_spec §2.7 default relevant level)",
           "correlate": "corpus: yaml of relative-strength-asset-selection 'gold with a correlated metal'; phase3 correlate file XAG_USD H1",
           "min_coverage": "declared-before-run: skip stub sessions when reading gold PDH/PDL (README trap 6)",
           "stop_atr": "declared-before-run: symmetric barrier 1.0 x ATR14(gold 1h) — the corpus gives no distance; 'turns' vs 'continues' as a 1:1 race",
           "rr": "declared-before-run: 1R (symmetric turn test)",
           "max_hold": "phase3: 10 entry-TF periods (1h)"}
    params = {"tf": TF, "level": "PDH/PDL per asset", "correlate": "XAG_USD H1", "min_coverage": 0.5,
              "stop_atr": STOP_ATR, "rr": RR1, "max_hold": HOLD[TF]}
    for reading, det in (("a", detect_a), ("b", detect_b)):
        ev = cl.cache_frame(f"catt_{reading}_{TF}_{STOP_ATR}_{RR1}", lambda: det(cl.load_m1()))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(det, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=HOLD[TF], claim="+")
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                                "exposure_bars", "ties", "ctrl_overlap", "avg_R")})
        state = {"a": "gold already took its own PDH (PDL) in an earlier 1h bar of the same trading day (Je7cd9HJUBE: no level left on the traded chart)",
                 "b": "gold has not taken its own PDH (PDL) through the tagging bar (q1NmxUTm4n4: SMT at the level)"}[reading]
        op = {"rules": [
            "silver's first 1h bar of the trading day whose high reaches silver's previous-day high (low reaches previous-day low); decide at that bar's close",
            "state: " + state,
            "trade gold against the move (short at a high tag, long at a low tag), enter next M1 open, stop 1.0 x ATR14(gold 1h), target 1R, 10h wall clock",
            "claim: the correlated asset's tag marks the end of gold's move (gold turns more than at a matched random moment)"],
            "params": params}
        path = cl.write_result("cross-asset-target-transfer", reading, res, operationalization=op,
                               params_source=src, script=__file__, probe=probe,
                               notes="Gold/silver stands in for the index pairs of the sources (ES/NQ); the exit rule is tested through its implication "
                                     "(the traded asset turns after the correlated tag), not as a P&L comparison against holding to the traded asset's own level, "
                                     "which the harness has no variant-vs-variant test for.")
        print("wrote", path)
