"""Acesso a dados usado pelas rotas e pelos serviços. As rotas não montam SQL: trocar o banco não muda as rotas."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.database.tabelas import (
    AcaoModeracao,
    Classificacao,
    ConjuntoOficial,
    ConjuntoPercepcao,
    ConjuntoReferencia,
    Relato,
    Voto,
)
from backend.services.classificacao import Bairro, bairros_de_lista

DIA_MS = 86_400_000
CHAVE_GEOGRAFIA = 'geografia-rio-claro'
CHAVE_REDE_APOIO = 'rede-apoio-rio-claro'


def instante_atual_ms() -> int:
    """``Date.now()`` do legado: milissegundos desde 1970."""
    return time.time_ns() // 1_000_000


class RepositorioRelatos:
    def __init__(self, sessao: Session):
        self.sessao = sessao

    def criar(self, *, id: str, tipos: list[str], cell: str, quando: str | None, periodo: str | None, texto: str,
              origem: str, criado: int, chave_hash: str) -> Relato:
        relato = Relato(id=id, tipos=list(tipos), cell=cell, quando=quando, periodo=periodo, texto=texto,
                        origem=origem, criado=criado, chave_hash=chave_hash)
        self.sessao.add(relato)
        self.sessao.flush()
        return relato

    def obter(self, relato_id: str) -> Relato | None:
        return self.sessao.get(Relato, relato_id)

    def listar_desde(self, desde_ms: int) -> list[Relato]:
        """Relatos criados a partir de ``desde_ms``, do mais novo para o mais antigo."""
        # a moderação no servidor ainda não existe: quando existir, os relatos ocultados saem aqui
        consulta = select(Relato).where(Relato.criado >= desde_ms).order_by(Relato.criado.desc(), Relato.id)
        return list(self.sessao.scalars(consulta))

    def apagar(self, relato_id: str) -> bool:
        self._apagar_ligados(Relato.id == relato_id)
        return self.sessao.execute(delete(Relato).where(Relato.id == relato_id)).rowcount > 0

    def apagar_anteriores(self, limite_ms: int) -> int:
        """Apaga os relatos criados antes de ``limite_ms`` e o que está ligado a eles. Devolve quantos relatos apagou."""
        self._apagar_ligados(Relato.criado < limite_ms)
        return self.sessao.execute(delete(Relato).where(Relato.criado < limite_ms)).rowcount

    def _apagar_ligados(self, criterio) -> None:
        # apaga explicitamente, sem depender do ON DELETE CASCADE do banco
        ids = select(Relato.id).where(criterio)
        for tabela in (Classificacao, Voto, AcaoModeracao):
            self.sessao.execute(delete(tabela).where(tabela.relato_id.in_(ids)))

    def contar(self) -> int:
        return self.sessao.scalar(select(func.count()).select_from(Relato))


class RepositorioClassificacoes:
    def __init__(self, sessao: Session):
        self.sessao = sessao

    def criar(self, *, relato_id: str, provedor: str, modelo: str | None, tipos: list[str], urgente: bool,
              quando: str | None, periodo: str | None, confianca: float | None, criado: int) -> Classificacao:
        c = Classificacao(relato_id=relato_id, provedor=provedor, modelo=modelo, tipos=list(tipos), urgente=urgente,
                          quando=quando, periodo=periodo, confianca=confianca, criado=criado)
        self.sessao.add(c)
        self.sessao.flush()
        return c

    def do_relato(self, relato_id: str) -> list[Classificacao]:
        consulta = select(Classificacao).where(Classificacao.relato_id == relato_id).order_by(Classificacao.id)
        return list(self.sessao.scalars(consulta))

    def contar(self) -> int:
        return self.sessao.scalar(select(func.count()).select_from(Classificacao))

    def contar_por_provedor(self) -> dict[str, int]:
        consulta = select(Classificacao.provedor, func.count()).group_by(Classificacao.provedor).order_by(Classificacao.provedor)
        return {provedor: n for provedor, n in self.sessao.execute(consulta)}


class RepositorioDados:
    """Conjuntos carregados de ``dados/`` (ver ``services/processamento_dados.py``)."""

    def __init__(self, sessao: Session):
        self.sessao = sessao

    def referencia(self, chave: str) -> ConjuntoReferencia | None:
        return self.sessao.get(ConjuntoReferencia, chave)

    def oficiais(self) -> list[ConjuntoOficial]:
        return list(self.sessao.scalars(select(ConjuntoOficial).order_by(ConjuntoOficial.chave)))

    def oficial(self, chave: str) -> ConjuntoOficial | None:
        return self.sessao.get(ConjuntoOficial, chave)

    def percepcoes(self) -> list[ConjuntoPercepcao]:
        return list(self.sessao.scalars(select(ConjuntoPercepcao).order_by(ConjuntoPercepcao.chave)))

    def percepcao(self, chave: str) -> ConjuntoPercepcao | None:
        return self.sessao.get(ConjuntoPercepcao, chave)

    def bairros(self) -> list[Bairro]:
        """Os bairros do data.json (``D.bairros``), na ordem original. Lista vazia se a geografia não foi carregada."""
        geo = self.referencia(CHAVE_GEOGRAFIA)
        lista = geo.dados.get('bairros') if geo is not None else None
        return bairros_de_lista(lista) if isinstance(lista, list) else []

    def substituir(self, conjunto: ConjuntoReferencia | ConjuntoOficial | ConjuntoPercepcao) -> None:
        """Troca o conjunto de mesma chave (e as células ou pontos dele) pelo novo."""
        existente = self.sessao.get(type(conjunto), conjunto.chave)
        if existente is not None:
            self.sessao.delete(existente)
            self.sessao.flush()
        self.sessao.add(conjunto)
        self.sessao.flush()

    def remover(self, tipo: type, chave: str) -> None:
        existente = self.sessao.get(tipo, chave)
        if existente is not None:
            self.sessao.delete(existente)
            self.sessao.flush()


def dados_completos(conjunto: ConjuntoReferencia | ConjuntoOficial | ConjuntoPercepcao) -> dict[str, Any]:
    """Remonta o objeto original do arquivo: as células (ou os pontos) voltam para a posição de onde saíram."""
    dados = dict(conjunto.dados)
    if isinstance(conjunto, (ConjuntoOficial, ConjuntoPercepcao)):
        if 'cells' in dados and dados['cells'] is None:
            dados['cells'] = {c.celula: c.dados for c in conjunto.celulas}
    elif conjunto.tipo == 'rede_apoio' and 'pontos' in dados and dados['pontos'] is None:
        dados['pontos'] = [p.dados for p in conjunto.pontos]
    return dados
