"""Dashboard-managed copy-trade accounts ("Add Data" on the Neymar tabs).

Every UserStrategy on the bot's Strategy is traded at its fixed lot_size
("Price" = TOTAL lot per signal, split across the TP legs); each row's
Pause/Resume gates that account only; an unreachable added account is isolated
instead of stalling the others.
"""
import asyncio

from cryptography.fernet import Fernet

import apis_persist as apis
import live_trader as lt
import metaapi_orders as mx

_RealClient = mx.MetaApiClient  # tests below monkeypatch mx.MetaApiClient


def _client(label, positions=()):
    c = _RealClient("tok", f"acct-{label}", dry_run=False, label=label)
    c._trading_url = "https://h"
    c.get_symbol_price = lambda symbol: {"bid": 2000.3, "ask": 2000.5}
    c._get_symbol_spec = lambda b: {"stops_level_price": 1.0, "tick_size": 0.01}
    c.get_open_positions = lambda symbol, _p=list(positions): list(_p)
    c.placed = []

    def rec_market(side, symbol, volume, sl, tp, comment=""):
        c.placed.append(volume)
        return f"{label}-m-{len(c.placed)}"

    c.place_market_order_full = rec_market
    c.place_limit_order = lambda *a, **k: (None, None)
    return c


def _acc(label, client, *, lot=None, entries=True, source="env", us_id=None):
    return {"label": label, "client": client, "risk_usd": 100.0, "apis": None,
            "source": source, "us_id": us_id or label, "lot": lot, "entries": entries,
            "healthy": True}


def _sig(n_tps=3):
    return {"side": "buy", "instrument": "XAUUSD", "entry_low": 1995.0, "entry_high": 2000.0,
            "sl": 1990.0, "tps": [2005.0 + 5 * i for i in range(n_tps)]}


def test_fixed_lot_is_total_split_across_tps(monkeypatch):
    primary, added = _client("primary"), _client("added")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary),
                                         _acc("us-1", added, lot=0.3, source="db")])
    asyncio.run(lt.place_order(1, _sig(3)))
    assert added.placed == [0.1, 0.1, 0.1]          # 0.3 total / 3 TPs
    assert len(primary.placed) == 3                  # risk-based account still trades


def test_fixed_lot_never_below_min_per_leg(monkeypatch):
    added = _client("added")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", _client("primary")),
                                         _acc("us-1", added, lot=0.01, source="db")])
    asyncio.run(lt.place_order(2, _sig(3)))
    assert added.placed == [0.01, 0.01, 0.01]


def test_env_account_uses_its_price_too(monkeypatch):
    primary = _client("primary")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary, lot=0.06)])
    asyncio.run(lt.place_order(3, _sig(3)))
    assert primary.placed == [0.02, 0.02, 0.02]


def test_paused_or_unhealthy_accounts_take_no_entries(monkeypatch):
    primary, paused, broken = _client("primary"), _client("paused"), _client("broken")
    b = _acc("us-3", broken, lot=0.1, source="db")
    b["healthy"] = False
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary),
                                         _acc("us-2", paused, lot=0.1, entries=False, source="db"),
                                         b])
    pos = asyncio.run(lt.place_order(4, _sig(3)))
    assert paused.placed == [] and broken.placed == []
    assert {o["account"] for o in pos["orders"]} == {"primary"}


def test_paused_primary_does_not_stop_added_accounts(monkeypatch):
    primary, added = _client("primary"), _client("added")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary, entries=False),
                                         _acc("us-1", added, lot=0.3, source="db")])
    pos = asyncio.run(lt.place_order(5, _sig(3)))
    assert primary.placed == []
    assert {o["account"] for o in pos["orders"]} == {"us-1"}


def test_unreachable_added_account_does_not_block_classification(monkeypatch):
    primary = _client("primary")
    broken = _client("broken")
    broken.get_open_positions = lambda symbol: None
    b = _acc("us-9", broken, source="db")
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary), b])

    class _Store:
        async def get(self, k):
            return None
    monkeypatch.setattr(lt, "r", _Store())
    live, unfilled, ok = asyncio.run(lt._classify_open_signals(["42"]))
    assert ok is True and b["healthy"] is False


