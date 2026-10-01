"""AddCopyTradeAccount / SetCopyTradeLot — the Neymar tabs' "Add Data" + "Price"."""
from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from apis.copy_trade import SOURCE_STRATEGY_IDS, parse_lot
from apis.models import CurrencyPair, Strategy, User, UserBroker, UserStrategy

NEYMAR_ID = SOURCE_STRATEGY_IDS["neymar"][0]
NEYMAR2_ID = SOURCE_STRATEGY_IDS["neymar"][1]
VIP_ID = SOURCE_STRATEGY_IDS["neymar-vip"][0]


def _info(user):
    return SimpleNamespace(context=SimpleNamespace(user=user))


class CopyTradeTestBase(TestCase):
    def setUp(self):
        cp, _ = CurrencyPair.objects.get_or_create(
            symbol="XAUUSD", defaults={"name": "XAUUSD", "ltp": "4540.00"})
        for sid, name in ((NEYMAR_ID, "Neymar Telegram Copy"),
                          (NEYMAR2_ID, "Neymar Telegram Copy (Account 2)"),
                          (VIP_ID, "Neymar VIP")):
            Strategy.objects.create(id=sid, name=name, currencypair=cp, is_active=True)
        self.user = User.objects.create(email=f"u-{uuid.uuid4()}@test.local",
                                        first_name="U", last_name="U")

    def broker(self, user=None, *, meta="acct-1", token="enc-token", active=True):
        return UserBroker.objects.create(
            user=user or self.user, api_key=str(uuid.uuid4()), label="Acc",
            meta_account_id=meta, meta_api_token_enc=token, is_active=active)

    def add(self, broker, source="neymar", lot=0.1, user=None):
        from apis.schema.mutation.user.add_copy_trade_account import AddCopyTradeAccount
        return AddCopyTradeAccount.mutate(None, _info(user or self.user), source=source,
                                          user_broker_id=str(broker.id), lot_size=lot)


class ParseLotTests(TestCase):
    def test_valid(self):
        self.assertEqual(parse_lot(0.1), (Decimal("0.10"), None))
        self.assertEqual(parse_lot("0.25")[0], Decimal("0.25"))
        self.assertEqual(parse_lot(1)[0], Decimal("1.00"))

    def test_invalid(self):
        for bad in (0, 0.001, -1, 0.015, 101, "abc", float("nan"), None):
            lot, err = parse_lot(bad)
            self.assertIsNone(lot, bad)
            self.assertTrue(err, bad)


class AddCopyTradeAccountTests(CopyTradeTestBase):
    def test_adds_account_under_source_strategy_with_lot(self):
        b = self.broker()
        res = self.add(b, lot=0.1)
        self.assertTrue(res.Ok, res.Response)
        us = UserStrategy.objects.get(user_broker=b)
        self.assertEqual(str(us.strategy_id), NEYMAR_ID)
        self.assertEqual(us.lot_size, Decimal("0.10"))
        self.assertTrue(us.is_active and us.deployed)

    def test_vip_source(self):
        b = self.broker()
        self.assertTrue(self.add(b, source="neymar-vip").Ok)
        self.assertEqual(str(UserStrategy.objects.get(user_broker=b).strategy_id), VIP_ID)

    def test_same_account_allowed_in_both_tabs(self):
        b = self.broker()
        self.assertTrue(self.add(b, source="neymar").Ok)
        self.assertTrue(self.add(b, source="neymar-vip").Ok)
        self.assertEqual(UserStrategy.objects.filter(user_broker=b).count(), 2)

    def test_duplicate_in_same_tab_rejected(self):
        b = self.broker()
        self.add(b)
        res = self.add(b)
        self.assertFalse(res.Ok)
        self.assertIn("already", res.Response)

    def test_account_2_row_counts_as_in_neymar_tab(self):
        b = self.broker()
        UserStrategy.objects.create(strategy_id=NEYMAR2_ID, user_broker=b)
        self.assertFalse(self.add(b).Ok)

    def test_missing_metaapi_creds_rejected(self):
        for kw in ({"meta": ""}, {"token": ""}):
            res = self.add(self.broker(**kw))
            self.assertFalse(res.Ok)
            self.assertIn("MetaAPI", res.Response)

    def test_inactive_account_rejected(self):
        self.assertFalse(self.add(self.broker(active=False)).Ok)

    def test_bad_lot_rejected(self):
        res = self.add(self.broker(), lot=0.005)
        self.assertFalse(res.Ok)
        self.assertFalse(UserStrategy.objects.exists())

    def test_unknown_source_rejected(self):
        self.assertFalse(self.add(self.broker(), source="other").Ok)

    def test_other_users_account_rejected(self):
        other = User.objects.create(email=f"o-{uuid.uuid4()}@test.local",
                                    first_name="O", last_name="O")
        res = self.add(self.broker(user=other))
        self.assertFalse(res.Ok)
        self.assertFalse(UserStrategy.objects.exists())


