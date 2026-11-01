"""Aparelhos que querem notificação no celular (Expo Push).

O app instalado manda o token dele e as áreas que a pessoa acompanha; o servidor guarda só isso (sem IP, nome ou
ligação com relatos) e avisa quando um relato novo cai numa dessas áreas (``services/push.py``).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session

from backend.database.repositorios import RepositorioPush
from backend.database.sessao import obter_sessao
from backend.models.comum import Erro, ErroValidacao
from backend.models.relatos import CELL_RE

router = APIRouter(tags=['push'])

TOKEN_RE = re.compile(r'^Expo(nent)?PushToken\[[A-Za-z0-9_-]{8,80}\]$')
AREAS_MAX = 40  # o mesmo limite que o frontend guarda em "áreas que acompanho"


class DispositivoEntrada(BaseModel):
    model_config = ConfigDict(extra='ignore')

    token: str
    areas: list[str] = []

    @field_validator('token')
    @classmethod
    def _token(cls, v: str) -> str:
        if not TOKEN_RE.match(v):
            raise PydanticCustomError('token_invalido', 'Token de notificação inválido.')
        return v

    @field_validator('areas')
    @classmethod
    def _areas(cls, v: list[str]) -> list[str]:
        if any(not CELL_RE.search(a) for a in v):
            raise PydanticCustomError('celula_invalida', 'Área do mapa inválida.')
        return list(dict.fromkeys(v))[:AREAS_MAX]


@router.post('/push/dispositivos', status_code=204, response_class=Response, responses={422: {'model': ErroValidacao}})
def registrar(entrada: DispositivoEntrada, sessao: Session = Depends(obter_sessao)):
    """Cadastra o aparelho ou troca as áreas dele. Sem áreas, o aparelho fica sem receber nada."""
    RepositorioPush(sessao).registrar(entrada.token, entrada.areas)
    sessao.commit()
    return Response(status_code=204)


@router.delete('/push/dispositivos', status_code=204, response_class=Response, responses={404: {'model': Erro}})
def remover(token: str | None = Header(None, alias='X-Push-Token'), sessao: Session = Depends(obter_sessao)):
    """Para de notificar o aparelho (o token vai no cabeçalho, não na URL)."""
    if not token or not RepositorioPush(sessao).remover(token):
        raise HTTPException(404, 'Aparelho não encontrado.')
    sessao.commit()
    return Response(status_code=204)
