# Hand-written (makemigrations would also pick up the unrelated, pre-existing
# drift documented in 0008/0009's headers). Adds ONLY UserStrategy.lot_size: the
# fixed total lot per signal that the Telegram copy-traders use for an account
# (the "Price" column on the Neymar / Neymar VIP tabs). Nullable, so every
# existing row keeps the bot's risk-based sizing until a Price is set.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apis', '0009_manager_backtest_run'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstrategy',
            name='lot_size',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
