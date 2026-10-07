"""continuation-over-reversal, reading u1007a (TTrades live stream h1ZQWWQDhKA).

New claim: "I don't normally trade reversals like this because ... your win rate's going to
be like 20, 30, 40% less than it normally is" -- said on a 5m-chart MNQ reversal short.
Prior reading (model_own_02b, 15m book, NULL) tested the sign only. This reading tests the
claim on the timeframe the quote was made on (5m CISD book; the stream's model is "5 minute
and 15 second", 2R) and records raw win rates per arm in notes. The verdict reads
control-adjusted R, not raw WR (trap 3); the claimed WR gap's R size is not fixed in advance
(~half the book exits on time), so no R magnitude is claimed here.
AUDIT 2026-10-07 (vault context): rules text corrected -- of two CISDs confirming on the same
bar the EARLIER-extreme one is scored and the later one skipped (was written the other way
round), and the "~0.24R" magnitude line dropped (it assumed every exit is -1R/+2R). Detector,
params and test unchanged.

Rules: identical to the prior reading's detector (phase-3 CISD, decide at confirm close,
stop = protected swing, 2R, 10 entry-TF bars), TF = 5min.
  reversal     = previous CISD opposite direction
  continuation = previous CISD same direction, its protected swing held to this confirm,
                 new extreme formed after its confirm and beyond it (HL / LH); re-anchors dropped
gate = is_cont, claim '+' (reversals worse). Raw per-arm win rates go in notes only.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C

TF = "5min"
RR = 2.0
MAX_HOLD = "50min"


def detect(m1):
    b = C.complete_bars(m1, TF)
    # same-bar opposite CISDs come out of cisd_events in a history-dependent order (probe
    # caught it on 5m); fix the order: by confirm time, then by extreme time (latest last)
    cz = C.cisd_table(b).sort_values(["t", "extreme_start", "dir"], kind="stable").reset_index(drop=True)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_cont"]
    if len(cz) < 2:
        return pd.DataFrame(columns=cols)
    lows = b["low"].to_numpy(); highs = b["high"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"]).as_unit("ns").asi8
    tpos = np.searchsorted(ct, pd.DatetimeIndex(cz["t"]).as_unit("ns").asi8)
    rows = []
    for k in range(1, len(cz)):
        p, c = cz.iloc[k - 1], cz.iloc[k]
        if c["t"] == p["t"]:
            continue
        if c["dir"] != p["dir"]:
            is_cont = False
        else:
            a0, a1 = tpos[k - 1] + 1, tpos[k] + 1
            if c["extreme_start"] <= p["t"] - pd.Timedelta(TF) or a1 <= a0:
                continue
            if c["dir"] == 1:
                held = lows[a0:a1].min() > p["stop"]; beyond = c["extreme_price"] > p["stop"]
            else:
                held = highs[a0:a1].max() < p["stop"]; beyond = c["extreme_price"] < p["stop"]
            if not (held and beyond):
                continue
            is_cont = True
        rows.append({"decision_time": c["t"], "available_at": c["t"], "direction": int(c["dir"]),
                     "stop_px": float(c["stop"]), "rr": RR, "is_cont": is_cont})
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    out["is_cont"] = out["is_cont"].astype(bool)
    return out


if __name__ == "__main__":
    ev = cl.cache_frame("cor_u1007a_5m_v2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["is_cont"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    r = cl.gate_test(ev, "is_cont", mask_available_at="decision_time", max_hold=MAX_HOLD,
                     keep_trades=True)
    tr = r.pop("_trades", None)
    wr_note = ""
    if tr is not None:
        w = tr["net_R"].to_numpy() > 0; g = tr["gate"].to_numpy().astype(bool)
        wr_note = (f"raw win rate (net_R>0): continuation {w[g].mean():.3f} (n={g.sum()}), "
                   f"reversal {w[~g].mean():.3f} (n={(~g).sum()}); claimed reversal WR gap 20-40% "
                   "(relative or pp, unstated). Raw WR is descriptive only (trap 3).")
    print(wr_note)
    print({k: r.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                 "verdict_detail", "ties", "exposure_bars")})
    params = {"tf": TF, "cisd": "series_open, swing 2/2, max_wait 3, min_series 1",
              "rr": RR, "max_hold": MAX_HOLD,
              "continuation_def": "prev CISD same dir, its protected swing held to this confirm, "
                                  "new extreme after prev confirm and beyond prev protected swing"}
    src = {"tf": "corpus: h1ZQWWQDhKA live MNQ reversal short read on 5m charts (draft timeframes htf 5m; "
                 "15s LTF not available on M1 data)",
           "cisd": "phase3: locked CISD config",
           "rr": "corpus: U1NJUh1RqMw 'entry on the close, my stop on the low' 2R target",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "continuation_def": "corpus: Qv6Ux_Z8VrA 'waiting for a lower high if bearish and a higher low if bullish'; "
                               "same definition as prior reading (model_own_02b)"}
    cl.write_result("continuation-over-reversal", "u1007a", r,
                    operationalization={"rules": [
                        "5m phase-3 CISD events, decide at the confirming close, enter next M1 open, "
                        "stop at the protected swing, 2R, exit after 50 min",
                        "reversal = previous CISD opposite direction; continuation = previous CISD same "
                        "direction whose protected swing held, new extreme beyond it after its confirmation; "
                        "re-anchors dropped; CISDs confirming on the same bar are ordered by extreme time (the "
                        "earlier one is scored, the later one is skipped as an event but is 'previous' for "
                        "the next event)",
                        "gate = continuation vs reversal complement; claim '+' (h1ZQWWQDhKA: reversal "
                        "win rate '20, 30, 40% less'); verdict reads control-adjusted R, raw WR in notes only"],
                        "params": params},
                    params_source=src, script=__file__, probe=probe, notes=wr_note or None)
