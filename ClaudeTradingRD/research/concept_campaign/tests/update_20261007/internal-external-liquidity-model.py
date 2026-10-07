"""internal-external-liquidity-model, readings u1007a / u1007b (update_20261007_edu_03,
video vMq1l8Zzzjw "Internal & External Liquidity Using the TTrades Fractal Model").

NEW claim only. The library reading (internal-external-liquidity-model.json, video
mwmWNCTEYtY: PDH/PDL stop raid inside a kill zone + 5m MSS + FVG retrace, 2R; n=227,
UNDERPOWERED) is untouched. vMq1l8Zzzjw gives a different execution recipe:
  * HTF: a candle-2 closure AT a fair value gap (internal liquidity) gives the draw to
    external liquidity = "the swing low that made the swing high" (mirror);
  * drop to the aligned LTF and wait for a valid fractal model: the change in the state of
    delivery, then "a new protected swing ... because we reach into a fair value gap and then
    close through this level"; enter on the open of the next candle;
  * stop "on this high or on the bodies"; "look for a 2R, which is right around that lower
    time frame target", or hold runners to the higher time frame target;
  * no kill zone / time filter anywhere in the video.

Declared before the first run (bearish described; bullish mirrors):
  ladder   H1 -> 5m, his worked example ("We're trading this hourly internal to external
           model right here"; "go to the 5-minute time frame and wait for a valid fractal
           model"). One ladder only: the others (D/4H/15m, W/4H/15m, 15m/1m) are the same
           rule shifted ("It is fractal"), and testing each would be a forking path.
  HTF C2   H1 bar i: high > previous high and close < previous high.
  at FVG   some bearish H1 FVG (3-bar gap, stamped on its 3rd bar k, i-120 <= k <= i-1) is
           not yet fully filled before i (max high of bars k+1..i-1 < gap top) and C2's high
           reaches into it (high_i >= gap bottom).
  draw     external = the latest H1 2/2 swing low confirmed by bar i (p <= i-2) that no bar
           p+1..i has traded through; none -> no setup. Target level = that low.
  LTF      5m bars, phase-3 locked CISD (series_open, swing 2/2, max_wait 3).
           E1 = a bearish 5m CISD whose extreme bar starts at/after the C2 open (the change in
                the state of delivery at/after the HTF reversal);
           E2 = a later bearish 5m CISD (the continuation) whose extreme is a LOWER high than
                E1's, whose extreme bar comes after E1's confirm bar, whose extreme high reaches
                into a bearish 5m FVG formed after E1's extreme (first gap bar >= E1 extreme,
                3rd bar < E2 extreme, not fully filled before E2's extreme), with no 5m high
                above E1's extreme between E1's extreme and E2's confirm bar;
           E2 must confirm in C3 (the confirming 5m bar starts inside the next H1 bar).
           The H1 draw must still be open: every 5m low from C3's open to E2's confirm bar is
           above the target, and the target is below E2's confirm close.
  trade    first E2 per H1 setup; decide at E2's confirm close, enter next M1 open (= the open
           of the new candle); stop = E2's extreme (the new protected swing, wick reading).
  u1007a   target 2R; time exit at the close of H1 C4 ("trade candle three ... or even candle
           four"), held in trading minutes (hold_basis 'bars').
  u1007b   same entries and stop; target = the H1 external level (the runner to the higher
           time frame target); time cap one trading session (1380 trading minutes: "it takes
           into the next day").
  control  harness matched random entries (+-30 d, same direction / stop / target distance /
           hold), NY clock held within +-30 min (README trap 9: not a timing claim, but the
           5m CISD-continuation events cluster in active hours).
Not modelled: the bodies stop, SMT/PSP (optional confluence in the video), the T-spot POI,
the daily bias layer above the H1 (the C2-at-FVG itself carries the draw in the claim).

Vault-context checks (Backtest Methodology Traps 1-9, Concept Campaign 2026-09-23 lessons):
  (1) geometry: scored on net R vs a matched control, never a raw win/hit rate;
  (2) exits on M1, stop-first same-bar ties (harness);
  (3)/(9) every bar read is closed by the decision: H1 bars <= C2 (C3 is used only for its
      open/nominal close stamps), 5m bars <= E2's confirm bar; probed symmetrically;
  (4) regime-matched control (harness, +-30 d);
  (6) MDE / power from the harness, sanity floor on;
  (7) no sparse join: every condition is evaluated per setup;
  (8) no point thresholds (structure only), certified 2016+ span, 1h bars UTC-aligned (no 4H
      grid involved).
  Campaign lesson 1: the stop sits at a fresh 5m swing extreme, so a control that only matches
  the stop DISTANCE flatters the book; lesson 2: 5m protected-swing stops are small, so spread
  at 0.45 pt (campaign base) and ~0.60 pt (S5 median, XAUUSD Data Inventory) is reported.
  Overlap with the refuted Conjunction Test (5m/1H/1D, bias -> POI -> CISD, 2R): this book
  differs in the C2-at-FVG trigger, the continuation (second) CISD entry and the external
  target, but is not independent of it.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np                                        # noqa: E402
import pandas as pd                                       # noqa: E402

import concept_lab as cl                                  # noqa: E402
from detectors.cisd import cisd_events                    # noqa: E402
from detectors.primitives import fair_value_gaps, swing_points   # noqa: E402

CID = "internal-external-liquidity-model"
OHLC = ["open", "high", "low", "close"]
CISD_KW = dict(level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
FVG_LOOKBACK = 120                      # H1 bars (~one trading week)
RR = 2.0
C4 = pd.Timedelta("60min")
RUNNER_HOLD = pd.Timedelta("1380min")   # one 23h trading session, in trading minutes
TOD_TOL = 30
SPREAD_PTS = (0.45, 0.60)
BASE_COLS = ["decision_time", "available_at", "direction", "stop_px", "target_ext", "max_hold"]


def _empty():
    return pd.DataFrame({"decision_time": pd.Series(dtype="datetime64[ns, UTC]"),
                         "available_at": pd.Series(dtype="datetime64[ns, UTC]"),
                         "direction": pd.Series(dtype="int64"),
                         "stop_px": pd.Series(dtype="float64"),
                         "target_ext": pd.Series(dtype="float64"),
                         "max_hold": pd.Series(dtype="timedelta64[ns]")})


def htf_setups(h):
    """H1 C2 closures at an unfilled same-side FVG with an untaken external swing.
    Returns list of (i, direction, target). Reads bars <= i only."""
    hi, lo, c = (h[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(h)
    ph, pl = np.r_[np.nan, hi[:-1]], np.r_[np.nan, lo[:-1]]
    bear = (hi > ph) & (c < ph)
    bull = (lo < pl) & (c > pl)
    fv = fair_value_gaps(h[OHLC])
    glo, ghi = fv["gap_low"].to_numpy(float), fv["gap_high"].to_numpy(float)
    bear_f = np.flatnonzero(fv["bearish_fvg"].to_numpy())
    bull_f = np.flatnonzero(fv["bullish_fvg"].to_numpy())
    sw = swing_points(h[OHLC], left=2, right=2)
    sl_pos = np.flatnonzero(sw["swing_low"].to_numpy())
    sh_pos = np.flatnonzero(sw["swing_high"].to_numpy())
    out = []
    for i in np.flatnonzero(bear ^ bull):
        if i + 1 >= n:
            continue                                     # no C3 bar yet
        d = -1 if bear[i] else 1
        fpos = bear_f if d == -1 else bull_f
        ks = fpos[(fpos >= i - FVG_LOOKBACK) & (fpos <= i - 1)]
        at_fvg = False
        for k in ks[::-1]:
            if d == -1:
                if hi[i] < glo[k] or (k + 1 <= i - 1 and hi[k + 1:i].max() >= ghi[k]):
                    continue
            else:
                if lo[i] > ghi[k] or (k + 1 <= i - 1 and lo[k + 1:i].min() <= glo[k]):
                    continue
            at_fvg = True
            break
        if not at_fvg:
            continue
        spos = sl_pos if d == -1 else sh_pos
        j = np.searchsorted(spos, i - 2, side="right") - 1
        if j < 0:
            continue
        p = spos[j]
        if d == -1:
            if lo[p + 1:i + 1].min() <= lo[p]:
                continue                                 # external already taken
            out.append((i, d, float(lo[p])))
        else:
            if hi[p + 1:i + 1].max() >= hi[p]:
                continue
            out.append((i, d, float(hi[p])))
    return out


def base_detect(m1):
    h = cl.build_bars(m1, "1h")
    if len(h) < 30:
        return _empty()
    setups = htf_setups(h)
    if not setups:
        return _empty()
    b = cl.build_bars(m1, "5min")
    o5, h5, l5, c5 = (b[k].to_numpy(float) for k in OHLC)
    t5 = pd.DatetimeIndex(b.index).as_unit("ns").asi8
    ct5 = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    ev = cisd_events(b[OHLC], **CISD_KW)
    if ev.empty:
        return _empty()
    cdir = np.where(ev["direction"] == "bullish", 1, -1)
    cext = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ccon = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    cpx = ev["extreme_price"].astype(float).to_numpy()
    fv = fair_value_gaps(b[OHLC])
    glo, ghi = fv["gap_low"].to_numpy(float), fv["gap_high"].to_numpy(float)
    fpos = {-1: np.flatnonzero(fv["bearish_fvg"].to_numpy()),
            1: np.flatnonzero(fv["bullish_fvg"].to_numpy())}
    by_dir = {}
    for d in (-1, 1):
        s = np.flatnonzero(cdir == d)
        s = s[np.argsort(ccon[s], kind="stable")]
        by_dir[d] = (cext[s], ccon[s], cpx[s])
    hs = pd.DatetimeIndex(h.index).as_unit("ns").asi8
    hct = pd.DatetimeIndex(h["close_time"]).tz_convert("UTC")
    rows = []
    for i, d, tgt in setups:
        a2 = np.searchsorted(t5, hs[i], side="left")
        a3 = np.searchsorted(t5, hs[i + 1], side="left")
        b3 = np.searchsorted(t5, hct[i + 1].value, side="left")
        if b3 <= a3:
            continue
        ext, con, px = by_dir[d]
        lo_k, hi_k = np.searchsorted(con, a3, "left"), np.searchsorted(con, b3, "left")
        for q in range(lo_k, hi_k):                     # E2 candidates, in time order
            e2x, e2c, e2p = ext[q], con[q], px[q]
            if d == -1:
                if l5[a3:e2c + 1].min() <= tgt:
                    break                                # draw delivered before entry
                if not tgt < c5[e2c]:
                    continue
            else:
                if h5[a3:e2c + 1].max() >= tgt:
                    break
                if not tgt > c5[e2c]:
                    continue
            ok = False
            for r in np.flatnonzero((ext >= a2) & (con < e2x)):   # E1 candidates
                e1x, e1p = ext[r], px[r]
                if d == -1:
                    if not (e2p < e1p and h5[e1x + 1:e2c + 1].max() <= e1p):
                        continue
                else:
                    if not (e2p > e1p and l5[e1x + 1:e2c + 1].min() >= e1p):
                        continue
                fk = fpos[d]
                for k in fk[(fk >= e1x + 2) & (fk < e2x)]:
                    if d == -1:
                        if h5[e2x] < glo[k] or (k + 1 <= e2x - 1 and h5[k + 1:e2x].max() >= ghi[k]):
                            continue
                    else:
                        if l5[e2x] > ghi[k] or (k + 1 <= e2x - 1 and l5[k + 1:e2x].min() <= glo[k]):
                            continue
                    ok = True
                    break
                if ok:
                    break
            if not ok:
                continue
            t = ct5[e2c]
            rows.append((t, t, d, e2p, tgt, (hct[i + 1] - t) + C4))
            break
    if not rows:
        return _empty()
    out = pd.DataFrame(rows, columns=BASE_COLS)
    out["direction"] = out["direction"].astype("int64")
    out["max_hold"] = pd.to_timedelta(out["max_hold"])
    out = out.sort_values(["decision_time", "direction"], kind="stable")
    out = out.drop_duplicates(["decision_time", "direction"], keep="first")
    return out.reset_index(drop=True)


def detect_a(m1):
    ev = base_detect(m1)
    return ev.assign(rr=RR)


def detect_b(m1):
    ev = base_detect(m1)
    return ev.assign(target_px=ev["target_ext"].astype(float),
                     max_hold=pd.Series([RUNNER_HOLD] * len(ev), dtype="timedelta64[ns]"))


DETECT = {"u1007a": detect_a, "u1007b": detect_b}


def run(reading):
    base = cl.cache_frame("iel_ttfm_h1c2fvg_5mcont_lb120_v1", lambda: base_detect(cl.load_m1()))
    ev = base.assign(rr=RR) if reading == "u1007a" else base.assign(
        target_px=base["target_ext"].astype(float),
        max_hold=pd.Series([RUNNER_HOLD] * len(base), dtype="timedelta64[ns]"))
    m1 = cl.load_m1()
    entry = m1["open"].reindex(pd.DatetimeIndex(ev["decision_time"]), method="bfill").to_numpy()
    sd = np.abs(entry - ev["stop_px"].to_numpy(float))
    td = np.abs(ev["target_ext"].to_numpy(float) - entry)
    print(reading, "events", len(ev), ev["direction"].value_counts().to_dict(),
          "stop pt median", round(float(np.nanmedian(sd)), 3),
          "share<1pt", round(float(np.nanmean(sd < 1)), 3),
          "ext target R median", round(float(np.nanmedian(td / sd)), 2))
    probe = cl.probe_lookahead(DETECT[reading], ev, lookback="20D")
    print("probe", probe.get("passed"), probe.get("n_cuts"), probe.get("n_targeted"))
    res = cl.trade_test(ev, claim="+", ctrl_tod_tol_min=TOD_TOL, hold_basis="bars")
    for kx in ("n", "dropped", "avg_R", "avg_R_gross", "win_rate", "diff", "ci_lo", "ci_hi",
               "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars",
               "ctrl_overlap", "exit_mix"):
        print(" ", kx, res.get(kx))
    print("  control", res.get("control"))
    sprd = {s: float(np.nanmean(s / sd)) for s in SPREAD_PTS}
    common = [
        "ladder H1 -> 5m; H1 bars UTC-aligned; certified 2016+ M1",
        "HTF C2 (bear): H1 high > previous high and close < previous high; bull mirrors",
        f"at FVG: an H1 bearish FVG (3rd bar k in [i-{FVG_LOOKBACK}, i-1]) not fully filled "
        "before C2 (max high k+1..i-1 < gap top) and C2's high >= gap bottom; bull mirrors",
        "draw: latest H1 2/2 swing low confirmed by C2 (p <= i-2) untaken through C2 = the "
        "external target; none -> no setup",
        "LTF 5m, phase-3 CISD (series_open, 2/2, max_wait 3). E1 = same-direction CISD with "
        "extreme at/after the C2 open; E2 = later same-direction CISD, extreme bar after E1's "
        "confirm, lower high than E1 (bear), E1's extreme never exceeded through E2's confirm, "
        "E2's extreme reaches into a same-side 5m FVG formed after E1's extreme and not fully "
        "filled before it; E2 confirms inside H1 C3",
        "draw still open at E2 (no 5m low at/below target from C3 open to E2 confirm; target "
        "below E2's confirm close); first E2 per H1 setup; dedupe same minute+direction",
        "enter next M1 open after E2's 5m confirm close; stop = E2's extreme (wick)",
        "control: matched random entries, NY clock within +-30 min; holds in trading minutes"]
    if reading == "u1007a":
        rules = common + ["target 2R; time exit at the close of H1 C4 (C3 close + 60 trading min)"]
        params = {"target": "2R", "max_hold": "per row: C3 close - decision + 60 min (trading)"}
        src_t = {"target": "corpus: vMq1l8Zzzjw 'then look for a 2R, which is right around that "
                           "lower time frame target'",
                 "max_hold": "corpus: vMq1l8Zzzjw 'trade candle three in this fractal model "
                             "towards that high or even candle four'"}
    else:
        rules = common + ["target = the H1 external level (runner to the higher time frame "
                          "target); time cap 1380 trading minutes (one session)"]
        params = {"target": "H1 external swing level", "max_hold": "1380 trading minutes"}
        src_t = {"target": "corpus: vMq1l8Zzzjw 'look for those higher time frame targets'",
                 "max_hold": "declared-before-run: one 23h trading session; corpus: vMq1l8Zzzjw "
                             "'it takes into the next day'"}
    params.update({"ladder": "1h -> 5min", "c2": "sweep previous H1 extreme, close back inside",
                   "fvg_lookback_h1": FVG_LOOKBACK, "fvg_rule": "C2 wick reaches into an unfilled "
                   "same-side H1 FVG", "external": "latest confirmed untaken H1 2/2 swing",
                   "cisd": "5m series_open, 2/2, max_wait 3", "continuation": "second CISD "
                   "whose extreme reaches into a post-E1 5m FVG, lower high", "stop": "E2 extreme "
                   "(wick)", "kill_zone": "none", "ctrl_tod_tol_min": TOD_TOL,
                   "hold_basis": "bars", "grid4h": "n/a (no 4H bars)"})
    src = {"ladder": "corpus: vMq1l8Zzzjw 'We're trading this hourly internal to external model "
                     "right here' / 'go to the 5-minute time frame and wait for a valid fractal model'",
           "c2": "corpus: vMq1l8Zzzjw 'a candle two closure at a fair value gap'; method_spec: "
                 "§3.2 C2 closure",
           "fvg_lookback_h1": "declared-before-run: one trading week of H1 bars (the source "
                              "leaves the gap's age open)",
           "fvg_rule": "corpus: vMq1l8Zzzjw 'if price reaches into internal liquidity here and "
                       "we have a reaction or a candle two closure'",
           "external": "corpus: vMq1l8Zzzjw 'the swing low that made the swing high'; phase3: "
                       "locked 2/2 swing",
           "cisd": "phase3: locked CISD config (series_open, 2/2, max_wait 3)",
           "continuation": "corpus: vMq1l8Zzzjw 'a new protected swing ... because we reach into "
                           "a fair value gap and then close through this level'",
           "stop": "corpus: vMq1l8Zzzjw 'put our stop either on this high or on the bodies' "
                   "(the wick reading; method_spec §5 stop = protected swing)",
           "kill_zone": "corpus: vMq1l8Zzzjw (no time filter stated; draft ambiguity)",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9 / vault Concept Campaign "
                               "lesson 3; not a timing claim but events cluster in active hours",
           "hold_basis": "declared-before-run: README trap 7; holds span the 17:00 NY halt / "
                         "weekend, so trading minutes for real and control alike",
           "grid4h": "declared-before-run: no 4H bars used",
           **src_t}
    notes = (f"New-claim reading of vMq1l8Zzzjw (TTFM execution of the internal/external "
             f"model), not the library mwmWNCTEYtY kill-zone reading (n=227, UNDERPOWERED, "
             f"untouched). Same entries in u1007a/u1007b, only the exit differs. Events {len(ev)}; "
             f"median stop {np.nanmedian(sd):.2f} pt, {np.nanmean(sd < 1):.1%} under 1 pt; "
             f"median external target {np.nanmedian(td / sd):.2f}R. Spread cost per trade "
             f"(mean R) at 0.45 / 0.60 pt: {sprd[0.45]:.3f} / {sprd[0.60]:.3f}. Control matches "
             f"stop DISTANCE, not placement at a fresh 5m swing extreme (campaign lesson 1), "
             f"so the differential is flattered. Overlaps the refuted Conjunction Test "
             f"(5m/1H/1D CISD stack). Not modelled: bodies stop, SMT/PSP, T-spot, daily layer.")
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)


if __name__ == "__main__":
    for r in (sys.argv[1:] or list(DETECT)):
        run(r)
