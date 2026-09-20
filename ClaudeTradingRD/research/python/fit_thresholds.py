"""Measure, on real XAUUSD data, the quantities the corpus's undefined adjectives
resolve to — and price the thresholds it never states.

Read `meta/qualifier_calls.md` first. Part A established WHICH quantity each
blocked term is about; this script establishes WHAT VALUE it takes on XAUUSD, so
`meta/threshold_fits.md` can hand a backtest a default plus a sweep range.

The supervision problem, stated honestly
----------------------------------------
Part A yielded 56 curated narrated calls. **Not one of them can be tied to a
specific bar.** A transcript names no instrument, no date and no price; the
author says "this candle" while pointing at a screen we do not have. So a
supervised fit — "find the ratio that reproduces his labels" — is NOT available,
and this script does not pretend otherwise.

What is available instead is three weaker but real things, and this script does
all three:

  (1) DISTRIBUTIONS. Report each candidate ratio's distribution on XAUUSD so any
      proposed cut can be quoted as a percentile rather than as a bare number.
  (2) CORPUS-ANCHORED CUTS PRICED. The corpus does state two numbers — wick vs
      body (crossover 1.0) and equilibrium / "the upper half" (0.5). Measure
      where those sit and how many candles they admit.
  (3) OUTCOME-FITTING, which is the honest substitute for label-fitting. Every
      narrated label in Part A comes attached to a PREDICTION ("this doesn't
      support expansion", "expectations favour back towards the daily open").
      The prediction is testable even though the label instance is not
      recoverable. So: sweep the threshold, and report which cut best separates
      the outcome the author attaches to it. That fits the term to the behaviour
      it is supposed to name.

Everything here is offline: ClaudeTradingRD/m3_scalper/xau_m1_3y.parquet.

Run:  python fit_thresholds.py            (from research/)
      python fit_thresholds.py --quick    (1D/4h only, skips the leg scan)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bars import load_m1, resample                       # noqa: E402
from detectors.primitives import swing_points, fair_value_gaps   # noqa: E402

TFS = ["15min", "1h", "4h", "1D"]
TF_MINUTES = {"15min": 15, "1h": 60, "4h": 240, "1D": 1440}
PCTLS = [1, 5, 10, 25, 50, 75, 90, 95, 99]


def pct_of(series: pd.Series, value: float) -> float:
    """Percentile of the distribution that `value` sits at (share at or below)."""
    s = series.dropna()
    return float((s <= value).mean() * 100) if len(s) else float("nan")


def q(series: pd.Series) -> dict[int, float]:
    s = series.dropna()
    return {p: float(np.percentile(s, p)) for p in PCTLS} if len(s) else {}


def fmt(d: dict[int, float], nd: int = 3) -> str:
    return "  ".join(f"p{p}={v:.{nd}f}" for p, v in d.items())


# ── 1. candle geometry ────────────────────────────────────────────────────────
def candle_geometry(htf: pd.DataFrame, m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Per-candle wick/body/close geometry plus the TIME the extreme printed.

    `opposing_run` is the corpus's own numerator, fixed by SlWxhzhLo3A: the move
    from the OPEN to the extreme AGAINST the candle's eventual direction. For an
    up-closing candle that is open - low; for a down-closing candle, high - open.
    It is deliberately NOT high-minus-low and NOT the sum of both wicks.
    """
    o, h, l, c = (htf[k] for k in ("open", "high", "low", "close"))
    rng = (h - l).replace(0, np.nan)
    body = (c - o).abs()
    bullish = c >= o

    out = pd.DataFrame(index=htf.index)
    out["bullish"] = bullish
    out["range"] = h - l
    out["body"] = body
    out["opposing_run"] = np.where(bullish, o - l, h - o)
    out["following_run"] = np.where(bullish, h - c, c - l)   # the far-side wick
    out["wick_share_of_range"] = out["opposing_run"] / rng
    out["far_wick_share"] = out["following_run"] / rng
    out["wick_vs_body"] = out["opposing_run"] / body.replace(0, np.nan)
    out["body_share_of_range"] = body / rng
    # (close - low)/range for bullish, mirrored for bearish: 1.0 == closed AT the
    # extreme, which is 5rbFskdmEmU's "closes in the high or the low".
    out["close_position"] = np.where(bullish, (c - l) / rng, (h - c) / rng)

    # ---- time-share: WHEN in the candle did the opposing extreme print? ----
    # This is the axis SlWxhzhLo3A measures on ("uses most of its time period",
    # "almost half the time") and it is only computable because we hold M1.
    freq = tf if tf != "1D" else "1D"
    bucket = m1.index.floor(freq)
    g = m1.groupby(bucket)
    t_low = g["low"].idxmin()
    t_high = g["high"].idxmax()
    span = pd.Timedelta(minutes=TF_MINUTES[tf])
    tl = ((t_low.values - t_low.index.values) / span).astype("float64")
    th = ((t_high.values - t_high.index.values) / span).astype("float64")
    frac = pd.DataFrame({"t_low": tl, "t_high": th}, index=t_low.index)
    frac = frac.reindex(out.index)
    out["time_share_to_extreme"] = np.where(out["bullish"], frac["t_low"], frac["t_high"])
    return out


