import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_GET, require_POST

from core.models import Vehicle, Alert, Event, SyncLog, PositionHistory, EventoIgnicao, Manutencao, ManutencaoArquivo, Ocorrencia, OcorrenciaArquivo


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    now = timezone.now()
    ultimo_dia = now - timedelta(hours=24)

    total_veiculos  = Vehicle.objects.filter(ativo=True).count()
    ligados         = Vehicle.objects.filter(ativo=True, ignicao=True, latitude__isnull=False, longitude__isnull=False).count()
    desligados      = Vehicle.objects.filter(ativo=True, ignicao=False).count()
    sem_sinal       = total_veiculos - ligados - desligados

    # Último sync
    ultimo_sync = SyncLog.objects.order_by('-iniciado_em').first()

    # Alertas recentes
    alertas_recentes = Alert.objects.select_related('vehicle').order_by('-ocorrido_em')[:10]

    # Veículos para os cards
    veiculos_cards = Vehicle.objects.filter(ativo=True).order_by('-ignicao', 'placa')

    # Eventos de ignição recentes (últimas 24h)
    eventos_ignicao = EventoIgnicao.objects.select_related('vehicle').filter(
        ocorrido_em__gte=ultimo_dia
    ).order_by('-ocorrido_em')[:20]

    nao_autorizados_hoje = EventoIgnicao.objects.filter(
        ocorrido_em__gte=ultimo_dia, tipo='nao_autorizado'
    ).count()

    context = {
        'total_veiculos':    total_veiculos,
        'ligados':           ligados,
        'desligados':        desligados,
        'sem_sinal':         sem_sinal,
        'ultimo_sync':       ultimo_sync,
        'alertas_recentes':      alertas_recentes,
        'veiculos_cards':        veiculos_cards,
        'eventos_ignicao':       eventos_ignicao,
        'nao_autorizados_hoje':  nao_autorizados_hoje,
    }
    return render(request, 'core/dashboard.html', context)


# ─── Mapa ─────────────────────────────────────────────────────────────────────

@login_required
def mapa(request):
    veiculos = Vehicle.objects.filter(ativo=True).exclude(latitude=None)
    return render(request, 'core/mapa.html', {'veiculos': veiculos})


@login_required
@require_GET
def api_veiculos_posicao(request):
    """Endpoint JSON para atualização do mapa em tempo real.
    Busca posições frescas da API Fulltrack se os dados tiverem > 15s."""
    from datetime import timedelta

    # Verifica se a posição mais recente no banco tem mais de 15 segundos
    ultima = Vehicle.objects.filter(ativo=True, ultima_posicao__isnull=False) \
                            .order_by('-ultima_posicao') \
                            .values_list('ultima_posicao', flat=True).first()

    dados_velhos = (
        ultima is None or
        (timezone.now() - ultima).total_seconds() > 15
    )

    if dados_velhos:
        try:
            from core.sync import sync_positions
            sync_positions()
        except Exception:
            pass

    # Verifica se está dentro do horário autorizado (Seg-Sex 08:00-18:00 SP)
    from datetime import datetime as _dt, time as _time
    now_sp    = timezone.localtime()
    weekday   = now_sp.weekday()   # 0=Seg … 4=Sex, 5=Sáb, 6=Dom
    hora      = now_sp.hour
    autorizado_horario = (0 <= weekday <= 4) and (8 <= hora < 18)

    # Primeira posição registrada hoje para cada veículo (para mostrar trajeto não autorizado)
    today_start = timezone.make_aware(
        _dt.combine(now_sp.date(), _time.min)
    )
    from django.db.models import Min
    primeiros_ts = dict(
        PositionHistory.objects.filter(registrado_em__gte=today_start)
        .values('vehicle_id').annotate(ts=Min('registrado_em'))
        .values_list('vehicle_id', 'ts')
    )
    pos_iniciais = {}
    if primeiros_ts:
        for ph in PositionHistory.objects.filter(
            vehicle_id__in=primeiros_ts.keys(),
            registrado_em__in=primeiros_ts.values()
        ).values('vehicle_id', 'latitude', 'longitude'):
            pos_iniciais[ph['vehicle_id']] = (ph['latitude'], ph['longitude'])

    veiculos = Vehicle.objects.filter(ativo=True).values(
        'id', 'placa', 'descricao', 'latitude', 'longitude',
        'velocidade_atual', 'ignicao', 'direcao', 'ultima_posicao',
        'km_base', 'km_percorrido_hoje',
    )
    data = []
    for v in veiculos:
        pi = pos_iniciais.get(v['id'])
        data.append({
            **v,
            'ultima_posicao':    v['ultima_posicao'].isoformat() if v['ultima_posicao'] else None,
            'autorizado_horario': autorizado_horario,
            'pos_inicial_lat':   pi[0] if pi else None,
            'pos_inicial_lng':   pi[1] if pi else None,
        })
    return JsonResponse({'veiculos': data})


