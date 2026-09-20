"""The higher-timeframe bias layer — `meta/ttrades_method_spec.md` §2.

Phase 2 established that every primitive measured in isolation sits near its base
rate (sweeps 40-44%, FVGs in 61-77% of break windows, the C2 wick effect ~0 where
the data has power). The corpus's own claim is that the edge lives in the
**conjunction**: higher-timeframe bias, then a point of interest, then a CISD, then
timing. This module is the first half of that conjunction.

What is implemented, and where it comes from:

* **§2.1 order of operations** — daily bias, then the daily profile which must
  *support* the bias, then entry. The profile gate is the one that surprises: if
  the profile does not support the bias, **the entry is not taken even though the
  bias stands**. Plus the two hard gates: do not drop timeframes until the POI is
  tagged (`poi.py`), and do not fade the current daily candle.
* **§2.2 the draw on liquidity** — previous day high/low over a 3-day lookback,
  and which side is more likely to be taken. No ranking among candidates is ever
  given **[GAP]**, so `draw_rule=` selects between the readings the corpus does
  state.
* **§2.3 the previous-candle engine** — continuation closure / reversal closure /
  both sides taken / inside bar / range-bound.
* **§2.4 daily bias** — previous day high, low and EQ; the reversal-vs-continuation
  binary; and the confirmation gate that is used in every video of the weekly
  profile series: a daily **C2 or C3 closure PLUS an hourly CISD** in the same
  direction. Either alone is explicitly no bias.
* **§2.5 profiles** — the four daily profiles, classified by *where in the day the
  manipulation happens*, and the support gate.
* **§2.6 SMT** — divergence against a correlated asset, subject to the ordering
  doctrine "you find the model and *then* check for SMT".

**Settled in phase 2 — not knobs, do not re-sweep** (`meta/session_window_fit.md`):
timezone is `America/New_York` **with DST**, and gold uses the **forex 4-hour grid
(17/21/01/09 NY)**. Both are constants here with a documented override only so a
test can pin the alternative, never so a fit can wander back onto them.

Every rule the spec marks **[GAP]** or **[P]** is an explicit parameter with a
documented default. Where the spec preserves two readings, both are implemented and
the caller selects.

## Availability — read this before wiring anything downstream

**Every OHLC frame in this project is LEFT-LABELLED** (`bars.resample(label="left")`
and OANDA's own convention alike), so a bar's index timestamp is its **START**. A
bar's information does not exist until its **close**, which is `index + freq`. The
off-by-one in either direction is silent and catastrophic: replaying the signal
candle drives a book to a ~3% win rate, and letting a gate peek at the bar it fires
on manufactures a fake edge that looks like success.

So **every gate here reports an `*_available_at` timestamp**, and downstream entry
code must not open a position on any bar starting before it. What each gate uses:

| gate | information used | available from |
|---|---|---|
| `previous_candle_state` | candle i and i-1; `implied_bias` is for candle **i+1** | close of candle i |
| `draw_on_liquidity` | 3-day extremes shifted back one, plus today's **open** | the day's open |
| `daily_closures` | the candle's own close vs the previous candle | close of that candle |
| `hourly_cisd_in_candle` | LTF bars inside the HTF candle | close of the confirming LTF bar (`confirm_time + ltf_freq`) |
| `daily_bias` | both of the above | `bias_available_at` = max(day's last bar close, CISD bar close) |
| `daily_profile` | Asia/London/NY-am ranges; `outside_day` needs the daily close | `profile_available_at` |
| `alignment_frame` | the last **closed** 4H and hourly candle of the day | `alignment_available_at` |
| `poi_gate` | bars up to the extreme, **plus** `body_hold_bars` forward on the CISD branch (that branch waits by design) | `detail["last_bar_used"]` + freq |
| `smt_events` | both series at the **same left label**, hence the same close window | `available_at` = `time + freq` |

**A daily bias is therefore NOT tradeable inside its own day.** `daily_bias` answers
*"is today's daily candle confirmed"*, which by construction resolves at or near the
day's close. `bias_report` returns `gates_available_at` for exactly this reason, and
`next_day_view()` shifts the frame forward one session for callers that want a
forecast rather than a classification.

`test_bias.py::test_no_gate_reads_past_its_availability` enforces this by
perturbing every bar after a gate's claimed availability and asserting the verdict
does not move.

Data note: `smt_events` needs a correlated asset. `python/fetch_correlated.py`
pulls XAG_USD (silver) H1+D into `m3_scalper/`; on this window silver's H1 returns
correlate with gold's at **0.766** and daily at **0.796**, which is ample for a
divergence test. The dollar-index proxy fetched alongside it (EUR_USD inverted) is
weaker and is a *proxy*, never "DXY" — OANDA carries no dollar index at all.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# `_run_into_extreme` / `_level` are imported from cisd.py on purpose, private or
# not: the hourly-CISD confirmation in §2.4 must use exactly the same notion of
# "the opposing series" as the CISD detector, or the two silently diverge.
from .cisd import LEVEL_RULES, _level, _run_into_extreme
from .fractal import c2_events
from .poi import poi_gate
from .primitives import swing_points

# ── settled constants (phase 2) ───────────────────────────────────────────────
TZ = "America/New_York"                  # DST-aware. Settled, not a knob.
FOUR_HOUR_GRID_OFFSETS = {"forex": 1, "futures": 2}   # first grid hour of the day
DEFAULT_GRID = "forex"                   # gold. Settled weakly; see §1.4.
DAILY_OPEN_HOUR = 18                     # §1.4 canon; 0 (midnight) is the [P] alternative.

# §2.5 `daily-profile-session-windows`; Asia from `killzones.yaml` (forex).
SESSION_WINDOWS = {
    "asia": ("20:00", "00:00"),
    "london": ("02:00", "05:00"),
    "ny_am": ("08:30", "12:00"),
}

# §2.4 `daily-wick-confirmation-timeframes`. Encoded as data because it is a stated
# table; the implemented default is hourly everywhere, because §2.4 also says the
# hourly CISD is "the single confirmation gate used in every video of the weekly
# profile series" and the map is "a floor, not a ceiling".
CONFIRMATION_TF_BY_SESSION = {
    "asia": ("1h", "4h"),
    "london": ("15min", "30min", "4h"),
    "ny_am": ("5min", "15min", "1h"),
}

DAILY_PROFILES = ("london_reversal", "new_york_reversal",
                  "new_york_manipulation", "seek_and_destroy", "unclassified")
DRAW_RULES = ("proximity", "bias", "displacement")
C3_REFERENCES = ("c2_open", "c2_extreme")
CISD_SCOPES = ("range", "wick")
WICK_MEASURES = ("body", "range")

# `meta/threshold_fits.md` recommended defaults. Grades in brackets.
WICK_CUT_BODY = 1.0        # opposing_run / |close-open| <= 1.0   [A]
WICK_CUT_RANGE = 0.30      # opposing_run / (high-low)   <= 0.30  [C]


# ── availability ──────────────────────────────────────────────────────────────
def infer_freq(index: pd.DatetimeIndex, fallback: pd.Timedelta | None = None
               ) -> pd.Timedelta:
    """Bar width, from the modal gap. Used to turn a left label into a close time.

    The mode rather than the median or `index.freq`: these series have weekend and
    holiday gaps, and `freq` is None on anything loaded from parquet.
    """
    if len(index) < 3:
        return fallback or pd.Timedelta(minutes=1)
    d = pd.Series(index).diff().dropna()
    return pd.Timedelta(d.mode().iloc[0]) if len(d) else (fallback or pd.Timedelta(minutes=1))


def bar_close(index, freq: pd.Timedelta):
    """The moment a left-labelled bar's information actually exists."""
    return pd.DatetimeIndex(index) + freq


