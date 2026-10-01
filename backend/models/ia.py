"""Schemas Pydantic das rotas de IA (``/ia/provedor`` e ``/ia/extrair``)."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.models.comum import texto_bem_formado


class EntradaExtracao(BaseModel):
    """O texto a analisar. A heurística lê o texto inteiro; provedores com modelo cortam no prompt (1500)."""
    texto: str = Field(min_length=1, max_length=4000)

    @field_validator('texto')
    @classmethod
    def _texto(cls, v: str) -> str:
        return texto_bem_formado(v)


class BairroExtraido(BaseModel):
    nome: str
    lat: float
    lng: float


class ResultadoExtracaoPublico(BaseModel):
    urgente: bool
    tipos: list[str]
    bairro: BairroExtraido | None
    quando: str | None
    periodo: str | None
    descricao: str
    removidos: list[str]
    resposta: str


class RespostaExtracao(BaseModel):
    provedor: str
    usa_modelo: bool
    tipo_evidencia: str
    resultado: ResultadoExtracaoPublico


class InfoProvedor(BaseModel):
    nome: str
    usa_modelo: bool
    modelo: str | None
    capacidades: list[str]
    nao_implementado: list[str]
