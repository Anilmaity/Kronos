"""Always 5 legs (last TP repeated), partial breakeven, "trade failed" exits all."""
import asyncio
import json

import live_trader as lt
from manage_signals import classify_management


def _sig(tps, tp_open=False):
    return {"side": "buy", "instrument": "XAUUSD", "entry_low": 1995.0, "entry_high": 2000.0,
            "sl": 1990.0, "tps": tps, "tp_open": tp_open}


def test_three_tps_become_five_legs_with_last_tp_repeated(monkeypatch):
    monkeypatch.setattr(lt, "LEG_COUNT", 5)
    assert lt.order_tps(_sig([2005.0, 2010.0, 2015.0])) == [2005.0, 2010.0, 2015.0, 2015.0, 2015.0]


def test_five_tps_one_leg_each(monkeypatch):
    monkeypatch.setattr(lt, "LEG_COUNT", 5)
    tps = [2005.0, 2010.0, 2015.0, 2020.0, 2025.0]
    assert lt.order_tps(_sig(tps)) == tps


def test_more_than_five_trimmed_vip_runner_dropped(monkeypatch):
    monkeypatch.setattr(lt, "LEG_COUNT", 5)
    monkeypatch.setattr(lt, "TP_OPEN_LEG", True)
    tps = [2005.0, 2010.0, 2015.0, 2020.0, 2025.0]
    assert lt.order_tps(_sig(tps, tp_open=True)) == tps
    assert lt.order_tps(_sig(tps[:4], tp_open=True)) == tps[:4] + [None]


def test_single_tp_becomes_five_legs(monkeypatch):
    monkeypatch.setattr(lt, "LEG_COUNT", 5)
    assert lt.order_tps(_sig([2005.0])) == [2005.0] * 5


def test_trade_failed_means_exit_all():
    for text in ("Trade failed", "this trade has failed guys", "Setup failed, exit",
                 "failed trade, closing"):
        assert classify_management(text).get("close") == "all", text


def test_breakeven_still_recognised():
    for text in ("Set breakeven now", "zero risk now", "move sl to entry"):
        assert classify_management(text).get("breakeven"), text


class _Store:
    def __init__(self, kv):
        self.kv = kv

    async def get(self, k):
        return self.kv.get(k)

    async def set(self, k, v):
        self.kv[k] = v


class _Broker:
    label = "primary"

    def __init__(self):
        self.closed, self.cancelled, self.moved = [], [], []

    def close_position(self, t):
        self.closed.append(t)
        return True

    def cancel_order(self, t):
        self.cancelled.append(t)
        return True

    def modify_position_sl(self, t, sl):
        self.moved.append((t, sl))
        return True

    def get_position_realized_pnl(self, p):
        return None


def test_breakeven_exits_three_keeps_two_farthest_at_entry(monkeypatch):
    monkeypatch.setattr(lt, "BE_KEEP_LEGS", 2)
    broker = _Broker()
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": broker})
    monkeypatch.setattr(lt, "APIS_BY_LABEL", {"primary": None})
    monkeypatch.setattr(lt.db, "record_slice_close", lambda *a, **k: None)
    tps = [2005.0, 2010.0, 2015.0, 2015.0, 2015.0]
    orders = [{"tp_index": i, "tp": tp, "ticket_id": f"t{i}", "kind": "market", "volume": 0.02,
               "broker_state": "filled", "account": "primary", "last_profit": 3.0,
               "ladder": {"budget": 40}}
              for i, tp in enumerate(tps, start=1)]
    key = f"{lt.REDIS_PREFIX}:signal:42"
    store = _Store({key: json.dumps({"side": "buy", "entry_mid": 2000.0, "orders": orders})})
    monkeypatch.setattr(lt, "r", store)

    asyncio.run(lt.breakeven_partial(42))

    assert sorted(broker.closed) == ["t1", "t2", "t3"]          # nearest three exit
    assert sorted(t for t, _ in broker.moved) == ["t4", "t5"]  # two farthest run on
    assert {sl for _, sl in broker.moved} == {2000.0}           # ... at entry (zero risk)
    pos = json.loads(store.kv[key])
    states = {o["ticket_id"]: o["broker_state"] for o in pos["orders"]}
    assert states == {"t1": "closed", "t2": "closed", "t3": "closed",
                      "t4": "filled", "t5": "filled"}
    assert all(o["ladder"]["stopped"] for o in pos["orders"])   # no re-entries after BE