# ── calendar ──────────────────────────────────────────────────────────────────
def trading_day(index: pd.DatetimeIndex, tz: str = TZ,
                open_hour: int = DAILY_OPEN_HOUR) -> pd.DatetimeIndex:
    """Label each bar with the trading day it belongs to (naive local midnight).

    With `open_hour=18` the day runs 18:00 NY -> 18:00 NY, which is the venue's own
    daily candle (§1.4) and which the gold week fits exactly: Sunday 18:00 to Friday
    17:00, with the break at 17:00-18:04 and **zero bars in NY hour 17**.

    The arithmetic is done on naive *local wall clock* on purpose. Subtracting 18
    fixed hours in UTC would drift by an hour across a DST switch and smear the
    label; on the wall clock a DST day is simply 23 or 25 hours long, which is
    what actually happened.
    """
    local = index.tz_convert(tz).tz_localize(None)
    return (local - pd.Timedelta(hours=open_hour)).normalize()


def daily_candles(df: pd.DataFrame, tz: str = TZ,
                  open_hour: int = DAILY_OPEN_HOUR) -> pd.DataFrame:
    """Daily OHLC on the 18:00-NY anchor, indexed by trading day.

    Carries `utc_start` / `utc_end` so intraday slicing needs no second calendar
    pass, and `n_bars` so a half-formed day (a holiday, the last day of the file)
    can be filtered rather than silently trusted.
    """
    day = trading_day(df.index, tz, open_hour)
    g = df.groupby(day, sort=True)
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last"))
    idx = pd.Series(df.index, index=day)
    out["utc_start"] = idx.groupby(level=0).min()
    out["utc_end"] = idx.groupby(level=0).max()
    # `utc_end` is a LEFT label — the last bar's start. The day's information is
    # complete only at that bar's close, which is what downstream availability
    # arithmetic must use.
    out["utc_end_close"] = out["utc_end"] + infer_freq(df.index)
    out["n_bars"] = g.size()
    out.index.name = "trading_day"
    return out


def four_hour_candles(df: pd.DataFrame, grid: str = DEFAULT_GRID,
                      tz: str = TZ) -> pd.DataFrame:
    """4-hour candles on the asset-class grid (§1.4).

    forex   17:00, 21:00, 01:00, 05:00, 09:00, 13:00 NY  <- gold uses this one
    futures 18:00, 22:00, 02:00, 06:00, 10:00, 14:00 NY

    The grid is applied on the local wall clock so it survives DST, and the result
    is indexed by the **first UTC bar** in each bucket rather than by the nominal
    local open. That avoids the ambiguity of localising a 01:00 label on the
    fall-back night, and on a venue with gaps the first traded bar is the honest
    open anyway. The nominal label is kept in `grid_open_local`.
    """
    if grid not in FOUR_HOUR_GRID_OFFSETS:
        raise ValueError(f"grid must be one of {tuple(FOUR_HOUR_GRID_OFFSETS)}")
    off = FOUR_HOUR_GRID_OFFSETS[grid]
    local = df.index.tz_convert(tz).tz_localize(None)
    bucket = (local - pd.Timedelta(hours=off)).floor("4h") + pd.Timedelta(hours=off)
    g = df.groupby(bucket, sort=True)
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last"))
    idx = pd.Series(df.index, index=bucket)
    starts = idx.groupby(level=0).min()
    out["grid_open_local"] = out.index
    # Build from the Series (not .values) so the tz-aware dtype survives.
    out.index = pd.DatetimeIndex(starts.reindex(out.index)).rename("time")
    return out


def session_slice(df: pd.DataFrame, session: str, tz: str = TZ) -> pd.DataFrame:
    """Bars inside a named session window (§2.5), by local wall clock."""
    if session not in SESSION_WINDOWS:
        raise ValueError(f"session must be one of {tuple(SESSION_WINDOWS)}")
    start, end = SESSION_WINDOWS[session]
    local = df.index.tz_convert(tz)
    t = pd.Series(local.time, index=df.index)
    lo, hi = pd.Timestamp(start).time(), pd.Timestamp(end).time()
    mask = (t >= lo) & (t < hi) if lo < hi else (t >= lo) | (t < hi)
    return df[mask.to_numpy()]


# ── wick geometry (§3.6) ──────────────────────────────────────────────────────
def opposing_run(df: pd.DataFrame, direction: str) -> pd.Series:
    """Open -> extreme AGAINST the intended direction. §3.6, settled and one-sided.

    Not `high - low`, not the sum of both wicks: *"When I say opposing run, I mean
    from the opening price to that high."*
    """
    if direction == "bullish":
        return (df["open"] - df["low"]).clip(lower=0)
    if direction == "bearish":
        return (df["high"] - df["open"]).clip(lower=0)
    raise ValueError("direction must be 'bullish' or 'bearish'")


def wick_ratio(df: pd.DataFrame, direction: str,
               measure: str = "body") -> pd.Series:
    """The opposing run normalised. `measure="body"` is the grade-A parameterisation."""
    if measure not in WICK_MEASURES:
        raise ValueError(f"measure must be one of {WICK_MEASURES}")
    run = opposing_run(df, direction)
    denom = ((df["close"] - df["open"]).abs() if measure == "body"
             else (df["high"] - df["low"]))
    return run / denom.replace(0, np.nan)


def is_small_wick(df: pd.DataFrame, direction: str, measure: str = "body",
                  cut: float | None = None) -> pd.Series:
    """Small wick == the candle supports expansion in `direction` (§3.6).

    Defaults come from `meta/threshold_fits.md`: 1.0 on the body measure (grade A,
    the one cut three independent videos state) and 0.30 on the range measure
    (grade C — the corpus's own 0.5 is a *ceiling* admitting ~85% of candles).
    """
    if cut is None:
        cut = WICK_CUT_BODY if measure == "body" else WICK_CUT_RANGE
    return (wick_ratio(df, direction, measure) <= cut).fillna(False)


