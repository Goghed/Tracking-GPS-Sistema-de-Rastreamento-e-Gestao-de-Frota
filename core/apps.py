from django.apps import AppConfig


def _configurar_sqlite_wal(sender, connection, **kwargs):
    """
    Ativa WAL mode e busy_timeout no SQLite assim que a conexão é criada.
    WAL (Write-Ahead Logging) permite leituras e escritas simultâneas sem
    bloquear umas às outras, resolvendo o 'database is locked' com múltiplas threads.
    """
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')
            cursor.execute('PRAGMA busy_timeout=20000;')  # 20s em ms


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Tracking GPS'

    def ready(self):
        # Ativa WAL mode em todas as conexões SQLite (resolve database is locked)
        from django.db.backends.signals import connection_created
        connection_created.connect(_configurar_sqlite_wal)

        import sys

        # Comandos de gerenciamento que NÃO devem iniciar o scheduler
        _management_cmds = {
            'migrate', 'makemigrations', 'collectstatic', 'shell',
            'test', 'createsuperuser', 'check', 'showmigrations',
            'sqlmigrate', 'dbshell', 'flush', 'loaddata', 'dumpdata',
        }
        _cmd = sys.argv[1] if len(sys.argv) > 1 else ''
        _deve_iniciar = _cmd not in _management_cmds

        if _deve_iniciar:
            from core.scheduler import start
            start()

            from core.rabbitmq_consumer import start_consumer
            start_consumer()
