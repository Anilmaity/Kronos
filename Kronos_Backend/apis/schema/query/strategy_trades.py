"""Per-strategy trade list behind the dashboard's Backtest | Paper | Live
calendar (/strategy-data).

  backtest - trades from the latest backtest_worker replay queued by the
             RunStrategyBacktest mutation (label "strategy:<userStrategyId>").
  paper    - every StrategySignal the strategy fired (placed or rejected),
             played forward on OANDA M1 candles to its SL/TP at PAPER_LOT.
  live     - the strategy's closed Positions on the broker account.
  lab      - display-only research results loaded by hand onto a
             ManagerBacktestRun row labelled "lab:<userStrategyId>" (e.g. the
             averaging ping-pong the live engine cannot trade).

Times go out as UTC epoch seconds. DB datetimes are naive IST wall clock
(USE_TZ=False, TIME_ZONE=Asia/Kolkata - see pnl_calendar.py), hence _IST.
"""
import calendar
import threading
import time as _time
from datetime import datetime, timedelta, timezone

import graphene
from graphql import GraphQLError
from django.db.models import Max

from apis.models import (ManagerBacktestRun, Order, Position, StrategySignal,
                         UserStrategy)
from apis.schema.query import get_candles
from apis.schema.utils import user_authenticate

KINDS = ("backtest", "paper", "live", "lab")
PAPER_LOT = 0.01
USD_PER_POINT_LOT = 100.0          # XAUUSD: 1.0 lot = 100 oz
MAX_HOLD_S = 24 * 3600             # paper trades are force-closed after a day
_IST = timedelta(hours=5, minutes=30)
_PAPER_TTL = 300.0
_PAPER_CACHE = {}                  # (user_strategy_id, year, month) -> (at, trades)
_PAPER_LOCK = threading.Lock()


class StrategyTradeType(graphene.ObjectType):
    entryTime = graphene.Int()
    exitTime = graphene.Int()
    side = graphene.String()
    entryPrice = graphene.Float()
    exitPrice = graphene.Float()
    stopLoss = graphene.Float()
    takeProfit = graphene.Float()
    pnlUsd = graphene.Float()
    outcome = graphene.String()
    note = graphene.String()


class StrategyTradesType(graphene.ObjectType):
    kind = graphene.String()
    status = graphene.String()      # backtest: NONE|PENDING|RUNNING|DONE|FAILED|CANCELLED
    progressPct = graphene.Float()
    error = graphene.String()
    periodStart = graphene.Date()
    periodEnd = graphene.Date()
    baseLot = graphene.Float()      # lot the pnlUsd figures are at; null = real fills
    trades = graphene.List(StrategyTradeType)


def _epoch(naive_ist):
    return int((naive_ist - _IST).replace(tzinfo=timezone.utc).timestamp())


def _month_utc(year, month):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    days = calendar.monthrange(year, month)[1]
    return int(start.timestamp()), int((start + timedelta(days=days)).timestamp())


def backtest_label(user_strategy_id):
    return f"strategy:{user_strategy_id}"


def simulate(signals, bars, lot=PAPER_LOT):
    """signals: [(epoch, side, entry, sl, tp, note)]; bars: ascending
    [(epoch, o, h, l, c)]. Fill at the signal's own entry price, then walk the
    bars after it: stop is checked before target inside a bar (worst case).
    Signals still open when the bars run out are left out."""
    out, i = [], 0
    for ts, side, entry, sl, tp, note in sorted(signals):
        while i < len(bars) and bars[i][0] <= ts:
            i += 1
        buy = side.upper() == "BUY"
        for t, _o, h, low, c in bars[i:]:
            hit_sl = sl is not None and (low <= sl if buy else h >= sl)
            hit_tp = tp is not None and (h >= tp if buy else low <= tp)
            timed = t - ts >= MAX_HOLD_S
            if not (hit_sl or hit_tp or timed):
                continue
            px, outcome = (sl, "SL") if hit_sl else (tp, "TP") if hit_tp else (c, "TIME")
            pts = (px - entry) if buy else (entry - px)
            out.append(dict(
                entryTime=ts, exitTime=t + 60, side=side.upper(), entryPrice=entry,
                exitPrice=px, stopLoss=sl, takeProfit=tp, outcome=outcome, note=note,
                pnlUsd=round(pts * USD_PER_POINT_LOT * lot, 2)))
            break
    return out


def _fetch_m1(start, end):
    """OANDA M1 mid bars covering [start, end], paged backwards."""
    bars, cursor = [], min(end, int(_time.time()))
    while cursor > start:
        page = get_candles._fetch_oanda("XAU_USD", "M1", get_candles._MAX_COUNT, to=cursor)
        page = [b for b in page if b[0] < cursor]
        if not page:
            break
        bars = page + bars
        cursor = page[0][0]
    return [b for b in bars if b[0] >= start]


