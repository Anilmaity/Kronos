"""Step 3 - counterfactual exits ON THE SAME 178 ENTRIES, using only the S5 path after each entry.

Entry = the real fill price and time. Exit-side quote = basis-corrected S5 (long: bid, short: ask), so the
spread is paid inside the path. Every position is 0.04 lots ($4 per point). Rules of the simulator:
  * the path starts at the first bar that opens after the entry;
  * TP is a limit: filled AT the level (no credit for gapping through it);
  * stop fill = min(level, bar open) - 0.30 pt slippage  [stress: the bar's worst print];
  * stop and target inside the same 5-second bar -> the stop wins;
  * a time stop exits at the open of the first bar >= entry + T;
  * unresolved at the end of data (2026-11-11 13:43 UTC) -> marked to market, counted as OPEN.
Families: (a) fixed TP x SL grid, (b) time stop, (c) break-even after +X, (d) the trader's own TP + hard SL,
(e) the trader's real exits with a hard SL laid over them. Controls for (a): same entries moved to a random
bar within +-60 min (one shift per burst), same side and flipped side, 200 draws each.
Run: python 03_counterfactuals.py      (about 1-2 min)
"""
import numpy as np
import pandas as pd

from common import BAR_NS, HERE, RES, USD_PER_PT, Quotes, load_trades, stats

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60); pd.set_option("display.max_rows", 400)
out = []
P = lambda *a: (print(*a), out.append(" ".join(str(x) for x in a)))

SLIP = 0.30
TPS = np.arange(2, 16).astype(float)                                   # 2..15 pts
SLS = np.array([3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30], float)
N_DRAWS, JITTER_MIN, SEED = 200, 60, 20261111

q = Quotes()
t = load_trades()
x = pd.read_csv(HERE / "trade_excursions.csv")
assert (x.position_id.values == t.position_id.values).all()
for c in ("add_to_loser", "hedge_vs_loser", "fresh", "burst_id", "is_lock_leg", "lock_t", "pts_econ"):
    t[c] = x[c].values
n = len(t)
SGN, ENT, T0 = t.sgn.values, t.entry.values, t.t0.values
I0 = np.array([q.first_bar_after(v) for v in T0])
SUBSETS = {"ALL": np.ones(n, bool), "EX_ADDS": ~t.add_to_loser.values, "ADDS_ONLY": t.add_to_loser.values, "FRESH": t.fresh.values}
DAY = t.open_time.dt.strftime("%m-%d").values


def side_px(sgn):
    return q.px["bid" if sgn > 0 else "ask"]


def running(sgn, entry, i0):
    """Running best favourable excursion and running worst adverse depth (both non-decreasing) from bar i0."""
    fh, al, _, _ = q.path(sgn, entry, i0)
    return np.maximum.accumulate(fh), np.maximum.accumulate(-al)


RUN = [running(SGN[k], ENT[k], I0[k]) for k in range(n)]


def resolve(sgn, entry, i0, RM, RN, tp=None, sl=None, be=None, i_time=None, stop_fill="slip"):
    """One position -> (points, bar index relative to i0, exit kind, worst adverse excursion while held)."""
    N, px = len(RM), side_px(sgn)
    exc = lambda key, i: sgn * (px[key][i0 + i] - entry)
    adv_key = "l" if sgn > 0 else "h"
    i_tp = int(np.searchsorted(RM, tp, "left")) if tp is not None else N
    i_st = int(np.searchsorted(RN, sl, "left")) if sl is not None else N
    lvl, kind = (-sl if sl is not None else 0.0), "SL"
    if be is not None:
        i_be = int(np.searchsorted(RM, be, "left"))
        if i_be < i_st and i_be < i_tp:                      # armed in a bar strictly before the stop / target bar
            a = px[adv_key][i0 + i_be + 1:]
            hit = np.flatnonzero(a <= entry if sgn > 0 else a >= entry)
            i_st, lvl, kind = (i_be + 1 + int(hit[0]) if len(hit) else N), 0.0, "BE"
    i_tm = N if i_time is None else max(int(i_time), 0)
    if i_tm < N and i_tm <= min(i_st, i_tp):
        pts, i, kind = exc("o", i_tm), i_tm, "TIME"
    elif i_st < N and i_st <= i_tp:
        pts = exc(adv_key, i_st) if stop_fill == "extreme" else min(lvl, exc("o", i_st)) - (SLIP if stop_fill == "slip" else 0.0)
        i = i_st
    elif i_tp < N:
        pts, i, kind = tp, i_tp, "TP"
    else:
        pts, i, kind = exc("c", N - 1), N - 1, "OPEN"
    return pts, i, kind, min(pts, -RN[i - 1] if i > 0 else 0.0)


