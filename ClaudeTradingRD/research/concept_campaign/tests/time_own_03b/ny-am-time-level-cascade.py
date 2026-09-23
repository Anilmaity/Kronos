"""ny-am-time-level-cascade (TTrades own voice, shorts_03 B_7pMkbHyC4). Declared before any run.

The cascade: with a bias held into New York, 'if 8:30 makes an opposing run, 9:30 can
expand'; 'if 8:30 fails to make an opposing run, 9:30 makes the opposing run and 10:00
expands'. One level manipulates, the next expands. Tested as a rate_test (a timing
prediction), the concept's own measurable: 'conditional probability that 9:30 expands
given an 8:30 opposing run, versus the unconditional 9:30 expansion rate'.

Operationalisation (bullish shown, bearish mirrored):
  time levels   = 30m candles opening 08:30, 09:30, 10:00 NY (htf list has 30m; DST-aware NY)
  bias          = direction of the prior trading day's candle (18:00 roll; close vs open);
                  doji days skipped. (Declared: the concept only says 'a bias is held'.)
  opposing run  = open -> extreme AGAINST the bias; a level 'makes an opposing run' when
                  opposing_run / |close-open| > 1.0 (threshold_fits: large wick, grade A)
  expands       = candle closes in the bias direction with opposing_run/|close-open| <= 1.0
                  (threshold_fits: small wick / expansion candle, grade A)
  branch 1      : 8:30 made an opposing run -> predict 9:30 expands (decided 09:00 NY)
  branch 2      : 8:30 did not, 9:30 did  -> predict 10:00 expands (decided 10:00 NY)
  observed      = the predicted slot expands in the bias direction
  null          = the SAME slot's expansion rate in the SAME direction on matched random
                  trading days within +/-30 days (unconditional rate), seeded rng.
  London-set-extreme branching is hindsight in the source and is not gated; both branches
  share the one-manipulates-next-expands structure being tested.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd

CUT = 1.0


def slots(m1):
    b = cl.build_bars(m1, "30min")
    mod = cl.ny_minute_of_day(b.index)
    td = pd.DatetimeIndex(cl.trading_day(b.index))
    td = (td.tz_localize(None) if td.tz is not None else td).normalize()
    out = {}
    for name, m in (("s0830", 510), ("s0930", 570), ("s1000", 600)):
        sel = mod == m
        s = b[sel].copy()
        s["tday"] = td[sel]
        s = s[~s["tday"].duplicated()]
        out[name] = s.set_index("tday")
    return out


def orun(c, d):
    """opposing run and body in direction d (+1 bull / -1 bear)."""
    o, h, l, cl_ = c["open"].to_numpy(), c["high"].to_numpy(), c["low"].to_numpy(), c["close"].to_numpy()
    run = np.where(d > 0, o - l, h - o)
    body = (cl_ - o) * d
    return run, body


def made_run(c, d):
    run, body = orun(c, d)
    return run > CUT * np.abs(body)


def expands(c, d):
    run, body = orun(c, d)
    return (body > 0) & (run <= CUT * body)


def detect(m1):
    S = slots(m1)
    a = S["s0830"]
    t0 = pd.DatetimeIndex(a["close_time"])
    pr = cl.prior_hilo(t0, "1D", m1=m1)
    d = np.sign(pr["close"].to_numpy() - pr["open"].to_numpy())
    ok = np.isfinite(d) & (d != 0)
    d = np.where(ok, d, 1.0)
    r830 = made_run(a, d)
    br1 = ok & r830
    # branch 2 needs the 9:30 candle (closed at its own decision time); never the 10:00 one
    days2 = a.index[ok & ~r830].intersection(S["s0930"].index)
    b9 = S["s0930"].loc[days2]
    d2 = pd.Series(d, index=a.index).loc[days2].to_numpy()
    br2 = made_run(b9, d2)
    rows = pd.DataFrame({
        "tday": np.concatenate([a.index[br1], days2[br2]]),
        "decision_time": np.concatenate([t0[br1], pd.DatetimeIndex(b9["close_time"])[br2]]),
        "direction": np.concatenate([d[br1], d2[br2]]).astype(int),
        "slot": ["s0930"] * int(br1.sum()) + ["s1000"] * int(br2.sum()),
    })
    rows["decision_time"] = pd.DatetimeIndex(rows["decision_time"]).tz_convert("UTC") \
        if pd.DatetimeIndex(rows["decision_time"]).tz is not None else pd.DatetimeIndex(rows["decision_time"]).tz_localize("UTC")
    rows["available_at"] = rows["decision_time"]
    return rows.sort_values("decision_time").reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    pred = cl.cache_frame("t03b_cascade_v1", lambda: detect(cl.load_m1()))
    print(len(pred), pred["slot"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, pred, lookback="20D", ignore_cols=())
    S = slots(m1)
    D = pred["direction"].to_numpy()
    obs = np.full(len(pred), np.nan)
    for sl in ("s0930", "s1000"):
        i = np.where(pred["slot"].to_numpy() == sl)[0]
        c = S[sl].reindex(pd.DatetimeIndex(pred["tday"].iloc[i]))
        good = c["open"].notna().to_numpy()
        e = expands(c, D[i]).astype(float)
        e[~good] = np.nan
        obs[i] = e
    # null: same slot, same direction, random trading days within +/-30 calendar days
    exp_by = {}
    for sl in ("s0930", "s1000"):
        c = S[sl]
        exp_by[sl] = (c.index.to_numpy(), expands(c, np.ones(len(c))), expands(c, -np.ones(len(c))))
    tdays = pd.DatetimeIndex(pred["tday"]).to_numpy()

    def null_fn(rng, k):
        out = np.full(len(pred), np.nan)
        for sl in ("s0930", "s1000"):
            idx, eu, ed = exp_by[sl]
            i = np.where(pred["slot"].to_numpy() == sl)[0]
            lo = np.searchsorted(idx, tdays[i] - np.timedelta64(30, "D"))
            hi = np.searchsorted(idx, tdays[i] + np.timedelta64(30, "D"), side="right")
            j = lo + np.floor(rng.random(len(i)) * (hi - lo)).astype(int)
            j = np.clip(j, 0, len(idx) - 1)
            same = idx[j] == tdays[i]          # redraw once if we picked the event day itself
            j2 = lo + np.floor(rng.random(len(i)) * (hi - lo)).astype(int)
            j = np.where(same, np.clip(j2, 0, len(idx) - 1), j)
            out[i] = np.where(D[i] > 0, eu[j], ed[j]).astype(float)
        return out

    res = cl.rate_test(obs, pred["decision_time"], available_at=pred["available_at"],
                       null_fn=null_fn, predictors=pred, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": ["time levels = 30m candles opening 08:30, 09:30, 10:00 New York (DST-aware), 18:00 trading-day roll",
                    "bias = prior trading day's candle direction (close vs open), doji skipped",
                    "opposing run = open to extreme against the bias; 'made' when opposing_run/|body| > 1.0",
                    "expansion = candle closes with the bias and opposing_run/|body| <= 1.0",
                    "branch 1: 8:30 made an opposing run -> predict 9:30 expands (decided at 09:00 NY)",
                    "branch 2: 8:30 did not, 9:30 did -> predict 10:00 expands (decided at 10:00 NY)",
                    "null: same slot, same direction, expansion rate on random trading days within +/-30 days"],
          "params": {"slot_tf": "30min", "bias_rule": "prior-day candle direction", "run_cut": CUT,
                     "expansion_cut": CUT, "null_window_days": 30, "day_open_hour": 18}}
    src = {"slot_tf": "corpus: concept timeframes htf 1H/30m; B_7pMkbHyC4 '8:30 and 9:30 are the most important time levels'",
           "bias_rule": "declared-before-run: concept precondition 'a directional bias is already held' gives no rule; method_spec §2.4 previous-candle bias",
           "run_cut": "threshold_fits: large wick / reversal candle opposing_run/|close-open| > 1.0 (grade A)",
           "expansion_cut": "threshold_fits: small wick / expansion candle opposing_run/|close-open| <= 1.0 (grade A)",
           "null_window_days": "declared-before-run: matches the locked +/-30 day control window",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    out = cl.write_result("ny-am-time-level-cascade", None, res, operationalization=op,
                          params_source=src, script=__file__, probe=probe,
                          notes="Both cascade branches pooled (one-manipulates-next-expands). London-set-extreme precondition not gated (hindsight in the source). Null is the unconditional same-slot same-direction expansion rate, the concept's own stated comparison.")
    print(out)
