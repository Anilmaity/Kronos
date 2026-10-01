"""Trade SL ladder, drawdown guard, VIP priority and parallel leg placement."""
import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytest

import apis_persist as apis
import db_persist as db
import live_trader as lt
import metaapi_orders as mx

_RealClient = mx.MetaApiClient


def _client(label="acc", *, ask=2000.5, stops=1.0):
    c = _RealClient("tok", f"acct-{label}", dry_run=False, label=label)
    c._trading_url = "https://h"
    c.get_symbol_price = lambda symbol: {"bid": ask - 0.2, "ask": ask}
    c._get_symbol_spec = lambda b: {"stops_level_price": stops, "tick_size": 0.01}
    c.get_open_positions = lambda symbol=None: []
    c.placed = []

    def rec_market(side, symbol, volume, sl, tp, comment=""):
        c.placed.append({"vol": volume, "sl": sl, "tp": tp, "comment": comment})
        return f"{label}-m-{len(c.placed)}"

    c.place_market_order_full = rec_market
    c.place_limit_order = lambda *a, **k: (None, None)
    return c


def _acc(label, client, **kw):
    a = {"label": label, "client": client, "risk_usd": 100.0, "apis": None, "source": "db",
         "us_id": label, "ub_id": f"ub-{label}", "lot": None, "entries": True, "healthy": True}
    a.update(kw)
    return a


def _sig(n_tps=5):
    return {"side": "buy", "instrument": "XAUUSD", "entry_low": 1995.0, "entry_high": 2000.0,
            "sl": 1990.0, "tps": [2010.0 + 5 * i for i in range(n_tps)]}


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(lt, "_dd_state", {})
    monkeypatch.setattr(lt, "USD_PER_POINT_PER_LOT", 100.0)


# ── Trade SL ladder ──────────────────────────────────────────────────────────
def test_trade_sl_split_across_legs_sets_sl_from_usd(monkeypatch):
    """Trade SL 200 over 5 legs = $40 per leg; 0.01 lot -> SL 40.00 below entry."""
    c = _client("a")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", c, lot=0.05, trade_sl=200.0)])
    pos = asyncio.run(lt.place_order(1, _sig(5)))
    assert [p["vol"] for p in c.placed] == [0.01] * 5
    # market plan: reference = ask 2000.5 -> SL 1960.5 on every leg (TPs unchanged)
    assert {p["sl"] for p in c.placed} == {1960.5}
    assert [p["tp"] for p in c.placed] == [2010.0, 2015.0, 2020.0, 2025.0, 2030.0]
    lad = pos["orders"][0]["ladder"]
    assert lad["budget"] == 40.0 and lad["used"] == 40.0 and lad["cap"] == 90.0


def test_trade_sl_leg_capped_at_max_sl_per_trade(monkeypatch):
    """Trade SL 1000 over 5 legs = $200 per leg, but one stop is at most $90."""
    c = _client("a")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", c, lot=0.05, trade_sl=1000.0, max_sl=90.0)])
    asyncio.run(lt.place_order(2, _sig(5)))
    assert {p["sl"] for p in c.placed} == {1910.5}          # 90 / (0.01*100) = 90.00 away


def test_no_trade_sl_keeps_channel_sl(monkeypatch):
    c = _client("a")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", c, lot=0.05)])
    pos = asyncio.run(lt.place_order(3, _sig(5)))
    assert {p["sl"] for p in c.placed} == {1990.0}
    assert "ladder" not in pos["orders"][0]


def _stopped_leg(budget=200.0, used=90.0, last=90.0, attempt=0, tp=2010.0):
    return {"tp_index": 1, "tp": tp, "ticket_id": "t1", "kind": "market", "volume": 0.01,
            "entry": 2000.5, "sl": 1910.5, "account": "a", "broker_state": "closed",
            "ladder": {"budget": budget, "cap": 90.0, "used": used, "last": last,
                       "attempt": attempt, "base": 1}}


def _setup_reenter(monkeypatch, client):
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", client)])
    inserted = []
    monkeypatch.setattr(db, "insert_order", lambda mid, o: inserted.append((mid, o)))
    return inserted


