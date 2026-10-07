"""Gera relatos SINTÉTICOS (fictícios) para popular o banco da Aurora em demonstrações e testes.

Adaptado do notebook "Seguranca_mulher_dados_sinteticos": mesmas categorias, frases e pesos, mas no
formato que a tabela ``relatos`` espera (célula hexagonal em vez de latitude/longitude, tipos e períodos
do vocabulário do projeto, hora em milissegundos). Os pontos são sorteados em volta dos bairros reais de
Rio Claro que estão em ``dados/data.json``.

Uso (na raiz do projeto, com o ambiente virtual):

    python -m scripts.gerar_dados_sinteticos --simular            # só mostra o resumo, não grava nada
    python -m scripts.gerar_dados_sinteticos -n 300 --substituir  # grava 300 relatos (apaga os sintéticos antigos)
    python -m scripts.gerar_dados_sinteticos --so-limpar          # apaga só os relatos sintéticos

Os relatos sintéticos ficam marcados com ``origem = 'sintetico'``. Use um banco separado do real
(``AURORA_BANCO_URL`` ou ``--banco``): relatos fictícios no banco de produção apareceriam no mapa
como se fossem de verdade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import secrets
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:  # permite rodar também como "python scripts/gerar_dados_sinteticos.py"
    sys.path.insert(0, str(RAIZ))

from backend.models.vocabulario import QUANDO, TIPOS_POR_ID, periodo_da_hora  # noqa: E402
from backend.services.anonimizacao import anonimizar_texto  # noqa: E402

ORIGEM = 'sintetico'
FUSO = timezone(timedelta(hours=-3))  # horário de Brasília: é nele que o período do dia faz sentido

# (categoria do notebook, tipo do vocabulário do projeto, peso, frases)
CATEGORIAS = [
    ('rua mal iluminada', 'ambiente', 0.22, ['poste apagado', 'rua muito escura sem iluminação', 'calçada sem luz']),
    ('pessoa suspeita', 'intimidacao', 0.20, ['homem me encarando', 'sujeito estranho parado', 'pessoa me seguindo']),
    ('rua deserta', 'ambiente', 0.15, ['rua vazia e silenciosa', 'sem ninguém passando', 'muito isolado']),
    ('assédio verbal', 'assedio', 0.08, ['homem gritou algo', 'comentários ofensivos', 'assédio na rua']),
    ('seguidor a pé', 'perseguicao', 0.12, ['alguém me seguindo', 'homem andando atrás de mim']),
    ('carro suspeito', 'veiculo', 0.10, ['carro parado na esquina', 'veículo me observando', 'carro rondando']),
    ('ponto de ônibus inseguro', 'ambiente', 0.07, ['ponto escuro e vazio', 'espera de ônibus perigosa']),
    ('terreno abandonado', 'ambiente', 0.06, ['terreno com mato alto', 'prédio abandonado']),
]
# "quando" é o que a usuária diz sobre quando aconteceu; a hora do relato (``criado``) é outra coisa
PESO_QUANDO = {'hoje': 0.55, 'ontem': 0.20, 'semana': 0.15, 'antes': 0.10}

# se o vocabulário do projeto mudar, o script avisa em vez de gravar dados inválidos
assert all(tipo in TIPOS_POR_ID for _, tipo, _, _ in CATEGORIAS), 'tipo fora do vocabulário do projeto'
assert set(PESO_QUANDO) == set(QUANDO), 'valores de "quando" mudaram no projeto'


# ---------------------------------------------------------------- geografia

S3 = math.sqrt(3)
MLAT = 110574  # metros por grau de latitude (mesmo valor de frontend/shared/grade.js)


def _arredondar(v: float) -> int:
    return math.floor(v + 0.5)  # Math.round do JavaScript (arredonda .5 para cima)


def celula_de(lat: float, lng: float, hex_: dict) -> str:
    """Porte de ``cellOf`` (frontend/shared/grade.js): latitude/longitude -> célula hexagonal "q_r"."""
    mlng = 111320 * math.cos(hex_['lat0'] * math.pi / 180)
    x, y = (lng - hex_['lng0']) * mlng, (lat - hex_['lat0']) * MLAT
    q, r = (S3 / 3 * x - y / 3) / hex_['R'], (2 / 3 * y) / hex_['R']
    s = -q - r
    rq, rr, rs = _arredondar(q), _arredondar(r), _arredondar(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return f'{rq}_{rr}'


class Geografia:
    """Lê de ``dados/data.json`` a grade, os bairros (com o peso de cada um) e as células do município."""

    def __init__(self, pasta_dados: Path):
        d = json.loads((pasta_dados / 'data.json').read_text(encoding='utf-8'))
        self.hex = d['hex']
        self.bairros = [(b[1], b[2], max(b[3], 1)) for b in d['bairros']]  # (lat, lng, peso)
        centro = next((b for b in d['bairros'] if b[0] == 'Centro'), None)
        self.centro = (centro[1], centro[2]) if centro else (self.hex['lat0'], self.hex['lng0'])
        self.validas = set(d.get('field') or [])

    def sortear_celula(self, rng: random.Random) -> str:
        """70% dos pontos agrupados em volta de bairros, 30% espalhados pela cidade (como no notebook)."""
        for _ in range(50):
            if rng.random() < 0.7:
                lat0, lng0, _peso = rng.choices(self.bairros, weights=[b[2] for b in self.bairros])[0]
                lat, lng = rng.gauss(lat0, 0.003), rng.gauss(lng0, 0.003)
            else:
                lat, lng = rng.gauss(self.centro[0], 0.02), rng.gauss(self.centro[1], 0.02)
            cell = celula_de(lat, lng, self.hex)
            if not self.validas or cell in self.validas:
                return cell
        raise RuntimeError('Não consegui sortear uma célula dentro do município; confira dados/data.json.')


# ---------------------------------------------------------------- geração

def gerar_relatos(n: int, dias: int, seed: int, geo: Geografia, agora_ms: int) -> list[dict]:
    """Devolve ``n`` relatos prontos para gravar. Mesma ``seed`` e mesmo ``agora_ms`` dão o mesmo resultado."""
    rng = random.Random(seed)
    pesos = [c[2] for c in CATEGORIAS]
    chaves_quando, pesos_quando = list(PESO_QUANDO), list(PESO_QUANDO.values())
    relatos = []
    for _ in range(n):
        _nome, tipo, _peso, frases = rng.choices(CATEGORIAS, weights=pesos)[0]
        criado = agora_ms - rng.randrange(0, dias * 24 * 60) * 60_000
        hora = datetime.fromtimestamp(criado / 1000, FUSO).hour
        texto = anonimizar_texto(rng.choice(frases)).texto  # passa pela mesma limpeza dos relatos reais
        relatos.append({
            'tipos': [tipo],
            'cell': geo.sortear_celula(rng),
            'quando': rng.choices(chaves_quando, weights=pesos_quando)[0],
            'periodo': periodo_da_hora(hora),
            'texto': texto,
            'criado': criado,
        })
    return relatos


def resumo(relatos: list[dict]) -> str:
    def linhas(titulo, contador):
        itens = ', '.join(f'{k}: {v}' for k, v in contador.most_common())
        return f'  {titulo}: {itens}'

    celulas = Counter(r['cell'] for r in relatos)
    mais_cheias = ', '.join(f'{c} ({v})' for c, v in celulas.most_common(5))
    return '\n'.join([
        f'{len(relatos)} relato(s) sintético(s) em {len(celulas)} célula(s) diferente(s).',
        linhas('tipos', Counter(t for r in relatos for t in r['tipos'])),
        linhas('períodos', Counter(r['periodo'] for r in relatos)),
        linhas('quando', Counter(r['quando'] for r in relatos)),
        f'  células mais cheias: {mais_cheias}',
    ])


# ---------------------------------------------------------------- banco

def gravar(relatos: list[dict], *, banco_url: str | None, classificar: bool, substituir: bool,
           so_limpar: bool, forcar: bool) -> None:
    # imports aqui dentro: gerar e simular não precisam do SQLAlchemy
    from sqlalchemy import func, select

    from backend.config import obter_configuracoes
    from backend.database import sessao as banco
    from backend.database.repositorios import RepositorioClassificacoes, RepositorioDados, RepositorioRelatos
    from backend.database.tabelas import Relato

    cfg = obter_configuracoes()
    motor = banco.configurar_banco(banco_url)  # None = o banco configurado (AURORA_BANCO_URL ou aurora.db)
    banco.criar_tabelas(motor)
    print('Banco:', motor.url.render_as_string(hide_password=True))

    with banco.SessionLocal() as sessao:
        repo = RepositorioRelatos(sessao)

        if substituir or so_limpar:
            ids = list(sessao.scalars(select(Relato.id).where(Relato.origem == ORIGEM)))
            for relato_id in ids:
                repo.apagar(relato_id)
            sessao.commit()
            print(f'{len(ids)} relato(s) sintético(s) anterior(es) apagado(s).')
        if so_limpar:
            return

        reais = sessao.scalar(select(func.count()).select_from(Relato).where(Relato.origem != ORIGEM))
        if reais and not forcar:
            sys.exit(f'Este banco já tem {reais} relato(s) reais. Para não misturar dados fictícios com os reais, '
                     'use um banco separado (AURORA_BANCO_URL ou --banco) ou confirme com --forcar.')

        provedor = contexto = None
        if classificar:
            from backend.services.ia import ContextoIA, obter_provedor
            provedor = obter_provedor(cfg.ia_provedor)
            contexto = ContextoIA(bairros=RepositorioDados(sessao).bairros())

        for r in relatos:
            chave_hash = hashlib.sha256(secrets.token_urlsafe(24).encode('utf-8')).hexdigest()  # a chave é descartada
            relato = repo.criar(id=uuid4().hex, tipos=r['tipos'], cell=r['cell'], quando=r['quando'],
                                periodo=r['periodo'], texto=r['texto'], origem=ORIGEM, criado=r['criado'],
                                chave_hash=chave_hash)
            if provedor is not None:
                c = provedor.classificar(r['texto'], contexto)
                RepositorioClassificacoes(sessao).criar(
                    relato_id=relato.id, provedor=provedor.nome, modelo=provedor.modelo, tipos=list(c.tipos),
                    urgente=bool(c.urgente), quando=c.quando, periodo=c.periodo, confianca=c.confianca,
                    criado=relato.criado)
        sessao.commit()
        print(f'{len(relatos)} relato(s) sintético(s) gravado(s).')


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description='Gera relatos sintéticos para o banco da Aurora.')
    p.add_argument('-n', type=int, default=300, help='quantos relatos gerar (padrão: 300)')
    p.add_argument('--dias', type=int, default=30,
                   help='espalha os relatos pelos últimos N dias (padrão: 30, a janela do mapa)')
    p.add_argument('--seed', type=int, default=42, help='semente do sorteio (padrão: 42)')
    p.add_argument('--banco', default=None, help='URL do banco (padrão: AURORA_BANCO_URL ou backend/database/aurora.db)')
    p.add_argument('--simular', action='store_true', help='só mostra o resumo, sem gravar no banco')
    p.add_argument('--substituir', action='store_true', help='apaga os relatos sintéticos anteriores antes de gravar')
    p.add_argument('--so-limpar', action='store_true', help='apaga os relatos sintéticos e termina')
    p.add_argument('--sem-classificacao', action='store_true', help='não preenche a tabela de classificação automática')
    p.add_argument('--forcar', action='store_true', help='grava mesmo que o banco já tenha relatos reais')
    a = p.parse_args(argv)
    if a.n < 1 or a.dias < 1:
        p.error('-n e --dias precisam ser maiores que zero.')

    if a.so_limpar and not a.simular:
        gravar([], banco_url=a.banco, classificar=False, substituir=False, so_limpar=True, forcar=True)
        return

    geo = Geografia(RAIZ / 'dados')
    agora_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    relatos = gerar_relatos(a.n, a.dias, a.seed, geo, agora_ms)
    print(resumo(relatos))
    if a.simular:
        print('Simulação: nada foi gravado.')
        return
    gravar(relatos, banco_url=a.banco, classificar=not a.sem_classificacao, substituir=a.substituir,
           so_limpar=False, forcar=a.forcar)


if __name__ == '__main__':
    main()
