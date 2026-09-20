"""s5x_stab_spread_regime_maker.py — ADVERSARIAL VERIFICATION (subperiod stability)

Re-runs EXACTLY one config from family spread_regime_maker:
    k3_z3.0_tp1.5_sl1.5_maker_low
    {k_min:3, z_thr:3.0, tp:1.5, sl:1.5, gate:low_spread_q30_roll1h,
     maker_offset:0.15, maker_ttl_bars:36, maker_exit:True, max_hold_bars:360, lot:0.1}

Signal/feature construction copied verbatim from s5x_spread_regime_maker.py
(that file is NOT edited). Breaks results down by month, by ISO week within
the test window (>= 2026-05-01), by day-of-week and by hour-of-day.
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Projects\ClaudeProjects\ClaudeTradingBot")
import s5_engine as eng

T0 = time.time()

# ── fixed params (verbatim from original family file) ──
BARS_PER_MIN = 12
MAX_HOLD = 360
MAKER_OFF = 0.15
MAKER_TTL = 36
LOT = 0.10
ROLL_W = 720
GATE_Q_LO = 0.30
K = 3
ZT = 3.0
TP = 1.5
SL = 1.5
TAG = "k3_z3.0_tp1.5_sl1.5_maker_low"

df = eng.load_s5()
n = len(df)
mid = df["mid_c"].values
spr = (df["ask_c"] - df["bid_c"]).values
spr_s = pd.Series(spr)
print(f"[{time.time()-T0:5.1f}s] loaded {n} bars")

# ── causal gate + z-score (verbatim) ──
q_lo = spr_s.rolling(ROLL_W, min_periods=ROLL_W // 2).quantile(GATE_Q_LO).values
gate_low = spr <= q_lo
gate_low[np.isnan(q_lo)] = False

mid_s = pd.Series(mid)
ret = mid_s.diff(K * BARS_PER_MIN)
m = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).mean()
sd = ret.rolling(ROLL_W, min_periods=ROLL_W // 2).std()
z = ((ret - m) / sd).values

zp = np.roll(z, 1); zp[0] = 0.0
sell = (z > ZT) & (zp <= ZT)
buy = (z < -ZT) & (zp >= -ZT)
sell[np.isnan(z)] = False; buy[np.isnan(z)] = False
sell_i, buy_i = np.where(sell)[0], np.where(buy)[0]
print(f"[{time.time()-T0:5.1f}s] features done (gate_low frac={gate_low.mean():.3f})")

# ── intents (verbatim maker branch) ──
intents = []
for side, idxs in (("sell", sell_i), ("buy", buy_i)):
    idxs = idxs[gate_low[idxs]]
    idxs = idxs[(idxs > ROLL_W) & (idxs < len(df) - MAX_HOLD - 2)]
    for i in idxs:
        base = mid[i]
        lp = base + MAKER_OFF if side == "sell" else base - MAKER_OFF
        tp = lp - TP if side == "sell" else lp + TP
        sl = lp + SL if side == "sell" else lp - SL
        intents.append(eng.OrderIntent(
            signal_i=int(i), side=side, tp=tp, sl=sl,
            max_hold_bars=MAX_HOLD, lot=LOT, entry_type="maker",
            limit_price=lp, maker_exit=True, entry_ttl_bars=MAKER_TTL, tag=TAG))

fills = eng.simulate(df, intents, spread_model=0.20)
s = eng.stats(df, fills, TAG)
print(f"[{time.time()-T0:5.1f}s] intents={len(intents)} fills={len(fills)}")
print("REPRO full:", s["full"])
print("REPRO train:", s["train_jan_apr"])
print("REPRO test:", s["test_may_jul"])

# ── breakdowns ──
t = df["time"].values
rows = pd.DataFrame({
    "entry_t": pd.to_datetime([t[f.entry_i] for f in fills]),
    "pnl": [f.pnl for f in fills],
    "side": [f.intent.side for f in fills],
    "reason": [f.exit_reason for f in fills],
})
rows["month"] = rows["entry_t"].dt.strftime("%Y-%m")
rows["dow"] = rows["entry_t"].dt.day_name()
rows["hour"] = rows["entry_t"].dt.hour
# week label = Monday of the ISO week
rows["week"] = rows["entry_t"].dt.to_period("W-SUN").apply(lambda p: str(p.start_time.date()))

TEST_START = pd.Timestamp("2026-05-01")
test = rows[rows["entry_t"] >= TEST_START]


def agg(g):
    return pd.DataFrame({
        "trades": g["pnl"].count(),
        "net": g["pnl"].sum().round(2),
        "win_rate": (100 * (g["pnl"].apply(lambda x: (x > 0).mean()))).round(1),
        "expectancy": g["pnl"].mean().round(3),
    })


monthly = agg(rows.groupby("month"))
weekly_test = agg(test.groupby("week"))
dow = agg(rows.groupby("dow")).reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).dropna(how="all")
hod = agg(rows.groupby("hour"))
dow_test = agg(test.groupby("dow")).reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).dropna(how="all")
hod_test = agg(test.groupby("hour"))

full_net = rows["pnl"].sum()
test_net = test["pnl"].sum()

print("\n===== MONTHLY (full period) =====")
print(monthly.to_string())
print(f"\nfull net = {full_net:.2f}")
mshare = (monthly["net"] / full_net * 100).round(1)
print("month share of full net (%):")
print(mshare.to_string())

print("\n===== WEEKLY (test window, week=Mon date) =====")
print(weekly_test.to_string())
best_week = weekly_test["net"].idxmax()
best_week_net = weekly_test.loc[best_week, "net"]
print(f"\ntest net = {test_net:.2f}; best test week {best_week} net={best_week_net:.2f}; "
      f"test net ex-best-week = {test_net - best_week_net:.2f}")
pos_weeks = int((weekly_test["net"] > 0).sum())
print(f"positive test weeks: {pos_weeks}/{len(weekly_test)}")

# test months
test_monthly = agg(test.groupby("month"))
print("\n===== TEST MONTHLY =====")
print(test_monthly.to_string())

print("\n===== DAY OF WEEK (full | test) =====")
print(dow.to_string())
print(dow_test.to_string())

print("\n===== HOUR OF DAY (full) =====")
print(hod.to_string())
print("\n===== HOUR OF DAY (test) =====")
print(hod_test.to_string())

payload = {
    "family": "spread_regime_maker",
    "config": TAG,
    "verification": "subperiod_stability",
    "repro_stats": s,
    "monthly_full": monthly.reset_index().to_dict("records"),
    "monthly_share_pct": mshare.to_dict(),
    "weekly_test": weekly_test.reset_index().to_dict("records"),
    "test_monthly": test_monthly.reset_index().to_dict("records"),
    "dow_full": dow.reset_index().to_dict("records"),
    "dow_test": dow_test.reset_index().to_dict("records"),
    "hour_full": hod.reset_index().to_dict("records"),
    "hour_test": hod_test.reset_index().to_dict("records"),
    "test_net": round(float(test_net), 2),
    "test_net_ex_best_week": round(float(test_net - best_week_net), 2),
    "best_test_week": {"week": best_week, "net": round(float(best_week_net), 2)},
}
path = eng.save_result("stab_spread_regime_maker", payload)
print(f"\n[{time.time()-T0:5.1f}s] saved -> {path}")
