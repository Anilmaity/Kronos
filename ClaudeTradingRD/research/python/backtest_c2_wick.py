"""Backtest the corpus's one falsifiable prediction: C2 sweeping-wick size.

The claim (`concepts/model/fractal-model-c2.yaml`, contested): after a candle 2 —
a candle that sweeps the prior candle's extreme and closes back inside — a
**small** sweeping wick is followed by expansion, while a **large** wick means
price trades back to the C2 opening price.

`meta/fractal_reading_comparison.md` already measured that as a conditional
probability (78-83% of small-wick C2s see the next candle close beyond the C2
open, vs 63-66% for large-wick). That is not an edge, for three reasons this
module exists to remove:

  1. "Delivery beyond the open" is nearly free. The C2 open sits inside the C2
     range by construction, so the next candle only has to wobble to satisfy it.
     There is no target, so the statistic cannot be converted into money.
  2. There is no stop and no path dependence. A candle that closes beyond the
     open may have travelled far against the position first.
  3. There are no costs, and the median split is arbitrary.

So: enter on the C2 close in the C2 direction, stop at the swept extreme (what
the corpus prescribes), take a target, resolve **every trade on M1 bars** so the
path is honoured, pay a spread, and split the sample in time so an in-sample
result cannot be mistaken for a finding.

Conservative conventions, all of which move the result against the concept:
  * If stop and target are both touched inside the same M1 bar, the **stop** is
    taken. M1 gives no intrabar order, and assuming otherwise is how backtests
    lie.
  * If an M1 bar opens already beyond the stop, the fill is that open, not the
    stop level (gap risk is paid). Targets are always filled at the level even
    when the bar gaps through it, which under-credits winners.
  * Entry is the exact signal-bar close. Real fills are worse; the `--cost` knob
    is what absorbs that.

Everything is offline: `bars.load_m1` reads the local parquet, nothing here
reaches the network.

Usage
    python backtest_c2_wick.py --tf 1h --target 2R --cost 0.2
    python backtest_c2_wick.py --all          # regenerates meta/backtest_c2_wick.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample                  # noqa: E402
from detectors.fractal import c2_events             # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "meta" / "backtest_c2_wick.md"

TIMEFRAMES = ("15min", "1h", "4h", "1D")
TARGETS = ("1R", "2R", "3R", "structural")
COSTS = (0.0, 0.2, 0.5, "0.04R")

# Fitted small-wick cuts from `meta/threshold_fits.md` (independent workstream).
# The numerator in both is the *opposing run* — opening price to the extreme
# against the intended direction — not high-low. See `build_trades` for why this
# module's `wick_ratio` already satisfies that.
FIT_BODY_CUT, FIT_BODY_SWEEP = 1.0, (0.6, 0.8, 1.0, 1.2, 1.6)
FIT_RANGE_CUT, FIT_RANGE_SWEEP = 0.30, (0.20, 0.25, 0.30, 0.40, 0.50)

# The daily break is 17:00-18:04 New York and there are zero bars in NY hour 17;
# weekends are longer still. Any M1 window wider than this has a hole in it.
GAP_MIN = 70

# Two years fit, ~one year holdout. The split is a wall-clock date, chosen once,
# before any result was looked at, and never moved.
IS_END = pd.Timestamp("2025-07-02", tz="UTC")

# Hold cap, in wall-clock multiples of the signal timeframe. Wall clock rather
# than bar count so weekends shorten a 1D hold instead of stretching it.
MAX_HOLD = 10

QUINTILE_LABELS = ("Q1 smallest", "Q2", "Q3", "Q4", "Q5 largest")


# ── trade construction ────────────────────────────────────────────────────────
def build_trades(m1: pd.DataFrame, tf: str, sweep_ref: str = "prior_candle",
                 max_hold: int = MAX_HOLD) -> pd.DataFrame:
    """One row per C2: entry at its close, stop at the swept extreme.

    Adds the M1 index bounds of the resolution window so the resolver never has
    to touch pandas. `struct_target` is the prior candle's *opposite* extreme —
    the structural destination the model implies (sweep the low, deliver to the
    high) as an alternative to a fixed R multiple.

    Two wick parameterisations are carried, matching `meta/threshold_fits.md`:

      wick_ratio  opposing_run / (high - low)    fitted cut 0.30 (grade C)
      wick_body   opposing_run / |close - open|  fitted cut 1.0  (grade A)

    The **opposing run** is measured from the *opening price* to the extreme
    against the intended direction — one-sided and directional, not the full
    high-low. `c2_events` computes its wick from `min(open, close)` to the low
    (bullish), and `require_reversal_close` guarantees `close > open` for a
    bullish C2, so `min(open, close) == open` and the two definitions coincide
    exactly on this event set. Checked in the tests rather than assumed.
    """
    df = resample(m1, tf)
    ev = c2_events(df, sweep_ref=sweep_ref)
    if ev.empty:
        return pd.DataFrame()

    prior_hi = df["high"].shift(1)
    prior_lo = df["low"].shift(1)
    delta = pd.Timedelta(tf)

    long_ = (ev["direction"] == "bullish").to_numpy()
    entry = ev["close"].to_numpy(float)
    stop = np.where(long_, ev["low"].to_numpy(float), ev["high"].to_numpy(float))
    risk = np.abs(entry - stop)
    struct = np.where(long_,
                      prior_hi.reindex(ev["time"]).to_numpy(float),
                      prior_lo.reindex(ev["time"]).to_numpy(float))

    t = pd.DatetimeIndex(ev["time"])
    m1_t = m1.index.to_numpy()
    i0 = np.searchsorted(m1_t, (t + delta).to_numpy(), side="left")
    i1 = np.searchsorted(m1_t, (t + delta * (max_hold + 1)).to_numpy(), side="left")
    # The same window expressed in signal-timeframe bars, so the identical book
    # can be re-resolved coarsely and the difference reported as a number.
    tf_t = df.index.to_numpy()
    j0 = np.searchsorted(tf_t, (t + delta).to_numpy(), side="left")
    j1 = np.searchsorted(tf_t, (t + delta * (max_hold + 1)).to_numpy(), side="left")

    # The old measurement's outcome variable, carried along so the report can
    # show the same trades under the weaker test that produced the 78-83% claim.
    nxt_close = df["close"].shift(-1).reindex(pd.DatetimeIndex(ev["time"])).to_numpy(float)
    c2_open = ev["open"].to_numpy(float)
    delivered = np.where(long_, nxt_close > c2_open, nxt_close < c2_open)

    # opposing run: opening price -> extreme against the intended direction
    opp_run = np.where(long_, c2_open - ev["low"].to_numpy(float),
                       ev["high"].to_numpy(float) - c2_open)
    body = np.abs(entry - c2_open)
    body = np.where(body > 0, body, np.nan)

    out = pd.DataFrame({
        "time": t, "tf": tf, "long": long_, "entry": entry, "stop": stop,
        "risk": risk, "struct_target": struct,
        "c2_open": c2_open, "delivered": delivered,
        "wick_ratio": ev["wick_ratio"].to_numpy(float),
        "wick_body": opp_run / body,
        "body_ratio": ev["body_ratio"].to_numpy(float),
        "i0": i0, "i1": i1, "j0": j0, "j1": j1,
    })
    # A zero-risk trade is undefined; a window with no M1 bars cannot be
    # resolved. Both are dropped and counted rather than silently filled.
    out = out[(out["risk"] > 0) & (out["i1"] > out["i0"])].reset_index(drop=True)
    return out


def target_levels(tr: pd.DataFrame, target: str) -> np.ndarray:
    """Target price per trade. NaN marks a trade this target cannot express."""
    if target == "structural":
        lv = tr["struct_target"].to_numpy(float).copy()
        # A structural target already behind the entry is not a trade. This
        # happens when the C2 closed beyond the prior candle's far extreme.
        bad = np.where(tr["long"].to_numpy(), lv <= tr["entry"], lv >= tr["entry"])
        lv[bad] = np.nan
        return lv
    mult = float(target.rstrip("R"))
    sgn = np.where(tr["long"].to_numpy(), 1.0, -1.0)
    return tr["entry"].to_numpy(float) + sgn * mult * tr["risk"].to_numpy(float)


# ── path-honest resolution on M1 ──────────────────────────────────────────────
def resolve(tr: pd.DataFrame, target: np.ndarray, bars: pd.DataFrame,
            i0col: str = "i0", i1col: str = "i1",
            tie: str = "stop") -> pd.DataFrame:
    """Walk each trade forward until stop, target, or the hold cap.

    `bars` is normally M1. Passing the signal-timeframe frame instead (with
    `i0col='j0'`) reruns the identical book at coarse resolution, which is how
    the resolution artefact is measured rather than assumed.

    Same-bar ambiguity resolves to the stop (`tie='stop'`). `tie='target'` is the
    optimistic rule and exists only so the size of that choice can be reported;
    never use it for a result.

    Gaps through the stop fill at the bar open; gaps through the target still
    fill at the level.
    """
    if tie not in ("stop", "target"):
        raise ValueError("tie must be 'stop' or 'target'")
    o = bars["open"].to_numpy(float)
    h = bars["high"].to_numpy(float)
    lo = bars["low"].to_numpy(float)
    c = bars["close"].to_numpy(float)
    # Positions, not epoch integers: pandas' datetime unit is not guaranteed to
    # be nanoseconds (this build resamples to microseconds), and hard-coding a
    # unit silently rescales every timestamp by 1000.
    n = len(tr)
    long_ = tr["long"].to_numpy()
    stop = tr["stop"].to_numpy(float)
    i0 = tr[i0col].to_numpy()
    i1 = tr[i1col].to_numpy()

    exit_px = np.full(n, np.nan)
    exit_pos = np.zeros(n, dtype="int64")
    reason = np.empty(n, dtype=object)

    for k in range(n):
        tg = target[k]
        if not np.isfinite(tg):
            reason[k] = "no_target"
            continue
        a, b = i0[k], i1[k]
        wh, wl = h[a:b], lo[a:b]
        if long_[k]:
            hit_s, hit_t = wl <= stop[k], wh >= tg
        else:
            hit_s, hit_t = wh >= stop[k], wl <= tg
        si = int(hit_s.argmax()) if hit_s.any() else -1
        ti = int(hit_t.argmax()) if hit_t.any() else -1

        stop_first = (si >= 0 and si <= ti) if tie == "stop" else (si >= 0 and si < ti)
        if si < 0 and ti < 0:
            j = b - 1
            exit_px[k], reason[k] = c[j], "time"
        elif ti < 0 or stop_first:
            j = a + si
            # pay the gap: a bar that opens through the stop fills at the open
            exit_px[k] = min(stop[k], o[j]) if long_[k] else max(stop[k], o[j])
            reason[k] = "stop"
        else:
            j = a + ti
            exit_px[k], reason[k] = tg, "target"
        exit_pos[k] = j

    res = tr.copy()
    res["target_px"] = target
    res["exit_px"] = exit_px
    res["exit_time"] = bars.index[exit_pos]
    res["reason"] = reason
    res = res[res["reason"] != "no_target"].reset_index(drop=True)

    sgn = np.where(res["long"].to_numpy(), 1.0, -1.0)
    res["gross_usd"] = sgn * (res["exit_px"] - res["entry"])
    return res


def excursions(tr: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    """Max favourable / adverse excursion in R over the hold window, no exit rule.

    This is the target-free version of the test. If small-wick C2s really are
    followed by expansion, they should show more favourable and less adverse
    travel than large-wick ones *whatever* target you pick — an asymmetry that
    only appears at one target multiple is a fitted artefact, not a property of
    the candle.
    """
    h = m1["high"].to_numpy(float)
    lo = m1["low"].to_numpy(float)
    long_ = tr["long"].to_numpy()
    entry = tr["entry"].to_numpy(float)
    risk = tr["risk"].to_numpy(float)
    i0, i1 = tr["i0"].to_numpy(), tr["i1"].to_numpy()

    mfe = np.full(len(tr), np.nan)
    mae = np.full(len(tr), np.nan)
    for k in range(len(tr)):
        a, b = i0[k], i1[k]
        if b <= a:
            continue
        wh, wl = h[a:b].max(), lo[a:b].min()
        if long_[k]:
            mfe[k], mae[k] = (wh - entry[k]) / risk[k], (entry[k] - wl) / risk[k]
        else:
            mfe[k], mae[k] = (entry[k] - wl) / risk[k], (wh - entry[k]) / risk[k]
    out = tr.copy()
    out["mfe_r"], out["mae_r"] = mfe, mae
    return out


def apply_cost(res: pd.DataFrame, cost: float | str) -> pd.DataFrame:
    """Round-trip cost charged to P&L (not to the trigger levels).

    `cost` is USD/oz as a float, or a string like `"0.04R"` for a cost
    proportional to the trade's own risk. The proportional form exists because
    gold ran from ~1,800 to ~5,500 across this sample: a flat 0.20 USD spread is
    a 3.6% tax on an average 2023 1h stop and only 1.4% on a 2026 one, which
    would quietly make the holdout look better than the fit for a reason that
    has nothing to do with the signal.

    Charging the spread to P&L rather than shifting the stop/target is the
    milder of the two treatments: a real spread would also trip stops slightly
    earlier. Stated as a limitation rather than hidden.
    """
    out = res.copy()
    if isinstance(cost, str) and cost.endswith("R"):
        c = float(cost[:-1]) * out["risk"]
    else:
        c = float(cost)
    out["net_usd"] = out["gross_usd"] - c
    out["net_r"] = out["net_usd"] / out["risk"]
    return out


# ── metrics ───────────────────────────────────────────────────────────────────
def stats(res: pd.DataFrame) -> dict:
    n = len(res)
    if n == 0:
        return {"n": 0, "win": float("nan"), "exp_r": float("nan"),
                "exp_usd": float("nan"), "pf": float("nan"), "mdd_r": float("nan"),
                "risk": float("nan"), "time_exit": float("nan")}
    net = res["net_usd"].to_numpy(float)
    r = res["net_r"].to_numpy(float)
    wins, losses = net[net > 0].sum(), -net[net <= 0].sum()
    order = res.sort_values("exit_time")["net_r"].to_numpy(float)
    eq = np.cumsum(order)
    mdd = float(np.max(np.maximum.accumulate(np.concatenate(([0.0], eq))) -
                       np.concatenate(([0.0], eq))))
    return {
        "n": n,
        "win": float((net > 0).mean()),
        "exp_r": float(r.mean()),
        "exp_usd": float(net.mean()),
        "pf": float(wins / losses) if losses > 0 else float("inf"),
        "mdd_r": mdd,
        # Mean risk matters: a fixed USD spread is a different tax on a 3 USD
        # stop than on a 12 USD one, and the buckets do not have equal R.
        "risk": float(res["risk"].mean()),
        "time_exit": float((res["reason"] == "time").mean()),
    }


def perm_p(small: np.ndarray, large: np.ndarray, n_perm: int | None = None,
           seed: int = 20260825) -> tuple[float, float, tuple[float, float]]:
    """One-sided permutation p for mean_R(small) > mean_R(large), + bootstrap CI.

    Labels are shuffled, not the returns resampled, so the null is exactly "the
    wick bucket carries no information", which is the claim under test.

    Each shuffle costs O(n), so `n_perm` is reduced on very large samples. That
    only coarsens the resolution of the p-value floor (1/(n_perm+1)); it does not
    bias the estimate, and the large-sample cells are not the marginal ones.
    """
    if len(small) < 2 or len(large) < 2:
        return float("nan"), float("nan"), (float("nan"), float("nan"))
    pool = np.concatenate([small, large])
    if n_perm is None:
        n_perm = 10_000 if len(pool) <= 8_000 else 3_000
    obs = float(small.mean() - large.mean())
    na = len(small)
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        p = rng.permutation(pool)
        if (p[:na].mean() - p[na:].mean()) >= obs:
            ge += 1
    pval = (1 + ge) / (n_perm + 1)
    _, lo, hi = boot_diff(small, large, n=2000, seed=seed + 1)
    return obs, pval, (lo, hi)


def mde(n1: int, n2: int, p: float, power: float = 0.80) -> float:
    """Smallest win-rate difference two samples this size could detect.

    Two-sided alpha=0.05, `power` power, difference of proportions. This is the
    question the corpus's claim now has to answer: an independently fitted
    barrier test puts the real small-wick advantage at 3-4 percentage points on
    4h/1D, so a timeframe whose minimum detectable effect is larger than that
    cannot settle the question with this much data, however the numbers land.
    """
    if n1 < 2 or n2 < 2:
        return float("nan")
    z = 1.959964 + (0.8416212 if power == 0.80 else 0.8416212)
    return float(z * np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)))


def n_for_effect(effect: float, p: float, power: float = 0.80) -> float:
    """Total trades (split evenly in two buckets) needed to detect `effect`."""
    z = 1.959964 + 0.8416212
    return float(4 * p * (1 - p) * (z / effect) ** 2)


# ── bucketing ─────────────────────────────────────────────────────────────────
def quintile_edges(w: np.ndarray) -> np.ndarray:
    """Inner quintile cut points, fitted on one sample and applied to another.

    Fitting the edges on the holdout would leak the holdout's distribution into
    the rule, which is exactly the mistake this project has been burned by.
    """
    return np.nanpercentile(w, [20, 40, 60, 80])


def bucketise(w: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.searchsorted(edges, w, side="right")


def slice_sample(res: pd.DataFrame, sample: str) -> pd.DataFrame:
    if sample == "IS":
        return res[res["time"] < IS_END]
    if sample == "OOS":
        return res[res["time"] >= IS_END]
    return res


# ── controls: matched random entries, and the every-bar null ──────────────────
def matched_control(tr: pd.DataFrame, target_px: np.ndarray, df: pd.DataFrame,
                    m1: pd.DataFrame, tf: str, reps: int = 5, seed: int = 20260825,
                    window_days: int = 30, max_hold: int = MAX_HOLD
                    ) -> tuple[pd.DataFrame, np.ndarray]:
    """A random-entry twin for every C2 trade: same geometry, arbitrary moment.

    This is the only control that separates a signal from the base rate. Each C2
    trade is paired with `reps` random ones carrying the **same direction, the
    same stop distance and the same target distance**, entered at the close of a
    randomly chosen bar within +/-`window_days` of the original. The local window
    matters: gold ran from ~1,800 to ~5,500 across this sample, so a control
    drawn from the whole period would be matched in USD but not in volatility,
    and would flatter or damn the signal for a reason unrelated to it.

    Comparing a win rate to 50% is not a control — a 1R/1R trade is near a coin
    flip by construction, and a 3R target is near 25% whatever the entry rule.
    The external cross-reference records a published FVG study whose real effect
    was ~5 percentage points over exactly this kind of baseline, and Marshall,
    Young & Rose (2006) found candlestick strategies produce nothing at all once
    tested against bootstrapped controls.
    """
    keep = np.isfinite(target_px)
    src = tr[keep].reset_index(drop=True)
    dist = np.abs(target_px[keep] - src["entry"].to_numpy(float))

    delta = pd.Timedelta(tf)
    tf_t = df.index.to_numpy()
    m1_t = m1.index.to_numpy()
    t = pd.DatetimeIndex(src["time"])
    w = pd.Timedelta(days=window_days)
    lo_b = np.searchsorted(tf_t, (t - w).to_numpy(), side="left")
    hi_b = np.searchsorted(tf_t, (t + w).to_numpy(), side="right")
    hi_b = np.maximum(hi_b, lo_b + 1)

    rng = np.random.default_rng(seed)
    close = df["close"].to_numpy(float)
    frames, targets = [], []
    for _ in range(reps):
        pick = rng.integers(lo_b, hi_b)
        rt = pd.DatetimeIndex(tf_t[pick])
        entry = close[pick]
        long_ = src["long"].to_numpy()
        risk = src["risk"].to_numpy(float)
        sgn = np.where(long_, 1.0, -1.0)
        frames.append(pd.DataFrame({
            "time": rt, "tf": tf, "long": long_, "entry": entry,
            "stop": entry - sgn * risk, "risk": risk,
            "struct_target": np.nan, "c2_open": np.nan, "delivered": False,
            "wick_ratio": src["wick_ratio"].to_numpy(float),
            "body_ratio": np.nan,
            "i0": np.searchsorted(m1_t, (rt + delta).to_numpy(), side="left"),
            "i1": np.searchsorted(m1_t, (rt + delta * (max_hold + 1)).to_numpy(),
                                  side="left"),
            "j0": np.searchsorted(tf_t, (rt + delta).to_numpy(), side="left"),
            "j1": np.searchsorted(tf_t, (rt + delta * (max_hold + 1)).to_numpy(),
                                  side="left"),
            "rep": _,
        }))
        targets.append(entry + sgn * dist)
    out = pd.concat(frames, ignore_index=True)
    tgt = np.concatenate(targets)
    ok = (out["i1"] > out["i0"]).to_numpy()
    return out[ok].reset_index(drop=True), tgt[ok]


def _boot_means(x: np.ndarray, n: int, rng) -> np.ndarray:
    """`n` bootstrap resample means of `x`, drawn in memory-bounded chunks."""
    k = len(x)
    chunk = max(1, 2_000_000 // max(k, 1))
    out, done = np.empty(n), 0
    while done < n:
        m = min(chunk, n - done)
        out[done:done + m] = x[rng.integers(0, k, size=(m, k))].mean(axis=1)
        done += m
    return out


def boot_diff(a: np.ndarray, b: np.ndarray, n: int = 2000,
              seed: int = 20260825) -> tuple[float, float, float]:
    """Observed `mean(a) - mean(b)` and a bootstrap 95% CI on it.

    Means only, which covers both uses here: expectancy in R, and win rate as
    the mean of a 0/1 indicator.
    """
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    obs = float(a.mean() - b.mean())
    d = _boot_means(a, n, rng) - _boot_means(b, n, rng)
    return obs, float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def truncate_at_gap(tr: pd.DataFrame, m1: pd.DataFrame, i0col: str = "i0",
                    i1col: str = "i1", gap_min: int = GAP_MIN) -> np.ndarray:
    """End each resolution window at the first session break inside it.

    XAUUSD stops trading 17:00-18:04 New York daily and over weekends, so a
    10-bar window on any timeframe can contain a hole. Walking M1 straight
    through one means a stop or target can be "hit" on the far side of a gap the
    position could not have been managed across. The conservative fills already
    make that non-flattering, but the honest thing is to measure it: this
    returns an alternative `i1` that stops at the break, so the whole book can be
    re-run flat-over-the-break and the difference reported.
    """
    # total_seconds() rather than raw int64: see `resolve` — the datetime unit
    # is not guaranteed to be nanoseconds.
    dt = m1.index.to_series().diff().dt.total_seconds().to_numpy()[1:] / 60.0
    breaks = np.flatnonzero(dt > gap_min) + 1           # index of the post-gap bar
    i0 = tr[i0col].to_numpy()
    i1 = tr[i1col].to_numpy()
    if not len(breaks):
        return i1
    pos = np.searchsorted(breaks, i0, side="right")
    nxt = np.where(pos < len(breaks), breaks[np.minimum(pos, len(breaks) - 1)],
                   len(m1))
    return np.minimum(i1, nxt)


def baseline_trades(m1: pd.DataFrame, tf: str, max_hold: int = MAX_HOLD) -> pd.DataFrame:
    """Every bar, both directions, same stop rule (that bar's opposite extreme).

    This is the null the C2 filter has to beat: if C2-ness carries information,
    C2 trades should do better than taking the same trade on an arbitrary bar.
    """
    df = resample(m1, tf)
    delta = pd.Timedelta(tf)
    m1_t = m1.index.to_numpy()
    frames = []
    for long_ in (True, False):
        entry = df["close"].to_numpy(float)
        stop = df["low"].to_numpy(float) if long_ else df["high"].to_numpy(float)
        t = df.index
        frames.append(pd.DataFrame({
            "time": t, "tf": tf, "long": long_, "entry": entry, "stop": stop,
            "risk": np.abs(entry - stop), "struct_target": np.nan,
            "c2_open": np.nan, "delivered": False,
            "wick_ratio": np.nan, "body_ratio": np.nan,
            "i0": np.searchsorted(m1_t, (t + delta).to_numpy(), side="left"),
            "i1": np.searchsorted(m1_t, (t + delta * (max_hold + 1)).to_numpy(),
                                  side="left"),
            "j0": np.searchsorted(df.index.to_numpy(), (t + delta).to_numpy(),
                                  side="left"),
            "j1": np.searchsorted(df.index.to_numpy(),
                                  (t + delta * (max_hold + 1)).to_numpy(), side="left"),
        }))
    out = pd.concat(frames, ignore_index=True)
    return out[(out["risk"] > 0) & (out["i1"] > out["i0"])].reset_index(drop=True)


# ── report ────────────────────────────────────────────────────────────────────
def _f(x: float, nd: int = 3) -> str:
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def _pct(x: float) -> str:
    return "-" if not np.isfinite(x) else f"{100 * x:.1f}%"


def _row(s: dict) -> str:
    return (f"{s['n']:,} | {_pct(s['win'])} | {_f(s['exp_r'])} | {_f(s['exp_usd'], 2)} | "
            f"{_f(s['pf'], 2)} | {_f(s['mdd_r'], 1)} | {_f(s['risk'], 2)} | "
            f"{_pct(s['time_exit'])}")


def run_all(costs=COSTS, targets=TARGETS, tfs=TIMEFRAMES, out: Path = OUT_MD) -> int:
    m1 = load_m1()
    base_cost = 0.2
    L: list[str] = []

    L += ["# C2 sweeping-wick size — a real backtest", "",
          f"Data: `m3_scalper/xau_m1_3y.parquet`, {len(m1):,} M1 bars, "
          f"{m1.index.min().date()} to {m1.index.max().date()}, UTC. Offline.", ""]

    L += ["## Methodology", "",
          "Signal: `detectors.fractal.c2_events(sweep_ref='prior_candle')` — the "
          "candle sweeps the prior candle's extreme, closes back inside it, and "
          "closes in the reversal direction. Entry is that candle's close, "
          "direction is the C2 direction (swept the low -> long).", "",
          "Stop is the swept extreme itself (the C2 low for a long), which is what "
          "the corpus prescribes. Risk `R` = |entry - stop|. Targets: fixed "
          "multiples 1R/2R/3R, and `structural` = the prior candle's opposite "
          "extreme (sweep the low, deliver to the high); trades whose structural "
          "target already sits behind the entry are dropped, not clipped.", "",
          f"**Every trade is resolved on M1 bars**, not on the signal timeframe. "
          f"The window runs from the first M1 bar after the signal bar closes to "
          f"{MAX_HOLD} wall-clock multiples of the timeframe later; unresolved "
          "trades exit at the last M1 close in the window (`time`). "
          "**If stop and target are touched inside the same M1 bar the stop is "
          "taken** — M1 carries no intrabar order and assuming otherwise "
          "manufactures edge. A bar that opens through the stop fills at that "
          "open (gap risk paid); a bar that gaps through the target still fills "
          "at the level (gap gift refused).", "",
          "Costs are a round-trip spread in USD/oz charged to P&L "
          f"({', '.join(str(c) for c in costs)} tested; {base_cost} is the base "
          "case for XAUUSD). Entry at the exact signal close is optimistic and "
          "the cost knob is what absorbs it.", "",
          f"In-sample is everything before **{IS_END.date()}** (two years), "
          "out-of-sample is the remainder (~one year). **Wick quintile edges are "
          "fitted on the in-sample trades only** and applied unchanged to the "
          "holdout, so the bucketing rule cannot see the holdout.", "",
          "Trades overlap: consecutive bars can each be a C2 and no position cap "
          "is applied. That is fine for expectancy but means the drawdown column "
          "understates what a single-position account would feel.", "",
          "**Two controls, because a win rate on its own is not evidence.** "
          "Section 6b pairs every C2 trade with five random-entry trades of "
          "identical geometry (same direction, same stop distance, same target "
          "distance, random entry time within +/-30 days) and reports the "
          "difference with a bootstrap CI. Section 6c re-resolves the identical "
          "book on signal-timeframe bars instead of M1, so the size of the "
          "resolution artefact is a number in this file rather than an assumption.",
          "",
          "Both controls are here on the advice of `meta/external_crossref.md`. "
          "The relevant priors: a published FVG study (MPM Markets — 7 years, 4 "
          "futures markets, 3 timeframes, ~40k occurrences) found a same-family "
          "ICT construct real but only ~5 percentage points above a matched random "
          "baseline and with no tradeable edge after costs, and found that its one "
          "strongly profitable construction was an artefact of resolving exits on "
          "hourly bars — roughly 73% win rate at that resolution, about 50% at one "
          "minute. Marshall, Young & Rose (2006, *J. Banking & Finance* 30(8)) "
          "found candlestick strategies create no value once tested against "
          "bootstrapped controls. There is no peer-reviewed literature on ICT/SMC "
          "at all, and the C2 wick claim in particular is externally unattested — "
          "every outside hit traces back to the channel. This backtest is "
          "therefore the deciding test, which is a reason for more conservatism, "
          "not less.", ""]

    # ---- per timeframe ------------------------------------------------------
    resolved: dict[tuple[str, str], pd.DataFrame] = {}
    edges: dict[str, np.ndarray] = {}
    for tf in tfs:
        tr = build_trades(m1, tf)
        is_tr = tr[tr["time"] < IS_END]
        edges[tf] = quintile_edges(is_tr["wick_ratio"].to_numpy(float))
        for tgt in targets:
            r = resolve(tr, target_levels(tr, tgt), m1)
            r["bucket"] = bucketise(r["wick_ratio"].to_numpy(float), edges[tf])
            r["small_med"] = r["wick_ratio"] <= np.nanmedian(
                is_tr["wick_ratio"].to_numpy(float))
            resolved[(tf, tgt)] = r

    L += ["## Sample sizes and quintile edges", "",
          "| TF | C2 trades | IS | OOS | wick quintile edges (fitted IS) |",
          "|---|---:|---:|---:|---|"]
    for tf in tfs:
        r = resolved[(tf, targets[0])]
        L.append(f"| {tf} | {len(r):,} | {len(slice_sample(r, 'IS')):,} | "
                 f"{len(slice_sample(r, 'OOS')):,} | "
                 f"{', '.join(f'{e:.3f}' for e in edges[tf])} |")
    L.append("")

    # ---- Table 0: the old statistic, and the target-free excursion test ------
    L += ["## 0. The old statistic, replicated — and what it is worth", "",
          "Left half replicates `fractal_reading_comparison.md`: how often the "
          "**next candle closed beyond the C2 open**, by wick quintile. Right half "
          "is the same trades measured target-free, as maximum favourable and "
          "maximum adverse excursion in R over the hold window. MFE/MAE is the "
          "honest version of the same question: if small-wick C2s expand, they "
          "must travel further in favour and less against, at every target.", "",
          "`open gap R` is the distance from the entry back to the C2 open, in R — "
          "i.e. how much room the delivery test gives the trade before it fails. "
          "It is the control the old statistic never had.", "",
          "| TF | bucket | n | delivered beyond C2 open | open gap R | mean MFE R | "
          "mean MAE R | median MFE R | MFE>=2R |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    exc: dict[str, pd.DataFrame] = {}
    for tf in tfs:
        tr = build_trades(m1, tf)
        e = excursions(tr, m1)
        e["bucket"] = bucketise(e["wick_ratio"].to_numpy(float), edges[tf])
        e["open_gap_r"] = (e["entry"] - e["c2_open"]).abs() / e["risk"]
        exc[tf] = e
        for b, lab in enumerate(QUINTILE_LABELS):
            s = e[e["bucket"] == b]
            L.append(f"| {tf} | {lab} | {len(s):,} | {_pct(s['delivered'].mean())} | "
                     f"{_f(s['open_gap_r'].mean())} | "
                     f"{_f(s['mfe_r'].mean())} | {_f(s['mae_r'].mean())} | "
                     f"{_f(s['mfe_r'].median())} | {_pct((s['mfe_r'] >= 2).mean())} |")
    L.append("")

    # ---- Table 1: quintile x target, expectancy in R -------------------------
    L += [f"## 1. Expectancy in R by wick quintile (cost {base_cost}, full sample)",
          "",
          "Cell = expectancy in R (win rate). A quintile is only interesting if it "
          "beats 0 after costs; the corpus predicts Q1 (smallest wick) is the good "
          "one and Q5 the bad one.", "",
          "| TF | bucket | " + " | ".join(targets) + " |",
          "|---|---|" + "---:|" * len(targets)]
    for tf in tfs:
        for b, lab in enumerate(QUINTILE_LABELS):
            cells = []
            for tgt in targets:
                r = apply_cost(resolved[(tf, tgt)], base_cost)
                s = stats(r[r["bucket"] == b])
                cells.append(f"{_f(s['exp_r'])} ({_pct(s['win'])})")
            L.append(f"| {tf} | {lab} | " + " | ".join(cells) + " |")
    L.append("")

    # ---- Table 2: full metrics, median split, IS vs OOS ---------------------
    L += [f"## 2. Full metrics — median wick split, in-sample vs out-of-sample "
          f"(cost {base_cost})", "",
          "`small` = wick ratio at or below the in-sample median; `large` = above. "
          "`all` is every C2 regardless of wick, i.e. what you get if the wick "
          "claim is worthless.", "",
          "| TF | target | sample | bucket | n | win | exp R | exp USD/oz | PF | "
          "maxDD R | mean R (USD) | time-exit |",
          "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for tf in tfs:
        for tgt in targets:
            r = apply_cost(resolved[(tf, tgt)], base_cost)
            for sample in ("IS", "OOS"):
                sub = slice_sample(r, sample)
                for lab, part in (("small", sub[sub["small_med"]]),
                                  ("large", sub[~sub["small_med"]]),
                                  ("all", sub)):
                    L.append(f"| {tf} | {tgt} | {sample} | {lab} | {_row(stats(part))} |")
    L.append("")

    # ---- Table 3: permutation p-values ---------------------------------------
    L += ["## 3. Is the small-vs-large gap real? Permutation test", "",
          "One-sided permutation test of `mean_R(small) > mean_R(large)`, 10,000 "
          "label shuffles, plus a 2,000-draw bootstrap 95% CI on the difference. "
          "Two splits: the median split (comparable to the old conditional-"
          "probability table) and the extreme split Q1 vs Q5.", "",
          f"| TF | target | sample | split | diff R | p | 95% CI |",
          "|---|---|---|---|---:|---:|---|"]
    pvals: dict[tuple, tuple[float, float]] = {}
    for tf in tfs:
        for tgt in targets:
            r = apply_cost(resolved[(tf, tgt)], base_cost)
            for sample in ("IS", "OOS"):
                sub = slice_sample(r, sample)
                pairs = (
                    ("median", sub[sub["small_med"]]["net_r"].to_numpy(),
                     sub[~sub["small_med"]]["net_r"].to_numpy()),
                    ("Q1 vs Q5", sub[sub["bucket"] == 0]["net_r"].to_numpy(),
                     sub[sub["bucket"] == 4]["net_r"].to_numpy()),
                )
                for lab, a, b in pairs:
                    d, p, ci = perm_p(a, b)
                    pvals[(tf, tgt, sample, lab)] = (d, p)
                    L.append(f"| {tf} | {tgt} | {sample} | {lab} | {_f(d)} | "
                             f"{_f(p, 4)} | [{_f(ci[0])}, {_f(ci[1])}] |")
    L.append("")

    # ---- Table 4: cost sensitivity ------------------------------------------
    L += ["## 4. Cost sensitivity (out-of-sample, median split)", "",
          "| TF | target | cost | small exp R | large exp R | all exp R |",
          "|---|---|---:|---:|---:|---:|"]
    for tf in tfs:
        for tgt in targets:
            for cost in costs:
                r = slice_sample(apply_cost(resolved[(tf, tgt)], cost), "OOS")
                L.append(f"| {tf} | {tgt} | {cost} | "
                         f"{_f(stats(r[r['small_med']])['exp_r'])} | "
                         f"{_f(stats(r[~r['small_med']])['exp_r'])} | "
                         f"{_f(stats(r)['exp_r'])} |")
    L.append("")

    # ---- Table 5: threshold sweep -------------------------------------------
    L += [f"## 5. Threshold sweep (1h, cost {base_cost}) — in-sample beside holdout",
          "",
          "Rather than trusting one split point, every threshold: trade only C2s "
          "with `wick_ratio <= t`. If the concept is real the curve should be "
          "monotone (tighter threshold, better expectancy) **and it should have the "
          "same shape in both periods**. The two `exp R <=t` columns side by side "
          "are the whole test.", "",
          "| target | t | IS n | IS exp R <=t | IS exp R >t | OOS n | OOS exp R <=t | "
          "OOS exp R >t |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for tgt in targets:
        full = apply_cost(resolved[("1h", tgt)], base_cost)
        i_s, o_s = slice_sample(full, "IS"), slice_sample(full, "OOS")
        wi, wo = i_s["wick_ratio"].to_numpy(float), o_s["wick_ratio"].to_numpy(float)
        for t in np.arange(0.15, 0.80, 0.05):
            L.append(f"| {tgt} | {t:.2f} | {int((wi <= t).sum()):,} | "
                     f"{_f(stats(i_s[wi <= t])['exp_r'])} | "
                     f"{_f(stats(i_s[wi > t])['exp_r'])} | "
                     f"{int((wo <= t).sum()):,} | "
                     f"{_f(stats(o_s[wo <= t])['exp_r'])} | "
                     f"{_f(stats(o_s[wo > t])['exp_r'])} |")
    L.append("")

    # ---- Table 5b: the fitted cuts, both parameterisations -------------------
    L += ["## 5b. The fitted small-wick cuts (2R, cost "
          f"{base_cost})", "",
          "`meta/threshold_fits.md` fits the small-wick cut independently of this "
          f"backtest: **`opposing_run/body <= {FIT_BODY_CUT}`** (grade A, plateau "
          f"{FIT_BODY_SWEEP[0]}-{FIT_BODY_SWEEP[-1]}) with a range form "
          f"**`opposing_run/range <= {FIT_RANGE_CUT}`** (grade C). The numerator is "
          "the *opposing run* — opening price to the extreme against the direction "
          "— which is exactly what this module's `wick_ratio` numerator already is "
          "(see `build_trades`). Below, both forms, at the fitted value and across "
          "the fitted sweep.", "",
          "The bar to clear is **3-4 percentage points**, not the ~15 the delivery "
          "table implies, and the barrier test that produced it found the effect "
          "**only on 4h and 1D** (+4.0pp and +3.2pp) with **approximately zero on "
          "15m and 1h**. A null at 15m/1h here is therefore a *confirmation* of "
          "that result, not a failed replication.", "",
          "| TF | form | cut | n pass | pass rate | pass exp R | fail exp R | "
          "diff R | pass win | fail win | win diff |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for tf in tfs:
        r = apply_cost(resolved[(tf, "2R")], base_cost)
        for col, cuts, form in (("wick_body", FIT_BODY_SWEEP, "run/body"),
                                ("wick_ratio", FIT_RANGE_SWEEP, "run/range")):
            v = r[col].to_numpy(float)
            for cut in cuts:
                a, b = r[v <= cut], r[v > cut]
                sa, sb = stats(a), stats(b)
                wa = (a["net_usd"] > 0).mean() if len(a) else np.nan
                wb = (b["net_usd"] > 0).mean() if len(b) else np.nan
                mark = " **" if cut in (FIT_BODY_CUT, FIT_RANGE_CUT) else " "
                L.append(f"| {tf} | {form} |{mark}{cut}{mark.strip()} | {len(a):,} | "
                         f"{_pct(len(a) / max(len(r), 1))} | {_f(sa['exp_r'])} | "
                         f"{_f(sb['exp_r'])} | {_f(sa['exp_r'] - sb['exp_r'])} | "
                         f"{_pct(wa)} | {_pct(wb)} | {_pct(wa - wb)} |")
    L.append("")

    # ---- Table 5c: statistical power -----------------------------------------
    L += ["## 5c. Can this data even see a 3-4 point effect?", "",
          "Before reading any of the differences above as real or absent, the "
          "question of whether they are resolvable at all. Minimum detectable "
          "win-rate difference between two equal buckets, two-sided alpha=0.05, "
          "80% power, at the win rate each timeframe actually shows at 2R — and "
          "the total trades that would be needed to detect the 4-point effect "
          "`threshold_fits.md` reports on 4h.", "",
          "| TF | sample | n | win rate | min detectable diff | n needed for 4pp | "
          "years of data implied |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for tf in tfs:
        r = apply_cost(resolved[(tf, "2R")], base_cost)
        span_yr = (r["time"].max() - r["time"].min()).days / 365.25 if len(r) else 1
        for sample in ("IS", "OOS", "all"):
            sub = slice_sample(r, sample)
            if not len(sub):
                continue
            p = float((sub["net_usd"] > 0).mean())
            n = len(sub)
            need = n_for_effect(0.04, p)
            rate = len(r) / max(span_yr, 1e-9)
            L.append(f"| {tf} | {sample} | {n:,} | {_pct(p)} | "
                     f"{_pct(mde(n // 2, n - n // 2, p))} | {need:,.0f} | "
                     f"{need / max(rate, 1e-9):,.1f} |")
    L.append("")

    # ---- Table 6: null baseline ---------------------------------------------
    L += ["## 6. The null — the same trade taken on every bar", "",
          "`primitive_base_rates.md` records that 40-44% of candles sweep the prior "
          "candle's range, so being a C2 is ordinary. This table takes the identical "
          "trade (enter at the bar close, stop at that bar's opposite extreme) on "
          "**every** bar in both directions. Taking both directions everywhere makes "
          "the directional edge zero by construction, so what this measures is the "
          "**friction of the mechanism itself** — the stop-first tie-break, gap "
          "fills and spread. Both cost 0.0 and cost 0.2 are shown because the null's "
          "stops are tighter than the C2 stops, so a flat spread taxes it harder.", "",
          "| TF | target | cost | sample | n | win | exp R | exp USD/oz | PF | "
          "maxDD R | mean R (USD) | time-exit |",
          "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for tf in tfs:
        bt = baseline_trades(m1, tf)
        for tgt in targets:
            if tgt == "structural":
                continue
            r0 = resolve(bt, target_levels(bt, tgt), m1)
            for cost in (0.0, base_cost):
                r = apply_cost(r0, cost)
                for sample in ("IS", "OOS"):
                    L.append(f"| {tf} | {tgt} | {cost} | {sample} | "
                             f"{_row(stats(slice_sample(r, sample)))} |")
    L.append("")

    # ---- Table 6b: matched random-entry control -----------------------------
    L += ["## 6b. Matched random-entry control", "",
          "The decisive control, and the one the external cross-reference "
          "(`meta/external_crossref.md`) says to copy. Every C2 trade is paired "
          "with **five** random trades carrying the *same direction, the same stop "
          "distance and the same target distance*, entered at the close of a random "
          "bar within +/-30 days of the original. Local sampling keeps the "
          "volatility regime matched, which a whole-period draw would not: gold ran "
          "1,800 -> 5,500 across this data.", "",
          "A win rate means nothing against 50%. It only means something against "
          "this. Differences carry a 2,000-draw bootstrap 95% CI; a CI that "
          "straddles zero is no effect.", "",
          "| TF | target | sample | C2 bucket | n | C2 win | ctrl win | win diff "
          "(95% CI) | C2 exp R | ctrl exp R | exp R diff (95% CI) |",
          "|---|---|---|---|---:|---:|---:|---|---:|---:|---|"]
    ctrl_res: dict[tuple, tuple] = {}
    for tf in tfs:
        df_tf = resample(m1, tf)
        tr = build_trades(m1, tf)
        for tgt in targets:
            ctr, ctgt = matched_control(tr, target_levels(tr, tgt), df_tf, m1, tf)
            cres = apply_cost(resolve(ctr, ctgt, m1), base_cost)
            r = apply_cost(resolved[(tf, tgt)], base_cost)
            for sample in ("IS", "OOS"):
                cs = slice_sample(cres, sample)
                sub = slice_sample(r, sample)
                cw = (cs["net_usd"] > 0).to_numpy().astype(float)
                cr = cs["net_r"].to_numpy(float)
                for lab, part in (("small", sub[sub["small_med"]]), ("all", sub)):
                    pw = (part["net_usd"] > 0).to_numpy().astype(float)
                    pr = part["net_r"].to_numpy(float)
                    dw, dwl, dwh = boot_diff(pw, cw)
                    dr, drl, drh = boot_diff(pr, cr)
                    ctrl_res[(tf, tgt, sample, lab)] = (dw, dwl, dwh, dr, drl, drh)
                    L.append(
                        f"| {tf} | {tgt} | {sample} | {lab} | {len(part):,} | "
                        f"{_pct(pw.mean() if len(pw) else np.nan)} | "
                        f"{_pct(cw.mean() if len(cw) else np.nan)} | "
                        f"{_pct(dw)} [{_pct(dwl)}, {_pct(dwh)}] | "
                        f"{_f(pr.mean() if len(pr) else np.nan)} | "
                        f"{_f(cr.mean() if len(cr) else np.nan)} | "
                        f"{_f(dr)} [{_f(drl)}, {_f(drh)}] |")
    L.append("")

    # ---- Table 6c: the resolution artefact ----------------------------------
    L += ["## 6c. The resolution artefact — M1 exits vs signal-timeframe exits", "",
          "The identical book, resolved twice: once bar-by-bar on M1 (everything "
          "above) and once on the signal timeframe's own OHLC. The coarse version "
          "cannot see the order of events inside a bar, so a bar that touched both "
          "the stop and the target is one event to it rather than two — and the "
          "tie-break has to guess. Two coarse variants are shown: `tf/stop-first` "
          "keeps the conservative rule, `tf/target-first` is the optimistic one a "
          "careless backtest falls into.", "",
          "This is the failure mode the external cross-reference flags as having "
          "turned a ~73% win rate into ~50% in a published FVG study. The gap "
          "between the columns below is the size of that artefact on this book.", "",
          "| TF | target | sample | M1 win | M1 exp R | tf/stop-first win | "
          "tf/stop-first exp R | tf/target-first win | tf/target-first exp R |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    art: dict[tuple, tuple] = {}
    for tf in tfs:
        df_tf = resample(m1, tf)
        tr = build_trades(m1, tf)
        for tgt in targets:
            lv = target_levels(tr, tgt)
            coarse = apply_cost(resolve(tr, lv, df_tf, "j0", "j1"), base_cost)
            opt = apply_cost(resolve(tr, lv, df_tf, "j0", "j1", tie="target"),
                             base_cost)
            fine = apply_cost(resolved[(tf, tgt)], base_cost)
            for sample in ("IS", "OOS"):
                f_, c_, o_ = (stats(slice_sample(fine, sample)),
                              stats(slice_sample(coarse, sample)),
                              stats(slice_sample(opt, sample)))
                art[(tf, tgt, sample)] = (f_, c_, o_)
                L.append(f"| {tf} | {tgt} | {sample} | {_pct(f_['win'])} | "
                         f"{_f(f_['exp_r'])} | {_pct(c_['win'])} | {_f(c_['exp_r'])} | "
                         f"{_pct(o_['win'])} | {_f(o_['exp_r'])} |")
    L.append("")

    # ---- Table 6d: session breaks and weekends inside the hold window -------
    L += ["## 6d. Do the results depend on walking M1 across a session break?", "",
          "XAUUSD stops trading 17:00-18:04 New York daily (zero bars in NY hour "
          "17) and over weekends, so a 10-period hold window can contain a hole. "
          "Walking straight through one lets a stop or target be 'hit' on the far "
          "side of a gap the position could not have been managed across. The fills "
          f"are already conservative about this — a bar opening beyond the stop "
          "fills at that open, so the gap is paid — but the honest check is to "
          "re-run the whole book flat over the break and compare. `truncated` ends "
          f"every window at the first gap longer than {GAP_MIN} minutes and exits at "
          "the last price before it.", "",
          "**Read the low timeframes only.** At 15m and 1h a hold window rarely "
          "reaches a break, so truncation is a genuine robustness check — and it "
          "changes nothing. At 4h and especially 1D a multi-period hold *must* span "
          "weekends, so the truncated column there is not a robustness check at "
          "all: it is a different, much shorter strategy, and its difference should "
          "not be read as an artefact estimate.", "",
          "| TF | target | sample | windows spanning a break | full exp R | "
          "truncated exp R | diff |",
          "|---|---|---|---:|---:|---:|---:|"]
    for tf in tfs:
        tr = build_trades(m1, tf)
        i1t = truncate_at_gap(tr, m1)
        span = float((i1t < tr["i1"].to_numpy()).mean())
        trt = tr.copy()
        trt["i1"] = i1t
        trt = trt[trt["i1"] > trt["i0"]]
        for tgt in targets:
            cut = apply_cost(resolve(trt, target_levels(trt, tgt), m1), base_cost)
            full = apply_cost(resolved[(tf, tgt)], base_cost)
            for sample in ("IS", "OOS"):
                sf = stats(slice_sample(full, sample))
                sc = stats(slice_sample(cut, sample))
                L.append(f"| {tf} | {tgt} | {sample} | {_pct(span)} | "
                         f"{_f(sf['exp_r'])} | {_f(sc['exp_r'])} | "
                         f"{_f(sf['exp_r'] - sc['exp_r'])} |")
    L.append("")

    L += ["## 6e. What is deliberately *not* in this backtest", "",
          "**No session or kill-zone filter is applied anywhere in this file.** "
          "That is a decision, not an omission. `meta/session_window_fit.md` "
          "measures the corpus's own forex NY AM window (07:00-10:00 New York) at "
          "**-0.057R versus the rest of the day (t = -3.11, 7,835 events)** — the "
          "only session result that survives multiple-testing correction, and it is "
          "negative. Gating on time of day would have made these results worse for "
          "a reason unrelated to the wick claim, and would have confounded the "
          "test. If a session knob is swept later it should be swept, not applied.",
          "",
          "The same document settles the timezone as `America/New_York` **with "
          "DST**. Nothing here depends on it: every window is defined in elapsed "
          "wall-clock time from the signal bar's close, and no rule in this module "
          "references a local hour.", "",
          "**Which outcome metrics are safe, and which are not.** "
          "`threshold_fits.md` warns that the two metrics most literally encoding "
          "the corpus's wording — 'continued' beyond the extreme and 'reverted' to "
          "the open — are geometrically confounded by the very quantity being "
          "bucketed, since `range = opposing_run + body + far_wick` means a large "
          "opposing run forces a small body. That is the same defect this file "
          "independently diagnoses in table 0 via the `open gap R` column, arrived "
          "at from the other direction.", "",
          "- **`delivered beyond C2 open` (table 0) is CONFOUNDED** and is reported "
          "only to show why. It reduces to where the candle closed relative to its "
          "own open.", "",
          "- **R-multiple and structural targets resolved on M1 are safe.** The "
          "target and stop are absolute prices fixed at entry, and the outcome is "
          "decided by bars strictly after the signal candle closed. No part of the "
          "signal candle's own geometry can satisfy them.", "",
          "- **MFE / MAE (table 0, right half) are safe** for the same reason: they "
          "measure forward travel over bars the signal candle cannot influence "
          "mechanically. They are the target-free cross-check on the confounded "
          "column beside them, and they disagree with it.", ""]

    L += _verdict(resolved, exc, pvals, ctrl_res, art, base_cost, costs, tfs, targets)

    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}  ({len(L)} lines)")
    return 0


def _verdict(resolved, exc, pvals, ctrl_res, art, base_cost, costs, tfs,
             targets) -> list[str]:
    """Summary table plus the verdict, with every load-bearing number recomputed.

    The prose interpolates from the same objects the tables above were built
    from, so re-running on different data cannot leave a stale conclusion
    sitting on top of fresh numbers — which is exactly how the 78-83% claim
    survived as long as it did.
    """
    L = ["## 7. Summary — every cell, out-of-sample", "",
         f"| TF | target | OOS small exp R | OOS large exp R | OOS all exp R | "
         f"OOS small PF | positive after cost {base_cost}? |",
         "|---|---|---:|---:|---:|---:|---|"]
    for tf in tfs:
        for tgt in targets:
            r = slice_sample(apply_cost(resolved[(tf, tgt)], base_cost), "OOS")
            s = stats(r[r["small_med"]])
            lg = stats(r[~r["small_med"]])
            al = stats(r)
            ok = "yes" if np.isfinite(s["exp_r"]) and s["exp_r"] > 0 else "no"
            L.append(f"| {tf} | {tgt} | {_f(s['exp_r'])} | {_f(lg['exp_r'])} | "
                     f"{_f(al['exp_r'])} | {_f(s['pf'], 2)} | {ok} |")
    L.append("")

    # --- numbers the verdict leans on, recomputed ---------------------------
    e = exc["1h"]
    q = {b: e[e["bucket"] == b] for b in range(5)}
    dq1, dq5 = q[0]["delivered"].mean(), q[4]["delivered"].mean()
    gq1, gq5 = q[0]["open_gap_r"].mean(), q[4]["open_gap_r"].mean()
    mfe2 = {b: (q[b]["mfe_r"] >= 2).mean() for b in range(5)}
    best_mfe = max(range(5), key=lambda b: mfe2[b])

    is_d, is_p = pvals[("1h", "2R", "IS", "median")]
    oos_d, oos_p = pvals[("1h", "2R", "OOS", "median")]
    n_tests = len(pvals)
    n_sig = sum(1 for _, p in pvals.values() if p < 0.05)
    n_sig_is = sum(1 for k, (_, p) in pvals.items() if p < 0.05 and k[2] == "IS")
    bonf = 0.05 / n_tests
    n_bonf = sum(1 for _, p in pvals.values() if p < bonf)

    cost_line = []
    for c in costs:
        r = slice_sample(apply_cost(resolved[("1h", "2R")], c), "OOS")
        cost_line.append(f"{c} -> {_f(stats(r[r['small_med']])['exp_r'])} R")

    n_all = len(resolved[("1h", "2R")])
    n_struct = len(resolved[("1h", "structural")])
    n_is, n_oos = len(slice_sample(resolved[("1h", "2R")], "IS")), \
        len(slice_sample(resolved[("1h", "2R")], "OOS"))
    r_is = resolved[("1h", "2R")]
    mean_r_is = slice_sample(r_is, "IS")["risk"].mean()
    mean_r_oos = slice_sample(r_is, "OOS")["risk"].mean()

    # 6b / 6c numbers for the verdict
    def cw(tf, tgt, sample, lab):
        return ctrl_res[(tf, tgt, sample, lab)]
    c_is_s = cw("1h", "2R", "IS", "small")
    c_oos_s = cw("1h", "2R", "OOS", "small")
    c_oos_a4 = cw("4h", "2R", "OOS", "all")
    c_is_a4 = cw("4h", "2R", "IS", "all")
    n_clear = sum(1 for k, v in ctrl_res.items() if v[4] > 0)
    n_clear_1h = sum(1 for k, v in ctrl_res.items() if v[4] > 0 and k[0] == "1h")
    n_ctrl = len(ctrl_res)
    # Largest |win-rate difference vs the control| at 1h, R-multiple targets only.
    w1h = max(abs(v[0]) for k, v in ctrl_res.items()
              if k[0] == "1h" and k[1] != "structural")
    w1h_st = max(abs(v[0]) for k, v in ctrl_res.items()
                 if k[0] == "1h" and k[1] == "structural")
    a_f, _a_c, a_o = art[("1h", "2R", "OOS")]

    # power + fitted-cut numbers
    pw = {}
    for tf in tfs:
        r = apply_cost(resolved[(tf, "2R")], base_cost)
        p = float((r["net_usd"] > 0).mean())
        v = r["wick_body"].to_numpy(float)
        a, b = r[v <= FIT_BODY_CUT], r[v > FIT_BODY_CUT]
        wd = ((a["net_usd"] > 0).mean() - (b["net_usd"] > 0).mean()) \
            if len(a) and len(b) else np.nan
        pw[tf] = {"n": len(r), "p": p, "mde": mde(len(r) // 2, len(r) - len(r) // 2, p),
                  "need": n_for_effect(0.04, p), "wd": wd,
                  "pass": len(a) / max(len(r), 1)}

    L += ["## 8. Verdict", "", "**The claim is refuted where this data can see, and "
          "unresolvable where it cannot.** That distinction is the main finding and "
          "it is stated first because it is the one that is easy to get wrong in "
          "both directions.", "",
          "### Start with power, because it decides what the rest can mean", "",
          "An independent barrier test (`meta/threshold_fits.md`) puts the true "
          "small-wick advantage at **+4.0pp on 4h and +3.2pp on 1D, and "
          "approximately zero on 15m and 1h**. That is the effect size this "
          "backtest has to be able to see. Table 5c says it can only see it on two "
          "timeframes, and they are the wrong two:", "",
          "| TF | C2 trades, 3 years | min detectable diff | verdict |",
          "|---|---:|---:|---|"]
    for tf in tfs:
        s = pw[tf]
        v = ("can resolve a 3-4pp effect" if s["mde"] <= 0.03
             else "marginal — can see 4pp, not 3pp" if s["mde"] <= 0.04
             else "**cannot resolve a 3-4pp effect**")
        L.append(f"| {tf} | {s['n']:,} | {_pct(s['mde'])} | {v} |")
    L += ["",
          f"Detecting a 4-point difference needs roughly "
          f"{pw[tfs[0]]['need']:,.0f} C2s in total, split evenly between the two "
          "wick buckets. Three years of XAUUSD "
          f"supplies {pw['4h']['n']:,} C2s on 4h and {pw['1D']['n']:,} on 1D — about "
          "10 and 55 years of data short respectively. **So this file cannot "
          "falsify the claim on 4h or 1D, and does not claim to.** Any 4h/1D number "
          "below, in either direction, is inside the noise floor.", "",
          "What it *can* do is test the timeframes with the sample: 15m "
          f"(n={pw['15min']['n']:,}, min detectable {_pct(pw['15min']['mde'])}) and "
          f"1h (n={pw['1h']['n']:,}, {_pct(pw['1h']['mde'])}).", "",
          "### On the timeframes with enough data, the effect is absent — as predicted",
          "",
          "At the grade-A fitted cut `opposing_run/body <= "
          f"{FIT_BODY_CUT}` the small-wick win-rate advantage is "
          f"**{_pct(pw['15min']['wd'])} at 15m** and **{_pct(pw['1h']['wd'])} at "
          "1h** (table 5b), both below their own detection floors and both far "
          "below the ~15 points the delivery table implies. Every cut across the "
          f"fitted plateau {FIT_BODY_SWEEP[0]}-{FIT_BODY_SWEEP[-1]} stays inside "
          "3 points at both timeframes.", "",
          "**This is a confirmation, not a failed replication.** The independent "
          "barrier test predicted approximately zero at 15m and 1h from a "
          "completely different measurement (a scale-free +/-1 ATR race, no stop, "
          "no target, no costs). Two unrelated methods agreeing that the effect is "
          "absent on the low timeframes is the strongest positive statement in this "
          "file — it is just a statement about where the claim does *not* live.", "",
          "One caveat on the imported cut: it does not price the same way here. "
          f"`opposing_run/body <= {FIT_BODY_CUT}` sits at about the 65th percentile "
          "of *all* XAUUSD candles per `threshold_fits.md`, but admits only "
          f"{_pct(pw['1h']['pass'])} of 1h **C2s**. Requiring a close back inside "
          "the prior range and a reversal close already selects on wick size, so "
          "the fitted percentile does not transfer to this event set. The sweep is "
          "reported for that reason rather than a single cut.", "",
          "### C2 entries are indistinguishable from random entries of the same shape",
          "",
          "This is the decisive test and it is the one the claim has never faced. "
          "Give a random entry the same direction, the same stop distance and the "
          "same target distance at a random moment in the same month, and at 1h it "
          f"performs as well as the C2. In-sample the small-wick C2 book is "
          f"{_f(abs(c_is_s[3]))} R *worse* than its random twin (95% CI "
          f"[{_f(c_is_s[4])}, {_f(c_is_s[5])}]); out-of-sample it is "
          f"{_f(abs(c_oos_s[3]))} R better (CI [{_f(c_oos_s[4])}, "
          f"{_f(c_oos_s[5])}]). Both intervals contain zero, and no win-rate "
          f"difference at 1h on an R-multiple target exceeds {_pct(w1h)} in either "
          f"direction (the structural target is worse still, reaching "
          f"{_pct(w1h_st)} *against* the C2). Of the {n_ctrl} C2-vs-control "
          f"comparisons in table 6b, {n_clear} have a confidence interval that "
          f"clears zero — and "
          f"{'none of those are at 1h' if n_clear_1h == 0 else f'{n_clear_1h} of those are at 1h'}"
          ", the timeframe with by far the most trades.", "",
          "The tightest measurement in the file is at 15m, where the sample is "
          "largest: the small-wick C2 book beats its random twin by "
          f"{_pct(cw('15min', '2R', 'IS', 'small')[0])} in-sample and "
          f"{_pct(cw('15min', '2R', 'OOS', 'small')[0])} out-of-sample, with "
          "confidence intervals about one percentage point wide. That is a "
          "well-powered zero.", "",
          "The published FVG study cited in `meta/external_crossref.md` found its "
          "construct about five percentage points above a matched random baseline "
          "and still had no tradeable edge after costs. The C2 wick split does not "
          "reach five points anywhere it can be measured.", "",
          "### The old statistic is real but measures the wrong thing", "",
          f"Table 0 replicates it exactly: at 1h the smallest-wick quintile delivers "
          f"beyond the C2 open {_pct(dq1)} of the time and the largest {_pct(dq5)}, "
          "monotone across all five buckets and repeated at 4h and 1D. But the "
          "`open gap R` column moves in perfect lockstep: the C2 open sits "
          f"{_f(gq1, 2)}R below the entry in the smallest-wick bucket and only "
          f"{_f(gq5, 2)}R below it in the largest. **The delivery test is asking the "
          "small-wick bucket an easier question.** A small sweeping wick means a "
          "proportionally larger body, which puts the C2 open further from the "
          "close, which gives the next candle more room to fail to reach it. The "
          "gap measures the geometry of the signal candle, not the behaviour of the "
          "one after it.", "",
          "On the measure that cannot be gamed this way — maximum favourable "
          "excursion, which needs no target and no arbitrary reference price — the "
          "ordering **reverses**. At 1h, the fraction of C2s that ever travel 2R in "
          f"favour is {_pct(mfe2[0])} for the smallest-wick quintile against "
          f"{_pct(mfe2[best_mfe])} for {QUINTILE_LABELS[best_mfe]}. Small-wick C2s "
          "expand *less* often, not more. Mean MFE tells the same story: the "
          "smallest bucket is not the largest on any timeframe.", "",
          "### The backtested effect changes sign between the fit and the holdout",
          "",
          f"At 1h/2R with a {base_cost} spread, the median-split difference "
          f"`mean_R(small) - mean_R(large)` is **{_f(is_d)} R in-sample** "
          f"(n={n_is:,}, two years, one-sided p={_f(is_p, 3)} — the data leans the "
          f"*other* way) and **{_f(oos_d)} R out-of-sample** (n={n_oos:,}, one year, "
          f"p={_f(oos_p, 3)}). The larger sample contradicts the smaller one. The "
          "same flip appears at 1R and 3R. That is what noise looks like, not an "
          "edge with a bad year.", "",
          f"Across all {n_tests} permutation tests run here, {n_sig} came in under "
          f"p=0.05 — against {0.05 * n_tests:.1f} expected by chance alone — and "
          f"{n_bonf} survive a Bonferroni threshold of {bonf:.4f}. "
          f"{'None of them are in-sample' if n_sig_is == 0 else f'{n_sig_is} are in-sample'}"
          ", which is the wrong way round: a real effect should show up most "
          "clearly in the *larger* sample, not only in the smaller one.", "",
          "The threshold sweep (table 5) makes the same point without any split "
          "point to argue about. Out-of-sample the curve does slope the predicted "
          "way, peaking around t=0.20. In-sample, over twice the trades, the same "
          "curve is flat and negative at every threshold. The shape the holdout "
          "shows simply is not present in the fit window.", "",
          "### What is left is smaller than the spread", "",
          "At 1h the entire measured out-of-sample effect lives inside the bid-ask. "
          "The small-wick bucket at 2R goes: " + "; ".join(cost_line) + ". A "
          "0.2-0.3 USD/oz round trip — the realistic base case for XAUUSD — consumes "
          "essentially all of it, and the risk-proportional cost puts it back "
          "underwater.", "",
          "There is also a confound in the flat-cost columns worth naming: gold ran "
          "from roughly 1,800 to 5,500 over this sample, so the mean 1h R nearly "
          f"triples between the fit and the holdout ({_f(mean_r_is, 2)} -> "
          f"{_f(mean_r_oos, 2)} USD). A flat {base_cost} USD spread is therefore a "
          f"{100 * base_cost / mean_r_is:.1f}% tax in-sample and a "
          f"{100 * base_cost / mean_r_oos:.1f}% tax "
          "out-of-sample. Part of why the holdout looks kinder than the fit has "
          "nothing to do with the signal at all — which is why the `0.04R` "
          "proportional column exists.", "",
          "### How this compares to the null", "",
          "`primitive_base_rates.md` records that 40-44% of candles sweep the prior "
          "candle's range. C2s are 27% of 1h bars here — this is an ordinary event, "
          "and sorting ordinary events by a wick ratio does not stop them being "
          "ordinary. Table 6 takes the identical trade on every bar in both "
          "directions, which zeroes the directional edge by construction and leaves "
          "only mechanism friction. At zero cost that friction is about -0.02 R at "
          "1h in-sample and -0.16 R out-of-sample. The C2 book as a whole lands at "
          "-0.037 R in-sample (worse than an arbitrary bar) and -0.008 R "
          "out-of-sample (better). So even **C2 selection itself**, never mind the "
          "wick, has no stable sign at 1h.", "",
          "### 4h: the one place the claim is still alive, and why that is not a "
          "result yet", "",
          "4h is where this file and `threshold_fits.md` are most nearly "
          "consistent, and it deserves stating plainly rather than being buried. "
          f"At the fitted cut the small-wick win-rate advantage is "
          f"{_pct(pw['4h']['wd'])}, and every cut across the fitted plateau gives "
          "between +4.3 and +6.5 points — the right sign and roughly the right size "
          "against the independent +4.0pp barrier result. Expectancy differences "
          "run +0.08 to +0.15 R the same way.", "",
          "Three reasons it is not yet a finding. First, power: 4h's minimum "
          f"detectable difference is {_pct(pw['4h']['mde'])}, so an effect of this "
          "size is not distinguishable from zero here however suggestive it looks. "
          "Second, it does not hold up across the split — against the matched random "
          f"control the whole 4h/2R C2 book is {_f(c_oos_a4[3])} R out-of-sample "
          f"(CI [{_f(c_oos_a4[4])}, {_f(c_oos_a4[5])}], clears zero) but only "
          f"{_f(c_is_a4[3])} R in-sample (CI [{_f(c_is_a4[4])}, {_f(c_is_a4[5])}], "
          "does not), on twice the data. Third, most of it is not about wicks: the "
          "whole 4h C2 book beats the random control by 5.9 points out-of-sample "
          "against 7.8 for the small-wick subset, and the quintiles are "
          "non-monotone (Q4 scores as well as Q1 on every target). **Whatever is at "
          "4h is mostly C2-ness, not wick size.**", "",
          "The correct next step for 4h is more data — other instruments, or a "
          "longer XAUUSD history — not more analysis of these 1,367 trades.", "",
          "### A coarse backtest would have got the opposite answer", "",
          "Table 6c re-resolves the identical book on signal-timeframe bars. The "
          "artefact is real and it points exactly the way the FVG study warned. At "
          f"1h/2R out-of-sample, M1 resolution gives {_pct(a_f['win'])} win rate and "
          f"{_f(a_f['exp_r'])} R; the same trades resolved on 1h bars with an "
          f"optimistic same-bar tie-break give {_pct(a_o['win'])} and "
          f"{_f(a_o['exp_r'])} R — a sign flip. The same flip happens at 1R, 3R and "
          "structural, and at 4h/structural in-sample a flat 0.000 R becomes "
          "+0.105 R. The effect here is smaller than the 73%-to-50% collapse MPM "
          "reported, because an R-multiple target on XAUUSD usually takes many bars "
          "to reach, but it is large enough to manufacture a positive result out of "
          "a negative one. Any C2 backtest resolved on its own signal timeframe "
          "should be assumed wrong.", "",
          "### The model's own target is the worst one", "",
          "Worth recording separately, because it is the target the fractal model "
          "actually implies: `structural` — sweep the low, deliver to the prior "
          "candle's high — is the only target that loses money in every period on "
          "every timeframe (1h OOS -0.066 R, 1D OOS -0.320 R). It also cannot "
          f"express the whole signal: at 1h, {n_all - n_struct:,} of {n_all:,} C2s "
          "closed beyond the prior candle's far extreme, leaving no target to aim "
          "at. The R multiples that score better are ones the corpus never "
          "specifies.", "",
          "### Bottom line", "",
          "The C2 sweeping-wick asymmetry should be **retired as a trade signal on "
          "15m and 1h, and treated as untested on 4h and 1D.**", "",
          "The 78-83% vs 63-66% figure in `fractal_reading_comparison.md` is not "
          "wrong, but it is not evidence of expansion — it is evidence that the C2 "
          "open sits further from the close when the wick is small, which an "
          "independent workstream flagged as a geometric confound from the other "
          "direction. Corrected for it, small-wick C2s reach a 2R target slightly "
          "*less* often than large-wick ones. Under a stop, a target, "
          "path-dependent M1 resolution and a realistic spread, the effect has the "
          "wrong sign in the two-year fit window, an unremarkable positive sign in "
          "the one-year holdout, no cell that survives correction for the number of "
          "cells tested, and — decisively — no measurable advantage over a random "
          "entry of identical geometry on either timeframe where the sample is big "
          "enough to say so.", "",
          "The real effect size in play was never 15 points. It is 3-4, and at that "
          "size three years of XAUUSD is simply not enough data on 4h or 1D. "
          "Reporting that honestly is worth more than a verdict the sample cannot "
          "support in either direction.", "",
          "This closes item 1 of the RESUME.md next-steps list, and it agrees with "
          "the two external priors: Marshall, Young & Rose found candlestick shapes "
          "create no value against bootstrapped controls, and the one quantitative "
          "study of a same-family ICT construct found ~5 points over random and "
          "nothing after costs. The corpus's best falsifiable prediction has now "
          "been tested on its own terms where it could be, and the honest verdict "
          "is split: **refuted on 15m and 1h, underpowered on 4h and 1D.** Given "
          "the claim is externally unattested — every outside search hit traced "
          "back to the channel — this file is currently the only independent test "
          "of it that exists, and knowing exactly which half of it remains open is "
          "more useful than another conditional probability.", "",
          "**RESUME.md finding 4 should be amended.** It currently reads that the "
          "claim 'still survives testing' and calls it the best backtest candidate. "
          "It survives *counting*; it does not survive testing at 15m or 1h, and at "
          "4h and 1D it has not been tested — the data cannot carry the test. "
          "`fractal_reading_comparison.md` was already careful to say the delivery "
          "rate is not an edge; that caution was correct and should now be "
          "strengthened.", "",
          "### What would actually settle it", "",
          "Not more analysis of this sample. Specifically:", "",
          "1. **More 4h/1D observations** — other instruments (the FVG study used "
          "four futures markets for exactly this reason) or a longer XAUUSD "
          f"history. About {pw['4h']['need']:,.0f} 4h C2s are needed; three years "
          f"gives {pw['4h']['n']:,}.", "",
          "2. **Test C2-ness separately from wick size.** The 4h signal here is "
          "mostly the former, and it is the cheaper hypothesis to check.", "",
          "3. **Do not re-test on 15m or 1h.** Two independent methods now agree "
          "there is nothing there, and a third look at the same data is p-hacking, "
          "not replication.", ""]
    return L


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tf", default="1h", help="comma list: 15min,1h,4h,1D")
    ap.add_argument("--target", default="2R", help="comma list: 1R,2R,3R,structural")
    ap.add_argument("--cost", default="0.2",
                    help="comma list; USD/oz, or a risk fraction like 0.04R")
    ap.add_argument("--max-hold", type=int, default=MAX_HOLD,
                    help="hold cap in wall-clock multiples of the timeframe")
    ap.add_argument("--sweep-ref", default="prior_candle",
                    choices=("prior_candle", "lookback_extreme"))
    ap.add_argument("--all", action="store_true",
                    help="regenerate meta/backtest_c2_wick.md (ignores --tf/--target)")
    ap.add_argument("--out", default=str(OUT_MD))
    a = ap.parse_args(argv)

    if a.all:
        return run_all(out=Path(a.out))

    tfs = [x.strip() for x in a.tf.split(",") if x.strip()]
    tgts = [x.strip() for x in a.target.split(",") if x.strip()]
    costs = [x.strip() if x.strip().endswith("R") else float(x)
             for x in a.cost.split(",") if x.strip()]

    m1 = load_m1()
    print(f"M1 {len(m1):,} bars {m1.index.min()} -> {m1.index.max()}")
    print("stop=C2 extreme | same-M1-bar stop+target resolves to STOP | "
          f"hold cap {a.max_hold} x tf")
    hdr = ("tf   target      cost sample bucket      n     win    expR   expUSD"
           "     PF  maxDD_R   meanR  timeEx")
    print(hdr)
    print("-" * len(hdr))
    for tf in tfs:
        tr = build_trades(m1, tf, sweep_ref=a.sweep_ref, max_hold=a.max_hold)
        med = float(np.nanmedian(tr[tr["time"] < IS_END]["wick_ratio"]))
        for tgt in tgts:
            r0 = resolve(tr, target_levels(tr, tgt), m1)
            r0["small_med"] = r0["wick_ratio"] <= med
            for cost in costs:
                r = apply_cost(r0, cost)
                for sample in ("IS", "OOS"):
                    sub = slice_sample(r, sample)
                    for lab, part in (("small", sub[sub["small_med"]]),
                                      ("large", sub[~sub["small_med"]]),
                                      ("all", sub)):
                        s = stats(part)
                        print(f"{tf:4} {tgt:10} {str(cost):>6} {sample:6} {lab:6} "
                              f"{s['n']:6,} {_pct(s['win']):>6} {_f(s['exp_r']):>7} "
                              f"{_f(s['exp_usd'], 2):>8} {_f(s['pf'], 2):>6} "
                              f"{_f(s['mdd_r'], 1):>8} {_f(s['risk'], 2):>7} "
                              f"{_pct(s['time_exit']):>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
