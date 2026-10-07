"""smt-requires-framework -- update 2026-10-07 (TTrades live_06 draft, uW55Tuk-ngY).

New claim vs the library entry (already tested, no-reading result): the SMT must form at the
EXTERNAL range high/low, not at internal equal highs inside a range.
  "The fact that we just have an equal high right here. That's not ideal. ... I want SMT off
   the external range high. It's just very choppy" (uW55Tuk-ngY)

gate_test, claim '+'. Base book = the prior reading's hourly gold/XAG SMT book (liquidity_own_02a
_common.smt_frame, 2/2 swings, 20-bar lookback; traded in gold in the SMT direction at the next
M1 open, stop 1 x ATR14(1h), 1R, 10h). Gate `external` = gold's reference level for the SMT
(its held level if gold held, the swept level if gold swept) is the extreme of gold's own
1h range over the SMT search span (the 23 bars before the SMT bar = lookback 20 + right 2 + the
swing bar): bearish -> level >= max(high), bullish -> level <= min(low). Otherwise internal.

Readings (the base book is the only open choice; gate rule identical in both):
  u1007a: all hourly SMTs (the gate alone).
  u1007b: only model-first SMTs (same-direction 1h CISD within 3h before, the prior reading's
          gate) -- the doctrine's "SMT confirms an existing setup".
"""
from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02a")
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "smt_rf_prior", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/"
                    "liquidity_own_02a/smt-requires-framework.py")
_prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prior)

CID = "smt-requires-framework"
SPAN = c.SMT_LOOKBACK + c.SWING + 1        # 23 bars: every bar the SMT search could reference
MAX_HOLD, TOD_TOL = _prior.MAX_HOLD, _prior.TOD_TOL


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    base = _prior.detect(m1)                # decision_time, ..., model_first
    if base.empty:
        return base.assign(external=pd.Series(dtype=bool))
    f = c.smt_frame(m1, "gold_last").drop_duplicates(subset=["decision_time", "direction"],
                                                      keep="first")
    g = cl.build_bars(m1, "1h")
    hi = g["high"].rolling(SPAN, min_periods=SPAN).max().shift(1)   # bars j-23..j-1
    lo = g["low"].rolling(SPAN, min_periods=SPAN).min().shift(1)
    t = pd.DatetimeIndex(f["time"])
    lvl = f["gold_level"].to_numpy(float)
    bull = f["direction"].to_numpy(int) == 1
    h, l = hi.reindex(t).to_numpy(float), lo.reindex(t).to_numpy(float)
    ext = np.where(bull, lvl <= l, lvl >= h) & np.isfinite(np.where(bull, l, h))
    key = pd.Series(ext, index=pd.MultiIndex.from_arrays(
        [pd.DatetimeIndex(f["decision_time"]), f["direction"].to_numpy(int)]))
    out = base.copy()
    out["external"] = key.reindex(pd.MultiIndex.from_arrays(
        [pd.DatetimeIndex(out["decision_time"]), out["direction"].to_numpy(int)])
    ).fillna(False).to_numpy(bool)
    return out


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect(m1)
    return ev[ev["model_first"].astype(bool)].reset_index(drop=True)


def run(reading: str, fn) -> None:
    ev = cl.cache_frame(f"{CID}_u1007_{reading}_span{SPAN}", lambda: fn(cl.load_m1()))
    probe = cl.probe_lookahead(fn, ev, lookback="20D")
    print(reading, "n", len(ev), "external rate", round(float(ev["external"].mean()), 3))
    res = cl.gate_test(ev, "external", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL)
    print(reading, res["n"], res["diff"], res["ci_lo"], res["ci_hi"], res["verdict"],
          res.get("verdict_detail"))
    base_rule = ("base: every hourly gold/XAG SMT (detectors.bias.smt_events, 2/2 swings, "
                 "20-bar lookback), traded in gold in its direction at the next M1 open after "
                 "the SMT bar close; stop 1 x ATR14(1h), 1R, 10h")
    rules = [base_rule,
             "gate external: gold's reference level for the SMT (held level if gold held, swept "
             "level if gold swept) is at/beyond gold's 1h range extreme over the 23 bars before "
             "the SMT bar (bearish: level >= max high; bullish: level <= min low)",
             "complement = SMT at an internal level (a higher high / lower low already inside "
             "the range)"]
    if reading == "u1007b":
        rules.insert(1, "base restricted to model-first SMTs: same-direction 1h CISD "
                        "(series_open, 2/2, max_wait 3) confirmed within 3h before the SMT close")
    params = {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": c.SMT_LOOKBACK,
              "swing": "2/2", "range_span_bars": SPAN, "stop_atr": _prior.STOP_ATR,
              "atr_n": c.ATR_N, "rr": _prior.RR, "max_hold": MAX_HOLD,
              "ctrl_tod_tol_min": TOD_TOL,
              "base": "all SMTs" if reading == "u1007a" else "model-first SMTs (CISD 3h)"}
    src = {"tf": "declared-before-run: silver held only at H1 (prior reading)",
           "correlate": "corpus: 'they just need to be correlated' (silver is allowed)",
           "smt_lookback": "phase3: detectors.bias.smt_events default",
           "swing": "phase3: 2/2 swings (§1.8)",
           "range_span_bars": "declared-before-run: the SMT's own search span (lookback 20 + "
                              "right 2 + swing bar); corpus uW55Tuk-ngY 'I want SMT off the "
                              "external range high' gives no range length",
           "stop_atr": "declared-before-run (prior reading)", "atr_n": "declared-before-run",
           "rr": "declared-before-run (prior reading)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9",
           "base": "corpus: uW55Tuk-ngY 'SMT is a confirmation to a setup' -> reading b keeps "
                   "the prior reading's model-first gate; reading a tests the external rule alone"}
    notes = ("Tests only the new external-vs-internal claim. Range = gold's own 1h range over "
             "the SMT search span; silver's position in its range is not required. The "
             "on-chart example (NQ 1m at the 10:00 open) is not reproducible: only XAG H1 exists.")
    print("wrote", cl.write_result(CID, reading, res,
                                   operationalization={"rules": rules, "params": params},
                                   params_source=src, script=__file__, probe=probe, notes=notes))


if __name__ == "__main__":
    run("u1007a", detect)
    run("u1007b", detect_b)
