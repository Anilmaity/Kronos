"""S93 + Order Block entry model — signal expansion test (M5).

OB spec (ict-smc-strategy-design, adapted to S93 geometry):
  BOS: close[k] breaks the prior 5-bar extreme AND |close-open| >= dispm x ATR14.
  OB : last opposite-color candle in the 10 bars before k; zone [open, close].
  Entry at zone midpoint on first retrace within 12 bars; cancel if the probe
  pierces the stop first. Stop beyond zone far side - 0.2xATR. TP 1.5R.
Guards shared with the validated S93 set: killzones, SOFT M15 structure veto,
zone size <= 1.5xATR. One position at a time (busy_until), FVG takes priority
on bars where both fire.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRATCH = Path(__file__).parent
sys.path.insert(0, str(SCRATCH))

from s93_struct_validate import (  # noqa: E402
    KZ, load, m15_structure_on_m5, split_summary, fmt,
)
from optimize_manager_strategies import Trade, atr_np, walk_exit  # noqa: E402


def wilder_rsi_np(close: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(close)
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    ag = gain.ewm(alpha=1.0 / n, adjust=False).mean()
    al = loss.ewm(alpha=1.0 / n, adjust=False).mean().replace(0.0, 1e-12)
    return (100.0 - 100.0 / (1.0 + ag / al)).to_numpy()


def run_combo(m5, *, models=("fvg", "ob"), min_fvg_atr=0.3, dispm=1.0,
              ob_lookback=10, retrace_w=12, tp_r=1.5, buf_atr=0.2, atr_n=14,
              hold_bars=24, hours=KZ, cost=0.45,
              struct: np.ndarray | None = None,
              max_gap_atr: float | None = 1.5,
              rsi_n=14, rsi_ob=70.0, rsi_os=30.0,
              rsi_sl_atr=1.0, rsi_mode="revert",
              ob_break=5, ob_entry="mid",
              max_concurrent=1, tp_floor_pts=None,
              ema_filter=False, ema_fast=20, ema_slow=200,
              regime_mask: np.ndarray | None = None,
              confirm_entry=False,
              daily_stop_pts: float | None = None) -> list[Trade]:
    times = m5["time"]
    h = m5["high"].to_numpy(float)
    l = m5["low"].to_numpy(float)
    c = m5["close"].to_numpy(float)
    o = m5["open"].to_numpy(float)
    dates = times.dt.date.to_numpy()
    hr = times.dt.hour.to_numpy()
    a = atr_np(h, l, c, atr_n)
    hi5 = pd.Series(h).rolling(ob_break).max().to_numpy()
    lo5 = pd.Series(l).rolling(ob_break).min().to_numpy()
    rsi = wilder_rsi_np(c, rsi_n) if "rsi" in models else None
    ema_dir = None
    if ema_filter:
        ef = pd.Series(c).ewm(span=ema_fast, adjust=False).mean().to_numpy()
        es = pd.Series(c).ewm(span=ema_slow, adjust=False).mean().to_numpy()
        ema_dir = np.where(ef > es, 1, -1)
        ema_dir[:ema_slow] = 0            # warmup: no trades either way

    trades: list[Trade] = []
    tags: list[str] = []
    open_exits: list[int] = []   # exit bar index of each open position
    pending: list[tuple[int, float]] = []   # (exit_bar, pnl) awaiting realization
    day_real = 0.0
    cur_day = None
    for k in range(atr_n + ob_lookback + 2, len(c)):
        if hr[k] not in hours or not (a[k] > 0):
            continue
        if daily_stop_pts is not None:
            if dates[k] != cur_day:
                cur_day = dates[k]
                day_real = 0.0
                pending = [p for p in pending if p[0] > k]
            still = []
            for ke_, pnl_ in pending:
                if ke_ <= k:
                    day_real += pnl_       # realized only once the exit bar passes
                else:
                    still.append((ke_, pnl_))
            pending = still
            if day_real <= -daily_stop_pts:
                continue                   # kill-switch: done for the day
        open_exits = [e for e in open_exits if e > k]
        if len(open_exits) >= max_concurrent:
            continue
        if regime_mask is not None and not regime_mask[k]:
            continue
        side = 0
        model = None
        # ── FVG (S93) ────────────────────────────────────────────────────
        if "fvg" in models:
            if l[k] > h[k - 2] and (l[k] - h[k - 2]) >= min_fvg_atr * a[k]:
                side, prox, dist, model = 1, l[k], h[k - 2], "fvg"
            elif h[k] < l[k - 2] and (l[k - 2] - h[k]) >= min_fvg_atr * a[k]:
                side, prox, dist, model = -1, h[k], l[k - 2], "fvg"
        # ── OB (BOS + displacement -> last opposite candle) ──────────────
        if side == 0 and "ob" in models:
            body = c[k] - o[k]
            if c[k] > hi5[k - 1] and body >= dispm * a[k]:
                for j in range(k - 1, k - 1 - ob_lookback, -1):
                    if c[j] < o[j]:            # last bearish candle
                        zone_hi, zone_lo = o[j], c[j]
                        side, model = 1, "ob"
                        prox = (zone_hi if ob_entry == "edge"
                                else (zone_hi + zone_lo) / 2.0)
                        dist = zone_lo
                        break
            elif c[k] < lo5[k - 1] and -body >= dispm * a[k]:
                for j in range(k - 1, k - 1 - ob_lookback, -1):
                    if c[j] > o[j]:            # last bullish candle
                        zone_lo, zone_hi = o[j], c[j]
                        side, model = -1, "ob"
                        prox = (zone_lo if ob_entry == "edge"
                                else (zone_hi + zone_lo) / 2.0)
                        dist = zone_hi
                        break
        # ── RSI extreme cross-back (mean reversion, immediate market entry) ─
        if side == 0 and "rsi" in models and k > rsi_n + 1:
            r_side = 0
            if rsi_mode == "momentum":
                # user-inverted: strength begets strength
                if rsi[k - 1] < rsi_ob <= rsi[k]:
                    r_side = 1             # crossed UP into overbought -> BUY
                elif rsi[k - 1] > rsi_os >= rsi[k]:
                    r_side = -1            # crossed DOWN into oversold -> SELL
            else:
                if rsi[k - 1] < rsi_os <= rsi[k]:
                    r_side = 1             # crossed back UP out of oversold
                elif rsi[k - 1] > rsi_ob >= rsi[k]:
                    r_side = -1            # crossed back DOWN out of overbought
            if r_side != 0:
                if ema_dir is not None and ema_dir[k] != r_side:
                    continue
                if struct is not None and struct[k] == -r_side:
                    continue
                entry = c[k]
                sl = entry - r_side * rsi_sl_atr * a[k]
                risk = abs(entry - sl)
                if risk <= 0:
                    continue
                tp_d = max(tp_r * risk, tp_floor_pts or 0.0)
                tp = entry + r_side * tp_d
                ke, px, out = walk_exit(h, l, c, dates, k, r_side, entry, sl,
                                        tp, hold_bars, False, times)
                pnl = r_side * (px - entry) - cost
                trades.append(Trade(times.iloc[k], r_side, entry, sl, tp,
                                    times.iloc[ke], px, out, pnl))
                tags.append("rsi")
                open_exits.append(ke)
                if daily_stop_pts is not None:
                    pending.append((ke, pnl))
                continue
        if side == 0:
            continue
        if ema_dir is not None and ema_dir[k] != side:
            continue
        gap = abs(prox - dist)
        if max_gap_atr is not None and gap > max_gap_atr * a[k]:
            continue
        if struct is not None and struct[k] == -side:
            continue
        sl = dist - (buf_atr * a[k] * (1 if side > 0 else -1))
        entry_j = None
        entry = prox
        for j in range(k + 1, min(k + 1 + retrace_w, len(c))):
            touched = (l[j] <= prox) if side > 0 else (h[j] >= prox)
            if not touched:
                continue
            if (side > 0 and l[j] <= sl) or (side < 0 and h[j] >= sl):
                break                      # swept through the stop: cancel
            if confirm_entry:
                closed_back = (c[j] > prox) if side > 0 else (c[j] < prox)
                if not closed_back:
                    continue               # touched but no reclaim: keep waiting
                entry = c[j]               # market on confirmation-bar close
            entry_j = j
            break
        if entry_j is None:
            continue
        risk0 = abs(prox - sl)             # zone-anchored geometry
        if risk0 <= 0:
            continue
        tp = prox + side * max(tp_r * risk0, tp_floor_pts or 0.0)
        if (side > 0 and (entry >= tp or entry <= sl)) or \
           (side < 0 and (entry <= tp or entry >= sl)):
            continue                       # confirmation fill already beyond
        ke, px, out = walk_exit(h, l, c, dates, entry_j, side, entry, sl, tp,
                                hold_bars, False, times)
        pnl = side * (px - entry) - cost
        trades.append(Trade(times.iloc[entry_j], side, entry, sl, tp,
                            times.iloc[ke], px, out, pnl))
        tags.append(model)
        open_exits.append(ke)
        if daily_stop_pts is not None:
            pending.append((ke, pnl))
    return trades, tags


def main():
    m5 = load("5m")
    m15 = load("15m")
    struct = m15_structure_on_m5(m5, m15)

    print(f"{'variant':<26}{'cost':>5}{'trainPF':>9}{'trainN':>7}{'testPF':>8}"
          f"{'testN':>7}{'testAvg':>9}")
    for label, models, kw in (
        ("FVG only (ref)", ("fvg",), {}),
        ("OB only d1.0", ("ob",), {}),
        ("OB only d1.5", ("ob",), {"dispm": 1.5}),
        ("FVG+OB d1.0", ("fvg", "ob"), {}),
        ("FVG+OB d1.5", ("fvg", "ob"), {"dispm": 1.5}),
    ):
        for cost in (0.45, 0.80):
            tr_list, tags = run_combo(m5, models=models, cost=cost,
                                      struct=struct, **kw)
            tr, te = split_summary(tr_list, "x")
            print(f"{label:<26}{cost:>5}{tr['pf']:>9.2f}{tr['n']:>7}"
                  f"{te['pf']:>8.2f}{te['n']:>7}{te['avg_pts']:>9.2f}")
        # attribution at 0.45 for combined runs
        if len(models) == 2:
            from optimize_manager_strategies import TRAIN_END
            per = {}
            for t, g in zip(tr_list, tags):
                key = (g, "test" if t.t_entry >= TRAIN_END else "train")
                per.setdefault(key, []).append(t.pnl)
            for (g, half), pnls in sorted(per.items()):
                arr = np.array(pnls)
                w = (arr > 0).sum()
                gl = -arr[arr <= 0].sum()
                pf = arr[arr > 0].sum() / gl if gl > 0 else float("inf")
                print(f"    {g:<4}{half:<6} n={len(arr):<4} PF={pf:5.2f} "
                      f"net={arr.sum():+8.1f}pts")


if __name__ == "__main__":
    main()
