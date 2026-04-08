from django.urls import path
from core import views

urlpatterns = [
    path('',                           views.dashboard,            name='dashboard'),
    path('mapa/',                      views.mapa,                 name='mapa'),
    path('veiculos/',                  views.veiculos_lista,       name='veiculos'),
    path('veiculos/<int:pk>/',         views.veiculo_detalhe,      name='veiculo_detalhe'),
    path('alertas/',                   views.alertas_lista,        name='alertas'),
    path('alertas/<int:pk>/lido/',     views.marcar_alerta_lido,   name='marcar_lido'),
    path('alertas/todos-lidos/',       views.marcar_todos_lidos,   name='todos_lidos'),
    path('relatorios/',                views.relatorios,           name='relatorios'),
    path('relatorios/alertas.csv',     views.exportar_alertas_csv,  name='export_alertas'),
    path('relatorios/eventos.csv',     views.exportar_eventos_csv,  name='export_eventos'),
    path('relatorios/ignicoes.csv',    views.exportar_ignicoes_csv, name='export_ignicoes'),

    # APIs internas
    path('api/posicoes/',              views.api_veiculos_posicao,   name='api_posicoes'),
    path('api/historico/<int:pk>/',    views.api_historico_posicoes, name='api_historico'),
    path('api/sync/',                  views.sync_agora,             name='sync_agora'),
    path('api/ultimo-sync/',           views.api_ultimo_sync,        name='api_ultimo_sync'),
    path('api/km-base/<int:pk>/',         views.atualizar_km_base,         name='atualizar_km_base'),
    path('api/foto/<int:pk>/',            views.veiculo_upload_foto,        name='upload_foto'),
    path('api/evento-ignicao/<int:pk>/',  views.registrar_evento_ignicao,  name='evento_ignicao'),

    # Gestão de frota
    path('frota/',                              views.frota,                      name='frota'),
    path('frota/manutencao/novo/',              views.manutencao_criar,            name='manutencao_criar'),
    path('frota/manutencao/<int:pk>/editar/',   views.manutencao_editar,           name='manutencao_editar'),
    path('frota/manutencao/<int:pk>/deletar/',  views.manutencao_deletar,          name='manutencao_deletar'),
    path('frota/manutencao/arquivo/<int:pk>/deletar/', views.manutencao_arquivo_deletar, name='manutencao_arquivo_deletar'),
    path('frota/ocorrencia/novo/',              views.ocorrencia_criar,            name='ocorrencia_criar'),
    path('frota/ocorrencia/<int:pk>/editar/',   views.ocorrencia_editar,           name='ocorrencia_editar'),
    path('frota/ocorrencia/<int:pk>/deletar/',  views.ocorrencia_deletar,          name='ocorrencia_deletar'),
    path('frota/ocorrencia/arquivo/<int:pk>/deletar/', views.ocorrencia_arquivo_deletar, name='ocorrencia_arquivo_deletar'),

    # Gestão de usuários
    path('usuarios/',                     views.usuarios_lista,    name='usuarios'),
    path('usuarios/novo/',                views.usuario_criar,     name='usuario_criar'),
    path('usuarios/<int:pk>/editar/',     views.usuario_editar,    name='usuario_editar'),
    path('usuarios/<int:pk>/deletar/',    views.usuario_deletar,   name='usuario_deletar'),
]
