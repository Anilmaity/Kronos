"""orderflow-tight-stop-profile (HolyAngelBruv, guest): ~40% win rate with a 2.5-point stop and
an 8-point first target (3.2R), runners left.

The order-flow (footprint/DOM) confirmation is not in OHLC data; the ICT point-of-interest
entry is proxied by the bare 5m CISD (the concept's LTF list is 5m/1m/15s). The testable
part is the risk profile itself: a tight fixed stop with a 3.2R target on these entries,
scored against the harness's matched random-entry control of identical geometry
(claim '+': the entries beat random under this profile).
  stop  = 2.5 ES points expressed as a fraction of price: 2.5 / 4000 = 0.0625% of entry
  target = 8 / 2.5 = 3.2R; runners have no exit rule -> not modelled (full exit at T1)
  max_hold = 10 entry-TF bars = 50 min
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book

STOP_FRAC = 2.5 / 4000.0
RR = 8.0 / 2.5


def detect(m1):
    ev = cisd_book(m1, "5min")
    out = ev[["decision_time", "available_at", "direction"]].copy()
    out["stop_dist"] = ev["entry_ref"].to_numpy(float) * STOP_FRAC
    out["rr"] = RR
    return out


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_tightstop_5mcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events")
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.trade_test(ev, max_hold="50min", claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": ["entries: bare 5m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming 5m close, enter next M1 open -- a proxy for the order-flow-confirmed ICT POI entry",
                    "stop = 0.0625% of price (2.5 ES points at ES 4000)",
                    "target = 3.2R (8 points / 2.5 points); runners not modelled (no exit rule stated)",
                    "exit after 50 minutes if neither hit"],
          "params": {"entry_tf": "5min", "stop_frac": STOP_FRAC, "rr": RR, "max_hold": "50min",
                     "level_rule": "series_open", "swing": "2/2", "max_wait": 3}}
    src = {"entry_tf": "declared-before-run: concept LTF list 5m/1m/15s; 5m CISD as the ICT-POI entry proxy",
           "stop_frac": "corpus: 8Z2AbZLjunU 'two and a half point stop loss' (ES points, ES~4000 -> % of price, declared-before-run)",
           "rr": "corpus: 8Z2AbZLjunU 'then i go for eight points' (8/2.5)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "level_rule": "phase3: locked CISD config", "swing": "phase3: locked CISD config",
           "max_wait": "phase3: locked CISD config"}
    p = cl.write_result("orderflow-tight-stop-profile", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Order-flow confirmation (footprint/DOM) is not in OHLC; this tests the stated tight-stop/3.2R profile on a CISD proxy entry. Runners untested (no exit rule).")
    print(p)