# ── §2.3 the previous-candle engine ───────────────────────────────────────────
def previous_candle_state(candles: pd.DataFrame,
                          range_lookback: int = 3) -> pd.DataFrame:
    """The mechanical core of bias, applied at any scale (§2.3).

    Per candle, relative to the one before it:
      continuation  took a side AND closed outside   -> same direction next
      reversal      took a side AND closed inside    -> opposite direction next
      both          took both sides                  -> no bias
      inside        took neither                     -> no information; the spec
                                                        says default to trend
      range_bound   `range_lookback` consecutive inside bars

    `implied_bias` is the bias for the **next** candle, so reading it at candle i
    and acting on candle i+1 involves no look-ahead. `trend` is the most mechanical
    of the corpus's three trend definitions (`trend-by-previous-day-extremes`): the
    direction of the last resolved side-taking.
    """
    h, l, c = candles["high"], candles["low"], candles["close"]
    ph, pl = h.shift(1), l.shift(1)
    took_high = (h > ph).fillna(False)
    took_low = (l < pl).fillna(False)
    closed_above = (c > ph).fillna(False)
    closed_below = (c < pl).fillna(False)

    state = pd.Series("inside", index=candles.index, dtype=object)
    bias = pd.Series("none", index=candles.index, dtype=object)

    both = took_high & took_low
    only_high = took_high & ~took_low
    only_low = took_low & ~took_high

    state[both] = "both"
    state[only_high & closed_above] = "continuation"
    state[only_high & ~closed_above] = "reversal"
    state[only_low & closed_below] = "continuation"
    state[only_low & ~closed_below] = "reversal"

    bias[only_high & closed_above] = "bullish"
    bias[only_high & ~closed_above] = "bearish"
    bias[only_low & closed_below] = "bearish"
    bias[only_low & ~closed_below] = "bullish"

    inside = ~took_high & ~took_low
    state[inside] = "inside"
    rng = inside.rolling(range_lookback, min_periods=range_lookback).sum()
    state[(rng >= range_lookback).fillna(False)] = "range_bound"

    # Trend: the last resolved side-taking, carried forward for the inside case.
    resolved = pd.Series(np.where(took_high & ~took_low, "bullish",
                         np.where(took_low & ~took_high, "bearish", None)),
                         index=candles.index, dtype=object)
    trend = resolved.ffill().fillna("none")

    out = pd.DataFrame({
        "state": state, "implied_bias": bias, "trend": trend,
        "prev_high": ph, "prev_low": pl, "prev_eq": (ph + pl) / 2.0,
        "took_high": took_high, "took_low": took_low,
    })
    # "Inside bar -> no information; default to trend continuation."
    m = out["state"].isin(("inside", "range_bound"))
    out.loc[m, "implied_bias"] = out.loc[m, "trend"]
    out.loc[out["state"] == "range_bound", "implied_bias"] = "none"
    return out


# ── §2.2 the draw on liquidity ────────────────────────────────────────────────
def draw_on_liquidity(candles: pd.DataFrame, rule: str = "proximity",
                      lookback: int = 3,
                      bias: pd.Series | None = None) -> pd.DataFrame:
    """Which side is more likely to be taken — the destination the day is framed to.

    Later canon (§2.2): mark previous day high and low, ask which is more likely to
    be reached. Look back **three days** and extend each day's high and low forward
    (`previous-day-lookback-three-days`), so the pools are the 3-day extremes rather
    than yesterday's alone.

    **[GAP] — no ranking among candidates is ever given.** Three readings the corpus
    does state, selectable:
      "proximity"     the nearer extreme is the draw (`proximity-bias-nearest-extreme`)
                      — the only fully mechanical one, hence the default.
      "bias"          the side consistent with the previous-candle engine.
      "displacement"  follow the displacement, which he calls "generally right"
                      (`draw-on-liquidity`) — the side the last candle closed toward.
    """
    if rule not in DRAW_RULES:
        raise ValueError(f"rule must be one of {DRAW_RULES}")
    hi = candles["high"].shift(1).rolling(lookback, min_periods=1).max()
    lo = candles["low"].shift(1).rolling(lookback, min_periods=1).min()
    ref = candles["open"]

    if rule == "proximity":
        draw = np.where((hi - ref).abs() <= (ref - lo).abs(), "buyside", "sellside")
    elif rule == "bias":
        if bias is None:
            raise ValueError("rule='bias' needs the `bias` series")
        b = bias.reindex(candles.index).fillna("none")
        draw = np.where(b == "bullish", "buyside",
                        np.where(b == "bearish", "sellside", "none"))
    else:
        prev_dir = np.sign((candles["close"] - candles["open"]).shift(1).fillna(0))
        draw = np.where(prev_dir > 0, "buyside",
                        np.where(prev_dir < 0, "sellside", "none"))

    return pd.DataFrame({"draw": draw, "buyside_pool": hi, "sellside_pool": lo,
                         "eq_pool": (hi + lo) / 2.0}, index=candles.index)


# ── §2.4 daily closures and the hourly CISD ───────────────────────────────────
def daily_closures(candles: pd.DataFrame, c3_reference: str = "c2_open",
                   **c2_kw) -> pd.DataFrame:
    """C2 and C3 closures on the bias timeframe (§3.2, §3.3).

    C2 comes from `fractal.c2_events` so the definition cannot drift between
    modules. C3-as-a-closure is built here rather than taken from
    `fractal.c3_events`, because §3.3 keeps two senses of C3 apart and only this
    one — *"a C3 closure exists only when C2 failed to close"* — is what §2.4's
    confirmation step means.

    **[P] — the C3 closure reference. Both readings implemented; neither source
    reconciles them.**
      "c2_open"     Reading A: C3 closes beyond the body / opening price of C2.
      "c2_extreme"  Reading B: C3 closes beyond C2's high (bullish) / low (bearish).
                    Strictly stronger; selects a subset of Reading A.
    """
    if c3_reference not in C3_REFERENCES:
        raise ValueError(f"c3_reference must be one of {C3_REFERENCES}")

    out = pd.DataFrame(index=candles.index)
    out["c2_closure"] = "none"
    ev = c2_events(candles, **c2_kw)
    if len(ev):
        out.loc[ev["time"].to_numpy(), "c2_closure"] = ev["direction"].to_numpy()

    o, h, l, c = (candles["open"], candles["high"],
                  candles["low"], candles["close"])
    po, ph, pl = o.shift(1), h.shift(1), l.shift(1)
    prev_c2 = out["c2_closure"].shift(1).fillna("none")

    if c3_reference == "c2_open":
        up_ref, dn_ref = po, po
    else:
        up_ref, dn_ref = ph, pl

    # "A C3 closure exists ONLY when C2 failed to close" — so the previous candle
    # must be a *candidate* C2 (it took the prior extreme, i.e. it engaged the
    # liquidity) that nonetheless produced no C2 closure. Without that precondition
    # the test degenerates to "did this candle close beyond the last one's open",
    # which fires on ~75% of daily candles and measures nothing. With it the rate
    # lands near the ~20% `meta/fractal_reading_comparison.md` reports.
    prev_took_low = (l.shift(1) < l.shift(2)).fillna(False)
    prev_took_high = (h.shift(1) > h.shift(2)).fillna(False)
    no_c2 = prev_c2 == "none"

    c3 = pd.Series("none", index=candles.index, dtype=object)
    c3[(c > up_ref).fillna(False) & no_c2 & prev_took_low] = "bullish"
    c3[(c < dn_ref).fillna(False) & no_c2 & prev_took_high] = "bearish"
    out["c3_closure"] = c3
    out["c3_reference"] = c3_reference
    out["closure"] = np.where(out["c2_closure"] != "none", out["c2_closure"],
                              out["c3_closure"])
    out["closure_kind"] = np.where(out["c2_closure"] != "none", "C2",
                                   np.where(out["c3_closure"] != "none", "C3", "none"))
    return out