def run(tp=None, sl=None, be=None, tmax_min=None, stop_fill="slip", idx=None):
    """tp / sl may be scalars or per-trade arrays (nan = none). Returns a per-trade DataFrame."""
    rows = []
    for k in (range(n) if idx is None else idx):
        tpk = tp[k] if isinstance(tp, np.ndarray) else tp
        tpk = None if tpk is None or tpk != tpk else float(tpk)
        i_time = None if tmax_min is None else np.searchsorted(q.T, T0[k] + int(tmax_min * 60e9), "left") - I0[k]
        rows.append((k,) + resolve(SGN[k], ENT[k], I0[k], *RUN[k], tp=tpk, sl=sl, be=be, i_time=i_time, stop_fill=stop_fill))
    r = pd.DataFrame(rows, columns=["k", "pts", "i", "kind", "mae"]).set_index("k")
    r["g_exit"] = I0[r.index] + r.i
    return r


def curve(k_idx, g0, g1, pts):
    """Mark-to-market book of 0.04-lot positions on the S5 grid -> (worst floating loss, max equity drawdown) in USD."""
    flo, real = np.zeros(q.n), np.zeros(q.n)
    for k, a, b, p in zip(k_idx, g0, g1, pts):
        b = min(int(b), q.n - 1)
        if b > a:
            flo[a:b] += SGN[k] * (side_px(SGN[k])["c"][a:b] - ENT[k])
        real[b] += p
    eq = real.cumsum() + flo
    return flo.min() * USD_PER_PT, (np.maximum.accumulate(eq) - eq).max() * USD_PER_PT


def summarise(r, label, **params):
    rows = []
    for name, m in SUBSETS.items():
        s = r[m[r.index]]
        if not len(s):
            continue
        mf, dd = curve(s.index, I0[s.index], s.g_exit.values, s.pts.values)
        rows.append(dict(family=label, **params, subset=name, **stats(s.pts.values), worst_mae=round(s.mae.min(), 1),
                         min_float_usd=round(mf), max_dd_usd=round(dd), n_open=int((s.kind == "OPEN").sum()),
                         n_tp=int((s.kind == "TP").sum()), n_stop=int(s.kind.isin(["SL", "BE"]).sum()), n_time=int((s.kind == "TIME").sum()),
                         med_hold_min=round(float(np.median((q.T[np.minimum(s.g_exit.values, q.n - 1)] - T0[s.index]) / 6e10)), 1)))
    return rows


# ---- self-check of the simulator ------------------------------------------------------------------------
def selfcheck():
    # synthetic long: entry 100; bars (o,h,l,c): flat, then one bar that touches +5 AND -5, then a gap down to 90
    class _Q:  # minimal stand-in for the price store
        pass
    save = q.px
    o = np.array([100, 100, 100, 90.0]); h = np.array([101, 105, 100, 91.0]); l = np.array([99.5, 95, 100, 89.0]); c = np.array([100, 100, 100, 90.0])
    q.px = {"bid": dict(o=o, h=h, l=l, c=c), "ask": dict(o=o, h=h, l=l, c=c)}
    RM, RN = np.maximum.accumulate(h - 100), np.maximum.accumulate(100 - l)
    assert resolve(1, 100, 0, RM, RN, tp=5, sl=5, stop_fill="level")[:3] == (-5, 1, "SL")            # same-bar tie -> stop
    assert resolve(1, 100, 0, RM, RN, tp=5, sl=7, stop_fill="level")[:3] == (5, 1, "TP")
    assert resolve(1, 100, 0, RM, RN, tp=6, sl=7, stop_fill="level")[:3] == (-10, 3, "SL")           # gap: filled at the open
    assert resolve(1, 100, 0, RM, RN, tp=6, sl=7, stop_fill="extreme")[0] == -11
    assert resolve(1, 100, 0, RM, RN, tp=6, sl=20, be=1, stop_fill="level")[:3] == (0.0, 1, "BE")    # armed bar 0, back to entry bar 1
    assert resolve(1, 100, 0, RM, RN, tp=6, sl=20, i_time=2)[:3] == (0, 2, "TIME")
    assert resolve(1, 100, 0, RM, RN, tp=50)[:3] == (-10, 3, "OPEN")
    q.px = save
    # real data: the trader's own TP with no stop must reproduce his 42 real TP exits to the bar
    tpd = t.tp_dist.values
    r = run(tp=tpd)
    real_tp = np.flatnonzero((t.reason == "TP").values)
    dt = (q.T[r.g_exit[real_tp].values] - t.t1.values[real_tp]) / 1e9
    assert (r.kind[real_tp] == "TP").all() and np.abs(dt).max() <= 10, (r.kind[real_tp].value_counts(), dt)
    P(f"self-check OK: synthetic ordering/gap/BE/time cases pass; real TP exits reproduced {len(real_tp)}/{len(real_tp)} (max |dt| {np.abs(dt).max():.1f}s)")


