"""Per-trade forensics — last 12 months of the M3 stack (gated, mc=1).

Joins every trade to its entry-bar context (EMA20/200 distance, RSI3, ATR,
hour, dow) and prints the diagnostic tables used to identify structural
problems in the scalper.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH = Path(__file__).parent
sys.path.insert(0, str(SCRATCH))

from s93_ob_validate import run_combo, wilder_rsi_np  # noqa: E402
from optimize_manager_strategies import atr_np  # noqa: E402

m1 = pd.read_parquet(SCRATCH / "xau_m1_3y.parquet")
m1["time"] = pd.to_datetime(m1["time"], utc=True)
m3 = (m1.sort_values("time").set_index("time").resample("3min")
      .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
      .dropna().reset_index())

WIDE = tuple(range(1, 16))
KW = dict(dispm=0.5, ob_break=3, ob_entry="edge", rsi_n=3, rsi_ob=85,
          rsi_os=15, rsi_mode="momentum", max_concurrent=1, ema_filter=True)
COST = 0.45

trades, tags = run_combo(m3, models=("fvg", "ob", "rsi"), hours=WIDE,
                         cost=COST, struct=None, **KW)

Y0 = pd.Timestamp("2025-07-23", tz="UTC")
c = m3["close"].to_numpy(float)
h = m3["high"].to_numpy(float)
l = m3["low"].to_numpy(float)
atr = atr_np(h, l, c, 14)
ema20 = pd.Series(c).ewm(span=20, adjust=False).mean().to_numpy()
ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().to_numpy()
rsi3 = wilder_rsi_np(c, 3)
tidx = {t: i for i, t in enumerate(m3["time"])}

rows = []
for t, g in zip(trades, tags):
    if t.t_entry < Y0:
        continue
    i = tidx.get(t.t_entry)
    if i is None:
        continue
    risk = abs(t.entry - t.sl)
    rows.append({
        "t": t.t_entry, "model": g, "side": t.side, "outcome": t.outcome,
        "pnl": t.pnl, "risk": risk, "R": t.pnl / risk if risk > 0 else 0,
        "hold_min": (t.t_exit - t.t_entry).total_seconds() / 60.0,
        "hour": t.t_entry.hour, "dow": t.t_entry.dayofweek,
        "month": str(t.t_entry.to_period("M")),
        "risk_atr": risk / atr[i] if atr[i] > 0 else np.nan,
        "ema20_d": (t.entry - ema20[i]) / atr[i] * t.side,
        "ema200_d": (t.entry - ema200[i]) / atr[i] * t.side,
        "rsi3": rsi3[i],
    })
df = pd.DataFrame(rows)
print(f"trades last 12mo: {len(df)}  net {df['pnl'].sum():+.0f}pts  "
      f"WR {(df['pnl']>0).mean()*100:.1f}%")


def agg(g):
    gl = -g.loc[g.pnl <= 0, "pnl"].sum()
    pf = g.loc[g.pnl > 0, "pnl"].sum() / gl if gl > 0 else np.inf
    return pd.Series({"n": len(g), "WR": (g.pnl > 0).mean() * 100,
                      "PF": pf, "net": g.pnl.sum(), "avg": g.pnl.mean()})


pd.set_option("display.width", 150)
for dim in ("model", "hour", "dow", "month", "outcome", "side"):
    print(f"\n== by {dim} ==")
    print(df.groupby(dim).apply(agg, include_groups=False).round(2).to_string())

print("\n== risk size (ATR multiples) ==")
df["risk_b"] = pd.cut(df.risk_atr, [0, .5, .8, 1.1, 1.4, 99],
                      labels=["<0.5", "0.5-0.8", "0.8-1.1", "1.1-1.4", ">1.4"])
print(df.groupby("risk_b", observed=True).apply(agg, include_groups=False).round(2).to_string())

print("\n== entry stretch from EMA20 (ATRs, signed with trade dir) ==")
df["st_b"] = pd.cut(df.ema20_d, [-99, -1, 0, 1, 2, 99],
                    labels=["<-1", "-1-0", "0-1", "1-2", ">2"])
print(df.groupby("st_b", observed=True).apply(agg, include_groups=False).round(2).to_string())

print("\n== hold time of losers vs winners (min) ==")
print(df.groupby(df.pnl > 0)["hold_min"].describe()[["mean", "50%", "75%"]].round(1).to_string())
print("\nSL exits under 9 min (3 bars):",
      len(df[(df.outcome == "SL") & (df.hold_min <= 9)]),
      "net", round(df[(df.outcome == "SL") & (df.hold_min <= 9)].pnl.sum(), 0))

print("\n== re-entry same model+side within 15 min after an SL ==")
df = df.sort_values("t").reset_index(drop=True)
re_n, re_pnl = 0, 0.0
last_sl = {}
for _, r in df.iterrows():
    key = (r.model, r.side)
    if key in last_sl and (r.t - last_sl[key]).total_seconds() <= 900:
        re_n += 1
        re_pnl += r.pnl
    if r.outcome == "SL":
        last_sl[key] = r.t
print(f"re-entries: {re_n}  net {re_pnl:+.0f}pts")

print("\n== loss streaks / cluster days ==")
sign = (df.pnl > 0).astype(int)
streak = (sign.groupby((sign != sign.shift()).cumsum()).cumcount() + 1)
print("max consecutive losses:", int(streak[sign == 0].max()))
day = df.groupby(df.t.dt.date)["pnl"].agg(["sum", "count"])
bad = day[day["sum"] < -15]
print(f"days with net < -15pts: {len(bad)} (total {bad['sum'].sum():+.0f}pts "
      f"over {len(day)} days)")
print("worst 5 days:")
print(day.nsmallest(5, "sum").round(1).to_string())

print("\n== cost share ==")
aw = df.loc[df.pnl > 0, "pnl"].mean()
print(f"avg win {aw:.2f}pts, cost {COST}pt = {100*COST/ (aw + COST):.0f}% of gross win")
print("\n== EOD forced exits ==")
print(df[df.outcome == "EOD"].pipe(agg).round(2).to_string())
print("\n== TIME backstop exits ==")
print(df[df.outcome == "TIME"].pipe(agg).round(2).to_string())
