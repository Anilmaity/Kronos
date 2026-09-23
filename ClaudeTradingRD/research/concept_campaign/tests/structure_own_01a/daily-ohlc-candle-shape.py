"""daily-ohlc-candle-shape (TTrades own voice, contested) -> two readings.

The concept: the ORDER in which a candle builds its extremes is the read -- open then low
first = bullish (O-L-H-C), open then high first = bearish (O-H-L-C). Most of it is applied
under an assumed bias (the draw on liquidity selects the shape), which this test does not
have; two parts are decidable from OHLC + M1 without a bias:

Declared before the first run:
  Common: 18:00-NY daily candles (canon; the older midnight-open recording is not used),
  stub sessions (<600 M1) dropped.
  reading a -- the tie-breaker (chart_lessons_01, Nlw-PZhoViQ 'it did open high, low close'):
    when a daily candle's close does not settle the direction -- it closes back inside the
    PREVIOUS day's range -- reconstruct the order of its extremes on M1 (time of the day's
    high vs time of its low). High made first -> bearish read for the next day, low first ->
    bullish, regardless of the close sign. trade_test, claim '+': trade the read from the
    next session open; stop = that day's extreme against the read (its high for a short --
    the wick that must be respected), target = its opposite extreme; max hold one session
    (23h of trading bars); controls drawn on the daily grid (18:00 session opens, +/-30 days).
    Days whose high and low print in the same M1 bar are skipped.
  reading b -- the no-information case (sdZkE-naNiY 'usually that means I don't really have
    much bias going into the day'): a DOJI daily closure yields no bias. gate_test, claim '-':
    baseline = the mechanical previous-candle daily bias book (method_spec §2.3: continuation
    closure -> same direction; took one side and closed back inside -> opposite; both sides /
    inside -> no trade), traded from the next session open, stop = the candle's extreme
    against the bias, target = its extreme in the bias direction, max hold one session.
    Gate = the bias candle is a doji: |close-open| <= 0.10 x (high-low).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, daily, show

CID = "daily-ohlc-candle-shape"
DOJI = 0.10
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "target_px", "doji"]


def extreme_times(m1: pd.DataFrame, d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per row of d: int64 ns time of the day's high and low M1 bars (first occurrence)."""
    td = cl.trading_day(m1.index)
    tn = np.asarray(cl.data.utc_ns(pd.DatetimeIndex(m1.index))).astype("datetime64[ns]").astype(np.int64)
    df = pd.DataFrame({"td": td, "h": m1["high"].to_numpy(float), "l": m1["low"].to_numpy(float),
                       "t": tn})
    g = df.groupby("td", sort=True)
    ih = g["h"].idxmax()
    il = g["l"].idxmin()
    th = pd.Series(tn[ih.to_numpy()], index=ih.index)
    tl = pd.Series(tn[il.to_numpy()], index=il.index)
    key = pd.DatetimeIndex(d["trading_day"])
    return th.reindex(key).to_numpy(), tl.reindex(key).to_numpy()


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS_A)
    H, L, C = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    th, tl = extreme_times(m1, d)
    settle_not = (C >= pl) & (C <= ph)
    ok = settle_not & (th != tl)
    sel = np.flatnonzero(ok)
    sgn = np.where(th[sel] < tl[sel], -1, 1)
    ct = pd.DatetimeIndex(d["close_time"])
    ev = pd.DataFrame({"decision_time": ct[sel], "available_at": ct[sel], "direction": sgn,
                       "stop_px": np.where(sgn < 0, H[sel], L[sel]),
                       "target_px": np.where(sgn < 0, L[sel], H[sel])})
    return ev[COLS_A].reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS_B)
    O, H, L, C = (d[c].to_numpy(float) for c in ("open", "high", "low", "close"))
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    took_h, took_l = H > ph, L < pl
    bull = (took_h & ~took_l & (C > ph)) | (took_l & ~took_h & (C >= pl))
    bear = (took_l & ~took_h & (C < pl)) | (took_h & ~took_l & (C <= ph))
    sel = np.flatnonzero(bull | bear)
    sgn = np.where(bull[sel], 1, -1)
    rng = H[sel] - L[sel]
    ct = pd.DatetimeIndex(d["close_time"])
    ev = pd.DataFrame({"decision_time": ct[sel], "available_at": ct[sel], "direction": sgn,
                       "stop_px": np.where(sgn > 0, L[sel], H[sel]),
                       "target_px": np.where(sgn > 0, H[sel], L[sel]),
                       "doji": (np.abs(C[sel] - O[sel]) <= DOJI * rng) & (rng > 0)})
    return ev[COLS_B].reset_index(drop=True)


