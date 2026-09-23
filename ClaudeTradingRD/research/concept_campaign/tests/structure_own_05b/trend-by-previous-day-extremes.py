"""trend-by-previous-day-extremes -> rate_test.

Claim (FXJBFbZQbck): "in a bullish trend price will continue to take previous day's high"
(bearish: previous day's low). The trend = the repetition; while it holds the draw for the
next day is the corresponding previous-day extreme. claim '+': given a trend, the next day
takes today's extreme in the trend direction MORE often than a geometry-matched null.

Reading (all declared before the first run):
  * Daily candles on the 18:00 NY trading day (settled roll); stub sessions (< 600 M1 bars)
    dropped, so "previous day" = previous real session.
  * 'takes' = wick through (high > previous high / low < previous low): the literal word;
    close-beyond is not stated.
  * Trend = the last N=2 consecutive sessions each took their previous day's high (bull) /
    low (bear). A session pair qualifying both ways (outside days) is dropped.
  * Decision at the session's close; level = that session's high (bull) / low (bear),
    i.e. the next day's PDH/PDL.
  * Outcome: any M1 high >= level (bull) / low <= level (bear) during the next session
    (horizon = that session's M1-bar count, trading time).
  * Null: 5 matched random M1 moments within +/-30 days; level at the same signed distance
    from the first open after the moment, same side, same bar horizon.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import show  # noqa: E402

CID = "trend-by-previous-day-extremes"
N_TREND = 2
MIN_BARS = 600
COLS = ["decision_time", "available_at", "direction", "level"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_BARS]
    if len(d) < N_TREND + 2:
        return pd.DataFrame(columns=COLS)
    h, l = d["high"].to_numpy(float), d["low"].to_numpy(float)
    th = np.r_[False, h[1:] > h[:-1]]
    tl = np.r_[False, l[1:] < l[:-1]]
    bull = np.ones(len(d), bool)
    bear = np.ones(len(d), bool)
    for j in range(N_TREND):
        bull &= np.r_[np.zeros(j, bool), th[:len(d) - j]]
        bear &= np.r_[np.zeros(j, bool), tl[:len(d) - j]]
    keep = bull ^ bear
    ct = pd.DatetimeIndex(d["close_time"])[keep]
    dirn = np.where(bull[keep], 1, -1)
    lvl = np.where(bull[keep], h[keep], l[keep])
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": dirn,
                         "level": lvl}).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_N{N_TREND}_wick", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"), len(ev), ev["direction"].value_counts().to_dict())
    mkt = cl.get_market()
    dall = cl.bars("1D")
    ct_all = cl.data.utc_ns(pd.DatetimeIndex(dall["close_time"]))
    t = pd.DatetimeIndex(ev["decision_time"])
    # next session = first daily bar whose close_time > t (its bar-count is the horizon)
    k = np.searchsorted(ct_all, cl.data.utc_ns(t), side="right")
    ok = k < len(dall)
    ev, t, k = ev[ok].reset_index(drop=True), t[ok], k[ok]
    nxt = dall["n_m1"].to_numpy()[k].astype(np.int64)
    lvl = ev["level"].to_numpy(float)
    up = ev["direction"].to_numpy() > 0
    p0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = lvl - p0

    def hits(times, level, horizon):
        out = np.zeros(len(times), float)
        for side, sel in (("above", up), ("below", ~up)):
            if sel.any():
                out[sel] = cl.touch(times[sel], level[sel], side,
                                    horizon_bars=horizon[sel])["hit"].to_numpy()
        return out

    obs = hits(t, lvl, nxt)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, kk):
        tk = pd.DatetimeIndex(rt[:, kk]).tz_localize("UTC")
        okk = ~tk.isna()
        out = np.full(len(t), np.nan)
        tt = tk[okk]
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tt), len(mkt.o) - 1)]
        o2 = np.zeros(okk.sum())
        u = up[okk]
        for side, sel in (("above", u), ("below", ~u)):
            if sel.any():
                o2[sel] = cl.touch(tt[sel], (px + dist[okk])[sel], side,
                                   horizon_bars=nxt[okk][sel])["hit"].to_numpy()
        out[okk] = o2
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev, outcome_horizon="1D")
    show(res)
    op = {"rules": [
        "daily candles on the 18:00 NY trading day; sessions with < 600 M1 bars dropped",
        "take = wick through the previous session's high (low)",
        "bull trend = the last 2 sessions each took their previous day's high; bear = each "
        "took the previous low; both at once -> dropped",
        "decide at the session close; level = that session's high (bull) / low (bear)",
        "hit = level touched during the next session (M1-bar horizon)",
        "null = same signed distance from price, same side, same bar horizon, 5 random "
        "moments within +/-30 days"],
        "params": {"n_trend": N_TREND, "take": "wick", "min_bars": MIN_BARS,
                   "day_open_hour": 18, "horizon": "next session M1 bars"}}
    src = {"n_trend": "declared-before-run: 'over and over again' / 'each successive day'; no "
                      "count given (ambiguity) -> the minimum repetition, 2 consecutive days",
           "take": "declared-before-run: literal 'take' = trade through (wick); close-beyond "
                   "is not stated",
           "min_bars": "declared-before-run: README trap 6 stub sessions (example uses >600)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "horizon": "corpus: FXJBFbZQbck 'the draw for the coming day' -> one session"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Tests the trend-conditioned next-day draw vs a geometry-"
                              "matched null (the raw hit rate is mostly distance).")
    print(p)
