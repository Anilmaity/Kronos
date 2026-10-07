"""Faithfulness/robustness verification of average-daily-range u1007a (ADR cap, rate).

Read-only w.r.t. ledger/results: never calls rate_test / write_result / cache_frame.
Rebuilds events + the script's null, then perturbs: N, mean/median, vol window, decision
grid, spread, ADR multiples (structural: is ADR special?), a beyond-extreme conditional
null, per-side, per-year, feed-regression exclusion.
"""
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                   # noqa: E402

SEED = cl.rules.SEED
m1 = cl.load_m1()
mkt = cl.get_market()
D = cl.build_bars(m1, "1D")
REAL = D[D["n_m1"] >= 600]
RCT = cl.data.utc_ns(pd.DatetimeIndex(REAL["close_time"]))
CS = np.concatenate([[0.0], np.cumsum(mkt.h - mkt.l)])


def events(n_days=14, agg="mean", minute=0, mult=1.0, filt_mult=1.0):
    rng_ = (REAL["high"] - REAL["low"]).rolling(n_days, min_periods=n_days)
    adr = (rng_.mean() if agg == "mean" else rng_.median()).to_numpy()
    start = pd.DatetimeIndex(D.index)
    close = pd.DatetimeIndex(D["close_time"])
    ev = pd.concat([pd.DataFrame({"t": start + pd.Timedelta(hours=h, minutes=minute),
                                  "day_close": close}) for h in range(1, 23)],
                   ignore_index=True)
    ev = ev[ev["t"] < ev["day_close"]].sort_values("t").reset_index(drop=True)
    t = pd.DatetimeIndex(ev["t"])
    pos = np.searchsorted(RCT, cl.data.utc_ns(t), side="right") - 1
    a = np.where(pos >= 0, adr[np.clip(pos, 0, None)], np.nan)
    run = cl.running_hilo(t, "1D", m1=m1)
    hi, lo = run["high"].to_numpy(float), run["low"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(hi) & np.isfinite(lo) & ((hi - lo) < filt_mult * a)
    ev = ev[ok].assign(adr=a[ok], hi=hi[ok], lo=lo[ok])
    up = ev.assign(side=1, cap=ev["lo"] + mult * ev["adr"])
    dn = ev.assign(side=-1, cap=ev["hi"] - mult * ev["adr"])
    return pd.concat([up, dn], ignore_index=True).sort_values(["t", "side"]).reset_index(drop=True)


def lvol(times, nbars):
    p = mkt.pos_at_or_after(times)
    v = (CS[p] - CS[np.maximum(p - nbars, 0)]) / nbars
    return np.where(p >= nbars, v, np.nan)


def hits(times, level, side, nb):
    out = np.full(len(level), np.nan)
    for s, sd in ((1, "above"), (-1, "below")):
        m = (side == s) & np.isfinite(level) & (nb > 0)
        if m.any():
            out[m] = cl.touch(times[m], level[m], sd, horizon_bars=nb[m])["hit"].to_numpy()
    return out


class Book:
    """events + null draws; evaluate(level offsets) returns per-row obs and null matrix."""

    def __init__(self, ev, vol_bars=240, tod_tol=30, seed=SEED):
        self.ev = ev
        self.t = pd.DatetimeIndex(ev["t"])
        self.side = ev["side"].to_numpy()
        self.i0 = mkt.pos_at_or_after(self.t)
        self.nb = mkt.pos_at_or_after(pd.DatetimeIndex(ev["day_close"])) - self.i0
        self.p0 = mkt.o[np.minimum(self.i0, len(mkt.o) - 1)]
        self.ve = lvol(self.t, vol_bars)
        self.vol_bars = vol_bars
        self.rt = cl.sample_times(self.t, 5, 30, seed=seed, tod_tol_min=tod_tol)
        self.tk, self.px, self.vn, self.nrun = [], [], [], []
        for k in range(5):
            tk = pd.DatetimeIndex(self.rt[:, k]).tz_localize("UTC")
            self.tk.append(tk)
            okk = ~tk.isna()
            px = np.full(len(tk), np.nan)
            px[okk] = mkt.o[mkt.pos_at_or_after(tk[okk])]
            self.px.append(px)
            vn = np.full(len(tk), np.nan)
            vn[okk] = lvol(tk[okk], vol_bars)
            self.vn.append(vn)
            r = np.full((len(tk), 2), np.nan)
            rr = cl.running_hilo(tk[okk], "1D", m1=m1)
            r[okk, 0], r[okk, 1] = rr["high"].to_numpy(), rr["low"].to_numpy()
            self.nrun.append(r)

    def run(self, cap, spread=0.0, beyond_only=False):
        side = self.side
        dist = (cap - self.p0) * side
        obs = hits(self.t, cap + side * spread, side, self.nb)
        mat = np.full((len(cap), 5), np.nan)
        for k in range(5):
            tk, px, vn = self.tk[k], self.px[k], self.vn[k]
            ok = np.flatnonzero(np.isfinite(px))
            dd = dist[ok] * vn[ok] / self.ve[ok]
            lev = px[ok] + side[ok] * dd
            h = hits(tk[ok], lev + side[ok] * spread, side[ok], self.nb[ok])
            if beyond_only:   # null level must ALSO lie beyond its own day's running extreme
                nh, nl = self.nrun[k][ok, 0], self.nrun[k][ok, 1]
                beyond = np.where(side[ok] == 1, lev > nh, lev < nl)
                h = np.where(beyond, h, np.nan)
            mat[ok, k] = h
        return obs, mat


def stat(obs, mat, t, sel=None, n_boot=1000, seed=1):
    cnt = np.isfinite(mat).sum(1)
    nm = np.where(cnt > 0, np.nansum(mat, 1) / np.maximum(cnt, 1), np.nan)
    keep = np.isfinite(obs) & np.isfinite(nm)
    if sel is not None:
        keep &= sel
    o, n_, tt = obs[keep], nm[keep], t[keep]
    if len(o) < 30:
        return {"n": int(len(o))}
    d = float(o.mean() - n_.mean())
    day = cl.trading_day(tt)
    codes = pd.factorize(day)[0]
    nd = codes.max() + 1
    so = np.bincount(codes, o, nd)
    sn = np.bincount(codes, n_, nd)
    c = np.bincount(codes, minlength=nd).astype(float)
    rg = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for b in range(n_boot):
        w = np.bincount(rg.integers(0, nd, nd), minlength=nd)
        bs[b] = (w @ so - w @ sn) / (w @ c)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"n": int(len(o)), "days": int(nd), "obs": round(float(o.mean()), 5),
            "null": round(float(n_.mean()), 5), "diff": round(d, 5),
            "ci": [round(float(lo), 5), round(float(hi), 5)],
            "excl0_neg": bool(hi < 0)}


