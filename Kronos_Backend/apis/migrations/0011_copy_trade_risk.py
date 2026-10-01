# Hand-written (see 0010). Copy-trade risk settings for the Neymar tabs:
#   UserStrategy.trade_sl_usd / max_sl_per_trade_usd — per-signal USD stop budget
#   UserBroker.*dd* — daily / max drawdown equity floors + guard state
# All nullable: nothing changes for existing rows until a value is set.

from django.db import migrations, models


def _money(digits=14):
    return models.DecimalField(blank=True, decimal_places=2, max_digits=digits, null=True)


class Migration(migrations.Migration):

    dependencies = [
        ('apis', '0010_userstrategy_lot_size'),
    ]

    operations = [
        migrations.AddField(model_name='userstrategy', name='trade_sl_usd', field=_money(10)),
        migrations.AddField(model_name='userstrategy', name='max_sl_per_trade_usd', field=_money(10)),
        migrations.AddField(model_name='userbroker', name='daily_dd_floor', field=_money()),
        migrations.AddField(model_name='userbroker', name='max_dd_floor', field=_money()),
        migrations.AddField(model_name='userbroker', name='daily_dd_offset', field=_money()),
        migrations.AddField(model_name='userbroker', name='max_dd_offset', field=_money()),
        migrations.AddField(model_name='userbroker', name='dd_day',
                            field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='userbroker', name='dd_blocked_day',
                            field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='userbroker', name='dd_status',
                            field=models.CharField(blank=True, default='', max_length=60)),
        migrations.AddField(model_name='userbroker', name='dd_equity', field=_money()),
        migrations.AddField(model_name='userbroker', name='dd_equity_at',
                            field=models.DateTimeField(blank=True, null=True)),
    ]
