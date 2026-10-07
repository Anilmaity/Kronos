"""large-wick-target-adjustment — update_20261007 new claims (prior readings a/b untouched).

Entry book = the canonical 1h CISD (phase-3 locked; stop at protected swing, 10h hold),
reused from risk_own_02b/_base.py, since the concept changes only the targets.

Reading u1007a (live_08/09: the ORDERED ladder, third rung):
  large-wick day as in readings a/b (18:00 NY day; O = day open, H/L running hi/lo,
  P = CISD close; large = opposing run > 1.0 x max(body_d, 0)); price still on the wick
  side of the open; the ladder must be strictly ordered in the trade direction:
  short P > O > L > PDL (long P < O < H < PDH). Target = rung 3 (PDL short / PDH long),
  i.e. the trade is held through rung 1 (daily open) and rung 2 (intraday extreme).
  trade_test, claim '+'.
Reading u1007b (live_03: soft invalidation trigger):
  daily C2 = previous trading day that swept the day before it and closed back inside
  (bearish C2: H1 > H2 and C1 < H2; bullish mirror). Bias for today = the C2 direction.
  Book = today's CISD trades in the bias direction, target = the C2 far extreme
  (PDL bearish / PDH bullish), kept only if beyond P. Gate = soft invalidation: some
  1h close of today (closed by the decision) beyond the C2 EQ = (H1+L1)/2 against the bias.
  Claim '-': soft-invalidated trades toward the expansion target do worse.

AUDIT 2026-10-07 (vault context), same readings, same hypotheses:
  * both readings now use a NY time-of-day matched control (ctrl_tod_tol_min=30, README
    trap 9). u1007a events sit at 0.107 of their mass in 18:00-01:59 NY vs 0.313 for the
    base CISD book (the ladder needs the day to have traded both sides of the open);
    u1007b's arms differ by clock (complement 0.536 in 18-01 NY vs gated 0.232), because
    "some 1h close of today beyond EQ" fires more often later in the day.
  * u1007b: an outside day that is BOTH a bearish and a bullish C2 has no C2 direction;
    it was silently assigned bearish (13.9% of events). Now excluded (bias 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "risk_own_02b"))
from _base import cl, np, pd, cisd_book, show, PHASE3_SRC, HOLD_SRC  # noqa: E402

CID = "large-wick-target-adjustment"
HOLD = "10h"
WICK_CUT = 1.0
OPEN_DELAY = 60
TOD = 30


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    ev = cisd_book(m1, "1h")
    if ev.empty:
        return pd.DataFrame(columns=cols)
    dt = pd.DatetimeIndex(ev["decision_time"])
    op = cl.open_at(dt, "18:00", m1=m1, max_delay_min=OPEN_DELAY)
    rh = cl.running_hilo(dt, "1D", m1=m1)
    ph = cl.prior_hilo(dt, "1D", m1=m1, min_coverage=0.5)
    s = ev["direction"].to_numpy()
    O = op["price"].to_numpy(float)
    H, L = rh["high"].to_numpy(float), rh["low"].to_numpy(float)
    P = ev["confirm_close"].to_numpy(float)
    pdx = np.where(s > 0, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    ext = np.where(s > 0, H, L)                      # rung 2: intraday extreme, trade side
    opp = np.where(s > 0, O - L, H - O)
    large = opp > WICK_CUT * np.maximum(s * (P - O), 0.0)
    with np.errstate(invalid="ignore"):
        ladder = (s * (O - P) > 0) & (s * (ext - O) > 0) & (s * (pdx - ext) > 0)
    keep = large & ladder & np.isfinite(O) & np.isfinite(ext) & np.isfinite(pdx)
    pav = pd.DatetimeIndex(ph["available_at"]).tz_convert("UTC")
    oav = pd.DatetimeIndex(op["time"]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    av = pd.to_datetime(np.maximum(np.maximum(dt.asi8, pav.asi8), oav.asi8), utc=True)
    out = pd.DataFrame({"decision_time": dt, "available_at": av, "direction": s,
                        "stop_px": ev["stop_px"].to_numpy(float), "target_px": pdx})
    return out[keep].reset_index(drop=True)


def detect_b(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "soft_inv"]
    ev = cisd_book(m1, "1h")
    if ev.empty:
        return pd.DataFrame(columns=cols)
    dt = pd.DatetimeIndex(ev["decision_time"])
    c2 = cl.prior_hilo(dt, "1D", m1=m1, min_coverage=0.5)            # C2 = yesterday
    c1 = cl.prior_hilo(dt, "1D", n_back=2, m1=m1, min_coverage=0.5)  # C1 = day before
    H1, L1, C1c = (c2[k].to_numpy(float) for k in ("high", "low", "close"))
    H2, L2 = c1["high"].to_numpy(float), c1["low"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        bear = (H1 > H2) & (C1c < H2)
        bull = (L1 < L2) & (C1c > L2)
        bias = np.where(bear & ~bull, -1, np.where(bull & ~bear, 1, 0))  # both = undecidable
    eq = (H1 + L1) / 2
    # today's 1h closes so far: running max/min close per trading day, read as-of
    b = cl.build_bars(m1, "1h")
    td = cl.trading_day(b.index)
    k = pd.Series(td.to_numpy())
    b["cmax"] = pd.Series(b["close"].to_numpy()).groupby(k).cummax().to_numpy()
    b["cmin"] = pd.Series(b["close"].to_numpy()).groupby(k).cummin().to_numpy()
    b["td"] = td
    a = cl.asof(b, dt)
    same = pd.DatetimeIndex(a["td"]).to_numpy() == cl.trading_day(dt - pd.Timedelta(minutes=1)).to_numpy()
    s = ev["direction"].to_numpy()
    P = ev["confirm_close"].to_numpy(float)
    tgt = np.where(s > 0, H1, L1)
    with np.errstate(invalid="ignore"):
        inv = np.where(bias < 0, a["cmax"].to_numpy(float) > eq, a["cmin"].to_numpy(float) < eq)
        run = np.where(bias < 0, a["cmax"].to_numpy(float), a["cmin"].to_numpy(float))
        keep = (bias == s) & same & np.isfinite(eq) & np.isfinite(run) & (s * (tgt - P) > 0)
    av = np.maximum(dt.asi8, pd.DatetimeIndex(c2["available_at"]).tz_convert("UTC").asi8)
    av = np.maximum(av, pd.DatetimeIndex(c1["available_at"]).tz_convert("UTC").asi8)
    out = pd.DataFrame({"decision_time": dt, "available_at": pd.to_datetime(av, utc=True),
                        "direction": s, "stop_px": ev["stop_px"].to_numpy(float),
                        "target_px": tgt, "soft_inv": inv.astype(bool)})
    return out[keep].reset_index(drop=True)


BASE = ["entry: 1h CISD (series_open, 2/2 swings, max_wait 3, min_series 1), decide at the "
        "confirming 1h close, enter next M1 open, stop at the protected swing, hold 10h"]
PARAMS = {"entry_tf": "1h", "max_hold": HOLD, "daily_open": "18:00 NY",
          "pdx_min_coverage": 0.5, "ctrl_tod_tol_min": TOD}
SRC = {"entry_tf": PHASE3_SRC + " — the concept changes targets only",
       "max_hold": HOLD_SRC,
       "daily_open": "method_spec §1.4: 18:00 NY daily candle (same as prior readings a/b)",
       "pdx_min_coverage": "declared-before-run: README trap 6, skip stub sessions",
       "ctrl_tod_tol_min": "declared-before-run (audit, decided from event clock profiles, "
                           "not outcomes): README trap 9 - not a timing concept but events "
                           "cluster in NY hours (u1007a 18-01 NY share 0.107 vs base 0.313; "
                           "u1007b complement 0.536 vs gated 0.232)"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame("lwta_u1007a_ladder_rung3", lambda: detect_a(cl.load_m1()))
        print("a rows", len(ev))
        probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=TOD)
        show(res)
        op = {"rules": BASE + [
            "running 18:00 NY day: O = first M1 open 18:00-19:00 NY, H/L running high/low, "
            "P = confirm close; large wick = opposing run > 1.0 x max(direction*(P-O),0)",
            "ordered ladder strictly in trade direction: short P > O > L > PDL, long "
            "P < O < H < PDH (rung1 daily open, rung2 intraday extreme, rung3 PDL/PDH)",
            "target = rung 3 (PDL short / PDH long); claim '+' vs matched random entry"],
            "params": {**PARAMS, "wick_cut": WICK_CUT, "open_max_delay_min": OPEN_DELAY,
                       "target": "rung 3 previous-day extreme"}}
        print(cl.write_result(CID, "u1007a", res, operationalization=op, params_source={
            **SRC,
            "wick_cut": "threshold_fits: large wick = opposing_run/|body| > 1.0 (grade A; "
                        "same as readings a/b)",
            "open_max_delay_min": "declared-before-run: first traded minute of reopen hour",
            "target": "corpus: K7XVj2w3CP4 'daily open, then it would be intraday lows, then "
                      "previous day low' / 'It's always in that order.'"},
            script=__file__, probe=probe,
            notes="Tests the new third rung (PDL/PDH) held through the ordered ladder; "
                  "rung 1 (daily open) was reading b. Order itself is geometric given the "
                  "ladder filter, so only reachability of rung 3 is scored."))
    if "b" in which:
        ev = cl.cache_frame("lwta_u1007b_c2eq_softinv", lambda: detect_b(cl.load_m1()))
        print("b rows", len(ev), "soft_inv share", ev["soft_inv"].mean())
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        res = cl.gate_test(ev, "soft_inv", mask_available_at="decision_time", max_hold=HOLD,
                           claim="-", ctrl_tod_tol_min=TOD)
        show(res)
        op = {"rules": BASE + [
            "daily C2 = previous 18:00 NY day; bearish C2: its high > the prior day's high "
            "and its close < that high (bullish mirror on lows); bias = C2 direction; a day "
            "that is both (outside day closing inside) has no direction and is excluded",
            "book = CISD trades in the bias direction; target = C2 low (bearish) / C2 high "
            "(bullish), kept only if beyond P",
            "gate soft_inv = a 1h close of today (closed by the decision) beyond the C2 EQ "
            "(H+L)/2 against the bias; claim '-' (less expansion after soft invalidation)"],
            "params": {**PARAMS, "c2_def": "sweep of C1 extreme + close back inside; "
                                           "both-sided outside days excluded",
                       "eq": "midpoint of C2 range", "inv_tf": "1h close"}}
        print(cl.write_result(CID, "u1007b", res, operationalization=op, params_source={
            **SRC,
            "c2_def": "method_spec: TTrades fractal model C2 (sweep of C1 extreme, close back "
                      "inside); corpus rVRk4MLTJSs 'daily close bearish ... daily C2 EQ'",
            "eq": "corpus: rVRk4MLTJSs 'one hour close above daily C2 EQ'",
            "inv_tf": "corpus: rVRk4MLTJSs 'if one hour close above daily C2 EQ' / 'soft "
                      "invalidation of the bias'",
            "target": "corpus: rVRk4MLTJSs 'you're not really looking for it to go super low' "
                      "— expansion target = C2 far extreme"},
            script=__file__, probe=probe,
            notes="15m-C2 no-entry claim (live_09) not scored: discretionary 'not ideal'."))
