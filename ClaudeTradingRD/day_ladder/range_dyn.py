"""Dynamic Range Scalper — range_scalp.py with more clips, volatility-based averaging and an adaptive exit.

  entry    same as range_scalp: oscillating market, fade a 5-min push at the edge of the 2-hour range
  adds     up to K clips. Step g = STEP x ATR30 at entry (wider when gold is moving). A clip is added only when price is
           at least g beyond the last fill AND the latest closed minute turned back our way (dynamic, not a resting grid)
  target   TP = TPA x ATR30 beyond the average entry, multiplied by DECAY for each extra clip (deep baskets get out sooner)
  exits    target; hard stop (K+1) x g from the first entry, sized so it loses <= the risk budget; range break (the 2-hour
           net move exceeds ER_EXIT of the range -> close now); time stop; flat for news and at 20:50 UTC
Cost default 0.25 pt = FundingPips 0.2 spread + $5/lot round-trip commission (measured from the account's deals).
"""
import sys
from dataclasses import dataclass
import numpy as np, pandas as pd
from data import load_m1
from range_scalp import prep, stats

@dataclass
class P:
    K: int = 6
    step: float = 2.0
    tpa: float = 1.5
    decay: float = 0.7
    confirm: bool = True
    er_max: float = 0.3
    er_exit: float = 0.6
    pull: float = 1.0
    risk_pct: float = 0.5
    day_floor: float = -2.5
    max_hold: int = 240
    cost: float = 0.25
    start: float = 10_000.0
    flip: bool = False
    reverse: int = 0          # after a losing time-stop or hard stop, open the opposite side, up to this many times in a row

def run(d, p=P()):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    A, R5, RNG, POS, ER, news, gap = (d[k].to_numpy() for k in ("atr", "r5", "rng", "pos", "er", "news", "gap"))
    idx = d.index; mn = idx.hour.to_numpy() * 60 + idx.minute.to_numpy(); day = idx.strftime("%Y-%m-%d").to_numpy()
    hs = p.cost / 2; eq = d0 = p.start; b = None; trades = []; days = {}; pend = None
    for i in range(len(c) - 1):
        if i == 0 or day[i] != day[i - 1]: d0 = eq
        if b:
            s = b["s"]; px = None
            if b.get("add"):                                             # add decided on the previous close fills at this open
                b["fills"].append(o[i] + s * hs); b["ft"].append(i); b["add"] = False
            if (l[i] - hs <= b["stop"]) if s > 0 else (h[i] + hs >= b["stop"]):
                gapped = (o[i] - hs <= b["stop"]) if s > 0 else (o[i] + hs >= b["stop"])
                px, why = ((o[i] - s * hs) if gapped else b["stop"]), "stop"
            else:
                n = len(b["fills"]); tp = np.mean(b["fills"]) + s * b["tp0"] * p.decay ** (n - 1)
                if (h[i] - hs >= tp) if s > 0 else (l[i] + hs <= tp): px, why = tp, "tp"
                elif ER[i] > p.er_exit and (c[i] - b["fills"][0]) * s < 0: px, why = c[i] - s * hs, "range break"
                elif news[i] or mn[i] >= 20 * 60 + 50 or gap[i + 1]: px, why = c[i] - s * hs, "flat"
                elif i - b["i"] >= p.max_hold: px, why = c[i] - s * hs, "time"
                elif n < p.K and (b["fills"][-1] - c[i]) * s >= b["g"] and (not p.confirm or (c[i] - o[i]) * s > 0):
                    b["add"] = True
            if px is not None:
                pnl = sum((px - f) * s for f in b["fills"]) * b["lot"] * 100
                eq += pnl; trades.append(dict(t=idx[b["i"]], day=day[b["i"]], side=s, clips=len(b["fills"]), pnl=pnl, why=why, mins=i - b["i"], lot=b["lot"],
                                             exit_t=idx[i], exit_px=px, fills=list(b["fills"]), fill_t=[idx[k] for k in b["ft"]], eq=eq, chain=b["chain"]))
                if pnl < 0 and why in ("time", "stop") and b["chain"] < p.reverse: pend = (-s, b["chain"] + 1)
                b = None
        days[day[i]] = (d0, eq); dp = (eq / d0 - 1) * 100
        if b or dp <= p.day_floor or news[i] or gap[i + 1] or mn[i] >= 20 * 60: pend = None if not b else pend; continue
        g = p.step * A[i]; chain = 0
        if pend:                                                         # reverse entry: no signal needed
            s, chain = pend; pend = None
        else:
            if ER[i] > p.er_max or RNG[i] < 2 * g: continue
            s = -1 if (POS[i] > 0.7 and R5[i] >= p.pull * A[i]) else 1 if (POS[i] < 0.3 and R5[i] <= -p.pull * A[i]) else 0
            if not s: continue
            if p.flip: s = -s
        risk = min(eq * p.risk_pct / 100, (dp - p.day_floor) / 100 * d0)
        S = (p.K + 1) * g                                                # stop distance from the first entry
        lot = round(risk / ((p.K * S - g * p.K * (p.K - 1) / 2) * 100), 2)  # worst case: every clip filled exactly one step apart
        if lot < 0.01: continue
        e = o[i + 1] + s * hs
        b = dict(s=s, i=i + 1, chain=chain, fills=[e], ft=[i + 1], lot=lot, g=g, tp0=p.tpa * A[i], stop=e - s * S)
    t = pd.DataFrame(trades); dd = pd.DataFrame(days, index=["start", "end"]).T; dd["pct"] = (dd.end / dd.start - 1) * 100
    return t, dd

KEEP = ("tr_day", "win", "pf", "stops", "clips", "hold", "worst", "best", "red", "total")
if __name__ == "__main__":
    d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
    sets = {"TRAIN": d[d.index < cut], "TEST": d[d.index >= cut], "LAST2W": d[d.index >= d.index[-1] - pd.Timedelta(days=14)]}
    if "grid" in sys.argv:
        rows = [dict(K=K, step=st, tpa=tpa, decay=dc, **{k: v for k, v in stats(*run(sets["TRAIN"], P(K=K, step=st, tpa=tpa, decay=dc))).items() if k in KEEP})
                for K in (4, 6, 8) for st in (1.5, 2.5, 4.0) for tpa in (1.0, 2.0, 3.0) for dc in (1.0, 0.7)]
        r = pd.DataFrame(rows).sort_values("pf", ascending=False); r.to_csv("dyn_grid_train.csv", index=False); print(r.head(20).to_string(index=False)); print("...worst 5"); print(r.tail(5).to_string(index=False)); sys.exit()
    kw = {k: (int(v) if k == "K" else float(v)) for k, v in (a.split("=") for a in sys.argv[1:])}
    for label, extra in (("pick (cost 0.25)", {}), ("cost 0.6", dict(cost=.6)), ("zero cost", dict(cost=0)), ("control: with the push", dict(flip=True)), ("no reversal-bar confirm", dict(confirm=False))):
        for n, part in sets.items():
            t, dd = run(part, P(**{**kw, **extra})); print(f"{label:<24} {n:<7}", {k: float(v) for k, v in stats(t, dd).items() if k in KEEP})
            if not extra and n != "TRAIN": print("   exits:", t.why.value_counts().to_dict(), "| clips:", t.clips.value_counts().sort_index().to_dict())
            if not extra and n == "LAST2W":
                print(dd.assign(baskets=t.groupby("day").size(), wins=t[t.pnl > 0].groupby("day").size(), clips=t.groupby("day").clips.sum()).fillna(0).round(2).to_string())
