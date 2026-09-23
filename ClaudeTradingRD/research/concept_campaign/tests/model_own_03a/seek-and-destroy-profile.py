"""seek-and-destroy-profile — Seek & Destroy (broadening daily profile). CONTESTED; mixed voice.

Recognition A (the load-bearing rule, 4WCiIyCiBrQ / Tjk9bXERZy0), readable before New York:
London (02:00-05:00 NY) takes BOTH the Asia (20:00-00:00 NY) high and low, and London's close
(05:00) is back inside the Asia range — it failed to displace out of either side. Both
windows need >= 50% of their nominal minutes. Known at the London window's end.

Reading a — the stand-aside rule ("take no trades — the order flow is not readable"):
  gate_test on a baseline book of New-York-AM (08:30-12:00) 15m bare CISD trades (phase-3
  rung-0 config: series_open, 2/2 swing, max_wait 3, stop at the protected swing, 2R,
  150 min). Gate = the day is flagged S&D. claim '-': trades on S&D days are WORSE.
Reading b — the tradeable version, outside-in deviations (PlZD45uLPjE, Tjk9bXERZy0): on a
  flagged day, in NY AM 08:30-12:00, a 15m bar that trades above London's high and closes
  back below it -> short at that close (mirrored for London's low -> long); stop at the
  deviation extreme (highest high since 08:30); target = London range equilibrium (the
  first rung of the target ladder); first deviation per side per day; 150 min hold.
  trade_test claim '+'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                            # noqa: E402
from detectors.cisd import cisd_events                              # noqa: E402

CID = "seek-and-destroy-profile"
TF = "15min"
NY = ("08:30", "12:00")
MAX_HOLD = "150min"
MIN_COV = 0.5


def sd_days(m1: pd.DataFrame) -> pd.DataFrame:
    """Per trading day: S&D flag (recognition A) and the London range. Rows only for days
    where both windows are adequately covered."""
    a = cl.window_hilo("asia", m1)
    lo = cl.window_hilo("london", m1)
    j = a[["high", "low", "n_m1"]].join(
        lo[["high", "low", "close", "n_m1", "available_at"]], lsuffix="_as", rsuffix="_ld",
        how="inner")
    j = j[(j["n_m1_as"] >= MIN_COV * 240) & (j["n_m1_ld"] >= MIN_COV * 180)]
    j["sd"] = ((j["high_ld"] > j["high_as"]) & (j["low_ld"] < j["low_as"])
               & (j["close"] < j["high_as"]) & (j["close"] > j["low_as"]))
    return j


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "sd_day", "sd_at"]
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})
    out = out[cl.in_window(out["decision_time"], *NY)]
    days = sd_days(m1)
    td = cl.trading_day(out["decision_time"])
    ok = td.isin(days.index)
    out = out[np.asarray(ok)].copy()
    td = td[np.asarray(ok)]
    out["sd_day"] = days.loc[td, "sd"].to_numpy().astype(bool)
    out["sd_at"] = pd.DatetimeIndex(days.loc[td, "available_at"]).to_numpy()
    out["sd_at"] = pd.DatetimeIndex(out["sd_at"]).tz_localize("UTC") \
        if pd.DatetimeIndex(out["sd_at"]).tz is None else out["sd_at"]
    return out[cols].reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    b = cl.build_bars(m1, TF)
    b = b[cl.in_window(b["close_time"] - pd.Timedelta(minutes=15), *NY)]
    days = sd_days(m1)
    days = days[days["sd"]]
    if b.empty or days.empty:
        return pd.DataFrame(columns=cols)
    td = cl.trading_day(b.index)
    rows = []
    for day, g in b.groupby(td):
        if day not in days.index:
            continue
        L = days.loc[day]
        eq = (L["high_ld"] + L["low_ld"]) / 2.0
        done = {1: False, -1: False}
        hi_run, lo_run = -np.inf, np.inf
        for t, r in g.iterrows():
            hi_run, lo_run = max(hi_run, r["high"]), min(lo_run, r["low"])
            if not done[-1] and r["high"] > L["high_ld"] and r["close"] < L["high_ld"]:
                done[-1] = True
                if r["close"] > eq:
                    rows.append({"decision_time": r["close_time"],
                                 "available_at": r["close_time"], "direction": -1,
                                 "stop_px": float(hi_run), "target_px": float(eq)})
            if not done[1] and r["low"] < L["low_ld"] and r["close"] > L["low_ld"]:
                done[1] = True
                if r["close"] < eq:
                    rows.append({"decision_time": r["close_time"],
                                 "available_at": r["close_time"], "direction": 1,
                                 "stop_px": float(lo_run), "target_px": float(eq)})
    return pd.DataFrame(rows, columns=cols)


COMMON_SRC = {
    "asia_window": "session_window_fit: Asia 20:00-00:00 (killzones.yaml, SESSION_WINDOWS)",
    "london_window": "method_spec: §2.5 daily-profile session windows, London 02:00-05:00",
    "ny_window": "method_spec: §2.5 New York a.m. 08:30-12:00",
    "recognition": "corpus: 4WCiIyCiBrQ 'London will take both sides of the Asia range' + "
                   "Tjk9bXERZy0 'if London session took Asia high and low then I'm "
                   "anticipating New York'; 'failed to displace' = London's close back inside "
                   "Asia (threshold_fits: displacement = a close beyond the level)",
    "min_cov": "declared-before-run: both windows need >= 50% of nominal minutes (trap 6)",
    "tf": "corpus: PlZD45uLPjE — ltf 15m/5m/1m; phase3 15m primary entry TF",
    "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
COMMON_PARAMS = {"asia_window": "20:00-00:00", "london_window": "02:00-05:00",
                 "ny_window": "08:30-12:00",
                 "recognition": "London high>Asia high & London low<Asia low & London close "
                                "inside Asia range", "min_cov": MIN_COV, "tf": TF,
                 "max_hold": MAX_HOLD}

if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        ev = cl.cache_frame(f"{CID}_a_v1", lambda: detect_a(cl.load_m1()))
        print("a", len(ev), "sd share", ev["sd_day"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "sd_day", mask_available_at="sd_at", max_hold=MAX_HOLD,
                           claim="-")
        for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                  "ties", "ctrl_overlap"):
            print(" ", k, res.get(k))
        op = {"rules": [
            "baseline: 15m bare CISD (series_open, 2/2, max_wait 3), decided inside NY "
            "08:30-12:00; stop at protected swing; 2R; exit after 150 min",
            "gate: the trading day is Seek & Destroy by recognition A (London took both Asia "
            "extremes and closed back inside the Asia range), known at 05:00 NY",
            "claim '-': gated (S&D-day) trades are worse than the rest -> stand aside"],
            "params": {**COMMON_PARAMS, "baseline": "15m CISD rung-0 in NY AM", "rr": 2.0}}
        src = {**COMMON_SRC, "baseline": "phase3: rung-0 CISD config (conjunction "
                                         "preregistration), NY AM restriction per §2.5",
               "rr": "phase3: rung-0 2R target"}
        print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe,
                              notes="Stand-aside reading tested as a gate with claim '-'."))
    if "b" in which:
        ev = cl.cache_frame(f"{CID}_b_v1", lambda: detect_b(cl.load_m1()))
        print("b", len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="10D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                  "verdict_detail", "ties", "ctrl_overlap", "dropped"):
            print(" ", k, res.get(k))
        op = {"rules": [
            "only on days flagged Seek & Destroy by recognition A",
            "NY 08:30-12:00, 15m: first bar per side that trades beyond London's high (low) and "
            "closes back inside -> short (long) at that close, if the close is on the far side "
            "of London's EQ",
            "stop at the highest high (lowest low) since 08:30; target London range EQ; exit "
            "after 150 min"],
            "params": {**COMMON_PARAMS, "target": "London range EQ", "entry": "outside-in"}}
        src = {**COMMON_SRC,
               "target": "corpus: PlZD45uLPjE target ladder — 'equilibrium (0.5) of the range, as "
                         "first target'; method_spec §2.5 seek-destroy-target-ladder",
               "entry": "corpus: PlZD45uLPjE 'the first thing I do is identify deviations from "
                        "the range' — outside-in only (seek-destroy-outside-in-entry)"}
        print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                              script=__file__, probe=probe))
