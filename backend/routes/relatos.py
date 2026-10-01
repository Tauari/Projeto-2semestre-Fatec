"""Relatos da comunidade (tipo de evidência relato_comunidade).

O servidor sempre limpa o texto de novo (``anonimizar_texto``, o mesmo ``scrub`` do legado) e corta em
``relatos_texto_max``. O texto original nunca é guardado nem registrado em log, e o relato não guarda
nada de quem enviou: só o hash da chave que permite apagá-lo.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import (
    DIA_MS,
    RepositorioClassificacoes,
    RepositorioDados,
    RepositorioRelatos,
    instante_atual_ms,
)
from backend.database.sessao import obter_sessao
from backend.database.tabelas import Relato
from backend.models.comum import Erro, ErroValidacao, texto_bem_formado
from backend.models.relatos import ListaRelatos, RelatoEntrada, RelatoPublico, RespostaRelato, RespostaRelatoCriado
from backend.models.vocabulario import TipoEvidencia
from backend.services.anonimizacao import anonimizar_texto
from backend.services.ia import ContextoIA, obter_provedor
from backend.services.retencao import aplicar_retencao, limite_retencao_ms
from backend.services.texto import fatiar_js

log = logging.getLogger('aurora.relatos')
router = APIRouter(tags=['relatos'])

HORA_MS = 3_600_000


def hash_da_chave(chave: str) -> str:
    return hashlib.sha256(chave.encode('utf-8')).hexdigest()


def arredondar_criado(ms: int, precisao: str) -> int:
    """``relatos_precisao_criado``: "exata" guarda o instante; "hora" e "dia" arredondam para baixo (em UTC)."""
    if precisao == 'hora':
        return ms - ms % HORA_MS
    if precisao == 'dia':
        return ms - ms % DIA_MS
    return ms


def relato_publico(relato: Relato) -> dict:
    return RelatoPublico.model_validate(relato).model_dump()


def _classificar(sessao: Session, relato: Relato, texto: str, cfg: Configuracoes) -> None:
    # a classificação é um extra: se falhar, o relato já está salvo e segue sem ela
    try:
        provedor = obter_provedor(cfg.ia_provedor)
        r = provedor.classificar(texto, ContextoIA(bairros=RepositorioDados(sessao).bairros()))
        RepositorioClassificacoes(sessao).criar(relato_id=relato.id, provedor=provedor.nome, modelo=provedor.modelo,
                                                tipos=list(r.tipos), urgente=bool(r.urgente), quando=r.quando,
                                                periodo=r.periodo, confianca=r.confianca, criado=relato.criado)
        sessao.commit()
    except Exception as e:
        sessao.rollback()
        log.warning('classificação automática falhou (%s); o relato foi salvo sem ela.', type(e).__name__)


@router.get('/relatos', response_model=ListaRelatos)
def listar(janela_dias: int | None = Query(None, ge=1, le=3650), sessao: Session = Depends(obter_sessao),
           cfg: Configuracoes = Depends(obter_configuracoes)):
    n = cfg.relatos_janela_dias if janela_dias is None else janela_dias
    agora = instante_atual_ms()
    desde = max(agora - n * DIA_MS, limite_retencao_ms(cfg, agora) or 0)  # nada fora do prazo de retenção sai daqui
    relatos = RepositorioRelatos(sessao).listar_desde(desde)
    return {'tipo_evidencia': TipoEvidencia.RELATO_COMUNIDADE.value, 'janela_dias': n,
            'relatos': [relato_publico(r) for r in relatos]}


@router.get('/relatos/{relato_id}', response_model=RespostaRelato, responses={404: {'model': Erro}})
def obter(relato_id: str, sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    relato = RepositorioRelatos(sessao).obter(relato_id)
    limite = limite_retencao_ms(cfg, instante_atual_ms())
    if relato is None or (limite is not None and relato.criado < limite):
        raise HTTPException(404, 'Relato não encontrado.')
    return {'relato': relato_publico(relato)}


@router.post('/relatos', status_code=201, response_model=RespostaRelatoCriado, responses={422: {'model': ErroValidacao}})
def criar(entrada: RelatoEntrada, sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    aplicar_retencao(sessao)  # com prazo configurado, apaga o que venceu (também sem reiniciar o servidor)
    limpo = anonimizar_texto(entrada.texto)
    texto = texto_bem_formado(fatiar_js(limpo.texto, cfg.relatos_texto_max))
    chave = secrets.token_urlsafe(24)
    relato = RepositorioRelatos(sessao).criar(
        id=uuid4().hex, tipos=entrada.tipos, cell=entrada.cell, quando=entrada.quando, periodo=entrada.periodo,
        texto=texto, origem=entrada.origem, criado=arredondar_criado(instante_atual_ms(), cfg.relatos_precisao_criado),
        chave_hash=hash_da_chave(chave))
    sessao.commit()
    publico = relato_publico(relato)
    if limpo.texto and cfg.ia_classificar_ao_criar:
        _classificar(sessao, relato, limpo.texto, cfg)
    return {'relato': publico, 'chave_exclusao': chave, 'anonimizacao': {'removidos': limpo.removidos}}


@router.delete('/relatos/{relato_id}', status_code=204, response_class=Response,
               responses={403: {'model': Erro}, 404: {'model': Erro}})
def apagar(relato_id: str, chave: str | None = Header(None, alias='X-Chave-Exclusao'), sessao: Session = Depends(obter_sessao)):
    repo = RepositorioRelatos(sessao)
    relato = repo.obter(relato_id)
    if relato is None:
        raise HTTPException(404, 'Relato não encontrado.')
    if not chave or not hmac.compare_digest(hash_da_chave(chave), relato.chave_hash):
        raise HTTPException(403, 'A chave para apagar este relato está errada ou não foi enviada.')
    repo.apagar(relato_id)
    sessao.commit()
    return Response(status_code=204)