COMMON_SRC = {"tf": "corpus: u8bnmaih_hA 'I am only looking to trade the daily open high low close'",
              "day_open": "method_spec: §1.4 daily open 18:00 canon [P] (midnight is the earlier recording)",
              "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
              "max_hold": "declared-before-run: one trading session (the next daily candle)",
              "hold_basis": "declared-before-run: trading-time hold (trap 7)",
              "grid4h": "declared-before-run: not used"}


def run_a():
    ev = cl.cache_frame("ohlc_a_order_tiebreak", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), "short", int((ev["direction"] < 0).sum()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="30D", recent="3D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="23h", hold_basis="bars", ctrl_grid="1D")
    show(res)
    op = {"rules": [
        "18:00-NY daily candles; stub sessions dropped",
        "only days whose close is back inside the previous day's range (close does not settle the direction)",
        "order of extremes from M1: day's high printed before its low -> bearish read; low first -> bullish; same M1 -> skip",
        "trade the read at the next session open; stop = that day's extreme against the read; target = its opposite extreme; "
        "max hold 23h trading bars; controls on the daily grid"],
        "params": {"tf": "1D", "day_open": "18:00 NY", "stub_min_m1": 600, "order_tf": "M1",
                   "stop": "day extreme against the read", "target": "day extreme with the read",
                   "max_hold": "23h", "hold_basis": "bars", "ctrl_grid": "1D", "grid4h": "n/a"}}
    src = dict(COMMON_SRC,
               order_tf="declared-before-run: ambiguity 'which lower timeframe' - M1 is the finest available, the hourly used in the video only approximates it",
               stop="corpus: sdZkE-naNiY 'does it open and respect one side of the wick' - the day's extreme against the read",
               target="method_spec: §2.3 previous-candle levels - the opposite extreme of the reference candle",
               ctrl_grid="declared-before-run: every entry is the 18:00 session open; controls on the same daily grid (trap 9)")
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading a: order-of-extremes tie-breaker on non-settling daily closes; no draw-on-liquidity bias available, so the shape read is traded by itself."))


def run_b():
    ev = cl.cache_frame("ohlc_b_doji_gate", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev), "doji", int(ev["doji"].sum()))
    probe = cl.probe_lookahead(detect_b, ev, lookback="30D", recent="3D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "doji", mask_available_at="decision_time", claim="-",
                       max_hold="23h", hold_basis="bars")
    show(res)
    op = {"rules": [
        "18:00-NY daily candles; stub sessions dropped",
        "baseline: previous-candle bias (continuation closure -> same way; one side taken and closed back inside -> opposite; "
        "both sides / inside -> none) traded at the next session open; stop = candle extreme against the bias; "
        "target = candle extreme with the bias; max hold 23h trading bars",
        f"gate: the bias candle is a doji, |close-open| <= {DOJI} x range",
        "claim '-': bias trades after a doji closure are worse (no information)"],
        "params": {"tf": "1D", "day_open": "18:00 NY", "stub_min_m1": 600, "doji_body_ratio": DOJI,
                   "bias": "previous-candle engine", "stop": "candle extreme against bias",
                   "target": "candle extreme with bias", "max_hold": "23h", "hold_basis": "bars",
                   "grid4h": "n/a"}}
    src = dict(COMMON_SRC,
               doji_body_ratio="declared-before-run: 'doji is never quantified' (ambiguities); body <= 10% of range",
               bias="method_spec: §2.3 previous-candle engine",
               stop="method_spec: §2.3/§3.8 the reference candle's opposite extreme as invalidation",
               target="method_spec: §2.3 continuation/reversal closure -> next candle reaches the candle's extreme")
    print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading b: 'a doji daily closure yields no bias' as a gate on the mechanical daily bias book."))


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        {"a": run_a, "b": run_b}[r]()
