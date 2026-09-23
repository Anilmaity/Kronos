"""gb-range-return-entry — AP's second entry: body close beyond the 0.41 + displacement,
then a limit back at the 0.41 trading toward the deep zone (0.7475).

trade_test. After a 15m structure flip (as gb-retracement-entry), the first 15m close
beyond the 0.41 retracement (and beyond any earlier wick that pierced it) is the
signal; displacement over the next 4 bars (threshold_fits N=4, r=1.5, d=0.65) must
follow or the flip is not acted on.  Then a limit at the 0.41 against the flip
direction, stop at the opposing extreme ('maybe at this extreme'), target 0.7475.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_01a")
from common01a import cl, bars_arr, m1_arrays, structure_flips, to_utc, NS_MIN  # noqa: E402

TF = "15min"
X_SIG, X_TGT = 0.41, 0.7475
N_DISP, R_DISP, D_DISP = 4, 1.5, 0.65
SEARCH_NS = np.int64(24 * 3600 * 10 ** 9)
EXPIRY_NS = np.int64(24 * 3600 * 10 ** 9)
MAX_HOLD = "24h"
SWING = (2, 2)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bars_arr(cl.build_bars(m1, TF))
    m = m1_arrays(m1)
    fl = structure_flips(b, *SWING)
    h, l, c, ct = b["h"], b["l"], b["c"], b["close_t"]
    n = len(h)
    rows = []
    for r in fl.itertuples(index=False):
        d, A = int(r.dir), float(r.anchor)
        # work in "long-flip" coordinates: s*price, so the flip leg always goes up
        s = 1.0 if d == 1 else -1.0
        opp = s * float(r.opp0)
        lo_anchor = s * A
        hb = int(r.bar)
        pierce = np.inf
        sig = -1
        i = int(r.bar) + 1
        while i < n and ct[i] <= int(r.flip_t) + SEARCH_NS:
            hi_i = s * h[i] if s > 0 else s * l[i]       # "high" in flip coordinates
            lo_i = s * l[i] if s > 0 else s * h[i]
            cl_i = s * c[i]
            if cl_i < lo_anchor:                          # anchor closed through: range void
                break
            if hi_i > opp:
                opp, hb, pierce = hi_i, i, np.inf
            lvl = opp - X_SIG * (opp - lo_anchor)
            if cl_i < lvl and cl_i < pierce:
                sig = i
                break
            if i > hb and lo_i < lvl:
                pierce = min(pierce, lo_i)
            i += 1
        if sig < 0 or sig - N_DISP < 0 or sig + N_DISP - 1 >= n:
            continue
        H = opp
        lvl = H - X_SIG * (H - lo_anchor)
        pre = slice(sig - N_DISP, sig)
        win = slice(sig, sig + N_DISP)
        ph, pl = (s * h[pre], s * l[pre]) if s > 0 else (s * l[pre], s * h[pre])
        wh, wl = (s * h[win], s * l[win]) if s > 0 else (s * l[win], s * h[win])
        pre_rng = ph.max() - pl.min()
        if not pre_rng > 0:
            continue
        if wh.max() > H:                                  # returned through the extreme
            continue
        if (wh.max() - wl.min()) / pre_rng < R_DISP or (lvl - wl.min()) / pre_rng < D_DISP:
            continue
        t_dec = int(ct[sig + N_DISP - 1])
        a = np.searchsorted(m["t"], t_dec, "left")
        z = np.searchsorted(m["t"], t_dec + EXPIRY_NS, "left")
        px = s * lvl
        seg = m["h"][a:z] >= px if d == 1 else m["l"][a:z] <= px
        hit = np.flatnonzero(seg)
        if not len(hit):
            continue
        k = a + int(hit[0])
        rng = H - lo_anchor
        rows.append((int(m["t"][k]) + NS_MIN, -d, X_SIG * rng, (X_TGT - X_SIG) * rng, px,
                     s * H, A, int(r.flip_t), t_dec))
    ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_dist", "target_dist", "limit_px",
                                     "extreme", "anchor", "flip_t", "signal_t"])
    ev.insert(0, "decision_time", to_utc(ev["dt"].to_numpy()))
    ev["available_at"] = ev["decision_time"]
    ev["flip_t"] = to_utc(ev["flip_t"].to_numpy())
    ev["signal_t"] = to_utc(ev["signal_t"].to_numpy())
    return ev.drop(columns="dt").sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"gb_rr_{TF}_{X_SIG}_{X_TGT}_{N_DISP}_{R_DISP}_{D_DISP}_sw22", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, ctrl_tod_tol_min=30)
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties",
              "ctrl_overlap", "avg_R", "win_rate"):
        print(k, res.get(k))
    op = {"rules": [
        "Flips/anchor as gb-retracement-entry: 15m, fractal 2/2, close beyond last confirmed unbroken swing against the previous break; anchor = strong extreme.",
        "After the flip, opposing extreme H extends with each closed 15m bar; signal = FIRST 15m close beyond the 0.41 retracement of anchor->H and beyond the lowest earlier wick (after the H bar) that pierced it; searched for 24h, abandoned if the anchor is closed through.",
        "Displacement: over the signal bar + 3 bars, window range / pre-4-bar range >= 1.5 and distance beyond the 0.41 / pre-range >= 0.65, and H not exceeded; otherwise the flip is not acted on.",
        "Decision to place: close of the 4th displacement bar. Limit at the 0.41 against the flip direction; fill = first M1 bar through it within 24h; decision = fill bar close.",
        "Stop = the opposing extreme H (stop_dist 0.41 x range); target = 0.7475 level (target_dist 0.3375 x range) -> 0.82R."],
        "params": {"tf": TF, "x_signal_entry": X_SIG, "x_target": X_TGT, "disp_N": N_DISP, "disp_r": R_DISP,
                   "disp_d": D_DISP, "signal_search": "24h", "expiry": "24h", "max_hold": MAX_HOLD,
                   "swing_left_right": SWING, "ctrl_tod_tol_min": 30}}
    ps = {"x_signal_entry": "corpus: gjoRPszj-Qk 'Wait for a body close beyond the 0.41' / 'Enter on the retracement back to the 0.41'",
          "x_target": "corpus: gjoRPszj-Qk targets '0.7475'",
          "disp_N": "threshold_fits: displacement magnitude N-window default N=4",
          "disp_r": "threshold_fits: displacement r=1.5 (win_range/pre_range)",
          "disp_d": "threshold_fits: displacement d=0.65 (dist/pre_range)",
          "stop": "corpus: gjoRPszj-Qk worked short 'maybe at this extreme' -> opposing extreme",
          "tf": "declared-before-run: 15m (listed LTF)",
          "swing_left_right": "declared-before-run: fractal 2/2",
          "signal_search": "declared-before-run: 24h after the flip",
          "expiry": "declared-before-run: 24h after placement",
          "max_hold": "declared-before-run: 24h",
          "ctrl_tod_tol_min": "declared-before-run: 30 (README trap 9)"}
    p = cl.write_result("gb-range-return-entry", None, res, operationalization=op, params_source=ps,
                        script=__file__, probe=probe,
                        notes="Tests the INTO-range leg only (the headline reading); the out-of-range 0.295->0.41 variant is not separately run.")
    print(p)
