"""The TTrades Fractal Model candle sequence: C2 (reversal) and C3 (continuation).

From `concepts/model/fractal-model-c2.yaml` and `fractal-model-c3.yaml`, both
`contested`. C1 is deliberately absent: the corpus states it "is explicitly
arbitrary and is never analysed on its own", so modelling it would add a concept
the source does not have.

Contested points, exposed as parameters rather than resolved:

C2
  * "Whether the sweep must exceed the prior candle's extreme or merely a nearby
    liquidity pool is used inconsistently"        -> `sweep_ref` / `lookback`
  * "'Reversal shape' is judged visually; no ratio of wick to body is given"
                                                  -> `require_reversal_close`,
                                                     `max_body_ratio`
  * "Whether the sweep must be a wick or may be a body close outside"
                                                  -> `require_close_inside`
  * "A C2 with a small wick supports expansion; a large wick suggests a trade back
    to the opening price"                         -> `wick_ratio` is reported, and
                                                     `half_wick_level` gives the
                                                     0.5-of-wick level the corpus
                                                     says to expect price to reach

C3
  * sequential (must follow a confirmed C2) vs standalone (no sweep required,
    "provided the EQ is respected")               -> `mode`
  * "C3 must close beyond the open of C2" vs the standalone case explicitly not
    requiring it                                  -> `require_close_beyond_c2_open`
  * "wick in the relevant half ... a shallow wick supports expansion"
                                                  -> `require_wick_in_half`

Nothing here looks ahead: C2 is decided on its own close, C3 on its own close.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SWEEP_REFS = ("prior_candle", "lookback_extreme")
C3_MODES = ("sequential", "standalone")


def c2_events(df: pd.DataFrame, sweep_ref: str = "prior_candle",
              lookback: int = 5, require_close_inside: bool = True,
              require_reversal_close: bool = True,
              max_body_ratio: float | None = None) -> pd.DataFrame:
    """Candle-2 detections: a sweep of the reference extreme that closes back inside.

    sweep_ref="prior_candle"     sweep the immediately preceding candle's extreme.
    sweep_ref="lookback_extreme" sweep the extreme of the prior `lookback` candles
                                 (the "nearby liquidity pool" reading).

    Reported per detection:
      direction        'bullish' (swept the low) | 'bearish' (swept the high)
      ref_level        the level that was swept
      wick_ratio       the sweeping wick as a fraction of the candle's range.
                       The corpus ties this to what happens next: small wick ->
                       expansion; large wick -> expect a trade back to the open.
      half_wick_level  0.5 of the sweeping wick — the level the corpus says to
                       mark and expect price to reach when the wick is large.
      body_ratio       |close-open| / range, offered for `max_body_ratio`
                       filtering since no ratio is given in the source.
    """
    if sweep_ref not in SWEEP_REFS:
        raise ValueError(f"sweep_ref must be one of {SWEEP_REFS}")
    if df.empty:
        return _empty_c2()

    if sweep_ref == "prior_candle":
        ref_hi, ref_lo = df["high"].shift(1), df["low"].shift(1)
    else:
        ref_hi = df["high"].shift(1).rolling(lookback, min_periods=1).max()
        ref_lo = df["low"].shift(1).rolling(lookback, min_periods=1).min()

    o, h, l, c = (df["open"], df["high"], df["low"], df["close"])
    rng = (h - l).replace(0, np.nan)

    bull = l < ref_lo
    bear = h > ref_hi
    if require_close_inside:
        bull = bull & (c >= ref_lo)
        bear = bear & (c <= ref_hi)
    if require_reversal_close:
        # "open, extreme against the intended direction, then close in the
        # intended direction" -- approximated by the close direction, since the
        # source gives no intrabar sequence test.
        bull = bull & (c > o)
        bear = bear & (c < o)

    body_ratio = (c - o).abs() / rng
    lower_wick = (np.minimum(o, c) - l) / rng
    upper_wick = (h - np.maximum(o, c)) / rng

    rows = []
    for direction, mask, ref, wick in (("bullish", bull, ref_lo, lower_wick),
                                       ("bearish", bear, ref_hi, upper_wick)):
        sel = mask.fillna(False)
        if max_body_ratio is not None:
            sel = sel & (body_ratio <= max_body_ratio)
        for t in df.index[sel.values]:
            wr = float(wick.loc[t]) if pd.notna(wick.loc[t]) else float("nan")
            if direction == "bullish":
                half = float(df["low"].loc[t] + (min(o.loc[t], c.loc[t]) - df["low"].loc[t]) / 2)
            else:
                half = float(df["high"].loc[t] - (df["high"].loc[t] - max(o.loc[t], c.loc[t])) / 2)
            rows.append({
                "time": t, "direction": direction,
                "ref_level": float(ref.loc[t]),
                "open": float(o.loc[t]), "high": float(h.loc[t]),
                "low": float(l.loc[t]), "close": float(c.loc[t]),
                "wick_ratio": wr,
                "body_ratio": float(body_ratio.loc[t]) if pd.notna(body_ratio.loc[t]) else float("nan"),
                "half_wick_level": half,
                "sweep_ref": sweep_ref,
            })
    if not rows:
        return _empty_c2()
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def _empty_c2() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "time", "direction", "ref_level", "open", "high", "low", "close",
        "wick_ratio", "body_ratio", "half_wick_level", "sweep_ref"])


def c3_events(df: pd.DataFrame, mode: str = "sequential",
              require_close_beyond_c2_open: bool = True,
              require_wick_in_half: bool = False,
              **c2_kw) -> pd.DataFrame:
    """Candle-3 continuations.

    mode="sequential"  C3 is the candle immediately following a C2 detection, and
                       is expected to expand in the direction C2 reversed toward.
    mode="standalone"  The corpus's looser reading: "the candle does not need to
                       sweep the prior candle's extreme, and it does not need to
                       close beyond the opening price, provided the EQ is
                       respected". Here that is implemented as: the candle closes
                       beyond the previous candle's midpoint (its EQ) in the
                       trend direction, with no C2 required.

    `require_close_beyond_c2_open` applies the sequential reading's delivery test
    ("C3 must close beyond the open of C2"). The corpus explicitly waives it in
    the standalone case, so it is ignored there.
    """
    if mode not in C3_MODES:
        raise ValueError(f"mode must be one of {C3_MODES}")
    if df.empty:
        return _empty_c3()

    idx = df.index
    pos = {t: i for i, t in enumerate(idx)}
    rows = []

    if mode == "sequential":
        c2 = c2_events(df, **c2_kw)
        for _, e in c2.iterrows():
            i = pos[e["time"]]
            if i + 1 >= len(idx):
                continue
            t3 = idx[i + 1]
            b = df.loc[t3]
            bullish = e["direction"] == "bullish"
            delivered = (b["close"] > e["open"]) if bullish else (b["close"] < e["open"])
            if require_close_beyond_c2_open and not delivered:
                continue
            rng = b["high"] - b["low"]
            if rng <= 0:
                continue
            # "wick in the relevant half": for a bullish continuation the
            # counter-directional (lower) wick should stay shallow, i.e. the body
            # sits in the upper half.
            wick = ((min(b["open"], b["close"]) - b["low"]) / rng if bullish
                    else (b["high"] - max(b["open"], b["close"])) / rng)
            if require_wick_in_half and wick > 0.5:
                continue
            rows.append({
                "time": t3, "direction": e["direction"], "mode": mode,
                "c2_time": e["time"], "c2_open": e["open"],
                "close": float(b["close"]), "counter_wick_ratio": float(wick),
                "delivered_beyond_c2_open": bool(delivered),
            })
    else:
        prev_mid = ((df["high"] + df["low"]) / 2).shift(1)
        up = df["close"] > prev_mid
        dn = df["close"] < prev_mid
        for direction, mask in (("bullish", up), ("bearish", dn)):
            for t in idx[mask.fillna(False).values]:
                b = df.loc[t]
                rng = b["high"] - b["low"]
                if rng <= 0:
                    continue
                bullish = direction == "bullish"
                wick = ((min(b["open"], b["close"]) - b["low"]) / rng if bullish
                        else (b["high"] - max(b["open"], b["close"])) / rng)
                if require_wick_in_half and wick > 0.5:
                    continue
                rows.append({
                    "time": t, "direction": direction, "mode": mode,
                    "c2_time": pd.NaT, "c2_open": np.nan,
                    "close": float(b["close"]), "counter_wick_ratio": float(wick),
                    "delivered_beyond_c2_open": pd.NA,
                })
    if not rows:
        return _empty_c3()
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def _empty_c3() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "time", "direction", "mode", "c2_time", "c2_open", "close",
        "counter_wick_ratio", "delivered_beyond_c2_open"])
