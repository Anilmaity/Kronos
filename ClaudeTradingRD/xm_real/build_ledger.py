"""deals_raw.json -> trades.csv (one row per broker position) + cashflows.csv. Times UTC."""
import json
import pandas as pd

d = pd.DataFrame(json.load(open("deals_raw.json"))["deals"])
d["time"] = pd.to_datetime(d["time"], utc=True)
d.to_csv("deals.csv", index=False)
cash = d[d["type"].isin(["DEAL_TYPE_BALANCE", "DEAL_TYPE_CREDIT"])][["time", "type", "profit", "comment"]]
cash.to_csv("cashflows.csv", index=False)

rows = []
for pid, g in d[d["symbol"].notna()].groupby("positionId"):
    g = g.sort_values("time")
    i, o = g[g.entryType == "DEAL_ENTRY_IN"], g[g.entryType != "DEAL_ENTRY_IN"]
    if i.empty:
        continue
    vin, vout = i.volume.sum(), o.volume.sum()
    last = lambda col: (o[col].dropna().iloc[-1] if col in o and o[col].notna().any() else None)
    rows.append(dict(
        position_id=pid, symbol=i.symbol.iloc[0],
        side="BUY" if i["type"].iloc[0] == "DEAL_TYPE_BUY" else "SELL",
        open_time=i.time.iloc[0], close_time=o.time.iloc[-1] if len(o) else None,
        volume=round(vin, 2), closed_volume=round(vout, 2),
        entry=(i.price * i.volume).sum() / vin,
        exit=(o.price * o.volume).sum() / vout if vout else None,
        profit=g.profit.sum(), commission=g.commission.sum(), swap=g.swap.sum(),
        n_in=len(i), n_out=len(o),
        entry_reason=i.reason.iloc[0], exit_reason=o.reason.iloc[-1] if len(o) else None,
        exit_entry_type=o.entryType.iloc[-1] if len(o) else None,
        sl=last("stopLoss"), tp=last("takeProfit"),
        comment=o["comment"].dropna().iloc[-1] if "comment" in o and o["comment"].notna().any() else None,
    ))
t = pd.DataFrame(rows).sort_values("open_time").reset_index(drop=True)
t["net"] = t.profit + t.commission + t.swap
t["hold_s"] = (t.close_time - t.open_time).dt.total_seconds()
sgn = t.side.map({"BUY": 1, "SELL": -1})
t["pts"] = (t.exit - t.entry) * sgn
t.to_csv("trades.csv", index=False)

if __name__ == "__main__":
    c = t[t.close_time.notna()]
    print(len(t), "positions,", len(c), "closed | net", round(c.net.sum(), 2), "| win%", round((c.net > 0).mean() * 100, 1))
    print("PF", round(c.net[c.net > 0].sum() / -c.net[c.net < 0].sum(), 2), "| avg win", round(c.net[c.net > 0].mean(), 2), "avg loss", round(c.net[c.net < 0].mean(), 2))
    print("hold s quantiles", c.hold_s.quantile([.1, .5, .9]).round(0).tolist(), "| lots", c.volume.value_counts().head(8).to_dict())
    print("pts quantiles", c.pts.quantile([.05, .25, .5, .75, .95]).round(2).tolist())
    print(c.groupby(c.close_time.dt.date).net.agg(["count", "sum"]).round(2))
    print(t.entry_reason.value_counts().to_dict(), t.exit_reason.value_counts().to_dict(), t.exit_entry_type.value_counts().to_dict())
    print("SL set on", t.sl.notna().sum(), "TP set on", t.tp.notna().sum())
    print(cash.groupby("type").profit.agg(["count", "sum"]), cash.head(12).to_string())