selfcheck()
res = []

# ---- baseline: what he actually did, at flat 0.04 ------------------------------------------------------
g_act = np.array([np.searchsorted(q.T, v, "right") - 1 for v in np.where(t.is_lock_leg | (t.lock_t != t.lock_t), t.t1.values, t.lock_t.fillna(0).values).astype("int64")])
base = pd.DataFrame(dict(pts=t.pts_econ.values, i=g_act - I0, kind="ACTUAL", mae=x.mae_pts.values, g_exit=g_act))
BASE = pd.DataFrame(summarise(base, "actual"))
res += BASE.to_dict("records")
mf_u, dd_u = None, None
flo, real = np.zeros(q.n), np.zeros(q.n)                                  # the same book at his real lot sizes
for k in range(n):
    a, b = I0[k], int(g_act[k])
    if b > a:
        flo[a:b] += SGN[k] * (side_px(SGN[k])["c"][a:b] - ENT[k]) * t.volume[k] * 100
    real[b] += t.profit[k]
eq = real.cumsum() + flo
P("\n== baseline: the trader's real exits ==")
P(BASE.drop(columns=["family"]).to_string(index=False))
P(f"at his real lot sizes: net ${t.profit.sum():.0f}; worst simultaneous floating loss ${flo.min():.0f}; max mark-to-market drawdown ${(np.maximum.accumulate(eq) - eq).max():.0f}")

# ---- (a) fixed TP x SL grid ------------------------------------------------------------------------------
per_trade = {}
for tp in TPS:
    for sl in SLS:
        r = run(tp=tp, sl=sl)
        per_trade[(tp, sl)] = r.pts.values
        res += summarise(r, "a_grid", tp=tp, sl=sl)
GRID = pd.DataFrame([r for r in res if r["family"] == "a_grid"])


def grid_fast(sgn, entry, i0):
    """Vectorised (tp x sl) outcome matrix for one path - used for the controls and cross-checked against resolve()."""
    RM, RN = running(sgn, entry, i0)
    N, px = len(RM), side_px(sgn)
    i_tp, i_sl = np.searchsorted(RM, TPS, "left"), np.searchsorted(RN, SLS, "left")
    stop = np.minimum(-SLS, sgn * (px["o"][i0 + np.minimum(i_sl, N - 1)] - entry)) - SLIP
    m = np.where(i_sl[None, :] <= i_tp[:, None], np.where(i_sl < N, stop, np.nan)[None, :], np.where(i_tp < N, TPS, np.nan)[:, None])
    return np.where(np.isnan(m), sgn * (px["c"][-1] - entry), m)


fast = np.stack([grid_fast(SGN[k], ENT[k], I0[k]) for k in range(n)])
slow = np.stack([[per_trade[(tp, sl)] for sl in SLS] for tp in TPS]).transpose(2, 0, 1)
assert np.allclose(fast, slow), "vectorised grid disagrees with resolve()"

