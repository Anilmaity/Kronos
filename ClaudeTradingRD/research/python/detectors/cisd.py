"""CISD — Change In State Of Delivery — the corpus's central confirmation event.

Faithful to `concepts/entry/cisd.yaml`, including its `contested` status. The
corpus gives three readings of WHICH level price must close through, and the
speakers disagree explicitly (one rejects the opening-price rule by name). Rather
than silently picking one, `level_rule` selects the reading, so a backtest can
decide empirically which one carries an edge.

The shared skeleton all readings agree on:
  1. Find the extreme the reversal turned on (a low for bullish, a high for bearish).
  2. Identify the CONTIGUOUS RUN of same-direction-close candles that produced it
     -- down-close candles at a low, up-close candles at a high. The corpus is
     emphatic that this is a *series*, never a single candle, though it also
     accepts a series of length one in some walkthroughs; `min_series` exposes that.
  3. Require a later candle to CLOSE back through a level derived from that run.
  4. That close simultaneously creates a protected swing at the extreme, and marks
     the run as the opposing-candle / order block that may be retested.

Level readings (`level_rule`):
  "series_open"     close beyond the OPEN of the FIRST candle of the run.
  "series_extreme"  close beyond the run's opposite extreme (its high for a
                    bullish case, its low for a bearish case). The strictest.
  "series_close"    close beyond the CLOSE of the last candle of the run. The
                    loosest; included because one reading rejects the opening-
                    price requirement without naming a replacement.

No look-ahead: an event's confirming bar is always strictly after both the
extreme's swing confirmation and the end of the run.
"""
from __future__ import annotations

import pandas as pd

from .primitives import swing_points

LEVEL_RULES = ("series_open", "series_extreme", "series_close")

EVENT_COLUMNS = [
    "direction", "extreme_time", "extreme_price", "series_start", "series_end",
    "series_len", "level_rule", "level", "confirm_time", "confirm_close",
    "bars_waited", "protected_swing",
]


def _empty_events() -> pd.DataFrame:
    """Empty result that still carries the full schema.

    Returning a bare DataFrame() instead made every downstream consumer raise
    KeyError on an empty input, which is a silly way to fail.
    """
    return pd.DataFrame(columns=EVENT_COLUMNS)


def _run_into_extreme(df: pd.DataFrame, i: int, bullish: bool,
                      max_len: int = 10) -> tuple[int, int]:
    """Contiguous run of same-direction-close candles producing the extreme at i.

    Bullish case (a low): down-close candles (close < open).
    Bearish case (a high): up-close candles (close > open).
    Returns (start, end) inclusive positional indices. The run always includes i
    itself when i qualifies; otherwise it is the run ending at i.
    """
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()

    def qualifies(k: int) -> bool:
        return (c[k] < o[k]) if bullish else (c[k] > o[k])

    end = i
    # The extreme bar itself may be the turn candle (opposite direction); if so the
    # run is the one immediately preceding it.
    while end > 0 and not qualifies(end):
        end -= 1
        if i - end > 2:          # the turn is too far from any qualifying run
            return (-1, -1)
    if not qualifies(end):
        return (-1, -1)
    start = end
    while start > 0 and qualifies(start - 1) and (end - start + 1) < max_len:
        start -= 1
    return (start, end)


def _level(df: pd.DataFrame, start: int, end: int, bullish: bool,
           rule: str) -> float:
    if rule == "series_open":
        return float(df["open"].iloc[start])
    if rule == "series_close":
        return float(df["close"].iloc[end])
    if rule == "series_extreme":
        seg = df.iloc[start:end + 1]
        return float(seg["high"].max() if bullish else seg["low"].min())
    raise ValueError(f"level_rule must be one of {LEVEL_RULES}")


def cisd_events(df: pd.DataFrame, level_rule: str = "series_open",
                left: int = 2, right: int = 2, max_wait: int = 40,
                min_series: int = 1, max_series: int = 10) -> pd.DataFrame:
    """Detect CISD confirmations.

    Returns one row per confirmed event:
      direction        'bullish' | 'bearish'
      extreme_time     the swing the reversal turned on
      extreme_price
      series_start/end times of the opposing-candle run
      series_len
      level            the price that had to be closed through
      confirm_time     the bar that closed through it (the CISD)
      confirm_close
      bars_waited      confirm bar minus run end
      protected_swing  the extreme, which the close protects

    `max_wait` bounds how long after the extreme a closure still counts; without
    it a distant, unrelated close would be attributed to a stale swing.
    """
    if level_rule not in LEVEL_RULES:
        raise ValueError(f"level_rule must be one of {LEVEL_RULES}")
    if df.empty:
        return _empty_events()

    sw = swing_points(df, left=left, right=right)
    close = df["close"].to_numpy()
    idx = df.index
    n = len(df)
    rows = []

    for bullish, col in ((True, "swing_low"), (False, "swing_high")):
        for pos in range(n):
            if not sw[col].iloc[pos]:
                continue
            start, end = _run_into_extreme(df, pos, bullish, max_len=max_series)
            if start < 0 or (end - start + 1) < min_series:
                continue
            lvl = _level(df, start, end, bullish, level_rule)
            # Scan begins after BOTH the run ends and the swing is confirmable.
            begin = max(end, pos + right) + 1
            stop = min(n, begin + max_wait)
            for j in range(begin, stop):
                closed_through = close[j] > lvl if bullish else close[j] < lvl
                if closed_through:
                    rows.append({
                        "direction": "bullish" if bullish else "bearish",
                        "extreme_time": idx[pos],
                        "extreme_price": float(df["low"].iloc[pos] if bullish
                                               else df["high"].iloc[pos]),
                        "series_start": idx[start],
                        "series_end": idx[end],
                        "series_len": end - start + 1,
                        "level_rule": level_rule,
                        "level": lvl,
                        "confirm_time": idx[j],
                        "confirm_close": float(close[j]),
                        "bars_waited": j - end,
                        "protected_swing": float(df["low"].iloc[pos] if bullish
                                                 else df["high"].iloc[pos]),
                    })
                    break

    if not rows:
        return _empty_events()
    return (pd.DataFrame(rows)
            .sort_values("confirm_time")
            .reset_index(drop=True))


def compare_level_rules(df: pd.DataFrame, **kw) -> pd.DataFrame:
    """Run all three contested readings side by side.

    The point of the concept being `contested` is that nobody in the corpus
    settles it; this makes the disagreement measurable instead of theoretical.
    """
    out = []
    for rule in LEVEL_RULES:
        ev = cisd_events(df, level_rule=rule, **kw)
        out.append({
            "level_rule": rule,
            "events": len(ev),
            "bullish": int((ev["direction"] == "bullish").sum()) if len(ev) else 0,
            "bearish": int((ev["direction"] == "bearish").sum()) if len(ev) else 0,
            "median_series_len": float(ev["series_len"].median()) if len(ev) else float("nan"),
            "median_bars_waited": float(ev["bars_waited"].median()) if len(ev) else float("nan"),
        })
    return pd.DataFrame(out)
