"""Provedor padrão: as mesmas regras de palavras-chave do chat do legado, sem modelo."""
from __future__ import annotations

from backend.services.classificacao import extrair_campos
from backend.services.ia.base import ContextoIA, ProvedorIA, ResultadoExtracao


class ProvedorHeuristico(ProvedorIA):
    nome = 'heuristica'
    usa_modelo = False
    modelo = None
    capacidades = frozenset({'extrair', 'classificar', 'analise_padroes'})

    def extrair(self, texto: str, contexto: ContextoIA) -> ResultadoExtracao:
        # texto inteiro, como heuristic() no legado; o corte em 1500 era só do prompt da IA (prompts.py)
        e = extrair_campos(texto or '', contexto.bairros)
        return ResultadoExtracao(urgente=e.urgente, tipos=list(e.tipos), bairro=e.bairro, quando=e.quando, periodo=e.periodo,
                                 descricao=e.descricao, removidos=list(e.removidos), resposta=e.resposta)
