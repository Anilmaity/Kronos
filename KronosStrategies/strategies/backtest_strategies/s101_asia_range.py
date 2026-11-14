"""
Kronos S101 -- Asia-session range fade (M1), demo deployment 2026-11-12
-----------------------------------------------------------------------
The live-engine shape of the "Asia-only ping-pong" lab strategy that was fitted to a
manual trader's (XM Real) results (ClaudeTradingRD/day_ladder/ping_pong.py, README).

Setup (zero discretion), on the newest CLOSED 1m bar, 00:00-16:00 UTC (Asia + London;
the London hours were added 2026-11-12 by operator request and were never lab-fitted):
  regime : over the last 120 closed minutes the range is >= _MIN_RANGE pts and the net
           move is <= _ER_MAX of that range (gold is oscillating, not trending).
  entry  : price is in the outer _EDGE of that range and the last 5 minutes pushed
           >= _PULL x ATR(30, M1) further into it -> fade the push
           (SELL near the top, BUY near the bottom).
  target : _TP_PTS points.   stop: _SL_PTS points (hard, broker-attached).
  time   : flat by 20:50 UTC (max_hold_min).

Deliberate differences from the lab version (the engine's rules, not oversights):
  - ONE position per signal with its own stop. The lab version averaged into losers with
    no per-position stop; entry_manager's no_add_to_loser gate forbids that and it stays on.
    ponytail: no averaging; to add it, the engine needs position-aware adds (spacing +
    a basket stop) -- do not get it by switching NO_ADD_TO_LOSER off.
  - Sized by RISK_PER_TRADE_USD like every other runner (0.01 lots at a 24-pt stop).

Honest expectation (lab, cost 0.25 pt, one clip per side, 8/24): TRAIN PF 0.94, TEST PF
0.92, ~2.5 trades/day, worst day about -$40 at 0.01 lots. It is NOT a validated edge --
it is on the demo book by operator decision to watch live behaviour.
"""
from __future__ import annotations

from datetime import datetime

from .base import Signal, StrategyConfig

NAME = "KRONOS_S101_ASIA_RANGE"
CONFIG = StrategyConfig(
    name=NAME,
    description="Asia-session range fade (M1): fade a 5-min push at the edge of the 2-hour range while gold oscillates; TP 8 / SL 24.",
    cooldown_s=300,
    session_start_hour=0,
    session_end_hour=16,                # Asia + London (00:00-16:00 UTC) since 2026-11-12, operator request
    max_concurrent_positions=2,        # room for one buy and one sell
)

_LOOK = 120          # minutes of range
_ATR_N = 30
_MIN_RANGE = 16.0    # points; below this the range is too small to fade
_ER_MAX = 0.15       # net move / range
_EDGE = 0.75         # outer quarter of the range
_PULL = 0.5          # 5-min push in ATR units
_TP_PTS = 8.0
_SL_PTS = 24.0
_FLAT_MIN = 20 * 60 + 50                 # 20:50 UTC
MIN_BARS_1M = _LOOK + _ATR_N             # research_runner refuses to start with a smaller window


def get_signal(w1m, w5m, w15m, now_utc: datetime) -> Signal | None:
    if w1m is None or len(w1m) < _LOOK + 2:
        return None
    h = w1m["high"].astype(float).to_numpy(); l = w1m["low"].astype(float).to_numpy(); c = w1m["close"].astype(float).to_numpy()
    hi, lo = h[-_LOOK:].max(), l[-_LOOK:].min(); rng = hi - lo
    if rng < _MIN_RANGE:
        return None
    if abs(c[-1] - c[-_LOOK - 1]) / rng > _ER_MAX:
        return None
    prev = c[-_ATR_N - 1:-1]
    tr = [max(h[-_ATR_N + i] - l[-_ATR_N + i], abs(h[-_ATR_N + i] - prev[i]), abs(l[-_ATR_N + i] - prev[i])) for i in range(_ATR_N)]
    atr = sum(tr) / _ATR_N
    pos = (c[-1] - lo) / rng; push = c[-1] - c[-6]
    if pos > _EDGE and push >= _PULL * atr:
        side = "SELL"
    elif pos < 1 - _EDGE and push <= -_PULL * atr:
        side = "BUY"
    else:
        return None
    sgn = 1 if side == "BUY" else -1; e = float(c[-1])
    hold = _FLAT_MIN - (now_utc.hour * 60 + now_utc.minute)
    return Signal(side=side, entry_price=e, stop_loss=e - sgn * _SL_PTS, take_profit=e + sgn * _TP_PTS,
                  reason=f"asia range fade pos={pos:.2f} er={abs(c[-1] - c[-_LOOK - 1]) / rng:.2f} rng={rng:.1f}",
                  max_hold_min=float(hold) if hold > 0 else None)
