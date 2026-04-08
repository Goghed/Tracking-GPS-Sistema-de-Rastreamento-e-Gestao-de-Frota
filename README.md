<<<<<<< HEAD
# FleetCore

Dashboard de monitoramento de frota integrado com a API Fulltrack2.

## Stack
- Django 5 + SQLite
- APScheduler (sync automático a cada 1 minuto)
- Leaflet.js (mapa ao vivo)
- Chart.js (gráficos)
- Design: Space Mono + DM Sans, tema escuro industrial

## Instalação

### 1. Crie e ative o ambiente virtual
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure o token da Fulltrack
Edite `config/settings.py` e preencha:
```python
FULLTRACK_TOKEN = 'seu-token-aqui'
```

### 4. Rode as migrations
```bash
python manage.py migrate
```

### 5. Crie um superusuário
```bash
python manage.py createsuperuser
```

### 6. Inicie o servidor
```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## Módulos

| URL | Descrição |
|-----|-----------|
| `/` | Dashboard com KPIs e gráficos |
| `/mapa/` | Mapa ao vivo com Leaflet.js |
| `/veiculos/` | Lista de veículos com filtros |
| `/veiculos/<id>/` | Detalhe do veículo |
| `/alertas/` | Feed de alertas com filtros |
| `/relatorios/` | Exportação CSV e histórico de sync |
| `/admin/` | Painel admin Django |
| `/api/sync/` | POST — dispara sync manual |
| `/api/posicoes/` | GET JSON — posições para o mapa |

## Sincronização

O scheduler inicia automaticamente com o servidor (`runserver` ou `gunicorn`).
Você também pode disparar uma sync manual pelo botão **SYNC** no topo da interface.

## Estrutura
```
fleetcore/
├── config/
│   ├── settings.py
│   └── urls.py
├── core/
│   ├── models.py          # Vehicle, Alert, Event, SyncLog
│   ├── sync.py            # Consome a Fulltrack API
│   ├── scheduler.py       # APScheduler (1 min)
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── context_processors.py
│   └── templates/core/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── mapa.html
│       ├── veiculos.html
│       ├── veiculo_detalhe.html
│       ├── alertas.html
│       └── relatorios.html
└── manage.py
```
=======
# Tracking-GPS-Sistema-de-Rastreamento-e-Gestao-de-Frota
Sistema de Rastreamento de Veiculo e Gestão de Frota
>>>>>>> 45ff0d2c52d9674149dc2cb91f6a224c4a8e52e4
