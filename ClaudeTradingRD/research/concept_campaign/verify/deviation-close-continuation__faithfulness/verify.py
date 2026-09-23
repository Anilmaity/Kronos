"""Faithfulness/robustness check (scratch, no ledgered tests, no write_result)."""
import sys, importlib.util
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

SRC = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_guest_02a/deviation-close-continuation.py"
spec = importlib.util.spec_from_file_location("dcc", SRC); dcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dcc)

class CLProxy:
    def __init__(self, grid): self.grid = grid
    def __getattr__(self, k): return getattr(cl, k)
    def build_bars(self, m1, tf, **kw):
        if tf == "4h": kw.setdefault("grid4h", self.grid)
        return cl.build_bars(m1, tf, **kw)

m1 = cl.load_m1(); mkt = cl.get_market()
H = 240
BLOCKS = [("B1","2016-01-01","2018-08-22 11:01"),("B2","2018-08-22 11:01","2021-04-12 08:43"),
          ("B3","2021-04-12 08:43","2023-12-02 06:25"),("B4","2023-12-02 06:25","2027-01-01")]

def day_boot(x, days, n=2000, seed=1):
    df = pd.DataFrame({"x": x, "d": days}).groupby("d")["x"].agg(["sum","count"])
    s, c = df["sum"].to_numpy(), df["count"].to_numpy(); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), (n, len(s)))
    b = s[idx].sum(1) / c[idx].sum(1)
    return x.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)

def analyse(grid):
    dcc.cl = CLProxy(grid)
    ev = dcc.detect_a(m1)
    dcc.cl = cl
    t = pd.DatetimeIndex(ev["decision_time"]); d = ev["direction"].to_numpy()
    tgt = ev["target_px"].to_numpy(float)
    pos = np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1); px0 = mkt.o[pos]
    dist = tgt - px0
    def hits(times, lv, dirs_up):
        out = np.full(len(times), np.nan)
        for up in (True, False):
            m = dirs_up == up
            if m.any(): out[m] = cl.touch(times[m], lv[m], "above" if up else "below", horizon_bars=H)["hit"].to_numpy()
        return out
    obs = hits(t, tgt, d == 1)
    opp = hits(t, px0 - dist, d != 1)            # same distance, opposite side, same moments
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)
    nulls = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        o = np.full(len(t), np.nan)
        pk = mkt.o[np.minimum(mkt.pos_at_or_after(tk[ok]), len(mkt.o) - 1)]
        o[ok] = hits(tk[ok], pk + dist[ok], (d == 1)[ok])
        nulls.append(o)
    null = np.nanmean(np.vstack(nulls), 0)
    days = cl.trading_day(t) if hasattr(cl, "trading_day") else t.floor("D")
    days = np.asarray(pd.Index(days).astype(str))
    print(f"\n=== grid={grid} n={len(ev)} dir={pd.Series(d).value_counts().to_dict()}")
    print(" obs %.4f  null %.4f  opp %.4f  mean |dist|/px %.4f%%" % (obs.mean(), np.nanmean(null), opp.mean(), 100*np.mean(np.abs(dist)/px0)))
    for name, x in (("obs-null", obs - null), ("obs-opp (continuation vs symmetric)", obs - opp),
                    ("opp-null (volatility)", opp - null)):
        ok = ~np.isnan(x); m, lo, hi = day_boot(x[ok], days[ok]); print(f" {name:40s} {m:+.4f} [{lo:+.4f}, {hi:+.4f}]")
    for b, s, e in BLOCKS:
        m = (t >= pd.Timestamp(s, tz="UTC")) & (t < pd.Timestamp(e, tz="UTC"))
        print(f"  {b} n={m.sum():4d} obs-null {np.nanmean((obs-null)[m]):+.4f} obs-opp {np.mean((obs-opp)[m]):+.4f}")
    for y in range(2016, 2027):
        m = t.year == y
        if m.any(): print(f"  {y} n={m.sum():4d} obs-null {np.nanmean((obs-null)[m]):+.4f} obs-opp {np.mean((obs-opp)[m]):+.4f}")

for g in ("forex", "futures"):
    analyse(g)
