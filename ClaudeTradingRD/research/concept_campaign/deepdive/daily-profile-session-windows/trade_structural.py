"""Deep-dive 2: can "day extremes form in London 02-05 / NY 08:30-12" be TRADED, and does
it beat a STRUCTURE-matched control?

Book A (tf in {5min, 15min}): FADE a fresh day extreme. A bar whose low breaks the running
trading-day low (day >= 60 min old) -> long at next M1 open, stop = bar low - 0.25*ATR14,
target rr in {1,2}, max_hold 4h (shorts mirrored). gate in_win = bar started inside a window.
Structural control (per event, 3 draws): random bar close within +/-30 days, NY time-of-day
within +/-30 min of the event (so window events get window-timed controls), RANDOM
direction, stop beyond the extreme of the last k in {1,2,3} bars (+0.25*ATR), k picked to
match the event's stop distance, same rr, same hold.
Every arm is costed at 0.30 pt of spread per trade (net_R = gross - 0.30/risk), and also
re-scored with ambiguous same-bar exits as 50/50.
Harness used for bars + M1 resolution + its own random-entry control (ledger redirected to
this folder; nothing written to results/).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "ledger_deepdive.jsonl")
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

SPREAD = 0.30
W = [("02:00", "05:00"), ("08:30", "12:00")]
rng = np.random.default_rng(20260923)
m1 = cl.load_m1()


def fade_events(tf, grid4h="forex"):
    b = cl.bars(tf, grid4h=grid4h).copy()
    tr = np.maximum(b.high - b.low, np.maximum((b.high - b.close.shift()).abs(), (b.low - b.close.shift()).abs()))
    b["atr"] = tr.rolling(14).mean()
    b["td"] = np.asarray(cl.trading_day(b.index, 18))
    g = b.groupby("td")
    b["plo"] = g.low.transform(lambda s: s.cummin().shift())
    b["phi"] = g.high.transform(lambda s: s.cummax().shift())
    b["age"] = g.cumcount()
    per_hr = pd.Timedelta("60min") // pd.Timedelta(cl.data.tf_delta(tf))
    ok = (b.age >= per_hr) & b.atr.notna()
    nl = ok & (b.low < b.plo); nh = ok & (b.high > b.phi)
    both = nl & nh
    nl &= ~both; nh &= ~both
    ev = b[nl | nh].copy()
    ev["direction"] = np.where(nl[nl | nh], 1, -1)
    ev["stop_px"] = np.where(ev.direction > 0, ev.low - 0.25 * ev.atr, ev.high + 0.25 * ev.atr)
    inw = np.zeros(len(ev), bool)
    for a, z in W:
        inw |= cl.in_window(ev.index, a, z)
    out = pd.DataFrame({"decision_time": pd.DatetimeIndex(ev.close_time), "available_at": pd.DatetimeIndex(ev.close_time),
                        "direction": ev.direction.to_numpy(), "stop_px": ev.stop_px.to_numpy(), "in_win": inw,
                        "td": ev.td.to_numpy()})
    return out.reset_index(drop=True), b


def struct_controls(ev, b, reps=3):
    """random-direction entries, timing matched (+/-30 d, NY tod +/-30 min), stop beyond the
    last-k-bar extreme (k=1..3) chosen to match the event's stop distance."""
    ct = pd.DatetimeIndex(b.close_time)
    ctn = ct.as_unit("ns").asi8
    nymod = np.asarray(cl.ny_minute_of_day(ct))
    lo_k = [b.low.rolling(k).min().to_numpy() for k in (1, 2, 3)]
    hi_k = [b.high.rolling(k).max().to_numpy() for k in (1, 2, 3)]
    atr = b.atr.to_numpy()
    # next M1 open after each bar close = approx entry for distance matching
    mk = cl.get_market()
    pos = mk.pos_at_or_after(ct); pos = np.clip(pos, 0, len(mk.o) - 1)
    entry = mk.o[pos]
    dt = ev.decision_time.dt.tz_convert("UTC").astype("datetime64[ns, UTC]")
    evn = pd.DatetimeIndex(dt).as_unit("ns").asi8
    evmod = np.asarray(cl.ny_minute_of_day(pd.DatetimeIndex(dt)))
    epos = np.clip(mk.pos_at_or_after(pd.DatetimeIndex(dt)), 0, len(mk.o) - 1)
    edist = np.abs(mk.o[epos] - ev.stop_px.to_numpy())
    rows = []
    day = 86400 * 10**9
    for i in range(len(ev)):
        lo_i = np.searchsorted(ctn, evn[i] - 30 * day); hi_i = np.searchsorted(ctn, evn[i] + 30 * day)
        cand = np.arange(lo_i, hi_i)
        dm = np.abs(((nymod[cand] - evmod[i]) + 720) % 1440 - 720)
        cand = cand[(dm <= 30) & np.isfinite(atr[cand])]
        if len(cand) == 0:
            continue
        pick = rng.choice(cand, size=reps)
        for j in pick:
            s = rng.choice([-1, 1])
            if s > 0:
                st = np.array([lo_k[k][j] for k in range(3)]) - 0.25 * atr[j]
            else:
                st = np.array([hi_k[k][j] for k in range(3)]) + 0.25 * atr[j]
            dist = np.abs(entry[j] - st)
            valid = np.isfinite(st) & (s * (entry[j] - st) > 0)
            if not valid.any():
                continue
            kk = np.argmin(np.where(valid, np.abs(dist - edist[i]), np.inf))
            rows.append((ct[j], s, st[kk], ev.in_win.iat[i], i, dist[kk], edist[i]))
    c = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "in_win", "src", "dist", "edist"])
    c["available_at"] = c.decision_time
    return c


