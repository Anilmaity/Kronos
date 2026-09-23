"""session-high-low (liquidity, TTrades own voice, specified) — batch liquidity_own_01b.

Claim (MPeeE55rNOw / YESqIoA7Wyg / U8xH2dEgH5A): the high and low of a completed killzone
session are "liquidity pools of the same kind as previous-day levels" — price is drawn to
them. Measurable named in the concept: "frequency with which the Asia range high/low is
swept during London".

Rate test. Levels: forex Asia (20:00-00:00 NY) and London (02:00-05:00 NY) highs and lows,
from cl.window_hilo (available at the window's end). A row is a level still beyond the
first M1 open after the window ends. Hit = traded to within the rest of the morning, up to
12:00 NY (the end of the forex London-close killzone), counted in M1 bars. Null: the same
signed distance from the open of a random other day's same NY minute (+/-30 min) within
+/-30 days, same bar count, 5 reps. The time-of-day match matters here: the window ends
right before the London / New York volatility ramp, which a clock-free null would lack.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

WINDOWS = {"fx_asia": 12 * 60, "fx_london": 7 * 60}   # minutes from window end to 12:00 NY
MIN_COVER = 0.5                                        # of the window's nominal minutes
NOMINAL = {"fx_asia": 240, "fx_london": 180}
TOD_TOL = 30


def build_rows():
    rows = []
    for w, h_min in WINDOWS.items():
        f = cl.window_hilo(w)
        f = f[f["n_m1"] >= MIN_COVER * NOMINAL[w]]
        av = pd.DatetimeIndex(f["available_at"]).tz_convert("UTC")
        for side, col in ((1, "high"), (-1, "low")):
            rows.append(pd.DataFrame({"decision_time": av, "level": f[col].to_numpy(),
                                      "side": side, "window": w, "h_min": h_min}))
    ev = pd.concat(rows, ignore_index=True)
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)


if __name__ == "__main__":
    mkt = cl.get_market()
    ev = build_rows()
    t = pd.DatetimeIndex(ev["decision_time"])
    N = len(mkt.o)
    i0 = mkt.pos_at_or_after(t)
    i1 = mkt.pos_at_or_after(t + pd.to_timedelta(ev["h_min"].to_numpy(), unit="min"))
    hb = (i1 - i0).astype(np.int64)
    ok = (i0 < N) & (hb > 0)
    first_px = mkt.o[np.minimum(i0, N - 1)]
    lvl, side = ev["level"].to_numpy(), ev["side"].to_numpy()
    dist = lvl - first_px
    ok &= np.sign(dist) == side
    obs = np.full(len(ev), np.nan)
    for s, nm in ((1, "above"), (-1, "below")):
        r = ok & (side == s)
        obs[r] = cl.touch(t[r], lvl[r], nm, horizon_bars=hb[r])["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

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

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="+")
    print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail")})
    for w in WINDOWS:
        s = (ev["window"].to_numpy() == w) & np.isfinite(obs)
        print(w, int(s.sum()), float(np.nanmean(obs[s])))
    op = {"rules": ["levels: high and low of the forex Asia (20:00-00:00 NY) and London (02:00-05:00 NY) windows, available at the window end",
                    "row kept if the window covered >=50% of its minutes and the level is still beyond the first open after the window",
                    "hit = price trades to the level before 12:00 NY the same trading day (horizon in M1 bars)",
                    "claim: session extremes are reached more often than an arbitrary level at the same distance at the same clock time"],
          "params": {"windows": {"fx_asia": "20:00-00:00", "fx_london": "02:00-05:00"}, "horizon_end": "12:00 NY",
                     "min_cover": MIN_COVER, "null": "distance-matched, NY clock +/-30min, +/-30d, 5 reps"}}
    src = {"windows": "corpus: MPeeE55rNOw killzone pivots; concept detection_rules asia 20:00-00:00, london 02:00-05:00 (session_window_fit: killzones.yaml verbatim)",
           "horizon_end": "session_window_fit: forex London Close killzone ends 12:00 NY (08:30-12:00 is the corpus-faithful superset)",
           "min_cover": "declared-before-run: skip windows with <50% of nominal minutes (data holes, README trap 6)",
           "null": "declared-before-run: same signed distance from the open at a random other day's same NY minute (+/-30 min, +/-30 d), same M1-bar count, 5 reps"}
    notes = ("Liquidity-pool (draw) reading of session highs/lows. NY AM window levels are not included: their "
             "natural target window (the NY PM / next session) is not stated. The two stated displacement rules "
             "('fails to displace -> other side'; 'sweep high then displace below low -> continuation') need an "
             "undefined displacement measure and are not tested here.")
    p = cl.write_result("session-high-low", None, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes,
                        no_detector="pure clock/level rule: session window highs/lows from cl.window_hilo with its available_at (window end); no detector")
    print("wrote", p)
