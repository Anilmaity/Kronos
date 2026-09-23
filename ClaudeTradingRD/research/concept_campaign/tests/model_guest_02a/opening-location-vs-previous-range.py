"""opening-location-vs-previous-range (guest: DexterLab, wWIHS_dxbEY; unit t_talks_02).

Claim: classify the developing 4H candle by where it OPENS inside the standard-deviation
projection of the previous 4H candle's manipulation leg.
  framework one  (reading a): open at the 1 / 1.5 deviation -> "unfinished business",
                  continuation to the 2 / 2.5 deviation is high probability.
  framework two  (reading b): open at the 2 / 2.5 deviation -> projection satisfied,
                  expect a retracement to equilibrium of the previous range.
Projection exactly as in deviation-close-continuation (same batch): forex 4H grid;
previous candle bearish -> leg from the lowest low before its high up to the high,
deviation k at L - k*leg (bullish mirror); legs < 10% of the candle's range skipped.
  open deviation d = dir * (open - base) / leg.
  a: d in [1.0, 1.5] -> outcome: touch of the -2 deviation within 240 M1 bars.
  b: d in [2.0, 2.5] -> outcome: touch of the previous candle's 50% (its EQ) within 240.
Decision at the close of the new candle's first M1 bar (its open is then known).
Null (declared before any run of this script): the SAME moment, the SAME distance and
horizon, in the OPPOSITE direction (mirror level). It holds time, regime and local
volatility fixed, so the statistic is the directional asymmetry the frameworks claim.
(The sibling concept's random-moment null was shown to be volatility-confounded.)
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MIN_LEG_FRAC = 0.10
HORIZON = 240
BANDS = {"a": (1.0, 1.5), "b": (2.0, 2.5)}


def legs_4h(m1):
    b = cl.build_bars(m1, "4h").reset_index()
    starts = cl.data.utc_ns(pd.DatetimeIndex(b["time"]))
    tn = cl.data.utc_ns(m1.index)
    bi = np.searchsorted(starts, tn, side="right") - 1
    ok = bi >= 0
    df = pd.DataFrame({"b": bi[ok], "h": m1["high"].to_numpy(float)[ok],
                       "l": m1["low"].to_numpy(float)[ok]})
    df["cmin"] = df.groupby("b")["l"].cummin()
    df["cmax"] = df.groupby("b")["h"].cummax()
    ih = df.groupby("b")["h"].idxmax()
    il = df.groupby("b")["l"].idxmin()
    leg = pd.DataFrame({"lo_before_hi": df.loc[ih.to_numpy(), "cmin"].to_numpy(),
                        "hi_before_lo": df.loc[il.to_numpy(), "cmax"].to_numpy()},
                       index=ih.index)
    b = b.join(leg)
    bear = b["close"] < b["open"]
    bull = b["close"] > b["open"]
    b["pdir"] = np.where(bull, 1, np.where(bear, -1, 0))
    b["leg"] = np.where(bear, b["high"] - b["lo_before_hi"],
                        np.where(bull, b["hi_before_lo"] - b["low"], np.nan))
    b["base"] = np.where(bear, b["lo_before_hi"], np.where(bull, b["hi_before_lo"], np.nan))
    rng = b["high"] - b["low"]
    b.loc[(b["leg"] < MIN_LEG_FRAC * rng) | (b["pdir"] == 0), "pdir"] = 0
    return b


def make_detect(reading):
    lo_d, hi_d = BANDS[reading]

    def detect(m1):
        cols = ["decision_time", "available_at", "direction", "open_dev", "target_px"]
        b = legs_4h(m1)
        prev = b.shift(1)
        pdir = prev["pdir"].fillna(0).to_numpy()
        leg = prev["leg"].to_numpy(float)
        base = prev["base"].to_numpy(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = pdir * (b["open"].to_numpy(float) - base) / leg
        sel = (pdir != 0) & (d >= lo_d) & (d <= hi_d)
        if reading == "a":
            tgt = base + pdir * 2.0 * leg
            direction = pdir                       # continuation
        else:
            tgt = (prev["high"].to_numpy(float) + prev["low"].to_numpy(float)) / 2.0
            direction = -pdir                      # retracement to EQ
        e = b[sel]
        if e.empty:
            return pd.DataFrame(columns=cols)
        dt = (pd.DatetimeIndex(e["first_m1"]) + pd.Timedelta(minutes=1)).tz_convert("UTC")
        return pd.DataFrame({"decision_time": dt, "available_at": dt,
                             "direction": direction[sel].astype(int),
                             "open_dev": d[sel], "target_px": tgt[sel]}).reset_index(drop=True)
    return detect


def run_rate(ev):
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    tgt = ev["target_px"].to_numpy(float)
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = tgt - px
    up = dist > 0
    obs = np.zeros(len(t))
    mir = np.zeros(len(t))
    for m, sd, osd in ((up, "above", "below"), (~up, "below", "above")):
        if m.any():
            obs[m] = cl.touch(t[m], tgt[m], sd, horizon_bars=HORIZON)["hit"].to_numpy()
            mir[m] = cl.touch(t[m], px[m] - dist[m], osd,
                              horizon_bars=HORIZON)["hit"].to_numpy()
    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null=mir, predictors=ev)


if __name__ == "__main__":
    for reading in sys.argv[1:] or ["a", "b"]:
        fn = make_detect(reading)
        ev = cl.cache_frame(f"openloc_{reading}_v1", lambda fn=fn: fn(cl.load_m1()))
        print(reading, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="10D")
        res = run_rate(ev)
        for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "verdict", "verdict_detail"):
            print(" ", k, res.get(k))
        if reading == "a":
            rules = ["new 4H candle opens between the 1.0 and 1.5 deviation of the previous "
                     "candle's manipulation-leg projection (framework one)",
                     "outcome: M1 touch of the 2.0 deviation within 240 M1 bars"]
        else:
            rules = ["new 4H candle opens between the 2.0 and 2.5 deviation (framework two)",
                     "outcome: M1 touch of the previous candle's 50% (EQ) within 240 M1 bars"]
        op = {"rules": ["forex 4H grid; leg = lowest low before the high -> high (bearish "
                        "prev candle; bullish mirror); deviation k at base + dir*k*leg"]
                       + rules + ["decision after the new candle's first M1 bar closes",
                                  "null: same moment, same distance and horizon, opposite "
                                  "direction (mirror level)"],
              "params": {"grid4h": "forex", "min_leg_frac": MIN_LEG_FRAC,
                         "open_band": list(BANDS[reading]),
                         "target": "2.0 dev" if reading == "a" else "prev candle 50%",
                         "horizon_m1_bars": HORIZON, "null": "same-moment mirror level"}}
        src = {"grid4h": "corpus: wWIHS_dxbEY 'forex ... 1am, 5am, 9am NY' 4H opens = forex "
                         "grid; session_window_fit: forex grid for gold",
               "min_leg_frac": "declared-before-run: a leg under 10% of the candle's range "
                               "is no manipulation leg",
               "open_band": "corpus: wWIHS_dxbEY 'opens at the 1 / 1.5 deviation' / 'at the "
                            "2 / 2.5 deviation' (declared-before-run: the closed band "
                            "between the two named levels)",
               "target": "corpus: wWIHS_dxbEY 'continuation to the 2 / 2.5' (first level "
                         "of the band) / 'retracement to equilibrium of the previous range'",
               "horizon_m1_bars": "declared-before-run: the developing 4H candle = 240 "
                                  "M1 bars of trading time",
               "null": "declared-before-run: same-moment mirror null holds volatility "
                       "(README trap 4)"}
        p = cl.write_result("opening-location-vs-previous-range", reading, res,
                            operationalization=op, params_source=src, script=__file__,
                            probe=probe)
        print(" ", p)
