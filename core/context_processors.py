from core.models import Alert


def nao_lidos(request):
    """Injeta contagem de alertas não lidos em todos os templates."""
    if request.user.is_authenticated:
        return {'nao_lidos': Alert.objects.filter(lido=False).count()}
    return {'nao_lidos': 0}
