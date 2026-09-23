"""mmxm-range-definition (guest: The MMXM Trader, Ibw4saRtYMk) — declared before the first run.

Claim: a lower-timeframe range is a market maker model only when it is paired with a
higher-timeframe key level that sits in discount (buy model) / premium (sell model) of the
prevailing higher-timeframe dealing range. The 'most obvious swing' selection is visual, so
the LTF reversal is taken mechanically as the campaign's canonical 1h reversal (bare CISD,
phase-3 locked config), and the claim is tested as a GATE on that book:

  baseline: 1h CISD (series_open, 2/2, max_wait 3), stop at the protected swing, 2R, 10h.
  mask (buy model; sell mirrored): the reversal low (the curve split) traded through a
        DAILY key level — the prior NY day's low — AND that level sits in discount: below
        the equilibrium (50%) of the prior completed WEEK's range.
  Pairing 1H <-> Daily comes from the MMXM Trader's own timeframe table (daily <-> 1H);
  the weekly range stands in for 'higher-timeframe institutional order flow' (deferred
  to other material in the source).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

TF = "1h"
RR = 2.0
HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "htf_key_pd", "extreme_close"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close_t = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    xt = pd.DatetimeIndex(b.loc[ev["extreme_time"], "close_time"])
    pd_ = cl.prior_hilo(xt, "1D", m1=m1, min_coverage=0.5)
    pw = cl.prior_hilo(xt, "1W", m1=m1, min_coverage=0.5)
    bull = (ev["direction"] == "bullish").to_numpy()
    ext = ev["extreme_price"].to_numpy()
    weq = (pw["high"].to_numpy() + pw["low"].to_numpy()) / 2.0
    pdl, pdh = pd_["low"].to_numpy(), pd_["high"].to_numpy()
    with np.errstate(invalid="ignore"):
        m_bull = bull & (ext < pdl) & (pdl < weq)
        m_bear = ~bull & (ext > pdh) & (pdh > weq)
    mask = np.nan_to_num(m_bull | m_bear, nan=False).astype(bool)
    out = pd.DataFrame({"decision_time": close_t, "available_at": close_t,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR,
                        "htf_key_pd": mask, "extreme_close": xt})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("mmxm_range_def_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.htf_key_pd.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "htf_key_pd", mask_available_at="extreme_close", max_hold=HOLD, claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties")})
    op = {"rules": [
        "baseline: 1h bare CISD (series_open, 2/2 swing, max_wait 3), decide at the confirming "
        "bar close, stop protected swing, 2R, 10h",
        "gate (buy): the reversal low < prior NY-day low (the HTF key level) AND prior-day low < "
        "50% of the prior completed week's range (discount); sell mirrored (PDH above weekly EQ)",
        "levels read with prior_hilo at the extreme bar's close (min_coverage 0.5)"],
        "params": {"tf": TF, "cisd": "series_open 2/2 max_wait 3", "rr": RR, "max_hold": HOLD,
                   "htf_key_level": "prior-day low/high", "order_flow_range": "prior week",
                   "min_coverage": 0.5}}
    src = {"tf": "phase3: rung-0 1h CISD book (conjunction_preregistration)",
           "cisd": "phase3: locked CISD config",
           "rr": "phase3: 2R target", "max_hold": "phase3: 10 entry-TF bars",
           "htf_key_level": "corpus: Ibw4saRtYMk timeframe table pairs daily with 1H; daily level = prior-day extreme, declared-before-run",
           "order_flow_range": "declared-before-run: prior week's range as the HTF dealing range for premium/discount",
           "min_coverage": "declared-before-run: skip stub sessions (README trap 6)"}
    p = cl.write_result("mmxm-range-definition", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Range selection 'most obvious swing' is visual; replaced by the canonical "
                              "1h CISD reversal. Tested: does pairing with a HTF key level in "
                              "discount/premium improve the LTF reversal.")
    print(p)
