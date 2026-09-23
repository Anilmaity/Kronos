import sys, json
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b")
import numpy as np, pandas as pd
import _batch_common as bc
from _batch_common import cl
import importlib.util
spec = importlib.util.spec_from_file_location("cce", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/cheat-code-entry.py")
cce = importlib.util.module_from_spec(spec); spec.loader.exec_module(cce)

m1 = cl.load_m1()
rng = np.random.default_rng(7)

def base(tf="15min"):
    b = bc.bars(m1, tf)
    legs = bc.displacement_legs(b)
    tdir, tfire, _ = bc.trend_state(b, legs)
    return b, tdir

def mk(b, j, d, buf=0.0):
    o,h,l,c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[j]).tz_convert("UTC")
    stop = np.where(d == -1, h[j] + buf[j] if np.ndim(buf) else h[j] + buf,
                    l[j] - buf[j] if np.ndim(buf) else l[j] - buf)
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct, "direction": d, "stop_px": stop, "rr": 2.0})
    return bc.finish(ev)

def run(name, ev, hold="150min", extra=None):
    r = cl.trade_test(ev, max_hold=hold, n_boot=500, keep_trades=True)
    tr = r["_trades"]
    g = np.isfinite(tr["ctrl_mean_R_5050"])
    d5 = float((tr["net_R_5050"][g] - tr["ctrl_mean_R_5050"][g]).mean())
    out = dict(n=r["n"], diff=round(r["diff"],4), ci=[round(r["ci_lo"],4), round(r["ci_hi"],4)],
               verdict=r["verdict"], diff5050=round(d5,4),
               ties=[round(r["ties"]["real_ambiguous"],4), round(r["ties"]["control_ambiguous"],4)],
               ctrl_overlap=round(r["ctrl_overlap"],3),
               blocks={k: round(v["diff"],3) for k,v in (r.get("blocks") or {}).items()})
    # per-year
    tr = tr.assign(dd=tr["net_R"]-tr["ctrl_mean_R"], yr=pd.DatetimeIndex(tr["decision_time"]).year)
    out["by_year"] = tr.groupby("yr")["dd"].mean().round(3).to_dict()
    # stop/ATR quintile
    print(name, json.dumps(out, default=str), flush=True)
    return r, tr

b, tdir = base()
o,h,l,c = (b[k].to_numpy(float) for k in ("open","high","low","close"))
rngs = (b["high"]-b["low"]).rolling(96).mean().to_numpy()

# 1. original
ev0 = cce.detect(m1)
r0, tr0 = run("ORIG", ev0)
# stop quintile by risk / ATR
# 2. same opposing candles random direction
opp = ((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o))
j = np.flatnonzero(opp)
for s in range(3):
    dr = np.random.default_rng(100+s).choice([-1,1], len(j))
    run(f"SAMECANDLE_RANDDIR_s{s}", mk(b, j, dr))
# 3. counter-trend on same candles
run("SAMECANDLE_COUNTER", mk(b, j, -tdir[j]))
# 4. every in-trend candle (any colour), with trend
jt = np.flatnonzero(tdir != 0)
run("ALLTREND_WITHTREND", mk(b, jt, tdir[jt]))
# 4b. with-trend candles (same colour as trend) - non-opposing
wt = ((tdir == -1) & (c < o)) | ((tdir == 1) & (c > o))
jw = np.flatnonzero(wt)
run("WITHCOLOUR_WITHTREND", mk(b, jw, tdir[jw]))
# 5. opposing-colour candles anywhere (no trend filter): direction against the candle colour
jn = np.flatnonzero((c != o) & (tdir == 0))
run("NOTREND_FADECANDLE", mk(b, jn, np.where(c[jn] > o[jn], -1, 1)))
# 6. buffers (orig events)
jj = j[np.isfinite(rngs[j])]
for frac in (0.00025,):
    buf = c * frac
    run(f"BUF_pct{frac}", mk(b, j, tdir[j], buf))
for k in (0.05, 0.1):
    buf = np.nan_to_num(rngs * k)
    run(f"BUF_atr{k}", mk(b, j, tdir[j], buf))
