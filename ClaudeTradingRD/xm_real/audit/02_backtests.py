"""Audit step 2: independent re-implementation of the three backtests' DEFAULT cells from STRATEGY_SPEC.md,
compared with the numbers on disk, then perturbed (signal +1 bar, cost x2, cost 0, side flipped, own random control).
Nothing is imported from backtest/. Indicators are computed in a streaming loop (bar i sees bars <= i only).
Run: ../../.venv/bin/python 02_backtests.py  -> out/02_backtests.txt   (about 3-4 minutes, pure Python)
"""
import os, json, math, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); RD = os.path.dirname(ROOT)
os.makedirs(f"{HERE}/out", exist_ok=True)
_L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); _L.append(s)

MIN, HOUR, DAY = 60 * 10**9, 3600 * 10**9, 86400 * 10**9
NEWS = ((12 * HOUR + 25 * MIN, 12 * HOUR + 45 * MIN), (13 * HOUR + 25 * MIN, 13 * HOUR + 45 * MIN))
TS = lambda s: pd.Timestamp(s, tz="UTC").value
TRAIN0, TEST0, WEEK0 = TS("2025-07-16"), TS("2026-04-01"), TS("2026-11-04")

# ---------------- data ----------------
a = pd.read_parquet(f"{RD}/xau_m1_oanda.parquet")
b = pd.read_parquet(f"{ROOT}/xau_m1_2026-07-16_now_mba.parquet")
df = pd.concat([a[a.time < pd.Timestamp("2026-07-16", tz="UTC")], b], ignore_index=True)
assert df.time.is_monotonic_increasing and df.time.is_unique
t = pd.DatetimeIndex(df.time).as_unit("ns").asi8
n = len(t); quoted = df.bid_close.notna().to_numpy()
P(f"stitched M1 {n} bars {df.time.iloc[0]} .. {df.time.iloc[-1]} | quoted bars {quoted.sum()} | mid-only {(~quoted).sum()}")

def quotes(mult=1.0):
    """spec 5.2 base at mult=1; the bid-ask distance around its own centre is scaled by `mult` (0 = no spread)."""
    q = {}
    for x, k in zip(("open", "high", "low", "close"), "ohlc"):
        mid = df[x].to_numpy(float)
        b0 = np.where(quoted, df["bid_" + x].to_numpy(float) - 0.05, mid - 0.30)
        a0 = np.where(quoted, df["ask_" + x].to_numpy(float) + 0.06, mid + 0.30)
        if mult != 1.0:
            m = (a0 + b0) / 2; b0, a0 = m - mult * (m - b0), m + mult * (a0 - m)
        q["b" + k], q["a" + k] = b0.tolist(), a0.tolist()
    q["mid"] = df.close.to_numpy(float).tolist(); q["slip"] = 0.30 * mult
    return q

sh, sl, sc = (np.where(quoted, df["bid_" + x].to_numpy(float) - 0.05, df[x].to_numpy(float) - 0.30) for x in ("high", "low", "close"))

# ---------------- indicators, streaming (causal by construction) ----------------
def stream_atr5(t, sh, sl, sc):
    atr = np.full(len(t), np.nan); FIVE = 5 * MIN
    cur = None; prev_c = None; a_ = None; n5 = 0; ntr = 0
    for i in range(len(t)):
        k = t[i] // FIVE
        if cur is not None and cur[0] != k:            # an older bucket whose 5th minute never printed: closed by now
            if prev_c is not None:
                tr = max(cur[1] - cur[2], abs(cur[1] - prev_c), abs(cur[2] - prev_c)); a_ = tr if a_ is None else a_ + (tr - a_) / 14; ntr += 1
            prev_c = cur[3]; n5 += 1; cur = None
        cur = [k, sh[i], sl[i], sc[i]] if cur is None else [k, max(cur[1], sh[i]), min(cur[2], sl[i]), sc[i]]
        if t[i] - k * FIVE == 4 * MIN:                 # this M1 bar's close is the M5 bar's close
            if prev_c is not None:
                tr = max(cur[1] - cur[2], abs(cur[1] - prev_c), abs(cur[2] - prev_c)); a_ = tr if a_ is None else a_ + (tr - a_) / 14; ntr += 1
            prev_c = cur[3]; n5 += 1; cur = None
        if n5 > 100 and ntr >= 14: atr[i] = a_
    return atr

