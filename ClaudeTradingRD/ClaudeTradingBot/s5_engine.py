"""s5_engine.py — shared fill/cost engine for the 2026 full-year S5 (bid/ask) study.

ALL strategy candidates in this study MUST run through this engine so results
are comparable and fills are honest. Conventions:

  * Signals are decided on the CLOSE of bar i; execution begins at bar i+1.
  * Taker entry fills at next-bar open on the crossing side (buy=ask_o, sell=bid_o).
  * Maker entry posts a limit; a BUY limit at L fills only when bid_l < L
    (market traded down through it) — adverse selection is structural.
  * Exits (long): TP when bid_h >= tp, SL when bid_l <= sl. If both hit in the
    same bar, the SL is assumed to hit FIRST (worst case). Shorts mirrored on ask.
  * maker_exit=True: the TP is a resting limit — long TP fills when ask_h > tp
    (someone lifts the offer), earning the spread; SL is always taker.
  * Time exit at the close of the max-hold bar (taker, crossing the spread).
  * P&L: $100 per 1.0 price point per 1.0 lot (XAU contract size 100).
  * Commission: $ per lot round-trip (default 4.9 — the live account's real rate).

Data: reports/xau_s5_2026_mba.csv.gz  (time, volume, mid/bid/ask OHLC, complete)
"""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
S5_PATH = os.path.join(HERE, "reports", "xau_s5_2026_mba.csv.gz")
RESULTS_DIR = os.path.join(HERE, "reports", "s5_2026_results")

DOLLARS_PER_POINT_PER_LOT = 100.0
COMMISSION_PER_LOT_RT = 4.9

# canonical train/test split for the whole study — DO NOT tune on test
TRAIN_END = np.datetime64("2026-05-01T00:00:00")


_df_cache: dict = {}


def load_s5(path: str = S5_PATH) -> pd.DataFrame:
    """Load the S5 dataset once per process (parquet cache for fast reloads)."""
    if path in _df_cache:
        return _df_cache[path]
    pq = path.rsplit(".csv.gz", 1)[0] + ".parquet"
    if os.path.exists(pq):
        df = pd.read_parquet(pq)
    else:
        df = pd.read_csv(path, compression="gzip")
        df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
        df = df[df["complete"] == 1].drop(columns=["complete"])
        df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
        try:
            df.to_parquet(pq, index=False)
        except Exception:
            pass
    _df_cache[path] = df
    return df


def resample(df: pd.DataFrame, rule: str, price: str = "mid") -> pd.DataFrame:
    """Resample S5 to e.g. '1min','5min','15min','1h','4h','1D' on one price side."""
    x = df.set_index("time")
    o, h, l, c = (f"{price}_o", f"{price}_h", f"{price}_l", f"{price}_c")
    out = pd.DataFrame({
        "o": x[o].resample(rule).first(),
        "h": x[h].resample(rule).max(),
        "l": x[l].resample(rule).min(),
        "c": x[c].resample(rule).last(),
        "v": x["volume"].resample(rule).sum(),
    }).dropna()
    return out


@dataclass
class OrderIntent:
    """One intended trade, decided at the close of bar `signal_i`."""
    signal_i: int                 # index into the S5 frame; execution from signal_i+1
    side: str                     # 'buy' | 'sell'
    tp: float                     # absolute price
    sl: float                     # absolute price
    max_hold_bars: int            # S5 bars (720 = 1h, 17280 = 1 day)
    lot: float = 0.10
    entry_type: str = "taker"     # 'taker' | 'maker'
    limit_price: float = 0.0      # required for maker entries
    maker_exit: bool = False      # TP as resting limit
    entry_ttl_bars: int = 24      # maker: cancel unfilled limit after this many bars
    tag: str = ""                 # free-form label for analysis


@dataclass
class Fill:
    intent: OrderIntent
    entry_i: int
    exit_i: int
    entry_px: float
    exit_px: float
    exit_reason: str              # 'tp' | 'sl' | 'time' | 'eod'
    pnl: float                    # $ net of commission