def _paper(us, year, month):
    key = (str(us.id), year, month)
    with _PAPER_LOCK:
        hit = _PAPER_CACHE.get(key)
        if hit and _time.monotonic() - hit[0] < _PAPER_TTL:
            return hit[1]
    lo, hi = _month_utc(year, month)
    rows = StrategySignal.objects.filter(
        strategy_id=us.strategy_id,
        signal_at__gte=datetime.fromtimestamp(lo, timezone.utc).replace(tzinfo=None) + _IST,
        signal_at__lt=datetime.fromtimestamp(hi, timezone.utc).replace(tzinfo=None) + _IST)
    signals = [(
        _epoch(r.signal_at), r.side, float(r.entry_price),
        float(r.stop_loss) if r.stop_loss is not None else None,
        float(r.take_profit) if r.take_profit is not None else None,
        f"{r.status}{': ' + r.rejection_reason if r.rejection_reason else ''}"[:70],
    ) for r in rows]
    trades = []
    if signals:
        first, last = min(s[0] for s in signals), max(s[0] for s in signals)
        trades = simulate(signals, _fetch_m1(first, last + MAX_HOLD_S + 3600))
    with _PAPER_LOCK:
        _PAPER_CACHE[key] = (_time.monotonic(), trades)
    return trades


def _live(us, year, month):
    lo, hi = _month_utc(year, month)
    out = []
    qs = Position.objects.filter(user_strategy=us, quantity=0).annotate(
        exit_at=Max("order__created_at"))
    for p in qs:
        entry = p.order_set.filter(condition="ENTRY").order_by("created_at").first()
        if entry is None:
            continue
        ts = _epoch(entry.created_at)
        if not lo <= ts < hi:
            continue
        buy = entry.side.upper() == "BUY"
        # avg_buy/avg_sell only carry the entry side; the exit fill is the
        # last non-ENTRY order's price.
        exit_order = p.order_set.exclude(condition="ENTRY").order_by("created_at").last()
        out.append(dict(
            entryTime=ts, exitTime=_epoch(p.exit_at or p.modified_at),
            side="BUY" if buy else "SELL",
            entryPrice=float(p.avg_buy_price if buy else p.avg_sell_price),
            exitPrice=float(exit_order.price) if exit_order else 0.0,
            stopLoss=None, takeProfit=None, outcome="CLOSED", note="",
            pnlUsd=round(float(p.realized_profit_loss or 0) * USD_PER_POINT_LOT, 2)))
    return sorted(out, key=lambda t: t["entryTime"])


def _backtest(us, year, month, label=None):
    run = (ManagerBacktestRun.objects.filter(label=label or backtest_label(us.id))
           .order_by("-created_at").first())
    if run is None:
        return dict(status="NONE", trades=[])
    lo, hi = _month_utc(year, month)
    trades = []
    for t in (run.result or {}).get("trades", []) if run.status == "DONE" else []:
        ts = int(datetime.fromisoformat(t["entry_time"]).timestamp())
        if not lo <= ts < hi:
            continue
        trades.append(dict(
            entryTime=ts, exitTime=int(datetime.fromisoformat(t["exit_time"]).timestamp()),
            side=t["side"], entryPrice=t["entry_px"], exitPrice=t["exit_px"],
            stopLoss=t["sl"], takeProfit=t["tp"], outcome=t["outcome"], note="",
            pnlUsd=round(t["pnl_usd"], 2)))
    return dict(status=run.status, progressPct=run.progress_pct, error=run.error,
                baseLot=(run.result or {}).get("lot") or (run.params or {}).get("lots")
                or PAPER_LOT,
                periodStart=run.period_start, periodEnd=run.period_end, trades=trades)


def owned_user_strategy(user, user_strategy_id):
    qs = UserStrategy.objects.filter(id=user_strategy_id)
    if not user.is_superuser:
        qs = qs.filter(user_broker__user=user)
    us = qs.first()
    if us is None:
        raise GraphQLError("strategy not found")
    return us


class StrategyTrades(graphene.ObjectType):
    strategyTrades = graphene.Field(
        StrategyTradesType, userStrategyId=graphene.UUID(required=True),
        kind=graphene.String(required=True), year=graphene.Int(required=True),
        month=graphene.Int(required=True))

    @user_authenticate
    def resolve_strategyTrades(self, info, userStrategyId, kind, year, month):
        if kind not in KINDS:
            raise GraphQLError(f"kind must be one of {KINDS}")
        if not 1 <= month <= 12 or not 2020 <= year <= 2100:
            raise GraphQLError("year/month out of range")
        us = owned_user_strategy(info.context.user, userStrategyId)
        if kind in ("backtest", "lab"):
            data = _backtest(us, year, month,
                             label=f"lab:{us.id}" if kind == "lab" else None)
        elif kind == "paper":
            data = dict(status="DONE", baseLot=PAPER_LOT, trades=_paper(us, year, month))
        else:
            data = dict(status="DONE", trades=_live(us, year, month))
        data["trades"] = [StrategyTradeType(**t) for t in data["trades"]]
        return StrategyTradesType(kind=kind, **data)