class SetCopyTradeLotTests(CopyTradeTestBase):
    def set_lot(self, us, lot, user=None):
        from apis.schema.mutation.user.set_copy_trade_lot import SetCopyTradeLot
        return SetCopyTradeLot.mutate(None, _info(user or self.user),
                                      user_strategy_id=str(us.id), lot_size=lot)

    def test_sets_lot(self):
        us = UserStrategy.objects.create(strategy_id=VIP_ID, user_broker=self.broker())
        self.assertTrue(self.set_lot(us, 0.25).Ok)
        us.refresh_from_db()
        self.assertEqual(us.lot_size, Decimal("0.25"))

    def test_rejects_non_copy_trade_strategy(self):
        cp = CurrencyPair.objects.first()
        other = Strategy.objects.create(name="Algo", currencypair=cp)
        us = UserStrategy.objects.create(strategy=other, user_broker=self.broker())
        self.assertFalse(self.set_lot(us, 0.1).Ok)

    def test_rejects_bad_lot(self):
        us = UserStrategy.objects.create(strategy_id=VIP_ID, user_broker=self.broker())
        self.assertFalse(self.set_lot(us, 0).Ok)
        us.refresh_from_db()
        self.assertIsNone(us.lot_size)


class RiskSettingsTests(CopyTradeTestBase):
    """Daily / Max drawdown are USD loss amounts; floors = equity - amount."""

    def update(self, us, **kw):
        from apis.schema.mutation.user.update_copy_trade_risk import UpdateCopyTradeRisk
        return UpdateCopyTradeRisk.mutate(None, _info(self.user), user_strategy_id=str(us.id), **kw)

    def add_full(self, b, source="neymar-vip", **kw):
        from apis.schema.mutation.user.add_copy_trade_account import AddCopyTradeAccount
        return AddCopyTradeAccount.mutate(None, _info(self.user), source=source,
                                          user_broker_id=str(b.id), lot_size=0.1, **kw)

    def test_add_with_trade_sl_and_drawdown_amounts(self):
        b = self.broker()
        b.dd_equity = Decimal("9864.23"); b.save()
        res = self.add_full(b, trade_sl_usd=200, daily_dd_offset=230, max_dd_offset=480)
        self.assertTrue(res.Ok, res.Response)
        us = UserStrategy.objects.get(user_broker=b)
        self.assertEqual(us.trade_sl_usd, Decimal("200.00"))
        self.assertEqual(us.max_sl_per_trade_usd, Decimal("90.00"))       # default cap
        b.refresh_from_db()
        self.assertEqual(b.daily_dd_offset, Decimal("230.00"))
        self.assertEqual(b.max_dd_offset, Decimal("480.00"))
        self.assertEqual(b.daily_dd_floor, Decimal("9634.23"))            # equity - 230
        self.assertEqual(b.max_dd_floor, Decimal("9384.23"))              # equity - 480
        self.assertIsNone(b.dd_day)                                        # bot adopts for today

    def test_amounts_without_known_equity_leave_floor_to_the_bot(self):
        b = self.broker()
        self.assertTrue(self.add_full(b, daily_dd_offset=230).Ok)
        b.refresh_from_db()
        self.assertEqual(b.daily_dd_offset, Decimal("230.00"))
        self.assertIsNone(b.daily_dd_floor)
        self.assertIsNone(b.max_dd_offset)

    def test_old_floor_arguments_are_ignored(self):
        b = self.broker()
        b.dd_equity = Decimal("9800"); b.save()
        self.assertTrue(self.add_full(b, daily_dd_floor=230, max_dd_floor=480).Ok)
        b.refresh_from_db()
        self.assertIsNone(b.daily_dd_floor)
        self.assertIsNone(b.daily_dd_offset)

    def test_add_without_risk_keeps_channel_sl_and_no_drawdown(self):
        b = self.broker()
        self.assertTrue(self.add(b).Ok)
        us = UserStrategy.objects.get(user_broker=b)
        self.assertIsNone(us.trade_sl_usd)
        b.refresh_from_db()
        self.assertIsNone(b.daily_dd_offset)

    def test_adding_to_second_tab_without_drawdown_keeps_first_tabs_drawdown(self):
        b = self.broker()
        self.add_full(b, source="neymar", daily_dd_offset=230)
        self.assertTrue(self.add(b, source="neymar-vip").Ok)
        b.refresh_from_db()
        self.assertEqual(b.daily_dd_offset, Decimal("230.00"))

    def test_amount_not_below_equity_rejected(self):
        b = self.broker()
        b.dd_equity = Decimal("4600"); b.save()
        res = self.add_full(b, source="neymar", daily_dd_offset=4595)
        self.assertFalse(res.Ok)
        self.assertIn("equity", res.Response)
        self.assertFalse(UserStrategy.objects.exists())

    def test_update_sets_and_clears(self):
        b = self.broker()
        b.dd_equity = Decimal("10000"); b.save()
        us = UserStrategy.objects.create(strategy_id=VIP_ID, user_broker=b)
        res = self.update(us, trade_sl_usd=1000, max_sl_per_trade_usd=90,
                          daily_dd_offset=230, max_dd_offset=500)
        self.assertTrue(res.Ok, res.Response)
        us.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(us.trade_sl_usd, Decimal("1000.00"))
        self.assertEqual(b.daily_dd_floor, Decimal("9770.00"))
        self.assertEqual(b.max_dd_floor, Decimal("9500.00"))
        self.assertIsNone(b.dd_day)
        self.assertTrue(self.update(us).Ok)                   # empty fields clear
        us.refresh_from_db(); b.refresh_from_db()
        self.assertIsNone(us.trade_sl_usd)
        self.assertIsNone(us.max_sl_per_trade_usd)
        self.assertIsNone(b.daily_dd_floor)
        self.assertIsNone(b.daily_dd_offset)
        self.assertIsNone(b.max_dd_offset)

    def test_update_rejects_bad_values(self):
        us = UserStrategy.objects.create(strategy_id=VIP_ID, user_broker=self.broker())
        for kw in ({"trade_sl_usd": -5}, {"daily_dd_offset": 0}, {"max_sl_per_trade_usd": "x"},
                   {"max_dd_offset": -1}):
            self.assertFalse(self.update(us, **kw).Ok, kw)

    def test_update_rejects_non_copy_trade_row(self):
        cp = CurrencyPair.objects.first()
        other = Strategy.objects.create(name="Algo", currencypair=cp)
        us = UserStrategy.objects.create(strategy=other, user_broker=self.broker())
        self.assertFalse(self.update(us, trade_sl_usd=100).Ok)

    def test_editing_amount_keeps_todays_block(self):
        import datetime as dt
        b = self.broker()
        b.daily_dd_offset = Decimal("230"); b.dd_blocked_day = dt.date(2026, 10, 1); b.save()
        us = UserStrategy.objects.create(strategy_id=VIP_ID, user_broker=b)
        self.assertTrue(self.update(us, daily_dd_offset=300).Ok)
        b.refresh_from_db()
        self.assertEqual(b.dd_blocked_day, dt.date(2026, 10, 1))


