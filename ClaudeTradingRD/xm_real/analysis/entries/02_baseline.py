"""Step 2 - do the entries differ from random entries? Matched Monte-Carlo baselines + FDR.

Unit = decision event (first click of a burst), because taps seconds apart are one decision.
Every random entry goes through the same `sign_features` code as the real ones.

NULL A (hour-matched, as specified): each event is replaced by a random 5-second bar of the SAME UTC
        hour, any day of the trade week (2026-11-04 00:00 .. 11-11 13:44), same side. Independent draws.
NULL C (block-shift, cluster-aware): events are grouped into blocks (new block after a > 60 min pause);
        each block is slid as a whole by one random offset in +-[5, 90] min. Keeps side, the day, the
        local regime and the spacing between entries, so the null variance reflects how few independent
        decisions there really are. This is the stricter test of *timing*.
B = 10,000 synthetic weeks per null. Statistic = mean of the feature over events.
p = two-sided Monte-Carlo p ((k+1)/(B+1)); d = (real mean - null mean) / SD of single random entries;
q = Benjamini-Hochberg over every feature x subset tested under that null (Bonferroni flag also given).

Run: ../../../.venv/bin/python 02_baseline.py
"""
import math

import numpy as np
import pandas as pd

from lib import HERE, MIN, NS, TOUCH, ns, outcomes, sign_features

B, CHUNK, SEED = 10_000, 500, 20261111
rng = np.random.default_rng(SEED)
g = pd.read_parquet(HERE / "grid.parquet")
gc, ghour = g.c.to_numpy(), g.hour.to_numpy()
e = pd.read_csv(HERE / "entries_features.csv")
e["open_time"] = pd.to_datetime(e.open_time, utc=True, format="ISO8601")
ev = e[e.click_in_event == 0].reset_index(drop=True)
T = ns(ev.open_time)
side = np.where(ev.side.eq("BUY"), 1, -1)
gi = np.searchsorted(gc, T, "right") - 1
real_f = pd.concat([sign_features(g.iloc[gi].reset_index(drop=True), side), outcomes(g.iloc[gi].reset_index(drop=True), side)], axis=1)
FEATS = [c for c in real_f.columns if not c.startswith(("fwd", "touch"))]
OUTS = [c for c in real_f.columns if c.startswith(("fwd", "touch"))]
COLS = FEATS + OUTS
assert np.allclose(real_f[FEATS].to_numpy(float), ev[FEATS].to_numpy(float), equal_nan=True)  # same numbers as the csv

block = np.cumsum(np.r_[True, np.diff(T) > 60 * MIN])
SUBSETS = {"all": np.ones(len(ev), bool), "first": ev.role.eq("first").to_numpy(), "avg_add": ev.role.eq("avg_add").to_numpy(),
           "hedge": ev.role.eq("hedge").to_numpy()}
print(f"events {len(ev)} | blocks {block.max()} | " + ", ".join(f"{k} {v.sum()}" for k, v in SUBSETS.items()),
      f"| side mix BUY {int((side > 0).sum())} / SELL {int((side < 0).sum())}")


def draw_A(nb):
    pools = {h: np.flatnonzero(ghour == h) for h in np.unique(ev.hour_utc)}
    return np.column_stack([rng.choice(pools[h], nb) for h in ev.hour_utc])


def draw_C(nb):
    idx = np.empty((nb, len(ev)), np.int64)
    for b in np.unique(block):
        m = block == b
        got = np.empty((0, m.sum()), np.int64)
        while len(got) < nb:                                    # rejection: every event must land on an open market
            d = rng.uniform(5, 90, 2 * nb) * rng.choice([-1, 1], 2 * nb) * MIN
            tt = T[m][None, :] + d[:, None].astype(np.int64)
            j = np.searchsorted(gc, tt, "right") - 1
            ok = ((j >= 0) & (tt - gc[np.clip(j, 0, None)] <= 60 * NS)).all(axis=1)
            got = np.vstack([got, j[ok]])
        idx[:, m] = got[:nb]
    return idx


