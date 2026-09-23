"""multi-timeframe-fvg-indicator (guest: Trade For Opportunity, 0bH_kkG2q6s).

Claim: "a five-minute gap that coincides with gaps from a couple of other
timeframes" is "more likely to be reactive" (no guarantee). Gate test:

  baseline book  every 5m three-candle FVG, traded on its first return: the
                 first M1 that trades into the gap within 48 5m bars (4h), decided
                 at that M1's close if it has not closed beyond the far edge;
                 enter next M1 open in the gap's direction, stop at the far edge,
                 target 2R, max hold 10 5m bars.
  gate           at the decision (what the indicator shows when price returns),
                 the 5m gap's zone intersects at least one SAME-direction 10m or
                 15m gap formed within the prior 4h whose far edge has not been
                 traded through since.
First run evaluated the gate at the 5m gap's close instead; fixed after seeing
that verdict (NULL, gate rate 3.9%) because the indicator is read when price
returns to the gap, not when the gap forms. Both runs are in the ledger.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
import concept_lab as cl
from detectors.primitives import fair_value_gaps

MAX_AGE = 48
RR = 2.0
MAX_HOLD = "50min"
HTFS = ("10min", "15min")
HTF_LIVE = pd.Timedelta("4h")


def _gaps(m1, tf):
    b = cl.build_bars(m1, tf)
    b = b[b["n_m1"] > 0]
    g = fair_value_gaps(b)
    out = []
    for bull in (True, False):
        m = g["bullish_fvg" if bull else "bearish_fvg"].to_numpy()
        out.append(pd.DataFrame({"t": pd.DatetimeIndex(b["close_time"])[m], "bull": bull,
                                 "lo": g["gap_low"].to_numpy()[m],
                                 "hi": g["gap_high"].to_numpy()[m]}))
    return pd.concat(out).sort_values("t").reset_index(drop=True)


def detect(m1):
    B = cl.build_bars(m1, "5min")
    B = B[B["n_m1"] > 0]
    n = len(B)
    g = fair_value_gaps(B)
    hi, lo = B["high"].to_numpy(), B["low"].to_numpy()
    first = pd.DatetimeIndex(B["first_m1"])
    last = pd.DatetimeIndex(B["last_m1"])
    ctime = pd.DatetimeIndex(B["close_time"])
    m1t = m1.index
    m1l, m1h, m1c = m1["low"].to_numpy(), m1["high"].to_numpy(), m1["close"].to_numpy()
    nm = len(m1t)
    pad = np.full(MAX_AGE, np.nan)
    Lw = sliding_window_view(np.concatenate([lo, pad]), MAX_AGE + 1)[:n, 1:]
    Hw = sliding_window_view(np.concatenate([hi, pad]), MAX_AGE + 1)[:n, 1:]
    htf = pd.concat([_gaps(m1, tf) for tf in HTFS]).sort_values("t").reset_index(drop=True)
    ht_ns = cl.data.utc_ns(htf["t"])
    ct_ns = cl.data.utc_ns(ctime)
    # 5m-bar position of each HTF gap's close (first 5m bar starting at/after it)
    first_ns = cl.data.utc_ns(first)
    m1_ns = cl.data.utc_ns(m1t)
    rows = []
    for bull in (True, False):
        gi = np.where(g["bullish_fvg" if bull else "bearish_fvg"].to_numpy())[0]
        if not len(gi):
            continue
        ghi, glo = g["gap_high"].to_numpy()[gi], g["gap_low"].to_numpy()[gi]
        hitm = (Lw[gi] <= ghi[:, None]) if bull else (Hw[gi] >= glo[:, None])
        has = hitm.any(axis=1)
        gi, ghi, glo, k = gi[has], ghi[has], glo[has], (np.argmax(hitm, axis=1) + 1)[has]
        j = gi + k
        s = m1t.searchsorted(first[j])
        e = m1t.searchsorted(last[j], side="right")
        q = np.full(len(gi), -1)
        for off in range(4, -1, -1):          # earliest M1 inside bar j that trades in
            p = s + off
            ok = p < e
            pp = np.minimum(p, nm - 1)
            hit = ok & ((m1l[pp] <= ghi) if bull else (m1h[pp] >= glo))
            q = np.where(hit, p, q)
        good = q >= 0
        gi, ghi, glo, q = gi[good], ghi[good], glo[good], q[good]
        cpx = m1c[q]
        good = (cpx > glo) if bull else (cpx < ghi)
        gi, ghi, glo, q = gi[good], ghi[good], glo[good], q[good]
        # the gate: overlap with a same-direction 10m/15m gap on the chart at the
        # DECISION (the touch M1's close): formed within the prior 4h and its far
        # edge not traded through (M1 lows/highs from its close to the touch M1).
        hsel = (htf["bull"] == bull).to_numpy()
        hts, hlo, hhi = ht_ns[hsel], htf["lo"].to_numpy()[hsel], htf["hi"].to_numpy()[hsel]
        hq = np.searchsorted(m1_ns, hts, side="left")      # first M1 after HTF gap close
        live_ns = np.timedelta64(int(HTF_LIVE.value), "ns")
        dec_ns = m1_ns[q] + np.timedelta64(60, "s")
        gate = np.zeros(len(gi), bool)
        for a in range(len(gi)):
            T = dec_ns[a]
            r1 = np.searchsorted(hts, T, side="right")
            r0 = np.searchsorted(hts, T - live_ns, side="left")
            for c in range(r0, r1):
                if hlo[c] > ghi[a] or hhi[c] < glo[a]:
                    continue
                if hq[c] > q[a]:
                    alive = True
                elif bull:
                    alive = m1l[hq[c]:q[a] + 1].min() > hlo[c]
                else:
                    alive = m1h[hq[c]:q[a] + 1].max() < hhi[c]
                if alive:
                    gate[a] = True
                    break
        rows.append(pd.DataFrame({
            "decision_time": m1t[q] + pd.Timedelta("1min"),
            "direction": 1 if bull else -1,
            "stop_px": glo if bull else ghi,
            "gap_close": ctime[gi],
            "mtf_overlap": gate}))
    ev = pd.concat(rows, ignore_index=True)
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    return ev.sort_values(["decision_time", "direction", "gap_close"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"mtf_fvg_5m_{MAX_AGE}_atdecision", lambda: detect(cl.load_m1()))
    print(len(ev), ev.mtf_overlap.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    res = cl.gate_test(ev, "mtf_overlap", mask_available_at="decision_time", max_hold=MAX_HOLD)
    for k in ("n", "n_gated", "gate_rate", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline: every 5m 3-candle FVG traded on its first M1 return within 48 5m bars; "
        "decide at that M1 close if not closed beyond the far edge; enter next M1 open; "
        "stop at the far edge; target 2R; max hold 50 min",
        "gate: at the decision, the 5m gap intersects >= 1 same-direction 10m or 15m FVG "
        "formed within the prior 4h and whose far edge has not been traded through (M1) "
        "from its close up to the touch M1",
        "mask known at the decision"],
        "params": {"entry_tf": "5min", "sources": list(HTFS), "max_age_bars": MAX_AGE,
                   "rr": RR, "max_hold": MAX_HOLD, "htf_live": "4h", "min_overlaps": 1}}
    src = {"entry_tf": "corpus: 0bH_kkG2q6s 'a five-minute gap that coincides with gaps from "
                       "a couple of other timeframes'",
           "sources": "corpus: 0bH_kkG2q6s preferred sources 5/10/15-minute",
           "max_age_bars": "declared-before-run: a 5m gap stays live 4h",
           "rr": "method_spec §5.3: 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "htf_live": "declared-before-run: HTF gap considered live 4h unless traded through",
           "min_overlaps": "declared-before-run: overlap count unstated; >=1 other timeframe"}
    print(cl.write_result("multi-timeframe-fvg-indicator", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Gate test of the indicator's one testable claim: MTF overlap "
                                "makes a gap more reactive. A first run evaluated overlap at the "
                                "5m gap's close (gate rate 3.9%, diff +0.038 [-0.008,+0.084] "
                                "NULL); fixed to evaluate at the touch/decision, as the chart "
                                "shows it, and re-run once. Both runs are ledgered."))
