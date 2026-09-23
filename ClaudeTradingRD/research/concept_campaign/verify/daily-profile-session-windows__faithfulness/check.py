"""Faithfulness/robustness probe of the daily-profile-session-windows EDGE (no harness writes).
Recomputes from raw M1, decomposes by window, re-anchors, drops reopen minutes, calendar blocks."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

m1 = cl.load_m1(); idx = m1.index
mod = np.asarray(cl.ny_minute_of_day(idx))
rng0 = np.random.default_rng(12345)

def hm(s): h, m = s.split(":"); return int(h)*60+int(m)

def build(anchor_hour, drop_after_open=0):
    td = cl.trading_day(idx, anchor_hour) if anchor_hour == 18 else None
    if anchor_hour != 18:
        ny = idx.tz_convert("America/New_York")
        td = pd.DatetimeIndex((ny - pd.Timedelta(hours=anchor_hour)).date)
    roll = anchor_hour*60
    msr = (mod - roll) % 1440
    df = pd.DataFrame({"td": np.asarray(td), "hi": m1.high.to_numpy(), "lo": m1.low.to_numpy(), "msr": msr, "t": idx})
    if drop_after_open:
        # minutes since previous bar gap > 30 min -> mark first N minutes after a halt
        t = idx.view("int64")//60_000_000_000
        gap = np.r_[10**9, np.diff(t)] > 30
        last_open = pd.Series(np.where(gap, t, np.nan)).ffill().to_numpy()
        df = df[(t - last_open) >= drop_after_open]
    g = df.groupby("td", sort=True)
    n = g.size(); keep = n[n >= 600].index
    ihi = g["hi"].idxmax().loc[keep].to_numpy(); ilo = g["lo"].idxmin().loc[keep].to_numpy()
    msr_all = df["msr"]
    return msr_all.loc[ihi].to_numpy(), msr_all.loc[ilo].to_numpy(), pd.DatetimeIndex(g["t"].min().loc[keep]), roll

def score(xh, xl, wins, shift=0):
    def ins(x):
        r = np.zeros(len(x), bool)
        for a, z in wins: r |= (x >= a+shift) & (x < z+shift)
        return r
    return ins(xh), ins(xl)

def run(label, windows, anchor=18, drop=0, reps=50):
    xh, xl, t, roll = build(anchor, drop)
    wins = [((hm(a)-roll) % 1440, (hm(z)-roll) % 1440) for a, z in windows]
    lo_ = min(a for a, _ in wins); hi_ = max(z for _, z in wins)
    day_len = 1380 if anchor == 18 else 1440
    h, l = score(xh, xl, wins)
    obs = (h.astype(float)+l)/2
    nulls = []
    for _ in range(reps):
        s = rng0.integers(-lo_, day_len-hi_+1, size=len(obs))
        hh, ll = score(xh, xl, wins, s); nulls.append((hh.astype(float)+ll)/2)
    nul = np.mean(nulls, axis=0)
    d = obs - nul
    # day bootstrap CI
    bs = [d[rng0.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    yrs = pd.Series(d, index=t.year).groupby(level=0).mean().round(3).to_dict()
    blocks = [round(b.mean(), 3) for b in np.array_split(d, 4)]
    print(f"{label:55s} n={len(d)} obs={obs.mean():.3f} null={nul.mean():.3f} diff={d.mean():+.3f} "
          f"CI[{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}] blocks={blocks}")
    return yrs

L = [("02:00", "05:00")]; N = [("08:30", "12:00")]; B = L+N
y = run("both windows (as tested)", B)
print("   by year:", y)
run("London 02-05 alone", L)
run("NY am 08:30-12 alone", N)
run("NY am standard end 08:30-11:00 alone", [("08:30", "11:00")])
run("both, drop first 30min after any halt", B, drop=30)
run("both, midnight NY anchor", B, anchor=0)
run("London alone, midnight anchor", L, anchor=0)
# placebo placements of the same total geometry (not the concept's): pre-registered comparison
run("forex killzones London+NY 07-10 (corpus alt)", [("02:00","05:00"),("07:00","10:00")])
