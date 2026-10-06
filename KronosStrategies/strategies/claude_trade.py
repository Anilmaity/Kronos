"""Claude Strategy executor — the only code that trades for "Claude Strategy".

The Claude Code session on reaper reaches this through the claude-gw SSH
gateway (claude_strategy/claude_gw.py):

    python claude_trade.py status
    python claude_trade.py market [--tf 5m,15m,1h] [--bars 120]
    python claude_trade.py open --side BUY|SELL --sl X --tp Y --why "..."
    python claude_trade.py close --why "..."

Every call prints one JSON object. Limits live in claude_guard (pure, tested);
orders go through entry_manager.place_entry like every other strategy, so
manager gating, position_manager exits and the dashboard apply unchanged.
arm_mode PAPER forces DRY_RUN before the broker client is imported.
Spec: docs/superpowers/specs/2026-10-06-claude-strategy-design.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from decimal import Decimal

import claude_guard as guard

NAME = "Claude Strategy"
VARIATION = "claude_strategy"
SYMBOL = "XAU_USD"
TFS = ("1m", "5m", "15m", "1h", "4h", "1d")
# Calendar days of history to request per timeframe — enough for 300 bars
# across a weekend.
_DAYS = {"1m": 4, "5m": 5, "15m": 8, "1h": 25, "4h": 90, "1d": 450}
CLOSE_WAIT_S = 20


def _tfs(v: str) -> str:
    if any(t not in TFS for t in v.split(",")):
        raise argparse.ArgumentTypeError(f"timeframes must be from {TFS}")
    return v


def _bars(v: str) -> int:
    n = int(v)
    if not 1 <= n <= 300:
        raise argparse.ArgumentTypeError("bars must be 1..300")
    return n


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="claude_trade.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    m = sub.add_parser("market")
    m.add_argument("--tf", type=_tfs, default="5m,15m,1h")
    m.add_argument("--bars", type=_bars, default=120)
    o = sub.add_parser("open")
    o.add_argument("--side", required=True, choices=("BUY", "SELL"))
    o.add_argument("--sl", required=True, type=float)
    o.add_argument("--tp", required=True, type=float)
    o.add_argument("--why", required=True)
    c = sub.add_parser("close")
    c.add_argument("--why", required=True)
    return p


# ── DB helpers ──────────────────────────────────────────────────────────────

def _rows(sess):
    from shared.models import ManagedStrategy, Strategy, UserStrategy
    us = (sess.query(UserStrategy)
          .join(Strategy, UserStrategy.strategy_id == Strategy.id)
          .filter(Strategy.name == NAME, UserStrategy.deployed == True)  # noqa: E712
          .first())
    if us is None:
        raise RuntimeError("Claude Strategy is not deployed")
    ms = sess.query(ManagedStrategy).filter_by(user_strategy_id=us.id).first()
    return us, ((ms.arm_mode if ms else None) or "OFF")


def _open_position(sess, us):
    from shared.models import Position
    return (sess.query(Position)
            .filter(Position.user_strategy_id == us.id, Position.quantity > 0)
            .order_by(Position.created_at.desc())
            .first())


def _describe(sess, pos) -> dict | None:
    if pos is None:
        return None
    from shared.models import Trigger
    levels = {}
    for t in sess.query(Trigger).filter_by(position_id=pos.id, status="PENDING"):
        key = "TIME_EXIT" if t.order_type == "TIME_EXIT" else t.trigger_type
        levels[key] = float(t.trigger_price)
    long = float(pos.avg_buy_price or 0) > 0
    return {
        "id": str(pos.id),
        "side": "BUY" if long else "SELL",
        "entry": float(pos.avg_buy_price if long else pos.avg_sell_price),
        "lots": float(pos.quantity),
        "sl": levels.get("STOPLOSS"),
        "tp": levels.get("TARGET"),
        "closing": "TIME_EXIT" in levels,
        "open_pnl_usd": round(float(pos.profit_loss or 0), 2),
        "opened_at": pos.created_at.isoformat() if pos.created_at else None,
    }


def _day(sess, em, us, pos) -> tuple[float, float]:
    realized = em._todays_realized_usd(sess, [us.id])
    open_pnl = float(pos.profit_loss or 0) if pos is not None else 0.0
    return round(realized, 2), round(open_pnl, 2)


def _request_close(sess, pos) -> bool:
    """Hand the close to position_manager: an already-expired TIME_EXIT trigger
    makes it close the position through its normal path (realize P&L, cancel
    the other triggers, close at the broker) on its next 1 s tick."""
    from shared.models import Position, Trigger
    long = float(pos.avg_buy_price or 0) > 0
    sess.add(Trigger(
        id=uuid.uuid4(),
        symbol=SYMBOL,
        trigger_price=Decimal(str(round(time.time() - 1, 2))),  # epoch, not price
        order_type="TIME_EXIT",
        side="SELL" if long else "BUY",
        greater_than=False,
        quantity=pos.quantity,
        trigger_type="CUSTOM",
        status="PENDING",
        position_id=pos.id,
    ))
    sess.commit()
    deadline = time.time() + CLOSE_WAIT_S
    while time.time() < deadline:
        sess.expire_all()
        if float(sess.get(Position, pos.id).quantity or 0) == 0:
            return True
        time.sleep(1)
    return False


# ── commands ────────────────────────────────────────────────────────────────

def cmd_status(sess, em, us, arm) -> dict:
    pos = _open_position(sess, us)
    realized, open_pnl = _day(sess, em, us, pos)
    lock = guard.day_lock(realized + open_pnl)
    out = {"ok": True, "arm_mode": arm, "armed": arm != "OFF" and bool(us.is_active),
           "realized_today_usd": realized, "open_pnl_usd": open_pnl,
           "day_pnl_usd": round(realized + open_pnl, 2), "day_locked": lock,
           "limits": {"target": guard.DAY_TARGET_USD, "loss": -guard.DAY_LOSS_USD,
                      "risk_per_trade": guard.RISK_PER_TRADE_USD, "max_open": 1},
           "position": _describe(sess, pos)}
    if lock and pos is not None:
        out["closed_for_lock"] = _request_close(sess, pos)
        out["position"] = _describe(sess, _open_position(sess, us))
    out["can_trade"] = out["armed"] and not lock and out["position"] is None
    return out


def cmd_market(tfs: list[str], bars: int) -> dict:
    from shared.tsdb_reader import fetch_candles, fetch_latest_ltp
    out = {"ok": True, "symbol": SYMBOL, "ltp": fetch_latest_ltp(SYMBOL),
           "bar_format": ["time_utc", "open", "high", "low", "close"]}
    for tf in tfs:
        df = fetch_candles(tf, days=_DAYS[tf], symbol=SYMBOL).tail(bars)
        out[tf] = [[str(r.time), round(float(r.open), 2), round(float(r.high), 2),
                    round(float(r.low), 2), round(float(r.close), 2)]
                   for r in df.itertuples(index=False)]
    return out


def cmd_open(sess, em, us, arm, a) -> dict:
    from shared.models import StrategySignal
    from shared.tsdb_reader import fetch_latest_ltp
    from strategy.ict_engine import EntrySignal
    if arm == "OFF" or not us.is_active:
        return {"ok": True, "placed": False,
                "reason": f"not armed (arm_mode={arm}, active={bool(us.is_active)})"}
    pos = _open_position(sess, us)
    realized, open_pnl = _day(sess, em, us, pos)
    entry = fetch_latest_ltp(SYMBOL)
    if entry is None:
        return {"ok": True, "placed": False, "reason": "no_price"}
    lots, why = guard.check_open(a.side, entry, a.sl, a.tp, realized + open_pnl,
                                 pos is not None, em.MAX_LOT)
    if lots is None:
        return {"ok": True, "placed": False, "reason": why, "entry_ltp": entry}
    sig = EntrySignal(side=a.side, entry_price=entry, stop_loss=a.sl, take_profit=a.tp,
                      reason=("CLAUDE: " + a.why)[:200], zone_low=entry, zone_high=entry)
    placed = em.place_entry(sig, symbol=SYMBOL, variation=VARIATION, max_concurrent=1)
    sess.expire_all()
    last = (sess.query(StrategySignal)
            .filter_by(strategy_id=us.strategy_id)
            .order_by(StrategySignal.signal_at.desc())
            .first())
    return {"ok": True, "placed": bool(placed), "guard": why, "entry_ltp": entry,
            "dry_run": arm == "PAPER",
            "signal_status": last.status if last else None,
            "rejection_reason": last.rejection_reason if last else None,
            "position": _describe(sess, _open_position(sess, us))}


def cmd_close(sess, us) -> dict:
    pos = _open_position(sess, us)
    if pos is None:
        return {"ok": True, "closed": False, "reason": "no open position"}
    closed = _request_close(sess, pos)
    return {"ok": True, "closed": closed,
            "reason": None if closed else f"still open after {CLOSE_WAIT_S}s — position_manager will finish it",
            "position": _describe(sess, _open_position(sess, us))}


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "market":
        print(json.dumps(cmd_market(a.tf.split(","), a.bars)))
        return 0
    from shared.models import Session
    sess = Session()
    try:
        us, arm = _rows(sess)
        # Both knobs are read at import time by entry_manager / metaapi_client,
        # so they must be set before the import below.
        os.environ["RISK_PER_TRADE_USD"] = str(guard.RISK_PER_TRADE_USD)
        if arm == "PAPER":
            os.environ["DRY_RUN"] = "true"
        from strategy import entry_manager as em
        if a.cmd == "status":
            out = cmd_status(sess, em, us, arm)
        elif a.cmd == "open":
            out = cmd_open(sess, em, us, arm, a)
        else:
            out = cmd_close(sess, us)
        if a.cmd != "status":
            out["why"] = a.why
        print(json.dumps(out, default=str))
        return 0
    except Exception as e:  # one JSON line back to the session, never a traceback
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
        return 1
    finally:
        sess.close()


if __name__ == "__main__":
    sys.exit(main())
