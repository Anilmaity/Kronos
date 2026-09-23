"""c2-confirmation-scaling — gate_test.

Concept: the confirmation demanded before entering off a HTF candle 2 scales inversely with
bias/structure strength; with strong structure ("a clean expansion, consolidation, sweep of the
high and an ideal closure") the first LTF CISD confirming the wick is a sufficient entry.
Implied, testable claim: on the minimal-confirmation book (C2 + its single LTF CISD, no
continuation entry, no SMT) the strong-structure subset performs better than the rest.

Baseline book (stated, shared with single-cisd-at-swing-point): 4h forex-grid C2 with a
same-direction 15m CISD inside it; trade C3 from the C2 close, stop C2 extreme, 2R, 4h hold.
Gate `strong` (declared-before-run proxy of the named components that have a mechanical test):
  (1) clean expansion: C1 (the candle C2 sweeps) closed in the prior direction with a small
      opposing run: opposing_run/|body| <= 1.0 (threshold_fits small-wick default);
  (2) ideal closure: C2 closes beyond the OPEN of the first candle of the HTF opposing-close
      series ending at C1 (the series that ran into the swept extreme) — spec §3.2 ideal formation.
  'consolidation' has no mechanical test at this scale and is omitted; SMT is not used.
claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, c2_book, PHASE3_SRC

CID = "c2-confirmation-scaling"
HOLD = "4h"
RR = 2.0
WICK_CUT = 1.0


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "strong"]
    bk = c2_book(m1)
    if bk.empty:
        return pd.DataFrame(columns=cols)
    s = bk["sgn"].to_numpy()
    o1, h1, l1, c1 = (bk[k].to_numpy(float) for k in ("c1_o", "c1_h", "c1_l", "c1_c"))
    body = np.abs(c1 - o1)
    # C1 must be an expansion candle in the PRIOR direction (opposite the C2 trade)
    prior_dir_ok = np.where(s > 0, c1 < o1, c1 > o1)
    opp_run = np.where(s > 0, h1 - o1, o1 - l1)          # bearish C1: open -> high; bullish C1: open -> low
    clean = prior_dir_ok & (body > 0) & (opp_run <= WICK_CUT * np.where(body > 0, body, 1.0))
    so = bk["series_open"].to_numpy(float)
    ideal = np.isfinite(so) & np.where(s > 0, bk["c"].to_numpy(float) > so, bk["c"].to_numpy(float) < so)
    t = pd.DatetimeIndex(bk["c2_close"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": s,
                        "stop_px": np.where(s > 0, bk["l"], bk["h"]).astype(float), "rr": RR,
                        "strong": clean & ideal})
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h15m_strong", lambda: detect(cl.load_m1()))
    print(len(ev), ev["strong"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "strong", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "avg_R", "exposure_bars", "ctrl_overlap")})
    op = {"rules": [
        "baseline: 4h forex-grid C2 (sweep prior extreme, close back inside) carrying a same-direction "
        "15m CISD (series_open, 2/2, max_wait 3) with extreme and confirm inside C2; decide at C2 close, "
        "enter next M1 open, stop C2 extreme, 2R, 4h hold",
        "gate strong = clean expansion AND ideal closure:",
        "clean expansion: C1 closed in the prior direction with opposing run (open->extreme against its "
        "direction) <= 1.0 x body",
        "ideal closure: C2 close beyond the open of the first candle of the contiguous 4h opposing-close "
        "series ending at C1 (<=10 candles)",
        "consolidation component omitted (no mechanical test); SMT not used"],
        "params": {"htf": "4h", "grid4h": "forex", "ltf": "15min", "level_rule": "series_open",
                   "swing": "2/2", "max_wait": 3, "rr": RR, "max_hold": HOLD, "wick_cut": WICK_CUT,
                   "ideal_ref": "first open of HTF opposing series"}}
    src = {"htf": "method_spec: §1.3 4H/15m pairing; c2-confirmation-scaling.yaml htf 4H ltf 15m",
           "grid4h": PHASE3_SRC, "ltf": "corpus: uzPGXVYpVGc ltf 15m/5m (c2-confirmation-scaling.yaml)",
           "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "rr": "corpus: uzPGXVYpVGc 2R stated as the normal expectation (yaml execution.targets)",
           "max_hold": "method_spec: §5.5 time-based-exit-htf-close",
           "wick_cut": "threshold_fits: small wick opposing_run/|body| <= 1.0 (grade A default)",
           "ideal_ref": "method_spec: §3.2 ideal formation — closure clears the series of opposing candles "
                        "(CISD level = first-candle open, §4.2)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=f"gate firing rate {ev['strong'].mean():.3f}; strength scale "
                        "is discretionary in the corpus ([GAP] spec §4.4) - this is a declared proxy, "
                        "medium/weak arms (continuation entry, SMT) not tested")
    print(p)
