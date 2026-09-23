"""smt-reversal-continuation-double — Reversal SMT (C1<->C2) and Continuation SMT (C2<->C3)
as confluence gates on the fractal-model candle book, gold vs gold-in-euro / gold-in-pound.

Everything below is fixed BEFORE the first run.

Reading a — REVERSAL SMT on the C2 trade.
  baseline: 1h C2 (sweeps the prior 1h candle's extreme, closes back inside, closes in the
  reversal direction) that also has a SMALL WICK (opposing run / body <= 1.0) — the concept's
  own rule: "If trading the candle 2 reversal itself, the candle must independently support
  expansion (small wick) before the SMT is allowed to count". Enter at C2 close in the reversal
  direction, stop beyond the C2 extreme, 2R, 10 bars.
  gate: reversal SMT = at least one correlate (XAU/EUR, XAU/GBP) did NOT take its own C1
  extreme during its C2 bar (bearish: corr C2 high <= corr C1 high; bullish mirrored).
Reading b — CONTINUATION SMT on the C3 continuation.
  baseline: sequential 1h C3 = the bar after a C2 (as above, no wick filter) that closes
  beyond the C2 open (delivery). Enter at C3 close in the C2 direction ("trust that this
  candle two can hold"), stop beyond max(C2, C3) extreme, 2R, 10 bars.
  gate: continuation SMT = for at least one correlate, exactly one of {gold, correlate} took
  its own C2 extreme during C3 (transcript: "We don't take out the high but on a correlated
  market we do take out the high").
Both: rows where neither correlate has both bars are dropped (never-evaluated != failed).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import aligned

CID = "smt-reversal-continuation-double"
TF = "1h"
CORRS = ("xau_eur", "xau_gbp")
WICK_CUT = 1.0
RR = 2.0
HOLD = "10h"


def _base(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    bear = (h > ph) & (c <= ph) & (c < o)
    bull = (l < pl) & (c >= pl) & (c > o)
    cor = {k: aligned(k, b.index) for k in CORRS}
    return b, o, h, l, c, ph, pl, bear, bull, cor


def detect_a(m1):
    b, o, h, l, c, ph, pl, bear, bull, cor = _base(m1)
    body = np.abs(c - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        wr_bear = np.clip(h - o, 0, None) / body
        wr_bull = np.clip(o - l, 0, None) / body
    small = np.where(bear, wr_bear <= WICK_CUT, wr_bull <= WICK_CUT)
    sel = (bear | bull) & small & (body > 0)
    smt = np.zeros(len(b), bool)
    evaluable = np.zeros(len(b), bool)
    for k in CORRS:
        ch, cl_ = cor[k]["high"].to_numpy(float), cor[k]["low"].to_numpy(float)
        cph, cpl = np.r_[np.nan, ch[:-1]], np.r_[np.nan, cl_[:-1]]
        ok = ~np.isnan(ch) & ~np.isnan(cph)
        div = np.where(bear, ch <= cph, cl_ >= cpl) & ok
        smt |= div
        evaluable |= ok
    # C1 must be the immediately preceding bar in time (no gap between C1 and C2)
    sel &= evaluable
    i = np.flatnonzero(sel)
    i = i[i >= 1]
    d = np.where(bear[i], -1, 1)
    stop = np.where(d < 0, h[i], l[i])
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[i]).tz_convert("UTC") if len(i) else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": d, "stop_px": stop, "rr": RR,
                         "smt": smt[i].astype(bool)})


def detect_b(m1):
    b, o, h, l, c, ph, pl, bear, bull, cor = _base(m1)
    n = len(b)
    i2 = np.flatnonzero((bear | bull))
    i2 = i2[(i2 >= 1) & (i2 + 1 < n)]
    i3 = i2 + 1
    dirn = np.where(bear[i2], -1, 1)
    delivered = np.where(dirn < 0, c[i3] < o[i2], c[i3] > o[i2])
    g_took = np.where(dirn < 0, h[i3] > h[i2], l[i3] < l[i2])
    smt = np.zeros(len(i2), bool)
    evaluable = np.zeros(len(i2), bool)
    for k in CORRS:
        ch, cl_ = cor[k]["high"].to_numpy(float), cor[k]["low"].to_numpy(float)
        ok = ~np.isnan(ch[i2]) & ~np.isnan(ch[i3])
        c_took = np.where(dirn < 0, ch[i3] > ch[i2], cl_[i3] < cl_[i2])
        smt |= (c_took != g_took) & ok
        evaluable |= ok
    keep = delivered & evaluable
    i2, i3, dirn, smt = i2[keep], i3[keep], dirn[keep], smt[keep]
    stop = np.where(dirn < 0, np.maximum(h[i2], h[i3]), np.minimum(l[i2], l[i3]))
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[i3]).tz_convert("UTC") if len(i3) else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": dirn, "stop_px": stop, "rr": RR,
                         "smt": smt.astype(bool)})


PARAMS_COMMON = {"tf": TF, "correlates": "XAU_EUR,XAU_GBP (OANDA H1 mid), SMT if either diverges",
                 "rr": RR, "max_hold": HOLD, "hold_basis": "bars",
                 "divergence_tolerance": "none (strict >, <=)"}
SRC_COMMON = {
    "tf": "declared-before-run: 1H is in the concept's htf list and the finest TF the correlate data (H1) supports; the spec's 15m spotting preference cannot be met without M1 correlates",
    "correlates": "corpus: -ocfPuD_oqE 'gold has this SMT with gold euro, gold pound' and W7Fu3Rx5iMs 'generally, I use the gold euro gold pound'",
    "rr": "phase3: locked 2R target (conjunction_preregistration §1.13)",
    "max_hold": "phase3: 10 entry-TF bars (§1.13)",
    "hold_basis": "declared-before-run: trading-time holds so halts/weekends do not shorten real vs control exposure (trap 7)",
    "divergence_tolerance": "declared-before-run: the concept gives no tolerance ('No tolerance is given for relatively equal'), so strict comparison",
}


def run(reading):
    det = detect_a if reading == "a" else detect_b
    ev = cl.cache_frame(f"{CID}_{reading}_{TF}", lambda: det(cl.load_m1()))
    print(reading, len(ev), "smt rate", ev["smt"].mean())
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    res = cl.gate_test(ev, "smt", mask_available_at="decision_time", max_hold=HOLD,
                       hold_basis="bars")
    if reading == "a":
        rules = ["1h bars (UTC hours); C2 = high > prior high & close <= prior high & close < open (bearish; bullish mirrored)",
                 "baseline: C2 with small wick: opposing run (open->extreme against) / |body| <= 1.0",
                 "enter next M1 open after C2 close, reversal direction; stop at C2 extreme; 2R; 10 bars trading time",
                 "gate smt: XAU/EUR or XAU/GBP failed to take its own C1 extreme on the same C2 hour",
                 "rows with no correlate data for C1 and C2 dropped"]
        params = {**PARAMS_COMMON, "wick_cut_body": WICK_CUT}
        src = {**SRC_COMMON, "wick_cut_body": "threshold_fits: small wick = opposing_run/|body| <= 1.0 (grade A)"}
    else:
        rules = ["1h bars; C2 as reading a (no wick filter); C3 = next bar closing beyond the C2 open in the C2 direction",
                 "enter next M1 open after C3 close in the C2 direction; stop beyond max(C2,C3) extreme; 2R; 10 bars trading time",
                 "gate smt: for XAU/EUR or XAU/GBP, exactly one of gold / correlate took its own C2 extreme during C3",
                 "rows with no correlate data for C2 and C3 dropped"]
        params = {**PARAMS_COMMON, "c3": "sequential, close beyond C2 open"}
        src = {**SRC_COMMON, "c3": "method_spec: §3.3 sequential C3 must close beyond the open of C2"}
    notes = (f"gate fires on {ev['smt'].mean():.1%} of {len(ev)} baseline events. Baseline is the "
             "closure-only model (the LTF CISD leg of 'valid model' is omitted; phase 3 found the CISD "
             "conjunction null). Correlates are OANDA spot crosses, not the GC1!-based futures he charts. "
             "Double SMT (both) is not tested as its own reading (two-reading cap); the concept itself "
             "says 'No claim is made that a double SMT is better than a single one'.")
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties")})
    print(p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
