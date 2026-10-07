"""positional-entry-before-open — update u1007 (TTrades, New York Open Live Q&A).

Prior readings a (pre-open 15m positional book, trade_test) and b (pre- vs post-open gate) are
NOT re-tested. Two NEW claims, one reading each, all parameters declared before the first run:

u1007a  (live_09, Hlwq1dRjBZo) rate_test, claim '+'.
  "We have taken out this short-term high ... when we have some protected swings lined up after
   taking out something, a lot of times we go run out that protected swing before we actually
   get the continuation" / "you have no swings you're expecting to hold after we take out a high".
  * 15m bars, phase-3 2/2 fractal swings, everything scoped to the CURRENT trading day (18:00 NY
    roll) = "short-term"; this also bounds the detector's state to one day.
  * decision at 09:30 NY (close of the full 09:15 15m bar).
  * condition (bull case): a 15m bar starting in [08:30, 09:30) traded above an intact (never
    exceeded) same-day 15m swing high confirmed before that bar ("just took out a short-term
    high"), AND at 09:30 at least 2 intact same-day 15m swing lows sit below ("lined up").
    Intact lows are ascending by construction (a later one can never sit below an earlier
    intact one), i.e. they are stacked. Mirror (took a same-day low, >= 2 intact highs above)
    is included: the quote's mechanism is "after taking out something", not long-only.
  * hit: an M1 bar in the first 30 M1 bars from 09:30 trades to the NEAREST stacked swing
    ("run out that protected swing").
  * null: 5 matched moments, +/-30 days, SAME NY minute (09:30; tod tolerance 0, because gold's
    volatility step is at 09:30), same side, distance from the M1 open scaled by the ratio of
    local volatility (mean M1 high-low over the 60 M1 bars before the moment), same 30-bar
    horizon. Lesson 3 of the 09-23 campaign: rate nulls must match time of day and local vol.

u1007b  (live_12, rTomJ8URFnw) gate_test, claim '+'.
  "Entry prior to 9:30. Use M15 or greater ... any time frame works" (read: before 09:30 use
  M15+, after 09:30 any timeframe). The directional half is tested: among PRE-OPEN entries
  (decided 07:00-09:30 NY), 15m setups beat sub-15m setups. Book = phase-3 bare CISD on 15m
  (gated) and 5m (complement), stop = protected swing, 2R, 10 entry-TF bars hold (150 / 50 min).
  Control-adjusted (each trade minus its own matched control), controls held to +/-30 min of
  the NY clock. "After 09:30 any timeframe works" is a no-difference statement and is not a
  testable direction; it is not scored.

Vault rerun (2026-10-07, KronosVault 'Backtest Methodology Traps' + 'Concept Campaign 2026-09-23'):
  both readings re-checked trap by trap and kept UNCHANGED (same frames, same settings -> same
  hyp_key; the script refuses to overwrite a written reading whose hyp_key differs).
  1 geometry: null keeps side, horizon and vol-scaled distance  2 M1 resolution, stop-first ties
  3/9 decide at the 15m bar close, no HTF bar read  4 +/-30d regime controls  6 MDE reported
  7 firing rate printed  8 2016+ certified span, no point thresholds  campaign lesson 3: rate
  null holds the NY minute (09:30) and local vol. Added: trap 5 = headline recomputed from raw
  M1 outside the harness (raw_check_a / raw_check_b); lesson 2 = per-arm stop size in points and
  what a 0.30 pt spread costs in R, since the control-adjusted differential cancels cost.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "entry_own_03a"))
import numpy as np                                   # noqa: E402
import pandas as pd                                  # noqa: E402

import concept_lab as cl                             # noqa: E402
from _common import cisd_book, run_and_print, CISD_KW  # noqa: E402
from detectors.primitives import swing_points       # noqa: E402

CID = "positional-entry-before-open"
OHLC = ["open", "high", "low", "close"]

# ---- reading u1007a
TF = "15min"
DEC_MOD = 9 * 60 + 15            # start of the 15m bar that closes at 09:30 NY
SWEEP_LO, SWEEP_HI = 8 * 60 + 30, 9 * 60 + 30
MIN_STACK = 2
HBARS = 30
VOL_BARS = 60
A_COLS = ["decision_time", "available_at", "direction", "level", "n_stack", "take_time"]

# ---- reading u1007b
B_WIN = ("07:00", "09:30")
HOLD = {"15min": pd.Timedelta("150min"), "5min": pd.Timedelta("50min")}


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 20:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in A_COLS})
    sw = swing_points(b[OHLC], left=2, right=2)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    st = pd.DatetimeIndex(b.index)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    ny = cl.to_ny(st)
    mod = (ny.hour * 60 + ny.minute).to_numpy()
    day = cl.trading_day(st).to_numpy()
    full = (ct - st.tz_convert("UTC")) == pd.Timedelta(TF)
    rows = []
    hs, ls = [], []                  # intact same-day swings: (level, pos); hs descending, ls ascending
    took_hi = took_lo = None         # start pos of the last bar that took a same-day swing
    for i in range(len(b)):
        if i == 0 or day[i] != day[i - 1]:
            hs, ls, took_hi, took_lo = [], [], None, None
        p = i - 3                    # swing at p confirmed at close of p+2 = i-1
        if p >= 0 and day[p] == day[i]:
            if is_sh[p]:
                hs.append((h[p], p))
            if is_sl[p]:
                ls.append((l[p], p))
        while hs and h[i] > hs[-1][0]:
            hs.pop()
            took_hi = i
        while ls and l[i] < ls[-1][0]:
            ls.pop()
            took_lo = i
        if mod[i] != DEC_MOD or not full[i]:
            continue
        p2 = i - 2                   # confirmed exactly at this bar's close: known at 09:30
        hs2 = hs + ([(h[p2], p2)] if p2 >= 0 and day[p2] == day[i] and is_sh[p2] else [])
        ls2 = ls + ([(l[p2], p2)] if p2 >= 0 and day[p2] == day[i] and is_sl[p2] else [])
        for d, took, stack in ((1, took_hi, ls2), (-1, took_lo, hs2)):
            if took is None or not (SWEEP_LO <= mod[took] < SWEEP_HI):
                continue
            if len(stack) < MIN_STACK:
                continue
            lvl = max(x[0] for x in stack) if d == 1 else min(x[0] for x in stack)
            rows.append((ct[i], ct[i], d, lvl, len(stack), ct[took]))
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in A_COLS})
    out = pd.DataFrame(rows, columns=A_COLS)
    for c in ("decision_time", "available_at", "take_time"):
        out[c] = pd.DatetimeIndex(out[c]).tz_convert("UTC")
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for tf, is15 in (("15min", True), ("5min", False)):
        e = cisd_book(m1, tf)
        e = e[cl.in_window(pd.DatetimeIndex(e["decision_time"]), *B_WIN)].copy()
        e["tf15"] = is15
        e["max_hold"] = HOLD[tf]
        parts.append(e)
    ev = pd.concat(parts, ignore_index=True)
    ev["tf15"] = ev["tf15"].astype(bool)
    ev["direction"] = ev["direction"].astype(int)
    return ev.sort_values(["decision_time", "direction", "tf15"], kind="stable").reset_index(drop=True)


SRC_A = {
    "tf": "corpus: rTomJ8URFnw 'Entry prior to 9:30. Use M15 or greater' (pre-open chart TF); "
          "U4j-fZD-FJk 'Really only if uh it's a 15-minute valid setup'",
    "swing": "phase3: locked 2/2 fractal (conjunction_preregistration 1.8)",
    "decision": "corpus: Hlwq1dRjBZo 'This isn't an open where I would try to trade through the open' "
                "(09:30 equity open; same stream '9:30 open in volatility')",
    "sweep_window": "declared-before-run: 'just' taken = by a 15m bar starting in the hour before the open "
                    "[08:30, 09:30); Hlwq1dRjBZo 'We have taken out this short-term high' said at the open",
    "short_term_scope": "declared-before-run: 'short-term' swings = 15m swings formed in the current trading "
                        "day (18:00 NY roll, session_window_fit)",
    "min_stack": "corpus: Hlwq1dRjBZo 'protected swings lined up' (plural; no count given, draft ambiguity) "
                 "-> declared-before-run minimum 2",
    "target_swing": "corpus: Hlwq1dRjBZo 'we go run out that protected swing before we actually get the "
                    "continuation' -> the nearest stacked swing",
    "horizon_bars": "corpus draft measurable (update_20261007_live_09): 'run within the first 30 minutes after "
                    "9:30'; Hlwq1dRjBZo 'better off waiting for 10 a.m.'",
    "mirror": "corpus: Hlwq1dRjBZo 'after taking out something' (mechanism stated generally) -> "
              "declared-before-run: bear mirror included",
    "null": "declared-before-run: 5 moments +/-30d (phase3 locked), same NY minute 09:30 (tod_tol 0; 09:30 is "
            "gold's volatility step, session-open-volume-nyse), same side, distance x local-vol ratio "
            "(concept campaign 2026-09-23 lesson 3: rate nulls must match time of day and local volatility)",
    "vol_bars": "declared-before-run: local volatility = mean M1 high-low over the 60 M1 bars before the moment",
}

SRC_B = {
    "tf_gated": "corpus: rTomJ8URFnw 'Entry prior to 9:30. Use M15 or greater'",
    "tf_complement": "declared-before-run: sub-M15 arm = 5m, the finest phase-3 locked stack "
                     "(time_own_01a baseline book)",
    "window": "session_window_fit: forex NY AM killzone start 07:00 (killzones.yaml) to the 09:30 open, "
              "as prior readings a/b; corpus rTomJ8URFnw 'Entry prior to 9:30'",
    "cisd": "phase3: locked CISD config (conjunction_preregistration 1.8-1.13: series_open, 2/2, max_wait 3)",
    "rr": "phase3: 2R target (conjunction_preregistration locked config)",
    "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 150 min on 15m, 50 min on 5m",
    "ctrl_tod_tol_min": "declared-before-run: controls held within +/-30 min of the NY clock so both arms are "
                        "judged against the same pre-open hours (trap 9)",
}


RES_DIR = Path(__file__).resolve().parents[2] / "results"
SPREAD_PT = 0.30          # vault lesson 2 (0.25-0.35 pt); descriptive only, not a scored knob


def guard_same_hyp(reading: str, res: dict) -> None:
    """A rerun may rewrite its own reading only if the hypothesis is identical."""
    f = RES_DIR / f"{CID}__{reading}.json"
    if f.exists():
        import json
        old = json.loads(f.read_text()).get("hyp_key")
        if old != res["hyp_key"]:
            raise SystemExit(f"{f.name}: hyp_key {old} != {res['hyp_key']}; use a new reading label")


def raw_check_a(ev: pd.DataFrame) -> float:
    """Trap 5: observed hit rate from raw M1 arrays, no cl.touch / get_market."""
    m1 = cl.load_m1()
    tn = m1.index.as_unit("ns").asi8
    lo, hi, op = (m1[c].to_numpy() for c in ("low", "high", "open"))
    hits = []
    for t, d, lvl in zip(pd.DatetimeIndex(ev["decision_time"]).as_unit("ns").asi8,
                         ev["direction"].to_numpy(), ev["level"].to_numpy(float)):
        i = int(np.searchsorted(tn, t, "left"))
        if i >= len(tn) or d * (op[i] - lvl) <= 0:
            continue                                     # same drop rule as run_a
        hits.append(lo[i:i + HBARS].min() <= lvl if d == 1 else hi[i:i + HBARS].max() >= lvl)
    return float(np.mean(hits))


def raw_check_b(ev: pd.DataFrame) -> dict:
    """Trap 5 + lesson 2: per-arm gross R of the real trades from a plain M1 loop, and the
    stop size in points (what a SPREAD_PT spread costs in R)."""
    m1 = cl.load_m1()
    tn = m1.index.as_unit("ns").asi8
    o, h, l, c = (m1[k].to_numpy() for k in ("open", "high", "low", "close"))
    out = {}
    for arm, sub in (("15m", ev[ev["tf15"]]), ("5m", ev[~ev["tf15"]])):
        rs, risk = [], []
        for t, d, sp, mh in zip(pd.DatetimeIndex(sub["decision_time"]).as_unit("ns").asi8,
                                sub["direction"].to_numpy(), sub["stop_px"].to_numpy(float),
                                pd.to_timedelta(sub["max_hold"]).to_numpy().astype("timedelta64[ns]")
                                .astype("int64")):
            i0 = int(np.searchsorted(tn, t, "left"))
            i1 = int(np.searchsorted(tn, t + mh, "left"))
            if i0 >= len(tn) or i1 <= i0:
                continue
            e = o[i0]
            r = d * (e - sp)
            if r <= 0:
                continue
            tg = e + d * 2.0 * r
            px = c[i1 - 1]
            for j in range(i0, i1):
                stop_hit = l[j] <= sp if d == 1 else h[j] >= sp
                if stop_hit:                              # stop first on a tie; gap fills at open
                    px = min(o[j], sp) if d == 1 else max(o[j], sp)
                    break
                if (h[j] >= tg) if d == 1 else (l[j] <= tg):
                    px = tg
                    break
            rs.append(d * (px - e) / r)
            risk.append(r)
        risk = np.asarray(risk)
        out[arm] = {"n": len(rs), "avg_R_gross_raw": round(float(np.mean(rs)), 4),
                    "median_stop_pt": round(float(np.median(risk)), 3),
                    "spread_cost_R_median": round(float(np.median(SPREAD_PT / risk)), 3)}
    return out


def run_a():
    ev = cl.cache_frame("u1007_peo_a_stack15", lambda: detect_a(cl.load_m1()))
    print("u1007a events", len(ev), ev["direction"].value_counts().to_dict(),
          "n_stack median", ev["n_stack"].median())
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    d = ev["direction"].to_numpy()
    rng_hl = mkt.h - mkt.l
    csum = np.concatenate([[0.0], np.cumsum(rng_hl)])

    def vol(i0):
        lo = np.maximum(i0 - VOL_BARS, 0)
        return (csum[i0] - csum[lo]) / np.maximum(i0 - lo, 1)

    i0 = mkt.pos_at_or_after(t)
    p0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = d * (p0 - ev["level"].to_numpy())           # > 0: level on the far side of the open
    v0 = vol(i0)
    ok = (dist > 0) & (v0 > 0)
    print("dropped (open already through level / no vol)", int((~ok).sum()))

    def outcome(times, px, dd, dist_, sel):
        res = np.full(len(sel), np.nan)
        idx = np.flatnonzero(sel)
        for s, side in ((1, "below"), (-1, "above")):
            m = idx[dd[idx] == s]
            if len(m):
                res[m] = cl.touch(times[m], px[m] - s * dist_[m], side,
                                  horizon_bars=HBARS)["hit"].to_numpy()
        return res

    obs = outcome(t, p0, d, dist, ok)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=0)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        good = ok & ~tk.isna()
        ik = np.zeros(len(t), np.int64)
        ik[good] = mkt.pos_at_or_after(tk[good])
        good &= ik < len(mkt.o)
        pk = np.where(good, mkt.o[np.minimum(ik, len(mkt.o) - 1)], np.nan)
        vk = np.where(good, vol(np.minimum(ik, len(mkt.o) - 1)), np.nan)
        good &= vk > 0
        dk = np.where(good, dist * vk / np.where(v0 > 0, v0, np.nan), np.nan)
        return outcome(tk, pk, d, dk, good)        # only `good` rows are touched

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       predictors=ev)
    run_and_print(res)
    guard_same_hyp("u1007a", res)
    raw = raw_check_a(ev)
    n_days = int(pd.Index(cl.trading_day(cl.load_m1().index)).nunique())
    fire = round(pd.Index(cl.trading_day(pd.DatetimeIndex(ev["decision_time"]))).nunique() / n_days, 3)
    print("raw recompute observed rate", raw, "harness", res["observed_rate"], "| days firing", fire)
    assert abs(raw - res["observed_rate"]) < 1e-9, "trap 5: raw recompute disagrees with harness"
    rules = [
        "15m bars, 2/2 fractal swings; only swings formed in the current trading day (18:00 NY roll) count",
        "decision 09:30 NY = close of the full 09:15 15m bar",
        "bull case: a 15m bar starting in [08:30, 09:30) traded above an intact same-day swing high "
        "confirmed before it, and >= 2 intact same-day 15m swing lows (never traded below) exist at 09:30; "
        "bear case mirrored",
        "hit: any of the first 30 M1 bars from 09:30 trades to the nearest stacked swing (low <= level / high >= level)",
        "null: 5 moments +/-30d at the same NY minute (09:30), same side, distance from the M1 open scaled by "
        "local vol ratio (mean M1 range, 60 bars before), same 30-bar horizon",
    ]
    params = {"tf": TF, "swing": "2/2", "decision": "09:30 NY", "sweep_window": "08:30-09:30",
              "short_term_scope": "current trading day", "min_stack": MIN_STACK,
              "target_swing": "nearest", "horizon_bars": HBARS, "mirror": True,
              "null": "tod 0, +/-30d, vol-scaled distance", "vol_bars": VOL_BARS}
    p = cl.write_result(CID, "u1007a", res, operationalization={"rules": rules, "params": params},
                        params_source=SRC_A, script=__file__, probe=probe,
                        notes="Tests only the live_09 negative case: after a pre-open take of a short-term "
                              "extreme with protected swings stacked behind, the nearest one is run in the "
                              "first 30 min more than a vol- and clock-matched equidistant level. Indices' "
                              "09:30 open applied to gold as a clock time; the source stream was trading NQ "
                              "(vault: gold's volatility step is at 09:30, not 08:30). Vault rerun: trap 5 raw "
                              f"recompute of the observed rate = {raw:.4f} (matches harness); share of trading "
                              f"days with an event = {fire}. A NULL here does not separate 'after a pre-open "
                              "take' from 'stacked swings' (no structural split was pre-declared).")
    print(p)


def run_b():
    ev = cl.cache_frame("u1007_peo_b_tf15v5", lambda: detect_b(cl.load_m1()))
    print("u1007b events", len(ev), "15m share", round(float(ev["tf15"].mean()), 3))
    probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "tf15", mask_available_at="decision_time", max_hold=None,
                       ctrl_tod_tol_min=30)
    run_and_print(res)
    guard_same_hyp("u1007b", res)
    raw = raw_check_b(ev)
    print("raw recompute", raw, "| harness gross gated", res["avg_R_gross"],
          "complement net", res["complement"]["avg_R"])
    rules = [
        "pre-open book: phase-3 bare CISD (series_open, 2/2, max_wait 3) on 15m and on 5m, decided in "
        "[07:00, 09:30) NY; enter next M1 open; stop = protected swing; 2R; hold 10 entry-TF bars",
        "gate: setup timeframe is 15m (gated) vs 5m (complement)",
        "control-adjusted: each trade minus its own matched control (+/-30d, +/-30 min NY clock)",
    ]
    params = {"tf_gated": "15min", "tf_complement": "5min", "window": "07:00-09:30",
              "cisd": CISD_KW, "rr": 2.0, "max_hold": "150min (15m) / 50min (5m)",
              "ctrl_tod_tol_min": 30}
    p = cl.write_result(CID, "u1007b", res, operationalization={"rules": rules, "params": params},
                        params_source=SRC_B, script=__file__, probe=probe,
                        notes="Tests only the live_12 timeframe floor (directional half). The caption split "
                              "('before 09:30 use M15+, after 09:30 any TF') is the draft's inference. The "
                              "differential is control-adjusted, so spread costs that hit 5m stops harder "
                              "cancel within each arm. Vault rerun (trap 5 / campaign lesson 2): raw M1 "
                              f"recompute of the real arms {raw}; 'spread_cost_R_median' is what a "
                              f"{SPREAD_PT} pt spread costs per trade, which the differential does not see.")
    print(p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
