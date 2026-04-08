import math
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)


def _haversine_km(lat1, lon1, lat2, lon2):
    """Calcula distância em km entre dois pontos geográficos (fórmula de Haversine)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# MemoryJobStore passado no construtor garante que nunca usa DjangoJobStore
scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
_scheduler_started = False


def start():
    global _scheduler_started

    if _scheduler_started:
        return

    # Posições em tempo real — a cada 15 segundos
    scheduler.add_job(
        _job_posicoes,
        trigger=IntervalTrigger(seconds=15),
        id='sync_posicoes',
        name='Sync Posições (15s)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=10,
    )

    # Veículos e alertas — a cada 2 minutos
    scheduler.add_job(
        _job_completo,
        trigger=IntervalTrigger(minutes=2),
        id='sync_completo',
        name='Sync Completo (2min)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=30,
    )

    # KM diário — a cada 5 minutos
    scheduler.add_job(
        _job_km_diario,
        trigger=IntervalTrigger(minutes=5),
        id='km_diario',
        name='Cálculo KM Diário (5min)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.start()
    _scheduler_started = True
    logger.info("Scheduler iniciado: posições a cada 30s, sync completo a cada 2min.")


def _job_posicoes():
    """Atualiza apenas lat/lng/velocidade/ignição de todos os veículos."""
    try:
        from core.sync import sync_positions
        sync_positions()
    except Exception:
        logger.exception("Erro no job de posições")


def _job_completo():
    """Sincroniza veículos, posições e alertas."""
    try:
        from core.sync import run_sync
        run_sync()
    except Exception:
        logger.exception("Erro no sync completo")


def _job_km_diario():
    """Calcula o KM percorrido hoje para cada veículo a partir do histórico de posições."""
    try:
        from django.utils import timezone
        from core.models import Vehicle, PositionHistory

        today = timezone.localdate()

        for vehicle in Vehicle.objects.filter(ativo=True):
            # Reseta acumulador se virou o dia
            if vehicle.km_dia_data != today:
                vehicle.km_percorrido_hoje = 0.0
                vehicle.km_dia_data = today
                vehicle.save(update_fields=['km_percorrido_hoje', 'km_dia_data'])

            # Busca todos os pontos de hoje em ordem cronológica
            pontos = list(
                PositionHistory.objects.filter(
                    vehicle=vehicle,
                    registrado_em__date=today,
                ).order_by('registrado_em').values('latitude', 'longitude')
            )

            if len(pontos) < 2:
                continue

            total_km = 0.0
            for i in range(1, len(pontos)):
                a, b = pontos[i - 1], pontos[i]
                dist = _haversine_km(a['latitude'], a['longitude'], b['latitude'], b['longitude'])
                # Ignora saltos absurdos (>2 km entre pontos de 15s = 480 km/h)
                if dist < 2.0:
                    total_km += dist

            km_arredondado = round(total_km, 1)
            if vehicle.km_percorrido_hoje != km_arredondado:
                vehicle.km_percorrido_hoje = km_arredondado
                vehicle.save(update_fields=['km_percorrido_hoje'])

    except Exception:
        logger.exception("Erro no cálculo de KM diário")
