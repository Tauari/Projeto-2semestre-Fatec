"""Schemas dos alertas recentes (``GET /alertas``): o que o app de celular precisa para avisar quando a pessoa chega perto.

Só título padrão, área e posição aproximada (o centro da célula de ~150 m). Nada do texto da usuária.
"""
from __future__ import annotations

from pydantic import BaseModel


class AlertaRecente(BaseModel):
    id: str
    tipo: str
    titulo: str
    cell: str
    lat: float
    lng: float
    area: str
    criado: int


class ListaAlertas(BaseModel):
    tipo_evidencia: str
    janela_horas: int
    alertas: list[AlertaRecente]
