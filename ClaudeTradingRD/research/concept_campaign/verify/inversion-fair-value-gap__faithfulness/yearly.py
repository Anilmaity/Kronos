import pandas as pd, numpy as np
tr = pd.read_pickle("base_trades.pkl")
tr["d"] = tr.net_R - tr.ctrl_mean_R; tr["d5"] = tr.net_R_5050 - tr.ctrl_mean_R_5050
print("overall diff", tr.d.mean().round(4), "5050", tr.d5.mean().round(4), "tie share", tr.tie.mean() if tr.tie.dtype!=object else tr.tie.value_counts().to_dict())
y = tr.groupby(pd.DatetimeIndex(tr.decision_time).year).agg(n=("d","size"), diff=("d","mean"), sd=("d","std"))
y["se"] = y.sd/np.sqrt(y.n); y["t"] = y["diff"]/y.se; print(y.round(4))
# leave-one-year-out
for yr in y.index:
    print(yr, "excluded ->", round(tr.d[pd.DatetimeIndex(tr.decision_time).year != yr].mean(),4))
# drop the best 12-month window
s = tr.set_index(pd.DatetimeIndex(tr.decision_time)).d.sort_index()
roll = s.rolling("365D").sum(); end = roll.idxmax(); start = end - pd.Timedelta("365D")
rest = s[(s.index <= start) | (s.index > end)]
print("best 365D window", start.date(), end.date(), "sum", round(roll.max(),1), "total sum", round(s.sum(),1), "rest diff", round(rest.mean(),4), "n", len(rest))
# since 2021 and 2023-12
print("post-2021-04 diff", round(s["2021-04-12":].mean(),4), "post-2023-12", round(s["2023-12-04":].mean(),4))
print("direction", tr.groupby("direction").d.agg(["size","mean"]).round(4))
print("delay entry-min after decision", (pd.DatetimeIndex(tr.entry_time)-pd.DatetimeIndex(tr.decision_time)).total_seconds().describe())