def simulate(df: pd.DataFrame, intents: list[OrderIntent],
             commission_per_lot_rt: float = COMMISSION_PER_LOT_RT,
             sl_slippage_pts: float = 0.05,
             max_concurrent: int = 1,
             spread_model: float | str = 0.20) -> list[Fill]:
    """Simulate all intents against the S5 tape. Conservative fill rules (see module doc).

    max_concurrent: intents whose lifetime would overlap an open position are skipped
    (keeps equity-curve math honest for single-position strategies).

    spread_model — the study's primary cost decision:
      * float s (default 0.20): synthetic constant spread around the REAL mid path
        (bid = mid - s/2, ask = mid + s/2). Calibrated to the deployment venue
        (FundingPips-style raw feed ~0.2 pt + commission). The OANDA practice
        feed's own spread is ~1.0 pt median — NOT representative of the target
        broker, so it must not silently price the strategies.
      * "feed": use the real OANDA bid/ask columns as-is (worst-case robustness).
    """
    n = len(df)
    if spread_model == "feed":
        bid_o = df["bid_o"].values; bid_h = df["bid_h"].values
        bid_l = df["bid_l"].values; bid_c = df["bid_c"].values
        ask_o = df["ask_o"].values; ask_h = df["ask_h"].values
        ask_l = df["ask_l"].values; ask_c = df["ask_c"].values
    else:
        half = float(spread_model) / 2.0
        bid_o = df["mid_o"].values - half; bid_h = df["mid_h"].values - half
        bid_l = df["mid_l"].values - half; bid_c = df["mid_c"].values - half
        ask_o = df["mid_o"].values + half; ask_h = df["mid_h"].values + half
        ask_l = df["mid_l"].values + half; ask_c = df["mid_c"].values + half

    fills: list[Fill] = []
    busy_until = np.zeros(0)  # exit indices of open positions
    open_exits: list[int] = []

    for it in sorted(intents, key=lambda x: x.signal_i):
        start = it.signal_i + 1
        if start >= n:
            continue
        open_exits = [e for e in open_exits if e >= start]
        if len(open_exits) >= max_concurrent:
            continue

        long = it.side == "buy"

        # ── entry (vectorized first-touch scan) ──
        if it.entry_type == "taker":
            entry_i = start
            entry_px = ask_o[start] if long else bid_o[start]
        else:
            ttl_end = min(start + it.entry_ttl_bars, n)
            seg = bid_l[start:ttl_end] < it.limit_price if long else ask_h[start:ttl_end] > it.limit_price
            k = int(np.argmax(seg)) if seg.any() else -1
            if k < 0:
                continue  # never filled
            entry_i, entry_px = start + k, it.limit_price

        # ── exit scan (vectorized; worst-case: SL beats TP in the same bar) ──
        # Maker-entry bars are intra-bar ambiguous: the limit fills at an unknown
        # moment inside the bar, so a TP touch in that same bar may have printed
        # BEFORE the fill. Conservative rule (audit 2026-07-02): on the maker
        # entry bar only the SL may trigger; TP scanning starts one bar later.
        last = min(entry_i + it.max_hold_bars, n - 1)
        if long:
            sl_seg = bid_l[entry_i:last + 1] <= it.sl
            tp_seg = (ask_h[entry_i:last + 1] > it.tp) if it.maker_exit else (bid_h[entry_i:last + 1] >= it.tp)
        else:
            sl_seg = ask_h[entry_i:last + 1] >= it.sl
            tp_seg = (bid_l[entry_i:last + 1] < it.tp) if it.maker_exit else (ask_l[entry_i:last + 1] <= it.tp)
        if it.entry_type == "maker" and len(tp_seg):
            tp_seg[0] = False
        sl_k = int(np.argmax(sl_seg)) if sl_seg.any() else -1
        tp_k = int(np.argmax(tp_seg)) if tp_seg.any() else -1

        if sl_k >= 0 and (tp_k < 0 or sl_k <= tp_k):
            slip = -sl_slippage_pts if long else sl_slippage_pts
            exit_i, exit_px, reason = entry_i + sl_k, it.sl + slip, "sl"
        elif tp_k >= 0:
            exit_i, exit_px, reason = entry_i + tp_k, it.tp, "tp"
        else:
            exit_i, exit_px, reason = last, (bid_c[last] if long else ask_c[last]), "time"
        if exit_i == n - 1 and reason == "time":
            reason = "eod"

        pts = (exit_px - entry_px) if long else (entry_px - exit_px)
        pnl = pts * DOLLARS_PER_POINT_PER_LOT * it.lot - commission_per_lot_rt * it.lot
        fills.append(Fill(it, entry_i, exit_i, entry_px, exit_px, reason, round(pnl, 2)))
        open_exits.append(exit_i)

    return fills


def stats(df: pd.DataFrame, fills: list[Fill], label: str = "") -> dict:
    """Standard stat block. Also splits train (Jan–Apr) / test (May→) on entry time."""
    if not fills:
        return {"label": label, "trades": 0}
    t = df["time"].values
    pnl = np.array([f.pnl for f in fills])
    entry_t = np.array([t[f.entry_i] for f in fills])
    hold_s = np.array([(t[f.exit_i] - t[f.entry_i]) / np.timedelta64(1, "s") for f in fills])

    def block(mask):
        p = pnl[mask]
        if len(p) == 0:
            return {"trades": 0}
        wins = p[p > 0]; losses = p[p <= 0]
        eq = np.cumsum(p)
        dd = float((eq - np.maximum.accumulate(eq)).min())
        days = max(1e-9, (entry_t[mask].max() - entry_t[mask].min()) / np.timedelta64(1, "D"))
        return {
            "trades": int(len(p)),
            "win_rate": round(float(len(wins) / len(p)) * 100, 1),
            "net": round(float(p.sum()), 2),
            "expectancy": round(float(p.mean()), 3),
            "pf": round(float(wins.sum() / max(1e-9, -losses.sum())), 3) if len(losses) else float("inf"),
            "worst": round(float(p.min()), 2),
            "best": round(float(p.max()), 2),
            "max_dd": round(dd, 2),
            "trades_per_day": round(float(len(p) / days), 2),
            "median_hold_s": round(float(np.median(hold_s[mask])), 1),
            "exit_mix": {r: int(sum(1 for f, m in zip(fills, mask) if m and f.exit_reason == r))
                         for r in ("tp", "sl", "time", "eod")},
        }

    all_mask = np.ones(len(fills), bool)
    train_mask = entry_t < TRAIN_END
    return {
        "label": label,
        "full": block(all_mask),
        "train_jan_apr": block(train_mask),
        "test_may_jul": block(~train_mask),
    }


def save_result(name: str, payload: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path