def hourly_cisd_in_candle(ltf: pd.DataFrame, start, end, direction: str,
                          scope: str = "range", level_rule: str = "series_open",
                          max_series: int = 10,
                          htf_open: float | None = None,
                          max_bars_waited: int | None = None) -> dict | None:
    """§2.4 step 3: the change in the state of delivery inside one HTF candle.

    Procedure, verbatim: on the 1H chart restrict attention to price action *inside*
    the candidate daily candle; find the extreme; identify the consecutive series of
    opposing-close candles that made it; require a 1H close through that series.
    Until that close-through occurs the daily closure is **not** confirmed.

    The series definition and the level readings are imported from `cisd.py` so the
    two detectors cannot disagree about what a CISD is.

    **[P] — `scope`.** Whether the CISD must sit inside the *wick* specifically or
    anywhere inside the daily candle's range is stated both ways across the series.
      "range" (default)  anywhere inside the HTF candle.
      "wick"             only up to the first LTF close back beyond the HTF open in
                         the setup's direction — i.e. while the wick is still
                         forming. Needs `htf_open`.

    `max_bars_waited` is §4.2's speed test — *"I prefer 1, 2, maybe three"* — the
    corpus's only candle-count threshold for "swift". It is stated as a *preference*
    rather than a rule, so the default is `None` (off); set 3 to apply it.
    """
    if scope not in CISD_SCOPES:
        raise ValueError(f"scope must be one of {CISD_SCOPES}")
    if level_rule not in LEVEL_RULES:
        raise ValueError(f"level_rule must be one of {LEVEL_RULES}")
    bullish = direction == "bullish"
    if direction not in ("bullish", "bearish"):
        raise ValueError("direction must be 'bullish' or 'bearish'")

    seg = ltf.loc[(ltf.index >= start) & (ltf.index <= end)]
    if len(seg) < 3:
        return None

    if scope == "wick":
        if htf_open is None:
            raise ValueError("scope='wick' needs htf_open")
        back = (seg["close"] > htf_open) if bullish else (seg["close"] < htf_open)
        hits = np.flatnonzero(back.to_numpy())
        if len(hits):
            seg = seg.iloc[:int(hits[0]) + 1]
        if len(seg) < 3:
            return None

    ext_pos = int(np.argmin(seg["low"].to_numpy()) if bullish
                  else np.argmax(seg["high"].to_numpy()))
    s, e = _run_into_extreme(seg, ext_pos, bullish, max_len=max_series)
    if s < 0:
        return None
    level = _level(seg, s, e, bullish, level_rule)

    close = seg["close"].to_numpy()
    last = len(seg) if max_bars_waited is None else min(len(seg), e + 1 + max_bars_waited)
    for j in range(e + 1, last):
        if (close[j] > level) if bullish else (close[j] < level):
            return {"direction": direction, "level": float(level),
                    "level_rule": level_rule, "scope": scope,
                    "extreme_time": seg.index[ext_pos],
                    "extreme_price": float(seg["low"].iloc[ext_pos] if bullish
                                           else seg["high"].iloc[ext_pos]),
                    "series_start": seg.index[s], "series_end": seg.index[e],
                    "series_len": e - s + 1,
                    "confirm_time": seg.index[j], "confirm_close": float(close[j]),
                    "bars_waited": j - e}
    return None


# ── §2.4 daily bias, assembled ────────────────────────────────────────────────
def daily_bias(daily: pd.DataFrame, ltf: pd.DataFrame, *,
               draw_rule: str = "proximity", draw_lookback: int = 3,
               c3_reference: str = "c2_open",
               cisd_scope: str = "range", cisd_level_rule: str = "series_open",
               cisd_max_bars_waited: int | None = None,
               require_closure: bool = True, require_hourly_cisd: bool = True,
               wick_measure: str = "body", wick_cut: float | None = None,
               eq_respect: bool = True) -> pd.DataFrame:
    """§2.4 end to end, one row per trading day.

    Columns that matter downstream:
      prev_high/prev_low/prev_eq  the three marked levels (`inside-day-three-levels`)
      draw                        the destination (§2.2)
      closure / closure_kind      the daily C2 or C3 closure
      hourly_cisd                 direction of the confirming LTF CISD, or 'none'
      bias                        the confirmed bias, 'none' when either leg is missing
      branch                      'reversal' | 'continuation' | 'none' (§2.4 step 2)
      tradeable_same_day          §2.4 step 4: small wick -> the reversal candle
                                  itself may be traded; large wick -> do not, trade
                                  the following candle
      eq_respected                the continuation branch's negative test: no LTF
                                  closures beyond the previous day's EQ

    **Every leg is a switch.** `require_closure` and `require_hourly_cisd` default
    True because §2.4 says either alone is no bias, but they are exposed so the
    build note can report what each one costs in sample size.

    Look-ahead: the confirming CISD is searched inside the day being biased and the
    bias is stamped on that same day, which is correct for *"is today's daily candle
    confirmed"* — it is a within-day confirmation, not a next-day forecast. Callers
    forecasting the next day must shift by one.
    """
    eng = previous_candle_state(daily)
    dr = draw_on_liquidity(daily, rule=draw_rule, lookback=draw_lookback,
                           bias=eng["implied_bias"])
    cl = daily_closures(daily, c3_reference=c3_reference)

    out = pd.concat([daily[["open", "high", "low", "close",
                            "utc_start", "utc_end", "utc_end_close"]],
                     eng[["state", "implied_bias", "trend",
                          "prev_high", "prev_low", "prev_eq"]],
                     dr[["draw", "buyside_pool", "sellside_pool"]],
                     cl[["c2_closure", "c3_closure", "closure", "closure_kind"]]],
                    axis=1)

    cisd_dir, cisd_time = [], []
    for day, row in out.iterrows():
        s, e = daily.loc[day, "utc_start"], daily.loc[day, "utc_end"]
        # With a closure present, look only in its direction — §2.4 wants the two
        # legs to agree. With none (and `require_closure=False`) look both ways and
        # accept only an unambiguous answer, so the switch is real rather than
        # decorative: searching one arbitrary direction would make it inert.
        dirs = [row["closure"]] if row["closure"] != "none" \
            else ([] if require_closure else ["bullish", "bearish"])
        found = []
        for d in dirs:
            ev = hourly_cisd_in_candle(ltf, s, e, d, scope=cisd_scope,
                                       level_rule=cisd_level_rule,
                                       htf_open=float(row["open"]),
                                       max_bars_waited=cisd_max_bars_waited)
            if ev:
                found.append(ev)
        if len(found) == 1:
            cisd_dir.append(found[0]["direction"])
            cisd_time.append(found[0]["confirm_time"])
        else:
            cisd_dir.append("none"); cisd_time.append(pd.NaT)
    out["hourly_cisd"] = cisd_dir
    out["hourly_cisd_time"] = cisd_time

    # Availability. The daily closure resolves at the day's last bar close; the LTF
    # CISD at the confirming bar's close. Both are LEFT labels, so add the bar width.
    ltf_freq = infer_freq(ltf.index, pd.Timedelta(hours=1))
    closure_at = daily["utc_end_close"].reindex(out.index)
    cisd_at = pd.Series(pd.DatetimeIndex(cisd_time) + ltf_freq, index=out.index)
    out["closure_available_at"] = closure_at.where(out["closure"] != "none")
    out["cisd_available_at"] = cisd_at
    out["bias_available_at"] = out[["closure_available_at",
                                    "cisd_available_at"]].max(axis=1)

    has_closure = out["closure"] != "none"
    has_cisd = out["hourly_cisd"] != "none"
    agree = has_closure & has_cisd & (out["closure"] == out["hourly_cisd"])
    ok = agree.copy()
    if not require_closure:
        ok = ok | has_cisd
    if not require_hourly_cisd:
        ok = ok | has_closure
    out["bias"] = np.where(ok, np.where(has_closure, out["closure"],
                                        out["hourly_cisd"]), "none")

    # §2.4 step 2: the binary. A reversal is always framed off the previous day's
    # extreme; a continuation trades against the bias first, respects the EQ, then
    # trades through the previous extreme.
    took_low = (out["low"] < out["prev_low"]).fillna(False)
    took_high = (out["high"] > out["prev_high"]).fillna(False)
    rev = ((out["bias"] == "bullish") & took_low) | \
          ((out["bias"] == "bearish") & took_high)
    out["branch"] = np.where(out["bias"] == "none", "none",
                             np.where(rev, "reversal", "continuation"))

    # §2.4 step 4 -> §3.6: the reversal-day tradeability gate.
    small_bull = is_small_wick(daily, "bullish", wick_measure, wick_cut)
    small_bear = is_small_wick(daily, "bearish", wick_measure, wick_cut)
    out["small_wick"] = np.where(out["bias"] == "bullish", small_bull,
                                 np.where(out["bias"] == "bearish", small_bear, False))
    out["tradeable_same_day"] = np.where(out["branch"] == "reversal",
                                         out["small_wick"], True)
    out.loc[out["bias"] == "none", "tradeable_same_day"] = False

    # The continuation branch's EQ test, operationalised negatively: no LTF closures
    # beyond the previous day's EQ against the bias.
    if eq_respect:
        resp = []
        for day, row in out.iterrows():
            if row["branch"] != "continuation" or pd.isna(row["prev_eq"]):
                resp.append(pd.NA); continue
            s, e = daily.loc[day, "utc_start"], daily.loc[day, "utc_end"]
            seg = ltf.loc[(ltf.index >= s) & (ltf.index <= e), "close"]
            if seg.empty:
                resp.append(pd.NA); continue
            beyond = ((seg < row["prev_eq"]).any() if row["bias"] == "bullish"
                      else (seg > row["prev_eq"]).any())
            resp.append(not bool(beyond))
        out["eq_respected"] = resp
    else:
        out["eq_respected"] = pd.NA
    return out


