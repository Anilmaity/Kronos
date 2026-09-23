"""Control check: an event stamped at the signal bar START (available_at also = start) is
accepted by trade_test (enters at the signal bar's own open) but probe_lookahead catches it."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
def detect(m1):
    b = cl.build_bars(m1, "1h"); a = (b.high - b.low).rolling(20).mean()
    s = ((b.close - b.open) > 0.3 * a) & a.notna(); e = b[s]; st = pd.DatetimeIndex(e.index)
    return pd.DataFrame({"decision_time": st, "available_at": st, "direction": 1,
                         "stop_dist": a[s].to_numpy() * 2, "rr": 1.0})
ev = detect(cl.load_m1())
r = cl.trade_test(ev, max_hold="1h")
print({k: r[k] for k in ("n", "avg_R", "win_rate", "diff", "verdict", "sanity_flags")})
try:
    cl.probe_lookahead(detect, ev, n_sample=20, lookback="5D"); print("probe passed (BAD)")
except cl.LookaheadError as e:
    print("probe raised (good):", str(e)[:110])
