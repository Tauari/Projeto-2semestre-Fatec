"""Contratos da moderação, sem campos internos ou chaves de exclusão."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from backend.models.equipe import ContaPublica
from backend.models.relatos import RelatoPublico


class AcaoModeracaoEntrada(BaseModel):
    model_config = ConfigDict(extra='forbid')
    campo: Literal['oculto', 'verificado']
    valor: StrictBool


class EstadoModeracao(BaseModel):
    oculto: dict[str, bool] = Field(default_factory=dict)
    verificado: dict[str, bool] = Field(default_factory=dict)


class PainelModeracao(BaseModel):
    usuario: ContaPublica
    relatos: list[RelatoPublico]
    mod: EstadoModeracao


class VerificacoesPublicas(BaseModel):
    verificado: dict[str, bool]