def test_ladder_reenters_90_then_20_until_budget_spent(monkeypatch):
    """$200 leg: stops of 90, 90, then 20 — then no more re-entries."""
    c = _client("a", ask=2000.5)
    inserted = _setup_reenter(monkeypatch, c)
    pos = {"side": "buy", "instrument": "XAUUSD"}

    first = _stopped_leg()
    loop = asyncio.new_event_loop()
    try:
        new = loop.run_until_complete(lt._ladder_reenter(loop, pos, 7, first, "a", -90.0))
        assert new["tp_index"] == 101 and new["tp"] == 2010.0
        assert c.placed[-1]["sl"] == 1910.5 and c.placed[-1]["comment"] == "tg-7-tp101"
        assert new["ladder"]["used"] == 180.0
        new["broker_state"] = "closed"
        third = loop.run_until_complete(lt._ladder_reenter(loop, pos, 7, new, "a", -90.0))
        assert third["tp_index"] == 201
        assert c.placed[-1]["sl"] == 1980.5                  # last $20 -> 20.00 away
        assert third["ladder"]["used"] == 200.0
        assert loop.run_until_complete(lt._ladder_reenter(loop, pos, 7, third, "a", -20.0)) is None
    finally:
        loop.close()
    assert [o["tp_index"] for _, o in inserted] == [101, 201]
    assert first["ladder"]["reentered"] is True


@pytest.mark.parametrize("pnl", [-1.0, 0.0, 5.0, None])
def test_no_reentry_on_breakeven_or_profit(monkeypatch, pnl):
    c = _client("a")
    _setup_reenter(monkeypatch, c)
    leg = _stopped_leg()
    assert _run(lambda lp: lt._ladder_reenter(lp, {"side": "buy", "instrument": "XAUUSD"},
                                              7, leg, "a", pnl)) is None
    assert c.placed == []


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro(loop))
    finally:
        loop.close()


def test_no_reentry_when_ladder_stopped_or_tp_passed_or_blocked(monkeypatch):
    pos = {"side": "buy", "instrument": "XAUUSD"}
    c = _client("a", ask=2011.0)                    # price already through TP 2010
    _setup_reenter(monkeypatch, c)
    assert _run(lambda lp: lt._ladder_reenter(lp, pos, 7, _stopped_leg(), "a", -90.0)) is None
    c2 = _client("a")
    _setup_reenter(monkeypatch, c2)
    leg = _stopped_leg()
    leg["ladder"]["stopped"] = True                 # channel moved the SL (breakeven)
    assert _run(lambda lp: lt._ladder_reenter(lp, pos, 7, leg, "a", -90.0)) is None
    lt.ACCOUNTS[0]["entries"] = False               # paused on the dashboard
    assert _run(lambda lp: lt._ladder_reenter(lp, pos, 7, _stopped_leg(), "a", -90.0)) is None
    assert c2.placed == []


# ── Drawdown guard ───────────────────────────────────────────────────────────
class _GuardClient:
    def __init__(self, equity, broker_time=None):
        self.label = "acc"
        self.account = "meta-1"
        self.equity = equity
        self.broker_time = broker_time or datetime(2026, 10, 1, 12, 0, 0)
        self.closed = 0

    def get_account_information(self):
        return {"equity": self.equity, "balance": self.equity}

    def get_broker_time(self):
        return self.broker_time

    def close_everything(self):
        self.closed += 1
        return {"positions": 3, "orders": 1, "failed": 0, "complete": True}


def _guard(monkeypatch, client, cfg, ticks=1):
    saved = []
    monkeypatch.setattr(apis, "save_drawdown", lambda ub, **f: saved.append(f) or True)
    for _ in range(ticks):
        _run(lambda lp: lt._guard_account(lp, "ub-1", client, cfg))
    return saved


def _cfg(daily=4500.0, mx_=4000.0, dd_day=date(2026, 10, 1), blocked=None):
    return {"daily_dd_floor": daily, "max_dd_floor": mx_, "daily_dd_offset": 230.0,
            "max_dd_offset": 500.0, "dd_day": dd_day, "dd_blocked_day": blocked}


def test_guard_ok_above_floors(monkeypatch):
    c = _GuardClient(4700.0)
    saved = _guard(monkeypatch, c, _cfg())
    assert c.closed == 0
    assert saved[-1]["dd_status"] == "ok" and saved[-1]["dd_equity"] == 4700.0
    assert not lt._dd_blocked({"ub_id": "ub-1"})


