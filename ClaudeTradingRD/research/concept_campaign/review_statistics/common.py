import sys, time
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl
from concept_lab.engine import get_market

M1 = cl.load_m1()
MKT = get_market()
TN = MKT.tn
NY = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC")).tz_convert("America/New_York")
NYMIN = (NY.hour * 60 + NY.minute).to_numpy()
DAYKEY = np.asarray(cl.trading_day(pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC")))) if hasattr(cl, "trading_day") else None

def events_from_pos(pos, dirs, stop_dist=3.0, rr=2.0):
    t = pd.DatetimeIndex(pd.to_datetime(TN[pos]).tz_localize("UTC"))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": dirs,
                         "stop_dist": stop_dist, "rr": rr})

def z(r):
    se = (r["ci_hi"] - r["ci_lo"]) / (2 * 1.959964)
    return r["diff"] / se
