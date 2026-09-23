"""continuation-over-reversal (model, TTrades own voice, contested).

Claim: never enter on the reversal CISD itself; enter on the continuation that follows it
(bullish: a higher low after the reversal, then a new close through the opposing series).
Measurable: "win rate of reversal-CISD entries versus continuation entries on the same swings".

gate_test on a 15m CISD book (phase-3 locked CISD, entry at the confirming close, stop at the
protected swing, 2R, 10 entry bars):
  * reversal CISD      = the previous CISD was in the OPPOSITE direction (a change of delivery)
  * continuation CISD  = the previous CISD was in the SAME direction, its protected swing held
                         from its confirmation to this confirmation, and this CISD's extreme
                         formed after that confirmation and beyond it (higher low / lower high)
  * same-direction CISDs whose prior protected swing was broken (re-anchors) are dropped.
gate = continuation; claim '+' (continuations beat reversals, control-adjusted).
Single reading: the variants (C3 vs C2, "reversal only when bias very strong") are all the
same selection preference; the one decidable form is reversal-CISD vs continuation-CISD.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

TF = "15min"
RR = 2.0
MAX_HOLD = "150min"


def detect(m1):
    b = C.complete_bars(m1, TF)
    cz = C.cisd_table(b)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_cont"]
    if len(cz) < 2:
        return pd.DataFrame(columns=cols)
    lows = b["low"].to_numpy(); highs = b["high"].to_numpy()
    ct = C.utc = pd.DatetimeIndex(b["close_time"]).as_unit("ns").asi8
    tpos = np.searchsorted(ct, pd.DatetimeIndex(cz["t"]).as_unit("ns").asi8)   # confirm bar pos
    rows = []
    for k in range(1, len(cz)):
        p, c = cz.iloc[k - 1], cz.iloc[k]
        if c["t"] == p["t"]:
            continue
        if c["dir"] != p["dir"]:
            is_cont = False
        else:
            a0, a1 = tpos[k - 1] + 1, tpos[k] + 1          # bars after prev confirm .. this confirm
            if c["extreme_start"] <= p["t"] - pd.Timedelta(minutes=15) or a1 <= a0:
                continue
            if c["dir"] == 1:
                held = lows[a0:a1].min() > p["stop"]
                beyond = c["extreme_price"] > p["stop"]
            else:
                held = highs[a0:a1].max() < p["stop"]
                beyond = c["extreme_price"] < p["stop"]
            if not (held and beyond):
                continue
            is_cont = True
        rows.append({"decision_time": c["t"], "available_at": c["t"], "direction": int(c["dir"]),
                     "stop_px": float(c["stop"]), "rr": RR, "is_cont": is_cont})
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    out["is_cont"] = out["is_cont"].astype(bool)
    return out


if __name__ == "__main__":
    ev = cl.cache_frame("cor_events_15m_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["is_cont"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    r = cl.gate_test(ev, "is_cont", mask_available_at="decision_time", max_hold=MAX_HOLD)
    print({k: r.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars")})
    params = {"tf": TF, "cisd": "series_open, swing 2/2, max_wait 3, min_series 1",
              "rr": RR, "max_hold": MAX_HOLD,
              "continuation_def": "prev CISD same dir, its protected swing held to this confirm, "
                                  "new extreme after prev confirm and beyond prev protected swing"}
    src = {"tf": "phase3: 15m entry TF of his favourite 15m/4H/1D stack",
           "cisd": "phase3: locked CISD config",
           "rr": "corpus: U1NJUh1RqMw 'entry on the close, my stop on the low' 2R target",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "continuation_def": "corpus: Qv6Ux_Z8VrA 'waiting for a lower high if bearish and a higher low if bullish'; method_spec §4.5"}
    cl.write_result("continuation-over-reversal", None, r,
                    operationalization={"rules": [
                        "15m phase-3 CISD events, decide at the confirming close, enter next M1 "
                        "open, stop at the protected swing, 2R, exit after 150 min",
                        "reversal = previous CISD opposite direction; continuation = previous CISD "
                        "same direction whose protected swing held, new extreme beyond it and "
                        "after its confirmation (higher low / lower high); re-anchors dropped",
                        "gate = continuation vs reversal complement; claim '+'"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe)
