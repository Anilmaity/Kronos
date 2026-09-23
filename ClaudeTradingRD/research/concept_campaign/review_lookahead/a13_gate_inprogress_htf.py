"""gate_test: gate = 'the enclosing forex-4h bar closes up', evaluated at the close of the
first 15m bar of that 4h bar (4h still IN PROGRESS). mask_available_at = decision_time
(what an agent writes for a 'clock-like' condition). Accepted; comes back EDGE.
The README documents no behavioural probe for masks; probe_lookahead only catches it if the
agent thinks to put the mask in key_cols."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
def detect(m1):
    b15 = cl.build_bars(m1, "15min"); b4 = cl.build_bars(m1, "4h")
    pos = np.searchsorted(b4.index.asi8, b15.index.asi8, side="right") - 1
    h4 = b4.iloc[np.clip(pos, 0, None)]
    first = (pos >= 0) & (h4.index.asi8 == b15.index.asi8)
    atr = (b15.high - b15.low).rolling(20).mean().to_numpy()
    sel = first & np.isfinite(atr)
    up4 = h4.close.to_numpy() > h4.open.to_numpy()
    di = pd.DatetimeIndex(b15.index)
    leak = (di.dayofyear % 6 == 0)                      # leak on ~1/6 of days only
    coin = ((di.dayofyear * 7 + di.hour) % 2 == 0)      # innocuous clock-hash elsewhere
    g = np.where(leak, up4, coin)
    e = b15[sel]; ct = pd.DatetimeIndex(e.close_time)
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_dist": atr[sel] * 1.5, "rr": 1.0,
                         "gate": g[sel]})
ev = detect(cl.load_m1())
r = cl.gate_test(ev.drop(columns="gate"), ev["gate"].to_numpy(), mask_available_at=ev["decision_time"], max_hold="225min")
print({k: r[k] for k in ("n", "n_complement", "gate_firing_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "sanity_flags")})
print("probe default:", cl.probe_lookahead(detect, ev, n_sample=20, lookback="5D")["passed"])
try:
    cl.probe_lookahead(detect, ev, n_sample=20, lookback="5D", key_cols=("direction", "gate")); print("probe key_cols=gate passed")
except cl.LookaheadError as e:
    print("probe with key_cols=gate raises:", str(e)[:90])
