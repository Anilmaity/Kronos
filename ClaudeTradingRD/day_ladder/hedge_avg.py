"""Hedge-and-average scalper (operator's idea, 2026-11-12).

  open     a buy and a sell together, one clip each, while gold is oscillating (no direction call needed)
  phase 1  whichever side reaches +T first is closed at its target (profit banked)
  phase 2  the other side is now ~T under water: average into it — one more clip each time price is a step g further
           against and the last closed minute turned back — up to K clips
  exit     close the averaged side at no profit / no loss (its average entry). Cycle result = the banked target.
           `be="cycle"` instead closes when banked + floating = 0 (the literal "whole trade at breakeven" reading).
  rails    hard stop (K+1) steps from the open, sized so the worst case loses <= the risk budget; time limit; day floor;
           flat for news and at 20:50 UTC.    T = TPA x ATR30, g = STEP x ATR30, cost 0.25 pt per round trip per clip.
"""
import sys
from dataclasses import dataclass
import numpy as np, pandas as pd
from data import load_m1
from range_scalp import prep, stats

@dataclass
class P:
    tpa: float = 1.0
    step: float = 1.5
    K: int = 4
    be: str = "side"          # "side": averaged side exits at its own breakeven; "cycle": whole cycle exits at zero
    max_hold: int = 240
    er_max: float = 0.3
    risk_pct: float = 0.5
    day_floor: float = -2.5
    cost: float = 0.25
    start: float = 10_000.0

def run(d, p=P()):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    A, RNG, ER, news, gap = (d[k].to_numpy() for k in ("atr", "rng", "er", "news", "gap"))
    idx = d.index; mn = idx.hour.to_numpy() * 60 + idx.minute.to_numpy(); day = idx.strftime("%Y-%m-%d").to_numpy()
    hs = p.cost / 2; eq = d0 = p.start; b = None; trades = []; days = {}
    for i in range(len(c) - 1):
        if i == 0 or day[i] != day[i - 1]: d0 = eq
        if b:
            px = None; flat = news[i] or mn[i] >= 20 * 60 + 50 or gap[i + 1]; late = i - b["i"] >= p.max_hold
            if b["s"] == 0:                                              # phase 1: both sides open
                up, dn = h[i] - hs >= b["p"] + hs + b["T"], l[i] + hs <= b["p"] - hs - b["T"]
                if up and dn: up = c[i] < o[i]; dn = not up              # both touched: assume the worse order for what follows
                if up or dn:
                    b["s"] = -1 if up else 1                             # the side we keep (the loser)
                    b["bank"] = b["T"] * b["lot"] * 100; b["fills"] = [b["p"] + b["s"] * hs]; b["stop"] = b["p"] - b["s"] * b["S"]
                elif flat or late:
                    pnl = -4 * hs * b["lot"] * 100                             # both closed at the same price: two round-trip costs
                    eq += pnl; trades.append(dict(t=idx[b["i"]], day=day[b["i"]], pnl=pnl, why="no move", clips=0, mins=i - b["i"])); b = None
            else:                                                        # phase 2: average the remaining side
                s = b["s"]
                if b.get("add"): b["fills"].append(o[i] + s * hs); b["add"] = False
                n = len(b["fills"]); avg = float(np.mean(b["fills"]))
                tgt = avg if p.be == "side" else avg - s * b["bank"] / (n * b["lot"] * 100)   # cycle: banked profit lets it exit earlier
                if (l[i] - hs <= b["stop"]) if s > 0 else (h[i] + hs >= b["stop"]):
                    gapped = (o[i] - hs <= b["stop"]) if s > 0 else (o[i] + hs >= b["stop"])
                    px, why = ((o[i] - s * hs) if gapped else b["stop"]), "stop"
                elif (h[i] - hs >= tgt) if s > 0 else (l[i] + hs <= tgt): px, why = tgt, "breakeven"
                elif flat or late: px, why = c[i] - s * hs, "flat" if flat else "time"
                elif n < p.K + 1 and (b["fills"][-1] - c[i]) * s >= b["g"] and (c[i] - o[i]) * s > 0: b["add"] = True
                if px is not None:
                    pnl = b["bank"] + sum((px - f) * s for f in b["fills"]) * b["lot"] * 100
                    eq += pnl; trades.append(dict(t=idx[b["i"]], day=day[b["i"]], pnl=pnl, why=why, clips=n, mins=i - b["i"])); b = None
        days[day[i]] = (d0, eq); dp = (eq / d0 - 1) * 100
        if b or dp <= p.day_floor or news[i] or gap[i + 1] or mn[i] >= 20 * 60: continue
        g = p.step * A[i]
        if ER[i] > p.er_max or RNG[i] < 2 * g: continue
        risk = min(eq * p.risk_pct / 100, (dp - p.day_floor) / 100 * d0); n = p.K + 1; S = (p.K + 1) * g
        lot = round(risk / ((n * S - g * n * (n - 1) / 2) * 100), 2)     # worst case: every clip one step apart, then the stop
        if lot < 0.01: continue
        b = dict(s=0, i=i + 1, p=o[i + 1], T=p.tpa * A[i], g=g, lot=lot, S=S)
    t = pd.DataFrame(trades); dd = pd.DataFrame(days, index=["start", "end"]).T; dd["pct"] = (dd.end / dd.start - 1) * 100
    return t, dd
