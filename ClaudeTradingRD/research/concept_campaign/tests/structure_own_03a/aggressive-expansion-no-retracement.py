"""aggressive-expansion-no-retracement (TTrades own voice, underspecified) — batch structure_own_03a.

Claim: an AGGRESSIVE expansion yields a very shallow retracement or none at all (so the
trade, if wanted, is taken at the next candle open rather than on a pullback).
"Aggressive" == "displacement" (threshold_fits §2, one term): structural gate = a CLOSE
beyond the broken short-term high; magnitude gate = N=4-candle window from the break with
win_range/pre_range >= 1.5 AND distance-beyond-level/pre_range >= 0.65 (threshold_fits
grade B). "Shallow" (retracement leg) = pullback <= 0.50 of the impulse leg
(threshold_fits §3).

Test: gate_test (claim '+'). Baseline book = every 15m close through a live fractal 2/2
short-term high (mirror: low). Decide at the close of the 4th candle of the break window,
enter at the next M1 open in the break direction ("enter at the open of the new candle"),
stop = the 50% retracement of the impulse leg (leg = lowest low from the swing bar to the
window end -> window extreme; a retracement deeper than 0.5 is the non-shallow outcome),
target = 1R (an equal extension: continuation before a deep retracement), exit 150 min.
Gate = the break is aggressive by the magnitude test. If aggressive expansions really
retrace less, their control-adjusted R beats non-aggressive breaks'.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import cl, np, pd, summary  # noqa: E402

CID = "aggressive-expansion-no-retracement"
TF, N, R_CUT, D_CUT, SHALLOW, RR, HOLD = "15min", 4, 1.5, 0.65, 0.50, 1.0, "150min"


def _bull(o, h, l, c):
    n = len(o)
    piv = np.zeros(n, bool)
    for i in range(2, n - 2):
        if (h[i] > h[i - 2:i]).all() and (h[i] >= h[i + 1:i + 3]).all():
            piv[i] = True
    rows = []
    live = -1          # latest pivot confirmed (close of pivot+2) before the current bar
    used = -1
    pp = np.flatnonzero(piv)
    ptr = 0
    for i in range(N, n - N + 1):
        while ptr < len(pp) and pp[ptr] + 2 < i:
            live = pp[ptr]
            ptr += 1
        if live < 0 or live == used:
            continue
        lvl = h[live]
        if not (c[i] > lvl):
            continue
        # skip if an earlier bar since the pivot already closed through it
        if (c[live + 1:i] > lvl).any():
            used = live
            continue
        used = live
        e = i + N - 1
        whi = h[i:e + 1].max()
        wr = whi - l[i:e + 1].min()
        pre = h[i - N:i].max() - l[i - N:i].min()
        if not pre > 0:
            continue
        dist = whi - lvl
        aggressive = (wr / pre >= R_CUT) and (dist / pre >= D_CUT)
        leg_lo = l[live:e + 1].min()
        leg_hi = h[live:e + 1].max()
        stop = leg_hi - SHALLOW * (leg_hi - leg_lo)
        if not c[e] > stop:
            continue
        rows.append((e, stop, aggressive))
    return rows


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rows = []
    for d, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        rows += [(e, d, d * s, a) for e, s, a in _bull(*arrs)]
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "aggressive"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["e", "d", "stop", "agg"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[r["e"].to_numpy()])
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct,
                       "direction": r["d"].to_numpy().astype(int),
                       "stop_px": r["stop"].to_numpy(float), "rr": RR,
                       "aggressive": r["agg"].to_numpy(bool)})
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"aenr_{TF}_{N}_{R_CUT}_{D_CUT}_{SHALLOW}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["aggressive"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "aggressive", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    rules = [f"{TF} bars; live short-term high = latest fractal 2/2 swing high confirmed before "
             "the bar; break = first CLOSE above it (mirror for lows)",
             f"window = {N} candles from the break bar; decide at the close of its last candle",
             f"aggressive := win_range/pre_range >= {R_CUT} AND (window extreme - level)/pre_range "
             f">= {D_CUT} (pre_range = the {N} candles before the break)",
             "enter next M1 open in the break direction; stop = 50% retracement of the impulse "
             "leg (lowest low from the swing bar to the window end -> window high); skip if the "
             f"window already closed beyond it; target {RR}R; exit after {HOLD}",
             "gate_test: aggressive breaks vs the rest, control-adjusted R, claim '+'"]
    params = {"tf": TF, "window_n": N, "r_cut": R_CUT, "d_cut": D_CUT, "swing": "fractal 2/2",
              "shallow_cut": SHALLOW, "rr": RR, "max_hold": HOLD}
    src = {"tf": "corpus: aggressive-expansion-no-retracement.yaml timeframes ltf 15m",
           "window_n": "threshold_fits: §2 displacement magnitude N=4",
           "r_cut": "threshold_fits: §2 win_range/pre_range >= 1.5",
           "d_cut": "threshold_fits: §2 dist/pre_range >= 0.65",
           "swing": "threshold_fits: §2 breaks of fractal 2/2 short-term highs/lows",
           "shallow_cut": "threshold_fits: §3 shallow retracement leg <= 0.50",
           "rr": "declared-before-run: 1R = an equal extension, the no-retracement outcome "
                 "against the deep-retracement outcome",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="The aggressive classifier is threshold_fits' absolute proxy for "
                              "the corpus's relative displacement test; the corpus gives no "
                              "classifier of its own (status underspecified).")
    print("  wrote", p)


if __name__ == "__main__":
    main()
