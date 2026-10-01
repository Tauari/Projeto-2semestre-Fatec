"""Tabelas do banco (SQLAlchemy 2, estilo ``Mapped[...]``), separadas por tipo de evidência.

- relato_comunidade: ``relatos``; classificacao_automatica: ``classificacoes`` (separada do relato);
- dado_oficial: ``conjuntos_oficiais`` + ``oficiais_celulas``;
- percepcao: ``conjuntos_percepcao`` + ``percepcao_celulas``;
- referência: ``conjuntos_referencia`` (geografia e metadados da rede de apoio) + ``pontos_apoio``.

``votos``, ``moderacao_acoes``, ``usuarios`` e ``analises_ia`` são estruturas preparadas, sem rota na fase 1.
Nenhuma tabela guarda IP, nome, e-mail ou o texto original de um relato.

As tabelas ``*_celulas`` e ``pontos_apoio`` têm ``ordem`` para o servidor devolver os objetos na ordem dos
arquivos de ``dados/``. No ``dados`` do conjunto, a chave ``cells`` (ou ``pontos``) fica com ``null``, só para
guardar a posição dela no objeto original.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Relato(Base):
    """Relato da comunidade, já anonimizado: os mesmos campos que o ``cleanReport`` do legado produz.

    Guarda só o hash (sha256) da chave de exclusão, nunca a chave.
    """
    __tablename__ = 'relatos'

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tipos: Mapped[list[str]] = mapped_column(JSON)
    cell: Mapped[str] = mapped_column(String(16))
    quando: Mapped[str | None] = mapped_column(String(16))
    periodo: Mapped[str | None] = mapped_column(String(16))
    texto: Mapped[str] = mapped_column(Text, default='')
    criado: Mapped[int] = mapped_column(BigInteger, index=True)  # ms desde 1970, como o Date.now() do legado
    origem: Mapped[str] = mapped_column(String(16))
    chave_hash: Mapped[str] = mapped_column(String(64))


class Classificacao(Base):
    """Classificação automática de um relato (tipo de evidência classificacao_automatica).

    Fica separada: os tipos do relato continuam sendo os que a usuária escolheu.
    """
    __tablename__ = 'classificacoes'

    id: Mapped[int] = mapped_column(primary_key=True)
    relato_id: Mapped[str] = mapped_column(ForeignKey('relatos.id', ondelete='CASCADE'), index=True)
    provedor: Mapped[str] = mapped_column(String(64))
    modelo: Mapped[str | None] = mapped_column(String(128))
    tipos: Mapped[list[str]] = mapped_column(JSON)
    urgente: Mapped[bool]
    quando: Mapped[str | None] = mapped_column(String(16))
    periodo: Mapped[str | None] = mapped_column(String(16))
    confianca: Mapped[float | None]
    criado: Mapped[int] = mapped_column(BigInteger)  # o mesmo do relato, para não revelar a hora exata


class ConjuntoReferencia(Base):
    """Dados de referência: a geografia do mapa (``tipo='geografia'``) e a rede de apoio (``tipo='rede_apoio'``)."""
    __tablename__ = 'conjuntos_referencia'

    chave: Mapped[str] = mapped_column(String(64), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(32))
    titulo: Mapped[str] = mapped_column(String(200))
    fonte: Mapped[str] = mapped_column(String(300))
    gerado_em: Mapped[str | None] = mapped_column(String(32))
    notas: Mapped[list[str]] = mapped_column(JSON)
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)
    sha256_arquivo: Mapped[str] = mapped_column(String(64))
    carregado_em: Mapped[int] = mapped_column(BigInteger)

    pontos: Mapped[list[PontoApoio]] = relationship(order_by='PontoApoio.ordem', cascade='all, delete-orphan')


class PontoApoio(Base):
    """Um ponto da rede de apoio (endereço público de serviço), na ordem do rede-de-apoio.json."""
    __tablename__ = 'pontos_apoio'
    __table_args__ = (UniqueConstraint('conjunto_chave', 'ordem'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conjunto_chave: Mapped[str] = mapped_column(ForeignKey('conjuntos_referencia.chave', ondelete='CASCADE'), index=True)
    ordem: Mapped[int]
    ponto_id: Mapped[str | None] = mapped_column(String(64))
    tipo: Mapped[str | None] = mapped_column(String(32))
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)


class ConjuntoOficial(Base):
    """Conjunto de dados oficiais (tipo de evidência dado_oficial), ex.: os B.O. da SSP-SP."""
    __tablename__ = 'conjuntos_oficiais'

    chave: Mapped[str] = mapped_column(String(64), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    periodo: Mapped[str | None] = mapped_column(String(100))
    fonte: Mapped[str] = mapped_column(String(300))
    gerado_em: Mapped[str | None] = mapped_column(String(32))
    avisos: Mapped[list[str]] = mapped_column(JSON)
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)
    sha256_arquivo: Mapped[str] = mapped_column(String(64))
    carregado_em: Mapped[int] = mapped_column(BigInteger)

    celulas: Mapped[list[CelulaOficial]] = relationship(order_by='CelulaOficial.ordem', cascade='all, delete-orphan')


class CelulaOficial(Base):
    """Contagens oficiais de uma célula de ~1 km."""
    __tablename__ = 'oficiais_celulas'
    __table_args__ = (UniqueConstraint('conjunto_chave', 'celula'), UniqueConstraint('conjunto_chave', 'ordem'))

    id: Mapped[int] = mapped_column(primary_key=True)
    conjunto_chave: Mapped[str] = mapped_column(ForeignKey('conjuntos_oficiais.chave', ondelete='CASCADE'), index=True)
    celula: Mapped[str] = mapped_column(String(16))
    ordem: Mapped[int]
    n: Mapped[int | None]
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)


class ConjuntoPercepcao(Base):
    """Conjunto de percepção (tipo de evidência percepcao), ex.: a pesquisa com mulheres de Rio Claro."""
    __tablename__ = 'conjuntos_percepcao'

    chave: Mapped[str] = mapped_column(String(64), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    periodo: Mapped[str | None] = mapped_column(String(100))
    fonte: Mapped[str] = mapped_column(String(300))
    gerado_em: Mapped[str | None] = mapped_column(String(32))
    de: Mapped[str | None] = mapped_column(String(32))
    ate: Mapped[str | None] = mapped_column(String(32))
    respostas: Mapped[int | None]
    avisos: Mapped[list[str]] = mapped_column(JSON)
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)
    sha256_arquivo: Mapped[str] = mapped_column(String(64))
    carregado_em: Mapped[int] = mapped_column(BigInteger)

    celulas: Mapped[list[CelulaPercepcao]] = relationship(order_by='CelulaPercepcao.ordem', cascade='all, delete-orphan')


class CelulaPercepcao(Base):
    """Quantas mulheres da pesquisa citaram a célula, e em que horário."""
    __tablename__ = 'percepcao_celulas'
    __table_args__ = (UniqueConstraint('conjunto_chave', 'celula'), UniqueConstraint('conjunto_chave', 'ordem'))

    id: Mapped[int] = mapped_column(primary_key=True)
    conjunto_chave: Mapped[str] = mapped_column(ForeignKey('conjuntos_percepcao.chave', ondelete='CASCADE'), index=True)
    celula: Mapped[str] = mapped_column(String(16))
    ordem: Mapped[int]
    n: Mapped[int | None]
    dados: Mapped[dict[str, Any]] = mapped_column(JSON)


class Usuario(Base):
    """Estrutura preparada, sem rota na fase 1 (não existe autenticação).

    Sem nome e sem e-mail: só um id, o papel (ex.: moderacao) e, se um dia houver login externo, o
    identificador opaco que esse serviço devolver.
    """
    __tablename__ = 'usuarios'

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    papel: Mapped[str] = mapped_column(String(32))
    identificador_externo: Mapped[str | None] = mapped_column(String(255), unique=True)
    criado_em: Mapped[int] = mapped_column(BigInteger)
    ativo: Mapped[bool] = mapped_column(default=True)


class Voto(Base):
    """Estrutura preparada, sem rota na fase 1: as confirmações continuam no aparelho.

    ``valor`` segue o legado: ``c`` (ainda acontece), ``p`` (não acontece mais), ``f`` (informação falsa).
    Como contar um voto por pessoa sem identificar ninguém é decisão pendente.
    """
    __tablename__ = 'votos'

    id: Mapped[int] = mapped_column(primary_key=True)
    relato_id: Mapped[str] = mapped_column(ForeignKey('relatos.id', ondelete='CASCADE'), index=True)
    usuario_id: Mapped[str | None] = mapped_column(ForeignKey('usuarios.id', ondelete='SET NULL'))
    valor: Mapped[str] = mapped_column(String(1))
    criado_em: Mapped[int] = mapped_column(BigInteger)


class AcaoModeracao(Base):
    """Estrutura preparada, sem rota na fase 1: a moderação continua local, no aparelho.

    ``acao`` segue o legado (ocultar ou verificar um relato, e desfazer).
    """
    __tablename__ = 'moderacao_acoes'

    id: Mapped[int] = mapped_column(primary_key=True)
    relato_id: Mapped[str] = mapped_column(ForeignKey('relatos.id', ondelete='CASCADE'), index=True)
    usuario_id: Mapped[str | None] = mapped_column(ForeignKey('usuarios.id', ondelete='SET NULL'))
    acao: Mapped[str] = mapped_column(String(32))
    criado_em: Mapped[int] = mapped_column(BigInteger)


class AnaliseIA(Base):
    """Estrutura preparada, sem rota na fase 1 (tipo de evidência analise_ia).

    Análises agregadas por IA dependem do Observatório; nada grava aqui ainda.
    """
    __tablename__ = 'analises_ia'

    id: Mapped[int] = mapped_column(primary_key=True)
    provedor: Mapped[str] = mapped_column(String(64))
    modelo: Mapped[str | None] = mapped_column(String(128))
    capacidade: Mapped[str] = mapped_column(String(64))
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON)
    resultado: Mapped[dict[str, Any]] = mapped_column(JSON)
    criado_em: Mapped[int] = mapped_column(BigInteger)
