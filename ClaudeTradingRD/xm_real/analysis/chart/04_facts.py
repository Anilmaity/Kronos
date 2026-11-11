"""Numbers read off the chart, recomputed from the raw ledgers so they do not depend on the plotting code.

Run:  ../../../.venv/bin/python 04_facts.py     (after 01_basis.py and 02_equity.py)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
pd.set_option("display.width", 200)

basis = json.loads((HERE / "basis.json").read_text())
SPREAD = basis["xm_implied_median_spread"]
t = pd.read_csv(ROOT / "trades.csv")
for c in ("open_time", "close_time"):
    t[c] = pd.to_datetime(t[c], utc=True, format="ISO8601")
t["sgn"] = t.side.map({"BUY": 1, "SELL": -1})
t["how"] = np.where(t.exit_entry_type == "DEAL_ENTRY_OUT_BY", "close-by",
                    t.exit_reason.map({"DEAL_REASON_MOBILE": "manual", "DEAL_REASON_TP": "TP", "DEAL_REASON_SO": "stop-out"}))
eq = pd.read_parquet(HERE / "equity_5s.parquet")
eq = eq[eq.time >= t.open_time.min()]

print("== exits: how positions ended, by sign of the booked net")
x = t.assign(res=np.where(t.net > 0, "win", np.where(t.net < 0, "loss", "zero")))
print(x.pivot_table(index="how", columns="res", values="net", aggfunc=["count", "sum"], fill_value=0).round(2))
print(f"positions closed by hand at a loss (not close-by, not stop-out): {((t.how == 'manual') & (t.net < 0)).sum()} of {len(t)}"
      f"  worth {t[(t.how == 'manual') & (t.net < 0)].net.sum():.2f}")
print(f"stop-loss set on {t.sl.notna().sum()} positions, take-profit on {t.tp.notna().sum()}")

print("\n== exposure (5 s grid, market hours from first trade to end of data)")
op = eq[eq.gross_lots > 0]
print(f"time with a position open: {len(op) / len(eq):.1%} of {len(eq) * 5 / 3600:.0f} market hours")
ev = pd.concat([pd.DataFrame(dict(time=t.open_time, side=t.side, d=1)), pd.DataFrame(dict(time=t.close_time, side=t.side, d=-1))]).sort_values(["time", "d"])
print(f"gross lots  max {eq.gross_lots.max():.2f}   net lots  min {eq.net_lots.min():+.2f}  max {eq.net_lots.max():+.2f}"
      f"   positions open at once: max {ev.d.cumsum().max()} (buys {ev[ev.side == 'BUY'].d.cumsum().max()}, sells {ev[ev.side == 'SELL'].d.cumsum().max()})")
print(f"while open: floating P&L negative {((op.floating < 0).mean()):.1%} of the time, median {op.floating.median():.2f}, worst {op.floating.min():.2f}"
      f" at {op.time[op.floating.idxmin()]}")
pk = eq.loc[eq.balance.idxmax()]
print(f"balance peak {pk.balance:.2f} at {pk.time}: equity then {pk.equity:.2f} (floating {pk.floating:.2f}, net {pk.net_lots:+.2f} lots)")
print(f"own-money equity peak {eq.equity.max():.2f} at {eq.time[eq.equity.idxmax()]}")

print("\n== adds: was a same-side position already open, and under water, when each entry was made?")
rows = []
for p in t.itertuples():
    o = t[(t.side == p.side) & (t.open_time < p.open_time) & (t.close_time > p.open_time)]
    if len(o) == 0:
        rows.append(dict(n_open=0, stack_pts=np.nan, worst_pts=np.nan))
        continue
    # an existing long is worth (this buy's ask - spread) - its entry; an existing short, its entry - (this sell's bid + spread)
    fl = ((p.entry - p.sgn * SPREAD) - o.entry) * p.sgn
    rows.append(dict(n_open=len(o), stack_pts=float((fl * o.volume).sum() / o.volume.sum()), worst_pts=float(fl.min())))
a = pd.concat([t[["side", "open_time", "volume", "entry", "net", "how"]], pd.DataFrame(rows)], axis=1)
first, add = a[a.n_open == 0], a[a.n_open > 0]
print(f"entries with no same-side position open: {len(first)}   adds to an existing same-side stack: {len(add)}")
print(f"  of the {len(add)} adds: stack under water {(add.stack_pts < 0).sum()} ({(add.stack_pts < 0).mean():.1%}), in profit {(add.stack_pts >= 0).sum()}")
u = add[add.stack_pts < 0]
print(f"  adds to a losing stack: stack was a median {u.stack_pts.median():.2f} USD/oz under water (p10 {u.stack_pts.quantile(.1):.2f}, worst {u.stack_pts.min():.2f});"
      f" same-side positions already open: median {u.n_open.median():.0f}, max {u.n_open.max()}")
for name, g in [("first entries", first), ("adds, stack in profit", add[add.stack_pts >= 0]), ("adds, stack under water", u)]:
    print(f"  {name:24s} n={len(g):3d}  win rate {(g.net > 0).mean():.1%}  net {g.net.sum():9.2f}  stop-outs {(g.how == 'stop-out').sum()}")
print("  side split:", t.side.value_counts().to_dict(), " lots:", t.volume.value_counts().to_dict())

print("\n== cash habit: what is left on the account after each withdrawal")
d = pd.read_csv(ROOT / "deals.csv")
d["time"] = pd.to_datetime(d["time"], utc=True, format="ISO8601")
d = d.sort_values(["time", "id"]).reset_index(drop=True)
d["bal"] = (d.profit + d.swap.fillna(0) + d.commission.fillna(0)).where(d.type != "DEAL_TYPE_CREDIT", 0).cumsum()
w = d[d.comment.fillna("").str.startswith("CW-") & ~d.comment.fillna("").str.contains("ERR")]
print(w[["time", "profit", "bal"]].to_string(index=False, float_format="%.2f"))
dep = d[d.comment.fillna("").str.startswith("CD-") | d.comment.fillna("").str.startswith("Transfer")]
print(f"deposits n={len(dep)} median {dep.profit.median():.2f} total {dep.profit.sum():.2f}; withdrawals n={len(w)} total {w.profit.sum():.2f}")
print("each deposit: balance just before it, floating P&L then, time since the last stop-out")
for r in dep.itertuples():
    prior, e = d.bal[d.time < r.time], eq[eq.time <= r.time].tail(1)
    live = len(e) and (r.time - e.time.iloc[0]) < pd.Timedelta(minutes=5)
    last = t[(t.how == "stop-out") & (t.close_time < r.time)].close_time.max()
    print(f"  {r.time:%m-%d %H:%M}  +{r.profit:7.2f}  balance before {prior.iloc[-1] if len(prior) else 0:8.2f}"
          f"  floating {e.floating.iloc[0] if live else 0:9.2f}  since last stop-out {'-' if pd.isna(last) else str(r.time - last).split('.')[0]}")

print("\n== account wipe-outs: balance back to zero after a stop-out, refilled by a new deposit")
so = t[t.how == "stop-out"].sort_values("close_time")
so = so.assign(cl=(so.close_time.diff() > pd.Timedelta(minutes=5)).cumsum())
for _, c in so.groupby("cl"):
    j = eq.time.searchsorted(c.close_time.min()) - 1
    b, k = eq.iloc[j], eq.iloc[min(j + 60, len(eq) - 1)]
    print(f"  {c.close_time.min():%m-%d %H:%M} UTC  n={len(c):2d}  booked {c.net.sum():9.2f}  sides {dict(c.side.value_counts())}"
          f"  before: balance {b.balance:8.2f} equity {b.equity:8.2f} bonus {b.credit:6.2f}   5 min later: balance {k.balance:7.2f}")
