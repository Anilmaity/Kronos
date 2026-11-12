"""Export the Asia-fit ping-pong lab trades (fit_asia_best.json) as the JSON the
dashboard's /strategy-data Lab tab reads. python export_lab_trades.py 2026-09-11 > lab.json"""
import json, sys, warnings
import pandas as pd
import ping_pong
from data import load_m1
from range_scalp import prep

warnings.simplefilter("ignore")
kw = json.load(open("fit_asia_best.json"))["kw"]
d = prep(load_m1()); d = d[d.index >= pd.Timestamp(sys.argv[1], tz="UTC")]
t, _ = ping_pong.run(d, ping_pong.P(stop=False, day_floor=-1e9, **kw))
json.dump({"lot": kw["lot"], "notes": ["lab ping-pong, Asia fit; display only"], "trades": [dict(
    entry_time=r.t.isoformat(), exit_time=r.exit_t.isoformat(), side="BUY" if r.side > 0 else "SELL",
    entry_px=float(r.e), exit_px=float(r.x), sl=None, tp=None, outcome=str(r.why), pnl_usd=float(r.pnl))
    for r in t.itertuples()]}, sys.stdout)
