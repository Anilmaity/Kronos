import graphene

from apis.copy_trade import SOURCE_STRATEGY_IDS, parse_lot
from apis.models import UserStrategy
from apis.schema.utils import user_authenticate

_COPY_TRADE_STRATEGY_IDS = {sid for ids in SOURCE_STRATEGY_IDS.values() for sid in ids}


class SetCopyTradeLot(graphene.Mutation):
    """Set the fixed total lot ("Price") a copy-trade account trades per signal.
    Applies from the next signal (the copy-trader re-reads it at signal time)."""

    Response = graphene.String()
    Ok = graphene.Boolean()

    class Arguments:
        user_strategy_id = graphene.String(required=True)
        lot_size = graphene.Float(required=True)

    @user_authenticate
    def mutate(self, info, user_strategy_id, lot_size):
        lot, err = parse_lot(lot_size)
        if err:
            return SetCopyTradeLot(Response=err, Ok=False)

        qs = UserStrategy.objects.filter(id=user_strategy_id)
        if not info.context.user.is_superuser:
            qs = qs.filter(user_broker__user=info.context.user)
        us = qs.first()
        if us is None:
            return SetCopyTradeLot(Response="Strategy does not exist", Ok=False)
        if str(us.strategy_id) not in _COPY_TRADE_STRATEGY_IDS:
            return SetCopyTradeLot(Response="Price can only be set on Neymar / Neymar VIP rows", Ok=False)

        us.lot_size = lot
        us.save(update_fields=["lot_size", "modified_at"])
        return SetCopyTradeLot(Response="Success", Ok=True)