# ── §2.5 profiles ─────────────────────────────────────────────────────────────
def session_ranges(intraday: pd.DataFrame, tz: str = TZ,
                   open_hour: int = DAILY_OPEN_HOUR) -> pd.DataFrame:
    """Asia / London / New York a.m. high-low per trading day (§2.5 windows).

    Pass M1 or 15m: the New York window opens at **08:30**, which is not an hourly
    boundary, so hourly bars round it to 08:00 and the profile shifts. The function
    does not stop you — it records `ny_bars` so you can see the resolution you got.
    """
    day = trading_day(intraday.index, tz, open_hour)
    freq = infer_freq(intraday.index)
    frames = {}
    for name in SESSION_WINDOWS:
        sl = session_slice(intraday, name, tz)
        d = trading_day(sl.index, tz, open_hour)
        g = sl.groupby(d, sort=True)
        times = pd.Series(sl.index, index=d)
        frames[name] = pd.DataFrame({
            f"{name}_high": g["high"].max(), f"{name}_low": g["low"].min(),
            f"{name}_open": g["open"].first(), f"{name}_close": g["close"].last(),
            f"{name}_bars": g.size(),
            # left labels -> the window's information exists one bar width later
            f"{name}_end": times.groupby(level=0).max() + freq,
        })
    out = pd.concat(frames.values(), axis=1)
    out = out.reindex(pd.Index(sorted(set(day)), name="trading_day"))
    return out


