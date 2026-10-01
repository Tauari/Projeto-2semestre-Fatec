"""Moderação: só a estrutura. Na fase 1 ela continua local, no aparelho (ver frontend/moderacao)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.comum import Erro

router = APIRouter(tags=['moderação'])

MENSAGEM = 'A moderação ainda não foi migrada para o servidor. Nesta fase ela continua local, no aparelho.'


def moderacao():
    raise HTTPException(501, MENSAGEM)


for _metodo in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
    router.add_api_route('/moderacao', moderacao, methods=[_metodo], status_code=501, responses={501: {'model': Erro}},
                         operation_id='moderacao_' + _metodo.lower())