def run_book(ev, rr, hold):
    e = ev.assign(rr=rr)
    r = cl.trade_test(e, max_hold=hold, cost=SPREAD, keep_trades=True, n_boot=200)
    t = r["_trades"]
    return r, t


def dayboot(x, days, n=2000):
    df = pd.DataFrame({"x": x, "d": days}).dropna()
    gs = df.groupby("d").x.agg(["sum", "count"])
    s, c = gs["sum"].to_numpy(), gs["count"].to_numpy()
    k = len(s); out = np.empty(n)
    for b_ in range(n):
        ii = rng.integers(0, k, k); out[b_] = s[ii].sum() / c[ii].sum()
    return np.percentile(out, [2.5, 97.5])


def diffboot(a, da, b, db, n=2000):
    A = pd.DataFrame({"x": a, "d": da}).groupby("d").x.agg(["sum", "count"])
    B = pd.DataFrame({"x": b, "d": db}).groupby("d").x.agg(["sum", "count"])
    alld = A.index.union(B.index)
    A = A.reindex(alld, fill_value=0); B = B.reindex(alld, fill_value=0)
    out = np.empty(n); k = len(alld)
    for b_ in range(n):
        ii = rng.integers(0, k, k)
        out[b_] = A["sum"].to_numpy()[ii].sum() / max(A["count"].to_numpy()[ii].sum(), 1) - \
                  B["sum"].to_numpy()[ii].sum() / max(B["count"].to_numpy()[ii].sum(), 1)
    return np.percentile(out, [2.5, 97.5])


