"""relevant-level (liquidity, TTrades own voice, contested) — batch liquidity_own_01b.

Claim (_CSO5Mf7CM8, HbOeD_JVens, method spec §2): "no trade in the counter direction until
the relevant level is hit" — a reversal is only worth taking once price has actually
reached a relevant level; without it, expect continuation. So: reversals that turned ON a
relevant level should beat reversals that did not.

Gate test on a stated baseline book: the phase-3 rung-0 1h CISD book (series_open level,
2/2 swings, max_wait 3, stop at the protected swing, 2R target, 10h hold; entry next M1
open after the confirming bar closes). The reversal's extreme is the CISD's protected swing.

 a  relevant = the attested default set (detectors.bias.relevant_level_frame, method spec
    §2.7: "previous day and previous week extremes always qualify"): gate passes when the
    bullish (bearish) extreme traded at or below the previous day's low / previous-5-session
    low (at or above PDH / previous-5-session high), read with prior_hilo at the extreme bar.
    PWL <= PDL, so the union reduces to "extreme took the PDL (PDH)".
 b  relevant = a relevant swing inside the three-HTF-candle window (HbOeD_JVens /
    relevant-swing-lookback: hourly chart -> three days): gate passes when the extreme
    traded beyond a confirmed, still-untaken 1h swing of the same side that formed within
    the current and previous two trading days.

claim '+': gated reversals have higher control-adjusted R than the rest.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

TF = "1h"
CISD = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
RR = 2.0
MAX_HOLD = "10h"
WINDOW_DAYS = 3        # three HTF (daily) candles including the current one


def base(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD)
    return b, ev


def events_frame(b, ev):
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(float), "rr": RR})


def detect_a(m1):
    b, ev = base(m1)
    out = events_frame(b, ev)
    if len(out) == 0:
        out["rl_hit"] = pd.Series(dtype=bool)
        return out
    xt = pd.DatetimeIndex(ev["extreme_time"])
    pdl = cl.prior_hilo(xt, "1D", m1=m1, min_coverage=0.5)
    bull = out["direction"].to_numpy() == 1
    xp = ev["extreme_price"].to_numpy(float)
    ph, pl = pdl["high"].to_numpy(float), pdl["low"].to_numpy(float)
    hit = np.where(bull, xp <= pl, xp >= ph)
    hit = np.where(np.isfinite(ph) & np.isfinite(pl), hit, False)
    out["rl_hit"] = hit.astype(bool)
    keep = np.isfinite(ph) & np.isfinite(pl)             # level must exist (warm-up)
    return out[keep].reset_index(drop=True)


def detect_b(m1):
    b, ev = base(m1)
    out = events_frame(b, ev)
    if len(out) == 0:
        out["rl_hit"] = pd.Series(dtype=bool)
        return out
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    R = CISD["right"]
    sw = __import__("detectors.primitives", fromlist=["swing_points"]).swing_points(b, 2, R)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    td = pd.DatetimeIndex(b["trading_day"]) if "trading_day" in b.columns else cl.trading_day(b.index)
    day_codes = pd.factorize(pd.Series(td.to_numpy()), sort=True)[0]
    pos = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    first_bar_of_day = {}
    for k, dc in enumerate(day_codes):
        first_bar_of_day.setdefault(dc, k)
    hit = np.zeros(len(ev), bool)
    valid = np.zeros(len(ev), bool)
    bull = out["direction"].to_numpy() == 1
    for e, p in enumerate(pos):
        dc = day_codes[p]
        if dc - (WINDOW_DAYS - 1) not in first_bar_of_day:
            continue
        w0 = first_bar_of_day[dc - (WINDOW_DAYS - 1)]
        if w0 < 2:
            continue
        valid[e] = True
        hi_s = p - 1 - R                                # swing must be confirmed before bar p
        if hi_s < w0:
            continue
        if bull[e]:
            cand = np.flatnonzero(sl[w0:hi_s + 1]) + w0
            for s in cand:
                if l[s + 1:p].min() >= l[s] and l[p] < l[s]:   # untaken until p, taken by p
                    hit[e] = True
                    break
        else:
            cand = np.flatnonzero(sh[w0:hi_s + 1]) + w0
            for s in cand:
                if h[s + 1:p].max() <= h[s] and h[p] > h[s]:
                    hit[e] = True
                    break
    out["rl_hit"] = hit
    return out[valid].reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    for reading, det, lb in (("a", detect_a, "20D"), ("b", detect_b, "20D")):
        ev = cl.cache_frame(f"relevant_level_{reading}_{TF}", lambda: det(m1))
        probe = cl.probe_lookahead(det, ev, lookback=lb)
        res = cl.gate_test(ev, "rl_hit", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
        print(reading, "fire", float(ev["rl_hit"].mean()),
              {k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
        base_rules = ["baseline: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open",
                      "stop at the protected swing (the reversal extreme), target 2R, exit after 10h wall clock"]
        if reading == "a":
            gate = ["gate: the extreme traded through the previous trading day's low (bullish) / high (bearish) — "
                    "prior_hilo('1D', min_coverage=0.5) at the extreme bar's start; previous-week (5-session) extremes are nested inside this"]
            params = {"tf": TF, **CISD, "rr": RR, "max_hold": MAX_HOLD, "levels": "PDH/PDL (+ prev-5-session extremes, redundant)",
                      "min_coverage": 0.5}
            src_extra = {"levels": "method_spec: §2.7 relevant-level attested default (detectors.bias.relevant_level_frame, weekly_lookback 5)",
                         "min_coverage": "declared-before-run: skip stub sessions when reading PDH/PDL (README trap 6)"}
        else:
            gate = ["gate: the extreme traded beyond a confirmed 1h swing of the same side (2/2 fractal) that formed in the current or previous two trading days and was untaken until the extreme bar"]
            params = {"tf": TF, **CISD, "rr": RR, "max_hold": MAX_HOLD, "window_days": WINDOW_DAYS, "swing": "2/2 fractal"}
            src_extra = {"window_days": "method_spec: §1.1 relevant-swing look-back = three higher-timeframe candles incl. current (hourly chart -> three days)",
                         "swing": "phase3: 2/2 fractal swings (conjunction_preregistration locked config)"}
        src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
        src.update(src_extra)
        op = {"rules": base_rules + gate + ["claim: gated reversals beat the rest (control-adjusted R)"], "params": params}
        notes = {"a": "Reading a: relevant level = previous-day/previous-week extremes (the attested default). 'Hit' = traded through (touch counted as hit via <=/>=). The V-shape reversal test is carried by the CISD itself.",
                 "b": "Reading b: relevant level = a relevant swing inside the three-daily-candle window (HbOeD_JVens). No separation filter (the corpus gives none mechanically)."}[reading]
        p = cl.write_result("relevant-level", reading, res, operationalization=op, params_source=src,
                            script=__file__, probe=probe, notes=notes)
        print("wrote", p)
