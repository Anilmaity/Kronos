"""cisd (update 2026-10-07, live_07) — the consolidation exclusion on SWING-PAIRED CISDs.

Source: 9YVBe-20Hdg (New York Open Live Q&A), answering why a 15m CISD was ignored:
  "It's not paired with any sort of swing point" / "I don't define a CISD by volatility" /
  "you don't want to use a CISD within cons consolidation".
In the same video consolidation is the INSIDE CANDLE: "we're inside day. So inside day ...
pretty much just a consolidation. We're in a range" and "We're inside that candle and then
we're inside that candle. So that's just consolidation."

New claim only (swing pairing is already in the library = the POI gate of cisd__a):
  baseline = the cisd__a book (15m, series_open, 2/2, max_wait 3, POI gate ON);
  gate (kept) = CISD NOT formed inside consolidation; claim '+'.
  Consolidation is structural (inside candle), never a volatility measure — that is how the
  "I don't define a CISD by volatility" clause is honoured; a "no effect" statement has no
  directional test of its own.
Readings (the source leaves the HTF of the inside candle open; one per TF of his stack):
  u1007a  daily: the developing NY trading day (18:00 roll) is so far inside the prior real
          day (running high <= PDH and running low >= PDL, M1 closed by the decision).
  u1007b  4H (forex grid): the developing 4H candle is so far inside the prior 4H candle
          (running high/low of its 15m bars up to the confirming bar).
Not tested: the 'against bias' clause — his bias there is cross-index relative strength
(NQ/ES/YM), which needs assets we lack; bias gates are separate library concepts.
All parameters declared before the first run.

Rerun 2026-10-07 with the KronosVault context (Backtest Methodology Traps, Concept Campaign,
Session Timing, Data Inventory). detect/readings/params are UNCHANGED from the first run of
this update (pre-declared; changing them after seeing a result would be a forking path).
Traps checked: (3/9) decide at the confirming 15m close, HTF state from M1/15m closed by then,
prior HTF candle fully closed, symmetric probe; (5) both gate flags recomputed from raw M1
independently of the harness helpers (_raw_check, asserted); (7) unevaluated rows DROPPED,
gate firing rate printed; (8) forex 4H grid recorded, inside test is scale-free (no $ units);
session timing -> ctrl_tod_tol_min=30; spread caveat -> median stop in points printed.
Not a repeat: consolidation-avoidance__a/b (NEGATIVE) gated the BARE book on a COMPLETED
inside day; this is the developing-candle state on the swing-paired (POI-on) book.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01a")
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import _common as C         # noqa: E402  (cisd_with_poi, to_trade_frame, htf_context)
import concept_lab as cl    # noqa: E402

CID = "cisd"
TF = "15min"
RR = 2.0
MAX_HOLD = "150min"
MIN_COV = 0.5
TOD = 30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "not_cons_d", "not_cons_4h"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b, ev = C.cisd_with_poi(m1, TF, level_rule="series_open", max_wait=3, min_series=1)
    if ev.empty:
        return C.empty_frame(COLS[:5]).assign(not_cons_d=pd.Series(dtype=bool),
                                                not_cons_4h=pd.Series(dtype=bool))
    ev = ev[ev["poi_passed"]].reset_index(drop=True)
    out = C.to_trade_frame(ev, RR)
    t = pd.DatetimeIndex(out["decision_time"])
    # daily: today so far inside the prior real day
    run = cl.running_hilo(t, "1D", m1=m1)
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=MIN_COV)
    rh, rl = run["high"].to_numpy(float), run["low"].to_numpy(float)
    ph, pl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    ok_d = np.isfinite(rh) & np.isfinite(ph)
    in_d = ok_d & (rh <= ph) & (rl >= pl)
    # 4H forex grid: the 4H candle holding the confirming bar is so far inside the prior one
    hc = C.htf_context(b, m1, "4h").iloc[ev["conf_pos"].to_numpy()]
    ok_4 = hc["valid"].to_numpy(bool)
    in_4 = ok_4 & (hc["run_high"].to_numpy(float) <= hc["p1_high"].to_numpy(float)) \
        & (hc["run_low"].to_numpy(float) >= hc["p1_low"].to_numpy(float))
    out["not_cons_d"] = ~in_d
    out["not_cons_4h"] = ~in_4
    keep = ok_d & ok_4                         # never evaluated != passed: drop, don't default
    return out[keep].reset_index(drop=True)


BASE_RULES = [
    "baseline = cisd__a book: 15m bars; CISD via detectors.cisd.cisd_events level_rule=series_open, "
    "swing 2/2, max_wait 3, min_series 1; POI gate (swing pairing) ON, evaluated on bars up to the "
    "confirming bar; decide at confirming close, enter next M1 open, stop protected swing, 2R, 150 min",
    "consolidation = inside candle (structural, no volatility criterion), state read at the decision",
]
BASE_PARAMS = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "min_series": 1,
               "poi_gate": "on", "stop": "protected_swing", "rr": RR, "max_hold": MAX_HOLD,
               "inside": "wick range, non-strict (<=, >=); running extremes of the developing candle",
               "ctrl_tod_tol_min": TOD}
BASE_SRC = {
    "tf": "corpus: 9YVBe-20Hdg 'Why don't I consider this 15-minute CISD?'",
    "level_rule": "method_spec: §4.2 [P] first-candle open (cisd__a reading a)",
    "swing": "phase3: locked 2/2 fractal",
    "max_wait": "phase3: §1.8 max_wait=3",
    "min_series": "phase3: §1.8 min_series=1",
    "poi_gate": "corpus: 9YVBe-20Hdg 'It's not paired with any sort of swing point' -> library POI gate (cisd__a)",
    "stop": "method_spec: §5.1 protected swing",
    "rr": "phase3: §1.12 2R fixed",
    "max_hold": "phase3: §1.13 10 entry-TF bars",
    "inside": "corpus: 9YVBe-20Hdg 'We're inside that candle ... So that's just consolidation'; "
              "'I don't define a CISD by volatility' -> no range/ATR criterion",
    "ctrl_tod_tol_min": "declared-before-run: README trap 9 — the inside-so-far state clusters by "
                        "NY hour while the concept is not about timing; control holds the clock",
}
SPEC = {
    "u1007a": ("not_cons_d",
               "gate (kept) = NOT (today's running high <= prior real day's high AND running low >= its "
               "low), 18:00 NY roll, prior day via prior_hilo min_coverage 0.5; claim +",
               {"htf": "1D", "day_roll": "18:00 NY", "min_coverage": MIN_COV},
               {"htf": "corpus: 9YVBe-20Hdg 'inside day ... pretty much just a consolidation'",
                "day_roll": "session_window_fit: settled 18:00 NY roll",
                "min_coverage": "declared-before-run: README trap 6 stub sessions skipped"}),
    "u1007b": ("not_cons_4h",
               "gate (kept) = NOT (running high/low of the 4H candle holding the confirming 15m bar, "
               "through that bar, inside the prior 4H candle's range), forex grid; claim +",
               {"htf": "4h", "grid4h": "forex"},
               {"htf": "method_spec: §1.3 favourite stack Daily/4H/15m — 4H is the 15m CISD's HTF",
                "grid4h": "session_window_fit: forex grid for gold (knob, phase3 caveat)"}),
}

def _raw_check(ev: pd.DataFrame, m1: pd.DataFrame, n: int = 400, seed: int = 7) -> None:
    """Trap 5: recompute both 'inside so far' flags from raw M1 with plain pandas (no
    running_hilo/prior_hilo/htf_context), on a random sample of events; must agree exactly."""
    ny = m1.index.tz_convert("America/New_York").tz_localize(None)
    td = (ny + pd.Timedelta(hours=6)).normalize()                 # 18:00 NY roll
    slot = (ny - pd.Timedelta(hours=1)).floor("4h") + pd.Timedelta(hours=1)   # 01/05/09/13/17/21 NY
    hi, lo = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    dcnt = pd.Series(1, index=td).groupby(level=0).size()
    dhi = pd.Series(hi, index=td).groupby(level=0).max()
    dlo = pd.Series(lo, index=td).groupby(level=0).min()
    real_days = dcnt.index[dcnt.to_numpy() >= MIN_COV * float(np.median(dcnt.to_numpy()))]
    shi = pd.Series(hi, index=slot).groupby(level=0).max()
    slo = pd.Series(lo, index=slot).groupby(level=0).min()
    slots = shi.index
    rows = ev.sample(min(n, len(ev)), random_state=seed)
    bad = 0
    for _, r in rows.iterrows():
        t = r["decision_time"]
        j = int(m1.index.searchsorted(t, side="left"))            # M1 bars with start < t are closed by t
        tl = (t.tz_convert("America/New_York").tz_localize(None) - pd.Timedelta(minutes=1))
        # daily
        today = (tl + pd.Timedelta(hours=6)).normalize()
        k0 = int(td[:j].searchsorted(today, side="left"))
        rh, rl = hi[k0:j].max(), lo[k0:j].min()
        prev = real_days[real_days < today][-1]
        in_d = (rh <= dhi[prev]) and (rl >= dlo[prev])
        # 4H forex grid
        s0 = (tl - pd.Timedelta(hours=1)).floor("4h") + pd.Timedelta(hours=1)
        k4 = int(slot[:j].searchsorted(s0, side="left"))
        r4h, r4l = hi[k4:j].max(), lo[k4:j].min()
        p1 = slots[slots < s0][-1]
        in_4 = (r4h <= shi[p1]) and (r4l >= slo[p1])
        if (in_d != (not r["not_cons_d"])) or (in_4 != (not r["not_cons_4h"])):
            bad += 1
            print("RAW MISMATCH", t, in_d, not r["not_cons_d"], in_4, not r["not_cons_4h"])
    print(f"raw recompute: {len(rows) - bad}/{len(rows)} agree")
    assert bad == 0, "gate flags disagree with raw-M1 recomputation"


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"u1007_cisd_poi_inside_d_4h_cov{MIN_COV}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "in-cons share d/4h",
          round(1 - ev["not_cons_d"].mean(), 3), round(1 - ev["not_cons_4h"].mean(), 3),
          "| span", ev["decision_time"].min(), "->", ev["decision_time"].max())
    _raw_check(ev, m1)
    ent = m1["open"].to_numpy(float)[np.minimum(m1.index.searchsorted(ev["decision_time"], side="left"),
                                                len(m1) - 1)]
    sd = np.abs(ent - ev["stop_px"].to_numpy(float))
    print("median stop pts", round(float(np.median(sd)), 3), "| share < 1pt", round(float((sd < 1).mean()), 3))
    nyh = ev["decision_time"].dt.tz_convert("America/New_York").dt.hour
    print("in-cons share by NY hour (daily):",
          (1 - ev.groupby(nyh)["not_cons_d"].mean()).round(2).to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    for reading, (col, rule, pp, ps) in SPEC.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=MAX_HOLD,
                           claim="+", ctrl_tod_tol_min=TOD)
        for k in ("n", "n_gated", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "ctrl_overlap", "halves"):
            print(" ", reading, k, res.get(k))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": BASE_RULES + [rule], "params": {**BASE_PARAMS, **pp}},
                            params_source={**BASE_SRC, **ps}, script=__file__, probe=probe,
                            notes="Tests only the new claim (9YVBe-20Hdg): exclude CISDs formed inside "
                                  "consolidation, on the swing-paired (POI-on) book. Prior bare-CISD "
                                  "consolidation gates: consolidation-avoidance__a/b NEGATIVE (inside-"
                                  "consolidation CISDs did better), consolidation-range-no-trade__a NULL. "
                                  "'Against bias' (cross-index strength) not tested: needs NQ/ES/YM. "
                                  "Rerun with vault context: same pre-declared readings; gate flags "
                                  "verified against an independent raw-M1 recomputation.")
        print("wrote", p)
