from django.db import models
from django.utils import timezone


class Vehicle(models.Model):
    # IDs da API
    api_id          = models.CharField(max_length=20, unique=True, verbose_name="ID API")
    api_client_id   = models.CharField(max_length=20, blank=True)

    # Dados do veículo
    placa           = models.CharField(max_length=20, blank=True, verbose_name="Placa")
    tag             = models.CharField(max_length=50, blank=True, verbose_name="Tag")
    descricao       = models.CharField(max_length=200, blank=True, verbose_name="Descrição")
    chassi          = models.CharField(max_length=50, blank=True)
    ano             = models.CharField(max_length=10, blank=True)
    cor             = models.CharField(max_length=50, blank=True)
    tipo            = models.CharField(max_length=10, blank=True)
    fabricante      = models.CharField(max_length=10, blank=True)
    modelo          = models.CharField(max_length=100, blank=True)
    combustivel     = models.CharField(max_length=10, blank=True)
    consumo         = models.CharField(max_length=20, blank=True)
    velocidade_limite = models.CharField(max_length=20, blank=True)
    odometro        = models.CharField(max_length=20, blank=True)
    equipamento     = models.CharField(max_length=100, blank=True, null=True)

    # Posição atual (atualizada no sync)
    latitude        = models.FloatField(null=True, blank=True)
    longitude       = models.FloatField(null=True, blank=True)
    velocidade_atual = models.FloatField(null=True, blank=True)
    ignicao         = models.BooleanField(null=True, blank=True)
    direcao         = models.FloatField(null=True, blank=True, verbose_name="Direção (graus)")
    ultima_posicao  = models.DateTimeField(null=True, blank=True)

    # Foto
    foto            = models.ImageField(upload_to='veiculos/', null=True, blank=True, verbose_name="Foto")

    # KM / Odômetro
    km_base         = models.FloatField(null=True, blank=True, verbose_name="KM Base (odômetro manual)")
    km_percorrido_hoje = models.FloatField(default=0.0, verbose_name="KM percorrido hoje")
    km_dia_data     = models.DateField(null=True, blank=True, verbose_name="Data referência km diário")

    # Controle
    ativo           = models.BooleanField(default=True)
    criado_em       = models.DateTimeField(auto_now_add=True)
    atualizado_em   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ['placa']

    def __str__(self):
        return f"{self.placa} - {self.descricao}"

    @property
    def km_total_estimado(self):
        """Soma km_base (manual) + km_percorrido_hoje (automático)."""
        base = self.km_base or 0.0
        return base + (self.km_percorrido_hoje or 0.0)

    @property
    def status_display(self):
        if self.ignicao is None:
            return "Desconhecido"
        return "Ligado" if self.ignicao else "Desligado"

    @property
    def status_color(self):
        if self.ignicao is None:
            return "gray"
        return "green" if self.ignicao else "red"


class Event(models.Model):
    vehicle         = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='events')
    api_event_id    = models.CharField(max_length=50, blank=True)
    tipo            = models.CharField(max_length=100, blank=True, verbose_name="Tipo")
    descricao       = models.TextField(blank=True, verbose_name="Descrição")
    latitude        = models.FloatField(null=True, blank=True)
    longitude       = models.FloatField(null=True, blank=True)
    velocidade      = models.FloatField(null=True, blank=True)
    ocorrido_em     = models.DateTimeField(default=timezone.now)
    criado_em       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ['-ocorrido_em']

    def __str__(self):
        return f"{self.vehicle.placa} | {self.tipo} | {self.ocorrido_em:%d/%m/%Y %H:%M}"


class Alert(models.Model):
    SEVERIDADE_CHOICES = [
        ('info',    'Informação'),
        ('warning', 'Atenção'),
        ('danger',  'Crítico'),
    ]

    vehicle         = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='alerts')
    api_alert_id    = models.CharField(max_length=50, blank=True)
    tipo            = models.CharField(max_length=100, blank=True, verbose_name="Tipo")
    descricao       = models.TextField(blank=True, verbose_name="Descrição")
    severidade      = models.CharField(max_length=10, choices=SEVERIDADE_CHOICES, default='info')
    latitude        = models.FloatField(null=True, blank=True)
    longitude       = models.FloatField(null=True, blank=True)
    lido            = models.BooleanField(default=False)
    ocorrido_em     = models.DateTimeField(default=timezone.now)
    criado_em       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-ocorrido_em']

    def __str__(self):
        return f"{self.vehicle.placa} | {self.tipo} | {self.ocorrido_em:%d/%m/%Y %H:%M}"


class PositionHistory(models.Model):
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='historico')
    latitude    = models.FloatField()
    longitude   = models.FloatField()
    velocidade  = models.FloatField(null=True, blank=True)
    ignicao     = models.BooleanField(null=True, blank=True)
    direcao     = models.FloatField(null=True, blank=True)
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['registrado_em']
        indexes  = [
            models.Index(fields=['vehicle', 'registrado_em']),
        ]

    def __str__(self):
        return f"{self.vehicle.placa} @ {self.registrado_em:%d/%m %H:%M:%S}"


class EventoIgnicao(models.Model):
    TIPO_CHOICES = [
        ('autorizado',    'Autorizado'),
        ('nao_autorizado', 'Não Autorizado'),
    ]

    vehicle     = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='eventos_ignicao')
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    dia_semana  = models.CharField(max_length=20)
    mensagem    = models.TextField()
    lido        = models.BooleanField(default=False)
    ocorrido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento de Ignição'
        verbose_name_plural = 'Eventos de Ignição'
        ordering = ['-ocorrido_em']

    def __str__(self):
        return f"{self.vehicle.placa} | {self.tipo} | {self.ocorrido_em:%d/%m/%Y %H:%M}"


