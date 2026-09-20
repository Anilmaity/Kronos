"""Sweep-reversal (manipulation -> distribution) backtest on 1m candles.

Built from the numbers in manipulation_research.py:
  - only FAST sweeps (extreme reached in <= FAST_BARS): slow breaks had
    negative expectancy
  - swing-level sweeps must clear a size floor (expanding percentile of past
    penetrations — no lookahead); PD / session sweeps always qualify
  - entry variants:  market @ confirmation close  |  limit retest @ swept level
  - TP variants:     nearest opposite liquidity (66% hit rate)  |  2x penetration
  - SL beyond the sweep extreme (+10% pen buffer), min RR gate, time exit,
    one position at a time, round-trip cost subtracted

Usage:
  python backtest_sweep_reversal.py           # XAUUSD (GC=F) 1m
  python backtest_sweep_reversal.py --btc     # BTC 1m parquet
"""

from dataclasses import dataclass
import sys

import numpy as np
import pandas as pd

from manipulation_research import (
    SESSIONS, SWING_K, CONFIRM_N, Level,
    fetch_xau_1m, load_btc_1m, precompute_swings, nearest_opposite,
)

FAST_BARS = 3         # sweep must reach its extreme within this many bars
PEN_PCTL = 0.25       # swing sweeps below this expanding percentile are noise
WARMUP_EVENTS = 50    # events before the size floor becomes active
SL_BUFFER = 0.10      # fraction of penetration beyond the extreme
MIN_RR = 1.0          # skip trades whose target pays less than the risk
ENTRY_TTL = 30        # bars a retest limit order stays working
HORIZON = 240         # max bars in a trade (4h)
LEVEL_TTL = 1440


@dataclass
class Sweep:
    conf_i: int
    direction: str     # 'down' | 'up'
    kind: str
    level: float
    extreme: float
    m_pen: float
    manip_bars: int
    target: float | None


def detect_sweeps(df: pd.DataFrame) -> list[Sweep]:
    t = df["time"]
    day = t.dt.floor("D").values
    hour = t.dt.hour.values
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    swing_hi, swing_lo = precompute_swings(df)

    levels: list[Level] = []
    sweeps: list[Sweep] = []
    cur_day = None
    day_hi = day_lo = None
    sess_state = {}

    for i in range(n):
        if day[i] != cur_day:
            if day_hi is not None:
                levels = [lv for lv in levels if lv.kind != "PD"]
                levels.append(Level(day_hi, "high", "PD", i))
                levels.append(Level(day_lo, "low", "PD", i))
            cur_day, day_hi, day_lo = day[i], h[i], l[i]
            sess_state = {}
        else:
            day_hi, day_lo = max(day_hi, h[i]), min(day_lo, l[i])

        for name, start, end in SESSIONS:
            if start <= hour[i] < end:
                st = sess_state.setdefault(name, [h[i], l[i]])
                st[0], st[1] = max(st[0], h[i]), min(st[1], l[i])
            elif name in sess_state and hour[i] >= end:
                st = sess_state.pop(name)
                levels.append(Level(st[0], "high", "session", i))
                levels.append(Level(st[1], "low", "session", i))

        j = i - SWING_K
        if j >= 0:
            if swing_hi[j]:
                levels.append(Level(h[j], "high", "swing", i))
            if swing_lo[j]:
                levels.append(Level(l[j], "low", "swing", i))

        confirmed = []
        kill = []
        for lv in levels:
            if lv.kind != "PD" and i - lv.born > LEVEL_TTL:
                kill.append(lv)
                continue
            if lv.break_i is None:
                if lv.side == "high" and h[i] > lv.price:
                    lv.break_i, lv.extreme = i, h[i]
                elif lv.side == "low" and l[i] < lv.price:
                    lv.break_i, lv.extreme = i, l[i]
            else:
                lv.extreme = max(lv.extreme, h[i]) if lv.side == "high" else min(lv.extreme, l[i])
                back = c[i] < lv.price if lv.side == "high" else c[i] > lv.price
                if back:
                    confirmed.append(lv)
                    kill.append(lv)
                elif i - lv.break_i >= CONFIRM_N:
                    kill.append(lv)
        for lv in kill:
            levels.remove(lv)

        if confirmed:
            lv = max(confirmed, key=lambda x: abs(x.extreme - x.price))
            m_pen = abs(lv.extreme - lv.price)
            if m_pen <= 0:
                continue
            direction = "down" if lv.side == "high" else "up"
            sweeps.append(Sweep(
                conf_i=i, direction=direction, kind=lv.kind, level=lv.price,
                extreme=lv.extreme, m_pen=m_pen, manip_bars=i - lv.break_i + 1,
                target=nearest_opposite(levels, c[i], direction),
            ))
    return sweeps


