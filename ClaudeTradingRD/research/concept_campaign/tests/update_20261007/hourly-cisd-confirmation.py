"""hourly-cisd-confirmation, update_20261007_live_03: substitute confirmations on a large manipulation leg.

New claim only (prior readings a/b = bare H1 CISD are untouched). Source rVRk4MLTJSs (New York Open
Live Q&A): viewer swept the previous day low on gold but the hourly CISD series spanned the whole prior
daily candle. TTrades: "you don't really care to wait for this CISD level ... by the time you get that
closure through, you're already creating like most of the daily range ... we could use some sort of
higher time frame candle closures or continuation. Okay, here's a 4hour candle closure. You could use
that or you can use some sort of new continuation. Right here, we reach into a fair value gap close over
it ... in the cases where you have a very large manipulation leg".

Detector (pure, causal, 1H bars, NY day 18:00 roll). Bullish (bearish mirrored):
  - the day's running low takes out the previous trading day's low (the swept-PDL case of the question);
  - the 1H CISD level for that low = high of the consecutive down-close series that made it (reading a
    of the prior test, same run rule);
  - "large manipulation leg": CISD level - low >= 0.5 x ADR20 ("most of the daily range" = more than half;
    ADR20 = mean range of the 20 prior trading days, built from the input's 1H bars);
  - the substitute must close BEFORE the CISD close-through (once the CISD has closed the substitute is moot);
  - reading u1007a: a completed 4H (forex grid) candle, closing at/after the low's hour, closes above the
    prior 4H candle's high, still below the CISD level;
  - reading u1007b: a 1H close above the top of the lowest still-open bearish 1H FVG formed in the day's
    down leg (between the day open and the low), still below the CISD level.
  - one event per extreme; a new low re-arms. Decide at the confirming close, next M1 open entry, stop at
    the day's low, 2R, 10h (identical execution to prior readings a/b).

AUDIT 2026-10-07 (vault-context re-run): detector unchanged. Control fixed: events cluster in NY hours
(u1007a fires only at 4H closes, 29% at the 17:00 day close -> 18:00 reopen entry; u1007b 53% in 09-14 NY)
but the concept is not about timing, so README trap 9 requires the control to hold the NY clock
(ctrl_tod_tol_min=30). The first run drew controls at any hour.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import concept_lab as cl     # noqa: E402

TF = "1h"
MAX_HOLD = "10h"
RR = 2.0
MAX_SERIES = 10
LEG_FRAC = 0.5
ADR_N = 20
MIN_DAY_BARS = 12
CTRL_TOD = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def _run(o, c, i, day_start, bullish):
    """Consecutive opposing-close run making the extreme at i (same rule as prior readings a/b)."""
    def q(k):
        return (c[k] < o[k]) if bullish else (c[k] > o[k])
    end = i
    while end > day_start and not q(end):
        end -= 1
        if i - end > 2:
            return -1, -1
    if not q(end):
        return -1, -1
    start = end
    while start > day_start and q(start - 1) and (end - start + 1) < MAX_SERIES:
        start -= 1
    return start, end


def _fvg_level(h, l, c, ds, pos, bullish):
    """Nearest still-open opposing FVG of the down (up) leg, formed in [ds, pos]; NaN if none."""
    best = np.nan
    for k in range(ds + 2, pos + 1):
        if bullish and h[k] < l[k - 2]:                    # bearish FVG, top = l[k-2]
            top = l[k - 2]
            if k == pos or c[k + 1:pos + 1].max() <= top:
                best = top if np.isnan(best) else min(best, top)
        if not bullish and l[k] > h[k - 2]:                # bullish FVG, bottom = h[k-2]
            bot = h[k - 2]
            if k == pos or c[k + 1:pos + 1].min() >= bot:
                best = bot if np.isnan(best) else max(best, bot)
    return best


def make_detect(kind):
    def detect(m1):
        b = cl.build_bars(m1, TF)
        if len(b) < 3:
            return pd.DataFrame({k: [] for k in COLS})
        o, h, l, c = (b[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
        ct = pd.DatetimeIndex(b["close_time"])
        day = cl.trading_day(b.index).to_numpy()
        # per-day stats from the input's 1H bars (only completed prior days are read)
        dfd = pd.DataFrame({"d": day, "h": h, "l": l})
        g = dfd.groupby("d", sort=True).agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
        g = g[g.n >= MIN_DAY_BARS]                         # drop stub sessions
        rng = (g.h - g.l)
        # map every day (stubs too) to the last full day strictly before it
        alld = pd.Index(np.unique(day))
        idx = np.searchsorted(g.index.to_numpy(), alld.to_numpy(), side="left") - 1
        pmap = {}
        for d, ix in zip(alld, idx):
            if ix >= 0:
                r = g.iloc[ix]
                a = rng.iloc[max(0, ix - ADR_N + 1):ix + 1]
                pmap[d] = (r.h, r.l, a.mean() if len(a) == ADR_N else np.nan)
        h4 = {}
        if kind == "4h":
            b4 = cl.build_bars(m1, "4h")
            c4 = b4["close"].to_numpy(float)
            ph = b4["high"].shift(1).to_numpy(float)
            pl = b4["low"].shift(1).to_numpy(float)
            for t, cc, a, z in zip(pd.DatetimeIndex(b4["close_time"]), c4, ph, pl):
                h4[t] = (cc, a, z)
        rows = []
        n = len(b)
        for bullish in (True, False):
            ds, ext, pos, armed, lev, sub = 0, np.nan, -1, False, np.nan, np.nan
            pinfo = None
            for j in range(n):
                if j == 0 or day[j] != day[j - 1]:
                    ds, ext, pos, armed, lev, sub = j, np.nan, -1, False, np.nan, np.nan
                    pinfo = pmap.get(day[j])
                x = l[j] if bullish else h[j]
                if pos < 0 or (x < ext if bullish else x > ext):
                    ext, pos, armed = x, j, False
                    if pinfo is None or np.isnan(pinfo[2]):
                        continue
                    pdh, pdl, adr = pinfo
                    if not ((ext < pdl) if bullish else (ext > pdh)):
                        continue
                    s, e = _run(o, c, j, ds, bullish)
                    if s < 0:
                        continue
                    lev = h[s:e + 1].max() if bullish else l[s:e + 1].min()
                    if abs(lev - ext) < LEG_FRAC * adr:
                        continue
                    sub = _fvg_level(h, l, c, ds, pos, bullish) if kind == "fvg" else np.nan
                    if kind == "fvg" and np.isnan(sub):
                        continue
                    armed = True
                if not armed:
                    continue
                if (c[j] > lev) if bullish else (c[j] < lev):      # CISD closed first: moot
                    armed = False
                    continue
                if kind == "4h":
                    q = h4.get(ct[j])
                    hit = q is not None and ((q[0] > q[1]) if bullish else (q[0] < q[2]))
                else:
                    hit = j > pos and ((c[j] > sub) if bullish else (c[j] < sub))
                if hit:
                    rows.append((ct[j], 1 if bullish else -1, ext))
                    armed = False
        if not rows:
            return pd.DataFrame({k: [] for k in COLS})
        rows.sort(key=lambda r: (r[0], r[1]))
        t = pd.DatetimeIndex([r[0] for r in rows])
        return pd.DataFrame({"decision_time": t, "available_at": t,
                             "direction": np.array([r[1] for r in rows], dtype=int),
                             "stop_px": np.array([r[2] for r in rows], dtype=float), "rr": RR})
    return detect


PARAMS_SOURCE = {
    "context": "corpus: rVRk4MLTJSs 'gold today, we sweep previous day [low] ... hourly CST [CISD]' "
               "(the question's swept-PDL case); 'in the cases where you have a very large manipulation leg'",
    "tf": "corpus: hourly-cisd-confirmation.yaml 'On the 1H chart ... inside the candidate daily candle'; "
          "rVRk4MLTJSs 'hourly CST [CISD]'",
    "series_rule": "phase3: detectors.cisd run rule (extreme bar or run ending <=2 bars before it, max 10 "
                   "candles), restricted to the day, same as prior reading a",
    "min_day_bars": "declared-before-run: README trap 6 stub sessions; a prior day with <12 1H bars is skipped "
                    "as PDH/PDL/ADR source (min_coverage ~0.5 equivalent)",
    "cisd_level": "phase3/prior reading a: high of the down-close series that made the low (run<=10, <=2 "
                  "bars back), same as hourly-cisd-confirmation__a",
    "leg_frac": "declared-before-run: 'by the time you get that closure through, you're already creating "
                "like most of the daily range' (rVRk4MLTJSs) -> 'most' read as > half: CISD distance >= 0.5 "
                "x ADR20; the source gives no number (draft ambiguity), one pre-declared value, not searched",
    "adr_n": "declared-before-run: conventional 20-day ADR for 'the daily range'",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 / vault Concept Campaign lesson 3 - not a timing "
                        "concept but events cluster in NY hours (4H closes only; NY session), so the control "
                        "holds the NY clock +/-30 min (audit fix of the first run)",
    "substitute": "corpus: rVRk4MLTJSs 'here's a 4hour candle closure. You could use that' (reading u1007a: "
                  "4H close beyond the prior 4H candle's extreme) / 'we reach into a fair value gap close over "
                  "it' (reading u1007b: 1H close over the nearest open opposing FVG of the leg)",
    "grid4h": "method_spec: forex 4H grid 17/21/01/05/09/13 NY (README trap 8 default)",
    "stop": "corpus: hourly-cisd-confirmation.yaml execution.stop 'Beyond the confirmed extreme'",
    "rr": "phase3: §1.12 2R (same as prior readings)",
    "max_hold": "phase3: §1.13 10 entry-TF bars (same as prior readings)",
    "day_open_hour": "session_window_fit: 18:00 NY daily candle (settled)",
}


def run(reading, kind):
    detect = make_detect(kind)
    ev = cl.cache_frame(f"u1007_hcisd_sub_{kind}", lambda: detect(cl.load_m1()))
    print(reading, kind, "events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=CTRL_TOD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    sub_rule = ("a completed forex-grid 4H candle closes beyond the prior 4H candle's high (low)"
                if kind == "4h" else
                "a 1H close over the nearest still-open opposing 1H FVG formed in the leg into the extreme")
    op = {"rules": [
        "1H bars, NY trading day (18:00 roll); day's running low (high) must take out the previous full "
        "day's low (high)",
        "CISD level = high (low) of the consecutive down- (up-) close 1H series that made the extreme",
        f"large leg: |CISD level - extreme| >= {LEG_FRAC} x ADR{ADR_N} (prior full days)",
        f"substitute confirmation before any CISD close-through: {sub_rule}",
        "one event per extreme (new extreme re-arms); decide at the confirming close, next M1 open; stop "
        "at the day's extreme; 2R; 10h"],
        "params": {"tf": TF, "day_open_hour": 18, "series_rule": "run<=10,<=2 bars back",
                   "cisd_level": "series_extreme", "leg_frac": LEG_FRAC, "adr_n": ADR_N,
                   "min_day_bars": MIN_DAY_BARS, "substitute": kind, "grid4h": "forex",
                   "stop": "day_extreme", "rr": RR, "max_hold": MAX_HOLD,
                   "ctrl_tod_tol_min": CTRL_TOD}}
    p = cl.write_result("hourly-cisd-confirmation", reading, res, operationalization=op,
                        params_source=PARAMS_SOURCE, script=__file__, probe=probe,
                        notes="Tests only the new substitute-confirmation claim (rVRk4MLTJSs). Source "
                              "calls it a discretionary allowance; mechanically the trend is unchanged "
                              "until the CISD close.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["u1007a", "u1007b"]
    if "u1007a" in which:
        run("u1007a", "4h")
    if "u1007b" in which:
        run("u1007b", "fvg")
