"""Structural control.

For every real 1h-CISD trade, draw control trades at random 1h closes within +-30 days
(same NY hour-of-day), entry next M1 open, and place the stop BEYOND THE EXTREME OF THE
PRIOR k=1..3 CLOSED 1h CANDLES (k chosen so the distance best matches the real stop;
accepted only within 0.8x..1.25x).  2R target, 10h wall-clock hold, same cost.
Two direction variants: (S) same direction as the real trade, (R) random direction.
Also: a 'swing' variant whose stop is beyond the extreme of the prior 4..12 candles
(closer to how far back a CISD protected swing sits).

Then:
  A. gated / complement real R minus their structural control
  B. gate diff re-scored against the structural control
  C. GENERIC-SWEEP test: apply the SAME poi_a gate (detectors.poi.poi_gate, the extreme
     bar = the bar that set the control's stop, body-hold window up to the decision bar)
     to the structural control book itself.  If the random structural book shows the same
     pass-vs-fail gap, the POI gate is a generic "stops behind an extreme that swept a
     swing survive" effect, not something tied to the CISD/POI concept.
  D. tie 50/50 re-score of the real book.
"""
from common import *
from detectors.poi import poi_gate, range_from_swing

ev, an = load_events()
m1 = cl.load_m1(); mkt = cl.get_market(m1)
b = cl.bars("1h"); df = b[["open", "high", "low", "close"]]
H, L = df.high.to_numpy(), df.low.to_numpy()
bct = pd.DatetimeIndex(b.close_time).as_unit("ns")
bct_ns = bct.asi8
tr = pd.read_pickle(DD + "/trades_primary.pkl")          # from 01 (harness trades, gate col)
tr = tr[np.isfinite(tr.risk)].reset_index(drop=True)
n = len(tr)
COST_R = 0.04
HOLD = np.timedelta64(10, "h")
ny_hour_bars = bct.tz_convert("America/New_York").hour.to_numpy()
ny_hour_real = pd.DatetimeIndex(tr.decision_time).tz_convert("America/New_York").hour.to_numpy()
real_pos = np.searchsorted(bct_ns, pd.DatetimeIndex(tr.decision_time).as_unit("ns").asi8)  # bar whose close == decision
assert (bct_ns[real_pos] == pd.DatetimeIndex(tr.decision_time).as_unit("ns").asi8).all()

# bars with enough M1 to be tradable (skip weekend placeholders)
valid_bar = (b.n_m1.to_numpy() > 0)


# precomputed per-bar geometry: entry at next M1 open after each bar close; k-bar extremes
TN = mkt.tn.view('int64')
BAR_I0 = np.searchsorted(TN, bct_ns)
BAR_I0c = np.clip(BAR_I0, 0, len(mkt.tn) - 1)
BAR_ENTRY = mkt.o[BAR_I0c]
NB = len(bct_ns)


def kbar_ext(k):
    lo = pd.Series(L).rolling(k).min().to_numpy(); hi = pd.Series(H).rolling(k).max().to_numpy()
    # position of the extreme bar (last occurrence irrelevant; first argmin)
    lpos = np.full(NB, -1); hpos = np.full(NB, -1)
    win = np.lib.stride_tricks.sliding_window_view
    lpos[k - 1:] = np.arange(NB - k + 1) + win(L, k).argmin(1)
    hpos[k - 1:] = np.arange(NB - k + 1) + win(H, k).argmax(1)
    return lo, hi, lpos, hpos


