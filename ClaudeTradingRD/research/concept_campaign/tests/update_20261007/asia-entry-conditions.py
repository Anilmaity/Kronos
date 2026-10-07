"""asia-entry-conditions — update u1007 (TTrades own voice, BgVkJf0kMo4 "How to Trade Asia Using
TTrades Fractal Model"). trade_test, claim '+'. New concept (not in batches.json).

The claim: trade Asia only when a daily C2 closure implies a C3 expansion, with a mandatory
higher-timeframe bias; execute either (1) an hourly POSITIONAL entry at the daily open when a
protected swing sits "very close in proximity to the open of candle three" (stop on it, 2R), or
(2) when the hourly structure is not good enough, wait for a 4H candle-2 closure in Asia and take
the 15m fractal model on a new intra-candle CISD (stop on the 15m protected swing, "the wick high
of the 4-hour candle" in his example, 2R).

What was already tested and is NOT re-tested here (vault: Concept Campaign 2026-09-23):
  * asia-session-c2-protected-swing (time_own_03a): daily C2 + latest 1h CISD swing, entry at the
    next daily open, target = D's extreme -> UNDERPOWERED, -0.018R [-0.078, +0.082], n=697.
  * positional-entry u1007b: 1D C2 + 1h CISD, stop below EQ/CISD50, 2R at the C3 open.
  New here: the method SELECTION (positional only when the swing is close to the open, else the
  4H-C2 + 15m fractal fallback inside Asia), the 2R target, and the HTF-bias gate.

Operationalisation (every parameter declared before the first run; nothing tuned):
  * daily candles on the 18:00 NY roll, stub sessions (<600 M1) dropped, previous day = the
    preceding real session (time_own_03a conventions). D = one-sided daily C2 closure (spec §3.2).
  * bias (both readings): D's extreme is confirmed by a 1h CISD inside D (spec §2.4 / bias.py
    hourly_cisd_in_candle: D's extreme, the opposing 1h series that made it, a later 1h close
    through the series' first open before D closes) — "We have a candle two closure on the daily
    paired with an hourly change in the state of delivery, which confirms the swing point".
    u1007b adds the monthly layer of his first example ("a nice monthly reversal candle and ...
    going into this new monthly candle a bullish bias"): the last CLOSED month's previous-candle
    engine (§2.3) implies D's direction for the month C3 trades in; continuation or reversal
    closures only (an inside/both-sides month gives no monthly bias -> no trade; the spec's
    "default to trend" fallback reads unbounded history and is not used).
  * method 1 (positional): protected-swing candidates = D's extreme (confirmed by the bias CISD)
    and every same-direction 1h CISD (phase-3 locked: series_open, 2/2, max_wait 3) whose extreme
    lies inside D and whose confirming bar closed by D's close; the LATEST-confirmed candidate
    still intact at D's close (no M1 beyond it since its confirmation) is the swing (§3.8). It is
    "very close" when 0 < dir*(D close - swing) <= 0.25 x ADR20. Then: decide at D's close, enter
    at the C3 open (first M1 at/after 18:00 NY), stop = swing, 2R.
  * method 2 (only when method 1 does not qualify): Asia = [C3 open, 02:00 NY). A forex-grid 4H
    candle closing inside Asia (the 17:00 and 21:00 NY candles) that is a one-sided C2 closure
    vs the previous 4H candle in D's direction; then the first same-direction 15m CISD (phase-3
    locked config) whose extreme formed after that 4H close (an intra-candle CISD of the next 4H
    candle) and whose confirming bar closes within the next 4H candle and inside Asia. Void if,
    before that confirmation, C3 traded beyond D's extreme (the daily protected swing) or beyond
    the 4H C2's extreme. Decide at the 15m confirm close, enter next M1 open, stop = the 15m
    protected swing, 2R. At most one trade per day (method 1, else the first method-2 setup).
  * exit: stop / 2R / time exit at the end of C3 (17:00 NY), "I'm going to take my entry, go to
    bed, and I'm either going to get stopped out or it's going to hit TP"; hold in trading
    minutes (hold_basis='bars', README trap 7). Controls hold the NY clock +/-30 min (trap 9).
  * NOT modelled: case (b) "opening near a drawn liquidity" (named, not demonstrated — draft
    ambiguity); the reversal-day variant (trading the daily C2 itself with SMT + hourly CISD + 4H
    closure + 15m continuation) — a different, rarer setup on the still-forming C2 that needs SMT
    (phase 3 demoted SMT for sparsity: 31 -> 9 days); the optional "ideally paired with an hourly
    CISD" on the 4H closure; EQ / wick-size eyeballing; trailing.

Vault checks (Backtest Methodology Traps 1-9, campaign lessons 1-4): 1 matched control at the same
stop and target distance; 2 M1 exits, stop-first ties (ties reported); 3/9 every HTF read is a
CLOSED bar (D at its close, the 4H C2 at its close, months via cl.asof); 4 +/-30d regime-matched
controls; 5 headline gross R recomputed from raw M1 outside the harness (raw_check); 6 MDE
reported, no tuning; 7 hold_basis='bars' + exposure_bars printed; 8 certified 2016+ span, the
proximity threshold in ADR units, grid4h recorded; lesson 2 median stop in points and the R a
0.30 pt spread costs (cost cancels in the differential).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(HERE.parent / "time_own_03a"))
sys.path.insert(0, str(HERE.parent / "model_own_04b"))
import numpy as np                                   # noqa: E402
import pandas as pd                                  # noqa: E402

import concept_lab as cl                             # noqa: E402
from detectors.cisd import cisd_events               # noqa: E402
from _common import daily, MIN_DAY_M1, trading_minutes, OHLC   # noqa: E402  (time_own_03a)
from _helpers import c2_flags, cisd_in_candle        # noqa: E402  (model_own_04b)

CID = "asia-entry-conditions"
TZ = "America/New_York"
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
ADR_N = 20
PROX = 0.25
RR = 2.0
GRID4H = "forex"
ASIA_END_H = 2                       # 02:00 NY
SPREAD_PT = 0.30                     # vault campaign lesson 2; descriptive only
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "method"]
RES_DIR = HERE.parents[1] / "results"


def _empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})


def _c3_end(t: pd.Timestamp) -> pd.Timestamp:
    """End of the C3 trading day: the first 17:00 NY after t that is not on a weekend."""
    ny = t.tz_convert(TZ)
    e = ny.normalize() + pd.Timedelta(hours=17)
    if e <= ny:
        e += pd.Timedelta(days=1)
    while e.dayofweek >= 5:
        e += pd.Timedelta(days=1)
    return e.tz_convert("UTC")


def _monthly_bias(m1: pd.DataFrame) -> pd.DataFrame:
    """Previous-candle engine (§2.3) on monthly bars: implied bias for the NEXT month, from
    continuation / reversal closures only (+1 / -1; 0 = inside, both sides, or no prior)."""
    mb = cl.build_bars(m1, "1M")
    h, l, c = (mb[k].to_numpy(float) for k in ("high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    th, tl = h > ph, l < pl
    only_h, only_l = th & ~tl, tl & ~th
    bias = np.zeros(len(mb), int)
    bias[only_h & (c > ph)] = 1
    bias[only_h & ~(c > ph)] = -1
    bias[only_l & (c < pl)] = -1
    bias[only_l & ~(c < pl)] = 1
    return mb.assign(mbias=bias.astype(float))


def detect_core(m1: pd.DataFrame, monthly: bool) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < ADR_N + 2:
        return _empty()
    # No "day complete" filter: D's events carry D's NOMINAL close (18:00 NY), so a partial D on a
    # truncated slice emits only events after the cut (never compared), and the data's own last,
    # unfinished day is dropped by the harness (no bar after decision). A filter on the slice's
    # last M1 wrongly drops complete days at an 18:00 cut (the 17-18 halt has no bars).
    adr = (d["high"] - d["low"]).rolling(ADR_N, min_periods=ADR_N).mean().to_numpy()
    d_ct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    d_st = pd.DatetimeIndex(d.index).tz_convert("UTC")
    bull = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).fillna(False).to_numpy()
    bear = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).fillna(False).to_numpy()
    ok = d["p_ok"].to_numpy(bool) & (bull ^ bear) & np.isfinite(adr)
    if not ok.any():
        return _empty()
    dc, dh, dl = (d[k].to_numpy(float) for k in ("close", "high", "low"))

    # 1h bars (bias CISD inside D, method-1 swings)
    b1 = cl.build_bars(m1, "1h")
    o1, h1, l1, c1 = (b1[k].to_numpy(float) for k in OHLC)
    i1 = pd.DatetimeIndex(b1.index).tz_convert("UTC")
    ct1 = pd.DatetimeIndex(b1["close_time"]).tz_convert("UTC")
    e1 = cisd_events(b1[OHLC], **CISD_KW)
    if len(e1):
        e1_dec = pd.DatetimeIndex(b1.loc[e1["confirm_time"], "close_time"]).tz_convert("UTC").asi8
        e1_ext = pd.DatetimeIndex(e1["extreme_time"]).tz_convert("UTC").asi8
        e1_dir = np.where(e1["direction"].to_numpy() == "bullish", 1, -1)
        e1_px = e1["protected_swing"].to_numpy(float)
        o_ = np.argsort(e1_dec, kind="stable")
        e1_dec, e1_ext, e1_dir, e1_px = e1_dec[o_], e1_ext[o_], e1_dir[o_], e1_px[o_]
    else:
        e1_dec = e1_ext = np.zeros(0, np.int64)
        e1_dir = np.zeros(0, int)
        e1_px = np.zeros(0)

    # 4h forex grid (method 2 C2 closure)
    b4 = cl.build_bars(m1, "4h", grid4h=GRID4H)
    o4, h4, l4, c4 = (b4[k].to_numpy(float) for k in OHLC)
    c2_4 = c2_flags(o4, h4, l4, c4)
    ct4 = pd.DatetimeIndex(b4["close_time"]).tz_convert("UTC").asi8

    # 15m bars + CISD (method 2 entry)
    q = cl.build_bars(m1, "15min")
    qh, ql = q["high"].to_numpy(float), q["low"].to_numpy(float)
    qst = pd.DatetimeIndex(q.index).tz_convert("UTC").asi8
    qct = pd.DatetimeIndex(q["close_time"]).tz_convert("UTC").asi8
    e15 = cisd_events(q[OHLC], **CISD_KW)
    if len(e15):
        f_dec = pd.DatetimeIndex(q.loc[e15["confirm_time"], "close_time"]).tz_convert("UTC").asi8
        f_ext = pd.DatetimeIndex(e15["extreme_time"]).tz_convert("UTC").asi8
        f_dir = np.where(e15["direction"].to_numpy() == "bullish", 1, -1)
        f_px = e15["protected_swing"].to_numpy(float)
        o_ = np.argsort(f_dec, kind="stable")
        f_dec, f_ext, f_dir, f_px = f_dec[o_], f_ext[o_], f_dir[o_], f_px[o_]
    else:
        f_dec = f_ext = np.zeros(0, np.int64)
        f_dir = np.zeros(0, int)
        f_px = np.zeros(0)

    mbias = None
    if monthly:
        mb = _monthly_bias(m1)
        mbias = cl.asof(mb, d_ct)["mbias"].to_numpy()

    tn = pd.DatetimeIndex(m1.index).tz_convert("UTC").asi8
    lo, hi = m1["low"].to_numpy(float), m1["high"].to_numpy(float)
    H4 = pd.Timedelta(hours=4).value
    rows = []
    for i in np.flatnonzero(ok):
        s = 1 if bull[i] else -1
        if monthly and not (np.isfinite(mbias[i]) and int(mbias[i]) == s):
            continue
        D0, D1 = d_st[i].value, d_ct[i].value
        a = int(i1.asi8.searchsorted(D0, "left"))
        b = int(i1.asi8.searchsorted(D1, "left"))
        j, e = cisd_in_candle(o1, h1, l1, c1, a, b, s > 0)
        if j < 0:                                      # no confirmed daily bias
            continue
        # ---- method 1: latest-confirmed intact protected swing, close to the open
        cands = [(ct1[j].value, float(l1[e] if s > 0 else h1[e]))]
        k0 = int(np.searchsorted(e1_dec, D0, "left"))
        k1 = int(np.searchsorted(e1_dec, D1, "right"))
        for k in range(k0, k1):
            if e1_dir[k] == s and e1_ext[k] >= D0:
                cands.append((int(e1_dec[k]), float(e1_px[k])))
        cands.sort(key=lambda x: x[0])
        swing = np.nan
        for tc, px in reversed(cands):
            j0 = int(np.searchsorted(tn, tc, "left"))
            j1 = int(np.searchsorted(tn, D1, "left"))
            if j1 > j0 and ((s > 0 and lo[j0:j1].min() < px) or (s < 0 and hi[j0:j1].max() > px)):
                continue
            swing = px
            break
        dist = s * (dc[i] - swing) if np.isfinite(swing) else np.nan
        if np.isfinite(dist) and 0 < dist <= PROX * adr[i]:
            t = d_ct[i]
            rows.append((t, t, s, swing, RR, trading_minutes(t, _c3_end(t)), 1))
            continue
        # ---- method 2: 4H C2 closure in Asia, then a 15m intra-candle CISD
        p0 = int(np.searchsorted(tn, D1, "left"))
        if p0 >= len(tn):
            continue
        c3_open = pd.Timestamp(tn[p0], tz="UTC")
        c3_ny = c3_open.tz_convert(TZ)
        if c3_ny.hour != 18:                           # C3 must open at the 18:00 reopen
            continue
        asia_end = (c3_ny.normalize() + pd.Timedelta(days=1, hours=ASIA_END_H)).tz_convert("UTC").value
        c3o = c3_open.value
        q0 = int(np.searchsorted(qst, c3o, "left"))
        for k4 in np.flatnonzero((ct4 > c3o) & (ct4 <= asia_end)):
            if c2_4[k4] != s:
                continue
            c2c = int(ct4[k4])
            w_end = min(c2c + H4, asia_end)
            a15 = int(np.searchsorted(f_dec, c2c, "right"))
            b15 = int(np.searchsorted(f_dec, w_end, "right"))
            hit = None
            for m in range(a15, b15):
                if f_dir[m] == s and f_ext[m] >= c2c:
                    hit = m
                    break
            if hit is None:
                continue
            dec = int(f_dec[hit])
            qe = int(np.searchsorted(qct, dec, "right"))          # 15m bars closed by dec
            qa = int(np.searchsorted(qst, c2c, "left"))
            if s > 0:
                void = ql[q0:qe].min() < dl[i] or ql[qa:qe].min() < l4[k4]
            else:
                void = qh[q0:qe].max() > dh[i] or qh[qa:qe].max() > h4[k4]
            if void:
                break                                   # invalidation taken: no Asia trade
            t = pd.Timestamp(dec, tz="UTC")
            rows.append((t, t, s, float(f_px[hit]), RR, trading_minutes(t, _c3_end(t)), 2))
            break
    if not rows:
        return _empty()
    ev = pd.DataFrame(rows, columns=COLS)
    for c in ("decision_time", "available_at"):
        ev[c] = pd.DatetimeIndex(ev[c]).tz_convert("UTC")
    ev["max_hold"] = pd.to_timedelta(ev["max_hold"])
    ev["direction"] = ev["direction"].astype(int)
    ev["method"] = ev["method"].astype(int)
    return ev.sort_values("decision_time", kind="stable").reset_index(drop=True)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    return detect_core(m1, monthly=False)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    return detect_core(m1, monthly=True)


def raw_check(ev: pd.DataFrame) -> dict:
    """Trap 5 + lesson 2: gross R of the real book from a plain M1 loop (entry = next M1 open,
    stop-first ties, gap through the stop fills at the open, hold in M1 bars), and stop size."""
    m1 = cl.load_m1()
    tn = m1.index.as_unit("ns").asi8
    o, h, l, c = (m1[k].to_numpy() for k in ("open", "high", "low", "close"))
    rs, risk = [], []
    for t, s, sp, mh in zip(pd.DatetimeIndex(ev["decision_time"]).as_unit("ns").asi8,
                            ev["direction"].to_numpy(), ev["stop_px"].to_numpy(float),
                            pd.to_timedelta(ev["max_hold"]).dt.total_seconds().to_numpy() // 60):
        i0 = int(np.searchsorted(tn, t, "left"))
        if i0 >= len(tn):
            continue
        e = o[i0]
        r = s * (e - sp)
        if r <= 0:
            continue
        i1 = min(i0 + int(mh), len(tn))
        tg = e + s * RR * r
        px = c[i1 - 1]
        for k in range(i0, i1):
            if (l[k] <= sp) if s > 0 else (h[k] >= sp):
                px = min(o[k], sp) if s > 0 else max(o[k], sp)
                break
            if (h[k] >= tg) if s > 0 else (l[k] <= tg):
                px = max(o[k], tg) if s > 0 else min(o[k], tg)
                break
        rs.append(s * (px - e) / r)
        risk.append(r)
    risk = np.asarray(risk)
    return {"n": len(rs), "avg_R_gross_raw": round(float(np.mean(rs)), 4),
            "median_stop_pt": round(float(np.median(risk)), 3),
            "spread_cost_R_median": round(float(np.median(SPREAD_PT / risk)), 3)}


def by_method(ev: pd.DataFrame, tr: pd.DataFrame) -> dict:
    """Descriptive split of the scored book (no extra test is run)."""
    meth = ev["method"].to_numpy()[tr["ev_id"].to_numpy()]
    out = {}
    for mth in (1, 2):
        s = tr[meth == mth]
        g = np.isfinite(s["ctrl_mean_R"].to_numpy())
        out[f"m{mth}"] = {"n": int(len(s)),
                          "avg_R_net": round(float(s["net_R"].mean()), 4) if len(s) else None,
                          "diff_vs_ctrl": round(float((s["net_R"] - s["ctrl_mean_R"])[g].mean()), 4)
                          if g.any() else None}
    return out


def guard_same_hyp(reading: str, res: dict) -> None:
    f = RES_DIR / f"{CID}__{reading}.json"
    if f.exists():
        old = json.loads(f.read_text()).get("hyp_key")
        if old != res.get("hyp_key"):
            raise SystemExit(f"{f.name}: hyp_key {old} != {res.get('hyp_key')}; use a new reading label")


RULES_COMMON = [
    "daily candles on the 18:00 NY roll; stub sessions (<600 M1) dropped; previous day = the preceding "
    "real session; D = one-sided daily C2 closure (spec 3.2)",
    "bias: D's extreme confirmed by a 1h CISD inside D (D's extreme, the opposing 1h series that made "
    "it, a later 1h close through the series' first open before D closes; spec 2.4)",
    "method 1: swing = latest-confirmed intact candidate among D's extreme and same-direction 1h CISD "
    "extremes inside D (series_open, 2/2, max_wait 3) confirmed by D's close; if 0 < dir*(D close - "
    "swing) <= 0.25 x ADR20 (mean range of the last 20 real days incl. D): decide at D's close, enter "
    "at the C3 open (18:00 NY), stop = swing, 2R",
    "method 2 (only if method 1 does not qualify): Asia = [C3 open, 02:00 NY); a forex-grid 4H candle "
    "closing inside Asia that is a one-sided C2 closure in D's direction; the first same-direction 15m "
    "CISD (locked config) with its extreme after that 4H close, confirmed within the next 4H candle and "
    "inside Asia; void if C3 traded beyond D's extreme or the 4H C2 extreme before confirmation; enter "
    "next M1 open, stop = the 15m protected swing, 2R",
    "one trade per day; exit at stop / 2R / end of C3 (17:00 NY), hold in trading minutes "
    "(hold_basis='bars'); matched control +/-30d, same NY clock +/-30 min",
]
PARAMS_COMMON = {"stub_filter_min_m1": MIN_DAY_M1, "c2": "one-sided daily, 18:00 NY roll",
                 "bias": "daily C2 + 1h CISD at D's extreme (spec 2.4)",
                 "cisd": CISD_KW, "swing_pick": "latest intact", "prox_adr_mult": PROX,
                 "adr_n": ADR_N, "grid4h": GRID4H, "asia_window": "18:00-02:00 NY",
                 "ltf_entry": "15min", "rr": RR, "max_hold": "to C3 end 17:00 NY",
                 "hold_basis": "bars", "ctrl_tod_tol_min": 30}
SRC_COMMON = {
    "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (time_own_03a convention)",
    "c2": "method_spec: §3.2 C2 closure; corpus: BgVkJf0kMo4 'a candle two closure in which we can expect "
          "the following candle or candle three to have an expansion'",
    "bias": "corpus: BgVkJf0kMo4 'you really do need a bias' / 'We have a candle two closure on the daily "
            "paired with an hourly change in the state of delivery'; method_spec §2.4 C2 + hourly CISD",
    "cisd": "phase3: locked CISD config (series_open, 2/2, max_wait 3, min_series 1)",
    "swing_pick": "method_spec: §3.8 'Each new protected swing supersedes the last'; corpus: BgVkJf0kMo4 "
                  "'We have a new protected swing and then we have another protected swing'",
    "prox_adr_mult": "declared-before-run: 'very close in proximity to the open of candle three' is "
                     "unbounded (draft ambiguity); 0.25 ADR puts the 2R target within half an average day "
                     "(method_spec §5 ADR budget caps targets)",
    "adr_n": "declared-before-run: ADR20 of real days (risk_own_01b average-daily-range-targeting precedent; "
             "method_spec §5 gives no lookback [GAP])",
    "grid4h": "session_window_fit: forex 4H grid for gold (carried as a knob, README trap 8)",
    "asia_window": "declared-before-run: Asia = day open 18:00 to the London killzone start 02:00 NY "
                   "(killzones.yaml via session_window_fit; time_own_03a session partition); the "
                   "source gives no clock times (draft ambiguity)",
    "ltf_entry": "corpus: BgVkJf0kMo4 'go down to the 4-hour and 15-minute fractal model and trade the "
                 "standard fractal model using an intra-candle change in the state of delivery'",
    "rr": "corpus: BgVkJf0kMo4 'Then I can look for two R' / 'we could look for two R'",
    "max_hold": "corpus: BgVkJf0kMo4 'expecting the daily range to play out' and 'take my entry, go to bed' "
                "-> declared-before-run: time exit at the end of C3",
    "hold_basis": "declared-before-run: README trap 7, holds cross the 17:00 halt / weekend",
    "ctrl_tod_tol_min": "declared-before-run: entries cluster at the 18:00 reopen and in Asia; hold the NY "
                        "clock fixed (README trap 9, Session Timing on Gold)",
}


def run(reading: str, detect, key: str, lookback: str, extra_rules, extra_params, extra_src, note):
    ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
    print(f"{reading} events", len(ev), ev["direction"].value_counts().to_dict(),
          "method", ev["method"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback=lookback)
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, hold_basis="bars", ctrl_tod_tol_min=30, keep_trades=True)
    for k in ("n", "dropped", "avg_R", "avg_R_gross", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "halves"):
        print(f"  {k:14s} {res.get(k)}")
    guard_same_hyp(reading, res)
    raw = raw_check(ev)
    split = by_method(ev, res["_trades"])
    print("raw recompute", raw, "| harness gross", res["avg_R_gross"])
    print("by method", split)
    op = {"rules": RULES_COMMON + extra_rules, "params": {**PARAMS_COMMON, **extra_params}}
    notes = (note + " Vault rerun checks: trap 5 raw M1 recompute of the real book "
             f"{raw} vs harness avg_R_gross {res['avg_R_gross']}; descriptive method split (not a "
             f"separate test) {split}. Campaign lesson 2: cost cancels in the differential; "
             f"'spread_cost_R_median' is what a {SPREAD_PT} pt spread costs per trade. Not modelled: "
             "case (b) open near drawn liquidity (not demonstrated), the reversal-day variant (needs SMT; "
             "a different setup on the forming C2), the optional hourly CISD paired with the 4H closure, "
             "EQ/wick eyeballing, trailing.")
    p = cl.write_result(CID, reading, res, operationalization=op, params_source={**SRC_COMMON, **extra_src},
                        script=__file__, probe=probe, notes=notes, allow_unknown_id=True)
    print(p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run("u1007a", detect_a, "u1007_asia_entry_a_v1", "45D", [], {}, {},
            "Reading a: the higher-timeframe bias is the spec 2.4 daily bias (daily C2 + hourly CISD), "
            "the stated reason in his second example.")
    if "b" in which:
        run("u1007b", detect_b, "u1007_asia_entry_b_v1", "100D",
            ["monthly bias: the last CLOSED month's previous-candle engine (continuation or reversal "
             "closure vs the prior month) implies D's direction for the month C3 trades in; inside / "
             "both-sides months give no bias (no trade)"],
            {"htf_bias": "monthly previous-candle engine, no trend fallback"},
            {"htf_bias": "corpus: BgVkJf0kMo4 'We have a nice monthly reversal candle and we have going into "
                         "this new monthly candle a bullish bias'; method_spec §2.3 previous-candle engine; "
                         "declared-before-run: no inside-bar trend fallback (unbounded history)"},
            "Reading b: adds the monthly bias of his first example to reading a.")
