"""reversal-signature (TTrades own voice, contested) — batch structure_own_02a.

"A reversal is when we have expansion met with expansion" (VD4xb9VfMHA), only at a
RELEVANT level — "focus on previous days highs and lows or previous week's highs and
lows" — cleanest as a V: the counter-leg closes over the series of opposing candles
(CISD). Execution: bias away from the swept extreme, stop beyond it.

Operationalisation (1H entry timeframe under the 1D/1W reference levels):
  expansion into the level : a 1h extreme (below its 2 prior lows and the lowest low of
                             the prior 20 bars; mirror for highs) that trades beyond the
                             previous trading day's low (PDL) or previous week's low (PWL)
  expansion away           : a 1h close through the OPEN of the first candle of the
                             opposing series that made the extreme (CISD), IMMEDIATELY =
                             within 3 candles of the extreme, no new extreme first
  trade                    : decide at that close, enter next M1 open away from the
                             extreme, stop = the extreme, 2R, 10h exit (phase-3 1h book)
Readings:
  a  primary (this unit): relevant level + immediate CISD, no SMT requirement
  b  variant definition: the same, AND an SMT with the correlate at the reversal point —
     XAG_USD (silver, the method's sanctioned gold correlate, method_spec §2.6) has NOT
     taken its own counterpart of the level gold took (its PDL / PWL) between the start
     of the extreme's trading day (week) and the closing candle. Events whose silver
     bars are missing are dropped (not evaluable), never passed.
Both are trade_tests (full entry/stop/target) vs the matched random-entry control.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import H1, _xag_raw, cl, cisd_speed, np, pd, summary  # noqa: E402

CID = "reversal-signature"
TF, POI_LB, MAX_K, RR, HOLD = "1h", 20, 3, 2.0, "10h"


def _week_key(td: pd.DatetimeIndex) -> pd.DatetimeIndex:
    sd = td + pd.Timedelta(days=1)
    return sd - pd.to_timedelta(sd.dayofweek, unit="D")


def detect_a(m1, keep_levels=False):
    b = cl.build_bars(m1, TF)
    ev = cisd_speed(b, poi_lookback=POI_LB, max_k=MAX_K)
    ct = pd.DatetimeIndex(b["close_time"].to_numpy())
    xt = ct[ev["pos"].to_numpy()]
    d = cl.prior_hilo(xt, "1D", m1=m1, min_coverage=0.5)
    w = cl.prior_hilo(xt, "1W", m1=m1)
    bull = ev["dir"].to_numpy() > 0
    x = ev["extreme"].to_numpy()
    took_d = np.where(bull, x < d["low"].to_numpy(), x > d["high"].to_numpy())
    took_w = np.where(bull, x < w["low"].to_numpy(), x > w["high"].to_numpy())
    rel = took_d | took_w
    j = ev["j"].to_numpy()
    out = pd.DataFrame({"decision_time": ct[j], "available_at": ct[j],
                        "direction": ev["dir"].to_numpy().astype(int),
                        "stop_px": x, "rr": RR, "took_pd": took_d, "took_pw": took_w})
    if keep_levels:
        out["x_start"] = b.index[ev["pos"].to_numpy()]
        out["j_start"] = b.index[j]
    return out[rel].reset_index(drop=True)


def detect_b(m1):
    ev = detect_a(m1, keep_levels=True)
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    s = _xag_raw()
    s = s[(s.index + H1 <= cutoff) & (s.index >= m1.index[0].floor("h"))]
    std = cl.trading_day(s.index)
    wk = _week_key(std)
    day_hi = s["high"].groupby(std).max()
    day_lo = s["low"].groupby(std).min()
    wk_hi = s["high"].groupby(wk).max()
    wk_lo = s["low"].groupby(wk).min()
    sn = s.index
    smt = np.zeros(len(ev), bool)
    ok = np.zeros(len(ev), bool)
    for i, r in enumerate(ev.itertuples()):
        if not ((sn == r.x_start).any() and (sn == r.j_start).any()):
            continue
        td = cl.trading_day(pd.DatetimeIndex([r.x_start]))[0]
        wkk = _week_key(pd.DatetimeIndex([td]))[0]
        dpos = day_hi.index.searchsorted(td) - 1
        wpos = wk_hi.index.searchsorted(wkk) - 1
        if dpos < 0 or wpos < 0:
            continue
        seg_d = s[(std == td) & (sn <= r.j_start)]
        seg_w = s[(wk == wkk) & (sn <= r.j_start)]
        held = []
        if r.took_pd:
            held.append(seg_d["low"].min() >= day_lo.iloc[dpos] if r.direction > 0
                        else seg_d["high"].max() <= day_hi.iloc[dpos])
        if r.took_pw:
            held.append(seg_w["low"].min() >= wk_lo.iloc[wpos] if r.direction > 0
                        else seg_w["high"].max() <= wk_hi.iloc[wpos])
        ok[i] = True
        smt[i] = any(held)
    ev = ev[ok & smt].drop(columns=["x_start", "j_start"])
    return ev.reset_index(drop=True)


def main():
    rules = [f"{TF} extreme = bar below its 2 prior lows and the lowest low of the prior "
             f"{POI_LB} bars (mirror for highs) that trades beyond the previous trading day's "
             "low/high (18:00 NY day, coverage >= 0.5) or the previous week's low/high",
             "expansion away = close beyond the OPEN of the first candle of the opposing "
             f"series into the extreme within {MAX_K} candles of the extreme, no new extreme first",
             f"decide at that close, enter next M1 open away from the extreme, stop = extreme, "
             f"{RR}R, exit after {HOLD}"]
    params = {"tf": TF, "poi_lookback": POI_LB, "max_k": MAX_K, "rr": RR, "max_hold": HOLD,
              "levels": "PDH/PDL (min_coverage 0.5) or PWH/PWL"}
    src = {"tf": "corpus yaml timeframes: htf 1D/4H, ltf 1H first",
           "poi_lookback": "phase3: lookback 20 knob",
           "max_k": "corpus: PQiRV0JMhIQ 'It only takes a couple candles. Now, I prefer 1 2 maybe three.' (immediately)",
           "rr": "phase3: 2R", "max_hold": "phase3: 1h book 10h exit",
           "levels": "corpus: VD4xb9VfMHA 'focus on previous days highs and lows or previous week's highs and lows'"}
    for reading, det, key, xr, xp, xs in (
            ("a", detect_a, "rs_a", [], {}, {}),
            ("b", detect_b, "rs_b",
             ["SMT: XAG_USD H1 has NOT traded beyond its own counterpart (previous trading "
              "day / week low for a bullish case) of a level gold took, from the start of the "
              "extreme's trading day (week) through the closing candle; events without silver "
              "bars at the extreme or closing hour are dropped"],
             {"correlate": "XAG_USD H1 (OANDA, m3_scalper/xag_h1_full.parquet)"},
             {"correlate": "method_spec: §2.6 SMT = one shared level, one asset beyond, the other not; silver is the method's sanctioned gold correlate (fetch_correlated.py)"})):
        ev = cl.cache_frame(f"revsig_{key}_{TF}_{POI_LB}_{MAX_K}", lambda d=det: d(cl.load_m1()))
        probe = cl.probe_lookahead(det, ev, lookback="30D")
        res = cl.trade_test(ev, max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res, operationalization={
            "rules": rules + xr, "params": {**params, **xp}},
            params_source={**src, **xs}, script=__file__, probe=probe,
            notes="'expansion' on either leg has no threshold in the corpus; the counter-leg "
                  "is operationalised as his CISD closure within 1-3 candles (the only "
                  "candle-count threshold for 'swift'). Consolidation fallback and the "
                  "half-wick condition are not modelled.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
