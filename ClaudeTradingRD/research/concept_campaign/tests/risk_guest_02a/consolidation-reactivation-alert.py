"""consolidation-reactivation-alert (guest: NickDoesFutures) — batch risk_guest_02a.

Claim tested (rate): when gold is consolidating (small daily ranges, small bodies),
an alert above the nearest opposing (bearish) daily fair value gap above price marks
the moment it "has the confirmation to reach for the liquidity above". Prediction:
once the alert fires, price reaches the liquidity above (the draw) more often than an
equal distance above price is reached from matched random moments over the same
number of trading bars.

Operationalisation (bullish case, as stated in the source):
  * daily bars roll at 18:00 NY; stub days (< 600 M1 bars) are skipped
  * consolidation at a daily close k: mean range of the last 5 days < 0.8 x mean range
    of the 20 days before them, and mean |body| of the last 5 days < 0.5 x their mean
    range
  * bearish daily FVG: bars (a, a+1, a+2) with low[a] > high[a+2]; known at the close
    of a+2; still open if no later daily high (through day k) exceeded its top low[a];
    'above' if its bottom high[a+2] > close[k]; nearest = lowest bottom; search the
    last 60 daily bars
  * alert = the gap TOP; armed for the next session (1,380 M1 bars after the close of
    day k); fires on the first M1 high above it; one fire per gap
  * draw = nearest confirmed (2/2, confirmed by the close of day k) daily swing high
    above the alert level that no later daily high has exceeded, last 60 daily bars;
    events without such a draw are dropped
  * hit = any M1 high >= draw within the next 5 sessions (5 x 1,380 M1 bars)
  * null = the same distance above the entry price, same bar count, at 5 matched
    random moments within +/-30 days
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

MIN_DAY_M1 = 600
SHORT_N, LONG_N = 5, 20
RANGE_RATIO = 0.8
BODY_RATIO = 0.5
SEARCH_BARS = 60
SESSION_BARS = 1380
HORIZON_SESSIONS = 5


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "alert_level", "draw_px", "gap_bottom"]
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_DAY_M1]
    n = len(d)
    if n < LONG_N + SHORT_N + 3:
        return pd.DataFrame(columns=cols)
    O = d["open"].to_numpy(float)
    H = d["high"].to_numpy(float)
    L = d["low"].to_numpy(float)
    C = d["close"].to_numpy(float)
    ct = _ns(d["close_time"])
    rng = H - L
    body = np.abs(C - O)
    sw = swing_points(d[["open", "high", "low", "close"]], left=2, right=2)
    sh = np.nonzero(sw["swing_high"].to_numpy())[0]
    mt = _ns(m1.index)
    mh = m1["high"].to_numpy(float)
    fired = set()
    rows = []
    for k in range(LONG_N + SHORT_N - 1, n):
        s5 = slice(k - SHORT_N + 1, k + 1)
        s20 = slice(k - SHORT_N - LONG_N + 1, k - SHORT_N + 1)
        r5 = rng[s5].mean()
        if not (r5 < RANGE_RATIO * rng[s20].mean() and body[s5].mean() < BODY_RATIO * r5):
            continue
        best = None
        for a in range(max(0, k - SEARCH_BARS), k - 1):
            top, bot = L[a], H[a + 2]
            if not top > bot or a in fired:
                continue
            if a + 3 <= k and H[a + 3:k + 1].max() > top:
                continue
            if bot <= C[k]:
                continue
            if best is None or bot < H[best + 2]:
                best = a
        if best is None:
            continue
        top = L[best]
        s = int(np.searchsorted(mt, ct[k], side="left"))
        e = min(len(mt), s + SESSION_BARS)
        if e <= s:
            continue
        above = np.nonzero(mh[s:e] > top)[0]
        if len(above) == 0:
            continue
        kk = s + int(above[0])
        t = mt[kk] + 60_000_000_000
        # draw: nearest unbroken daily swing high above the alert, confirmed by close k
        draw = np.nan
        for i in sh[(sh >= k - SEARCH_BARS) & (sh + 2 <= k)]:
            if H[i] <= top:
                continue
            if i + 1 <= k and H[i + 1:k + 1].max() > H[i]:
                continue
            if np.isnan(draw) or H[i] < draw:
                draw = H[i]
        fired.add(best)
        if not np.isfinite(draw):
            continue
        # the session may already have run through the draw before the alert fired
        if mh[s:kk + 1].max() >= draw:
            continue
        rows.append((t, top, draw, H[best + 2]))
    if not rows:
        return pd.DataFrame(columns=cols)
    a = np.array(rows, dtype=float)
    dt = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype(np.int64), utc=True))
    return pd.DataFrame({"decision_time": dt, "available_at": dt, "alert_level": a[:, 1],
                         "draw_px": a[:, 2], "gap_bottom": a[:, 3]})


if __name__ == "__main__":
    ev = cl.cache_frame("rg02a_consol_alert_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="180D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    hb = HORIZON_SESSIONS * SESSION_BARS
    obs = cl.touch(t, ev["draw_px"].to_numpy(), "above", horizon_bars=hb)["hit"].to_numpy()
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = ev["draw_px"].to_numpy() - first_px
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[ok])]
        out[ok] = cl.touch(tk[ok], px + dist[ok], "above",
                           horizon_bars=hb)["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, outcome_horizon="5D", claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "daily bars (18:00 NY roll), stub days < 600 M1 bars skipped",
        "consolidation at day k: mean range(last 5) < 0.8 x mean range(20 before) and "
        "mean |body|(last 5) < 0.5 x mean range(last 5)",
        "nearest open bearish daily FVG above close[k] (low[a] > high[a+2], top not "
        "exceeded since), searched over 60 daily bars",
        "alert = gap top, armed for the next 1,380 M1 bars; fires on first M1 high above; "
        "once per gap; decision at that M1 close",
        "draw = nearest unbroken confirmed 2/2 daily swing high above the alert (60 bars); "
        "drop if none or if already reached before the alert",
        "hit = M1 high >= draw within 5 x 1,380 M1 bars; null = same distance above "
        "price, same bars, at 5 random moments +/-30 days"],
        "params": {"min_day_m1": MIN_DAY_M1, "short_n": SHORT_N, "long_n": LONG_N,
                   "range_ratio": RANGE_RATIO, "body_ratio": BODY_RATIO,
                   "search_bars": SEARCH_BARS, "alert_level": "gap top",
                   "session_bars": SESSION_BARS, "horizon_sessions": HORIZON_SESSIONS,
                   "draw": "nearest unbroken daily 2/2 swing high", "day_open_hour": 18}}
    src = {
        "min_day_m1": "declared-before-run: skip stub sessions (README trap 6; as the "
                      "harness rate example)",
        "short_n": "declared-before-run: 'small days' judged over the last week (5 sessions)",
        "long_n": "declared-before-run: vs the prior 20 sessions",
        "range_ratio": "declared-before-run: small days = 5-day mean range < 0.8x the "
                       "prior 20-day mean (corpus does not quantify 'small days')",
        "body_ratio": "declared-before-run: small bodies = mean body < half the mean range",
        "search_bars": "declared-before-run: 60 daily bars (~3 months) gap/draw search",
        "alert_level": "corpus: tDiwwMRWF2k 'set like an alert above the bearish gap from "
                       "June 5th' -> above the gap's top (ambiguity resolved to the top)",
        "session_bars": "declared-before-run: one ~23h session = 1,380 M1 bars",
        "horizon_sessions": "declared-before-run: 5 sessions (one week) to reach the draw",
        "draw": "declared-before-run: 'the liquidity above' = nearest unbroken daily swing "
                "high above the alert (yaml: 'treat the liquidity above as the draw')",
        "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
    }
    p = cl.write_result("consolidation-reactivation-alert", None, res,
                        operationalization=op, params_source=src, script=__file__,
                        probe=probe)
    print(p)
