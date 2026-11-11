"""Shared feature code for the XM Real entry study.

One code path for real and random entries: `build_grid` computes side-agnostic market context at
every 5-second bar CLOSE using only bars that had closed by then; `sign_features` turns a grid row
plus a side (+1 BUY / -1 SELL) into direction-signed features. A real entry at instant T uses the
grid row with the latest close <= T, so nothing at or after T is visible.

Conventions (all UTC, prices = OANDA bid, i.e. what an MT5 chart draws; XM = OANDA + basis):
  trading day   22:00 -> 22:00 UTC (17:00 New York, EST in November)
  Asian range   [00:00, 07:00) UTC of the UTC date, defined only from 07:00 on (workspace convention)
  M5 swing      5-bar fractal (2 bars each side), usable once the 2nd right-hand bar has closed
  sweep         an M1 bar that trades through a level known at its open and closes back inside
                (levels: last M5 swing, prior-60-bar extreme, prior-day high/low, Asian high/low)
  FVG           3-bar gap >= 0.5 pt; M5 zone stays live 60 min or until fully filled
  displacement  body >= 1.5 x ATR14 (M5) / 2.5 x ATR14 (M1) of the bar before it, body >= 60% of range
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
NS = 1_000_000_000
MIN = 60 * NS
DAY = 86400 * NS
HORIZONS = (5, 15, 30, 60)   # minutes, forward signed return
# first-touch exits: name -> (take-profit pts, stop pts, horizon cap in S5 bars). Same-bar tie = stop.
#   touch5 / touch10   symmetric, 4 h cap: does the entry pick direction?
#   touch_g1           the ledger's own geometry: median winning click +4.7 pt, median losing click -9.5 pt
#   touch_g2           'TP 5, no stop until the margin call': 5.0 pt (the modal TP distance, 5.06) vs 28.0 pt
#                      (median distance to zero equity at entry, 03_sequence_setups.py section H); 12 h cap
TOUCH = {"touch5": (5.0, 5.0, 2880), "touch10": (10.0, 10.0, 2880), "touch_g1": (4.7, 9.5, 8640), "touch_g2": (5.0, 28.0, 8640)}


def ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").tz_localize(None).as_unit("ns").asi8


def load_s5():
    return pd.read_parquet(ROOT / "xau_s5_2026-11-03_now_ba.parquet").sort_values("time").reset_index(drop=True)


def load_m1():
    return pd.read_parquet(ROOT / "xau_m1_2026-07-16_now_mba.parquet").sort_values("time").reset_index(drop=True)


def load_deals():
    d = pd.read_csv(ROOT / "deals.csv")
    d["time"] = pd.to_datetime(d.time, utc=True, format="ISO8601")
    return d.sort_values(["time", "id"]).reset_index(drop=True)


def asof(t, ev_t, vals):
    """vals of the last event with ev_t <= t (NaN if none)."""
    if len(ev_t) == 0:
        return np.full(len(t), np.nan)
    j = np.searchsorted(ev_t, t, "right") - 1
    return np.where(j >= 0, np.asarray(vals, float)[np.clip(j, 0, None)], np.nan)


def _atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def _ema(c, n):
    return pd.Series(c).ewm(span=n, adjust=False).mean().to_numpy()


def _pivots(h, l, close_ns, k=2):
    """5-bar fractals -> (confirm_ns, level) for highs and lows; confirmed at close of bar i+k."""
    hi, lo = [], []
    for i in range(k, len(h) - k):
        if h[i] > h[i - k:i].max() and h[i] >= h[i + 1:i + k + 1].max():
            hi.append((close_ns[i + k], h[i]))
        if l[i] < l[i - k:i].min() and l[i] <= l[i + 1:i + k + 1].min():
            lo.append((close_ns[i + k], l[i]))
    unzip = lambda x: (np.array([a for a, _ in x], np.int64), np.array([b for _, b in x], float))
    return unzip(hi), unzip(lo)   # ((times, levels), (times, levels)) - times stay int64 ns


def _fvgs(h, l, close_ns, min_gap, life_ns):
    """-> list of (confirm_ns, dir, zone_lo, zone_hi, end_ns). end = full fill or expiry."""
    out = []
    n = len(h)
    for i in range(2, n):
        for d, zlo, zhi in ((1, h[i - 2], l[i]), (-1, h[i], l[i - 2])):
            if zhi - zlo < min_gap:
                continue
            end = close_ns[i] + life_ns
            for j in range(i + 1, n):
                if close_ns[j] > end:
                    break
                if (d == 1 and l[j] <= zlo) or (d == -1 and h[j] >= zhi):
                    end = close_ns[j]
                    break
            out.append((close_ns[i], d, zlo, zhi, end))
    return out


def build_grid(s5, m1, basis_bid=0.0, fwd=True, start=None):
    o = ns(s5.time)
    c = o + 5 * NS
    bid, ask = s5.bid_close.to_numpy(), s5.ask_close.to_numpy()
    bh, bl = s5.bid_high.to_numpy(), s5.bid_low.to_numpy()
    g = pd.DataFrame({"c": c, "bid": bid, "ask": ask, "spread": ask - bid})
    g["hour"] = (o % DAY) // (60 * MIN)
    g["minute"] = (o % (60 * MIN)) // MIN
    g["date"] = o // DAY

    for k in (1, 3, 5, 15, 60):                       # price k minutes before the bar close
        j = np.searchsorted(c, c - k * MIN, "right") - 1
        g[f"r{k}"] = np.where(j >= 0, bid - bid[np.clip(j, 0, None)], np.nan)

    idx = pd.DatetimeIndex(c)
    j2 = np.searchsorted(c, c - 2 * MIN, "right") - 1
    for w in (15, 60):                                # rolling range (c-w, c] and the same ending 2 min ago
        hi = pd.Series(bh, idx).rolling(f"{w}min").max().to_numpy()
        lo = pd.Series(bl, idx).rolling(f"{w}min").min().to_numpy()
        g[f"hi{w}"], g[f"lo{w}"] = hi, lo
        g[f"hi{w}x"] = np.where(j2 >= 0, hi[np.clip(j2, 0, None)], np.nan)
        g[f"lo{w}x"] = np.where(j2 >= 0, lo[np.clip(j2, 0, None)], np.nan)

    tday = (o + 2 * 60 * MIN) // DAY
    g["hiday"] = pd.Series(bh).groupby(tday).cummax().to_numpy()
    g["loday"] = pd.Series(bl).groupby(tday).cummin().to_numpy()

    # ---- M1 / M5 context (bid bars) ----
    mo = ns(m1.time)
    mc = mo + MIN
    mop, mh, ml, mcl = (m1[f"bid_{x}"].to_numpy() for x in ("open", "high", "low", "close"))
    atr1 = _atr(mh, ml, mcl)
    m5 = (m1.set_index("time")[["bid_open", "bid_high", "bid_low", "bid_close"]]
          .resample("5min").agg({"bid_open": "first", "bid_high": "max", "bid_low": "min", "bid_close": "last"}).dropna())
    fo = ns(m5.index)
    fc = fo + 5 * MIN
    fop, fh, fl, fcl = (m5[f"bid_{x}"].to_numpy() for x in ("open", "high", "low", "close"))
    atr5 = _atr(fh, fl, fcl)
    for name, t, v in (("atr1", mc, atr1), ("ema20_1", mc, _ema(mcl, 20)), ("ema50_1", mc, _ema(mcl, 50)),
                       ("atr5", fc, atr5), ("ema20_5", fc, _ema(fcl, 20)), ("ema50_5", fc, _ema(fcl, 50))):
        g[name] = asof(c, t, v)

    # volatility state: ATR(M5) vs the median ATR(M5) of the same UTC hour over the previous 20 dates
    hh = pd.DataFrame({"d": fo // DAY, "h": (fo % DAY) // (60 * MIN), "a": atr5}).groupby(["h", "d"]).a.median()
    base = hh.groupby(level="h").transform(lambda s: s.rolling(20, min_periods=10).median().shift(1))
    key = pd.MultiIndex.from_arrays([g.hour.to_numpy(), g.date.to_numpy()])
    g["volratio"] = g.atr5.to_numpy() / base.reindex(key).to_numpy()

    # prior trading day high / low
    daily = pd.DataFrame({"t": (mo + 2 * 60 * MIN) // DAY, "h": mh, "l": ml}).groupby("t").agg(h=("h", "max"), l=("l", "min"))
    prev = daily.shift(1)
    g["pdh"], g["pdl"] = prev.h.reindex(tday).to_numpy(), prev.l.reindex(tday).to_numpy()

    # Asian range of the UTC date, known from 07:00
    mhour = (mo % DAY) // (60 * MIN)
    am = mhour < 7
    asia = pd.DataFrame({"d": mo[am] // DAY, "h": mh[am], "l": ml[am]}).groupby("d").agg(h=("h", "max"), l=("l", "min"))
    done = (c % DAY) >= 7 * 60 * MIN
    cdate = c // DAY
    g["asia_hi"] = np.where(done, asia.h.reindex(cdate).to_numpy(), np.nan)
    g["asia_lo"] = np.where(done, asia.l.reindex(cdate).to_numpy(), np.nan)

    # last confirmed M5 swing high / low
    (pht, phv), (plt_, plv) = _pivots(fh, fl, fc)
    g["swhi"], g["swlo"] = asof(c, pht, phv), asof(c, plt_, plv)

    # liquidity sweeps on M1: trade through a level known at the bar's open, close back inside
    r60h = pd.Series(mh).rolling(60).max().shift(1).to_numpy()
    r60l = pd.Series(ml).rolling(60).min().shift(1).to_numpy()
    mt = (mo + 2 * 60 * MIN) // DAY
    adone = mhour >= 7
    lv_hi = [asof(mo, pht, phv), r60h, prev.h.reindex(mt).to_numpy(), np.where(adone, asia.h.reindex(mo // DAY).to_numpy(), np.nan)]
    lv_lo = [asof(mo, plt_, plv), r60l, prev.l.reindex(mt).to_numpy(), np.where(adone, asia.l.reindex(mo // DAY).to_numpy(), np.nan)]
    bsl = np.zeros(len(mo), bool)
    ssl = np.zeros(len(mo), bool)
    with np.errstate(invalid="ignore"):
        for L in lv_hi:
            bsl |= (mh > L) & (mcl < L) & (mop <= L)
        for L in lv_lo:
            ssl |= (ml < L) & (mcl > L) & (mop >= L)
    def age(ev_t):                                     # minutes since the last event (inf if none yet)
        j = np.searchsorted(ev_t, c, "right") - 1
        return np.where(j >= 0, (c - ev_t[np.clip(j, 0, None)]) / MIN, np.inf) if len(ev_t) else np.full(len(c), np.inf)
    g["bsl_age"], g["ssl_age"] = age(mc[bsl]), age(mc[ssl])   # buy-side sweep = highs taken and rejected

    # fair value gaps
    t0 = c[0] - 2 * 60 * MIN
    k5, k1 = fc >= t0 - 60 * MIN, mc >= t0 - 60 * MIN
    f5 = _fvgs(fh[k5], fl[k5], fc[k5], 0.5, 60 * MIN)
    f1 = _fvgs(mh[k1], ml[k1], mc[k1], 0.5, 15 * MIN)
    for name, f, win in (("fvg5", f5, 30 * MIN), ("fvg1", f1, 5 * MIN)):   # direction of the latest gap, if recent
        ft = np.array([x[0] for x in f], np.int64)
        j = np.searchsorted(ft, c, "right") - 1
        recent = (j >= 0) & ((c - ft[np.clip(j, 0, None)]) <= win) if len(ft) else np.zeros(len(c), bool)
        g[name] = np.where(recent, np.array([x[1] for x in f], float)[np.clip(j, 0, None)] if len(ft) else 0.0, 0.0)
    inz = np.zeros(len(c))                                                # inside a live M5 gap: +1 bullish zone, -1 bearish
    for t_conf, d, zlo, zhi, t_end in f5:
        m = (c >= t_conf) & (c < t_end) & (bid >= zlo) & (bid <= zhi)
        inz[m] += d
    g["in_fvg5"] = np.sign(inz)

    # displacement
    for name, op, hi_, lo_, cl, t, a, mult, win in (("disp5", fop, fh, fl, fcl, fc, atr5, 1.5, 15 * MIN),
                                                    ("disp1", mop, mh, ml, mcl, mc, atr1, 2.5, 5 * MIN)):
        body = cl - op
        pa = np.r_[np.nan, a[:-1]]
        with np.errstate(invalid="ignore"):
            ev = (np.abs(body) >= mult * pa) & (np.abs(body) >= 0.6 * (hi_ - lo_))
        et, ed = t[ev], np.sign(body[ev])
        j = np.searchsorted(et, c, "right") - 1
        recent = (j >= 0) & ((c - et[np.clip(j, 0, None)]) <= win) if len(et) else np.zeros(len(c), bool)
        g[name] = np.where(recent, ed[np.clip(j, 0, None)] if len(et) else 0.0, 0.0)

    # round numbers on the XM chart price
    x = bid + basis_bid
    for m in (5, 10, 50):
        g[f"rn{m}"] = np.abs((x + m / 2) % m - m / 2)

    if start is not None:
        g = g[g.c >= start].reset_index(drop=True)
    if fwd:
        _forward(g, s5)
    return g


def _forward(g, s5):
    """OUTCOME columns (look ahead by construction, never used as features).
    Enter at the quote of the row's bar close: BUY pays ask, exits on bid; SELL the mirror."""
    c_all = ns(s5.time) + 5 * NS
    b, a = s5.bid_close.to_numpy(), s5.ask_close.to_numpy()
    bh, bl, ah, al = (s5[x].to_numpy() for x in ("bid_high", "bid_low", "ask_high", "ask_low"))
    c = g.c.to_numpy()
    i0 = np.searchsorted(c_all, c)
    for h in HORIZONS:
        j = np.searchsorted(c_all, c + h * MIN, "right") - 1
        ok = c + h * MIN <= c_all[-1]
        g[f"fwdB{h}"] = np.where(ok, b[j] - a[i0], np.nan)
        g[f"fwdS{h}"] = np.where(ok, b[i0] - a[j], np.nan)
    for name, (tpd, sld, cap) in TOUCH.items():
        rb, rs = np.full(len(g), np.nan), np.full(len(g), np.nan)   # 1 = target first, 0 = stop first, NaN = neither within cap
        for n, i in enumerate(i0):
            sl = slice(i + 1, i + 1 + cap)
            tp, st = bh[sl] >= a[i] + tpd, bl[sl] <= a[i] - sld     # BUY: exits on bid
            it, is_ = (tp.argmax() if tp.any() else 10**9), (st.argmax() if st.any() else 10**9)
            if min(it, is_) < 10**9:
                rb[n] = float(it < is_)                             # same-bar tie -> stop
            tp, st = al[sl] <= b[i] - tpd, ah[sl] >= b[i] + sld     # SELL: exits on ask
            it, is_ = (tp.argmax() if tp.any() else 10**9), (st.argmax() if st.any() else 10**9)
            if min(it, is_) < 10**9:
                rs[n] = float(it < is_)
        g[f"B_{name}"], g[f"S_{name}"] = rb, rs


