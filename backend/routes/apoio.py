"""Rede de apoio: onde pedir ajuda (endereços públicos de serviços)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.repositorios import CHAVE_REDE_APOIO, RepositorioDados, dados_completos
from backend.database.sessao import obter_sessao
from backend.models.comum import Erro, RedeApoio

router = APIRouter(tags=['apoio'])


def _texto(v) -> str | None:
    return v if isinstance(v, str) else None


@router.get('/apoio', response_model=RedeApoio, responses={404: {'model': Erro}})
def apoio(sessao: Session = Depends(obter_sessao)):
    rede = RepositorioDados(sessao).referencia(CHAVE_REDE_APOIO)
    if rede is None:
        raise HTTPException(404, 'A rede de apoio ainda não foi carregada.')
    dados = dados_completos(rede)
    return {'tipo': 'rede_apoio', 'atualizado': _texto(dados.get('atualizado')), 'nota': _texto(dados.get('nota')), 'dados': dados}
