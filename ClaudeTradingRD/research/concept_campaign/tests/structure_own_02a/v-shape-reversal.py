"""v-shape-reversal (TTrades own voice, underspecified) — batch structure_own_02a.

The yaml gives three roles; the one with a decidable, directional claim is role 3
(and its measurable): "a V-shape not occurring at a relevant level does not create a
tradeable framework" — "Continuation rate after V-shapes at relevant levels vs away from
them". Roles 1/2 (substitute for CISD; reclassification of a deep retracement) are
labelling rules, not outcome claims.

V-shape (declared before the run; the corpus gives no geometry):
  15m extreme = the lowest low of the prior 20 bars (mirror: highest high); leg = from the
  highest high of those 20 bars down to the extreme. V completes at the FIRST candle,
  within 3 candles after the extreme and with no new extreme, whose close has retraced
  >= 0.62 of the leg (the OTE depth of role 2 — "reaching OTE of the leg" is what makes a
  retracement a V-shape reversal). Direction = the V's direction.
Baseline book: every V; decide at the completing close, enter next M1 open in the V's
direction, stop behind the V extreme, 2R target, 150-min exit (phase-3 15m).
Gate: relevant level = the extreme traded beyond the previous trading day's low/high
(18:00 NY day) or the previous week's low/high ("previous day and previous week extremes
are always relevant", method_spec §2.7). claim '+': V at relevant levels beat V elsewhere.
The corpus enters "only on the following continuation"; both arms share the at-the-V
entry, so the gate isolates the relevance claim.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "v-shape-reversal"
TF, LB, MAX_K, DEPTH, RR, HOLD = "15min", 20, 3, 0.62, 2.0, "150min"


def v_events(b):
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(b)
    rows = []
    for bull in (True, False):
        x = l if bull else -h
        top = h if bull else -l
        cc = c if bull else -c
        for pos in range(LB, n - 1):
            xp = x[pos]
            if not (x[pos - LB:pos] > xp).all():
                continue
            thr = xp + DEPTH * (top[pos - LB:pos].max() - xp)
            for j in range(pos + 1, min(n, pos + MAX_K + 1)):
                if x[j] < xp:
                    break
                if cc[j] >= thr:
                    rows.append((j, pos, 1 if bull else -1, xp if bull else -xp))
                    break
    ev = pd.DataFrame(rows, columns=["j", "pos", "dir", "extreme"])
    return ev.drop_duplicates(["j", "dir"]).sort_values(["j", "dir"]).reset_index(drop=True)


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = v_events(b)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy())
    xt = ct[ev["pos"].to_numpy()]
    d = cl.prior_hilo(xt, "1D", m1=m1, min_coverage=0.5)
    w = cl.prior_hilo(xt, "1W", m1=m1)
    bull = ev["dir"].to_numpy() > 0
    x = ev["extreme"].to_numpy()
    dl, dh, wl, wh = (d["low"].to_numpy(), d["high"].to_numpy(), w["low"].to_numpy(),
                      w["high"].to_numpy())
    ok = np.isfinite(np.where(bull, dl, dh)) & np.isfinite(np.where(bull, wl, wh))
    rel = np.where(bull, (x < dl) | (x < wl), (x > dh) | (x > wh))
    j = ev["j"].to_numpy()
    out = pd.DataFrame({"decision_time": ct[j], "available_at": ct[j],
                        "direction": ev["dir"].to_numpy().astype(int), "stop_px": x,
                        "rr": RR, "relevant": rel})
    return out[ok].reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"vshape_{TF}_{LB}_{MAX_K}_{DEPTH}", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "relevant", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    rules = [f"{TF} extreme = lowest low (highest high) of the prior {LB} bars; leg = from the "
             f"highest high (lowest low) of those {LB} bars to the extreme",
             f"V completes at the first close within {MAX_K} candles after the extreme (no new "
             f"extreme) that has retraced >= {DEPTH} of the leg",
             f"decide at that close, enter next M1 open in the V's direction, stop = the V "
             f"extreme, {RR}R, exit after {HOLD}",
             "gate: the extreme traded beyond the previous trading day's (18:00 NY, coverage "
             ">= 0.5) or previous week's low/high"]
    params = {"tf": TF, "leg_lookback": LB, "max_k": MAX_K, "depth": DEPTH, "rr": RR,
              "max_hold": HOLD, "levels": "PDH/PDL (min_coverage 0.5), PWH/PWL"}
    src = {"tf": "corpus yaml timeframes: ltf 15m (htf 4H/1H)",
           "leg_lookback": "phase3: lookback 20 knob",
           "max_k": "corpus: PQiRV0JMhIQ 'It only takes a couple candles. Now, I prefer 1 2 maybe three.' (v-shape-reversal-speed)",
           "depth": "corpus yaml role 2: 'if the retracement of an expansion leg is deep (reaching OTE of the leg), reclassify as V-shape reversal' — OTE entry 0.62",
           "rr": "phase3: 2R", "max_hold": "phase3: 15m book 150-min exit",
           "levels": "method_spec: §2.7 'Reversal -> only at a relevant level; previous day and previous week extremes always qualify'"}
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Tests role 3 only (relevant level vs elsewhere). No geometric "
                              "V definition exists in the corpus; this one is declared from "
                              "the related speed concept (1-3 candles) and role 2's OTE depth.")
    print("  wrote", p)


if __name__ == "__main__":
    main()
