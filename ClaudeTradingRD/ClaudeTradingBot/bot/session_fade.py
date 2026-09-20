"""GuardedSessionFade — your real scalp style, made survivable.

Learned from your 67 live trades on account 5216074f (see reports/mobile_scalp_research.md):
  - FADE: sell after a short up-extension, buy after a down-extension (41/67 of your entries)
  - quiet sessions: you concentrated entries at 22-23 UTC (NY close / Asia open) + 08, 12-13 UTC
  - tiny take-profit, fast exit

Honest finding: this style's WIN RATE is structural (random entries + your no-stop exit
also win ~87%), and its systematic expectancy is ~breakeven-negative after costs. Your
+$452 was at the 94th percentile of random — possibly a sliver of discretionary timing
edge, unprovable on 67 trades. So this module does NOT claim a systematic edge. What it
does: keep your entry FILTERS but bolt on the guardrails your live trading lacked, so a
discretionary edge (if real) can express itself without the no-stop ruin tail that makes
the raw style blow a $5k challenge 72.5% of the time.

Guardrails (the whole point):
  - HARD stop on every trade (initial, never widened)  -> caps the -$269-heat tail
  - daily loss kill-switch                              -> one bad session can't bust you
  - max concurrent positions + risk-based sizing        -> -1R stays inside the daily limit

Pure/inspectable so the live layer is a thin wrapper over signal() + position_size().
"""
from __future__ import annotations

USD_PER_POINT_PER_0_1_LOT = 10.0
SESSIONS_DEFAULT = frozenset({22, 23, 0, 8, 12, 13})   # UTC hours you actually traded


def position_size(equity, *, stop_points, risk_pct=0.006, risk_floor=30.0,
                  min_lot=0.01, max_lot=0.50, lot_step=0.01):
    """Lots so a stop-out (stop_points) risks ~max(risk_floor, risk_pct*equity).
    Defaults keep a -1R loss well under a $250 daily limit on a $5k account."""
    risk_dollars = max(risk_floor, risk_pct * equity)
    if stop_points <= 0:
        return 0.0, 0.0
    raw = risk_dollars / (stop_points * (USD_PER_POINT_PER_0_1_LOT / 0.1))
    lot = max(min_lot, min(max_lot, round(raw / lot_step) * lot_step))
    actual_risk = stop_points * (USD_PER_POINT_PER_0_1_LOT / 0.1) * lot
    return round(lot, 2), round(actual_risk, 2)


def signal(closes, hour_utc, *, sessions=SESSIONS_DEFAULT, ext_points=1.0,
           lookback=60, require_15m=True, lb15=180):
    """Fade a short extension during a permitted session.
    closes: recent 5s (or 1s) close prices, newest last. Returns 'buy'|'sell'|None.

    - only trades in `sessions` (UTC hours)
    - needs a real 5-min extension >= ext_points to fade
    - require_15m: the 15-min move must agree (a genuinely stretched move, not noise)
    """
    if hour_utc not in sessions:
        return None
    if len(closes) <= max(lookback, lb15):
        return None
    m5 = closes[-1] - closes[-1 - lookback]
    if abs(m5) < ext_points:
        return None
    side = "sell" if m5 > 0 else "buy"
    if require_15m:
        m15 = closes[-1] - closes[-1 - lb15]
        if (side == "sell" and m15 <= 0) or (side == "buy" and m15 >= 0):
            return None
    return side


class DailyGuard:
    """Kill-switch: stop trading for the UTC day after `max_loss` realized, or
    `max_trades` taken, or `max_consec_losses` in a row."""
    def __init__(self, max_loss=120.0, max_trades=15, max_consec_losses=3):
        self.max_loss = max_loss; self.max_trades = max_trades
        self.max_consec = max_consec_losses
        self._day = None; self._pnl = 0.0; self._n = 0; self._streak = 0

    def _roll(self, day):
        if day != self._day:
            self._day = day; self._pnl = 0.0; self._n = 0; self._streak = 0

    def allowed(self, day) -> bool:
        self._roll(day)
        return (self._pnl > -self.max_loss and self._n < self.max_trades
                and self._streak < self.max_consec)

    def record(self, day, pnl):
        self._roll(day)
        self._pnl += pnl; self._n += 1
        self._streak = self._streak + 1 if pnl <= 0 else 0
