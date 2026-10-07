"""positional-entry -- update u1007 (two new claims; readings a/b of entry_own_02a untouched).

u1007a  live_09 (Hlwq1dRjBZo, New York Open Live Q&A) -- GATE on the existing book:
  "a positional entry is a protected swings prior to the open of the new higher time frame
   candle ... How confident are you on this bias and that this low holds? ... would I try to
   take a positional entry at 10:00 a.m.? No. Because I'd want to first just let the 4hour
   candle form whatever wick ... the only reason I don't like this is just how deep this ran
   that makes so many failure swings ... I can trust this low. To me I can't trust this low."
  Base book = library reading a, unchanged: 4h forex-grid C2 (method_spec 3.2, one-sided), the
  most recent 15m CISD (series_open, 2/2, max_wait 3) in the C2 direction confirmed inside C2,
  protected swing intact at the C2 close and beyond C2's EQ; decide at the C2 close, enter at
  the C3 open, stop on the swing, 2R, 240 trading minutes.
  Gate column `trusted` = NOT (deep run AND failure swings), all read from bars closed by the
  C2 close:
    deep run      = C2's opposing run (open -> extreme against the trade, one-sided) > 1.0 x
                    its body (threshold_fits grade A large-wick / reversal-candle cut); he
                    ties the deep run to "Larger wick. Now we're at failure swings."
    failure swing = >= 2 confirmed 15m 2/2 counter-swings (swing highs for a long, lows for a
                    short) strictly inside the run into the protected extreme, the run being
                    the 15m bars from its origin (the C1+C2-span extreme on the other side,
                    taken before the protected extreme) to the protected extreme: the
                    reversal attempts the run left behind ("Failure swing. Failure swing.
                    Failure swing. Failure swing.").
  gate_test, claim '+': trusted positional entries beat untrusted ones (control-adjusted R).

u1007b  edu_01 (cWDnzI3lpUk, "How to Trade With a 9-5 Job", daily + hourly fractal model):
  "We expect the EQ to hold ... We expect 50% of this change in the state of delivery to hold.
   ... I just need my stop below both of those things, usually around the body of this
   opposing candle. And you can see how that gives me around two R to those highs."
  1D C2 (18:00 NY roll, one-sided), most recent 1h CISD in the C2 direction confirmed inside
  C2 with its protected swing intact at the C2 close. EQ = C2 wick-to-wick midpoint. CISD 50% =
  midpoint of the CISD series (series open level -> protected extreme), which sits inside the
  opposing candle body as he describes. Stop = below both: min(EQ, CISD50) for a long, max for
  a short; must be on the stop side of the C2 close. "Those highs" = the higher of C1/C2 high
  (lows for shorts); require >= 2R to them from the C2 close. Decide at the C2 close, enter at
  the C3 open (positional, before any IC-CISD can form), 2R target, one session (1380 trading
  minutes). trade_test, claim '+', control drawn on the daily-close grid.
  Not modelled: "confident on the move" (discretion). "No IC-CISD formed" is not a filter: at
  the C3 open none can have formed yet; using its later absence would read the future.

Rerun 2026-10-07 (vault context: Backtest Methodology Traps, Session Timing on Gold, Concept
Campaign lessons). Detectors, gate and stop rules unchanged. One change, to u1007a only: the
first run drew controls on any :00 M1 minute, so the 1-in-6 decisions at the 17:00 NY C2
close (entry at the 18:00 reopen, a gap artefact per Session Timing on Gold) were matched to
ordinary hours, and the gate could inherit a slot effect. Controls are now drawn on the 4h
forex close grid at the same NY slot (ctrl_grid="4h", ctrl_tod_tol_min=30; README trap 9).
u1007b already drew on the 1D close grid. Spread lesson (campaign lesson 2): cost cancels in
the differential, so the median stop in points and the R a 0.30 pt spread would cost are
printed and written to notes for both books.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import concept_lab as cl      # noqa: E402
from detectors.cisd import cisd_events          # noqa: E402
from detectors.primitives import swing_points   # noqa: E402

CID = "positional-entry"
DEEP_CUT = 1.0          # opposing run / body
MIN_FS = 2              # failure swings
MIN_RR_AVAIL = 2.0      # R available to "those highs"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "deep", "n_fs",
          "trusted"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def _empty(cols):
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})


def _c2_setups(m1, htf, ltf):
    """Yield (H, L, ev, i, d, j) for every one-sided HTF C2 i with its most recent aligned
    LTF CISD j confirmed inside C2 whose protected swing is intact at the C2 close and lies
    beyond the C2 close (entry_own_02a construct, verbatim)."""
    H = cl.build_bars(m1, htf)
    L = cl.build_bars(m1, ltf)
    ev = cisd_events(L[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty or len(H) < 3:
        return H, L, ev, []
    hh, hl, hc = (H[k].to_numpy() for k in ("high", "low", "close"))
    bull = np.r_[False, (hl[1:] < hl[:-1]) & (hc[1:] > hl[:-1])]
    bear = np.r_[False, (hh[1:] > hh[:-1]) & (hc[1:] < hh[:-1])]
    c2dir = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    st = H.index.as_unit("ns").asi8
    en = pd.DatetimeIndex(H["close_time"]).as_unit("ns").asi8
    cst = pd.DatetimeIndex(ev["confirm_time"]).as_unit("ns").asi8
    edir = np.where(ev["direction"] == "bullish", 1, -1)
    k = np.searchsorted(st, cst, side="right") - 1
    ok = (k >= 0) & (cst < en[np.clip(k, 0, None)])
    k = np.where(ok, k, -1)
    lst = L.index.as_unit("ns").asi8
    llo = L["low"].to_numpy(); lhi = L["high"].to_numpy()
    out = []
    for i in np.flatnonzero(c2dir != 0):
        d = c2dir[i]
        cand = np.flatnonzero((k == i) & (edir == d))
        if len(cand) == 0:
            continue
        j = cand[-1]
        sw = float(ev["protected_swing"].iloc[j])
        xs = np.searchsorted(lst, pd.Timestamp(ev["extreme_time"].iloc[j]).value)
        xe = np.searchsorted(lst, en[i], side="left")
        intact = llo[xs:xe].min() >= sw if d == 1 else lhi[xs:xe].max() <= sw
        beyond_close = sw < hc[i] if d == 1 else sw > hc[i]
        if intact and beyond_close:
            out.append((i, d, j, xs))
    return H, L, ev, out


def detect_a(m1):
    H, L, ev, setups = _c2_setups(m1, "4h", "15min")
    if not setups:
        return _empty(COLS_A)
    ho, hh, hl, hc = (H[k].to_numpy() for k in ("open", "high", "low", "close"))
    en = pd.DatetimeIndex(H["close_time"]).as_unit("ns").asi8
    st = H.index.as_unit("ns").asi8
    lst = L.index.as_unit("ns").asi8
    llo = L["low"].to_numpy(); lhi = L["high"].to_numpy()
    sp = swing_points(L[["open", "high", "low", "close"]], left=2, right=2)
    is_sh = sp["swing_high"].to_numpy(); is_sl = sp["swing_low"].to_numpy()
    rows = []
    for i, d, j, x in setups:
        sw = float(ev["protected_swing"].iloc[j])
        eq = (hh[i] + hl[i]) / 2.0
        if not (sw < eq if d == 1 else sw > eq):           # reading a EQ selection
            continue
        body = abs(hc[i] - ho[i])
        orun = (ho[i] - hl[i]) if d == 1 else (hh[i] - ho[i])
        deep = bool(orun > DEEP_CUT * body)
        s = min(np.searchsorted(lst, st[i - 1]), x)          # first 15m bar of C1
        if d == 1:
            org = s + int(np.argmax(lhi[s:x + 1]))
            n_fs = int(is_sh[org + 1:x].sum())
        else:
            org = s + int(np.argmin(llo[s:x + 1]))
            n_fs = int(is_sl[org + 1:x].sum())
        rows.append((en[i], d, sw, deep, n_fs))
    if not rows:
        return _empty(COLS_A)
    dt = pd.to_datetime(np.array([r[0] for r in rows]), utc=True)
    deep = np.array([r[3] for r in rows], bool)
    n_fs = np.array([r[4] for r in rows], np.int64)
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": np.array([r[1] for r in rows]),
                         "stop_px": np.array([r[2] for r in rows], float), "rr": 2.0,
                         "deep": deep, "n_fs": n_fs,
                         "trusted": ~(deep & (n_fs >= MIN_FS))})


def detect_b(m1):
    H, L, ev, setups = _c2_setups(m1, "1D", "1h")
    if not setups:
        return _empty(COLS_B)
    hh, hl, hc = (H[k].to_numpy() for k in ("high", "low", "close"))
    en = pd.DatetimeIndex(H["close_time"]).as_unit("ns").asi8
    rows = []
    for i, d, j, _ in setups:
        sw = float(ev["protected_swing"].iloc[j])
        lvl = float(ev["level"].iloc[j])
        c50 = (lvl + sw) / 2.0
        eq = (hh[i] + hl[i]) / 2.0
        if d == 1:
            stop = min(eq, c50)
            risk = hc[i] - stop
            reward = max(hh[i - 1], hh[i]) - hc[i]
        else:
            stop = max(eq, c50)
            risk = stop - hc[i]
            reward = hc[i] - min(hl[i - 1], hl[i])
        if risk > 0 and reward >= MIN_RR_AVAIL * risk:
            rows.append((en[i], d, stop))
    if not rows:
        return _empty(COLS_B)
    dt = pd.to_datetime(np.array([r[0] for r in rows]), utc=True)
    return pd.DataFrame({"decision_time": dt, "available_at": dt,
                         "direction": np.array([r[1] for r in rows]),
                         "stop_px": np.array([r[2] for r in rows], float), "rr": 2.0})


BASE_SRC = {
    "rr": "corpus: YAML execution targets '2R'; cWDnzI3lpUk 'You can see that goes and hits our two R'",
    "hold_basis": "declared-before-run: decisions sit at HTF closes, including the Friday close "
                  "before the weekend (trap 7)",
}
SRC_A = dict(BASE_SRC, **{
    "base_book": "phase3: entry_own_02a reading a construct, unchanged (the draft 'adds a confidence "
                 "and deep-run gate to the existing EQ-selection')",
    "htf": "corpus: Hlwq1dRjBZo 'let the 4hour candle form whatever wick'; library reading a 4H",
    "grid4h": "session_window_fit: forex grid (knob, trap 8)",
    "ltf": "corpus: YAML ltf 15m; library reading a",
    "selection": "corpus: xMFd_kfmIqI 'the stop on candle two is above the EQ of candle two'",
    "deep_run": "threshold_fits: large wick / reversal candle = opposing_run/|close-open| > 1.0 "
                "(grade A); corpus: Hlwq1dRjBZo 'Larger wick. Now we're at failure swings.' / "
                "'just how deep this ran'",
    "failure_swings": "corpus: Hlwq1dRjBZo 'how deep this ran that makes so many failure swings' "
                      "(he marks four); declared-before-run: >= 2 confirmed 15m 2/2 counter-swings "
                      "between the run origin (from the C1 open) and the protected extreme (plural; "
                      "2/2 = phase3 fractal)",
    "gate": "corpus: Hlwq1dRjBZo 'To me I can't trust this low' -> trusted = not (deep and failure swings)",
    "max_hold": "declared-before-run: hold for the C3 candle (4h of trading time), as reading a",
    "ctrl_grid": "declared-before-run (rerun): decisions sit on the 4h forex close grid, one in "
                 "six at the 17:00 NY close with entry at the 18:00 reopen; controls drawn on "
                 "the same grid (vault Session Timing on Gold: the reopen is a gap artefact)",
    "ctrl_tod_tol_min": "declared-before-run (rerun): README trap 9, the concept is not about "
                        "timing but its events sit at six NY slots; 30 min on the 4h grid = same slot",
})
SRC_B = dict(BASE_SRC, **{
    "htf": "corpus: cWDnzI3lpUk 'trade the daily and hourly fractal model'",
    "day_open_hour": "session_window_fit: settled 18:00 NY roll",
    "ltf": "corpus: cWDnzI3lpUk 'daily and hourly fractal model'",
    "eq": "corpus: cWDnzI3lpUk 'We expect the EQ to hold'; draft ambiguity -> C2 range, wick to "
          "wick (IPZjNI1B5a0)",
    "cisd50": "corpus: cWDnzI3lpUk 'We expect 50% of this change in the state of delivery to hold'; "
              "declared-before-run: 50% of the CISD series (series-open level -> protected extreme), "
              "which lies inside the opposing candle body per 'usually around the body of this "
              "opposing candle'",
    "stop": "corpus: cWDnzI3lpUk 'I just need my stop below both of those things' -> min(EQ, CISD50) "
            "long / max short, no buffer",
    "target_ref": "corpus: cWDnzI3lpUk 'that gives me around two R to those highs'; "
                  "declared-before-run: those highs = max(C1 high, C2 high) (mirror for shorts)",
    "min_rr_avail": "corpus: draft 'Proceed only if that gives about 2R to the target'; wM1s7UivQ08 "
                    "'if 2R is not achievable with that stop, do not take'",
    "max_hold": "declared-before-run: one session (1380 trading minutes), as library reading b",
    "ctrl_grid": "declared-before-run: every decision sits at the daily close (entry at the 18:00 NY "
                 "reopen), so controls are drawn on the 1D close grid to hold that clock fixed "
                 "(trap 9); ctrl_tod_tol_min cannot be used: 17:00 NY has no M1 bar",
})


def _stop_note(tr):
    """Median stop in points and the R a 0.30 pt spread costs at that stop (lesson 2)."""
    def one(r):
        m = float(np.median(r))
        return f"n={len(r)} median stop {m:.2f} pt (0.30 pt spread = {0.30 / m:.3f}R)"
    r = tr["risk"].to_numpy()
    if "gate" not in tr:
        return one(r)
    g = tr["gate"].to_numpy(bool)
    return f"gated {one(r[g])}; complement {one(r[~g])}"


def run():
    keys = ("n", "n_complement", "gate_firing_rate", "avg_R", "win_rate", "diff", "ci_lo",
            "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties",
            "ctrl_overlap", "halves")
    out = {}

    # ---- u1007a: gate on the reading-a book
    ev = cl.cache_frame("posentry_u1007a_4h15m_deep1_fs2_v1", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), "trusted", int(ev["trusted"].sum()), "deep", int(ev["deep"].sum()),
          "fs>=2", int((ev["n_fs"] >= MIN_FS).sum()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    print("a probe", probe.get("passed"))
    res = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="240min",
                       hold_basis="bars", ctrl_grid="4h", ctrl_tod_tol_min=30,
                       keep_trades=True)
    tr = res.pop("_trades")
    stops_a = _stop_note(tr)
    print("a", {k: res.get(k) for k in keys})
    print("a no-control trades", int((~np.isfinite(tr["ctrl_mean_R"])).sum()), "|", stops_a)
    params = {"base_book": "entry_own_02a reading a", "htf": "4h", "grid4h": "forex",
              "ltf": "15min", "selection": "protected swing beyond C2 EQ (wick-to-wick 50%)",
              "deep_run": f"C2 opposing run > {DEEP_CUT} x body", "failure_swings":
              f">= {MIN_FS} 15m 2/2 counter-swings inside the run", "gate": "trusted",
              "rr": 2.0, "max_hold": "240min", "hold_basis": "bars", "ctrl_grid": "4h",
              "ctrl_tod_tol_min": 30}
    rules = [
        "base: 4h forex-grid C2 (method_spec 3.2, one-sided); most recent 15m CISD (series_open, "
        "2/2, max_wait 3) in the C2 direction confirmed inside C2, swing intact at the C2 close, "
        "beyond the C2 close and beyond C2's EQ; decide at the C2 close, enter C3 open, stop on "
        "the swing, 2R, 240 trading min (entry_own_02a reading a)",
        "deep run: C2 opposing run (open -> low for a long, open -> high for a short) > 1.0 x body",
        "failure swings: 15m 2/2 swing highs (long; lows for short) strictly between the run "
        "origin (highest 15m high from the C1 open to the protected extreme) and the protected "
        "extreme; >= 2",
        "gate trusted = not (deep run and failure swings); claim '+': trusted beats untrusted on "
        "control-adjusted R",
    ]
    out["u1007a"] = cl.write_result(
        CID, "u1007a", res, operationalization={"rules": rules, "params": params},
        params_source=SRC_A, script=__file__, probe=probe,
        notes="Tests only the live_09 gate on the existing reading-a book. 'Confidence in the "
              "bias' is discretionary and not modelled; the concrete trigger he shows (deep run "
              "leaving failure swings) is. The alternative action ('let the 4H wick form first') "
              "is not traded here; the complement arm is what positioning anyway would earn. "
              "Design note (before any test call, no outcome seen): the run window was first cut "
              "at the C2 open; a detector-only dry run showed the gate firing on 2.6% of events "
              "because a 2/2 fractal rarely fits two swings inside one 4h candle, so the run "
              "origin was moved once to the C1 open (the decline into C2's sweep) and then frozen. "
              "RERUN with vault context: the first u1007a run (controls on any :00 minute) gave "
              "UNDERPOWERED, diff +0.012R [-0.071, +0.099], MDE 0.121, n 2159/1329; this run "
              "holds the 4h slot in the control (ctrl_grid 4h, tod 30). Traps checked: swings "
              "counted need 2 right bars, all before the CISD confirm (>= extreme + 3 bars) inside "
              "C2, so no in-progress bar is read; both arms stop at a fresh protected swing, so the "
              "structural-stop confound cancels in the gate differential. "
              f"Spread lesson (cost cancels in diff): {stops_a}.")
    print(out["u1007a"])

    # ---- u1007b: EQ + 50%-of-CISD positional stop, daily/hourly
    ev = cl.cache_frame("posentry_u1007b_1d1h_eq_c50_rr2_v1", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="45D")
    print("b probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="1380min", hold_basis="bars", ctrl_grid="1D",
                        keep_trades=True)
    tr = res.pop("_trades")
    stops_b = _stop_note(tr)
    print("b", {k: res.get(k) for k in keys})
    print("b", stops_b)
    params = {"htf": "1D", "day_open_hour": 18, "ltf": "1h", "eq": "C2 (high+low)/2",
              "cisd50": "(series_open level + protected extreme)/2",
              "stop": "min(EQ, CISD50) long / max short", "target_ref": "max(C1,C2) high / min low",
              "min_rr_avail": MIN_RR_AVAIL, "rr": 2.0, "max_hold": "1380min", "hold_basis": "bars",
              "ctrl_grid": "1D"}
    rules = [
        "1D C2 (18:00 NY roll, method_spec 3.2, one-sided); most recent 1h CISD (series_open, 2/2, "
        "max_wait 3) in the C2 direction confirmed inside C2, protected swing intact at the C2 "
        "close and beyond it",
        "stop below both C2 EQ and 50% of the CISD series: min(EQ, CISD50) long, max short; must "
        "be on the stop side of the C2 close",
        "take only if (max(C1 high, C2 high) - C2 close) >= 2 x (C2 close - stop) (mirror short)",
        "decide at the C2 close, enter at the first M1 open of C3 (positional), 2R target, 1380 "
        "trading min; control on the 1D close grid",
    ]
    out["u1007b"] = cl.write_result(
        CID, "u1007b", res, operationalization={"rules": rules, "params": params},
        params_source=SRC_B, script=__file__, probe=probe,
        notes="Tests only the edu_01 stop rule (EQ + 50% of CISD, about 2R to the highs) as a "
              "positional daily/hourly book. 'Confident on the move' not modelled. 'IC-CISD has "
              "not formed' is satisfied by construction at the C3 open; filtering on its later "
              "absence would be look-ahead. RERUN with vault context: design unchanged (control "
              "already on the 1D close grid, entering at the same 18:00 reopen); traps checked: "
              "the stop is a midpoint level, not a fresh extreme, so the structural-stop confound "
              "of campaign lesson 1 does not flatter it; the effective n (trading days) is the "
              "binding limit. "
              f"Spread lesson: {stops_b}.")
    print(out["u1007b"])
    return out


if __name__ == "__main__":
    run()
