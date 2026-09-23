"""htf-two-entry-opportunities — $niper: a higher-timeframe (W/D/4H) buy-side curve gives TWO
entry opportunities (taps into same-TF FVGs) before the premium array; a lower-timeframe curve
gives ONE. Used as a budget: once spent, the next event is the premium array, not another entry.

Operationalisation (bullish; bearish = same on negated prices):
  leg anchor = the earliest confirmed 2/2 swing low in the last LEG_MAX bars that no later
               bar has traded below (the curve low; see bull_taps).
  opportunity = the first tap of a bullish FVG formed (third bar) after the anchor pivot:
               a bar with low <= gap_high and close >= gap_low (FVG not closed through yet).
               Several FVGs tapped by one bar count as ONE opportunity.
  trade = long at the tap bar's close (next M1 open), stop = min(lowest tapped gap_low, tap-bar low),
          2R target, 10 entry-TF bars max hold.
  tap_no = 1, 2, 3, ... within the leg.
Reading a (4H = higher timeframe): gate = tap_no <= 2 (inside the budget) vs tap_no >= 3.
Reading b (1H = lower timeframe):  gate = tap_no <= 1 vs tap_no >= 2.
claim '+': in-budget taps beat the taps the budget says not to take.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "htf-two-entry-opportunities"
LEG_MAX = 120
RR = 2.0
CFG = {"a": ("4h", 2, "40h", "60D"), "b": ("1h", 1, "10h", "20D")}


def swing_lows(l, left=2, right=2):
    ls = pd.Series(l)
    prev_l = ls.shift(1).rolling(left).min()
    next_l = ls[::-1].shift(1).rolling(right).min()[::-1]
    return ((ls < prev_l) & (ls <= next_l)).to_numpy()


def bull_taps(h, l, c):
    """History-bounded definition (everything depends only on the last LEG_MAX bars):
    anchor(j) = the EARLIEST confirmed 2/2 swing low pivoting in [j-LEG_MAX, j-2] that no bar
    since has traded below (the curve low); an FVG k's first touch t_k (first bar after k with
    low <= gap_high) is an opportunity iff it closes >= gap_low; tap_no(j) = number of
    opportunity bars in (anchor, j] whose tapped FVG formed after the anchor."""
    n = len(h)
    is_l = swing_lows(l)
    piv = np.where(is_l)[0]
    bull = np.where(np.r_[False, False, l[2:] > h[:-2]])[0]
    glo = np.r_[np.nan, np.nan, h[:-2]]
    ghi = l
    taps = {}                      # bar j -> list of FVG k first-touched validly at j
    for k in bull:
        j = k + 1
        stop_j = min(n, k + 1 + LEG_MAX + 2)
        while j < stop_j and l[j] > ghi[k]:
            j += 1
        if j < stop_j and c[j] >= glo[k]:
            taps.setdefault(j, []).append(k)
    out = []
    for j in sorted(taps):
        lo_p = np.searchsorted(piv, j - LEG_MAX)
        hi_p = np.searchsorted(piv, j - 2, side="right")
        A = None
        for p in piv[lo_p:hi_p]:
            if l[p + 1:j + 1].min() >= l[p]:
                A = p
                break
        if A is None:
            continue
        ks = [k for k in taps[j] if k > A]
        if not ks:
            continue
        cnt = 0
        for jj in range(A + 1, j + 1):
            if jj in taps and max(taps[jj]) > A:
                cnt += 1
        stop = min(min(glo[k] for k in ks), l[j])
        out.append((j, cnt, stop))
    return out


def detect_tf(m1, tf, budget):
    b = cl.build_bars(m1, tf)
    h, l, c = (b[x].to_numpy() for x in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for sgn, (hh, ll, cc) in ((1, (h, l, c)), (-1, (-l, -h, -c))):
        for i, k, stop in bull_taps(hh, ll, cc):
            rows.append((ct[i], sgn, stop * sgn, k))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "tap_no", "in_budget"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "tap_no"])
    df = df.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.decision_time, "available_at": df.decision_time,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "rr": RR, "tap_no": df.tap_no.astype(int),
                         "in_budget": (df.tap_no <= budget).to_numpy()})


if __name__ == "__main__":
    reading = sys.argv[1]
    tf, budget, hold, lb = CFG[reading]
    det = lambda m: detect_tf(m, tf, budget)
    ev = cl.cache_frame(f"{CID}_{tf}_b{budget}_leg{LEG_MAX}", lambda: det(cl.load_m1()))
    print(len(ev), ev.in_budget.mean(), ev.tap_no.value_counts().sort_index().head(8).to_dict())
    if "--dry" in sys.argv:
        raise SystemExit
    probe = cl.probe_lookahead(det, ev, lookback=lb)
    res = cl.gate_test(ev, "in_budget", mask_available_at="decision_time", max_hold=hold, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        f"{tf} bars; leg anchor at bar j = earliest confirmed 2/2 swing low pivoting in the last "
        f"{LEG_MAX} bars that no later bar has traded below (the curve low)",
        "opportunity = first tap of a same-direction FVG formed after the anchor (low<=gap_high, "
        "close>=gap_low); one bar = one opportunity",
        "long at tap-bar close (next M1 open); stop = min(tapped gap_low, tap-bar low); 2R; "
        f"max hold {hold}; bearish mirrored",
        f"gate = tap_no <= {budget} (the stated budget for a "
        f"{'higher' if budget == 2 else 'lower'}-timeframe curve) vs later taps"],
        "params": {"tf": tf, "budget": budget, "leg_max_bars": LEG_MAX, "swing": "2/2",
                   "rr": RR, "max_hold": hold}}
    src = {"tf": "corpus: UmLWRlXd_V8 'the weekly the daily and the four hour' = HTF; 1H = first LTF below",
           "budget": "corpus: UmLWRlXd_V8 'two opportunities before reaching its premium' / 'one opportunity to buy'",
           "leg_max_bars": "declared-before-run: the curve is looked for in the last 120 bars only (bounds the budget window and the probe warm-up); set before the first probe/test",
           "swing": "phase3: meta/conjunction_preregistration.md §1.8 left=2,right=2",
           "rr": "phase3: §1.12 primary 2R fixed",
           "max_hold": "phase3: §1.13 10 entry-TF periods"}
    notes = ("The premium array that ends a curve is not located objectively in the source, so the "
             "curve is bounded by its anchor low and a 120-bar look-back (a first stateful-chain "
             "version failed the lookahead probe on warm-up path dependence and was replaced before "
             "any test ran); the budget claim is tested as "
             "'in-budget taps outperform over-budget taps'.")
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes, probe=probe)
    print(p)
