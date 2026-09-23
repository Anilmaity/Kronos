"""Independent verification of cheat-code-entry EDGE (implementation / look-ahead lens).
Scratch only: never calls write_result."""
import sys, importlib.util, json, time
import numpy as np, pandas as pd
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl

ORIG = '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/cheat-code-entry.py'
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
spec = importlib.util.spec_from_file_location("cce", ORIG); cce = importlib.util.module_from_spec(spec); spec.loader.exec_module(cce)

m1 = cl.load_m1()
NB = int(sys.argv[1]) if len(sys.argv) > 1 else 500

# ---------- independent 15m bars (plain pandas, no harness builder) ----------
def my_bars(m1):
    idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    df = m1[["open","high","low","close"]].copy(); df.index = idx
    df["_last"] = idx
    g = df.resample("15min", label="left", closed="left")
    b = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "last": g["_last"].max()}).dropna()
    b["close_time"] = b["last"] + pd.Timedelta(minutes=1)   # close of last M1 inside
    return b

# ---------- independent trend: my own swings + displacement grading ----------
def my_trend(b, N=4, R=1.5, D=0.65, life=24):
    h, l, c = (b[k].to_numpy(float) for k in ("high","low","close"))
    n = len(b)
    # 2/2 fractal: strict greater than 2 each side
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for p in range(2, n-2):
        if h[p] > max(h[p-2], h[p-1], h[p+1], h[p+2]): sh[p] = True
        if l[p] < min(l[p-2], l[p-1], l[p+1], l[p+2]): sl[p] = True
    fires = []   # (fire_pos, dir, origin)
    cur_h = cur_l = None
    for i in range(n):
        p = i - 3                                   # confirmed at close of p+2 <= i-1
        if p >= 0:
            if sh[p]: cur_h = p
            if sl[p]: cur_l = p
        if cur_h is not None and c[i] > h[cur_h]:
            p0 = cur_h; lvl = h[p0]; cur_h = None
            if i >= N and i+N-1 < n:
                pre = h[i-N:i].max() - l[i-N:i].min()
                wh = h[i:i+N].max(); wl = l[i:i+N].min()
                if pre > 0 and (wh-wl)/pre >= R and (wh-lvl)/pre >= D:
                    fires.append((i+N-1, 1, l[p0:i+1].min()))
        if cur_l is not None and c[i] < l[cur_l]:
            p0 = cur_l; lvl = l[p0]; cur_l = None
            if i >= N and i+N-1 < n:
                pre = h[i-N:i].max() - l[i-N:i].min()
                wh = h[i:i+N].max(); wl = l[i:i+N].min()
                if pre > 0 and (wh-wl)/pre >= R and (lvl-wl)/pre >= D:
                    fires.append((i+N-1, -1, h[p0:i+1].max()))
    fires.sort(key=lambda x: x[0])
    tdir = np.zeros(n, int); k = 0; cur = None
    for j in range(n):
        while k < len(fires) and fires[k][0] < j:
            cur = list(fires[k]) + [False]; k += 1
        if cur is None or cur[3]: continue
        f, d, s = cur[:3]
        if j - f > life or (d == 1 and c[j] < s) or (d == -1 and c[j] > s):
            cur[3] = True; continue
        tdir[j] = d
    return tdir

def mk(b, sel, d, stop):
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[sel]).tz_convert("UTC") if pd.DatetimeIndex(b["close_time"]).tz is not None else pd.DatetimeIndex(b["close_time"].to_numpy()[sel]).tz_localize("UTC")
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d[sel].astype(int),
                       "stop_px": stop[sel], "rr": 2.0})
    ev = ev.sort_values(["decision_time","direction"]).drop_duplicates(["decision_time","direction"]).reset_index(drop=True)
    return ev

def run(name, ev, **kw):
    t0 = time.time()
    r = cl.trade_test(ev, max_hold="150min", n_boot=NB, keep_trades=True, **kw)
    tr = r["_trades"]
    out = {k: r.get(k) for k in ("n","avg_R","win_rate","diff","ci_lo","ci_hi","verdict")}
    out["H1"] = r["halves"]["H1"]["diff"]; out["H2"] = r["halves"]["H2"]["diff"]
    out["ties"] = {k: r["ties"].get(k) for k in ("real_ambiguous","control_ambiguous")}
    d5 = (tr["net_R_5050"] - tr["ctrl_mean_R_5050"]).mean(); out["diff_5050"] = float(d5)
    # stop-size quintiles by stop/ATR
    print(f"== {name}  ({time.time()-t0:.0f}s)", json.dumps(out, default=float))
    return r, tr

res = {}
# 1) re-run original
ev0 = cce.detect(m1)
print("orig events", len(ev0), "fp", cl.frame_fingerprint(ev0))
res["orig"] = run("ORIGINAL", ev0)

# 2) independent implementation
b = my_bars(m1)
o, h, l, c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
tdir = my_trend(b)
col = np.sign(c - o).astype(int)
opp = (tdir != 0) & (col == -tdir)
evm = mk(b, opp, tdir, np.where(tdir == -1, h, l))
print("mine events", len(evm), "trend-alive share", (tdir != 0).mean())
res["mine"] = run("MINE (independent)", evm)

# 3) geometry nulls
fade = col != 0
dfade = -col
stop_fade = np.where(dfade == -1, h, l)
res["fade_all"] = run("NULL fade-every-15m-candle (no trend)", mk(b, fade, dfade, stop_fade))
res["fade_notrend"] = run("NULL fade candle when NO trend alive", mk(b, fade & (tdir == 0), dfade, stop_fade))
res["fade_countertrend"] = run("NULL fade WITH-trend candle (trade against trend)", mk(b, fade & (tdir != 0) & (col == tdir), dfade, stop_fade))
rng = np.random.default_rng(7)
rd = rng.choice([-1, 1], len(b))
res["rand_on_opp"] = run("NULL random dir on concept candles, stop at matching extreme", mk(b, opp, rd, np.where(rd == -1, h, l)))
