"""The point-of-interest gate — `meta/ttrades_method_spec.md` §4.1.

**"Without a POI, no candle closure and no CISD is valid"** (`point-of-interest`).
This module is that sentence, made decidable.

What the spec actually specifies, and what this module therefore implements:

* **The enumeration.** A POI is *a fair value gap, a high being taken out, or a
  low being taken out* — "I use fair value gaps and highs and lows". Two
  extensions: a **series of opposing candles** may serve as one ("more advanced"),
  and where neither an FVG nor a sweepable extreme exists, **0.5 of the opposing
  candle** is used.
* **The search order within a range** (from the reversal point to the current
  extreme): (1) is there an FVG? (2) if not, is there a swing high/low to be
  taken? (3) only if neither, use the CISD level, *and additionally* require 50%
  of the bodies of that opposing series to hold. If **both** an FVG and a swing
  exist, require **both** to be tagged.
* **Density scaling** (`poi-density-by-timeframe`): six 4-hour candles a day means
  a 4-hour candle without a POI is acceptable; ~24 hourly candles means on the
  hourly a POI is *required* — it is the filter that says which of them matters.
* **Reversal vs continuation:** the requirement is mandatory for a reversal and
  **waived for a continuation**.

**THE GATE IS A SWITCH, NOT A HARD-WIRED PRECONDITION.** `meta/external_crossref.md`
§1c found the POI requirement to be *this channel's* tightening rather than the
general definition of CISD: one outside implementation requires the sweep, another
states explicitly that it is a quality filter and not definitional, and two more do
not mention it. It is also the single biggest frequency lever in the whole model.
So `enabled=` exists on every entry point and downstream code is expected to report
every statistic **both ways**.

Two things §4.1 leaves open, carried here as parameters with documented defaults
rather than silent choices:

* **[GAP] "relevant level" / "key level" is never defined.** Only two decay rules
  are given (a level already traded through stops being relevant; reaching a level
  is not enough — price must actually reverse off it). `relevant_levels()` therefore
  takes the levels from the caller; §2.7 `relevant-level` supplies the one attested
  default, "previous day and previous week extremes always qualify".
* **[GAP] FVG polarity is never stated.** The corpus says "a fair value gap",
  full stop. `fvg_polarity="any"` is the literal default.

No look-ahead: every candidate is derived from bars at or before the extreme it is
being asked to justify, and "tagged" is decided on the extreme bar's own excursion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .primitives import fair_value_gaps, swing_points

POI_KINDS = ("fvg", "swing", "cisd_level")
SETUP_TYPES = ("reversal", "continuation")
FVG_POLARITIES = ("any", "aligned", "opposing")

# Candles per day, used by the density rule. The spec names exactly two points on
# this curve — 4-hour (6/day, POI optional) and hourly (~24/day, POI required) —
# so any default cut must sit between them. 12.0 is the midpoint in candles/day.
TF_CANDLES_PER_DAY = {
    "1D": 1.0, "1d": 1.0, "D": 1.0,
    "4h": 6.0, "4H": 6.0,
    "1h": 24.0, "1H": 24.0, "h": 24.0,
    "30min": 48.0, "15min": 96.0, "5min": 288.0, "1min": 1440.0,
}
POI_REQUIRED_ABOVE_DENSITY = 12.0        # [GAP]-derived: see note above


@dataclass
class PoiResult:
    """Outcome of the gate for one candidate event.

    `required` and `passed` are deliberately separate. A 4-hour candle with no POI
    is a *pass with no POI* (required=False, passed=True, kind_used=None), which is
    a different animal from an hourly candle that found one. Downstream frequency
    accounting needs to tell those apart.
    """
    passed: bool
    required: bool
    setup_type: str
    kinds_found: tuple = ()
    kinds_required: tuple = ()
    kind_used: str | None = None
    level: float = float("nan")
    reason: str = ""
    detail: dict = field(default_factory=dict)


# ── helpers ───────────────────────────────────────────────────────────────────
def _pos(df: pd.DataFrame, when) -> int:
    """Positional index for a Timestamp, or pass an int straight through."""
    if isinstance(when, (int, np.integer)):
        return int(when)
    return int(df.index.get_indexer([pd.Timestamp(when)])[0])


def _validate_direction(direction: str) -> bool:
    if direction not in ("bullish", "bearish"):
        raise ValueError("direction must be 'bullish' or 'bearish'")
    return direction == "bullish"


def range_from_swing(df: pd.DataFrame, extreme, direction: str,
                     lookback: int = 40, left: int = 2, right: int = 2) -> int:
    """The "reversal point" that opens §4.1's search range.

    The spec phrases the range as *from the reversal point to the current extreme*
    but never says how the reversal point is found. The reading implemented here is
    the structural one: the most recent **opposing** swing before the extreme —
    for a bullish case (extreme = a low), the last swing high above it. Falls back
    to `extreme - lookback` when no such swing exists inside the window, so the
    range is always well defined.
    """
    bullish = _validate_direction(direction)
    e = _pos(df, extreme)
    lo = max(0, e - lookback)
    if e - lo < left + right + 1:
        return lo
    sw = swing_points(df.iloc[lo:e + 1], left=left, right=right)
    col = "swing_high" if bullish else "swing_low"
    hits = np.flatnonzero(sw[col].to_numpy())
    return lo + int(hits[-1]) if len(hits) else lo


# ── candidate finders ─────────────────────────────────────────────────────────
def fvg_pois(df: pd.DataFrame, start, end, direction: str,
             polarity: str = "any", min_size: float = 0.0,
             tag_tolerance: float = 0.0) -> list[dict]:
    """Fair-value-gap POIs inside [start, end], and whether the extreme tagged them.

    "Tagged" means the extreme bar's excursion reached into the gap zone — for a
    bullish case the bar's low trades at or below the gap's top. A gap that merely
    *exists* in the range is not a POI the market used; §4.1's both-must-be-tagged
    clause only makes sense on the engagement reading.

    polarity  "any"       every gap in the range (the literal corpus reading; [GAP])
              "aligned"   gaps in the setup's direction (bullish setup -> bullish FVG)
              "opposing"  gaps left by the leg being faded (bullish setup -> bearish FVG)
    """
    if polarity not in FVG_POLARITIES:
        raise ValueError(f"polarity must be one of {FVG_POLARITIES}")
    bullish = _validate_direction(direction)
    s, e = _pos(df, start), _pos(df, end)
    if e <= s:
        return []
    # Only the two bars before the range matter to a 3-bar FVG, so compute on a
    # window rather than on all history. Identical results, and it turns the whole
    # gate from O(n) per call into O(range).
    w0 = max(0, s - 2)
    g = fair_value_gaps(df.iloc[w0:e + 1])
    seg = g.iloc[s - w0:]
    if polarity == "aligned":
        mask = seg["bullish_fvg"] if bullish else seg["bearish_fvg"]
    elif polarity == "opposing":
        mask = seg["bearish_fvg"] if bullish else seg["bullish_fvg"]
    else:
        mask = seg["bullish_fvg"] | seg["bearish_fvg"]
    mask = mask & (seg["gap_size"] > min_size)

    ext_low = float(df["low"].iloc[e])
    ext_high = float(df["high"].iloc[e])
    out = []
    for t, row in seg[mask.to_numpy()].iterrows():
        glo, ghi = float(row["gap_low"]), float(row["gap_high"])
        # The level marked is the edge price reaches first coming from the extreme.
        level = ghi if bullish else glo
        tagged = (ext_low <= ghi + tag_tolerance) if bullish \
            else (ext_high >= glo - tag_tolerance)
        out.append({"kind": "fvg", "time": t, "level": level,
                    "gap_low": glo, "gap_high": ghi, "tagged": bool(tagged)})
    return out


def swing_pois(df: pd.DataFrame, start, end, direction: str,
               left: int = 2, right: int = 2,
               tag_tolerance: float = 0.0) -> list[dict]:
    """Swing-extreme POIs: "a high being taken out, or a low being taken out".

    For a bullish setup the POI is a swing **low** below, which the extreme takes
    out. Only swings that were confirmable strictly before the extreme bar count,
    so nothing here can see forward.
    """
    bullish = _validate_direction(direction)
    s, e = _pos(df, start), _pos(df, end)
    if e <= s:
        return []
    # Same windowing argument as fvg_pois: a swing at p only consults p-left..p+right.
    w0 = max(0, s - left)
    sw = swing_points(df.iloc[w0:e + 1], left=left, right=right)
    col = "swing_low" if bullish else "swing_high"
    price_col = "low" if bullish else "high"
    ext = float(df[price_col].iloc[e])
    flags = sw[col].to_numpy()

    out = []
    for p in range(s, e):
        if not bool(flags[p - w0]):
            continue
        if p + right >= e:            # not confirmable before the extreme printed
            continue
        lvl = float(df[price_col].iloc[p])
        tagged = (ext < lvl + tag_tolerance) if bullish else (ext > lvl - tag_tolerance)
        out.append({"kind": "swing", "time": df.index[p], "level": lvl,
                    "tagged": bool(tagged)})
    return out


def cisd_level_poi(df: pd.DataFrame, start, end, direction: str,
                   level_rule: str = "series_open", max_series: int = 10,
                   require_body_half_hold: bool = True,
                   body_hold_bars: int = 5) -> dict | None:
    """Branch (3): the CISD level of the opposing series, plus the 50%-body test.

    §4.1: *"only if neither, use the CISD level, and additionally require 50% of
    the bodies of that opposing series to hold."* The series is the contiguous run
    of opposing-close candles that produced the extreme — the same object
    `cisd.py` builds — and the extra condition implemented here is that within
    `body_hold_bars` after the run no candle **closes** through the midpoint of the
    run's body span in the adverse direction.

    This is also where §4.1's "0.5 of the opposing candle" fallback lands: with a
    run of length one the body midpoint *is* 0.5 of that candle's body.

    `level_rule` mirrors `cisd.LEVEL_RULES`; first-candle-open is the spec's
    sensible default (§4.2 [P]).
    """
    bullish = _validate_direction(direction)
    s, e = _pos(df, start), _pos(df, end)
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()

    def qualifies(k: int) -> bool:
        return (c[k] < o[k]) if bullish else (c[k] > o[k])

    end_i = e
    while end_i > s and not qualifies(end_i):
        end_i -= 1
    if end_i <= s or not qualifies(end_i):
        return None
    start_i = end_i
    while start_i > s and qualifies(start_i - 1) and (end_i - start_i + 1) < max_series:
        start_i -= 1

    seg = df.iloc[start_i:end_i + 1]
    if level_rule == "series_open":
        level = float(seg["open"].iloc[0])
    elif level_rule == "series_close":
        level = float(seg["close"].iloc[-1])
    elif level_rule == "series_extreme":
        level = float(seg["high"].max() if bullish else seg["low"].min())
    else:
        raise ValueError("level_rule must be series_open/series_close/series_extreme")

    body_hi = float(np.maximum(seg["open"], seg["close"]).max())
    body_lo = float(np.minimum(seg["open"], seg["close"]).min())
    body_half = (body_hi + body_lo) / 2.0

    # "50% of the bodies ... hold": read as the body midpoint being reclaimed by a
    # CLOSE in the setup's direction within a short window. Bodies, not wicks, is
    # the corpus's own distinction (`wick-vs-body-marking-rule`: bodies must respect
    # the level, wicks may trade into it), so the test is on closes.
    held = True
    if require_body_half_hold:
        j0, j1 = end_i + 1, min(len(df), end_i + 1 + body_hold_bars)
        fwd = c[j0:j1]
        held = bool((fwd > body_half).any()) if bullish else bool((fwd < body_half).any())

    # The body-hold test looks FORWARD of the series by design — you wait to see
    # whether the level holds. `last_bar_used` records how far forward, so callers
    # can compute honestly when this verdict was actually available.
    last_used = min(len(df) - 1, end_i + body_hold_bars) if require_body_half_hold \
        else end_i
    return {"kind": "cisd_level", "time": df.index[start_i], "level": level,
            "series_start": df.index[start_i], "series_end": df.index[end_i],
            "series_len": end_i - start_i + 1,
            "body_half": body_half, "body_half_held": bool(held),
            "last_bar_used": df.index[last_used],
            "tagged": bool(held) if require_body_half_hold else True}


def pois_in_range(df: pd.DataFrame, start, end, direction: str, **kw) -> pd.DataFrame:
    """Every candidate in the range, in §4.1's search order, as one frame.

    Diagnostic sibling of `poi_gate`: useful for counting what exists before asking
    whether the gate passes.
    """
    fvg_kw = {k: kw[k] for k in ("polarity", "min_size", "tag_tolerance") if k in kw}
    sw_kw = {k: kw[k] for k in ("left", "right", "tag_tolerance") if k in kw}
    cisd_kw = {k: kw[k] for k in ("level_rule", "max_series", "require_body_half_hold",
                                  "body_hold_bars") if k in kw}
    rows = fvg_pois(df, start, end, direction, **fvg_kw)
    rows += swing_pois(df, start, end, direction, **sw_kw)
    c = cisd_level_poi(df, start, end, direction, **cisd_kw)
    if c is not None:
        rows.append(c)
    if not rows:
        return pd.DataFrame(columns=["kind", "time", "level", "tagged"])
    out = pd.DataFrame(rows)
    lead = ["kind", "time", "level", "tagged"]
    return out[lead + [c for c in out.columns if c not in lead]]


# ── the gate ──────────────────────────────────────────────────────────────────
def poi_required(timeframe: str | None, setup_type: str = "reversal",
                 enabled: bool = True,
                 waive_for_continuation: bool = True,
                 density_cut: float = POI_REQUIRED_ABOVE_DENSITY) -> bool:
    """Is the gate required at all? Three independent off-switches, in order.

    1. `enabled=False` — the master switch (see the module docstring).
    2. continuation setups — §4.1 waives the requirement outright.
    3. density — a 4-hour candle without a POI is acceptable; an hourly one is not.
    """
    if not enabled:
        return False
    if setup_type not in SETUP_TYPES:
        raise ValueError(f"setup_type must be one of {SETUP_TYPES}")
    if setup_type == "continuation" and waive_for_continuation:
        return False
    if timeframe is None:
        return True
    density = TF_CANDLES_PER_DAY.get(timeframe)
    if density is None:
        raise ValueError(f"unknown timeframe {timeframe!r}; add it to TF_CANDLES_PER_DAY")
    return density >= density_cut


def poi_gate(df: pd.DataFrame, extreme, direction: str, *,
             range_start=None, lookback: int = 40,
             setup_type: str = "reversal", timeframe: str | None = None,
             enabled: bool = True, waive_for_continuation: bool = True,
             density_cut: float = POI_REQUIRED_ABOVE_DENSITY,
             require_both_when_both_exist: bool = True,
             polarity: str = "any", min_size: float = 0.0,
             tag_tolerance: float = 0.0, left: int = 2, right: int = 2,
             level_rule: str = "series_open",
             require_body_half_hold: bool = True,
             body_hold_bars: int = 5) -> PoiResult:
    """Evaluate §4.1 for one candidate extreme. This is the entry point.

    The ordering is exactly the spec's: FVG first; swing only if there is no FVG;
    the CISD level only if there is neither; and if an FVG *and* a swing both exist,
    both must be tagged.
    """
    _validate_direction(direction)
    e = _pos(df, extreme)
    s = _pos(df, range_start) if range_start is not None else \
        range_from_swing(df, e, direction, lookback=lookback, left=left, right=right)

    required = poi_required(timeframe, setup_type, enabled,
                            waive_for_continuation, density_cut)

    fvgs = fvg_pois(df, s, e, direction, polarity=polarity, min_size=min_size,
                    tag_tolerance=tag_tolerance)
    swings = swing_pois(df, s, e, direction, left=left, right=right,
                        tag_tolerance=tag_tolerance)
    has_fvg, has_swing = bool(fvgs), bool(swings)
    kinds_found = tuple(k for k, present in
                        (("fvg", has_fvg), ("swing", has_swing)) if present)

    # `last_bar_used` starts at the extreme: the FVG and swing branches never look
    # past it. The CISD branch can, and updates this below.
    detail = {"range_start": df.index[s], "extreme": df.index[e],
              "n_fvg": len(fvgs), "n_swing": len(swings),
              "last_bar_used": df.index[e]}

    if has_fvg and has_swing:
        kinds_required = ("fvg", "swing")
        fvg_ok = any(p["tagged"] for p in fvgs)
        swing_ok = any(p["tagged"] for p in swings)
        passed_search = fvg_ok and swing_ok
        used = "fvg+swing" if passed_search else None
        level = max((p["level"] for p in fvgs if p["tagged"]), default=float("nan")) \
            if passed_search else float("nan")
        reason = "both an FVG and a swing exist; both tagged" if passed_search \
            else f"both exist but tagged fvg={fvg_ok} swing={swing_ok}"
    elif has_fvg:
        kinds_required = ("fvg",)
        passed_search = any(p["tagged"] for p in fvgs)
        used = "fvg" if passed_search else None
        level = next((p["level"] for p in fvgs if p["tagged"]), float("nan"))
        reason = "FVG tagged" if passed_search else "FVG present but not tagged"
    elif has_swing:
        kinds_required = ("swing",)
        passed_search = any(p["tagged"] for p in swings)
        used = "swing" if passed_search else None
        level = next((p["level"] for p in swings if p["tagged"]), float("nan"))
        reason = "swing taken out" if passed_search else "swing present but not taken"
    else:
        kinds_required = ("cisd_level",)
        c = cisd_level_poi(df, s, e, direction, level_rule=level_rule,
                           require_body_half_hold=require_body_half_hold,
                           body_hold_bars=body_hold_bars)
        if c is None:
            passed_search, used, level = False, None, float("nan")
            reason = "no FVG, no swing, no opposing series"
        else:
            passed_search = bool(c["tagged"])
            used = "cisd_level" if passed_search else None
            level = c["level"]
            detail["body_half"] = c["body_half"]
            detail["series_len"] = c["series_len"]
            detail["last_bar_used"] = max(detail["last_bar_used"],
                                          c["last_bar_used"])
            reason = ("CISD level with 50% of series bodies holding" if passed_search
                      else "CISD level found but 50% of series bodies did not hold")

    if not require_both_when_both_exist and has_fvg and has_swing:
        # The looser reading: either one suffices. Off by default because the
        # both-clause is stated outright in §4.1 and is the tighter of the two.
        fvg_ok = any(p["tagged"] for p in fvgs)
        swing_ok = any(p["tagged"] for p in swings)
        passed_search = fvg_ok or swing_ok
        kinds_required = ("fvg|swing",)
        used = "fvg" if fvg_ok else ("swing" if swing_ok else None)
        level = (next((p["level"] for p in fvgs if p["tagged"]), float("nan"))
                 if fvg_ok else
                 next((p["level"] for p in swings if p["tagged"]), float("nan")))
        reason = "either an FVG or a swing tagged (loose reading)"

    passed = passed_search if required else True
    if not required:
        reason = ("gate disabled" if not enabled else
                  "waived: continuation" if setup_type == "continuation" else
                  f"waived: density of {timeframe} below cut") + \
            f" (search would have said {passed_search})"

    return PoiResult(passed=passed, required=required, setup_type=setup_type,
                     kinds_found=kinds_found, kinds_required=kinds_required,
                     kind_used=used, level=float(level), reason=reason,
                     detail=detail)


def poi_gate_events(df: pd.DataFrame, events: pd.DataFrame, *,
                    time_col: str = "extreme_time",
                    direction_col: str = "direction",
                    setup_col: str | None = None,
                    **kw) -> pd.DataFrame:
    """Annotate an events frame (e.g. `cisd.cisd_events`) with the gate's verdict.

    Adds `poi_passed`, `poi_required`, `poi_kind`, `poi_level`, `poi_kinds_found`.
    The frame is returned as a copy; nothing is dropped, because the whole point of
    the switch is that downstream code reports counts with and without it.
    """
    if events.empty:
        out = events.copy()
        for c in ("poi_passed", "poi_required", "poi_kind", "poi_level",
                  "poi_kinds_found"):
            out[c] = pd.Series(dtype="object")
        return out
    rows = []
    for _, ev in events.iterrows():
        setup = ev[setup_col] if setup_col else kw.get("setup_type", "reversal")
        res = poi_gate(df, ev[time_col], ev[direction_col],
                       **{**kw, "setup_type": setup})
        rows.append({"poi_passed": res.passed, "poi_required": res.required,
                     "poi_kind": res.kind_used, "poi_level": res.level,
                     "poi_kinds_found": ",".join(res.kinds_found)})
    out = events.copy().reset_index(drop=True)
    return pd.concat([out, pd.DataFrame(rows)], axis=1)


def firing_rate(df: pd.DataFrame, events: pd.DataFrame, **kw) -> dict:
    """Standalone + marginal firing statistics for the gate, both ways.

    `both_ways` is the point: `pass_rate_enabled` is what the gate costs in sample
    size, `n` is what you keep with it switched off.
    """
    ann = poi_gate_events(df, events, **kw)
    n = len(ann)
    if n == 0:
        return {"n": 0}
    passed = int(ann["poi_passed"].sum())
    required = int(ann["poi_required"].sum())
    return {
        "n": n,
        "n_required": required,
        "n_passed": passed,
        "pass_rate": round(passed / n, 4),
        "pass_rate_among_required": round(
            float(ann.loc[ann["poi_required"], "poi_passed"].mean()), 4)
        if required else float("nan"),
        "kind_mix": ann["poi_kind"].value_counts(dropna=False).to_dict(),
    }
