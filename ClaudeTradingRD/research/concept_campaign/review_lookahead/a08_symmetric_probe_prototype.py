"""Prototype fix: compare the EVENT SET both ways. For random cut points T, every event
the detector emits on m1[T-lb, T) with decision_time in (T-recent, T] must also be in the
full-data book (same time/direction/price columns) and vice versa. Catches a02 and a07."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
sys.path.insert(0, ".")
import importlib.util
def load(name):
    spec = importlib.util.spec_from_file_location(name, f"{name}.py")
    src = open(f"{name}.py").read().split("\nev = detect")[0].split("\nm1 = cl.load_m1()")[0]
    ns = {}; exec(src, ns); return ns["detect"]

def sym_probe(detect, n_cut=40, lookback="5D", recent="1D", price_cols=("stop_px", "stop_dist", "rr"), seed=0):
    m1 = cl.load_m1(); full = detect(m1)
    full["decision_time"] = pd.DatetimeIndex(full.decision_time).tz_convert("UTC")
    rng = np.random.default_rng(seed)
    t = m1.index; lo_i = np.searchsorted(t, t[0] + pd.Timedelta("30D"))
    cuts = t[np.sort(rng.integers(lo_i, len(t), n_cut))]
    bad = 0
    for T in cuts:
        sl = m1.iloc[np.searchsorted(t, T - pd.Timedelta(lookback)):np.searchsorted(t, T)]
        got = detect(sl)
        gd = pd.DatetimeIndex(got.decision_time).tz_convert("UTC")
        w = (gd > T - pd.Timedelta(recent)) & (gd <= T)
        fw = (full.decision_time > T - pd.Timedelta(recent)) & (full.decision_time <= T)
        cols = ["decision_time", "direction"] + [c for c in price_cols if c in got.columns]
        def key(df):
            return sorted((str(r[0]),) + tuple(round(float(x), 6) for x in r[1:]) for r in df[cols].itertuples(index=False))
        a = key(got.loc[np.asarray(w)]); b = key(full.loc[np.asarray(fw)])
        if sorted(a) != sorted(b):
            bad += 1
    return bad, n_cut

for name in ("a02_future_stop_passes_probe", "a07_future_filter_passes_probe"):
    print(name, "cuts failing:", sym_probe(load(name)))
# honest control: 1h bar-close momentum, no lookahead
def honest(m1):
    b = cl.build_bars(m1, "1h"); a = (b.high - b.low).rolling(20).mean()
    s = (b.close > b.open) & a.notna(); e = b[s]; ct = pd.DatetimeIndex(e.close_time)
    return pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 1, "stop_dist": a[s].to_numpy(), "rr": 1.0})
print("honest detector cuts failing:", sym_probe(honest))
