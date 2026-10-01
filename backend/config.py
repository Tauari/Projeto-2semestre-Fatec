"""Configurações do servidor, lidas das variáveis de ambiente com o prefixo ``AURORA_``.

Os padrões reproduzem o comportamento atual do app. Onde a regra depende do Observatório, o padrão é
o de hoje e o campo diz "decisão pendente". Listas vêm em JSON (ex.: ``AURORA_CORS_ORIGENS='["http://localhost:8080"]'``).

Nos testes, mude as variáveis de ambiente e chame ``obter_configuracoes.cache_clear()``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[1]


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='AURORA_', env_ignore_empty=True, extra='ignore')

    banco_url: str = 'sqlite:///' + (RAIZ / 'backend' / 'database' / 'aurora.db').as_posix()
    pasta_dados: Path = RAIZ / 'dados'
    pasta_frontend: Path = RAIZ / 'frontend'
    pasta_vendor: Path = RAIZ / 'vendor'
    servir_frontend: bool = True
    cors_origens: list[str] = Field(default_factory=list)
    carga_automatica: bool = True
    relatos_janela_dias: int = Field(30, ge=1, le=3650)
    relatos_tipos_max: int = Field(4, ge=1)
    relatos_texto_max: int = Field(300, ge=0)
    # decisão pendente com o Observatório: None = nenhum relato é apagado por idade
    relatos_retencao_dias: int | None = Field(None, ge=1)
    # decisão pendente: "hora" e "dia" arredondam a hora de envio para baixo (em UTC)
    relatos_precisao_criado: Literal['exata', 'hora', 'dia'] = 'exata'
    # tamanho máximo do corpo de uma requisição (bytes): um relato tem poucos KB; acima disso, 413
    limite_corpo_bytes: int = Field(64 * 1024, ge=1024)
    ia_provedor: str = 'heuristica'
    ia_classificar_ao_criar: bool = True


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
