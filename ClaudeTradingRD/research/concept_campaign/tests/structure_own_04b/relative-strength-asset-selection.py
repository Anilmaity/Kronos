"""relative-strength-asset-selection (structure, TTrades own voice, contested) — batch structure_own_04b.

Claim: among correlated assets, take longs on the STRONGER asset and shorts on the WEAKER one;
"the same idea and the same trade can lose on the wrong asset and win on the right one"; never
trade the lagging asset. Only gold is tradeable here, so the testable implication is: a gold setup
taken when gold is the right asset (stronger than its correlate for a long, weaker for a short)
beats the same setup taken when gold is the lagging asset. Correlate = silver (gold's correlated
metal is named in the yaml preconditions: "gold with a correlated metal"); OANDA XAG_USD H1.

Baseline: phase-3 rung-0 1h CISD book on gold (series_open, 2/2, max_wait 3, stop protected swing,
2R, 10h). The yaml ranks strength with three tools and the readings disagree on which governs;
two readings (the two decidable tools, measured on the execution timeframe as he instructs —
"measured on the timeframe you are executing on"):

 a  tool 3, candle closure: compare the SAME closed 1h candle (the CISD confirming bar) — gold is
    stronger when its (close-open)/ATR14 exceeds silver's (each in its own ATR14(1h) units).
 b  tool 2, separation: distance each asset has travelled from the shared reference (the reversal
    extreme's bar) to the confirming close, in own-ATR units — further = stronger (for a long) /
    weaker (for a short).
Gate = gold is the right asset for the trade direction. claim '+'. Declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, pair_h1, atr, HOLD, CISD, RR

TF = "1h"


def detect(m1):
    b, ev, out = cisd_frame(m1, TF)
    P = pair_h1(m1)
    ga = atr(P.rename(columns={"g_high": "high", "g_low": "low", "g_close": "close"}))
    sa = atr(P.rename(columns={"s_high": "high", "s_low": "low", "s_close": "close"}))
    gi = P.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    xi = P.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ok = (gi >= 0) & (xi >= 0)
    gi_, xi_ = np.where(ok, gi, 0), np.where(ok, xi, 0)
    ok &= np.isfinite(ga[gi_]) & np.isfinite(sa[gi_])
    d = out["direction"].to_numpy()
    go, gc, so, sc = (P[k].to_numpy(float) for k in ("g_open", "g_close", "s_open", "s_close"))
    gh, gl, sh, sl = (P[k].to_numpy(float) for k in ("g_high", "g_low", "s_high", "s_low"))
    g_ret = (gc[gi_] - go[gi_]) / ga[gi_]
    s_ret = (sc[gi_] - so[gi_]) / sa[gi_]
    rs_close = np.where(d == 1, g_ret > s_ret, g_ret < s_ret)
    g_tr = np.full(len(ev), np.nan)
    s_tr = np.full(len(ev), np.nan)
    for e in np.flatnonzero(ok):
        a, z = xi[e], gi[e]
        if z < a:
            ok[e] = False
            continue
        if d[e] == 1:
            g_tr[e] = (gc[z] - gl[a:z + 1].min()) / ga[z]
            s_tr[e] = (sc[z] - sl[a:z + 1].min()) / sa[z]
        else:
            g_tr[e] = (gh[a:z + 1].max() - gc[z]) / ga[z]
            s_tr[e] = (sh[a:z + 1].max() - sc[z]) / sa[z]
    out["rs_close"] = np.where(ok, rs_close, False).astype(bool)
    out["rs_sep"] = np.where(ok, g_tr > s_tr, False).astype(bool)
    return out[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"rsas_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["rs_close"].mean()), float(ev["rs_sep"].mean()),
          float((ev["rs_close"] == ev["rs_sep"]).mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    base = ["baseline: gold 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open; stop at the protected swing, 2R, 10h wall clock",
            "correlate: silver (OANDA XAG_USD H1) inner-joined on gold's 1h labels; events without a joined silver bar dropped"]
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"correlate": "corpus: yaml precondition 'gold with a correlated metal' (he names gold/silver among correlated sets); phase3 correlate file",
                "atr_norm": "declared-before-run: each asset in its own ATR14(1h) units (silver's beta would otherwise decide every ranking; the corpus gives no normalisation)"})
    params = {"tf": TF, **CISD, "rr": RR, "max_hold": HOLD[TF], "correlate": "XAG_USD H1", "atr_norm": "ATR14(1h) own units"}
    for reading, col in (("a", "rs_close"), ("b", "rs_sep")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                                "exposure_bars", "ties", "ctrl_overlap")})
        gate = {"a": ["gate (tool 3, closure): on the confirming 1h candle, gold's (close-open)/ATR14 > silver's for a long (< for a short) — gold is the stronger (weaker) asset"],
                "b": ["gate (tool 2, separation): from the reversal extreme's bar to the confirming close, gold travelled further than silver in own-ATR units in the trade direction"]}[reading]
        op = {"rules": base + gate + ["claim: gold setups taken when gold is the ranked-correct asset beat those taken when gold is the lagging asset (control-adjusted R)"],
              "params": params}
        path = cl.write_result("relative-strength-asset-selection", reading, res, operationalization=op,
                               params_source=src, script=__file__, probe=probe,
                               notes=f"gate firing rate {float(ev[col].mean()):.3f} of {len(ev)}. Two-asset version only (gold vs silver); "
                                     "the index-triad 'middle asset' rule and 'looks cleaner' are not decidable with one tradeable asset.")
        print("wrote", path)
