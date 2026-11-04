"""Postgres na nuvem: a URL que a hospedagem entrega é aceita e as tabelas valem para o dialeto do Postgres.

Estes testes não precisam de um Postgres rodando. A conferência com um banco de verdade fica para a hospedagem
(``AURORA_BANCO_URL``); o teste do motor só roda onde o driver ``psycopg`` está instalado.
"""
from __future__ import annotations

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.database.sessao import criar_motor, normalizar_url
from backend.database.tabelas import Base


@pytest.mark.parametrize('url, esperado', [
    ('postgres://u:p@host:5432/db', 'postgresql+psycopg://u:p@host:5432/db'),
    ('postgresql://u:p@host/db?sslmode=require', 'postgresql+psycopg://u:p@host/db?sslmode=require'),
    ('postgresql+psycopg://u:p@host/db', 'postgresql+psycopg://u:p@host/db'),
    ('sqlite:///backend/database/aurora.db', 'sqlite:///backend/database/aurora.db'),
])
def test_normalizar_url(url, esperado):
    assert normalizar_url(url) == esperado


def test_as_13_tabelas_compilam_para_postgres():
    tabelas = Base.metadata.sorted_tables
    assert len(tabelas) == 13
    for t in tabelas:
        ddl = str(CreateTable(t).compile(dialect=postgresql.dialect()))
        assert t.name in ddl


def test_tipos_no_postgres():
    ddl = str(CreateTable(Base.metadata.tables['relatos']).compile(dialect=postgresql.dialect()))
    assert 'JSON' in ddl  # tipos e células
    assert 'BIGINT' in ddl  # a hora de envio, em milissegundos, não cabe em 32 bits
    assert 'VARCHAR(32)' in ddl


def test_motor_do_postgres_confere_a_conexao_antes_de_usar():
    pytest.importorskip('psycopg')
    motor = criar_motor('postgres://u:p@localhost:5432/aurora')
    try:
        assert motor.dialect.name == 'postgresql'
        assert motor.pool._pre_ping is True  # Postgres que dorme derruba a conexão: troca antes de usar
    finally:
        motor.dispose()