def test_unreachable_env_account_still_fails_safe(monkeypatch):
    primary = _client("primary")
    primary.get_open_positions = lambda symbol: None
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", primary)])

    class _Store:
        async def get(self, k):
            return None
    monkeypatch.setattr(lt, "r", _Store())
    assert asyncio.run(lt._classify_open_signals(["42"]))[2] is False


def _row(us_id, *, strategy, lot=None, entries=True, meta="acct-new", token_enc=""):
    return {"user_strategy_id": us_id, "strategy_id": strategy, "lot_size": lot,
            "entries": entries, "user_broker_id": "ub-" + us_id, "meta_account_id": meta,
            "token_enc": token_enc}


def test_refresh_loads_new_account_and_syncs_env_rows(monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key.decode())
    monkeypatch.setenv("META_ACCOUNT_ID", "acct-primary")
    enc = Fernet(key).encrypt(b"tok-new").decode()
    strat = apis.STRATEGY_ID
    primary = _client("primary")
    accounts = [_acc("primary", primary, us_id="us-primary")]
    monkeypatch.setattr(lt, "ACCOUNTS", accounts)
    monkeypatch.setattr(lt, "ACCOUNTS_BY_LABEL", {"primary": primary})
    monkeypatch.setattr(lt, "APIS_BY_LABEL", {"primary": None})
    monkeypatch.setattr(lt, "DB_ACCOUNTS", True)
    rows = [
        _row("us-primary", strategy=strat, lot=0.2, entries=False, meta="acct-primary"),
        _row("11111111-new", strategy=strat, lot=0.1, token_enc=enc),
        _row("22222222-dup", strategy=strat, meta="acct-primary", token_enc=enc),  # same acct as env
        _row("33333333-paused", strategy=strat, entries=False, token_enc=enc),
        _row("44444444-nocreds", strategy=strat, meta=""),
    ]
    monkeypatch.setattr(apis, "load_account_rows", lambda sid, ids: rows)
    made = []

    def fake_client(token, acct, **kw):
        made.append((token, acct))
        return _client(kw.get("label", "x"))
    monkeypatch.setattr(mx, "MetaApiClient", fake_client)

    assert asyncio.run(lt.refresh_accounts()) is True
    assert accounts[0]["lot"] == 0.2 and accounts[0]["entries"] is False   # env row synced
    labels = [a["label"] for a in accounts]
    assert labels == ["primary", "us-11111111"]                             # only the valid new one
    assert made == [("tok-new", "acct-new")]                              # token decrypted
    assert accounts[1]["lot"] == 0.1 and accounts[1]["source"] == "db"
    assert "us-11111111" in lt.ACCOUNTS_BY_LABEL and "us-11111111" in lt.APIS_BY_LABEL

    # second refresh: nothing re-added; a pause on the dashboard reaches the account
    rows[1]["entries"] = False
    assert asyncio.run(lt.refresh_accounts()) is True
    assert len(accounts) == 2 and accounts[1]["entries"] is False


def test_refresh_fails_closed_when_db_unreachable(monkeypatch):
    monkeypatch.setattr(lt, "ACCOUNTS", [_acc("primary", _client("primary"))])
    monkeypatch.setattr(apis, "load_account_rows", lambda sid, ids: None)
    assert asyncio.run(lt.refresh_accounts()) is False


def test_unreachable_new_account_is_not_added(monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key.decode())
    enc = Fernet(key).encrypt(b"tok").decode()
    accounts = [_acc("primary", _client("primary"), us_id="us-primary")]
    monkeypatch.setattr(lt, "ACCOUNTS", accounts)
    monkeypatch.setattr(lt, "DB_ACCOUNTS", True)
    monkeypatch.setattr(apis, "load_account_rows", lambda sid, ids: [
        _row("us-primary", strategy=apis.STRATEGY_ID),
        _row("55555555-down", strategy=apis.STRATEGY_ID, token_enc=enc)])

    def down_client(token, acct, **kw):
        c = _client("down")
        c.get_open_positions = lambda symbol: None
        return c
    monkeypatch.setattr(mx, "MetaApiClient", down_client)
    assert asyncio.run(lt.refresh_accounts()) is True
    assert [a["label"] for a in accounts] == ["primary"]
