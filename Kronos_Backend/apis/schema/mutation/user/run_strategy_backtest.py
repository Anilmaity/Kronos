from datetime import date, timedelta

import graphene

from apis.models import ManagerBacktestRun
from apis.schema.mutation.user.run_manager_backtest import (
    DEFAULT_REGIME_CADENCE_MIN, DEFAULT_SLIPPAGE_PTS, DEFAULT_SPREAD_PTS, MAX_QUEUED)
from apis.schema.query.strategy_trades import backtest_label, owned_user_strategy
from apis.schema.utils import user_authenticate

WINDOW_DAYS = 62      # the calendar shows the last two months
LOTS = 0.01


class RunStrategyBacktest(graphene.Mutation):
    """Queue a single-strategy replay for the /strategy-data Backtest tab.
    Rides the Manager Backtest queue: a one-strategy always_on roster with the
    book-level limits switched off, and emit_trades so the worker stores the
    trade list on the row."""

    ok = graphene.Boolean()
    run_id = graphene.UUID()
    error = graphene.String()

    class Arguments:
        user_strategy_id = graphene.UUID(required=True)

    @user_authenticate
    def mutate(self, info, user_strategy_id):
        us = owned_user_strategy(info.context.user, user_strategy_id)
        queued = ManagerBacktestRun.objects.filter(
            status__in=["PENDING", "RUNNING"]).count()
        if queued >= MAX_QUEUED:
            return RunStrategyBacktest(
                ok=False, error=f"queue full: {queued} runs already pending/running")
        end = date.today()
        run = ManagerBacktestRun.objects.create(
            label=backtest_label(us.id),
            period_start=end - timedelta(days=WINDOW_DAYS), period_end=end,
            params={
                "spread_pts": DEFAULT_SPREAD_PTS, "slippage_pts": DEFAULT_SLIPPAGE_PTS,
                "lots": LOTS, "kill_switch_usd": 1e9, "max_concurrent": 10,
                "regime_cadence_min": DEFAULT_REGIME_CADENCE_MIN,
                "include_ungated": False, "emit_trades": True,
                "roster_snapshot": [{"name": us.strategy.name,
                                     "policy_key": "always_on", "policy_params": {}}],
            },
            requested_by=info.context.user)
        return RunStrategyBacktest(ok=True, run_id=run.id, error=None)
