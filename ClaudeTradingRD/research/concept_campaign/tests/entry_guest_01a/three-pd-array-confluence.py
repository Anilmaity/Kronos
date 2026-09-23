"""three-pd-array-confluence — Rauf's hard count: an entry level is high probability when
THREE PD arrays overlap at the same price.

gate_test on the gb-retracement-entry book (AP's 0.7475 blind limit, the source video
that carries the 'at least one more thing lined up' rule).  At the fill, count the
arrays coinciding with the entry zone 0.705-0.79: the GB level itself (1) plus each of
  - an unmitigated same-direction 15m FVG overlapping the zone,
  - an unmitigated same-direction 1h FVG overlapping the zone,
  - the order block (last opposite-close 15m candle at/before the anchor candle, body)
    overlapping the zone, unmitigated since the flip,
  - the 50% of the anchor (extreme) candle's wick inside the zone.
Gate = count >= 3.  'Unmitigated' = not traded into between its formation and the
moment the running opposing extreme was set (i.e. before the current retracement).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, bars_arr, m1_arrays, structure_flips, gb_limit_fill, fvgs, to_utc, NS_MIN  # noqa: E402

TF = "15min"
X_ENTRY, X_TGT, Z_LO, Z_HI = 0.7475, 0.41, 0.705, 0.79
EXPIRY_NS = np.int64(24 * 3600 * 10 ** 9)
MAX_HOLD = "24h"
SWING = (2, 2)
N_REQ = 3
OB_LOOKBACK = 10


def _unmitigated(m, t0, t1, d, lo, hi):
    """No M1 bar in [t0, t1) traded into the array (long: low <= hi; short: high >= lo)."""
    a = np.searchsorted(m["t"], t0, "left")
    z = np.searchsorted(m["t"], t1, "left")
    if z <= a:
        return True
    return bool(m["l"][a:z].min() > hi) if d == 1 else bool(m["h"][a:z].max() < lo)


def _fvg_hit(fv, m, d, anchor_t, t_set, zlo, zhi):
    f = fv[(fv["dir"].to_numpy() == d) & (fv["t"].to_numpy() >= anchor_t) & (fv["t"].to_numpy() <= t_set)]
    for g in f.itertuples(index=False):
        if g.hi >= zlo and g.lo <= zhi and _unmitigated(m, int(g.t), t_set, d, g.lo, g.hi):
            return True
    return False


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    b1h = bars_arr(cl.build_bars(m1, "1h"))
    m = m1_arrays(m1)
    fl = structure_flips(b, *SWING)
    fv15, fv1h = fvgs(b), fvgs(b1h)
    rows = []
    for r in fl.itertuples(index=False):
        d, A = int(r.dir), float(r.anchor)
        t_to = min(int(r.flip_t) + EXPIRY_NS, int(r.cancel_t))
        f = gb_limit_fill(m, int(r.flip_t), t_to, d, A, float(r.opp0), X_ENTRY)
        if f is None:
            continue
        k, lvl, opp, k_opp = f
        rng = abs(opp - A)
        t_set = int(m["t"][k_opp]) + NS_MIN if k_opp >= 0 else int(r.flip_t)
        z1, z2 = opp - d * Z_LO * rng, opp - d * Z_HI * rng
        zlo, zhi = min(z1, z2), max(z1, z2)
        ab = int(r.anchor_bar)
        anchor_t = int(b["start"][ab])
        p_f15 = _fvg_hit(fv15, m, d, anchor_t, t_set, zlo, zhi)
        p_f1h = _fvg_hit(fv1h, m, d, anchor_t, t_set, zlo, zhi)
        # order block: last opposite-close candle at/before the anchor candle
        p_ob = False
        for j in range(ab, max(-1, ab - OB_LOOKBACK), -1):
            if (b["c"][j] < b["o"][j]) if d == 1 else (b["c"][j] > b["o"][j]):
                lo_, hi_ = sorted((b["o"][j], b["c"][j]))
                p_ob = (hi_ >= zlo and lo_ <= zhi and
                        _unmitigated(m, int(r.flip_t), t_set, d, lo_, hi_))
                break
        if d == 1:
            wick_mid = b["l"][ab] + 0.5 * (min(b["o"][ab], b["c"][ab]) - b["l"][ab])
        else:
            wick_mid = b["h"][ab] - 0.5 * (b["h"][ab] - max(b["o"][ab], b["c"][ab]))
        p_wick = bool(zlo <= wick_mid <= zhi)
        cnt = 1 + int(p_f15) + int(p_f1h) + int(p_ob) + int(p_wick)
        rows.append((int(m["t"][k]) + NS_MIN, d, (1 - X_ENTRY) * rng, (X_ENTRY - X_TGT) * rng, lvl,
                     int(r.flip_t), p_f15, p_f1h, p_ob, p_wick, cnt, cnt >= N_REQ))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "limit_px", "flip_t",
                                     "poi_fvg15", "poi_fvg1h", "poi_ob", "poi_wick50", "n_arrays", "stack3"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    ev["flip_t"] = to_utc(ev["flip_t"].to_numpy())
    return ev.drop(columns="dt").sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"pd3_gb_{TF}_{X_ENTRY}_{N_REQ}_ob{OB_LOOKBACK}_sw22", lambda: detect(cl.load_m1()))
    print(len(ev), ev["n_arrays"].value_counts().sort_index().to_dict(),
          ev[["poi_fvg15", "poi_fvg1h", "poi_ob", "poi_wick50"]].mean().round(3).to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "stack3", mask_available_at="decision_time", max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties", "gate_rate", "firing_rate"):
        print(k, res.get(k))
    op = {"rules": [
        "Baseline book = gb-retracement-entry exactly (15m flips, 0.7475 blind limit, stop anchor, target 0.41, 24h/opposite-flip expiry).",
        "Arrays counted at the fill against the zone [0.705, 0.79] of anchor->running extreme: the GB level (always 1); unmitigated same-direction 15m FVG overlapping the zone; unmitigated same-direction 1h FVG overlapping the zone; order block = last opposite-close 15m candle (body) at/before the anchor candle within 10 bars, overlapping the zone and untouched since the flip; 50% of the anchor candle's extreme wick inside the zone.",
        "FVGs must be stamped (third bar closed) between the anchor candle start and the moment the running extreme was set; unmitigated = no M1 trade into the gap from its stamp until that moment.",
        "Gate stack3 = n_arrays >= 3 (Rauf's count); complement = 1-2 arrays."],
        "params": {"n_required": N_REQ, "zone": [Z_LO, Z_HI], "ob_lookback_bars": OB_LOOKBACK, "tf": TF,
                   "htf_fvg_tf": "1h", "max_hold": MAX_HOLD, "swing_left_right": SWING, "ctrl_tod_tol_min": 30}}
    ps = {"n_required": "corpus: wB-fQiT_UDo 'when you have three PD arrays overlapping each other'",
          "zone": "corpus: gjoRPszj-Qk '0.705/0.7475/0.79 form the deep-retracement entry zone'",
          "poi_set": "corpus: gjoRPszj-Qk POI list 'unmitigated order block, an imbalance, ... the 50 percent of an extreme wick' (internal-flip-zone 50% and volume node not computable from OHLC-only / not attempted)",
          "ob_lookback_bars": "declared-before-run: 10 bars",
          "htf_fvg_tf": "declared-before-run: 1h (listed HTF)",
          "tf": "declared-before-run: 15m", "swing_left_right": "declared-before-run: fractal 2/2",
          "max_hold": "declared-before-run: 24h", "ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)"}
    p = cl.write_result("three-pd-array-confluence", None, res, operationalization=op, params_source=ps,
                        script=__file__, probe=probe,
                        notes="Overlap = any price intersection with the zone (the corpus defines no tolerance). DTR's T-spot exception not tested.")
    print(p)
