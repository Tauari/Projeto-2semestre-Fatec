from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, field_validator


class AcessoEquipe(BaseModel):
    model_config = ConfigDict(extra='forbid')
    login: str = Field(min_length=3, max_length=64, pattern=r'^[a-z0-9][a-z0-9._-]{2,63}$')
    senha: SecretStr = Field(min_length=1, max_length=128)

    @field_validator('login', mode='before')
    @classmethod
    def normalizar_login(cls, valor):
        return valor.strip().lower() if isinstance(valor, str) else valor


class NovaConta(AcessoEquipe):
    senha: SecretStr = Field(min_length=12, max_length=128)
    papel: Literal['administrador', 'moderacao'] = 'moderacao'


class AtividadeConta(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ativo: StrictBool


class ContaPublica(BaseModel):
    id: str
    login: str
    papel: Literal['administrador', 'moderacao']
    ativo: bool
