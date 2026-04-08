from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_eventoignicao'),
    ]

    operations = [
        migrations.CreateModel(
            name='Manutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('preventiva','Preventiva'),('corretiva','Corretiva'),('revisao','Revisão'),('pneu','Pneu / Borracharia'),('funilaria','Funilaria / Pintura'),('eletrica','Elétrica'),('outros','Outros')], default='preventiva', max_length=20)),
                ('descricao', models.CharField(max_length=200)),
                ('data_manutencao', models.DateField()),
                ('custo', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('km_na_manutencao', models.IntegerField(blank=True, null=True)),
                ('fornecedor', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('agendada','Agendada'),('em_andamento','Em andamento'),('concluida','Concluída')], default='concluida', max_length=15)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manutencoes', to='core.vehicle')),
            ],
            options={'verbose_name': 'Manutenção', 'verbose_name_plural': 'Manutenções', 'ordering': ['-data_manutencao']},
        ),
        migrations.CreateModel(
            name='ManutencaoArquivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to='manutencoes/')),
                ('nome_original', models.CharField(blank=True, max_length=255)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('manutencao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos', to='core.manutencao')),
            ],
            options={'verbose_name': 'Arquivo de Manutenção', 'ordering': ['criado_em']},
        ),
        migrations.CreateModel(
            name='Ocorrencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('acidente','Acidente'),('multa','Multa'),('furto','Furto / Roubo'),('vandalismo','Vandalismo'),('avaria','Avaria'),('outros','Outros')], default='acidente', max_length=20)),
                ('descricao', models.TextField()),
                ('data_ocorrencia', models.DateField()),
                ('local', models.CharField(blank=True, max_length=200)),
                ('gravidade', models.CharField(choices=[('leve','Leve'),('moderada','Moderada'),('grave','Grave')], default='leve', max_length=10)),
                ('status', models.CharField(choices=[('aberta','Aberta'),('em_analise','Em análise'),('resolvida','Resolvida')], default='aberta', max_length=15)),
                ('custo_estimado', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('observacoes', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ocorrencias', to='core.vehicle')),
            ],
            options={'verbose_name': 'Ocorrência', 'verbose_name_plural': 'Ocorrências', 'ordering': ['-data_ocorrencia']},
        ),
        migrations.CreateModel(
            name='OcorrenciaArquivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to='ocorrencias/')),
                ('nome_original', models.CharField(blank=True, max_length=255)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('ocorrencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos', to='core.ocorrencia')),
            ],
            options={'verbose_name': 'Arquivo de Ocorrência', 'ordering': ['criado_em']},
        ),
    ]
