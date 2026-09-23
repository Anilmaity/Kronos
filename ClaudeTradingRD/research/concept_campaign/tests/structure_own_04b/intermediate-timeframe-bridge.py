"""intermediate-timeframe-bridge (structure, mixed voice, contested) — batch structure_own_04b.

Claim (0bH_kkG2q6s, V8P6lNIisvc; method spec §1.2 rule 10): with a 15m/5m/1m triad the confirming
structure shift must appear on the INTERMEDIATE timeframe (5m) at minimum — "you ideally want to
see a structure shift on the five minute" — and the preferred sequence is a domino, 1m break ->
5m break -> 15m break. yaml measurable: R of entries confirmed on the intermediate timeframe vs
entries taken on the low timeframe alone.

Baseline: the phase-3 rung-0 CISD book on the 1m (the execution timeframe of the stated triad):
series_open, 2/2 swings, max_wait 3, stop at the protected swing, 2R, 10 min (10 x 1m); decide at
the confirming 1m close, enter next M1 open. Structure shift = CISD (the method's change in the
state of delivery). The state of a timeframe at the decision = the direction of its most recent
CISD whose confirming bar has CLOSED by the decision (opposite CISDs confirming on the same bar
= neutral state; fixed after the first probe flagged the unstable tie order, before any test ran).

 a  intermediate confirmation: the 5m state agrees with the 1m entry's direction.
 b  full domino: the 5m AND the 15m states both agree.
Gate vs complement on the same baseline. claim '+'. All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, last_before, HOLD, CISD, RR

LTF, ITF, HTF = "1min", "5min", "15min"


def state(m1, tf, times):
    _, _, e = cisd_frame(m1, tf)
    if len(e) == 0:
        return np.full(len(times), np.nan)
    # CISDs of opposite direction can confirm on the same bar; cisd_events' sort is not stable,
    # so collapse ties to one state per bar (mixed -> 0, neutral) instead of an arbitrary pick.
    g = e.groupby("decision_time")["direction"].agg(["min", "max"])
    st = np.where(g["min"].to_numpy() == g["max"].to_numpy(), g["min"].to_numpy(), 0).astype(float)
    return last_before(pd.DatetimeIndex(g.index), st, times)


def detect(m1):
    _, _, out = cisd_frame(m1, LTF)
    t = out["decision_time"]
    s5 = state(m1, ITF, t)
    s15 = state(m1, HTF, t)
    ok = np.isfinite(s5) & np.isfinite(s15)
    d = out["direction"].to_numpy()
    out["itf_aligned"] = np.where(ok, s5 == d, False).astype(bool)
    out["domino"] = np.where(ok, (s5 == d) & (s15 == d), False).astype(bool)
    return out[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"itb_{LTF}_{ITF}_{HTF}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["itf_aligned"].mean()), float(ev["domino"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    base = ["baseline: 1m CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming 1m close, enter next M1 open; stop at the protected swing, 2R, 10 min wall clock",
            "timeframe state = direction of that timeframe's most recent CISD (same config) whose confirming bar closed at or before the decision"]
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"triad": "corpus: 0bH_kkG2q6s 'you ideally want to see a structure shift on the five minute' (15/5/1 triad); V8P6lNIisvc 'ideally you want to see it kind of domino'",
                "structure_shift": "method_spec: §1.2 rule 10 / CISD is the method's change in state of delivery",
                "state_rule": "declared-before-run: a timeframe has 'shifted' in the direction of its most recent closed CISD (no recency bound; the corpus gives no time bound for the domino)"})
    params = {"triad": "15m/5m/1m", **CISD, "rr": RR, "max_hold": HOLD[LTF], "structure_shift": "CISD", "state_rule": "most recent closed CISD"}
    for reading, col in (("a", "itf_aligned"), ("b", "domino")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD[LTF], claim="+")
        print(reading, {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                                "exposure_bars", "ties", "ctrl_overlap")})
        gate = {"a": ["gate: the 5m (intermediate) state agrees with the 1m entry direction"],
                "b": ["gate: the 5m and the 15m states both agree with the 1m entry direction (the full domino)"]}[reading]
        op = {"rules": base + gate + ["claim: 1m entries confirmed on the higher timeframe(s) beat 1m entries without that confirmation (control-adjusted R)"],
              "params": params}
        path = cl.write_result("intermediate-timeframe-bridge", reading, res, operationalization=op,
                               params_source=src, script=__file__, probe=probe,
                               notes=f"gate firing rate {float(ev[col].mean()):.3f} of {len(ev)} 1m CISDs. "
                                     "Displacement on the intermediate shift is not required (the corpus does not quantify it).")
        print("wrote", path)
