"""Carga dos arquivos de ``dados/`` no banco, separada por tipo de evidência.

O ``data.json`` vira três conjuntos: a geografia (``conjuntos_referencia``), o dado oficial (``bo`` →
``conjuntos_oficiais`` + ``oficiais_celulas``) e a percepção (``pesq`` → ``conjuntos_percepcao`` +
``percepcao_celulas``). A rede de apoio vai para ``conjuntos_referencia`` + ``pontos_apoio``. O mapa de ruas
(``osm/basemap.json``) não entra no banco: ``GET /mapa/base`` serve o arquivo como está.

É idempotente: cada conjunto guarda o sha256 do arquivo de onde veio, e a carga só refaz o que mudou.
Os títulos, as fontes e os avisos repetem os textos que o legado já mostra.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.database.repositorios import CHAVE_GEOGRAFIA, CHAVE_REDE_APOIO, RepositorioDados, instante_atual_ms
from backend.database.tabelas import (
    CelulaOficial,
    CelulaPercepcao,
    ConjuntoOficial,
    ConjuntoPercepcao,
    ConjuntoReferencia,
    PontoApoio,
)

log = logging.getLogger('aurora.dados')

CHAVE_DADO_OFICIAL = 'bo-ssp-2025-2026'
CHAVE_PERCEPCAO = 'pesquisa-percepcao-2026'

TITULO_GEOGRAFIA = 'Mapa de Rio Claro: células de ~1 km, contorno do município e bairros'
NOTAS_GEOGRAFIA = [
    'A cidade é dividida em hexágonos de cerca de 1 km.',
    'Relatos e dados aparecem por célula, nunca num ponto exato, para proteger quem relata e para não expor endereços.',
    'O contorno do município vem da base da SSP.',
    'Os nomes de bairros no mapa são referências aproximadas.',
]
TITULO_DADO_OFICIAL = 'Boletins de ocorrência (SSP-SP, base R.D.O. via FALASP)'
FONTE_DADO_OFICIAL = 'Base R.D.O. da SSP-SP obtida via FALASP'
TITULO_PERCEPCAO = 'Pesquisa “Segurança e percepção das mulheres em Rio Claro”'
FONTE_PERCEPCAO = 'Formulário “Segurança e percepção das mulheres em Rio Claro”'
TITULO_REDE_APOIO = 'Rede de apoio'

MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']


def _fmt_data(iso) -> str | None:
    """Porte de ``fmtDate`` (``2026-09-10`` → ``10 set 2026``)."""
    try:
        y, m, d = (int(x) for x in str(iso).split('-'))
        return f'{d} {MESES[m - 1]} {y}'
    except (ValueError, IndexError):
        return None


def _avisos_oficiais(bo: dict) -> list[str]:
    avisos = [
        'São contagens por bairro, sem boletins individuais.',
        'A data de registro pode diferir da data do fato.',
        'As coordenadas são centros médios dos boletins de cada bairro.',
    ]
    n = _n(bo.get('total'))
    if n is not None:
        avisos.append(f'{n} é a soma de três contadores e não garante {n} episódios ou pessoas distintas.')
    avisos.append('Não é taxa por população nem medida de risco atual.')
    return avisos


def _avisos_percepcao(pesq: dict) -> list[str]:
    avisos = ['Percepção não é ocorrência.', 'Cada mulher conta uma vez por área.']
    if pesq.get('comRegiao') is not None and pesq.get('mapeadas') is not None:
        avisos.append(f'No mapa, as {pesq["comRegiao"]} respostas sobre regiões inseguras foram ligadas aos bairros '
                      f'da base de B.O.; {pesq["mapeadas"]} citavam lugares localizáveis.')
    return avisos


def _sem_celulas(obj: dict) -> tuple[dict, list[tuple[str, dict]]]:
    # "cells" fica null no lugar, para guardar a posição da chave no objeto original
    celulas = obj.get('cells')
    if not isinstance(celulas, dict):
        return dict(obj), []
    atributos = dict(obj)
    atributos['cells'] = None
    return atributos, list(celulas.items())


def _n(valor) -> int | None:
    n = valor.get('n') if isinstance(valor, dict) else None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def _ler(caminho: Path) -> tuple[bytes, str] | None:
    if not caminho.is_file():
        log.warning('arquivo de dados não encontrado: %s', caminho.name)
        return None
    bruto = caminho.read_bytes()
    return bruto, hashlib.sha256(bruto).hexdigest()


def _carregar_data_json(repo: RepositorioDados, caminho: Path, agora: int) -> str:
    lido = _ler(caminho)
    if lido is None:
        return 'ausente'
    bruto, sha = lido
    atuais = (repo.referencia(CHAVE_GEOGRAFIA), repo.oficial(CHAVE_DADO_OFICIAL), repo.percepcao(CHAVE_PERCEPCAO))
    if all(c is not None and c.sha256_arquivo == sha for c in atuais):
        return 'inalterado'
    d = json.loads(bruto.decode('utf-8'))
    gerado = d.get('gerado')
    geo = {k: v for k, v in d.items() if k not in ('bo', 'pesq')}
    repo.substituir(ConjuntoReferencia(chave=CHAVE_GEOGRAFIA, tipo='geografia', titulo=TITULO_GEOGRAFIA, fonte='dados/data.json',
                                       gerado_em=gerado, notas=list(NOTAS_GEOGRAFIA), dados=geo, sha256_arquivo=sha,
                                       carregado_em=agora))
    bo = d.get('bo')
    if isinstance(bo, dict):
        atributos, celulas = _sem_celulas(bo)
        repo.substituir(ConjuntoOficial(
            chave=CHAVE_DADO_OFICIAL, titulo=TITULO_DADO_OFICIAL, periodo=bo.get('periodo'), fonte=FONTE_DADO_OFICIAL,
            gerado_em=gerado, avisos=_avisos_oficiais(bo), dados=atributos, sha256_arquivo=sha, carregado_em=agora,
            celulas=[CelulaOficial(celula=k, ordem=i, n=_n(v), dados=v) for i, (k, v) in enumerate(celulas)]))
    else:
        repo.remover(ConjuntoOficial, CHAVE_DADO_OFICIAL)
    pesq = d.get('pesq')
    if isinstance(pesq, dict):
        atributos, celulas = _sem_celulas(pesq)
        de, ate = _fmt_data(pesq.get('de')), _fmt_data(pesq.get('ate'))
        repo.substituir(ConjuntoPercepcao(
            chave=CHAVE_PERCEPCAO, titulo=TITULO_PERCEPCAO, periodo=f'{de} a {ate}' if de and ate else None,
            fonte=FONTE_PERCEPCAO, gerado_em=gerado, de=pesq.get('de'), ate=pesq.get('ate'), respostas=_n(pesq),
            avisos=_avisos_percepcao(pesq), dados=atributos, sha256_arquivo=sha, carregado_em=agora,
            celulas=[CelulaPercepcao(celula=k, ordem=i, n=_n(v), dados=v) for i, (k, v) in enumerate(celulas)]))
    else:
        repo.remover(ConjuntoPercepcao, CHAVE_PERCEPCAO)
    return 'carregado'


def _carregar_rede(repo: RepositorioDados, caminho: Path, agora: int) -> str:
    lido = _ler(caminho)
    if lido is None:
        return 'ausente'
    bruto, sha = lido
    atual = repo.referencia(CHAVE_REDE_APOIO)
    if atual is not None and atual.sha256_arquivo == sha:
        return 'inalterado'
    rede = json.loads(bruto.decode('utf-8'))
    atributos = dict(rede)
    pontos = rede.get('pontos')
    if isinstance(pontos, list):
        atributos['pontos'] = None  # só guarda a posição; os pontos ficam em pontos_apoio
    else:
        pontos = []
    nota = rede.get('nota')
    repo.substituir(ConjuntoReferencia(
        chave=CHAVE_REDE_APOIO, tipo='rede_apoio', titulo=TITULO_REDE_APOIO, fonte='dados/rede-de-apoio.json',
        gerado_em=rede.get('atualizado'), notas=[nota] if isinstance(nota, str) else [], dados=atributos,
        sha256_arquivo=sha, carregado_em=agora,
        pontos=[PontoApoio(ordem=i, ponto_id=p.get('id') if isinstance(p, dict) else None,
                           tipo=p.get('tipo') if isinstance(p, dict) else None, dados=p) for i, p in enumerate(pontos)]))
    return 'carregado'


def carregar_dados_iniciais(sessao: Session, pasta_dados: Path) -> dict:
    """Carrega ``data.json`` e ``rede-de-apoio.json`` e confere se ``osm/basemap.json`` existe.

    Devolve ``{"data.json": s, "rede-de-apoio.json": s, "osm/basemap.json": s}``, com ``s`` igual a
    ``"carregado"``, ``"inalterado"`` ou ``"ausente"`` (o mapa de ruas só pode estar ``"presente"`` ou ``"ausente"``).
    """
    pasta = Path(pasta_dados)
    repo = RepositorioDados(sessao)
    agora = instante_atual_ms()
    try:
        resultado = {
            'data.json': _carregar_data_json(repo, pasta / 'data.json', agora),
            'rede-de-apoio.json': _carregar_rede(repo, pasta / 'rede-de-apoio.json', agora),
        }
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    base = pasta / 'osm' / 'basemap.json'
    if not base.is_file():
        log.warning('arquivo de dados não encontrado: osm/%s', base.name)
    resultado['osm/basemap.json'] = 'presente' if base.is_file() else 'ausente'
    return resultado