def build_controls(kset, dir_mode, reps=5, tries=80, seed=7):
    rng = np.random.default_rng(seed)
    K = [kbar_ext(k) for k in kset]
    day_ns = np.int64(86400 * 10**9)
    rows = []
    for j in range(n):
        p0 = real_pos[j]; risk = tr.risk[j]; sgn0 = tr.direction[j]
        lo_p = np.searchsorted(bct_ns, bct_ns[p0] - 30 * day_ns)
        hi_p = np.searchsorted(bct_ns, bct_ns[p0] + 30 * day_ns)
        cand = np.arange(max(lo_p, 15), min(hi_p, NB - 1))
        cand = cand[(ny_hour_bars[cand] == ny_hour_real[j]) & valid_bar[cand] & (cand != p0) & (BAR_I0[cand] < len(mkt.tn))]
        if len(cand) == 0:
            continue
        P = rng.choice(cand, size=tries, replace=True)
        S = np.full(tries, sgn0) if dir_mode == "S" else np.where(rng.random(tries) < .5, 1, -1)
        E = BAR_ENTRY[P]
        best_d = np.full(tries, np.nan); best_s = np.full(tries, np.nan); best_e = np.full(tries, -1); best_k = np.zeros(tries, int)
        for k, (lo, hi, lpos, hpos) in zip(kset, K):
            stop = np.where(S > 0, lo[P], hi[P]); e = np.where(S > 0, lpos[P], hpos[P])
            d = S * (E - stop)
            d = np.where(d > 0, d, np.nan)
            better = np.isfinite(d) & (~np.isfinite(best_d) | (np.abs(np.log(d / risk)) < np.abs(np.log(best_d / risk))))
            best_d = np.where(better, d, best_d); best_s = np.where(better, stop, best_s)
            best_e = np.where(better, e, best_e); best_k = np.where(better, k, best_k)
        ok = np.flatnonzero(np.isfinite(best_d) & (best_d / risk >= 0.8) & (best_d / risk <= 1.25))[:reps]
        for i in ok:
            rows.append((j, P[i], S[i], BAR_I0[P[i]], E[i], best_s[i], best_d[i], best_e[i], best_k[i]))
    c = pd.DataFrame(rows, columns=["src", "pos", "sgn", "i0", "entry", "stop", "risk", "ext_pos", "k"])
    c["target"] = c.entry + c.sgn * 2.0 * c.risk
    c["i1"] = np.searchsorted(TN, TN[c.i0.to_numpy()] + np.int64(10 * 3600 * 10**9))
    c = c[c.i1 > c.i0].reset_index(drop=True)
    res = cl.resolve_trades(mkt, c.sgn.to_numpy() > 0, c.stop.to_numpy(), c.target.to_numpy(),
                            c.i0.to_numpy(), c.i1.to_numpy())
    c["gross_R"] = c.sgn * (res["exit_px"] - c.entry) / c.risk
    c["net_R"] = c.gross_R - COST_R
    c["reason"] = res["reason"]
    c["amb"] = res["ambiguous"] | res["open_tgt"]
    return c


def summarize(c, label):
    cm = c.groupby("src").net_R.mean()
    t = tr.copy(); t["sctrl"] = cm.reindex(range(n)).to_numpy()
    t = t[np.isfinite(t.sctrl)]
    t["sadj"] = t.net_R - t.sctrl
    day = cl.trading_day(t.decision_time)
    g, cc = t.gate.to_numpy(), ~t.gate.to_numpy()
    fill = len(t) / n
    print(f"\n== {label}: control fill {fill:.3f}, ctrl draws {len(c)}, mean k {c.k.mean():.2f}, "
          f"ctrl mean net R {c.net_R.mean():+.4f}, ctrl exit mix stop/tgt/time "
          f"{np.bincount(c.reason, minlength=3) / len(c)}")
    for nm, msk in (("gated", g), ("complement", cc), ("all", np.ones(len(t), bool))):
        m, lo, hi, k = day_boot_ci(t.sadj[msk], day[msk])
        print(f"  {nm:10s} real {t.net_R[msk].mean():+.4f}  struct-ctrl {t.sctrl[msk].mean():+.4f}  "
              f"adj {m:+.4f} [{lo:+.4f},{hi:+.4f}] n={k}")
    d, lo, hi, p = diff_boot_ci(t.sadj[g], day[g], t.sadj[cc], day[cc])
    print(f"  GATE DIFF vs structural ctrl: {d:+.4f} [{lo:+.4f},{hi:+.4f}] p={p:.4f}")
    t["yr"] = t.decision_time.dt.year
    t["blk"] = pd.qcut(t.decision_time.astype("int64"), 4, labels=["B1", "B2", "B3", "B4"])
    t["half"] = np.where(t.decision_time < pd.Timestamp("2021-01-01", tz="UTC"), "H1", "H2")
    for col in ("half", "blk"):
        print("  ", col, t.groupby(col, observed=True).apply(
            lambda x: round(x[x.gate].sadj.mean() - x[~x.gate].sadj.mean(), 3)).to_dict())
    return t


