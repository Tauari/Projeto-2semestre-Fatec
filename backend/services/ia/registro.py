"""Registro dos provedores de IA disponíveis. Na fase 1 só existe ``heuristica``."""
from __future__ import annotations

from typing import Callable

from backend.services.ia.base import ProvedorIA
from backend.services.ia.heuristico import ProvedorHeuristico

_FABRICAS: dict[str, Callable[[], ProvedorIA]] = {}


def registrar_provedor(nome: str, fabrica: Callable[[], ProvedorIA]) -> None:
    _FABRICAS[nome] = fabrica


def provedores_disponiveis() -> list[str]:
    return list(_FABRICAS)


def obter_provedor(nome: str | None = None) -> ProvedorIA:
    if nome is None:
        try:
            from backend.config import obter_configuracoes
        except ImportError:
            # sem backend/config.py (ainda não criado): fica o padrão
            nome = 'heuristica'
        else:
            nome = obter_configuracoes().ia_provedor
    fabrica = _FABRICAS.get(nome)
    if fabrica is None:
        raise ValueError(f'Provedor de IA desconhecido: {nome!r}. Disponíveis: {", ".join(_FABRICAS) or "nenhum"}.')
    return fabrica()


registrar_provedor('heuristica', ProvedorHeuristico)
registrar_provedor('ollama', lambda: __import__('backend.services.ia.ollama', fromlist=['ProvedorOllama']).ProvedorOllama())
