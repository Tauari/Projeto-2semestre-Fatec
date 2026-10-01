"""Identidade de quem usa o app. Na fase 1 não existe autenticação: todo mundo é anônimo."""
from __future__ import annotations

from fastapi import APIRouter

from backend.models.comum import Identidade

router = APIRouter(tags=['usuários'])


@router.get('/usuarios/eu', response_model=Identidade)
def eu():
    return {'autenticado': False, 'papeis': []}
