"""risk_own_01b / average-daily-range-targeting (underspecified).

reading a (the concept's name — target ceiling): gate_test on the 15m rung-0 CISD
  book. Kept = the 2R target lies INSIDE the day's remaining expansion budget
  (long: target <= running day low + expected range; short: target >= running day
  high - expected range). Expected range = median H-L of the expansion days among
  the last 20 real days ("Read typical expansion candle size off recent daily
  candles"). Claim +: targets inside the budget do better than ones that "require
  an atypically large day".
reading b (the stated corollary): rate_test. After a very large range day
  (range > 1.5 x ADR20 of the prior days), is the NEXT day's range below ADR20
  more often than on a matched random day (+/-30 days)? Claim +.
Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF = "15min"
LOOKBACK = 20
OPP_CUT = 1.0
MIN_N_M1 = 600
BIG = 1.5


def detect_a(m1):
    ev, _, _ = cisd_book(m1, TF)
    ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr", "confirm_close"]].copy()
    if ev.empty:
        return ev.assign(inside_budget=pd.Series(dtype=bool))
    run = cl.running_hilo(ev["decision_time"], "1D", m1=m1)
    ref = asof_ref(daily_ref(m1, LOOKBACK, MIN_N_M1, OPP_CUT), ev["decision_time"])
    exb = ref["exp_band"].to_numpy(float)
    hi, lo = run["high"].to_numpy(), run["low"].to_numpy()
    ok = np.isfinite(hi) & np.isfinite(lo) & np.isfinite(exb)
    ev = ev[ok].reset_index(drop=True)
    hi, lo, exb = hi[ok], lo[ok], exb[ok]
    s = ev["direction"].to_numpy()
    c = ev["confirm_close"].to_numpy()
    tgt_est = c + s * 2.0 * np.abs(c - ev["stop_px"].to_numpy())
    ceiling = np.where(s > 0, lo + exb, hi - exb)
    ev["exp_band"] = exb
    ev["target_est"] = tgt_est
    ev["ceiling"] = ceiling
    ev["inside_budget"] = np.where(s > 0, tgt_est <= ceiling, tgt_est >= ceiling)
    return ev


def detect_b(m1):
    ref = daily_ref(m1, LOOKBACK, MIN_N_M1, OPP_CUT).reset_index(drop=True)
    adr_prev = ref["adr"].shift(1).to_numpy()
    big = ref["range"].to_numpy() > BIG * adr_prev
    t = pd.DatetimeIndex(ref["close_time"])
    out = pd.DataFrame({"decision_time": t[big], "available_at": t[big],
                        "range": ref["range"].to_numpy()[big], "adr_prev": adr_prev[big]})
    return out.reset_index(drop=True)


def run_a():
    ev = cl.cache_frame(f"adrt_gate_{TF}_lb{LOOKBACK}_opp{OPP_CUT}", lambda: detect_a(cl.load_m1()))
    print(len(ev), ev["inside_budget"].mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="60D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "inside_budget", mask_available_at="decision_time",
                       max_hold=HOLD[TF], claim="+")
    show(res)
    params = {"baseline_tf": TF, **BASE_PARAMS, "max_hold": HOLD[TF], "adr_lookback_days": LOOKBACK,
              "expansion_cut_opp_over_body": OPP_CUT, "stub_day_min_n_m1": MIN_N_M1,
              "budget_anchor": "running trading-day low (long) / high (short) from M1 closed by decision",
              "target_estimate": "confirm close +/- 2 x |confirm close - protected swing|",
              "grid4h": "n/a"}
    src = {"baseline_tf": "phase3: primary stack entry TF (README gate example)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "adr_lookback_days": "corpus: X4XSsv5CNqg variants 'at least the current month visible' -> 20 trading days (declared-before-run)",
           "expansion_cut_opp_over_body": "threshold_fits: small wick / expansion candle opposing_run/|body| <= 1.0 (grade A)",
           "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6)",
           "budget_anchor": "corpus: bMkRomKEunU/wM1s7UivQ08 'subtracts what has already been delivered' (concept definition); declared-before-run: measured from the day's extreme",
           "target_estimate": "declared-before-run: entry unknown at decision, confirm close stands in",
           "grid4h": "declared-before-run: no 4h bars used"}
    op = {"rules": ["baseline: 15m rung-0 CISD book (series_open, 2/2, max_wait 3, protected-swing stop, 2R, hold 150min)",
                    "expected range = median H-L of expansion days (opp_run/|body|<=1.0) among last 20 completed real days",
                    "kept: 2R target inside [running day low/high +/- expected range]; complement: target needs an atypically large day",
                    "claim +: kept book beats the complement (control-adjusted)"],
          "params": params}
    p = cl.write_result("average-daily-range-targeting", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="the concept has no lookback/averaging; the 20-day expansion median is the declared reading.")
    print("wrote", p)


def run_b():
    m1 = cl.load_m1()
    ref = daily_ref(m1, LOOKBACK, MIN_N_M1, OPP_CUT).reset_index(drop=True)
    ev = detect_b(m1)
    probe = cl.probe_lookahead(detect_b, ev, lookback="60D")
    print("probe", probe.get("passed"), "n big days", len(ev))
    ct = cl.data.utc_ns(pd.DatetimeIndex(ref["close_time"]))
    rng = ref["range"].to_numpy()
    adr_prev = ref["adr"].shift(1).to_numpy()
    nxt = np.append(rng[1:], np.nan)
    outcome = np.where(np.isfinite(nxt) & np.isfinite(adr_prev), (nxt < adr_prev).astype(float), np.nan)
    pos = np.searchsorted(ct, cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])))
    obs = outcome[pos]
    t = pd.DatetimeIndex(ev["decision_time"])
    grid = pd.DatetimeIndex(ref["close_time"][np.isfinite(outcome)])
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED,
                         grid_times=grid)

    def null_fn(rng_, k):
        out = np.full(len(t), np.nan)
        tk = rt[:, k]
        ok = ~np.isnat(tk)
        pk = np.searchsorted(ct, tk[ok].astype("datetime64[ns]").astype(np.int64))
        out[ok] = outcome[pk]
        return out

    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="+")
    show(res)
    op = {"rules": ["completed real trading days (18:00 NY roll, n_m1>=600)",
                    f"big day: range > {BIG} x ADR20 of the 20 real days before it",
                    "outcome: next real day's range < that ADR20",
                    "null: same outcome on matched random real days within +/-30 days (daily close grid)",
                    "claim +: next-day range after a big day falls below ADR more often than on a random day"],
          "params": {"big_mult": BIG, "adr_lookback_days": LOOKBACK, "stub_day_min_n_m1": MIN_N_M1,
                     "day_roll": "18:00 NY"}}
    src = {"big_mult": "declared-before-run: the concept's measurable 'next-day range conditional on a >1.5x ADR day' (corpus example ~1,000 vs 700-800 on YM)",
           "adr_lookback_days": "corpus: X4XSsv5CNqg variants 'current month visible' -> 20 trading days (declared-before-run)",
           "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6)",
           "day_roll": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result("average-daily-range-targeting", "b", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="corollary 'after a very large range day expect a smaller range'; volatility clustering is the obvious counter-hypothesis.")
    print("wrote", p)


if __name__ == "__main__":
    run_a()
    run_b()