summary = {}
for tf in ("5min", "15min"):
    ev, b = fade_events(tf)
    sc = struct_controls(ev, b)
    tdc = np.asarray(cl.trading_day(pd.DatetimeIndex(sc.decision_time), 18))
    print(f"\n=== {tf} fade-fresh-day-extreme: n={len(ev)} in-window {ev.in_win.mean():.1%}; struct ctrl n={len(sc)}; "
          f"median stop dist ev {sc.groupby('src').edist.first().median():.2f} ctrl {sc.dist.median():.2f}")
    for rr in (1.0, 2.0):
        r, t = run_book(ev, rr, "4h")
        rc, tc = run_book(sc[["decision_time", "available_at", "direction", "stop_px"]], rr, "4h")
        t = t.merge(ev[["in_win", "td"]], left_on="ev_id", right_index=True, how="left") if "ev_id" in t else t
        tc = tc.assign(in_win=sc.in_win.to_numpy()[tc.ev_id.to_numpy()], td=tdc[tc.ev_id.to_numpy()])
        for arm in (True, False):
            a = t[t.in_win == arm]; c = tc[tc.in_win == arm]
            key = f"{tf}_rr{rr:g}_{'WIN' if arm else 'OUT'}"
            gr = a.gross_R.mean(); nr = a.net_R.mean(); n5 = a.net_R_5050.mean()
            cn = c.net_R.mean(); c5 = c.net_R_5050.mean()
            dlo, dhi = diffboot(a.net_R.to_numpy(), a.td.to_numpy(), c.net_R.to_numpy(), c.td.to_numpy())
            rnd = (a.net_R - a.ctrl_mean_R).mean()
            cost_R = (SPREAD / a.risk).mean()
            h1 = pd.DatetimeIndex(a.decision_time) < pd.Timestamp("2021-01-01", tz="UTC")
            h1c = pd.DatetimeIndex(c.decision_time) < pd.Timestamp("2021-01-01", tz="UTC")
            blk = np.array_split(np.argsort(pd.DatetimeIndex(a.decision_time).asi8), 4)
            blkc = np.array_split(np.argsort(pd.DatetimeIndex(c.decision_time).asi8), 4)
            bdiff = [round(a.net_R.to_numpy()[x].mean() - c.net_R.to_numpy()[y].mean(), 3) for x, y in zip(blk, blkc)]
            summary[key] = dict(n=len(a), gross=gr, net=nr, net5050=n5, struct_ctrl_net=cn, struct_ctrl_net5050=c5,
                                vs_struct=nr - cn, vs_struct_ci=[dlo, dhi], vs_struct_5050=n5 - c5,
                                vs_random_ctrl=rnd, cost_R=cost_R, median_risk=a.risk.median(),
                                ties_real=a.tie.mean(), ties_ctrl=c.tie.mean(),
                                H1_vs_struct=a.net_R[h1].mean() - c.net_R[h1c].mean(),
                                H2_vs_struct=a.net_R[~h1].mean() - c.net_R[~h1c].mean(), blocks_vs_struct=bdiff)
            s = summary[key]
            print(f"{key:18s} n={s['n']:6d} gross {gr:+.3f} net {nr:+.3f} (cost {cost_R:.3f}R, risk med {s['median_risk']:.2f}) "
                  f"| struct ctrl net {cn:+.3f} -> diff {nr-cn:+.3f} [{dlo:+.3f},{dhi:+.3f}] 50/50 diff {n5-c5:+.3f} "
                  f"| vs random-entry ctrl {rnd:+.3f} | H1 {s['H1_vs_struct']:+.3f} H2 {s['H2_vs_struct']:+.3f} blocks {bdiff} "
                  f"| ties {s['ties_real']:.3f}/{s['ties_ctrl']:.3f}")
        # gate: window vs outside, both structure-placed (harness gate_test, random-entry control)
        g = cl.gate_test(ev.assign(rr=rr), "in_win", mask_available_at="decision_time", max_hold="4h",
                         cost=SPREAD, n_boot=500)
        print(f"   gate_test in_win vs out (ctrl-adjusted): diff {g['diff']:+.4f} [{g['ci_lo']:+.4f},{g['ci_hi']:+.4f}] "
              f"verdict {g['verdict']} ties {g.get('ties',{}).get('verdict_5050')}")
        summary[f"{tf}_rr{rr:g}_gate"] = dict(diff=g["diff"], ci=[g["ci_lo"], g["ci_hi"]], verdict=g["verdict"])

json.dump(summary, open(os.path.join(HERE, "trade_structural.json"), "w"), indent=1, default=float)
