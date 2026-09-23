"""upper-half-positioning — gate_test.

Concept: when trading toward a defined target, the entry must sit in the half of the
swing-to-target distance nearer the swing (upper half for shorts, lower half for longs);
entries in the half nearer the target are rejected.

Baseline book (stated): phase-3 rung-0 1h CISD (series_open, 2/2 swing, max_wait 3),
decided at the confirming bar's close, stop = protected swing, TARGET = the prior NY
trading day's extreme in the trade direction (PDH for longs / PDL for shorts; the
"defined target" — method_spec §5.2 #1 previous-candle unswept extreme), kept only when
that target is still untaken today and beyond the entry.
Gate: (entry - swing) <= 0.5 * (target - swing), mirrored for shorts.
claim '+': gated (swing-half) entries beat the target-half entries, control-adjusted.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import *   # noqa: F401,F403
from _common import cl, np, pd, cisd_frame, complete_bars, PHASE3_SRC

CID = "upper-half-positioning"
TF = "1h"
HOLD = "10h"
HALF = 0.5


def detect(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_frame(b)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "in_half"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DatetimeIndex(ev["conf_close_time"])
    pdl = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(t, "1D", m1=m1)
    sgn = ev["sgn"].to_numpy()
    entry = ev["confirm_close"].to_numpy(float)
    swing = ev["protected_swing"].to_numpy(float)
    tgt = np.where(sgn > 0, pdl["high"].to_numpy(float), pdl["low"].to_numpy(float))
    today_ext = np.where(sgn > 0, run["high"].to_numpy(float), run["low"].to_numpy(float))
    untaken = np.where(sgn > 0, today_ext < tgt, today_ext > tgt)
    ahead = np.where(sgn > 0, tgt > entry, tgt < entry)
    valid_stop = np.where(sgn > 0, swing < entry, swing > entry)
    keep = np.isfinite(tgt) & np.isfinite(today_ext) & untaken & ahead & valid_stop
    d_entry = np.abs(entry - swing)
    d_tgt = np.abs(tgt - swing)
    out = pd.DataFrame({
        "decision_time": t, "available_at": t, "direction": sgn,
        "stop_px": swing, "target_px": tgt,
        "in_half": d_entry <= HALF * d_tgt,
    })[keep].reset_index(drop=True)
    return out[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_1h_cisd_pdhl", lambda: detect(cl.load_m1()))
    print(len(ev), ev["in_half"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"], probe["events_compared"])
    res = cl.gate_test(ev, "in_half", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "exposure_bars", "ties", "gate")})
    op = {"rules": [
        "baseline: 1h bars (UTC-aligned), CISD = close through the open of the first candle of the "
        "opposing-close series after a 2/2 fractal swing, within 3 bars (phase-3 rung 0)",
        "decide at the CISD confirming bar's close; enter next M1 open; stop at the protected swing",
        "target = prior NY trading day's high (longs) / low (shorts), prior_hilo 1D min_coverage 0.5; "
        "event kept only if today's running extreme has not yet taken it and it lies beyond the entry",
        "gate in_half: |entry - swing| <= 0.5 * |target - swing| (entry in the swing-side half)",
        "exit at target, stop or 10h"],
        "params": {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "target": "prior day extreme (PDH/PDL), untaken", "half": HALF,
                   "max_hold": HOLD, "min_coverage": 0.5}}
    src = {"tf": PHASE3_SRC, "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC,
           "target": "method_spec: §5.2 #1 previous candles' unswept extremes (previous-period-high-low); "
                     "phase3 §1.12 structural secondary target",
           "half": "corpus: uzPGXVYpVGc upper 50% of swing-to-target distance (upper-half-positioning.yaml)",
           "max_hold": "phase3: §1.13 10 entry-TF periods",
           "min_coverage": "declared-before-run: skip stub sessions (<50% of median M1 count) per README trap 6"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes=f"gate firing rate {ev['in_half'].mean():.3f}")
    print(p)
