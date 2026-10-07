"""v-shape-reversal-speed (TTrades update 2026-10-07) — rate_test, wall-clock speed claim.

New claim (Hlwq1dRjBZo, NY Open Live Q&A): after the sweep and the reaction off the low, "if
price is going to expand, it's not going to wait 35 minutes, not 35, 20 minutes to go expand" —
no expansion ~20 min after the reaction => downgrade the idea to consolidation. The library's
candle-count version (1-3 candles, readings a/b, both NULL) is NOT retested here.

Reaction  = the library detector's 15m closure (structure_own_02a cisd_speed: a 20-bar low/high
            swept, close back through the opening price of the opposing series within 10 candles).
            T0 = that closing candle's close; R = |close - swept extreme|; E = close + 1R (expansion).
Stale     = in the 20 wall-clock minutes after T0 (M1 bars starting in [T0, T0+20m), >= 18 of them)
            price touched neither E nor the swept extreme. Decision time = T0 + 20 min.
Outcome   = from T0+20m (first M1 open P20), E touched before the extreme (1 / 0; same-bar 0.5;
            unresolved within 1380 M1 bars -> NaN, dropped).
Null      = same signed distances to E and to the extreme from P20, same direction, at 5 random
            moments within +/-30 d holding the NY clock within +/-30 min. claim '-': stale
            setups expand LESS often than the geometry says (downgraded to consolidation).
Reading u1007a: every reaction. u1007b: reactions whose T0 is in the forex NY AM window
(07:00-10:00 NY) — the NY-open context the number was spoken in.

Vault rerun (readings u1007va / u1007vb, same event frames as u1007a / u1007b; a/b untouched):
the u1007a null puts the stop barrier at an ARBITRARY level at the same distance while the
observed arm's barrier is a real swept extreme — vault Concept Campaign lesson 1 ("matching
stop distance is not matching stop placement"), which biases toward the observed arm, i.e.
against claim '-'. Structural control instead: the null is a FRESH reaction (any closure from
the same detector, same direction, T0 within +/-30 d and NY clock within +/-30 min of the stale
decision time, never the event's own reaction) at its own T0, with its OWN barriers (close+1R
and its swept extreme). Geometry: driftless barrier order P(E first) = dn/(up+dn); the null is
the fresh reaction's excess over that ratio carried to this event's ratio. So diff = stale
excess - fresh excess: what 20 idle minutes cost, everything else structural held equal.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02a")
from _common import cisd_speed, cl, np, pd  # noqa: E402  (same detector as the library readings)

CID = "v-shape-reversal-speed"
TF, POI_LB, MAX_K = "15min", 20, 10
WAIT = pd.Timedelta(minutes=20)
MIN_WIN_BARS = 18
EXP_R = 1.0
H_BARS = 1380
TOD_TOL = 30
COLS = ["decision_time", "available_at", "direction", "extreme", "exp_level", "k"]


def _detect(m1, ny_am):
    b = cl.build_bars(m1, TF)
    ev = cisd_speed(b, poi_lookback=POI_LB, max_k=MAX_K)
    if ev.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    j = ev["j"].to_numpy()
    t0 = pd.DatetimeIndex(b["close_time"].to_numpy()[j]).tz_convert("UTC")
    d = ev["dir"].to_numpy().astype(int)
    x = ev["extreme"].to_numpy(float)
    c0 = b["close"].to_numpy(float)[j]
    E = c0 + d * EXP_R * np.abs(c0 - x)
    t20 = t0 + WAIT
    mt = pd.DatetimeIndex(m1.index).tz_convert("UTC").as_unit("ns").asi8
    i0 = np.searchsorted(mt, t0.as_unit("ns").asi8, side="left")
    i1 = np.searchsorted(mt, t20.as_unit("ns").asi8, side="left")   # bars starting < T0+20m
    h, l = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    keep = ((i1 - i0) >= MIN_WIN_BARS) & (np.abs(c0 - x) > 0)
    for k in np.flatnonzero(keep):
        hi, lo = h[i0[k]:i1[k]].max(), l[i0[k]:i1[k]].min()
        if d[k] == 1:
            stale = hi < E[k] and lo > x[k]
        else:
            stale = lo > E[k] and hi < x[k]
        keep[k] = stale
    if ny_am:
        keep &= cl.in_window(t0, *cl.KILLZONES["fx_ny_am"])
    out = pd.DataFrame({"decision_time": t20, "available_at": t20, "direction": d,
                        "extreme": x, "exp_level": E, "k": ev["k"].to_numpy()})[keep]
    return out.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


def detect_a(m1):
    return _detect(m1, False)


def detect_b(m1):
    return _detect(m1, True)


def order(times, px, dirs, up, dn):
    """1 if the expansion level (px + d*up) is touched before the stop (px - d*dn), 0 if the
    stop first, 0.5 same M1 bar, NaN if neither within H_BARS trading minutes."""
    out = np.full(len(times), np.nan)
    tgt, stp = px + dirs * up, px - dirs * dn
    mt, ms = np.full(len(times), np.nan), np.full(len(times), np.nan)
    for s, ts, ss in ((1, "above", "below"), (-1, "below", "above")):
        m = dirs == s
        if m.any():
            mt[m] = cl.touch(times[m], tgt[m], ts, horizon_bars=H_BARS)["minutes"].to_numpy()
            ms[m] = cl.touch(times[m], stp[m], ss, horizon_bars=H_BARS)["minutes"].to_numpy()
    ft, fs = np.isfinite(mt), np.isfinite(ms)
    out[ft & (~fs | (mt < ms))] = 1.0
    out[fs & (~ft | (ms < mt))] = 0.0
    out[ft & fs & (mt == ms)] = 0.5
    return out


def run(which, dry=False):
    det = detect_a if which == "u1007a" else detect_b
    ev = cl.cache_frame(f"{CID}_{which}_{TF}_{POI_LB}_{MAX_K}_w20_e1", lambda: det(cl.load_m1()))
    print(which, "events", len(ev), "days", pd.DatetimeIndex(ev["decision_time"]).normalize().nunique())
    if dry:
        return
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    print("probe", probe["passed"], probe["events_compared"])
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    dirs = ev["direction"].to_numpy().astype(int)
    p20 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    up = dirs * (ev["exp_level"].to_numpy(float) - p20)       # signed distance to E
    dn = dirs * (p20 - ev["extreme"].to_numpy(float))          # signed distance to the extreme
    obs = order(t, p20, dirs, up, dn)
    rt = cl.sample_times(t, cl.rules.CTRL_REPS, cl.rules.CTRL_WINDOW_DAYS, seed=cl.rules.SEED,
                         tod_tol_min=TOD_TOL)
    res_frac = []

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        m = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[m])]
        out[m] = order(tk[m], px, dirs[m], up[m], dn[m])
        res_frac.append(float(np.isfinite(out).mean()))
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       claim="-", predictors=ev)
    diag = {"obs_resolved": round(float(np.isfinite(obs).mean()), 4),
            "null_resolved": [round(f, 4) for f in res_frac],
            "obs_ties": int((obs == 0.5).sum()), "median_R_up": float(np.median(up)),
            "median_dn": float(np.median(dn))}
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "observed_rate", "null_rate",
                                   "diff", "ci_lo", "ci_hi", "p", "mde", "halves")}, diag)
    rules = [
        f"{TF} bars; reaction = closure: extreme bar's low (high) below the 2 prior bars AND the lowest "
        f"low (highest high) of the prior {POI_LB} bars (the swept low); opposing series = contiguous "
        "down-close (up-close) candles ending at the extreme (or <=2 bars before), <=10 long; first "
        f"close beyond that series' first-candle OPEN within {MAX_K} candles, no new extreme first",
        "T0 = the closing candle's close; R = |close - extreme|; expansion level E = close + 1R in the "
        "reaction direction",
        f"stale: M1 bars starting in [T0, T0+20min) (>= {MIN_WIN_BARS} of them) touched neither E nor "
        "the swept extreme; decision_time = T0 + 20 min",
        f"hit: from the first M1 bar at/after T0+20min, E touched before the extreme within {H_BARS} "
        "M1 bars (same bar = 0.5; neither = dropped)",
        "null: same signed distances to E and to the extreme from the first M1 open, same direction, "
        f"at 5 random moments within +/-30 days and +/-{TOD_TOL} min NY clock; claim '-' (stale "
        "setups expand less often than the geometry implies)"]
    if which == "u1007b":
        rules.append("scope: T0 inside the forex NY AM window 07:00-10:00 New York")
    params = {"tf": TF, "poi_lookback": POI_LB, "left": 2, "max_k": MAX_K,
              "level": "series first-candle open", "wait_min": 20, "expansion_R": EXP_R,
              "min_window_bars": MIN_WIN_BARS, "horizon_bars": H_BARS, "tie": 0.5,
              "null_window_days": 30, "null_reps": 5, "null_tod_tol_min": TOD_TOL,
              "scope": "fx_ny_am 07:00-10:00 NY" if which == "u1007b" else "all sessions"}
    src = {"tf": "corpus: Hlwq1dRjBZo 'It'd be a new C2 on the 15minute' + draft ambiguity "
                 "(1-minute/15-minute NY open context); same 15m detector as library readings a/b",
           "poi_lookback": "phase3: lookback 20 knob (backtest_conjunction)",
           "left": "phase3: fractal 2/2 swing knob",
           "max_k": "declared-before-run: library reading structure_own_02a (closures up to 10 candles)",
           "level": "method_spec: §4.2 first-candle-open default",
           "wait_min": "corpus: Hlwq1dRjBZo 'it's not going to wait 35 minutes, not 35, 20 minutes "
                       "to go expand'",
           "expansion_R": "declared-before-run: the corpus gives no size for 'expand'; one reaction "
                          "risk (close-to-swept-extreme) beyond the reaction close",
           "min_window_bars": "declared-before-run: the 20 minutes must be traded minutes (>=18 of 20 "
                              "M1 bars) so a window into the 17:00 NY halt/weekend is not 'no expansion'",
           "horizon_bars": "declared-before-run: one trading day of M1 bars so nearly every event "
                           "resolves; barrier order is then insensitive to the stale set's low local "
                           "volatility (Concept Campaign lesson 3)",
           "tie": "declared-before-run: same-bar ambiguity scored as a coin flip in both arms (README §3 r2)",
           "null_window_days": "phase3: +/-30-day regime window (locked)",
           "null_reps": "phase3: 5 control reps (locked)",
           "null_tod_tol_min": "declared-before-run: README trap 9 / Concept Campaign lesson 3, rate "
                               "nulls hold the NY clock fixed",
           "scope": ("session_window_fit: forex NY AM killzone 07:00-10:00 (killzones.yaml); corpus: "
                     "Hlwq1dRjBZo is a 'New York Open Live Q&A'" if which == "u1007b" else
                     "corpus: claim stated without a session ('If price is going to expand ... It's just "
                     "going to go')")}
    p = cl.write_result(CID, which, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="TTrades update 2026-10-07 wall-clock speed claim; library candle-count "
                              f"readings a/b untouched. Diagnostics: {diag}")
    print(p)


# ── vault rerun: structural control (fresh reactions) ─────────────────────────
NEW = {"u1007va": ("u1007a", detect_a), "u1007vb": ("u1007b", detect_b)}
CTRL_DAYS = 30


def fresh_pool(m1):
    """Every closure (stale or not) as a fresh-reaction control decided at its own T0."""
    b = cl.build_bars(m1, TF)
    ev = cisd_speed(b, poi_lookback=POI_LB, max_k=MAX_K)
    j = ev["j"].to_numpy()
    c0 = b["close"].to_numpy(float)[j]
    x = ev["extreme"].to_numpy(float)
    d = ev["dir"].to_numpy().astype(int)
    return pd.DataFrame({"t0": pd.DatetimeIndex(b["close_time"].to_numpy()[j]).tz_convert("UTC"),
                         "dir": d, "extreme": x, "exp_level": c0 + d * EXP_R * np.abs(c0 - x)})


def _barriers(times, dirs, exp_level, extreme, mkt):
    px = mkt.o[np.minimum(mkt.pos_at_or_after(times), len(mkt.o) - 1)]
    up, dn = dirs * (exp_level - px), dirs * (px - extreme)
    return px, up, dn, np.clip(dn / (up + dn), 0, 1)       # driftless P(E first)


def run_v(which, dry=False):
    base, det = NEW[which]
    ev = cl.cache_frame(f"{CID}_{base}_{TF}_{POI_LB}_{MAX_K}_w20_e1", lambda: det(cl.load_m1()))
    pool = cl.cache_frame(f"{CID}_fresh_{TF}_{POI_LB}_{MAX_K}_e1", lambda: fresh_pool(cl.load_m1()))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    dirs = ev["direction"].to_numpy().astype(int)
    p20, up, dn, pos = _barriers(t, dirs, ev["exp_level"].to_numpy(float),
                                 ev["extreme"].to_numpy(float), mkt)
    obs = order(t, p20, dirs, up, dn)

    ft = pd.DatetimeIndex(pool["t0"])
    fd = pool["dir"].to_numpy().astype(int)
    p0, fup, fdn, fpos = _barriers(ft, fd, pool["exp_level"].to_numpy(float),
                                   pool["extreme"].to_numpy(float), mkt)
    ok = (fup > 0) & (fdn > 0)                  # entry open still inside its own band
    fobs = np.full(len(ft), np.nan)
    fobs[ok] = order(ft[ok], p0[ok], fd[ok], fup[ok], fdn[ok])
    fex = fobs - fpos                           # fresh excess over the driftless ratio
    good = np.isfinite(fex)

    ftn, tn, own = ft.asi8, t.asi8, (t - WAIT).asi8
    fmod, emod = cl.ny_minute_of_day(ft), cl.ny_minute_of_day(t)
    w = pd.Timedelta(days=CTRL_DAYS).value
    lo, hi = np.searchsorted(ftn, tn - w, "left"), np.searchsorted(ftn, tn + w, "right")
    cands = []
    for i in range(len(t)):
        s = np.arange(lo[i], hi[i])
        dm = np.abs(fmod[s] - emod[i])
        dm = np.minimum(dm, 1440 - dm)
        cands.append(s[(fd[s] == dirs[i]) & (dm <= TOD_TOL) & good[s] & (ftn[s] != own[i])])
    sizes = np.array([len(s) for s in cands])
    st = np.isfinite(obs)
    diag = {"events": len(ev), "fresh_pool": len(pool), "fresh_usable": int(good.sum()),
            "fresh_resolved": round(float(np.isfinite(fobs[ok]).mean()), 4),
            "obs_resolved": round(float(st.mean()), 4),
            "cand_median": int(np.median(sizes)), "cand_empty_share": round(float((sizes == 0).mean()), 4),
            "stale_excess": round(float(np.mean(obs[st] - pos[st])), 4),
            "fresh_excess_pool": round(float(np.mean(fex[good])), 4),
            "median_dn_stale": round(float(np.median(dn)), 3),
            "median_dn_fresh": round(float(np.median(fdn[good])), 3),
            "median_pos_stale": round(float(np.median(pos)), 4)}
    print(which, diag)
    if dry:
        return
    probe = cl.probe_lookahead(det, ev, lookback="10D")
    print("probe", probe["passed"], probe["events_compared"])

    def null_fn(rng, k):
        out = np.full(len(t), np.nan)
        for i, s in enumerate(cands):
            if len(s):
                out[i] = fex[s[rng.integers(len(s))]] + pos[i]
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]), null_fn=null_fn,
                       claim="-", predictors=ev)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "observed_rate", "null_rate",
                                   "diff", "ci_lo", "ci_hi", "p", "mde", "halves")})
    rules = [
        f"{TF} bars; reaction = closure: extreme bar's low (high) below the 2 prior bars AND the lowest "
        f"low (highest high) of the prior {POI_LB} bars (the swept low); opposing series = contiguous "
        "down-close (up-close) candles ending at the extreme (or <=2 bars before), <=10 long; first "
        f"close beyond that series' first-candle OPEN within {MAX_K} candles, no new extreme first",
        "T0 = the closing candle's close; R = |close - extreme|; expansion level E = close + 1R",
        f"stale: M1 bars starting in [T0, T0+20min) (>= {MIN_WIN_BARS}) touched neither E nor the swept "
        "extreme; decision_time = T0 + 20 min; outcome from the first M1 open at/after it (P20): E "
        f"before the extreme within {H_BARS} M1 bars (same bar 0.5, neither dropped)",
        "control = a FRESH reaction (any closure of the same detector, same direction, T0 within +/-30 "
        f"days and NY clock within +/-{TOD_TOL} min of the stale decision time, not the event's own) "
        "scored the same way from the first M1 open at/after ITS T0 against ITS OWN E and extreme",
        "geometry: driftless P(E first) = dn/(up+dn) from the start price; null = fresh outcome - its "
        "ratio + the stale event's ratio, 5 draws; claim '-': 20 idle minutes lower the expansion "
        "rate below a fresh reaction's (downgrade to consolidation)"]
    if which == "u1007vb":
        rules.append("scope: stale event's T0 inside the forex NY AM window 07:00-10:00 New York")
    params = {"tf": TF, "poi_lookback": POI_LB, "left": 2, "max_k": MAX_K,
              "level": "series first-candle open", "wait_min": 20, "expansion_R": EXP_R,
              "min_window_bars": MIN_WIN_BARS, "horizon_bars": H_BARS, "tie": 0.5,
              "control": "fresh reaction, own structural barriers", "ctrl_window_days": CTRL_DAYS,
              "ctrl_tod_tol_min": TOD_TOL, "ctrl_reps": 5, "geometry": "driftless dn/(up+dn) shift",
              "scope": "fx_ny_am 07:00-10:00 NY" if which == "u1007vb" else "all sessions"}
    src = {"tf": "corpus: Hlwq1dRjBZo 'It'd be a new C2 on the 15minute' + draft ambiguity "
                 "(1-minute/15-minute NY open context); same 15m detector as library readings a/b",
           "poi_lookback": "phase3: lookback 20 knob (backtest_conjunction)",
           "left": "phase3: fractal 2/2 swing knob",
           "max_k": "declared-before-run: library reading structure_own_02a (closures up to 10 candles)",
           "level": "method_spec: §4.2 first-candle-open default",
           "wait_min": "corpus: Hlwq1dRjBZo 'it's not going to wait 35 minutes, not 35, 20 minutes "
                       "to go expand'",
           "expansion_R": "declared-before-run: the corpus gives no size for 'expand'; one reaction "
                          "risk (close-to-swept-extreme) beyond the reaction close (as u1007a)",
           "min_window_bars": "declared-before-run: the 20 minutes must be traded minutes (>=18 of 20 "
                              "M1 bars) so a window into the 17:00 NY halt/weekend is not 'no expansion'",
           "horizon_bars": "declared-before-run: one trading day of M1 bars so nearly every event "
                           "resolves in both arms; barrier order is then insensitive to the stale "
                           "set's low local volatility (Concept Campaign lesson 3)",
           "tie": "declared-before-run: same-bar ambiguity scored as a coin flip in both arms (README §3 r2)",
           "control": "declared-before-run: vault Concept Campaign 2026-09-23 lesson 1 (matching stop "
                      "distance is not matching stop placement) — both arms keep real structural "
                      "barriers; draft measurable 'expansion probability as a function of minutes "
                      "elapsed since the reaction' makes the fresh reaction the comparison",
           "ctrl_window_days": "phase3: +/-30-day regime window (locked value, reused for the pool)",
           "ctrl_tod_tol_min": "declared-before-run: Concept Campaign lesson 3 / README trap 9, the null "
                               "holds the NY clock of the stale decision time",
           "ctrl_reps": "phase3: 5 control reps (locked)",
           "geometry": "declared-before-run: README trap 4 / vault trap 1 — the start position inside "
                       "the band differs between arms; the driftless barrier-order ratio removes it",
           "scope": ("session_window_fit: forex NY AM killzone 07:00-10:00 (killzones.yaml); corpus: "
                     "Hlwq1dRjBZo is a 'New York Open Live Q&A'" if which == "u1007vb" else
                     "corpus: claim stated without a session ('If price is going to expand ... It's just "
                     "going to go')")}
    p = cl.write_result(CID, which, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Vault-context rerun 2026-10-07 of the wall-clock speed claim: structural "
                              "fresh-reaction control replaces u1007a/b's random-moment null (vault lesson "
                              f"1). Same event frame as {base}. Diagnostics: {diag}")
    print(p)


if __name__ == "__main__":
    dry = len(sys.argv) > 2 and sys.argv[2] == "--count"
    run_v(sys.argv[1], dry) if sys.argv[1] in NEW else run(sys.argv[1], dry=dry)