flipreal = np.stack([grid_fast(-SGN[k], float(q.at(T0[k], "bid" if SGN[k] > 0 else "ask")), I0[k]) for k in range(n)])  # fade him: sell his buys at the bid
rng = np.random.default_rng(SEED)
ctrl_tfp = []                                                                    # geometry control for "time to first profit"
bursts = t.burst_id.values
ub = np.unique(bursts)
lo = np.searchsorted(q.T, T0 - JITTER_MIN * 60 * 10**9, "left")
hi = np.minimum(np.searchsorted(q.T, T0 + JITTER_MIN * 60 * 10**9, "right"), q.n - 2)
first_of = {b: np.flatnonzero(bursts == b)[0] for b in ub}
ctrl = {flip: np.zeros((N_DRAWS, n, len(TPS), len(SLS))) for flip in (1, -1)}
for dr in range(N_DRAWS):
    jb = {b: int(rng.integers(lo[first_of[b]], hi[first_of[b]])) for b in ub}     # one random bar per burst
    for k in range(n):
        j = jb[bursts[k]]
        for flip in (1, -1):
            s = SGN[k] * flip
            e = (q.px["ask"] if s > 0 else q.px["bid"])["c"][j]                    # buy at ask, sell at bid, at that bar's close
            ctrl[flip][dr, k] = grid_fast(s, e, j + 1)
            if flip == 1 and dr < 40:
                hit = np.flatnonzero(q.path(s, e, j + 1, j + 1 + 720)[0] > 0)
                ctrl_tfp.append(5.0 * (hit[0] + 1) if len(hit) else np.inf)
rows = []
for name, m in SUBSETS.items():
    real_tot = fast[m].sum(0)
    same, flp = ctrl[1][:, m].sum(1), ctrl[-1][:, m].sum(1)
    for a, tp in enumerate(TPS):
        for b, sl in enumerate(SLS):
            rows.append(dict(subset=name, tp=tp, sl=sl, real_pts=round(real_tot[a, b], 1), ctrl_same_mean=round(same[:, a, b].mean(), 1),
                             ctrl_same_sd=round(same[:, a, b].std(), 1), real_pctile_vs_same=round(100 * (same[:, a, b] < real_tot[a, b]).mean()),
                             ctrl_flip_mean=round(flp[:, a, b].mean(), 1), ctrl_flip_sd=round(flp[:, a, b].std(), 1),
                             flip_real_pts=round(flipreal[m].sum(0)[a, b], 1)))
CTRL = pd.DataFrame(rows)
GRID = GRID.merge(CTRL, on=["subset", "tp", "sl"])
GRID.to_csv(RES / "cf_grid.csv", index=False)
piv = lambda sub, col, df=GRID: df[df.subset == sub].pivot(index="tp", columns="sl", values=col)
P("\n== (a) fixed TP x SL grid: total points per cell (rows TP, cols SL), stop slippage 0.30 ==")
for sub in ("ALL", "EX_ADDS", "FRESH"):
    P(f"-- {sub} (n={int(SUBSETS[sub].sum())}; real exits made {t.pts_econ[SUBSETS[sub]].sum():.0f} pts)")
    P(piv(sub, "total_pts").round(0).astype(int).to_string())
P("-- ALL: win %"); P(piv("ALL", "win_pct").round(0).astype(int).to_string())
P("-- ALL: profit factor"); P(piv("ALL", "pf").round(2).to_string())
P("-- ALL: max mark-to-market drawdown, USD at 0.04"); P(piv("ALL", "max_dd_usd").astype(int).to_string())
P("-- ALL: positions still open at data end"); P(piv("ALL", "n_open").astype(int).to_string())
P(f"-- ALL: mean total of the SAME-SIDE random-time control (+-{JITTER_MIN} min, {N_DRAWS} draws)"); P(piv("ALL", "ctrl_same_mean").round(0).astype(int).to_string())
P("-- ALL: percentile of the real entries inside that control distribution"); P(piv("ALL", "real_pctile_vs_same").astype(int).to_string())
P("-- ALL: mean total of the FLIPPED-SIDE random-time control"); P(piv("ALL", "ctrl_flip_mean").round(0).astype(int).to_string())
P("-- ALL: the trader's entries FADED at the same instant (sell his buys at the bid, buy his sells at the ask)"); P(piv("ALL", "flip_real_pts").round(0).astype(int).to_string())
P("-- EX_ADDS: percentile of the real entries vs same-side control"); P(piv("EX_ADDS", "real_pctile_vs_same").astype(int).to_string())
g = GRID[GRID.subset == "ALL"]
P(f"cells positive (ALL): {(g.total_pts > 0).sum()}/{len(g)}; PF>=1.2: {(g.pf >= 1.2).sum()}; real above the same-side control mean: {(g.real_pts > g.ctrl_same_mean).sum()}; "
  f"real >= 95th pct of control: {(g.real_pctile_vs_same >= 95).sum()}; median percentile {g.real_pctile_vs_same.median():.0f}")
