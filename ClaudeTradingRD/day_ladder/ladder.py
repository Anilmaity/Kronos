"""Day-Ladder gold scalper — lab backtest (closed M1 bars, fill at next open, stop-before-target inside a bar).

Idea (operator's): the entry is ordinary; the strategy is the risk ladder around it.
  entry    with the trend (close vs EMA240 of M1), after a 5-min pullback of >= PULL x ATR30, active hours only
  basket   up to 3 legs (40/30/30 %) at 0, S/3, 2S/3 against; ONE hard stop at S; size so a full stop = risk budget
  target   S/3 beyond the average entry  -> high win rate by construction
  ladder   risk % steps down as the day's profit builds; day floor -2.5 %; after +6 % the floor trails the peak
           (run=True) or the day ends (run=False); week +18 % and month +60 % caps; risk % shrinks as equity grows
  flat     before the 08:30 / 10:00 New York releases and at 20:50 UTC
ponytail: news = fixed daily New York windows, not a calendar; add a real calendar if this goes live.
"""
import sys
from dataclasses import dataclass
import numpy as np, pandas as pd
from data import load_m1, atr

@dataclass
class P:
    start: float = 10_000.0
    base_pct: float = 1.0          # risk per basket, % of equity, before the ladder
    day_floor: float = -2.5        # stop for the day here (% of day-start equity)
    day_target: float = 6.0
    giveback: float = 2.0          # after the target, floor = peak - giveback
    run: bool = True               # keep trading past the target behind the trailing floor
    week_cap: float = 18.0
    month_cap: float = 60.0
    s_atr: float = 6.0             # stop distance in ATR30, clamped to [s_min, s_max] points
    s_min: float = 6.0
    s_max: float = 30.0
    tp_frac: float = 1 / 3         # target as a fraction of the stop distance
    pull: float = 1.5              # pullback size in ATR30 over 5 closed minutes
    max_hold: int = 60             # minutes
    cost: float = 0.6              # round-trip spread in points
    hours: tuple = (0, 1, 2, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17)   # TRAIN median hourly range >= 14 pts
    flip: bool = False             # control: trade against the trend instead
    mode: str = "protect"          # protect: risk steps DOWN as the day's profit builds
                                   # press:   base risk + press x (today's profit), floor trails the day's peak
    press: float = 0.3
    trail: float = 4.0             # press mode: floor = peak - trail (a +4 % day can no longer end red)
    max_pct: float = 3.0           # never risk more than this % on one basket
W = (0.4, 0.3, 0.3)

def prep(d):
    d = d.copy(); d["atr"] = atr(d, 30); d["ema"] = d.close.ewm(span=240, adjust=False).mean()
    d["r5"] = d.close - d.close.shift(5)
    ny = d.index.tz_convert("America/New_York"); m = ny.hour * 60 + ny.minute
    d["news"] = ((m >= 8 * 60 + 25) & (m < 8 * 60 + 45)) | ((m >= 9 * 60 + 55) & (m < 10 * 60 + 10))
    d["gap"] = d.index.to_series().diff().dt.total_seconds().fillna(60) > 90
    return d.dropna()