def daily_profile(bias_frame: pd.DataFrame, sessions: pd.DataFrame,
                  intraday: pd.DataFrame | None = None, *,
                  relevant_levels: pd.DataFrame | None = None,
                  direction_ref: str = "bias",
                  london_counter_ref: str = "asia",
                  require_outside_day: bool = True,
                  require_cisd_for_london_reversal: bool = True,
                  ny_manip_requires_london_quiet: bool = True,
                  cisd_level_rule: str = "series_open") -> pd.DataFrame:
    """Classify each day into one of §2.5's four profiles.

    The discriminator between the first two is one question — **did London reach a
    relevant higher-timeframe PD array?** "Relevant" is never defined **[GAP]**, so
    `relevant_levels` is supplied by the caller. §2.7 `relevant-level` gives the one
    attested default: *previous day and previous week extremes always qualify*, and
    `relevant_level_frame()` builds exactly that.

    | profile | recognition |
    |---|---|
    | london_reversal | London runs counter to the bias, **reaches** a relevant level, and changes the state of delivery there. New York continues off it. |
    | new_york_reversal | London ran counter but did **not** reach a relevant level, so the run continues into New York where the level is finally reached. |
    | new_york_manipulation | London produced nothing usable; New York sweeps one side of London's range and expands the other way. Power of Three. |
    | seek_and_destroy | London takes **both** Asia extremes and the daily candle is an outside/indecision bar. **Stand-aside day.** |

    `direction_ref="bias"` (default) measures "counter to the daily direction"
    against the *bias*, not against the day's realised close — the realised reading
    is look-ahead for anything decided before the close, and is available as
    `direction_ref="realized"` only for post-hoc classification.

    `require_outside_day=True` is faithful to the spec's second Seek & Destroy
    clause but is only checkable at the daily close; `seek_destroy_asia_both` is
    returned separately so an intraday-safe version is available.
    """
    if direction_ref not in ("bias", "realized"):
        raise ValueError("direction_ref must be 'bias' or 'realized'")
    if london_counter_ref not in ("asia", "day_open"):
        raise ValueError("london_counter_ref must be 'asia' or 'day_open'")

    df = bias_frame.join(sessions, how="left")
    direction = (df["bias"] if direction_ref == "bias"
                 else np.where(df["close"] > df["open"], "bullish", "bearish"))
    direction = pd.Series(direction, index=df.index).fillna("none")

    bull = direction == "bullish"
    bear = direction == "bearish"

    # Counter-run: London's extreme against the intended direction exceeds the
    # reference on that side.
    if london_counter_ref == "asia":
        ref_lo, ref_hi = df["asia_low"], df["asia_high"]
    else:
        ref_lo = ref_hi = df["open"]
    london_counter = ((bull & (df["london_low"] < ref_lo)) |
                      (bear & (df["london_high"] > ref_hi))).fillna(False)

    # Seek & Destroy: London takes BOTH Asia extremes.
    sd_asia_both = ((df["london_high"] > df["asia_high"]) &
                    (df["london_low"] < df["asia_low"])).fillna(False)
    outside_day = ((df["high"] > df["prev_high"]) &
                   (df["low"] < df["prev_low"])).fillna(False)
    seek_destroy = sd_asia_both & outside_day if require_outside_day else sd_asia_both

    # Did London reach a relevant level on the counter side?
    if relevant_levels is None:
        relevant_levels = relevant_level_frame(bias_frame)
    rl = relevant_levels.reindex(df.index)
    reached = pd.Series(False, index=df.index)
    for col in [c for c in rl.columns if c.endswith("_low")]:
        reached |= (bull & (df["london_low"] <= rl[col])).fillna(False)
    for col in [c for c in rl.columns if c.endswith("_high")]:
        reached |= (bear & (df["london_high"] >= rl[col])).fillna(False)

    # Did the state of delivery change in London?
    london_cisd = pd.Series(False, index=df.index)
    if require_cisd_for_london_reversal and intraday is not None:
        ldn = session_slice(intraday, "london")
        ldn_day = trading_day(ldn.index)
        for day in df.index[london_counter & reached]:
            seg = ldn[ldn_day == day]
            if len(seg) < 3:
                continue
            ev = hourly_cisd_in_candle(seg, seg.index[0], seg.index[-1],
                                       direction.loc[day],
                                       level_rule=cisd_level_rule)
            london_cisd.loc[day] = ev is not None
    elif not require_cisd_for_london_reversal:
        london_cisd = pd.Series(True, index=df.index)

    # New York manipulation: "London consolidated or produced nothing usable. New
    # York sweeps one side of London's range and changes the state of delivery."
    # The "London consolidated" clause is read with the corpus's own mechanical test
    # for consolidation (`consolidation`: *price remains internal to a high and a
    # low*) — London stayed inside the Asia range.
    ny_sweep_up = ((df["ny_am_high"] > df["london_high"]) &
                   (df["ny_am_close"] < df["london_high"])).fillna(False)
    ny_sweep_dn = ((df["ny_am_low"] < df["london_low"]) &
                   (df["ny_am_close"] > df["london_low"])).fillna(False)
    london_quiet = ((df["london_high"] <= df["asia_high"]) &
                    (df["london_low"] >= df["asia_low"])).fillna(False)
    if not ny_manip_requires_london_quiet:
        london_quiet = pd.Series(True, index=df.index)
    ny_manip = (~london_counter) & london_quiet & \
               (ny_sweep_up | ny_sweep_dn) & ~seek_destroy

    profile = pd.Series("unclassified", index=df.index, dtype=object)
    pdir = pd.Series("none", index=df.index, dtype=object)

    m = london_counter & reached & london_cisd & ~seek_destroy
    profile[m] = "london_reversal"
    pdir[m] = direction[m]

    m = london_counter & ~(reached & london_cisd) & ~seek_destroy
    profile[m] = "new_york_reversal"
    pdir[m] = direction[m]

    profile[ny_manip] = "new_york_manipulation"
    pdir[ny_manip & ny_sweep_up] = "bearish"      # swept the high, expands down
    pdir[ny_manip & ny_sweep_dn] = "bullish"

    # All three of the directional profiles are defined relative to "the daily
    # direction", so a day with no confirmed bias cannot be one of them. Only Seek
    # & Destroy is direction-free, and it is a stand-aside label anyway.
    no_dir = direction == "none"
    profile[no_dir] = "unclassified"
    pdir[no_dir] = "none"

    profile[seek_destroy] = "seek_and_destroy"
    pdir[seek_destroy] = "none"                    # stand-aside day

    # Availability: the NY a.m. window closes at 12:00 NY, so a profile that only
    # needs the session ranges is known then. `require_outside_day` additionally
    # needs the daily close, which pushes the whole verdict to the day's end.
    ny_end = df["ny_am_end"] if "ny_am_end" in df.columns else pd.Series(pd.NaT, index=df.index)
    day_end = df["utc_end_close"] if "utc_end_close" in df.columns else ny_end
    avail = day_end if require_outside_day else ny_end

    return pd.DataFrame({
        "profile": profile, "profile_direction": pdir,
        "london_counter": london_counter, "london_reached_relevant": reached,
        "london_cisd": london_cisd,
        "seek_destroy_asia_both": sd_asia_both, "outside_day": outside_day,
        "ny_sweep_up": ny_sweep_up, "ny_sweep_down": ny_sweep_dn,
        "profile_available_at": avail,
    }, index=df.index)


def relevant_level_frame(daily: pd.DataFrame, weekly_lookback: int = 5
                         ) -> pd.DataFrame:
    """The one attested default for "relevant level" (§2.7 `relevant-level`).

    *"previous day and previous week extremes always qualify"* — so: previous day
    high/low, and the rolling extreme of the previous `weekly_lookback` sessions as
    the previous-week proxy. Everything else the corpus calls "relevant" / "key" /
    "higher-timeframe objective" is undefined **[GAP]**; supply your own frame with
    `_high` / `_low` suffixed columns to use a different set.
    """
    return pd.DataFrame({
        "pd_high": daily["high"].shift(1),
        "pd_low": daily["low"].shift(1),
        "pw_high": daily["high"].shift(1).rolling(weekly_lookback, min_periods=1).max(),
        "pw_low": daily["low"].shift(1).rolling(weekly_lookback, min_periods=1).min(),
    }, index=daily.index)


def profile_supports_bias(profile: pd.Series, profile_direction: pd.Series,
                          bias: pd.Series,
                          unclassified_supports: bool = False) -> pd.Series:
    """§2.1 step 2 — the gate that is easy to skip and changes the answer.

    *"Name which profile the day is, and check it supports the bias. If it does
    not, do not take the entry even though the bias stands."*

    Seek & Destroy never supports anything — it is a stand-aside day by name.
    `unclassified_supports=False` is the conservative default; what would count as
    invalidation of a profile is never given **[GAP]**, so an unnamed day is treated
    as unconfirmed rather than as permission.
    """
    supports = (profile_direction == bias) & (bias != "none")
    supports &= profile != "seek_and_destroy"
    if unclassified_supports:
        supports |= (profile == "unclassified") & (bias != "none")
    return supports.fillna(False)


