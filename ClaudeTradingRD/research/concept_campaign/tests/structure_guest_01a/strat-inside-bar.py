"""strat-inside-bar (guest: Alex's Options, TheSTRAT) -> trade_test.

Declared before the first run:
  * Timeframe: daily (1D, 18:00 NY roll) - the lowest analysis timeframe in the concept's htf
    list ('inside day'); the break is resolved on M1 (the ltf execution).
  * inside_bar := high <= prev.high AND low >= prev.low (wicks; the concept's own formula).
  * "A break of the inside bar's high or low ends the consolidation and puts prior candles'
    extremes in play": on the NEXT daily bar, the first M1 that trades beyond one side of the
    inside bar (and not the other side in the same minute) triggers a trade in the break
    direction. Decide at that M1's close; harness enters the next M1 open.
  * Target: the mother (previous) candle's extreme on the break side (first prior extreme
    in play). Stop: the inside bar's opposite extreme. Rows whose target is not beyond the
    entry are dropped by the harness.
  * Hold: one trading day of M1 bars ("23h", hold_basis="bars"). claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "strat-inside-bar"
TF = "1D"
MAX_HOLD = "23h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 3:
        return pd.DataFrame(columns=COLS)
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    inside = (H <= ph) & (L >= pl)
    # for bar row r (the breakout bar), the inside bar is r-1 and the mother r-2
    ins_prev = np.r_[False, inside[:-1]]
    IH, IL = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    MH, ML = np.r_[np.nan, np.nan, H[:-2]], np.r_[np.nan, np.nan, L[:-2]]
    mt = m1.index
    pos = np.searchsorted(b.index.values, mt.values, side="right") - 1
    ok = (pos >= 0)
    posc = np.clip(pos, 0, None)
    act = ok & ins_prev[posc]
    if not act.any():
        return pd.DataFrame(columns=COLS)
    mh, ml = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    g = pd.Series(posc)
    cmax = pd.Series(mh).groupby(g).cummax().to_numpy()
    cmin = pd.Series(ml).groupby(g).cummin().to_numpy()
    up = act & (cmax > IH[posc])
    dn = act & (cmin < IL[posc])
    rows = []
    for r in np.unique(posc[act]):
        idx = np.flatnonzero((posc == r) & act)
        u = idx[up[idx]]
        d = idx[dn[idx]]
        fu = u[0] if len(u) else None
        fd = d[0] if len(d) else None
        if fu is None and fd is None:
            continue
        if fu is not None and fd is not None and fu == fd:
            continue                                   # both sides in one minute: ambiguous
        if fd is None or (fu is not None and fu < fd):
            rows.append((fu, 1, IL[r], MH[r]))
        else:
            rows.append((fd, -1, IH[r], ML[r]))
    if not rows:
        return pd.DataFrame(columns=COLS)
    ev = pd.DataFrame(rows, columns=["i", "direction", "stop_px", "target_px"])
    ev["decision_time"] = mt[ev["i"].to_numpy()] + pd.Timedelta("1min")
    ev["available_at"] = ev["decision_time"]
    return ev.sort_values("decision_time").reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame("strat_ib_1d", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis="bars")
    for k in ("n", "dropped", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "daily bars (18:00 NY roll); inside bar: high <= prev high and low >= prev low",
        "next day: first M1 trading beyond one side of the inside bar (not both in the same minute) -> trade the break",
        "target = mother candle's extreme on the break side; stop = inside bar's opposite extreme",
        "hold one trading day of M1 bars"],
        "params": {"tf": TF, "containment": "wicks", "target": "mother candle extreme", "stop": "inside bar far side",
                   "max_hold": MAX_HOLD, "hold_basis": "bars", "grid4h": "n/a (1D)"}}
    src = {"tf": "declared-before-run: lowest htf in the concept's list (1D, alias 'inside day')",
           "containment": "corpus: V8P6lNIisvc concept formula 'inside_bar := candle.high <= prev.high AND candle.low >= prev.low'",
           "target": "corpus: V8P6lNIisvc 'a break of the inside bar's extreme ... puts the preceding candles' extremes in play'",
           "stop": "declared-before-run: inside bar's opposite extreme (the consolidation's far side)",
           "max_hold": "declared-before-run: the breakout candle's trading day",
           "hold_basis": "declared-before-run: one trading day of bars across weekends",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe)
    print(p)
