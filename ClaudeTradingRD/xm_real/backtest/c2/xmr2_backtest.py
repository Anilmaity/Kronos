#!/usr/bin/env python
"""XMR-2 "capped fade basket" - standalone event-driven M1 backtester.

Spec: ../../analysis/STRATEGY_SPEC.md, sections 5 (common definitions), 7 (rules, parameters), 9 (protocol).
Everything is decided on CLOSED M1 bars and filled at the NEXT bar's open. M5 ATR uses closed M5 bars only.

Run (deterministic, about 2 minutes on 12 cores; XMR2_NCTRL=24 for a 20-second smoke run):
    ../../../.venv/bin/python xmr2_backtest.py | tee results/run.log
Outputs: results/*.csv, results/tables.md, equity.png. Reads the shared inputs, never writes them.

Units: 1 point = 1 USD/oz. LOT = 0.01 per leg = 1 USD per point per leg, so "points" (summed over legs) = USD.
"""
import bisect
import multiprocessing as mp
import os
import time as _time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
XM, RD = HERE.parents[1], HERE.parents[2]
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)

# ---- fixed parameters (spec 7.2). Nothing here is tuned. ----------------------------------------------------------
LOT = 0.01
USD_PT = 100 * LOT                                    # USD per point per leg
K_FADE, MIN_ATR5, K_STEP, STEP_FLOOR = 0.6, 3.0, 0.7, 2.0
RISK_USD, SL_ATR, MIN_STOP_GAP = 30.0, 6.0, 3.0
COOLDOWN_MIN, DAILY_STOPS, KILL_USD = 20, 3, -250.0
SESS_START, EOD_MIN = 60, 21 * 60                     # session [01:00, 21:00) UTC on c(t); end-of-day decision at c(t) >= 21:00
NEWS = ((12 * 60 + 25, 12 * 60 + 45), (13 * 60 + 25, 13 * 60 + 45))
GRID = [(3, 1.0), (2, 1.0), (1, 1.0), (3, 2.5), (2, 2.5), (1, 2.5)]     # (N_MAX, TP_ATR); the first cell is the hypothesis
SEAM, TRAIN_END, TEST_END = "2026-07-16", "2026-04-01", "2026-11-04"   # mid file < SEAM <= quote file; TRAIN < TRAIN_END <= TEST < TEST_END <= parity week
N_CTRL = int(os.environ.get("XMR2_NCTRL", 200))                   # 200 is the pre-registered count; the env knob is for a quick smoke run
# cost levels: half-spread applied to the mid; `quote` = (bid offset, ask offset) on real OANDA quotes where they exist
COSTS = {
    "rt0.45": dict(half=0.225, quote=None, slip=0.30),            # task brief, optimistic: 0.45 pts round trip everywhere
    "base":   dict(half=0.30, quote=(0.05, 0.06), slip=0.30),     # spec 5.2 base: mid +-0.30; quotes with the XM basis
    "rt0.80": dict(half=0.40, quote=None, slip=0.30),             # task brief, realistic: 0.80 pts round trip everywhere
    "stress": dict(half=0.50, quote=(0.25, 0.26), slip=0.60),     # spec 5.2 stress: mid +-0.50; quotes a further 0.20 per side
}
COSTS_MAIN = tuple(COSTS)
MIN_NS, DAY_NS = 60 * 10**9, 86400 * 10**9
TABLES = []


def ns(x):
    """UTC nanoseconds since the epoch, whatever resolution pandas parsed the column at."""
    return pd.DatetimeIndex(x).as_unit("ns").asi8


def at(s):
    return pd.Timestamp(s, tz="UTC").value


def say(*a):
    print(*a, flush=True)


def md(df, title, note=""):
    d = df.reset_index(drop=True).copy()
    for c in d:
        d[c] = d[c].map(lambda v: f"{v:,.2f}" if isinstance(v, (float, np.floating)) else str(v))
    s = f"\n### {title}\n\n" + "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns) + "\n"
    s += "\n".join("| " + " | ".join(r) + " |" for r in d.to_numpy()) + "\n" + (f"\n{note}\n" if note else "")
    TABLES.append(s)
    say(s)


# ---- data ------------------------------------------------------------------------------------------------------
def load_main():
    a = pd.read_parquet(RD / "xau_m1_oanda.parquet")
    a = a[a.time < SEAM].rename(columns=dict(open="mo", high="mh", low="ml", close="mc"))
    b = pd.read_parquet(XM / "xau_m1_2026-07-16_now_mba.parquet").rename(columns=dict(open="mo", high="mh", low="ml", close="mc"))
    b = b.rename(columns={f"{s}_{k}": s[0] + k[0] for s in ("bid", "ask") for k in ("open", "high", "low", "close")})
    m = pd.concat([a.assign(isq=False), b.assign(isq=True)], ignore_index=True).sort_values("time").reset_index(drop=True)
    assert m.time.is_unique and m.time.is_monotonic_increasing
    # signal series = the bid (spec 5.2): real bid - XM basis where quoted, mid - 0.30 before; the offset cancels in every indicator
    for k in "hlc":
        m["s" + k] = np.where(m.isq, m["b" + k] - 0.05, m["m" + k] - 0.30)
    return m


def indicators(t, h, l, c, leaky=False):
    """ATR5 (Wilder 14 on closed M5 bars), fade triggers and the validity guard, per M1 bar. `leaky=True` is the
    in-progress-M5 bug (vault trap 9), kept only so the look-ahead test can show it catches it."""
    t = pd.Series(pd.DatetimeIndex(t))
    s = pd.DataFrame({"h": np.asarray(h), "l": np.asarray(l), "c": np.asarray(c)}, index=pd.DatetimeIndex(t))
    m5 = s.resample("5min", label="left", closed="left").agg({"h": "max", "l": "min", "c": "last"}).dropna()
    pc = m5.c.shift()
    tr = np.maximum(m5.h - m5.l, np.maximum((m5.h - pc).abs(), (m5.l - pc).abs()))
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    atr.iloc[:100] = np.nan                                         # spec 5.3: discard the first 100 M5 bars
    atr = atr.dropna()
    # an M5 bar opened at T5 is closed once the M1 bar opened at T5 + 4 min has closed
    avail = pd.DataFrame({"time": atr.index + pd.Timedelta(minutes=0 if leaky else 4), "atr5": atr.to_numpy(), "t5": atr.index})
    j = pd.merge_asof(pd.DataFrame({"time": t}), avail, on="time")
    probe = ((j.t5 + pd.Timedelta(minutes=5)) - (j.time + pd.Timedelta(minutes=1))).max()   # (last M5 open + 5 min) - c(t)
    a = j.atr5.to_numpy()
    s = s.reset_index(drop=True)
    ret5 = (s.c - s.c.shift(5)).to_numpy()
    hi, lo = s.h.rolling(15).max(), s.l.rolling(15).min()
    pos15 = ((s.c - lo) / (hi - lo).where(hi > lo)).to_numpy()
    gap_ok = ((t - t.shift(14)) <= pd.Timedelta(minutes=30)).to_numpy()   # spec 5.1 gap guard
    with np.errstate(invalid="ignore"):
        guard = gap_ok & (a >= MIN_ATR5)
        sell = guard & (ret5 >= K_FADE * a) & (pos15 >= 2 / 3)
        buy = guard & (ret5 <= -K_FADE * a) & (pos15 <= 1 / 3)
    return a, sell, buy, guard, probe


