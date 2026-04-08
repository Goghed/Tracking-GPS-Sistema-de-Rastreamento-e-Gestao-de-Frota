"""
Management command para sincronização de posições e dados da frota.
Uso: python manage.py sync_posicoes

Configure no PythonAnywhere Scheduled Tasks para rodar a cada minuto:
  /home/<usuario>/.virtualenvs/<venv>/bin/python /home/<usuario>/<projeto>/manage.py sync_posicoes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Sincroniza posições, veículos e alertas com a API Fulltrack'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas-posicoes',
            action='store_true',
            help='Sincroniza apenas posições (mais rápido, sem veículos/alertas)',
        )

    def handle(self, *args, **options):
        inicio = timezone.now()

        if options['apenas_posicoes']:
            try:
                from core.sync import sync_positions
                count = sync_positions()
                self.stdout.write(
                    self.style.SUCCESS(f'[{inicio:%H:%M:%S}] Posições: {count} veículos atualizados')
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Erro ao sincronizar posições: {e}'))
        else:
            try:
                from core.sync import run_sync
                run_sync()
                self.stdout.write(
                    self.style.SUCCESS(f'[{inicio:%H:%M:%S}] Sync completo executado com sucesso')
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Erro no sync completo: {e}'))
