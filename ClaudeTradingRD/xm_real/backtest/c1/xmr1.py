#!/usr/bin/env python
"""XMR-1 "deposit-as-stop averaging fade" - standalone event-driven M1 backtester.

Implements analysis/STRATEGY_SPEC.md sections 5 (common framework) and 6 (Candidate 1) exactly as pre-registered.
It is a RISK EXHIBIT, not a deployment candidate: no stop-loss, the margin stop-out of a 200 USD account is the only loss exit.

Run (deterministic, fixed seeds; about one minute on 12 processes; writes results/):
    ../../../.venv/bin/python xmr1.py            # every step
    ../../../.venv/bin/python xmr1.py selftest   # engine self-check + look-ahead asserts only
    ../../../.venv/bin/python xmr1.py qa|null|grid|shadow|control|ruin|week|secondary
Then: ../../../.venv/bin/python report.py        # REPORT.md + PNGs from results/

Money: 1 lot = 100 oz, so 0.04 lots = 4 USD per point (1 point = 1 USD per oz). All times UTC.
"""
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # xm_real/
RD = ROOT.parent                            # ClaudeTradingRD/
OUT = HERE / "results"

# ---- fixed parameters (spec 6.3) -------------------------------------------------------------------------------------
CLIP, FRESH_CLIPS, N_MAX = 0.04, 2, 10
K_FADE, MIN_ATR5, K_STEP, STEP_FLOOR, TP_FLOOR = 0.6, 3.0, 0.7, 2.0, 3.0
DEPOSIT, LEVERAGE, SO_LEVEL, REDEP_MIN = 200.0, 1000, 0.20, 60
U = 100 * CLIP                              # USD per point per clip
MARG_K = CLIP * 100 / LEVERAGE              # margin per net clip per USD of gold price
GRID = [(tp, mode, sw) for tp in (1.0, 2.5) for mode in ("per_leg", "shared_first") for sw in (True, False)]  # default first
STITCH = pd.Timestamp("2026-07-16", tz="UTC")
W = {"TRAIN": ("2025-07-16", "2026-04-01"), "TEST": ("2026-04-01", "2026-11-04"), "WEEK": ("2026-11-04", "2026-11-12")}
COSTS = ["base", "stress", 0.45, 0.80]      # spec base / stress, plus flat round-trip points on the mid (house convention)
NPROC = min(12, mp.cpu_count())


# ---- data ------------------------------------------------------------------------------------------------------------
def load_main():
    """OANDA M1 mid to 2026-07-15, then OANDA M1 bid/ask. ~16 months."""
    a = pd.read_parquet(RD / "xau_m1_oanda.parquet")
    b = pd.read_parquet(ROOT / "xau_m1_2026-07-16_now_mba.parquet").drop(columns="volume")
    df = pd.concat([a[a.time < STITCH], b], ignore_index=True)
    assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
    return df


def load_secondary():
    """Long mid-only history, secondary window 2019-01-01 .. 2025-07-15 (quality: see qa())."""
    f = pd.read_parquet(RD / "m3_scalper/xau_m1_full.parquet")
    return f[(f.time >= "2019-01-01") & (f.time < "2025-07-16")].reset_index(drop=True)


def quotes(df, cost):
    """XM bid/ask OHLC under a cost mode. base/stress = spec 5.2; float = flat round-trip pts on mid; ('bp', x) = x bp of price."""
    q = df.bid_close.notna().to_numpy() if "bid_close" in df else np.zeros(len(df), bool)
    out = {}
    for x in ("open", "high", "low", "close"):
        mid = df[x].to_numpy()
        if cost in ("base", "stress"):
            hm, ex = (0.30, 0.0) if cost == "base" else (0.50, 0.20)
            bid = np.where(q, df[f"bid_{x}"].to_numpy() - 0.05 - ex, mid - hm) if q.any() else mid - hm
            ask = np.where(q, df[f"ask_{x}"].to_numpy() + 0.06 + ex, mid + hm) if q.any() else mid + hm
        else:
            half = cost / 2 if not isinstance(cost, tuple) else df.close.to_numpy() * cost[1] * 1e-4 / 2
            bid, ask = mid - half, mid + half
        out["b" + x[0]], out["a" + x[0]] = bid, ask
    out["mid"] = df.close.to_numpy()
    return out


