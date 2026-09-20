"""S93 structure-filter validation — RD-style M15 swing structure gate.

Baseline parity first (must reproduce ~train PF 1.30 / test PF 1.24 at
0.45pt cost), then variants at the validated knobs (f0.3 tp1.5R w12 KZ):
  base        : no bias (live S93)
  struct-strict: only trade when M15 structure (HH/HL vs LH/LL, RD
                 fvg_ict.py method, causal confirmation) matches side
  struct-soft : block only OPPOSITE structure (ranging allowed)
  h4bias      : harness-native H4 EMA20/50 bias (original sweep variant)
Then 0.80pt stress on base + best variant. No repo changes.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"E:\Projects\Kronos\KronosStrategies\strategies")
sys.path.insert(0, str(REPO / "backtest"))

import optimize_manager_strategies as oms
from optimize_manager_strategies import (
    Trade, atr_np, h4_bias_on_m5, load, split_summary, fmt, walk_exit,
)

KZ = (7, 8, 9, 12, 13, 14)


def m15_structure_on_m5(m5: pd.DataFrame, m15: pd.DataFrame,
                        lookback: int = 3, window: int = 60) -> np.ndarray:
    """+1/-1/0 RD-style swing structure per M5 bar, causal.

    Swing at i needs `lookback` bars either side -> confirmed at i+lookback.
    Structure at M15 bar t uses the last two CONFIRMED swing highs/lows
    within the trailing `window` bars: HH&HL -> +1, LH&LL -> -1, else 0.
    Mapped to M5 using only M15 bars CLOSED before the M5 bar opens.
    """
    h = m15["high"].to_numpy(float)
    l = m15["low"].to_numpy(float)
    n = len(m15)
    sw_hi = np.zeros(n, bool)
    sw_lo = np.zeros(n, bool)
    for i in range(lookback, n - lookback):
        wh = h[i - lookback:i + lookback + 1]
        wl = l[i - lookback:i + lookback + 1]
        if h[i] == wh.max():
            sw_hi[i] = True
        if l[i] == wl.min():
            sw_lo[i] = True

    struct = np.zeros(n, int)
    hi_idx: list[int] = []
    lo_idx: list[int] = []
    ptr_h = ptr_l = 0
    for t in range(n):
        conf = t - lookback          # newest swing index confirmed by bar t
        while ptr_h <= conf:
            if conf >= 0 and ptr_h >= 0 and ptr_h <= conf and sw_hi[ptr_h]:
                hi_idx.append(ptr_h)
            ptr_h += 1
        while ptr_l <= conf:
            if conf >= 0 and ptr_l >= 0 and ptr_l <= conf and sw_lo[ptr_l]:
                lo_idx.append(ptr_l)
            ptr_l += 1
        hs = [i for i in hi_idx[-4:] if i >= t - window]
        ls = [i for i in lo_idx[-4:] if i >= t - window]
        if len(hs) >= 2 and len(ls) >= 2:
            if h[hs[-1]] > h[hs[-2]] and l[ls[-1]] > l[ls[-2]]:
                struct[t] = 1
            elif h[hs[-1]] < h[hs[-2]] and l[ls[-1]] < l[ls[-2]]:
                struct[t] = -1
    # map to M5: last M15 bar closed before the M5 bar opens
    m15_close = (m15["time"] + pd.Timedelta(minutes=15)).to_numpy()
    pos = np.searchsorted(m15_close, m5["time"].to_numpy(), side="right") - 1
    out = np.zeros(len(m5), int)
    ok = pos >= 0
    out[ok] = struct[pos[ok]]
    return out


def run_fvg_scalp_v2(m5, *, min_fvg_atr=0.3, retrace_w=12, tp_r=1.5,
                     buf_atr=0.2, atr_n=14, hold_bars=24, hours=KZ,
                     cost=0.45, struct: np.ndarray | None = None,
                     struct_mode: str = "strict",
                     max_gap_pts: float | None = None,
                     max_gap_atr: float | None = None,
                     regime_mask: np.ndarray | None = None) -> list[Trade]:
    """Copy of oms.run_fvg_scalp with an explicit cost + structure gate.
    struct_mode 'strict': trade only when struct == side.
    struct_mode 'soft'  : skip only when struct == -side (ranging allowed)."""
    times = m5["time"]
    h = m5["high"].to_numpy(float)
    l = m5["low"].to_numpy(float)
    c = m5["close"].to_numpy(float)
    dates = times.dt.date.to_numpy()
    hr = times.dt.hour.to_numpy()
    a = atr_np(h, l, c, atr_n)

    trades: list[Trade] = []
    busy_until = -1
    for k in range(atr_n + 3, len(c)):
        if k <= busy_until or hr[k] not in hours or not (a[k] > 0):
            continue
        if regime_mask is not None and not regime_mask[k]:
            continue
        side = 0
        if l[k] > h[k - 2] and (l[k] - h[k - 2]) >= min_fvg_atr * a[k]:
            side = 1
            prox, dist = l[k], h[k - 2]
        elif h[k] < l[k - 2] and (l[k - 2] - h[k]) >= min_fvg_atr * a[k]:
            side = -1
            prox, dist = h[k], l[k - 2]
        if side == 0:
            continue
        gap = abs(prox - dist)
        if max_gap_pts is not None and gap > max_gap_pts:
            continue
        if max_gap_atr is not None and gap > max_gap_atr * a[k]:
            continue
        if struct is not None:
            if struct_mode == "strict" and struct[k] != side:
                continue
            if struct_mode == "soft" and struct[k] == -side:
                continue
        entry_j = None
        for j in range(k + 1, min(k + 1 + retrace_w, len(c))):
            if side > 0 and l[j] <= prox:
                entry_j = j
                break
            if side < 0 and h[j] >= prox:
                entry_j = j
                break
        if entry_j is None:
            continue
        entry = prox
        sl = dist - (buf_atr * a[k] * (1 if side > 0 else -1))
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * tp_r * risk
        if (side > 0 and l[entry_j] <= sl) or (side < 0 and h[entry_j] >= sl):
            continue
        ke, px, out = walk_exit(h, l, c, dates, entry_j, side, entry, sl, tp,
                                hold_bars, False, times)
        pnl = side * (px - entry) - cost
        trades.append(Trade(times.iloc[entry_j], side, entry, sl, tp,
                            times.iloc[ke], px, out, pnl))
        busy_until = ke
    return trades


def show(trades, label):
    tr, te = split_summary(trades, label)
    print(fmt(tr))
    print(fmt(te))


def main():
    m5 = load("5m")
    m15 = load("15m")
    h4 = load("4h")
    print(f"m5 bars: {len(m5)}  {m5['time'].iloc[0]} .. {m5['time'].iloc[-1]}")

    struct = m15_structure_on_m5(m5, m15)
    frac = {v: float((struct == v).mean()) for v in (-1, 0, 1)}
    print(f"M15 structure occupancy: bull {frac[1]:.0%} bear {frac[-1]:.0%} "
          f"ranging {frac[0]:.0%}")
    h4b = h4_bias_on_m5(m5, h4)

    print("\n===== 0.45pt cost =====")
    # parity check vs harness implementation
    oms.COST_PTS = 0.45
    show(oms.run_fvg_scalp(m5, min_fvg_atr=0.3, tp_r=1.5, retrace_w=12,
                           hours=KZ), "harness-base f0.3 tp1.5 w12 KZ")
    base = run_fvg_scalp_v2(m5, cost=0.45)
    show(base, "v2-base (parity check)")
    show(run_fvg_scalp_v2(m5, cost=0.45, struct=struct, struct_mode="strict"),
         "v2 +M15struct STRICT")
    show(run_fvg_scalp_v2(m5, cost=0.45, struct=struct, struct_mode="soft"),
         "v2 +M15struct SOFT")
    show(run_fvg_scalp_v2(m5, cost=0.45, struct=h4b, struct_mode="strict"),
         "v2 +H4bias")

    print("\n===== 0.80pt stress =====")
    show(run_fvg_scalp_v2(m5, cost=0.80), "v2-base @0.80")
    show(run_fvg_scalp_v2(m5, cost=0.80, struct=struct, struct_mode="strict"),
         "v2 +M15struct STRICT @0.80")
    show(run_fvg_scalp_v2(m5, cost=0.80, struct=struct, struct_mode="soft"),
         "v2 +M15struct SOFT @0.80")


if __name__ == "__main__":
    main()
