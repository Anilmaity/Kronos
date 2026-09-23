"""timeframe-alignment-pairs (TTrades own voice, contested) — batch model_own_01b.

Claim: every model is a PAIR — a higher-timeframe closure plus an aligned
lower-timeframe CISD in the same direction; entries on the lower timeframe of the
pair are taken only when they align with the higher timeframe's closure.

Baseline book: the phase-3 bare CISD on the pair's LTF (series_open, swing 2/2,
max_wait 3, stop at the protected swing, 2R, 10 LTF bars).
Gate: the last COMPLETED HTF candle (close_time <= decision) is a closure in the
same direction as the LTF entry:
  C2 closure — bullish low<prev low & close>prev low (bearish mirrored; two-sided dropped)
  C3 closure — (reading A of method_spec §3.3) previous candle took the prior low
               but printed no C2, and this candle closes above the previous open
               (bearish mirrored).
Reading a: pair 1H -> 5m.   Reading b: pair 4H (forex grid) -> 15m.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01b")
from _common import PHASE3, cisd_book, cl, np, pd, summary  # noqa: E402

CID = "timeframe-alignment-pairs"
PAIRS = {"a": ("1h", "5min", "50min"), "b": ("4h", "15min", "150min")}


def htf_closure(H: pd.DataFrame) -> np.ndarray:
    o, lo, hi, c = (H[k].to_numpy() for k in ("open", "low", "high", "close"))
    plo, phi, po = np.r_[np.nan, lo[:-1]], np.r_[np.nan, hi[:-1]], np.r_[np.nan, o[:-1]]
    bull2 = (lo < plo) & (c > plo)
    bear2 = (hi > phi) & (c < phi)
    c2 = np.where(bull2 & ~bear2, 1, np.where(bear2 & ~bull2, -1, 0))
    c2_any = bull2 | bear2
    pp_lo, pp_hi = np.r_[np.nan, plo[:-1]], np.r_[np.nan, phi[:-1]]
    prev_took_low = plo < pp_lo
    prev_took_high = phi > pp_hi
    prev_no_c2 = ~np.r_[False, c2_any[:-1]]
    bull3 = prev_took_low & prev_no_c2 & (c > po)
    bear3 = prev_took_high & prev_no_c2 & (c < po)
    c3 = np.where(bull3 & ~bear3, 1, np.where(bear3 & ~bull3, -1, 0))
    return np.where(c2 != 0, c2, c3)


def make_detect(htf: str, ltf: str):
    def detect(m1):
        ev = cisd_book(m1, ltf).drop(columns=["extreme_time", "extreme_price"])
        H = cl.build_bars(m1, htf)
        cl_dir = htf_closure(H)
        hc = cl.data.utc_ns(pd.DatetimeIndex(H["close_time"]))
        t = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"]))
        pos = np.searchsorted(hc, t, side="right") - 1
        hd = np.where(pos >= 0, cl_dir[np.clip(pos, 0, None)], 0)
        ev["htf_closure"] = hd
        ev["aligned"] = (hd != 0) & (hd == ev["direction"].to_numpy())
        return ev
    return detect


def main():
    for reading, (htf, ltf, hold) in PAIRS.items():
        detect = make_detect(htf, ltf)
        ev = cl.cache_frame(f"tap_{htf}_{ltf}_v1", lambda: detect(cl.load_m1()))
        probe = cl.probe_lookahead(detect, ev, lookback="15D")
        res = cl.gate_test(ev, "aligned", mask_available_at="decision_time", max_hold=hold)
        print(f"reading {reading} ({htf}->{ltf})\n" + summary(res))
        op = {"rules": [
            f"baseline: {ltf} bare CISD (series_open, swing 2/2, max_wait 3), decide at the "
            f"confirming bar close, enter next M1 open, stop protected swing, 2R, {hold}",
            f"gate: last completed {htf} candle is a C2 or C3 (reading A) closure in the "
            "entry's direction"],
            "params": {"htf": htf, "ltf": ltf, "grid4h": "forex", "level_rule": "series_open",
                       "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": hold,
                       "c3_reference": "c2_open"}}
        src = {"htf": "method_spec: §1.2 timeframe pairing table",
               "ltf": "method_spec: §1.2 timeframe pairing table",
               "grid4h": "session_window_fit: forex grid for gold (weak; recorded)",
               "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
               "max_hold": "phase3: 10 entry-TF bars (§1.13)",
               "c3_reference": "method_spec: §3.3 reading A (detectors.bias default)"}
        p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe)
        print("  wrote", p)


if __name__ == "__main__":
    main()
