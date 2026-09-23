"""previous-period-high-low (liquidity, TTrades own voice, contested) — batch liquidity_own_01b.

Two readings, both rate tests against a geometry-matched null:

 a  DRAW reading (variant, YESqIoA7Wyg / g3oDYq4P9ZE): "expect price to trade to PDH, PDL,
    or both" — the previous day's high and low are magnets. At each trading-day close,
    the day's high (above) and low (below) are the levels; hit = traded during the next
    session. Null: the SAME signed distance from the next session's first open, on a
    random other session open within +/-30 days (same NY clock), same bar count.

 b  REVERSAL-CASE reading (A4NasIa371c fractal targeting + variant): day D-1 trades
    beyond D-2's high (low) but closes back inside D-2's range (and did not take the other
    side) -> "expect the opposite level to become the draw": D-2's low (high) is reached
    during day D. Candle-1's extreme is the first target (A4NasIa371c). Same null.

All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from concept_lab.data import utc_ns

MIN_DAY_BARS = 600          # drop stub sessions (data holes); README trap 6 / example_rate
TOD_TOL = 30                # null draws at the same NY clock (+/- 30 min) on another day


def daily(m1):
    d = cl.build_bars(m1, "1D")
    return d[d["n_m1"] > MIN_DAY_BARS]


def detect_a(m1):
    d = daily(m1)
    t = pd.DatetimeIndex(d["close_time"])
    n = len(d)
    out = pd.DataFrame({
        "decision_time": np.concatenate([t, t]),
        "available_at": np.concatenate([t, t]),
        "level": np.concatenate([d["high"].to_numpy(), d["low"].to_numpy()]),
        "side": np.array([1] * n + [-1] * n),        # +1 level above (PDH), -1 below (PDL)
    })
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = pd.DatetimeIndex(out["available_at"]).tz_convert("UTC")
    return out.sort_values(["decision_time", "side"]).reset_index(drop=True)


def detect_b(m1):
    d = daily(m1)
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    h2, l2 = np.roll(h, 1), np.roll(l, 1)            # D-2 (candle 1) relative to D-1 (candle 2)
    valid = np.arange(len(d)) >= 1
    took_hi = h > h2
    took_lo = l < l2
    inside = (c < h2) & (c > l2)
    bear = valid & took_hi & ~took_lo & inside       # swept C1 high, closed back inside
    bull = valid & took_lo & ~took_hi & inside
    t = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    sel = bear | bull
    out = pd.DataFrame({
        "decision_time": t[sel], "available_at": t[sel],
        "level": np.where(bear, l2, h2)[sel],          # candle 1's opposite extreme
        "side": np.where(bear, -1, 1)[sel],
    })
    return out.reset_index(drop=True)


def outcome_and_null(ev, full_daily):
    """hit during the next real session (its M1 bar count), and a matched null."""
    mkt = cl.get_market()
    ct = pd.DatetimeIndex(full_daily["close_time"]).tz_convert("UTC")
    nb = full_daily["n_m1"].to_numpy()
    t = pd.DatetimeIndex(ev["decision_time"])
    pos = np.searchsorted(utc_ns(ct), utc_ns(t))                 # row of this day in full_daily
    nxt = pos + 1
    has = nxt < len(full_daily)
    hb = np.where(has, nb[np.minimum(nxt, len(nb) - 1)], 0)
    i0 = mkt.pos_at_or_after(t)
    ok = has & (i0 < len(mkt.o))
    first_px = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    start = pd.DatetimeIndex(mkt.tn[np.minimum(i0, len(mkt.o) - 1)]).tz_localize("UTC")
    lvl = ev["level"].to_numpy()
    side = ev["side"].to_numpy()
    dist = lvl - first_px
    ok &= np.sign(dist) == side                     # level still untaken at the session open
    obs = np.full(len(ev), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        r = ok & (side == s)
        if r.any():
            obs[r] = cl.touch(t[r], lvl[r], nm, horizon_bars=hb[r])["hit"].to_numpy()
    # null: sample around the session's first bar so the NY clock is matched (18:00 open)
    rt = cl.sample_times(start, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(ev), np.nan)
        good = ok & ~tk.isna()
        for s, nm in ((1, "above"), (-1, "below")):
            r = good & (side == s)
            if r.any():
                px = mkt.o[mkt.pos_at_or_after(tk[r])]
                out[r] = cl.touch(tk[r], px + dist[r], nm, horizon_bars=hb[r])["hit"].to_numpy()
        return out
    return obs, null_fn


def run(reading):
    m1 = cl.load_m1()
    det = detect_a if reading == "a" else detect_b
    ev = cl.cache_frame(f"pphl_{reading}_min{MIN_DAY_BARS}", lambda: det(m1))
    probe = cl.probe_lookahead(det, ev, lookback="20D")
    fd = daily(m1)
    obs, null_fn = outcome_and_null(ev, fd)
    res = cl.rate_test(obs, ev["decision_time"], available_at=ev["available_at"],
                       null_fn=null_fn, predictors=ev, claim="+")
    return ev, res, probe


if __name__ == "__main__":
    common_src = {
        "min_day_bars": "declared-before-run: drop stub sessions <=600 M1 bars (README trap 6; example_rate uses the same cut)",
        "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
        "horizon": "declared-before-run: the next real session, counted in M1 bars (trading time)",
        "null": "declared-before-run: same signed distance from the next session's first open, random other session open +/-30d, NY clock +/-30min, same bar count, 5 reps",
    }
    for reading in ("a", "b"):
        ev, res, probe = run(reading)
        print(reading, {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
        if reading == "a":
            op = {"rules": ["levels: each completed NY trading day's high (PDH) and low (PDL)",
                            "decision at that day's close; row kept only if the level is still beyond the next session's first open",
                            "hit = next session trades to the level (any M1 high >= PDH / low <= PDL)",
                            "claim: PDH/PDL are reached more often than an arbitrary level at the same distance (they are 'the draw')"],
                  "params": {"min_day_bars": MIN_DAY_BARS, "day_open_hour": 18,
                             "horizon": "next session (M1 bars)", "null": "distance-matched, clock-matched +/-30min, +/-30d, 5 reps"}}
            notes = ("Draw reading of the variant definition. Both sides per day are rows; the day-block CI "
                     "handles their shared day. Consolidation (inside-day) days were NOT excluded because "
                     "'not consolidating' is only knowable after the day it would qualify.")
        else:
            op = {"rules": ["candle 2 = day D-1: trades beyond D-2's high (low), does not take D-2's other side, and closes back inside D-2's range",
                            "decision at D-1's close; level = candle 1's (D-2's) OPPOSITE extreme",
                            "hit = day D trades to that level; row kept only if the level is still beyond day D's first open",
                            "claim: the opposite previous-candle extreme is reached more often than an equal-distance level"],
                  "params": {"min_day_bars": MIN_DAY_BARS, "day_open_hour": 18,
                             "horizon": "next session (M1 bars)", "null": "distance-matched, clock-matched +/-30min, +/-30d, 5 reps"}}
            notes = ("Reversal-case reading ('price trades beyond the level but the period closes back inside the "
                     "previous range -> expect the opposite level to become the draw'); first target = candle 1's extreme "
                     "per A4NasIa371c. Horizon limited to the next day ('next period').")
        src = dict(common_src)
        p = cl.write_result("previous-period-high-low", reading, res, operationalization=op,
                            params_source=src, script=__file__, probe=probe, notes=notes)
        print("wrote", p)
