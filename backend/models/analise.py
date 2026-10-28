"""Schemas Pydantic de ``GET /analise/padroes``."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Evidencia(BaseModel):
    n: int
    de: int
    pct: int


class Padrao(BaseModel):
    id: str
    fonte: str
    dimensoes: list[Literal['regiao', 'periodo', 'tipo']]
    titulo: str
    descricao: str
    evidencia: Evidencia
    confianca: Literal['baixa', 'media', 'alta']
    areas: list[str]


class Fonte(BaseModel):
    id: str
    titulo: str
    total: int
    situacao: Literal['ok', 'insuficiente']


class Insuficiente(BaseModel):
    fonte: str
    dimensao: Literal['regiao', 'periodo', 'tipo']
    motivo: str


class AnalisePadroes(BaseModel):
    tipo_evidencia: str
    provedor: str
    usa_modelo: bool
    resumo: str
    janela_dias: int
    fontes: list[Fonte]
    padroes: list[Padrao]
    insuficiente: list[Insuficiente]
    avisos: list[str]
