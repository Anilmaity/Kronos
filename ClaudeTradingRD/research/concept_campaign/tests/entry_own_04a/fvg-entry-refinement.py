"""fvg-entry-refinement — "Three ways to refine an entry inside a fair value gap" (fwUUkJ5q6tc).

Batch entry_own_04a. gate_test, claim '+': on the SAME gaps, the refined 0.5 (consequent
encroachment) entry beats the unrefined edge entry, after each trade is adjusted by its own
matched random control (so the bigger R-multiple a tighter stop buys is not counted as skill).

Only method 1 (0.5 of the gap) is fully mechanical. Method 2 ("look left" for an overlapping
block, no lookback bound) and method 3 (drop timeframes, no ratio) are not tested; the
concept says the three converge ("the 1-minute order block and the 0.5 fib land in nearly
the same place").

Operationalisation (declared BEFORE the first run):
  gaps: every 1H three-candle FVG (bullish: low[3] > high[1]), known at the 3rd candle's
    close, size >= 0.25 x ATR14(1H) at that close. Parent model = none (every gap), which is
    stated as the baseline book.
  unrefined row (mask False): first M1 candle after the gap is known that trades into the
    gap's near edge (bull: low <= top), within 48h -> decide at that candle's close.
  refined row (mask True): first M1 candle (same or later) that trades to the gap's 0.5
    -> decide at its close.
  both: stop = the gap's far edge ("beyond the gap"); target = the SAME price for both rows,
    near edge + 2 x gap size (inherited parent target, 2R for the unrefined entry). A row
    whose deciding candle already CLOSED beyond the far edge is dropped (gap failed).
  max_hold 10h (10 entry-TF bars at 1H). cluster = gap id (the two rows share a gap).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "fvg-entry-refinement"
P = {"gap_tf": "1h", "min_gap_atr": 0.25, "atr_n": 14, "return_window": "48h",
     "refined_level": 0.5, "target_gap_mult": 2.0, "max_hold": "10h"}


def detect(m1):
    b = cl.build_bars(m1, P["gap_tf"])
    h, l, c = (b[k].to_numpy() for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    atr = pd.Series(tr).rolling(P["atr_n"]).mean().to_numpy()
    b1 = cl.build_bars(m1, "1min")
    lo1, hi1, cl1 = (b1[k].to_numpy() for k in ("low", "high", "close"))
    st1 = b1.index.asi8
    ct1 = pd.DatetimeIndex(b1["close_time"])
    win = pd.Timedelta(P["return_window"]).value
    rows = []
    for k in range(2, len(b)):
        for sgn in (1, -1):
            if sgn == 1:
                if not l[k] > h[k - 2]:
                    continue
                far, near = h[k - 2], l[k]
            else:
                if not h[k] < l[k - 2]:
                    continue
                far, near = l[k - 2], h[k]
            size = abs(near - far)
            if not np.isfinite(atr[k]) or size < P["min_gap_atr"] * atr[k]:
                continue
            known = ct[k].value
            a = np.searchsorted(st1, known, "left")
            z = np.searchsorted(st1, known + win, "left")
            if a >= z:
                continue
            ce = far + P["refined_level"] * (near - far)
            tgt = near + sgn * P["target_gap_mult"] * size
            gid = known * 2 + (sgn == 1)
            if sgn == 1:
                t_near = np.flatnonzero(lo1[a:z] <= near)
                t_ce = np.flatnonzero(lo1[a:z] <= ce)
            else:
                t_near = np.flatnonzero(hi1[a:z] >= near)
                t_ce = np.flatnonzero(hi1[a:z] >= ce)
            for flag, hits in ((False, t_near), (True, t_ce)):
                if not len(hits):
                    continue
                j = a + hits[0]
                if (sgn == 1 and cl1[j] <= far) or (sgn == -1 and cl1[j] >= far):
                    continue
                rows.append((ct1[j], known, sgn, far, tgt, flag, gid))
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px",
            "refined", "gap_id"]
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "known", "direction", "stop_px",
                                     "target_px", "refined", "gap_id"])
    ev["decision_time"] = pd.to_datetime(ev["decision_time"], utc=True)
    ev["available_at"] = ev["decision_time"]     # the touching M1 candle's close
    ev["refined"] = ev["refined"].astype(bool)
    ev["gap_id"] = ev["gap_id"].astype(np.int64)
    ev = ev.sort_values(["decision_time", "gap_id", "refined"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("fvg_ce_refine_1h_v1", lambda: detect(cl.load_m1()))
    print("rows", len(ev), ev["refined"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "refined", mask_available_at="decision_time",
                       max_hold=P["max_hold"], cluster="gap_id")
    for k in ("n", "n_gated", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "gate_rate"):
        print(k, res.get(k))
    op = {"rules": [
        "1H three-candle FVGs, size >= 0.25 ATR14(1H), known at the 3rd candle close",
        "unrefined row: first M1 touch of the near edge within 48h; refined row: first M1 "
        "touch of the gap's 0.5; decide at that M1 close, enter next M1 open",
        "stop at the far edge; common target = near edge + 2 x gap size; drop a row whose "
        "deciding candle closed beyond the far edge",
        "gate_test: refined rows vs unrefined rows on control-adjusted R, clustered by gap"],
        "params": P}
    src = {"gap_tf": "corpus: fwUUkJ5q6tc examples (daily gap -> hourly; 5m -> 1m); concept "
                     "timeframes.htf [1D, 1H, 5m]; 1H chosen",
           "min_gap_atr": "declared-before-run: drop sub-quarter-ATR gaps (M1 noise stop)",
           "atr_n": "declared-before-run: ATR14 yardstick (trap 6: ATR units)",
           "return_window": "declared-before-run: 48h for the first return",
           "refined_level": "corpus: fwUUkJ5q6tc 'throw a 0.5 fib on there and your entry "
                            "would be here'",
           "target_gap_mult": "method_spec: §5.3 2R normal; target inherited from the parent "
                              "model and held fixed for both entries",
           "max_hold": "phase3: 10 entry-TF bars (§1.13) at 1H"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Only refinement method 1 (0.5 of the gap) is operationalised; "
                              "methods 2-3 have no lookback/ratio. Baseline book = every 1H "
                              "FVG's first near-edge touch (no parent model).")
    print(p)
