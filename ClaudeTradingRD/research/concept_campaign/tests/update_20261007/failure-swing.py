"""failure-swing, update_20261007_edu_02: the failure-swing C2 GATING rule (new claim).

Prior readings a/b (2026-09-23, 15m failure-swing clusters as targets, rate tests) and
failure-swing-draw are untouched. This tests ONLY the new candle-level usage:

Source, tUbrCewFdCU (How to Trade London Using TTrades Fractal Model), on the 4-hour chart:
  "it did fail to take out this previous high ... This is a valid candle to closure cuz you
   can see it swept out its previous candle and then close below, but it is a failure swing.
   So, in a case like this, it doesn't mean we cannot trade it. It's just I would prefer there
   to be SMT here. If I am going to trade something with failure swings, I must demand more
   confirmation on the lower time frame."
  (gold example, same video) "I'll only ever look to trade away from something like this if we
   have SMT on the low"
Draft measurable: "outcome of failure-swing C2 setups with vs without SMT" -> gate_test.

Population (detector, all closed bars at the C2 close):
  4H forex-grid C2 (detectors.fractal.c2_events defaults: sweep of the PRIOR candle's
  extreme, close back inside it, close in the reversal direction), traded exactly as the
  library's fractal-model-c2 reading a trades C3 (enter at C2 close, stop C2 extreme, target
  nearest of the C1/C2 far extremes, 240 trading minutes), KEPT ONLY IF it is a FAILURE-SWING
  C2: its extreme did not take out the earlier high (low) = the highest high (lowest low) from
  the latest confirmed 2/2 swing high (low) before C1 through C1.

SMT is "one asset takes the level, the other does not" (smt-divergence.yaml). The source does
not say WHICH level the SMT is read at, so two pre-declared readings (one per interpretation):
  u1007a  SMT at the swept candle: silver did NOT take its own C1 extreme on the C2 bar
          (gold swept C1, silver failed) -- the candle-level SMT at the C2 sweep itself.
  u1007b  SMT at the failure swing: silver DID take its own earlier high (low) over the same
          bar window while gold failed -- the SMT-as-swing-point-substitute reading
          ("if this asset did not run out the high/low but a correlated asset did").
The "clean lower-timeframe continuation structure" alternative is NOT tested: "clean" is
discretionary and unquantified in the source (see notes).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np                                 # noqa: E402
import pandas as pd                                # noqa: E402

import concept_lab as cl                           # noqa: E402
from detectors.fractal import c2_events            # noqa: E402
from detectors.primitives import swing_points      # noqa: E402

CID = "failure-swing"
XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
OHLC = ["open", "high", "low", "close"]
MIN_M1 = 60          # fractal-model-c2 reading a stub-bar guard
SW_L, SW_R = 2, 2    # phase-3 locked fractal
HOLD = "240min"      # C3's duration, trading bars (fractal-model-c2 reading a)
H4 = np.int64(4 * 3600 * 10**9)
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px",
        "smt_c1", "smt_fs", "ref_bars"]
_XAG = None


def xag_for(m1):
    """Silver H1 bars that have CLOSED by the end of this M1 slice."""
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        x.index = pd.to_datetime(x.index, utc=True)
        x = x[OHLC].astype(float).sort_index()
        _XAG = x[~x.index.duplicated(keep="first")]
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    start = pd.DatetimeIndex(m1.index).min().floor("1h")
    return _XAG[(_XAG.index >= start) & (_XAG.index + pd.Timedelta(hours=1) <= end)]


def _per_bar(starts, t_ns, vals, how):
    """Aggregate 1h rows (start t_ns) into the 4H bar whose [start, start+4h) holds them."""
    n = len(starts)
    k = np.searchsorted(starts, t_ns, "right") - 1
    ok = (k >= 0) & (t_ns < starts[np.maximum(k, 0)] + H4)
    out = np.full(n, np.nan)
    if ok.any():
        s = pd.Series(vals[ok]).groupby(k[ok])
        r = getattr(s, how)()
        out[r.index.to_numpy()] = r.to_numpy()
    return out


def detect(m1):
    b = cl.build_bars(m1, "4h", grid4h="forex")
    b = b[b["n_m1"] >= MIN_M1]
    if len(b) < 20:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    n = len(b)
    o, h, l, c = (b[k].to_numpy(float) for k in OHLC)
    starts = b.index.asi8

    # silver per 4H bar + coverage (silver H1 count must equal gold's hour count)
    x = xag_for(m1)
    xt = x.index.asi8
    xh = _per_bar(starts, xt, x["high"].to_numpy(), "max")
    xl = _per_bar(starts, xt, x["low"].to_numpy(), "min")
    xn = _per_bar(starts, xt, np.ones(len(xt)), "sum")
    g1 = cl.build_bars(m1, "1h")
    gn = _per_bar(starts, g1.index.asi8, np.ones(len(g1)), "sum")
    xcov = np.nan_to_num(xn) >= np.nan_to_num(gn, nan=1e9)          # full same-clock coverage

    # latest confirmed 2/2 swing at p <= i-2 (right bars p+1, p+2 <= i are all closed)
    sw = swing_points(b[OHLC], left=SW_L, right=SW_R)
    ar = np.arange(n)
    last_sh = np.maximum.accumulate(np.where(sw["swing_high"].to_numpy(), ar, -1))
    last_sl = np.maximum.accumulate(np.where(sw["swing_low"].to_numpy(), ar, -1))

    c2 = c2_events(b[OHLC])
    if c2.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    pos = b.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    bull = (c2["direction"] == "bullish").to_numpy()
    rows = []
    for i, up in zip(pos, bull):
        if i < 2:
            continue
        p = last_sl[i - 2] if up else last_sh[i - 2]
        if p < 0:
            continue
        # earlier extreme: from the swing through C1 (bars p..i-1)
        if up:
            ref = l[p:i].min()
            fail = l[i] > ref                                  # C2 low did not take it
        else:
            ref = h[p:i].max()
            fail = h[i] < ref
        if not fail:
            continue
        if not xcov[p:i + 1].all():                            # SMT not evaluable -> drop
            continue
        if up:
            smt_c1 = xl[i] >= xl[i - 1]                        # silver did not take its C1 low
            smt_fs = xl[i] < xl[p:i].min()                     # silver took its earlier low
            stop, tgt = l[i], max(h[i - 1], h[i])
        else:
            smt_c1 = xh[i] <= xh[i - 1]
            smt_fs = xh[i] > xh[p:i].max()
            stop, tgt = h[i], min(l[i - 1], l[i])
        rows.append((b["close_time"].iloc[i], 1 if up else -1, stop, tgt,
                     bool(smt_c1), bool(smt_fs), int(i - p)))
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                     "smt_c1", "smt_fs", "ref_bars"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    ev["available_at"] = ev["decision_time"]
    ev = ev[COLS].sort_values(["decision_time", "direction"], kind="stable")
    return ev.reset_index(drop=True)


def diag(ev):
    return {"events": int(len(ev)), "bull_share": round(float((ev.direction == 1).mean()), 3),
            "smt_c1_rate": round(float(ev.smt_c1.mean()), 3),
            "smt_fs_rate": round(float(ev.smt_fs.mean()), 3),
            "both": round(float((ev.smt_c1 & ev.smt_fs).mean()), 3),
            "median_ref_bars": float(ev.ref_bars.median())}


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame("failswing_c2_4h_forex_smt_u1007_v1", lambda: detect(m1))
    D = diag(ev)
    print("DIAG", D)
    if "--diag" in sys.argv:
        sys.exit(0)
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))

    OP_COMMON = [
        "4H bars on the forex grid (17/21/01/05/09/13 NY), bars with < 60 M1 skipped",
        "C2: low < prior low, close >= prior low, close > open (bullish); mirror bearish "
        "(detectors.fractal.c2_events defaults)",
        "earlier high (bearish C2) = max high over bars p..C1, p = latest 2/2 swing high at "
        "p <= C2-2 (its right bars closed by the C2 close); mirror for lows",
        "FAILURE-SWING C2 (population): the C2 extreme did NOT take the earlier high/low "
        "(C2 high < earlier high; bullish C2 low > earlier low); C2s that took it are excluded",
        "silver = XAG_USD H1 aggregated into the same 4H bars; a C2 is dropped (never scored) "
        "unless every bar p..C2 has silver H1 coverage equal to gold's hour count",
        "trade C3: decide at the C2 close_time, enter next M1 open in the C2 direction, stop = "
        "C2 extreme, target = max(C1 high, C2 high) bullish / min(C1 low, C2 low) bearish, "
        "time exit after 240 trading minutes (fractal-model-c2 reading a)",
        "gate_test: control-adjusted R (matched random entries, same direction/stop/target "
        "distance, +-30 d, held at the NY clock +-30 min) of SMT-gated failure-swing C2s minus "
        "the non-SMT failure-swing C2s; claim '+' (SMT makes them tradeable)",
    ]
    PARAMS = {"htf": "4h", "grid4h": "forex", "min_m1": MIN_M1, "swing": "2/2",
              "sweep_ref": "prior_candle", "require_reversal_close": True,
              "earlier_extreme": "max high (min low) from latest confirmed 2/2 swing through C1",
              "target": "nearest unswept of C1/C2 far extremes", "max_hold": HOLD,
              "hold_basis": "bars", "correlate": "XAG_USD H1 -> 4H", "silver_coverage": "full",
              "ctrl_tod_tol_min": 30}
    SRC = {
        "htf": "corpus: tUbrCewFdCU 'we want to find a swing point on the 4-hour chart' / "
               "'This is a valid candle to closure' (the 4H C2)",
        "grid4h": "session_window_fit: forex grid for gold (phase3 knob, primary)",
        "min_m1": "declared-before-run: fractal-model-c2 reading a stub-bar guard (60 M1)",
        "swing": "phase3: locked 2/2 fractal",
        "sweep_ref": "corpus: tUbrCewFdCU 'it swept out its previous candle and then close below'",
        "require_reversal_close": "corpus: fractal-model-c2 'The candle's own shape must be a "
                                  "reversal' (c2_events default)",
        "earlier_extreme": "corpus: tUbrCewFdCU 'it did fail to take out this previous high' -> "
                           "the previous swing high (latest confirmed 2/2) and anything higher "
                           "printed since it; declared-before-run",
        "target": "corpus: fractal-model-c2 execution.targets 'previous candles' unswept "
                  "highs/lows' / method_spec §5.2 'starting with candle 1's'",
        "max_hold": "method_spec: §5.5 time-based exit at the close of the HTF candle traded (C3)",
        "hold_basis": "declared-before-run: README trap 7 - 4H holds cross the daily halt",
        "correlate": "corpus: tUbrCewFdCU 'I would prefer there to be SMT here' (gold example: "
                     "'if we have SMT on the low'); XAG is the campaign's gold correlate "
                     "(vault XAUUSD Data Inventory)",
        "silver_coverage": "declared-before-run: README trap 5 - an SMT never evaluated must not "
                           "look like no-SMT, so uncovered rows are dropped, not set False",
        "ctrl_tod_tol_min": "declared-before-run: README trap 9 - 4H C2s close at only six NY "
                            "clock times; SMT is not a timing concept",
    }
    READ = {
        "u1007a": ("smt_c1",
                   "gate = SMT at the swept candle: on the C2 bar silver did NOT take its own C1 "
                   "extreme (bearish: silver C2 high <= silver C1 high; bullish mirror)",
                   "corpus: smt-divergence.yaml 'one asset takes the level and the other does "
                   "not' with the level = C1's extreme the gold C2 swept ('swept out its previous "
                   "candle'); declared-before-run"),
        "u1007b": ("smt_fs",
                   "gate = SMT at the failure swing: silver DID take its own earlier extreme "
                   "(silver C2 high > silver max high over bars p..C1; bullish mirror) while "
                   "gold failed to",
                   "corpus: smt-swing-point-substitute.yaml 'If this asset did not run out the "
                   "high/low but a correlated asset did, the level is treated as if it had been "
                   "swept'; declared-before-run"),
    }
    NOTE = ("Population = failure-swing 4H C2s only (C2s that took the earlier extreme excluded): "
            "4,484 4H C2s -> 3,271 failure-swing (72.9%) -> 3,269 after 2 silver-coverage drops "
            "(counted before the run). The two gates are mutually exclusive by construction. "
            "Untested: the 'clearly clean lower-timeframe continuation structure' alternative "
            "('clean' is discretionary, unquantified), and proximity ('quite close' vs 'further "
            "away' from the reversal, unquantified in the source). Related prior tests NOT "
            "repeated here: smt-swing-point-substitute__b (daily C2 + silver SMT gate, all C2s, "
            "UNDERPOWERED) and __a (1h failure swing + silver sweep, trade test). Diagnostics: "
            + str(D))
    for rd, (col, rule, src) in READ.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD,
                           hold_basis="bars", ctrl_tod_tol_min=30, claim="+")
        for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "verdict", "verdict_detail", "ties", "ctrl_overlap", "dropped", "halves"):
            print(rd, k, res.get(k))
        path = cl.write_result(CID, rd, res,
                               operationalization={"rules": OP_COMMON + [rule],
                                                   "params": {**PARAMS, "gate": col}},
                               params_source={**SRC, "gate": src}, script=__file__,
                               probe=probe, notes=NOTE)
        print("wrote", path)