# ─── Veículos ─────────────────────────────────────────────────────────────────

@login_required
def veiculos_lista(request):
    qs = Vehicle.objects.filter(ativo=True)

    busca = request.GET.get('q', '').strip()
    if busca:
        qs = qs.filter(
            Q(placa__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(modelo__icontains=busca)
        )

    status = request.GET.get('status', '')
    if status == 'ligado':
        qs = qs.filter(ignicao=True)
    elif status == 'desligado':
        qs = qs.filter(ignicao=False)
    elif status == 'sem_sinal':
        qs = qs.filter(ignicao=None)

    return render(request, 'core/veiculos.html', {
        'veiculos': qs.order_by('placa'),
        'busca':    busca,
        'status':   status,
    })


@login_required
def veiculo_detalhe(request, pk):
    veiculo  = get_object_or_404(Vehicle, pk=pk)
    eventos  = veiculo.events.order_by('-ocorrido_em')[:30]
    alertas  = veiculo.alerts.order_by('-ocorrido_em')[:30]
    return render(request, 'core/veiculo_detalhe.html', {
        'veiculo': veiculo,
        'eventos': eventos,
        'alertas': alertas,
    })


@login_required
@require_POST
def veiculo_upload_foto(request, pk):
    """Recebe o upload de foto via AJAX e retorna a URL da nova imagem."""
    veiculo = get_object_or_404(Vehicle, pk=pk)
    arquivo = request.FILES.get('foto')
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Nenhum arquivo enviado.'}, status=400)

    # Valida tipo
    if not arquivo.content_type.startswith('image/'):
        return JsonResponse({'ok': False, 'erro': 'O arquivo deve ser uma imagem.'}, status=400)

    # Apaga foto antiga para não acumular arquivos
    if veiculo.foto:
        veiculo.foto.delete(save=False)

    veiculo.foto = arquivo
    veiculo.save(update_fields=['foto'])
    return JsonResponse({'ok': True, 'url': veiculo.foto.url})


# ─── Alertas ──────────────────────────────────────────────────────────────────

@login_required
def alertas_lista(request):
    qs = Alert.objects.select_related('vehicle').order_by('-ocorrido_em')

    sev = request.GET.get('sev', '')
    if sev in ('info', 'warning', 'danger'):
        qs = qs.filter(severidade=sev)

    lido = request.GET.get('lido', '')
    if lido == '0':
        qs = qs.filter(lido=False)
    elif lido == '1':
        qs = qs.filter(lido=True)

    return render(request, 'core/alertas.html', {
        'alertas': qs[:200],
        'sev':     sev,
        'lido':    lido,
        'total_nao_lidos': Alert.objects.filter(lido=False).count(),
    })


@login_required
def marcar_alerta_lido(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.lido = True
    alert.save(update_fields=['lido'])
    return JsonResponse({'ok': True})


@login_required
def marcar_todos_lidos(request):
    Alert.objects.filter(lido=False).update(lido=True)
    return JsonResponse({'ok': True})


# ─── Relatórios ───────────────────────────────────────────────────────────────

@login_required
def relatorios(request):
    import csv
    from datetime import datetime as _dt

    now = timezone.now()
    aba = request.GET.get('aba', 'alertas')

    # ── filtros comuns ──
    veiculos_lista = Vehicle.objects.filter(ativo=True).order_by('placa')
    veiculo_id = request.GET.get('veiculo', '')
    data_ini   = request.GET.get('data_ini', '')
    data_fim   = request.GET.get('data_fim', '')

    def parse_date(s, end=False):
        try:
            d = _dt.strptime(s.strip(), '%Y-%m-%d')
            if end:
                d = d.replace(hour=23, minute=59, second=59)
            return timezone.make_aware(d)
        except Exception:
            return None

    dt_ini = parse_date(data_ini) if data_ini else None
    dt_fim = parse_date(data_fim, end=True) if data_fim else None

    # ── relatório: alertas ──
    alertas_qs = Alert.objects.select_related('vehicle').order_by('-ocorrido_em')
    sev_filtro = request.GET.get('severidade', '')
    if veiculo_id:
        alertas_qs = alertas_qs.filter(vehicle_id=veiculo_id)
    if sev_filtro:
        alertas_qs = alertas_qs.filter(severidade=sev_filtro)
    if dt_ini:
        alertas_qs = alertas_qs.filter(ocorrido_em__gte=dt_ini)
    if dt_fim:
        alertas_qs = alertas_qs.filter(ocorrido_em__lte=dt_fim)
    alertas = alertas_qs[:200]

    # ── relatório: eventos de ignição ──
    ignicao_qs = EventoIgnicao.objects.select_related('vehicle').order_by('-ocorrido_em')
    tipo_ign   = request.GET.get('tipo_ign', '')
    if veiculo_id:
        ignicao_qs = ignicao_qs.filter(vehicle_id=veiculo_id)
    if tipo_ign:
        ignicao_qs = ignicao_qs.filter(tipo=tipo_ign)
    if dt_ini:
        ignicao_qs = ignicao_qs.filter(ocorrido_em__gte=dt_ini)
    if dt_fim:
        ignicao_qs = ignicao_qs.filter(ocorrido_em__lte=dt_fim)
    ignicoes = ignicao_qs[:200]

    # ── relatório: velocidade (veículos acima de X km/h) ──
    vel_min  = request.GET.get('vel_min', '80')
    vel_qs   = Event.objects.select_related('vehicle').order_by('-ocorrido_em')
    try:
        vel_min_f = float(vel_min)
        vel_qs = vel_qs.filter(velocidade__gte=vel_min_f)
    except (ValueError, TypeError):
        vel_min_f = 80
    if veiculo_id:
        vel_qs = vel_qs.filter(vehicle_id=veiculo_id)
    if dt_ini:
        vel_qs = vel_qs.filter(ocorrido_em__gte=dt_ini)
    if dt_fim:
        vel_qs = vel_qs.filter(ocorrido_em__lte=dt_fim)
    eventos_vel = vel_qs[:200]

    # ── histórico de sync ──
    sync_status = request.GET.get('sync_status', '')
    syncs_qs    = SyncLog.objects.order_by('-iniciado_em')
    if sync_status:
        syncs_qs = syncs_qs.filter(status=sync_status)
    syncs = syncs_qs[:50]

    return render(request, 'core/relatorios.html', {
        'aba': aba, 'now': now,
        'veiculos_lista': veiculos_lista,
        'veiculo_id': veiculo_id,
        'data_ini': data_ini, 'data_fim': data_fim,
        # alertas
        'alertas': alertas, 'sev_filtro': sev_filtro,
        # ignições
        'ignicoes': ignicoes, 'tipo_ign': tipo_ign,
        # velocidade
        'eventos_vel': eventos_vel, 'vel_min': vel_min,
        # sync
        'syncs': syncs, 'sync_status': sync_status,
    })


@login_required
def exportar_alertas_csv(request):
    import csv
    from datetime import datetime as _dt

    def parse_date(s, end=False):
        try:
            d = _dt.strptime(s.strip(), '%Y-%m-%d')
            if end:
                d = d.replace(hour=23, minute=59, second=59)
            return timezone.make_aware(d)
        except Exception:
            return None

    qs = Alert.objects.select_related('vehicle').order_by('-ocorrido_em')
    if request.GET.get('veiculo'):
        qs = qs.filter(vehicle_id=request.GET['veiculo'])
    if request.GET.get('severidade'):
        qs = qs.filter(severidade=request.GET['severidade'])
    dt_ini = parse_date(request.GET.get('data_ini', ''))
    dt_fim = parse_date(request.GET.get('data_fim', ''), end=True)
    if dt_ini:
        qs = qs.filter(ocorrido_em__gte=dt_ini)
    if dt_fim:
        qs = qs.filter(ocorrido_em__lte=dt_fim)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="alertas.csv"'
    writer = csv.writer(response)
    writer.writerow(['Data/Hora', 'Veículo', 'Placa', 'Tipo', 'Severidade', 'Descrição', 'Lat', 'Long'])
    for a in qs[:5000]:
        writer.writerow([
            timezone.localtime(a.ocorrido_em).strftime('%d/%m/%Y %H:%M:%S'),
            a.vehicle.descricao, a.vehicle.placa,
            a.tipo, a.get_severidade_display(), a.descricao,
            a.latitude or '', a.longitude or '',
        ])
    return response


@login_required
def exportar_eventos_csv(request):
    import csv

    qs = Event.objects.select_related('vehicle').order_by('-ocorrido_em')
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="eventos.csv"'
    writer = csv.writer(response)
    writer.writerow(['Data/Hora', 'Veículo', 'Placa', 'Tipo', 'Descrição', 'Velocidade', 'Lat', 'Long'])
    for e in qs[:5000]:
        writer.writerow([
            timezone.localtime(e.ocorrido_em).strftime('%d/%m/%Y %H:%M:%S'),
            e.vehicle.descricao, e.vehicle.placa,
            e.tipo, e.descricao, e.velocidade or '',
            e.latitude or '', e.longitude or '',
        ])
    return response


@login_required
def exportar_ignicoes_csv(request):
    import csv
    from datetime import datetime as _dt

    def parse_date(s, end=False):
        try:
            d = _dt.strptime(s.strip(), '%Y-%m-%d')
            if end:
                d = d.replace(hour=23, minute=59, second=59)
            return timezone.make_aware(d)
        except Exception:
            return None

    qs = EventoIgnicao.objects.select_related('vehicle').order_by('-ocorrido_em')
    if request.GET.get('veiculo'):
        qs = qs.filter(vehicle_id=request.GET['veiculo'])
    if request.GET.get('tipo_ign'):
        qs = qs.filter(tipo=request.GET['tipo_ign'])
    dt_ini = parse_date(request.GET.get('data_ini', ''))
    dt_fim = parse_date(request.GET.get('data_fim', ''), end=True)
    if dt_ini:
        qs = qs.filter(ocorrido_em__gte=dt_ini)
    if dt_fim:
        qs = qs.filter(ocorrido_em__lte=dt_fim)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="ignicoes.csv"'
    writer = csv.writer(response)
    writer.writerow(['Data/Hora', 'Veículo', 'Placa', 'Tipo', 'Dia da Semana', 'Mensagem'])
    for i in qs[:5000]:
        writer.writerow([
            timezone.localtime(i.ocorrido_em).strftime('%d/%m/%Y %H:%M:%S'),
            i.vehicle.descricao, i.vehicle.placa,
            i.get_tipo_display(), i.dia_semana, i.mensagem,
        ])
    return response


# ─── API: histórico de posições ───────────────────────────────────────────────

@login_required
@require_GET
def api_historico_posicoes(request, pk):
    """Retorna os últimos N pontos de histórico de um veículo."""
    from django.utils import timezone
    from datetime import timedelta

    horas = int(request.GET.get('horas', 4))
    cutoff = timezone.now() - timedelta(hours=horas)

    pontos = PositionHistory.objects.filter(
        vehicle_id=pk,
        registrado_em__gte=cutoff,
    ).order_by('registrado_em').values(
        'latitude', 'longitude', 'velocidade', 'ignicao', 'registrado_em'
    )

    data = [
        {
            'lat': p['latitude'],
            'lng': p['longitude'],
            'vel': p['velocidade'],
            'ign': p['ignicao'],
            'ts':  p['registrado_em'].isoformat(),
        }
        for p in pontos
    ]
    return JsonResponse({'pontos': data})


# ─── API: evento de ignição ───────────────────────────────────────────────────

@login_required
@require_POST
def registrar_evento_ignicao(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    now = timezone.localtime()
    dia_semana_num = now.weekday()  # 0=Seg … 4=Sex, 5=Sáb, 6=Dom

    dias_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira',
               'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    dia_nome = dias_pt[dia_semana_num]
    hora_fmt = now.strftime('%H:%M')
    eh_fim_semana = dia_semana_num >= 5
    eh_fora_horario = eh_fim_semana or not (8 <= now.hour < 18)

    if eh_fora_horario:
        tipo = 'nao_autorizado'
        if eh_fim_semana:
            motivo = 'final de semana'
        elif now.hour < 8:
            motivo = f'antes do horário permitido ({hora_fmt})'
        else:
            motivo = f'após o horário permitido ({hora_fmt})'
        mensagem = (
            f'Veículo ligado em {dia_nome} às {hora_fmt} — {motivo}. '
            f'O uso NÃO é autorizado fora do horário comercial (Seg-Sex 08h-18h). '
            f'Este evento foi registrado para auditoria.'
        )
    else:
        tipo = 'autorizado'
        mensagem = (
            f'Veículo ligado em {dia_nome} às {hora_fmt}. '
            f'Uso autorizado — dia útil dentro do horário comercial.'
        )

    EventoIgnicao.objects.create(
        vehicle=vehicle,
        tipo=tipo,
        dia_semana=dia_nome,
        mensagem=mensagem,
    )

    return JsonResponse({
        'ok': True,
        'tipo': tipo,
        'dia_semana': dia_nome,
        'hora': hora_fmt,
        'mensagem': mensagem,
        'eh_fim_semana': eh_fora_horario,  # popup usa este campo para cor de alerta
    })


# ─── API: atualizar km base ───────────────────────────────────────────────────

@login_required
@require_POST
def atualizar_km_base(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    try:
        km = float(request.POST.get('km', ''))
        if km < 0:
            return JsonResponse({'error': 'Valor inválido'}, status=400)
        vehicle.km_base = km
        vehicle.save(update_fields=['km_base'])
        return JsonResponse({'ok': True, 'km': km})
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Valor inválido'}, status=400)


# ─── API: status da última sync ───────────────────────────────────────────────

@login_required
def api_ultimo_sync(request):
    """Retorna dados do último SyncLog sem acionar nenhuma sincronização."""
    ultimo = SyncLog.objects.order_by('-iniciado_em').first()
    if not ultimo:
        return JsonResponse({'ok': False})
    return JsonResponse({
        'ok': True,
        'data': timezone.localtime(ultimo.iniciado_em).strftime('%d/%m/%Y %H:%M:%S'),
        'status': ultimo.status,
        'status_display': ultimo.get_status_display(),
    })


# ─── API: sync manual ─────────────────────────────────────────────────────────

@login_required
def sync_agora(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    from core.sync import run_sync
    run_sync()
    ultimo = SyncLog.objects.order_by('-iniciado_em').first()
    return JsonResponse({
        'status':  ultimo.status if ultimo else 'ok',
        'veiculos': ultimo.veiculos_sync if ultimo else 0,
        'alertas':  ultimo.alertas_sync if ultimo else 0,
        'eventos':  ultimo.eventos_sync if ultimo else 0,
    })


# ─── Gestão de Usuários ───────────────────────────────────────────────────────

def _is_staff(user):
    return user.is_active and (user.is_staff or user.is_superuser)

_staff_required = user_passes_test(_is_staff, login_url='login')


@login_required
@_staff_required
def usuarios_lista(request):
    usuarios = User.objects.all().order_by('username')
    return render(request, 'core/usuarios.html', {'usuarios': usuarios})


@login_required
@_staff_required
def usuario_criar(request):
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '')
        is_staff   = request.POST.get('is_staff') == 'on'

        if not username or not password:
            messages.error(request, 'Usuário e senha são obrigatórios.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'O usuário "{username}" já existe.')
        else:
            User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name,
                email=email, is_staff=is_staff,
            )
            messages.success(request, f'Usuário "{username}" criado com sucesso.')
            return redirect('usuarios')

    return render(request, 'core/usuario_form.html', {'acao': 'Novo usuário', 'obj': None})


@login_required
@_staff_required
def usuario_editar(request, pk):
    obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        obj.first_name = request.POST.get('first_name', '').strip()
        obj.last_name  = request.POST.get('last_name', '').strip()
        obj.email      = request.POST.get('email', '').strip()
        obj.is_staff   = request.POST.get('is_staff') == 'on'
        nova_senha     = request.POST.get('password', '').strip()
        if nova_senha:
            obj.set_password(nova_senha)
        obj.save()
        messages.success(request, f'Usuário "{obj.username}" atualizado.')
        return redirect('usuarios')

    return render(request, 'core/usuario_form.html', {'acao': 'Editar usuário', 'obj': obj})


@login_required
@_staff_required
def usuario_deletar(request, pk):
    obj = get_object_or_404(User, pk=pk)
    if obj == request.user:
        messages.error(request, 'Você não pode excluir seu próprio usuário.')
    else:
        nome = obj.username
        obj.delete()
        messages.success(request, f'Usuário "{nome}" excluído.')
    return redirect('usuarios')


# ─── Gestão de Frota ──────────────────────────────────────────────────────────

@login_required
def frota(request):
    aba = request.GET.get('aba', 'manutencao')
    veiculos = Vehicle.objects.filter(ativo=True).order_by('placa')

    # filtros comuns
    veiculo_id = request.GET.get('veiculo', '')
    data_ini   = request.GET.get('data_ini', '')
    data_fim   = request.GET.get('data_fim', '')

    from datetime import datetime as _dt
    def parse_date(s, end=False):
        try:
            d = _dt.strptime(s.strip(), '%Y-%m-%d')
            if end: d = d.replace(hour=23, minute=59, second=59)
            return timezone.make_aware(d)
        except Exception:
            return None

    dt_ini = parse_date(data_ini)
    dt_fim = parse_date(data_fim, end=True)

    # manutenções
    man_qs = Manutencao.objects.select_related('vehicle').prefetch_related('arquivos')
    if veiculo_id: man_qs = man_qs.filter(vehicle_id=veiculo_id)
    tipo_man = request.GET.get('tipo_man', '')
    status_man = request.GET.get('status_man', '')
    if tipo_man:   man_qs = man_qs.filter(tipo=tipo_man)
    if status_man: man_qs = man_qs.filter(status=status_man)
    if dt_ini: man_qs = man_qs.filter(data_manutencao__gte=dt_ini.date())
    if dt_fim: man_qs = man_qs.filter(data_manutencao__lte=dt_fim.date())
    manutencoes = man_qs[:100]

    # ocorrências
    oco_qs = Ocorrencia.objects.select_related('vehicle').prefetch_related('arquivos')
    if veiculo_id: oco_qs = oco_qs.filter(vehicle_id=veiculo_id)
    tipo_oco = request.GET.get('tipo_oco', '')
    status_oco = request.GET.get('status_oco', '')
    gravidade_oco = request.GET.get('gravidade_oco', '')
    if tipo_oco:     oco_qs = oco_qs.filter(tipo=tipo_oco)
    if status_oco:   oco_qs = oco_qs.filter(status=status_oco)
    if gravidade_oco: oco_qs = oco_qs.filter(gravidade=gravidade_oco)
    if dt_ini: oco_qs = oco_qs.filter(data_ocorrencia__gte=dt_ini.date())
    if dt_fim: oco_qs = oco_qs.filter(data_ocorrencia__lte=dt_fim.date())
    ocorrencias = oco_qs[:100]

    # totalizadores
    from django.db.models import Sum, Count
    total_custo_man = Manutencao.objects.aggregate(t=Sum('custo'))['t'] or 0
    total_ocorrencias_abertas = Ocorrencia.objects.filter(status='aberta').count()

    return render(request, 'core/frota.html', {
        'aba': aba, 'veiculos': veiculos,
        'veiculo_id': veiculo_id, 'data_ini': data_ini, 'data_fim': data_fim,
        'manutencoes': manutencoes, 'tipo_man': tipo_man, 'status_man': status_man,
        'ocorrencias': ocorrencias, 'tipo_oco': tipo_oco, 'status_oco': status_oco, 'gravidade_oco': gravidade_oco,
        'total_custo_man': total_custo_man,
        'total_ocorrencias_abertas': total_ocorrencias_abertas,
    })


@login_required
def manutencao_criar(request):
    veiculos = Vehicle.objects.filter(ativo=True).order_by('placa')
    if request.method == 'POST':
        man = Manutencao.objects.create(
            vehicle_id       = request.POST.get('vehicle'),
            tipo             = request.POST.get('tipo', 'preventiva'),
            descricao        = request.POST.get('descricao', '').strip(),
            data_manutencao  = request.POST.get('data_manutencao'),
            fornecedor       = request.POST.get('fornecedor', '').strip(),
            status           = request.POST.get('status', 'concluida'),
            observacoes      = request.POST.get('observacoes', '').strip(),
            custo            = request.POST.get('custo') or None,
            km_na_manutencao = request.POST.get('km_na_manutencao') or None,
        )
        for f in request.FILES.getlist('arquivos'):
            ManutencaoArquivo.objects.create(manutencao=man, arquivo=f, nome_original=f.name)
        messages.success(request, 'Manutenção registrada com sucesso.')
        return redirect('frota')
    return render(request, 'core/manutencao_form.html', {'veiculos': veiculos, 'obj': None})


@login_required
def manutencao_editar(request, pk):
    man = get_object_or_404(Manutencao, pk=pk)
    veiculos = Vehicle.objects.filter(ativo=True).order_by('placa')
    if request.method == 'POST':
        man.vehicle_id       = request.POST.get('vehicle')
        man.tipo             = request.POST.get('tipo', 'preventiva')
        man.descricao        = request.POST.get('descricao', '').strip()
        man.data_manutencao  = request.POST.get('data_manutencao')
        man.fornecedor       = request.POST.get('fornecedor', '').strip()
        man.status           = request.POST.get('status', 'concluida')
        man.observacoes      = request.POST.get('observacoes', '').strip()
        man.custo            = request.POST.get('custo') or None
        man.km_na_manutencao = request.POST.get('km_na_manutencao') or None
        man.save()
        for f in request.FILES.getlist('arquivos'):
            ManutencaoArquivo.objects.create(manutencao=man, arquivo=f, nome_original=f.name)
        messages.success(request, 'Manutenção atualizada.')
        return redirect('frota')
    return render(request, 'core/manutencao_form.html', {'veiculos': veiculos, 'obj': man})


@login_required
def manutencao_deletar(request, pk):
    man = get_object_or_404(Manutencao, pk=pk)
    man.delete()
    messages.success(request, 'Manutenção excluída.')
    return redirect('frota')


@login_required
@require_POST
def manutencao_arquivo_deletar(request, pk):
    arq = get_object_or_404(ManutencaoArquivo, pk=pk)
    arq.arquivo.delete(save=False)
    arq.delete()
    return JsonResponse({'ok': True})


@login_required
def ocorrencia_criar(request):
    veiculos = Vehicle.objects.filter(ativo=True).order_by('placa')
    if request.method == 'POST':
        oco = Ocorrencia.objects.create(
            vehicle_id      = request.POST.get('vehicle'),
            tipo            = request.POST.get('tipo', 'acidente'),
            descricao       = request.POST.get('descricao', '').strip(),
            data_ocorrencia = request.POST.get('data_ocorrencia'),
            local           = request.POST.get('local', '').strip(),
            gravidade       = request.POST.get('gravidade', 'leve'),
            status          = request.POST.get('status', 'aberta'),
            observacoes     = request.POST.get('observacoes', '').strip(),
            custo_estimado  = request.POST.get('custo_estimado') or None,
        )
        for f in request.FILES.getlist('arquivos'):
            OcorrenciaArquivo.objects.create(ocorrencia=oco, arquivo=f, nome_original=f.name)
        messages.success(request, 'Ocorrência registrada com sucesso.')
        return redirect('/frota/?aba=ocorrencias')
    return render(request, 'core/ocorrencia_form.html', {'veiculos': veiculos, 'obj': None})


@login_required
def ocorrencia_editar(request, pk):
    oco = get_object_or_404(Ocorrencia, pk=pk)
    veiculos = Vehicle.objects.filter(ativo=True).order_by('placa')
    if request.method == 'POST':
        oco.vehicle_id      = request.POST.get('vehicle')
        oco.tipo            = request.POST.get('tipo', 'acidente')
        oco.descricao       = request.POST.get('descricao', '').strip()
        oco.data_ocorrencia = request.POST.get('data_ocorrencia')
        oco.local           = request.POST.get('local', '').strip()
        oco.gravidade       = request.POST.get('gravidade', 'leve')
        oco.status          = request.POST.get('status', 'aberta')
        oco.observacoes     = request.POST.get('observacoes', '').strip()
        oco.custo_estimado  = request.POST.get('custo_estimado') or None
        oco.save()
        for f in request.FILES.getlist('arquivos'):
            OcorrenciaArquivo.objects.create(ocorrencia=oco, arquivo=f, nome_original=f.name)
        messages.success(request, 'Ocorrência atualizada.')
        return redirect('/frota/?aba=ocorrencias')
    return render(request, 'core/ocorrencia_form.html', {'veiculos': veiculos, 'obj': oco})


@login_required
def ocorrencia_deletar(request, pk):
    oco = get_object_or_404(Ocorrencia, pk=pk)
    oco.delete()
    messages.success(request, 'Ocorrência excluída.')
    return redirect('frota?aba=ocorrencias')


@login_required
@require_POST
def ocorrencia_arquivo_deletar(request, pk):
    arq = get_object_or_404(OcorrenciaArquivo, pk=pk)
    arq.arquivo.delete(save=False)
    arq.delete()
    return JsonResponse({'ok': True})