def null_means(draw):
    """-> means[subset] (B x n_cols) and the SD of single random entries per column."""
    means = {k: [] for k in SUBSETS}
    s1 = s2 = n = 0
    for _ in range(B // CHUNK):
        idx = draw(CHUNK)
        r = g.iloc[idx.ravel()].reset_index(drop=True)
        s = np.tile(side, CHUNK)
        x = pd.concat([sign_features(r, s), outcomes(r, s)], axis=1)[COLS].to_numpy(float).reshape(CHUNK, len(ev), -1)
        for k, m in SUBSETS.items():
            means[k].append(np.nanmean(x[:, m, :], axis=1))
        flat = x.reshape(-1, x.shape[2])
        s1, s2, n = s1 + np.nansum(flat, 0), s2 + np.nansum(flat ** 2, 0), n + (~np.isnan(flat)).sum(0)
    return {k: np.vstack(v) for k, v in means.items()}, np.sqrt(s2 / n - (s1 / n) ** 2)


def bh(p):
    p = np.asarray(p)
    o = np.argsort(p)
    q = np.minimum.accumulate((p[o] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]
    out = np.empty(len(p))
    out[o] = np.minimum(q, 1)
    return out


res = []
for name, draw in (("A", draw_A), ("C", draw_C)):
    nm, sd1 = null_means(draw)
    for k, m in SUBSETS.items():
        real = np.nanmean(real_f[COLS].to_numpy(float)[m], axis=0)
        mu, sd = nm[k].mean(0), nm[k].std(0)
        p = ((np.abs(nm[k] - mu) >= np.abs(real - mu) - 1e-12).sum(0) + 1) / (B + 1)
        for i, c in enumerate(COLS):
            res.append(dict(null=name, subset=k, n=int(m.sum()), n_valid=int(real_f[c][m].notna().sum()), feature=c,
                            family="outcome" if c in OUTS else "feature", real=real[i], null_mean=mu[i],
                            d=(real[i] - mu[i]) / sd1[i], z=(real[i] - mu[i]) / sd[i], p=p[i]))
res = pd.DataFrame(res)
for (nl, fam), x in res.groupby(["null", "family"]):               # BH within each null x family, across all subsets
    res.loc[x.index, "q"] = bh(x.p.to_numpy())
    res.loc[x.index, "bonf"] = x.p.to_numpy() * len(x) < 0.05
    res.loc[x.index, "n_tests"] = len(x)
res.to_csv(HERE / "baseline_tests.csv", index=False)

w = res.pivot_table(index=["family", "subset", "feature"], columns="null", values=["real", "null_mean", "d", "z", "p", "q"], sort=False)
w.columns = [f"{a}_{b}" for a, b in w.columns]
w = w.reset_index()
w["real"] = w.real_A
pd.set_option("display.width", 250, "display.max_rows", 500)
show = ["feature", "real", "null_mean_A", "d_A", "p_A", "q_A", "null_mean_C", "d_C", "p_C", "q_C"]
for fam in ("feature", "outcome"):
    for k in SUBSETS:
        x = w[(w.family == fam) & (w.subset == k)]
        x = x.reindex(x.z_A.abs().sort_values(ascending=False).index)
        print(f"\n=== {fam} | subset {k} (n events {int(SUBSETS[k].sum())}) | tests in family: {int(res[res.family == fam].n_tests.iloc[0])} per null ===")
        print(x[show].round(4).to_string(index=False))
sig = res[(res.q < 0.05)].groupby(["family", "null"]).size()
print("\ncount of q<0.05 by family/null:\n", sig.to_string())
both = w[(w.q_A < 0.05) & (w.q_C < 0.05)]
print("\nq<0.05 under BOTH nulls:\n", both[["family", "subset"] + show].round(4).to_string(index=False))

# ---- what the outcome tests could have seen: minimum detectable effect (80% power, two-sided 5%) = 2.8 x null SD ----
o = res[res.family == "outcome"].assign(mde=lambda x: 2.8 * ((x.real - x.null_mean) / x.z).abs())
print("\nminimum detectable difference in the outcome means (2.8 x SD of the null mean):")
print(o.pivot_table(index="feature", columns=["null", "subset"], values="mde", sort=False).round(3).to_string())

# ---- exit geometry alone: win rate and points expectancy of RANDOM entries under each first-touch rule ----
print("\nfirst-touch rules, all 124 decisions: win rate real vs random, and points expectancy = win*TP - (1-win)*SL")
for name, (tpd, sld, cap) in TOUCH.items():
    x = res[(res.feature == name) & (res.subset == "all")].set_index("null")
    exp = lambda w_: w_ * tpd - (1 - w_) * sld
    print(f"  {name:9s} TP {tpd:>4} / SL {sld:>4} / cap {cap * 5 / 3600:.0f}h | driftless no-cost win rate {sld / (tpd + sld):.3f} | real {x.real.A:.3f} (exp {exp(x.real.A):+.2f} pt)"
          f" | random A {x.null_mean.A:.3f} (exp {exp(x.null_mean.A):+.2f} pt, p {x.p.A:.3f}) | random C {x.null_mean.C:.3f} (p {x.p.C:.3f})"
          f" | resolved {int(x.n_valid.A)}/{int(x.n.A)}")

# ---- clock habits (no price involved): exact binomial vs a uniform clock ----
def binom_p(k, n, p0):                                              # two-sided exact
    pm = [math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in pm if x <= pm[k] + 1e-15))
n = len(ev)
for label, hit, p0 in (("minute within 0-4 of an M15 boundary", (ev.minute % 15 < 5), 1 / 3),
                       ("minute within 0-1 of an M5 boundary", (ev.minute % 5 < 2), 2 / 5),
                       ("minute 58-02 around the hour", ((ev.minute >= 58) | (ev.minute <= 2)), 5 / 60),
                       ("minute 28-32 around the half hour", ((ev.minute >= 28) & (ev.minute <= 32)), 5 / 60),
                       ("second 0-9 of the minute (just after an M1 close)", (ev.second < 10), 1 / 6)):
    k = int(hit.sum())
    print(f"clock: {label}: {k}/{n} = {k / n:.3f} vs uniform {p0:.3f}, binomial p = {binom_p(k, n, p0):.3f}")
