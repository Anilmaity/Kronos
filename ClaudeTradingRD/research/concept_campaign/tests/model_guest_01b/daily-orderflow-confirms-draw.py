"""daily-orderflow-confirms-draw (guest: Jokerszn, JABOO4LYNjQ).

Claim: when daily order flow confirms the draw on liquidity, the marked objective
(an old high/low or a HTF FVG) is reached. rate_test: objective reached within the
next 5 trading sessions vs a geometry-matched null (same distance, same side, same
M1-bar horizon, from matched random moments +/-30d).

Declared before the first run:
  objective pools  unmitigated confirmed daily 2/2 swing highs/lows (<= 120 days old)
                   and live (un-inverted, <= 60 trading days) daily FVGs on the far side
                   of price: buy-side = nearest swing high above the close or bottom of a
                   bearish FVG above it; sell-side mirrored.
  draw             the nearer of the two objectives (proximity rule, method_spec §2.2
                   default); a side with no objective cannot be the draw.
  order flow       _common.daily_orderflow: daily CLOSES vs daily FVGs (respect = trade
                   into and close beyond the mean threshold; disrespect = close through).
  confirmed        order-flow state == draw direction. Only confirmed days are events.
  horizon          5 trading sessions (one week), counted in M1 bars.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, daily, daily_fvgs, daily_orderflow, np, pd,  # noqa: E402
                     swings_confirmed, OF_FVG_LIFE)

CID = "daily-orderflow-confirms-draw"
SWING_AGE = 120
HORIZON_DAYS = 5


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "level", "of_state"]
    d = daily(m1)
    if len(d) < 30:
        return pd.DataFrame(columns=cols)
    n = len(d)
    of = daily_orderflow(d)
    sw = swings_confirmed(d)
    ct = pd.DatetimeIndex(d["close_time"])
    ct_ns = ct.as_unit("ns").asi8
    conf_ns = pd.DatetimeIndex(sw["conf"]).as_unit("ns").asi8
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    f = daily_fvgs(d)
    fv = f.to_numpy() if len(f) else np.zeros((0, 4))
    sh_idx = np.flatnonzero(sw["sh"].to_numpy())
    sl_idx = np.flatnonzero(sw["sl"].to_numpy())
    rows = []
    for i in range(n):
        st = of["of_state"].iat[i]
        if st == 0:
            continue
        # unmitigated old highs above the close, confirmed by day i's close
        up = []
        for j in sh_idx:
            if j >= i or i - j > SWING_AGE or conf_ns[j] > ct_ns[i]:
                continue
            if h[j] > c[i] and h[j + 1:i + 1].max() <= h[j]:
                up.append(h[j])
        dn = []
        for j in sl_idx:
            if j >= i or i - j > SWING_AGE or conf_ns[j] > ct_ns[i]:
                continue
            if l[j] < c[i] and l[j + 1:i + 1].min() >= l[j]:
                dn.append(l[j])
        # live FVGs on the far side (not closed through since formation, <= life days)
        for k, pol, lo, hi in fv:
            k = int(k)
            if k > i or i - k > OF_FVG_LIFE:
                continue
            closes = c[k + 1:i + 1]
            if pol < 0 and lo > c[i] and not (closes > hi).any():
                up.append(lo)
            if pol > 0 and hi < c[i] and not (closes < lo).any():
                dn.append(hi)
        u = min(up) if up else np.nan
        w = max(dn) if dn else np.nan
        if np.isnan(u) and np.isnan(w):
            continue
        if np.isnan(w) or (not np.isnan(u) and (u - c[i]) <= (c[i] - w)):
            draw, lvl = 1, u
        else:
            draw, lvl = -1, w
        if draw != st:
            continue
        rows.append((ct[i], draw, lvl, st))
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "level", "of_state"])
    out.insert(1, "available_at", out["decision_time"])
    return out[cols]


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    mkt = cl.get_market()
    d = daily(m1)
    t = pd.DatetimeIndex(ev["decision_time"])
    # horizon: the next 5 sessions' M1-bar count (outcome side only)
    ct_all = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    pos = np.searchsorted(ct_all, t.as_unit("ns").asi8)
    nm = d["n_m1"].to_numpy()
    csum = np.concatenate([[0], np.cumsum(nm)])
    end = np.minimum(pos + 1 + HORIZON_DAYS, len(nm))
    hb = (csum[end] - csum[pos + 1]).astype(int)
    keep = (pos + HORIZON_DAYS < len(nm))
    ev = ev[keep].reset_index(drop=True)
    t, hb = t[keep], hb[keep]
    lvl = ev["level"].to_numpy()
    sgn = ev["direction"].to_numpy()
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = lvl - first_px
    obs = np.full(len(t), np.nan)
    for s, side in ((1, "above"), (-1, "below")):
        m = sgn == s
        obs[m] = cl.touch(t[m], lvl[m], side, horizon_bars=hb[m])["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        for s, side in ((1, "above"), (-1, "below")):
            m = ok & (sgn == s)
            if not m.any():
                continue
            px = mkt.o[mkt.pos_at_or_after(tk[m])]
            out[m] = cl.touch(tk[m], px + dist[m], side, horizon_bars=hb[m])["hit"].to_numpy()
        return out

    print("events", len(ev), "long share", (sgn > 0).mean(), "median dist/px", np.median(np.abs(dist) / first_px))
    # probe the frame actually scored (rows whose horizon runs past the data end removed)
    probe = cl.probe_lookahead(detect, ev, lookback="300D")
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, outcome_horizon="5D", claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "at each completed daily close (18:00 NY day, stubs < 600 M1 dropped): order flow = latest one-sided daily-close reaction to a live daily FVG"
        " (bullish: close above a bearish FVG, or trade into a bullish FVG and close at/above its mean threshold; bearish mirrored; <= 60 days memory)",
        "objectives: unmitigated confirmed daily 2/2 swing highs/lows (<= 120 days) and live daily FVGs beyond price (buy-side: bottom of a bearish FVG above)",
        "draw = nearer objective; event only when order flow == draw direction",
        "hit = the objective level is traded within the next 5 sessions (M1-bar horizon)",
        "null = same side, same distance from the first M1 open, same M1-bar horizon, at matched random moments (5 reps, +/-30d)"],
        "params": {"swing": "2/2 daily", "swing_age_days": SWING_AGE, "fvg_life_days": OF_FVG_LIFE,
                   "draw_rule": "proximity", "horizon_sessions": HORIZON_DAYS, "stub_min_m1": 600,
                   "day_open_hour": 18}}
    src = {"swing": "declared-before-run: 2/2 fractal swings, as phase-3 locked config",
           "swing_age_days": "declared-before-run: 'old highs/lows' bounded to ~6 months",
           "fvg_life_days": "declared-before-run: a daily FVG is a live PD array for 60 trading days",
           "draw_rule": "method_spec: §2.2 draw on liquidity, 'proximity' is the only fully mechanical reading (default)",
           "horizon_sessions": "declared-before-run: one trading week for a daily-scale objective",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Weekly-chart objectives and the 'return to neutral after objective' "
                        "rule are not modelled (daily pools only; each day re-derives the draw).")
    print("wrote", p)
