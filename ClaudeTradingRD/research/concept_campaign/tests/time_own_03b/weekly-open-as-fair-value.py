"""weekly-open-as-fair-value (TTrades own voice, wrIZ7CAuFCc): 'the weekly opening price
showing me fair value for the week ... you can see how price reacted along that level all
throughout the week'. Declared before any run.

Reading tested (one; the concept is underspecified, not contested): fair value = a level
price keeps returning to during the week. rate_test (claim '+'):
  rows      : every trading day of the week EXCEPT the week's first (the level must already
              exist), 18:00 NY roll, stub days (<= 600 M1 bars) skipped.
  level     : the week's opening price = open of the week's first M1 bar (Sunday 18:00 NY
              futures-style open; the 18:00 anchor is corpus canon for the daily candle).
  observed  : the weekly open is touched during that trading day (horizon = the day's own
              M1-bar count, trading time).
  null      : a level at the SAME signed distance from price, same bar count, at matched
              random moments (+/-30 days) -- the README rate example's geometry match.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd

if __name__ == "__main__":
    mkt = cl.get_market()
    d = cl.bars("1D")
    w = cl.bars("1W")
    ws = pd.DatetimeIndex(w.index)
    ds = pd.DatetimeIndex(d.index)
    j = np.searchsorted(ws.asi8, ds.asi8, side="right") - 1
    ok = (j >= 0) & (d["n_m1"].to_numpy() > 600)
    jj = np.clip(j, 0, None)
    first_of_week = ds == ws[jj]
    keep = ok & ~first_of_week
    d = d[keep]
    jj = jj[keep]
    t = pd.DatetimeIndex(d.index)
    avail = ws[jj]
    wo = w["open"].to_numpy(float)[jj]
    nb = d["n_m1"].to_numpy()
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = wo - px
    side_up = dist >= 0
    obs = np.full(len(t), np.nan)
    for up, sd in ((True, "above"), (False, "below")):
        i = np.where(side_up == up)[0]
        obs[i] = cl.touch(t[i], wo[i], sd, horizon_bars=nb[i])["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        for up, sd in ((True, "above"), (False, "below")):
            i = np.where((side_up == up) & ~tk.isna())[0]
            p = mkt.o[np.minimum(mkt.pos_at_or_after(tk[i]), len(mkt.o) - 1)]
            out[i] = cl.touch(tk[i], p + dist[i], sd, horizon_bars=nb[i])["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=avail, null_fn=null_fn, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": ["rows: each trading day (18:00 NY roll) except the week's first, stub days (<=600 M1 bars) skipped",
                    "level: the week's opening price (open of the week's first M1 bar, Sunday 18:00 NY)",
                    "hit: an M1 bar trades to the weekly open during that trading day (horizon = its M1-bar count)",
                    "null: same signed distance from price, same bar count, matched random moments +/-30 days (5 reps)"],
          "params": {"week_open": "Sunday 18:00 NY first M1 open", "horizon": "the trading day, in M1 bars",
                     "min_day_bars": 600, "day_open_hour": 18}}
    src = {"week_open": "declared-before-run: concept ambiguity (Sunday 18:00 vs Monday); 18:00 is corpus canon for the daily open (method_spec §1.4)",
           "horizon": "corpus: wrIZ7CAuFCc 'reacted along that level all throughout the week' read day by day (midnight dividers); declared-before-run: one trading day",
           "min_day_bars": "declared-before-run: README rate example's stub-day filter",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    out = cl.write_result("weekly-open-as-fair-value", None, res, operationalization=op,
                          params_source=src, script=__file__,
                          no_detector="pure level rule: the week's opening price from bars('1W') (known at the week's first bar), asked at each later day's 18:00 start; no detector",
                          notes="Magnet reading of 'fair value'. The 'reaction at the level' reading is not separately tested (concept not contested; no reaction size given). Script re-run once only because write_result was passed an invalid kwarg; test settings unchanged (same seed, identical numbers).")
    print(out)