for sub in ("ALL", "EX_ADDS", "FRESH"):
    gg = GRID[GRID.subset == sub]
    P(f"{sub}: cells positive {(gg.total_pts > 0).sum()}/{len(gg)}; with SL<=20 positive {((gg.total_pts > 0) & (gg.sl <= 20)).sum()}/{(gg.sl <= 20).sum()}; real <=5th pct of same-side control in {(gg.real_pctile_vs_same <= 5).sum()} cells, >=95th in {(gg.real_pctile_vs_same >= 95).sum()} (chance alone: about {len(gg) * 0.05:.0f} each); best cell TP{gg.loc[gg.total_pts.idxmax(), 'tp']:g}/SL{gg.loc[gg.total_pts.idxmax(), 'sl']:g} {gg.total_pts.max():.0f} pts")
P(f"control check, both sides pooled = pure geometry: mean per trade {((g.ctrl_same_mean + g.ctrl_flip_mean) / 2 / n).mean():+.3f} pts (expected about -spread-slip share)")
P(f"faded entries positive in {(g.flip_real_pts > 0).sum()}/{len(g)} cells; real minus faded > 0 in {(g.real_pts > g.flip_real_pts).sum()}/{len(g)}")
ctrl_tfp = np.array(ctrl_tfp); real_tfp = x.t_first_profit_s.fillna(np.inf).values
P(f"geometry check on 'time to first profit': real entries median {np.median(real_tfp):.0f}s, in profit at some moment within 60s {100 * (real_tfp <= 60).mean():.0f}%, within 5 min {100 * (real_tfp <= 300).mean():.0f}%;  "
  f"random same-side entries ({len(ctrl_tfp)} draws) median {np.median(ctrl_tfp):.0f}s, within 60s {100 * (ctrl_tfp <= 60).mean():.0f}%, within 5 min {100 * (ctrl_tfp <= 300).mean():.0f}%")
best = g.sort_values("total_pts", ascending=False).head(8)
P("top 8 cells (ALL):"); P(best[["tp", "sl", "total_pts", "usd_004", "win_pct", "pf", "worst_trade", "worst_mae", "min_float_usd", "max_dd_usd", "n_open", "med_hold_min", "ctrl_same_mean", "ctrl_same_sd", "real_pctile_vs_same", "ctrl_flip_mean"]].to_string(index=False))

# stop-fill stress + per-day concentration for a few representative cells
SEL = [(3.0, 30.0), (4.0, 25.0), (5.0, 10.0), (5.0, 20.0), (10.0, 10.0), (10.0, 20.0), (15.0, 15.0), (15.0, 30.0)]
rows, days = [], []
for tp, sl in SEL:
    for fill in ("level", "slip", "extreme"):
        r = run(tp=tp, sl=sl, stop_fill=fill)
        for sub in ("ALL", "EX_ADDS"):
            rows.append(dict(tp=tp, sl=sl, stop_fill=fill, subset=sub, **stats(r.pts[SUBSETS[sub]].values)))
        if fill == "slip":
            days.append(pd.Series(r.pts.values).groupby(DAY).sum().round(0).rename(f"TP{tp:g}/SL{sl:g}"))
STRESS = pd.DataFrame(rows)
P("\npower: mean points per decision (one value per burst) and its standard error, ALL entries:")
for tp, sl in SEL:
    bm = pd.Series(per_trade[(tp, sl)]).groupby(bursts).mean()
    se = bm.std(ddof=1) / np.sqrt(len(bm))
    P(f"  TP{tp:g}/SL{sl:g}: mean {bm.mean():+.2f}  SE {se:.2f}  -> 95% band +-{1.96 * se:.2f} pts per decision = +-{1.96 * se * len(bm):.0f} pts on {len(bm)} decisions")
P("\nstop-fill stress (level = no slippage, slip = level-0.30, extreme = worst print of the 5s bar):")
P(STRESS.pivot_table(index=["tp", "sl", "subset"], columns="stop_fill", values="total_pts")[["level", "slip", "extreme"]].to_string())
BYDAY = pd.concat(days + [pd.Series(t.pts_econ.values).groupby(DAY).sum().round(0).rename("actual")], axis=1).T
P("\npoints by entry day (ALL):"); P(BYDAY.to_string())
BYDAY.to_csv(RES / "cf_by_day.csv")

