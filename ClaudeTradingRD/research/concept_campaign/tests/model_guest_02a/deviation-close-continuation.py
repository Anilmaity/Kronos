"""deviation-close-continuation (guest: DexterLab, wWIHS_dxbEY; unit t_talks_02).

Claim: once a candle body closes beyond the 2.5 standard deviation of the previous 4H
candle's manipulation-leg projection, continuation to the 4th deviation is "high
probability".

Projection (shared with opening-location-vs-previous-range):
  working TF 4H on the forex grid (Dexter: forex 4H opens 01/05/09 NY = forex grid).
  previous 4H candle bearish (close < open): manipulation extreme H = its high (first
  M1 that printed it); the leg is the move INTO that high, from the lowest low between
  the candle open and H (L) up to H.  Fib 1 at H, 0 at L; deviation k sits at
  L - k*(H - L) (downward, the distribution direction). Bullish mirror.
  Legs smaller than 10% of the previous candle's range are skipped (no manipulation leg).
Readings (the unit leaves the close's timeframe open, YAML ambiguities):
  a  the first 15m candle inside the current 4H candle whose close is beyond -2.5,
     with -4 not yet touched in that 4H candle -> does price touch -4 within 240
     M1 bars (one 4H candle of trading time)?
  b  the current 4H candle itself closes beyond -2.5 without having touched -4 ->
     does price touch -4 within the next 240 M1 bars?
rate_test vs a matched null: the same signed distance from the entry price to the
target, the same 240-bar horizon, at matched random moments (+/-30 days, same NY
time-of-day +/-30 min).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MIN_LEG_FRAC = 0.10
HORIZON = 240
DEV_TRIG, DEV_TGT = 2.5, 4.0


def legs_4h(m1):
    """4H bars with the manipulation-leg projection of EACH bar (for use by the next)."""
    b = cl.build_bars(m1, "4h").reset_index()
    starts = cl.data.utc_ns(pd.DatetimeIndex(b["time"]))
    tn = cl.data.utc_ns(m1.index)
    bi = np.searchsorted(starts, tn, side="right") - 1
    hi = m1["high"].to_numpy(float)
    lo = m1["low"].to_numpy(float)
    ok = bi >= 0
    df = pd.DataFrame({"b": bi[ok], "h": hi[ok], "l": lo[ok]})
    # running extremes inside each bar, to find the low before the high (and vice versa)
    df["cmin"] = df.groupby("b")["l"].cummin()
    df["cmax"] = df.groupby("b")["h"].cummax()
    ih = df.groupby("b")["h"].idxmax()          # first M1 printing the bar's high
    il = df.groupby("b")["l"].idxmin()
    lo_before_hi = df.loc[ih.to_numpy(), "cmin"].to_numpy()
    hi_before_lo = df.loc[il.to_numpy(), "cmax"].to_numpy()
    leg = pd.DataFrame({"lo_before_hi": lo_before_hi, "hi_before_lo": hi_before_lo},
                       index=ih.index)
    b = b.join(leg)
    bear = b["close"] < b["open"]
    bull = b["close"] > b["open"]
    b["pdir"] = np.where(bull, 1, np.where(bear, -1, 0))
    # bearish: leg L->H, base L, projection down ; bullish: leg H'->L, base H', up
    b["leg"] = np.where(bear, b["high"] - b["lo_before_hi"],
                        np.where(bull, b["hi_before_lo"] - b["low"], np.nan))
    b["base"] = np.where(bear, b["lo_before_hi"], np.where(bull, b["hi_before_lo"], np.nan))
    rng = b["high"] - b["low"]
    b.loc[(b["leg"] < MIN_LEG_FRAC * rng) | (b["pdir"] == 0), "pdir"] = 0
    return b


def level(base, pdir, leg, k):
    # distribution direction is the previous candle's direction
    return base + pdir * k * leg


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "trigger_px", "target_px"]
    b = legs_4h(m1)
    prev = b.shift(1)
    cur = b.assign(pdir=prev["pdir"], leg=prev["leg"], base=prev["base"])
    q = cl.build_bars(m1, "15min").reset_index()
    s4 = cl.data.utc_ns(pd.DatetimeIndex(cur["time"]))
    qs = cl.data.utc_ns(pd.DatetimeIndex(q["time"]))
    j = np.searchsorted(s4, qs, side="right") - 1
    okj = j >= 1
    q = q[okj].copy()
    j = j[okj]
    c = cur.iloc[j].reset_index(drop=True)
    q = q.reset_index(drop=True)
    within = (cl.data.utc_ns(pd.DatetimeIndex(q["close_time"])) <=
              cl.data.utc_ns(pd.DatetimeIndex(c["close_time"])))
    q["j"] = j
    pdir = c["pdir"].fillna(0).to_numpy()
    q["pdir"] = pdir
    q["trig"] = level(c["base"].to_numpy(), pdir, c["leg"].to_numpy(), DEV_TRIG)
    q["tgt"] = level(c["base"].to_numpy(), pdir, c["leg"].to_numpy(), DEV_TGT)
    # running extreme of the current 4H candle up to and including this 15m bar
    q["runlo"] = q.groupby("j")["low"].cummin()
    q["runhi"] = q.groupby("j")["high"].cummax()
    beyond = np.where(pdir == -1, q["close"] < q["trig"], q["close"] > q["trig"])
    untouched = np.where(pdir == -1, q["runlo"] > q["tgt"], q["runhi"] < q["tgt"])
    sel = within & (pdir != 0) & beyond & untouched
    # only the FIRST 15m close beyond -2.5 in each 4H candle (and none earlier that
    # already touched -4: an earlier qualifying bar always comes first)
    first_beyond = pd.Series(np.where(within & (pdir != 0) & beyond, 1, 0)).groupby(
        q["j"]).cumsum().to_numpy()
    sel = sel & (first_beyond == 1)
    e = q[sel]
    if e.empty:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(e["close_time"]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": e["pdir"].astype(int).to_numpy(),
                         "trigger_px": e["trig"].to_numpy(float),
                         "target_px": e["tgt"].to_numpy(float)}).reset_index(drop=True)


def detect_b(m1):
    cols = ["decision_time", "available_at", "direction", "trigger_px", "target_px"]
    b = legs_4h(m1)
    prev = b.shift(1)
    pdir = prev["pdir"].fillna(0).to_numpy()
    trig = level(prev["base"].to_numpy(), pdir, prev["leg"].to_numpy(), DEV_TRIG)
    tgt = level(prev["base"].to_numpy(), pdir, prev["leg"].to_numpy(), DEV_TGT)
    beyond = np.where(pdir == -1, b["close"] < trig, b["close"] > trig)
    untouched = np.where(pdir == -1, b["low"] > tgt, b["high"] < tgt)
    sel = (pdir != 0) & beyond & untouched
    e = b[sel]
    if e.empty:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(e["close_time"]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": pdir[sel].astype(int),
                         "trigger_px": trig[sel], "target_px": tgt[sel]}).reset_index(drop=True)


def run_rate(ev):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    side = np.where(ev["direction"].to_numpy() == 1, "above", "below")
    tgt = ev["target_px"].to_numpy(float)
    pos = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)
    first_px = mkt.o[pos]
    dist = tgt - first_px
    obs = np.full(len(t), np.nan)
    for sd in ("above", "below"):
        m = side == sd
        obs[m] = cl.touch(t[m], tgt[m], sd, horizon_bars=HORIZON)["hit"].to_numpy()
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        for sd in ("above", "below"):
            m = (side == sd) & ~tk.isna()
            if not m.any():
                continue
            px = mkt.o[np.minimum(mkt.pos_at_or_after(tk[m]), len(mkt.o) - 1)]
            out[m] = cl.touch(tk[m], px + dist[m], sd, horizon_bars=HORIZON)["hit"].to_numpy()
        return out

    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null_fn=null_fn, predictors=ev)


COMMON_PARAMS = {"grid4h": "forex", "leg": "low-before-high to high (bearish) / "
                 "high-before-low to low (bullish) inside the previous 4H candle",
                 "min_leg_frac": MIN_LEG_FRAC, "trigger_dev": DEV_TRIG,
                 "target_dev": DEV_TGT, "horizon_m1_bars": HORIZON,
                 "null": "same signed distance, same bars, +/-30d, tod +/-30min"}
COMMON_SRC = {
    "grid4h": "corpus: wWIHS_dxbEY 'forex ... 1am, 5am, 9am NY' 4H opens = forex grid; "
              "session_window_fit: forex grid for gold",
    "leg": "corpus: wWIHS_dxbEY 'project standard deviations from the previous candle's "
           "manipulation leg'; method_spec §targets (AM Trades construction: the leg that "
           "took the high, anchored high to low)",
    "min_leg_frac": "declared-before-run: a leg under 10% of the candle's range is no "
                    "manipulation leg",
    "trigger_dev": "corpus: wWIHS_dxbEY 'body close beyond the 2.5 deviation'",
    "target_dev": "corpus: wWIHS_dxbEY 'continuation to the 4th deviation'",
    "horizon_m1_bars": "declared-before-run: one 4H candle of trading time",
    "null": "declared-before-run: geometry-matched touch null (README §2 rate example) "
            "with time-of-day held (README trap 9)"}


NOTES = {
    "a": ("Re-written once (deterministic re-run, identical result) only to attach this "
          "note. Post-verdict diagnostic, not a test: at the SAME decision moments, a "
          "target at the same distance in the OPPOSITE direction is touched within 240 "
          "bars 62.5% of the time vs 62.6% for the -4 target (n=2,823). The +2.8pp over "
          "the random-moment null is therefore post-displacement VOLATILITY (any level "
          "that far is reached more often after a strong 15m close), not directional "
          "continuation to the 4th deviation. Treat this EDGE as a null-design artefact."),
    "b": ""}
READINGS = sys.argv[1:] or ["a", "b"]

if __name__ == "__main__":
    for reading, fn, tfdesc in (("a", detect_a, "15m close inside the current 4H candle"),
                                ("b", detect_b, "the 4H candle's own close")):
        if reading not in READINGS:
            continue
        ev = cl.cache_frame(f"devclose_{reading}_v1", lambda fn=fn: fn(cl.load_m1()))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="10D")
        res = run_rate(ev)
        for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "verdict", "verdict_detail"):
            print(" ", k, res.get(k))
        op = {"rules": [
            "previous 4H candle's manipulation leg projected in its direction "
            "(deviation k at base + dir*k*leg)",
            f"trigger: {tfdesc} beyond the 2.5 deviation, 4th deviation not yet touched",
            "outcome: M1 touch of the 4th deviation within 240 M1 bars of the decision",
            "null: same distance from the entry price, same horizon, matched random "
            "moments"],
            "params": {**COMMON_PARAMS, "trigger_tf": "15min" if reading == "a" else "4h"}}
        src = {**COMMON_SRC, "trigger_tf": "corpus: wWIHS_dxbEY; the unit leaves the "
               "close's timeframe open (executing candle vs 4H) -> one reading each"}
        p = cl.write_result("deviation-close-continuation", reading, res,
                            operationalization=op, params_source=src, script=__file__,
                            probe=probe, notes=NOTES[reading])
        print(" ", p)
