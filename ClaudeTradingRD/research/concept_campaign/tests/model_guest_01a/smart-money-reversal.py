"""smart-money-reversal (guest, contested) — two readings, declared before the first run.

Shared base: 15m bare CISD, phase-3 locked config (close through the opening price of the
opposing candle series after a 2/2 swing, within 3 bars).

Reading a — the components reading (foundation units + the gold example): a reversal is
  a smart money reversal when ALL of these hold, and it is traded:
  * HTF level reached: the reversal extreme took the prior NY day's low (bull) / high (bear);
  * change in state of delivery: the 15m CISD close over the down-close series;
  * inversion: by the CISD bar, a 15m close has gone above the gap high of the last bearish
    FVG stamped in the 8 bars up to the extreme (mirrored for bearish);
  * a short-term low is put in: after the CISD, a 1/1 fractal low above the extreme,
    confirmed within 8 bars — decide at the confirming bar's close.
  Long at the next M1 open, stop at the reversal extreme, target 2R, hold 10 bars (150 min,
  trading time).
Reading b — Finessee_Fx: "the smart money reversal always happens at a higher-timeframe PD
  array". Gate on the bare 15m CISD book (stop protected swing, 2R, 150 min): mask = the
  reversal extreme lies inside a DAILY PD array of the matching side — an unmitigated daily
  FVG or daily order block (body zone of the opposing series before a daily CISD), formed on
  completed daily bars within the last 60 trading days and not closed through since.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.blocks import order_blocks  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402

TF = "15min"
RR = 2.0
HOLD = "150min"
FVG_LOOKBACK = 8
STL_WAIT = 8
ARRAY_AGE_D = 60


def _cisd(m1):
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    return b, ev


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b, ev = _cisd(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    idx = b.index
    pos_of = pd.Series(np.arange(len(b)), index=idx)
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"])
    fg = fair_value_gaps(b)
    bull_f, bear_f = fg["bullish_fvg"].to_numpy(), fg["bearish_fvg"].to_numpy()
    glo, ghi = fg["gap_low"].to_numpy(), fg["gap_high"].to_numpy()
    xpos = pos_of[ev["extreme_time"]].to_numpy()
    cpos = pos_of[ev["confirm_time"]].to_numpy()
    ph = cl.prior_hilo(ct[xpos], "1D", m1=m1, min_coverage=0.5)
    rows = []
    for k in range(len(ev)):
        bull = ev["direction"].iat[k] == "bullish"
        x, cf = xpos[k], cpos[k]
        ext = ev["extreme_price"].iat[k]
        # HTF level: extreme took the prior day low/high
        lvl = ph["low"].iat[k] if bull else ph["high"].iat[k]
        if not np.isfinite(lvl) or (bull and not ext < lvl) or (not bull and not ext > lvl):
            continue
        # inversion: last opposing FVG stamped in the FVG_LOOKBACK bars up to the extreme
        fl = bear_f if bull else bull_f
        cand = [i for i in range(max(0, x - FVG_LOOKBACK), x + 1) if fl[i]]
        if not cand:
            continue
        g = cand[-1]
        seg = c[x:cf + 1]
        if bull and not (seg > ghi[g]).any():
            continue
        if (not bull) and not (seg < glo[g]).any():
            continue
        # short-term low (high) put in after the CISD: 1/1 fractal beyond the extreme
        dec = None
        for j in range(cf + 1, min(len(b) - 1, cf + STL_WAIT) + 1):
            p = j - 1
            if p <= cf - 1:
                continue
            if bull:
                if l[p] < l[p - 1] and l[p] <= l[j] and l[p] > ext:
                    dec = j
                    break
                if l[j] <= ext:
                    break
            else:
                if h[p] > h[p - 1] and h[p] >= h[j] and h[p] < ext:
                    dec = j
                    break
                if h[j] >= ext:
                    break
        if dec is None:
            continue
        rows.append({"decision_time": ct[dec], "available_at": ct[dec],
                     "direction": 1 if bull else -1, "stop_px": ext, "rr": RR})
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)


def _daily_arrays(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 0]
    dct = pd.DatetimeIndex(d["close_time"])
    fg = fair_value_gaps(d)
    arr = []
    for i in np.flatnonzero(fg["bullish_fvg"].to_numpy()):
        arr.append(("bullish", fg["gap_low"].iat[i], fg["gap_high"].iat[i], i))
    for i in np.flatnonzero(fg["bearish_fvg"].to_numpy()):
        arr.append(("bearish", fg["gap_low"].iat[i], fg["gap_high"].iat[i], i))
    ob = order_blocks(d[["open", "high", "low", "close"]], zone="body", level_rule="series_open",
                      left=2, right=2, max_wait=3, min_series=1)
    pos_of = pd.Series(np.arange(len(d)), index=d.index)
    for _, r in ob.iterrows():
        arr.append((r["direction"], r["zone_low"], r["zone_high"], int(pos_of[r["valid_from"]])))
    a = pd.DataFrame(arr, columns=["dir", "lo", "hi", "pos"])
    a["avail"] = dct[a["pos"].to_numpy()]
    return d, dct, a


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b, ev = _cisd(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "at_htf_array"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close_t = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    xt = pd.DatetimeIndex(b.loc[ev["extreme_time"], "close_time"])
    d, dct, a = _daily_arrays(m1)
    dclose = d["close"].to_numpy()
    dn = dct.asi8
    mask = np.zeros(len(ev), dtype=bool)
    for k in range(len(ev)):
        bull = ev["direction"].iat[k] == "bullish"
        p = ev["extreme_price"].iat[k]
        t = xt[k].value
        last = np.searchsorted(dn, t, side="right") - 1        # last daily bar closed by t
        if last < 0:
            continue
        sub = a[(a["dir"] == ("bullish" if bull else "bearish")) & (a["pos"] <= last)
                & (a["pos"] >= last - ARRAY_AGE_D) & (a["lo"] <= p) & (a["hi"] >= p)]
        for _, r in sub.iterrows():
            after = dclose[r["pos"] + 1:last + 1]
            broken = (after < r["lo"]).any() if bull else (after > r["hi"]).any()
            if not broken:
                mask[k] = True
                break
    out = pd.DataFrame({
        "decision_time": close_t, "available_at": close_t,
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR, "at_htf_array": mask,
        "extreme_close": xt})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


BASE_SRC = {"tf": "phase3: 15m entry TF of the primary stack",
            "cisd": "phase3: series_open, 2/2 swing, max_wait 3 (conjunction_preregistration locked config)",
            "rr": "phase3: 2R target",
            "max_hold": "phase3: 10 entry-TF bars (§1.13)",
            "hold_basis": "declared-before-run: trading-time hold across the 17:00 halt (trap 7)"}
BASE_PARAMS = {"tf": TF, "cisd": "series_open 2/2 max_wait 3", "rr": RR, "max_hold": HOLD,
               "hold_basis": "bars"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    m1 = cl.load_m1()
    if "a" in which:
        ea = cl.cache_frame("smr_a_v1", lambda: detect_a(m1))
        print("a events", len(ea))
        pa = cl.probe_lookahead(detect_a, ea, lookback="10D")
        ra = cl.trade_test(ea, max_hold=HOLD, hold_basis="bars", claim="+")
        print("a", {k: ra.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties")})
        cl.write_result("smart-money-reversal", "a", ra, operationalization={"rules": [
            "15m CISD (series_open, 2/2, max_wait 3) whose extreme took the prior NY day low/high",
            "inversion: a close through the far side of the last opposing FVG stamped in the 8 bars "
            "up to the extreme, by the CISD bar",
            "short-term low/high: a 1/1 fractal low above (high below) the extreme, confirmed within 8 bars "
            "of the CISD; decide at that bar's close",
            "enter next M1 open, stop at the reversal extreme, 2R, hold 150 min trading time"],
            "params": {**BASE_PARAMS, "htf_level": "prior-day low/high, coverage>=0.5",
                       "fvg_lookback": FVG_LOOKBACK, "stl_wait": STL_WAIT, "stl_fractal": "1/1"}},
            params_source={**BASE_SRC,
                           "htf_level": "corpus: precondition 'price has reached a higher timeframe level' (equal highs/lows example) — prior-day extreme declared-before-run",
                           "fvg_lookback": "declared-before-run: FVG must belong to the leg into the extreme (8 bars = 2h)",
                           "stl_wait": "declared-before-run: short-term low within 2h of the CISD",
                           "stl_fractal": "declared-before-run: 'short-term low' = 1/1 fractal (undefined in corpus)"},
            script=__file__, probe=pa,
            notes="Components reading: change in state of delivery + inversion + short-term low at a HTF level.")
    if "b" in which:
        eb = cl.cache_frame("smr_b_v1", lambda: detect_b(m1))
        print("b events", len(eb), eb.at_htf_array.mean())
        pb = cl.probe_lookahead(detect_b, eb, lookback="100D")
        rb = cl.gate_test(eb, "at_htf_array", mask_available_at="extreme_close", max_hold=HOLD,
                          hold_basis="bars", claim="+")
        print("b", {k: rb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties")})
        cl.write_result("smart-money-reversal", "b", rb, operationalization={"rules": [
            "baseline: 15m bare CISD, stop protected swing, 2R, hold 150 min trading time",
            "gate: the reversal extreme lies inside a same-side DAILY PD array: a daily FVG or daily "
            "order block (body zone of the opposing series behind a daily CISD, series_open 2/2 mw3)",
            "array formed on daily bars closed by the extreme bar's close, <= 60 daily bars old, "
            "no daily close through its far edge since"],
            "params": {**BASE_PARAMS, "htf": "1D", "array_age_days": ARRAY_AGE_D,
                       "arrays": "daily FVG + daily order block (body)", "touch": "extreme inside zone"}},
            params_source={**BASE_SRC,
                           "htf": "corpus: eK_6wgNpNh0 'the smart money reversal is always going to happen on a higher time frame' — daily declared-before-run",
                           "array_age_days": "declared-before-run: arrays from the last ~3 months",
                           "arrays": "corpus: eK_6wgNpNh0 detection 'an order block, a breaker, or an imbalance' (breaker omitted)",
                           "touch": "declared-before-run: the corpus gives no proximity rule"},
            script=__file__, probe=pb,
            notes="Finessee_Fx reading as a gate on bare 15m CISD reversals; breakers not included.")
