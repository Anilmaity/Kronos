"""ttfm-scalping-model, readings u1007a / u1007b (update_20261007_live_10, video GRc5FVB5tdg).

New claim (prior reading, model_own_04b: hourly-C2 / 15m positional book, NULL, untouched):
on a REVERSAL day, when little expansion is expected and the target is the daily open, drop
from the 4H/15m pairing to the 15m/1m fractal model, because the 15m entry gives poor R to
that target: "it's a reversal day. I'm not getting good risk-to-reward on the 15-minut to try
to trade a reversal day here. I'm not expecting a ton of expansion. So, I had to refine it down."

Everything below was declared before the first run.
  reversal day, long (short mirrors), evaluated at the decision t on the 18:00-NY trading day:
    PDL < O < PDH          the day opened inside the prior day's range (O = 18:00 open)
    running low(t) < PDL   expansion into the prior day's low, the HTF target ("we hit this
                           previous low ... expansion into a low that is a target")
    running high(t) < PDH  the other side is untaken (not an outside day)
    P < O                  the daily open, the reversal-day target, is still ahead
  window: decision in [09:00, 12:00) NY (forex-grid 4H close nearest his "wait for 10 a.m."
          futures 4H close, to the end of NY a.m.).
  15m arm (the 4H/15m entry he rejects): first 15m phase-3 CISD in the reversal direction in
          the window; stop = its protected swing; target = O.
  1m arm (the 15m/1m fractal model): first 1m phase-3 CISD in the reversal direction in the
          window whose protected swing is the low (high) of the 15m candle in progress up to
          the confirming bar ("let the wick form") and which confirms inside that 15m candle
          ("trade the body"); stop = its protected swing; target = O.
  both:   decide at the confirming bar close, enter next M1 open, 150 min clock hold; the
          control holds the NY clock (+-30 min) because every event sits in 09:00-12:00 NY.
  u1007a: trade_test on the 1m arm, claim '+' (the switch's model carries an edge).
  u1007b: gate_test on both arms pooled, gate = 1m arm, claim '+' (on the same reversal days
          the 1m entry beats the 15m entry, each against its own matched control).
Not modelled: the 3m-vs-1m clause (that R-gated ladder is rr-gated-entry-refinement,
NEGATIVE), the 4H candle-closure context, the POI ("reach into this gap") and SMT.

Vault-context rerun (2026-10-07): same pre-declared design and labels, checked against
Backtest Methodology Traps 1-9 and the Concept Campaign lessons. Decisions are at closed-bar
times (no in-progress HTF bar: the 15m-wick rule reads only M1 bars closed by the confirm
bar), exits on M1 stop-first, no 4H bars, no point thresholds, window+hold never crosses the
17:00 NY halt. Known ceiling (campaign lesson 1): a stop at a fresh 1m extreme beats a random
stop at the same distance generically, so u1007a's control flatters; u1007b (both arms stop
at a protected swing) is the cleaner read of the switch. Spread is reported at the campaign
0.45 pt and at the S5-measured median ~0.60 pt (XAUUSD Data Inventory).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402

import concept_lab as cl                 # noqa: E402
from detectors.cisd import cisd_events   # noqa: E402

CID = "ttfm-scalping-model"
OHLC = ["open", "high", "low", "close"]
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
WIN = ("09:00", "12:00")
PAD_START = "08:00"                     # 1m slice start: 60 min of warm-up before the window
HOLD = "150min"
TOD_TOL = 30
SPREAD_PTS = (0.45, 0.60)               # descriptive only: campaign base cost, S5 median spread
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "is_1m"]


def _cisd(b):
    """Phase-3 CISD events with decision_time = confirming bar close, deterministic order."""
    ev = cisd_events(b[OHLC], **CISD_KW)
    if ev.empty:
        return ev
    ev = ev.copy()
    ev["decision_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[
        b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))]).tz_convert("UTC")
    ev["sgn"] = np.where(ev["direction"] == "bullish", 1, -1)
    return ev.sort_values(["confirm_time", "extreme_time", "sgn"], kind="stable")


def _arm_15m(m1):
    ev = _cisd(cl.build_bars(m1, "15min"))
    if ev.empty:
        return ev
    return ev[cl.in_window(ev["decision_time"], *WIN)]


def _arm_1m(m1):
    """1m CISDs per NY morning slice; keep those turning the in-progress 15m candle's wick."""
    sl = m1[cl.in_window(m1.index, PAD_START, WIN[1])]
    if sl.empty:
        return pd.DataFrame()
    lows, highs = sl["low"].to_numpy(float), sl["high"].to_numpy(float)
    t_ns = pd.DatetimeIndex(sl.index).tz_convert("UTC").as_unit("ns").asi8
    day = cl.to_ny(sl.index).normalize()
    out = []
    for _, g in sl.groupby(day, sort=True):
        b = cl.build_bars(g, "1min")
        ev = _cisd(b)
        if not ev.empty:
            out.append(ev[cl.in_window(ev["decision_time"], *WIN)])
    if not out:
        return pd.DataFrame()
    ev = pd.concat(out, ignore_index=True)
    conf = pd.DatetimeIndex(ev["confirm_time"]).tz_convert("UTC")
    bucket = conf.floor("15min")
    ext = pd.DatetimeIndex(ev["extreme_time"]).tz_convert("UTC")
    a = np.searchsorted(t_ns, bucket.as_unit("ns").asi8, side="left")
    z = np.searchsorted(t_ns, conf.as_unit("ns").asi8, side="right")       # incl. confirm bar
    ps, sg = ev["protected_swing"].to_numpy(float), ev["sgn"].to_numpy()
    wick = np.zeros(len(ev), bool)
    for k in range(len(ev)):
        if ext[k] < bucket[k] or z[k] <= a[k]:
            continue
        wick[k] = (ps[k] <= lows[a[k]:z[k]].min()) if sg[k] > 0 else (ps[k] >= highs[a[k]:z[k]].max())
    return ev[wick]


