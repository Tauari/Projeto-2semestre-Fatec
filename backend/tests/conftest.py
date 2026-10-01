"""Fixtures dos testes da API: banco SQLite temporário por teste, configurações sobrescritas e TestClient.

Os testes nunca usam o banco de ``backend/database/aurora.db``: cada teste que cria o app ganha um banco
novo em ``tmp_path``. Para mudar uma configuração, use ``configurar(nome=valor)`` (vira ``AURORA_NOME``)
ou ``criar_cliente(nome=valor)``, antes de criar o app.
"""
from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest

from backend.config import obter_configuracoes

API = '/api/v1'


@pytest.fixture(autouse=True)
def _ambiente_isolado(monkeypatch):
    """Nenhuma variável ``AURORA_*`` de quem roda os testes vaza para eles."""
    for nome in list(os.environ):
        if nome.upper().startswith('AURORA_'):
            monkeypatch.delenv(nome)
    obter_configuracoes.cache_clear()
    yield
    obter_configuracoes.cache_clear()


def _valor_env(v) -> str:
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return str(v)


@pytest.fixture
def configurar(monkeypatch, tmp_path):
    """Sobrescreve configurações. O banco fica sempre num arquivo novo em ``tmp_path``."""
    monkeypatch.setenv('AURORA_BANCO_URL', 'sqlite:///' + (tmp_path / 'aurora-teste.db').as_posix())
    obter_configuracoes.cache_clear()

    def _configurar(**valores):
        for nome, valor in valores.items():
            if valor is None:
                monkeypatch.delenv('AURORA_' + nome.upper(), raising=False)
            else:
                monkeypatch.setenv('AURORA_' + nome.upper(), _valor_env(valor))
        obter_configuracoes.cache_clear()
        return obter_configuracoes()

    return _configurar


@pytest.fixture
def criar_cliente(configurar):
    """Cria o app com as configurações dadas e abre um TestClient (roda a inicialização: tabelas, carga, retenção)."""
    from fastapi.testclient import TestClient

    from backend.database import sessao as banco
    from backend.main import create_app

    abertos = []

    def _criar(**valores):
        configurar(**valores)
        cliente = TestClient(create_app())
        cliente.__enter__()
        abertos.append(cliente)
        return cliente

    yield _criar
    for cliente in reversed(abertos):
        cliente.__exit__(None, None, None)
    if banco.engine is not None:
        banco.engine.dispose()


@pytest.fixture
def cliente(criar_cliente):
    return criar_cliente()


@pytest.fixture
def sessao(cliente):
    """Sessão no mesmo banco do ``cliente``, para conferir e preparar dados direto pelos repositórios."""
    from backend.database.sessao import SessionLocal

    with SessionLocal() as s:
        yield s


@pytest.fixture
def publicar(cliente):
    """Publica um relato pela API (``POST /relatos``) e devolve o JSON da resposta."""
    def _publicar(**campos):
        corpo = {'tipos': ['assedio'], 'cell': '0_0', 'quando': 'hoje', 'periodo': '20-22', 'texto': '', 'origem': 'chat'}
        corpo.update(campos)
        r = cliente.post(API + '/relatos', json=corpo)
        assert r.status_code == 201, r.text
        return r.json()

    return _publicar


@pytest.fixture
def inserir_relato(sessao):
    """Grava um relato direto pelo repositório (ex.: com data antiga), sem passar pela API."""
    from backend.database.repositorios import RepositorioRelatos
    from backend.routes.relatos import hash_da_chave

    def _inserir(criado: int, chave: str = 'chave-de-teste', **campos):
        dados = dict(id=uuid4().hex, tipos=['roubo'], cell='1_0', quando=None, periodo=None, texto='', origem='chat',
                     criado=criado, chave_hash=hash_da_chave(chave))
        dados.update(campos)
        relato = RepositorioRelatos(sessao).criar(**dados)
        sessao.commit()
        return relato

    return _inserir


@pytest.fixture
def contar_linhas():
    """Quantas linhas tem cada tabela do banco."""
    from sqlalchemy import func, select

    from backend.database.tabelas import Base

    def _contar(s) -> dict[str, int]:
        return {t.name: s.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}

    return _contar
