"""
Tracking GPS — Serviço de Sincronização com a Fulltrack API
Auth: headers apiKey + secretKey em cada requisição (sem token/sessão).
  - vehicles/all  → cadastro e dados dos veículos
  - events/all    → última posição de cada veículo (lat, lng, ignição, velocidade)
  - alerts/all    → alertas abertos
Roda a cada 1 minuto via APScheduler.
"""
import logging
import threading
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

_sync_lock = threading.Lock()

logger = logging.getLogger(__name__)

BASE_URL = settings.FULLTRACK_API_URL.rstrip('/')
HEADERS  = {
    'apiKey':    settings.FULLTRACK_API_KEY,
    'secretKey': settings.FULLTRACK_SECRET_KEY,
}
TIMEOUT = 15


def _get(endpoint: str, params: dict = None) -> dict | None:
    """GET autenticado com apiKey/secretKey como headers."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get('status'):
            return data
        logger.warning("Fulltrack: status=false para %s: %s", endpoint, data.get('message'))
        return None
    except requests.RequestException as e:
        logger.error("Erro ao chamar %s: %s", endpoint, e)
        return None


def _parse_dt(value: str | None) -> datetime | None:
    """Parseia datas da API Fulltrack.
    A API envia horários em UTC — fazemos aware em UTC e deixamos
    o Django converter para São Paulo ao exibir."""
    if not value:
        return None
    import datetime as _dt
    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return timezone.make_aware(dt, _dt.timezone.utc)
        except ValueError:
            continue
    return None


# ─── sync de veículos ─────────────────────────────────────────

def sync_vehicles() -> int:
    from core.models import Vehicle

    data = _get('vehicles/all')
    if not data:
        return 0

    count = 0
    for item in data.get('data', []):
        api_id = str(item.get('ras_vei_id', ''))
        if not api_id:
            continue

        defaults = {
            'api_client_id':     str(item.get('ras_vei_id_cli', '') or ''),
            'placa':             str(item.get('ras_vei_placa', '') or ''),
            'tag':               str(item.get('ras_vei_tag_identificacao', '') or ''),
            'descricao':         str(item.get('ras_vei_veiculo', '') or ''),
            'chassi':            str(item.get('ras_vei_chassi', '') or ''),
            'ano':               str(item.get('ras_vei_ano', '') or ''),
            'cor':               str(item.get('ras_vei_cor', '') or ''),
            'tipo':              str(item.get('ras_vei_tipo', '') or ''),
            'fabricante':        str(item.get('ras_vei_fabricante', '') or ''),
            'modelo':            str(item.get('ras_vei_modelo', '') or ''),
            'combustivel':       str(item.get('ras_vei_combustivel', '') or ''),
            'consumo':           str(item.get('ras_vei_consumo', '') or ''),
            'velocidade_limite': str(item.get('ras_vei_velocidade_limite', '') or ''),
            'odometro':          str(item.get('ras_vei_odometro', '') or ''),
            'equipamento':       item.get('ras_vei_equipamento') or None,
        }
        Vehicle.objects.update_or_create(api_id=api_id, defaults=defaults)
        count += 1

    logger.info("sync_vehicles: %d veículos sincronizados", count)
    return count


# ─── sync de posições ─────────────────────────────────────────
# events/all retorna a ÚLTIMA POSIÇÃO de cada veículo

def sync_positions() -> int:
    # Se run_sync já está em andamento (tem o lock), espera até 5s ou desiste
    if not _sync_lock.acquire(blocking=True, timeout=5):
        logger.info("sync_positions: lock ocupado, ignorando chamada isolada")
        return 0
    try:
        return _sync_positions_inner()
    finally:
        _sync_lock.release()


def _sync_positions_inner() -> int:
    from core.models import Vehicle, PositionHistory

    data = _get('events/all')
    if not data:
        return 0

    count = 0
    history_bulk = []

    for item in data.get('data', []):
        vei_id = str(item.get('ras_vei_id', ''))
        if not vei_id:
            continue

        try:
            lat_raw = item.get('ras_eve_latitude')
            lng_raw = item.get('ras_eve_longitude')
            vel_raw = item.get('ras_eve_velocidade')
            ign_raw = item.get('ras_eve_ignicao')

            lat = float(lat_raw) if lat_raw not in (None, '', '0') else None
            lng = float(lng_raw) if lng_raw not in (None, '', '0') else None
            vel = float(vel_raw) if vel_raw not in (None, '') else None
            ignicao = bool(int(ign_raw)) if ign_raw not in (None, '') else None
        except (ValueError, TypeError):
            continue

        if lat is None or lng is None:
            continue

        ultima = _parse_dt(
            item.get('ras_eve_data_gps') or item.get('ras_ras_data_ult_comunicacao')
        )

        try:
            dir_raw = item.get('ras_eve_direcao')
            direcao = float(dir_raw) if dir_raw not in (None, '') else None
        except (ValueError, TypeError):
            direcao = None

        try:
            vehicle = Vehicle.objects.get(api_id=vei_id)
        except Vehicle.DoesNotExist:
            continue

        # Grava histórico apenas se a posição mudou
        pos_mudou = (vehicle.latitude != lat or vehicle.longitude != lng)

        Vehicle.objects.filter(pk=vehicle.pk).update(
            latitude=lat,
            longitude=lng,
            velocidade_atual=vel,
            ignicao=ignicao,
            direcao=direcao,
            ultima_posicao=ultima,
        )

        if pos_mudou:
            history_bulk.append(PositionHistory(
                vehicle=vehicle,
                latitude=lat,
                longitude=lng,
                velocidade=vel,
                ignicao=ignicao,
                direcao=direcao,
            ))

        count += 1

    if history_bulk:
        PositionHistory.objects.bulk_create(history_bulk)

    # Limpa histórico com mais de 24h para não encher o banco
    from django.utils import timezone
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24)
    deleted, _ = PositionHistory.objects.filter(registrado_em__lt=cutoff).delete()
    if deleted:
        logger.info("sync_positions: %d pontos de histórico antigos removidos", deleted)

    logger.info("sync_positions: %d veículos atualizados, %d novos pontos de histórico",
                count, len(history_bulk))
    return count


# ─── sync de alertas ──────────────────────────────────────────

def sync_alerts() -> int:
    from core.models import Vehicle, Alert

    data = _get('alerts/all')
    if not data:
        return 0

    count = 0
    for item in data.get('data', []):
        vei_id   = str(item.get('ras_eal_id_veiculo', ''))
        alert_id = str(item.get('_id', '') or item.get('ras_eal_id_evento', ''))

        if not vei_id:
            continue

        try:
            vehicle = Vehicle.objects.get(api_id=vei_id)
        except Vehicle.DoesNotExist:
            continue

        if alert_id and Alert.objects.filter(api_alert_id=alert_id).exists():
            continue

        descricao = str(item.get('ras_eal_descricao', '') or '')
        extra     = str(item.get('ras_eal_descricao_extra', '') or '')
        tipo      = f"{descricao} - {extra}".strip(' -') if extra else descricao

        sev = 'info'
        tipo_lower = tipo.lower()
        if any(w in tipo_lower for w in ['excesso', 'velocidade', 'panico', 'jammer', 'bloqueio']):
            sev = 'danger'
        elif any(w in tipo_lower for w in ['cerca', 'zona', 'rota', 'entrou', 'saiu']):
            sev = 'warning'

        try:
            lat = float(item.get('ras_eal_latitude') or 0) or None
            lng = float(item.get('ras_eal_longitude') or 0) or None
        except (ValueError, TypeError):
            lat = lng = None

        Alert.objects.create(
            vehicle      = vehicle,
            api_alert_id = alert_id,
            tipo         = tipo,
            descricao    = descricao,
            severidade   = sev,
            latitude     = lat,
            longitude    = lng,
            ocorrido_em  = _parse_dt(item.get('ras_eal_data_alerta')) or timezone.now(),
        )
        count += 1

    logger.info("sync_alerts: %d novos alertas", count)
    return count


# ─── job principal ────────────────────────────────────────────

def run_sync():
    """Job executado a cada 1 minuto pelo APScheduler."""
    # Se já há um sync em andamento, descarta esta chamada para evitar
    # "database is locked" por escritas simultâneas no SQLite
    if not _sync_lock.acquire(blocking=False):
        logger.info("run_sync: já em andamento, ignorando chamada concorrente")
        return

    from core.models import SyncLog
    log = SyncLog.objects.create()
    try:
        v = sync_vehicles()
        _sync_positions_inner()  # run_sync já tem o lock, chama interno diretamente
        a = sync_alerts()

        log.veiculos_sync = v
        log.alertas_sync  = a
        log.status        = 'success'
    except Exception as exc:
        logger.exception("Erro crítico no run_sync")
        log.status   = 'error'
        log.erro_msg = str(exc)
    finally:
        log.finalizado_em = timezone.now()
        log.save()
        _sync_lock.release()
