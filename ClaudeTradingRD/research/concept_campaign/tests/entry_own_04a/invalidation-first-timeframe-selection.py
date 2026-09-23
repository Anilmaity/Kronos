"""invalidation-first-timeframe-selection — "Choose the timeframe by where the stop can go".

Batch entry_own_04a. Contested -> two readings, both gate_tests on one detector frame.

Setup (both readings): 1H CISD (phase-3 locked config: series_open, 2/2 swings, max_wait 3),
decided at the confirming 1H close. The HTF objective is fixed at that moment and never moved:
T = 1H close + 2 x (1H close - 1H protected swing) ("targets stay on the higher timeframe";
"2R described as normal").

Rows (per setup id):
  A  structure-TF execution: enter at the 1H CISD close, stop = 1H protected swing, target T.
  B  LTF refinement (habit/default 5m): within 36 5m candles (3h) after the 1H close, the first
     5m CISD in the same direction (close through the open of the opposing-close series that
     made the pullback extreme since the 1H close; cisd.py run rule). Cancel if the 1H protected
     swing trades first or the 5m close is already beyond T. Stop = the 5m pullback extreme.
  C  the same 5m entry as B, but the stop at the 1H protected swing (the genuine, structural
     invalidation) instead of the 5m swing.
All rows: target T, max_hold 10h (10 bars of the 1H structure TF), cluster = setup id.

reading a (the top-down video iEaMbuFZb24: "I don't need three time frames ... dropping lower is
  to increase your risk to reward toward the same objective"): gate B (mask) vs A, claim '+'
  (the LTF refinement improves the control-adjusted outcome).
reading b (variant definition: "ask where the invalidation can be placed; that level determines
  the entry, not a default timeframe"): gate C (mask) vs B, claim '+' (a stop at the genuine
  structural invalidation beats the default-timeframe swing stop, same entry).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "invalidation-first-timeframe-selection"
P = {"structure_tf": "1h", "cisd_level_rule": "series_open", "swing": "2/2", "max_wait": 3,
     "min_series": 1, "htf_rr": 2.0, "exec_tf": "5min", "refine_wait_bars": 36,
     "max_hold": "10h", "grid": "UTC-aligned 1h"}


def _series_level(o, c, i, bullish, max_len=10):
    """Mirror of detectors.cisd._run_into_extreme + series_open level."""
    q = (lambda k: c[k] < o[k]) if bullish else (lambda k: c[k] > o[k])
    end = i
    while end > 0 and not q(end):
        end -= 1
        if i - end > 2:
            return None
    if not q(end):
        return None
    start = end
    while start > 0 and q(start - 1) and (end - start + 1) < max_len:
        start -= 1
    return o[start]


def detect(m1):
    b = cl.build_bars(m1, P["structure_tf"])
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule=P["cisd_level_rule"],
                     left=2, right=2, max_wait=P["max_wait"], min_series=P["min_series"])
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "arm",
            "setup_id", "is_B", "is_C"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    b5 = cl.build_bars(m1, P["exec_tf"])
    o5, h5, l5, c5 = (b5[k].to_numpy() for k in ("open", "high", "low", "close"))
    st5 = b5.index.asi8
    ct5 = pd.DatetimeIndex(b5["close_time"])
    rows = []
    for _, e in ev.iterrows():
        d = 1 if e["direction"] == "bullish" else -1
        t1 = b.loc[e["confirm_time"], "close_time"]
        c1 = float(e["confirm_close"])
        s1 = float(e["protected_swing"])
        risk = (c1 - s1) * d
        if not risk > 0:
            continue
        T = c1 + d * P["htf_rr"] * risk
        sid = int(pd.Timestamp(t1).value) * 2 + (d == 1)
        rows.append((t1, d, s1, T, "A", sid))
        a = np.searchsorted(st5, pd.Timestamp(t1).value, "left")
        z = min(len(b5), a + P["refine_wait_bars"])
        ext_i = None
        for i in range(a, z):
            if (d == 1 and l5[i] <= s1) or (d == -1 and h5[i] >= s1):
                break                               # HTF invalidation traded first
            if ext_i is None or (d == 1 and l5[i] < l5[ext_i]) or (d == -1 and h5[i] > h5[ext_i]):
                ext_i = i
                continue
            lvl = _series_level(o5, c5, ext_i, d == 1)
            if lvl is None:
                continue
            if (d == 1 and c5[i] > lvl) or (d == -1 and c5[i] < lvl):
                if (d == 1 and c5[i] >= T) or (d == -1 and c5[i] <= T):
                    break
                ext = l5[ext_i] if d == 1 else h5[ext_i]
                rows.append((ct5[i], d, ext, T, "B", sid))
                rows.append((ct5[i], d, s1, T, "C", sid))
                break
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px",
                                      "arm", "setup_id"])
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = out["decision_time"]
    out["setup_id"] = out["setup_id"].astype(np.int64)
    out["is_B"] = out["arm"] == "B"
    out["is_C"] = out["arm"] == "C"
    out = out.sort_values(["decision_time", "setup_id", "arm"]).reset_index(drop=True)
    return out[cols]


def show(res):
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties",
              "exposure_bars", "ctrl_overlap"):
        print(" ", k, res.get(k))


if __name__ == "__main__":
    full = cl.cache_frame("invfirst_1h_cisd_5m_refine_v1", lambda: detect(cl.load_m1()))
    print("rows", len(full), full["arm"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, full, lookback="20D")
    print("probe", probe.get("passed"))
    # the two readings score different row subsets of the probed frame; each subset is a
    # filter of the SAME detector output by a probed column, so re-probe each subset.

    def det_a(m1):
        x = detect(m1)
        return x[x["arm"].isin(["A", "B"])].reset_index(drop=True)

    def det_b(m1):
        x = detect(m1)
        return x[x["arm"].isin(["B", "C"])].reset_index(drop=True)

    ev_a = full[full["arm"].isin(["A", "B"])].reset_index(drop=True)
    ev_b = full[full["arm"].isin(["B", "C"])].reset_index(drop=True)
    pa = cl.probe_lookahead(det_a, ev_a, lookback="20D")
    pb = cl.probe_lookahead(det_b, ev_b, lookback="20D")
    common_src = {
        "structure_tf": "corpus: iEaMbuFZb24 hourly structure timeframe executed directly",
        "cisd_level_rule": "phase3: locked CISD config (conjunction_preregistration §1.8-1.13)",
        "swing": "phase3: 2/2 fractal swings", "max_wait": "phase3: max_wait=3",
        "min_series": "phase3: min_series=1",
        "htf_rr": "corpus: concept execution.targets 'Sized in R from that stop; 2R described "
                  "as normal'",
        "exec_tf": "corpus: concept timeframes.ltf [15m, 5m]; 5m chosen (1H/5m pairing, "
                   "method_spec §1.2)",
        "refine_wait_bars": "declared-before-run: 3h of 5m candles for the LTF entry",
        "max_hold": "phase3: 10 structure-TF bars (§1.13) -> 10h, same for every arm",
        "grid": "phase3: 1h bars UTC-aligned as in the example book"}
    ra = cl.gate_test(ev_a, "is_B", mask_available_at="decision_time", max_hold=P["max_hold"],
                      cluster="setup_id")
    print("reading a")
    show(ra)
    op_a = {"rules": [
        "1H CISD setup (locked phase-3 config); HTF target T = 1H close + 2R of the 1H stop",
        "arm A: enter at 1H close, stop 1H protected swing, target T",
        "arm B (mask): first same-direction 5m CISD within 3h after the 1H close (cancel if the "
        "1H protected swing trades first), stop = 5m pullback extreme, target T",
        "gate_test B vs A on control-adjusted R, clustered by setup; 10h exit"], "params": P}
    pa_ = cl.write_result(CID, "a", ra, operationalization=op_a, params_source=common_src,
                          script=__file__, probe=pa,
                          notes="Reading a (top-down video): dropping a timeframe is only to "
                                "improve R toward the same HTF objective; either works. Claim "
                                "'+' = the 5m refinement improves the control-adjusted outcome.")
    print(pa_)
    rb = cl.gate_test(ev_b, "is_C", mask_available_at="decision_time", max_hold=P["max_hold"],
                      cluster="setup_id")
    print("reading b")
    show(rb)
    op_b = {"rules": [
        "same 1H CISD setups and 5m entries as reading a",
        "arm B: 5m entry, stop at the default-timeframe (5m) pullback extreme",
        "arm C (mask): same 5m entry, stop at the genuine structural invalidation (1H protected "
        "swing)", "both target T; gate_test C vs B, clustered by setup; 10h exit"],
        "params": P}
    pb_ = cl.write_result(CID, "b", rb, operationalization=op_b, params_source=common_src,
                          script=__file__, probe=pb,
                          notes="Reading b (variant definition): the level that genuinely "
                                "invalidates the idea, not the default timeframe's swing, sets "
                                "the stop. Claim '+' = stop at the 1H invalidation beats the 5m "
                                "habit stop on the same entry.")
    print(pb_)
