"""Two-sided ping-pong scalper — what the XM Real trader did on 2026-11-05 / 06 / 09, with a rail he did not have.

  books    a buy book and a sell book can be open together; every clip is one fixed size and has ITS OWN target T
  entry    a side with no clip opens one on a fade signal (5-min push at the edge of the 2-hour range)
  flip     when a clip reaches its target, open one clip on the OTHER side at once (sell -> target -> buy -> target ...)
  average  a side adds a clip when price is a step G beyond its last clip and the last closed minute turned back (max K)
  wait     a losing clip is never closed on its own; it waits for its target (his behaviour)
  rail     equity stop: if the floating loss of everything open reaches R % of equity, close everything (he had none —
           the broker's margin stop-out did this for him). Day floor -2.5 %. Flat at 20:50 UTC and for the news windows.
Clip size = R / worst case of one full book (K clips a step apart, one step beyond). Closed M1 bars, fills at next open.
ponytail: the equity stop is checked at each bar's high and low and exits at that extreme, slightly worse than a real stop.
"""
import sys
from dataclasses import dataclass
import numpy as np, pandas as pd
from data import load_m1
from range_scalp import prep

@dataclass
class P:
    T: float = 12.0
    G: float = 6.0
    K: int = 4
    flip: bool = True
    er_max: float = 0.3
    pull: float = 1.0
    risk_pct: float = 1.0
    day_floor: float = -2.5
    cost: float = 0.25
    start: float = 10_000.0
    lot: float = 0.0          # > 0: every clip is this fixed size (the trader used 0.04) instead of sizing from risk_pct
    stop: bool = True         # False: no equity stop (the trader's actual behaviour); set day_floor very low as well

def run(d, p=P()):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    A, R5, RNG, POS, ER, news, gap = (d[k].to_numpy() for k in ("atr", "r5", "rng", "pos", "er", "news", "gap"))
    idx = d.index; mn = idx.hour.to_numpy() * 60 + idx.minute.to_numpy(); day = idx.strftime("%Y-%m-%d").to_numpy()
    hs = p.cost / 2; eq = d0 = p.start; book = {1: [], -1: []}; pend = []; trades = []; days = {}
    unit = p.G * p.K * (p.K + 1) / 2 * 100

    def close(s, clip, px, why, i):
        nonlocal eq
        pnl = (px - clip["e"]) * s * clip["lot"] * 100; eq += pnl
        trades.append(dict(t=idx[clip["i"]], exit_t=idx[i], day=day[clip["i"]], side=s, e=clip["e"], x=px, pnl=pnl, why=why, mins=i - clip["i"], lot=clip["lot"], kind=clip["kind"], eq=eq))

    for i in range(len(c) - 1):
        if i == 0 or day[i] != day[i - 1]: d0 = eq
        for s, kind in pend:                                             # opens decided on the previous close
            lot = p.lot or round(eq * p.risk_pct / 100 / unit, 2)
            if lot >= 0.01 and len(book[s]) < p.K: book[s].append(dict(e=o[i] + s * hs, i=i, lot=lot, kind=kind))
        pend = []
        n_open = len(book[1]) + len(book[-1])
        if n_open:
            fl = lambda px: sum((px - hs - x["e"]) * x["lot"] for x in book[1]) * 100 + sum((x["e"] - px - hs) * x["lot"] for x in book[-1]) * 100
            R = eq * p.risk_pct / 100; worst = min((l[i], h[i]), key=fl)
            stop = p.stop and fl(worst) <= -R
            if stop or news[i] or mn[i] >= 20 * 60 + 50 or gap[i + 1]:
                for s in (1, -1):
                    for x in book[s]: close(s, x, (worst if stop else c[i]) - s * hs, "equity stop" if stop else "flat", i)
                    book[s] = []
            else:
                for s in (1, -1):
                    keep = []
                    for x in book[s]:
                        tp = x["e"] + s * p.T
                        if (h[i] - hs >= tp) if s > 0 else (l[i] + hs <= tp):
                            close(s, x, tp, "target", i)
                            if p.flip and len(book[-s]) < p.K and all(abs(y["e"] - tp) >= p.G for y in book[-s]): pend.append((-s, "flip"))
                        else: keep.append(x)
                    book[s] = keep
                for s in (1, -1):                                        # averaging
                    if book[s] and len(book[s]) < p.K and (book[s][-1]["e"] - c[i]) * s >= p.G and (c[i] - o[i]) * s > 0 and not any(q[0] == s for q in pend):
                        pend.append((s, "add"))
        days[day[i]] = (d0, eq); dp = (eq / d0 - 1) * 100
        if dp <= p.day_floor or news[i] or gap[i + 1] or mn[i] >= 20 * 60: pend = []; continue
        if ER[i] <= p.er_max and RNG[i] >= 2 * p.G:
            s = -1 if (POS[i] > 0.7 and R5[i] >= p.pull * A[i]) else 1 if (POS[i] < 0.3 and R5[i] <= -p.pull * A[i]) else 0
            if s and not book[s] and not any(q[0] == s for q in pend): pend.append((s, "signal"))
    t = pd.DataFrame(trades); dd = pd.DataFrame(days, index=["start", "end"]).T; dd["pct"] = (dd.end / dd.start - 1) * 100
    return t, dd