# ─── Gestão de Frota ──────────────────────────────────────────────────────────

class Manutencao(models.Model):
    TIPO_CHOICES = [
        ('preventiva', 'Preventiva'),
        ('corretiva',  'Corretiva'),
        ('revisao',    'Revisão'),
        ('pneu',       'Pneu / Borracharia'),
        ('funilaria',  'Funilaria / Pintura'),
        ('eletrica',   'Elétrica'),
        ('outros',     'Outros'),
    ]
    STATUS_CHOICES = [
        ('agendada',      'Agendada'),
        ('em_andamento',  'Em andamento'),
        ('concluida',     'Concluída'),
    ]

    vehicle          = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='manutencoes')
    tipo             = models.CharField(max_length=20, choices=TIPO_CHOICES, default='preventiva')
    descricao        = models.CharField(max_length=200)
    data_manutencao  = models.DateField()
    custo            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    km_na_manutencao = models.IntegerField(null=True, blank=True)
    fornecedor       = models.CharField(max_length=100, blank=True)
    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default='concluida')
    observacoes      = models.TextField(blank=True)
    criado_em        = models.DateTimeField(auto_now_add=True)
    atualizado_em    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Manutenção'
        verbose_name_plural = 'Manutenções'
        ordering = ['-data_manutencao']

    def __str__(self):
        return f"{self.vehicle.placa} | {self.get_tipo_display()} | {self.data_manutencao}"


class ManutencaoArquivo(models.Model):
    manutencao    = models.ForeignKey(Manutencao, on_delete=models.CASCADE, related_name='arquivos')
    arquivo       = models.FileField(upload_to='manutencoes/')
    nome_original = models.CharField(max_length=255, blank=True)
    criado_em     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Arquivo de Manutenção'
        ordering = ['criado_em']

    def __str__(self):
        return self.nome_original or self.arquivo.name

    @property
    def extensao(self):
        name = self.nome_original or self.arquivo.name
        return name.rsplit('.', 1)[-1].lower() if '.' in name else ''

    @property
    def eh_imagem(self):
        return self.extensao in ('jpg', 'jpeg', 'png', 'webp', 'gif')


class Ocorrencia(models.Model):
    TIPO_CHOICES = [
        ('acidente',   'Acidente'),
        ('multa',      'Multa'),
        ('furto',      'Furto / Roubo'),
        ('vandalismo', 'Vandalismo'),
        ('avaria',     'Avaria'),
        ('outros',     'Outros'),
    ]
    GRAVIDADE_CHOICES = [
        ('leve',     'Leve'),
        ('moderada', 'Moderada'),
        ('grave',    'Grave'),
    ]
    STATUS_CHOICES = [
        ('aberta',     'Aberta'),
        ('em_analise', 'Em análise'),
        ('resolvida',  'Resolvida'),
    ]

    vehicle         = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='ocorrencias')
    tipo            = models.CharField(max_length=20, choices=TIPO_CHOICES, default='acidente')
    descricao       = models.TextField()
    data_ocorrencia = models.DateField()
    local           = models.CharField(max_length=200, blank=True)
    gravidade       = models.CharField(max_length=10, choices=GRAVIDADE_CHOICES, default='leve')
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='aberta')
    custo_estimado  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observacoes     = models.TextField(blank=True)
    criado_em       = models.DateTimeField(auto_now_add=True)
    atualizado_em   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ocorrência'
        verbose_name_plural = 'Ocorrências'
        ordering = ['-data_ocorrencia']

    def __str__(self):
        return f"{self.vehicle.placa} | {self.get_tipo_display()} | {self.data_ocorrencia}"


class OcorrenciaArquivo(models.Model):
    ocorrencia    = models.ForeignKey(Ocorrencia, on_delete=models.CASCADE, related_name='arquivos')
    arquivo       = models.FileField(upload_to='ocorrencias/')
    nome_original = models.CharField(max_length=255, blank=True)
    criado_em     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Arquivo de Ocorrência'
        ordering = ['criado_em']

    def __str__(self):
        return self.nome_original or self.arquivo.name

    @property
    def extensao(self):
        name = self.nome_original or self.arquivo.name
        return name.rsplit('.', 1)[-1].lower() if '.' in name else ''

    @property
    def eh_imagem(self):
        return self.extensao in ('jpg', 'jpeg', 'png', 'webp', 'gif')


class SyncLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Sucesso'),
        ('error',   'Erro'),
        ('partial', 'Parcial'),
    ]

    iniciado_em     = models.DateTimeField(auto_now_add=True)
    finalizado_em   = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    veiculos_sync   = models.IntegerField(default=0)
    alertas_sync    = models.IntegerField(default=0)
    eventos_sync    = models.IntegerField(default=0)
    erro_msg        = models.TextField(blank=True)

    class Meta:
        verbose_name = "Log de Sincronização"
        verbose_name_plural = "Logs de Sincronização"
        ordering = ['-iniciado_em']

    def __str__(self):
        return f"Sync {self.iniciado_em:%d/%m/%Y %H:%M:%S} - {self.status}"

    @property
    def duracao_segundos(self):
        if self.finalizado_em:
            return (self.finalizado_em - self.iniciado_em).total_seconds()
        return None