def test_guard_closes_everything_at_daily_floor_and_blocks_day(monkeypatch):
    c = _GuardClient(4700.0)
    cfg = _cfg()
    _guard(monkeypatch, c, cfg)                     # arms (equity seen above floors)
    c.equity = 4499.0
    saved = _guard(monkeypatch, c, cfg)
    assert c.closed == 1
    assert saved[-1]["dd_status"] == "breached_daily"
    assert saved[-1]["dd_blocked_day"] == date(2026, 10, 1)
    assert lt._dd_blocked({"ub_id": "ub-1"})


def test_guard_closes_at_max_floor(monkeypatch):
    c = _GuardClient(4700.0)
    cfg = _cfg(daily=None)
    _guard(monkeypatch, c, cfg)
    c.equity = 3999.0
    saved = _guard(monkeypatch, c, cfg)
    assert c.closed == 1 and saved[-1]["dd_status"] == "breached_max"


def test_guard_near_floor_blocks_without_closing(monkeypatch):
    c = _GuardClient(4700.0)
    cfg = _cfg()
    _guard(monkeypatch, c, cfg)
    c.equity = 4508.0                               # within $10 of 4500
    saved = _guard(monkeypatch, c, cfg)
    assert c.closed == 0
    assert saved[-1]["dd_status"] == "near_daily"
    assert lt._dd_blocked({"ub_id": "ub-1"})


def test_guard_floor_above_equity_when_first_seen_never_closes(monkeypatch):
    c = _GuardClient(4400.0)                        # floor 4500 already above equity
    saved = _guard(monkeypatch, c, _cfg())
    assert c.closed == 0
    assert saved[-1]["dd_status"] == "floor_above_equity"
    assert lt._dd_blocked({"ub_id": "ub-1"})


def test_guard_new_broker_day_resets_floors_from_equity(monkeypatch):
    c = _GuardClient(4620.0, broker_time=datetime(2026, 10, 2, 0, 5, 0))
    cfg = _cfg(dd_day=date(2026, 10, 1), blocked=date(2026, 10, 1))
    saved = _guard(monkeypatch, c, cfg)
    assert saved[0]["daily_dd_floor"] == 4390.0     # 4620 - 230
    assert saved[0]["max_dd_floor"] == 4120.0       # 4620 - 500
    assert saved[0]["dd_day"] == date(2026, 10, 2)
    assert not lt._dd_blocked({"ub_id": "ub-1"})    # yesterday's block is over
    assert c.closed == 0


def test_guard_adopts_fresh_floors_for_today(monkeypatch):
    c = _GuardClient(4700.0)
    saved = _guard(monkeypatch, c, _cfg(dd_day=None))
    assert saved[0]["dd_day"] == date(2026, 10, 1)
    assert "daily_dd_floor" not in saved[0]         # user's value kept, not reset


def test_blocked_account_takes_no_entries(monkeypatch):
    a = _acc("a", _client("a"))
    lt._dd_state["ub-a"] = {"day": date(2026, 10, 1), "blocked_day": date(2026, 10, 1)}
    monkeypatch.setattr(lt, "ACCOUNTS", [a])
    assert lt._entry_accounts() == []


# ── VIP priority ─────────────────────────────────────────────────────────────
class _Store:
    def __init__(self):
        self.kv, self.sets = {}, {}

    async def get(self, k):
        return self.kv.get(k)

    async def set(self, k, v):
        self.kv[k] = v

    async def sadd(self, k, v):
        self.sets.setdefault(k, set()).add(v)


def _priority_setup(monkeypatch, vip_answers):
    shared = _acc("s", _client("s"), lot=0.05)
    monkeypatch.setattr(lt, "ACCOUNTS", [shared])
    monkeypatch.setattr(lt, "PRIORITY_CHANNEL", "-100vip")
    monkeypatch.setattr(lt, "PRIORITY_WAIT_SEC", 1.2)
    answers = iter(vip_answers)
    monkeypatch.setattr(db, "find_channel_match", lambda *a, **k: next(answers, None))
    monkeypatch.setattr(db, "insert_signal", lambda pos, ch: None)
    monkeypatch.setattr(db, "insert_order", lambda mid, o: None)
    monkeypatch.setattr(lt, "_record_signals", lambda *a, **k: None)
    store = _Store()
    monkeypatch.setattr(lt, "r", store)
    return shared, store


