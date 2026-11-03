"""Configurações do servidor, lidas das variáveis de ambiente com o prefixo ``AURORA_`` e do arquivo ``.env`` na raiz
(fora do git; veja ``.env.example``). A variável de ambiente vale mais que o ``.env``.

Os padrões reproduzem o comportamento atual do app. Onde a regra depende do Observatório, o padrão é
o de hoje e o campo diz "decisão pendente". Listas vêm em JSON (ex.: ``AURORA_CORS_ORIGENS='["http://localhost:8080"]'``).

Nos testes, mude as variáveis de ambiente e chame ``obter_configuracoes.cache_clear()``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_ENV: Path | None = RAIZ / '.env'  # os testes põem None, para um .env local não vazar para eles


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
    ia_modelo: str = 'qwen2.5:3b'
    ia_ollama_url: str = 'http://localhost:11434'
    ia_timeout_s: float = Field(60.0, gt=0)
    ia_classificar_ao_criar: bool = True
    # provedor "groq": o texto sai da máquina rumo à API do Groq, só depois da limpeza por regras (telefone, placa,
    # número de casa, e-mail, documento, perfil e nome dito como "se chama X"; outros nomes podem passar)
    groq_api_key: SecretStr | None = None
    groq_modelo: str = 'openai/gpt-oss-120b'
    groq_url: str = 'https://api.groq.com/openai/v1'
    # notificação no celular (Expo Push): quem acompanha uma área recebe o alerta de um relato novo nela
    push_ativo: bool = True
    push_url: str = 'https://exp.host/--/api/v2/push/send'
    push_intervalo_min: int = Field(10, ge=0)  # no máximo uma notificação por aparelho a cada tanto tempo
    push_timeout_s: float = Field(10.0, gt=0)


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes(_env_file=ARQUIVO_ENV)
