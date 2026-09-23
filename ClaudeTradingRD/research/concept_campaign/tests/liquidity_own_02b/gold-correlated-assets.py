"""gold-correlated-assets — is SMT against gold-in-euro / gold-in-pound (his stated set) a
better confluence than SMT against silver (the set he rejects when a viewer proposes it)?

Fixed BEFORE the first run.
Baseline book: every 1h C2 (sweeps the prior 1h candle's extreme, closes back inside, closes
in the reversal direction); enter at C2 close in the reversal direction, stop at the C2 extreme,
2R, 10 bars trading time. Reversal SMT per correlate = the correlate did NOT take its own prior
1h extreme on the C2 hour.
  EG-SMT  = reversal SMT against XAU/EUR or XAU/GBP
  AG-SMT  = reversal SMT against XAG/USD
Head-to-head: keep only C2s where exactly one family shows SMT (the two instrument choices
disagree — the only rows where the choice changes the decision). gate = EG-SMT (so the
complement is the silver-only SMT). claim '+': his gold-euro/gold-pound SMT beats silver's.
Rows missing any of the three correlates on C1/C2 are dropped.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import aligned

CID = "gold-correlated-assets"
TF = "1h"
RR = 2.0
HOLD = "10h"


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    bear = (h > ph) & (c <= ph) & (c < o)
    bull = (l < pl) & (c >= pl) & (c > o)
    div, ok = {}, {}
    for k in ("xau_eur", "xau_gbp", "xag_usd"):
        a = aligned(k, b.index)
        ch, cl_ = a["high"].to_numpy(float), a["low"].to_numpy(float)
        cph, cpl = np.r_[np.nan, ch[:-1]], np.r_[np.nan, cl_[:-1]]
        ok[k] = ~np.isnan(ch) & ~np.isnan(cph)
        div[k] = np.where(bear, ch <= cph, cl_ >= cpl) & ok[k]
    allok = ok["xau_eur"] & ok["xau_gbp"] & ok["xag_usd"]
    eg = div["xau_eur"] | div["xau_gbp"]
    ag = div["xag_usd"]
    sel = (bear | bull) & allok & (eg != ag)
    i = np.flatnonzero(sel)
    i = i[i >= 1]
    d = np.where(bear[i], -1, 1)
    stop = np.where(d < 0, h[i], l[i])
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[i]).tz_convert("UTC") if len(i) else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close, "direction": d,
                         "stop_px": stop, "rr": RR, "eg_smt": eg[i].astype(bool)})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["eg_smt"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "eg_smt", mask_available_at="decision_time", max_hold=HOLD,
                       hold_basis="bars")
    rules = ["1h bars (UTC hours); C2 = sweeps prior 1h high/low, closes back inside, closes in the reversal direction",
             "enter next M1 open after C2 close, reversal direction; stop at C2 extreme; 2R; 10 bars trading time",
             "reversal SMT vs a correlate = that correlate did not take its own prior-hour extreme on the C2 hour",
             "keep C2s where SMT vs {XAU/EUR or XAU/GBP} disagrees with SMT vs XAG/USD",
             "gate = SMT vs gold-euro/gold-pound (complement = silver-only SMT)"]
    params = {"tf": TF, "rr": RR, "max_hold": HOLD, "hold_basis": "bars",
              "eg_family": "SMT if XAU_EUR or XAU_GBP diverges", "ag_family": "XAG_USD",
              "divergence_tolerance": "none (strict)"}
    src = {"tf": "declared-before-run: 1H is in the concept's timeframe lists and the finest TF the H1 correlate data supports",
           "rr": "phase3: locked 2R target (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "hold_basis": "declared-before-run: trading-time holds (trap 7)",
           "eg_family": "corpus: W7Fu3Rx5iMs 'generally, I use the gold euro gold pound' (no ranking between the two given)",
           "ag_family": "corpus: W7Fu3Rx5iMs — viewer asserted silver is the correlation; he names gold-euro/gold-pound instead",
           "divergence_tolerance": "declared-before-run: no tolerance given in the corpus"}
    notes = (f"{len(ev)} C2s where the two correlate choices disagree; EG-SMT on {ev['eg_smt'].mean():.1%}. "
             "Not tested: 'chart gold as GC1! futures' (only spot XAU/USD exists here) and 'stand aside when "
             "the correlation is behaving oddly' (no threshold). Correlates are OANDA spot crosses.")
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars")})
    print(res.get("gate") or {k: v for k, v in res.items() if "compl" in k or "gated" in k})
    print(p)
