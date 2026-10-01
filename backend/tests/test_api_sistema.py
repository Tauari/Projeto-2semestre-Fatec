"""/saude, /config, /usuarios/eu, /moderacao e /ia/provedor."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.models.vocabulario import PERIODOS, QUANDO, TIPOS, vocabulario_publico

API = '/api/v1'
RAIZ = Path(__file__).resolve().parents[2]
VOCABULARIO_JS = RAIZ / 'frontend' / 'shared' / 'vocabulario.js'


def test_saude(cliente):
    r = cliente.get(API + '/saude')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok', 'versao': '0.1.0'}


def test_config_formato(cliente):
    cfg = cliente.get(API + '/config').json()
    assert list(cfg) == ['versao_api', 'vocabulario', 'relatos', 'ia', 'conjuntos_padrao', 'modulos']
    assert cfg['versao_api'] == '1'
    assert cfg['vocabulario'] == vocabulario_publico()
    assert cfg['relatos'] == {'janela_dias': 30, 'tipos_max': 4, 'texto_max': 300, 'precisao_criado': 'exata'}
    assert cfg['ia'] == {'provedor': 'heuristica', 'usa_modelo': False}
    assert cfg['conjuntos_padrao'] == {'dado_oficial': 'bo-ssp-2025-2026', 'percepcao': 'pesquisa-percepcao-2026'}
    assert cfg['modulos'] == {'relatos': True, 'apoio': True, 'dados_oficiais': True, 'percepcao': True, 'dashboard': True,
                              'ia': True, 'moderacao': False, 'usuarios': False, 'relatorios': False}


def test_config_vocabulario_na_ordem_do_backend(cliente):
    voc = cliente.get(API + '/config').json()['vocabulario']
    assert [t['id'] for t in voc['tipos']] == [t.id for t in TIPOS]
    assert [p['id'] for p in voc['periodos']] == [p.id for p in PERIODOS]
    assert list(voc['quando']) == list(QUANDO)
    assert voc['tipos'][0] == {'id': 'assedio', 'label': 'Assédio verbal', 'long': None}
    assert voc['periodos'][0] == {'id': 'manha', 'label': 'Manhã', 'long': 'Manhã (6h–12h)', 'from': 6, 'to': 12}
    assert voc['quando'] == {'hoje': 'hoje', 'ontem': 'ontem', 'semana': 'nesta semana', 'antes': 'há mais de uma semana'}


def _bloco(fonte: str, nome: str, abre: str, fecha: str) -> str:
    inicio = fonte.index(f'export const {nome} = {abre}')
    return fonte[inicio:fonte.index(fecha, inicio)]


def test_config_vocabulario_igual_ao_frontend(cliente):
    if not VOCABULARIO_JS.is_file():
        pytest.skip('frontend/shared/vocabulario.js ainda não existe')
    fonte = VOCABULARIO_JS.read_text(encoding='utf-8')
    voc = cliente.get(API + '/config').json()['vocabulario']
    assert re.findall(r"\{\s*id:\s*'([^']+)'", _bloco(fonte, 'TIPOS', '[', '];')) == [t['id'] for t in voc['tipos']]
    assert re.findall(r"\{\s*id:\s*'([^']+)'", _bloco(fonte, 'PERIODOS', '[', '];')) == [p['id'] for p in voc['periodos']]
    assert re.findall(r"(\w+):\s*'", _bloco(fonte, 'QUANDO', '{', '};')) == list(voc['quando'])


def test_config_vocabulario_igual_ao_frontend_no_node(cliente):
    """Com o Node, compara também rótulos, textos longos e horas (o módulo do frontend é executado de verdade)."""
    node = shutil.which('node')
    if not node or not VOCABULARIO_JS.is_file():
        pytest.skip('Node.js ou frontend/shared/vocabulario.js indisponível')
    script = ("import { readFileSync } from 'node:fs';"
              "const m = await import('data:text/javascript;base64,' + Buffer.from(readFileSync(process.argv[1], 'utf8')).toString('base64'));"
              "process.stdout.write(JSON.stringify({tipos: m.TIPOS.map(t => ({id: t.id, label: t.label, long: t.long ?? null})),"
              " periodos: m.PERIODOS, quando: m.QUANDO}));")
    proc = subprocess.run([node, '--input-type=module', '-e', script, str(VOCABULARIO_JS)], capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode('utf-8', 'replace')
    do_frontend = json.loads(proc.stdout.decode('utf-8'))
    voc = cliente.get(API + '/config').json()['vocabulario']
    assert json.dumps(do_frontend, ensure_ascii=False) == json.dumps(voc, ensure_ascii=False)


def test_config_segue_as_configuracoes(criar_cliente):
    c = criar_cliente(relatos_janela_dias=7, relatos_tipos_max=2, relatos_texto_max=100)
    assert c.get(API + '/config').json()['relatos'] == {'janela_dias': 7, 'tipos_max': 2, 'texto_max': 100, 'precisao_criado': 'exata'}


def test_usuarios_eu(cliente):
    r = cliente.get(API + '/usuarios/eu')
    assert r.status_code == 200
    assert r.json() == {'autenticado': False, 'papeis': []}


@pytest.mark.parametrize('metodo', ['GET', 'POST', 'DELETE'])
def test_moderacao_501(cliente, metodo):
    r = cliente.request(metodo, API + '/moderacao')
    assert r.status_code == 501
    assert r.json() == {'detail': 'A moderação ainda não foi migrada para o servidor. Nesta fase ela continua local, no aparelho.'}


def test_ia_provedor(cliente):
    r = cliente.get(API + '/ia/provedor')
    assert r.status_code == 200
    assert r.json() == {'nome': 'heuristica', 'usa_modelo': False, 'modelo': None, 'capacidades': ['extrair', 'classificar'],
                        'nao_implementado': ['analise_padroes', 'analise_agregada', 'relatorios']}


def test_provedor_desconhecido_falha_na_inicializacao(configurar):
    from fastapi.testclient import TestClient

    from backend.main import create_app

    configurar(ia_provedor='gpt-qualquer')
    with pytest.raises(ValueError, match='Provedor de IA desconhecido'):
        with TestClient(create_app()):
            pass


def test_docs_ficam_dentro_da_api(cliente):
    r = cliente.get(API + '/openapi.json')
    assert r.status_code == 200
    caminhos = r.json()['paths']
    for p in ('/saude', '/config', '/mapa/geografia', '/mapa/base', '/relatos', '/relatos/{relato_id}', '/dados-oficiais',
              '/dados-oficiais/{chave}', '/percepcao', '/percepcao/{chave}', '/apoio', '/dashboard/resumo', '/ia/provedor',
              '/ia/extrair', '/usuarios/eu', '/moderacao'):
        assert API + p in caminhos
    assert all(c.startswith(API + '/') for c in caminhos)