# ── §2.1 / §3.5 timeframe alignment ───────────────────────────────────────────
def timeframe_alignment(direction: str, daily_row: pd.Series,
                        h4_row: pd.Series | None = None,
                        h1_row: pd.Series | None = None, *,
                        min_aligned: int = 2, no_fade_daily: bool = True,
                        wick_measure: str = "body",
                        wick_cut: float | None = None) -> dict:
    """Daily / 4H / hourly all pointing at the same objective (§2.1, §3.5).

    A layer *supports* `direction` when its candle closes in that direction **and**
    its opposing run is small (§3.6: "if any layer has a large wick or opens against
    the intended direction, you do not trade that layer").

    `min_aligned=2` is the corpus's stated minimum ("minimum two aligned expansion
    candles; three preferred for sub-5-minute execution"). `no_fade_daily` is the
    separate hard gate from §2.1 (`no-fading-the-daily-candle`): the daily layer may
    not oppose, regardless of how many other layers agree.
    """
    if wick_cut is None:
        wick_cut = WICK_CUT_BODY if wick_measure == "body" else WICK_CUT_RANGE
    bullish = direction == "bullish"
    if direction not in ("bullish", "bearish"):
        raise ValueError("direction must be 'bullish' or 'bearish'")

    def layer(row):
        if row is None or row is pd.NaT or (isinstance(row, float) and np.isnan(row)):
            return None
        d = pd.DataFrame([row[["open", "high", "low", "close"]].astype(float)])
        closes_with = (row["close"] > row["open"]) if bullish else (row["close"] < row["open"])
        small = bool(is_small_wick(d, direction, wick_measure, wick_cut).iloc[0])
        return {"closes_with": bool(closes_with), "small_wick": small,
                "supports": bool(closes_with and small)}

    layers = {"daily": layer(daily_row), "h4": layer(h4_row), "h1": layer(h1_row)}
    present = {k: v for k, v in layers.items() if v is not None}
    n_aligned = sum(v["supports"] for v in present.values())
    daily_opposes = (layers["daily"] is not None
                     and not layers["daily"]["closes_with"])

    passed = n_aligned >= min_aligned
    if no_fade_daily and daily_opposes:
        passed = False
    return {"passed": bool(passed), "n_aligned": int(n_aligned),
            "n_layers": len(present), "daily_opposes": bool(daily_opposes),
            "layers": layers}


def alignment_frame(daily: pd.DataFrame, h4: pd.DataFrame, h1: pd.DataFrame,
                    direction: pd.Series, **kw) -> pd.DataFrame:
    """`timeframe_alignment` over a whole daily index.

    For each day the 4H and hourly layers are the **last closed candle of that day**
    — the state at the day's end, matching how `daily_bias` stamps its confirmation
    within the day rather than forecasting the next one.
    """
    h4_freq, h1_freq = infer_freq(h4.index), infer_freq(h1.index)
    rows = []
    for day, drow in daily.iterrows():
        d = direction.get(day, "none")
        if d == "none":
            rows.append({"passed": False, "n_aligned": 0, "n_layers": 0,
                         "daily_opposes": False,
                         "alignment_available_at": pd.NaT})
            continue
        s, e = drow["utc_start"], drow["utc_end"]
        # A layer only counts once it has CLOSED, so the window ends one bar width
        # before the day's end and the availability stamp is that bar's close.
        h4s = h4.loc[(h4.index >= s) & (h4.index + h4_freq <= drow["utc_end_close"])]
        h1s = h1.loc[(h1.index >= s) & (h1.index + h1_freq <= drow["utc_end_close"])]
        res = timeframe_alignment(
            d, drow,
            h4s.iloc[-1] if len(h4s) else None,
            h1s.iloc[-1] if len(h1s) else None, **kw)
        avail = [drow["utc_end_close"]]
        if len(h4s):
            avail.append(h4s.index[-1] + h4_freq)
        if len(h1s):
            avail.append(h1s.index[-1] + h1_freq)
        row = {k: res[k] for k in
               ("passed", "n_aligned", "n_layers", "daily_opposes")}
        row["alignment_available_at"] = max(avail)
        rows.append(row)
    return pd.DataFrame(rows, index=daily.index).rename(
        columns={"passed": "alignment_passed"})


# ── §2.6 SMT / PSP ────────────────────────────────────────────────────────────
def smt_events(a: pd.DataFrame, b: pd.DataFrame, *, lookback: int = 20,
               left: int = 2, right: int = 2,
               names: tuple[str, str] = ("a", "b")) -> pd.DataFrame:
    """SMT divergence between two correlated assets (§2.6 `smt-divergence`).

    *Pick **one** shared level; one asset trades beyond it and the correlated one
    does not. At the lows it is bullish, at the highs bearish.*

    The shared level is taken at a shared **moment**: the most recent confirmed
    swing extreme in the sweeping asset within `lookback`, and the other asset's
    own extreme at that same timestamp. That is what makes it one level rather than
    two independent structures.

    Each row carries `invalidation` — the held low/high of the **diverging** (the
    non-sweeping) asset. §2.6 notes this is the only place SMT is given a standalone
    stop (`smt-invalidation-level`): if that level is taken, the divergence no longer
    exists.

    This function is deliberately **diagnostic only**. §2.6's ordering rule is
    doctrine — *"you do not find an SMT and build a model around it; you find the
    model and then check for SMT"* — so gate these events with `smt_gate` against
    model times rather than trading them directly.
    """
    cols = ["time", "direction", "swept_by", "held_by", "ref_time",
            "ref_level_swept", "ref_level_held", "invalidation", "available_at"]
    # The two series are compared at the SAME LEFT LABEL, which — because both use
    # the same left-labelled convention and the same bar width — means the same
    # close window. Comparing a label in one series against a close in the other
    # would be the classic silent misalignment; assert the widths match instead of
    # assuming it.
    fa, fb = infer_freq(a.index), infer_freq(b.index)
    if fa != fb:
        raise ValueError(
            f"bar widths differ ({fa} vs {fb}); resample both to one grid before "
            "comparing, or the 'shared level' is not shared in time")
    idx = a.index.intersection(b.index)
    if len(idx) < lookback + right + 2:
        return pd.DataFrame(columns=cols)
    A, B = a.loc[idx], b.loc[idx]
    swA = swing_points(A, left=left, right=right)
    swB = swing_points(B, left=left, right=right)

    rows = []
    for lo_side, col, price in ((True, "swing_low", "low"), (False, "swing_high", "high")):
        for (X, Y, swX, nx, ny) in ((A, B, swA, names[0], names[1]),
                                    (B, A, swB, names[1], names[0])):
            hits = np.flatnonzero(swX[col].to_numpy())
            xp = X[price].to_numpy()
            yp = Y[price].to_numpy()
            for p in hits:
                lvl_x, lvl_y = xp[p], yp[p]
                j0, j1 = p + right + 1, min(len(idx), p + right + 1 + lookback)
                for j in range(j0, j1):
                    beyond_x = xp[j] < lvl_x if lo_side else xp[j] > lvl_x
                    beyond_y = yp[j] < lvl_y if lo_side else yp[j] > lvl_y
                    if beyond_x and not beyond_y:
                        rows.append({
                            "time": idx[j],
                            "direction": "bullish" if lo_side else "bearish",
                            "swept_by": nx, "held_by": ny,
                            "ref_time": idx[p],
                            "ref_level_swept": float(lvl_x),
                            "ref_level_held": float(lvl_y),
                            "invalidation": float(lvl_y),
                            "available_at": idx[j] + fa,
                        })
                        break
                    if beyond_x and beyond_y:
                        break            # both went; no divergence
    if not rows:
        return pd.DataFrame(columns=cols)
    return (pd.DataFrame(rows).drop_duplicates(subset=["time", "direction", "swept_by"])
            .sort_values("time").reset_index(drop=True))