def detect(m1):
    parts = []
    for flag, ev in ((False, _arm_15m(m1)), (True, _arm_1m(m1))):
        if len(ev):
            parts.append(pd.DataFrame({
                "decision_time": pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC"),
                "direction": ev["sgn"].to_numpy(), "stop_px": ev["protected_swing"].to_numpy(float),
                "P": ev["confirm_close"].to_numpy(float), "extreme_time": ev["extreme_time"].to_numpy(),
                "is_1m": flag}))
    if not parts:
        return pd.DataFrame(columns=COLS)
    ev = pd.concat(parts, ignore_index=True)
    dt = pd.DatetimeIndex(ev["decision_time"])
    op = cl.open_at(dt, "18:00", m1=m1, max_delay_min=60)
    ph = cl.prior_hilo(dt, "1D", m1=m1, min_coverage=0.5)
    rh = cl.running_hilo(dt, "1D", m1=m1)
    O = op["price"].to_numpy(float)
    pdh, pdl = ph["high"].to_numpy(float), ph["low"].to_numpy(float)
    H, L = rh["high"].to_numpy(float), rh["low"].to_numpy(float)
    s, P, stop = ev["direction"].to_numpy(), ev["P"].to_numpy(float), ev["stop_px"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        inside = (pdl < O) & (O < pdh)
        rev_long = inside & (L < pdl) & (H < pdh)
        rev_short = inside & (H > pdh) & (L > pdl)
        keep = np.where(s > 0, rev_long, rev_short) & (s * (O - P) > 0) & (s * (P - stop) > 0)
    oav = pd.DatetimeIndex(op["time"]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    pav = pd.DatetimeIndex(ph["available_at"]).tz_convert("UTC")
    av = pd.to_datetime(np.maximum(np.maximum(dt.asi8, pav.asi8), oav.asi8), utc=True)
    ev = ev.assign(available_at=av, target_px=O, td=cl.trading_day(dt))[keep]
    ev = ev.sort_values(["decision_time", "extreme_time", "direction"], kind="stable")
    ev = ev.groupby(["td", "is_1m"], sort=False).head(1)                  # first per day per arm
    ev = ev.sort_values(["decision_time", "is_1m"], kind="stable").reset_index(drop=True)
    ev["is_1m"] = ev["is_1m"].astype(bool)
    return ev[COLS]


def detect_a(m1):
    ev = detect(m1)
    return ev[ev["is_1m"].to_numpy(bool)].drop(columns="is_1m").reset_index(drop=True)


RULES = [
    "18:00-NY trading day; O = first M1 open 18:00-19:00 NY; PDH/PDL = prior day (min_coverage 0.5); "
    "running high/low from M1 bars closed by the decision",
    "reversal day long at decision t: PDL < O < PDH, running low < PDL, running high < PDH, entry ref "
    "P (confirm close) < O; short mirrors; target = O (daily open)",
    "decision window [09:00, 12:00) NY; first qualifying event per trading day per arm",
    "15m arm: 15m phase-3 CISD (series_open, 2/2, max_wait 3, min_series 1) in the reversal direction; "
    "stop = protected swing",
    "1m arm (15m/1m fractal model): 1m phase-3 CISD in the reversal direction whose protected swing is "
    "the low (high) of the in-progress 15m candle up to the confirm bar and which confirms inside that "
    "15m candle; stop = protected swing; 1m CISDs computed per NY morning slice from 08:00",
    "decide at confirm close, enter next M1 open, exit at O / stop / 150 min; control NY clock +-30 min",
]
PARAMS = {"day_open": "18:00 NY", "open_max_delay_min": 60, "pdx_min_coverage": 0.5,
          "reversal_day": "day opened inside prior range; prior-day extreme swept, other side untaken; "
                          "daily open still ahead",
          "target": "daily open (18:00)", "window": "09:00-12:00 NY", "slice_start_1m": PAD_START,
          "cisd": "series_open, swing 2/2, max_wait 3, min_series 1",
          "wick_rule": "1m protected swing = in-progress 15m candle extreme, confirm inside that candle",
          "per_day": "first qualifying event per arm", "max_hold": HOLD,
          "ctrl_tod_tol_min": TOD_TOL, "grid4h": "n/a (no 4H bars read)"}
SRC = {
    "day_open": "method_spec §1.4: 18:00 NY daily candle",
    "open_max_delay_min": "declared-before-run: first traded minute of the reopen hour (as large-wick-target-adjustment)",
    "pdx_min_coverage": "declared-before-run: README trap 6, skip stub sessions",
    "reversal_day": "corpus: GRc5FVB5tdg 'we hit this previous low' / 'expansion into a low that is a target' "
                    "/ 'reversal day if you want to trade back into the range'",
    "target": "corpus: GRc5FVB5tdg 'We're back towards that daily open, which on a reversal day, that's the target.'",
    "window": "corpus: GRc5FVB5tdg 'what do we need to wait for, guys? 10:00 a.m.' (futures 4H close; "
              "forex-grid 4H close 09:00 NY) to method_spec §2.5 ny_am end 12:00",
    "slice_start_1m": "declared-before-run: 60 min warm-up for 1m swings/series before the window",
    "cisd": "phase3: meta/conjunction_preregistration.md §1.8-1.16 (locked CISD config)",
    "wick_rule": "corpus: GRc5FVB5tdg 'we let this wick form and then we look to trade the body higher' / "
                 "'Then we use the 15-minute and 1 minute fractal model.'",
    "per_day": "declared-before-run: one idea per day ('I only have one idea')",
    "max_hold": "phase3: §1.13 10 entry-TF periods at the setup's 15m timeframe (as rr-gated-entry-refinement)",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 — events all sit in 09:00-12:00 NY, concept is not "
                        "about timing, so the control holds the NY clock",
    "grid4h": "declared-before-run: no 4H bars are read; the 4H closure context is not modelled",
}


def _spread_note(res, label):
    """Descriptive per-arm numbers from the real trades (not part of the verdict)."""
    tr = res.pop("_trades", None)
    if tr is None:
        return ""
    risk = tr["risk"].to_numpy(float)
    gross = tr["gross_R"].to_numpy(float)
    rr = np.abs(tr["target"].to_numpy(float) - tr["entry"].to_numpy(float)) / risk
    adj = tr["net_R"].to_numpy(float) - tr["ctrl_mean_R"].to_numpy(float)
    g = tr["gate"].to_numpy(bool) if "gate" in tr.columns else np.ones(len(tr), bool)
    parts = []
    for name, m in (("1m", g), ("15m", ~g)):
        if m.any():
            parts.append(f"{name} arm n={int(m.sum())}: median stop {np.median(risk[m]):.2f} pt, "
                         f"median R-to-target {np.median(rr[m]):.1f}, target-hit "
                         f"{(tr['reason'].to_numpy()[m] == 'target').mean():.3f}, gross "
                         f"{gross[m].mean():+.3f}R, vs-control {np.nanmean(adj[m]):+.3f}R, net at "
                         + " / ".join(f"{c} pt {(gross[m] - c / risk[m]).mean():+.3f}R" for c in SPREAD_PTS)
                         + " spread")
    return f"{label} descriptive: " + "; ".join(parts)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    show = ("n", "n_gated", "n_complement", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
            "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped", "halves",
            "gated_vs_own_control", "complement")
    if "a" in which:
        ev = cl.cache_frame("ttfm_scalp_u1007a_rev_1m", lambda: detect_a(cl.load_m1()))
        print("a rows", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        print("probe", probe.get("passed"), probe.get("events_compared"))
        res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=TOD_TOL, keep_trades=True)
        note = _spread_note(res, "u1007a")
        for k in show:
            if res.get(k) is not None:
                print(f"  {k:22s} {res[k]}")
        print(note)
        print(cl.write_result(CID, "u1007a", res, operationalization={"rules": RULES + [
            "u1007a: trade_test on the 1m arm only, claim '+'"], "params": PARAMS},
            params_source=SRC, script=__file__, probe=probe,
            notes="Tests the 15m/1m model on reversal days (the switch's model) against a matched "
                  "random entry. Caveat (campaign lesson 1): the 1m stop sits at a fresh extreme, "
                  "which beats a random stop at the same distance generically, so this control "
                  "flatters the arm. " + note))
    if "b" in which:
        ev = cl.cache_frame("ttfm_scalp_u1007b_rev_1m_vs_15m", lambda: detect(cl.load_m1()))
        print("b rows", len(ev), "1m share", ev["is_1m"].mean())
        probe = cl.probe_lookahead(detect, ev, lookback="10D")
        print("probe", probe.get("passed"), probe.get("events_compared"))
        res = cl.gate_test(ev, "is_1m", mask_available_at="decision_time", max_hold=HOLD, claim="+",
                           ctrl_tod_tol_min=TOD_TOL, keep_trades=True)
        note = _spread_note(res, "u1007b")
        for k in show:
            if res.get(k) is not None:
                print(f"  {k:22s} {res[k]}")
        print(note)
        print(cl.write_result(CID, "u1007b", res, operationalization={"rules": RULES + [
            "u1007b: gate_test on both arms pooled, gate = 1m arm, claim '+' (on reversal-day setups the "
            "1m entry beats the 15m entry, each arm on its own qualifying days vs its own matched control)"], "params": PARAMS},
            params_source=SRC, script=__file__, probe=probe,
            notes="The 'poor R on the 15m' premise is geometric (a tighter stop to a fixed target); "
                  "the matched controls cancel geometry, so the diff asks whether the 1m timing adds "
                  "anything beyond it. Cost cancels in the diff; spread-adjusted means are below. " + note))
