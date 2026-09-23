"""ratio-chart-reversal-lead (TTrades' stated, untested theory) — batch structure_own_05a.

"reversals on the es and nq comparison chart ... it's kind of like an smt without an smt"
(c_mh19e3mhI): a reversal on the ratio chart (his examples: a sweep of a ratio high
followed by a fall back inside the range) anticipates a reversal on the instruments, and
may print AHEAD of it (ratio high at 10:00, instruments' low at 10:05). The yaml asks for
exactly this test: "whether the effect survives on a matched random-time control".

Transfer: the campaign has no ES/NQ; the method's sanctioned gold correlate is silver
(method_spec §2.6), so the ratio chart is XAU/XAG. Mapping from his example: a ratio HIGH
that is swept and fails -> the instruments put in a LOW -> long gold; a ratio low swept
and failed -> short gold. (ES is the low-beta numerator of ES/NQ as gold is of XAU/XAG.)

trade_test on H1 (the only silver resolution held):
  ratio line : gold H1 close / silver H1 close on shared bar starts
  reversal   : ratio close at bar j-1 above the highest ratio close of the 20 bars before it
               (the sweep) and ratio close at bar j back below that level (fall back inside);
               mirror for lows
  trade      : decide at bar j close, next M1 open, stop 1.0 x ATR14(1h gold), 1R target,
               exit after 10h (same book as smt-divergence, since this is 'an smt without an smt')
claim '+'.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_05a")
from _common import atr, cl, corr_h1, np, pd, summary  # noqa: E402

CID = "ratio-chart-reversal-lead"
LOOKBACK = 20
STOP_ATR = 1.0
RR = 1.0
MAX_HOLD = "10h"
TOD_TOL = 30


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    g = cl.build_bars(m1, "1h")
    x = corr_h1("xag", m1)
    cols = ["decision_time", "available_at", "direction", "stop_dist", "rr"]
    if len(g) < LOOKBACK + 20 or len(x) < LOOKBACK + 5:
        return pd.DataFrame(columns=cols)
    a = atr(g)
    j = g[["close", "close_time"]].join(x[["close"]].rename(columns={"close": "xc"}), how="inner")
    j["atr"] = a.reindex(j.index)
    # consecutive shared bars only (a gap in either feed breaks the pattern)
    r = (j["close"] / j["xc"]).to_numpy(float)
    gap = np.r_[True, np.diff(pd.DatetimeIndex(j.index).as_unit("ns").asi8) != 3_600_000_000_000]
    s = pd.Series(r)
    hi = s.rolling(LOOKBACK).max().shift(2).to_numpy()     # range of bars j-21 .. j-2
    lo = s.rolling(LOOKBACK).min().shift(2).to_numpy()
    prev = s.shift(1).to_numpy()
    contig = ~gap                                            # bar j-1 is the hour right before j
    top = contig & (prev > hi) & (r < hi)
    bot = contig & (prev < lo) & (r > lo)
    ct = pd.DatetimeIndex(j["close_time"])
    at = j["atr"].to_numpy(float)
    rows = []
    for sel, d in ((top, 1), (bot, -1)):
        i = np.flatnonzero(sel & np.isfinite(at))
        rows.append(pd.DataFrame({"decision_time": ct[i], "direction": d,
                                  "stop_dist": STOP_ATR * at[i]}))
    out = pd.concat(rows).sort_values(["decision_time", "direction"]).reset_index(drop=True)
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out[cols]


def main():
    ev = cl.cache_frame(f"ratiorev_h1_lb{LOOKBACK}", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(summary(res))
    op = {"rules": [
        "ratio line = gold 1h close / XAG_USD 1h close (OANDA) on shared, consecutive bar starts",
        "ratio high reversal at bar j: ratio close at j-1 above the highest ratio close of the 20 "
        "bars before j-1, ratio close at j back below it -> long gold; mirror (ratio low swept and "
        "reclaimed) -> short gold",
        "decide at bar j close, enter next M1 open, stop 1.0 x ATR14(1h gold), 1R, exit after 10h"],
        "params": {"tf": "1h", "correlate": "XAG_USD H1", "ratio": "XAU/XAG closes",
                   "range_lookback": LOOKBACK, "stop_atr": STOP_ATR, "atr_n": 14, "rr": RR,
                   "max_hold": MAX_HOLD, "ctrl_tod_tol_min": TOD_TOL,
                   "direction_map": "ratio high reversal -> long numerator"}}
    src = {"tf": "declared-before-run: silver is held only at H1 (yaml ltf lists 1H first)",
           "correlate": "method_spec: §2.6 silver is the method's sanctioned gold correlate; campaign holds no ES/NQ",
           "ratio": "corpus: c_mh19e3mhI 'reversals on the es and Q comparison chart' (numerator/denominator comparison)",
           "range_lookback": "phase3: lookback 20 knob",
           "stop_atr": "declared-before-run: same book as smt-divergence (liquidity_own_02a), 'smt without an smt'",
           "atr_n": "declared-before-run: smt-divergence book",
           "rr": "declared-before-run: smt-divergence book (1R = does the direction come true)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9",
           "direction_map": "corpus: c_mh19e3mhI example - ratio high at 10:00, instruments' low at 10:05"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Transfer test: ES/NQ -> XAU/XAG (the only correlate held, H1 only), so "
                              "the claimed minutes-scale lead cannot be resolved; what is tested is "
                              "whether a failed sweep on the ratio line predicts the instrument's "
                              "reversal direction over the next 10h against a matched random entry. "
                              "The lead/lag distribution itself is not measured.")
    print("wrote", p)


if __name__ == "__main__":
    main()
