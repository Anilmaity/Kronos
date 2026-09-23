import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
import numpy as np, pandas as pd
m1 = cl.load_m1()
ev = pd.read_pickle("ev.pkl")
# --- independent daily table: trading day = NY date of (t + 6h) (18:00 NY roll)
idx = m1.index.tz_convert("America/New_York")
td = (idx + pd.Timedelta(hours=6)).normalize().tz_localize(None)
g = pd.DataFrame({"h": m1["high"].to_numpy(), "l": m1["low"].to_numpy(), "td": td,
                  "close_ns": (m1.index + pd.Timedelta(minutes=1)).asi8})
day = g.groupby("td").agg(h=("h","max"), l=("l","min"), n=("h","size"), last_close=("close_ns","max"))
day = day[day.n >= 600]
day["rng"] = day.h - day.l
day["adr"] = day.rng.rolling(20, min_periods=20).mean()
# running range per M1 bar
g["rh"] = g.groupby("td")["h"].cummax(); g["rl"] = g.groupby("td")["l"].cummin()
dt = pd.DatetimeIndex(ev.decision_time)
dns = dt.asi8
pos = np.searchsorted(g.close_ns.to_numpy(), dns, side="right") - 1
ev_td = (dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).normalize().tz_localize(None)
same = g.td.to_numpy()[pos] == ev_td.to_numpy()
cov = np.where(same, g.rh.to_numpy()[pos] - g.rl.to_numpy()[pos], np.nan)
# ADR from the last completed day strictly before the event's trading day (completed => last_close <= t)
dpos = np.searchsorted(day.last_close.to_numpy(), dns, side="right") - 1
adr = np.where(dpos >= 0, day.adr.to_numpy()[np.clip(dpos,0,None)], np.nan)
# also check the chosen day is not the event's own day
own = day.index.to_numpy()[np.clip(dpos,0,None)] == ev_td.to_numpy()
print("own-day leak rows:", own.sum())
ok = np.isfinite(cov) & np.isfinite(adr)
print("kept", ok.sum())
mine = pd.DataFrame({"decision_time": dt[ok], "cov": cov[ok], "adr": adr[ok]})
orig = pd.read_pickle("ev.pkl")
# orig ev.pkl is post-detect (already filtered)
print(len(orig))
mm = orig.merge(mine, on="decision_time", how="outer", indicator=True)
print(mm["_merge"].value_counts())
b = mm[mm._merge=="both"]
print("cov maxdiff", np.nanmax(np.abs(b["cov"]-b["day_covered"])), "adr maxdiff", np.nanmax(np.abs(b["adr"]-b["adr20"])))
mask_mine = (b["cov"] < b["adr"]).to_numpy()
print("mask agree", (mask_mine == b.open_adr.to_numpy()).mean(), "gate rate", mask_mine.mean())
