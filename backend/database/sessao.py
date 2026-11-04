"""Conexão com o banco: ``engine``, ``SessionLocal``, ``obter_sessao()`` e ``criar_tabelas()``.

A URL vem de ``banco_url`` (``AURORA_BANCO_URL``). Trocar SQLite por Postgres muda só a URL.
``engine`` fica ``None`` até ``configurar_banco()``, que o ``create_app()`` chama; o ``SessionLocal`` é
o mesmo objeto o tempo todo e passa a usar o engine configurado.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import obter_configuracoes
from backend.database.tabelas import Base

engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)
_url_atual: str | None = None


def normalizar_url(url: str) -> str:
    """As hospedagens de Postgres entregam ``postgres://`` ou ``postgresql://``; o SQLAlchemy precisa do driver no nome."""
    for prefixo in ('postgres://', 'postgresql://'):
        if url.startswith(prefixo):
            return 'postgresql+psycopg://' + url[len(prefixo):]
    return url


def criar_motor(url: str) -> Engine:
    url = normalizar_url(url)
    u = make_url(url)
    # hide_parameters: os valores (ex.: o texto de um relato) não aparecem em mensagens de erro nem em log de SQL
    if u.get_backend_name() != 'sqlite':
        # banco na nuvem: o pre_ping troca a conexão que o provedor derrubou (ex.: Postgres que "dorme" sem uso); o recycle evita conexão velha
        opcoes_pg: dict = {'pool_pre_ping': True, 'pool_recycle': 300, 'hide_parameters': True}
        if url.startswith('postgresql+psycopg://'):
            # sem comandos "preparados" no servidor: funciona também atrás do pooler (pgbouncer) que alguns provedores põem na frente
            opcoes_pg['connect_args'] = {'prepare_threshold': None}
        return create_engine(url, **opcoes_pg)
    opcoes: dict = {'connect_args': {'check_same_thread': False}, 'hide_parameters': True}
    if not u.database or u.database == ':memory:':
        opcoes['poolclass'] = StaticPool  # banco em memória: uma conexão só, vista por todas as threads
    else:
        Path(u.database).parent.mkdir(parents=True, exist_ok=True)
    motor = create_engine(url, **opcoes)

    @event.listens_for(motor, 'connect')
    def _ligar_chaves_estrangeiras(conexao, _registro):
        # o SQLite só respeita ON DELETE CASCADE com esta opção ligada
        cursor = conexao.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        # relato apagado (pela usuária ou pela retenção) não fica recuperável nas páginas livres do arquivo
        cursor.execute('PRAGMA secure_delete=ON')
        cursor.close()

    return motor


def configurar_banco(url: str | None = None) -> Engine:
    """Cria o ``engine`` para a URL (padrão: ``banco_url``) e liga o ``SessionLocal`` a ele."""
    global engine, _url_atual
    url = normalizar_url(url or obter_configuracoes().banco_url)
    if engine is not None and url == _url_atual:
        return engine
    if engine is not None:
        engine.dispose()
    engine = criar_motor(url)
    _url_atual = url
    SessionLocal.configure(bind=engine)
    return engine


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with SessionLocal() as sessao:
        yield sessao


def criar_tabelas(motor: Engine | None = None) -> None:
    Base.metadata.create_all(motor or engine or configurar_banco())
