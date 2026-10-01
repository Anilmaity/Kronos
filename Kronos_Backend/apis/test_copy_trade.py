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
