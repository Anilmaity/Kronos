"""draw-on-liquidity (TTrades own voice, contested) — batch liquidity_own_01a.

The later canon (FXJBFbZQbck, the_foundation_01): mark previous day high (PDH) and
previous day low (PDL); ask which is more likely to be reached; that is the draw and
the target. Measurable: "hit rate of the selected draw being reached before the
opposite candidate level". Operationalised as a trade_test at the 18:00 NY day open:
direction toward the nominated draw, target = the draw, stop = the opposite level
(so a win = the draw reached before the other side). The matched control (same
direction, same stop and target distances, same NY clock on another day +/-30d)
removes the geometry, so the differential measures the draw SELECTION.  claim '+'.

Two readings of "which is more likely", both in the concept's own rules:
  a  later canon: "If price is trending up, anticipate previous day high being taken;
     if trending down, previous day low" — trend = trend-by-previous-day-extremes:
     yesterday took the day-before's high and not its low -> up (mirror); else no draw.
  b  earlier canon behavioural read 2: "follow the displacement - the side price is
     displacing toward is generally the draw" — yesterday's close vs its open.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "draw-on-liquidity"
MIN_BARS = 600          # stub-session guard on the two days read
MAX_HOLD = "1376min"    # one full trading session of M1 bars (hold_basis='bars')


def detect(m1, reading):
    d = cl.build_bars(m1, "1D")
    O, H, L, C, N = (d[k].to_numpy() for k in ("open", "high", "low", "close", "n_m1"))
    ct = pd.DatetimeIndex(d["close_time"])
    rows = []
    for k in range(2, len(d) + 1):
        y, yy = k - 1, k - 2               # yesterday, the day before
        if N[y] < MIN_BARS or N[yy] < MIN_BARS:
            continue
        if reading == "a":
            up, dn = H[y] > H[yy], L[y] < L[yy]
            s = 1 if (up and not dn) else (-1 if (dn and not up) else 0)
        else:
            s = int(np.sign(C[y] - O[y]))
        if s == 0:
            continue
        t = ct[y]                          # 18:00 NY: yesterday closed, today opens
        rows.append((t, t, s, L[y] if s > 0 else H[y], H[y] if s > 0 else L[y]))
    return pd.DataFrame(rows, columns=["decision_time", "available_at", "direction",
                                       "stop_px", "target_px"])


def run(reading):
    fn = lambda m: detect(m, reading)
    ev = cl.cache_frame(f"{CID}_{reading}_min{MIN_BARS}", lambda: fn(cl.load_m1()))
    probe = cl.probe_lookahead(fn, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+", hold_basis="bars",
                        ctrl_tod_tol_min=30)
    sel = ("trend by previous-day extremes: yesterday's high > the day-before's high "
           "and yesterday's low >= its low -> long toward PDH (mirror); otherwise no draw"
           if reading == "a" else
           "follow the displacement: yesterday closed above its open -> long toward "
           "PDH; below -> short toward PDL; doji -> no draw")
    op = {"rules": [
        "decision at the 18:00 NY daily roll (yesterday's close_time); entry = first M1 "
        "open of the new trading day",
        "draw selection: " + sel,
        "target = the nominated previous-day extreme, stop = the opposite one "
        "(draw reached first = win); a gap beyond either level drops the day",
        "hold: one session (1376 M1 bars); days with < 600 M1 bars are not read"],
        "params": {"reading": reading, "min_bars": MIN_BARS, "max_hold": MAX_HOLD,
                   "hold_basis": "bars", "ctrl_tod_tol_min": 30,
                   "day_open_hour": 18}}
    src = {"reading": ("corpus: FXJBFbZQbck 'If price is trending up, anticipate previous "
                       "day high being taken' (the_foundation_01) + trend-by-previous-day-"
                       "extremes" if reading == "a" else
                       "corpus: education_ict_01 'follow the displacement - generally "
                       "right' (behavioural read 2)"),
           "min_bars": "declared-before-run: README trap 6 stub-session guard",
           "max_hold": "corpus: measurable 'hit rate of the nominated draw being reached "
                       "the same day' -> one session",
           "hold_basis": "declared-before-run: trading-time hold (README trap 7, weekend "
                         "entries)",
           "ctrl_tod_tol_min": "declared-before-run: every entry is at the 18:00 open; the "
                               "control must sit at the same NY clock (README trap 9)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    return res, op, src, probe


if __name__ == "__main__":
    import os, pickle
    for r in (sys.argv[1:] or ["a", "b"]):
        pk = os.path.join(cl.CACHE_DIR, f"liquidity_own_01a_{CID}_{r}_result.pkl")
        if os.path.exists(pk):
            res, op, src, probe = pickle.load(open(pk, "rb"))
        else:
            res, op, src, probe = run(r)
            pickle.dump((res, op, src, probe), open(pk, "wb"))
        print(f"== reading {r}")
        for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap",
                  "dropped"):
            if res.get(k) is not None:
                print(f"  {k:15s} {res[k]}")
        print("  wrote", cl.write_result(CID, r, res, operationalization=op,
                                         params_source=src, script=__file__, probe=probe))
