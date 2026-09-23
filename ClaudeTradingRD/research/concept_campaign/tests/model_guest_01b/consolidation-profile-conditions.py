"""consolidation-profile-conditions (guest: Jokerszn, JABOO4LYNjQ).

Claim: any of three conditions at a daily close makes a CONSOLIDATION profile the
expectation for the next session. rate_test: P(next day is consolidation | any
condition fired) vs a regime-matched base rate (random other day within +/-30d).

Parameters declared before the first run (the corpus gives no numbers):
  consolidation day   |close - open| <= 0.20 x ADR20   ("opens and closes at almost
                       the same price", ADR-normalised per README trap 6)
  cond1 HTF level     the day is the FIRST day of its week to trade through the prior
                       completed week's high or low
  cond2 overextended  last 3 daily candles closed the same direction, OR the last two
                       daily ranges each >= 1.5 x the ADR20 before them
  cond3 range EQ      close within 0.40-0.60 of the dealing range between the most
                       recent confirmed daily 2/2 swing high and swing low
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, daily, np, pd, regime_null_fn, swings_confirmed  # noqa: E402

CID = "consolidation-profile-conditions"
CONS_BODY_ADR = 0.20
OVEREXT_MULT = 1.5
EQ_BAND = 0.10


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "cond_htf", "cond_overext", "cond_eq"]
    d = daily(m1)
    if len(d) < 30:
        return pd.DataFrame(columns=cols)
    ct = pd.DatetimeIndex(d["close_time"])
    # cond1: first day of the week to trade through the prior completed week's H/L
    w = cl.build_bars(m1, "1W")
    pw = cl.asof(w, pd.DatetimeIndex(d["first_m1"]))          # week closed before today opened
    pwh, pwl = pw["high"].to_numpy(), pw["low"].to_numpy()
    wk = d["wk"].to_numpy()
    prev_hi_wk = d.groupby("wk")["high"].transform(lambda s: s.shift(1).cummax()).to_numpy()
    prev_lo_wk = d.groupby("wk")["low"].transform(lambda s: s.shift(1).cummin()).to_numpy()
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    took_h = (h > pwh) & ~(np.nan_to_num(prev_hi_wk, nan=-np.inf) > pwh)
    took_l = (l < pwl) & ~(np.nan_to_num(prev_lo_wk, nan=np.inf) < pwl)
    cond_htf = (took_h | took_l) & ~np.isnan(pwh)
    # cond2: overextension
    sgn = np.sign(d["close"].to_numpy() - d["open"].to_numpy())
    s = pd.Series(sgn)
    three = ((s == s.shift(1)) & (s == s.shift(2)) & (s != 0)).to_numpy()
    rng = d["rng"].to_numpy()
    adr_before = pd.Series(rng).rolling(20, min_periods=20).mean().shift(2).to_numpy()
    big2 = (rng >= OVEREXT_MULT * adr_before) & (np.roll(rng, 1) >= OVEREXT_MULT * adr_before)
    big2[:1] = False
    cond_over = three | np.nan_to_num(big2, nan=0).astype(bool)
    # cond3: close at the EQ of the dealing range (latest confirmed swing H and L)
    sw = swings_confirmed(d)
    conf = sw["conf"]
    sh_t = conf.where(sw["sh"]).dropna()
    sl_t = conf.where(sw["sl"]).dropna()
    shv = sw.loc[sh_t.index, "high"].to_numpy()
    slv = sw.loc[sl_t.index, "low"].to_numpy()
    sh_ns = pd.DatetimeIndex(sh_t).as_unit("ns").asi8
    sl_ns = pd.DatetimeIndex(sl_t).as_unit("ns").asi8
    o_sh, o_sl = np.argsort(sh_ns, kind="stable"), np.argsort(sl_ns, kind="stable")
    tn = ct.as_unit("ns").asi8
    ph = np.searchsorted(sh_ns[o_sh], tn, side="right") - 1
    pl = np.searchsorted(sl_ns[o_sl], tn, side="right") - 1
    H = np.where(ph >= 0, shv[o_sh][np.clip(ph, 0, None)], np.nan) if len(shv) else np.full(len(d), np.nan)
    L = np.where(pl >= 0, slv[o_sl][np.clip(pl, 0, None)], np.nan) if len(slv) else np.full(len(d), np.nan)
    width = H - L
    pos = (d["close"].to_numpy() - L) / np.where(width > 0, width, np.nan)
    cond_eq = np.nan_to_num(np.abs(pos - 0.5) <= EQ_BAND, nan=0).astype(bool) & (width > 0)
    anyc = cond_htf | cond_over | cond_eq
    ok = anyc & ~np.isnan(d["adr"].to_numpy())
    out = pd.DataFrame({"decision_time": ct[ok], "available_at": ct[ok],
                        "cond_htf": cond_htf[ok], "cond_overext": cond_over[ok],
                        "cond_eq": cond_eq[ok]})
    return out.reset_index(drop=True)


def outcomes(m1):
    d = daily(m1)
    body = (d["close"] - d["open"]).abs().to_numpy()
    cons = (body <= CONS_BODY_ADR * d["adr"].shift(1).to_numpy()).astype(float)
    cons[np.isnan(d["adr"].shift(1).to_numpy())] = np.nan
    # outcome for a decision at day i's close = consolidation of the NEXT day (i+1)
    y_next = np.append(cons[1:], np.nan)
    return pd.DatetimeIndex(d["close_time"]), y_next


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="120D")
    t_all, y_all = outcomes(m1)
    t = pd.DatetimeIndex(ev["decision_time"])
    pos = np.searchsorted(t_all.as_unit("ns").asi8, t.as_unit("ns").asi8)
    obs = y_all[pos]
    null_fn = regime_null_fn(t, t_all, y_all)
    print("events", len(ev), "fire rates", ev[["cond_htf", "cond_overext", "cond_eq"]].mean().round(3).to_dict(),
          "base cons rate", np.nanmean(y_all))
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "decision at each completed daily close (18:00 NY trading day; stub days < 600 M1 bars dropped)",
        "event if ANY of: (1) the day is the first of its week to trade through the prior completed week's high or low;"
        " (2) last 3 daily candles closed the same direction, or the last two daily ranges each >= 1.5x the prior ADR20;"
        " (3) close within 0.40-0.60 of the dealing range spanned by the latest confirmed daily 2/2 swing high and swing low",
        "outcome: the NEXT trading day is a consolidation profile, |close-open| <= 0.20 x ADR20 (ADR known at its open)",
        "null: the same outcome on a random other trading day within +/-30 days (regime-matched base rate)"],
        "params": {"cons_body_adr": CONS_BODY_ADR, "adr_n": 20, "overext_mult": OVEREXT_MULT,
                   "three_closes": 3, "eq_band": EQ_BAND, "swing": "2/2 daily", "htf_level": "prior week H/L",
                   "null_window_days": 30, "stub_min_m1": 600, "day_open_hour": 18}}
    src = {"cons_body_adr": "declared-before-run: 'opens and closes at almost the same price' (JABOO4LYNjQ) unquantified; 0.2 ADR",
           "adr_n": "declared-before-run: 20-day average range as the 'average daily expansion'",
           "overext_mult": "threshold_fits: displacement magnitude r=1.5 (range vs prior range) reused for 'large relative to average'",
           "three_closes": "corpus: JABOO4LYNjQ 'three or more of the last daily candles closed in the same direction'",
           "eq_band": "declared-before-run: 'at the 0.5 of the daily dealing range' as the middle fifth",
           "swing": "declared-before-run: 2/2 fractal swings, as phase-3 locked config",
           "htf_level": "declared-before-run: 'taken out a HTF old high or low' read as the prior week's H/L",
           "null_window_days": "phase3: +/-30 day regime-matched control window",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Union of the three stated triggers; per-trigger firing rates "
                        + str(ev[["cond_htf", "cond_overext", "cond_eq"]].mean().round(3).to_dict()))
    print("wrote", p)
