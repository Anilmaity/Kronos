"""direction=0 ('no signal') is silently traded as SHORT."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
from concept_lab.tests_api import _direction, _DIR_MAP
print("_DIR_MAP:", _DIR_MAP)
print("_direction([0, np.int64(0), 0.0, False]) ->", _direction(pd.Series([0, np.int64(0), 0.0, False])))
b = cl.bars("1h")
b = b[b.index >= "2023-01-01"].iloc[:600]
ct = pd.DatetimeIndex(b.close_time)
ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": 0,
                   "stop_dist": 5.0, "rr": 2.0})
r = cl.trade_test(ev, max_hold="4h", keep_trades=True)
print("n traded with direction=0:", r["n"], "dropped:", r["dropped"], "verdict:", r["verdict"])
print("directions actually traded:", np.unique(r["_trades"]["direction"]))
