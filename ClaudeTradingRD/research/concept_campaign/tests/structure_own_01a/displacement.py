"""displacement (TTrades own voice + $niper, contested) -> two readings, both gates on one book.

The concept: a break of a short-term high/low only counts as a real structure break when it
DISPLACES. Component (a), the structural gate, is a CLOSE beyond the level (no knob;
threshold_fits §2(a), grade A) -- it defines the baseline book here. The contested part is
what makes a close 'displacement':
  reading a -- the comparative magnitude test (1oco9lesido 'if you just take these four
    candles when we broke this High'; 'in the same amount of time right we have a larger
    range'): threshold_fits §2(b) absolute form, N=4, window range / pre-break N-range >= 1.5
    AND distance beyond the level / pre-break N-range >= 0.65 (grade B).
  reading b -- the FVG requirement (PePk1V0Q4QQ 'for displacement to occur you want to see a
    fair value gap created'; FdRKBTz0Fps; UmLWRlXd_V8): a same-direction three-bar FVG inside
    the N=4 window.

Declared before the first run:
  * 15m bars (concept htf list; 15m is the entry TF of the phase-3 primary stack).
  * short-term highs/lows = fractal 2/2 swings, known at the close of the 2nd right bar.
  * break: the first 15m close above the most recent swing high known at the previous bar's
    close (mirrored for lows); one break per swing level.
  * window = the break bar and the next 3 bars (N=4); pre-window = the 4 bars before the break.
    Decide at the close of the window's last bar.
  * FVG 'inside the window': a same-direction FVG whose MIDDLE bar is in the window's first
    three bars (third bar within the window).
  * Trade: the break direction, entry next M1 open; stop = the window's extreme against the
    trade ('the displacement range'); target 2R; max hold 10 entry-TF bars (150 min).
  * Gates (claim '+', breaks WITH displacement beat breaks without):
      a: disp_mag;  b: has_fvg.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, show
from detectors.primitives import swing_points, fair_value_gaps

CID = "displacement"
TF = "15min"
N = 4
R_MIN, D_MIN = 1.5, 0.65
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "disp_mag", "has_fvg"]


def breaks(b: pd.DataFrame):
    """Yield (break_bar, direction, level) - first close beyond the latest known swing."""
    o = b[["open", "high", "low", "close"]]
    sw = swing_points(o, left=2, right=2)
    H, L, C = (o[c].to_numpy(float) for c in ("high", "low", "close"))
    n = len(b)
    sh_at = np.full(n, np.nan)
    sl_at = np.full(n, np.nan)
    for p in np.flatnonzero(sw["swing_high"].to_numpy()):
        if p + 2 < n:
            sh_at[p + 2] = H[p]
    for p in np.flatnonzero(sw["swing_low"].to_numpy()):
        if p + 2 < n:
            sl_at[p + 2] = L[p]
    out = []
    cur_h = cur_l = np.nan
    used_h = used_l = True
    for k in range(n):
        # levels known at the close of bar k-1 apply to bar k's close
        if k > 0:
            if np.isfinite(sh_at[k - 1]):
                cur_h, used_h = sh_at[k - 1], False
            if np.isfinite(sl_at[k - 1]):
                cur_l, used_l = sl_at[k - 1], False
        if not used_h and C[k] > cur_h:
            out.append((k, 1, cur_h))
            used_h = True
        if not used_l and C[k] < cur_l:
            out.append((k, -1, cur_l))
            used_l = True
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 20:
        return pd.DataFrame(columns=COLS)
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    fb, fs = f["bullish_fvg"].to_numpy(), f["bearish_fvg"].to_numpy()
    ct = pd.DatetimeIndex(b["close_time"])
    n = len(b)
    rows = []
    for k, sgn, lvl in breaks(b):
        e = k + N - 1
        if k - N < 0 or e >= n:
            continue
        wh, wl = H[k:e + 1].max(), L[k:e + 1].min()
        ph, pl = H[k - N:k].max(), L[k - N:k].min()
        pre = ph - pl
        if not pre > 0:
            continue
        win = wh - wl
        dist = (wh - lvl) if sgn > 0 else (lvl - wl)
        mag = (win / pre >= R_MIN) and (dist / pre >= D_MIN)
        third = slice(k + 1, e + 1)            # third bar in window => middle bar in k..e-1
        fvg = bool(fb[third].any()) if sgn > 0 else bool(fs[third].any())
        rows.append((e, sgn, wl if sgn > 0 else wh, mag, fvg))
    if not rows:
        return pd.DataFrame(columns=COLS)
    r = pd.DataFrame(rows, columns=["e", "direction", "stop_px", "disp_mag", "has_fvg"])
    r["decision_time"] = ct[r["e"].to_numpy()]
    r["available_at"] = r["decision_time"]
    r["rr"] = 2.0
    r = r.drop_duplicates(["decision_time", "direction"])
    r = r.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return r[COLS]


def main(readings):
    ev = cl.cache_frame(f"displacement_{TF}_N{N}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "mag", int(ev["disp_mag"].sum()), "fvg", int(ev["has_fvg"].sum()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    base = [f"{TF} bars; short-term highs/lows = 2/2 fractal swings known at the 2nd right bar's close",
            "break = first close beyond the most recent known swing high/low (structural displacement gate, one per level)",
            "window = break bar + 3 bars (N=4), pre-window = 4 bars before; decide at the window's last close",
            "trade the break direction; stop = window extreme against the trade; 2R; max hold 150 min"]
    params = {"tf": TF, "swing": "2/2", "N": N, "r_min": R_MIN, "d_min": D_MIN, "rr": 2.0,
              "max_hold": "150min", "stop": "window extreme", "grid4h": "n/a"}
    src = {"tf": "phase3: primary stack entry TF 15m; concept htf list includes 15m",
           "swing": "phase3: §1.8 swing 2/2 (short-term high)",
           "N": "threshold_fits: §2(b) N=4 (1oco9lesido 'these four candles')",
           "r_min": "threshold_fits: §2(b) r=1.5", "d_min": "threshold_fits: §2(b) d=0.65",
           "rr": "method_spec: §5.3 2R floor", "max_hold": "phase3: §1.13 10 entry-TF bars",
           "stop": "corpus: 1oco9lesido buy in the discount of the displacement range - its low is the invalidation",
           "grid4h": "declared-before-run: not used"}
    for r in readings:
        col = {"a": "disp_mag", "b": "has_fvg"}[r]
        res = cl.gate_test(ev, col, mask_available_at="decision_time", claim="+",
                           max_hold="150min")
        show(res)
        rule = {"a": f"gate a: window range/pre-range >= {R_MIN} AND distance beyond the level/pre-range >= {D_MIN}",
                "b": "gate b: a same-direction 3-bar FVG with its third bar inside the window"}[r]
        print(cl.write_result(CID, r, res, operationalization={"rules": base + [rule, "claim '+'"],
                                                              "params": dict(params, gate=col)},
                              params_source=dict(src, gate=("threshold_fits: §2(b) comparative magnitude test"
                                                            if r == "a" else
                                                            "corpus: PePk1V0Q4QQ 'for displacement to occur you want to see a fair value gap created'")),
                              script=__file__, probe=probe,
                              notes=f"Reading {r}: {col} gate on 15m closes beyond 2/2 swings."))


if __name__ == "__main__":
    main(sys.argv[1:] or ["a", "b"])