def indicators(df):
    """Spec 5.3 on the signal series (bid; constant offsets cancel). CLOSED bars only. Returns numpy arrays."""
    t = df.time
    if "bid_close" in df:
        q = df.bid_close.notna().to_numpy()
        sh, sl, sc = (np.where(q, df[f"bid_{x}"].to_numpy() - 0.05, df[x].to_numpy() - 0.30) for x in ("high", "low", "close"))
    else:
        sh, sl, sc = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    s = pd.DataFrame({"h": sh, "l": sl, "c": sc})
    m5 = s.groupby(t.dt.floor("5min").to_numpy()).agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
    pc = m5.c.shift()
    tr = np.maximum(m5.h - m5.l, np.maximum((m5.h - pc).abs(), (m5.l - pc).abs()))
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    atr.iloc[:100] = np.nan                                                    # warm-up
    # an M5 bar opened at T5 is usable at M1 bar t iff T5 + 5 min <= c(t) = t + 1 min  <=>  t >= T5 + 4 min
    avail = pd.DataFrame({"time": m5.index + pd.Timedelta(minutes=4), "atr5": atr.to_numpy(), "src": m5.index})
    avail["time"] = avail.time.astype(t.dtype)
    m = pd.merge_asof(pd.DataFrame({"time": t}), avail, on="time")
    probe = ((m.src.dt.tz_localize("UTC") if m.src.dt.tz is None else m.src) + pd.Timedelta(minutes=5)) - (t + pd.Timedelta(minutes=1))
    assert not (probe.dropna() > pd.Timedelta(0)).any(), "closed-bar probe failed: an M5 bar in progress was used"
    a5 = m.atr5.to_numpy()
    ret5 = s.c - s.c.shift(5)
    hi, lo = s.h.rolling(15).max(), s.l.rolling(15).min()
    pos15 = ((s.c - lo) / (hi - lo).where(hi > lo)).to_numpy()
    ok = ((t - t.shift(14)) <= pd.Timedelta(minutes=30)).to_numpy()            # gap guard
    elig = ok & ~np.isnan(a5) & (a5 >= MIN_ATR5)
    with np.errstate(invalid="ignore"):
        sell = elig & (ret5.to_numpy() >= K_FADE * a5) & (pos15 >= 2 / 3)
        buy = elig & (ret5.to_numpy() <= -K_FADE * a5) & (pos15 <= 1 / 3)
    ct = t + pd.Timedelta(minutes=1)                                           # c(t)
    sess = ((ct.dt.hour >= 1) & (ct.dt.hour < 21) & (ct.dt.dayofweek < 5)).to_numpy()
    tmin = (t.astype("int64") // 60_000_000_000).to_numpy() if str(t.dtype).startswith("datetime64[ns") else \
        (t.astype("datetime64[ns, UTC]").astype("int64") // 60_000_000_000).to_numpy()
    return dict(atr=a5, sell=sell, buy=buy, sess=sess, elig=elig, tmin=tmin, day=tmin // 1440,
                bucket=((ct.dt.year * 12 + ct.dt.month) * 24 + ct.dt.hour).to_numpy(), probe_max_s=probe.dropna().max().total_seconds())


def as_lists(ind, q):
    d = {k: v.tolist() for k, v in q.items()}
    d.update({k: ind[k].tolist() for k in ("atr", "sess", "tmin", "day")})
    return d


def random_signals(ind, seed):
    """Control: each side's trigger permuted among eligible in-session bars inside (calendar month, UTC hour) buckets,
    so the firing rate per hour and month is exact and the volatility/price regime is matched. No directional content."""
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(ind["elig"] & ind["sess"])
    _, inv = np.unique(ind["bucket"][idx], return_inverse=True)
    starts = np.r_[0, np.cumsum(np.bincount(inv))[:-1]]
    out = []
    for sig in (ind["sell"], ind["buy"]):
        ntrue = np.bincount(inv, weights=sig[idx]).astype(int)
        order = np.lexsort((rng.random(len(idx)), inv))
        rank = np.arange(len(idx)) - starts[inv[order]]
        r = np.zeros(len(sig), bool)
        r[idx[order]] = rank < ntrue[inv[order]]
        out.append(r.tolist())
    return out


# ---- engine ----------------------------------------------------------------------------------------------------------
def simulate(D, i0, i1, sell, buy, tp_atr=1.0, mode="per_leg", sweep=True, deposit=DEPOSIT,
             shadow=False, redeposit=True, fine=None, curve=False):
    """One account over bars [i0, i1). Per bar: (1) fill orders decided at the previous close at this OPEN,
    (2) margin stop-out on the bar's worst-case equity, (3) take-profits, (4) at the CLOSE: sweep / re-deposit / decisions.
    fine=(bid_low, bid_high, ask_low, ask_high, f0, f1) resolves steps 2-3 on sub-bars f0[i]..f1[i] (S5) instead of the M1 bar.
    shadow=True: unlimited balance - no stop-out, no margin rule; tracks the floating loss the stop-out hides."""
    bo, bc, ao, ac, mid, atr, sess, tmin, day = (D[k] for k in ("bo", "bc", "ao", "ac", "mid", "atr", "sess", "tmin", "day"))
    if fine is None:
        fl, fh, gl, gh = D["bl"], D["bh"], D["al"], D["ah"]
    else:
        fl, fh, gl, gh, f0, f1 = fine
    shared, INF = mode == "shared_first", float("inf")
    bal, dep, wd = float(deposit), float(deposit), 0.0
    L, S, nL, nS, sumL, sumS, mnL, mxS = [], [], 0, 0, 0.0, 0.0, INF, -INF   # books: (entry, tp, open_idx); mnL/mxS = nearest TP
    pL = pS = None                                                           # pending order: (clips, tp distance, signal idx)
    waiting, wipe_until = False, 0
    trades, wipes, cash, days, eq = [], [], [(i0, "dep", deposit)], [], []          # trades: (side, open_i, close_i, entry, exit, reason 0 TP/1 SO/2 EOW)
    flat = hedged = full = maxpos = maxnet = rejected = 0
    worst_float, worst_i, worst_adv, absorbed, forfeited = 0.0, -1, 0.0, 0.0, 0.0
    cur_day = day[i0]
    for i in range(i0, i1):
        if day[i] != cur_day:
            j = i - 1
            days.append((cur_day, wd - dep + bal + U * ((bc[j] * nL - sumL) + (sumS - ac[j] * nS))))
            cur_day = day[i]
        # (1) fills at this bar's open
        if pL is not None:
            k, dd, si = pL
            pL = None
            assert i > si, "entry bar must be strictly after the signal bar"
            px = ao[i]
            tp = L[0][1] if (shared and nL) else px + dd
            L.extend([(px, tp, i)] * k)
            nL += k
            sumL += k * px
            if tp < mnL:
                mnL = tp
        if pS is not None:
            k, dd, si = pS
            pS = None
            assert i > si, "entry bar must be strictly after the signal bar"
            px = bo[i]
            tp = S[0][1] if (shared and nS) else px - dd
            S.extend([(px, tp, i)] * k)
            nS += k
            sumS += k * px
            if tp > mxS:
                mxS = tp
        if nL or nS:
            n_open = nL + nS
            if n_open > maxpos:
                maxpos = n_open
            wiped = False
            for k in ((i,) if fine is None else range(f0[i], f1[i])):
                lb, hb, la, ha = fl[k], fh[k], gl[k], gh[k]
                f_lo = U * ((lb * nL - sumL) + (sumS - la * nS))             # longs at bid_low, shorts at ask_low
                f_hi = U * ((hb * nL - sumL) + (sumS - ha * nS))             # longs at bid_high, shorts at ask_high
                low_side = f_lo <= f_hi
                # (2) stop-out, before any TP in the same (sub-)bar
                if shadow:
                    w = f_lo if low_side else f_hi
                    if w < worst_float:
                        worst_float, worst_i = w, i
                    if nL:
                        adv = max(p[0] for p in L) - lb
                        if adv > worst_adv:
                            worst_adv = adv
                    if nS:
                        adv = ha - min(p[0] for p in S)
                        if adv > worst_adv:
                            worst_adv = adv
                else:
                    emin = bal + (f_lo if low_side else f_hi)
                    net = nL - nS if nL >= nS else nS - nL
                    if net > maxnet:
                        maxnet = net
                    if emin <= SO_LEVEL * net * MARG_K * mid[i]:
                        for p in L:
                            trades.append((1, p[2], i, p[0], lb if low_side else hb, 1))
                        for p in S:
                            trades.append((-1, p[2], i, p[0], la if low_side else ha, 1))
                        wipes.append((i, bal, emin, nL, nS))
                        cash.append((i, "wipe", bal))
                        if emin < 0:
                            absorbed -= emin
                        else:
                            forfeited += emin
                        bal, L, S, nL, nS, sumL, sumS, mnL, mxS = 0.0, [], [], 0, 0, 0.0, 0.0, INF, -INF
                        waiting, wipe_until, wiped = True, tmin[i] + 1 + REDEP_MIN, True
                        break
                # (3) take-profits: long when bid_high >= P, short when ask_low <= P, filled at P
                if hb >= mnL:
                    keep = []
                    for p in L:
                        if hb >= p[1]:
                            bal += (p[1] - p[0]) * U
                            sumL -= p[0]
                            trades.append((1, p[2], i, p[0], p[1], 0))
                        else:
                            keep.append(p)
                    L, nL = keep, len(keep)
                    mnL = min(p[1] for p in L) if nL else INF
                    if not nL:
                        sumL = 0.0
                if la <= mxS:
                    keep = []
                    for p in S:
                        if la <= p[1]:
                            bal += (p[0] - p[1]) * U
                            sumS -= p[0]
                            trades.append((-1, p[2], i, p[0], p[1], 0))
                        else:
                            keep.append(p)
                    S, nS = keep, len(keep)
                    mxS = max(p[1] for p in S) if nS else -INF
                    if not nS:
                        sumS = 0.0
                if not (nL or nS):
                    break
            if wiped:
                flat += 1
                if curve:
                    eq.append(wd - dep)
                if not redeposit:
                    break
                continue
        # (4) bar close
        if nL == 0 and nS == 0:
            flat += 1
            if waiting:
                if redeposit and tmin[i] + 1 >= wipe_until:
                    bal, waiting = float(deposit), False
                    dep += deposit
                    cash.append((i, "dep", deposit))
                else:
                    if curve:
                        eq.append(wd - dep)
                    continue
            elif sweep and bal > deposit:
                wd += bal - deposit
                cash.append((i, "sweep", bal - deposit))
                bal = float(deposit)
        elif nL and nS:
            hedged += 1
        if nL == N_MAX or nS == N_MAX:
            full += 1
        if curve:
            eq.append(wd - dep + bal + U * ((bc[i] * nL - sumL) + (sumS - ac[i] * nS)))
        if sess[i] and i + 1 < i1:
            a = atr[i]
            k = 0
            if nL == 0:
                if buy[i]:
                    k = FRESH_CLIPS
            elif nL < N_MAX and a == a and L[-1][0] - ac[i] >= (K_STEP * a if K_STEP * a > STEP_FLOOR else STEP_FLOOR):
                k = 1
            if k:
                new = nL + k - nS if nL + k >= nS else nS - nL - k
                if shadow or new < (nL - nS if nL >= nS else nS - nL) or \
                        bal + U * ((bc[i] * nL - sumL) + (sumS - ac[i] * nS)) > new * MARG_K * mid[i]:
                    pL = (k, tp_atr * a if tp_atr * a > TP_FLOOR else TP_FLOOR, i)
                else:
                    rejected += 1
            k = 0
            if nS == 0:
                if sell[i]:
                    k = FRESH_CLIPS
            elif nS < N_MAX and a == a and bc[i] - S[-1][0] >= (K_STEP * a if K_STEP * a > STEP_FLOOR else STEP_FLOOR):
                k = 1
            if k:
                new = nS + k - nL if nS + k >= nL else nL - nS - k
                if shadow or new < (nL - nS if nL >= nS else nS - nL) or \
                        bal + U * ((bc[i] * nL - sumL) + (sumS - ac[i] * nS)) > new * MARG_K * mid[i]:
                    pS = (k, tp_atr * a if tp_atr * a > TP_FLOOR else TP_FLOOR, i)
                else:
                    rejected += 1
    last = min(i, i1 - 1)
    for p in L:
        trades.append((1, p[2], last, p[0], bc[last], 2))
    for p in S:
        trades.append((-1, p[2], last, p[0], ac[last], 2))
    final_eq = bal + U * ((bc[last] * nL - sumL) + (sumS - ac[last] * nS))
    days.append((cur_day, wd - dep + final_eq))
    r = dict(dep=dep, wd=wd, final_eq=final_eq, owner=wd + final_eq - dep, trades=trades, wipes=wipes, cash=cash, days=days,
             flat=flat, hedged=hedged, full=full, bars=last - i0 + 1, maxpos=maxpos, maxnet=maxnet, rejected=rejected, absorbed=absorbed,
             forfeited=forfeited, eq=eq, worst_float=worst_float, worst_i=worst_i, worst_adv=worst_adv, i0=i0, last=last)
    if not shadow:                                                          # accounting identity (spec 6.2)
        pnl = sum(s * (x - e) * U for s, _, _, e, x, _ in trades)
        assert abs(r["owner"] - (pnl + absorbed - forfeited)) < 1e-6 * max(1.0, dep), "cash and position P&L disagree"
    return r


def audit(r, D):
    """Independent replay of a run's trade list against the bars (not through the engine's own state)."""
    for side, oi, ci, e, x, why in r["trades"]:
        assert ci >= oi and e == (D["ao"][oi] if side > 0 else D["bo"][oi]), "entry is not the open of its bar"
        if why == 0:
            assert (D["bh"][ci] >= x) if side > 0 else (D["al"][ci] <= x), "TP filled in a bar that never reached it"
        elif why == 1:
            assert x in ((D["bl"][ci], D["bh"][ci]) if side > 0 else (D["al"][ci], D["ah"][ci])), "stop-out mark is not a bar extreme"


def summarize(r, tmin=None):
    """Metrics of one run. Position P&L of stop-out legs is marked at the worst-case price of the stop-out bar."""
    t = np.array(r["trades"], dtype=float).reshape(-1, 6)
    pnl = t[:, 0] * (t[:, 4] - t[:, 3]) * U
    win, loss = pnl[pnl > 0], pnl[pnl < 0]
    d = pd.Series(dict(r["days"])).sort_index()
    daily = d.diff().fillna(d.iloc[0])
    dts = pd.to_datetime(daily.index * 86400, unit="s")
    wk = daily.groupby(dts.to_period("W-SAT")).sum()               # Sun-Sat: the Sunday-evening open belongs to the week that follows
    mo = daily.groupby(dts.to_period("M")).sum()
    w = r["wipes"]
    # longest run of consecutive wipe-outs with no withdrawal in between
    run = best = 0
    lives, got, born = [], 0.0, r["i0"]                                      # a life = one deposit until its stop-out
    for i, kind, amt in r["cash"][1:]:
        if kind == "sweep":
            run, got = 0, got + amt
        elif kind == "wipe":
            run += 1
            best = max(best, run)
            lives.append((got, i - born))
        else:
            got, born = 0.0, i
    lv = np.array(lives, dtype=float).reshape(-1, 2)
    out = dict(owner_cash=r["owner"], deposits=r["dep"], withdrawals=r["wd"], final_equity=r["final_eq"],
               wipeouts=len(w), wipe_loss=sum(x[1] for x in w), wipe_loss_avg=np.mean([x[1] for x in w]) if w else 0.0,
               wipe_loss_median=np.median([x[1] for x in w]) if w else 0.0, wipe_loss_max=max([x[1] for x in w], default=0.0),
               wipe_run_max=best, lives_paid_back=float((lv[:, 0] >= r["dep"] / max(1, len(lv) + 1) - 1e-9).mean()) if len(lv) else np.nan,
               life_withdrawn_median=float(np.median(lv[:, 0])) if len(lv) else np.nan, absorbed_by_broker=r["absorbed"], forfeited_residual=r["forfeited"],
               n=len(pnl), n_tp=int((t[:, 5] == 0).sum()), n_so=int((t[:, 5] == 1).sum()), n_open_end=int((t[:, 5] == 2).sum()),
               win_rate=len(win) / max(1, len(pnl)), pf=win.sum() / -loss.sum() if len(loss) else np.inf,
               avg_win=win.mean() if len(win) else 0.0, avg_loss=loss.mean() if len(loss) else 0.0,
               n_win=len(win), n_loss=len(loss), gross_win=win.sum(), gross_loss=loss.sum(),
               net_pts=float((t[:, 0] * (t[:, 4] - t[:, 3])).sum()), pos_pnl=pnl.sum(),
               flat_share=r["flat"] / r["bars"], hedged_share=r["hedged"] / r["bars"], full_side_share=r["full"] / r["bars"], max_positions=r["maxpos"], max_net_lots=r["maxnet"] * CLIP, rejected=r["rejected"],
               weeks=len(wk), weeks_pos=float((wk > 0).mean()), worst_week=wk.min(), best_week=wk.max(),
               wipes_per_week=len(w) / max(1, len(wk)), months=len(mo), months_pos=float((mo > 0).mean()),
               worst_day=daily.min(), max_dd=float((d.cummax().clip(lower=0) - d).max()),
               top_month_share=float(mo.max() / mo.sum()) if mo.sum() > 0 else np.nan)
    if tmin is not None and len(t):
        out["hold_med_min"] = float(np.median(tmin[t[:, 2].astype(int)] - tmin[t[:, 1].astype(int)]))
        ww = pd.Series(1, index=pd.to_datetime(tmin[[x[0] for x in w]] * 60, unit="s")).groupby(lambda x: x.to_period("W-SAT")).sum() if w else pd.Series(dtype=float)
        out.update(wipe_weeks_share=len(ww) / max(1, len(wk)), wipes_week_max=int(ww.max()) if len(ww) else 0,
                   wipe_days_share=len({int(tmin[x[0]]) // 1440 for x in w}) / max(1, len(d)))
    return out, wk, mo, daily


# ---- shared state for forked workers ---------------------------------------------------------------------------------
G = {}


def setup(df=None):
    df = load_main() if df is None else df
    ind = indicators(df)
    G.update(df=df, ind=ind, t=df.time, D={c: as_lists(ind, quotes(df, c)) for c in COSTS},
             sell=ind["sell"].tolist(), buy=ind["buy"].tolist())
    G["idx"] = {k: (int(df.time.searchsorted(pd.Timestamp(a, tz="UTC"))), int(df.time.searchsorted(pd.Timestamp(b, tz="UTC"))))
                for k, (a, b) in W.items()}


def _cell(a):
    win, cost, tp, mode, sw = a
    i0, i1 = G["idx"][win]
    r = simulate(G["D"][cost], i0, i1, G["sell"], G["buy"], tp, mode, sw)
    D = G["D"][cost]
    audit(r, D)
    s, wk, mo, daily = summarize(r, G["ind"]["tmin"])
    s["spread_paid"] = U * sum(D["ao"][t[1]] - D["bo"][t[1]] for t in r["trades"])      # quoted spread at each entry
    return dict(window=win, cost=str(cost), tp_atr=tp, tp_mode=mode, sweep=sw, **s), wk, mo, daily


def _ctrl(a):
    win, cost, seed, tp, mode, sw = a
    i0, i1 = G["idx"][win]
    rs, rb = random_signals(G["ind"], seed)
    s, _, _, _ = summarize(simulate(G["D"][cost], i0, i1, rs, rb, tp, mode, sw))
    return dict(window=win, cost=str(cost), seed=seed, **s)


def _ruin(a):
    start, deposit, sw = a
    r = simulate(G["D"]["base"], start, G["idx"]["TEST"][1], G["sell"], G["buy"], 1.0, "per_leg", sw, deposit=deposit, redeposit=False)
    tm = G["ind"]["tmin"]
    ruined = len(r["wipes"]) == 1
    return dict(start=str(G["t"].iloc[start]), deposit=deposit, sweep=sw, ruined=ruined,
                minutes=(tm[r["wipes"][0][0]] if ruined else tm[r["last"]]) - tm[start],
                withdrawn=r["wd"], lost=r["wipes"][0][1] if ruined else 0.0, owner=r["owner"], positions=len(r["trades"]))


def pool_map(fn, jobs):
    with mp.get_context("fork").Pool(NPROC) as p:
        return p.map(fn, jobs, chunksize=1)


# ---- steps -----------------------------------------------------------------------------------------------------------
def step_grid():
    jobs = [(w, c, *cell) for w in ("TRAIN", "TEST") for c in ("base", "stress") for cell in GRID]
    jobs += [(w, c, *cell) for w in ("TRAIN", "TEST") for c in (0.45, 0.80) for cell in GRID]
    res = pool_map(_cell, jobs)
    g = pd.DataFrame([r[0] for r in res])
    g.to_csv(OUT / "grid.csv", index=False)
    wk = pd.concat({f"{j[0]}|{j[1]}|{j[2]}|{j[3]}|{j[4]}": r[1] for j, r in zip(jobs, res)}, axis=1)
    mo = pd.concat({f"{j[0]}|{j[1]}|{j[2]}|{j[3]}|{j[4]}": r[2] for j, r in zip(jobs, res)}, axis=1)
    pd.concat({f"{j[0]}|{j[1]}|{j[2]}|{j[3]}|{j[4]}": r[3] for j, r in zip(jobs, res)}, axis=1).to_csv(OUT / "daily_owner_cash.csv")
    wk.to_csv(OUT / "weekly_owner_cash.csv")
    mo.to_csv(OUT / "monthly_owner_cash.csv")
    # default cell: every stop-out and (base cost) every position, so the report's statements can be checked row by row
    wl, tl, t = [], [], G["t"]
    for w in ("TRAIN", "TEST"):
        for c in ("base", "stress"):
            r = simulate(G["D"][c], *G["idx"][w], G["sell"], G["buy"])
            wl += [dict(window=w, cost=c, time=t.iloc[i], balance_wiped=b, equity_min=e, n_long=a, n_short=z) for i, b, e, a, z in r["wipes"]]
            if c == "base":
                tl += [dict(window=w, side="BUY" if sd > 0 else "SELL", opened=t.iloc[oi], closed=t.iloc[ci], entry=e, exit=x, usd=sd * (x - e) * U,
                            reason=("TP", "STOP_OUT", "OPEN_AT_END")[why]) for sd, oi, ci, e, x, why in r["trades"]]
    pd.DataFrame(wl).to_csv(OUT / "wipeouts_default.csv", index=False)
    pd.DataFrame(tl).to_csv(OUT / "trades_default_base.csv", index=False)
    print(g[g.cost.isin(["base", "stress"])][["window", "cost", "tp_atr", "tp_mode", "sweep", "owner_cash", "deposits", "withdrawals",
                                              "wipeouts", "n", "win_rate", "pf", "flat_share", "weeks_pos"]].round(3).to_string(index=False))


def step_shadow():
    """Unlimited balance, one continuous run over TRAIN+TEST: the floating loss the stop-out hides."""
    i0, i1 = G["idx"]["TRAIN"][0], G["idx"]["TEST"][1]
    tm = G["ind"]["tmin"]
    rows = []
    for tp, mode in ((1.0, "per_leg"), (2.5, "per_leg"), (1.0, "shared_first"), (2.5, "shared_first")):
        for cost in ("base", "stress"):
            r = simulate(G["D"][cost], i0, i1, G["sell"], G["buy"], tp, mode, False, shadow=True, curve=True)
            t = np.array(r["trades"], dtype=float)
            pnl = t[:, 0] * (t[:, 4] - t[:, 3]) * U
            eq = np.array(r["eq"]) + r["dep"]                                # realised + floating, from 0
            hwm = np.maximum.accumulate(eq)
            uw = eq < hwm - 1e-9
            edges = np.flatnonzero(np.diff(np.r_[0, uw.astype(int), 0]))
            st, en = edges[::2], edges[1::2] - 1
            k = int(np.argmax(tm[i0 + en] - tm[i0 + st])) if len(st) else 0
            hold = tm[t[:, 2].astype(int)] - tm[t[:, 1].astype(int)]
            closed = t[:, 5] == 0
            rows.append(dict(tp_atr=tp, tp_mode=mode, cost=cost, n=len(t), n_tp=int(closed.sum()), n_open_end=int((~closed).sum()),
                             realised=pnl[closed].sum(), floating_end=pnl[~closed].sum(), total=pnl.sum(), win_rate=(pnl > 0).mean(),
                             worst_floating_usd=r["worst_float"], worst_floating_time=str(G["t"].iloc[r["worst_i"]]),
                             worst_floating_clip_pts=r["worst_float"] / U, worst_single_position_adverse_pts=r["worst_adv"],
                             max_dd_usd=float((hwm - eq).max()), longest_underwater_days=float((tm[i0 + en[k]] - tm[i0 + st[k]]) / 1440) if len(st) else 0.0,
                             longest_position_days=float(hold.max() / 1440), max_positions=r["maxpos"]))
            if tp == 1.0 and mode == "per_leg" and cost == "base":             # the positions the run never closes
                o = t[~closed]
                pd.DataFrame({"side": np.where(o[:, 0] > 0, "BUY", "SELL"), "opened": G["t"].iloc[o[:, 1].astype(int)].to_numpy(), "entry": o[:, 3],
                              "mark_at_end": o[:, 4], "floating_usd": pnl[~closed]}).to_csv(OUT / "shadow_open_positions.csv", index=False)
                rows[-1]["last_order_opened"] = str(G["t"].iloc[int(t[:, 1].max())])
            if tp == 1.0 and mode == "per_leg":
                pd.Series(eq[::60], index=G["t"].iloc[i0:i1:60].to_numpy()).to_csv(OUT / f"shadow_equity_{cost}.csv", header=["equity"])
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "shadow.csv", index=False)
    print(s.round(2).T.to_string())


def step_control(n=100):
    jobs = [(w, c, 1000 + k, 1.0, "per_leg", True) for w in ("TRAIN", "TEST") for c in ("base", "stress") for k in range(n)]
    c = pd.DataFrame(pool_map(_ctrl, jobs))
    c.to_csv(OUT / "control.csv", index=False)
    print(c.groupby(["window", "cost"])[["owner_cash", "wipeouts", "n", "win_rate", "pf", "pos_pnl"]].describe(percentiles=[.05, .5, .95]).round(3).T.to_string())


def step_ruin():
    """Time to the first margin stop-out with no re-deposit, from every trading day's first in-session bar (default cell, base cost)."""
    i0, i1 = G["idx"]["TRAIN"][0], G["idx"]["TEST"][1]
    ind = G["ind"]
    ok = ind["sess"] & ~np.isnan(ind["atr"])
    ok[:i0] = ok[i1:] = False
    starts = pd.Series(np.flatnonzero(ok)).groupby(ind["day"][ok]).first().tolist()
    jobs = [(s, d, sw) for d in (200.0, 1000.0) for sw in (True, False) for s in starts]
    r = pd.DataFrame(pool_map(_ruin, jobs))
    r.to_csv(OUT / "ruin.csv", index=False)
    end = G["t"].iloc[i1 - 1]
    rows = []
    for (d, sw), g in r.groupby(["deposit", "sweep"]):
        row = dict(deposit=d, sweep=sw, starts=len(g), ruined=int(g.ruined.sum()),
                   median_hours=g[g.ruined].minutes.median() / 60, p90_hours=g[g.ruined].minutes.quantile(.9) / 60,
                   max_survival_days=g.minutes.max() / 1440, owner_mean=g.owner.mean(), owner_median=g.owner.median(),
                   owner_positive_share=(g.owner > 0).mean(), withdrawn_median=g.withdrawn.median())
        left = (end - pd.to_datetime(g.start)).dt.total_seconds() / 60
        for name, h in (("1d", 1440), ("1w", 10080), ("30d", 43200), ("90d", 129600)):
            e = g[left >= h]                                                 # starts with at least h of data left
            row[f"p_ruin_{name}"] = ((e.ruined) & (e.minutes <= h)).mean() if len(e) else np.nan
            row[f"n_{name}"] = len(e)
        rows.append(row)
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "ruin_summary.csv", index=False)
    print(s.round(3).T.to_string())


def measure_basis():
    """XM deal price minus OANDA same-side quote in the S5 bar containing the deal (BUY fills at ask, SELL at bid)."""
    s5 = pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet").set_index("time").sort_index()
    d = pd.read_csv(ROOT / "deals.csv")
    d["time"] = pd.to_datetime(d.time, utc=True, format="ISO8601")
    d = d[d.symbol.notna()].copy()
    buy = d.type.eq("DEAL_TYPE_BUY").to_numpy()
    i = s5.index.searchsorted(d.time, side="right") - 1
    age = (d.time - s5.index[i]).dt.total_seconds().to_numpy()
    frac = np.clip(age / 5, 0, 1)
    o = np.where(buy, s5.ask_open.to_numpy()[i], s5.bid_open.to_numpy()[i])
    c = np.where(buy, s5.ask_close.to_numpy()[i], s5.bid_close.to_numpy()[i])
    basis = d.price.to_numpy() - (o + (c - o) * frac)
    ok = (age < 5) & d.reason.ne("DEAL_REASON_SO").to_numpy()                # inside an S5 bar; stop-outs fill far from quote
    out = {}
    for name, m in (("sell_at_bid", ok & ~buy), ("buy_at_ask", ok & buy), ("stop_outs", (age < 5) & d.reason.eq("DEAL_REASON_SO").to_numpy())):
        b = basis[m]
        out[name] = dict(n=int(m.sum()), median=round(float(np.median(b)), 3), mean=round(float(b.mean()), 3), sd=round(float(b.std()), 3),
                         p05=round(float(np.quantile(b, .05)), 3), p95=round(float(np.quantile(b, .95)), 3))
    out["oanda_spread_median_s5"] = round(float(np.median(s5.ask_close - s5.bid_close)), 3)
    return out


def test_no_lookahead(df, n=24, seed=7):
    """Proof that nothing at bar t depends on data stamped after t: scramble every bar after a random cut and recompute.
    Signals, ATR5 and the session flag at or before the cut must be bit-identical."""
    sub = df.iloc[-60000:].reset_index(drop=True)
    ref = indicators(sub)
    rng = np.random.default_rng(seed)
    px = [c for c in sub.columns if c != "time"]
    for cut in rng.integers(2000, len(sub) - 10, n):
        p = sub.copy()
        p.loc[cut + 1:, px] = p.loc[cut + 1:, px].to_numpy() * rng.uniform(0.5, 1.5, (len(sub) - cut - 1, 1))
        alt = indicators(p)
        for k in ("sell", "buy", "sess", "elig"):
            assert (alt[k][:cut + 1] == ref[k][:cut + 1]).all(), f"look-ahead in {k} at cut {cut}"
        assert np.array_equal(alt["atr"][:cut + 1], ref["atr"][:cut + 1], equal_nan=True), f"look-ahead in ATR5 at cut {cut}"
        assert not np.array_equal(alt["atr"][cut + 6:], ref["atr"][cut + 6:], equal_nan=True), "perturbation had no effect: test is vacuous"
    return dict(cuts=n, bars=len(sub), closed_bar_probe_max_s=ref["probe_max_s"])


def selftest():
    """Smallest checks that fail if the engine logic breaks (synthetic bars, spread 0.6)."""
    def mk(mids, atr=5.0):                                                   # each mid: (open, high, low, close)
        n = len(mids)
        o, h, l, c = (np.array([m[k] for m in mids], float) for k in range(4))
        return dict(bo=(o - .3).tolist(), bh=(h - .3).tolist(), bl=(l - .3).tolist(), bc=(c - .3).tolist(),
                    ao=(o + .3).tolist(), ah=(h + .3).tolist(), al=(l + .3).tolist(), ac=(c + .3).tolist(), mid=c.tolist(),
                    atr=[atr] * n, sess=[True] * n, tmin=list(range(600, 600 + n)), day=[0] * n)
    F, T = False, True
    # 1 fill at next open; per-leg TP at fill + 5 filled exactly at P; sweep to 200
    bars = [(4000, 4000, 4000, 4000), (4001, 4001, 4001, 4001), (4001, 4007, 4001, 4007), (4007, 4007, 4007, 4007)]
    r = simulate(mk(bars), 0, 4, [F] * 4, [T, F, F, F])
    assert [t[1:5] for t in r["trades"]] == [(1, 2, 4001.3, 4006.3)] * 2 and abs(r["wd"] - 40) < 1e-9 and r["final_eq"] == 200
    # 2 TP and stop-out in the same bar: the stop-out wins, balance to 0, re-deposit 60 min later, no entry while waiting
    bars = [(4000,) * 4, (4000, 4006, 3970, 4000)] + [(4000,) * 4] * 70
    r = simulate(mk(bars), 0, 72, [F] * 72, [T] + [F] * 5 + [T] * 66)
    assert len(r["wipes"]) == 1 and r["wipes"][0][0] == 1 and all(t[5] == 1 for t in r["trades"][:2])
    assert r["cash"][1] == (1, "wipe", 200.0) and r["cash"][2] == (61, "dep", 200.0), r["cash"]          # c(1) + 60 min = c(61)
    assert min(t[1] for t in r["trades"][2:]) == 62 and r["absorbed"] > 0
    # 3 add one clip when ask_close is >= max(0.7*ATR, 2) below the last fill; shared_first add takes the oldest TP
    bars = [(4000,) * 4, (4000, 4000, 3996.2, 3996.2), (3996.2,) * 4, (3996.2, 4006, 3996.2, 4006)]
    r = simulate(mk(bars), 0, 4, [F] * 4, [T, F, F, F], mode="shared_first")
    assert sorted(t[3] for t in r["trades"]) == [3996.5, 4000.3, 4000.3] and {t[4] for t in r["trades"]} == {4005.3}
    r = simulate(mk(bars), 0, 4, [F] * 4, [T, F, F, F], mode="per_leg")
    assert sorted(t[4] for t in r["trades"]) == [4001.5, 4005.3, 4005.3]
    # 4 margin rule 6: equity 200 - floating must exceed the margin after the order, else rejected
    bars = [(4000,) * 4, (4000, 4000, 3980, 3980), (3980,) * 4, (3980,) * 4]
    r = simulate(mk(bars), 0, 4, [F] * 4, [T, F, F, F])                      # floating -162.4, equity 37.6 < margin 47.8
    assert r["rejected"] >= 1 and len(r["trades"]) == 2
    # 5 shadow: no stop-out on the bar that wipes the real account
    r = simulate(mk([(4000,) * 4, (4000, 4006, 3970, 4000), (4000,) * 4]), 0, 3, [F] * 3, [T, F, F], shadow=True)
    assert not r["wipes"] and abs(r["worst_float"] + 8 * 30.6) < 1e-6
    # 6 sub-bar resolution: with the high first and the low later, S5 takes the TP that M1 resolves as a stop-out
    d = mk([(4000,) * 4, (4000, 4006, 3970, 4000), (4000,) * 4])
    fine = ([0, 3999.7, 3969.7, 0], [0, 4005.7, 3999.7, 0], [0, 4000.3, 3970.3, 0], [0, 4006.3, 4000.3, 0], [0, 1, 3], [1, 3, 4])
    r = simulate(d, 0, 3, [F] * 3, [T, F, F], fine=fine)
    assert not r["wipes"] and len(r["trades"]) == 2 and all(t[5] == 0 for t in r["trades"])
    print("selftest: engine checks passed (6)")


def _null(seed, n=150000):
    """Driftless +-0.1 tick random walk (150 ticks per M1 bar, M1 sd 1.22 pts) on real timestamps."""
    rng = np.random.default_rng(seed)
    path = 4000 + 0.1 * np.cumsum(rng.integers(0, 2, n * 150, dtype=np.int8) * 2 - 1).reshape(n, 150)
    o = np.r_[4000.0, path[:-1, -1]]
    rw = pd.DataFrame({"time": G["t"].iloc[G["idx"]["TEST"][0]:G["idx"]["TEST"][0] + n].reset_index(drop=True), "open": o,
                       "high": np.maximum(path.max(1), o), "low": np.minimum(path.min(1), o), "close": path[:, -1].astype(float)})
    ind = indicators(rw)
    rows = []
    for cost in (0.0, 0.6):
        D = as_lists(ind, quotes(rw, cost))
        r = simulate(D, 0, n, ind["sell"].tolist(), ind["buy"].tolist())
        s = summarize(r)[0]
        rows.append(dict(seed=seed, spread=cost, owner_cash=s["owner_cash"], wipeouts=s["wipeouts"], n=s["n"], win_rate=s["win_rate"], pf=s["pf"],
                         spread_paid=s["n"] * cost * U, tp_overshoot_max=0.1 * U * s["n_tp"],
                         residual_max=sum(SO_LEVEL * abs(w[3] - w[4]) * MARG_K * D["mid"][w[0]] for w in r["wipes"])))
    return rows


def step_null(n=24):
    """Harness fairness: on a driftless random walk the owner's expected cash must equal minus the spread paid, minus at most the
    equity forfeited at each stop-out (<= 20% of margin) and the sub-tick TP overshoot. Anything else would be an engine bias."""
    d = pd.DataFrame([r for rr in pool_map(_null, range(n)) for r in rr])
    d.to_csv(OUT / "null_random_walk.csv", index=False)
    rows = []
    for c, g in d.groupby("spread"):
        rows.append(dict(spread=c, seeds=len(g), owner_mean=g.owner_cash.mean(), owner_se=g.owner_cash.std() / np.sqrt(len(g)), owner_sd=g.owner_cash.std(),
                         expected_low=-(g.spread_paid + g.residual_max + g.tp_overshoot_max).mean(), expected_high=-g.spread_paid.mean(),
                         win_rate_mean=g.win_rate.mean(), pf_mean=g.pf.mean(), wipeouts_mean=g.wipeouts.mean(), n_mean=g.n.mean()))
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "null_summary.csv", index=False)
    print(s.round(3).T.to_string())
    for r in rows:
        assert r["expected_low"] - 3 * r["owner_se"] <= r["owner_mean"] <= r["expected_high"] + 3 * r["owner_se"], "engine is not a fair game on a random walk"


def step_qa():
    df, ind = G["df"], G["ind"]
    out = dict(rows=len(df), first=str(df.time.iloc[0]), last=str(df.time.iloc[-1]),
               windows={k: dict(bars=b - a, first=str(df.time.iloc[a]), last=str(df.time.iloc[b - 1])) for k, (a, b) in G["idx"].items()})
    out["basis_xm_minus_oanda"] = measure_basis()
    out["lookahead_test"] = test_no_lookahead(df)
    out["closed_bar_probe_max_s_full"] = ind["probe_max_s"]
    # stitch and long-file quality
    a = pd.read_parquet(RD / "xau_m1_oanda.parquet")
    b = pd.read_parquet(ROOT / "xau_m1_2026-07-16_now_mba.parquet")
    ov = a.merge(b[["time", "close"]], on="time", suffixes=("_a", "_b"))
    out["stitch_overlap"] = dict(bars=len(ov), max_abs_close_diff=float((ov.close_a - ov.close_b).abs().max()))
    q = df.bid_close.notna()
    out["oanda_m1_spread_median"] = round(float((df.ask_close - df.bid_close)[q].median()), 3)
    f = pd.read_parquet(RD / "m3_scalper/xau_m1_full.parquet")
    m = a.merge(f, on="time", how="left", suffixes=("", "_f"), indicator=True)
    m = m[m.time <= f.time.max()]
    out["long_file_vs_oanda_overlap"] = dict(bars_oanda=len(m), missing_in_long=int((m._merge == "left_only").sum()),
                                             close_exact_share=float((m.close == m.close_f)[m._merge == "both"].mean()),
                                             max_abs_high_diff=float((m.high - m.high_f).abs().max()))
    # trigger parity (spec 9.2 check 3): trigger on at the last bar CLOSED at the click
    e = pd.read_csv(ROOT / "analysis/entries/entries_features.csv")
    e["open_time"] = pd.to_datetime(e.open_time, utc=True, format="ISO8601")
    d = e[e.click_in_event == 0].reset_index(drop=True)
    j = np.searchsorted(df.time.to_numpy(), (d.open_time - pd.Timedelta(seconds=60)).to_numpy(), "right") - 1
    assert ((d.open_time - (df.time.iloc[j].reset_index(drop=True) + pd.Timedelta(minutes=1))).dt.total_seconds() >= 0).all()
    hit = np.where(d.side.eq("SELL"), ind["sell"][j], ind["buy"][j])
    fresh = d.role.eq("first").to_numpy()
    out["trigger_parity"] = dict(fresh_hit=int(hit[fresh].sum()), fresh_n=int(fresh.sum()), all_hit=int(hit.sum()), all_n=len(d),
                                 expected="11 of 27 and 39 of 124")
    assert (int(hit[fresh].sum()), int(hit.sum())) == (11, 39), "harness trigger disagrees with the specification"
    # trigger firing rate
    for w, (i0, i1) in G["idx"].items():
        s = ind["sess"][i0:i1]
        m = np.zeros(len(df), bool)
        m[i0:i1] = s
        ctl = [ind["atr"][m & (np.array(a) | np.array(b))].mean() for a, b in (random_signals(ind, 1000 + k) for k in range(10))]
        out["windows"][w].update(atr5_mean_at_trigger_bars=float(ind["atr"][m & (ind["sell"] | ind["buy"])].mean()), atr5_mean_at_control_bars=float(np.mean(ctl)))
        out["windows"][w].update(session_bars=int(s.sum()), elig_share=float(ind["elig"][i0:i1][s].mean()),
                                 sell_rate=float(ind["sell"][i0:i1][s].mean()), buy_rate=float(ind["buy"][i0:i1][s].mean()),
                                 atr5_median=float(np.nanmedian(ind["atr"][i0:i1][s])))
    (OUT / "qa.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def step_week():
    """Trade week: default cell on his active span (first deal to last deal), M1 and S5 exit resolution, and replication."""
    df, ind, tm = G["df"], G["ind"], G["ind"]["tmin"]
    tr = pd.read_csv(ROOT / "trades.csv")
    tr["open_time"] = pd.to_datetime(tr.open_time, utc=True, format="ISO8601")
    tr["close_time"] = pd.to_datetime(tr.close_time, utc=True, format="ISO8601")
    i0 = int(df.time.searchsorted(pd.Timestamp("2026-11-04 10:06", tz="UTC")))
    i1 = int(df.time.searchsorted(tr.close_time.max()))
    s5 = pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet")
    n = len(df)
    f0, f1 = np.zeros(n, int), np.zeros(n, int)
    pos = np.searchsorted(df.time.to_numpy(), s5.time.to_numpy(), "right") - 1   # M1 bar of each S5 bar
    f0[i0:i1] = np.searchsorted(pos, np.arange(i0, i1), "left")
    f1[i0:i1] = np.searchsorted(pos, np.arange(i0, i1), "right")
    assert (f1[i0:i1] > f0[i0:i1]).all(), "an M1 bar in the trade week has no S5 bars"
    rows, sims = [], {}
    for cost, ex in (("base", 0.0), ("stress", 0.20)):
        fine = ((s5.bid_low - .05 - ex).tolist(), (s5.bid_high - .05 - ex).tolist(), (s5.ask_low + .06 + ex).tolist(),
                (s5.ask_high + .06 + ex).tolist(), f0.tolist(), f1.tolist())
        for tp, mode, sw in GRID:
            for res, fn in (("M1", None), ("S5", fine)):
                if res == "S5" and (tp, mode, sw) != GRID[0]:
                    continue
                r = simulate(G["D"][cost], i0, i1, G["sell"], G["buy"], tp, mode, sw, fine=fn)
                s, *_ = summarize(r, tm)
                rows.append(dict(cost=cost, tp_atr=tp, tp_mode=mode, sweep=sw, exits=res, **s))
                sims[(cost, tp, mode, sw, res)] = r
    w = pd.DataFrame(rows)
    w.to_csv(OUT / "week.csv", index=False)
    print(w[["cost", "tp_atr", "tp_mode", "sweep", "exits", "owner_cash", "deposits", "withdrawals", "wipeouts", "n", "win_rate", "pf",
             "flat_share", "max_positions", "hold_med_min"]].round(3).to_string(index=False))
    # --- replication: do the rules reproduce his entries? (default cell, base cost, M1)
    r = sims[("base", 1.0, "per_leg", True, "M1")]
    t = np.array(r["trades"], dtype=float)
    sim = pd.DataFrame({"time": df.time.iloc[t[:, 1].astype(int)].to_numpy(), "side": np.where(t[:, 0] > 0, "BUY", "SELL")})
    sim_orders = sim.drop_duplicates().reset_index(drop=True)                # a double tap is one order
    e = pd.read_csv(ROOT / "analysis/entries/entries_features.csv")
    e["open_time"] = pd.to_datetime(e.open_time, utc=True, format="ISO8601")
    dec = e[e.click_in_event == 0][["open_time", "side", "role"]].rename(columns={"open_time": "time"}).reset_index(drop=True)
    tol = np.timedelta64(5, "m")

    def share(a_t, a_side, b_t, b_side, shift=0, flip=False):
        """Share of A events with a B event of the same side within +-5 min (B shifted by `shift` minutes for the placebo)."""
        naive = lambda v: pd.to_datetime(pd.Series(v), utc=True).dt.tz_localize(None).to_numpy().astype("datetime64[ns]")
        bt, at = naive(b_t) + np.timedelta64(shift, "m"), naive(a_t)
        hit = np.zeros(len(at), bool)
        for sd in ("BUY", "SELL"):
            b = np.sort(bt[(b_side == sd).to_numpy()])
            am = (a_side == ({"BUY": "SELL", "SELL": "BUY"}[sd] if flip else sd)).to_numpy()
            if len(b) == 0:
                continue
            k = np.searchsorted(b, at[am])
            lo = np.abs(at[am] - b[np.clip(k - 1, 0, len(b) - 1)]) <= tol
            hi = np.abs(b[np.clip(k, 0, len(b) - 1)] - at[am]) <= tol
            hit[am] = lo | hi
        return hit
    shifts = [s * m for m in (67, 113, 181, 239, 307, 421, 577, 733) for s in (1, -1)]
    sig = pd.concat([pd.DataFrame({"time": (df.time[i0:i1] + pd.Timedelta(minutes=1))[ind[k][i0:i1] & ind["sess"][i0:i1]], "side": sd})
                     for k, sd in (("sell", "SELL"), ("buy", "BUY"))], ignore_index=True)
    rep = {}
    for name, a, b in (("trader_decisions_explained_by_sim_orders", dec, sim_orders), ("trader_positions_explained_by_sim_orders", tr.rename(columns={"open_time": "time"}), sim_orders),
                       ("sim_orders_matching_a_trader_decision", sim_orders, dec), ("trader_decisions_with_trigger_within_5min", dec, sig),
                       ("trader_fresh_entries_explained_by_sim_orders", dec[dec.role.eq("first")], sim_orders)):
        h = share(a.time, a.side, b.time, b.side)
        rep[name] = dict(n=len(a), hit=int(h.sum()), rate=round(float(h.mean()), 4),
                         opposite_side_rate=round(float(share(a.time, a.side, b.time, b.side, flip=True).mean()), 4),
                         time_shift_placebo_rate=round(float(np.mean([share(a.time, a.side, b.time, b.side, s).mean() for s in shifts])), 4),
                         placebo_max=round(float(np.max([share(a.time, a.side, b.time, b.side, s).mean() for s in shifts])), 4))
    rep["counts"] = dict(sim_positions=len(sim), sim_orders=len(sim_orders), sim_buy=int((sim.side == "BUY").sum()), sim_sell=int((sim.side == "SELL").sum()),
                         real_positions=len(tr), real_decisions=len(dec), real_buy=int((tr.side == "BUY").sum()), real_sell=int((tr.side == "SELL").sum()),
                         trigger_bars_in_span=len(sig), span=f"{df.time.iloc[i0]} .. {df.time.iloc[i1 - 1]}")
    # real account, same span, for the side-by-side
    rep["real"] = dict(positions=178, win_rate=float((tr.net > 0).mean()), pf=float(tr.net[tr.net > 0].sum() / -tr.net[tr.net < 0].sum()),
                       net=float(tr.net.sum()), stopout_positions=int(tr.exit_reason.eq("DEAL_REASON_SO").sum()), wipeouts=7, flat_share=0.174,
                       hold_med_min=float(tr.hold_s.median() / 60), avg_win=float(tr.net[tr.net > 0].mean()), avg_loss=float(tr.net[tr.net < 0].mean()))
    (OUT / "replication.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    sim.assign(close=df.time.iloc[t[:, 2].astype(int)].to_numpy(), entry=t[:, 3], exit=t[:, 4], reason=t[:, 5].astype(int)).to_csv(OUT / "week_sim_trades.csv", index=False)


def step_secondary():
    """2019-01-01 .. 2025-07-15 on the long mid-only file, spread 1.5 bp (base) / 2.5 bp (stress) of price. Report only."""
    df = load_secondary()
    ind = indicators(df)
    sell, buy, n = ind["sell"].tolist(), ind["buy"].tolist(), len(df)
    rows = []
    for name, bp in (("base_1.5bp", 1.5), ("stress_2.5bp", 2.5)):
        D = as_lists(ind, quotes(df, ("bp", bp)))
        for tp, mode, sw in (GRID[0], GRID[1]):
            r = simulate(D, 0, n, sell, buy, tp, mode, sw)
            s, _, mo, daily = summarize(r, ind["tmin"])
            rows.append(dict(cost=name, tp_atr=tp, tp_mode=mode, sweep=sw, **s))
            if bp == 1.5 and sw:
                yr = daily.groupby(pd.to_datetime(daily.index * 86400, unit="s").year).sum()
                wy = pd.Series([df.time.iloc[x[0]].year for x in r["wipes"]]).value_counts().sort_index()
                el = pd.Series(ind["elig"][ind["sess"]]).groupby(df.time[ind["sess"]].dt.year.to_numpy()).mean()
                pd.DataFrame({"owner_cash": yr, "wipeouts": wy, "eligible_bar_share": el,
                              "atr5_median": pd.Series(ind["atr"]).groupby(df.time.dt.year.to_numpy()).median(),
                              "price_median": df.close.groupby(df.time.dt.year.to_numpy()).median()}).to_csv(OUT / "secondary_by_year.csv")
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "secondary.csv", index=False)
    print(s[["cost", "tp_atr", "sweep", "owner_cash", "deposits", "withdrawals", "wipeouts", "n", "win_rate", "pf", "flat_share", "weeks_pos"]].round(3).to_string(index=False))
    print(pd.read_csv(OUT / "secondary_by_year.csv").round(3).to_string(index=False))


STEPS = dict(qa=step_qa, null=step_null, grid=step_grid, shadow=step_shadow, control=step_control, ruin=step_ruin, week=step_week, secondary=step_secondary)

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    todo = sys.argv[1:] or ["selftest", *STEPS]
    if "selftest" in todo:
        selftest()
        todo = [s for s in todo if s != "selftest"]
        if not todo:
            print("look-ahead test:", test_no_lookahead(load_main()))
    if todo:
        t0 = time.time()
        if todo != ["secondary"]:
            setup()
        for s in todo:
            print(f"\n===== {s} ({time.time() - t0:.0f}s) =====")
            STEPS[s]()
        print(f"\ndone in {time.time() - t0:.0f}s")
