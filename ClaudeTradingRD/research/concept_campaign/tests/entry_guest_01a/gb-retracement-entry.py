"""gb-retracement-entry — AP's blind limit at 0.7475 of a validly flipped range.

trade_test. After a 15m structure flip (close beyond the last confirmed swing, against
the previous break), rest a limit at the 0.7475 retracement of strong-extreme ->
running opposing extreme; stop beyond the anchor (the strong extreme = level 1.0);
target the 0.41 ('low-hanging fruit').  Order lives 24h or until the next opposite flip.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, bars_arr, m1_arrays, structure_flips, gb_limit_fill, to_utc, NS_MIN  # noqa: E402

TF = "15min"
X_ENTRY, X_TGT = 0.7475, 0.41
EXPIRY_NS = np.int64(24 * 3600 * 10 ** 9)
MAX_HOLD = "24h"
SWING = (2, 2)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    m = m1_arrays(m1)
    fl = structure_flips(b, *SWING)
    rows = []
    for r in fl.itertuples(index=False):
        t_to = min(int(r.flip_t) + EXPIRY_NS, int(r.cancel_t))
        f = gb_limit_fill(m, int(r.flip_t), t_to, int(r.dir), float(r.anchor), float(r.opp0), X_ENTRY)
        if f is None:
            continue
        k, lvl, opp, _ = f
        rng = abs(opp - r.anchor)
        stop_hit_same_bar = (m["l"][k] <= r.anchor) if r.dir == 1 else (m["h"][k] >= r.anchor)
        rows.append((int(m["t"][k]) + NS_MIN, int(r.dir), (1 - X_ENTRY) * rng,
                     (X_ENTRY - X_TGT) * rng, lvl, float(r.anchor), opp, int(r.flip_t),
                     bool(stop_hit_same_bar)))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "limit_px",
                                     "anchor", "opp", "flip_t", "fill_bar_hits_stop"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    ev["flip_t"] = to_utc(ev["flip_t"].to_numpy())
    return ev.drop(columns="dt").sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"gb_retr_{TF}_{X_ENTRY}_{X_TGT}_24h_sw22", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict(), "same-bar stop:", ev.fill_bar_hits_stop.mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties",
              "ctrl_overlap", "avg_R", "win_rate", "drop"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars (forex grid irrelevant: no 4h). Fractal swings 2/2, known at close of bar j+2.",
        "Flip = 15m close beyond the most recent confirmed unbroken swing when the previous break was the other way (valid structure flip).",
        "Strong extreme (anchor, level 1.0) = most extreme price between the broken swing and the flip bar; opposing extreme = running flip-leg extreme, extended by every closed M1 bar until the fill.",
        "Resting limit at the 0.7475 retracement (long: H - 0.7475 (H - L)); filled on the first M1 bar that trades through it; decision = that M1 bar's close.",
        "Order cancelled at the next opposite flip or 24h after the flip, whichever first.",
        "Stop = anchor extreme (stop_dist = 0.2525 x range); target = 0.41 level (target_dist = 0.3375 x range) -> 1.34R.",
        "Distances fixed at the limit price; harness enters at the next M1 open with those distances.",
        "No additional-POI requirement in this book (tested separately in three-pd-array-confluence / gb-levels)."],
        "params": {"tf": TF, "swing_left_right": SWING, "x_entry": X_ENTRY, "x_target": X_TGT,
                   "expiry": "24h", "max_hold": MAX_HOLD, "ctrl_tod_tol_min": 30}}
    ps = {"x_entry": "corpus: gjoRPszj-Qk (via entry/gb-retracement-entry.yaml) 'Place a limit at 0.7475 in the direction of the flip'",
          "x_target": "corpus: gjoRPszj-Qk targets '0.41 (low-hanging fruit)'",
          "tf": "declared-before-run: 15m, one of the concept's listed LTFs (15m/5m/1m/5s); fractal:true",
          "swing_left_right": "declared-before-run: fractal 2/2 (the library's default swing primitive); 'valid' swing has no candle-count rule in the corpus",
          "expiry": "declared-before-run: 24h or next opposite flip; corpus gives no time limit on the resting limit",
          "max_hold": "declared-before-run: 24h wall clock",
          "ctrl_tod_tol_min": "declared-before-run: 30 min NY time-of-day match (README trap 9: fills cluster by hour, concept is not about timing)",
          "stop": "corpus: gjoRPszj-Qk execution 'Beyond the local extreme' / invalidation 'closes through the anchor extreme' -> anchor extreme"}
    notes = (f"fills whose own M1 bar also traded through the anchor stop: {ev.fill_bar_hits_stop.mean():.4f} "
             "(kept; entry at next open with the planned stop distance).")
    p = cl.write_result("gb-retracement-entry", None, res, operationalization=op, params_source=ps,
                        script=__file__, probe=probe, notes=notes)
    print(p)
