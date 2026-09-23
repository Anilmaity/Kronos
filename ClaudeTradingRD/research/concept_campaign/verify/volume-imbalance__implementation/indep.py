"""Independent re-implementation of volume-imbalance from the concept YAML (no _common helpers)."""
import os, sys, json
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl, pandas as pd, numpy as np

m1 = cl.load_m1()
idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
m1 = m1.set_axis(idx)
# 15m bars, own resample, label=left, drop empty buckets
g = m1.resample("15min", label="left", closed="left")
b = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                  "close": g["close"].last(), "n": g["open"].count()})
b = b[b.n > 0].copy()
b["ct"] = b.index + pd.Timedelta("15min")
pc = b.close.shift(1)
tr = pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)
b["atr"] = tr.rolling(20, min_periods=20).mean()
WILDER = len(sys.argv) > 1 and sys.argv[1] == "wilder"
if WILDER:
    b["atr"] = tr.ewm(alpha=1/20, adjust=False, min_periods=20).mean()

prev = b.shift(1)
gap = b.open - prev.close
overlap = (b.low <= prev.high) & (b.high >= prev.low)
zlo = np.minimum(b.open, prev.close); zhi = np.maximum(b.open, prev.close)
d = np.where(b.close > zhi, 1, np.where(b.close < zlo, -1, 0))
sel = overlap & (gap.abs() >= 0.10 * b.atr) & (d != 0) & b.atr.notna()
print("VI candidates", int(sel.sum()), "of", len(b))

t = m1.index.asi8; lo = m1.low.to_numpy(); hi = m1.high.to_numpy()
cts = b.ct.to_numpy().astype("datetime64[ns]").astype(np.int64)
pos = np.flatnonzero(sel.to_numpy())
rows = []
for j in pos:
    dd = d[j]; a = b.atr.iat[j]; zl = zlo.iat[j]; zh = zhi.iat[j]
    start = cts[j]; end = cts[j + 16] if j + 16 < len(b) else t[-1] + 60_000_000_000
    i0 = np.searchsorted(t, start, "left"); i1 = np.searchsorted(t, end, "left")
    if dd > 0:
        hit = np.flatnonzero(lo[i0:i1] <= zh); stop = zl - 0.25 * a
    else:
        hit = np.flatnonzero(hi[i0:i1] >= zl); stop = zh + 0.25 * a
    if not len(hit): continue
    q = i0 + hit[0]
    if (dd > 0 and lo[q] <= stop) or (dd < 0 and hi[q] >= stop): continue
    rows.append((t[q] + 60_000_000_000, dd, stop))
ev = pd.DataFrame(rows, columns=["dt", "direction", "stop_px"])
ev["decision_time"] = pd.to_datetime(ev.dt, utc=True); ev["available_at"] = ev.decision_time
ev["rr"] = 2.0
ev = ev.drop_duplicates(["decision_time", "direction"]).sort_values("decision_time").reset_index(drop=True)
ev = ev[["decision_time", "available_at", "direction", "stop_px", "rr"]]
print("events", len(ev)); print(ev.decision_time.dt.year.value_counts().sort_index().to_dict())
ev.to_pickle("ev_indep%s.pkl" % ("_wilder" if WILDER else ""))
res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
out = {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "mde", "ties", "ctrl_overlap", "exposure_bars")}
out["H1"] = res["halves"]["H1"]["diff"]; out["H2"] = res["halves"]["H2"]; out["blocks"] = {k: (v["n"], v["diff"], v["ci_lo"], v["ci_hi"]) for k, v in res["blocks"].items()}
print(json.dumps(out, default=str, indent=1))
res["_trades"].to_pickle("trades_indep%s.pkl" % ("_wilder" if WILDER else ""))
