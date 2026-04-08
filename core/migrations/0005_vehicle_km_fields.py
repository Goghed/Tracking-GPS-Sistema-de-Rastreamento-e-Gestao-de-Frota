from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_positionhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='km_base',
            field=models.FloatField(blank=True, null=True, verbose_name='KM Base (odômetro manual)'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='km_percorrido_hoje',
            field=models.FloatField(default=0.0, verbose_name='KM percorrido hoje'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='km_dia_data',
            field=models.DateField(blank=True, null=True, verbose_name='Data referência km diário'),
        ),
    ]
