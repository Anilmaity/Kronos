"""2026-10-13: "Set breakeven now for zero risk" exits EVERY leg (TG_BE_EXIT_ALL).

Before, breakeven closed the three nearest legs and left the two farthest
running at entry. The operator wants the whole trade flat on that message.
"""
import asyncio

import pytest

import live_trader as lt

MSG = "TakeProfit 2 checkkk!👏🏽👏🏽🤑\n\nSet breakeven now for zero riskk! 🥇"


class _Store:
    def __init__(self, open_ids):
        self.open_ids = set(open_ids)

    async def smembers(self, k):
        return self.open_ids


@pytest.fixture
def closes(monkeypatch):
    seen = []

    async def fake_close(msg_id, reason):
        seen.append((msg_id, reason))

    async def forbidden(*a, **k):
        raise AssertionError("breakeven must not keep legs running")

    monkeypatch.setattr(lt, "BE_EXIT_ALL", True)
    monkeypatch.setattr(lt, "ACT_ON_MANAGEMENT", True)
    monkeypatch.setattr(lt, "close_order", fake_close)
    monkeypatch.setattr(lt, "breakeven_partial", forbidden)
    monkeypatch.setattr(lt, "move_to_breakeven", forbidden)
    monkeypatch.setattr(lt, "r", _Store({"7736"}))
    return seen


def test_standalone_breakeven_exits_all(closes):
    action = asyncio.run(lt.apply_management(9001, lt.clean(MSG), None))
    assert closes == [(7736, "breakeven_exit")]
    assert action["close"] == "all"


def test_breakeven_reply_exits_all_once(closes):
    from types import SimpleNamespace
    from datetime import datetime, timezone
    msg = SimpleNamespace(id=9002, text=MSG, date=datetime.now(timezone.utc),
                          reply_to=SimpleNamespace(reply_to_msg_id=7736))
    asyncio.run(lt.handle_reply(msg))
    assert closes == [(7736, "breakeven_exit")]          # exactly once, no TP2 follow-up


def test_breakeven_with_explicit_close_all_closes_once(closes):
    asyncio.run(lt.apply_management(9003, "breakeven hit out of this entries now!", None))
    assert closes == [(7736, "breakeven_exit")]


def test_move_sl_to_price_still_just_moves(closes, monkeypatch):
    moved = []

    async def fake_modify(mid, sl):
        moved.append((mid, sl))

    monkeypatch.setattr(lt, "modify_sl", fake_modify)
    asyncio.run(lt.apply_management(9004, "Move SL to 4120", None))
    assert moved == [(7736, 4120.0)] and closes == []
