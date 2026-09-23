"""Timing is honest (decide at 1h bar close) but the STOP price is derived from
the FUTURE (min low of the next 3 bars) on 25% of events. probe_lookahead's
defaults compare only decision_time+direction, so it passes; trade_test has no
availability stamp on price columns, so it accepts; the book comes back EDGE."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

def detect(m1):
    b = cl.build_bars(m1, "1h")
    rng_ = (b.high - b.low).rolling(20).mean()
    up = (b.close > b.open) & rng_.notna()
    honest = b.close - 1.0 * rng_                     # honest stop: 1 ATR-ish
    fut_low = b.low.shift(-1).rolling(1).min()        # next bar's low (FUTURE)
    fut_low = pd.concat([b.low.shift(-k) for k in (1, 2, 3)], axis=1).min(axis=1)
    h = (np.floor(pd.DatetimeIndex(b.index).asi8 / 3.6e12).astype(np.int64) % 4) == 0  # 25% of hours
    stop = np.where(h & fut_low.notna(), np.minimum(honest, fut_low - 0.05), honest)
    e = b[up]
    ct = pd.DatetimeIndex(e.close_time)
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1,
                         "stop_px": stop[up.to_numpy()], "rr": 1.0})

m1 = cl.load_m1()
ev = detect(m1)
ev = ev[np.isfinite(ev.stop_px)].reset_index(drop=True)
probe = cl.probe_lookahead(detect, ev, n_sample=20, lookback="5D")
print("probe (defaults):", probe)
r = cl.trade_test(ev, max_hold="3h")
print({k: r[k] for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict", "sanity_flags")})
print("halves:", {k: r["halves"][k].get("diff") for k in ("H1", "H2")})
try:
    cl.probe_lookahead(detect, ev, n_sample=20, lookback="5D", compare_cols=("stop_px",))
    print("probe with compare_cols=stop_px: passed")
except cl.LookaheadError as e:
    print("probe with compare_cols=stop_px RAISES:", str(e)[:160])