# ---- (b) time stop ---------------------------------------------------------------------------------------
tpd = t.tp_dist.values
TMS = [1, 2, 5, 10, 15, 30, 60, 120, 240, 480]
for T in TMS:
    res += summarise(run(tmax_min=T), "b_time_only", tmax_min=T)
    res += summarise(run(tp=tpd, tmax_min=T), "b_actualTP_time", tmax_min=T)
    res += summarise(run(tp=5.0, tmax_min=T), "b_TP5_time", tmax_min=T)

spread0 = np.array([q.at(v, "ask") - q.at(v, "bid") for v in T0])
P(f"\n== (b0) drift after entry: points per position if simply closed T minutes later (no TP, no SL) ==")
P(f"a zero-edge entry is expected to show minus the spread paid: mean XM-equivalent spread at the 178 entries = {spread0.mean():.2f} (median {np.median(spread0):.2f})")
rows = []
for T in TMS:
    r = run(tmax_min=T)
    for sub in ("ALL", "EX_ADDS", "FRESH"):
        v = pd.Series(r.pts.values[SUBSETS[sub]])
        bm = v.groupby(bursts[SUBSETS[sub]]).mean()                               # one observation per burst
        rows.append(dict(T_min=T, subset=sub, n=len(v), bursts=len(bm), mean_pts=round(v.mean(), 2), in_profit_pct=round(100 * (v > 0).mean()),
                         burst_mean=round(bm.mean(), 2), burst_se=round(bm.std(ddof=1) / np.sqrt(len(bm)), 2),
                         t_vs_minus_spread=round((bm.mean() + spread0.mean()) / (bm.std(ddof=1) / np.sqrt(len(bm))), 2)))
DRIFT = pd.DataFrame(rows); DRIFT.to_csv(RES / "cf_drift.csv", index=False)
P(DRIFT.to_string(index=False))

# ---- (c) break-even after +X -----------------------------------------------------------------------------
tp_imp = np.where(np.isnan(tpd), np.nanmedian(tpd), tpd)                 # 37 positions had no TP: median distance imputed
for label, tp, sl in (("c_actualTP_noSL", tp_imp, None), ("c_actualTP_SL15", tp_imp, 15.0), ("c_TP5_SL15", 5.0, 15.0), ("c_TP10_SL15", 10.0, 15.0), ("c_TP15_SL30", 15.0, 30.0)):
    res += summarise(run(tp=tp, sl=sl), label, be=0.0, sl=sl if sl else np.nan)
    for be in (1.0, 2.0, 3.0, 5.0, 8.0):
        res += summarise(run(tp=tp, sl=sl, be=be), label, be=be, sl=sl if sl else np.nan)

# ---- (d) the trader's own TP + a hard stop -----------------------------------------------------------------
has_tp = np.flatnonzero(~np.isnan(tpd))
res += [dict(r, family="actual_tpset141") for r in summarise(base.iloc[has_tp], "actual_tpset141")]
dday = {}
SUB_ALL = dict(SUBSETS)
for sl in (None, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 75.0):
    SUBSETS = SUB_ALL
    res += summarise(run(tp=tp_imp, sl=sl), "d_actualTP_SL_all178_imputed", sl=sl if sl else np.inf)
    r = run(tp=tpd, sl=sl, idx=has_tp)
    res += summarise(r, "d_actualTP_SL_tpset141", sl=sl if sl else np.inf)
    if sl in (None, 10.0, 20.0, 25.0):
        dday[f"(d) own TP, SL {sl if sl else 'none'} (n=141)"] = r.pts.groupby(DAY[r.index]).sum().round(0)

