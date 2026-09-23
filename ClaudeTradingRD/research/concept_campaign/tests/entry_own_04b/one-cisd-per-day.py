"""one-cisd-per-day — rate_test.

Concept (i2HhHhWdaPQ): "you really only have one change in the state of delivery per day" —
the day's first CISD (London, else New York) is the one that forms the daily candle's wick;
later same-direction breaks are continuations of it. Invalidation: the wick it confirmed is
traded through (the day's extreme was not in).

Test: for each trading day, take the FIRST 15m CISD confirmed in 02:00-12:00 NY (London open
to the end of the NY AM session). Prediction: its protected swing is the day's extreme, i.e.
price does not trade through it before the trading day ends (17:00 NY halt).
Null: the same distance beyond price at matched random moments (+/-30 d, same NY time of day
+/-30 min), over the same number of M1 bars. claim '+': held rate > null held rate.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

TF = "15min"
MAX_WAIT = 3
SWING = 2
WIN = ("02:00", "12:00")      # London open .. end of NY AM (session windows)
DAY_END_NY = "17:00"          # daily halt = end of the trading day
NULL_TOD_TOL = 30


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    cols = ["decision_time", "available_at", "direction", "level", "entry_ref"]
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=SWING, right=SWING, max_wait=MAX_WAIT, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    df = pd.DataFrame({"decision_time": close, "available_at": close,
                       "direction": np.where(ev["direction"] == "bullish", 1, -1),
                       "level": ev["protected_swing"].to_numpy(float),
                       "entry_ref": ev["confirm_close"].to_numpy(float)})
    df = df[cl.in_window(df["decision_time"], *WIN)]
    df["_day"] = cl.trading_day(pd.DatetimeIndex(df["decision_time"]))
    df = df.sort_values("decision_time").groupby("_day", sort=True).head(1)
    return df[cols].reset_index(drop=True)


def day_end(times: pd.DatetimeIndex) -> pd.DatetimeIndex:
    ny = times.tz_convert("America/New_York")
    end = (ny.normalize() + pd.Timedelta(hours=17)).tz_localize(None)
    return end.tz_localize("America/New_York", ambiguous="NaT",
                           nonexistent="shift_forward").tz_convert("UTC")


if __name__ == "__main__":
    ev = cl.cache_frame(f"one_cisd_{TF}_mw{MAX_WAIT}_{WIN[0]}_{WIN[1]}",
                        lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print(len(ev), "probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    i0 = mkt.pos_at_or_after(t)
    nb = mkt.pos_at_or_after(day_end(t)) - i0
    keep = nb > 0                      # rows with no bar before day end -> NaN outcome
    nb = np.maximum(nb, 1)
    px0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    d = ev["direction"].to_numpy()
    lvl = ev["level"].to_numpy(float)
    dist = px0 - lvl                    # >0 for bullish (level below), <0 bearish
    side = np.where(d > 0, "below", "above")

    def held(times, level, bars_):
        out = np.full(len(times), np.nan)
        for s in ("below", "above"):
            m = (side == s) & ~pd.isna(times)
            if m.any():
                out[m] = ~cl.touch(pd.DatetimeIndex(times[m]), level[m], s,
                                   horizon_bars=bars_[m])["hit"].to_numpy()
        return out

    obs = held(t, lvl, nb)
    obs[~keep] = np.nan
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=NULL_TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        pk = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        tmp_side = side[ok]
        res = np.full(ok.sum(), np.nan)
        for s in ("below", "above"):
            m = tmp_side == s
            if m.any():
                res[m] = ~cl.touch(tk[ok][m], (pk - dist[ok])[m], s,
                                   horizon_bars=nb[ok][m])["hit"].to_numpy()
        out[ok] = res
        out[~keep] = np.nan
        return out

    # predictors must be the probed frame: re-probe the filtered frame is not needed if
    # no row was dropped; check.
    if not keep.all():
        print("dropped rows with no bars before day end:", int((~keep).sum()))
    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, predictors=ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "15m CISD (series_open, 2/2 swings, close-through within 3 bars), confirmed "
        "(decision at the confirming bar's close) between 02:00 and 12:00 NY",
        "the day's single CISD = the first such event in the trading day (18:00 NY roll)",
        "prediction: its protected swing is the daily wick -> not traded through from the "
        "next M1 open to the 17:00 NY halt",
        "null: same signed distance from the M1 open at matched random moments (+/-30d, "
        "NY time of day +/-30 min), same number of M1 bars"],
        "params": {"tf": TF, "max_wait": MAX_WAIT, "swing": SWING, "window": WIN,
                   "day_end": DAY_END_NY, "null_tod_tol_min": NULL_TOD_TOL}}
    src = {"tf": "corpus: daily-wick-confirmation-timeframes — London 15m/30m CISD, New York "
                 "5m/15m CISD; 15m is the one timeframe named for both sessions",
           "max_wait": "phase3: locked CISD config", "swing": "phase3: locked 2/2 swing",
           "window": "session_window_fit: London open 02:00 NY .. ny_am end 12:00 NY "
                     "(concept names London then New York)",
           "day_end": "session_window_fit: daily halt 17:00 NY ends the trading day",
           "null_tod_tol_min": "declared-before-run: hold NY clock fixed in the null (trap 9)"}
    notes = f"{int((~keep).sum())} events with no M1 bar before day end scored NaN (dropped)"
    p = cl.write_result("one-cisd-per-day", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)
