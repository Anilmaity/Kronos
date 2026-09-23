"""level-to-trade-away-from -- "No level to trade away from, no trade".

Gate test. Baseline book: bare 15m CISD (phase-3 rung 0 on the 15m entry TF):
series_open level, 2/2 swings, max_wait 3, decide at the confirming bar's close,
stop at the protected swing (the CISD extreme), 2R, 150 min hold.

The concept is a pre-trade gate: take the reversal only when the extreme it is
traded away from SWEPT a relevant level (a low for a long, a high for a short).
Contested / undefined "relevant level" -> two readings, declared before any run:
  a  execution-TF level: the extreme (or the opposing run into it) took out a
     confirmed 15m 2/2 swing low/high that was still untaken, formed within the
     prior 20 bars.
  b  HTF key level (htf 1D in the YAML): the run into the extreme took out the
     previous trading day's low (long) / high (short) while it was still untaken
     that day.
claim '+': gated trades beat the complement (control-adjusted R).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

CID = "level-to-trade-away-from"
TF = "15min"
LOOKBACK_BARS = 20
PARAMS = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
          "rr": 2.0, "max_hold": "150min", "swing_lookback_bars": LOOKBACK_BARS,
          "day_open_hour": 18, "prior_day_coverage_filter": "none"}
SRC = {
    "tf": "phase3: meta/conjunction_preregistration.md 15m entry TF (YAML ltf 15m/5m)",
    "level_rule": "phase3: locked CISD reading series_open (method_spec 4.2 default)",
    "swing": "phase3: locked 2/2 fractal swings",
    "max_wait": "phase3: locked max_wait=3",
    "rr": "phase3: locked 2R target (method_spec 5.3 minimum 2R)",
    "max_hold": "phase3: 10 entry-TF bars (s1.13)",
    "swing_lookback_bars": "declared-before-run: a 15m swing counts as a relevant "
                           "untaken level only if formed within the prior 20 bars (5h)",
    "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
    "prior_day_coverage_filter": "declared-before-run: prior_hilo without min_coverage "
                                 "(stub sessions are rare; keeps the probe symmetric)",
}


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    ohlc = b[["open", "high", "low", "close"]]
    ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "gate_swing", "gate_pd"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    pos = {t: i for i, t in enumerate(b.index)}
    sw = swing_points(ohlc, 2, 2)
    hi = b["high"].to_numpy(); lo = b["low"].to_numpy()
    isH = sw["swing_high"].to_numpy(); isL = sw["swing_low"].to_numpy()
    close_t = b["close_time"]
    g_sw = np.zeros(len(ev), bool)
    for k, e in enumerate(ev.itertuples()):
        bull = e.direction == "bullish"
        x = pos[e.extreme_time]; s = pos[e.series_start]
        s0 = min(s, x)
        # candidate swings j: confirmed (j+2) strictly before the run into the extreme
        for j in range(max(0, s0 - LOOKBACK_BARS), s0 - 2):
            if bull and isL[j]:
                lvl = lo[j]
                untaken = lo[j + 1:s0].min() >= lvl if s0 > j + 1 else True
                if untaken and lo[s0:x + 1].min() < lvl:
                    g_sw[k] = True; break
            if (not bull) and isH[j]:
                lvl = hi[j]
                untaken = hi[j + 1:s0].max() <= lvl if s0 > j + 1 else True
                if untaken and hi[s0:x + 1].max() > lvl:
                    g_sw[k] = True; break
    # reading b: previous trading day's extreme, untaken before the run began
    run_start = pd.DatetimeIndex(ev["series_start"].where(
        ev["series_start"] <= ev["extreme_time"], ev["extreme_time"]))
    pdl = cl.prior_hilo(run_start, "1D", m1=m1)
    rh = cl.running_hilo(run_start, "1D", m1=m1)    # day hi/lo from bars closed by run start
    ext = ev["extreme_price"].to_numpy()
    bull = (ev["direction"] == "bullish").to_numpy()
    same_day = np.asarray(cl.trading_day(run_start) ==
                          cl.trading_day(pd.DatetimeIndex(close_t.loc[ev["extreme_time"]])))
    rlo = np.nan_to_num(rh["low"].to_numpy(float), nan=np.inf)
    rhi = np.nan_to_num(rh["high"].to_numpy(float), nan=-np.inf)
    pl = pdl["low"].to_numpy(float); ph = pdl["high"].to_numpy(float)
    g_pd = np.where(bull, (ext < pl) & (rlo >= pl), (ext > ph) & (rhi <= ph))
    g_pd = np.nan_to_num(g_pd.astype(float), nan=0).astype(bool) & same_day
    close = pd.DatetimeIndex(close_t.loc[ev["confirm_time"]])
    return pd.DataFrame({
        "decision_time": close, "available_at": close,
        "direction": np.where(bull, 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
        "gate_swing": g_sw, "gate_pd": g_pd})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_cisd15_gates_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["gate_swing"].mean(), ev["gate_pd"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    base_rules = ["baseline: 15m CISD (series_open, 2/2 swings, max_wait 3), decide at the "
                  "confirming bar close, enter next M1 open, stop = protected swing, 2R, 150 min"]
    for reading, col, desc in (
            ("a", "gate_swing", "gate: the run into the CISD extreme swept a confirmed, still "
                                "untaken 15m 2/2 swing low (long) / high (short) formed within "
                                "the prior 20 bars"),
            ("b", "gate_pd", "gate: the run into the CISD extreme swept the previous trading "
                             "day's low (long) / high (short), untaken earlier that day")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min")
        print(reading, {k: res.get(k) for k in ("n", "n_gated", "diff", "ci_lo", "ci_hi",
                                                  "p", "verdict", "verdict_detail")})
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": base_rules + [desc,
                                "claim '+': gated beats complement on control-adjusted R"],
                                "params": PARAMS},
                            params_source=SRC, script=__file__, probe=probe,
                            notes="Contested 'relevant level': reading a = execution-TF "
                                  "swing sweep, reading b = prior-day extreme sweep. SMT "
                                  "substitute and 'too old/untrustworthy' filters not "
                                  "modelled (discretionary).")
        print("wrote", p)
