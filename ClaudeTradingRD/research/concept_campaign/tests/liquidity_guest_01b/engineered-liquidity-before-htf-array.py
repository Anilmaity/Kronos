"""engineered-liquidity-before-htf-array (guest: Finessee_Fx) -> gate_test.

Claim: before price reaches a marked HTF array it stops shy, consolidates sideways
and engineers liquidity, then spikes into the level and reverses; that spike is
the tradeable event, and a straight run into the array is the less desirable
case. Tested as a gate on a book of first-tag reactions at daily arrays:

  array: a daily FVG (18:00 NY roll), known at its third bar's close, remembered
    for 20 sessions, untagged so far.
  baseline trade (execution block: bias = the array's direction, entry only after
    the tag, stop beyond the array): at the close of the FIRST 4H bar (forex grid)
    that trades into it - bearish FVG above: high >= gap bottom; bullish mirrored -
    and does not close beyond its far edge, trade the array's direction; stop =
    beyond the far edge (max of gap top and the tag bar's high for a short);
    target 2R; hold 10 4H bars of trading time.
  gate consolidated_shy: the 6 4H bars before the tag bar (one trading day), all
    after the array became known, (i) came within 0.5 x ATR14(D1) of the array
    without touching it, and (ii) spanned a range <= 1.0 x ATR14(D1) (sideways).
    Complement = the straight run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

MEM = 20
K = 6
SHY_ATR = 0.5
RANGE_ATR = 1.0
MIN_M1 = 600


def detect(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= MIN_M1]
    dh, dl, dc = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    dct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    pc = np.r_[np.nan, dc[:-1]]
    tr = np.maximum(dh - dl, np.maximum(np.abs(dh - pc), np.abs(dl - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    fvgs = []   # (known_at_ns, lo, hi, side, day_index)
    for i in range(2, len(d)):
        if dl[i] > dh[i - 2]:
            fvgs.append((dct[i], dh[i - 2], dl[i], 1, i))
        if dh[i] < dl[i - 2]:
            fvgs.append((dct[i], dh[i], dl[i - 2], -1, i))
    f4 = cl.build_bars(m1, "4h", grid4h="forex")
    h, l, c = f4["high"].to_numpy(), f4["low"].to_numpy(), f4["close"].to_numpy()
    st = pd.DatetimeIndex(f4.index).as_unit("ns").asi8
    ct = pd.DatetimeIndex(f4["close_time"]).as_unit("ns").asi8
    rows = []
    for (known, lo, hi, side, di) in fvgs:
        # sessions memory: array expires after MEM further daily closes
        exp = dct[di + MEM] if di + MEM < len(dct) else np.iinfo(np.int64).max
        a = np.searchsorted(st, known, side="left")          # 4H bars starting after array known
        b = np.searchsorted(st, exp, side="left")
        if a >= b:
            continue
        if side == -1:
            touch = np.flatnonzero(h[a:b] >= lo)
        else:
            touch = np.flatnonzero(l[a:b] <= hi)
        if len(touch) == 0:
            continue
        t = a + touch[0]
        if side == -1 and c[t] >= hi:
            continue
        if side == 1 and c[t] <= lo:
            continue
        # ATR known before the tag bar started
        k = np.searchsorted(dct, st[t], side="right") - 1
        if k < 0 or np.isnan(atr[k]):
            continue
        A = atr[k]
        if t - K >= a:
            w0, w1 = t - K, t
            wh, wl = h[w0:w1].max(), l[w0:w1].min()
            shy = (lo - wh) <= SHY_ATR * A if side == -1 else (wl - hi) <= SHY_ATR * A
            gate = bool(shy and (wh - wl) <= RANGE_ATR * A)
        else:
            gate = False
        if side == -1:
            stop = max(hi, h[t]); dirn = -1
        else:
            stop = min(lo, l[t]); dirn = 1
        rows.append((ct[t], dirn, stop, gate))
    out = pd.DataFrame(rows, columns=["dt", "direction", "stop_px", "consolidated_shy"])
    out["decision_time"] = pd.to_datetime(out["dt"], utc=True)
    out["available_at"] = out["decision_time"]
    out["rr"] = 2.0
    out = out.sort_values("decision_time", kind="stable").reset_index(drop=True)
    return out[["decision_time", "available_at", "direction", "stop_px", "rr", "consolidated_shy"]]


if __name__ == "__main__":
    ev = cl.cache_frame(f"engineered_liq_d1fvg_4h_k{K}_s{SHY_ATR}_r{RANGE_ATR}_m{MEM}", lambda: detect(cl.load_m1()))
    print("events", len(ev), "gate rate", ev["consolidated_shy"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "consolidated_shy", mask_available_at="decision_time", max_hold="40h",
                       hold_basis="bars", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", k, res.get(k))
    op = {"rules": ["array = daily FVG (18:00 NY roll), known at third bar's close, remembered 20 sessions, first tag only",
                    "trade at close of the first 4H (forex grid) bar trading into it that does not close beyond the far edge; direction = array's (short at bearish FVG above, long at bullish below)",
                    "stop beyond the far edge (and beyond the tag bar's extreme); 2R; hold 40h of trading time (10 4H bars)",
                    "gate: the 6 4H bars before the tag (all after the array was known) came within 0.5 ATR14(D1) of it without touching and spanned <= 1.0 ATR14(D1)"],
          "params": {"array": "1D FVG", "entry_tf": "4h", "grid4h": "forex", "day_open_hour": 18,
                     "memory_sessions": MEM, "consol_bars_4h": K, "shy_atr": SHY_ATR, "range_atr": RANGE_ATR,
                     "atr_len_d1": 14, "rr": 2.0, "max_hold": "40h", "hold_basis": "bars",
                     "min_session_m1": MIN_M1}}
    src = {"array": "corpus: eK_6wgNpNh0 arrays are order block / breaker / imbalance; the FVG (imbalance) is the mechanically defined one",
           "entry_tf": "corpus: yaml timeframes htf 1M/1W/1D, ltf 4H/1H - daily array, 4H approach",
           "grid4h": "session_window_fit: forex grid for gold (weak; knob recorded)",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
           "memory_sessions": "declared-before-run: 20 sessions (~1 month; his example consolidation lasted a month)",
           "consol_bars_4h": "declared-before-run: one trading day of 4H bars as the consolidation window",
           "shy_atr": "declared-before-run: 'stop shy' has no distance in the corpus; 0.5 daily ATR",
           "range_atr": "declared-before-run: 'sideways' = the day's 4H range <= one daily ATR",
           "atr_len_d1": "declared-before-run: standard 14",
           "rr": "phase3: locked 2R target (the 'opposing array' target is not mechanised)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "hold_basis": "declared-before-run: 4H holds span weekends/halts (README trap 7)",
           "min_session_m1": "declared-before-run: skip stub sessions (README trap 6)"}
    p = cl.write_result("engineered-liquidity-before-htf-array", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="The 9-in-10 frequency is not tested directly (no null for it); the gate tests the trading claim that the post-consolidation spike beats a straight run.")
    print(p)