# ── 2. outcome fitting ────────────────────────────────────────────────────────
def outcomes(htf: pd.DataFrame, geo: pd.DataFrame, k: int = 3, mult: float = 1.0,
             atr_n: int = 20) -> pd.DataFrame:
    """The predictions the corpus attaches to the small/large-wick label.

    THREE measures, and the first two are reported only with a health warning:

    continued : next candle trades beyond THIS candle's extreme in its direction.
    reverted  : next candle trades back to THIS candle's OPEN
                (5UsKZ7pZqvY: "expectations is favoring back towards that open").

    Both of those are GEOMETRICALLY CONFOUNDED by the very quantity being
    bucketed. For a bullish candle, range = opposing_run + body + far_wick, so a
    large opposing run forces a small body, which puts the close near the open
    (making `reverted` trivially easy) and near the high (making `continued`
    trivially easy). Bucketing by wick share therefore moves both metrics for
    reasons that have nothing to do with the author's claim. They are kept
    because they are what the corpus literally says, and reported so the reader
    can see the artifact rather than be sold it.

    barrier   : THE ONE TO TRUST. From the candle's CLOSE, over the next `k`
                candles, does price reach close + mult*ATR in the candle's
                direction before close - mult*ATR against it? Both barriers are
                the same distance and neither is derived from the candle's own
                geometry, so the confound is removed. ATR is trailing and
                excludes the current candle.
    """
    o, h, l, c = (htf[x].to_numpy() for x in ("open", "high", "low", "close"))
    bull = geo["bullish"].to_numpy()
    n = len(htf)

    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[np.nan, c[:-1]]),
                                      np.abs(l - np.r_[np.nan, c[:-1]])))
    atr = pd.Series(tr).rolling(atr_n, min_periods=atr_n).mean().shift(1).to_numpy()

    barrier = np.full(n, np.nan)
    for i in range(n):
        a = atr[i]
        if not np.isfinite(a) or a <= 0 or i + k >= n:
            continue
        up, dn = c[i] + mult * a, c[i] - mult * a
        for j in range(i + 1, i + 1 + k):
            hit_up, hit_dn = h[j] >= up, l[j] <= dn
            if hit_up and hit_dn:
                break                      # same-bar ambiguity -> leave unknown
            if hit_up or hit_dn:
                fav = hit_up if bull[i] else hit_dn
                barrier[i] = 1.0 if fav else 0.0
                break

    nh, nl = np.r_[h[1:], np.nan], np.r_[l[1:], np.nan]
    out = pd.DataFrame(index=htf.index, dtype="float64")
    out["continued"] = np.where(bull, nh > h, nl < l).astype("float64")
    out["reverted"] = np.where(bull, nl <= o, nh >= o).astype("float64")
    out["barrier"] = barrier
    out.iloc[-1, out.columns.get_indexer(["continued", "reverted"])] = np.nan
    return out


def sweep(geo: pd.DataFrame, oc: pd.DataFrame, col: str, grid) -> pd.DataFrame:
    """For each cut, the outcome rates below ('small') and above ('large') it."""
    rows = []
    v = geo[col].replace([np.inf, -np.inf], np.nan)
    for t in grid:
        small, large = v.notna() & (v <= t), v.notna() & (v > t)
        if small.sum() < 50 or large.sum() < 50:
            continue
        r = dict(cut=float(t), n_small=int(small.sum()), n_large=int(large.sum()))
        for name in ("continued", "reverted", "barrier"):
            s = oc.loc[small, name].dropna()
            g = oc.loc[large, name].dropna()
            if len(s) < 30 or len(g) < 30:
                r[f"{name}_small"] = r[f"{name}_large"] = r[f"{name}_sep"] = np.nan
                continue
            r[f"{name}_small"] = s.mean()
            r[f"{name}_large"] = g.mean()
            r[f"{name}_sep"] = s.mean() - g.mean()
            r[f"{name}_n"] = len(s) + len(g)
        rows.append(r)
    return pd.DataFrame(rows)