OUT = {}


def rep(name, r):
    OUT[name] = r
    print(f"{name:55s} {json.dumps(r)}", flush=True)


def halves_years(name, b, obs, mat):
    t = b.t
    rep(name + " | H1 <2021", stat(obs, mat, t, np.asarray(t < pd.Timestamp("2021-01-01", tz="UTC"))))
    rep(name + " | H2 >=2021", stat(obs, mat, t, np.asarray(t >= pd.Timestamp("2021-01-01", tz="UTC"))))
    for y in range(2016, 2027):
        rep(f"{name} | year {y}", stat(obs, mat, t, np.asarray(t.year == y)))


if __name__ == "__main__":
    # 1. rebuild the reported statistic
    ev = events(14)
    b = Book(ev)
    obs, mat = b.run(ev["cap"].to_numpy())
    rep("A rebuild N14 (reported -0.00814)", stat(obs, mat, b.t))
    halves_years("A", b, obs, mat)
    for s in (1, -1):
        rep(f"A side {s}", stat(obs, mat, b.t, b.side == s))
    feed = np.asarray((b.t >= pd.Timestamp("2019-02-01", tz="UTC")) & (b.t < pd.Timestamp("2020-03-01", tz="UTC")))
    rep("A excl feed regression 2019-02..2020-02", stat(obs, mat, b.t, ~feed))
    hr = cl.to_ny(b.t).hour
    for lo_, hi_ in ((19, 24), (0, 7), (7, 12), (12, 17)):
        sel = np.asarray((hr >= lo_) & (hr < hi_))
        rep(f"A NY hours [{lo_},{hi_})", stat(obs, mat, b.t, sel))
    # remaining-range buckets (fraction of ADR already used)
    used = ((ev["hi"] - ev["lo"]) / ev["adr"]).to_numpy()
    for a_, z_ in ((0, .4), (.4, .6), (.6, .8), (.8, 1.0)):
        rep(f"A used ADR in [{a_},{z_})", stat(obs, mat, b.t, (used >= a_) & (used < z_)))

    # 2. spread: level must be exceeded by 0.15 / 0.30 pt (both arms)
    for sp in (0.15, 0.30):
        o2, m2 = b.run(ev["cap"].to_numpy(), spread=sp)
        rep(f"A spread {sp}pt", stat(o2, m2, b.t))

    # 3. structural: ADR multiples on the SAME rows (all beyond the running extreme)
    for mult in (1.1, 1.25, 1.5):
        cap = np.where(b.side == 1, ev["lo"] + mult * ev["adr"], ev["hi"] - mult * ev["adr"])
        o2, m2 = b.run(cap)
        rep(f"S mult {mult} same rows", stat(o2, m2, b.t))
    # structural: levels beyond extreme by a FIXED fraction of remaining range that is not ADR
    rem = (ev["adr"] - (ev["hi"] - ev["lo"])).to_numpy()
    for f in (0.5, 0.75):
        cap = np.where(b.side == 1, ev["hi"] + f * rem, ev["lo"] - f * rem)
        o2, m2 = b.run(cap)
        rep(f"S extreme + {f} x remaining (sub-ADR) same rows", stat(o2, m2, b.t))
    # 4. conditional null: null level must ALSO lie beyond its own day's running extreme
    o2, m2 = b.run(ev["cap"].to_numpy(), beyond_only=True)
    rep("S beyond-extreme null N14", stat(o2, m2, b.t))
    halves_years("S beyond-extreme null", b, o2, m2)
    for mult in (1.25,):
        cap = np.where(b.side == 1, ev["lo"] + mult * ev["adr"], ev["hi"] - mult * ev["adr"])
        o3, m3 = b.run(cap, beyond_only=True)
        rep(f"S beyond-extreme null mult {mult}", stat(o3, m3, b.t))

    # 5. parameter perturbations within source wording
    for n_days, agg in ((5, "mean"), (10, "mean"), (20, "mean"), (14, "median"), (7, "mean")):
        e2 = events(n_days, agg)
        b2 = Book(e2)
        o2, m2 = b2.run(e2["cap"].to_numpy())
        r = stat(o2, m2, b2.t)
        r["H1"] = stat(o2, m2, b2.t, np.asarray(b2.t < pd.Timestamp("2021-01-01", tz="UTC"))).get("diff")
        r["H2"] = stat(o2, m2, b2.t, np.asarray(b2.t >= pd.Timestamp("2021-01-01", tz="UTC"))).get("diff")
        rep(f"P N{n_days} {agg}", r)
    for vb in (120, 480, 1440):
        b2 = Book(ev, vol_bars=vb)
        o2, m2 = b2.run(ev["cap"].to_numpy())
        rep(f"P vol window {vb}", stat(o2, m2, b2.t))
    # decision grid shifted by 30 min (half-hour closes) = 'shifted' structural control
    e2 = events(14, minute=30)
    b2 = Book(e2)
    o2, m2 = b2.run(e2["cap"].to_numpy())
    rep("P grid :30", stat(o2, m2, b2.t))
    # null draw seed (control noise, not a source parameter)
    for sd in (1, 2, 3):
        b2 = Book(ev, seed=sd)
        o2, m2 = b2.run(ev["cap"].to_numpy())
        rep(f"P null seed {sd}", stat(o2, m2, b2.t))

    json.dump(OUT, open("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/update_20261007/adr_u1007a_faith_out.json", "w"), indent=1)
