"""Análise de padrões (US-02): ``GET /analise/padroes``.

Detecta padrões por região, período e tipo de ocorrência nos relatos, no histórico de B.O. e na pesquisa (``services/padroes.py``),
e pede ao provedor de IA o resumo em linguagem simples. Não guarda nada; o texto de relatos nunca vai ao modelo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import CHAVE_GEOGRAFIA, DIA_MS, RepositorioDados, RepositorioRelatos, instante_atual_ms
from backend.database.sessao import obter_sessao
from backend.models.analise import AnalisePadroes
from backend.models.comum import Erro
from backend.models.vocabulario import TipoEvidencia
from backend.services.ia import obter_provedor
from backend.services.padroes import analisar

router = APIRouter(tags=['analise'])


@router.get('/analise/padroes', response_model=AnalisePadroes, responses={404: {'model': Erro}})
def padroes(sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    dados = RepositorioDados(sessao)
    geo = dados.referencia(CHAVE_GEOGRAFIA)
    if geo is None or not isinstance(geo.dados.get('hex'), dict):
        raise HTTPException(404, 'A geografia do mapa não está carregada.')
    agora = instante_atual_ms()
    relatos = RepositorioRelatos(sessao).listar_desde(agora - cfg.relatos_janela_dias * DIA_MS)
    res = analisar(relatos, dados.oficiais(), dados.percepcoes(), geo.dados['hex'], dados.bairros(), cfg.relatos_janela_dias)
    provedor = obter_provedor(cfg.ia_provedor)
    texto, por_modelo = provedor.analisar_padroes(res)
    return {'tipo_evidencia': TipoEvidencia.ANALISE_IA.value, 'provedor': provedor.nome, 'usa_modelo': por_modelo, 'resumo': texto, **res}
