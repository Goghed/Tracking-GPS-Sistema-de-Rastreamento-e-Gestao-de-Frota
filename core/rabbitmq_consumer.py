"""
Tracking GPS — Consumer RabbitMQ (Guarnieri / Itu)
Fica em thread separada escutando a fila continuamente.
Formato esperado do JSON:
{
  "placa": "AAA1111",
  "data_recebida": "2026-04-06 06:52:19",
  "data_hora_gps": "2026-03-28 06:08:50",
  "latitude": "-5.641345",
  "longitude": "-44.362970",
  "velocidade": 83,
  "horimetro": 637042,
  "odometro": 441343353,
  "status_local": 1,
  "status_bateria": 0,
  "status_ignicao": 1,
  "tensao": 12,
  "satelite": 10,
  "condutor": "WALDREANO FRAZAO VALADARES",
  "nome_fila": "guarnieri"
}
"""
import json
import logging
import threading
import time

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

_consumer_thread = None
_stop_event      = threading.Event()


def _processar_mensagem(ch, method, properties, body):
    """Callback chamado para cada mensagem recebida na fila."""
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.error("RabbitMQ: mensagem inválida (não é JSON): %s", body[:200])
        ch.basic_ack(method.delivery_tag)
        return

    placa = str(data.get('placa', '')).strip().upper()
    if not placa:
        logger.warning("RabbitMQ: mensagem sem placa, ignorada.")
        ch.basic_ack(method.delivery_tag)
        return

    try:
        _salvar_posicao(placa, data)
    except Exception as e:
        logger.exception("RabbitMQ: erro ao salvar posição de %s: %s", placa, e)

    ch.basic_ack(method.delivery_tag)


def _salvar_posicao(placa, data):
    from django.utils import timezone
    from datetime import datetime
    from core.models import Vehicle

    def parse_dt(val):
        if not val:
            return None
        import datetime as _dt
        for fmt in ('%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
            try:
                dt = datetime.strptime(str(val).strip(), fmt)
                return timezone.make_aware(dt, _dt.timezone.utc)  # API envia UTC
            except ValueError:
                continue
        return None

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    lat = safe_float(data.get('latitude'))
    lng = safe_float(data.get('longitude'))
    vel = safe_float(data.get('velocidade'))
    ign = bool(int(data.get('status_ignicao', 0))) if data.get('status_ignicao') is not None else None
    ultima = parse_dt(data.get('data_hora_gps') or data.get('data_recebida'))

    # Odômetro: string bruta da fila (ex: 441343353)
    odo_raw = data.get('odometro')
    odometro_str = str(int(odo_raw)) if odo_raw is not None else None

    # Tenta encontrar o veículo pela placa
    veiculo = Vehicle.objects.filter(placa__iexact=placa).first()

    if veiculo:
        # Atualiza posição e dados do veículo existente
        update_fields = dict(
            latitude=lat,
            longitude=lng,
            velocidade_atual=vel,
            ignicao=ign,
            ultima_posicao=ultima or timezone.now(),
        )
        if odometro_str is not None:
            update_fields['odometro'] = odometro_str
        Vehicle.objects.filter(pk=veiculo.pk).update(**update_fields)
        logger.debug("RabbitMQ: posição atualizada — %s | %.4f, %.4f | %s km/h | odo=%s",
                     placa, lat or 0, lng or 0, vel or 0, odometro_str or '—')
    else:
        # Cria veículo novo com os dados recebidos
        Vehicle.objects.create(
            api_id=f"rmq_{placa}",
            placa=placa,
            descricao=data.get('condutor') or placa,
            latitude=lat,
            longitude=lng,
            velocidade_atual=vel,
            ignicao=ign,
            ultima_posicao=ultima or timezone.now(),
            odometro=odometro_str or '',
            ativo=True,
        )
        logger.info("RabbitMQ: novo veículo criado — %s", placa)


def _loop_consumer():
    """Loop principal do consumer — reconecta automaticamente em caso de falha."""
    logger.info("RabbitMQ consumer: iniciando thread...")

    while not _stop_event.is_set():
        try:
            creds  = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
            params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=creds,
                heartbeat=60,
                blocked_connection_timeout=30,
                socket_timeout=15,
                connection_attempts=3,
                retry_delay=5,
            )
            conn    = pika.BlockingConnection(params)
            channel = conn.channel()
            channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True, passive=True)
            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(
                queue=settings.RABBITMQ_QUEUE,
                on_message_callback=_processar_mensagem,
            )
            logger.info("RabbitMQ consumer: conectado. Aguardando mensagens em '%s'...", settings.RABBITMQ_QUEUE)

            # Fica consumindo até o stop_event ser acionado ou conexão cair
            while not _stop_event.is_set():
                conn.process_data_events(time_limit=1)

            conn.close()

        except pika.exceptions.AMQPConnectionError as e:
            logger.warning("RabbitMQ: falha de conexão (%s). Reconectando em 15s...", e)
            _stop_event.wait(15)
        except Exception as e:
            logger.exception("RabbitMQ: erro inesperado. Reconectando em 15s...")
            _stop_event.wait(15)

    logger.info("RabbitMQ consumer: thread encerrada.")


def start_consumer():
    """Inicia o consumer em thread daemon. Chamado pelo apps.py na inicialização."""
    global _consumer_thread

    if _consumer_thread and _consumer_thread.is_alive():
        return  # já está rodando

    _stop_event.clear()
    _consumer_thread = threading.Thread(
        target=_loop_consumer,
        name="rabbitmq-consumer",
        daemon=True,
    )
    _consumer_thread.start()
    logger.info("RabbitMQ consumer: thread iniciada.")


def stop_consumer():
    """Para o consumer (usado em testes ou shutdown)."""
    _stop_event.set()
