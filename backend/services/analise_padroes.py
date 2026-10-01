"""Contagens dos relatos da comunidade.

É só contagem descritiva: quantos relatos, por tipo, por período e por célula. Não calcula
tendências, não faz agrupamentos e não faz nenhum juízo de risco (os relatos não são verificados
um a um e mostram concentração de relatos, não risco).
"""
from __future__ import annotations


def _campo(r, nome):
    if isinstance(r, dict):
        return r.get(nome)
    return getattr(r, nome, None)


def contar_relatos(relatos) -> dict:
    """``{"total", "por_tipo", "por_periodo", "por_celula"}``, com as chaves na ordem em que aparecem.

    Aceita objetos com ``tipos``/``periodo``/``cell`` (ou ``celula``) ou dicts. Um tipo conta uma vez
    por relato; relatos sem período não entram em ``por_periodo``.
    """
    total = 0
    por_tipo: dict[str, int] = {}
    por_periodo: dict[str, int] = {}
    por_celula: dict[str, int] = {}
    for r in relatos:
        total += 1
        for t in dict.fromkeys(_campo(r, 'tipos') or []):
            por_tipo[t] = por_tipo.get(t, 0) + 1
        periodo = _campo(r, 'periodo')
        if periodo:
            por_periodo[periodo] = por_periodo.get(periodo, 0) + 1
        cell = _campo(r, 'cell')
        if cell is None:
            cell = _campo(r, 'celula')
        if cell:
            por_celula[cell] = por_celula.get(cell, 0) + 1
    return {'total': total, 'por_tipo': por_tipo, 'por_periodo': por_periodo, 'por_celula': por_celula}
