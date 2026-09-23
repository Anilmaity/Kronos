"""broadening-formation (TTrades, dSccSI7uqvE / Tjk9bXERZy0 / RhvalhK2Ulc) — rate_test, 2 readings.

Directional claim common to both framings: "since we failed this side of the range we
expect to see the other side" — once one side of the range is taken and price fails
(closes back inside), price rotates to the OTHER side. '+' = the opposite side is reached
more often than a level at the same distance, over the same number of trading minutes,
from a matched random moment.

Operationalisation (declared before the first run):
  reading a (later framing: the HTF outside bar / prior-day range, Tjk9bXERZy0,
    RhvalhK2Ulc "a daily candle that takes both PDH and PDL IS a broadening formation"):
    range = the prior trading day's high/low (18:00 NY roll, min_coverage 0.5). Event =
    the close of the first 1H bar of the day that CLOSES back inside after the day's
    running high has traded above PDH (mirror: PDL), while the other side has not been
    taken yet; decisions before 16:00 NY only. Hit = the other side traded before the
    17:00 NY halt that ends the trading day.
  reading b (earlier framing, dSccSI7uqvE "one high taking out another high", range-bound):
    range = the latest confirmed 1H 2/2 swing high and swing low, both still untaken, with
    price between them. A 1H bar trades above the swing high; if a 1H close back below it
    comes within 3 bars (that bar included) the side has failed -> event at that close;
    otherwise it is a breakout and nothing is emitted. Mirror for lows. Hit = the opposite
    swing traded within 1,440 M1 bars (one trading day).
  null (both): at 5 matched random M1 moments (+/-30 days, same NY time of day +/-30 min),
    a level at the same distance from the next M1 open, same side, same M1-bar horizon.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

FAIL_BARS, HORIZON_B = 3, 1440
TOD_TOL = 30


def detect_a(m1):
    b = cl.build_bars(m1, "1h")
    ct = pd.DatetimeIndex(b["close_time"])
    td = cl.trading_day(b.index)
    pd_ = cl.prior_hilo(ct, "1D", m1=m1, min_coverage=0.5)
    H, L, Cl = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    before16 = cl.in_window(ct, "18:01", "16:01")   # decision at or before 16:00 NY
    rows = []
    tdv = td.to_numpy()
    starts = np.flatnonzero(np.r_[True, tdv[1:] != tdv[:-1]])
    ends = np.r_[starts[1:], len(b)]
    for s, e in zip(starts, ends):
        if np.isnan(pdh[s]) or np.isnan(pdl[s]):
            continue
        # the prior day must be the same for every bar of this day (it is: closed before s)
        hi, lo_ = pdh[s], pdl[s]
        run_h = np.maximum.accumulate(H[s:e])
        run_l = np.minimum.accumulate(L[s:e])
        for side in (1, -1):             # 1: high side taken and failed -> target low
            for k in range(e - s):
                i = s + k
                if side == 1:
                    taken, other = run_h[k] > hi, run_l[k] < lo_
                    back = Cl[i] < hi
                else:
                    taken, other = run_l[k] < lo_, run_h[k] > hi
                    back = Cl[i] > lo_
                if other:
                    break
                if taken and back:
                    if before16[i]:
                        rows.append({"decision_time": ct[i], "available_at": ct[i],
                                     "failed_side": side, "target": lo_ if side == 1 else hi,
                                     "close": Cl[i]})
                    break
    cols = ["decision_time", "available_at", "failed_side", "target", "close"]
    return (pd.DataFrame(rows, columns=cols).sort_values("decision_time")
            .reset_index(drop=True))


def detect_b(m1):
    b = cl.build_bars(m1, "1h")
    ct = pd.DatetimeIndex(b["close_time"])
    sw = swing_points(b[["high", "low"]], 2, 2)
    H, L, Cl = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ish, isl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    n = len(b)
    rows = []
    sh = sl = np.nan                         # latest confirmed, untaken swing levels
    pend = {1: None, -1: None}               # (sweep bar, level, opposite level)
    for j in range(n):
        i = j - 3                            # swing at i usable from bar i+3
        if i >= 0 and ish[i]:
            sh = H[i]
        if i >= 0 and isl[i]:
            sl = L[i]
        # pending failures first
        for side in (1, -1):
            p = pend[side]
            if p is None:
                continue
            s0, lvl, opp = p
            if j - s0 >= FAIL_BARS:
                pend[side] = None
                continue
            if (side == 1 and Cl[j] < lvl) or (side == -1 and Cl[j] > lvl):
                if (side == 1 and Cl[j] > opp) or (side == -1 and Cl[j] < opp):
                    rows.append({"decision_time": ct[j], "available_at": ct[j],
                                 "failed_side": side, "target": opp, "close": Cl[j]})
                pend[side] = None
        # new sweeps of a range-bound pair
        if not (np.isnan(sh) or np.isnan(sl)) and sl < sh:
            if H[j] > sh and pend[1] is None and L[j] >= sl:
                if Cl[j] < sh and Cl[j] > sl:
                    rows.append({"decision_time": ct[j], "available_at": ct[j],
                                 "failed_side": 1, "target": sl, "close": Cl[j]})
                elif Cl[j] >= sh:
                    pend[1] = (j, sh, sl)
                sh = np.nan
            elif L[j] < sl and pend[-1] is None and H[j] <= sh:
                if Cl[j] > sl and Cl[j] < sh:
                    rows.append({"decision_time": ct[j], "available_at": ct[j],
                                 "failed_side": -1, "target": sh, "close": Cl[j]})
                elif Cl[j] <= sl:
                    pend[-1] = (j, sl, sh)
                sl = np.nan
        if not np.isnan(sh) and H[j] > sh:
            sh = np.nan
        if not np.isnan(sl) and L[j] < sl:
            sl = np.nan
    cols = ["decision_time", "available_at", "failed_side", "target", "close"]
    out = pd.DataFrame(rows, columns=cols)
    return (out.drop_duplicates(subset=["decision_time", "failed_side"])
            .sort_values("decision_time").reset_index(drop=True))


def day_end_bars(t: pd.DatetimeIndex, mkt) -> np.ndarray:
    ny = cl.to_ny(t)
    end_local = ny.normalize() + pd.Timedelta(hours=17)
    end_local = end_local.where(ny.hour < 17, end_local + pd.Timedelta(days=1))
    end = end_local.tz_convert("UTC")
    return mkt.pos_at_or_after(end) - mkt.pos_at_or_after(t)


def run_rate(ev: pd.DataFrame, nb: np.ndarray, outcome_horizon: str):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    tgt = ev["target"].to_numpy(float)
    below = ev["failed_side"].to_numpy() == 1          # high side failed -> low target
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = tgt - first_px                              # negative when the target is below

    def hits(times, lv, nbars):
        out = np.zeros(len(times), bool)
        for side, m in (("below", below), ("above", ~below)):
            if m.any():
                out[m] = cl.touch(times[m], lv[m], side, horizon_bars=nbars[m])["hit"].to_numpy()
        return out

    obs = hits(t, tgt, nb).astype(float)
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS,
                         seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        idx = np.flatnonzero(ok)
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        lv = px + dist[ok]
        o2 = np.zeros(len(idx), bool)
        bl = below[ok]
        for side, m in (("below", bl), ("above", ~bl)):
            if m.any():
                o2[m] = cl.touch(tk[ok][m], lv[m], side, horizon_bars=nb[ok][m])["hit"].to_numpy()
        out[idx] = o2
        return out

    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null_fn=null_fn, predictors=ev, outcome_horizon=outcome_horizon)


PSRC = {"null_tod_tol_min": "declared-before-run: hold NY time of day (+/-30 min) fixed in the null (trap 9)",
        "null_reps": "phase3: locked reps=5, +/-30-day window"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    mkt = cl.get_market()
    if "a" in which:
        ev = cl.cache_frame("broadening_a_pdr_1h", lambda: detect_a(cl.load_m1()))
        print("a", len(ev), ev.failed_side.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        print("probe", probe.get("passed"))
        nb = day_end_bars(pd.DatetimeIndex(ev["decision_time"]), mkt)
        res = run_rate(ev, nb, "1D")
        C.show(res)
        p = cl.write_result(
            "broadening-formation", "a", res,
            operationalization={"rules": [
                "range = prior trading day high/low (18:00 NY roll; periods with coverage < 0.5 skipped)",
                "event = close of the first 1H bar that closes back inside the prior-day range after the day's running high (low) traded beyond PDH (PDL), the other side untaken; decision before 16:00 NY",
                "hit = the other side of the prior-day range traded before the 17:00 NY halt (M1-bar horizon)",
                "null = same distance from the next M1 open, same side, same M1-bar horizon, 5 matched random moments (+/-30d, NY time +/-30min)"],
                "params": {"range": "prior day", "fail_tf": "1h", "min_coverage": 0.5,
                           "latest_decision": "16:00 NY", "horizon": "to 17:00 NY halt",
                           "null_tod_tol_min": TOD_TOL, "null_reps": 5}},
            params_source={
                "range": "corpus: RhvalhK2Ulc 'since it took both the range high and the range low' (daily outside bar = formation)",
                "fail_tf": "corpus: concept timeframes htf 1D/1H; failure = a 1H close back inside (declared-before-run)",
                "min_coverage": "declared-before-run: skip stub sessions (trap 6)",
                "latest_decision": "declared-before-run: leave at least an hour for the rotation",
                "horizon": "declared-before-run: the rest of the trading day",
                **PSRC},
            script=__file__, probe=probe,
            notes="Later framing (outside bar / prior-day range). Rows are per-day facts; day-block CI.")
        print(p)
    if "b" in which:
        ev = cl.cache_frame("broadening_b_1h_swings", lambda: detect_b(cl.load_m1()))
        print("b", len(ev), ev.failed_side.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        print("probe", probe.get("passed"))
        nb = np.full(len(ev), HORIZON_B, dtype=np.int64)
        res = run_rate(ev, nb, "2D")
        C.show(res)
        p = cl.write_result(
            "broadening-formation", "b", res,
            operationalization={"rules": [
                "range = latest confirmed 1H 2/2 swing high and swing low, both untaken, price between them",
                "a 1H bar trades beyond one side; a 1H close back inside within 3 bars (that bar included) = failed side -> event at that close (beyond = breakout, no event)",
                "hit = the opposite swing traded within 1,440 M1 bars",
                "null = same distance from the next M1 open, same side, same 1,440-bar horizon, 5 matched random moments (+/-30d, NY time +/-30min)"],
                "params": {"tf": "1h", "swing": "2/2", "fail_bars": FAIL_BARS,
                           "horizon_bars": HORIZON_B, "null_tod_tol_min": TOD_TOL,
                           "null_reps": 5}},
            params_source={
                "tf": "corpus: dSccSI7uqvE concept timeframes htf 1D/1H",
                "swing": "phase3: swing_points left=2 right=2",
                "fail_bars": "declared-before-run: 'fail to break out' is unquantified; 3 1H bars to close back inside",
                "horizon_bars": "declared-before-run: one trading day of M1 bars",
                **PSRC},
            script=__file__, probe=probe,
            notes="Earlier framing (one high taking out another, range-bound on 1H).")
        print(p)