def sign_features(r, side):
    """r: grid rows (DataFrame), side: array of +1 (BUY) / -1 (SELL). Returns direction-signed features.
    *_dir > 0 always means 'in the direction of the trade'; pos*_dir: 0 = bought the low / sold the high."""
    s = np.asarray(side, float)
    p = r.bid.to_numpy()
    f = pd.DataFrame(index=r.index)
    for k in (1, 3, 5, 15, 60):
        f[f"ret{k}_dir"] = s * r[f"r{k}"].to_numpy()
    a1, a5 = r.atr1.to_numpy(), r.atr5.to_numpy()
    f["ret5_atr_dir"] = f.ret5_dir / a5
    f["ret60_atr_dir"] = f.ret60_dir / a5

    def pos(lo, hi):
        lo, hi = r[lo].to_numpy(), r[hi].to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            q = (p - lo) / np.where(hi > lo, hi - lo, np.nan)
        return np.where(s > 0, q, 1 - q)
    f["pos15_dir"], f["pos60_dir"], f["posday_dir"] = pos("lo15", "hi15"), pos("lo60", "hi60"), pos("loday", "hiday")
    f["pospd_dir"] = pos("pdl", "pdh")
    f["posasia_dir"] = pos("asia_lo", "asia_hi")

    def beyond(lo, hi):   # +1 beyond the extreme in the trade direction, -1 beyond the opposite extreme, 0 inside
        lo, hi = r[lo].to_numpy(), r[hi].to_numpy()
        raw = np.where(p > hi, 1.0, np.where(p < lo, -1.0, 0.0))
        return np.where(np.isnan(lo) | np.isnan(hi), np.nan, s * raw)
    f["brk15_dir"], f["brk60_dir"] = beyond("lo15x", "hi15x"), beyond("lo60x", "hi60x")
    f["beyond_pd_dir"], f["beyond_asia_dir"] = beyond("pdl", "pdh"), beyond("asia_lo", "asia_hi")
    f["near_pd"] = np.minimum(np.abs(p - r.pdh.to_numpy()), np.abs(p - r.pdl.to_numpy()))
    f["near_asia"] = np.minimum(np.abs(p - r.asia_hi.to_numpy()), np.abs(p - r.asia_lo.to_numpy()))

    up, dn = r.swhi.to_numpy() - p, p - r.swlo.to_numpy()      # room to last swing high above / swing low below
    f["sw_stop_dist"] = np.where(s > 0, dn, up)                # protective side (negative = already broken)
    f["sw_tgt_dist"] = np.where(s > 0, up, dn)                 # target side
    f["sw_stop_atr"], f["sw_tgt_atr"] = f.sw_stop_dist / a5, f.sw_tgt_dist / a5

    f["rn5"], f["rn10"], f["rn50"] = r.rn5.to_numpy(), r.rn10.to_numpy(), r.rn50.to_numpy()
    f["atr1"], f["atr5"], f["volratio"] = a1, a5, r.volratio.to_numpy()
    f["rng15"], f["rng60"] = (r.hi15 - r.lo15).to_numpy(), (r.hi60 - r.lo60).to_numpy()
    f["spread"] = r.spread.to_numpy()

    spike = np.abs(r.r3.to_numpy()) >= a5                      # 3-min net move >= one average M5 range
    f["fade_spike"] = (spike & (f.ret3_dir.to_numpy() < 0)).astype(float)
    f["follow_spike"] = (spike & (f.ret3_dir.to_numpy() > 0)).astype(float)
    f["fade_brk60"] = (f.brk60_dir == -1).astype(float)
    f["follow_brk60"] = (f.brk60_dir == 1).astype(float)

    bsl, ssl = r.bsl_age.to_numpy(), r.ssl_age.to_numpy()
    f["sweep_stop_15"] = (np.where(s > 0, ssl, bsl) <= 15).astype(float)   # ICT reversal: sell after highs swept
    f["sweep_tgt_15"] = (np.where(s > 0, bsl, ssl) <= 15).astype(float)    # entry INTO the side just swept
    f["fvg5_dir"], f["fvg1_dir"] = s * r.fvg5.to_numpy(), s * r.fvg1.to_numpy()
    f["in_fvg5_dir"] = s * r.in_fvg5.to_numpy()
    f["disp5_dir"], f["disp1_dir"] = s * r.disp5.to_numpy(), s * r.disp1.to_numpy()

    for tf in (1, 5):
        a = a1 if tf == 1 else a5
        for n in (20, 50):
            e = r[f"ema{n}_{tf}"].to_numpy()
            f[f"ema{n}_m{tf}_side"] = s * np.sign(p - e)       # +1 = price on the with-trade side of the EMA
            if n == 20:
                f[f"ema20_m{tf}_dist_atr"] = s * (p - e) / a
        f[f"ematrend_m{tf}_dir"] = s * np.sign(r[f"ema20_{tf}"].to_numpy() - r[f"ema50_{tf}"].to_numpy())
    return f


def outcomes(r, side):
    """Forward outcome of an entry taken at the row's quote (spread paid), for the entry-edge test."""
    s = np.asarray(side)
    f = pd.DataFrame(index=r.index)
    for h in HORIZONS:
        f[f"fwd{h}"] = np.where(s > 0, r[f"fwdB{h}"].to_numpy(), r[f"fwdS{h}"].to_numpy())
    for name in TOUCH:
        f[name] = np.where(s > 0, r[f"B_{name}"].to_numpy(), r[f"S_{name}"].to_numpy())
    return f
