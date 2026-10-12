"""A timed-out leg POST can execute minutes after the bot's retry went through,
leaving two broker positions with one leg tag (2026-10-07, signal 7736 TP5:
121973848 ran untracked next to the recorded 121973673 and lost $38.72).
reconcile_broker must close the duplicate and keep tracking the recorded one."""
import asyncio
import json
import types

import live_trader as lt
from state_store import make_store


class _FakeBroker:
    def __init__(self, positions):
        self.positions = positions
        self.closed = []

    def get_open_positions(self, symbol=None):
        return self.positions

    def get_pending_orders(self, symbol=None):
        return []

    def close_position(self, position_id):
        self.closed.append(position_id)
        return True


def _run(monkeypatch, broker, ticket="121973673"):
    sig = {"msg_id": 7736, "side": "buy", "entry_mid": 4125.5, "total_volume": 0.04,
           "orders": [{"tp_index": 5, "tp": 4135.0, "sl": 4116.0, "entry": 4125.5,
                       "volume": 0.04, "ticket_id": ticket, "kind": "market",
                       "account": "primary", "broker_state": "filled", "observed": True}]}

    async def _go():
        lt.r, _ = await make_store(None)
        await lt.r.set(f"{lt.REDIS_PREFIX}:signal:7736", json.dumps(sig))
        await lt.r.sadd(f"{lt.REDIS_PREFIX}:open", "7736")
        await lt.reconcile_broker()
        return json.loads(await lt.r.get(f"{lt.REDIS_PREFIX}:signal:7736"))

    monkeypatch.setattr(lt, "ACCOUNTS", [{"label": "primary", "client": broker, "risk_usd": 100.0,
                                          "apis": None}])
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": broker})
    monkeypatch.setattr(lt, "APIS_BY_LABEL", {})
    monkeypatch.setattr(lt, "db", types.SimpleNamespace(record_fill=lambda *a, **k: None))
    return asyncio.run(_go())


def _pos(pid):
    return {"id": pid, "comment": "tg-7736-tp5", "openPrice": 4124.68, "profit": -1.0,
            "currentPrice": 4124.4}


def test_duplicate_of_a_tracked_leg_is_closed(monkeypatch):
    # the late duplicate listed first, so "last one wins" would not save us either way
    broker = _FakeBroker([_pos("121973848"), _pos("121973673")])
    sig = _run(monkeypatch, broker)
    assert broker.closed == ["121973848"]
    assert sig["orders"][0]["broker_position_id"] == "121973673"


def test_unmatched_twins_are_left_alone(monkeypatch):
    broker = _FakeBroker([_pos("A"), _pos("B")])     # neither is the recorded ticket
    _run(monkeypatch, broker)
    assert broker.closed == []


def test_single_position_untouched(monkeypatch):
    broker = _FakeBroker([_pos("121973673")])
    _run(monkeypatch, broker)
    assert broker.closed == []