class CopyTradeHistoryTests(CopyTradeTestBase):
    """copyTradeHistory: untraded signals from StrategySignal (the tg_* tables
    are Postgres-only and are exercised on the live DB)."""

    def history(self, source="neymar-vip", user=None):
        from apis.schema.query.copy_trade_history import CopyTradeHistory
        return CopyTradeHistory.resolve_copy_trade_history(None, _info(user or self.user),
                                                           source=source, days=7)

    def test_untraded_signals_listed_once_with_reason(self):
        from django.utils import timezone
        from apis.models import StrategySignal
        now = timezone.now().replace(second=10)
        for _ in range(2):                         # same signal recorded twice -> one row
            StrategySignal.objects.create(strategy_id=VIP_ID, symbol="XAUUSD", side="SELL",
                                          entry_price=Decimal("4150"), stop_loss=Decimal("4160"),
                                          take_profit=Decimal("4140"), status="REJECTED",
                                          rejection_reason="manager_gate (strategy paused)",
                                          signal_at=now)
        StrategySignal.objects.create(strategy_id=NEYMAR_ID, symbol="XAUUSD", side="BUY",
                                      entry_price=Decimal("4100"), status="REJECTED",
                                      rejection_reason="other tab", signal_at=now)
        rows = self.history()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertFalse(r.traded)
        self.assertEqual(r.side, "sell")
        self.assertEqual(r.rejection_reason, "manager_gate (strategy paused)")
        self.assertEqual(r.tps, [4140.0])

    def test_unknown_source_is_empty(self):
        self.assertEqual(self.history(source="nope"), [])

    def test_requires_login(self):
        from django.contrib.auth.models import AnonymousUser
        from graphql import GraphQLError
        with self.assertRaises(GraphQLError):
            self.history(user=AnonymousUser())