def smt_gate(events: pd.DataFrame, model_times, window: int = 3,
             freq: pd.Timedelta | None = None,
             standalone_allowed: bool = False) -> pd.DataFrame:
    """§2.6's ordering doctrine, enforced (`smt-requires-framework`).

    The gate is concrete in the spec: a C2/C3 closure at a POI **plus** the aligned
    lower-timeframe CISD must exist first. An SMT present before that is ignored
    however clean it looks. So an event only counts when it lands within `window`
    bars of a model time.

    **[P]** — `standalone_allowed`. Two videos in the same older playlist disagree:
    one says SMT is confluence to an already-existing model and never the trigger;
    the other permits a direct entry on the diverging asset, stopped at its
    divergent extreme. **The later canon sides with the first, so the default is
    False.**
    """
    out = events.copy()
    if out.empty:
        out["smt_confirmed"] = pd.Series(dtype=bool)
        return out
    mt = pd.DatetimeIndex(pd.Series(list(model_times)).dropna().sort_values()) \
        if len(list(model_times)) else pd.DatetimeIndex([])
    if len(mt) == 0:
        out["smt_confirmed"] = standalone_allowed
        return out
    tol = (freq or pd.Timedelta(hours=1)) * window
    nearest = mt.get_indexer(pd.DatetimeIndex(out["time"]), method="nearest")
    delta = np.abs(pd.DatetimeIndex(out["time"]) - mt[nearest])
    out["smt_confirmed"] = (delta <= tol) | standalone_allowed
    out["model_time"] = mt[nearest]
    return out


def psp(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    """Precision Swing Point: the two correlated markets close opposite colours.

    §2.6 surfaces this only as "C2 plus a PSP", never standalone, so it is returned
    as a boolean series to be ANDed into something else.
    """
    idx = a.index.intersection(b.index)
    da = np.sign(a.loc[idx, "close"] - a.loc[idx, "open"])
    db = np.sign(b.loc[idx, "close"] - b.loc[idx, "open"])
    return ((da * db) < 0).rename("psp")


# ── the whole stack ───────────────────────────────────────────────────────────
def bias_report(m1: pd.DataFrame, *, correlate_h1: pd.DataFrame | None = None,
                grid: str = DEFAULT_GRID, poi_enabled: bool = True,
                poi_timeframe: str = "1h", **bias_kw) -> pd.DataFrame:
    """Run §2.1's ladder over the whole series and return every gate as a column.

    One row per trading day, with each gate reported **standalone** so the marginal
    cost of stacking them can be measured rather than assumed:

      gate_bias         a confirmed daily bias exists (closure + hourly CISD)
      gate_profile      the day's profile supports that bias (§2.1 step 2)
      gate_alignment    daily / 4H / hourly point at the same objective
      gate_no_fade      the intraday direction does not fade the daily candle
      gate_poi          a POI was tagged at the day's bias-side extreme
      gate_smt          an SMT against the correlate confirms the same direction
      gate_all          the conjunction

    `poi_enabled=False` reruns the same day with §4.1 switched off, which is the
    single biggest frequency lever in the model — report both.
    """
    h1 = _resample(m1, "1h")
    # 15m, not M1, for the session layer: the New York window opens at 08:30, which
    # 15m hits exactly (as do 02:00 / 05:00 / 20:00 / 00:00), and it is also the
    # timeframe §2.4's session map names for London. M1 would give the same windows
    # far more slowly and a London CISD three timeframes below the stated one.
    m15 = _resample(m1, "15min")
    h4 = four_hour_candles(m1, grid=grid)
    daily = daily_candles(m1)

    bf = daily_bias(daily, h1, **bias_kw)
    sess = session_ranges(m15)
    prof = daily_profile(bf, sess, intraday=m15)
    align = alignment_frame(daily, h4, h1, bf["bias"])

    out = pd.concat([bf, prof, align], axis=1)
    out["gate_bias"] = out["bias"] != "none"
    out["gate_profile"] = profile_supports_bias(out["profile"],
                                                out["profile_direction"], out["bias"])
    out["gate_alignment"] = out["alignment_passed"].fillna(False)
    out["gate_no_fade"] = ~out["daily_opposes"].fillna(False)

    h1_freq = infer_freq(h1.index)
    poi_flags, poi_avail = [], []
    for day, row in out.iterrows():
        if row["bias"] == "none":
            poi_flags.append(False); poi_avail.append(pd.NaT); continue
        s, e = daily.loc[day, "utc_start"], daily.loc[day, "utc_end"]
        seg = h1.loc[(h1.index >= s) & (h1.index <= e)]
        if len(seg) < 6:
            poi_flags.append(False); poi_avail.append(pd.NaT); continue
        ext = (seg["low"].idxmin() if row["bias"] == "bullish"
               else seg["high"].idxmax())
        res = poi_gate(h1, ext, row["bias"], setup_type="reversal",
                       timeframe=poi_timeframe, enabled=poi_enabled)
        poi_flags.append(bool(res.passed))
        poi_avail.append(res.detail["last_bar_used"] + h1_freq)
    out["gate_poi"] = poi_flags
    out["poi_available_at"] = poi_avail

    if correlate_h1 is not None:
        smt = smt_events(h1, correlate_h1, names=("gold", "correlate"))
        gated = smt_gate(smt, out["hourly_cisd_time"].dropna(),
                         window=3, freq=h1_freq)
        flags = pd.Series(False, index=out.index)
        avail = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
        if len(gated):
            g = gated[gated["smt_confirmed"]]
            gd = trading_day(pd.DatetimeIndex(g["time"]))
            for day, d, at in zip(gd, g["direction"], g["available_at"]):
                if day in flags.index and out.loc[day, "bias"] == d:
                    flags.loc[day] = True
                    avail.loc[day] = at
        out["gate_smt"] = flags
        out["smt_available_at"] = avail
    else:
        out["gate_smt"] = pd.NA
        out["smt_available_at"] = pd.NaT

    gates = ["gate_bias", "gate_profile", "gate_alignment", "gate_no_fade", "gate_poi"]
    out["gate_all"] = out[gates].fillna(False).all(axis=1)

    # The single number downstream code must respect: no position may be opened on
    # a bar starting before this. It is at or after the day's close for every gate
    # that reads a daily closure, which is why `next_day_view` exists.
    avail_cols = ["bias_available_at", "profile_available_at",
                  "alignment_available_at", "poi_available_at"]
    out["gates_available_at"] = out[avail_cols].max(axis=1)
    return out


def next_day_view(report: pd.DataFrame) -> pd.DataFrame:
    """Shift the report forward one session so it can be *acted on* rather than read.

    `bias_report` classifies day D using information that resolves at D's close, so
    every gate in it is a statement about a day that is already over. This shifts
    each day's verdict onto D+1, which is the only lookahead-free way to trade it —
    and it is also exactly what §2.3's previous-candle engine means when it says
    *"anticipate the same direction on the next candle"*.
    """
    out = report.shift(1)
    out["applies_to"] = report.index
    return out


def _resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample(tf, label="left", closed="left").agg(agg).dropna()
