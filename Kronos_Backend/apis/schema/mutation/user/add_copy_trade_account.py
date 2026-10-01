import graphene

from apis.copy_trade import SOURCE_STRATEGY_IDS, parse_lot
from apis.models import UserStrategy, Strategy, UserBroker
from apis.schema.utils import user_authenticate
from apis.schema.types.user_strategy_type import UserStrategyType


class AddCopyTradeAccount(graphene.Mutation):
    """Add a broker account to a Telegram copy-trade tab (Neymar / Neymar VIP).

    Creates a UserStrategy on the source's Strategy with a fixed total lot per
    signal. The copy-trader picks the account up on its next refresh (~1 min)
    and trades every new signal on it at that lot, split across the TP legs.
    """

    UserStrategy = graphene.Field(UserStrategyType)
    Response = graphene.String()
    Ok = graphene.Boolean()

    class Arguments:
        source = graphene.String(required=True)
        user_broker_id = graphene.String(required=True)
        lot_size = graphene.Float(required=True)

    @user_authenticate
    def mutate(self, info, source, user_broker_id, lot_size):
        def fail(msg):
            return AddCopyTradeAccount(UserStrategy=None, Response=msg, Ok=False)

        strategy_ids = SOURCE_STRATEGY_IDS.get(source)
        if not strategy_ids:
            return fail("Unknown copy-trade source")

        lot, err = parse_lot(lot_size)
        if err:
            return fail(err)

        brokers = UserBroker.objects.all()
        if not info.context.user.is_superuser:
            brokers = brokers.filter(user=info.context.user)
        userbroker = brokers.filter(id=user_broker_id).first()
        if userbroker is None:
            return fail("Account does not exist")
        if not userbroker.is_active:
            return fail("Account is not active")
        # The copy-trader places orders with the account's own MetaAPI creds.
        if not (userbroker.meta_account_id or "").strip() or not userbroker.meta_api_token_enc:
            return fail("Account has no MetaAPI account id / token — add them in Accounts first")

        if UserStrategy.objects.filter(
            user_broker=userbroker, strategy_id__in=strategy_ids
        ).exists():
            return fail("Account is already in this tab")

        try:
            strategy = Strategy.objects.get(id=strategy_ids[0])
        except Strategy.DoesNotExist:
            return fail("Copy-trade strategy is not provisioned")

        userstrategy = UserStrategy.objects.create(
            user_broker=userbroker,
            strategy=strategy,
            name=strategy.name,
            multiplyer=1,
            lot_size=lot,
            is_active=True,
            deployed=True,
        )
        return AddCopyTradeAccount(UserStrategy=userstrategy, Response="Success", Ok=True)
