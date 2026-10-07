"""average-daily-range (ttrades) — update_20261007 draft edu_03, rate_test. NEW claim only.

Prior readings a/b (risk_own_01b) gated a 15m CISD book on 'band already covered' (raw EDGE,
both refuted in verification: time of day not held fixed). Untouched. This reading tests the
new, explicit claim of 3OIq9HmckH8:
  ADR = total high-low range of N daily candles / N ('You get the total range divided by the
  total days'; TradingView 'Average Daily Range', 'Go ahead and turn it on to daily'), laid on
  the current day FROM THE EXTREME ALREADY MADE: 'that is kind of what could cap our expansion,
  and that is the range we will see price not really wanting to trade beyond'; 'If this is the
  high, where does our 115 lie?'.

Event rows: every NY hour close 19:00..16:00 inside the trading day (18:00 NY roll) at which the
running day range (M1 closed by the decision) is still < ADR. Two caps per row-time:
  up-cap = running low + ADR (side above), down-cap = running high - ADR (side below).
Hit  = price reaches the cap before the trading day closes (M1, horizon in M1 bars).
Null = matched random moments (reps 5, +/-30 d, same NY minute via tod_tol 30 on the :00 grid),
       same side, same M1-bar horizon, same distance from the next M1 open in LOCAL-VOLATILITY
       units (distance x vol_null / vol_event, vol = mean M1 high-low over the 240 M1 bars closed
       before the moment). Claim '-': caps are reached less often than equidistant levels.
Readings (N is never stated): u1007a N=14 (the TradingView ADR indicator's default length; he
changes only its timeframe), u1007b N=5 ('only three daily candles. Ideally, you use a few more').

Vault audit (KronosVault Backtest Methodology Traps + Concept Campaign 2026-09-23):
  trap 1 geometry      : null keeps side, horizon and distance-from-price (vol units); no cushion
  trap 2 resolution    : touch on M1
  trap 3 label=left    : decisions at hour CLOSE; running range from M1 closed by t; scan from
                         the first M1 bar starting at/after t
  trap 4 regime        : +/-30 d controls; ADR is the instrument's own recent range (relative)
  trap 5 units         : observed rate recomputed from raw M1 on a sample (independent loop)
  trap 6 power         : MDE printed/written; n_eff = trading days
  trap 7 never-eval    : ADR warm-up rows dropped (not passed); exact as-of join on completed
                         real days; zero-exposure rows (no M1 bar left in the day) set NaN
  trap 8 structure     : certified 2016+ only; no absolute-point threshold
  trap 9 in-progress   : ADR from COMPLETED days only (close_time <= t); symmetric probe
  lesson 3             : running range < ADR selects calm days -> null matches NY minute AND
                         local volatility, else quietness alone reads as 'the cap holds'
Not re-tested: 'once covered, stop seeking continuations' (prior a/b, daily-range-budget), and
volatility clustering (average-daily-range-targeting b).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                  # noqa: E402

CID = "average-daily-range"
MIN_N_M1 = 600
HOURS = range(1, 23)          # 19:00 .. 16:00 NY (hours after the 18:00 roll)
VOL_BARS = 240
TOD_TOL = 30
REPS, WIN_DAYS = 5, 30


def _detect(m1, n_days):
    d = cl.build_bars(m1, "1D")
    real = d[d["n_m1"] >= MIN_N_M1]
    adr = (real["high"] - real["low"]).rolling(n_days, min_periods=n_days).mean().to_numpy()
    rct = cl.data.utc_ns(pd.DatetimeIndex(real["close_time"]))
    start = pd.DatetimeIndex(d.index)
    close = pd.DatetimeIndex(d["close_time"])
    ev = pd.concat([pd.DataFrame({"decision_time": start + pd.Timedelta(hours=h),
                                  "day_close": close}) for h in HOURS], ignore_index=True)
    ev = ev[ev["decision_time"] < ev["day_close"]]     # no data-extent filter: it would read the future
    ev = ev.sort_values("decision_time").reset_index(drop=True)
    t = pd.DatetimeIndex(ev["decision_time"])
    pos = np.searchsorted(rct, cl.data.utc_ns(t), side="right") - 1   # completed real days only
    a = np.where(pos >= 0, adr[np.clip(pos, 0, None)], np.nan)
    run = cl.running_hilo(t, "1D", m1=m1)
    hi, lo = run["high"].to_numpy(float), run["low"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(hi) & np.isfinite(lo) & ((hi - lo) < a)
    ev = ev[ok].assign(adr=a[ok], run_hi=hi[ok], run_lo=lo[ok])
    up = ev.assign(side=1, cap=ev["run_lo"] + ev["adr"])
    dn = ev.assign(side=-1, cap=ev["run_hi"] - ev["adr"])
    out = pd.concat([up, dn], ignore_index=True).sort_values(["decision_time", "side"])
    out["available_at"] = out["decision_time"]
    return out.reset_index(drop=True)


def detect_a(m1):
    return _detect(m1, 14)


def detect_b(m1):
    return _detect(m1, 5)


def run(reading, detect, n_days, n_src):
    m1 = cl.load_m1()
    mkt = cl.get_market()
    ev = cl.cache_frame(f"adr_cap_u1007_{reading}_N{n_days}", lambda: detect(cl.load_m1()))
    print(reading, "rows", len(ev), "days", ev["decision_time"].dt.normalize().nunique())
    probe = cl.probe_lookahead(detect, ev, lookback="40D")
    print("probe", probe.get("passed"))

    t = pd.DatetimeIndex(ev["decision_time"])
    side = ev["side"].to_numpy()
    cap = ev["cap"].to_numpy()
    i0 = mkt.pos_at_or_after(t)
    nb = mkt.pos_at_or_after(pd.DatetimeIndex(ev["day_close"])) - i0      # M1 bars left today
    p0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = (cap - p0) * side                                              # > 0: cap beyond price
    cs = np.concatenate([[0.0], np.cumsum(mkt.h - mkt.l)])

    def lvol(times):
        p = mkt.pos_at_or_after(times)
        v = (cs[p] - cs[np.maximum(p - VOL_BARS, 0)]) / VOL_BARS
        return np.where(p >= VOL_BARS, v, np.nan)

    vol_e = lvol(t)

    def hits(times, px, rows, dd):
        out = np.full(len(rows), np.nan)
        for s, sd in ((1, "above"), (-1, "below")):
            m = (side[rows] == s) & np.isfinite(dd) & (nb[rows] > 0)
            if m.any():
                out[m] = cl.touch(times[m], px[m] + s * dd[m], sd,
                                  horizon_bars=nb[rows][m])["hit"].to_numpy()
        return out

    allr = np.arange(len(t))
    obs = hits(t, p0, allr, dist)
    rt = cl.sample_times(t, REPS, WIN_DAYS, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)
    vol_n = []

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = np.flatnonzero(~tk.isna())
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[ok])]
        vn = lvol(tk[ok])
        vol_n.append(np.nanmedian(vn))
        out[ok] = hits(tk[ok], px, ok, dist[ok] * vn / vol_e[ok])
        return out

    # trap 5: recompute the observed rate from raw M1 on a sample, independent of touch()
    rs = np.random.default_rng(7).choice(np.flatnonzero(np.isfinite(obs)), 400, replace=False)
    H, L = m1["high"].to_numpy(), m1["low"].to_numpy()
    raw = [float((H[i0[r]:i0[r] + nb[r]].max() >= cap[r]) if side[r] == 1
                 else (L[i0[r]:i0[r] + nb[r]].min() <= cap[r])) for r in rs]
    print("trap5 raw vs touch on 400 rows: agree", float(np.mean(np.array(raw) == obs[rs])))

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev, claim="-")
    print("dist median pts", float(np.median(dist)), "dist/vol median",
          float(np.nanmedian(dist / vol_e)), "vol event median", float(np.nanmedian(vol_e)),
          "vol null median", float(np.median(vol_n)), "nb median", float(np.median(nb)))
    for s in (1, -1):
        m = (side == s) & np.isfinite(obs)
        print(" side", s, "obs rate", float(obs[m].mean()))
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "mde_threshold", "halves", "dependence", "verdict", "verdict_detail"):
        print(" ", k, res.get(k))

    rules = [
        "trading day rolls 18:00 NY; decisions at every NY hour close 19:00..16:00 inside the day",
        f"ADR = mean(high - low) of the last {n_days} COMPLETED real trading days (n_m1 >= {MIN_N_M1}), as of the decision",
        "kept: running day range (M1 closed by the decision) < ADR, so both caps lie beyond the day's extremes",
        "caps projected from the day's extreme: up = running low + ADR (above), down = running high - ADR (below); one row each",
        "hit = price reaches the cap before the trading day closes (M1, horizon = M1 bars left in the day)",
        f"null = matched random moments (reps {REPS}, +/-{WIN_DAYS} d, same NY minute: tod_tol {TOD_TOL} on the :00 grid), same side, "
        f"same M1-bar horizon, same distance from the next M1 open scaled by local vol (mean M1 high-low over the {VOL_BARS} M1 bars closed before the moment)",
        "claim '-': the ADR projection caps the day - caps are reached less often than equidistant (vol-matched) levels",
    ]
    params = {"adr_lookback_days": n_days, "adr_average": "mean of H-L (sum / N)",
              "adr_days": "completed real days only", "stub_day_min_n_m1": MIN_N_M1,
              "day_roll": "18:00 NY", "decision_grid": "NY hour closes 19:00..16:00",
              "projection_anchor": "day's running extreme (opposite side)",
              "outcome_window": "decision -> trading-day close, M1 bars",
              "null_reps": REPS, "null_window_days": WIN_DAYS, "null_tod_tol_min": TOD_TOL,
              "null_vol_bars": VOL_BARS, "grid4h": "n/a"}
    src = {
        "adr_lookback_days": n_src,
        "adr_average": "corpus: 3OIq9HmckH8 'You get the total range divided by the total days'",
        "adr_days": "declared-before-run: non-repainting reading of the daily ADR indicator (trap 9: no in-progress daily bar)",
        "stub_day_min_n_m1": "declared-before-run: skip data-hole stub days (README trap 6), as prior readings",
        "day_roll": "session_window_fit: settled 18:00 NY daily roll",
        "decision_grid": "declared-before-run: the projection is re-read through the day ('how much further we could go'); every hour close",
        "projection_anchor": "corpus: 3OIq9HmckH8 'If this is the high, where does our 115 lie?'",
        "outcome_window": "corpus: 3OIq9HmckH8 'there's not too much range left in the day'",
        "null_reps": "method_spec: locked reps=5",
        "null_window_days": "method_spec: locked window_days=30",
        "null_tod_tol_min": "declared-before-run: README trap 9 / campaign lesson 3 (rate nulls must match time of day)",
        "null_vol_bars": "declared-before-run: campaign 2026-09-23 lesson 3 (rate nulls must match local volatility); running range < ADR selects calm days; 240 M1 bars = 4 trading hours, as sibling update_20261007 scripts",
        "grid4h": "declared-before-run: no 4h bars used",
    }
    notes = ("New claim only: explicit ADR formula/indicator projected from the day's extreme as a cap. "
             "Rows share the day's outcome (two caps x up to 22 hour closes); day-block CI, n_eff = days. "
             "Caveat: cap levels always lie beyond the day's running extreme, while the equidistant null "
             "level may lie inside its own day's range; extremes acting as resistance would favour the claim, "
             "as liquidity draws against it. Vol scaling uses a 4h trailing window; volatility persistence "
             "beyond it is not matched.")
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["u1007a", "u1007b"]
    if "u1007a" in which:
        run("u1007a", detect_a, 14,
            "corpus: 3OIq9HmckH8 'Go ahead and turn it on to daily' - only the timeframe is changed, "
            "so the TradingView 'Average Daily Range' default length 14 applies (declared-before-run)")
    if "u1007b" in which:
        run("u1007b", detect_b, 5,
            "corpus: 3OIq9HmckH8 'this is only three daily candles. Ideally, you use a few more' -> "
            "N=5 (one trading week; declared-before-run)")
