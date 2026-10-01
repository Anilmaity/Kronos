import graphene

from apis.copy_trade import SOURCE_STRATEGY_IDS, apply_drawdown, parse_risk
from apis.models import UserStrategy
from apis.schema.utils import user_authenticate

_COPY_TRADE_STRATEGY_IDS = {sid for ids in SOURCE_STRATEGY_IDS.values() for sid in ids}


class UpdateCopyTradeRisk(graphene.Mutation):
    """Set a copy-trade row's Trade SL and its account's Daily / Max drawdown.

    Every field is sent each time: an empty (null) field clears that setting.
    Trade SL applies from the next signal; drawdown floors apply within seconds.
    """

    Response = graphene.String()
    Ok = graphene.Boolean()

    class Arguments:
        user_strategy_id = graphene.String(required=True)
        trade_sl_usd = graphene.Float()
        max_sl_per_trade_usd = graphene.Float()
        daily_dd_floor = graphene.Float()
        max_dd_floor = graphene.Float()
        daily_dd_offset = graphene.Float()
        max_dd_offset = graphene.Float()

    @user_authenticate
    def mutate(self, info, user_strategy_id, **risk_args):
        qs = UserStrategy.objects.select_related("user_broker").filter(id=user_strategy_id)
        if not info.context.user.is_superuser:
            qs = qs.filter(user_broker__user=info.context.user)
        us = qs.first()
        if us is None:
            return UpdateCopyTradeRisk(Response="Strategy does not exist", Ok=False)
        if str(us.strategy_id) not in _COPY_TRADE_STRATEGY_IDS:
            return UpdateCopyTradeRisk(
                Response="Stop loss can only be set on Neymar / Neymar VIP rows", Ok=False)

        broker = us.user_broker
        risk, err = parse_risk(**risk_args, last_equity=broker.dd_equity)
        if err:
            return UpdateCopyTradeRisk(Response=err, Ok=False)

        us.trade_sl_usd = risk["trade_sl_usd"]
        us.max_sl_per_trade_usd = risk["max_sl_per_trade_usd"]
        us.save(update_fields=["trade_sl_usd", "max_sl_per_trade_usd", "modified_at"])
        fields = apply_drawdown(broker, risk)
        if fields:
            broker.save(update_fields=fields + ["modified_at"])
        return UpdateCopyTradeRisk(Response="Success", Ok=True)
