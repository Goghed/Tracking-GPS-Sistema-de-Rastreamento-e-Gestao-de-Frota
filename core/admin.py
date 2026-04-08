from django.contrib import admin
from core.models import Vehicle, Alert, Event, SyncLog, EventoIgnicao, Manutencao, ManutencaoArquivo, Ocorrencia, OcorrenciaArquivo


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ['placa', 'descricao', 'modelo', 'ano', 'ignicao', 'velocidade_atual',
                     'km_base', 'km_percorrido_hoje', 'ultima_posicao']
    list_filter   = ['ativo', 'ignicao']
    search_fields = ['placa', 'descricao', 'chassi']
    readonly_fields = ['api_id', 'api_client_id', 'odometro', 'criado_em', 'atualizado_em',
                       'km_percorrido_hoje', 'km_dia_data']
    fieldsets = [
        ('Identificação', {'fields': ['api_id', 'api_client_id', 'placa', 'tag', 'descricao', 'ativo']}),
        ('Veículo', {'fields': ['chassi', 'ano', 'cor', 'tipo', 'fabricante', 'modelo', 'combustivel', 'consumo']}),
        ('Rastreamento', {'fields': ['equipamento', 'velocidade_limite', 'odometro']}),
        ('KM / Odômetro', {'fields': ['km_base', 'km_percorrido_hoje', 'km_dia_data'],
                           'description': 'km_base: inserido manualmente. km_percorrido_hoje: calculado automaticamente pelo sistema.'}),
        ('Posição Atual', {'fields': ['latitude', 'longitude', 'velocidade_atual', 'ignicao', 'direcao', 'ultima_posicao']}),
        ('Foto', {'fields': ['foto']}),
        ('Auditoria', {'fields': ['criado_em', 'atualizado_em']}),
    ]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ['vehicle', 'tipo', 'severidade', 'lido', 'ocorrido_em']
    list_filter   = ['severidade', 'lido']
    search_fields = ['vehicle__placa', 'tipo']
    readonly_fields = ['api_alert_id', 'criado_em']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display  = ['vehicle', 'tipo', 'velocidade', 'ocorrido_em']
    search_fields = ['vehicle__placa', 'tipo']
    readonly_fields = ['api_event_id', 'criado_em']


@admin.register(EventoIgnicao)
class EventoIgnicaoAdmin(admin.ModelAdmin):
    list_display  = ['vehicle', 'tipo', 'dia_semana', 'lido', 'ocorrido_em']
    list_filter   = ['tipo', 'lido', 'dia_semana']
    search_fields = ['vehicle__placa', 'vehicle__descricao']
    readonly_fields = ['vehicle', 'tipo', 'dia_semana', 'mensagem', 'ocorrido_em']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display  = ['iniciado_em', 'status', 'veiculos_sync', 'alertas_sync', 'eventos_sync']
    list_filter   = ['status']
    readonly_fields = ['iniciado_em', 'finalizado_em']


class ManutencaoArquivoInline(admin.TabularInline):
    model = ManutencaoArquivo
    extra = 0

@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display  = ['vehicle', 'tipo', 'descricao', 'data_manutencao', 'custo', 'status']
    list_filter   = ['tipo', 'status']
    search_fields = ['vehicle__placa', 'descricao', 'fornecedor']
    inlines       = [ManutencaoArquivoInline]


class OcorrenciaArquivoInline(admin.TabularInline):
    model = OcorrenciaArquivo
    extra = 0

@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    list_display  = ['vehicle', 'tipo', 'data_ocorrencia', 'gravidade', 'status', 'custo_estimado']
    list_filter   = ['tipo', 'gravidade', 'status']
    search_fields = ['vehicle__placa', 'descricao', 'local']
    inlines       = [OcorrenciaArquivoInline]
