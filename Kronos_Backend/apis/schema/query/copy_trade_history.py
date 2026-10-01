"""History of a Telegram copy-trade tab (Neymar / Neymar VIP): every signal the
channel posted, with the orders each account placed for it and how they ended.

Reads the copy-trader's own tables (tg_signals / tg_orders, same database,
written by KronosStrategies/Telegram_Bot) plus the dashboard's StrategySignal
rows for signals that were NOT traded (paused, duplicate, no-pyramiding...).
"""
from datetime import timedelta

import graphene
from django.db import connection
from django.utils import timezone

from apis.copy_trade import SOURCE_CHANNEL, SOURCE_STRATEGY_IDS
from apis.models import StrategySignal, UserStrategy
from apis.schema.utils import user_authenticate

MAX_DAYS = 365


class CopyTradeOrderType(graphene.ObjectType):
    account = graphene.String()
    tp_index = graphene.Int()
    kind = graphene.String()
    volume = graphene.Float()
    entry = graphene.Float()
    fill_price = graphene.Float()
    sl = graphene.Float()
    tp = graphene.Float()
    broker_state = graphene.String()
    realized_pnl = graphene.Float()
    created_at = graphene.DateTime()
    closed_at = graphene.DateTime()
    ticket_id = graphene.String()


class CopyTradeSignalType(graphene.ObjectType):
    msg_id = graphene.String()
    posted_at = graphene.DateTime()
    side = graphene.String()
    entry_low = graphene.Float()
    entry_high = graphene.Float()
    sl = graphene.Float()
    tps = graphene.List(graphene.Float)
    total_volume = graphene.Float()
    status = graphene.String()
    close_reason = graphene.String()
    realized_pnl = graphene.Float()
    closed_at = graphene.DateTime()
    raw = graphene.String()
    traded = graphene.Boolean()
    rejection_reason = graphene.String()
    orders = graphene.List(CopyTradeOrderType)


def _f(v):
    return float(v) if v is not None else None


def _account_names(source: str, user) -> dict[str, tuple[str, bool]]:
    """Copy-trader account label -> (account name, visible to this user)."""
    ids = SOURCE_STRATEGY_IDS[source]
    rows = (UserStrategy.objects.filter(strategy_id__in=ids)
            .select_related("user_broker").order_by("created_at"))
    out: dict[str, tuple[str, bool]] = {}
    for us in rows:
        b = us.user_broker
        name = b.label or b.meta_account_id or str(b.id)[:8]
        mine = user.is_superuser or b.user_id == user.id
        out[f"us-{str(us.id)[:8]}"] = (name, mine)
        if str(us.strategy_id) == ids[0]:
            out.setdefault("primary", (name, mine))     # the bot's env account
        elif len(ids) > 1 and str(us.strategy_id) == ids[1]:
            out.setdefault("neymar2", (name, mine))
    return out


def _fetch(sql: str, params) -> list[tuple]:
    try:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except Exception:
        return []        # copy-trader tables not created yet (e.g. a fresh DB)


class CopyTradeHistory(graphene.ObjectType):
    copy_trade_history = graphene.List(
        CopyTradeSignalType, source=graphene.String(required=True), days=graphene.Int())

    @user_authenticate
    def resolve_copy_trade_history(self, info, source, days=30):
        channel = SOURCE_CHANNEL.get(source)
        if channel is None:
            return []
        since = timezone.now() - timedelta(days=max(1, min(int(days or 30), MAX_DAYS)))
        names = _account_names(source, info.context.user)

        signals = _fetch(
            """SELECT msg_id, posted_at, side, entry_low, entry_high, sl, tps, total_volume,
                      status, close_reason, realized_pnl, closed_at, raw
                 FROM tg_signals WHERE channel = %s AND posted_at >= %s
                ORDER BY posted_at DESC""",
            [channel, since])
        orders_by_msg: dict = {}
        if signals:
            for (mid, tid, idx, kind, vol, entry, fill, sl, tp, state, pnl, created, closed,
                 account) in _fetch(
                    """SELECT msg_id, ticket_id, tp_index, kind, volume, entry, fill_price, sl, tp,
                              broker_state, realized_pnl, created_at, closed_at, account
                         FROM tg_orders WHERE msg_id = ANY(%s) ORDER BY account, tp_index""",
                    [[s[0] for s in signals]]):
                name, mine = names.get(account or "primary", (account or "primary", info.context.user.is_superuser))
                if not mine:
                    continue
                orders_by_msg.setdefault(mid, []).append(CopyTradeOrderType(
                    account=name, tp_index=idx, kind=kind, volume=_f(vol), entry=_f(entry),
                    fill_price=_f(fill), sl=_f(sl), tp=_f(tp), broker_state=state,
                    realized_pnl=_f(pnl), created_at=created, closed_at=closed,
                    ticket_id=str(tid)))

        out = [CopyTradeSignalType(
            msg_id=str(mid), posted_at=posted, side=side, entry_low=_f(lo), entry_high=_f(hi),
            sl=_f(sl), tps=[float(t) for t in (tps or [])], total_volume=_f(vol), status=status,
            close_reason=reason, realized_pnl=_f(pnl), closed_at=closed, raw=raw, traded=True,
            orders=orders_by_msg.get(mid, []))
            for (mid, posted, side, lo, hi, sl, tps, vol, status, reason, pnl, closed, raw) in signals]

        # Signals the channel posted that were NOT traded (one row per signal).
        traded_at = [(s.posted_at, (s.side or "").lower()) for s in out if s.posted_at]
        seen = set()
        for sig in (StrategySignal.objects.filter(strategy_id__in=SOURCE_STRATEGY_IDS[source],
                                                  status="REJECTED", created_at__gte=since)
                    .order_by("-created_at")):
            at = sig.signal_at or sig.created_at
            side = (sig.side or "").lower()
            if any(abs((at - t).total_seconds()) <= 180 and side == sd for t, sd in traded_at):
                continue        # an account-level rejection of a signal that WAS traded
            key = (at.replace(second=0, microsecond=0), side, sig.entry_price)
            if key in seen:
                continue
            seen.add(key)
            out.append(CopyTradeSignalType(
                msg_id=None, posted_at=at, side=side, entry_low=_f(sig.entry_price),
                entry_high=_f(sig.entry_price), sl=_f(sig.stop_loss),
                tps=[float(sig.take_profit)] if sig.take_profit is not None else [],
                traded=False, rejection_reason=sig.rejection_reason, orders=[]))
        out.sort(key=lambda s: s.posted_at or since, reverse=True)
        return out