def backtest(df: pd.DataFrame, sweeps: list[Sweep], entry_mode: str,
             tp_mode: str, cost: float) -> pd.DataFrame:
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    trades = []
    busy_until = -1
    pen_hist: list[float] = []

    for ev in sweeps:
        qualifies_size = (ev.kind in ("PD", "session") or
                          len(pen_hist) < WARMUP_EVENTS or
                          ev.m_pen >= np.quantile(pen_hist, PEN_PCTL))
        pen_hist.append(ev.m_pen)

        if ev.conf_i <= busy_until or ev.manip_bars > FAST_BARS or not qualifies_size:
            continue

        sign = -1 if ev.direction == "down" else 1
        stop = ev.extreme - sign * SL_BUFFER * ev.m_pen

        # ---- entry
        if entry_mode == "market":
            fill_i, entry = ev.conf_i, c[ev.conf_i]
        else:  # limit retest at the swept level
            entry = ev.level
            fill_i = None
            for x in range(ev.conf_i + 1, min(ev.conf_i + 1 + ENTRY_TTL, n)):
                if (sign < 0 and h[x] >= entry) or (sign > 0 and l[x] <= entry):
                    if (sign < 0 and h[x] >= stop) or (sign > 0 and l[x] <= stop):
                        fill_i = -1        # blew through to the stop same path
                    else:
                        fill_i = x
                    break
            if fill_i is None or fill_i == -1:
                continue

        risk = abs(stop - entry)
        if risk <= 0:
            continue

        # ---- target
        if tp_mode == "liquidity":
            if ev.target is None:
                continue
            tp = ev.target
        else:
            tp = entry + sign * 2.0 * ev.m_pen
        rr = abs(tp - entry) / risk
        if rr < MIN_RR:
            continue

        # ---- manage
        outcome, exit_px, exit_i = None, None, min(fill_i + HORIZON, n - 1)
        for x in range(fill_i + 1, min(fill_i + HORIZON, n)):
            hit_sl = h[x] >= stop if sign < 0 else l[x] <= stop
            hit_tp = l[x] <= tp if sign < 0 else h[x] >= tp
            if hit_sl:                       # conservative: SL wins ties
                outcome, exit_px, exit_i = "SL", stop, x
                break
            if hit_tp:
                outcome, exit_px, exit_i = "TP", tp, x
                break
        if outcome is None:
            outcome, exit_px = "TIME", c[exit_i]

        pnl = sign * (exit_px - entry) - cost
        trades.append({
            "time": df["time"].iloc[fill_i], "dir": ev.direction, "kind": ev.kind,
            "entry": entry, "stop": stop, "tp": tp, "outcome": outcome,
            "r": pnl / risk, "rr_planned": rr, "hold": exit_i - fill_i,
        })
        busy_until = exit_i
    return pd.DataFrame(trades)


def report(tr: pd.DataFrame, label: str) -> None:
    if tr.empty:
        print(f"{label:32s} no trades")
        return
    wins = tr.r > 0
    pf = tr.r[tr.r > 0].sum() / max(1e-9, -tr.r[tr.r <= 0].sum())
    eq = tr.r.cumsum()
    dd = (eq - eq.cummax()).min()
    print(f"{label:32s} n={len(tr):4d}  WR={100 * wins.mean():3.0f}%  "
          f"avgR={tr.r.mean():+.3f}  netR={tr.r.sum():+7.1f}  PF={pf:.2f}  "
          f"maxDD={dd:.1f}R  medHold={tr.hold.median():.0f}m")


if __name__ == "__main__":
    if "--btc" in sys.argv:
        df, cost, label = load_btc_1m(), 15.0, "BTC_USD 1m"
    elif "--oanda" in sys.argv:
        df = pd.read_parquet("xau_m1_oanda.parquet")
        cost, label = 0.30, "XAU_USD 1m (OANDA)"
    else:
        df, cost, label = fetch_xau_1m(), 0.30, "XAUUSD 1m"
    print(f"{label}: {len(df):,} bars {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    sweeps = detect_sweeps(df)
    fast = sum(1 for s in sweeps if s.manip_bars <= FAST_BARS)
    print(f"sweeps={len(sweeps)} fast={fast}\n")

    best = None
    for entry_mode in ("market", "retest"):
        for tp_mode in ("liquidity", "2x_pen"):
            tr = backtest(df, sweeps, entry_mode, tp_mode, cost)
            report(tr, f"entry={entry_mode} tp={tp_mode}")
            if not tr.empty and (best is None or tr.r.sum() > best[0]):
                best = (tr.r.sum(), entry_mode, tp_mode, tr)

    if best:
        _, em, tm, tr = best
        print(f"\nbest variant: entry={em} tp={tm} — breakdown by UTC hour block:")
        for hb, g in tr.groupby(tr.time.dt.hour // 4 * 4):
            print(f"  {hb:02d}-{hb + 4:02d}h  n={len(g):4d}  avgR={g.r.mean():+.3f}  netR={g.r.sum():+6.1f}")
        print("by level kind:")
        for k, g in tr.groupby("kind"):
            print(f"  {k:8s} n={len(g):4d}  avgR={g.r.mean():+.3f}  netR={g.r.sum():+6.1f}")
        name = "sweep_trades_btc.csv" if "--btc" in sys.argv else ("sweep_trades_oanda.csv" if "--oanda" in sys.argv else "sweep_trades_xau.csv")
        tr.to_csv(name, index=False)
        print(f"saved {name}")
