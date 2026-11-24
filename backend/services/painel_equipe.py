"""Contagens privadas da equipe: relatos retidos, incluindo os ocultos."""
from collections import Counter
from datetime import datetime, timezone
from backend.database.repositorios import DIA_MS, RepositorioRelatos, RepositorioModeracao, instante_atual_ms
from backend.services.retencao import limite_retencao_ms
from backend.services.analise_padroes import contar_relatos


def resumo_equipe(sessao, cfg, dias=30):
    agora = instante_atual_ms()
    desde = max(agora - dias * DIA_MS, limite_retencao_ms(cfg, agora) or 0)
    relatos = RepositorioRelatos(sessao).listar_desde(desde, incluir_ocultos=True)
    mod = RepositorioModeracao(sessao).estado([r.id for r in relatos])
    ocultos = sum(bool(mod['oculto'].get(r.id)) for r in relatos)
    verificados = sum(bool(mod['verificado'].get(r.id)) and not mod['oculto'].get(r.id) for r in relatos)
    contagem = contar_relatos(relatos)
    por_dia = Counter(datetime.fromtimestamp(r.criado / 1000, timezone.utc).strftime('%Y-%m-%d') for r in relatos)
    return {'dias': dias, 'gerado_em': agora, 'desde': desde,
            'indicadores': {'total': len(relatos), 'pendentes': len(relatos)-ocultos-verificados,
                            'verificados': verificados, 'ocultos': ocultos},
            'por_tipo': contagem['por_tipo'], 'por_celula': contagem['por_celula'],
            'por_dia': dict(sorted(por_dia.items())),
            'aviso': 'Contagens de relatos da comunidade, incluindo ocultos. Não representam risco nem boletins de ocorrência. Período pela data de envio (UTC).'}
