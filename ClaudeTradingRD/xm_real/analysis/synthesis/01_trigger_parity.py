"""Synthesis check: does the codified M1 fade trigger (STRATEGY_SPEC.md, sections 4 and 5) describe the trader's real entries?

Measures RECALL of the trigger on the real decisions and its BASE RATE on all in-session M1 bars.
No outcome (P&L, forward return) is read here: this calibrates the trigger to behaviour, it is not a backtest.

Trigger at the close of M1 bar t (bid series, closed bars only):
    ret5  = close[t] - close[t-5]
    ATR5  = Wilder ATR(14) on M5 bars whose close <= close of bar t
    pos15 = (close[t] - min(low[t-14..t])) / (max(high[t-14..t]) - min(low[t-14..t]))
    SELL  = ret5 >= +K * ATR5 and pos15 >= 2/3        BUY = ret5 <= -K * ATR5 and pos15 <= 1/3
A real click at time T is compared with the last M1 bar that had CLOSED by T (open <= T - 60 s).

Run: ../../../.venv/bin/python 01_trigger_parity.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
K_GRID, K_STEP, STEP_FLOOR = (0.4, 0.6, 0.8, 1.0), 0.7, 2.0

m = pd.read_parquet(ROOT / "xau_m1_2026-07-16_now_mba.parquet").sort_values("time").reset_index(drop=True)
m5 = m.set_index("time").resample("5min", label="left", closed="left").agg(
    h=("bid_high", "max"), l=("bid_low", "min"), c=("bid_close", "last")).dropna()
pc = m5.c.shift()
tr = np.maximum(m5.h - m5.l, np.maximum((m5.h - pc).abs(), (m5.l - pc).abs()))
atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().dropna()
# an M5 bar opened at T5 is closed once the M1 bar opened at T5+4min has closed
avail = pd.DataFrame({"time": atr.index + pd.Timedelta(minutes=4), "atr5": atr.values})
m = pd.merge_asof(m, avail, on="time")
assert (m.time - pd.merge_asof(m[["time"]], avail.assign(src=avail.time), on="time").src).min() >= pd.Timedelta(0)

m["ret5"] = m.bid_close - m.bid_close.shift(5)
hi, lo = m.bid_high.rolling(15).max(), m.bid_low.rolling(15).min()
m["pos15"] = (m.bid_close - lo) / (hi - lo).where(hi > lo)
m["ok"] = (m.time - m.time.shift(14)) <= pd.Timedelta(minutes=30)          # gap guard: 15 bars inside 30 min
close_t = m.time + pd.Timedelta(minutes=1)
m["sess"] = (close_t.dt.hour >= 1) & (close_t.dt.hour < 21) & (close_t.dt.dayofweek < 5)


def sig(k):
    s = m.ok & m.atr5.notna() & (m.ret5 >= k * m.atr5) & (m.pos15 >= 2 / 3)
    b = m.ok & m.atr5.notna() & (m.ret5 <= -k * m.atr5) & (m.pos15 <= 1 / 3)
    return s.to_numpy(), b.to_numpy()


e = pd.read_csv(ROOT / "analysis/entries/entries_features.csv")
e["open_time"] = pd.to_datetime(e.open_time, utc=True, format="ISO8601")
d = e[e.click_in_event == 0].reset_index(drop=True)                          # one row per decision
j = np.searchsorted(m.time.to_numpy(), (d.open_time - pd.Timedelta(seconds=60)).to_numpy(), "right") - 1
lag = (d.open_time - (m.time.iloc[j].reset_index(drop=True) + pd.Timedelta(minutes=1))).dt.total_seconds()
assert (lag >= 0).all(), "look-ahead: signal bar had not closed at the click"
print(f"decisions {len(d)}; click minus signal-bar close: median {lag.median():.0f}s, max {lag.max():.0f}s")
print(f"ATR5 at the decisions: median {m.atr5.iloc[j].median():.2f} pts (IQR {m.atr5.iloc[j].quantile(.25):.2f}-{m.atr5.iloc[j].quantile(.75):.2f})")

week = (m.time >= "2026-11-04") & m.sess
full = (m.time < "2026-11-04") & m.sess
is_sell = d.side.eq("SELL").to_numpy()
rows = []
for k in K_GRID:
    s, b = sig(k)
    hit0 = np.where(is_sell, s[j], b[j])                                     # trigger on the last closed bar
    hit3 = np.where(is_sell, s[j] | s[j - 1] | s[j - 2], b[j] | b[j - 1] | b[j - 2])   # ... or within the last 3 closed bars
    opp0 = np.where(is_sell, b[j], s[j])                                     # the OPPOSITE trigger was on (he went with the move)
    base_w = (s[week].mean() + b[week].mean()) / 2                           # per-side base rate, trade week, in session
    base_f = (s[full].mean() + b[full].mean()) / 2
    w3 = pd.Series(s).rolling(3).max().fillna(0).astype(bool).to_numpy(), pd.Series(b).rolling(3).max().fillna(0).astype(bool).to_numpy()
    base_w3 = (w3[0][week].mean() + w3[1][week].mean()) / 2
    onset = (s & ~np.r_[False, s[:-1]]) | (b & ~np.r_[False, b[:-1]])
    per_day = pd.Series(onset[full.to_numpy()]).groupby(m.time[full].dt.date.to_numpy()).sum()
    for name, mask in (("all", np.ones(len(d), bool)), ("first", d.role.eq("first").to_numpy()),
                       ("avg_add", d.role.eq("avg_add").to_numpy()), ("hedge", d.role.eq("hedge").to_numpy())):
        rows.append(dict(K=k, subset=name, n=int(mask.sum()), recall_last_bar=hit0[mask].mean(), recall_3_bars=hit3[mask].mean(),
                         opposite_trigger_on=opp0[mask].mean(), base_week_last_bar=base_w, base_week_3_bars=base_w3,
                         base_jul_nov_last_bar=base_f, onsets_per_day_jul_nov=per_day.median()))
out = pd.DataFrame(rows)
out["lift_last_bar"] = out.recall_last_bar / out.base_week_last_bar
out["lift_3_bars"] = out.recall_3_bars / out.base_week_3_bars
out.round(3).to_csv(HERE / "trigger_parity.csv", index=False)
print(out.round(3).to_string(index=False))

# averaging-add spacing rule: add when price is >= max(K_STEP*ATR5, STEP_FLOOR) beyond the previous same-side fill
a = d[d.role.eq("avg_add")]
step = np.maximum(K_STEP * m.atr5.iloc[j[a.index]].to_numpy(), STEP_FLOOR)
print(f"\navg_add decisions {len(a)}: spacing >= max({K_STEP} x ATR5, {STEP_FLOOR}) in {(a.same_adverse_last.to_numpy() >= step).mean():.0%}; "
      f"step at those decisions median {np.median(step):.2f} pts; real spacing median {a.same_adverse_last.median():.2f}")
a5 = m.atr5.iloc[j]
print(f"ATR5 at the {len(d)} decisions: min {a5.min():.2f}, p5 {a5.quantile(.05):.2f}, p10 {a5.quantile(.10):.2f}; "
      f">= 3.0 pts at {int((a5 >= 3.0).sum())} of {len(d)} decisions and {int((a5[d.role.eq('first').to_numpy()] >= 3.0).sum())} of 27 fresh entries")
print(f"in-session M1 bars with ATR5 >= 3.0: trade week {(m.atr5[week] >= 3.0).mean():.0%}, Jul-Nov before it {(m.atr5[full] >= 3.0).mean():.0%}")
s6, b6 = sig(0.6)
g = m.atr5.to_numpy() >= 3.0
on = ((s6 & g) & ~np.r_[False, (s6 & g)[:-1]]) | ((b6 & g) & ~np.r_[False, (b6 & g)[:-1]])
pdx = pd.Series(on[full.to_numpy()]).groupby(m.time[full].dt.date.to_numpy()).sum()
print(f"K=0.6 trigger onsets per day with the ATR5 >= 3.0 guard, Jul-Nov: median {pdx.median():.0f} (IQR {pdx.quantile(.25):.0f}-{pdx.quantile(.75):.0f})")
fr = d.role.eq("first").to_numpy()
hit = np.where(is_sell, s6[j], b6[j]) & g[j]
print(f"K=0.6 with the guard: trigger on at the last closed bar for {int(hit[fr].sum())} of 27 fresh entries, {int(hit.sum())} of {len(d)} decisions")
print(f"in-session M1 bars: trade week {int(week.sum())}, Jul-Nov before it {int(full.sum())} ({m.time[full].dt.date.nunique()} days)")
