"""consolidation-vs-retracement-test (TTrades own voice, contested) -> two readings.

The test: a counter-move is a RETRACEMENT only if price closes through the series of
opposing candles that made its extreme (a protected swing / CISD forms); if the closure
does not arrive it is a CONSOLIDATION. Two decidable consequences are stated:
  * 'after a failure to close below the level, the high is usually taken out' -- a failed
    closure predicts a sweep of the opposite side (Nlw-PZhoViQ, chart_lessons_01);
  * timing signature: 'If it consolidates for half of the candle and then closes over'
    (vn1RYjhJUnQ) -- a close-through that takes longer than ~half the candle is
    'usually just a consolidation', not a confirmed swing (threshold_fits §4, grade B).

Declared before the first run:
  reading a -- rate_test, claim '+'. On 1h bars (htf list), every confirmed fractal 2/2
    swing extreme with its opposing-candle series (detectors.cisd series logic). The
    closure level = open of the first candle of the series (locked phase-3 series_open);
    the closure must arrive within 3 bars after the run ends / swing is confirmable
    (locked max_wait 3). FAILURE = no such close in those 3 bars, and the extreme has not
    been traded through meanwhile -> consolidation. Decide at the close of the 3rd bar.
    Range = [lowest low from the series start to the decision, the swing high] (mirrored
    for a swing low). Prediction: the swing extreme (the 'high' of the text) is taken
    BEFORE the far side of the range. Outcome on M1 within 6900 bars (5 sessions); an M1 bar
    touching both, or neither touched -> NaN. Null: 5 random moments within +/-30 days
    (sample_times, locked seed), same up/down distances from the first M1 open after the
    decision, same horizon -> share where the predicted side is hit first.
  reading b -- gate_test, claim '+'. Baseline = locked phase-3 1h CISD book (2R, 10h).
    Gate 'timely closure' = inside the confirming 1h candle, the first M1 close beyond the
    CISD level occurs within the first half of the candle (elapsed <= 30 of 60 minutes,
    counted from the candle open). Known at the confirming close = decision.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, cisd_1h, show
from detectors.primitives import swing_points
from detectors.cisd import _run_into_extreme

CID = "consolidation-vs-retracement-test"
MAX_WAIT = 3
HORIZON = 6900
COLS_A = ["decision_time", "available_at", "side", "lvl_pred", "lvl_other"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr", "timely"]
def utc_ns(x):
    return np.asarray(cl.data.utc_ns(x)).astype("datetime64[ns]").astype(np.int64)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, "1h")
    if len(b) < 10:
        return pd.DataFrame(columns=COLS_A)
    o = b[["open", "high", "low", "close"]]
    sw = swing_points(o, left=2, right=2)
    H, L, C, O = (o[c].to_numpy(float) for c in ("high", "low", "close", "open"))
    ct = utc_ns(pd.DatetimeIndex(b["close_time"]))
    n = len(b)
    rows = []
    for bullish, col in ((True, "swing_low"), (False, "swing_high")):
        for p in np.flatnonzero(sw[col].to_numpy()):
            st, en = _run_into_extreme(o, int(p), bullish, max_len=10)
            if st < 0:
                continue
            lvl = O[st]
            begin = max(en, p + 2) + 1
            last = begin + MAX_WAIT - 1
            if last >= n:
                continue
            seg = slice(begin, last + 1)
            if bullish:
                if (C[seg] > lvl).any():               # closure arrived: retracement
                    continue
                if (L[p + 1:last + 1] < L[p]).any():   # extreme already taken
                    continue
                far = H[st:last + 1].max()
                rows.append((ct[last], -1, L[p], far))  # predicted: the low is taken
            else:
                if (C[seg] < lvl).any():
                    continue
                if (H[p + 1:last + 1] > H[p]).any():
                    continue
                far = L[st:last + 1].min()
                rows.append((ct[last], 1, H[p], far))   # predicted: the high is taken
    if not rows:
        return pd.DataFrame(columns=COLS_A)
    ev = pd.DataFrame(rows, columns=["t", "side", "lvl_pred", "lvl_other"])
    ev["decision_time"] = pd.to_datetime(ev["t"], utc=True)
    ev["available_at"] = ev["decision_time"]
    ev = ev.drop_duplicates(["decision_time", "side", "lvl_pred", "lvl_other"])
    ev = ev.sort_values(["decision_time", "side", "lvl_pred"]).reset_index(drop=True)
    return ev[COLS_A]


def first_side(times, up_lvl, dn_lvl, pred_side):
    """1 if the predicted side is touched first, 0 if the other, NaN if tie/none."""
    tu = cl.touch(times, up_lvl, "above", horizon_bars=HORIZON)
    td = cl.touch(times, dn_lvl, "below", horizon_bars=HORIZON)
    hu, hd = tu["hit"].to_numpy(), td["hit"].to_numpy()
    xu = utc_ns(pd.DatetimeIndex(tu["hit_time"]))
    xd = utc_ns(pd.DatetimeIndex(td["hit_time"]))
    big = np.iinfo(np.int64).max
    xu = np.where(hu, xu, big)
    xd = np.where(hd, xd, big)
    up_first = np.where(xu < xd, 1.0, np.where(xd < xu, 0.0, np.nan))
    up_first[~hu & ~hd] = np.nan
    return np.where(pred_side > 0, up_first, 1.0 - up_first)


def run_a():
    ev = cl.cache_frame("cvr_a_1h_fail_mw3", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    side = ev["side"].to_numpy()
    up_lvl = np.where(side > 0, ev["lvl_pred"], ev["lvl_other"]).astype(float)
    dn_lvl = np.where(side > 0, ev["lvl_other"], ev["lvl_pred"]).astype(float)
    i0 = np.clip(mkt.pos_at_or_after(t), 0, len(mkt.o) - 1)
    px0 = mkt.o[i0]
    du, dd = up_lvl - px0, px0 - dn_lvl
    obs = first_side(t, up_lvl, dn_lvl, side)
    bad = ~((du > 0) & (dd > 0))
    obs[bad] = np.nan
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]) if rt[:, k].dtype.kind == "M" else pd.DatetimeIndex(rt[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        okk = ~np.isnat(rt[:, k])
        out = np.full(len(t), np.nan)
        if okk.any():
            tt = tk[okk]
            j = np.clip(mkt.pos_at_or_after(tt), 0, len(mkt.o) - 1)
            p = mkt.o[j]
            r = first_side(tt, p + du[okk], p - dd[okk], side[okk])
            out[okk] = r
        out[bad] = np.nan
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn, claim="+",
                       predictors=ev, outcome_horizon="5D")
    show(res)
    op = {"rules": [
        "1h bars; every confirmed 2/2 swing extreme with its opposing-candle series (detectors.cisd run logic)",
        "closure level = open of the series' first candle; FAILURE = no close through it within 3 bars after "
        "the run ends / swing is confirmable, and the extreme not yet traded through -> consolidation; decide at the 3rd bar's close",
        "range = [swing extreme, far extreme of the series-start..decision bars]",
        "prediction: the swing extreme is taken before the far side (M1, 6900-bar horizon; ties/none -> NaN)",
        "null: 5 matched random moments (+/-30 days), same up/down distances from the first M1 open, same horizon"],
        "params": {"tf": "1h", "swing": "2/2", "level_rule": "series_open", "max_wait": MAX_WAIT,
                   "horizon_m1_bars": HORIZON, "null": "sample_times reps 5 window 30d"}}
    src = {"tf": "corpus: Nlw-PZhoViQ chart lesson worked on the hourly; concept htf 1D/4H/1H",
           "swing": "phase3: §1.8 locked swing 2/2",
           "level_rule": "phase3: §1.8 locked series_open (close through the series of opposing candles)",
           "max_wait": "phase3: §1.8 locked max_wait 3 ('1, 2, maybe three' candles)",
           "horizon_m1_bars": "declared-before-run: five trading sessions",
           "null": "declared-before-run: locked harness reps/window/seed, geometry-matched distances"}
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading a: 'failure to close => the opposite side (the swing extreme) is "
                                "usually taken out'. Precondition 'an expansion leg has completed' not "
                                "modelled: every 1h swing with an opposing series is classified."))


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b, ev = cisd_1h(m1)
    if ev.empty:
        return pd.DataFrame(columns=COLS_B)
    mt = utc_ns(pd.DatetimeIndex(m1.index))
    mc = m1["close"].to_numpy(float)
    st = utc_ns(pd.DatetimeIndex(ev["confirm_time"]))
    en = utc_ns(pd.DatetimeIndex(ev["decision_time"]))
    lvl = ev["level"].to_numpy(float)
    bull = ev["direction"].to_numpy() == "bullish"
    share = np.full(len(ev), np.nan)
    for i in range(len(ev)):
        a = np.searchsorted(mt, st[i], side="left")
        z = np.searchsorted(mt, en[i], side="left")
        cc = mc[a:z]
        hit = np.flatnonzero(cc > lvl[i]) if bull[i] else np.flatnonzero(cc < lvl[i])
        if len(hit):
            share[i] = (mt[a + hit[0]] + 60_000_000_000 - st[i]) / (en[i] - st[i])
    keep = np.isfinite(share)
    ev = ev[keep].reset_index(drop=True)
    out = pd.DataFrame({
        "decision_time": pd.DatetimeIndex(ev["decision_time"]),
        "available_at": pd.DatetimeIndex(ev["decision_time"]),
        "direction": np.where(ev["direction"].to_numpy() == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float),
        "rr": 2.0,
        "timely": share[keep] <= 0.5,
    })
    return out[COLS_B]


def run_b():
    ev = cl.cache_frame("cvr_b_cisd1h_halfcandle", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), "timely", int(ev["timely"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "timely", mask_available_at="decision_time", claim="+",
                       max_hold="10h")
    show(res)
    op = {"rules": [
        "baseline: locked phase-3 1h CISD (swing 2/2, series_open, max_wait 3; decide at the confirming close; "
        "stop = protected swing; 2R; 10h)",
        "gate 'timely closure': the first M1 close beyond the CISD level inside the confirming 1h candle "
        "occurs within the first half of the candle (<= 30 of 60 minutes from the candle open)",
        "claim '+': timely closures (retracement/swing confirmed) beat closures after half the candle ('usually just a consolidation')"],
        "params": {"tf": "1h", "cisd": "series_open/max_wait 3/swing 2-2", "rr": 2.0,
                   "max_hold": "10h", "half_candle": 0.5, "count_from": "candle open"}}
    src = {"tf": "phase3: §1.8 locked 1h CISD", "cisd": "phase3: §1.8 locked config",
           "rr": "phase3: §1.8 2R", "max_hold": "phase3: §1.13 10 entry-TF bars",
           "half_candle": "threshold_fits: §4 'If it consolidates for half of the candle and then closes over' (vn1RYjhJUnQ), time rider 0.5, grade B",
           "count_from": "declared-before-run: ambiguity (open vs sweep) resolved to the candle open"}
    print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading b: the half-candle timing signature as a gate on the phase-3 1h CISD book."))


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        {"a": run_a, "b": run_b}[r]()
