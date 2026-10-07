"""gold-correlated-assets -- update 2026-10-07 (TTrades live_12 draft, rTomJ8URFnw).

New claim vs the library entry: "Gold euro, gold pound for some divergences ... But I prefer
gold and silver on the higher time frame." The prior reading (liquidity_own_02b, NULL) was the
1h head-to-head with the gold-euro/gold-pound family as the gate. This tests ONLY the new part:
on a HIGHER timeframe, does silver SMT beat gold-euro/gold-pound SMT?

Fixed BEFORE the first run (same C2 book and SMT rule as the prior reading; only TF and gate
side change):
  C2 on the HTF = sweeps the prior HTF bar's high/low, closes back inside, closes in the
  reversal direction; enter next M1 open after the C2 close, reversal direction, stop at the
  C2 extreme, 2R, 10 HTF bars of trading time.
  Reversal SMT per correlate = the correlate did NOT take its own prior-bar extreme on the C2 bar.
    AG-SMT = vs XAG/USD;  EG-SMT = vs XAU/EUR or XAU/GBP.
  Keep C2s where the two families disagree (the only rows where the instrument choice changes
  the decision). gate = AG-SMT (silver-only); complement = gold-euro/pound-only. claim '+'.
  Correlate HTF bars are aggregated from H1 bars restricted to the hours gold actually traded
  in that HTF bar; a row is dropped unless every correlate has every one of those hours on
  both C1 and C2 ("never evaluated" must not look like "no sweep").
Readings (the source leaves "higher time frame" open):
  u1007a = 4h  (forex grid) -- his favourite HTF in this same stream ("the 4 hour and 15 minute model")
  u1007b = 1D  (18:00 NY roll) -- the library entry's other HTF

AUDIT 2026-10-07 (rerun with vault context): detect() unchanged (same frames, same fps).
  Fixed: README trap 9 / vault Session Timing on Gold -- the concept is not about timing but
  every decision sits on a HTF close (4h: six forex-grid NY slots, TV distance 0.778 vs the
  'auto' control's :00 minutes; 1D: all at the 18:00 NY close/reopen, TV 0.975), so the
  control did not hold the NY clock or the reopen gap. Now u1007a: ctrl_grid="4h" +
  ctrl_tod_tol_min=30 (same slot); u1007b: ctrl_grid="1D" (ctrl_tod_tol_min cannot be used:
  17:00 NY has no M1 bar). Checked, no change needed: correlate files cover 2016-2026 evenly
  (~5.9k H1 bars/yr each; vault trap 7 fetch default); stub C1/C2 bars (<50% median n_m1)
  touch 12/1841 (4h) and 1/326 (1D) events; stops are 5-18 pt median, so a 0.6 pt spread
  differs by only ~0.01-0.03R between arms (campaign lesson 2); gate_test, not the suggested
  trade_test, because both arms share the C2-extreme stop placement, so the structural-stop
  effect (campaign lesson 1) cancels in gated-minus-complement.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402

import concept_lab as cl                 # noqa: E402
from _common import corr_h1              # noqa: E402

CID = "gold-correlated-assets"
RR = 2.0
READINGS = {"u1007a": ("4h", "40h", "10D"), "u1007b": ("1D", "230h", "20D")}
CTRL = {"u1007a": {"ctrl_grid": "4h", "ctrl_tod_tol_min": 30}, "u1007b": {"ctrl_grid": "1D"}}
CTRL_SRC = {
    "u1007a": {
        "ctrl_grid": "declared-before-run (rerun): decisions sit on the 4h forex close grid, one in six "
                     "at the 17:00 NY close with entry at the 18:00 reopen; controls drawn on the same grid "
                     "(vault Session Timing on Gold: the reopen is a gap artefact)",
        "ctrl_tod_tol_min": "declared-before-run (rerun): README trap 9, not a timing concept but events "
                            "sit at six NY slots (TV 0.778 vs the auto control); 30 min on the 4h grid = same slot"},
    "u1007b": {
        "ctrl_grid": "declared-before-run (rerun): every decision is the daily close (entry at the 18:00 NY "
                     "reopen, TV 0.975 vs the auto control), so controls are drawn on the 1D close grid to "
                     "hold that clock (README trap 9); ctrl_tod_tol_min unusable: 17:00 NY has no M1 bar"}}
CORRS = ("xau_eur", "xau_gbp", "xag_usd")


def detect_tf(m1, tf):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "ag_smt"]
    b = cl.build_bars(m1, tf)
    if len(b) < 3:
        return pd.DataFrame(columns=cols)
    starts = pd.DatetimeIndex(b.index).tz_convert("UTC")
    # gold's traded hours, only hours fully closed by the slice end
    hrs = pd.DatetimeIndex(m1.index).tz_convert("UTC").floor("h").unique().sort_values()
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    hrs = hrs[hrs + pd.Timedelta(hours=1) <= end]
    k = np.searchsorted(starts.asi8, hrs.asi8, side="right") - 1
    keep = k >= 0
    hrs, k = hrs[keep], k[keep]
    n = len(b)
    need = np.bincount(k, minlength=n)                       # gold hours per HTF bar
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    bear = (h > ph) & (c <= ph) & (c < o)
    bull = (l < pl) & (c >= pl) & (c > o)
    div, ok = {}, {}
    for name in CORRS:
        a = corr_h1(name).reindex(hrs)
        g = pd.DataFrame({"k": k, "h": a["high"].to_numpy(float), "l": a["low"].to_numpy(float)})
        agg = g.groupby("k").agg(h=("h", "max"), l=("l", "min"), cnt=("h", "count")).reindex(range(n))
        ch, cl_ = agg["h"].to_numpy(float), agg["l"].to_numpy(float)
        full = (agg["cnt"].fillna(0).to_numpy() == need) & (need > 0)
        cph, cpl = np.r_[np.nan, ch[:-1]], np.r_[np.nan, cl_[:-1]]
        ok[name] = full & np.r_[False, full[:-1]]
        with np.errstate(invalid="ignore"):
            div[name] = np.where(bear, ch <= cph, cl_ >= cpl) & ok[name]
    allok = ok["xau_eur"] & ok["xau_gbp"] & ok["xag_usd"]
    eg = div["xau_eur"] | div["xau_gbp"]
    ag = div["xag_usd"]
    sel = (bear | bull) & allok & (eg != ag)
    i = np.flatnonzero(sel)
    i = i[i >= 1]
    if not len(i):
        return pd.DataFrame(columns=cols)
    d = np.where(bear[i], -1, 1)
    stop = np.where(d < 0, h[i], l[i])
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[i]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close, "direction": d,
                         "stop_px": stop, "rr": RR, "ag_smt": ag[i].astype(bool)})


def detect_4h(m1):
    return detect_tf(m1, "4h")


def detect_1d(m1):
    return detect_tf(m1, "1D")


DETECT = {"u1007a": detect_4h, "u1007b": detect_1d}


def run(reading):
    tf, hold, lookback = READINGS[reading]
    det = DETECT[reading]
    ev = cl.cache_frame(f"{CID}_{reading}_{tf}_htf_silver_v1", lambda: det(cl.load_m1()))
    print(reading, tf, "events", len(ev), "ag_smt share", round(float(ev["ag_smt"].mean()), 3))
    probe = cl.probe_lookahead(det, ev, lookback=lookback)
    res = cl.gate_test(ev, "ag_smt", mask_available_at="decision_time", max_hold=hold,
                       hold_basis="bars", claim="+", **CTRL[reading])
    for kk in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
               "gate_firing_rate", "n_complement", "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", kk, res.get(kk))
    rules = [f"{tf} gold bars ({'forex 4H grid 17/21/01/05/09/13 NY' if tf == '4h' else 'NY day rolling 18:00'}); "
             "C2 = sweeps prior bar high/low, closes back inside, closes in the reversal direction",
             "enter next M1 open after C2 close, reversal direction; stop at C2 extreme; 2R; "
             f"10 {tf} bars of trading time ({hold} of M1 bars)",
             "correlate HTF bars = OANDA H1 bars aggregated over the hours gold traded in that bar; "
             "row dropped unless all three correlates cover every such hour on C1 and C2",
             "reversal SMT vs a correlate = that correlate did not take its own prior-bar extreme on the C2 bar",
             "keep C2s where SMT vs XAG/USD disagrees with SMT vs {XAU/EUR or XAU/GBP}",
             "gate = SMT vs silver (complement = gold-euro/gold-pound-only SMT); claim '+' = silver better on the HTF"]
    params = {"tf": tf, "grid4h": "forex", "day_open_hour": 18, "rr": RR, "max_hold": hold,
              "hold_basis": "bars", "ag_family": "XAG_USD", "eg_family": "SMT if XAU_EUR or XAU_GBP diverges",
              "divergence_tolerance": "none (strict)", "correlate_coverage": "all gold hours present",
              **CTRL[reading]}
    tf_src = ("corpus: rTomJ8URFnw 'Why is the 4 hour and 15 minute model your favorite?' (his favourite HTF, "
              "same stream as 'I prefer gold and silver on the higher time frame'); 4H is in the library's htf list"
              if tf == "4h" else
              "declared-before-run: 1D is the library entry's other HTF; 'higher time frame' is left open by "
              "rTomJ8URFnw 'But I prefer gold and silver on the higher time frame.' -- second pre-declared reading")
    src = {"tf": tf_src,
           "grid4h": "session_window_fit: forex grid for gold (harness default; trap 8 knob recorded)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "rr": "phase3: locked 2R target (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13); 4h=40h, 1D=10x23 trading h=230h",
           "hold_basis": "declared-before-run: trading-time holds (trap 7), as the prior reading",
           "ag_family": "corpus: rTomJ8URFnw 'But I prefer gold and silver on the higher time frame.'",
           "eg_family": "corpus: rTomJ8URFnw 'Gold euro, gold pound for some divergences' (no ranking given)",
           "divergence_tolerance": "declared-before-run: no tolerance given in the corpus (as prior reading)",
           "correlate_coverage": "declared-before-run: a missing correlate hour must not read as a non-sweep (trap 5)",
           **CTRL_SRC[reading]}
    notes = (f"{len(ev)} {tf} C2s where silver and gold-euro/pound SMT disagree; silver-SMT on "
             f"{ev['ag_smt'].mean():.1%}. Tests only the new 'silver on the higher timeframe' claim; the "
             "gold-euro/pound 1h head-to-head is the prior (unlabelled) reading. Correlates are OANDA spot "
             "crosses at H1 aggregated to the gold HTF bar. AUDIT 2026-10-07 (vault rerun): control now "
             f"holds the NY clock ({CTRL[reading]}); stub C1/C2 bars, correlate extents and spread-in-pt "
             "checked, no change (see script docstring).")
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print("wrote", p)


if __name__ == "__main__":
    for r in (sys.argv[1:] or list(READINGS)):
        run(r)
