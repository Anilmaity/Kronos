"""counter-trend-ote-scalp — trade_test on M1 (the finest data held; the concept's
15-second chart is not available, the model is stated as fractal).

Short case (longs mirrored by negating prices):
 1. an aggressive up-move stalls: a 1m 2/2 swing high H whose 30-bar leg range is
    >= 1.5x the range of the 30 bars before it; leg low L = the 30-bar low;
 2. an aggressive move down breaks structure: within 30 bars after H is confirmed, the
    first 1m close below the most recent swing low inside the leg (between L and H),
    with no new high above H first; it leaves a bearish FVG (formed after H, by the break);
 3. entry: return to the START of that gap (its near edge) within 30 bars after the break,
    before price has reached the target; decide at that M1 close, enter next M1 open;
 4. stop: the high just above the gap (max high of the gap's first two candles);
 5. target: the 0.62 retracement of the up-leg (H - 0.62*(H-L)); time exit 30 min.
Claim (+): beats a matched random entry. All parameters declared before the first run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, run_and_print  # noqa: E402

LEG_N = 30
AGG_R = 1.5
BREAK_WIN = 30
ENTRY_WIN = 30
OTE = 0.62
MAX_HOLD = "30min"


def _fractals(h, l):
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n >= 5:
        c = slice(2, n - 2)
        sh[c] = ((h[2:n - 2] > h[1:n - 3]) & (h[2:n - 2] > h[0:n - 4])
                 & (h[2:n - 2] >= h[3:n - 1]) & (h[2:n - 2] >= h[4:n]))
        sl[c] = ((l[2:n - 2] < l[1:n - 3]) & (l[2:n - 2] < l[0:n - 4])
                 & (l[2:n - 2] <= l[3:n - 1]) & (l[2:n - 2] <= l[4:n]))
    return sh, sl


def _shorts(h, l, c):
    """Short setups on (possibly negated) M1 arrays -> list of (e, stop, target)."""
    n = len(h)
    sh, sl = _fractals(h, l)
    hs = pd.Series(h)
    ls = pd.Series(l)
    rmax = hs.rolling(LEG_N).max().to_numpy()
    rmin = ls.rolling(LEG_N).min().to_numpy()
    leg_rng = rmax - rmin
    pre_rng = np.concatenate([np.full(LEG_N, np.nan), leg_rng[:-LEG_N]])
    cand = np.flatnonzero(sh & (leg_rng >= AGG_R * pre_rng) & (h >= rmax))
    slp = np.flatnonzero(sl)
    bear = np.zeros(n, bool)
    bear[2:] = h[2:] < l[:-2]
    out = []
    for p in cand:
        if p < 2 * LEG_N or p + 3 >= n:
            continue
        H = h[p]
        a = p - LEG_N + 1 + int(np.argmin(l[p - LEG_N + 1:p + 1]))
        L = l[a]
        # most recent swing low inside the leg (a <= s < p)
        k = np.searchsorted(slp, p, side="left") - 1
        if k < 0 or slp[k] < a:
            continue
        lvl = l[slp[k]]
        j0, j1 = p + 3, min(p + 3 + BREAK_WIN, n)
        brk = np.flatnonzero(c[j0:j1] < lvl)
        if len(brk) == 0:
            continue
        j = j0 + brk[0]
        if h[p + 1:j + 1].max() > H:
            continue
        fv = np.flatnonzero(bear[p + 2:j + 1])
        if len(fv) == 0:
            continue
        i = p + 2 + fv[-1]
        near = h[i]
        stop = max(h[i - 2], h[i - 1])
        tgt = H - OTE * (H - L)
        e0, e1 = j + 1, min(j + 1 + ENTRY_WIN, n)
        if e0 >= e1:
            continue
        seg_h, seg_l = h[e0:e1], l[e0:e1]
        up = np.flatnonzero(seg_h >= near)
        if len(up) == 0:
            continue
        e = e0 + up[0]
        if (l[e0:e + 1] <= tgt).any():         # target reached before the return: missed
            continue
        if not (tgt < c[e] < stop):
            continue
        out.append((e, stop, tgt))
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    h = m1["high"].to_numpy(float)
    l = m1["low"].to_numpy(float)
    c = m1["close"].to_numpy(float)
    t = cl.data.utc_ns(pd.DatetimeIndex(m1.index))
    frames = []
    for sgn, (hh, ll, cc) in ((-1, (h, l, c)), (1, (-l, -h, -c))):
        rows = _shorts(hh, ll, cc)
        if not rows:
            continue
        e = np.array([r[0] for r in rows])
        frames.append(pd.DataFrame({
            "decision_time": cl.data.from_ns(t[e] + np.timedelta64(60, "s")),
            "direction": sgn,
            "stop_px": -sgn * np.array([r[1] for r in rows]),
            "target_px": -sgn * np.array([r[2] for r in rows])}))
    if not frames:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction", "stop_px",
                                     "target_px"])
    ev = pd.concat(frames, ignore_index=True)
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"ctote_n{LEG_N}_r{AGG_R}_b{BREAK_WIN}_e{ENTRY_WIN}_o{OTE}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    run_and_print(res)
    op = {"rules": [
        "M1 bars stand in for the 15-second chart; swings = 2/2 fractals, used only after confirmation",
        "stall: swing high H that is the 30-bar high, with that 30-bar range >= 1.5x the previous 30-bar range; "
        "leg low L = the 30-bar low",
        "structure break: first M1 close below the most recent swing low between L and H, within 30 bars after "
        "H is confirmed, with no new high above H before it; bearish FVG formed after H by the break bar (the latest one)",
        "entry: first M1 bar trading up into the gap's near edge within 30 bars after the break, if the target was "
        "not reached first and the bar closes between target and stop; decide at its close, enter next M1 open",
        "stop = max high of the gap's first two candles; target = 0.62 retracement of the L->H leg; exit after 30min",
        "longs mirrored"],
        "params": {"tf": "1min", "leg_n": LEG_N, "agg_r": AGG_R, "break_win": BREAK_WIN,
                   "entry_win": ENTRY_WIN, "ote": OTE, "max_hold": MAX_HOLD}}
    src = {"tf": "declared-before-run: 15-second data does not exist in this project; M1 is the finest (fractal: true)",
           "leg_n": "declared-before-run: the stalled leg is measured over the last 30 minutes",
           "agg_r": "threshold_fits: displacement range ratio r=1.5 (aggressive = displacement)",
           "break_win": "declared-before-run: the counter move must break structure within 30 bars",
           "entry_win": "declared-before-run: the return to the gap must come within 30 bars",
           "ote": "corpus: ivirRu3fc4o 'the 0.62 is the level he uses to take profit'",
           "max_hold": "declared-before-run: a scalp that is 'wrong quickly' — 30 minutes"}
    notes = ("The concept is stated on the 15-second chart; tested on M1, the finest data held, under its "
             "fractal claim. Partials in the OTE region are not modelled (single exit at 0.62).")
    p = cl.write_result("counter-trend-ote-scalp", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print("wrote", p)
