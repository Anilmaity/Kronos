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

    def modify_position_sl(self, t, sl, tp=None):
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


def test_sl_modify_keeps_the_take_profit(monkeypatch):
    """MetaAPI POSITION_MODIFY with only stopLoss REMOVES the TP (seen live on
    the demo account) — the TP must always be re-sent."""
    import metaapi_orders as mx
    c = mx.MetaApiClient("tok", "acct", dry_run=False, label="x")
    sent = []
    monkeypatch.setattr(c, "_trade", lambda payload: sent.append(payload) or {"ok": 1})
    c.modify_position_sl("p1", 1999.0, 2015.0)
    c.modify_position_sl("p2", 1999.0)                  # open-ended runner: no TP
    assert sent[0] == {"actionType": "POSITION_MODIFY", "positionId": "p1",
                       "stopLoss": 1999.0, "takeProfit": 2015.0}
    assert "takeProfit" not in sent[1]


def test_bot_passes_each_legs_tp_when_moving_sl(monkeypatch):
    broker = _Broker()
    calls = []
    broker.modify_position_sl = lambda t, sl, tp=None: calls.append((t, sl, tp)) or True
    monkeypatch.setattr(lt, "BE_KEEP_LEGS", 2)
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": broker})
    monkeypatch.setattr(lt, "APIS_BY_LABEL", {"primary": None})
    monkeypatch.setattr(lt.db, "record_slice_close", lambda *a, **k: None)
    orders = [{"tp_index": i, "tp": tp, "ticket_id": f"t{i}", "kind": "market", "volume": 0.02,
               "broker_state": "filled", "account": "primary"}
              for i, tp in enumerate([2005.0, 2010.0, 2015.0], start=1)]
    key = f"{lt.REDIS_PREFIX}:signal:43"
    store = _Store({key: json.dumps({"side": "buy", "entry_mid": 2000.0, "orders": orders})})
    monkeypatch.setattr(lt, "r", store)
    asyncio.run(lt.breakeven_partial(43))
    assert sorted(calls) == [("t2", 2000.0, 2010.0), ("t3", 2000.0, 2015.0)]


def test_schema_init_serialised_and_retried(monkeypatch):
    """Both bots start together after a reboot: the DDL takes an advisory lock
    and a transient failure (the 2026-10-01 deadlock) is retried."""
    import db_persist as db
    calls = {"n": 0, "sql": []}

    class Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            calls["sql"].append(sql.split()[0] + (" lock" if "advisory" in sql else ""))
            if "advisory" in sql:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("deadlock detected")

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return Cur()

    monkeypatch.setattr(db, "_connect", lambda: Conn())
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    assert db.init_schema() is True
    assert calls["n"] == 2                          # failed once, then succeeded
    assert calls["sql"][-3] == "SELECT lock"        # lock taken before the DDL


def test_failed_close_is_not_marked_closed(monkeypatch):
    """Found live: a leg whose close call failed was marked closed anyway, so a
    later 'Trade failed' skipped it and it stayed open."""
    monkeypatch.setattr(lt.time, "sleep", lambda s: None)
    broker = _Broker()
    tries = []
    broker.close_position = lambda t: tries.append(t) or (t != "t2")   # t2 keeps failing
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": broker})
    monkeypatch.setattr(lt.db, "record_slice_close", lambda *a, **k: None)
    slices = [{"tp_index": i, "ticket_id": f"t{i}", "kind": "market", "broker_state": "filled",
               "account": "primary", "volume": 0.02} for i in (1, 2, 3)]
    asyncio.run(_close(slices))
    assert {o["ticket_id"]: o["broker_state"] for o in slices} == {
        "t1": "closed", "t2": "filled", "t3": "closed"}
    assert tries.count("t2") == 3                          # 3 attempts, then left open


def _close(slices):
    async def go():
        await lt._close_slices(asyncio.get_running_loop(), 7, slices, "x")
    return go()


def test_failed_exit_keeps_retrying_in_background(monkeypatch):
    monkeypatch.setattr(lt.time, "sleep", lambda s: None)
    monkeypatch.setattr(lt, "CLOSE_RETRY_EVERY_SEC", 0.01)
    broker = _Broker()
    state = {"n": 0}

    def close(t):
        state["n"] += 1
        return state["n"] > 5            # MetaAPI down for the first 5 calls
    broker.close_position = close
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": broker})
    monkeypatch.setattr(lt.db, "record_slice_close", lambda *a, **k: None)
    slices = [{"tp_index": 1, "ticket_id": "t1", "kind": "market", "broker_state": "filled",
               "account": "primary", "volume": 0.02}]

    async def go():
        await lt._close_slices(asyncio.get_running_loop(), 8, slices, "x")
        await asyncio.sleep(0.2)          # let the background retry run
    asyncio.run(go())
    assert state["n"] >= 6                # 3 immediate tries + background retries until it closed
