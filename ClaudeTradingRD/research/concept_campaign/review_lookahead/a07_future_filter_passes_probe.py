"""Detector: long at the close of the FIRST 15m bar of each 4h (forex) bar when that 15m
bar closed up AND the enclosing 4h bar closes up (the 4h bar is still IN PROGRESS at the
decision). The agent stamps available_at = the 15m close (forgetting the 4h).
probe_lookahead only asks whether full-data events SURVIVE truncation; truncated at the
decision, the partial 4h bar == the 15m bar, so the future condition is trivially true
and every sampled event survives -> probe passes. The future acts as a FILTER, which a
survival-only probe cannot see."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

def detect(m1, dilute=True):
    b15 = cl.build_bars(m1, "15min"); b4 = cl.build_bars(m1, "4h", grid4h="forex")
    # map each 15m bar to its enclosing 4h bar (by start)
    pos = np.searchsorted(b4.index.asi8, b15.index.asi8, side="right") - 1
    ok = pos >= 0
    h4 = b4.iloc[np.clip(pos, 0, None)]
    first = ok & (h4.index.asi8 == b15.index.asi8)
    up15 = (b15.close > b15.open).to_numpy()
    up4 = (h4.close.to_numpy() > h4.open.to_numpy())
    atr = (b15.high - b15.low).rolling(20).mean().to_numpy()
    # dilute the leak so the sanity floor does not trip: keep all 15m-up events on
    # odd days, apply the in-progress-4h filter on even days
    even = (pd.DatetimeIndex(b15.index).day % 2 == 0)
    sel = first & up15 & np.isfinite(atr) & (up4 | ~even if dilute else up4)
    e = b15[sel]; ct = pd.DatetimeIndex(e.close_time)
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_dist": atr[sel] * 1.5, "rr": 1.0})

ev = detect(cl.load_m1())
probe = cl.probe_lookahead(detect, ev, n_sample=40, lookback="5D")
print("probe:", probe)
r = cl.trade_test(ev, max_hold="225min")
print({k: r[k] for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "sanity_flags")})
print("halves:", {k: round(r["halves"][k].get("diff"), 4) for k in ("H1", "H2")})
