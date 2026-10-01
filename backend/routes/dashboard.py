"""Resumo para o painel, com cada tipo de evidência numa seção separada.

Relatos nunca são somados com B.O. nem com a pesquisa. As contagens dos relatos são só descritivas
(``services/analise_padroes.contar_relatos``), sobre os mesmos relatos de ``GET /relatos``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import DIA_MS, RepositorioClassificacoes, RepositorioDados, RepositorioRelatos, instante_atual_ms
from backend.database.sessao import obter_sessao
from backend.models.comum import ResumoDashboard
from backend.models.vocabulario import TipoEvidencia
from backend.services.analise_padroes import contar_relatos

router = APIRouter(tags=['dashboard'])

AVISO_RELATOS = 'Relatos enviados por usuárias, sem verificação individual. Mostram concentração de relatos, não risco.'


@router.get('/dashboard/resumo', response_model=ResumoDashboard)
def resumo(sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    janela = cfg.relatos_janela_dias
    contagem = contar_relatos(RepositorioRelatos(sessao).listar_desde(instante_atual_ms() - janela * DIA_MS))
    dados = RepositorioDados(sessao)
    classificacoes = RepositorioClassificacoes(sessao)
    por_provedor = classificacoes.contar_por_provedor()
    return {
        'relatos_comunidade': {'tipo_evidencia': TipoEvidencia.RELATO_COMUNIDADE.value, 'janela_dias': janela, **contagem,
                               'aviso': AVISO_RELATOS},
        'dados_oficiais': [
            {'chave': c.chave, 'titulo': c.titulo, 'periodo': c.periodo, 'tipo_evidencia': TipoEvidencia.DADO_OFICIAL.value,
             'total': {k: (c.dados.get('total') or {}).get(k) for k in ('vd', 'fe', 'te', 'n')}}
            for c in dados.oficiais()],
        'percepcao': [
            {'chave': c.chave, 'titulo': c.titulo, 'tipo_evidencia': TipoEvidencia.PERCEPCAO.value, 'respostas': c.respostas,
             'de': c.de, 'ate': c.ate}
            for c in dados.percepcoes()],
        'classificacoes_automaticas': {'tipo_evidencia': TipoEvidencia.CLASSIFICACAO_AUTOMATICA.value,
                                       'total': sum(por_provedor.values()), 'por_provedor': por_provedor},
        'analise_ia': {'tipo_evidencia': TipoEvidencia.ANALISE_IA.value, 'implementado': False},
    }