def world(t, sh, sl, sc):
    """Everything the engines read besides quotes, for one bar series. Returns module globals."""
    n = len(t)
    atr = stream_atr5(t.tolist(), sh.tolist(), sl.tolist(), sc.tolist())
    ret5 = np.full(n, np.nan); ret5[5:] = sc[5:] - sc[:-5]
    hi = pd.Series(sh).rolling(15).max().to_numpy(); lo = pd.Series(sl).rolling(15).min().to_numpy()   # window ends at i
    with np.errstate(invalid="ignore", divide="ignore"):
        pos15 = np.where(hi > lo, (sc - lo) / (hi - lo), np.nan)
        gap = np.zeros(n, bool); gap[14:] = (t[14:] - t[:-14]) <= 30 * MIN
        elig = gap & (atr >= 3.0)
        SELL, BUY = elig & (ret5 >= 0.6 * atr) & (pos15 >= 2 / 3), elig & (ret5 <= -0.6 * atr) & (pos15 <= 1 / 3)
    c_ = t + MIN; tod, wk = c_ % DAY, (c_ // DAY + 3) % 7 < 5
    SESS = wk & (tod >= HOUR) & (tod < 21 * HOUR)
    NEWSC = wk & np.logical_or.reduce([(tod >= s) & (tod < e) for s, e in NEWS])
    d0 = t // DAY * DAY
    NCLOSE = np.logical_or.reduce([((t // DAY + 3) % 7 < 5) & (t >= d0 + s) & ~(np.r_[0, t[:-1]] >= d0 + s) for s, _ in NEWS])
    return dict(t=t, n=n, atr=atr, elig=elig, SELL=SELL, BUY=BUY, c_=c_, SESS=SESS, NEWSC=NEWSC, NCLOSE=NCLOSE, T_=t.tolist())

globals().update(world(t, sh, sl, sc))
P(f"in-session bars {SESS.sum()} | trigger rate per side in session (eligible bars): {(SELL[SESS&elig].mean()+BUY[SESS&elig].mean())/2:.1%}")

# ---------------- trigger parity against the raw deals (no file from analysis/) ----------------
raw = json.load(open(f"{ROOT}/deals_raw.json"))["deals"]
ins = sorted([(pd.Timestamp(x["time"]).value, 1 if x["type"] == "DEAL_TYPE_BUY" else -1, x["positionId"]) for x in raw if x.get("entryType") == "DEAL_ENTRY_IN"])
outs = {x["positionId"]: pd.Timestamp(x["time"]).value for x in raw if x.get("entryType") in ("DEAL_ENTRY_OUT", "DEAL_ENTRY_OUT_BY")}
dec = []
for j, (tm, sd, pid) in enumerate(ins):
    if j and sd == ins[j - 1][1] and tm - ins[j - 1][0] <= 30 * 10**9: continue          # same decision (taps <= 30 s apart)
    n_open = sum(1 for (t2, _, p2) in ins if t2 < tm and outs[p2] > tm)
    dec.append((tm, sd, n_open == 0))
bar = np.searchsorted(t, np.array([d[0] for d in dec]) - MIN, "right") - 1               # last M1 bar closed at the click
hit = np.array([(BUY if d[1] > 0 else SELL)[j] for d, j in zip(dec, bar)]); fresh = np.array([d[2] for d in dec])
P(f"TRIGGER PARITY (my indicators, my decisions from deals_raw): on for {hit[fresh].sum()} of {fresh.sum()} fresh and {hit.sum()} of {len(dec)} decisions  [spec/backtests: 11 of 27, 39 of 124]")

# ---------------- C3: single-shot fade, TP 1.5 / SL 1.5 ATR ----------------
def c3(Q, side, tp_atr=1.5, sl_atr=1.5, brakes=True):
    bo, bh, bl, ao, ah, al, slip = Q["bo"], Q["bh"], Q["bl"], Q["ao"], Q["ah"], Q["al"], Q["slip"]
    T = t.tolist(); A = atr.tolist(); sd_ = side.tolist(); out = []
    pos = None; pin = None; pout = None; day = -1; stops = 0; halted = False; cool = -1
    def ok(x):
        tod = x % DAY
        return (x // DAY + 3) % 7 < 5 and HOUR <= tod < 21 * HOUR and not any(s <= tod < e for s, e in NEWS)
    for i in range(n):
        ti = T[i]; closed = None
        if pout is not None: closed = ((bo[i] if pos[0] > 0 else ao[i]), pout, ti); pout = None
        if pin is not None:
            s, sd, a_ = pin; pin = None
            lot = math.floor(38.0 / (100 * (sl_atr * a_ + 0.30)) * 100 + 1e-9) / 100
            if lot >= 0.01 and ok(ti):
                e = ao[i] if sd > 0 else bo[i]; d0 = ti // DAY * DAY
                nw = next((d0 + x for x, _ in NEWS if d0 + x > ti), None)
                pos = (sd, e, e - sd * sl_atr * a_, e + sd * tp_atr * a_, lot, s, i, ti + 60 * MIN, d0 + 21 * HOUR, nw)
        if pos is not None and closed is None:
            sd, e, stp, tgt = pos[:4]
            if pos[9] is not None and ti >= pos[9] and i > pos[6]: closed = ((bo[i] if sd > 0 else ao[i]), "news", ti)
            elif sd > 0:
                if bl[i] <= stp: closed = (min(stp, bo[i]) - slip, "stop", ti + MIN)
                elif bh[i] >= tgt: closed = (tgt, "tp", ti + MIN)
            else:
                if ah[i] >= stp: closed = (max(stp, ao[i]) + slip, "stop", ti + MIN)
                elif al[i] <= tgt: closed = (tgt, "tp", ti + MIN)
        if closed is not None:
            px, how, when = closed
            if when // DAY != day: day, stops, halted = when // DAY, 0, False
            stops += how == "stop"; halted = brakes and stops >= 3; cool = when + 20 * MIN
            out.append((pos[5], pos[6], i, pos[0], pos[1], px, how, pos[4], T[pos[6]])); pos = None
        c = ti + MIN
        if pos is not None:
            if c >= pos[7] or c >= pos[8]: pout = "eod" if c >= pos[8] and pos[8] <= pos[7] else "time"
            continue
        if c // DAY != day: day, stops, halted = c // DAY, 0, False
        if sd_[i] == 0 or halted or c < cool or not ok(c) or i + 1 >= n: continue
        pin = (i, sd_[i], A[i])
    r = pd.DataFrame(out, columns=["sig", "ent", "ex", "side", "entry", "exit", "how", "lot", "t_in"])
    r["pts"] = (r.exit - r.entry) * r.side; r["usd"] = r.pts * 100 * r.lot
    return r

# ---------------- C2: capped fade basket, N_MAX 3, TP 1.0 ATR, 0.01 lot per leg ----------------
def c2(Q, sell, buy, n_max=3, tp_atr=1.0):
    bo, bh, bl, bc, ao, ah, al, ac, slip = Q["bo"], Q["bh"], Q["bl"], Q["bc"], Q["ao"], Q["ah"], Q["al"], Q["ac"], Q["slip"]
    A = atr.tolist(); sS, sB = sell.tolist(), buy.tolist(); sess, news, ncl = SESS.tolist(), NEWSC.tolist(), NCLOSE.tolist()
    out = []; pos = None; pend = None; cool = 0; stops = {}
    for i in range(n):
        ti = T_[i]; c = ti + MIN
        if pos is not None:
            side, legs, se, last, stop, tp, atr0, riskb, deadline, sig, first = pos
            ex = why = None
            if pend == "leg":
                last = ao[i] if side > 0 else bo[i]; legs += 1; se += last
                if first < 0: first = i
                stop = se / legs - side * riskb / legs; tp = se / legs + side * tp_atr * atr0; pend = None
            elif pend:
                ex, why = (bo[i] if side > 0 else ao[i]), pend; pend = None
            if why is None and ncl[i]: ex, why = (bo[i] if side > 0 else ao[i]), "news"
            if why is None:
                if side > 0:
                    if bl[i] <= stop: ex, why = min(stop, bo[i]) - slip, "stop"
                    elif bh[i] >= tp: ex, why = tp, "tp"
                else:
                    if ah[i] >= stop: ex, why = max(stop, ao[i]) + slip, "stop"
                    elif al[i] <= tp: ex, why = tp, "tp"
            if why is not None:
                cool = (c if why in ("stop", "tp") else ti) + 20 * MIN
                if why == "stop": stops[ti // DAY] = stops.get(ti // DAY, 0) + 1
                out.append((sig, first, i, side, legs, side * (ex * legs - se), why, T_[first])); pos = None
            else:
                if c >= deadline: pend = "eod"
                elif legs < n_max and sess[i] and not news[i] and A[i] == A[i]:
                    px = ac[i] if side > 0 else bc[i]
                    if side * (last - px) >= max(0.7 * A[i], 2.0) and side * (px - (se + px) / (legs + 1)) + riskb / (legs + 1) >= 3.0: pend = "leg"
                pos = (side, legs, se, last, stop, tp, atr0, riskb, deadline, sig, first)
                continue
        if (sS[i] or sB[i]) and sess[i] and not news[i] and c >= cool and stops.get(c // DAY, 0) < 3 and i + 1 < n:
            pos = (-1 if sS[i] else 1, 0, 0.0, 0.0, 0.0, 0.0, A[i], min(30.0, 6.0 * A[i]), (c // DAY) * DAY + 21 * HOUR, i, -1); pend = "leg"
    return pd.DataFrame(out, columns=["sig", "ent", "ex", "side", "legs", "pts", "why", "t_in"])

# ---------------- C1: deposit-as-stop averaging fade, per-leg TP 1.0 ATR, sweep to 200 ----------------
def c1(Q, sell, buy, i0, i1, tp_atr=1.0, sweep=True, sweep_open=0):
    bo, bh, bl, bc, ao, ah, al, ac, mid = (Q[k] for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mid"))
    A = atr.tolist(); sS, sB = sell.tolist(), buy.tolist(); sess = SESS.tolist()
    U, MK = 4.0, 0.04 * 100 / 1000
    bal, dep, wd = 200.0, 200.0, 0.0; L, S = [], []; pL = pS = None; waiting = False; wipe_until = 0
    wipes = npos = nwin = 0; gw = gl = 0.0; pos_pnl = 0.0
    def book(side, e, x):
        nonlocal npos, nwin, gw, gl, pos_pnl
        p = side * (x - e) * U; npos += 1; pos_pnl += p
        if p > 0: nwin += 1; gw += p
        elif p < 0: gl -= p
    for i in range(i0, i1):
        if pL is not None: L += [(ao[i], ao[i] + pL[1])] * pL[0]; pL = None
        if pS is not None: S += [(bo[i], bo[i] - pS[1])] * pS[0]; pS = None
        if L or S:
            nL, nS = len(L), len(S); sL, sS_ = sum(p[0] for p in L), sum(p[0] for p in S)
            f_lo = U * ((bl[i] * nL - sL) + (sS_ - al[i] * nS)); f_hi = U * ((bh[i] * nL - sL) + (sS_ - ah[i] * nS))
            low = f_lo <= f_hi
            if bal + (f_lo if low else f_hi) <= 0.20 * abs(nL - nS) * MK * mid[i]:
                for p in L: book(1, p[0], bl[i] if low else bh[i])
                for p in S: book(-1, p[0], al[i] if low else ah[i])
                wipes += 1; bal = 0.0; L, S = [], []; waiting = True; wipe_until = T_[i] + MIN + 60 * MIN
                continue
            keep = []
            for p in L:
                if bh[i] >= p[1]: bal += (p[1] - p[0]) * U; book(1, p[0], p[1])
                else: keep.append(p)
            L = keep; keep = []
            for p in S:
                if al[i] <= p[1]: bal += (p[0] - p[1]) * U; book(-1, p[0], p[1])
                else: keep.append(p)
            S = keep
        if not L and not S:
            if waiting:
                if T_[i] + MIN >= wipe_until: bal = 200.0; dep += 200.0; waiting = False
                else: continue
            elif sweep and bal > 200.0: wd += bal - 200.0; bal = 200.0
        elif sweep_open and not waiting and bal > 200.0 and len(L) + len(S) <= sweep_open:
            # variant (not in the spec): he withdrew with up to 2 positions open on 3 of 7 occasions, taking the balance to ~200
            fl_ = U * ((bc[i] * len(L) - sum(p[0] for p in L)) + (sum(p[0] for p in S) - ac[i] * len(S)))
            if 200.0 + fl_ > 2 * abs(len(L) - len(S)) * MK * mid[i]: wd += bal - 200.0; bal = 200.0
        if sess[i] and i + 1 < i1:
            a_ = A[i]; nL, nS = len(L), len(S)
            eq = bal + U * ((bc[i] * nL - sum(p[0] for p in L)) + (sum(p[0] for p in S) - ac[i] * nS))
            step = max(0.7 * a_, 2.0) if a_ == a_ else None
            k = 0
            if nL == 0: k = 2 if sB[i] else 0
            elif nL < 10 and step is not None and L[-1][0] - ac[i] >= step: k = 1
            if k and (abs(nL + k - nS) < abs(nL - nS) or eq > abs(nL + k - nS) * MK * mid[i]): pL = (k, max(tp_atr * a_, 3.0))
            k = 0
            if nS == 0: k = 2 if sS[i] else 0
            elif nS < 10 and step is not None and bc[i] - S[-1][0] >= step: k = 1
            if k and (abs(nS + k - nL) < abs(nL - nS) or eq > abs(nS + k - nL) * MK * mid[i]): pS = (k, max(tp_atr * a_, 3.0))
    last = i1 - 1; nL, nS = len(L), len(S)
    for p in L: book(1, p[0], bc[last])
    for p in S: book(-1, p[0], ac[last])
    feq = bal + U * ((bc[last] * nL - sum(p[0] for p in L)) + (sum(p[0] for p in S) - ac[last] * nS))
    return dict(owner=wd + feq - dep, dep=dep, wd=wd, wipes=wipes, n=npos, win=nwin / max(npos, 1), pf=gw / gl if gl else float("nan"), pos_pnl=pos_pnl)

# ---------------- helpers ----------------
def pf(x):
    x = np.asarray(x); g, l = x[x > 0].sum(), -x[x < 0].sum(); return g / l if l > 0 else float("nan")
def sl_(r, a_, b_): return r[(r.t_in >= a_) & (r.t_in < b_)]
def shift1(x):
    y = np.zeros_like(x); y[1:] = x[:-1]; return y
def day_shuffle(sell, buy, seed):
    """Own control: each UTC day's in-session trigger bars are re-drawn at random among that day's eligible in-session bars (count per day and side kept)."""
    rng = np.random.default_rng(seed); cs, cb = np.zeros(n, bool), np.zeros(n, bool)
    pool = SESS & ~NEWSC & elig; d = c_ // DAY
    order = np.flatnonzero(pool); starts = np.r_[0, np.flatnonzero(np.diff(d[order])) + 1, len(order)]
    for u, v in zip(starts[:-1], starts[1:]):
        idx = order[u:v]; ns_, nb_ = int(sell[idx].sum()), int(buy[idx].sum())
        pick = rng.permutation(idx)[: ns_ + nb_]; cs[pick[:ns_]] = True; cb[pick[ns_:]] = True
    return cs, cb

Q1, Q2, Q0 = quotes(1.0), quotes(2.0), quotes(0.0)
i_tr0, i_te0, i_wk0 = (int(np.searchsorted(t, x)) for x in (TRAIN0, TEST0, WEEK0))
SIDE = np.where(SESS & ~NEWSC & SELL, -1, np.where(SESS & ~NEWSC & BUY, 1, 0)).astype(int)

# ================= C3 =================
P("\n================ C3 (XMR-3 default: TP 1.5 / SL 1.5 ATR, K 0.6) ================")
def rep3(name, r):
    tr_, te_ = sl_(r, TRAIN0, TEST0), sl_(r, TEST0, WEEK0)
    P(f"  {name:38s} TRAIN n={len(tr_):5d} win={100*(tr_.pts>0).mean():5.1f}% pts={tr_.pts.sum():9.1f} PFusd={pf(tr_.usd):.3f} | TEST n={len(te_):5d} win={100*(te_.pts>0).mean():5.1f}% pts={te_.pts.sum():9.1f} PFusd={pf(te_.usd):.3f} avg={te_.pts.mean():+.3f}")
    return te_
P("  on disk (their grid.csv, spec_base):   TRAIN n= 1009 win= 43.7% pts=  -1018.0 PFusd=0.724 | TEST n=  972 win= 45.5% pts=   -616.2 PFusd=0.777")
base3 = c3(Q1, SIDE); rep3("mine, base cost", base3)
theirs = pd.read_csv(f"{ROOT}/backtest/c3/results/trades_default_spec_base.csv")
same = len(theirs) == len(base3) and np.allclose(theirs.entry, base3.entry) and np.allclose(theirs.exit, base3.exit) and (theirs.how.values == base3.how.replace({"eod": "eod"}).values).all()
P(f"  trade-by-trade vs their trades_default_spec_base.csv: theirs {len(theirs)} mine {len(base3)} identical={same}")
assert (base3.ent > base3.sig).all()
rep3("signal delayed +1 bar", c3(Q1, shift1(SIDE)))
rep3("cost x2 (spread and slippage)", c3(Q2, SIDE))
rep3("cost 0 (no spread, no slippage)", c3(Q0, SIDE))
rep3("side flipped (go WITH the move), base", c3(Q1, -SIDE))
rep3("side flipped, cost 0", c3(Q0, -SIDE))
rep3("brakes off, base", c3(Q1, SIDE, brakes=False))
rep3("brakes off, cost 0", c3(Q0, SIDE, brakes=False))
ctl = []
for sd in range(30):
    cs, cb = day_shuffle(SELL, BUY, 100 + sd); r = c3(Q1, np.where(cs, -1, np.where(cb, 1, 0)))
    ctl.append((sl_(r, TRAIN0, TEST0).pts.sum(), sl_(r, TEST0, WEEK0).pts.sum()))
ctl = np.array(ctl)
P(f"  own control (30 day-shuffles, base): TRAIN pts mean {ctl[:,0].mean():.0f} [p5 {np.percentile(ctl[:,0],5):.0f}, p95 {np.percentile(ctl[:,0],95):.0f}] real pct {100*(ctl[:,0] < sl_(base3,TRAIN0,TEST0).pts.sum()).mean():.0f}"
  f" | TEST mean {ctl[:,1].mean():.0f} [p5 {np.percentile(ctl[:,1],5):.0f}, p95 {np.percentile(ctl[:,1],95):.0f}] real pct {100*(ctl[:,1] < sl_(base3,TEST0,WEEK0).pts.sum()).mean():.0f}")

# ================= C2 =================
P("\n================ C2 (XMR-2 default: N_MAX 3, TP 1.0 ATR, 30 USD cap) ================")
def rep2(name, r):
    tr_, te_ = sl_(r, TRAIN0, TEST0), sl_(r, TEST0, WEEK0)
    P(f"  {name:38s} TRAIN n={len(tr_):5d} win={100*(tr_.pts>0).mean():5.1f}% net={tr_.pts.sum():9.2f} PF={pf(tr_.pts):.2f} | TEST n={len(te_):5d} win={100*(te_.pts>0).mean():5.1f}% net={te_.pts.sum():9.2f} PF={pf(te_.pts):.2f}")
P("  on disk (their cells.csv, base):       TRAIN n= 1641 win= 70.4% net= -3042.62 PF=0.75 | TEST n= 1777 win= 72.8% net= -3069.09 PF=0.76")
base2 = c2(Q1, SELL, BUY); rep2("mine, base cost", base2)
th2 = pd.read_csv(f"{ROOT}/backtest/c2/results/baskets_default_base.csv")
P(f"  basket-by-basket vs their baskets_default_base.csv: theirs {len(th2)} mine {len(base2)} identical={len(th2)==len(base2) and np.allclose(th2.pts, base2.pts) and (th2.i_in.values==base2.ent.values).all()}")
assert (base2.ent > base2.sig).all()
rep2("signal delayed +1 bar", c2(Q1, shift1(SELL), shift1(BUY)))
rep2("cost x2", c2(Q2, SELL, BUY))
rep2("cost 0", c2(Q0, SELL, BUY))
rep2("side flipped, base", c2(Q1, BUY, SELL))
rep2("N_MAX 1 (no averaging), base", c2(Q1, SELL, BUY, n_max=1))
rep2("N_MAX 1, cost 0", c2(Q0, SELL, BUY, n_max=1))
g = sl_(base2, TRAIN0, WEEK0).groupby("legs").pts.agg(["size", "sum", lambda v: 100 * (v > 0).mean()])
P("  by legs filled (conditioning on the path, NOT an ablation): " + "; ".join(f"{k} legs n={int(v['size'])} net={v['sum']:.0f} win={v.iloc[2]:.0f}%" for k, v in g.iterrows()))
x3, x1 = sl_(base2, TRAIN0, WEEK0), sl_(c2(Q1, SELL, BUY, n_max=1), TRAIN0, WEEK0)
P(f"  the ablation that answers 'does averaging cost money': N_MAX 3 net {x3.pts.sum():.0f} over {int(x3.legs.sum())} legs ({x3.pts.sum()/x3.legs.sum():+.2f}/leg) vs N_MAX 1 net {x1.pts.sum():.0f} over {len(x1)} legs ({x1.pts.sum()/len(x1):+.2f}/leg)")

# ================= C1 =================
P("\n================ C1 (XMR-1 default: per-leg TP 1.0 ATR, sweep on, 200 USD deposit) ================")
def rep1(name, Q, s, b_, **kw):
    r1, r2 = c1(Q, s, b_, i_tr0, i_te0, **kw), c1(Q, s, b_, i_te0, i_wk0, **kw)
    P(f"  {name:38s} TRAIN n={r1['n']:6d} win={100*r1['win']:.1f}% PF={r1['pf']:.2f} owner={r1['owner']:10.0f} wipes={r1['wipes']:4d} posPnL={r1['pos_pnl']:10.0f} | TEST n={r2['n']:6d} win={100*r2['win']:.1f}% PF={r2['pf']:.2f} owner={r2['owner']:10.0f} wipes={r2['wipes']:4d} posPnL={r2['pos_pnl']:10.0f}")
    return r1, r2
P("  on disk (their grid.csv, base):        TRAIN n= 11451 win=80.4% PF=0.76 owner=    -61516 wipes= 404 | TEST n= 12462 win=82.5% PF=0.76 owner=    -56784 wipes= 369")
b1 = rep1("mine, base cost", Q1, SELL, BUY)
rep1("signal delayed +1 bar", Q1, shift1(SELL), shift1(BUY))
rep1("cost x2", Q2, SELL, BUY)
rep1("cost 0", Q0, SELL, BUY)
rep1("side flipped (add WITH the move), base", Q1, BUY, SELL)
rep1("sweep off, base", Q1, SELL, BUY, sweep=False)
rep1("sweep also with <=2 positions open", Q1, SELL, BUY, sweep_open=2)
ctl = []
for sd in range(10):
    cs, cb = day_shuffle(SELL, BUY, 500 + sd); r = c1(Q1, cs, cb, i_te0, i_wk0); ctl.append((r["owner"], r["wipes"], r["win"]))
ctl = np.array(ctl)
P(f"  own control (10 day-shuffles, TEST, base): owner mean {ctl[:,0].mean():.0f} [min {ctl[:,0].min():.0f}, max {ctl[:,0].max():.0f}] wipes mean {ctl[:,1].mean():.0f} win {100*ctl[:,2].mean():.1f}%  vs real owner {b1[1]['owner']:.0f} wipes {b1[1]['wipes']}")
wk = c1(Q1, SELL, BUY, int(np.searchsorted(t, TS("2026-11-04 10:06"))), int(np.searchsorted(t, TS("2026-11-11 07:04"))))
P(f"  the trader's own span 11-04 10:06 .. 11-11 07:04: sim n={wk['n']} wipes={wk['wipes']} win={100*wk['win']:.1f}% owner={wk['owner']:.0f}  | real: 178 positions, 7 stop-out events, 75.8%, trading +490.83 (their report: 486 / 21 / 74.3% / -3,824)")

# ================= null: is the C2 / C3 engine a fair game on a driftless walk at zero cost? =================
P("\n================ NULL TEST (driftless +-0.1 tick walk, 150 ticks per M1 bar, real timestamps, zero cost) ================")
REAL_T = t[i_te0:i_te0 + 150000].copy(); res2, res3, res21 = [], [], []
for seed in range(40):
    rng = np.random.default_rng(900 + seed)
    path = 4000 + 0.1 * np.cumsum(rng.integers(0, 2, 150000 * 150, dtype=np.int8) * 2 - 1).reshape(150000, 150)
    o = np.r_[4000.0, path[:-1, -1]]; hh = np.maximum(path.max(1), o); ll = np.minimum(path.min(1), o); cc = path[:, -1].astype(float)
    globals().update(world(REAL_T, hh, ll, cc))
    Qn = {k + x: v.tolist() for k in "ba" for x, v in zip("ohlc", (o, hh, ll, cc))}; Qn["slip"] = 0.0
    side = np.where(SESS & ~NEWSC & SELL, -1, np.where(SESS & ~NEWSC & BUY, 1, 0))
    r3 = c3(Qn, side); r2 = c2(Qn, SELL, BUY); r21 = c2(Qn, SELL, BUY, n_max=1)
    res3.append((len(r3), r3.pts.sum())); res2.append((len(r2), r2.pts.sum())); res21.append((len(r21), r21.pts.sum()))
for nm, rr in (("C3 default", res3), ("C2 N_MAX 3", res2), ("C2 N_MAX 1", res21)):
    rr = np.array(rr); per = rr[:, 1] / rr[:, 0]
    P(f"  {nm}: 40 seeds, mean trades {rr[:,0].mean():.0f}, mean pts per trade/basket {per.mean():+.3f} +- {per.std(ddof=1)/np.sqrt(len(per)):.3f} (s.e.)  [a fair engine gives 0 within ~2 s.e.]")

open(f"{HERE}/out/02_backtests.txt", "w").write("\n".join(_L) + "\n")
