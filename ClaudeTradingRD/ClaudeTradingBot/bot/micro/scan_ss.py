"""Fast in-process param scan for the session-sweep-revert idea.
Loads train+OOS M1 synth-spread bars ONCE, then evaluates many configs at
0.20/0.30 maker+taker. Judges on taker PF ~0.25 (avg of .20/.30 taker) in BOTH
train and OOS. Prints a ranked table. Run: python -m bot.micro.scan_ss
"""
import itertools
import numpy as np
from bot.micro.engine import Bars, Signals, simulate, atr as atr_fn
from bot.micro.features import resample_bars, hours_mask, ema
from bot.oanda_s5 import load

TF = 60
TRAIN = ("2024-01", "2025-07")
OOS = ("2025-08", "2026-06")
SPREADS = (0.20, 0.30)
ASIA_A, ASIA_Z = 0, 7


def _synth(d, s):
    mo = (d["bo"] + d["ao"]) * 0.5; mh = (d["bh"] + d["ah"]) * 0.5
    ml = (d["bl"] + d["al"]) * 0.5; mc = (d["bc"] + d["ac"]) * 0.5
    h = s * 0.5
    return {"ts": d["ts"], "vol": d["vol"],
            "bo": mo - h, "bh": mh - h, "bl": ml - h, "bc": mc - h,
            "ao": mo + h, "ah": mh + h, "al": ml + h, "ac": mc + h}


def make_bars(window):
    d = load(*window)
    out = {}
    for s in SPREADS:
        out[s] = Bars(resample_bars(_synth(d, s), TF))
    return out


def session_range(b, hi, lo):
    n = b.n; day = b.day; hod = b.hod
    aH = np.full(n, np.nan); aL = np.full(n, np.nan)
    chg = np.concatenate(([0], np.where(np.diff(day) != 0)[0] + 1, [n]))
    for k in range(len(chg) - 1):
        s, e = int(chg[k]), int(chg[k + 1])
        m = (hod[s:e] >= ASIA_A) & (hod[s:e] < ASIA_Z)
        if m.any():
            aH[s:e] = hi[s:e][m].max(); aL[s:e] = lo[s:e][m].min()
    return aH, aL


def first_per_day(idx, day):
    if len(idx) == 0:
        return idx
    dd = day[idx]; keep = np.ones(len(idx), bool); keep[1:] = dd[1:] != dd[:-1]
    return idx[keep]


def gen(b, P):
    n = b.n
    hi = (b.ah + b.bh) * 0.5; lo = (b.al + b.bl) * 0.5; c = b.mid
    A = atr_fn(b, P["atrp"]); a = np.where(np.isfinite(A) & (A > 0), A, np.nan)
    aH, aL = session_range(b, hi, lo)
    rng = aH - aL
    sess = hours_mask(b, P["hours"])
    volok = np.isfinite(a) & (a >= P["atrlo"]) & (a <= P["atrhi"])
    rngok = np.isfinite(rng) & (rng >= P["rnglo"]) & (rng <= P["rnghi"])
    base = sess & volok & rngok & np.isfinite(aH)
    sweepH = base & (hi >= aH + P["swbuf"] * a) & (hi <= aH + P["maxpen"] * a) \
        & (c <= aH - P["reck"] * a) & ((hi - c) >= P["wick"] * a)
    sweepL = base & (lo <= aL - P["swbuf"] * a) & (lo >= aL - P["maxpen"] * a) \
        & (c >= aL + P["reck"] * a) & ((c - lo) >= P["wick"] * a)
    # HTF trend bias (causal): slope of a slow EMA over LAG bars.
    bmode = P.get("bias", "off")
    if bmode != "off":
        E = ema(c, P["biasp"])
        lag = P["biaslag"]
        slope = np.full(n, 0.0)
        slope[lag:] = E[lag:] - E[:-lag]
        up = slope > 0; dn = slope < 0
        if bmode == "with":      # trade direction must match HTF trend
            sweepH = sweepH & dn   # short only in downtrend
            sweepL = sweepL & up   # long only in uptrend
        elif bmode == "against":
            sweepH = sweepH & up
            sweepL = sweepL & dn
    # optional displacement confirmation: the sweep bar's body must close in the
    # reversal third (strong momentum reclaim), not just a wick poke.
    if P.get("conf", 0):
        rngbar_o = (b.ao + b.bo) * 0.5
        bodyH = (rngbar_o - c) >= P["confk"] * a   # short: close well below open
        bodyL = (c - rngbar_o) >= P["confk"] * a
        sweepH = sweepH & bodyH
        sweepL = sweepL & bodyL
    so = P.get("side", 0)
    iH = first_per_day(np.where(sweepH)[0], b.day)
    iL = first_per_day(np.where(sweepL)[0], b.day)
    if so > 0:
        iH = iH[:0]
    elif so < 0:
        iL = iL[:0]
    if len(iH) + len(iL) == 0:
        z = np.zeros(0); return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)
    KIND = P["kind"]
    if KIND == 1:
        lvH = aH[iH]; lvL = aL[iL]
    else:
        lvH = c[iH]; lvL = c[iL]
    slH = (hi[iH] - lvH) + P["slbuf"] * a[iH]
    slL = (lvL - lo[iL]) + P["slbuf"] * a[iL]
    if P["tpmode"] == "frac":
        tpH = P["tpfrac"] * rng[iH]; tpL = P["tpfrac"] * rng[iL]
    else:  # fixed R
        tpH = P["tpr"] * slH; tpL = P["tpr"] * slL
    i = np.concatenate([iH, iL])
    side = np.concatenate([-np.ones(len(iH), np.int64), np.ones(len(iL), np.int64)])
    level = np.concatenate([lvH, lvL]); slp = np.concatenate([slH, slL]); tpp = np.concatenate([tpH, tpL])
    rr = tpp / np.where(slp > 0, slp, np.nan)
    ok = np.isfinite(rr) & (slp >= P["slmin"]) & (slp <= P["slmax"]) \
        & (rr >= P["rrmin"]) & (rr <= P["rrmax"]) & (tpp > 0)
    i, side, level, slp, tpp = i[ok], side[ok], level[ok], slp[ok], tpp[ok]
    if len(i) == 0:
        z = np.zeros(0); return Signals(i=z, side=z, kind=z, level=z, sl_pts=z, tp_pts=z, ttl=z)
    o = np.argsort(i, kind="stable")
    i, side, level, slp, tpp = i[o], side[o], level[o], slp[o], tpp[o]
    m = len(i)
    return Signals(i=i, side=side, kind=np.full(m, KIND, np.int8), level=level,
                   sl_pts=slp, tp_pts=tpp, ttl=np.full(m, P["ttl"], np.int64))


