"""relevant-swing-separation (structure, TTrades own voice, contested) — batch structure_own_04b.

Claim (c7nk7ypJHN4, XCYmGJWnsAg, 28_luJwwVbw): a low is only a level to trade AWAY from when it
has enough separation from the previous (outer) low that "one could hold while the other is
taken"; a low sitting close to the previous low is not trusted, "not enough valid separation to
trust trading away from this low" without the earlier low being taken. Execution (yaml): entry
only away from a relevant, separated swing; stop beyond that swing.

Gate test on the phase-3 rung-0 1h CISD book (series_open, 2/2, max_wait 3, stop at the
protected swing = the swing traded away from, 2R, 10h). Baseline restricted to reversals whose
extreme did NOT take any earlier same-side swing and has an earlier, still-untaken, confirmed
same-side 1h three-candle swing beyond it inside the three-day look-back window (the
"previous low" it is compared with). Separation = distance from the extreme to the nearest such
outer swing. Gate (relevant) = separation >= 0.5 x ATR14 of the completed daily bars.
Complement = too close. claim '+'.

The single reading covers every variant in the yaml; the contested points (failure-swing
precedence, relevance migration) are not decidable without a threshold the corpus lacks.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, swing_points, atr, last_before, HOLD, CISD, RR

TF = "1h"
WINDOW_DAYS = 3
SEP_ADR = 0.5
SW = (1, 1)


def detect(m1):
    b, ev, out = cisd_frame(m1, TF)
    if len(out) == 0:
        out["separated"] = pd.Series(dtype=bool)
        out["sep_adr"] = pd.Series(dtype=float)
        return out
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    sw = swing_points(b[["high", "low"]], *SW)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    td = cl.trading_day(b.index)
    dc = pd.factorize(pd.Series(td.to_numpy()), sort=True)[0]
    first = {}
    for k, d in enumerate(dc):
        first.setdefault(d, k)
    d1 = cl.build_bars(m1, "1D")
    d1_atr = atr(d1)
    adr = last_before(d1["close_time"], d1_atr, out["decision_time"])
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    bull = out["direction"].to_numpy() == 1
    R = SW[1]
    sep = np.full(len(ev), np.nan)
    for e, p in enumerate(pos):
        d = dc[p]
        if d - (WINDOW_DAYS - 1) not in first:
            continue
        w0 = first[d - (WINDOW_DAYS - 1)]
        last_s = p - 1 - R
        if last_s < w0:
            continue
        if bull[e]:
            cand = np.flatnonzero(sl[w0:last_s + 1]) + w0
            live = [s for s in cand if p - s <= 1 or l[s + 1:p].min() >= l[s]]      # untaken before p
            if any(l[p] < l[s] for s in live):                                     # extreme took one: a sweep, excluded
                continue
            outer = [l[p] - l[s] for s in live if l[s] <= l[p]]
        else:
            cand = np.flatnonzero(sh[w0:last_s + 1]) + w0
            live = [s for s in cand if p - s <= 1 or h[s + 1:p].max() <= h[s]]
            if any(h[p] > h[s] for s in live):
                continue
            outer = [h[s] - h[p] for s in live if h[s] >= h[p]]
        if outer:
            sep[e] = min(outer)
    sep_adr = sep / adr
    keep = np.isfinite(sep_adr)
    out["sep_adr"] = sep_adr
    out["separated"] = np.where(keep, sep_adr >= SEP_ADR, False).astype(bool)
    return out[keep].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"rss_{TF}_w{WINDOW_DAYS}_s{SEP_ADR}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["separated"].mean()), ev["sep_adr"].describe().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "separated", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "baseline: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open; stop at the protected swing (the low/high traded away from), 2R, 10h wall clock",
        "baseline kept only when the reversal extreme took no untaken same-side 1h three-candle swing of the 3-trading-day window and at least one such swing lies beyond it (the 'previous low' it could leave untaken)",
        "separation = distance from the extreme to the nearest untaken outer same-side swing, in units of ATR14 of completed daily bars",
        "gate: separation >= 0.5 ADR (relevant, trustworthy to trade away from); complement: too close",
        "claim: separated reversals beat too-close reversals (control-adjusted R)"],
        "params": {"tf": TF, **CISD, "rr": RR, "max_hold": HOLD[TF], "window_days": WINDOW_DAYS,
                   "sep_adr": SEP_ADR, "adr": "ATR14 of completed 1D bars (18:00 NY roll)", "swing": "1/1 fractal"}}
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({"window_days": "corpus: HbOeD_JVens three-HTF-candle look-back (hourly chart -> three days)",
                "sep_adr": "declared-before-run: corpus instance c7nk7ypJHN4 '400 points' of NASDAQ ~ half to one NQ daily range; the lower bound 0.5 ADR used (the corpus gives no threshold)",
                "adr": "declared-before-run: ADR as ATR14 of daily bars (yaml measurable 'separation normalised by ADR')",
                "swing": "method_spec: §1.1 swing point = three-candle fractal"})
    p = cl.write_result("relevant-swing-separation", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"gate firing rate {float(ev['separated'].mean()):.3f} of {len(ev)} internal reversals. "
                              "Separation is never quantified in the corpus; 0.5 ADR is a declared reading of the one NQ instance.")
    print("wrote", p)
