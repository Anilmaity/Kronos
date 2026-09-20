"""Fit the corpus's undefined `session` gate into a parameterised knob, on XAUUSD.

Why this exists. `session` is the single largest automation blocker in the concept
library — it gates 68 concepts (`meta/automation_gaps.md`), more than any other
undefined term. Two facts are already settled by the reading phase and are NOT
re-litigated here:

  * the clock is New York / US-Eastern, stated outright in the corpus, and
  * TTrades never states a clock as *his own gating rule*. The widest such claim
    is "I only look to take trades between 8:30 and 12".

But "no hours anywhere" is too strong, and this script tests the stronger
candidate. `concepts/time/killzones.yaml` records two complete kill-zone grids
spoken in video MPeeE55rNOw ("ICT Killzones & Indicator Settings"), verified
against `raw/transcripts/MPeeE55rNOw.txt`:

    forex    Asia 20:00-00:00  London 02:00-05:00  NY AM 07:00-10:00  LC 10:00-12:00
    indices  Asia 20:00-00:00  London 02:00-05:00  NY AM 08:30-11:00  PM 13:30-16:00

That is taught convention presented in a lesson, not a rule he narrates himself
applying, and the concept is filed `contested` — so it is a candidate to test,
not an answer. XAUUSD could plausibly follow either grid, so both are scored.

This script measures where, in New York local time, XAUUSD actually does the
things the methodology cares about — forms its daily extremes, travels its
range, and lets the corpus's own primitives (C2, CISD, displacement) follow
through — and scores every corpus-anchored window against alternatives and
against an all-hours null.

It also settles two ambiguities the corpus leaves open for gold specifically:

  * EST-fixed (UTC-5) vs America/New_York-with-DST. The corpus says "Eastern
    Standard time" literally but anchors on the NYSE cash open, which is a
    DST-aware event. Here the question is decided by the data's own venue clock.
  * The 4H opening grid. The corpus gives two asset-class grids — futures
    02/06/10/14 NY and forex 17/21/01/09 NY — and says the 09:30 open "doesn't
    really apply" to forex. XAUUSD sits between the two, so both grids are built
    and compared on sweep-then-reverse quality.

Data: m3_scalper/xau_m1_3y.parquet, ~1.07M M1 bars, 2023-07-02..2026-07-23,
tz-aware UTC. Offline only; nothing here reaches the network.

Honest about what this is not: this measures *conditional follow-through of
primitives*, not the P&L of a finished strategy. Costs are not modelled (a fixed
gold spread is close to hour-invariant except in Asia, which is flagged rather
than priced), and every number is in-sample over three years of one instrument.
Treat the output as a prior for a sweep range, not as a fitted parameter to
freeze.

Writes research/meta/session_window_fit.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample, session                      # noqa: E402
from detectors.cisd import cisd_events                           # noqa: E402
from detectors.fractal import c2_events                          # noqa: E402
from detectors.primitives import (                               # noqa: E402
    candle_range_sweep, displacement,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "meta" / "session_window_fit.md"

NY = "America/New_York"          # Eastern WITH daylight saving
EST_FIXED = "Etc/GMT+5"          # the literal "EST" reading, UTC-5 year round

EXEC_TF = "15min"                # execution timeframe for the detector pass
HORIZON = 8                      # forward bars scored after an event (= 2h on 15m)
ATR_LOOKBACK = 20
REOPEN_DROP_MIN = 30              # minutes after a halt treated as reopen noise

# Candidate windows, NY local, [start, end). The first is the null.
#
# The `KZ ...` rows are NOT invented: they are the full kill-zone grids recorded
# in `concepts/time/killzones.yaml` and spoken in video MPeeE55rNOw ("ICT
# Killzones & Indicator Settings"). The corpus gives two grids, forex and
# indices, which differ only in the New York portion — and XAUUSD is exactly the
# instrument that could belong to either, so both are tested.
WINDOWS: list[tuple[str, str, str]] = [
    ("all-hours (null)", "00:00", "00:00"),
    ("KZ Asia 20:00-00:00", "20:00", "00:00"),
    ("KZ London 02:00-05:00", "02:00", "05:00"),
    ("KZ forex NY AM 07:00-10:00", "07:00", "10:00"),
    ("KZ forex London Close 10:00-12:00", "10:00", "12:00"),
    ("KZ forex AM+LC 07:00-12:00", "07:00", "12:00"),
    ("KZ indices NY AM 08:30-11:00", "08:30", "11:00"),
    ("KZ indices NY PM 13:30-16:00", "13:30", "16:00"),
    ("Silver Bullet 10:00-11:00", "10:00", "11:00"),
    ("08:30-12:00 (attested quote)", "08:30", "12:00"),
    ("09:30-11:00 (NY AM classic)", "09:30", "11:00"),
    ("08:00-12:00", "08:00", "12:00"),
    ("09:30-12:00", "09:30", "12:00"),
]

# 4H opening grids as the corpus states them, expressed as an offset in hours
# from NY local midnight.
GRIDS: dict[str, int] = {
    "futures 02/06/10/14 NY": 2,
    "forex 17/21/01/09 NY": 1,
}


# ── day framing ───────────────────────────────────────────────────────────────
def local_index(df: pd.DataFrame, tz: str) -> pd.DatetimeIndex:
    return df.index.tz_convert(tz)


def session_date(local: pd.DatetimeIndex, anchor_hour: int = 18) -> np.ndarray:
    """Session date for each bar, for a day that opens at `anchor_hour` local.

    The corpus's canonical daily candle opens at 18:00 New York, so a bar at
    18:00 Sunday belongs to Monday's daily candle. Implemented on the naive
    wall clock so a DST transition cannot shift a bar into the wrong day.
    """
    naive = local.tz_localize(None)
    return (naive + pd.Timedelta(hours=24 - anchor_hour)).normalize().values


def core_week_mask(local: pd.DatetimeIndex) -> np.ndarray:
    """Drop the weekly reopen and the weekly close.

    Sunday 18:00-24:00 NY is the week's first thin hours and Friday from 15:00 NY
    is its last; both are structurally unlike a normal session and would flatter
    or damage an evening window for reasons that have nothing to do with the hour
    of day. Everything session-related is reported with and without them.
    """
    dow = local.dayofweek.values
    hr = local.hour.values
    return ~(((dow == 6) & (hr >= 18)) | ((dow == 4) & (hr >= 15)))


# ── 1. where the daily extremes form ──────────────────────────────────────────
def extreme_formation(m1: pd.DataFrame, tz: str = NY, anchor_hour: int = 18,
                      mask: np.ndarray | None = None) -> pd.DataFrame:
    """Per-hour concentration of daily extremes.

    UNITS, because this is easy to get wrong and was got wrong here once.
    Each session day contributes exactly TWO extreme observations, its high and
    its low. So:

      high_pct / low_pct  share of DAYS whose high (resp. low) prints in that
                          hour. Each column sums to 100 across hours.
      extreme_share       share of all 2*n_days extreme OBSERVATIONS printing in
                          that hour = (high_pct + low_pct) / 2. Sums to 100.

    `extreme_share` is the one to quote and the only one comparable with a
    clock share, because both are then fractions of the same total. Adding
    high_pct and low_pct without halving yields extremes-per-day on a 0-200
    scale, which looks like a percentage, is not one, and overstates
    concentration by exactly 2x when set against a share of the clock.
    """
    df = m1 if mask is None else m1[mask]
    local = local_index(df, tz)
    sd = session_date(local, anchor_hour)
    hr = pd.Series(local.hour.values, index=df.index)

    g = pd.DataFrame({"sd": sd, "hr": hr.values,
                      "high": df["high"].values, "low": df["low"].values},
                     index=df.index)
    hi_hr = g.loc[g.groupby("sd")["high"].idxmax(), "hr"]
    lo_hr = g.loc[g.groupby("sd")["low"].idxmin(), "hr"]
    n_days = g["sd"].nunique()

    hours = list(range(24))
    out = pd.DataFrame(index=hours)
    out["high_pct"] = [100.0 * (hi_hr == h).sum() / n_days for h in hours]
    out["low_pct"] = [100.0 * (lo_hr == h).sum() / n_days for h in hours]
    out["extreme_share"] = (out["high_pct"] + out["low_pct"]) / 2.0
    out.attrs["n_days"] = n_days
    out.attrs["n_obs"] = 2 * n_days
    return out


def clock_share(n_hours: float, traded_hours: float = 23.0) -> float:
    """Percent of the traded clock occupied by `n_hours`. Hour 17 never trades."""
    return 100.0 * n_hours / traded_hours


# ── the reopen question ───────────────────────────────────────────────────────
def minutes_since_reopen(m1: pd.DataFrame, min_gap: float = 60.0
                         ) -> tuple[np.ndarray, np.ndarray]:
    """Minutes elapsed since the most recent trading halt ended, per bar.

    A "reopen" is the first bar after any gap of `min_gap` minutes or more —
    the 17:00-18:04 daily break and the weekend. Returns (msr, reopen_positions).
    """
    gaps = m1.index.to_series().diff().dt.total_seconds().to_numpy() / 60.0
    reopen_pos = np.flatnonzero(gaps >= min_gap)
    if len(reopen_pos) == 0:
        return np.full(len(m1), np.nan), reopen_pos
    pos = np.arange(len(m1))
    k = np.searchsorted(reopen_pos, pos, side="right") - 1
    t = m1.index.to_numpy()
    anchor = t[reopen_pos[np.maximum(k, 0)]]
    msr = (t - anchor) / np.timedelta64(1, "m")
    msr = np.where(k >= 0, msr.astype(float), np.nan)
    return msr, reopen_pos


def reopen_diagnostic(m1: pd.DataFrame, tz: str = NY, anchor_hour: int = 18,
                      windows: tuple[int, ...] = (15, 30, 60, 120)
                      ) -> tuple[pd.DataFrame, dict]:
    """Do the first bars after a halt set the day's extreme disproportionately?

    The test that matters: compare the share of EXTREME bars falling within k
    minutes of a reopen against the share of ALL bars that do. If the first bars
    after a halt merely inherit the halt's accumulated repricing, extremes will
    be over-represented there relative to the time the window occupies, and any
    "18:00 kill zone" read off the hour table is a gap artefact rather than a
    behavioural one.
    """
    msr, reopen_pos = minutes_since_reopen(m1)
    local = local_index(m1, tz)
    sd = session_date(local, anchor_hour)
    g = pd.DataFrame({"sd": sd, "high": m1["high"].values,
                      "low": m1["low"].values}, index=m1.index)
    hi_i = g.index.get_indexer(g.groupby("sd")["high"].idxmax())
    lo_i = g.index.get_indexer(g.groupby("sd")["low"].idxmin())
    ext_i = np.concatenate([hi_i, lo_i])
    ext_msr = msr[ext_i]

    rows = []
    for k in windows:
        base = np.nanmean(msr < k)
        obs = np.nanmean(ext_msr < k)
        rows.append({"within_min": k,
                     "pct_of_bars": 100.0 * base,
                     "pct_of_extremes": 100.0 * obs,
                     "lift": obs / base if base else np.nan,
                     "n_extremes": int(np.nansum(ext_msr < k))})
    tab = pd.DataFrame(rows)

    # Size of the repricing across the halt, for context.
    prev_close = m1["close"].to_numpy()[reopen_pos - 1]
    reopen_open = m1["open"].to_numpy()[reopen_pos]
    gap = np.abs(reopen_open - prev_close)
    info = {"n_reopens": len(reopen_pos),
            "median_gap": float(np.median(gap)),
            "mean_gap": float(np.mean(gap)),
            "p90_gap": float(np.quantile(gap, 0.90))}
    return tab, info


def extreme_formation_excluding_reopen(m1: pd.DataFrame, drop_min: int = 30,
                                       tz: str = NY, anchor_hour: int = 18
                                       ) -> pd.DataFrame:
    """Hourly extreme concentration with the first `drop_min` after each halt cut.

    Dropping the bars re-runs the argmax over what is left, so this answers
    "where would the extreme have formed if the reopen window did not count",
    which is the robustness check the raw hour table cannot supply.
    """
    msr, _ = minutes_since_reopen(m1)
    keep = ~(msr < drop_min)
    return extreme_formation(m1, tz=tz, anchor_hour=anchor_hour, mask=keep)


def extreme_formation_halfhour(m1: pd.DataFrame, lo_h: int = 6, hi_h: int = 14,
                               tz: str = NY, anchor_hour: int = 18) -> pd.DataFrame:
    """Half-hour resolution across the hours where the decision actually sits."""
    local = local_index(m1, tz)
    sd = session_date(local, anchor_hour)
    slot = local.hour.values * 2 + (local.minute.values >= 30).astype(int)
    g = pd.DataFrame({"sd": sd, "slot": slot,
                      "high": m1["high"].values, "low": m1["low"].values},
                     index=m1.index)
    hi = g.loc[g.groupby("sd")["high"].idxmax(), "slot"]
    lo = g.loc[g.groupby("sd")["low"].idxmin(), "slot"]
    n = g["sd"].nunique()
    slots = [h * 2 + k for h in range(lo_h, hi_h) for k in (0, 1)]
    out = pd.DataFrame(index=slots)
    out["label"] = [f"{s // 2:02d}:{'30' if s % 2 else '00'}" for s in slots]
    out["high_pct"] = [100.0 * (hi == s).sum() / n for s in slots]
    out["low_pct"] = [100.0 * (lo == s).sum() / n for s in slots]
    out["extreme_share"] = (out["high_pct"] + out["low_pct"]) / 2.0
    return out


# ── 2. where the range is ─────────────────────────────────────────────────────
def hourly_volatility(m1: pd.DataFrame, tz: str = NY, anchor_hour: int = 18,
                      mask: np.ndarray | None = None) -> pd.DataFrame:
    """Per NY hour: M1 bar range, hourly candle range, share of the daily range."""
    df = m1 if mask is None else m1[mask]
    local = local_index(df, tz)
    m1_rng = (df["high"] - df["low"]).values
    hr = local.hour.values

    bar = pd.DataFrame({"hr": hr, "rng": m1_rng})
    g = bar.groupby("hr")["rng"]

    h1 = resample(df, "1h")
    hl = local_index(h1, tz)
    h1 = h1.assign(hr=hl.hour.values, sd=session_date(hl, anchor_hour))
    h1["rng"] = h1["high"] - h1["low"]
    day_rng = h1.groupby("sd").apply(
        lambda d: d["high"].max() - d["low"].min(), include_groups=False)
    h1["day_rng"] = h1["sd"].map(day_rng)
    h1["share"] = 100.0 * h1["rng"] / h1["day_rng"]

    out = pd.DataFrame(index=range(24))
    out["m1_mean_rng"] = g.mean()
    out["m1_median_rng"] = g.median()
    out["h1_mean_rng"] = h1.groupby("hr")["rng"].mean()
    out["pct_of_day_rng"] = h1.groupby("hr")["share"].mean()
    out["n_bars"] = g.size()
    return out


# ── 3. detector firing and follow-through ─────────────────────────────────────
def atr(df: pd.DataFrame, n: int = ATR_LOOKBACK) -> pd.Series:
    """Trailing ATR, shifted so a bar never sees its own range."""
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean().shift(1)


def forward_scores(df: pd.DataFrame, pos: np.ndarray, sign: np.ndarray,
                   r: np.ndarray, horizon: int = HORIZON) -> np.ndarray:
    """Score each event on a symmetric +-1R barrier over the next `horizon` bars.

    Entry is the event bar's close. +1 if the favourable barrier is touched
    first, -1 if the adverse one is, otherwise the mark-to-market close in R.
    When both barriers fall inside one bar the loss is taken — intrabar order is
    unknowable from OHLC and the optimistic assumption is how backtests lie.
    """
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    c = df["close"].to_numpy()
    n = len(df)
    out = np.full(len(pos), np.nan)
    for k in range(len(pos)):
        i, s, rr = pos[k], sign[k], r[k]
        if not np.isfinite(rr) or rr <= 0 or i + 1 >= n:
            continue
        entry = c[i]
        tgt = entry + s * rr
        stp = entry - s * rr
        end = min(n, i + 1 + horizon)
        res = None
        for j in range(i + 1, end):
            hit_stop = (lo[j] <= stp) if s > 0 else (h[j] >= stp)
            hit_tgt = (h[j] >= tgt) if s > 0 else (lo[j] <= tgt)
            if hit_stop:
                res = -1.0
                break
            if hit_tgt:
                res = 1.0
                break
        if res is None:
            res = s * (c[end - 1] - entry) / rr
        out[k] = res
    return out


def collect_events(df15: pd.DataFrame) -> pd.DataFrame:
    """All three primitives as one event table: time, detector, direction sign."""
    pos_of = {t: i for i, t in enumerate(df15.index)}
    rows = []

    c2 = c2_events(df15)
    for t, d in zip(c2["time"], c2["direction"]):
        rows.append(("c2", t, 1 if d == "bullish" else -1))

    ci = cisd_events(df15, level_rule="series_open")
    if len(ci):
        for t, d in zip(ci["confirm_time"], ci["direction"]):
            rows.append(("cisd", t, 1 if d == "bullish" else -1))

    disp = displacement(df15)
    body = (df15["close"] - df15["open"]).to_numpy()
    for t, b in zip(df15.index[disp.values], body[disp.values]):
        if b != 0:
            rows.append(("displacement", t, 1 if b > 0 else -1))

    ev = pd.DataFrame(rows, columns=["detector", "time", "sign"])
    ev["pos"] = ev["time"].map(pos_of)
    return ev.dropna(subset=["pos"]).astype({"pos": int}).reset_index(drop=True)


def score_events(df15: pd.DataFrame, ev: pd.DataFrame, tz: str = NY
                 ) -> pd.DataFrame:
    a = atr(df15).to_numpy()
    ev = ev.copy()
    ev["r"] = a[ev["pos"].to_numpy()]
    ev["score"] = forward_scores(df15, ev["pos"].to_numpy(),
                                 ev["sign"].to_numpy(), ev["r"].to_numpy())
    local = df15.index.tz_convert(tz)
    ev["hour"] = local.hour.values[ev["pos"].to_numpy()]
    ev["dow"] = local.dayofweek.values[ev["pos"].to_numpy()]
    return ev.dropna(subset=["score"])


def hourly_detector_table(df15: pd.DataFrame, ev: pd.DataFrame,
                          tz: str = NY) -> pd.DataFrame:
    """Per hour: firing rate per bar, win rate, expectancy in R, total R."""
    local = df15.index.tz_convert(tz)
    bars = pd.Series(local.hour.values).value_counts().reindex(range(24)).fillna(0)
    out = pd.DataFrame(index=range(24))
    out["bars"] = bars.astype(int)
    g = ev.groupby("hour")
    out["events"] = g.size().reindex(range(24)).fillna(0).astype(int)
    out["fire_pct"] = 100.0 * out["events"] / out["bars"].replace(0, np.nan)
    out["win_pct"] = 100.0 * g["score"].apply(lambda s: (s > 0).mean()).reindex(range(24))
    out["exp_R"] = g["score"].mean().reindex(range(24))
    out["total_R"] = g["score"].sum().reindex(range(24))
    return out


def per_detector_table(ev: pd.DataFrame, windows: list[tuple[str, str, str]],
                       tz: str = NY) -> pd.DataFrame:
    """Expectancy of each detector inside each candidate window."""
    loc = pd.DatetimeIndex(ev["time"].values, tz="UTC").tz_convert(tz)
    mins = loc.hour.values * 60 + loc.minute.values
    rows = []
    for name, s, e in windows:
        sub = ev[minute_mask(mins, s, e)]
        row = {"window": name}
        for det in ("c2", "cisd", "displacement"):
            d = sub[sub["detector"] == det]
            row[f"{det}_n"] = len(d)
            row[f"{det}_R"] = d["score"].mean() if len(d) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ── 4. window comparison ──────────────────────────────────────────────────────
def minute_mask(mins: np.ndarray, start: str, end: str) -> np.ndarray:
    """Membership in [start, end) at true minute resolution.

    Minute resolution matters: the one attested window starts at 08:30, and
    flooring that to 08:00 silently swallows the 08:30 release spike, which is
    the single most active half hour in the whole day.
    """
    if start == end:
        return np.ones(len(mins), dtype=bool)
    lo = int(start[:2]) * 60 + int(start[3:])
    hi = int(end[:2]) * 60 + int(end[3:])
    if hi <= lo:
        hi = 24 * 60
    return (mins >= lo) & (mins < hi)


def window_bar_mask(local: pd.DatetimeIndex, start: str, end: str) -> np.ndarray:
    return minute_mask(local.hour.values * 60 + local.minute.values, start, end)


def crosscheck_against_bars_session(df: pd.DataFrame, tz: str = NY) -> list[str]:
    """Verify `minute_mask` reproduces `bars.session` exactly, for every window.

    `bars.session` is the project's existing session slicer and the one any
    downstream detector will use; this module needs a mask rather than a slice,
    so it reimplements the membership test. Reimplementing a predicate that
    already exists is how two parts of a codebase quietly disagree, so the two
    are asserted equal here rather than assumed equal.
    """
    local = df.index.tz_convert(tz)
    problems = []
    for name, s, e in WINDOWS:
        if s == e:
            continue                              # the null is not a session()
        mine = set(df.index[window_bar_mask(local, s, e)])
        theirs = set(session(df, s, e, tz=tz).index)
        if mine != theirs:
            problems.append(f"{name}: {len(mine ^ theirs)} bars differ")
    return problems


def compare_windows(m1: pd.DataFrame, df15: pd.DataFrame, ev: pd.DataFrame,
                    tz: str = NY, anchor_hour: int = 18,
                    mask1: np.ndarray | None = None,
                    mask15: np.ndarray | None = None) -> pd.DataFrame:
    """Score every candidate window on cost (time) against what it captures.

    `mask1` / `mask15` restrict the denominator to a subset of bars (used for the
    core-week robustness pass). `ev` must already be filtered to match.
    """
    m1 = m1 if mask1 is None else m1[mask1]
    df15 = df15 if mask15 is None else df15[mask15]
    local15 = df15.index.tz_convert(tz)
    local1 = m1.index.tz_convert(tz)
    sd = session_date(local1, anchor_hour)

    g = pd.DataFrame({"sd": sd, "high": m1["high"].values, "low": m1["low"].values},
                     index=m1.index)
    hi_t = g.groupby("sd")["high"].idxmax()
    lo_t = g.groupby("sd")["low"].idxmin()
    n_days = len(hi_t)
    hi_loc = pd.DatetimeIndex(hi_t.values, tz="UTC").tz_convert(tz)
    lo_loc = pd.DatetimeIndex(lo_t.values, tz="UTC").tz_convert(tz)

    m1_rng = (m1["high"] - m1["low"]).values
    total_path = m1_rng.sum()

    ev_loc = pd.DatetimeIndex(ev["time"].values, tz="UTC").tz_convert(tz)
    ev_min = ev_loc.hour.values * 60 + ev_loc.minute.values
    null_exp = ev["score"].mean()

    rows = []
    for name, s, e in WINDOWS:
        bm15 = window_bar_mask(local15, s, e)
        bm1 = window_bar_mask(local1, s, e)
        em = minute_mask(ev_min, s, e)
        sub, rest = ev[em], ev[~em]
        # Welch t of the window's events against everything OUTSIDE it. Comparing
        # against the all-hours null instead would be comparing a set with a
        # superset that contains it, which understates the difference.
        if len(sub) > 1 and len(rest) > 1:
            a, b = sub["score"].to_numpy(), rest["score"].to_numpy()
            t_vs_rest = (a.mean() - b.mean()) / np.sqrt(
                a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        else:
            t_vs_rest = np.nan
        hm = window_bar_mask(hi_loc, s, e)
        lm = window_bar_mask(lo_loc, s, e)
        time_pct = 100.0 * bm15.sum() / len(bm15)
        path_pct = 100.0 * m1_rng[bm1].sum() / total_path
        ev_pct = 100.0 * len(sub) / len(ev)
        rows.append({
            "window": name,
            "time_pct": time_pct,
            "path_pct": path_pct,
            "range_density": path_pct / time_pct,
            "day_hi_pct": 100.0 * hm.sum() / n_days,
            "day_lo_pct": 100.0 * lm.sum() / n_days,
            "extreme_density": (100.0 * (hm.sum() + lm.sum()) / (2 * n_days)) / time_pct,
            "events": len(sub),
            "event_pct": ev_pct,
            "opp_density": ev_pct / time_pct,
            "win_pct": 100.0 * (sub["score"] > 0).mean() if len(sub) else np.nan,
            "exp_R": sub["score"].mean() if len(sub) else np.nan,
            "se_R": (sub["score"].std(ddof=1) / np.sqrt(len(sub))) if len(sub) > 1 else np.nan,
            "edge_vs_null": (sub["score"].mean() - null_exp) if len(sub) else np.nan,
            "t_vs_rest": t_vs_rest,
        })
    return pd.DataFrame(rows)


# ── 5. DST ────────────────────────────────────────────────────────────────────
def dst_comparison(m1: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ny = extreme_formation(m1, tz=NY)
    est = extreme_formation(m1, tz=EST_FIXED)
    vny = hourly_volatility(m1, tz=NY)
    vest = hourly_volatility(m1, tz=EST_FIXED)

    d = m1.index.to_series().diff().dt.total_seconds() / 60
    resume = m1.index[(d >= 60) & (d < 180)]
    stats = {}
    for label, tz in (("America/New_York", NY), ("Etc/GMT+5", EST_FIXED)):
        h = pd.Series(resume.tz_convert(tz).hour)
        vc = h.value_counts()
        stats[label] = {"n": len(h), "modal_hour": int(vc.index[0]),
                        "modal_pct": 100.0 * vc.iloc[0] / len(h),
                        "hist": vc.sort_index().to_dict()}
    cmp_ex = pd.DataFrame({"ny_share": ny["extreme_share"],
                           "est_share": est["extreme_share"]})
    cmp_ex["delta"] = cmp_ex["ny_share"] - cmp_ex["est_share"]
    cmp_v = pd.DataFrame({"ny_m1_rng": vny["m1_mean_rng"],
                          "est_m1_rng": vest["m1_mean_rng"]})
    cmp_v["delta_pct"] = 100.0 * (cmp_v["ny_m1_rng"] - cmp_v["est_m1_rng"]) / cmp_v["est_m1_rng"]
    return cmp_ex, cmp_v, stats


# ── 6. the 4H grid question ───────────────────────────────────────────────────
def grid_quality(m1: pd.DataFrame, offset_h: int, tz: str = NY) -> dict:
    """Sweep-then-reverse quality of 4H candles built on a given opening grid."""
    # Bucket on the NAIVE New York wall clock. Resampling a tz-aware index bins
    # in UTC underneath, so a "4h" grid drifts by an hour across DST and the
    # candles stop opening at the stated local times entirely — which is exactly
    # the mistake this comparison exists to avoid. The cost is that the two
    # DST-transition hours each year are merged or dropped by one bucket; on
    # ~4,700 candles that is noise.
    local = m1.copy()
    local.index = m1.index.tz_convert(tz).tz_localize(None)
    local = local[~local.index.duplicated(keep="first")].sort_index()
    h4 = local.resample("4h", offset=pd.Timedelta(hours=offset_h),
                        label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()

    crt = candle_range_sweep(h4)
    c2 = (crt["swept_high"] | crt["swept_low"]) & ~crt["swept_both"]
    n = len(h4)

    # follow-through: after a one-sided sweep-and-close-back, does the NEXT candle
    # close beyond the C2's OPEN in the reversal direction? That is the corpus's
    # own delivery test, not an invented one.
    nxt_close = h4["close"].shift(-1)
    bull = crt["swept_low"] & ~crt["swept_both"]
    bear = crt["swept_high"] & ~crt["swept_both"]
    ft_bull = (nxt_close > h4["open"])[bull]
    ft_bear = (nxt_close < h4["open"])[bear]
    ft = pd.concat([ft_bull, ft_bear]).dropna()

    rng = (h4["high"] - h4["low"]).replace(0, np.nan)
    body_ratio = ((h4["close"] - h4["open"]).abs() / rng).mean()

    # How many candles straddle the venue's 17:00-18:04 daily break. A grid whose
    # buckets open exactly on the break never has a candle built from two
    # different trading days' worth of flow; a grid that straddles does.
    starts = h4.index.hour.values
    straddle = np.mean([(s < 17) and (s + 4 > 17) for s in starts])

    return {
        "candles": n,
        "c2_pct": 100.0 * c2.sum() / n,
        "sweep_both_pct": 100.0 * crt["swept_both"].sum() / n,
        "expansion_pct": 100.0 * (crt["expansion_up"] | crt["expansion_down"]).sum() / n,
        "inside_pct": 100.0 * crt["inside_bar"].sum() / n,
        "followthrough_pct": 100.0 * ft.mean() if len(ft) else np.nan,
        "ft_n": len(ft),
        "mean_body_ratio": float(body_ratio),
        "straddle_break_pct": 100.0 * straddle,
        "open_hours": sorted(set(starts.tolist())),
    }


# ── rendering ─────────────────────────────────────────────────────────────────
def f(x: float, nd: int = 1) -> str:
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:,.{nd}f}"


def hour_table(df: pd.DataFrame, cols: list[tuple[str, str, int]],
               skip_empty: str | None = None) -> list[str]:
    head = "| NY hour | " + " | ".join(c[1] for c in cols) + " |"
    sep = "|---|" + "|".join(["---:"] * len(cols)) + "|"
    lines = [head, sep]
    for h in df.index:
        if skip_empty and not np.isfinite(df.loc[h, skip_empty]):
            continue
        cells = [f(df.loc[h, c[0]], c[2]) for c in cols]
        lines.append(f"| {int(h):02d} | " + " | ".join(cells) + " |")
    return lines


def main() -> int:
    m1 = load_m1()
    local = local_index(m1, NY)
    print(f"loaded {len(m1):,} M1 bars {m1.index.min()} -> {m1.index.max()}")

    # -- data audit -----------------------------------------------------------
    d = m1.index.to_series().diff().dt.total_seconds() / 60
    gap_counts = d.value_counts()
    contiguous = 100.0 * gap_counts.get(1.0, 0) / (len(m1) - 1)
    hour_bars = pd.Series(local.hour.values).value_counts().reindex(range(24)).fillna(0)
    missing_hours = [h for h in range(24) if hour_bars[h] == 0]
    week_gaps = int(((d >= 1000)).sum())
    day_gaps = int(((d >= 60) & (d < 180)).sum())
    other_gaps = int(((d > 1) & (d < 60)).sum())

    core = core_week_mask(local)

    df15_probe = resample(m1, EXEC_TF)
    xcheck = crosscheck_against_bars_session(df15_probe)
    print("session() cross-check:", "OK" if not xcheck else xcheck)

    # -- 1. extremes ----------------------------------------------------------
    ex18 = extreme_formation(m1, anchor_hour=18)
    ex00 = extreme_formation(m1, anchor_hour=0)
    ex_core = extreme_formation(m1, anchor_hour=18, mask=core)
    ex_hh = extreme_formation_halfhour(m1)
    reopen_tab, reopen_info = reopen_diagnostic(m1)
    ex_noreopen = extreme_formation_excluding_reopen(m1, REOPEN_DROP_MIN)
    print(f"reopen lift (15m): {reopen_tab.iloc[0]['lift']:.2f}x  "
          f"hour18 {ex18.loc[18, 'extreme_share']:.1f}% -> "
          f"{ex_noreopen.loc[18, 'extreme_share']:.1f}%")

    # -- 2. volatility --------------------------------------------------------
    vol = hourly_volatility(m1)
    vol_core = hourly_volatility(m1, mask=core)

    # -- 3. detectors ---------------------------------------------------------
    df15 = resample(m1, EXEC_TF)
    print(f"{EXEC_TF} bars: {len(df15):,} — running detectors")
    ev = collect_events(df15)
    print(f"raw events: {len(ev):,}")
    ev = score_events(df15, ev)
    print(f"scored events: {len(ev):,}")
    det_hr = hourly_detector_table(df15, ev)

    ev_core = ev[~(((ev["dow"] == 6) & (ev["hour"] >= 18)) |
                   ((ev["dow"] == 4) & (ev["hour"] >= 15)))]
    det_hr_core = hourly_detector_table(
        df15[core_week_mask(df15.index.tz_convert(NY))], ev_core)

    # -- 4. windows -----------------------------------------------------------
    core15 = core_week_mask(df15.index.tz_convert(NY))
    win = compare_windows(m1, df15, ev)
    win_core = compare_windows(m1, df15, ev_core, mask1=core, mask15=core15)
    per_det = per_detector_table(ev, WINDOWS)

    # -- 5. DST ---------------------------------------------------------------
    dst_ex, dst_vol, dst_stats = dst_comparison(m1)

    # -- 6. grids -------------------------------------------------------------
    grids = {name: grid_quality(m1, off) for name, off in GRIDS.items()}

    # -- write ----------------------------------------------------------------
    L: list[str] = []
    A = L.append

    A("# Fitting the `session` gate — XAUUSD, New York clock")
    A("")
    A(f"Source: `m3_scalper/xau_m1_3y.parquet` — {len(m1):,} M1 bars, "
      f"{m1.index.min():%Y-%m-%d} to {m1.index.max():%Y-%m-%d}, tz-aware UTC. "
      f"Generated by `python/fit_session_window.py`. Offline, no network.")
    A("")
    A("`session` gates **68 concepts**, more than any other undefined term in "
      "`meta/automation_gaps.md`. The corpus answers the timezone (New York); "
      "the hours are the open question. This document turns the gate into a "
      "fitted default plus a sweep range, by measuring what gold actually does "
      "by New York hour.")
    A("")
    A("**A correction to the project's own record, up front.** `RESUME.md` "
      "finding #8 reads *\"session / kill-zone HOURS ARE NEVER STATED. Settled "
      "negative\"*, with the 08:30-12:00 quote as the widest usable claim. That "
      "is too strong. `concepts/time/killzones.yaml` records two **complete** "
      "kill-zone grids, and they were verified for this document against "
      "`raw/transcripts/MPeeE55rNOw.txt` rather than taken on trust:")
    A("")
    A("| grid | Asia | London | New York AM | fourth window |")
    A("|---|---|---|---|---|")
    A("| forex | 20:00-00:00 | 02:00-05:00 | 07:00-10:00 | London Close 10:00-12:00 |")
    A("| indices | 20:00-00:00 | 02:00-05:00 | 08:30-11:00 | New York PM 13:30-16:00 |")
    A("")
    A("All eight windows are present verbatim in that transcript, and the same "
      "video states the timezone (*\"all the time shown here are in New York "
      "time so that is EST or Eastern Standard Time\"*) and, importantly, "
      "addresses daylight saving directly — resolving it by setting "
      "TradingView's timezone selector to New York, which is a DST-aware "
      "selector. Section 5 confirms that operational reading empirically.")
    A("")
    A("**Provenance, graded — because this is weaker than it first looks.** "
      "MPeeE55rNOw is a solo instructional video walking through a PDF, so the "
      "windows are in TTrades' own voice within it; the concept file's "
      "`voice: mixed` tag comes from merging that unit with two guest-heavy "
      "units (Trader T, Ben, $niper), not from the windows themselves. But this "
      "is **taught convention presented in a lesson, not a rule he is narrated "
      "applying to his own entries**, it appears in essentially one video, and "
      "the concept is filed `contested`. That places it below a rule he repeats "
      "as his own gate and well above convention imported from outside the "
      "channel. The **Asian window is the one externally contested** — "
      "`meta/external_crossref.md` records outside sources disagreeing on it, "
      "and it is the only one of the eight where this data also finds nothing "
      "(section 4). The other three sessions match public ICT convention, with "
      "only minor variation on the forex New York AM bound — see the provenance "
      "grades at the end of this document for the per-window detail.")
    A("")
    A("So the corpus does supply candidate windows. It does not supply evidence "
      "that they work, and *\"volatility is higher\"* is asserted in that video "
      "and never measured. That is what the rest of this document does.")
    A("")
    A("## Headline")
    A("")

    # placeholders filled after tables are computed below (written inline later)
    headline_at = len(L)

    A("")
    A("## 0. The data, and where its holes are")
    A("")
    A(f"XAUUSD is not a 24h instrument. In this dataset the week runs **Sunday "
      f"18:00 NY to Friday 17:00 NY**, with a **daily break from 17:00 to ~18:04 "
      f"NY**. New York hour **17 contains zero bars** across the whole three "
      f"years; every other hour is essentially complete.")
    A("")
    A("| fact | value |")
    A("|---|---:|")
    A(f"| M1 bars | {len(m1):,} |")
    A(f"| consecutive-minute steps | {contiguous:.2f}% |")
    A(f"| daily-break gaps (60-180 min) | {day_gaps} |")
    A(f"| weekend gaps (>16h) | {week_gaps} |")
    A(f"| other intra-week gaps (2-59 min) | {other_gaps} |")
    A(f"| NY hours with no bars at all | {missing_hours} |")
    A(f"| session days (18:00-anchored) | {ex18.attrs['n_days']} |")
    A(f"| window membership agrees with `bars.session` | "
      f"{'yes, all ' + str(len(WINDOWS) - 1) + ' windows' if not xcheck else xcheck} |")
    A("")
    A("**How gaps are handled.** Nothing is forward-filled — `bars.resample` "
      "drops empty buckets rather than inventing flat candles, so an hourly or "
      "4H bucket spanning the break is built from the minutes that actually "
      "traded. Forward-return scoring walks bar positions, not wall clock, so an "
      "event late in the session is scored against the next bars that exist, "
      "which for a 16:5x event means bars on the far side of the break. That is "
      "a real limitation of the 16:00 row and it is why the recommendation below "
      "does not lean on the last hour of the session.")
    A("")
    A("Two day framings are reported because the corpus is contested on the "
      "daily open: **18:00-anchored** (the corpus's canonical daily candle, and "
      "the primary framing here) and **midnight NY**. All hours below are New "
      "York local unless stated.")
    A("")

    A("## 1. Where the day's high and low actually form")
    A("")
    A(f"18:00-anchored day, M1 resolution, {ex18.attrs['n_days']} session days = "
      f"**{ex18.attrs['n_obs']:,} extreme observations** (one high and one low "
      f"per day).")
    A("")
    A("**Units, stated once and used throughout.** `day high %` and `day low %` "
      "are shares of *days* and each column sums to 100. **`share of extremes`** "
      "is the share of all "
      f"{ex18.attrs['n_obs']:,} extreme *observations* printing in that hour — "
      "it is `(high% + low%) / 2`, sums to 100, and is the only one of the three "
      "directly comparable with a share of the clock. Adding the high and low "
      "columns without halving gives extremes-per-day on a 0-200 scale; that "
      "number looks like a percentage, is not one, and doubles the apparent "
      "concentration when set against a clock share. Every comparison below uses "
      "`share of extremes`.")
    A("")
    L += hour_table(ex18, [("high_pct", "day high %", 1),
                           ("low_pct", "day low %", 1),
                           ("extreme_share", "share of extremes %", 1)])
    A("")
    top = ex18["extreme_share"].sort_values(ascending=False)
    am_block = ex18.loc[8:11, "extreme_share"].sum()
    am_block_930_11 = ex18.loc[9:10, "extreme_share"].sum()
    lon_block = ex18.loc[2:4, "extreme_share"].sum()
    asia_block = ex18.loc[20:23, "extreme_share"].sum()
    am_lift = am_block / clock_share(4)
    A(f"Top hours by share of extremes: " + ", ".join(
        f"**{int(h):02d}** ({v:.1f}%)" for h, v in top.head(5).items()) +
      f". A uniform hour would hold {clock_share(1):.1f}%.")
    A("")
    A(f"The 08:00-11:59 block holds **{am_block:.1f}%** of all extreme "
      f"observations against a clock share of {clock_share(4):.1f}% (four of the "
      f"23 traded hours) — a lift of **{am_lift:.2f}x**. The narrow 09:30-11:00 "
      f"core (hours 09-10) holds {am_block_930_11:.1f}% on {clock_share(2):.1f}% "
      f"of the clock ({am_block_930_11 / clock_share(2):.2f}x). London 02-04 "
      f"holds {lon_block:.1f}% ({lon_block / clock_share(3):.2f}x) and Asia "
      f"20-23 holds {asia_block:.1f}% ({asia_block / clock_share(4):.2f}x).")
    A("")
    A("### Half-hour resolution, 06:00-13:59")
    A("")
    A(f"Same units. A uniform half hour would hold {clock_share(0.5):.1f}%.")
    A("")
    A("| NY slot | day high % | day low % | share of extremes % |")
    A("|---|---:|---:|---:|")
    for s in ex_hh.index:
        A(f"| {ex_hh.loc[s, 'label']} | {ex_hh.loc[s, 'high_pct']:.1f} | "
          f"{ex_hh.loc[s, 'low_pct']:.1f} | {ex_hh.loc[s, 'extreme_share']:.1f} |")
    A("")
    A(f"**The single densest hour is not in the New York morning. It is hour 18 "
      f"({ex18.loc[18, 'extreme_share']:.1f}%), the reopen hour** — ahead of "
      f"hour 10 ({ex18.loc[10, 'extreme_share']:.1f}%) and hour 09 "
      f"({ex18.loc[9, 'extreme_share']:.1f}%). Hour 16 "
      f"({ex18.loc[16, 'extreme_share']:.1f}%) is also elevated despite having "
      f"the lowest minute-bar range of the entire day (section 2), which is the "
      f"tell that something non-behavioural is at work. Two candidate mechanisms "
      f"— a day-boundary artefact and a market-reopen artefact — are separated "
      f"in the next two subsections. **Neither survives as a tradeable "
      f"finding.**")
    A("")
    A("### Control 1: re-anchor the day (tests the boundary artefact)")
    A("")
    A("The maximum of a near-random walk is most likely at the *ends* of the "
      "window it is measured over — the arcsine law. Hours 18 and 16 are the "
      "first and last hours of the 18:00-anchored day, so both are suspect. "
      "Change the anchor and a boundary artefact must move with it, while a real "
      "intraday concentration must stay put.")
    A("")
    L += hour_table(ex00, [("extreme_share", "share of extremes %", 1)])
    A("")
    A(f"Midnight-anchored, the humps relocate to the new boundaries — hour 00 "
      f"({ex00.loc[0, 'extreme_share']:.1f}%) and hour 23 "
      f"({ex00.loc[23, 'extreme_share']:.1f}%) — while 08-11 holds "
      f"{ex00.loc[8:11, 'extreme_share'].sum():.1f}% against "
      f"{am_block:.1f}% on the 18:00 anchor. **The New York morning "
      f"concentration is anchor-invariant; the boundary peaks are not.**")
    A("")
    A(f"But note hour 18 does *not* fully collapse: it still holds "
      f"{ex00.loc[18, 'extreme_share']:.1f}% when it is mid-day rather than a "
      f"boundary, against {clock_share(1):.1f}% uniform. So the boundary artefact "
      f"explains part of hour 18 and not all of it. The remainder is the reopen.")
    A("")
    A("### Control 2: the market reopen (tests the gap artefact)")
    A("")
    A(f"XAUUSD halts 17:00-18:04 NY daily and over the weekend. The first bars "
      f"after a halt absorb whatever repriced while the market was shut, so they "
      f"can set a session extreme mechanically rather than informatively. "
      f"Counting every halt of 60 minutes or more — daily breaks, weekends and "
      f"the handful of holiday closes — there are "
      f"**{reopen_info['n_reopens']} reopens**, with a median repricing across "
      f"the halt of ${reopen_info['median_gap']:.2f} and a 90th percentile of "
      f"${reopen_info['p90_gap']:.2f} (the tail is the weekend gaps).")
    A("")
    A("The test compares the share of extreme bars falling within k minutes of a "
      "reopen against the share of all bars that do — if the two match, the "
      "reopen window is unremarkable:")
    A("")
    A("| within k min of a reopen | % of all bars | % of all extremes | lift | n extremes |")
    A("|---:|---:|---:|---:|---:|")
    for _, r in reopen_tab.iterrows():
        A(f"| {int(r['within_min'])} | {r['pct_of_bars']:.2f} | "
          f"{r['pct_of_extremes']:.2f} | **{r['lift']:.2f}x** | "
          f"{int(r['n_extremes']):,} |")
    A("")
    r15 = reopen_tab.iloc[0]
    A(f"**Confirmed: it is a gap artefact.** The first {int(r15['within_min'])} "
      f"minutes after a halt are {r15['lift']:.1f}x over-represented among daily "
      f"extremes relative to the time they occupy — far above the "
      f"{am_lift:.2f}x of the entire New York morning, and produced by a window "
      f"lasting a quarter of an hour. That is the signature of extremes being "
      f"set by the reopening print, not by anything a trader could act on: the "
      f"level is already made by the time the window is observable.")
    A("")
    A(f"Re-running the hour table with the first {REOPEN_DROP_MIN} minutes after "
      f"every halt removed:")
    A("")
    L += hour_table(ex_noreopen, [("extreme_share", "share of extremes %", 1)])
    A("")
    A(f"Hour 18 falls from **{ex18.loc[18, 'extreme_share']:.1f}%** to "
      f"**{ex_noreopen.loc[18, 'extreme_share']:.1f}%**, while the 08:00-11:59 "
      f"block moves only from {am_block:.1f}% to "
      f"{ex_noreopen.loc[8:11, 'extreme_share'].sum():.1f}% "
      f"({ex_noreopen.loc[8:11, 'extreme_share'].sum() / clock_share(4):.2f}x, "
      f"against {am_lift:.2f}x before). **The 18:00 peak is the reopen; the New "
      f"York morning is not.**")
    A("")
    A("Two things follow, and the second is the one that matters for anyone "
      "reading the hour table on its own. First, the New York morning result is "
      "robust to both controls and is the finding this document rests on. "
      "Second, **do not build an 18:00 NY kill zone out of row 18.** It is a "
      "market-reopen gap wearing the costume of a session. The corpus's 18:00 "
      "daily open is a legitimate *anchor* for framing a daily candle — that is "
      "what `day_anchor_hour: 18` is for — but it is not evidence of a "
      "tradeable 18:00 window, and this data offers none.")
    A("")
    A("### Excluding the weekly open and close")
    A("")
    A("Dropping Sunday 18:00-24:00 and Friday from 15:00 NY:")
    A("")
    L += hour_table(ex_core, [("extreme_share", "share of extremes % (core week)", 1)])
    A("")
    A(f"The 08:00-11:59 block holds "
      f"{ex_core.loc[8:11, 'extreme_share'].sum():.1f}% here "
      f"({ex_core.loc[8:11, 'extreme_share'].sum() / clock_share(4):.2f}x), "
      f"against {am_block:.1f}% ({am_lift:.2f}x) on the full week — the result "
      f"does not depend on the weekly open or close.")
    A("")

    A("## 2. Where the range is")
    A("")
    A("`m1 mean/median range` is the average high-low of a one-minute bar in "
      "that hour, in dollars. `% of day range` is the hourly candle's range as a "
      "share of that session day's full range, averaged over days — it sums to "
      "well over 100% because hourly ranges overlap.")
    A("")
    L += hour_table(vol, [("m1_mean_rng", "m1 mean rng", 3),
                          ("m1_median_rng", "m1 median rng", 3),
                          ("h1_mean_rng", "1h mean rng", 2),
                          ("pct_of_day_rng", "% of day range", 1),
                          ("n_bars", "m1 bars", 0)])
    A("")
    peak = vol["m1_mean_rng"].idxmax()
    trough = vol["m1_mean_rng"].dropna().idxmin()
    A(f"Peak minute-bar range is hour **{int(peak):02d}** "
      f"({vol.loc[peak, 'm1_mean_rng']:.3f}), trough is hour "
      f"**{int(trough):02d}** ({vol.loc[trough, 'm1_mean_rng']:.3f}) — a ratio "
      f"of **{vol.loc[peak, 'm1_mean_rng'] / vol.loc[trough, 'm1_mean_rng']:.2f}x**. "
      f"Volatility concentration is the one place where time-of-day is not "
      f"subtle.")
    A("")
    A("Core week only (Sunday evening and Friday afternoon dropped):")
    A("")
    L += hour_table(vol_core, [("m1_mean_rng", "m1 mean rng", 3),
                               ("pct_of_day_rng", "% of day range", 1)])
    A("")

    A("## 3. Where the corpus's own primitives fire, and where they pay")
    A("")
    A(f"Detectors run on **{EXEC_TF}** bars ({len(df15):,} bars): "
      f"`c2_events` (sweep of the prior candle's extreme with a close back "
      f"inside), `cisd_events` with `level_rule=\"series_open\"`, and "
      f"`displacement` (body > 2x the trailing 20-bar mean body, direction taken "
      f"from the body's sign).")
    A("")
    A("**Follow-through measure.** Each event is entered at its own close and "
      "scored on a symmetric +/-1R barrier over the next "
      f"{HORIZON} bars (= {HORIZON * 15 // 60}h), with R = trailing "
      f"ATR({ATR_LOOKBACK}) shifted one bar so a bar never sizes itself. "
      "Target-first scores +1, stop-first -1, neither the mark-to-market close "
      "in R. Both barriers inside one bar is scored as the loss. Costs are not "
      "modelled: a gold spread is roughly hour-invariant except in the thin "
      "hours, so the Asia rows below are flattered by an amount this table "
      "cannot see.")
    A("")
    A(f"Total scored events: **{len(ev):,}** "
      f"({', '.join(f'{k}: {v:,}' for k, v in ev['detector'].value_counts().items())}).")
    A("")
    L += hour_table(det_hr, [("bars", f"{EXEC_TF} bars", 0),
                             ("events", "events", 0),
                             ("fire_pct", "fire %/bar", 1),
                             ("win_pct", "win %", 1),
                             ("exp_R", "exp R", 3),
                             ("total_R", "total R", 1)], skip_empty="exp_R")
    A("")
    best = det_hr["exp_R"].dropna().sort_values(ascending=False)
    worst = best.tail(4)
    A("Best hours by expectancy: " + ", ".join(
        f"**{int(h):02d}** ({v:+.3f}R)" for h, v in best.head(5).items()) + ".")
    A("Worst: " + ", ".join(
        f"{int(h):02d} ({v:+.3f}R)" for h, v in worst.items()) + ".")
    A("")
    A(f"Spread between the best and worst hour is "
      f"**{best.iloc[0] - best.iloc[-1]:.3f}R**, on a per-hour sample of "
      f"{int(det_hr['events'].median()):,} events (median). Firing rate and "
      f"expectancy are **not** the same ranking, which is the whole point of "
      f"measuring both — an hour that produces plenty of C2s and CISDs is not "
      f"automatically an hour where they resolve.")
    A("")
    A("Core week only (Sunday evening and Friday afternoon dropped):")
    A("")
    L += hour_table(det_hr_core, [("events", "events", 0),
                                  ("win_pct", "win %", 1),
                                  ("exp_R", "exp R", 3)], skip_empty="exp_R")
    A("")

    A("## 4. Candidate windows")
    A("")
    A("`time %` is the share of traded 15m bars inside the window — the cost of "
      "the gate. `path %` is the share of total minute-bar range travelled, and "
      "`range dens` is that divided by `time %`. `extr dens` does the same for "
      "daily extremes, `opp dens` for detector events. Above 1.00 means the "
      "window is denser than the clock alone would give it. `vs null` is the "
      "window's expectancy minus the all-hours expectancy, and `+/-se` is the "
      "standard error of the window's own expectancy.")
    A("")
    A("A raw \"total R captured\" column is deliberately **not** reported: every "
      "window's expectancy is negative, so such a column would rank a window "
      "highly for capturing more of the *losses*.")
    A("")
    A("| window | time % | path % | range dens | day hi % | day lo % | extr dens | events | opp dens | win % | exp R | +/-se | vs null | t vs rest |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in win.iterrows():
        A(f"| {r['window']} | {r['time_pct']:.1f} | {r['path_pct']:.1f} | "
          f"{r['range_density']:.2f} | {r['day_hi_pct']:.1f} | {r['day_lo_pct']:.1f} | "
          f"{r['extreme_density']:.2f} | {int(r['events']):,} | "
          f"{r['opp_density']:.2f} | {f(r['win_pct'])} | {f(r['exp_R'], 3)} | "
          f"{f(r['se_R'], 3)} | {f(r['edge_vs_null'], 3)} | {f(r['t_vs_rest'], 2)} |")
    A("")
    A("Core week only:")
    A("")
    A("| window | time % | path % | range dens | extr dens | events | win % | exp R | +/-se | vs null | t vs rest |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in win_core.iterrows():
        A(f"| {r['window']} | {r['time_pct']:.1f} | {r['path_pct']:.1f} | "
          f"{r['range_density']:.2f} | {r['extreme_density']:.2f} | "
          f"{int(r['events']):,} | {f(r['win_pct'])} | {f(r['exp_R'], 3)} | "
          f"{f(r['se_R'], 3)} | {f(r['edge_vs_null'], 3)} | {f(r['t_vs_rest'], 2)} |")
    A("")
    def w(name: str) -> pd.Series:
        return win[win["window"] == name].iloc[0]

    lc = w("KZ forex London Close 10:00-12:00")
    fxam = w("KZ forex NY AM 07:00-10:00")
    ixam = w("KZ indices NY AM 08:30-11:00")
    dom = w("09:30-12:00")
    early = w("08:00-12:00")
    n_tested = len(win) - 1
    bonf = 2.9

    A("### What the table actually says")
    A("")
    A(f"**1. Density is real; edge is almost entirely noise.** The density "
      f"columns move by factors — `extr dens` runs from "
      f"{win['extreme_density'].min():.2f} (London) to "
      f"{win['extreme_density'].max():.2f} (09:30-11:00) — while the expectancy "
      f"column barely moves at all. With {n_tested} windows tested, a "
      f"Bonferroni-style threshold is about |t| = {bonf:.1f}. **Exactly one "
      f"window clears it, and it clears it in the wrong direction.**")
    A("")
    A(f"**2. The one significant session effect on gold is negative, and it "
      f"lands on the corpus's own New York AM kill zone.** `KZ forex NY AM "
      f"07:00-10:00` returns {fxam['exp_R']:+.3f}R against the rest of the day, "
      f"t = {fxam['t_vs_rest']:.2f} on {int(fxam['events']):,} events — the only "
      f"result in the table that survives correcting for how many windows were "
      f"tried. `KZ indices NY AM 08:30-11:00` points the same way "
      f"({ixam['exp_R']:+.3f}R, t = {ixam['t_vs_rest']:.2f}), as does "
      f"`08:00-12:00` (t = {early['t_vs_rest']:.2f}). Both of the corpus's "
      f"New York AM windows are, on XAUUSD, **worse than average places to act "
      f"on one of these primitives** — while being better than average places "
      f"for the day's extreme to form. Those two facts are not in tension; they "
      f"are the same fact seen from two sides.")
    A("")
    A(f"**3. The best-scoring window is also corpus-anchored: London Close, "
      f"10:00-12:00.** {lc['exp_R']:+.3f}R (t = {lc['t_vs_rest']:+.2f}), "
      f"{lc['range_density']:.2f}x range density and "
      f"{lc['extreme_density']:.2f}x extreme density on only "
      f"{lc['time_pct']:.1f}% of the clock. It is **not statistically "
      f"significant** — t = {lc['t_vs_rest']:.2f} is nowhere near the "
      f"{bonf:.1f} threshold, and it would not be worth mentioning if it had "
      f"been found by scanning the grid. It is worth mentioning because it was "
      f"**pre-specified**: it is a window the corpus states, that outside "
      f"convention agrees on without dissent, that sits inside the attested "
      f"08:30-12:00 quote, and that contains the Silver Bullet sub-window. Four "
      f"independent reasons to have looked there before seeing the number.")
    A("")
    A(f"**4. And yet 08:30 is where the day's extreme most often prints** — "
      f"{ex_hh.loc[17, 'extreme_share']:.1f}% of all extreme observations in "
      f"that single half hour against {clock_share(0.5):.1f}% of the clock "
      f"({ex_hh.loc[17, 'extreme_share'] / clock_share(0.5):.1f}x), the joint "
      f"highest of the morning (section 1) — inside the hour with the day's "
      f"worst expectancy ({det_hr.loc[8, 'exp_R']:+.3f}R). The release spike "
      f"makes the day's high or low and simultaneously runs anything that "
      f"follows a primitive into it. That pairing is the corpus's own "
      f"'manipulation first' claim showing up as a number, and it is the most "
      f"decision-relevant line in this document: **the best hour to have a "
      f"level and the best hour to take an entry are not the same hour.**")
    A("")
    A(f"**5. The Asian window — the externally contested one — is the emptiest.** "
      f"`KZ Asia 20:00-00:00` sits at density ~1.0 on every measure "
      f"({w('KZ Asia 20:00-00:00')['range_density']:.2f} range, "
      f"{w('KZ Asia 20:00-00:00')['extreme_density']:.2f} extremes) and "
      f"t = {w('KZ Asia 20:00-00:00')['t_vs_rest']:+.2f}. On gold it is "
      f"indistinguishable from picking hours at random. The outside "
      f"disagreement about its bounds (20:00-00:00 vs 19:00-22:00 vs "
      f"20:00-23:00, per `meta/external_crossref.md`) is therefore not worth "
      f"resolving for this instrument — there is nothing there to get right.")
    A("")
    A("### By detector")
    A("")
    A("| window | c2 n | c2 R | cisd n | cisd R | disp n | disp R |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for _, r in per_det.iterrows():
        A(f"| {r['window']} | {int(r['c2_n']):,} | {f(r['c2_R'], 3)} | "
          f"{int(r['cisd_n']):,} | {f(r['cisd_R'], 3)} | "
          f"{int(r['displacement_n']):,} | {f(r['displacement_R'], 3)} |")
    A("")

    A("## 5. DST — is `EST` literal, or New York local?")
    A("")
    A("This is decidable without any theory, because the venue's own daily break "
      "is a fixed wall-clock event. If the broker clock is Eastern-with-DST the "
      "break resumes at the same local hour all year; if it is fixed UTC-5 it "
      "smears across two hours.")
    A("")
    A("| clock | break resumes at modal hour | share of breaks at that hour | histogram |")
    A("|---|---:|---:|---|")
    for label, s in dst_stats.items():
        A(f"| {label} | {s['modal_hour']:02d}:00 | {s['modal_pct']:.1f}% | "
          f"{s['hist']} |")
    A("")
    A("**Verdict: use `America/New_York` (Eastern with DST), not fixed UTC-5.** "
      "The venue clock is unambiguous. But the more useful question is whether "
      "the difference is *material* for anything downstream:")
    A("")
    A("| NY hour | extremes % (NY) | extremes % (UTC-5) | delta pp | m1 rng (NY) | m1 rng (UTC-5) | delta % |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for h in range(24):
        A(f"| {h:02d} | {f(dst_ex.loc[h, 'ny_share'])} | "
          f"{f(dst_ex.loc[h, 'est_share'])} | {f(dst_ex.loc[h, 'delta'])} | "
          f"{f(dst_vol.loc[h, 'ny_m1_rng'], 3)} | "
          f"{f(dst_vol.loc[h, 'est_m1_rng'], 3)} | "
          f"{f(dst_vol.loc[h, 'delta_pct'])} |")
    A("")
    ex_nb = dst_ex.drop(index=17)["delta"].abs()          # hour 17 is the break
    vol_nb = dst_vol.drop(index=17)["delta_pct"].abs()
    max_dpp, max_dpp_h = ex_nb.max(), int(ex_nb.idxmax())
    max_dv, max_dv_h = vol_nb.max(), int(vol_nb.idxmax())
    A(f"Hour 17 is excluded from the summary of that table: under fixed UTC-5 the "
      f"venue's daily break lands there for half the year, so its "
      f"{dst_ex.loc[17, 'delta']:.1f}pp gap measures the misalignment itself "
      f"rather than any market behaviour. Of the remaining hours, the largest "
      f"extreme-formation difference is **{max_dpp:.1f} percentage points** at "
      f"hour {max_dpp_h:02d} and the largest minute-range difference is "
      f"**{max_dv:.1f}%** at hour {max_dv_h:02d}. Those are not negligible — "
      f"picking the wrong clock moves the boundary of any 08:00 or 12:00 gate by "
      f"a full hour for roughly eight months of the year, which is why this "
      f"question had to be settled rather than waved through.")
    A("")

    A("## 6. The 4H opening grid for gold")
    A("")
    A("The corpus gives two grids and says the 09:30 open \"doesn't really "
      "apply\" to forex. Gold is neither. Both grids are built on NY-local time "
      "and compared on the behaviour the methodology cares about: a one-sided "
      "sweep of the prior 4H candle that closes back inside (`C2 %`), and "
      "whether the **next** 4H candle then closes beyond that candle's open "
      "(`follow-through %`, the corpus's own delivery test). `inside %` and "
      "`sweep-both %` are range-splitting symptoms — a grid that dices a move "
      "produces more of both.")
    A("")
    A("| grid | open hours | candles | C2 % | follow-through % | ft n | sweep-both % | expansion % | inside % | mean body/range | straddles the daily break % |")
    A("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, g in grids.items():
        A(f"| {name} | {'/'.join(f'{h:02d}' for h in g['open_hours'])} | "
          f"{g['candles']:,} | {g['c2_pct']:.1f} | {g['followthrough_pct']:.1f} | "
          f"{g['ft_n']:,} | {g['sweep_both_pct']:.1f} | {g['expansion_pct']:.1f} | "
          f"{g['inside_pct']:.1f} | {g['mean_body_ratio']:.3f} | "
          f"{g['straddle_break_pct']:.1f} |")
    A("")

    fut = grids["futures 02/06/10/14 NY"]
    fx = grids["forex 17/21/01/09 NY"]
    ft_gap = fx["followthrough_pct"] - fut["followthrough_pct"]
    c2_gap = fx["c2_pct"] - fut["c2_pct"]
    grid_winner = ("forex 17/21/01/09 NY" if ft_gap > 0 else "futures 02/06/10/14 NY")
    grid_offset = 1 if grid_winner.startswith("forex") else 2
    # significance sanity check on the follow-through difference (two proportions)
    p1, n1 = fx["followthrough_pct"] / 100, fx["ft_n"]
    p2, n2 = fut["followthrough_pct"] / 100, fut["ft_n"]
    pp = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else np.nan

    A(f"**Verdict for gold: the {grid_winner} grid, weakly.** It shows a "
      f"{abs(ft_gap):.1f}pp higher sweep-then-reverse follow-through "
      f"({fx['followthrough_pct']:.1f}% vs {fut['followthrough_pct']:.1f}%) and a "
      f"{abs(c2_gap):.1f}pp higher C2 rate. That difference is **not "
      f"statistically meaningful**: a two-proportion z on the follow-through "
      f"rates gives z = {z:.2f} on {fx['ft_n']:,} and {fut['ft_n']:,} events. On "
      f"candle statistics alone the two grids are indistinguishable.")
    A("")
    A(f"**The tiebreak is structural, and it is one-sided.** The venue's daily "
      f"break runs 17:00-18:04 NY. The forex grid opens a candle at 17:00, so "
      f"**{fx['straddle_break_pct']:.1f}%** of its candles are built across the "
      f"break; the futures grid's 14:00-18:00 bucket straddles it, so "
      f"**{fut['straddle_break_pct']:.1f}%** of its candles — one in six — mix "
      f"flow from either side of a one-hour halt. For XAUUSD specifically that "
      f"argues for the **forex grid**, and it is consistent with the corpus's "
      f"own reason for offsetting the forex grid in the first place: the 09:30 "
      f"cash open is not gold's event, the 17:00/18:00 rollover is.")
    A("")
    A(f"Confidence: **low-to-moderate**. The behavioural metrics do not separate "
      f"the grids, so the recommendation rests on the break alignment, which is "
      f"an argument about data hygiene rather than about market structure. "
      f"Sweep both offsets in any backtest that uses a 4H candle.")
    A("")

    # -- headline -------------------------------------------------------------
    rec = win[win["window"] == "08:30-12:00 (attested quote)"].iloc[0]
    null = win[win["window"] == "all-hours (null)"].iloc[0]
    best_win = win.iloc[1:].sort_values("exp_R", ascending=False).iloc[0]

    lc = win[win["window"] == "KZ forex London Close 10:00-12:00"].iloc[0]
    fxam = win[win["window"] == "KZ forex NY AM 07:00-10:00"].iloc[0]
    head: list[str] = []
    head.append(
        "**Recommended default: 10:00-12:00 New York on `America/New_York` — "
        "the corpus's own forex *London Close* kill zone. Conservative "
        "superset: the attested 08:30-12:00.** Sweep `start` over 08:30-10:30 "
        "and `end` over 11:00-13:00.")
    head.append("")
    head.append(
        f"10:00-12:00 is recommended because it is **pre-specified rather than "
        f"fitted** — the corpus states it (`concepts/time/killzones.yaml`, video "
        f"MPeeE55rNOw, verified against the transcript), outside convention "
        f"agrees on it without dissent, it sits inside the attested "
        f"08:30-12:00 quote, and it contains the Silver Bullet sub-window — "
        f"*and* it happens to score best here: {lc['exp_R']:+.3f}R with "
        f"{lc['range_density']:.2f}x range density and "
        f"{lc['extreme_density']:.2f}x daily-extreme density on "
        f"{lc['time_pct']:.1f}% of the traded clock. Its edge over the rest of "
        f"the day is **not** statistically significant (t = "
        f"{lc['t_vs_rest']:+.2f}); the four independent reasons to have looked "
        f"there before seeing the number are what make it a defensible default "
        f"rather than the best cell in a grid search.")
    head.append("")
    head.append(
        f"**Evidence strength, graded honestly — the two halves of the question "
        f"give opposite answers.** *Strong* for opportunity: the 08:00-11:59 "
        f"block carries **{am_block:.1f}% of all daily-extreme observations** on "
        f"{clock_share(4):.1f}% of the traded clock — a **{am_lift:.2f}x** lift "
        f"that survives re-anchoring the day, survives dropping the weekly open "
        f"and close, and survives excluding the market-reopen window. Minute-bar "
        f"range there peaks at "
        f"{vol['m1_mean_rng'].max() / vol['m1_mean_rng'].min():.1f}x the day's "
        f"trough. *Absent, and where measurable actually negative*, for edge: "
        f"the attested window returns {rec['exp_R']:+.3f}R "
        f"(+/-{rec['se_R']:.3f}) against an all-hours null of "
        f"{null['exp_R']:+.3f}R.")
    head.append("")
    head.append(
        f"**So be blunt: for gold, time-of-day buys opportunity, not accuracy — "
        f"and the New York AM kill zone actively costs accuracy.** Across "
        f"{len(win) - 1} windows the only result that survives correcting for "
        f"multiple testing is **negative**: the corpus's forex New York AM kill "
        f"zone (07:00-10:00) returns {fxam['exp_R']:+.3f}R against the rest of "
        f"the day, t = {fxam['t_vs_rest']:.2f} on {int(fxam['events']):,} "
        f"events. Hour 08 is the day's worst at {det_hr.loc[8, 'exp_R']:+.3f}R "
        f"while 08:30 is simultaneously the half hour where the day's extreme "
        f"most often prints ({ex_hh.loc[17, 'extreme_share']:.1f}% of all "
        f"extremes, {ex_hh.loc[17, 'extreme_share'] / clock_share(0.5):.1f}x "
        f"its clock share). **The best "
        f"half hour to have a level is not the best half hour to take an "
        f"entry.** A session gate is defensible as a liquidity and range filter "
        f"— trade when there is something to trade, size against a known range "
        f"— and is not defensible as an edge. Anything in the corpus leaning on "
        f"'this must all be done within a kill zone' to explain why a setup "
        f"works is unsupported here. The sign is, however, exactly what the "
        f"corpus's own 'manipulation first' framing predicts.")
    head.append("")
    head.append(
        f"**A trap in the hour table, flagged because it is the most likely way "
        f"to misread this document.** The single densest hour for daily-extreme "
        f"formation is **not** in the New York morning — it is hour 18 NY at "
        f"{ex18.loc[18, 'extreme_share']:.1f}%, ahead of hour 10 at "
        f"{ex18.loc[10, 'extreme_share']:.1f}%. That is the market-reopen hour "
        f"and it is an **artefact**: the first 15 minutes after a trading halt "
        f"are {reopen_tab.iloc[0]['lift']:.1f}x over-represented among daily "
        f"extremes relative to the time they occupy, and excluding the first "
        f"{REOPEN_DROP_MIN} minutes after each halt collapses hour 18 from "
        f"{ex18.loc[18, 'extreme_share']:.1f}% to "
        f"{ex_noreopen.loc[18, 'extreme_share']:.1f}% while leaving the "
        f"08:00-11:59 block untouched "
        f"({am_block:.1f}% to "
        f"{ex_noreopen.loc[8:11, 'extreme_share'].sum():.1f}%). **Do not build "
        f"an 18:00 NY kill zone out of that row** — the level is already made by "
        f"the time the window is observable. Section 1 separates it from the "
        f"day-boundary (arcsine) artefact that also inflates hours 18 and 16.")
    head.append("")
    head.append(
        f"**DST: settled — use `America/New_York`, do not sweep it.** The venue's "
        f"own daily break resumes at 18:00 NY on "
        f"{dst_stats['America/New_York']['modal_pct']:.1f}% of occasions under "
        f"DST-aware Eastern, but splits across two hours "
        f"({dst_stats['Etc/GMT+5']['modal_pct']:.1f}% / rest) under fixed UTC-5. "
        f"The venue clock is DST-aware and the question is closed. It is also "
        f"**material**, not a technicality: outside the break hour the choice "
        f"moves up to {max_dpp:.1f}pp of extreme-formation share and "
        f"{max_dv:.1f}% of minute range between hours.")
    head.append("")
    head.append(
        f"**4H grid: the forex grid (17/21/01/09 NY) for gold, weakly.** The two "
        f"grids are statistically indistinguishable on candle behaviour "
        f"(follow-through {fx['followthrough_pct']:.1f}% vs "
        f"{fut['followthrough_pct']:.1f}%, z = {z:.2f}). The tiebreak is "
        f"structural: the forex grid opens a candle at 17:00 NY, exactly on the "
        f"venue's daily break, so {fx['straddle_break_pct']:.0f}% of its candles "
        f"straddle it against {fut['straddle_break_pct']:.0f}% for the futures "
        f"grid. Confidence: **low-to-moderate** — sweep both.")
    L[headline_at:headline_at] = head

    A("## Recommendation")
    A("")
    A("### Default")
    A("")
    A("```yaml")
    A("session:")
    A("  timezone: America/New_York     # DST-aware; NOT fixed UTC-5")
    A("  start: \"10:00\"                 # KZ forex London Close")
    A("  end:   \"12:00\"                 # 08:30-12:00 = corpus-faithful superset")
    A(f"  htf_grid_offset_hours: {grid_offset}       "
      f"# {grid_winner}")
    A("  day_anchor_hour: 18            # corpus canonical daily open")
    A("```")
    A("")
    A("### Sweep range for any backtest")
    A("")
    A("| knob | sweep | evidence grade | note |")
    A("|---|---|---|---|")
    A("| `start` | 08:30, 09:00, 09:30, 10:00, 10:30 | **moderate** | 08:30 is "
      "the attested lower bound; every start before 09:30 imports the day's "
      "worst-expectancy hour |")
    A("| `end` | 11:00, 12:00, 13:00 | **moderate** | 12:00 is both the attested "
      "and the corpus kill-zone bound; range density has decayed to the daily "
      "mean by 13:00 |")
    A("| `timezone` | `America/New_York` only | **strong** | section 5; the "
      "venue clock settles it. Do not sweep |")
    A(f"| `htf_grid_offset_hours` | {grid_offset} (default), "
      f"{2 if grid_offset == 1 else 1} | **weak** | section 6; behavioural "
      f"metrics do not separate the grids, the tiebreak is break alignment |")
    A("| `day_anchor_hour` | 18 (default), 0 | **weak** | both framings reported; "
      "the choice moves the boundary artefact, not the NY-morning result |")
    A("| 07:00-10:00 as an *entry* window | avoid | **moderate, negative** | the "
      "only multiple-testing-robust result in section 4, and it is negative |")
    A("| gate as *edge* | do not | **negative** | no window beats the all-hours "
      "null by more than noise |")
    A("")
    A("### Provenance grades of the windows themselves")
    A("")
    A("| window | corpus status | outside status | grade |")
    A("|---|---|---|---|")
    A("| London Close 10:00-12:00 | stated, MPeeE55rNOw, `contested` file, "
      "taught convention | no dissent found | **strongest available** |")
    A("| NY AM 07:00-10:00 (forex) | stated, same source | some sites give "
      "08:00-11:00 | good provenance, **bad empirics here** |")
    A("| NY AM 08:30-11:00 (indices) | stated, same source | consistent | good "
      "provenance, bad empirics here |")
    A("| London 02:00-05:00 | stated, same source | consistent | attested, "
      "empirically empty on gold |")
    A("| Asia 20:00-00:00 | stated, same source | **contested** (19:00-22:00, "
      "20:00-23:00 also given) | attested, empirically empty on gold |")
    A("| 08:30-12:00 | TTrades' own voice, but one passing quote, no end-time "
      "rationale | n/a | **the only one in his own voice as a gate** |")
    A("| 09:30-11:00, 08:00-12:00, 09:30-12:00 | not in the corpus | outside "
      "convention / fitted | **weakest — do not cite as corpus** |")
    A("")
    A("None of these is TTrades narrating his own entry gate with a clock "
      "attached, except the 08:30-12:00 quote. Adopting a window because the "
      "corpus teaches it, or because the internet agrees, is a **default for a "
      "knob** and must be labelled as such wherever it is used — not backfilled "
      "into a concept file as though he had stated it.")
    A("")
    A("### What the evidence does and does not support")
    A("")
    A("A session gate on gold is justified by **where the tradeable range is**, "
      "not by a demonstrated per-trade edge. The strong claims this data will "
      "carry: the daily extreme is ~1.7x more likely to print in the New York "
      "morning than the clock alone implies, and that result is invariant to the "
      "day anchor and to dropping the weekly open and close; minute-bar range in "
      "that block is nearly 3x the day's trough. The claim it will **not** carry "
      "is that any of this improves a signal's hit rate. Every candidate window's "
      "follow-through expectancy sits within a few hundredths of an R of the "
      "all-hours null, and the two windows the methodology most favours — both "
      "New York AM readings — sit measurably on the wrong side of it.")
    A("")
    A("Read alongside `meta/primitive_base_rates.md`, where 40-44% of candles "
      "sweep the prior candle's range on every timeframe, the combined message is "
      "unglamorous and worth stating plainly: **the primitives are close to "
      "coin flips and the session gate does not fix that.** A strategy that only "
      "works inside 08:30-12:00 is not being validated by these numbers; it is "
      "being told it has fewer, larger opportunities there. That is still a "
      "reason to use the gate — position sizing and cost per unit of range both "
      "improve — but it is a different reason from the one the corpus implies.")
    A("")
    A("Limitations, stated rather than buried. This is in-sample across three "
      "years of one instrument on one execution timeframe, with no cost model "
      "(which flatters the thin hours where the best expectancies happen to sit) "
      "and one fixed +/-1R, 2-hour scoring rule — a different horizon or an "
      "asymmetric target could reorder the hour table. The event set is three "
      "primitives fired unconditionally, not a strategy: a real setup adds HTF "
      "context, and it is entirely possible that context interacts with hour in "
      "a way an unconditional pass cannot see. The window should be re-fitted, "
      "not inherited, if the instrument, the timeframe or the setup changes.")
    A("")
    A("### What this unblocks")
    A("")
    A("`session` is now a parameter with a default, a provenance grade and a "
      "stated sweep range rather than an undefined gate, which unblocks the "
      "**68 concepts** that cite it in `meta/automation_gaps.md` — including "
      "`average-daily-range`, `chart-timezone-est`, `cisd`, "
      "`irl-erl-flowchart-model`, `killzones`, `new-york-am-session-only`, "
      "`session-cascade`, `daily-profile-session-windows` and the rest of the "
      "`time` category's session-boundary problem. It also settles DST for the "
      "neighbouring `timezone` term (34 concepts) and answers "
      "`po3-four-hour-opening-times` for gold specifically. None of these become "
      "*correct* — they become *decidable*, with the fitted value and its "
      "evidence grade carried explicitly rather than assumed.")
    A("")
    A("One correction should be carried back into `RESUME.md` finding #8 when "
      "someone edits it: **\"the hours are never stated\" is too strong.** The "
      "accurate statement is that *TTrades never states a clock as his own "
      "gating rule*, while the corpus does contain two complete published "
      "kill-zone grids in a taught, `contested`, mixed-voice entry. That "
      "distinction matters, because it is the difference between having no "
      "candidate to test and having eight.")
    A("")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}  ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
