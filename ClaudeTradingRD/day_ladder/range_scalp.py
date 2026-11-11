"""Range Grid Scalper — codifies the XM Real trader's three profitable days (2026-11-05, 06, 09), plus the stop he lacked.

  regime  trade only while gold oscillates: over the last LOOK minutes the net move is < ER_MAX of the range travelled
  entry   fade a 5-minute push at the edge of that range (sell in the top 30 %, buy in the bottom 30 %)
  size    one fixed clip per entry, sized from the risk budget (his 0.04-lot habit); never a bigger clip
  grid    add one clip every G points against, up to K clips (his median add spacing was ~3.8 pts)
  target  small shared target: TP points beyond the basket's average entry
  stop    hard stop one grid step beyond the last clip; a full stop loses exactly the risk budget
  rails   0.5 % risk per basket, day floor -2.5 %, flat for the New York releases and at 20:50 UTC
Closed M1 bars, fill at next open, stop checked before adds and target inside a bar.
"""
import sys
from dataclasses import dataclass
import numpy as np, pandas as pd
from data import load_m1, atr

@dataclass
class P:
    tp: float = 2.0
    G: float = 4.0
    K: int = 4
    er_max: float = 0.3
    look: int = 120
    pull: float = 1.0
    risk_pct: float = 0.5
    day_floor: float = -2.5
    max_hold: int = 240
    cost: float = 0.6
    start: float = 10_000.0
    flip: bool = False        # control: trade WITH the push instead of fading it
    regime: bool = True       # control: False = ignore the oscillation filter

def prep(d, look=120):
    d = d.copy(); d["atr"] = atr(d, 30); d["r5"] = d.close - d.close.shift(5)
    hi, lo = d.high.rolling(look).max(), d.low.rolling(look).min()
    d["rng"] = hi - lo; d["pos"] = (d.close - lo) / (hi - lo); d["er"] = (d.close - d.close.shift(look)).abs() / (hi - lo)
    ny = d.index.tz_convert("America/New_York"); m = ny.hour * 60 + ny.minute
    d["news"] = ((m >= 8 * 60 + 25) & (m < 8 * 60 + 45)) | ((m >= 9 * 60 + 55) & (m < 10 * 60 + 10))
    d["gap"] = d.index.to_series().diff().dt.total_seconds().fillna(60) > 90
    return d.dropna()

