"""IA: qual provedor está em uso e a extração de campos do texto do chat.

Na fase 1 o provedor é o heurístico (palavras-chave, sem modelo). ``POST /ia/extrair`` não guarda nem
registra o texto recebido.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import RepositorioDados
from backend.database.sessao import obter_sessao
from backend.models.comum import ErroValidacao, texto_bem_formado
from backend.models.ia import EntradaExtracao, InfoProvedor, RespostaExtracao
from backend.models.vocabulario import TipoEvidencia
from backend.services.ia import ContextoIA, obter_provedor

router = APIRouter(tags=['ia'])


@router.get('/ia/provedor', response_model=InfoProvedor)
def provedor(cfg: Configuracoes = Depends(obter_configuracoes)):
    return obter_provedor(cfg.ia_provedor).info()


@router.post('/ia/extrair', response_model=RespostaExtracao, responses={422: {'model': ErroValidacao}})
def extrair(entrada: EntradaExtracao, sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    p = obter_provedor(cfg.ia_provedor)
    r = p.extrair(entrada.texto, ContextoIA(bairros=RepositorioDados(sessao).bairros()))
    bairro = {'nome': r.bairro.nome, 'lat': r.bairro.lat, 'lng': r.bairro.lng} if r.bairro is not None else None
    return {
        'provedor': p.nome,
        'usa_modelo': p.usa_modelo,
        'tipo_evidencia': TipoEvidencia.CLASSIFICACAO_AUTOMATICA.value,
        'resultado': {'urgente': bool(r.urgente), 'tipos': list(r.tipos), 'bairro': bairro, 'quando': r.quando,
                      'periodo': r.periodo, 'descricao': texto_bem_formado(r.descricao), 'removidos': list(r.removidos),
                      'resposta': texto_bem_formado(r.resposta)},
    }