def stats(t, dd):
    a = dd[dd.index.isin(t.day)]; w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]; m = t.why.value_counts(normalize=True).mul(100).round(0)
    return dict(clips_day=round(len(t) / len(a), 1), win=round(len(w) / len(t) * 100, 1), pf=round(w.sum() / -lo.sum(), 2), hold=float(t.mins.median()),
                worst=round(a.pct.min(), 2), best=round(a.pct.max(), 2), red=round((a.pct < 0).mean() * 100), total=round((dd.end.iloc[-1] / dd.start.iloc[0] - 1) * 100, 1),
                pct_target=m.get("target", 0), pct_stop=m.get("equity stop", 0), pct_flat=m.get("flat", 0))

if __name__ == "__main__":
    d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
    sets = {"TRAIN": d[d.index < cut], "TEST": d[d.index >= cut], "LAST2W": d[d.index >= d.index[-1] - pd.Timedelta(days=14)]}
    cells = [dict(T=T, G=G, K=K, flip=fl, er_max=er) for T in (5.0, 12.0) for G in (4.0, 8.0) for K in (3, 5) for fl in (True, False) for er in (0.3, 9.0)]
    r = pd.DataFrame([{**kw, **stats(*run(sets["TRAIN"], P(**kw)))} for kw in cells]).sort_values("pf", ascending=False); r.to_csv("pingpong_grid_train.csv", index=False)
    print("TRAIN grid, best 12 of 32 (er_max 9 = no oscillation filter)"); print(r.head(12).to_string(index=False))
    kw = {k: (r.iloc[0][k].item() if hasattr(r.iloc[0][k], "item") else r.iloc[0][k]) for k in ("T", "G", "K", "flip", "er_max")}
    print("\nBest on TRAIN, once on TEST / last two weeks:", kw)
    for cost in (0.25, 0.0):
        for n, part in sets.items():
            t, dd = run(part, P(cost=cost, **kw)); print(f"  cost {cost:<4} {n:<7}", stats(t, dd))
            if cost == 0.25 and n == "LAST2W":
                print(dd.assign(clips=t.groupby("day").size(), wins=t[t.pnl > 0].groupby("day").size(), flips=t[t.kind == "flip"].groupby("day").size(), adds=t[t.kind == "add"].groupby("day").size(), stops=t[t.why == "equity stop"].groupby("day").size()).fillna(0).round(2).to_string())
                print("  by entry kind:", t.groupby("kind").pnl.agg(["size", "sum"]).round(0).to_dict("index"))