def run(d, p=P()):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    A, R5, RNG, POS, ER, news, gap = (d[k].to_numpy() for k in ("atr", "r5", "rng", "pos", "er", "news", "gap"))
    idx = d.index; mn = idx.hour.to_numpy() * 60 + idx.minute.to_numpy(); day = idx.strftime("%Y-%m-%d").to_numpy()
    hs = p.cost / 2; eq = d0 = p.start; b = None; trades = []; days = {}
    unit = p.G * p.K * (p.K + 1) / 2 * 100                  # USD lost at the stop per 1.00-lot clip
    for i in range(len(c) - 1):
        if i == 0 or day[i] != day[i - 1]: d0 = eq
        if b:
            s = b["s"]; px = None
            if (l[i] - hs <= b["stop"]) if s > 0 else (h[i] + hs >= b["stop"]):
                gapped = (o[i] - hs <= b["stop"]) if s > 0 else (o[i] + hs >= b["stop"])
                px, why = ((o[i] - s * hs) if gapped else b["stop"]), "stop"
            else:
                added = False
                while b["n"] < p.K and ((l[i] + hs <= b["e"] - b["n"] * p.G) if s > 0 else (h[i] - hs >= b["e"] + b["n"] * p.G)):
                    b["fills"].append(b["e"] - s * b["n"] * p.G); b["n"] += 1; added = True
                tp = np.mean(b["fills"]) + s * p.tp
                if not added and ((h[i] - hs >= tp) if s > 0 else (l[i] + hs <= tp)): px, why = tp, "tp"
                if px is None and (i - b["i"] >= p.max_hold or news[i] or mn[i] >= 20 * 60 + 50 or gap[i + 1]):
                    px, why = c[i] - s * hs, "time/flat"
            if px is not None:
                pnl = sum((px - f) * s for f in b["fills"]) * b["lot"] * 100
                eq += pnl; trades.append(dict(t=idx[b["i"]], day=day[b["i"]], side=s, clips=b["n"], pnl=pnl, why=why, mins=i - b["i"], lot=b["lot"])); b = None
        days[day[i]] = (d0, eq); dp = (eq / d0 - 1) * 100
        if b or dp <= p.day_floor or news[i] or gap[i + 1] or mn[i] >= 20 * 60: continue
        if p.regime and (ER[i] > p.er_max or RNG[i] < 2 * p.G): continue
        s = -1 if (POS[i] > 0.7 and R5[i] >= p.pull * A[i]) else 1 if (POS[i] < 0.3 and R5[i] <= -p.pull * A[i]) else 0
        if not s: continue
        if p.flip: s = -s
        risk = min(eq * p.risk_pct / 100, (dp - p.day_floor) / 100 * d0); lot = round(risk / unit, 2)
        if lot < 0.01: continue
        e = o[i + 1] + s * hs
        b = dict(s=s, i=i + 1, e=e, fills=[e], n=1, lot=lot, stop=e - s * p.G * p.K)
    t = pd.DataFrame(trades); dd = pd.DataFrame(days, index=["start", "end"]).T; dd["pct"] = (dd.end / dd.start - 1) * 100
    return t, dd

def stats(t, dd):
    if t.empty: return dict(trades=0)
    a = dd[dd.index.isin(t.day)]; w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
    return dict(days=len(a), tr_day=round(len(t) / len(a), 1), win=round(len(w) / len(t) * 100, 1), pf=round(w.sum() / max(-lo.sum(), 1e-9), 2),
                stops=round((t.why == "stop").mean() * 100, 1), clips=round(t.clips.mean(), 2), hold=t.mins.median(),
                worst=round(a.pct.min(), 2), best=round(a.pct.max(), 2), red=round((a.pct < 0).mean() * 100), mean=round(a.pct.mean(), 3),
                total=round((dd.end.iloc[-1] / dd.start.iloc[0] - 1) * 100, 1))

if __name__ == "__main__":
    raw = load_m1(); d = prep(raw); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
    train, test = d[d.index < cut], d[d.index >= cut]; last = d[d.index >= d.index[-1] - pd.Timedelta(days=14)]
    if "grid" in sys.argv:
        rows = [dict(tp=tp, G=G, K=K, er=er, **stats(*run(train, P(tp=tp, G=G, K=K, er_max=er))))
                for tp in (1.2, 2.0, 4.0) for G in (3.0, 4.0, 6.0) for K in (3, 4) for er in (0.3, 0.5)]
        r = pd.DataFrame(rows).sort_values("pf", ascending=False); r.to_csv("range_grid_train.csv", index=False); print(r.to_string(index=False)); sys.exit()
    kw = {k: (int(v) if k == "K" else float(v)) for k, v in (a.split("=") for a in sys.argv[1:])}
    for label, p in (("pick", P(**kw)), ("cost 0.9", P(cost=.9, **kw)), ("zero cost", P(cost=0, **kw)),
                     ("control: with the push", P(flip=True, **kw)), ("control: no regime filter", P(regime=False, **kw))):
        for n, part in (("TRAIN", train), ("TEST", test), ("LAST2W", last)):
            t, dd = run(part, p); print(f"{label:<26} {n:<7}", stats(t, dd))
            if label == "pick" and n == "LAST2W":
                print(dd.assign(baskets=t.groupby("day").size(), wins=t[t.pnl > 0].groupby("day").size(), stops=t[t.why == "stop"].groupby("day").size()).fillna(0).round(2).to_string())