# ── 3. the displacement comparative procedure (RESUME finding #7) ─────────────
def displacement_windows(df: pd.DataFrame, n: int = 4, left: int = 2, right: int = 2
                         ) -> pd.DataFrame:
    """After a short-term high/low breaks, measure the N-candle window.

    Implements 1oco9lesido literally: "if you just take these four candles when
    we broke this High here" -> "in the same amount of time right we have a
    larger range". Two quantities per break:
        win_range : high-low of the N candles from the break
        distance  : how far beyond the broken level price got within those N
    Both are normalised by the pre-break N-candle range so breaks are comparable
    across regimes; the corpus compares two instances on one chart, which is only
    meaningful if the yardstick is local.
    """
    sp = swing_points(df, left, right)
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    idx = df.index
    n_bars = len(df)

    # a swing is only usable `right` bars after it prints
    pending_h: list[tuple[int, float]] = []
    pending_l: list[tuple[int, float]] = []
    for i in range(n_bars):
        if sp["swing_high"].iloc[i]:
            pending_h.append((i + right, h[i]))
        if sp["swing_low"].iloc[i]:
            pending_l.append((i + right, l[i]))

    # advance a cursor per side instead of rescanning the pending list, which
    # would make the whole scan O(n^2) and unusable on the 15m series (~78k bars)
    cur = {"buy": 0, "sell": 0}
    live = {"buy": None, "sell": None}

    def level_at(pend, side, i):
        while cur[side] < len(pend) and pend[cur[side]][0] <= i:
            live[side] = pend[cur[side]][1]
            cur[side] += 1
        return live[side]

    rows = []
    last_hi = last_lo = None
    for i in range(left + right, n_bars - n):
        for side in ("buy", "sell"):
            lvl = level_at(pending_h if side == "buy" else pending_l, side, i)
            if lvl is None:
                continue
            broke = (h[i] > lvl) if side == "buy" else (l[i] < lvl)
            if not broke:
                continue
            prev = last_hi if side == "buy" else last_lo
            if prev is not None and prev == lvl:
                continue                      # same level, already counted
            if side == "buy":
                last_hi = lvl
            else:
                last_lo = lvl
            w = slice(i, i + n)
            win_range = h[w].max() - l[w].min()
            dist = (h[w].max() - lvl) if side == "buy" else (lvl - l[w].min())
            pre = slice(max(0, i - n), i)
            pre_range = h[pre].max() - l[pre].min()
            rows.append(dict(t=idx[i], side=side, level=lvl,
                             win_range=win_range, distance=dist,
                             pre_range=pre_range,
                             range_ratio=win_range / pre_range if pre_range else np.nan,
                             dist_ratio=dist / pre_range if pre_range else np.nan))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.set_index("t").sort_index()


def displacement_fire_rate(br: pd.DataFrame, k: int = 20) -> dict:
    """"Larger range AND greater distance" against a rolling local reference.

    The corpus compares one break to ONE other break on the same chart. A single
    reference is unstable, so the reference here is the trailing median of the
    last `k` breaks — the same comparison, made repeatable. The fire rate is the
    honest headline: how often does a break qualify as displacement at all?
    """
    if br.empty:
        return {}
    rr = br["win_range"].rolling(k, min_periods=k).median().shift(1)
    dd = br["distance"].rolling(k, min_periods=k).median().shift(1)
    both = (br["win_range"] > rr) & (br["distance"] > dd)
    only_r = (br["win_range"] > rr) & ~(br["distance"] > dd)
    valid = rr.notna()
    return dict(n_breaks=int(len(br)), n_scored=int(valid.sum()),
                fire_rate=float(both[valid].mean()),
                range_only=float(only_r[valid].mean()),
                range_gt=float((br["win_range"] > rr)[valid].mean()),
                dist_gt=float((br["distance"] > dd)[valid].mean()))


def fvg_in_window(df: pd.DataFrame, br: pd.DataFrame, n: int = 4) -> float:
    """Share of breaks whose N-candle window contains a same-direction FVG.

    FdRKBTz0Fps rejects a break *because* there is no fair value gap, and
    _94CPMjWi9E calls the gap the easiest way to spot displacement. This is the
    base rate that test carries on XAUUSD.
    """
    if br.empty:
        return float("nan")
    f = fair_value_gaps(df)
    pos = {t: i for i, t in enumerate(df.index)}
    hits = 0
    for t, row in br.iterrows():
        i = pos[t]
        w = f.iloc[i:i + n]
        hits += bool((w["bullish_fvg"] if row["side"] == "buy" else w["bearish_fvg"]).any())
    return hits / len(br)


