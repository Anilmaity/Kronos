"""range-market-avoidance (guest: Trader Kane) — batch risk_guest_02a.

Claim tested (gate): the guest's model — buy the retracement into 50% of the prior
expansion leg and hold for the next expansion — does better in an expansive market
than in a range-bound one ("completely unprofitable in range-bound markets").

Baseline book (his model, 1h, both directions):
  * leg: a confirmed 1h 2/2 swing high (long case) and its origin = the lowest low
    since the most recent 1h swing low before it; leg range >= 1.0 x ATR14(1h)
  * after the swing high is confirmed (close of the 2nd right bar), the first M1 bar
    whose low reaches the leg's 50% level triggers, within 24h, provided no M1 bar
    first traded above the leg high (the leg extended = new leg) and the trigger bar
    did not reach the origin; decide at that M1 bar's close
  * stop = the leg origin (stop not stated by the guest: declared); target = the leg
    high (the start of "the next expansion"); hold 10h. Mirrored for down legs.
Gate: expansive := Kaufman efficiency ratio of the last 48 completed 1h closes >= 0.20
(range-bound = price rotating without net progress; a driftless random walk gives
~0.14 at n=48). The mask is known at the decision (closed 1h bars only).
The "trade the range if it is large enough" branch has no threshold in the corpus and
is not tested.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402
from _base_cisd import _ns  # noqa: E402

ER_N = 48
ER_CUT = 0.20
ATR_N = 14
MIN_LEG_ATR = 1.0
TRIGGER_WINDOW = pd.Timedelta("24h")
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "expansive"]
    b = cl.build_bars(m1, "1h")
    ohlc = b[["open", "high", "low", "close"]]
    n = len(b)
    if n < ER_N + 5:
        return pd.DataFrame(columns=cols)
    sw = swing_points(ohlc, left=2, right=2)
    is_h = sw["swing_high"].to_numpy()
    is_l = sw["swing_low"].to_numpy()
    H = b["high"].to_numpy(float)
    L = b["low"].to_numpy(float)
    C = b["close"].to_numpy(float)
    c_ns = _ns(b["close_time"])
    prevc = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - prevc), np.abs(L - prevc)]), axis=0)
    atr = pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    absd = np.r_[np.nan, np.abs(np.diff(C))]
    vol = pd.Series(absd).rolling(ER_N, min_periods=ER_N).sum().to_numpy()
    net = np.full(n, np.nan)
    net[ER_N:] = np.abs(C[ER_N:] - C[:-ER_N])
    with np.errstate(invalid="ignore", divide="ignore"):
        er = net / vol

    mt = _ns(m1.index)
    mh = m1["high"].to_numpy(float)
    ml = m1["low"].to_numpy(float)
    hi_idx = np.nonzero(is_h)[0]
    lo_idx = np.nonzero(is_l)[0]
    rows = []
    for d, ext_idx, opp_idx in ((1, hi_idx, lo_idx), (-1, lo_idx, hi_idx)):
        for i in ext_idx:
            if i + 2 >= n:
                continue
            q = int(np.searchsorted(opp_idx, i, side="left")) - 1
            if q < 0:
                continue
            a = opp_idx[q]
            if d == 1:
                ext, origin = H[i], L[a:i + 1].min()
            else:
                ext, origin = L[i], H[a:i + 1].max()
            j = i + 2                                      # bar that confirms the swing
            rng = abs(ext - origin)
            if not np.isfinite(atr[j]) or rng < MIN_LEG_ATR * atr[j] or rng <= 0:
                continue
            mid = (ext + origin) / 2.0
            tc = c_ns[j]
            s = int(np.searchsorted(mt, tc, side="left"))
            e = int(np.searchsorted(mt, tc + TRIGGER_WINDOW.value, side="left"))
            if e <= s:
                continue
            if d == 1:
                trig = ml[s:e] <= mid
                canc = mh[s:e] > ext
                bad = ml[s:e] <= origin
            else:
                trig = mh[s:e] >= mid
                canc = ml[s:e] < ext
                bad = mh[s:e] >= origin
            anyk = trig | canc
            if not anyk.any():
                continue
            k = int(np.argmax(anyk))
            if canc[k] or bad[k]:
                continue
            t = mt[s + k] + 60_000_000_000
            jj = int(np.searchsorted(c_ns, t, side="right")) - 1   # last closed 1h bar
            if jj < 0 or not np.isfinite(er[jj]):
                continue
            rows.append((t, d, origin, ext, bool(er[jj] >= ER_CUT)))
    if not rows:
        return pd.DataFrame(columns=cols)
    a = np.array(rows, dtype=object)
    dt = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype(np.int64), utc=True))
    out = pd.DataFrame({
        "decision_time": dt, "available_at": dt,
        "direction": a[:, 1].astype(int),
        "stop_px": a[:, 2].astype(float), "target_px": a[:, 3].astype(float),
        "expansive": a[:, 4].astype(bool),
    })
    return out.sort_values(["decision_time", "direction", "stop_px"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("rg02a_range_avoid_50pct_1h_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), "expansive share", ev["expansive"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "expansive", mask_available_at="decision_time",
                       max_hold=MAX_HOLD, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "gate", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "baseline (the guest's model): 1h 2/2 swing leg (origin = extreme since the prior "
        "opposite swing), leg >= 1.0 ATR14(1h); after the swing is confirmed, first M1 "
        "touch of the leg's 50% within 24h (cancel if the leg extends first or the "
        "trigger bar reaches the origin); decide at that M1 close",
        "stop = leg origin; target = leg extreme; hold 10h; both directions",
        "gate 'expansive' = efficiency ratio of the last 48 closed 1h closes >= 0.20 "
        "(complement = range-bound); known at the decision",
        "the 'trade the range if large enough' branch is not tested (no threshold)"],
        "params": {"tf": "1h", "swing": "2/2", "retrace_level": 0.5,
                   "min_leg_atr": MIN_LEG_ATR, "atr_n": ATR_N,
                   "trigger_window": "24h", "stop": "leg origin",
                   "target": "leg extreme", "max_hold": MAX_HOLD,
                   "er_n": ER_N, "er_cut": ER_CUT}}
    src = {
        "tf": "declared-before-run: 1h (guest gives no timeframe; phase-3 1h book TF)",
        "swing": "phase3: 2/2 fractal swings (locked config)",
        "retrace_level": "corpus: 1wKfc2gN4xg (yaml execution: 'Retracement into 50% of the "
                         "prior expansion leg')",
        "min_leg_atr": "declared-before-run: an 'expansion' leg spans at least one 1h ATR",
        "atr_n": "declared-before-run: standard ATR14",
        "trigger_window": "declared-before-run: the retracement must come within 24h",
        "stop": "declared-before-run: stop not stated by the guest; the leg origin is "
                "the leg's invalidation",
        "target": "corpus: 1wKfc2gN4xg (yaml targets: 'the next expansion leg') -> the "
                  "leg extreme where the next expansion begins",
        "max_hold": "phase3: 10 entry-TF bars (§1.13)",
        "er_n": "declared-before-run: 48 1h bars (two sessions) regime lookback",
        "er_cut": "declared-before-run: 0.20, above the ~0.14 driftless random-walk "
                  "efficiency ratio at n=48",
    }
    notes = ("Guest gives no mechanical range classifier ('by feel'); the efficiency "
             "ratio is the declared stand-in for 'rotating between a fixed high and low "
             "without producing new expansion'.")
    p = cl.write_result("range-market-avoidance", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)
