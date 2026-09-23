"""es-nq-ratio-chart (structure, TTrades own voice, specified) — batch structure_own_04b.

Claim (c_mh19e3mhI): chart ES/NQ as one instrument; a bullish ratio means ES has the relative
strength (look for longs on ES), a bearish ratio means ES is weak (look for shorts on ES). He works
the ratio on the daily and applies it to lower-timeframe setups.

ES and NQ are not in this dataset. The device is a ratio of two correlated assets, so it is
tested on the only correlated pair we can trade one leg of: gold/silver (XAU/XAG, OANDA XAG_USD H1
joined on gold's 1h labels). Ratio up = gold strong -> gold longs; ratio down = gold weak -> gold
shorts. This is a transfer of the device, recorded as such.

Baseline: phase-3 rung-0 1h CISD book on gold (series_open, 2/2, max_wait 3, stop protected
swing, 2R, 10h) — the yaml ltf 1H. "Bullish/bearish" on the ratio chart is undefined in the corpus;
read it "the way he would read any chart" with his daily-closure framework: the most recent
COMPLETED trading day's ratio candle (18:00 NY roll) closed up (bullish) or down (bearish).
Gate = trade direction agrees with the ratio's daily closure. claim '+'. Declared before the run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, pair_h1, last_before, HOLD, CISD, RR

TF = "1h"


def detect(m1):
    b, ev, out = cisd_frame(m1, TF)
    P = pair_h1(m1)
    d1 = cl.build_bars(m1, "1D")
    P = P.assign(td=cl.trading_day(P.index).to_numpy())
    g = P.groupby("td").agg(go=("g_open", "first"), so=("s_open", "first"),
                            gc=("g_close", "last"), sc=("s_close", "last"))
    r_open, r_close = g["go"] / g["so"], g["gc"] / g["sc"]
    sign = np.sign((r_close - r_open).to_numpy(float))
    dmap = pd.Series(pd.DatetimeIndex(d1["close_time"]).tz_convert("UTC"),
                     index=cl.trading_day(d1.index))
    avail = pd.DatetimeIndex(dmap.reindex(pd.DatetimeIndex(g.index)))
    okd = ~avail.isna()
    avail, sign = avail[okd], sign[okd]
    o = np.argsort(avail.asi8, kind="stable")
    avail, sign = avail[o], sign[o]
    rs = last_before(avail, sign, out["decision_time"])
    ok = np.isfinite(rs) & (rs != 0)
    d = out["direction"].to_numpy()
    out["ratio_aligned"] = np.where(ok, rs == d, False).astype(bool)
    return out[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"esnq_ratio_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["ratio_aligned"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "ratio_aligned", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "baseline: gold 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open; stop at the protected swing, 2R, 10h wall clock",
        "ratio chart: XAU/XAG built from joined 1h bars, one candle per trading day (18:00 NY roll): open = first gold open / first silver open, close = last gold close / last silver close; available at the gold daily bar's close_time",
        "ratio bullish = the most recent completed ratio day closed above its open (gold strong); bearish = closed below (gold weak); flat days dropped",
        "gate: long when the ratio is bullish, short when bearish",
        "claim: ratio-aligned gold setups beat ratio-opposed ones (control-adjusted R)"],
        "params": {"tf": TF, **CISD, "rr": RR, "max_hold": HOLD[TF], "pair": "XAU/XAG (transfer of ES/NQ)",
                   "ratio_tf": "1D", "ratio_read": "prior completed day closure"}}
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"pair": "declared-before-run: ES/NQ absent from the dataset; gold/silver is the correlated pair available (yaml of relative-strength-asset-selection names gold with a correlated metal)",
                "ratio_tf": "corpus: c_mh19e3mhI he works the ratio on the daily (yaml timeframes htf 1D) and applies it to lower-timeframe setups",
                "ratio_read": "declared-before-run: 'bullish/bearish' undefined in the corpus (yaml ambiguity); read with his daily-closure framework (method_spec daily bias = previous candle closure)"})
    p = cl.write_result("es-nq-ratio-chart", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"gate firing rate {float(ev['ratio_aligned'].mean()):.3f} of {len(ev)}. "
                              "Tested as a TRANSFER of the device to gold/silver: the named instruments (ES, NQ) are not in the data, "
                              "so this does not test the ES/NQ claim itself.")
    print("wrote", p)
