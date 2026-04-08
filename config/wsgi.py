import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Inicia o scheduler de sincronização após o app Django estar pronto.
# Isso garante funcionamento em qualquer servidor WSGI (uWSGI, gunicorn, etc.)
try:
    from core.scheduler import start
    start()
except Exception:
    import logging
    logging.getLogger(__name__).exception("Erro ao iniciar scheduler via wsgi.py")

try:
    from core.rabbitmq_consumer import start_consumer
    start_consumer()
except Exception:
    import logging
    logging.getLogger(__name__).exception("Erro ao iniciar RabbitMQ consumer via wsgi.py")