# ── 4. retracement depth ("shallow") ──────────────────────────────────────────
def retracement_depths(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    """Depth of each swing-to-swing pullback as a fraction of the impulse leg.

    This is the OTHER 'shallow' — 4Gm8p6O7Ebs's "very shallow moves against the
    trend", which is a property of a leg, not of a candle wick. Keeping it
    separate is the point: nothing in the corpus says the two share a threshold.
    """
    sp = swing_points(df, left, right)
    pts = []
    for t, r in sp.iterrows():
        if r["swing_high"]:
            pts.append((t, float(r["high"]), "H"))
        if r["swing_low"]:
            pts.append((t, float(r["low"]), "L"))
    pts.sort(key=lambda x: x[0])
    # collapse consecutive same-kind points to the more extreme one
    clean: list[tuple] = []
    for p in pts:
        if clean and clean[-1][2] == p[2]:
            better = p[1] > clean[-1][1] if p[2] == "H" else p[1] < clean[-1][1]
            if better:
                clean[-1] = p
            continue
        clean.append(p)
    depths = []
    for a, b, c in zip(clean, clean[1:], clean[2:]):
        leg = abs(b[1] - a[1])
        pull = abs(c[1] - b[1])
        if leg > 0:
            depths.append(pull / leg)
    return pd.Series(depths, dtype="float64")


# ── report ────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    tfs = ["4h", "1D"] if a.quick else TFS

    m1 = load_m1()
    print(f"# fit_thresholds — XAUUSD M1 {len(m1):,} bars  "
          f"{m1.index.min().date()} -> {m1.index.max().date()}\n")

    geos, ocs, htfs = {}, {}, {}
    for tf in tfs:
        htf = resample(m1, tf)
        htfs[tf] = htf
        geos[tf] = candle_geometry(htf, m1, tf)
        ocs[tf] = outcomes(htf, geos[tf])

    # ---- 1. distributions -------------------------------------------------
    print("## 1. Candle-geometry distributions\n")
    cols = ["wick_share_of_range", "wick_vs_body", "body_share_of_range",
            "close_position", "time_share_to_extreme"]
    for col in cols:
        print(f"### {col}")
        for tf in tfs:
            g = geos[tf][col].replace([np.inf, -np.inf], np.nan)
            print(f"  {tf:6} n={g.notna().sum():>7,}  {fmt(q(g))}")
        print()

    # ---- 2. the two corpus-anchored cuts, priced --------------------------
    print("## 2. Corpus-anchored cuts, priced as percentiles\n")
    print("| tf | cut | rule | percentile | share admitted as 'small wick' |")
    print("|---|---|---|--:|--:|")
    for tf in tfs:
        g = geos[tf]
        for col, cut, rule in [
            ("wick_vs_body", 1.0, "reversal candle = wick > body (ecTRHQrbYzI/TND1aTpnq5c)"),
            ("wick_share_of_range", 0.5, "equilibrium / upper half (3eVxTV_7L2U/Te9jUijPXZo)"),
            ("wick_share_of_range", 0.25, "convention: quarter-range"),
            ("time_share_to_extreme", 0.5, "'almost half the time' reject (SlWxhzhLo3A)"),
            ("time_share_to_extreme", 0.25, "'early into the candle' (Kf4c41_qO1s)"),
        ]:
            s = g[col].replace([np.inf, -np.inf], np.nan)
            print(f"| {tf} | {col} <= {cut} | {rule} | "
                  f"{pct_of(s, cut):.1f} | {(s <= cut).mean()*100:.1f}% |")
    print()

    # ---- 3. outcome fit ---------------------------------------------------
    print("## 3. Outcome fit — which cut separates the prediction?\n")
    print("barrier   = from the close, reaches +1 ATR(20) in the candle's direction")
    print("            before -1 ATR against it, within 3 candles. SCALE-FREE.")
    print("continued = next candle extends beyond this candle's extreme  [CONFOUNDED]")
    print("reverted  = next candle trades back to this candle's open     [CONFOUNDED]")
    print("`sep` is small-bucket minus large-bucket, in percentage points.")
    print("The corpus predicts barrier_sep > 0 and reverted_sep < 0.\n")
    grids = {
        "wick_share_of_range": np.round(np.arange(0.05, 0.71, 0.05), 2),
        "wick_vs_body": np.round(np.arange(0.2, 3.01, 0.2), 2),
        "time_share_to_extreme": np.round(np.arange(0.05, 0.81, 0.05), 2),
    }
    for col, grid in grids.items():
        print(f"### {col}")
        print("| tf | cut | n small/large | barrier small | barrier large | "
              "barrier sep | reverted sep | continued sep |")
        print("|---|--:|--:|--:|--:|--:|--:|--:|")
        for tf in tfs:
            sw = sweep(geos[tf], ocs[tf], col, grid)
            if sw.empty:
                continue
            marks = {}
            bi = sw["barrier_sep"].idxmax()
            if pd.notna(bi):
                marks[float(sw.loc[bi, "cut"])] = "best"
            for c in (0.25, 0.5, 1.0):
                r = sw[np.isclose(sw["cut"], c)]
                if not r.empty:
                    marks.setdefault(c, "anchor")
            for cut in sorted(marks):
                r = sw[np.isclose(sw["cut"], cut)]
                if r.empty:
                    continue
                r = r.iloc[0]
                print(f"| {tf} | {cut:.2f} ({marks[cut]}) | "
                      f"{int(r['n_small'])}/{int(r['n_large'])} | "
                      f"{r['barrier_small']*100:.1f}% | {r['barrier_large']*100:.1f}% | "
                      f"{r['barrier_sep']*100:+.1f}pp | {r['reverted_sep']*100:+.1f}pp | "
                      f"{r['continued_sep']*100:+.1f}pp |")
        print()

    # ---- 4. displacement procedure ---------------------------------------
    print("## 4. Displacement comparative procedure (RESUME #7)\n")
    print("| tf | N | breaks | fire rate (range AND distance) | range>ref | dist>ref | FVG in window |")
    print("|---|--:|--:|--:|--:|--:|--:|")
    for tf in tfs:
        for n in (2, 4, 6, 8):
            br = displacement_windows(htfs[tf], n=n)
            st = displacement_fire_rate(br)
            if not st:
                continue
            fv = fvg_in_window(htfs[tf], br, n=n)
            print(f"| {tf} | {n} | {st['n_breaks']:,} | {st['fire_rate']*100:.1f}% | "
                  f"{st['range_gt']*100:.1f}% | {st['dist_gt']*100:.1f}% | {fv*100:.1f}% |")
    print()

    # ---- 5. displacement magnitude distribution --------------------------
    print("## 5. Displacement window magnitudes (N=4), normalised by pre-break range\n")
    for tf in tfs:
        br = displacement_windows(htfs[tf], n=4)
        if br.empty:
            continue
        print(f"  {tf:6} range_ratio  {fmt(q(br['range_ratio']), 2)}")
        print(f"  {tf:6} dist_ratio   {fmt(q(br['dist_ratio']), 2)}")
    print()

    # ---- 6. retracement depth --------------------------------------------
    if not a.quick:
        print("## 6. Retracement depth — the leg-level 'shallow'\n")
        print("ALL legs includes full reversals (depth > 1), which is the wrong "
              "population: 4Gm8p6O7Ebs's 'shallow moves against the trend' presupposes "
              "the trend continued. CONTINUATION restricts to depth < 1.0, i.e. the "
              "pullback did not take out the leg's origin — the population the corpus "
              "is actually describing.\n")
        print("| tf | population | n legs | p10 | p25 | median | p75 | "
              "share <=0.382 | share <=0.5 | share in OTE 0.62-0.79 |")
        print("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
        for tf in tfs:
            alld = retracement_depths(htfs[tf])
            alld = alld[alld < 5]                  # drop reversal blow-outs
            for name, d in (("all", alld), ("continuation", alld[alld < 1.0])):
                if len(d) < 50:
                    continue
                qq = q(d)
                ote = ((d >= 0.62) & (d <= 0.79)).mean()
                print(f"| {tf} | {name} | {len(d):,} | {qq[10]:.2f} | {qq[25]:.2f} | "
                      f"{qq[50]:.2f} | {qq[75]:.2f} | {(d <= 0.382).mean()*100:.1f}% | "
                      f"{(d <= 0.5).mean()*100:.1f}% | {ote*100:.1f}% |")
        print()

    print("## 7. Label linkage\n")
    print("Curated calls in meta/qualifier_calls.json that can be tied to a dated bar "
          "on this dataset: 0 of 56. No transcript names an instrument, a date or a "
          "price. Everything above is therefore a DISTRIBUTION plus a percentile for "
          "each corpus-anchored cut, and an outcome fit for the prediction each label "
          "carries — not a supervised fit to the labels themselves.")


if __name__ == "__main__":
    main()
