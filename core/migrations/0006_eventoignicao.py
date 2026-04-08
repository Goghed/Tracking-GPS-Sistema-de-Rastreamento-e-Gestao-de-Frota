from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_vehicle_km_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoIgnicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('autorizado', 'Autorizado'), ('nao_autorizado', 'Não Autorizado')], max_length=20)),
                ('dia_semana', models.CharField(max_length=20)),
                ('mensagem', models.TextField()),
                ('lido', models.BooleanField(default=False)),
                ('ocorrido_em', models.DateTimeField(auto_now_add=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eventos_ignicao', to='core.vehicle')),
            ],
            options={
                'verbose_name': 'Evento de Ignição',
                'verbose_name_plural': 'Eventos de Ignição',
                'ordering': ['-ocorrido_em'],
            },
        ),
    ]
