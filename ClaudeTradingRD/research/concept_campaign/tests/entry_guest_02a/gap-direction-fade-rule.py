"""gap-direction-fade-rule — Alex's Options: fade a session-open gap back into the previous range,
UNLESS the gap takes out a higher-timeframe extreme (then the gap is continuation).

Test: rate_test, level-prediction form.
  session open = the first M1 bar of each NY trading day (18:00 NY reopen after the daily halt,
  incl. the Sunday weekly reopen). gap = that open - the previous trading day's close.
  decision t = close of the first M1 bar of the day (the open is then known); rows where the
  first minute already traded back to the previous close are dropped (decided at t).
  hit = price trades back to the previous close (gap fill = back into the previous range)
  within the next 60 M1 bars.
  HTF-through = the gap itself crosses the prior day's, week's or month's extreme in its
  direction (prev close <= high < open for a gap up; mirrored for a gap down).
  null = at matched random moments (+/-30 days, same NY time of day +/-30 min, i.e. other
  sessions' reopen minutes), a level at the SAME signed distance from price, same side,
  same 60-bar horizon.
Reading a: gaps NOT through an HTF extreme; claim '+': they fill more often than the null.
Reading b: gaps THROUGH an HTF extreme; claim '-': they fill less often than the null.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "gap-direction-fade-rule"
HORIZON = 60
TOD_TOL = 30
MIN_NM1 = 600


def build():
    mkt = cl.get_market()
    d = cl.bars("1D")
    ok = (d["n_m1"].to_numpy() > MIN_NM1)
    prev_ok = np.r_[False, ok[:-1]]
    prev_close = np.r_[np.nan, d["close"].to_numpy()[:-1]]
    sel = ok & prev_ok
    dd = d[sel]
    pc = prev_close[sel]
    op = dd["open"].to_numpy()
    t = pd.DatetimeIndex(dd["first_m1"]).tz_convert("UTC") + pd.Timedelta("1min")
    av = t
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    gap = op - pc
    up = gap > 0
    dn = gap < 0
    unfilled = (up & (px > pc)) | (dn & (px < pc))
    pdh = cl.prior_hilo(t, "1D"); pwh = cl.prior_hilo(t, "1W"); pmh = cl.prior_hilo(t, "1M")
    through_up = np.zeros(len(op), bool); through_dn = np.zeros(len(op), bool)
    for ph in (pdh, pwh, pmh):
        H, L = ph["high"].to_numpy(), ph["low"].to_numpy()
        through_up |= (pc <= H) & (op > H)          # the GAP itself takes out the level
        through_dn |= (pc >= L) & (op < L)
    through = (up & through_up) | (dn & through_dn)
    keep = (up | dn) & unfilled
    return pd.DataFrame({"decision_time": t[keep], "available_at": av[keep], "prev_close": pc[keep],
                         "px": px[keep], "up": up[keep], "through": through[keep]})


def run(reading):
    f = build()
    f = f[~f["through"]] if reading == "a" else f[f["through"]]
    f = f.reset_index(drop=True)
    t = pd.DatetimeIndex(f["decision_time"])
    up = f["up"].to_numpy()
    lvl = f["prev_close"].to_numpy()
    dist = lvl - f["px"].to_numpy()               # negative for gap up (fill below)
    obs = np.full(len(f), np.nan)
    for m, side in ((up, "below"), (~up, "above")):
        if m.any():
            obs[m] = cl.touch(t[m], lvl[m], side, horizon_bars=HORIZON)["hit"].to_numpy()
    mkt = cl.get_market()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        okk = ~tk.isna()
        for m, side in ((up, "below"), (~up, "above")):
            mm = m & okk
            if mm.any():
                pk = mkt.o[mkt.pos_at_or_after(tk[mm])]
                out[mm] = cl.touch(tk[mm], pk + dist[mm], side, horizon_bars=HORIZON)["hit"].to_numpy()
        return out

    claim = "+" if reading == "a" else "-"
    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(f["available_at"]), null_fn=null_fn,
                       claim=claim)
    return f, res


if __name__ == "__main__":
    reading = sys.argv[1]
    if "--dry" in sys.argv:
        f = build(); print(len(f), f.through.sum(), f.up.mean()); raise SystemExit
    f, res = run(reading)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "session open = first M1 of each NY trading day (18:00 NY reopen, incl. Sunday); both that "
        "day and the previous one must have > 600 M1 bars",
        "gap = day open - previous day close; decide at the first M1 close; drop rows already "
        "back at the previous close by then",
        "hit = price touches the previous close within the next 60 M1 bars",
        "HTF-through = the gap itself crosses a prior day / week / month high (prev close <= H < open) or low",
        "null = same signed distance, same side, same 60 bars, at 5 matched random moments "
        "(+/-30 d, NY time of day +/-30 min)",
        "reading a = not-through gaps, claim '+'; reading b = through gaps, claim '-'"],
        "params": {"horizon_bars": HORIZON, "null_tod_tol_min": TOD_TOL, "min_day_m1": MIN_NM1,
                   "htf_levels": "prior 1D/1W/1M high-low", "gap_size_min": 0, "reading": reading}}
    src = {"horizon_bars": "corpus: 1XWyy6Q-_8Q 'every hour is like a new day when you're trading these gappers' (fill judged within the first hour)",
           "null_tod_tol_min": "declared-before-run: null moments held at the reopen time of day (vault trap 9 / 18:00 reopen volatility artefact in session_window_fit)",
           "min_day_m1": "declared-before-run: skip stub sessions (README trap 6), as in the harness rate example",
           "htf_levels": "corpus: 1XWyy6Q-_8Q previous month's low example; 'or other higher-timeframe' -> day/week/month",
           "gap_size_min": "corpus: concept yaml ambiguity 'No gap-size threshold' — rule tested as stated",
           "reading": "declared-before-run: the rule's two branches"}
    notes = ("Gold trades ~23h, so its session-open gaps are the 18:00 NY reopen after the daily halt "
             "and the weekend gap — mostly small (median ~2% of the 14-day mean range). The source "
             "trades single stocks. Timeframe-continuity confirmation is not modelled.")
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src, script=__file__,
                        notes=notes, no_detector=("pure level/clock rule: day open vs previous day close "
                                                  "from bars('1D') and prior_hilo 1D/1W/1M at the first "
                                                  "M1 close of the day"))
    print(p)
