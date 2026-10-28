"""Schemas Pydantic dos relatos da comunidade.

``RelatoEntrada`` repete as regras do ``cleanReport`` do legado (src/app.js:257-271): tipos fora do
vocabulário são descartados, ``quando``/``periodo`` desconhecidos viram ``null`` e ``origem`` vira ``"chat"``.
``RelatoPublico`` tem exatamente os campos que o ``cleanReport`` produz, e nada além disso.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from backend.config import obter_configuracoes
from backend.models.comum import texto_bem_formado
from backend.models.vocabulario import PERIODOS_POR_ID, QUANDO, TIPOS_POR_ID
from backend.services.texto import regex_js

CELL_RE = regex_js(r'^f?-?\d{1,4}_-?\d{1,4}$')
TEXTO_MAX_ENTRADA = 2000


class RelatoEntrada(BaseModel):
    """O que o frontend envia. Campos extras (``v``, ``criado``...) são ignorados: a hora é sempre a do servidor."""
    model_config = ConfigDict(extra='ignore')

    tipos: list[str]
    cell: str
    quando: str | None = None
    periodo: str | None = None
    texto: str = ''
    origem: Literal['chat', 'chat-ia'] = 'chat'

    @field_validator('tipos', mode='before')
    @classmethod
    def _tipos(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v  # o Pydantic recusa: não é lista
        # r.tipos.filter(t => TIPO[t]).slice(0, 4) do legado, sem repetir
        validos = list(dict.fromkeys(t for t in v if isinstance(t, str) and t in TIPOS_POR_ID))
        validos = validos[:obter_configuracoes().relatos_tipos_max]
        if not validos:
            raise PydanticCustomError('tipos_invalidos', 'Escolha pelo menos um tipo de situação válido.')
        return validos

    @field_validator('cell')
    @classmethod
    def _cell(cls, v: str) -> str:
        if not CELL_RE.search(v):
            raise PydanticCustomError('celula_invalida', 'Área do mapa inválida.')
        return v

    @field_validator('quando', mode='before')
    @classmethod
    def _quando(cls, v: Any) -> str | None:
        return v if isinstance(v, str) and v in QUANDO else None

    @field_validator('periodo', mode='before')
    @classmethod
    def _periodo(cls, v: Any) -> str | None:
        return v if isinstance(v, str) and v in PERIODOS_POR_ID else None

    @field_validator('texto', mode='before')
    @classmethod
    def _texto(cls, v: Any) -> str:
        if not isinstance(v, str):
            return ''  # como no legado: texto que não é string fica vazio
        if len(v) > TEXTO_MAX_ENTRADA:
            raise PydanticCustomError('texto_longo', 'O texto pode ter no máximo {maximo} caracteres.', {'maximo': TEXTO_MAX_ENTRADA})
        return texto_bem_formado(v)

    @field_validator('origem', mode='before')
    @classmethod
    def _origem(cls, v: Any) -> str:
        return 'chat-ia' if v == 'chat-ia' else 'chat'


class RelatoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipos: list[str]
    cell: str
    quando: str | None
    periodo: str | None
    texto: str
    criado: int
    origem: str


class Anonimizacao(BaseModel):
    removidos: list[str]


class RespostaRelatoCriado(BaseModel):
    relato: RelatoPublico
    chave_exclusao: str
    anonimizacao: Anonimizacao


class RespostaRelato(BaseModel):
    relato: RelatoPublico


class ListaRelatos(BaseModel):
    tipo_evidencia: Literal['relato_comunidade']
    janela_dias: int
    relatos: list[RelatoPublico]