def test_shared_account_skips_when_vip_posts_during_wait(monkeypatch):
    shared, store = _priority_setup(monkeypatch, [None, 777])
    asyncio.run(lt._deferred_priority_entry(9, _sig(3), [shared], "txt", "2026-10-01T00:00:00"))
    assert shared["client"].placed == []
    assert store.kv == {}


def test_shared_account_trades_neymar_when_vip_never_posts(monkeypatch):
    shared, store = _priority_setup(monkeypatch, [])
    asyncio.run(lt._deferred_priority_entry(9, _sig(3), [shared], "txt", "2026-10-01T00:00:00"))
    assert len(shared["client"].placed) == 3
    pos = json.loads(store.kv[f"{lt.REDIS_PREFIX}:signal:9"])
    assert {o["account"] for o in pos["orders"]} == {"s"}
    assert "9" in store.sets[f"{lt.REDIS_PREFIX}:open"]


def test_deferred_orders_merge_into_existing_signal(monkeypatch):
    shared, store = _priority_setup(monkeypatch, [])
    key = f"{lt.REDIS_PREFIX}:signal:9"
    store.kv[key] = json.dumps({"msg_id": 9, "status": "submitted",
                                "orders": [{"account": "own", "tp_index": 1}]})
    asyncio.run(lt._deferred_priority_entry(9, _sig(3), [shared], "txt", "2026-10-01T00:00:00"))
    pos = json.loads(store.kv[key])
    assert [o["account"] for o in pos["orders"]] == ["own", "s", "s", "s"]


# ── Parallel leg placement ───────────────────────────────────────────────────
def test_legs_placed_in_parallel_and_rolled_back_on_failure():
    c = _RealClient("tok", "acct", dry_run=False, label="x")
    closed = []
    calls = []

    def market(side, symbol, volume, sl, tp, comment=""):
        calls.append(comment)
        return None if comment.endswith("tp2") else f"t-{comment}"
    c.place_market_order_full = market
    c.close_position = lambda tid: closed.append(tid) or True
    plan = {"use_market": True, "levels": [(1990.0, 2010.0), (1990.0, 2015.0), (1990.0, 2020.0)],
            "min_d": 1.0, "cur": 2000.5}
    out = c.submit_signal_orders(side="buy", symbol="XAUUSD", entry=2000.0, sl=1990.0,
                                 tps=[2010.0, 2015.0, 2020.0], total_volume=0.03, msg_id=5, plan=plan)
    assert out == []
    assert sorted(calls) == ["tg-5-tp1", "tg-5-tp2", "tg-5-tp3"]
    assert sorted(closed) == ["t-tg-5-tp1", "t-tg-5-tp3"]


def test_legs_keep_tp_order():
    c = _RealClient("tok", "acct", dry_run=False, label="x")
    c.place_market_order_full = lambda side, symbol, volume, sl, tp, comment="": f"t-{comment}"
    plan = {"use_market": True, "levels": [(1990.0, 2010.0 + i) for i in range(6)],
            "min_d": 1.0, "cur": 2000.5}
    out = c.submit_signal_orders(side="buy", symbol="XAUUSD", entry=2000.0, sl=1990.0,
                                 tps=[2010.0 + i for i in range(6)], total_volume=0.06,
                                 msg_id=6, plan=plan)
    assert [o["tp_index"] for o in out] == [1, 2, 3, 4, 5, 6]


# ── $90 cap on the channel's own SL, and on "move SL" ─────────────────────────
def test_channel_sl_wider_than_cap_is_capped_and_laddered(monkeypatch):
    """0.5 lot, 5 legs = 0.1/leg; channel SL 10.5 away = $105/leg > $90 cap."""
    c = _client("a")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", c, lot=0.5)])
    pos = asyncio.run(lt.place_order(11, _sig(5)))
    assert {p["sl"] for p in c.placed} == {1991.5}            # 2000.5 - 90/(0.1*100) = 9.0
    lad = pos["orders"][0]["ladder"]
    assert lad["budget"] == 105.0 and lad["used"] == 90.0