def run(d, p=P()):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    A, E, R5, news, gap = d.atr.to_numpy(), d.ema.to_numpy(), d.r5.to_numpy(), d.news.to_numpy(), d.gap.to_numpy()
    idx = d.index; hr = idx.hour.to_numpy(); mn = hr * 60 + idx.minute.to_numpy()
    day = idx.strftime("%Y-%m-%d").to_numpy(); wk = idx.strftime("%G-%V").to_numpy(); mo = idx.strftime("%Y-%m").to_numpy()
    hs = p.cost / 2; hours = set(p.hours)
    eq = p.start; d0 = w0 = m0 = eq; peak = 0.0; halted = False
    b = None; trades = []; days = {}
    for i in range(len(c) - 1):
        if i == 0 or day[i] != day[i - 1]:
            d0 = eq; peak = 0.0; halted = False
            if i == 0 or wk[i] != wk[i - 1]: w0 = eq
            if i == 0 or mo[i] != mo[i - 1]: m0 = eq
        if b:                                               # manage the open basket on bar i
            s = b["s"]; px = None
            stop_hit = (l[i] - hs <= b["stop"]) if s > 0 else (h[i] + hs >= b["stop"])
            if stop_hit:
                gapped = (o[i] - hs <= b["stop"]) if s > 0 else (o[i] + hs >= b["stop"])
                px, why = ((o[i] - s * hs) if gapped else b["stop"]), "stop"
            else:
                added = False
                while b["n"] < 3 and ((l[i] + hs <= b["lv"][b["n"]]) if s > 0 else (h[i] - hs >= b["lv"][b["n"]])):
                    k = b["n"]; b["fills"].append((b["lv"][k], b["lots"][k])); b["n"] += 1; added = True
                if added:
                    lots = sum(q for _, q in b["fills"]); avg = sum(x * q for x, q in b["fills"]) / lots
                    b["tp"] = avg + s * b["T"]
                elif (h[i] - hs >= b["tp"]) if s > 0 else (l[i] + hs <= b["tp"]):
                    px, why = b["tp"], "tp"
                if px is None and (i - b["i"] >= p.max_hold or news[i] or mn[i] >= 20 * 60 + 50 or gap[i + 1]):
                    px, why = c[i] - s * hs, "time/flat"
            if px is not None:
                pnl = sum((px - x) * s * q * 100 for x, q in b["fills"])
                eq += pnl; trades.append(dict(t=idx[b["i"]], day=day[b["i"]], side=s, legs=b["n"], pnl=pnl, why=why,
                                             risk=b["risk"], mins=i - b["i"])); b = None
        dp = (eq / d0 - 1) * 100; peak = max(peak, dp)
        floor = p.day_floor if peak < p.day_target else max(p.day_floor, peak - p.giveback)
        if p.mode == "press": floor = max(floor, peak - p.trail)
        if dp <= floor or (peak >= p.day_target and not p.run): halted = True
        if (eq / w0 - 1) * 100 >= p.week_cap or (eq / m0 - 1) * 100 >= p.month_cap: halted = True
        days[day[i]] = (d0, eq)
        if b or halted or hr[i] not in hours or news[i] or gap[i + 1] or mn[i] >= 20 * 60: continue
        trend = 1 if c[i] > E[i] else -1
        if p.flip: trend = -trend
        if R5[i] * trend > -p.pull * A[i]: continue                      # need a pullback against the trend
        if p.mode == "press":                                            # risk today's winnings, never the floor
            pct = min(p.max_pct, p.base_pct * min(1.0, p.start / eq) + p.press * max(dp, 0.0))
        else:
            step = 1.0 if dp < 2 else 0.75 if dp < 4 else 0.5           # less risk as the day's profit builds
            pct = p.base_pct * step * min(1.0, p.start / eq)            # and a smaller % as the account grows
        room = (dp - floor) / 100 * d0                                   # never risk past today's floor
        risk = min(eq * pct / 100, room)
        if risk < d0 * 0.0025: halted = True; continue
        S = float(np.clip(p.s_atr * A[i], p.s_min, p.s_max)); e = o[i + 1] + trend * hs
        total = risk / ((W[0] + W[1] * 2 / 3 + W[2] / 3) * S * 100)
        lots = [round(total * w, 2) for w in W]
        if lots[0] < 0.01: continue
        b = dict(s=trend, i=i + 1, stop=e - trend * S, T=S * p.tp_frac, tp=e + trend * S * p.tp_frac, n=1, risk=risk,
                 lv=[e, e - trend * S / 3, e - trend * 2 * S / 3], lots=lots, fills=[(e, lots[0])])
    t = pd.DataFrame(trades); dd = pd.DataFrame(days, index=["start", "end"]).T
    dd["pct"] = (dd.end / dd.start - 1) * 100
    return t, dd, eq

def report(name, t, dd, p):
    n = t.groupby("day").size().reindex(dd.index).fillna(0); a = dd[n > 0]
    w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
    print(f"{name:<34} days {len(a):>3} | trades {len(t):>5} ({len(t)/max(len(a),1):.0f}/day) | win {len(w)/max(len(t),1):.1%} | PF {w.sum()/max(-lo.sum(),1e-9):.2f} | "
          f"day%: mean {a.pct.mean():+.2f} worst {a.pct.min():+.2f} best {a.pct.max():+.2f} | days>=+6% {(a.pct>=p.day_target).mean():.0%} | days<0 {(a.pct<0).mean():.0%} | "
          f"total {((dd.end.iloc[-1]/dd.start.iloc[0])-1)*100:+.1f}%")

if __name__ == "__main__":
    d = prep(load_m1()); dates = np.unique(d.index.date); cut = pd.Timestamp(dates[int(len(dates) * .6)], tz="UTC")
    train, test = d[d.index < cut], d[d.index >= cut]
    last = d[d.index >= d.index[-1] - pd.Timedelta(days=14)]
    if "grid" in sys.argv:                                   # choose on TRAIN only
        for base in (1.0, 1.25):
            for press in (0.5, 1.0):
                for S in (6.0, 12.0):
                    for pull in (1.0, 1.5):
                        p = P(mode="press", base_pct=base, press=press, s_atr=S, s_min=S, pull=pull, max_hold=180)
                        t, dd, _ = run(train, p); report(f"b{base} pr{press} S{S:.0f} pull{pull} | TRAIN", t, dd, p)
        sys.exit()
    # chosen on TRAIN (see README): press ladder
    PICK = dict(mode="press", max_hold=180, **{k: float(v) for k, v in (a.split("=") for a in sys.argv[1:])})
    if "s_atr" in PICK: PICK["s_min"] = PICK["s_atr"]
    for label, p in (("pick, cost 0.6", P(**PICK)), ("pick, cost 0.9", P(cost=.9, **PICK)),
                     ("control: against trend", P(flip=True, **PICK)), ("zero cost", P(cost=0, **PICK))):
        for sname, part in (("TRAIN", train), ("TEST", test), ("LAST 2 WEEKS", last)):
            t, dd, eq = run(part, p); report(f"{label} | {sname}", t, dd, p)
            if label == "pick, cost 0.6":
                t.to_csv(f"trades_{sname.replace(' ', '_')}.csv", index=False); dd.to_csv(f"days_{sname.replace(' ', '_')}.csv")
                if sname == "LAST 2 WEEKS":
                    print(dd.assign(trades=t.groupby("day").size(), wins=t[t.pnl > 0].groupby("day").size()).fillna(0).round(2).to_string())
                    print("exit mix:", t.why.value_counts().to_dict(), "| legs:", t.legs.value_counts().sort_index().to_dict(), "| median hold min:", t.mins.median())
        print()
