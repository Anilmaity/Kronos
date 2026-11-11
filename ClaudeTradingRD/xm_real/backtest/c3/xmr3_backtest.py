#!/usr/bin/env python
"""XMR-3 "single-shot fade, balanced bracket" - standalone event-driven M1 backtester.

Pre-registered spec: ../../analysis/STRATEGY_SPEC.md (sections 5, 8, 9). Nothing here is tuned.
Run:  /Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python xmr3_backtest.py
Writes results/ (csv, tables.md, equity.png). Deterministic (fixed seeds). Reads the shared inputs, never writes them.

Bars are stamped by OPEN time. c(t) = open(t) + 60 s. A decision at c(t) fills at the open of bar t+1.
Longs open at the ask and close at the bid; shorts open at the bid and close at the ask.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
XM = HERE.parents[1]                      # .../xm_real
RD = XM.parent                            # .../ClaudeTradingRD
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)

# ---- fixed parameters (spec 8.2) -------------------------------------------------------------------------------
MIN_ATR5, RISK_MAX, T_MAX, COOLDOWN, DAILY_STOPS, KILL_USD = 3.0, 38.0, 60, 20, 3, -250.0
GRID = [(1.5, 1.5, 0.6), (2.5, 2.5, 0.6), (1.5, 2.5, 0.6), (1.5, 1.5, 1.0), (2.5, 2.5, 1.0), (1.5, 2.5, 1.0)]  # (TP_ATR, SL_ATR, K_FADE)
DEFAULT = GRID[0]
MIN, HOUR, DAY = 60 * 10**9, 3600 * 10**9, 86400 * 10**9
NEWS = ((12 * HOUR + 25 * MIN, 12 * HOUR + 45 * MIN), (13 * HOUR + 25 * MIN, 13 * HOUR + 45 * MIN))
TS = lambda s: pd.Timestamp(s, tz="UTC")
SEAM, TRAIN0, TEST0, WEEK0 = TS("2026-07-16"), TS("2025-07-16"), TS("2026-04-01"), TS("2026-11-04")
# cost levels. hs = half-spread applied to mid-only data; xm = (bid, ask) widening applied to OANDA quotes where they
# exist (None = ignore the quotes and use mid -/+ hs everywhere); slip = stop slippage against the position.
COSTS = {
    "spec_base": dict(hs=0.30, xm=(0.05, 0.06), slip=0.30),      # spec 5.2 base
    "spec_stress": dict(hs=0.50, xm=(0.25, 0.26), slip=0.60),    # spec 5.2 stress
    "flat_0.45": dict(hs=0.225, xm=None, slip=0.0),              # task: 0.45 pts round trip, optimistic
    "flat_0.80": dict(hs=0.40, xm=None, slip=0.0),               # task: 0.80 pts round trip, realistic
}
N_CTRL, N_BOOT = 200, 2000
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def ns(s):
    return pd.DatetimeIndex(s).as_unit("ns").asi8


def md(df, fmt=None):
    """Tiny markdown table (no tabulate dependency)."""
    fmt = fmt or {}
    f = lambda c, v: fmt[c].format(v) if c in fmt and isinstance(v, (int, float, np.number)) and pd.notna(v) else ("" if (isinstance(v, float) and np.isnan(v)) else str(v))
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(f(c, v) for c, v in zip(df.columns, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


# ---- data ------------------------------------------------------------------------------------------------------
def load_stitched():
    a = pd.read_parquet(RD / "xau_m1_oanda.parquet")
    b = pd.read_parquet(XM / "xau_m1_2026-07-16_now_mba.parquet")
    ov = a.merge(b[["time", "close"]], on="time", suffixes=("", "_b"))
    say(f"seam check: {len(ov)} overlapping M1 bars, max |mid close difference| {np.abs(ov.close - ov.close_b).max():.4f}")
    df = pd.concat([a[a.time < SEAM], b], ignore_index=True).sort_values("time").reset_index(drop=True)
    assert df.time.is_unique and df.time.is_monotonic_increasing
    quoted = df.bid_close.notna().to_numpy()
    # signal series = OANDA bid where quotes exist (same as synthesis/01_trigger_parity.py), mid - 0.30 before; a
    # constant offset cancels in ret5 / ATR / pos15, so the choice only matters for five bars at the seam.
    for x in ("high", "low", "close"):
        df["s_" + x] = np.where(quoted, df["bid_" + x], df[x] - 0.30)
    return df


def quotes(df, hs, xm, slip):
    """Bid/ask OHLC arrays for one cost level."""
    q = {"t": ns(df.time), "slip": slip}
    quoted = df.bid_close.notna().to_numpy() if "bid_close" in df else np.zeros(len(df), bool)
    for x, k in zip(("open", "high", "low", "close"), "ohlc"):
        mid = df[x].to_numpy(float)
        if xm is None or not quoted.any():
            q["b" + k], q["a" + k] = mid - hs, mid + hs
        else:
            q["b" + k] = np.where(quoted, df["bid_" + x].to_numpy(float) - xm[0], mid - hs)
            q["a" + k] = np.where(quoted, df["ask_" + x].to_numpy(float) + xm[1], mid + hs)
    return q


# ---- indicators: closed bars only (spec 5.1, 5.3) -----------------------------------------------------------------
def indicators(time, h, l, c):
    """Row i uses rows <= i only (proved by test_no_lookahead). Returns ret5, atr5, pos15, gap_ok, m5_close (ns)."""
    t = pd.DatetimeIndex(time)
    m5 = pd.DataFrame({"h": h, "l": l, "c": c}, index=t).resample("5min", label="left", closed="left").agg(
        {"h": "max", "l": "min", "c": "last"}).dropna()
    pc = m5.c.shift()
    tr = np.maximum(m5.h - m5.l, np.maximum((m5.h - pc).abs(), (m5.l - pc).abs()))
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()      # Wilder
    atr.iloc[:100] = np.nan                                              # warm-up: first 100 M5 bars discarded
    atr = atr.dropna()
    # an M5 bar opened at T5 is closed once the M1 bar opened at T5 + 4 min has closed  ->  usable from that M1 bar on
    tn, avail = ns(t), ns(atr.index) + 4 * MIN
    j = np.searchsorted(avail, tn, "right") - 1
    atr5 = np.where(j >= 0, atr.to_numpy()[np.clip(j, 0, None)], np.nan) if len(atr) else np.full(len(t), np.nan)
    m5_close = np.where(j >= 0, (avail - 4 * MIN + 5 * MIN)[np.clip(j, 0, None)], np.iinfo(np.int64).min) if len(atr) else np.full(len(t), np.iinfo(np.int64).min)
    cs, hs_, ls = pd.Series(c), pd.Series(h), pd.Series(l)
    hi, lo = hs_.rolling(15).max().to_numpy(), ls.rolling(15).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        pos15 = np.where(hi > lo, (np.asarray(c) - lo) / (hi - lo), np.nan)
    gap_ok = np.r_[np.zeros(14, bool), (tn[14:] - tn[:-14]) <= 30 * MIN][: len(tn)]      # 15 bars inside 30 minutes
    return pd.DataFrame({"ret5": (cs - cs.shift(5)).to_numpy(), "atr5": atr5, "pos15": pos15, "gap_ok": gap_ok, "m5_close": m5_close})


def trigger(ind, k):
    """SELL_SIG, BUY_SIG (spec 5.3) incl. gap guard and MIN_ATR5. NaN compares False."""
    a = ind.atr5.to_numpy()
    with np.errstate(invalid="ignore"):
        ok = ind.gap_ok.to_numpy() & (a >= MIN_ATR5)
        sell = ok & (ind.ret5.to_numpy() >= k * a) & (ind.pos15.to_numpy() >= 2 / 3)
        buy = ok & (ind.ret5.to_numpy() <= -k * a) & (ind.pos15.to_numpy() <= 1 / 3)
    return sell, buy, ok


def clock_ok(x):
    """Session [01:00, 21:00) UTC Mon-Fri and outside the news windows, for int64 ns instants x."""
    tod, dow = x % DAY, (x // DAY + 3) % 7                               # 1970-01-01 was a Thursday
    news = np.zeros(len(x), bool)
    for a, b in NEWS:
        news |= (tod >= a) & (tod < b)
    return (dow < 5) & (tod >= HOUR) & (tod < 21 * HOUR) & ~news


# ---- engine ----------------------------------------------------------------------------------------------------
def first_touch(long, stop, tgt, O, H, L, slip):
    """First stop/target touch over exit-side quote bars (bid for a long, ask for a short). Same bar -> the stop wins.
    Stop fills at min(P, open) - slip (long) / max(P, open) + slip (short); target fills at P. (-1, '', nan) if none."""
    sh, th = ((L <= stop), (H >= tgt)) if long else ((H >= stop), (L <= tgt))
    i_s = int(sh.argmax()) if sh.any() else 10**9
    i_t = int(th.argmax()) if th.any() else 10**9
    if i_s <= i_t and i_s < 10**9:
        return i_s, "stop", (min(stop, O[i_s]) - slip if long else max(stop, O[i_s]) + slip)
    if i_t < 10**9:
        return i_t, "tp", tgt
    return -1, "", np.nan


COLS = ["sig_i", "ent_i", "exit_i", "side", "atr5", "lot", "entry", "stop", "tgt", "exit", "how", "pts", "usd",
        "entry_ns", "exit_ns", "mkt_ns", "mkt_px", "eod_break"]


def run(q, side, atr, tp_atr, sl_atr, eod_literal=False, daily_stops=DAILY_STOPS, kill=KILL_USD):
    """One position at a time. side[t] in {+1 buy, -1 sell, 0}: decision at c(t) (clock/guards already applied)."""
    t, slip, n = q["t"], q["slip"], len(q["t"])
    open_ok = clock_ok(t)                                                # the fill bar must open in session, outside news
    cand = np.flatnonzero(side)
    tc_c = t[cand] + MIN
    out, ci, day, stops, realised, halted = [], 0, -1, 0, 0.0, False
    while ci < len(cand):
        s = int(cand[ci])
        e = s + 1
        if e >= n:
            break
        tc = t[s] + MIN
        if tc // DAY != day:
            day, stops, realised, halted = tc // DAY, 0, 0.0, False
        if halted:                                                       # brake: nothing until the next UTC day
            ci = int(np.searchsorted(tc_c, (day + 1) * DAY))
            continue
        sl, tp = sl_atr * atr[s], tp_atr * atr[s]
        lot = np.floor(RISK_MAX / (100 * (sl + 0.30)) * 100 + 1e-9) / 100
        if lot < 0.01 or not open_ok[e]:
            ci += 1
            continue
        long = side[s] > 0
        if long:
            entry = q["ao"][e]; stop, tgt = entry - sl, entry + tp; O, H, L, C = q["bo"], q["bh"], q["bl"], q["bc"]
        else:
            entry = q["bo"][e]; stop, tgt = entry + sl, entry - tp; O, H, L, C = q["ao"], q["ah"], q["al"], q["ac"]
        # last bar k the position may live through; a market exit then fills at the open of bar k+1
        day0 = t[e] // DAY * DAY
        k, kind = int(np.searchsorted(t, t[e] + (T_MAX - 1) * MIN)), "time"       # first c(u) >= fill + T_MAX
        u = int(np.searchsorted(t, day0 + 21 * HOUR - MIN))                       # first c(u) >= 21:00
        if u <= k:
            k, kind = u, "eod"
        for a, _ in NEWS:                                                          # first bar opening at/after a window start
            if day0 + a > t[e]:
                u = int(np.searchsorted(t, day0 + a)) - 1
                if u < k:
                    k, kind = u, "news"
                break
        if k + 1 >= n:
            break                                                                  # data ends inside the trade: drop it
        x, px, eod_break = k + 1, O[k + 1], False
        if kind == "eod" and not eod_literal and t[k + 1] - (t[k] + MIN) > 5 * MIN:
            px, eod_break = C[k], True                                             # market shut at 21:00 (US summer time): last quote
        mkt_ns = t[k] + MIN if eod_break else t[k + 1]
        mkt_px, exit_ns, how = px, mkt_ns, kind
        i, hit, hpx = first_touch(long, stop, tgt, O[e:k + 1], H[e:k + 1], L[e:k + 1], slip)
        fl = ((C[e:k + 1] - entry) if long else (entry - C[e:k + 1])) * 100 * lot  # floating P&L at each bar close
        kk = np.flatnonzero(realised + fl <= kill)
        if len(kk) and (i < 0 or kk[0] < i):                                       # kill switch: close at the next open, halt the day
            x = e + int(kk[0]) + 1; px, exit_ns, how = O[x], t[x], "kill"
        elif i >= 0:
            x = e + i; px, exit_ns, how = hpx, t[x] + MIN, hit
        assert x >= e > s                                                          # spec 9.2 check 1
        pts = (px - entry) if long else (entry - px)
        usd = pts * 100 * lot
        if exit_ns // DAY != day:                                                  # only after a data gap (early close)
            day, stops, realised, halted = exit_ns // DAY, 0, 0.0, False
        realised += usd
        stops += how == "stop"
        halted = how == "kill" or stops >= daily_stops                           # brakes (a) and (b)
        out.append((s, e, x, 1 if long else -1, atr[s], lot, entry, stop, tgt, px, how, pts, usd, t[e], exit_ns, mkt_ns, mkt_px, eod_break))
        ci = int(np.searchsorted(tc_c, exit_ns + COOLDOWN * MIN))
    tr = pd.DataFrame(out, columns=COLS)
    tr["entry_time"] = pd.to_datetime(tr.entry_ns, utc=True)
    tr["exit_time"] = pd.to_datetime(tr.exit_ns, utc=True)
    return tr


# ---- statistics ------------------------------------------------------------------------------------------------
def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l > 0 else np.nan


def stats(tr):
    if len(tr) == 0:
        return dict(n=0)
    u, p = tr.usd.to_numpy(), tr.pts.to_numpy()
    eq = np.r_[0, np.cumsum(u)]
    dayu = tr.groupby(tr.entry_time.dt.floor("D")).usd.sum()
    mon = tr.groupby(tr.entry_time.dt.strftime("%Y-%m")).usd.sum()
    return dict(n=len(tr), win=(p > 0).mean(), pf_usd=pf(u), pf_pts=pf(p), net_pts=p.sum(), avg_pts=p.mean(), net_usd=u.sum(),
                usd_004lot=4 * p.sum(), maxdd_usd=(np.maximum.accumulate(eq) - eq).max(), worst_day_usd=dayu.min(),
                days=len(dayu), months_pos=f"{int((mon > 0).sum())}/{len(mon)}")


def boot_days(tr, seed=7):
    """95% intervals by resampling UTC days (spec 9.3)."""
    d = tr.entry_time.dt.floor("D")
    g = pd.DataFrame({"gp": tr.usd.clip(lower=0), "gl": (-tr.usd).clip(lower=0), "pts": tr.pts, "n": 1, "w": (tr.pts > 0)}).groupby(d).sum()
    idx = np.random.default_rng(seed).integers(0, len(g), (N_BOOT, len(g)))
    S = {c: g[c].to_numpy(float)[idx].sum(1) for c in g}
    lohi = lambda v: (np.percentile(v, 2.5), np.percentile(v, 97.5))
    return dict(pf=lohi(S["gp"] / S["gl"]), net_usd=lohi(S["gp"] - S["gl"]), avg_pts=lohi(S["pts"] / S["n"]), win=lohi(S["w"] / S["n"]),
                p_net_le0=float(((S["gp"] - S["gl"]) <= 0).mean()))


def window(tr, a, b):
    return tr[(tr.entry_time >= a) & (tr.entry_time < b)]


def matched(ta, sa, tb, sb, tol=5 * MIN):
    """For each a: is there a b on the same side within +-tol? (int64 ns, sides +1/-1)"""
    out = np.zeros(len(ta), bool)
    for s in (1, -1):
        b, m = np.sort(tb[sb == s]), sa == s
        if len(b) and m.any():
            j = np.searchsorted(b, ta[m])
            out[m] = np.minimum(np.abs(ta[m] - b[np.clip(j - 1, 0, len(b) - 1)]), np.abs(b[np.clip(j, 0, len(b) - 1)] - ta[m])) <= tol
    return out


# ---- harness checks (spec 9.2) -----------------------------------------------------------------------------------
def test_no_lookahead(df, n_pts=120, seed=3):
    """Truncation invariance: indicators at bar i computed from rows [0..i] equal those computed from the whole
    series, and equal those computed when every later row is POISONED. So a signal at minute t reads nothing stamped after t."""
    seg = df.iloc[len(df) - 30000:].reset_index(drop=True)
    full = indicators(seg.time, seg.s_high.to_numpy(), seg.s_low.to_numpy(), seg.s_close.to_numpy())
    rng = np.random.default_rng(seed)
    cols = ["ret5", "atr5", "pos15", "gap_ok"]
    for i in rng.integers(2000, len(seg) - 1, n_pts):
        cut = indicators(seg.time[: i + 1], seg.s_high.to_numpy()[: i + 1], seg.s_low.to_numpy()[: i + 1], seg.s_close.to_numpy()[: i + 1])
        assert np.allclose(full.loc[i, cols].to_numpy(float), cut.loc[i, cols].to_numpy(float), equal_nan=True, atol=1e-9), f"look-ahead at row {i}"
        hp, lp, cp = (seg[c].to_numpy().copy() for c in ("s_high", "s_low", "s_close"))
        hp[i + 1:] += 500.0; lp[i + 1:] -= 500.0; cp[i + 1:] += 123.0
        poi = indicators(seg.time, hp, lp, cp)
        assert np.allclose(full.loc[: i, cols].to_numpy(float), poi.loc[: i, cols].to_numpy(float), equal_nan=True, atol=1e-9), f"future data leaks into rows <= {i}"
    say(f"CHECK look-ahead: {n_pts} random truncation + poison points on the last {len(seg)} bars: indicators at t unchanged -> PASS")


def test_engine():
    """Synthetic bars: same-bar stop+target resolves as the stop; fill is at the bar after the signal; time stop at T_MAX."""
    n = 200
    t = ns(pd.date_range("2026-01-05 02:00", periods=n, freq="1min", tz="UTC"))
    flat = np.full(n, 4000.0)
    q = {"t": t, "slip": 0.3, **{k: flat.copy() for k in ("bo", "bh", "bl", "bc")}, **{k: flat + 0.6 for k in ("ao", "ah", "al", "ac")}}
    side, atr = np.zeros(n, np.int8), np.full(n, 4.0)
    side[10] = 1                                                          # buy decided at c(10) -> fill at open of bar 11
    q["bh"][13], q["bl"][13] = 4010.0, 3990.0                             # bar 13 touches both stop (-6) and target (+6)
    tr = run(q, side, atr, 1.5, 1.5)
    r = tr.iloc[0]
    assert len(tr) == 1 and r.ent_i == 11 and r.sig_i == 10 and r.how == "stop" and abs(r.exit - (4000.6 - 6 - 0.3)) < 1e-9
    q["bh"][13], q["bl"][13] = 4000.0, 4000.0                             # nothing touched -> time stop 60 min after the fill
    r = run(q, side, atr, 1.5, 1.5).iloc[0]
    assert r.how == "time" and r.exit_i == 11 + T_MAX and (r.exit_ns - r.entry_ns) == T_MAX * MIN and abs(r.pts + 0.6) < 1e-9
    assert abs(r.lot - 0.06) < 1e-9                                       # 38 / (100 * (6 + 0.3)) = 0.0603 -> 0.06
    say("CHECK engine unit test: next-bar fill, same-bar stop-wins, stop slippage, time stop, lot rounding -> PASS")


def test_parity(df, ind):
    """Spec 9.2 check 3: K=0.6 trigger on at the last closed bar for exactly 11 of 27 fresh entries and 39 of 124 decisions."""
    e = pd.read_csv(XM / "analysis/entries/entries_features.csv")
    d = e[e.click_in_event == 0].reset_index(drop=True)
    click = ns(pd.to_datetime(d.open_time, utc=True, format="ISO8601"))
    t = ns(df.time)
    j = np.searchsorted(t, click - MIN, "right") - 1                      # last M1 bar that had closed at the click
    assert ((click - (t[j] + MIN)) >= 0).all()
    sell, buy, _ = trigger(ind, 0.6)
    hit = np.where(d.side.eq("SELL").to_numpy(), sell[j], buy[j])
    n_all, n_first = int(hit.sum()), int(hit[d.role.eq("first").to_numpy()].sum())
    ok = (n_first, n_all) == (11, 39)
    say(f"CHECK trigger parity: on for {n_first} of {int(d.role.eq('first').sum())} fresh entries and {n_all} of {len(d)} decisions (spec: 11 of 27, 39 of 124) -> {'PASS' if ok else 'FAIL'}")
    assert ok, "harness trigger disagrees with the specification"


def measure_basis():
    """XM deal price minus OANDA same-side S5 quote at the deal instant (BUY deals vs ask, SELL deals vs bid)."""
    s5 = pd.read_parquet(XM / "xau_s5_2026-11-03_now_ba.parquet")
    d = pd.read_csv(XM / "deals.csv")
    d = d[d.symbol.notna()].copy()
    dt, t5 = ns(pd.to_datetime(d.time, utc=True, format="ISO8601")), ns(s5.time)
    i = np.searchsorted(t5, dt, "right") - 1
    age = (dt - t5[i]) / 1e9
    buy = d.type.eq("DEAL_TYPE_BUY").to_numpy()
    o = np.where(buy, s5.ask_open.to_numpy()[i], s5.bid_open.to_numpy()[i])
    c = np.where(buy, s5.ask_close.to_numpy()[i], s5.bid_close.to_numpy()[i])
    d["basis"] = d.price.to_numpy() - (o + (c - o) * np.clip(age / 5, 0, 1))
    d["buy"], d["age"] = buy, age
    k = d[(d.age < 5) & ~d.reason.eq("DEAL_REASON_SO")]                   # inside an existing S5 bar, not a margin stop-out
    rows = []
    for name, g in (("SELL deals vs OANDA bid", k[~k.buy]), ("BUY deals vs OANDA ask", k[k.buy]),
                    ("stop-out deals (excluded above)", d[d.reason.eq("DEAL_REASON_SO") & (d.age < 5)])):
        rows.append(dict(what=name, n=len(g), median=g.basis.median(), mean=g.basis.mean(), sd=g.basis.std(),
                         p05=g.basis.quantile(.05), p95=g.basis.quantile(.95)))
    return pd.DataFrame(rows)


# ---- main --------------------------------------------------------------------------------------------------------
def main():
    T = []                                                                # markdown blocks -> results/tables.md
    df = load_stitched()
    t = ns(df.time)
    say(f"stitched M1: {len(df)} bars {df.time.iloc[0]} .. {df.time.iloc[-1]}; quoted (bid/ask) from {SEAM.date()}: {int(df.bid_close.notna().sum())} bars")
    basis = measure_basis()
    basis.to_csv(OUT / "basis.csv", index=False)
    T.append("### T0. Price basis, XM GOLD minus OANDA XAU_USD (S5 quote at the deal instant)\n\n" + md(basis, {c: "{:+.3f}" for c in ("median", "mean", "sd", "p05", "p95")}))

    ind = indicators(df.time, df.s_high.to_numpy(), df.s_low.to_numpy(), df.s_close.to_numpy())
    # --- harness checks, before any result is read ---
    test_no_lookahead(df)
    probe = (ind.m5_close.to_numpy() - (t + MIN))[ind.atr5.notna().to_numpy()]      # only where an M5 bar is in use
    late = int((probe > 0).sum())
    say(f"CHECK closed-bar probe: (last M5 open + 5 min) - c(t) over {len(probe)} bars: max {int(probe.max() / 1e9)} s, positive on {late} -> {'PASS' if late == 0 else 'FAIL'}")
    assert late == 0
    test_engine()
    test_parity(df, ind)

    atr = ind.atr5.to_numpy()
    elig = clock_ok(t + MIN)                                              # decision instant c(t) in session, outside news
    sides, okbar = {}, None
    for k in (0.6, 1.0):
        sell, buy, okbar = trigger(ind, k)
        assert not (sell & buy).any()
        sides[k] = np.where(elig & sell, -1, np.where(elig & buy, 1, 0)).astype(np.int8)
    WIN = {"TRAIN": (TRAIN0, TEST0), "TEST": (TEST0, WEEK0), "FULL": (TRAIN0, WEEK0), "WEEK": (WEEK0, TS("2026-11-12"))}
    insess = elig & okbar
    for w in ("TRAIN", "TEST", "WEEK"):
        m = (df.time >= WIN[w][0]).to_numpy() & (df.time < WIN[w][1]).to_numpy()
        say(f"{w}: {int(m.sum())} M1 bars, {df.time[m].dt.date.nunique()} dates, median ATR5 {np.nanmedian(atr[m]):.2f}, "
            f"in-session bars with ATR5>=3: {int((m & insess).sum())} ({(m & elig & (atr >= MIN_ATR5)).sum() / max((m & elig).sum(), 1):.0%} of in-session), "
            f"K0.6 trigger rate per side {(sides[0.6][m & insess] != 0).mean() / 2:.1%}")

    # --- grid: 6 cells x 4 cost levels, one continuous run each (state resets daily, so windows are independent) ---
    Q = {name: quotes(df, **c) for name, c in COSTS.items()}
    runs, rows = {}, []
    for cell in GRID:
        for cn in COSTS:
            tr = run(Q[cn], sides[cell[2]], atr, cell[0], cell[1])
            runs[cell, cn] = tr
            for w, (a, b) in WIN.items():
                rows.append(dict(cell=f"TP{cell[0]}/SL{cell[1]}/K{cell[2]}", cost=cn, window=w, **stats(window(tr, a, b))))
    grid = pd.DataFrame(rows)
    grid.to_csv(OUT / "grid.csv", index=False)
    F = {"win": "{:.1%}", "pf_usd": "{:.3f}", "pf_pts": "{:.3f}", "net_pts": "{:+.1f}", "avg_pts": "{:+.3f}", "net_usd": "{:+.0f}",
         "usd_004lot": "{:+.0f}", "maxdd_usd": "{:.0f}", "worst_day_usd": "{:+.0f}"}
    dname = f"TP{DEFAULT[0]}/SL{DEFAULT[1]}/K{DEFAULT[2]}"
    T.append("### T1. Default cell (TP 1.5 ATR / SL 1.5 ATR / K_FADE 0.6): every window at every cost level\n\n"
             + md(grid[grid.cell == dname].drop(columns="cell"), F))
    T.append("### T2. All six pre-registered cells, TRAIN and TEST, spec base and spec stress cost\n\n"
             + md(grid[grid.cost.isin(["spec_base", "spec_stress"]) & grid.window.isin(["TRAIN", "TEST"])].drop(columns=["usd_004lot", "days"]), F))
    T.append("### T3. All six cells at the task's flat round-trip costs (0.45 and 0.80 pts), TRAIN and TEST\n\n"
             + md(grid[grid.cost.isin(["flat_0.45", "flat_0.80"]) & grid.window.isin(["TRAIN", "TEST"])].drop(columns=["usd_004lot", "days"]), F))

    base, stress = runs[DEFAULT, "spec_base"], runs[DEFAULT, "spec_stress"]
    base.drop(columns=["entry_ns", "exit_ns", "mkt_ns"]).to_csv(OUT / "trades_default_spec_base.csv", index=False)
    stress.drop(columns=["entry_ns", "exit_ns", "mkt_ns"]).to_csv(OUT / "trades_default_spec_stress.csv", index=False)
    assert all((r.ent_i > r.sig_i).all() for r in runs.values())
    say(f"default/spec_base: {len(base)} trades; exits {base.how.value_counts().to_dict()}; lots {base.lot.min():.2f}-{base.lot.max():.2f} (median {base.lot.median():.2f}); "
        f"risk at stop USD {((base.atr5 * DEFAULT[1] + 0.3) * 100 * base.lot).min():.1f}-{((base.atr5 * DEFAULT[1] + 0.3) * 100 * base.lot).max():.1f}; "
        f"EOD exits filled at the last quote before a market break: {int(base.eod_break.sum())}")

    # how often M1 resolution had to break a same-bar tie (the only place finer data could change an outcome)
    qb, st = Q["spec_base"], base[base.how == "stop"]
    xi, lg = st.exit_i.to_numpy(), (st.side > 0).to_numpy()
    both = np.where(lg, qb["bh"][xi] >= st.tgt.to_numpy(), qb["al"][xi] <= st.tgt.to_numpy())
    say(f"same-bar ties: {int(both.sum())} of {len(st)} stop exits (default, spec base) also had the target inside the same M1 bar and were booked as stops; "
        f"end-of-day exits in all 24 runs: {sum(int((r.how == 'eod').sum()) for r in runs.values())}, of which filled at the last quote before a break: {sum(int(r.eod_break.sum()) for r in runs.values())}")

    # --- default cell: intervals, composition ---
    rows = []
    for cn in COSTS:
        for w in ("TRAIN", "TEST"):
            x = window(runs[DEFAULT, cn], *WIN[w]); b = boot_days(x)
            se = x.pts.std() / np.sqrt(len(x))
            rows.append(dict(cost=cn, window=w, n=len(x), pf_usd=pf(x.usd.to_numpy()), pf_ci95=f"{b['pf'][0]:.3f} .. {b['pf'][1]:.3f}",
                             net_usd=x.usd.sum(), net_usd_ci95=f"{b['net_usd'][0]:+.0f} .. {b['net_usd'][1]:+.0f}", avg_pts=x.pts.mean(),
                             avg_pts_ci95=f"{b['avg_pts'][0]:+.3f} .. {b['avg_pts'][1]:+.3f}", p_net_le0=b["p_net_le0"], sd_pts=x.pts.std(),
                             mde_pts_80pct=2.8 * se))
    T.append("### T4. Default cell: 95% intervals from a bootstrap over UTC days (2000 resamples); MDE = 2.8 x SE of mean points per trade\n\n"
             + md(pd.DataFrame(rows), {"pf_usd": "{:.3f}", "net_usd": "{:+.0f}", "avg_pts": "{:+.3f}", "p_net_le0": "{:.1%}", "sd_pts": "{:.2f}", "mde_pts_80pct": "{:.3f}"}))
    rows = []
    for w in ("TRAIN", "TEST"):
        x = window(base, *WIN[w])
        for name, g in [("all", x)] + [(f"exit={h}", x[x.how == h]) for h in ("tp", "stop", "time", "eod", "news", "kill")] + [("long", x[x.side > 0]), ("short", x[x.side < 0])]:
            if len(g):
                rows.append(dict(window=w, subset=name, n=len(g), share=len(g) / len(x), win=(g.pts > 0).mean(), avg_pts=g.pts.mean(), net_pts=g.pts.sum(), net_usd=g.usd.sum()))
        br = x[x.how.isin(["tp", "stop"])]
        rows.append(dict(window=w, subset="target-before-stop among bracket exits", n=len(br), share=len(br) / len(x), win=(br.how == "tp").mean(), avg_pts=br.pts.mean(), net_pts=br.pts.sum(), net_usd=br.usd.sum()))
    T.append("### T5. Default cell at spec base cost: exit mix and sides\n\n" + md(pd.DataFrame(rows), {"share": "{:.1%}", "win": "{:.1%}", "avg_pts": "{:+.3f}", "net_pts": "{:+.1f}", "net_usd": "{:+.0f}"}))

    # --- TEST months and halves ---
    rows = []
    for cn in ("spec_base", "spec_stress", "flat_0.80"):
        x = window(runs[DEFAULT, cn], *WIN["TEST"])
        g = x.groupby(x.entry_time.dt.strftime("%Y-%m")).agg(n=("pts", "size"), win=("pts", lambda v: (v > 0).mean()), net_pts=("pts", "sum"), net_usd=("usd", "sum"), pf_usd=("usd", lambda v: pf(v.to_numpy())))
        g.insert(0, "cost", cn)
        rows.append(g.reset_index(names="month"))
    monthly = pd.concat(rows)
    monthly.to_csv(OUT / "monthly_test_default.csv", index=False)
    T.append("### T6. Default cell, TEST by calendar month (2026-11 holds two trading days, 11-02 and 11-03)\n\n" + md(monthly, {"win": "{:.1%}", "net_pts": "{:+.1f}", "net_usd": "{:+.0f}", "pf_usd": "{:.3f}"}))
    mid_test = TEST0 + (WEEK0 - TEST0) / 2
    halves = {cn: (window(runs[DEFAULT, cn], TEST0, mid_test).usd.sum(), window(runs[DEFAULT, cn], mid_test, WEEK0).usd.sum()) for cn in COSTS}
    say(f"TEST halves split at {mid_test}: " + "; ".join(f"{cn} {a:+.0f} / {b:+.0f}" for cn, (a, b) in halves.items()))

    # --- random-signal control on TEST (gate 2): same rate per UTC hour x calendar month x side, identical management ---
    def control(k, wname, cn, n_draws, seed, **kw):
        a, b = WIN[wname]
        m = (df.time >= a).to_numpy() & (df.time < b).to_numpy()
        E = m & insess
        key = (df.time.dt.year * 12 + df.time.dt.month).to_numpy() * 24 + df.time.dt.hour.to_numpy()
        _, cid = np.unique(key, return_inverse=True)
        nE = np.bincount(cid, E)
        ps = np.bincount(cid, E & (sides[k] < 0)) / np.maximum(nE, 1)
        pb = np.bincount(cid, E & (sides[k] > 0)) / np.maximum(nE, 1)
        rng, res = np.random.default_rng(seed), []
        for _ in range(n_draws):
            u = rng.random(len(E))
            sd = np.where(E & (u < ps[cid]), -1, np.where(E & (u < ps[cid] + pb[cid]), 1, 0)).astype(np.int8)
            res.append(run(Q[cn], sd, atr, DEFAULT[0], DEFAULT[1], **kw))
        return res

    real_test = window(base, *WIN["TEST"])
    summ = lambda c: dict(n=len(c), win=(c.pts > 0).mean(), pf_usd=pf(c.usd.to_numpy()), net_pts=c.pts.sum(), avg_pts=c.pts.mean(), net_usd=c.usd.sum())
    rows, ctrl, cs, rs = [], None, None, None
    for w, seed in (("TRAIN", 5), ("TEST", 11)):
        cdraws = control(0.6, w, "spec_base", N_CTRL, seed)
        cst, rst = pd.DataFrame([summ(c) for c in cdraws]), summ(window(base, *WIN[w]))
        cst.to_csv(OUT / f"control_{w.lower()}_default.csv", index=False)
        rows += [dict(window=w, metric=c, real=rst[c], ctrl_mean=cst[c].mean(), ctrl_p05=cst[c].quantile(.05), ctrl_median=cst[c].median(), ctrl_p95=cst[c].quantile(.95),
                      real_percentile=(cst[c] < rst[c]).mean() * 100) for c in cst.columns]
        ctrl, cs, rs = cdraws, cst, rst                                   # TEST is last: the gate uses TEST only
    T.append(f"### T7. Default cell vs {N_CTRL} random-signal controls at spec base cost (same firing rate per UTC hour x calendar month x side; identical exits, sizing, brakes). The gate reads TEST net_pts only\n\n"
             + md(pd.DataFrame(rows), {c: "{:.3f}" for c in ("real", "ctrl_mean", "ctrl_p05", "ctrl_median", "ctrl_p95")} | {"real_percentile": "{:.1f}"}))
    gate2 = rs["net_pts"] > cs.net_pts.quantile(.95)

    # --- dose-response (gate 5) ---
    rows = []
    for w in ("TRAIN", "TEST"):
        a6, a10 = window(runs[GRID[0], "spec_base"], *WIN[w]), window(runs[GRID[3], "spec_base"], *WIN[w])
        w6, w10 = (a6.pts > 0).mean(), (a10.pts > 0).mean()
        se = np.sqrt(w6 * (1 - w6) / len(a6) + w10 * (1 - w10) / len(a10))
        rows.append(dict(window=w, n_K06=len(a6), win_K06=w6, avg_pts_K06=a6.pts.mean(), n_K10=len(a10), win_K10=w10, avg_pts_K10=a10.pts.mean(),
                         win_diff_pp=(w10 - w6) * 100, se_pp=se * 100, higher=w10 > w6))
    dose = pd.DataFrame(rows)
    T.append("### T8. Dose-response at TP 1.5 / SL 1.5, spec base cost: K_FADE 1.0 against 0.6 (SE is binomial, trades treated as independent)\n\n"
             + md(dose, {"win_K06": "{:.1%}", "win_K10": "{:.1%}", "avg_pts_K06": "{:+.3f}", "avg_pts_K10": "{:+.3f}", "win_diff_pp": "{:+.2f}", "se_pp": "{:.2f}"}))

    # --- gates ---
    g = lambda cell, cn, w, col: grid[(grid.cell == f"TP{cell[0]}/SL{cell[1]}/K{cell[2]}") & (grid.cost == cn) & (grid.window == w)][col].iloc[0]
    mb = monthly[monthly.cost == "spec_base"]
    tnet = mb.net_usd.sum()
    neigh = [g(c, "spec_base", "TEST", "pf_usd") for c in GRID[1:]]
    gates = [
        ("1", "PF >= 1.15 base and >= 1.00 stress, TRAIN and TEST (USD PF)",
         f"TRAIN {g(DEFAULT, 'spec_base', 'TRAIN', 'pf_usd'):.3f} / {g(DEFAULT, 'spec_stress', 'TRAIN', 'pf_usd'):.3f}; TEST {g(DEFAULT, 'spec_base', 'TEST', 'pf_usd'):.3f} / {g(DEFAULT, 'spec_stress', 'TEST', 'pf_usd'):.3f}",
         all(g(DEFAULT, "spec_base", w, "pf_usd") >= 1.15 and g(DEFAULT, "spec_stress", w, "pf_usd") >= 1.00 for w in ("TRAIN", "TEST"))),
        ("2", f"TEST total points above the 95th percentile of {N_CTRL} random controls",
         f"real {rs['net_pts']:+.1f} vs control p95 {cs.net_pts.quantile(.95):+.1f} (real at percentile {(cs.net_pts < rs['net_pts']).mean() * 100:.1f})", bool(gate2)),
        ("3", ">= 60% of TEST months net positive and no month > 40% of TEST net",
         f"{int((mb.net_usd > 0).sum())} of {len(mb)} months positive; TEST net {tnet:+.0f} USD" + (f"; largest month {mb.net_usd.max() / tnet:.0%} of net" if tnet > 0 else " (not positive, so the share test cannot be met)"),
         bool((mb.net_usd > 0).mean() >= 0.6 and tnet > 0 and mb.net_usd.max() / tnet <= 0.4)),
        ("4", "At least half of the 5 neighbouring cells with TEST PF > 1.00 at base cost",
         f"{sum(x > 1 for x in neigh)} of 5 (PFs {', '.join(f'{x:.3f}' for x in neigh)})", sum(x > 1 for x in neigh) >= 3),
        ("5", "K_FADE 1.0 win rate above K_FADE 0.6 on TRAIN and on TEST",
         "; ".join(f"{r.window} {r.win_K10:.1%} vs {r.win_K06:.1%}" for r in dose.itertuples()), bool(dose.higher.all())),
        ("6", "At least 300 trades in TEST", f"{rs['n']}", rs["n"] >= 300),
    ]
    gt = pd.DataFrame(gates, columns=["gate", "requirement (spec 9.3, default cell)", "measured", "pass"])
    gt["pass"] = np.where(gt["pass"], "PASS", "FAIL")
    T.append("### T9. Pre-registered pass marks (spec 9.3), default cell\n\n" + md(gt))
    f80, m80 = window(runs[DEFAULT, "flat_0.80"], *WIN["TEST"]), monthly[monthly.cost == "flat_0.80"]
    n80 = m80.net_usd.sum()
    task = [
        ("TEST PF >= 1.15 at 0.80 cost", f"{pf(f80.usd.to_numpy()):.3f}", pf(f80.usd.to_numpy()) >= 1.15),
        ("Positive in both halves of TEST", f"{halves['flat_0.80'][0]:+.0f} / {halves['flat_0.80'][1]:+.0f} USD", min(halves["flat_0.80"]) > 0),
        (">= 60% positive TEST months", f"{int((m80.net_usd > 0).sum())} of {len(m80)}", (m80.net_usd > 0).mean() >= 0.6),
        ("No single month above half of net", f"TEST net {n80:+.0f} USD" + (f"; largest month {m80.net_usd.max() / n80:.0%}" if n80 > 0 else " (not positive)"), bool(n80 > 0 and m80.net_usd.max() / n80 <= 0.5)),
        ("n >= 200 TEST trades", f"{len(f80)}", len(f80) >= 200),
    ]
    tt = pd.DataFrame(task, columns=["bar (task brief, flat 0.80 pts round trip)", "measured", "pass"])
    tt["pass"] = np.where(tt["pass"], "PASS", "FAIL")
    T.append("### T10. The task brief's generic bars, default cell\n\n" + md(tt))
    best = grid[(grid.cost == "spec_base") & (grid.window == "TRAIN")].sort_values("pf_usd", ascending=False).iloc[0]
    bt = grid[(grid.cost == "spec_base") & (grid.window == "TEST") & (grid.cell == best.cell)].iloc[0]
    say(f"best TRAIN cell at spec base: {best.cell} PF {best.pf_usd:.3f} (n {best.n}); its TEST: PF {bt.pf_usd:.3f}, n {bt.n}, net {bt.net_usd:+.0f} USD")

    # --- where the daily-stop brake puts the trades ---
    bd = window(base, *WIN["FULL"])
    dd = bd.groupby(bd.entry_time.dt.floor("D")).agg(n=("pts", "size"), stops=("how", lambda v: (v == "stop").sum()), last=("exit_time", "max"))
    h3 = dd[dd.stops >= DAILY_STOPS]["last"]
    say(f"brake: {len(h3)} of {len(dd)} trading days ({len(h3) / len(dd):.1%}) end on the third stop-out, median at {(h3.dt.hour + h3.dt.minute / 60).median():.1f} h UTC; "
        f"trades per day median {dd.n.median():.0f}; kill-switch exits in all 24 runs: {sum(int((r.how == 'kill').sum()) for r in runs.values())}")
    # --- DIAGNOSTIC, not pre-registered, not a pass mark: the same entry and bracket with the daily brakes off, all hours ---
    BLOCKS = (("all 01-21", 1, 21), ("01-07", 1, 7), ("07-12", 7, 12), ("12-16", 12, 16), ("16-21", 16, 21))
    blk = lambda x, a, b: x[(x.entry_time.dt.hour >= a) & (x.entry_time.dt.hour < b)]
    free = run(Q["spec_base"], sides[0.6], atr, *DEFAULT[:2], daily_stops=10**9, kill=-1e18)
    rows = []
    for w, seed in (("TRAIN", 31), ("TEST", 37)):
        cf = control(0.6, w, "spec_base", 100, seed, daily_stops=10**9, kill=-1e18)
        for name, a, b in BLOCKS:
            on, off = blk(window(base, *WIN[w]), a, b), blk(window(free, *WIN[w]), a, b)
            ca, cw_ = np.array([blk(c, a, b).pts.mean() for c in cf]), np.array([(blk(c, a, b).pts > 0).mean() for c in cf])
            rows.append(dict(window=w, entry_hour_utc=name, n_brakes_on=len(on), avg_pts_brakes_on=on.pts.mean() if len(on) else np.nan, n_brakes_off=len(off), win_off=(off.pts > 0).mean(),
                             avg_pts_off=off.pts.mean(), pf_usd_off=pf(off.usd.to_numpy()), ctrl_win=cw_.mean(), ctrl_avg_pts=ca.mean(), ctrl_p05=np.percentile(ca, 5), ctrl_p95=np.percentile(ca, 95),
                             real_percentile=(ca < off.pts.mean()).mean() * 100))
    T.append("### T17. Diagnostic, NOT pre-registered and not a pass mark: default cell with the daily brakes switched off (no 3-stop halt, no kill switch), spec base cost, "
             "against 100 random-signal controls run the same way. Shows the entry at all hours, since the 3-stop brake confines the pre-registered run to the first hours of the day\n\n"
             + md(pd.DataFrame(rows), {"avg_pts_brakes_on": "{:+.3f}", "win_off": "{:.1%}", "avg_pts_off": "{:+.3f}", "pf_usd_off": "{:.3f}", "ctrl_win": "{:.1%}", "ctrl_avg_pts": "{:+.3f}",
                                       "ctrl_p05": "{:+.3f}", "ctrl_p95": "{:+.3f}", "real_percentile": "{:.0f}"}))

    # --- sensitivity: the literal end-of-day rule (carry over the 21:00-22:00 summer break / weekend to the next open) ---
    lit = run(Q["spec_base"], sides[0.6], atr, *DEFAULT[:2], eod_literal=True)
    eb = base[base.eod_break]
    say(f"EOD rule: {int(base.eod_break.sum())} of {len(base)} default trades exit at 21:00 into a market break and are filled at the last quote (their net {eb.usd.sum():+.0f} USD). "
        f"Literal 'next open' variant: TRAIN PF {pf(window(lit, *WIN['TRAIN']).usd.to_numpy()):.3f}, TEST PF {pf(window(lit, *WIN['TEST']).usd.to_numpy()):.3f}, "
        f"FULL net {window(lit, *WIN['FULL']).usd.sum():+.0f} vs {window(base, *WIN['FULL']).usd.sum():+.0f} USD")

    # --- small-account survival, fixed sizing as specified (risk <= 38 USD per trade) ---
    rows = []
    for cn in ("spec_base", "spec_stress"):
        x = window(runs[DEFAULT, cn], *WIN["FULL"])
        dayid = x.entry_time.dt.floor("D")
        days = dayid.drop_duplicates().to_list()
        cum, first = np.r_[0, np.cumsum(x.usd.to_numpy())], dayid.searchsorted(days)
        for eq0 in (200, 1000):
            ttr, ruined60, n60 = [], 0, 0
            for di, i in enumerate(first):
                path = eq0 + cum[i + 1:] - cum[i]
                hit = np.flatnonzero(path < RISK_MAX)                     # cannot fund one more 38-USD risk
                if len(hit):
                    ttr.append((x.exit_time.iloc[i + hit[0]] - days[di]).days)
                if di + 60 < len(days):
                    n60 += 1
                    ruined60 += bool(len(hit)) and x.entry_time.iloc[i + hit[0]] < days[di + 60]
            rows.append(dict(cost=cn, start_equity=eq0, start_dates=len(days), ruined_before_data_end=len(ttr) / len(days),
                             median_calendar_days_to_ruin=float(np.median(ttr)) if ttr else np.nan, starts_with_60d_ahead=n60,
                             ruined_within_60_trading_days=ruined60 / max(n60, 1)))
    T.append("### T11. Small-account survival, default cell, every UTC trading day of TRAIN+TEST as a start date. "
             "Ruin = closed-trade equity below 38 USD (cannot fund the next trade's risk). Start dates near the end have little time left to fail (censored).\n\n"
             + md(pd.DataFrame(rows), {"ruined_before_data_end": "{:.1%}", "median_calendar_days_to_ruin": "{:.0f}", "ruined_within_60_trading_days": "{:.1%}"}))

    # --- trade-week replication (parity only; never part of pass/fail) ---
    wk = window(base, *WIN["WEEK"])
    real = pd.read_csv(XM / "trades.csv")
    rt, rside = ns(pd.to_datetime(real.open_time, utc=True, format="ISO8601")), np.where(real.side.eq("BUY"), 1, -1)
    ef = pd.read_csv(XM / "analysis/entries/entries_features.csv")
    dec = ef[ef.click_in_event == 0]
    dt_, dside, fresh = ns(pd.to_datetime(dec.open_time, utc=True, format="ISO8601")), np.where(dec.side.eq("BUY"), 1, -1), dec.role.eq("first").to_numpy()
    span = (rt.min() - 5 * MIN, rt.max() + 5 * MIN)
    inspan = lambda x: x[(x.entry_ns >= span[0]) & (x.entry_ns <= span[1])]
    sig_i = np.flatnonzero((sides[0.6] != 0) & (t + MIN >= span[0]) & (t + MIN <= span[1]))
    cw = [inspan(c) for c in control(0.6, "WEEK", "spec_base", N_CTRL, 23)]

    def rep(st, ss):                                                      # one row of shares for a set of strategy entries
        return dict(hit=matched(st, ss, rt, rside).mean() if len(st) else np.nan, hit_opp=matched(st, -ss, rt, rside).mean() if len(st) else np.nan,
                    pos=matched(rt, rside, st, ss).mean(), dec=matched(dt_, dside, st, ss).mean(), fresh=matched(dt_[fresh], dside[fresh], st, ss).mean())
    ws = inspan(wk)
    r_tr, r_sig = rep(ws.entry_ns.to_numpy(), ws.side.to_numpy()), rep(t[sig_i] + MIN, sides[0.6][sig_i].astype(int))
    r_c = pd.DataFrame([rep(c.entry_ns.to_numpy(), c.side.to_numpy()) for c in cw])
    inb = np.flatnonzero(elig & (t + MIN >= span[0]) & (t + MIN <= span[1]))                 # every in-session minute as a pseudo-entry
    raw_base = np.mean([matched(t[inb] + MIN, np.full(len(inb), sd), t[sig_i] + MIN, sides[0.6][sig_i].astype(int)).mean() for sd in (1, -1)])
    pct = lambda c: (r_c[c] < r_tr[c]).mean() * 100
    rows = [
        dict(measure="strategy entries with a real same-side position opened within +-5 min (hit rate)", n=len(ws), strategy_trades=r_tr["hit"], random_control_mean=r_c.hit.mean(), control_p95=r_c.hit.quantile(.95), percentile_vs_control=pct("hit"), raw_trigger_bars=r_sig["hit"]),
        dict(measure="same, but opposite side (placebo)", n=len(ws), strategy_trades=r_tr["hit_opp"], random_control_mean=r_c.hit_opp.mean(), control_p95=r_c.hit_opp.quantile(.95), percentile_vs_control=pct("hit_opp"), raw_trigger_bars=r_sig["hit_opp"]),
        dict(measure="real positions (178) with a same-side strategy entry within +-5 min", n=len(rt), strategy_trades=r_tr["pos"], random_control_mean=r_c.pos.mean(), control_p95=r_c.pos.quantile(.95), percentile_vs_control=pct("pos"), raw_trigger_bars=r_sig["pos"], raw_trigger_chance=raw_base),
        dict(measure="real decisions (124) explained", n=len(dt_), strategy_trades=r_tr["dec"], random_control_mean=r_c.dec.mean(), control_p95=r_c.dec.quantile(.95), percentile_vs_control=pct("dec"), raw_trigger_bars=r_sig["dec"], raw_trigger_chance=raw_base),
        dict(measure="real fresh entries (27) explained", n=int(fresh.sum()), strategy_trades=r_tr["fresh"], random_control_mean=r_c.fresh.mean(), control_p95=r_c.fresh.quantile(.95), percentile_vs_control=pct("fresh"), raw_trigger_bars=r_sig["fresh"], raw_trigger_chance=raw_base),
    ]
    repl = pd.DataFrame(rows)
    repl.to_csv(OUT / "replication_week.csv", index=False)
    T.append(f"### T12. Trade-week replication, default cell at spec base cost. Strategy entries inside the trader's active span "
             f"({pd.Timestamp(span[0], tz='UTC'):%m-%d %H:%M} .. {pd.Timestamp(span[1], tz='UTC'):%m-%d %H:%M} UTC): {len(ws)}; raw K=0.6 trigger bars in session: {len(sig_i)}; "
             f"random-control strategies: {N_CTRL} draws, mean {np.mean([len(c) for c in cw]):.0f} entries each\n\n"
             + md(repl, {c: "{:.1%}" for c in ("strategy_trades", "random_control_mean", "control_p95", "raw_trigger_bars", "raw_trigger_chance")} | {"percentile_vs_control": "{:.0f}"}))
    rows = [dict(who="trader, real (trades.csv; pts counts both legs of the 4 close-by pairs)", n=len(real), win=(real.net > 0).mean(), net_pts=real.pts.sum(), net_usd=real.net.sum(), pf_usd=pf(real.net.to_numpy()))]
    for cn in COSTS:
        x = window(runs[DEFAULT, cn], *WIN["WEEK"])
        rows.append(dict(who=f"XMR-3 default, {cn}", n=len(x), win=(x.pts > 0).mean(), net_pts=x.pts.sum(), net_usd=x.usd.sum(), pf_usd=pf(x.usd.to_numpy())))
    T.append("### T13. Trade week 2026-11-04 .. 11-11 13:43 UTC, side by side (parity only; 6 trading days)\n\n"
             + md(pd.DataFrame(rows), {"win": "{:.1%}", "net_pts": "{:+.1f}", "net_usd": "{:+.0f}", "pf_usd": "{:.3f}"}))

    # --- S5 re-resolution of exits where S5 bid/ask exists (2026-11-03 onward) ---
    s5 = pd.read_parquet(XM / "xau_s5_2026-11-03_now_ba.parquet")
    t5 = ns(s5.time)
    rows = []
    for cell in GRID:
        for cn in ("spec_base", "spec_stress"):
            c, tr = COSTS[cn], runs[cell, cn]
            x = tr[(tr.entry_ns >= t5[0]) & (tr.mkt_ns <= t5[-1])]
            B = {k: s5["bid_" + k].to_numpy() - c["xm"][0] for k in ("open", "high", "low")}
            A = {k: s5["ask_" + k].to_numpy() + c["xm"][1] for k in ("open", "high", "low")}
            p5, how5 = [], []
            for r in x.itertuples():
                i0, i1 = np.searchsorted(t5, r.entry_ns), np.searchsorted(t5, r.mkt_ns)
                P = B if r.side > 0 else A
                i, hit, px = first_touch(r.side > 0, r.stop, r.tgt, P["open"][i0:i1], P["high"][i0:i1], P["low"][i0:i1], c["slip"])
                px, hit = (px, hit) if i >= 0 else (r.mkt_px, r.how if r.how not in ("tp", "stop") else "market")
                p5.append((px - r.entry) * r.side); how5.append(hit)
            p5, how5 = np.array(p5), np.array(how5)
            rows.append(dict(cell=f"TP{cell[0]}/SL{cell[1]}/K{cell[2]}", cost=cn, n=len(x), exit_kind_changed=int((how5 != x.how.to_numpy()).sum()),
                             m1_net_pts=x.pts.sum(), s5_net_pts=p5.sum(), diff_pts_per_trade=(p5 - x.pts.to_numpy()).mean(),
                             m1_win=(x.pts > 0).mean(), s5_win=(p5 > 0).mean(), m1_net_usd=x.usd.sum(), s5_net_usd=(p5 * 100 * x.lot.to_numpy()).sum()))
    s5t = pd.DataFrame(rows)
    s5t.to_csv(OUT / "s5_vs_m1.csv", index=False)
    T.append(f"### T14. Exit resolution on S5 bid/ask against M1 bid/ask, same entries ({pd.Timestamp(t5[0], tz='UTC'):%Y-%m-%d} .. {pd.Timestamp(t5[-1], tz='UTC'):%m-%d}; S5 exists for this stretch only)\n\n"
             + md(s5t, {"m1_net_pts": "{:+.1f}", "s5_net_pts": "{:+.1f}", "diff_pts_per_trade": "{:+.3f}", "m1_win": "{:.1%}", "s5_win": "{:.1%}", "m1_net_usd": "{:+.0f}", "s5_net_usd": "{:+.0f}"}))

    # --- secondary, report only: 2019-01-01 .. 2025-07-15 on the long mid file (spread 1.5 bp base / 2.5 bp stress) ---
    f = pd.read_parquet(RD / "m3_scalper/xau_m1_full.parquet")
    a = pd.read_parquet(RD / "xau_m1_oanda.parquet")
    ov = a.merge(f, on="time", how="left", suffixes=("", "_f"), indicator=True)
    ov = ov[ov.time <= f.time.max()]
    both = ov[ov._merge == "both"]
    say(f"long-file QA against the OANDA file over their overlap: {len(both)} of {len(ov)} OANDA bars present ({len(both) / len(ov):.1%}); "
        f"close identical on {(both.close == both.close_f).mean():.2%}; |high or low difference| > 0.01 on {((both.high - both.high_f).abs().gt(.01) | (both.low - both.low_f).abs().gt(.01)).mean():.3%}")
    f = f[(f.time >= TS("2018-12-01")) & (f.time < TRAIN0)].reset_index(drop=True)
    fi = indicators(f.time, f.high.to_numpy(), f.low.to_numpy(), f.close.to_numpy())
    ft, fatr = ns(f.time), fi.atr5.to_numpy()
    fel = clock_ok(ft + MIN) & (f.time >= TS("2019-01-01")).to_numpy()
    rows, yr = [], []
    for cn, bp, slip in (("1.5bp spread, slip 0.30", 0.75e-4, 0.30), ("2.5bp spread, slip 0.60", 1.25e-4, 0.60)):
        fq = {"t": ft, "slip": slip}
        for x, k in zip(("open", "high", "low", "close"), "ohlc"):
            fq["b" + k], fq["a" + k] = f[x].to_numpy() * (1 - bp), f[x].to_numpy() * (1 + bp)
        for cell in GRID:
            sell, buy, _ = trigger(fi, cell[2])
            tr = run(fq, np.where(fel & sell, -1, np.where(fel & buy, 1, 0)).astype(np.int8), fatr, cell[0], cell[1])
            rows.append(dict(cell=f"TP{cell[0]}/SL{cell[1]}/K{cell[2]}", cost=cn, **stats(tr)))
            if cell == DEFAULT:
                y = tr.groupby(tr.entry_time.dt.year).agg(n=("pts", "size"), win=("pts", lambda v: (v > 0).mean()), net_pts=("pts", "sum"), net_usd=("usd", "sum"), pf_usd=("usd", lambda v: pf(v.to_numpy())))
                y.insert(0, "cost", cn)
                yr.append(y.reset_index(names="year"))
    sec = pd.DataFrame(rows)
    sec.to_csv(OUT / "secondary_2019_2025.csv", index=False)
    T.append("### T15. Secondary, report only: 2019-01-01 .. 2025-07-15 on `m3_scalper/xau_m1_full.parquet` (mid; never part of pass/fail)\n\n"
             + md(sec.drop(columns=["usd_004lot", "days"]), F))
    T.append("### T16. Secondary, default cell by year (MIN_ATR5 = 3.0 pts removes most bars before 2024, when gold's M5 ATR was below 3)\n\n"
             + md(pd.concat(yr), {"win": "{:.1%}", "net_pts": "{:+.1f}", "net_usd": "{:+.0f}", "pf_usd": "{:.3f}"}))

    # --- equity curve ---
    plot_equity(runs, ctrl, real_test)
    T.sort(key=lambda b: int(b.split(".")[0].split("T")[1]))               # T0 .. T17 in order
    (OUT / "tables.md").write_text("\n\n".join(T) + "\n")
    (OUT / "run.log").write_text("\n".join(LOG) + "\n")
    say("wrote", OUT)


def plot_equity(runs, ctrl, real_test):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INK, MUTED, GRIDC, SURF = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
    C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"                          # validated categorical slots 1-3
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e", "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(11, 8.2), gridspec_kw={"height_ratios": [1.15, 1]})
    for (cell, cn, lab, col) in ((DEFAULT, "spec_base", "default, base cost", C1), (DEFAULT, "spec_stress", "default, stress cost", C2), (GRID[3], "spec_base", "K_FADE 1.0, base cost", C3)):
        x = window(runs[cell, cn], TRAIN0, WEEK0)
        y = x.usd.cumsum()
        ax.plot(x.exit_time, y, color=col, lw=1.6, label=lab)
        ax.annotate(f"{lab}  {y.iloc[-1]:+,.0f}", (x.exit_time.iloc[-1], y.iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.axvline(TEST0, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(TEST0, ax.get_ylim()[1], "  TEST from 2026-04-01", va="top", ha="left", fontsize=9, color="#52514e")
    ax.text(TEST0, ax.get_ylim()[1], "TRAIN  ", va="top", ha="right", fontsize=9, color="#52514e")
    ax.axhline(0, color="#c3c2b7", lw=1)
    ax.set_title("XMR-3 single-shot fade: cumulative closed-trade P&L, USD (risk at most 38 USD per trade)", loc="left", fontsize=11, color=INK)
    ax.set_ylabel("USD")
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    ax.grid(axis="y", color=GRIDC, lw=0.6)
    ax.margins(x=0.0)
    ax.set_xlim(TRAIN0, WEEK0 + pd.Timedelta(days=75))
    tk = pd.date_range("2025-08-01", "2026-11-01", freq="3MS", tz="UTC")
    ax.set_xticks(tk, [d.strftime("%Y-%m") for d in tk])
    days = pd.date_range(TEST0, WEEK0, freq="D", tz="UTC")
    daily = lambda x: x.groupby(x.exit_time.dt.floor("D")).pts.sum().reindex(days, fill_value=0).cumsum().to_numpy()
    M = np.array([daily(c) for c in ctrl])
    bx.fill_between(days, np.percentile(M, 5, 0), np.percentile(M, 95, 0), color="#c3c2b7", alpha=0.55, lw=0, label=f"{len(ctrl)} random-signal controls, 5th-95th percentile")
    bx.plot(days, np.median(M, 0), color=MUTED, lw=1.2, label="control median")
    r = daily(real_test)
    bx.plot(days, r, color=C1, lw=1.8, label="default cell (fade trigger)")
    bx.annotate(f"fade trigger  {r[-1]:+,.0f} pts", (days[-1], r[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
    bx.annotate(f"control median  {np.median(M, 0)[-1]:+,.0f} pts", (days[-1], np.median(M, 0)[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
    bx.axhline(0, color="#c3c2b7", lw=1)
    bx.set_title("TEST only: cumulative points, fade trigger against random signals with identical exits, sizing and brakes (base cost)", loc="left", fontsize=11, color=INK)
    bx.set_ylabel("points (USD per oz)")
    bx.legend(frameon=False, loc="lower left", fontsize=9)
    bx.grid(axis="y", color=GRIDC, lw=0.6)
    bx.set_xlim(TEST0, WEEK0 + pd.Timedelta(days=40))
    tk = pd.date_range("2026-04-01", "2026-11-01", freq="MS", tz="UTC")
    bx.set_xticks(tk, [d.strftime("%Y-%m") for d in tk])
    fig.tight_layout()
    fig.savefig(OUT / "equity.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
