"""Audit step 1b: independent check of the 'no entry edge / the win rate is geometry' claims, from deals_raw.json + S5 only.
Run: ../../.venv/bin/python 04_entries_check.py -> out/04_entries_check.txt
"""
import json, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
_L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); _L.append(s)
BID_B, ASK_B = -0.053, 0.063                                  # measured in 01_headline.py (medians, manual market deals)
s5 = pd.read_parquet(f"{ROOT}/xau_s5_2026-11-03_now_ba.parquet")
st = s5.time.values.astype("datetime64[ns]").astype("int64")
B = {k: s5["bid_" + k].to_numpy() + BID_B for k in ("high", "low", "close")}
A = {k: s5["ask_" + k].to_numpy() + ASK_B for k in ("high", "low", "close")}
S = 10**9
raw = sorted(json.load(open(f"{ROOT}/deals_raw.json"))["deals"], key=lambda x: (x["time"], int(x["id"])))
ins = [(pd.Timestamp(x["time"]).value, 1 if x["type"] == "DEAL_TYPE_BUY" else -1, x["price"]) for x in raw if x.get("entryType") == "DEAL_ENTRY_IN"]
dec = [d for j, d in enumerate(ins) if not (j and d[1] == ins[j - 1][1] and d[0] - ins[j - 1][0] <= 30 * S)]
P(f"decisions (first click; same-side taps <= 30 s merged): {len(dec)} | BUY {sum(d[1]>0 for d in dec)} SELL {sum(d[1]<0 for d in dec)}")
idx = lambda ts: int(np.searchsorted(st, ts, "right") - 1)

def fwd(ts, side, px, mins):
    j = idx(ts + mins * 60 * S); q = B["close"][j] if side > 0 else A["close"][j]
    return side * (q - px)
def touch(ts, side, px, tp, sl, cap_h):
    """first touch on exit-side quotes from the bar AFTER the entry bar; tie -> stop. 1 win, 0 loss, nan none."""
    i0 = idx(ts) + 1; i1 = idx(ts + cap_h * 3600 * S) + 1
    if side > 0: hit_s, hit_t = B["low"][i0:i1] <= px - sl, B["high"][i0:i1] >= px + tp
    else:        hit_s, hit_t = A["high"][i0:i1] >= px + sl, A["low"][i0:i1] <= px - tp
    a = hit_s.argmax() if hit_s.any() else 10**9; b = hit_t.argmax() if hit_t.any() else 10**9
    return np.nan if a == b == 10**9 else float(b < a)
def entry_px(ts, side):                                      # what a market order pays at that instant
    j = idx(ts); return A["close"][j] if side > 0 else B["close"][j]

rng = np.random.default_rng(11); K = 100
lo, hi = st[0] + 3600 * S, st[-1] - 60 * S                 # windows near the data end are truncated for real and control alike
ctrl = []                                                    # K control sets, one shifted instant per decision
for _ in range(K):
    row = []
    for ts, side, _px in dec:
        while True:
            c = ts + int(rng.choice([-1, 1]) * rng.uniform(10, 120) * 60 * S)
            j = idx(c)
            if lo < c < hi and c - st[j] < 5 * S: break      # inside an existing S5 bar (market open)
        row.append((c, side, entry_px(c, side)))
    ctrl.append(row)

def line(name, f):
    real = np.array([f(*d) for d in dec]); cm = np.array([np.nanmean([f(*d) for d in row]) for row in ctrl])
    n = int(np.isfinite(real).sum()); m = np.nanmean(real); se = np.nanstd(real, ddof=1) / np.sqrt(n)
    P(f"  {name:34s} real {m:+.3f} (n={n}, s.e. {se:.3f}) | control mean {cm.mean():+.3f} [p5 {np.percentile(cm,5):+.3f}, p95 {np.percentile(cm,95):+.3f}] | real at control percentile {100*(cm < m).mean():.0f}")

P("\n== signed forward return net of the spread paid, points (control: same side, entry shifted +-10..120 min, 100 sets) ==")
for m in (1, 5, 30, 60, 240): line(f"{m} min", lambda ts, sd, px, m=m: fwd(ts, sd, px, m))
P("\n== first-touch win rate (share; tie = stop) ==")
line("+-5 pts, 4 h cap", lambda ts, sd, px: touch(ts, sd, px, 5, 5, 4))
line("+-10 pts, 4 h cap", lambda ts, sd, px: touch(ts, sd, px, 10, 10, 4))
line("TP 5 / SL 28 (his shape), 12 h cap", lambda ts, sd, px: touch(ts, sd, px, 5, 28, 12))
P("  random-walk expectation for TP 5 / SL 28 with a 0.6 spread: (28-0.6)/(33) = 83.0%")

P("\n== withdrawals: was the account flat when he swept? ==")
pos = pd.read_csv(f"{HERE}/out/positions_from_deals.csv", parse_dates=["t_in", "t_out"])
for x in raw:
    c = x.get("comment") or ""
    if x["type"] == "DEAL_TYPE_BALANCE" and c.startswith("CW-") and "ERR" not in c:
        ts = pd.Timestamp(x["time"]); o = pos[(pos.t_in <= ts) & (pos.t_out > ts)]
        P(f"  {x['time']} withdraw {x['profit']:8.2f} | open positions {len(o)} lots {o.vol.sum():.2f}")
open(f"{HERE}/out/04_entries_check.txt", "w").write("\n".join(_L) + "\n")