def generic_sweep(c, label):
    """poi_a gate applied to the structural control book's own stop-setting extreme."""
    pas = np.zeros(len(c), bool); rext = np.zeros(len(c), bool)
    for i, r in enumerate(c.itertuples(index=False)):
        res = poi_gate(df, int(r.ext_pos), "bullish" if r.sgn > 0 else "bearish", lookback=40,
                       timeframe="1h", setup_type="reversal", require_body_half_hold=True,
                       body_hold_bars=max(0, int(r.pos) - int(r.ext_pos)))
        pas[i] = bool(res.passed)
        e = int(r.ext_pos); d_ = "bullish" if r.sgn > 0 else "bearish"
        s0 = range_from_swing(df, e, d_, lookback=40)
        rext[i] = (L[e] <= L[s0:e + 1].min()) if r.sgn > 0 else (H[e] >= H[s0:e + 1].max())
    c = c.copy(); c["poi"] = pas; c["rext"] = rext
    day = cl.trading_day(pd.DatetimeIndex(bct[c.pos.to_numpy()]))
    d, lo, hi, p = diff_boot_ci(c.net_R[c.poi], day[c.poi], c.net_R[~c.poi], day[~c.poi])
    print(f"\n== GENERIC SWEEP on {label}: pass rate {pas.mean():.3f}; pass net R {c.net_R[c.poi].mean():+.4f} "
          f"(n={c.poi.sum()}), fail {c.net_R[~c.poi].mean():+.4f} (n={(~c.poi).sum()}); "
          f"diff {d:+.4f} [{lo:+.4f},{hi:+.4f}] p={p:.4f}")
    d, lo, hi, p = diff_boot_ci(c.net_R[c.rext], day[c.rext], c.net_R[~c.rext], day[~c.rext])
    print(f"   range-extreme label: rate {rext.mean():.3f}; true-extreme {c.net_R[c.rext].mean():+.4f}, "
          f"higher-low/lower-high {c.net_R[~c.rext].mean():+.4f}; diff {d:+.4f} [{lo:+.4f},{hi:+.4f}] p={p:.4f}")
    print("   crosstab poi x rext mean net R:\n", c.groupby(["rext", "poi"]).net_R.agg(["size", "mean"]).round(4))
    return c


out = {}
for kset, lab in (((1, 2, 3), "k1-3"), (tuple(range(4, 13)), "k4-12")):
    for dm in ("S", "R"):
        c = build_controls(kset, dm)
        name = f"{lab} dir={dm}"
        out[name] = summarize(c, name)
        c.to_pickle(DD + f"/ctrl_{lab}_{dm}.pkl")
        if dm == "R":
            generic_sweep(c, name)

# D. 50/50 tie re-score of the real book (harness columns)
t = tr.copy(); t["adj5"] = t.net_R_5050 - t.ctrl_mean_R_5050
day = cl.trading_day(t.decision_time)
d, lo, hi, p = diff_boot_ci(t.adj5[t.gate], day[t.gate], t.adj5[~t.gate], day[~t.gate])
print(f"\n== tie 50/50 re-score: real ambiguous share {t.tie.mean():.5f}; gate diff {d:+.4f} [{lo:+.4f},{hi:+.4f}] p={p:.4f}")