def eval_cfg(barsmap, P):
    """Return (taker_pf_025, train-style dict): pf/net/trades/wr at maker & taker, avg taker pf."""
    sim = dict(maxhold=P["maxhold"], dollars_per_point=1.0, commission=0.07,
               cooldown=P["cooldown"], gap_sec=max(30, TF * 2 + 5),
               trail_pts=P.get("trail", 0.0))
    res = {}
    tk_pfs = []; tk_nets = []; tr = 0; wr = 0
    for s in SPREADS:
        b = barsmap[s]
        sig = gen(b, P)
        rk = simulate(b, sig, **sim)
        km = dict(sim); km["slippage_pts"] = s
        rt = simulate(b, sig, **km)
        res[s] = (round(rk["pf"], 3), round(rt["pf"], 3), rt["trades"], round(rt["wr"], 1), round(rt["net$"], 1))
        tk_pfs.append(rt["pf"]); tk_nets.append(rt["net$"]); tr = rt["trades"]; wr = rt["wr"]
    avg_tk = float(np.mean([p if np.isfinite(p) else 0 for p in tk_pfs]))
    return avg_tk, tr, wr, res, float(np.mean(tk_nets))


def main():
    print("loading...")
    TB = make_bars(TRAIN); OB = make_bars(OOS)
    base = dict(atrp=20, swbuf=0.05, maxpen=1.6, wick=0.55, reck=0.02, slbuf=0.35,
                rnglo=4.0, rnghi=45.0, atrlo=0.5, atrhi=14.0, slmin=0.8, slmax=8.0,
                ttl=8, kind=1, maxhold=60, cooldown=1, tpmode="fixedr", tpr=1.2,
                rrmin=0.5, rrmax=8.0, tpfrac=0.5, hours=(7, 8, 9, 10, 11, 12, 13, 14),
                bias="off", biasp=240, biaslag=60, side=-1, trail=0.0,
                conf=0, confk=0.4)
    HOURSETS = {
        "lon": (7, 8, 9, 10, 11),
        "ny": (12, 13, 14, 15),
        "lonny": (7, 8, 9, 10, 11, 12, 13, 14),
        "open2": (7, 8, 12, 13),
    }
    grid = {
        "side": [-1, 0],
        "hours": list(HOURSETS.values()),
        "conf": [0, 1],
        "tpr": [2.0, 3.0],
        "slbuf": [1.0, 1.5],
    }
    keys = list(grid)
    rows = []
    combos = list(itertools.product(*[grid[k] for k in keys]))
    print(f"{len(combos)} combos")
    for vals in combos:
        P = dict(base); P.update(dict(zip(keys, vals)))
        tro, trn, trw, trr, trnet = eval_cfg(TB, P)
        if trn < 40:
            continue
        oo, on, ow, orr, onet = eval_cfg(OB, P)
        score = min(tro, oo)
        cfg = {k: P[k] for k in keys}
        rows.append((score, tro, oo, trn, on, trw, ow, trnet, onet, cfg))
    rows.sort(reverse=True)
    print("minPF tr_tkPF oos_tkPF trN oosN trWR oosWR trNet oosNet cfg")
    for r in rows[:30]:
        print(f"{r[0]:.2f}  {r[1]:.2f} {r[2]:.2f}  {r[3]:4d} {r[4]:4d}  {r[5]:4.1f} {r[6]:4.1f} {r[7]:7.1f} {r[8]:7.1f}  {r[9]}")
    if not rows:
        print("no configs with >=50 train trades")


if __name__ == "__main__":
    main()
