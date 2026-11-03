"""frontend/relatos/acessorios.js: só roupas e acessórios saem do texto do relato; nada de característica física nem dado pessoal.

O módulo é JavaScript puro (sem DOM), então roda no Node, o mesmo que os testes de paridade já usam."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'


@pytest.fixture(scope='module')
def modulo(tmp_path_factory) -> Path:
    """O repositório não tem package.json com "type": "module", então o Node leria os .js como CommonJS.
    As duas cópias com extensão .mjs (e o import apontando para a cópia) rodam como módulo ES, sem tocar nos originais."""
    pasta = tmp_path_factory.mktemp('acessorios')
    (pasta / 'formato.mjs').write_text((FRONTEND / 'shared' / 'formato.js').read_text(encoding='utf-8'), encoding='utf-8')
    fonte = (FRONTEND / 'relatos' / 'acessorios.js').read_text(encoding='utf-8')
    assert "'../shared/formato.js'" in fonte
    (pasta / 'acessorios.mjs').write_text(fonte.replace("'../shared/formato.js'", "'./formato.mjs'"), encoding='utf-8')
    return pasta / 'acessorios.mjs'


@pytest.fixture
def _acessorios(modulo):
    def chamar(textos: list[str]) -> list[list[str]]:
        codigo = (f"import {{ acessorios }} from {json.dumps(modulo.as_uri())};\n"
                  "const textos = JSON.parse(process.argv[1]);\n"
                  "console.log(JSON.stringify(textos.map(t => acessorios(t))));")
        r = subprocess.run(['node', '--input-type=module', '-e', codigo, json.dumps(textos)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    return chamar


@pytest.mark.parametrize('texto, esperado', [
    ('Fui assediada por um homem de camiseta preta e calça roxa', ['camiseta preta', 'calça roxa']),
    ('Um cara de boina verde e moto preta me seguiu', ['boina verde']),
    ('calça jeans e tênis branco', ['calça jeans', 'tênis branco']),
    ('uma camisa de cor azul', ['camisa de cor azul']),
    ('de capacete e mochila', ['capacete', 'mochila']),
    ('de óculos escuros', ['óculos escuros']),
    ('CAMISETA   PRETA', ['CAMISETA PRETA']),
    ('', []),
    ('Fui assediada.', []),
])
def test_roupas_e_acessorios(_acessorios, texto, esperado):
    assert _acessorios([texto]) == [esperado]


def test_caracteristicas_fisicas_e_dados_pessoais_nunca_saem(_acessorios):
    texto = ('Homem alto, careca, cabelo preto, pele branca, barba grande, tatuagem azul no braço, uns 30 anos, '
             'se chama João Silva, telefone 19 99999-1234, placa ABC1D23, de camiseta branca')
    (saida,) = _acessorios([texto])
    assert saida == ['camiseta branca']
    for proibido in ('alto', 'careca', 'cabelo', 'pele', 'barba', 'tatuagem', 'anos', 'João', 'Silva', '99999', 'ABC1D23'):
        assert not any(proibido.lower() in s.lower() for s in saida), proibido


@pytest.mark.parametrize('texto', ['ele não estava de boné', 'sem capuz e sem máscara', 'não usava camiseta preta'])
def test_negado_nao_conta(_acessorios, texto):
    assert _acessorios([texto]) == [[]]


def test_sem_repeticao_e_no_maximo_5(_acessorios):
    (rep,) = _acessorios(['camiseta preta, camiseta preta e calça roxa'])
    assert rep == ['camiseta preta', 'calça roxa']
    (muitas,) = _acessorios(['camiseta preta, calça roxa, boné azul, tênis branco, mochila verde, óculos escuros, capuz cinza'])
    assert len(muitas) == 5 and muitas[0] == 'camiseta preta'