def test_channel_sl_within_cap_untouched(monkeypatch):
    c = _client("a")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("a", c, lot=0.05)])  # $10.5/leg
    pos = asyncio.run(lt.place_order(12, _sig(5)))
    assert {p["sl"] for p in c.placed} == {1990.0}
    assert all("ladder" not in o for o in pos["orders"])


class _ModBroker:
    label = "a"
    account = "meta-a"

    def __init__(self, bid=2000.0):
        self.bid = bid
        self.moved = []

    def get_symbol_price(self, symbol):
        return {"bid": self.bid, "ask": self.bid + 0.2}

    def modify_position_sl(self, t, sl, tp=None):
        self.moved.append((t, sl))
        return True


def _mod_setup(monkeypatch, broker, *, equity=None, floors=(None, None)):
    acc = _acc("a", broker, ub_id="ub-a")
    monkeypatch.setattr(lt, "ACCOUNTS", [acc])
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"a": broker})
    monkeypatch.setattr(lt.db, "update_sl", lambda *a: None)
    if equity is not None:
        lt._dd_state["ub-a"] = {"equity": equity}
        monkeypatch.setattr(lt, "_dd_cfg", {"ub-a": {"daily_dd_floor": floors[0],
                                                     "max_dd_floor": floors[1]}})
    orders = [{"tp_index": i, "tp": 2010.0, "ticket_id": f"t{i}", "kind": "market",
               "volume": 0.1, "entry": 2000.0, "fill_price": 2000.0, "sl": 1995.0,
               "broker_state": "filled", "account": "a"} for i in (1, 2)]
    key = f"{lt.REDIS_PREFIX}:signal:50"
    store = {key: json.dumps({"side": "buy", "instrument": "XAUUSD", "entry_mid": 2000.0,
                              "sl": 1995.0, "orders": orders})}

    class S:
        async def get(self, k):
            return store.get(k)

        async def set(self, k, v):
            store[k] = v
    monkeypatch.setattr(lt, "r", S())
    return store, key


def test_move_sl_within_cap_moves_exactly(monkeypatch):
    b = _ModBroker()
    store, key = _mod_setup(monkeypatch, b)
    asyncio.run(lt.modify_sl(50, 1993.0))                     # $70/leg
    assert b.moved == [("t1", 1993.0), ("t2", 1993.0)]


def test_move_sl_beyond_cap_stops_at_cap_then_ladders(monkeypatch):
    b = _ModBroker()
    store, key = _mod_setup(monkeypatch, b)
    asyncio.run(lt.modify_sl(50, 1980.0))                     # $200/leg target
    assert {sl for _, sl in b.moved} == {1991.0}              # $90 stop: 9.0 below entry
    o = json.loads(store[key])["orders"][0]
    assert o["ladder"]["budget"] == 200.0 and o["ladder"]["used"] == 90.0


def test_move_sl_skipped_when_it_would_reach_drawdown(monkeypatch):
    b = _ModBroker()
    # equity 4600, daily floor 4500: two legs at $90 + $110 remaining each = $400 > room
    store, key = _mod_setup(monkeypatch, b, equity=4600.0, floors=(4500.0, None))
    asyncio.run(lt.modify_sl(50, 1980.0))
    assert b.moved == []
    assert json.loads(store[key])["orders"][0]["sl"] == 1995.0


def test_tightening_move_always_allowed_even_near_drawdown(monkeypatch):
    b = _ModBroker()
    store, key = _mod_setup(monkeypatch, b, equity=4520.0, floors=(4500.0, None))
    asyncio.run(lt.modify_sl(50, 1998.0))
    assert b.moved == [("t1", 1998.0), ("t2", 1998.0)]


def test_reentry_skipped_when_drawdown_room_too_small(monkeypatch):
    c = _client("a")
    _setup_reenter(monkeypatch, c)
    lt.ACCOUNTS[0]["ub_id"] = "ub-a"
    lt._dd_state["ub-a"] = {"equity": 4550.0}
    monkeypatch.setattr(lt, "_dd_cfg", {"ub-a": {"daily_dd_floor": 4500.0, "max_dd_floor": None}})
    assert _run(lambda lp: lt._ladder_reenter(lp, {"side": "buy", "instrument": "XAUUSD"},
                                              7, _stopped_leg(), "a", -90.0)) is None
    assert c.placed == []