# ---- (e) his real exits, with a hard stop laid over them ---------------------------------------------------
for sl in (3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0):
    rows = []
    for k in range(n):
        if t.is_lock_leg[k]:                                             # the lock leg only exists because of the loser it locked
            rows.append((0.0, g_act[k] - I0[k], "ACTUAL", 0.0)); continue
        i_sl = int(np.searchsorted(RUN[k][1], sl, "left"))
        if I0[k] + i_sl < g_act[k]:                                      # stop hit in a bar before his real exit / lock
            p, i, kind, mae = resolve(SGN[k], ENT[k], I0[k], *RUN[k], sl=sl)
            rows.append((p, i, kind, mae))
        else:
            rows.append((t.pts_econ[k], g_act[k] - I0[k], "ACTUAL", min(x.mae_pts[k], t.pts_econ[k])))
    r = pd.DataFrame(rows, columns=["pts", "i", "kind", "mae"]); r["g_exit"] = I0 + r.i
    res += [dict(z, usd_real_lots=round(float((r.pts.values * t.volume.values * 100)[SUBSETS[z["subset"]]].sum()))) for z in summarise(r, "e_actual_exits_plus_SL", sl=sl)]
    if sl in (10.0, 20.0, 25.0, 50.0):
        dday[f"(e) real exits + SL {sl:g}"] = r.pts.groupby(DAY).sum().round(0)
    if sl == 20.0:
        cut20 = r.kind.eq("SL").values
    if sl == 25.0:
        sw = cut20 & ~r.kind.eq("SL").values                                    # stopped by a 20-pt stop, survived a 25-pt one
        P(f"\n(e) the jump between SL 20 and SL 25 comes from {sw.sum()} positions whose worst point was 20-25 pts: real result {t.pts_econ[sw].sum():+.0f} pts vs {-(20 + SLIP) * sw.sum():.0f} if stopped; "
          f"by entry day/side: {pd.Series(1, index=pd.MultiIndex.from_arrays([DAY[sw], t.side.values[sw]])).groupby(level=[0, 1]).sum().to_dict()}; in {t.burst_id[sw].nunique()} decisions; "
          f"{int((t.tp[sw].between(4095.9, 4096.3)).sum())} of them are the Nov 9-10 short basket with TP ~4096")
    if sl == 10.0:
        cut = r.kind.eq("SL").values
        P(f"\n(e) detail at SL 10: {cut.sum()} positions stopped; of those {int((t.pts_econ[cut] > 0).sum())} were real winners worth {t.pts_econ[cut & (t.pts_econ > 0).values].sum():.0f} pts "
          f"and {int((t.pts_econ[cut] < 0).sum())} real losers worth {t.pts_econ[cut & (t.pts_econ < 0).values].sum():.0f} pts; stopped total {r.pts[cut].sum():.0f} pts")

dday["actual (n=178)"] = pd.Series(t.pts_econ.values).groupby(DAY).sum().round(0)
dday["actual (TP-set n=141)"] = pd.Series(t.pts_econ.values[has_tp]).groupby(DAY[has_tp]).sum().round(0)
DD = pd.DataFrame(dday).T.fillna(0)
P("\npoints by entry day, families (d) and (e):"); P(DD.to_string())
DD.to_csv(RES / "cf_by_day_de.csv")
ALLRES = pd.DataFrame(res)
ALLRES.to_csv(RES / "cf_all.csv", index=False)
show = ["subset", "n", "total_pts", "usd_004", "win_pct", "pf", "avg_win", "avg_loss", "worst_trade", "worst_mae", "min_float_usd", "max_dd_usd", "n_open", "n_tp", "n_stop", "n_time", "med_hold_min"]
P("\n== actual exits on the TP-set subset (n=141), baseline for (d) ==")
P(ALLRES[ALLRES.family == "actual_tpset141"][show].to_string(index=False))
P("\n(e) at his REAL lot sizes (USD), ALL: " + "  ".join(f"SL{r.sl:g}: ${r.usd_real_lots:.0f}" for r in ALLRES[(ALLRES.family == "e_actual_exits_plus_SL") & (ALLRES.subset == "ALL")].itertuples()) + f"   | no stop (actual): ${t.profit.sum():.0f}")
for fam, key in (("b_time_only", "tmax_min"), ("b_actualTP_time", "tmax_min"), ("b_TP5_time", "tmax_min"),
                 ("c_actualTP_noSL", "be"), ("c_actualTP_SL15", "be"), ("c_TP5_SL15", "be"), ("c_TP10_SL15", "be"), ("c_TP15_SL30", "be"),
                 ("d_actualTP_SL_tpset141", "sl"), ("d_actualTP_SL_all178_imputed", "sl"), ("e_actual_exits_plus_SL", "sl")):
    f = ALLRES[(ALLRES.family == fam) & ALLRES.subset.isin(["ALL", "EX_ADDS", "FRESH"])]
    P(f"\n== {fam} (by {key}; be=0 means no break-even rule; sl=inf means no stop) ==")
    P(f[[key] + show].sort_values(["subset", key]).to_string(index=False))
(RES / "03_counterfactuals.txt").write_text("\n".join(out) + "\n")
