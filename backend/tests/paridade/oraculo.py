"""Cliente do oráculo Node (oraculo.mjs), que executa as funções originais de src/app.js."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).with_name('oraculo.mjs')
RAIZ = Path(__file__).resolve().parents[3]


def caminho_node() -> str | None:
    return shutil.which('node')


def exigir_node() -> str:
    node = caminho_node()
    if not node:
        pytest.skip('Node.js não encontrado: testes de paridade com o src/app.js pulados.')
    return node


def consultar(pedidos: list[dict]) -> list:
    """Manda uma lista de ``{fn, args, bairros?}`` e devolve os resultados na mesma ordem."""
    node = exigir_node()
    entrada = json.dumps(pedidos, ensure_ascii=True).encode('ascii')
    proc = subprocess.run([node, str(ARQUIVO)], input=entrada, capture_output=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError('o oráculo falhou:\n' + proc.stderr.decode('utf-8', 'replace'))
    saida = json.loads(proc.stdout.decode('utf-8'))
    assert len(saida) == len(pedidos)
    for p, r in zip(pedidos, saida):
        if 'erro' in r:
            raise RuntimeError(f'o oráculo falhou em {p["fn"]}: {r["erro"]}')
    return [r.get('ok') for r in saida]


def chamar(fn: str, *args, bairros=None):
    return mapear(fn, [args], bairros=bairros)[0]


def mapear(fn: str, lista_args, bairros=None) -> list:
    pedidos = []
    for args in lista_args:
        p = {'fn': fn, 'args': list(args)}
        if bairros is not None:
            p['bairros'] = bairros
        pedidos.append(p)
    return consultar(pedidos)


def comparar(entradas, obtidos, esperados, rotulo: str, limite: int = 12) -> None:
    """Falha listando as primeiras divergências entre o Python (obtidos) e o legado (esperados)."""
    assert len(obtidos) == len(esperados) == len(entradas)
    difs = [(e, o, x) for e, o, x in zip(entradas, obtidos, esperados) if o != x]
    if difs:
        linhas = [f'{rotulo}: {len(difs)} de {len(entradas)} casos divergem do src/app.js']
        for e, o, x in difs[:limite]:
            linhas.append(f'  entrada={e!r}\n    python={o!r}\n    legado={x!r}')
        pytest.fail('\n'.join(linhas), pytrace=False)


def dados_brutos() -> dict:
    return json.loads((RAIZ / 'dados' / 'data.json').read_text(encoding='utf-8'))