def flags(t, eod_min=EOD_MIN):
    """Calendar flags per M1 bar. c(t) = open + 60 s is the decision instant."""
    t = pd.Series(pd.DatetimeIndex(t))
    c = t + pd.Timedelta(minutes=1)
    tod, wd = (c.dt.hour * 60 + c.dt.minute).to_numpy(), (c.dt.dayofweek < 5).to_numpy()
    sess = wd & (tod >= SESS_START) & (tod < eod_min)
    news = wd & np.logical_or.reduce([(tod >= a) & (tod < b) for a, b in NEWS])
    day0, prev, wdo = t.dt.normalize(), t.shift(), (t.dt.dayofweek < 5)
    nclose = np.logical_or.reduce([(wdo & (t >= day0 + pd.Timedelta(minutes=a)) & ~(prev >= day0 + pd.Timedelta(minutes=a))).to_numpy()
                                   for a, _ in NEWS])            # first bar opening at or after a window start
    T = ns(t)
    return dict(time=pd.DatetimeIndex(t), T=T.tolist(), C=(T + MIN_NS).tolist(), cday=((T + MIN_NS) // DAY_NS).tolist(),
                sess=sess.tolist(), news=news.tolist(), nclose=nclose.tolist(), ok_np=sess & ~news,
                chour=c.dt.hour.to_numpy(), cmonth=(c.dt.year * 12 + c.dt.month).to_numpy())


def quotes(m, cost):
    c = COSTS[cost]
    q = {"slip": c["slip"]}
    for k in "ohlc":
        mid = m["m" + k].to_numpy()
        half = mid * c["bp"] / 2e4 if "bp" in c else c["half"]
        bid, ask = mid - half, mid + half
        if c.get("quote"):
            bid = np.where(m.isq, m["b" + k] - c["quote"][0], bid)
            ask = np.where(m.isq, m["a" + k] + c["quote"][1], ask)
        q["b" + k], q["a" + k] = bid.tolist(), ask.tolist()
    return q


# ---- engine ----------------------------------------------------------------------------------------------------
def run(M, q, sS, sB, n_max, tp_atr, x=None, i0=0, i1=None, eod_min=EOD_MIN):
    """One basket at a time. Returns a list of closed baskets. `x` = finer execution bars (S5) with lo/hi index ranges
    per M1 bar; by default exits are resolved on the M1 bar itself. Bar-by-bar order of events:
      open of bar i : pending market close, else pending leg fill; then the news flatten
      inside bar i  : stop first, then target (spec 5.5: the stop wins a same-bar tie; the entry bar is checked)
      close of bar i: kill brake, end of day, add decision -> acted on at the open of bar i + 1
    """
    T, C, atr, sess, news, nclose, cday = (M[k] for k in ("T", "C", "atr", "sess", "news", "nclose", "cday"))
    bo, bc, ao, ac, slip = q["bo"], q["bc"], q["ao"], q["ac"], q["slip"]
    sub = (x["lo"], x["hi"]) if x else None
    x = x or q
    xbo, xbh, xbl, xao, xah, xal = x["bo"], x["bh"], x["bl"], x["ao"], x["ah"], x["al"]
    n = len(T) if i1 is None else i1
    E = np.flatnonzero((sS | sB) & M["ok_np"]).tolist()          # bars where a fresh entry may be decided
    sS = sS.tolist()
    cool_ns, eod_ns = COOLDOWN_MIN * MIN_NS, eod_min * MIN_NS
    out, cool, stops, dpnl, killed, i = [], 0, {}, {}, -1, i0
    while True:
        p = bisect.bisect_left(E, i)                              # flat: jump to the next signal bar
        if p == len(E):
            break
        i = E[p]
        if i + 1 >= n:
            break
        d = cday[i]
        if C[i] < cool or stops.get(d, 0) >= DAILY_STOPS or killed == d:
            i += 1
            continue
        side = -1 if sS[i] else 1
        atr0 = atr[i]
        riskb = min(RISK_USD, USD_PT * SL_ATR * atr0)
        deadline = d * DAY_NS + eod_ns
        i_sig = i_dec = i
        legs, se, fills, pend, why = 0, 0.0, [], "leg", None
        last = stop = tp = ex = 0.0
        i += 1
        while i < n:
            if pend == "leg":
                assert i > i_dec, "fill bar must be strictly after the signal bar"
                last = ao[i] if side > 0 else bo[i]
                legs += 1
                se += last
                fills.append(i)
                stop = se / legs - side * riskb / (USD_PT * legs)
                tp = se / legs + side * tp_atr * atr0
                pend = None
            elif pend:
                ex, why = (bo[i] if side > 0 else ao[i]), pend
                break
            if nclose[i]:
                ex, why = (bo[i] if side > 0 else ao[i]), "news"
                break
            for k in (range(sub[0][i], sub[1][i]) if sub else (i,)):
                if side > 0:
                    if xbl[k] <= stop:
                        ex, why = min(stop, xbo[k]) - slip, "stop"
                        break
                    if xbh[k] >= tp:
                        ex, why = tp, "tp"
                        break
                else:
                    if xah[k] >= stop:
                        ex, why = max(stop, xao[k]) + slip, "stop"
                        break
                    if xal[k] <= tp:
                        ex, why = tp, "tp"
                        break
            if why:
                break
            px = ac[i] if side > 0 else bc[i]                     # what a new leg would pay at c(i)
            mk = bc[i] if side > 0 else ac[i]                     # what the open legs would get at c(i)
            if dpnl.get(cday[i], 0.0) + side * (mk * legs - se) * USD_PT <= KILL_USD:
                pend, killed = "kill", cday[i]
            elif C[i] >= deadline:
                pend = "eod"
            elif legs < n_max and sess[i] and not news[i] and atr[i] == atr[i]:
                k1 = legs + 1
                if side * (last - px) >= max(K_STEP * atr[i], STEP_FLOOR) and \
                        side * (px - (se + px) / k1) + riskb / (USD_PT * k1) >= MIN_STOP_GAP:
                    pend, i_dec = "leg", i
            i += 1
        if why is None:
            break                                                # data ended with a basket open: dropped
        t_out = C[i] if why in ("stop", "tp") else T[i]
        pts = side * (ex * legs - se)
        d = T[i] // DAY_NS
        dpnl[d] = dpnl.get(d, 0.0) + pts * USD_PT
        if why == "stop":
            stops[d] = stops.get(d, 0) + 1
        cool = t_out + cool_ns
        out.append((i_sig, fills[0], i, side, legs, pts, why, atr0, riskb, tuple(fills)))
    return out


def frame(M, rows):
    b = pd.DataFrame(rows, columns=["i_sig", "i_in", "i_out", "side", "n", "pts", "reason", "atr0", "riskb", "fills"])
    t = M["time"]
    b["t_in"], b["t_out"] = t[b.i_in.to_numpy()], t[b.i_out.to_numpy()]
    b["usd"] = b.pts * USD_PT
    b["day"], b["month"] = b.t_in.dt.strftime("%Y-%m-%d"), b.t_in.dt.strftime("%Y-%m")
    b["hold_bars"] = (b.i_out - b.i_in).map(float)                # M1 bars, not clock (a close across the daily break shows in gap_min)
    T = np.asarray(M["T"])
    b["gap_min"] = (T[b.i_out.to_numpy()] - T[b.i_out.to_numpy() - 1]) / MIN_NS - 1   # minutes of missing bars before the exit bar
    return b


def audit(M, q, b, n_max, tp_atr):
    """Invariants every basket ledger must satisfy; a violation is a harness fault, not a result."""
    T, C = np.asarray(M["T"]), np.asarray(M["C"])
    isig, iin, iout = b.i_sig.to_numpy(), b.i_in.to_numpy(), b.i_out.to_numpy()
    assert (iin > isig).all() and (iout >= iin).all() and (b.n <= n_max).all() and (b.n >= 1).all()
    assert np.asarray(M["sess"])[isig].all() and not np.asarray(M["news"])[isig].any(), "entry decided outside the session or inside a news window"
    assert (isig[1:] >= iout[:-1]).all() and (C[isig[1:]] - T[iout[:-1]] >= COOLDOWN_MIN * MIN_NS).all(), "baskets overlap or the cooldown was skipped"
    assert (b.atr0 >= MIN_ATR5).all() and np.allclose(b.riskb, np.minimum(RISK_USD, USD_PT * SL_ATR * b.atr0))
    tp, sl = b[b.reason == "tp"], b[b.reason == "stop"]
    assert np.allclose(tp.pts, tp.n * tp_atr * tp.atr0), "a target fill is not VWAP + TP_ATR x atr0 on every leg"
    assert (sl.pts <= -(sl.riskb / USD_PT + q["slip"] * sl.n) + 1e-6).all(), "a stop lost less than RISK_B plus slippage"
    assert (sl.groupby((T[sl.i_out.to_numpy()] // DAY_NS)).size() <= DAILY_STOPS).all(), "more than DAILY_STOPS stop-outs in a UTC day"
    nc = np.flatnonzero(M["nclose"])                              # no basket is carried through the start of a news window
    k = np.searchsorted(nc, iin, "right")
    assert ((k == len(nc)) | (nc[np.minimum(k, len(nc) - 1)] >= iout)).all(), "a basket was open across a news-window start"


def cut(b, lo=None, hi=None):
    k = np.ones(len(b), bool)
    if lo:
        k &= (b.t_in >= pd.Timestamp(lo, tz="UTC")).to_numpy()
    if hi:
        k &= (b.t_in < pd.Timestamp(hi, tz="UTC")).to_numpy()
    return b[k]


def stats(b):
    if not len(b):
        return dict(n=0)
    u = b.usd.to_numpy()
    gp, gl, net = u[u > 0].sum(), -u[u < 0].sum(), u.sum()
    eq = np.r_[0.0, np.cumsum(u)]
    day, mon = b.groupby("day").usd.sum(), b.groupby("month").usd.sum()
    return dict(n=len(b), legs=int(b.n.sum()), win_rate=100 * (u > 0).mean(), pf=gp / gl if gl else np.inf, net=net,
                per_basket=net / len(b), avg_win=u[u > 0].mean() if gp else 0.0, avg_loss=u[u < 0].mean() if gl else 0.0,
                max_dd=(np.maximum.accumulate(eq) - eq).max(), worst_day=day.min(), days=len(day),
                months_pos=f"{int((mon > 0).sum())}/{len(mon)}", top_month_share=100 * mon.max() / net if net > 0 else np.nan,
                atr0=b.atr0.mean(), capped=100 * (b.riskb >= RISK_USD).mean())


def boot(b, B=5000, seed=7):
    """Bootstrap over UTC days (spec 9.3): 95% intervals for PF, net and USD per basket."""
    g = b.assign(gp=b.usd.clip(lower=0), gl=(-b.usd).clip(lower=0), k=1).groupby("day")[["gp", "gl", "usd", "k"]].sum().to_numpy()
    s = g[np.random.default_rng(seed).integers(0, len(g), (B, len(g)))].sum(axis=1)
    f = lambda v: "{:.2f} to {:.2f}".format(*np.percentile(v, [2.5, 97.5]))
    return dict(pf_ci=f(s[:, 0] / s[:, 1]), net_ci=f(s[:, 2]), per_basket_ci=f(s[:, 2] / s[:, 3]), p_net_le_0=100 * (s[:, 2] <= 0).mean())


def control_signals(M, sS, sB, guard, seed):
    """Random signals with the trigger's own count per (calendar month, UTC hour, side), drawn only from bars that pass
    the same validity guard (gap guard, ATR5 valid and >= MIN_ATR5). Only the fade condition is randomised."""
    grp = M["cmonth"] * 24 + M["chour"]
    grp = grp - grp.min()
    r = np.random.default_rng(seed).random(len(grp))
    r[~guard] = 2.0                                              # non-pool bars sort last inside their group
    order = np.lexsort((r, grp))
    gs = grp[order]
    start = np.r_[0, np.flatnonzero(np.diff(gs)) + 1]
    rank = np.arange(len(gs)) - np.repeat(start, np.diff(np.r_[start, len(gs)]))
    ns, nb = np.bincount(grp, sS, grp.max() + 1)[gs], np.bincount(grp, sB, grp.max() + 1)[gs]
    cs, cb = np.zeros(len(grp), bool), np.zeros(len(grp), bool)
    cs[order], cb[order] = rank < ns, (rank >= ns) & (rank < ns + nb)
    assert not (cs & ~guard).any() and not (cb & ~guard).any() and cs.sum() == sS.sum() and cb.sum() == sB.sum()
    return cs, cb


G = {}                                                           # shared with forked workers


def _ctrl(a):
    seed, n_max, tp_atr, cost = a
    cs, cb = control_signals(G["M"], G["sS"], G["sB"], G["guard"], seed)
    b = frame(G["M"], run(G["M"], G["Q"][cost], cs, cb, n_max, tp_atr))
    res = {"seed": seed}
    for name, lo, hi in G["slices"]:
        s = stats(cut(b, lo, hi))
        res.update({f"{name}_{k}": s.get(k, np.nan) for k in ("n", "win_rate", "pf", "net", "per_basket", "atr0", "capped")})
    daily = b.groupby("day").usd.sum().reindex(G["days"], fill_value=0.0).to_numpy()
    return res, daily


def controls(n_max, tp_atr, cost="base"):
    with mp.get_context("fork").Pool(min(12, mp.cpu_count())) as pool:
        r = pool.map(_ctrl, [(s, n_max, tp_atr, cost) for s in range(N_CTRL)])
    return pd.DataFrame([a for a, _ in r]), np.array([d for _, d in r])


# ---- self-tests (run on every execution, before any result) --------------------------------------------------------
def selftest(m):
    # 1. engine arithmetic on hand-built bars: zero spread, ATR 5 -> risk 30 USD, target 5 pts
    def toy(o, h, l, c, n_max=3):
        t = pd.date_range("2026-01-05 02:00", periods=len(o), freq="1min", tz="UTC")
        M = flags(t)
        M["atr"] = [5.0] * len(o)
        q = dict(slip=0.30, bo=o, bh=h, bl=l, bc=c, ao=o, ah=h, al=l, ac=c)
        sB = np.zeros(len(o), bool)
        sB[0] = True
        return run(M, q, np.zeros(len(o), bool), sB, n_max, 1.0)
    r = toy([100, 100, 100], [100, 106, 100], [100, 69, 100], [100, 100, 100])[0]
    assert r[6] == "stop" and abs(r[5] - (-30.3)) < 1e-9 and r[1] == 1 > r[0], r   # stop and target in one bar -> stop; fill bar > signal bar
    r = toy([100, 100, 100], [100, 106, 100], [100, 99, 100], [100, 100, 100])[0]
    assert r[6] == "tp" and abs(r[5] - 5.0) < 1e-9, r
    r = toy([100, 100, 96, 96], [100, 100.5, 103.2, 96], [100, 96, 95.5, 96], [100, 96, 100, 96])[0]
    assert r[4] == 2 and r[6] == "tp" and abs(r[5] - 10.0) < 1e-9, r                # add at 96, VWAP 98, target 103, both legs out
    r = toy([100, 100, 60, 60], [100, 100.5, 60, 60], [100, 99.5, 59, 60], [100, 100, 60, 60], n_max=1)[0]
    assert r[6] == "stop" and abs(r[5] - (-40.3)) < 1e-9, r                         # gap through the stop fills at the open - slippage
    # 2. no look-ahead: corrupt every bar stamped after k; everything at or before k must be unchanged
    w = m.iloc[200_000:215_000].reset_index(drop=True)
    cuts = np.random.default_rng(1).choice(np.arange(3000, len(w) - 10), 40, replace=False)
    assert set(w.time.dt.minute.to_numpy()[cuts] % 5) == {0, 1, 2, 3, 4}             # every position inside the M5 bar is tested
    bad = {False: 0, True: 0}
    for leaky in (False, True):
        ref = indicators(w.time, w.sh, w.sl, w.sc, leaky)
        for k in cuts:
            z = w[["sh", "sl", "sc"]].copy()
            z.iloc[k + 1:] += 500.0
            alt = indicators(w.time, z.sh, z.sl, z.sc, leaky)
            bad[leaky] += not all(np.array_equal(ref[j][:k + 1], alt[j][:k + 1], equal_nan=True) for j in range(4))
    assert bad[False] == 0, "look-ahead: a signal at minute t changed when data after t changed"
    assert bad[True] > 0, "the look-ahead test has no teeth"
    say(f"self-test: engine arithmetic OK (same-bar tie -> stop, target, add, gap-through); look-ahead test: 0/40 cut points "
        f"changed with closed M5 bars, {bad[True]}/40 with the in-progress M5 bar (the known bug, caught)")


# ---- main ------------------------------------------------------------------------------------------------------
def main():
    t0 = _time.time()
    m = load_main()
    say(f"M1 stitched: {len(m):,} bars {m.time.min()} .. {m.time.max()}; mid-only {int((~m.isq).sum()):,}, quoted {int(m.isq.sum()):,}")
    selftest(m)
    atr, sS, sB, guard, probe = indicators(m.time, m.sh, m.sl, m.sc)
    assert probe <= pd.Timedelta(0), probe
    M = flags(m.time)
    M["atr"] = atr.tolist()
    say(f"closed-bar probe: max((last M5 open + 5 min) - c(t)) = {probe} (must be <= 0)")
    ins = M["ok_np"]
    say(f"trigger: SELL on {sS[ins].mean():.1%} / BUY on {sB[ins].mean():.1%} of eligible in-session bars; guard passes {guard[ins].mean():.1%}; "
        f"ATR5 in session: median {np.nanmedian(atr[ins]):.2f}")
    a5 = pd.Series(atr[ins]).groupby(M["time"][ins].strftime("%Y-%m")).median()
    say("ATR5 median by month: " + ", ".join(f"{k} {v:.1f}" for k, v in a5.items()))

    # -- harness check 3 (spec 9.2): trigger parity with the synthesis study, no outcome read
    e = pd.read_csv(XM / "analysis/entries/entries_features.csv")
    e["open_time"] = pd.to_datetime(e.open_time, utc=True, format="ISO8601")
    dec = e[e.click_in_event == 0].reset_index(drop=True)
    Tn = np.asarray(M["T"])
    j = np.searchsorted(Tn, ns(dec.open_time) - MIN_NS, "right") - 1          # last bar CLOSED at the click
    assert (ns(dec.open_time) - (Tn[j] + MIN_NS) >= 0).all()
    hit = np.where(dec.side.eq("SELL"), sS[j], sB[j])
    par = (int(hit[dec.role.eq("first").to_numpy()].sum()), int(hit.sum()))
    say(f"trigger parity: on at the last closed bar for {par[0]} of {int(dec.role.eq('first').sum())} fresh entries and {par[1]} of {len(dec)} decisions (spec: 11 of 27, 39 of 124)")
    assert par == (11, 39), "harness and specification disagree on the trigger"

    # -- price basis: XM deal price vs the OANDA S5 quote of the bar containing the deal (hand-placed market deals only)
    s5 = pd.read_parquet(XM / "xau_s5_2026-11-03_now_ba.parquet")
    dl = pd.read_csv(XM / "deals.csv")
    dl = dl[(dl.symbol == "GOLD") & (dl.reason == "DEAL_REASON_MOBILE") & dl.entryType.isin(["DEAL_ENTRY_IN", "DEAL_ENTRY_OUT"])].copy()
    dl["time"] = pd.to_datetime(dl.time, utc=True, format="ISO8601")
    st = ns(s5.time)
    k = np.searchsorted(st, ns(dl.time), "right") - 1
    okk = (ns(dl.time) - st[k]) < 5 * 10**9
    rows = []
    for typ, sd in (("DEAL_TYPE_BUY", "ask"), ("DEAL_TYPE_SELL", "bid")):
        w = (dl.type == typ).to_numpy() & okk
        ref = (s5[f"{sd}_open"].to_numpy()[k[w]] + s5[f"{sd}_close"].to_numpy()[k[w]]) / 2
        dff = dl.price.to_numpy()[w] - ref
        rows.append(dict(side=f"XM {sd} - OANDA {sd}", n=int(w.sum()), median=np.median(dff), p25=np.percentile(dff, 25), p75=np.percentile(dff, 75),
                         spec_constant=0.06 if sd == "ask" else -0.05))
    md(pd.DataFrame(rows), "Price basis, XM GOLD vs OANDA XAU_USD (hand-placed market deals, S5 bar containing the deal)",
       "The spec's constants (bid -0.05, ask +0.06) are used for the quoted era; the difference from this re-measurement is inside the scatter.")
    assert all(abs(r["median"] - r["spec_constant"]) < 0.15 for r in rows)

    # -- grid x costs, one pass over the whole series each; slices are cut by basket entry time
    Q = {c: quotes(m, c) for c in COSTS}
    bars_tt = m.time[m.time < TEST_END]
    split60 = bars_tt.iloc[int(0.6 * len(bars_tt))].normalize().tz_localize(None).strftime("%Y-%m-%d")
    mid_test = (pd.Timestamp(TRAIN_END) + (pd.Timestamp(TEST_END) - pd.Timestamp(TRAIN_END)) / 2).strftime("%Y-%m-%d")
    SL = [("TRAIN", None, TRAIN_END), ("TEST", TRAIN_END, TEST_END), ("FULL", None, TEST_END), ("WEEK", TEST_END, None)]
    R, rows = {}, []
    for n_max, tp_atr in GRID:
        for c in COSTS:
            b = R[(n_max, tp_atr, c)] = frame(M, run(M, Q[c], sS, sB, n_max, tp_atr))
            audit(M, Q[c], b, n_max, tp_atr)
            for name, lo, hi in SL:
                rows.append(dict(N_MAX=n_max, TP_ATR=tp_atr, cost=c, slice=name, **stats(cut(b, lo, hi))))
    cells = pd.DataFrame(rows)
    cells.to_csv(OUT / "cells.csv", index=False)
    say(f"grid done in {_time.time() - t0:.0f}s; ledger audit passed on all {len(R)} runs (fills after signals, session, news, cooldown, "
        f"stop and target arithmetic, daily stop count)")
    show = ["N_MAX", "TP_ATR", "cost", "slice", "n", "legs", "win_rate", "pf", "net", "per_basket", "avg_win", "avg_loss", "max_dd", "worst_day", "months_pos", "top_month_share"]
    D = GRID[0]
    md(cells[(cells.N_MAX == D[0]) & (cells.TP_ATR == D[1])][show[2:]], "Default cell (N_MAX 3, TP_ATR 1.0) - every cost level and slice",
       "net, per_basket, avg_win, avg_loss, max_dd, worst_day are USD at 0.01 lot per leg, which equals points summed over legs. "
       "win_rate and top_month_share in %. top_month_share is blank when net <= 0. WEEK = 2026-11-04..11 parity week, never part of a pass mark.")
    md(cells[(cells.slice.isin(["TRAIN", "TEST"])) & (cells.cost.isin(["base", "stress"]))][show].sort_values(["slice", "cost"], kind="stable"),
       "All six pre-registered cells, base and stress cost")
    md(cells[(cells.slice.isin(["TRAIN", "TEST"])) & (cells.cost.isin(["rt0.45", "rt0.80"]))][show[:10]].sort_values(["slice", "cost"], kind="stable"),
       "All six cells at the task brief's 0.45 and 0.80 round-trip costs")

    bd = R[(*D, "base")]
    bd.drop(columns=["fills"]).to_csv(OUT / "baskets_default_base.csv", index=False)
    R[(*D, "stress")].drop(columns=["fills"]).to_csv(OUT / "baskets_default_stress.csv", index=False)
    tt = cut(bd, None, TEST_END)

    # -- default cell anatomy (TRAIN + TEST, base cost)
    g = tt.groupby("reason").agg(n=("usd", "size"), win_rate=("usd", lambda u: 100 * (u > 0).mean()), net=("usd", "sum"), avg=("usd", "mean"),
                                 worst=("usd", "min"), hold_bars_median=("hold_bars", "median")).reset_index()
    md(g, "Default cell by exit reason (TRAIN + TEST, base cost)")
    g = tt.groupby("n").agg(baskets=("usd", "size"), win_rate=("usd", lambda u: 100 * (u > 0).mean()), net=("usd", "sum"), avg=("usd", "mean"),
                            stop_share=("reason", lambda r: 100 * (r == "stop").mean())).reset_index().rename(columns={"n": "legs"})
    md(g, "Default cell by number of legs filled (TRAIN + TEST, base cost)")
    g = tt.assign(side=tt.side.map({1: "LONG", -1: "SHORT"})).groupby("side").agg(n=("usd", "size"), win_rate=("usd", lambda u: 100 * (u > 0).mean()),
                                                                               net=("usd", "sum"), avg=("usd", "mean")).reset_index()
    md(g, "Default cell by side (TRAIN + TEST, base cost)")
    mon = pd.concat({c: cut(R[(*D, c)], None, TEST_END).groupby("month").usd.sum() for c in COSTS}, axis=1).reset_index()
    mon.insert(1, "baskets", tt.groupby("month").size().to_numpy())
    mon.insert(1, "slice", np.where(mon.month < TRAIN_END[:7], "TRAIN", "TEST"))
    mon.to_csv(OUT / "monthly.csv", index=False)
    md(mon, "Default cell, net USD by calendar month and cost level")
    worst = tt.usd.min()
    xg = tt[(tt.reason == "eod") & (tt.gap_min > 5)]
    dn, d3 = tt.groupby("day").usd.sum(), tt[tt.reason == "stop"].groupby("day").size()
    say(f"days traded {len(dn)} (TRAIN {cut(tt, None, TRAIN_END).day.nunique()}, TEST {cut(tt, TRAIN_END).day.nunique()}); baskets per day {len(tt) / len(dn):.1f}; "
        f"days ended by the 3-stop brake {int((d3 >= DAILY_STOPS).sum())} ({100 * (d3 >= DAILY_STOPS).sum() / len(dn):.0f}%); day net mean {dn.mean():.2f}, "
        f"median {dn.median():.2f}, positive days {100 * (dn > 0).mean():.0f}%; same-bar fill-and-news-flatten baskets {int(((tt.reason == 'news') & (tt.hold_bars == 0)).sum())}")
    say(f"risk rail: worst basket {worst:.2f} USD; baskets losing more than 31 USD: {int((tt.usd < -31).sum())} of {len(tt)}; "
        f"kill-brake closes {int((tt.reason == 'kill').sum())}; days with 3 stops {int((tt[tt.reason == 'stop'].groupby('day').size() >= 3).sum())}")
    say(f"end-of-day closes that filled across a data gap > 5 min (the daily break or the weekend): {len(xg)} of {int((tt.reason == 'eod').sum())} "
        f"eod closes, net {xg.usd.sum():.2f} USD, worst {xg.usd.min() if len(xg) else 0:.2f}; of these over a weekend (gap > 24 h): {int((xg.gap_min > 1440).sum())}")

    # -- bootstrap over UTC days
    rows = [dict(slice=name, cost=c, **boot(cut(R[(*D, c)], lo, hi))) for name, lo, hi in SL[:3] for c in ("base", "rt0.80", "stress")]
    md(pd.DataFrame(rows), "Default cell, 95% bootstrap intervals over UTC days (5,000 resamples)", "p_net_le_0 = % of resamples with net <= 0.")

    # -- random-entry control, identical management (gate 2); also for the one-leg ablation
    days = sorted(tt.day.unique().tolist() + [d for d in cut(bd, TEST_END).day.unique()])
    G.update(M=M, Q=Q, sS=sS, sB=sB, guard=guard, slices=SL[:3], days=days)
    ctabs = {}
    for cx in (D, (1, 1.0)):
        ctrl, cd = controls(*cx)
        ctrl.to_csv(OUT / f"control_nmax{cx[0]}_tp{cx[1]}_base.csv", index=False)
        if cx == D:
            cdaily = cd
        rows = []
        for name, lo, hi in SL[:3]:
            s = stats(cut(R[(*cx, "base")], lo, hi))
            for k in ("n", "win_rate", "pf", "net", "per_basket", "atr0", "capped"):
                v = ctrl[f"{name}_{k}"].to_numpy()
                rows.append(dict(slice=name, metric=k, real=float(s[k]), ctrl_mean=v.mean(), ctrl_p5=np.percentile(v, 5), ctrl_p50=np.percentile(v, 50),
                                 ctrl_p95=np.percentile(v, 95), real_pctile=100 * (v < s[k]).mean()))
        ctabs[cx] = pd.DataFrame(rows)
        md(ctabs[cx], f"N_MAX {cx[0]}, TP_ATR {cx[1]} vs {N_CTRL} random-signal controls (base cost, identical management, costs and brakes)",
           "Control = same number of signals per calendar month, UTC hour and side, drawn from bars passing the same ATR and gap guard. "
           "real_pctile = % of control draws below the real value. atr0 = mean ATR5 at entry; capped = % of baskets where the 30 USD ceiling binds "
           "(these two describe the exit geometry: if they differ between real and control, the win rates are not comparable; net and per_basket still are).")
    ctab = ctabs[D]
    say(f"controls done in {_time.time() - t0:.0f}s")

    # -- zero-cost diagnostic (not a result): what the management alone does to the trigger before any spread or slippage
    COSTS["zero"] = dict(half=0.0, quote=None, slip=0.0)
    qz, rows = quotes(m, "zero"), []
    for cx in (D, (1, 1.0)):
        bz = frame(M, run(M, qz, sS, sB, *cx))
        for name, lo, hi in SL[:3]:
            s = stats(cut(bz, lo, hi))
            ci = boot(cut(bz, lo, hi))
            rows.append(dict(N_MAX=cx[0], TP_ATR=cx[1], slice=name, n=s["n"], legs=s["legs"], win_rate=s["win_rate"], pf=s["pf"], net=s["net"],
                             per_basket=s["per_basket"], per_basket_ci=ci["per_basket_ci"]))
    md(pd.DataFrame(rows), "Zero-cost diagnostic: mid prices, no spread, no slippage (not tradeable; shows what is left before costs)",
       "per_basket_ci = 95% bootstrap interval over UTC days.")

    # -- pass marks (spec 9.3), default cell only
    def cell(n_max, tp_atr, c, sl):
        return cells[(cells.N_MAX == n_max) & (cells.TP_ATR == tp_atr) & (cells.cost == c) & (cells.slice == sl)].iloc[0]
    te = cut(bd, TRAIN_END, TEST_END)
    monte = te.groupby("month").usd.sum()
    full_m = monte[monte.index != "2026-11"]                                  # November in TEST is two trading days
    p95 = ctab[(ctab.slice == "TEST") & (ctab.metric == "net")].iloc[0]
    neigh = [cell(a, b, "base", "TEST").pf for a, b in GRID[1:]]
    pf = {(c, s): cell(*D, c, s).pf for c in ("base", "stress") for s in ("TRAIN", "TEST")}
    net_te = te.usd.sum()
    gates = [
        ("1 PF >= 1.15 base and >= 1.00 stress, TRAIN and TEST", f"base {pf['base', 'TRAIN']:.2f} / {pf['base', 'TEST']:.2f}, stress {pf['stress', 'TRAIN']:.2f} / {pf['stress', 'TEST']:.2f}",
         min(pf["base", "TRAIN"], pf["base", "TEST"]) >= 1.15 and min(pf["stress", "TRAIN"], pf["stress", "TEST"]) >= 1.00),
        ("2 TEST points above the 95th percentile of 200 controls", f"real {p95.real:.1f} vs control p95 {p95.ctrl_p95:.1f} (mean {p95.ctrl_mean:.1f}); real at percentile {p95.real_pctile:.1f}", p95.real > p95.ctrl_p95),
        ("3 net positive in >= 60% of TEST months, none above 40% of net", f"{int((monte > 0).sum())}/{len(monte)} months positive ({int((full_m > 0).sum())}/{len(full_m)} without the 2-day November); TEST net {net_te:.1f}",
         (monte > 0).mean() >= 0.6 and net_te > 0 and monte.max() / net_te <= 0.4),
        ("4 at least half the neighbours with TEST PF > 1.00 at base", "neighbour PFs " + ", ".join(f"{v:.2f}" for v in neigh), sum(v > 1 for v in neigh) >= len(neigh) / 2),
        ("6 at least 300 baskets in TEST", f"{len(te)}", len(te) >= 300),
    ]
    gt = pd.DataFrame([dict(gate=a, measured=b, result="PASS" if c else "FAIL") for a, b, c in gates])
    md(gt, "Pre-registered pass marks (spec 9.3), default cell")

    # -- the task brief's generic protocol: 60/40 chronological split, cell chosen on TRAIN only, 0.80 cost
    rows = []
    for n_max, tp_atr in GRID:
        a, z = stats(cut(R[(n_max, tp_atr, "rt0.80")], None, split60)), stats(cut(R[(n_max, tp_atr, "rt0.80")], split60, TEST_END))
        rows.append(dict(N_MAX=n_max, TP_ATR=tp_atr, train_n=a["n"], train_pf=a["pf"], train_net=a["net"], test_n=z["n"], test_pf=z["pf"], test_net=z["net"]))
    g6 = pd.DataFrame(rows)
    pick = g6.sort_values("train_pf", ascending=False).iloc[0]
    PK = (int(pick.N_MAX), float(pick.TP_ATR))
    bp = cut(R[(*PK, "rt0.80")], split60, TEST_END)
    half = (pd.Timestamp(split60) + (pd.Timestamp(TEST_END) - pd.Timestamp(split60)) / 2).strftime("%Y-%m-%d")
    h1, h2, mp_ = cut(bp, None, half).usd.sum(), cut(bp, half, None).usd.sum(), bp.groupby("month").usd.sum()
    md(g6, f"Task-brief protocol: first 60% TRAIN (< {split60}), last 40% TEST, 0.80 round-trip cost",
       f"Cell chosen on TRAIN PF alone: N_MAX {PK[0]}, TP_ATR {PK[1]}. Its TEST: PF {pick.test_pf:.2f} (bar 1.15), n {int(pick.test_n)} (bar 200), "
       f"halves {h1:.1f} / {h2:.1f} USD (bar: both positive), months positive {int((mp_ > 0).sum())}/{len(mp_)} (bar 60%), "
       f"largest month share of net {'n/a (net <= 0)' if bp.usd.sum() <= 0 else f'{100 * mp_.max() / bp.usd.sum():.0f}%'} (bar 50%).")
    brief_pass = pick.test_pf >= 1.15 and pick.test_n >= 200 and h1 > 0 and h2 > 0 and (mp_ > 0).mean() >= 0.6 and bp.usd.sum() > 0 and mp_.max() / bp.usd.sum() <= 0.5
    say(f"task-brief bars: {'PASS' if brief_pass else 'FAIL'}; TEST halves of the pre-registered split (default, base): "
        f"{cut(te, None, mid_test).usd.sum():.1f} / {cut(te, mid_test, None).usd.sum():.1f}")
    if PK != D:
        G["slices"] = [("T40", split60, TEST_END)]
        c2, _ = controls(*PK, cost="rt0.80")
        v = c2["T40_net"].to_numpy()
        say(f"control for the TRAIN-chosen cell {PK} on the 40% TEST at 0.80: real net {bp.usd.sum():.1f}, control mean {v.mean():.1f}, "
            f"p5 {np.percentile(v, 5):.1f}, p95 {np.percentile(v, 95):.1f}, real at percentile {100 * (v < bp.usd.sum()).mean():.1f}; "
            f"control PF mean {c2['T40_pf'].mean():.2f} vs real {pick.test_pf:.2f}")

    # -- sensitivity (NOT pre-registered): end-of-day decision at 20:55 so the close fills before the daily break
    M2 = flags(m.time, 20 * 60 + 55)
    M2["atr"] = M["atr"]
    rows = []
    for c in ("base", "rt0.80", "stress"):
        b2 = frame(M2, run(M2, Q[c], sS, sB, *D, eod_min=20 * 60 + 55))
        for name, lo, hi in SL[:2]:
            s, s0 = stats(cut(b2, lo, hi)), stats(cut(R[(*D, c)], lo, hi))
            rows.append(dict(cost=c, slice=name, n=s["n"], pf_eod2055=s["pf"], net_eod2055=s["net"], pf_spec=s0["pf"], net_spec=s0["net"]))
    md(pd.DataFrame(rows), "Sensitivity, not pre-registered: flat by 20:55 UTC instead of the spec's 21:00 rule",
       "The spec's rule decides the close at 21:00:00. OANDA has no 21:00-21:59 UTC bars from mid-March to early November (US summer time), "
       "so the literal rule fills at the 22:00 reopen, or on Sunday after a Friday.")

    # -- S5 re-resolution of exits where S5 quotes exist (2026-11-03 onward)
    w0 = int(np.searchsorted(Tn, at("2026-11-03")))
    lo_, hi_ = np.searchsorted(st, Tn), np.searchsorted(st, Tn + MIN_NS)
    assert (hi_[w0:] > lo_[w0:]).all(), "an M1 bar in the S5 window has no S5 bars"
    first = lo_[w0:]
    say(f"S5 vs M1 consistency in the window: |M1 bid open - first S5 bid open| max {np.abs(m.bo.to_numpy()[w0:] - s5.bid_open.to_numpy()[first]).max():.3f}; "
        f"M1 bid low vs min S5 bid low max diff {np.abs(m.bl.to_numpy()[w0:] - np.minimum.reduceat(s5.bid_low.to_numpy(), first)[:len(first)]).max():.3f}")
    rows = []
    for c in ("base", "stress"):
        bq, aq = COSTS[c]["quote"]
        x = dict(lo=lo_.tolist(), hi=hi_.tolist(), bo=(s5.bid_open - bq).tolist(), bh=(s5.bid_high - bq).tolist(), bl=(s5.bid_low - bq).tolist(),
                 ao=(s5.ask_open + aq).tolist(), ah=(s5.ask_high + aq).tolist(), al=(s5.ask_low + aq).tolist())
        b1 = frame(M, run(M, Q[c], sS, sB, *D, i0=w0))
        b5 = frame(M, run(M, Q[c], sS, sB, *D, x=x, i0=w0))
        ref = cut(R[(*D, c)], "2026-11-03", None)
        assert len(b1) == len(ref) and np.allclose(b1.usd.to_numpy(), ref.usd.to_numpy()), "window run differs from the full run"
        same = len(b1) == len(b5) and (b1.reason.to_numpy() == b5.reason.to_numpy()).all()
        for nm, bb in (("M1", b1), ("S5", b5)):
            s = stats(bb)
            rows.append(dict(cost=c, exits_on=nm, n=s["n"], win_rate=s["win_rate"], pf=s["pf"], net=s["net"], stops=int((bb.reason == "stop").sum()),
                             same_baskets_and_reasons=str(same)))
        if c == "base":
            b5.drop(columns=["fills"]).to_csv(OUT / "baskets_week_s5_base.csv", index=False)
    md(pd.DataFrame(rows), "Exit resolution: M1 bars vs S5 quotes, default cell, 2026-11-03 .. 11-11")

    # -- replication of the trader's real entries, 2026-11-04 .. 11-11 (default cell, base cost)
    tr = pd.read_csv(XM / "trades.csv")
    tr["open_time"] = pd.to_datetime(tr.open_time, utc=True, format="ISO8601")
    wk = cut(bd, TEST_END, None)
    leg_i = np.array([i for f in wk.fills for i in f])
    leg_side = np.array([s for f, s in zip(wk.fills, wk.side) for _ in f])
    leg_first = np.array([j == 0 for f in wk.fills for j, _ in enumerate(f)])
    leg_t = Tn[leg_i]
    tol = 5 * MIN_NS

    def hits(at, aside, bt, bside):                               # for each a: is there a same-side b within +-5 min
        return np.array([bool(((np.abs(bt - t) <= tol) & (bside == s)).any()) for t, s in zip(at, aside)])
    tt_ = ns(tr.open_time)
    ts_ = np.where(tr.side == "SELL", -1, 1)
    dt_, ds_ = ns(dec.open_time), np.where(dec.side == "SELL", -1, 1)
    fr = dec.role.eq("first").to_numpy()
    wkbar = (Tn >= at(TEST_END)) & M["ok_np"]                                   # in-session, non-news bars of the week
    Cn = Tn + MIN_NS

    def chance(bt, bside, aside):                                 # P(a uniformly timed in-session entry of a's side mix hits b)
        cov = {s: np.mean([bool((np.abs(bt[bside == s] - c) <= tol).any()) for c in Cn[wkbar]]) for s in (-1, 1)}
        return 100 * np.mean([cov[s] for s in aside])
    sig_t = {-1: Cn[sS & (Tn >= at(TEST_END))], 1: Cn[sB & (Tn >= at(TEST_END))]}
    st_all, ss_all = np.r_[sig_t[-1], sig_t[1]], np.r_[-np.ones(len(sig_t[-1])), np.ones(len(sig_t[1]))]
    rows = [
        dict(question="strategy legs matched by a real entry (hit rate)", n=len(leg_t), matched=int(hits(leg_t, leg_side, tt_, ts_).sum()),
             pct=100 * hits(leg_t, leg_side, tt_, ts_).mean(), opposite_side_pct=100 * hits(leg_t, -leg_side, tt_, ts_).mean(), chance_pct=chance(tt_, ts_, leg_side)),
        dict(question="strategy first legs matched by a real entry", n=int(leg_first.sum()), matched=int(hits(leg_t[leg_first], leg_side[leg_first], tt_, ts_).sum()),
             pct=100 * hits(leg_t[leg_first], leg_side[leg_first], tt_, ts_).mean(), opposite_side_pct=100 * hits(leg_t[leg_first], -leg_side[leg_first], tt_, ts_).mean(),
             chance_pct=chance(tt_, ts_, leg_side[leg_first])),
        dict(question="real positions explained by a strategy leg", n=len(tr), matched=int(hits(tt_, ts_, leg_t, leg_side).sum()),
             pct=100 * hits(tt_, ts_, leg_t, leg_side).mean(), opposite_side_pct=100 * hits(tt_, -ts_, leg_t, leg_side).mean(), chance_pct=chance(leg_t, leg_side, ts_)),
        dict(question="real decisions explained by a strategy leg", n=len(dec), matched=int(hits(dt_, ds_, leg_t, leg_side).sum()),
             pct=100 * hits(dt_, ds_, leg_t, leg_side).mean(), opposite_side_pct=100 * hits(dt_, -ds_, leg_t, leg_side).mean(), chance_pct=chance(leg_t, leg_side, ds_)),
        dict(question="real fresh entries explained by a strategy leg", n=int(fr.sum()), matched=int(hits(dt_[fr], ds_[fr], leg_t, leg_side).sum()),
             pct=100 * hits(dt_[fr], ds_[fr], leg_t, leg_side).mean(), opposite_side_pct=100 * hits(dt_[fr], -ds_[fr], leg_t, leg_side).mean(), chance_pct=chance(leg_t, leg_side, ds_[fr])),
        dict(question="real positions with the raw trigger on (any bar, +-5 min)", n=len(tr), matched=int(hits(tt_, ts_, st_all, ss_all).sum()),
             pct=100 * hits(tt_, ts_, st_all, ss_all).mean(), opposite_side_pct=100 * hits(tt_, -ts_, st_all, ss_all).mean(), chance_pct=chance(st_all, ss_all, ts_)),
        dict(question="real fresh entries with the raw trigger on (+-5 min)", n=int(fr.sum()), matched=int(hits(dt_[fr], ds_[fr], st_all, ss_all).sum()),
             pct=100 * hits(dt_[fr], ds_[fr], st_all, ss_all).mean(), opposite_side_pct=100 * hits(dt_[fr], -ds_[fr], st_all, ss_all).mean(), chance_pct=chance(st_all, ss_all, ds_[fr])),
    ]
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "replication.csv", index=False)
    md(rep, "Replication, 2026-11-04 .. 11-11: rules vs the trader's real entries (+-5 minutes, same side)",
       "opposite_side_pct = same test with the side flipped (a placebo). chance_pct = expected hit rate of uniformly timed in-session entries with the same side mix.")
    sw = stats(wk)
    day_w = pd.DataFrame({"strategy_usd_0.01lot": wk.groupby("day").usd.sum(), "strategy_baskets": wk.groupby("day").size(),
                          "trader_net_usd": tr.groupby(tr.open_time.dt.strftime("%Y-%m-%d")).net.sum(), "trader_positions": tr.groupby(tr.open_time.dt.strftime("%Y-%m-%d")).size()}).fillna(0).reset_index(names="day")
    md(day_w, "Trade week by day: strategy (default cell, base cost) next to the trader",
       f"Strategy week: {sw['n']} baskets, {sw['legs']} legs, win rate {sw['win_rate']:.1f}%, PF {sw['pf']:.2f}, net {sw['net']:.1f} USD at 0.01 lot per leg. "
       "The trader's daily net is by open date of the position and is at 0.04+ lots with no stop; the two columns are not the same risk.")

    # -- small-account path: 200 and 1,000 USD, rolling start dates (default cell)
    rows = []
    for c in ("base", "rt0.80"):
        bb = cut(R[(*D, c)], None, TEST_END)
        dd_, u = bb.day.to_numpy(), bb.usd.to_numpy()
        starts = np.unique(dd_)
        for eq0 in (200.0, 1000.0):
            floor = RISK_USD + 12.0                                   # cannot fund one more full-risk basket plus margin for 0.03 lots at 1:1000
            ttr, ruined90, n90 = [], 0, 0
            for s in starts:
                k = dd_ >= s
                path = eq0 + np.cumsum(u[k])
                dead = np.flatnonzero(path < floor)
                days_left = (pd.Timestamp(TEST_END) - pd.Timestamp(s)).days
                if len(dead):
                    ttr.append((pd.Timestamp(dd_[k][dead[0]]) - pd.Timestamp(s)).days)
                if days_left >= 90:
                    n90 += 1
                    ruined90 += bool(len(dead)) and ttr[-1] <= 90
            rows.append(dict(cost=c, start_equity=eq0, start_dates=len(starts), ruined_before_data_end=len(ttr), pct=100 * len(ttr) / len(starts),
                             median_days_to_ruin=float(np.median(ttr)) if ttr else np.nan, starts_with_90d=n90, ruined_within_90d_pct=100 * ruined90 / n90))
    md(pd.DataFrame(rows), "Small account at 0.01 lot per leg: equity below 42 USD (one basket's risk plus margin) from every start date",
       "A margin stop-out cannot occur in this candidate (worst floating loss about 31 USD against about 12 USD of margin); 'ruin' here is running out of money to fund the next basket.")

    # -- secondary history, report only (spec 9.1): 2019-01-01 .. 2025-07-15, mid-only, spread 1.5 / 2.5 bp of price
    f = pd.read_parquet(RD / "m3_scalper/xau_m1_full.parquet")
    f = f[(f.time >= "2019-01-01") & (f.time < "2025-07-16")].rename(columns=dict(open="mo", high="mh", low="ml", close="mc")).reset_index(drop=True)
    fa, fS, fB, fg, fp = indicators(f.time, f.mh, f.ml, f.mc)
    assert fp <= pd.Timedelta(0)
    F = flags(f.time)
    F["atr"] = fa.tolist()
    rows = []
    for nm, bp_, sl_ in (("1.5bp", 1.5, 0.30), ("2.5bp", 2.5, 0.60)):
        COSTS[nm] = dict(bp=bp_, slip=sl_)
        b = frame(F, run(F, quotes(f.assign(isq=False), nm), fS, fB, *D))
        for y, gy in b.groupby(b.t_in.dt.year):
            s = stats(gy)
            rows.append(dict(cost=nm, year=y, n=s["n"], win_rate=s["win_rate"], pf=s["pf"], net=s["net"], months_pos=s["months_pos"],
                             guard_pass_pct=100 * fg[F["ok_np"] & (f.time.dt.year == y).to_numpy()].mean()))
        s = stats(b)
        rows.append(dict(cost=nm, year="all", n=s["n"], win_rate=s["win_rate"], pf=s["pf"], net=s["net"], months_pos=s["months_pos"], guard_pass_pct=100 * fg[F["ok_np"]].mean()))
    md(pd.DataFrame(rows), "Secondary history, report only: default cell on 2019-01-01 .. 2025-07-15 (mid-only, proportional spread)",
       "guard_pass_pct = share of in-session bars with ATR5 >= 3.0 pts. The 3-point floor and the 30 USD cap are absolute, so most of 2019-2023 is filtered out.")

    # -- equity curve (static PNG; palette validated with the dataviz skill's validate_palette.js, light surface)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SURF, INK, INK2, GRID_C, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#9a9993"
    plt.rcParams.update({"font.size": 9, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.edgecolor": GRID_C, "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})
    dts = pd.to_datetime(days)
    k = dts < pd.Timestamp(TEST_END)
    dk = np.array(days)[k]
    curve = lambda bb: cut(bb, None, TEST_END).groupby("day").usd.sum().reindex(dk, fill_value=0).cumsum().to_numpy()
    fig, ax = plt.subplots(2, 1, figsize=(11.5, 9), sharex=True, constrained_layout=True)
    cum = np.cumsum(cdaily[:, k], axis=1)
    ax[0].fill_between(dts[k], np.percentile(cum, 5, axis=0), np.percentile(cum, 95, axis=0), color=NEUTRAL, alpha=0.30, lw=0,
                       label=f"{N_CTRL} random-signal controls at base cost, 5th to 95th percentile")
    ax[0].plot(dts[k], np.median(cum, axis=0), color=INK2, lw=1.2, label="control median")
    # cost level is ordered, so one hue stepped light to dark
    for c, col in zip(COSTS_MAIN, ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")):
        y = curve(R[(*D, c)])
        ax[0].plot(dts[k], y, color=col, lw=2, solid_capstyle="round", label=f"XMR-2, {c} cost")
        ax[0].annotate(f"{c}  {y[-1]:,.0f}", (dts[k][-1], y[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
    ax[0].set_title("XMR-2 capped fade basket, default cell (N_MAX 3, target 1.0 x ATR): cumulative USD at 0.01 lot per leg, four cost levels",
                    loc="left", fontsize=10.5)
    # six cells: hue = N_MAX (identity), line style = target size
    for (n_max, tp_atr) in GRID:
        ax[1].plot(dts[k], curve(R[(n_max, tp_atr, "base")]), color={3: "#2a78d6", 2: "#eb6834", 1: "#1baf7a"}[n_max], lw=2,
                   ls="-" if tp_atr == 1.0 else (0, (4, 2)), label=f"N_MAX {n_max}, target {tp_atr} x ATR")
    ax[1].set_title("All six pre-registered cells at base cost (solid: target 1.0 x ATR, dashed: 2.5 x ATR)", loc="left", fontsize=10.5)
    for a_ in ax:
        a_.axhline(0, color=INK2, lw=0.8)
        a_.axvline(pd.Timestamp(TRAIN_END), color=INK2, lw=0.8)
        a_.annotate("TEST from 2026-04-01", (pd.Timestamp(TRAIN_END), 1), xycoords=("data", "axes fraction"), xytext=(5, -4),
                    textcoords="offset points", va="top", fontsize=8, color=INK2)
        a_.annotate("TRAIN", (pd.Timestamp(TRAIN_END), 1), xycoords=("data", "axes fraction"), xytext=(-5, -4),
                    textcoords="offset points", va="top", ha="right", fontsize=8, color=INK2)
        a_.set_ylabel("cumulative USD (= points summed over legs)")
        a_.grid(color=GRID_C, lw=0.8)
        a_.set_axisbelow(True)
        a_.spines[["top", "right"]].set_visible(False)
        a_.margins(x=0.01)
        a_.legend(fontsize=8, frameon=False, loc="lower left")
    ax[0].set_xlim(right=dts[k][-1] + pd.Timedelta(days=38))      # room for the end-of-line labels
    fig.savefig(HERE / "equity.png", dpi=140)
    (OUT / "tables.md").write_text("# XMR-2 result tables (generated by xmr2_backtest.py)\n" + "".join(TABLES))
    say(f"done in {_time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
