# Hand-written (see 0010). Position.realized_profit_loss is stored in USD / 100
# (points x lots), so 2 decimal places rounded every closed trade to the nearest
# whole dollar — a +$5.20 Winprofx TP showed as +$5.00. 4dp keeps cents.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apis', '0011_copy_trade_risk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='realized_profit_loss',
            field=models.DecimalField(decimal_places=4, default=0.0, max_digits=25),
        ),
    ]
