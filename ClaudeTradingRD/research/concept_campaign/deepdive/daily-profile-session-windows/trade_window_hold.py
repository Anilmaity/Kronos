"""Deep-dive 3: the most literal trade of the claim. If the day's low (high) so far was
printed INSIDE the window and the other extreme was not, then at the window's end bet that
it is THE day low (high): long (short) at the next M1 open, stop = that extreme -/+ 0.25*ATR14(15m),
target 1R or 2R, exit by 16:45 NY. Structural control = the identical rule at every other
window placement (same length, ending on each other NY hour 21:00..14:00) -- every arm has
its stop behind a freshly-made day extreme of the same kind. Cost 0.30 pt/trade; 50/50 ties.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "ledger_deepdive.jsonl")
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

SPREAD = 0.30
rng = np.random.default_rng(11)
m1 = cl.load_m1(); idx = m1.index
td = np.asarray(cl.trading_day(idx, 18))
msr = (np.asarray(cl.ny_minute_of_day(idx)) - 1080) % 1440
df = pd.DataFrame({"td": td, "h": m1.high.to_numpy(), "l": m1.low.to_numpy(), "msr": msr, "t": idx})
cnt = df.groupby("td").size(); df = df[df.td.isin(cnt[cnt >= 600].index)]
b15 = cl.bars("15min").copy()
trr = np.maximum(b15.high - b15.low, np.maximum((b15.high - b15.close.shift()).abs(), (b15.low - b15.close.shift()).abs()))
b15["atr"] = trr.rolling(14).mean()
day0 = df.groupby("td").t.min()   # first bar of each trading day


def events(end, L):
    sub = df[df.msr < end]
    g = sub.groupby("td")
    ih, il = g.h.idxmax(), g.l.idxmin()
    mh, ml = sub.msr.loc[ih].to_numpy(), sub.msr.loc[il].to_numpy()
    hin = (mh >= end - L); lin = (ml >= end - L)
    d = np.where(lin & ~hin, 1, np.where(hin & ~lin, -1, 0))
    tdays = g.size().index
    # decision = the day's 18:00 open + end minutes
    dec = pd.DatetimeIndex(day0.loc[tdays]).tz_convert("America/New_York")
    base = dec.normalize() + pd.Timedelta(hours=18)
    base = base.where(dec.hour >= 17, base - pd.Timedelta(days=1))
    dec = (base.tz_localize(None) + pd.to_timedelta(end, unit="m")).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    exit_ = (base.tz_localize(None) + pd.to_timedelta(1365, unit="m")).tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    atr = cl.asof(b15, dec)["atr"].to_numpy()
    lvl = np.where(d > 0, sub.l.loc[il].to_numpy(), sub.h.loc[ih].to_numpy())
    e = pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": d,
                      "stop_px": lvl - d * 0.25 * atr, "max_hold": exit_ - dec, "td": np.asarray(tdays)})
    e = e[(e.direction != 0) & np.isfinite(e.stop_px) & e.decision_time.notna() & e.max_hold.notna()]
    mk = cl.get_market()
    p = np.clip(mk.pos_at_or_after(pd.DatetimeIndex(e.decision_time)), 0, len(mk.o) - 1)
    ent = mk.o[p]
    e = e[(e.direction.to_numpy() * (ent - e.stop_px.to_numpy()) > 0)]
    return e.reset_index(drop=True)


rows = []
res = {}
for L in (180, 210):
    for endh in list(range(21, 24)) + list(range(0, 15)):
        end = ((endh * 60) - 1080) % 1440
        if end - L < 0:
            continue
        ev = events(end, L)
        if len(ev) < 30:
            print("skip", L, endh, len(ev)); continue
        for rr in (1.0, 2.0):
            r = cl.trade_test(ev.drop(columns=["td"]).assign(rr=rr), cost=SPREAD, keep_trades=True, n_boot=200)
            t = r["_trades"]
            concept = (L == 180 and endh == 5) or (L == 210 and endh == 12)
            rows.append(dict(L=L, end_ny=endh, rr=rr, concept=concept, n=len(t), gross=t.gross_R.mean(),
                             net=t.net_R.mean(), net5050=t.net_R_5050.mean(), vs_rand=(t.net_R - t.ctrl_mean_R).mean(),
                             cost_R=(SPREAD / t.risk).mean(), risk_med=t.risk.median(),
                             H1=t.net_R[pd.DatetimeIndex(t.decision_time) < pd.Timestamp("2021-01-01", tz="UTC")].mean(),
                             H2=t.net_R[pd.DatetimeIndex(t.decision_time) >= pd.Timestamp("2021-01-01", tz="UTC")].mean()))
R = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(R.round(3).to_string())
for L, eh in ((180, 5), (210, 12)):
    for rr in (1.0, 2.0):
        s = R[(R.L == L) & (R.rr == rr)]
        c = s[s.end_ny == eh].iloc[0]
        others = s[s.end_ny != eh]
        rank = (others.gross >= c.gross).sum()
        print(f"L={L} end {eh:02d}:00 rr={rr:g}: concept gross {c.gross:+.3f} net {c.net:+.3f} | placebo placements gross mean "
              f"{others.gross.mean():+.3f} sd {others.gross.std():.3f}; {rank}/{len(others)} placebos >= concept; "
              f"z={(c.gross-others.gross.mean())/others.gross.std():+.2f}")
R.to_csv(os.path.join(HERE, "trade_window_hold.csv"), index=False)
