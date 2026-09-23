"""stuck-orderflow (guests: Jokerszn, NickDoesFutures) -> two readings.

PD arrays (declared before the run): daily three-bar fair value gaps (18:00-NY days),
known at the third day's close, formed within the last 20 completed daily bars, and not
yet closed through (a bullish gap dies on a daily close below its low, a bearish gap on a
daily close above its high).
Stuck state at time t: price p sits between an active bullish daily FVG below (gap_low <= p)
and an active bearish daily FVG above (gap_high >= p), the bullish one lying under the
bearish one (bull.gap_high <= bear.gap_low).

Reading a (gate_test, claim '-'): the no-trade rule. Baseline book = the phase-3 rung-0
1h CISD (series_open, 2/2 swing, max_wait 3, stop protected swing, 2R, 10h hold). Gate
`stuck` = the stuck state at the decision (p = the confirming bar's close). claim '-' =
trades taken inside the stuck state do worse than trades outside it.

Reading b (trade_test, claim '+'): the resolution trigger. At a daily close, if the state
at the PREVIOUS daily close was stuck (p = that close) and this close is above the upper
(bearish) array's high -> long (breaker); below the lower (bullish) array's low -> short
(inversion). Entry next M1 open; stop at the far side of the resolved array (the array's
low for a long, its high for a short); 2R; max_hold 5 days (120h wall clock).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from concept_lab.examples import detect_cisd

LOOK = 20            # daily FVGs formed within the last 20 completed days
RR = 2.0
HOLD_A = "10h"
HOLD_B = "120h"


def daily_arrays(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] > 0]
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    n = len(d)
    bull = np.zeros(n, bool); bear = np.zeros(n, bool)
    glo = np.full(n, np.nan); ghi = np.full(n, np.nan)
    if n >= 3:
        bull[2:] = l[2:] > h[:-2]
        bear[2:] = h[2:] < l[:-2]
        glo[2:] = np.where(bull[2:], h[:-2], np.where(bear[2:], h[2:], np.nan))
        ghi[2:] = np.where(bull[2:], l[2:], np.where(bear[2:], l[:-2], np.nan))
    inv = np.full(n, n, np.int64)                 # first daily bar that closes through
    for j in np.flatnonzero(bull | bear):
        later = c[j + 1:]
        hit = np.flatnonzero(later < glo[j]) if bull[j] else np.flatnonzero(later > ghi[j])
        if len(hit):
            inv[j] = j + 1 + hit[0]
    ct = pd.DatetimeIndex(d["close_time"]).tz_convert("UTC")
    return d, ct, bull, bear, glo, ghi, inv, c


def stuck_at(L, p, bull, bear, glo, ghi, inv):
    """State using completed daily bars 0..L and price p. Returns (stuck, bull_j, bear_j)."""
    if L < 2 or not np.isfinite(p):
        return False, -1, -1
    js = np.arange(max(2, L - LOOK + 1), L + 1)
    act = inv[js] > L
    bj = js[act & bull[js] & (glo[js] <= p)]
    sj = js[act & bear[js] & (ghi[js] >= p)]
    if len(bj) == 0 or len(sj) == 0:
        return False, -1, -1
    # most recent qualifying pair with the bullish array below the bearish one
    for b_ in bj[::-1]:
        ok = sj[ghi[b_] <= glo[sj]]
        if len(ok):
            return True, int(b_), int(ok[-1])
    return False, -1, -1


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_cisd(m1, "1h")
    if ev.empty:
        return ev.assign(stuck=pd.Series(dtype=bool))
    d, ct, bull, bear, glo, ghi, inv, c = daily_arrays(m1)
    t = pd.DatetimeIndex(ev["decision_time"])
    L = np.searchsorted(ct.values, t.values, side="right") - 1
    mi = m1.index.values
    k = np.searchsorted(mi, t.values, side="left") - 1      # last M1 bar starting < t
    px = m1["close"].to_numpy()[np.clip(k, 0, None)]
    st = np.array([stuck_at(L[i], px[i], bull, bear, glo, ghi, inv)[0] for i in range(len(ev))])
    ev = ev.copy()
    ev["stuck"] = st.astype(bool)
    return ev.reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    d, ct, bull, bear, glo, ghi, inv, c = daily_arrays(m1)
    rows = []
    for L in range(3, len(d)):
        s, bj, sj = stuck_at(L - 1, c[L - 1], bull, bear, glo, ghi, inv)
        if not s:
            continue
        if c[L] > ghi[sj]:
            rows.append((ct[L], ct[L], 1, glo[sj], RR))
        elif c[L] < glo[bj]:
            rows.append((ct[L], ct[L], -1, ghi[bj], RR))
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


if __name__ == "__main__":
    reading = sys.argv[1] if len(sys.argv) > 1 else "a"
    params = {"pd_array": "daily 3-bar FVG, active = not closed through", "lookback_days": LOOK,
              "rr": RR}
    src = {"pd_array": "declared-before-run: 'two opposing daily PD arrays' (Jokerszn) / daily FVG pair (Nick); daily FVGs used",
           "lookback_days": "declared-before-run: arrays formed within the last 20 completed daily bars",
           "rr": "declared-before-run: no target stated; 2R"}
    if reading == "a":
        ev = cl.cache_frame(f"stuck_a_look{LOOK}", lambda: detect_a(cl.load_m1()))
        print(len(ev), ev.stuck.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="45D")
        print("probe", probe.get("passed"))
        res = cl.gate_test(ev, "stuck", mask_available_at="decision_time", max_hold=HOLD_A,
                           claim="-")
        op = {"rules": [
            "baseline: phase-3 rung-0 1h CISD (series_open, 2/2, max_wait 3, protected-swing stop, 2R, 10h)",
            "stuck = at decision, price between an active bullish daily FVG below and an active bearish daily FVG above",
            "active = formed within 20 completed days, no daily close through its far edge",
            "gate_test claim '-': stuck trades worse than the rest"],
            "params": dict(params, baseline="rung0 1h CISD", max_hold=HOLD_A)}
        src = dict(src, baseline="phase3: meta/conjunction_preregistration.md rung 0 (locked config)",
                   max_hold="phase3: 10 entry-TF bars (§1.13)")
    else:
        ev = cl.cache_frame(f"stuck_b_look{LOOK}", lambda: detect_b(cl.load_m1()))
        print(len(ev), ev.direction.value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="60D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=HOLD_B)
        op = {"rules": [
            "state at the previous daily close stuck between an active bullish (below) and bearish (above) daily FVG",
            "trigger: daily close above the bearish array's high -> long; below the bullish array's low -> short",
            "entry next M1 open; stop at the resolved array's far side; 2R; 120h hold"],
            "params": dict(params, max_hold=HOLD_B)}
        src = dict(src, max_hold="declared-before-run: 5 daily bars (120h wall clock)")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    p = cl.write_result("stuck-orderflow", reading, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("reading a: the no-trade state as a gate on the rung-0 book"
                               if reading == "a" else
                               "reading b: the close-through trigger (breaker / inversion) as a trade"))
    print(p)
