"""Order blocks and protected swings — both products of the CISD close.

The corpus constructs all three from one event: the close through the opposing
candle run simultaneously (a) confirms the CISD, (b) validates that run as the
order block / "opposing candle", and (c) protects the extreme beneath it. So this
module builds on `cisd.cisd_events` rather than re-deriving the structure, which
keeps the three concepts consistent by construction.

Ambiguities are exposed as parameters, never guessed. From
`concepts/structure/order-block.yaml`:

  * "The zone boundaries are not stated — whether it spans the bodies or the wicks
    of the series is never said."      -> `zone=`
  * "'Drawn liquidity' / 'objective' is the pivot of the mitigation rule but is
    never defined mechanically."       -> `objective` is supplied by the caller;
    there is no default, because inventing one would fabricate the rule.

From `concepts/structure/protected-swing.yaml`:

  * "There is separation between the swept level and the newly formed swing — a
    swing that forms at equal lows with the swept level is not tradeable away
    from."                             -> `min_separation=`
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cisd import cisd_events

ZONES = ("body", "wick")


def order_blocks(df: pd.DataFrame, zone: str = "body", **cisd_kw) -> pd.DataFrame:
    """Order blocks (the speaker's "opposing candles") from CISD events.

    zone="body" spans max/min of open&close across the run; zone="wick" spans the
    run's high/low. The corpus never says which, so both are offered.

    Returns one row per block with the zone bounds, the mean threshold (the 0.5
    level the corpus requires to hold on a retest), and the bar from which the
    block is valid (the CISD close).
    """
    if zone not in ZONES:
        raise ValueError(f"zone must be one of {ZONES}")
    ev = cisd_events(df, **cisd_kw)
    if ev.empty:
        return pd.DataFrame(columns=[
            "direction", "series_start", "series_end", "zone_low", "zone_high",
            "mean_threshold", "valid_from", "protected_swing", "zone"])

    rows = []
    for _, e in ev.iterrows():
        seg = df.loc[e["series_start"]:e["series_end"]]
        if seg.empty:
            continue
        if zone == "body":
            lo = float(np.minimum(seg["open"], seg["close"]).min())
            hi = float(np.maximum(seg["open"], seg["close"]).max())
        else:
            lo = float(seg["low"].min())
            hi = float(seg["high"].max())
        rows.append({
            "direction": e["direction"],
            "series_start": e["series_start"],
            "series_end": e["series_end"],
            "zone_low": lo,
            "zone_high": hi,
            "mean_threshold": (lo + hi) / 2.0,
            "valid_from": e["confirm_time"],
            "protected_swing": e["protected_swing"],
            "zone": zone,
        })
    return pd.DataFrame(rows).reset_index(drop=True)


def first_mitigation(df: pd.DataFrame, blocks: pd.DataFrame,
                     max_bars: int = 200) -> pd.DataFrame:
    """First return of price into each block after it became valid.

    Adds:
      mitigated_at        first bar trading inside the zone (NaT if none)
      bars_to_mitigation
      mean_threshold_held whether that bar respected the 0.5 level, i.e. for a
                          bullish block the low did not close past the midpoint.
                          The corpus requires this half to be respected on the
                          retest, so it is measured rather than assumed.
    """
    if blocks.empty:
        return blocks.assign(mitigated_at=pd.NaT, bars_to_mitigation=np.nan,
                             mean_threshold_held=pd.NA)

    idx = df.index
    pos_of = {t: i for i, t in enumerate(idx)}
    lows, highs, closes = (df["low"].to_numpy(), df["high"].to_numpy(),
                           df["close"].to_numpy())

    out = []
    for _, b in blocks.iterrows():
        start = pos_of.get(b["valid_from"])
        rec = {"mitigated_at": pd.NaT, "bars_to_mitigation": np.nan,
               "mean_threshold_held": pd.NA}
        if start is not None:
            stop = min(len(idx), start + 1 + max_bars)
            for j in range(start + 1, stop):
                inside = (lows[j] <= b["zone_high"]) and (highs[j] >= b["zone_low"])
                if inside:
                    if b["direction"] == "bullish":
                        held = bool(closes[j] >= b["mean_threshold"])
                    else:
                        held = bool(closes[j] <= b["mean_threshold"])
                    rec = {"mitigated_at": idx[j],
                           "bars_to_mitigation": j - start,
                           "mean_threshold_held": held}
                    break
        out.append(rec)
    return pd.concat([blocks.reset_index(drop=True),
                      pd.DataFrame(out)], axis=1)


def block_still_valid(block: pd.Series, now: pd.Timestamp,
                      objective_taken_at: pd.Timestamp | None) -> bool:
    """Apply the corpus's mitigation rule.

    "A block that has already been mitigated remains valid as long as the drawn
    liquidity / objective has NOT yet been taken. Once the objective has been
    reached, a re-tap is no longer a valid entry — this is the specific mistake he
    names as where people get stopped out."

    `objective_taken_at` must be supplied by the caller. The corpus never defines
    the objective mechanically, so this function will not invent one; passing None
    means "objective not yet taken".
    """
    if now < block["valid_from"]:
        return False
    if objective_taken_at is None:
        return True
    return now < objective_taken_at


def protected_swing_chain(df: pd.DataFrame, direction: str = "bullish",
                          min_separation: float = 0.0,
                          **cisd_kw) -> pd.DataFrame:
    """Ordered chain of protected swings, each superseding the last.

    The corpus uses protected swings three ways: the stop at entry, the qualifier
    that makes a candle-2 closure "ideal", and the trailing reference during
    management, where "each subsequent qualifying event creates a new, tighter
    protected swing that supersedes the previous one".

    `min_separation` implements the refusal rule: a swing forming at effectively
    equal levels with the one it swept "is not tradeable away from". Default 0.0
    disables it, because the corpus gives no tolerance — see the concept's
    `ambiguities`.
    """
    if direction not in ("bullish", "bearish"):
        raise ValueError("direction must be 'bullish' or 'bearish'")
    ev = cisd_events(df, **cisd_kw)
    ev = ev[ev["direction"] == direction].sort_values("confirm_time")
    if ev.empty:
        return pd.DataFrame(columns=["confirm_time", "protected_swing",
                                     "supersedes", "tighter"])

    rows, prev = [], None
    for _, e in ev.iterrows():
        lvl = float(e["protected_swing"])
        if prev is not None and abs(lvl - prev) < min_separation:
            continue          # no separation -> not tradeable away from
        tighter = (prev is None or
                   (lvl > prev if direction == "bullish" else lvl < prev))
        rows.append({"confirm_time": e["confirm_time"], "protected_swing": lvl,
                     "supersedes": prev, "tighter": tighter})
        prev = lvl
    return pd.DataFrame(rows).reset_index(drop=True)
