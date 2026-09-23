"""old-high-low-three-outcomes -> trade_test (the whole three-branch classification as one book).

Claim (ynFA6E3qHj0): at an old high/low price either (1) displaces out, retraces shallowly
and continues; (2) displaces out, is met with displacement back in and reverses; or (3) fails
to displace (closes back inside) and returns into the range. "the read is only valid on
closes". Each branch dictates a trade direction; claim '+': the branch-directed trades beat
a matched random entry.

Operationalisation (declared before the first run):
  * Old high/low = previous trading day's high/low (18:00 NY roll), read at the 15m bar's
    START. Execution candles: 15m (ltf list). First interaction per level per day only; the
    interacting bar must open back inside the level (price RETURNING to it).
  * Displacement = a candle CLOSE beyond the level (threshold_fits: structural gate, grade A).
  * Branch 3: first bar through the level closes back inside -> fade at its close; stop = that
    bar's extreme.
  * Branch 2: it closes beyond, and one of the next K=3 bars closes back inside -> fade at that
    close; stop = the extreme since the break.
  * Branch 1: it closes beyond and none of the next 3 bars closes back inside -> continue at
    the 3rd bar's close; stop = the retracement extreme of those 3 bars (skip if not beyond
    the entry).
  * 2R target; hold 150 min; decide at the deciding bar's close, enter next M1 open.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import show  # noqa: E402

CID = "old-high-low-three-outcomes"
TF = "15min"
K = 3
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "branch", "side"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < K + 3:
        return pd.DataFrame(columns=COLS)
    start = pd.DatetimeIndex(b.index)
    lv = cl.prior_hilo(start, "1D", m1=m1)
    PH, PL = lv["high"].to_numpy(float), lv["low"].to_numpy(float)
    td = cl.trading_day(start).asi8
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ctime = pd.DatetimeIndex(b["close_time"])
    n = len(b)
    out = []
    for side in (1, -1):                     # +1: old HIGH; -1: old LOW
        L = PH if side > 0 else PL
        beyond_w = (h > L) if side > 0 else (l < L)
        opened_in = (o <= L) if side > 0 else (o >= L)
        cand = np.flatnonzero(beyond_w & opened_in & np.isfinite(L))
        seen = set()
        for i in cand:
            if td[i] in seen:
                continue
            seen.add(td[i])
            lvl = L[i]
            closed_out = (c[i] > lvl) if side > 0 else (c[i] < lvl)
            if not closed_out:                                   # branch 3: fade
                out.append((i, -side, h[i] if side > 0 else l[i], 3, side))
                continue
            back = None
            for m in range(i + 1, min(i + K + 1, n)):
                if (c[m] < lvl) if side > 0 else (c[m] > lvl):
                    back = m
                    break
            if back is not None:                                 # branch 2: reverse
                stop = h[i:back + 1].max() if side > 0 else l[i:back + 1].min()
                out.append((back, -side, stop, 2, side))
            elif i + K < n:                                      # branch 1: continue
                m = i + K
                stop = l[i + 1:m + 1].min() if side > 0 else h[i + 1:m + 1].max()
                if (stop < c[m]) if side > 0 else (stop > c[m]):
                    out.append((m, side, stop, 1, side))
    if not out:
        return pd.DataFrame(columns=COLS)
    o_ = pd.DataFrame(out, columns=["i", "direction", "stop_px", "branch", "side"])
    dec = ctime[o_["i"].to_numpy()]
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o_["direction"].astype(int).to_numpy(),
                       "stop_px": o_["stop_px"].to_numpy(float), "rr": RR,
                       "branch": o_["branch"].astype(int).to_numpy(),
                       "side": o_["side"].astype(int).to_numpy()})
    return ev.sort_values(["decision_time", "side"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_K{K}_pdhl", lambda: detect(cl.load_m1()))
    print(len(ev), ev["branch"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD, keep_trades=True)
    show(res)
    tr = res.get("_trades")
    if tr is not None:
        try:
            print(tr.assign(branch=ev["branch"].to_numpy()).groupby("branch")["R"].mean())
        except Exception as e:  # diagnostics only
            print("branch split unavailable:", e, list(tr.columns)[:12])
    op = {"rules": [
        "old high/low = previous trading day's high/low (18:00 NY roll), read at the 15m bar "
        "start; first interaction per level per day, the bar must open back inside",
        "displacement = a 15m close beyond the level",
        "branch 3 (no close beyond) -> fade at that close, stop = the bar's extreme",
        "branch 2 (close beyond, then a close back inside within 3 bars) -> fade at that "
        "close, stop = extreme since the break",
        "branch 1 (close beyond, no close back inside for 3 bars) -> continue at the 3rd "
        "bar's close, stop = the retracement extreme of those bars",
        "2R, hold 150 min, next M1 open"],
        "params": {"tf": TF, "k_bars": K, "level": "PDH/PDL", "rr": RR, "max_hold": MAX_HOLD,
                   "displacement": "close beyond"}}
    src = {"tf": "declared-before-run: 15m from the concept's ltf list (15m/5m/1m) under 1D "
                 "levels (htf 1D/4H)",
           "k_bars": "declared-before-run: 'how many candles may pass before displacement "
                     "back in no longer counts is not stated'; 3 bars",
           "level": "declared-before-run: old high/low = previous day high/low (the "
                    "method's marked daily levels, method_spec 2.4)",
           "rr": "phase3: 2R primary target ('opposite side of the range' is a narrative "
                 "target)",
           "max_hold": "phase3: 10 entry-TF bars",
           "displacement": "threshold_fits: displacement = aggressive = a candle closes "
                           "beyond the reference level (grade A, no knob)"}
    notes = ("One book of every branch-directed trade. Branch 3's 'return to premium/discount "
             "before trusting' refinement is not applied. Branch counts: "
             + str(ev["branch"].value_counts().to_dict()))
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe, notes=notes))
