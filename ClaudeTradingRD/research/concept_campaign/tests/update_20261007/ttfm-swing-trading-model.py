"""ttfm-swing-trading-model, readings u1007a / u1007b (update_20261007_edu_01, video cWDnzI3lpUk).

New claim only. The prior reading (model_own_04b, n=41, UNDERPOWERED) is untouched: weekly C2 bias, a
daily C2 + H1 CISD, entered at the DAILY close with the weekly draw as target. Related books already
run and not repeated here: daily-bias-c2-c3-h1-cisd__b (daily C2/C3 + H1 CISD -> next-session bias,
NULL) and weekly-profile-framework a/b. What cWDnzI3lpUk adds, and what this script tests:
  * weekly bias = "is price going to reach for previous week's high or previous week's low?", or a
    weekly C2/C3 closure;
  * the entry is an hourly INTRA-CANDLE CISD inside the NEXT daily candle ("let the daily wick form"),
    decided at the top of an hour (the 9-5 cadence), stop on the daily wick, 2R "in the same daily range";
  * for US time zones, Asia first, and the New York session only if Asia gave nothing.

Declared before the first run (long; short mirrors):
  week  W = last weekly candle closed by day D's open. Bias +1 if W is a weekly C2 closure (low < prior
        week low, close > prior week low), else a weekly C3 closure (helpers Reading A). Draw = W's high
        (the previous week's high). The bias is live only while the week-to-date high < draw.
  day   P = last non-stub (>= 600 M1) trading day before D (18:00 NY roll). P is a daily C2 (else C3)
        closure in the bias direction AND carries a 1H CISD in that direction inside it
        ("a candle two or a candle three closure with a change in the state of delivery").
  entry on D's 1H bars: running low since D's open = the forming daily wick; the opposing (down-close)
        series that made it; the first later 1H close above that series' first open is the IC-CISD
        (a new low re-derives the series; a confirmed series is consumed until a new low). The
        confirming 1H bar must START in fx Asia 20:00-00:00 NY or fx NY AM 07:00-10:00 NY. At that close:
        D's low > P's low (the daily swing's protected swing intact) and week-to-date high < draw.
  trade decide at the 1H close (top of the hour), enter next M1 open, stop = D's low so far, 2R, time
        exit at D's 17:00 NY close, hold in trading minutes.
  u1007a: trade_test, ONE trade per day = the first qualifying event (Asia precedes NY inside the
          18:00-roll day, so this is "Asia first, NY if Asia gave nothing"); control holds the NY clock
          (+-30 min) because events sit only in two windows and the model is not a timing claim.
  u1007b: gate_test, first qualifying event per day per session, gate = Asia; claim '+' (the Asia
          entry beats the NY entry, each arm against its own matched control; no clock tolerance,
          because timing IS the claim, as in the README killzone example).
Not modelled: positional / swing-point entries, the weekly-range hold, the daily-bias-only shortcut, the
midweek/weekly-profile overlay, "Asia failed -> retry NY" as a loss rule (read as "no setup").

Vault traps checked: (1) geometry: 2R from a stop at the wick, scored vs a matched control, never a raw
win rate; (2) exits on M1, stop-first ties; (3)/(9) decisions at 1H closes, weekly/daily inputs read only
after their close (asof / closed P), probed symmetrically; (4) control +-30d regime-matched (harness);
(6) MDE from the harness; (7) no sparse join: every gate is computed per event, firing rate printed;
(8) no point thresholds, no 4H bars, post-2016 data only. Campaign lessons: the stop sits at a fresh
extreme (the day's low), so the matched control flatters (lesson 1); spread is reported per arm at
0.45 pt and the S5 median ~0.60 pt (lesson 2).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_04b")
import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

import concept_lab as cl                            # noqa: E402
from _helpers import c2_flags, c3_flags, cisd_in_candle, series_level  # noqa: E402

CID = "ttfm-swing-trading-model"
RR = 2.0
MIN_DAY_M1 = 600
ASIA = cl.KILLZONES["fx_asia"]
NYAM = cl.KILLZONES["fx_ny_am"]
TOD_TOL = 30
SPREAD_PTS = (0.45, 0.60)
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]


def _ohlc(b):
    return tuple(b[k].to_numpy(float) for k in ("open", "high", "low", "close"))


def _bias(b):
    o, h, l, c = _ohlc(b)
    c2 = c2_flags(o, h, l, c)
    return np.where(c2 != 0, c2, c3_flags(o, h, l, c, c2))


def detect(m1):
    """Every qualifying event, first per (trading day, session); column `asia` marks the session."""
    w = cl.build_bars(m1, "1W")
    d = cl.build_bars(m1, "1D")
    h1 = cl.build_bars(m1, "1h")
    if len(w) < 3 or len(d) < 3 or len(h1) < 3:
        return pd.DataFrame(columns=COLS + ["asia"])
    w = w.assign(wb=_bias(w).astype(float))
    dd = d[d["n_m1"].to_numpy() >= MIN_DAY_M1]
    dbias = _bias(dd)
    o, h, l, c = _ohlc(h1)
    i1 = pd.DatetimeIndex(h1.index)
    ct = pd.DatetimeIndex(h1["close_time"]).tz_convert("UTC")
    td1 = pd.DatetimeIndex(cl.trading_day(i1)).as_unit("ns").asi8
    sd = cl.trading_day(i1) + pd.Timedelta(days=1)               # week key = running_hilo's
    wk = (sd - pd.to_timedelta(sd.dayofweek, unit="D")).to_numpy()
    wk_hi = pd.Series(h).groupby(wk).cummax().to_numpy()
    wk_lo = pd.Series(l).groupby(wk).cummin().to_numpy()
    in_asia = cl.in_window(i1, *ASIA)
    in_ny = cl.in_window(i1, *NYAM)
    starts = np.r_[0, np.flatnonzero(td1[1:] != td1[:-1]) + 1]
    ends = np.r_[starts[1:], len(td1)]
    tdd = pd.DatetimeIndex(dd["trading_day"]).as_unit("ns").asi8
    d_td = pd.DatetimeIndex(d["trading_day"]).as_unit("ns").asi8
    d_end = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC") - pd.Timedelta(hours=1)   # 17:00 NY
    pa = {t: (s, e) for t, s, e in zip(td1[starts], starts, ends)}
    wkb = cl.asof(w, ct[starts])                                  # last week closed by D's first bar close
    rows = []
    for k, (a, b) in enumerate(zip(starts, ends)):
        D = td1[a]
        ip = np.searchsorted(tdd, D, side="left") - 1
        if ip < 1:
            continue
        s = int(dbias[ip])
        wb = wkb["wb"].iloc[k]
        if s == 0 or not np.isfinite(wb) or int(wb) != s:
            continue
        P = tdd[ip]
        if P not in pa:
            continue
        pa_, pb_ = pa[P]
        bull = s > 0
        if cisd_in_candle(o, h, l, c, pa_, pb_, bull)[0] < 0:
            continue
        p_ext = dd["low"].iloc[ip] if bull else dd["high"].iloc[ip]
        draw = wkb["high"].iloc[k] if bull else wkb["low"].iloc[k]
        idd = np.searchsorted(d_td, D)
        day_end = d_end[idd]
        ext, lvl, done = -1, np.nan, False
        seen = set()
        for j in range(a, b):
            x = l[j] if bull else h[j]
            if ext < 0 or ((x < l[ext]) if bull else (x > h[ext])):
                ext, lvl, done = j, series_level(o, c, j, bull, lo=a), False
                continue
            if done or not np.isfinite(lvl) or not ((c[j] > lvl) if bull else (c[j] < lvl)):
                continue
            done = True
            sess = "asia" if in_asia[j] else ("ny" if in_ny[j] else None)
            if sess is None or sess in seen:
                continue
            stop = l[ext] if bull else h[ext]
            intact = (stop > p_ext) if bull else (stop < p_ext)
            ahead = (wk_hi[j] < draw) if bull else (wk_lo[j] > draw)
            if not (intact and ahead):
                continue
            seen.add(sess)
            rows.append({"decision_time": ct[j], "available_at": ct[j], "direction": s,
                         "stop_px": float(stop), "rr": RR, "max_hold": day_end - ct[j],
                         "asia": sess == "asia"})
    ev = pd.DataFrame(rows, columns=COLS + ["asia"])
    ev = ev[ev["max_hold"] > pd.Timedelta(0)]
    ev["asia"] = ev["asia"].astype(bool)
    return ev.sort_values("decision_time", kind="stable").reset_index(drop=True)


def detect_a(m1):
    """Asia first, New York only if Asia gave nothing: the first event of each trading day."""
    ev = detect(m1)
    if ev.empty:
        return ev.drop(columns="asia")
    td = cl.trading_day(pd.DatetimeIndex(ev["decision_time"]))
    first = ~pd.Series(td).duplicated().to_numpy()
    return ev[first].drop(columns="asia").reset_index(drop=True)


RULES = [
    "weekly bias: last weekly candle closed by the day's first 1H close is a weekly C2 closure, else C3 "
    "(Reading A); draw = that week's high (bull) / low (bear) = previous week's high/low; live only while "
    "the week-to-date high < draw (low > draw) at the decision",
    "daily swing: the previous non-stub (>=600 M1) 18:00-NY day P is a daily C2 (else C3) closure in the "
    "bias direction with a 1H CISD (series_open) inside it",
    "entry: on day D's 1H bars, IC-CISD at the forming daily wick (running extreme, opposing series' first "
    "open, first later 1H close through it; new extreme re-derives; confirmed series consumed); the "
    "confirming 1H bar starts in fx Asia 20:00-00:00 NY or fx NY AM 07:00-10:00 NY; D's extreme has not "
    "taken P's extreme",
    "decide at the 1H close (top of the hour), enter next M1 open, stop = D's extreme so far, 2R, time exit "
    "at D's 17:00 NY close, hold in trading minutes",
]
PARAMS = {"bias_tf": "1W", "weekly_bias": "C2 else C3 (Reading A); draw = previous week's high/low, untaken",
          "swing_tf": "1D", "daily_closure": "C2 else C3 + 1H CISD inside", "entry_tf": "1h",
          "entry": "IC-CISD at the day's running extreme (series_open, series <= 10, run within 2 bars)",
          "sessions": "fx_asia 20:00-00:00 NY, fx_ny_am 07:00-10:00 NY (confirm-bar start)",
          "invalidation": "D's extreme beyond P's extreme", "rr": RR, "exit": "D 17:00 NY close",
          "day_open_hour": 18, "min_day_m1": MIN_DAY_M1, "hold_basis": "bars",
          "grid4h": "n/a (no 4H bars read)"}
SRC = {
    "bias_tf": "corpus: cWDnzI3lpUk 'The first thing to start with is a weekly bias.'",
    "weekly_bias": "corpus: cWDnzI3lpUk 'is price going to reach for previous week's high or previous week's low?' "
                   "/ 'a candle two or a candle three closure on the weekly'",
    "swing_tf": "corpus: cWDnzI3lpUk 'look to align daily swing points with that bias'",
    "daily_closure": "corpus: cWDnzI3lpUk 'A candle two or a candle three closure with a change in the state of delivery'",
    "entry_tf": "corpus: cWDnzI3lpUk 'it would really be 1 minute taking a look at the top of every hour'",
    "entry": "corpus: cWDnzI3lpUk 'the go-to is always going to be an intra-candle change in the state of "
             "delivery' / 'just letting that daily wick form and then looking to trade away'; method_spec §4.2 series_open",
    "sessions": "corpus: cWDnzI3lpUk 'focus on Asia session, see if I can position myself for the day' / "
                "'If that doesn't work, then I can check the New York session.'; windows: killzones.yaml forex "
                "Asia 20-00, NY AM 07-10 (vault Session Timing on Gold)",
    "invalidation": "corpus: ttfm-swing-trading-model yaml invalidation 'The daily swing point's protected swing is taken out.'",
    "rr": "corpus: cWDnzI3lpUk 'not only can you many times get 2R in the same daily range'",
    "exit": "corpus: cWDnzI3lpUk '2R in the same daily range' (the weekly-range hold is the prior reading's target)",
    "day_open_hour": "session_window_fit: settled 18:00 NY daily candle",
    "min_day_m1": "declared-before-run: README trap 6 stub sessions (as weekly-profile-framework)",
    "hold_basis": "declared-before-run (README trap 7): the hold ends at 17:00 NY, controls +-30d can span the "
                  "halt/weekend, so hold in trading minutes",
    "grid4h": "declared-before-run: no 4H bars are read",
}


def _spread_note(res, label):
    tr = res.pop("_trades", None)
    if tr is None:
        return ""
    risk = tr["risk"].to_numpy(float)
    gross = tr["gross_R"].to_numpy(float)
    g = tr["gate"].to_numpy(bool) if "gate" in tr.columns else np.ones(len(tr), bool)
    parts = []
    for name, m in (("gated/all", g), ("complement", ~g)):
        if m.any():
            parts.append(f"{name} n={int(m.sum())}: median stop {np.median(risk[m]):.2f} pt, gross "
                         f"{gross[m].mean():+.3f}R, net at " + " / ".join(
                             f"{x} pt {(gross[m] - x / risk[m]).mean():+.3f}R" for x in SPREAD_PTS) + " spread")
    return f"{label} descriptive: " + "; ".join(parts)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    show = ("n", "n_gated", "n_complement", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
            "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "halves", "dependence")
    if "a" in which:
        ev = cl.cache_frame("ttfm_swing_u1007a_asia_first", lambda: detect_a(cl.load_m1()))
        print("a rows", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="60D")
        print("probe", probe.get("passed"), probe.get("events_compared"))
        res = cl.trade_test(ev, claim="+", hold_basis="bars", ctrl_tod_tol_min=TOD_TOL, keep_trades=True)
        note = _spread_note(res, "u1007a")
        for k in show:
            if res.get(k) is not None:
                print(f"  {k:16s} {res[k]}")
        print(note)
        print(cl.write_result(CID, "u1007a", res, operationalization={"rules": RULES + [
            "u1007a: one trade per trading day = first qualifying event (Asia first, NY if Asia gave nothing); "
            "trade_test, control NY clock +-30 min"], "params": {**PARAMS, "ctrl_tod_tol_min": TOD_TOL}},
            params_source={**SRC, "ctrl_tod_tol_min": "declared-before-run: README trap 9 - events sit only in "
                           "two session windows and the model is not a timing claim, so the control holds the NY clock"},
            script=__file__, probe=probe,
            notes="The 9-5 model as stated in cWDnzI3lpUk (weekly C2/C3 bias with the previous-week draw, daily "
                  "C2/C3 + H1 CISD swing, hourly IC-CISD at the top of the hour inside the next daily candle, Asia "
                  "first). Caveat (campaign lesson 1): the stop sits at the day's fresh extreme, which beats a "
                  "random stop at the same distance generically, so the control flatters. " + note))
    if "b" in which:
        ev = cl.cache_frame("ttfm_swing_u1007b_asia_vs_ny", lambda: detect(cl.load_m1()))
        print("b rows", len(ev), "asia share", round(float(ev["asia"].mean()), 3))
        probe = cl.probe_lookahead(detect, ev, lookback="60D")
        print("probe", probe.get("passed"), probe.get("events_compared"))
        res = cl.gate_test(ev, "asia", mask_available_at="decision_time", claim="+", hold_basis="bars",
                           keep_trades=True)
        note = _spread_note(res, "u1007b")
        for k in show:
            if res.get(k) is not None:
                print(f"  {k:16s} {res[k]}")
        print(note)
        print(cl.write_result(CID, "u1007b", res, operationalization={"rules": RULES + [
            "u1007b: first qualifying event per trading day per session; gate_test gate = Asia session vs "
            "NY AM session, claim '+'; controls at any hour (timing is the claim)"], "params": PARAMS},
            params_source=SRC, script=__file__, probe=probe,
            notes="Asia-first preference for US time zones, scored as Asia entries vs NY entries of the same "
                  "model, each against its own matched control. The source hedges it ('this is really "
                  "working on any session'). " + note))
