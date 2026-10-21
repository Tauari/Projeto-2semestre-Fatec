"""Provedores de IA, registro e prompts.py x aiExtract/heuristic do src/app.js."""
import sys
import types

import pytest

from backend.services.classificacao import bairros_de_lista
from backend.services.ia import (CapacidadeNaoImplementada, ContextoIA, ProvedorHeuristico, ProvedorIA,
                                 ResultadoClassificacao, ResultadoExtracao, obter_provedor, provedores_disponiveis,
                                 registrar_provedor)
from backend.services.ia import registro
from backend.services.ia.prompts import _string_js, montar_prompt_extracao, validar_saida_extracao
from backend.tests.paridade import oraculo
from backend.tests.paridade.corpus import CASOS_MANUAIS, gerar_corpus, objetos_saida_ia, textos_longos


@pytest.fixture(scope='module')
def bairros():
    return bairros_de_lista(oraculo.dados_brutos()['bairros'])


def _res(r):
    if r is None:
        return None
    return {'urgente': r.urgente, 'tipos': r.tipos, 'bairro': r.bairro.nome if r.bairro else None, 'quando': r.quando,
            'periodo': r.periodo, 'descricao': r.descricao, 'removidos': r.removidos, 'resposta': r.resposta}


def _sem_from_ai(lista, esperado):
    saida = []
    for r in lista:
        if r is not None:
            assert r.pop('fromAI') is esperado
        saida.append(r)
    return saida


# ------------------------------------------------------------------ prompt de aiExtract

def test_prompt_identico_ao_legado_byte_a_byte(bairros):
    nomes = [b.nome for b in bairros]
    textos = CASOS_MANUAIS + textos_longos() + gerar_corpus(300, semente=41) + ['', '"""', '""""', '"""""', 'a"""b"""c']
    js = oraculo.mapear('aiPrompt', [[t] for t in textos])
    for t, esperado in zip(textos, js):
        obtido = montar_prompt_extracao(t, nomes)
        assert obtido.encode('utf-8', 'surrogatepass') == esperado.encode('utf-8', 'surrogatepass'), repr(t)[:80]


def test_prompt_com_outras_listas_de_bairros():
    for lista in ([], [['A', 0, 0, 0]], [['X; Y', 0, 0, 0], ['Ümlaut', 1, 1, 1], ['', 2, 2, 2]]):
        textos = ['oi', 'x' * 1600]
        js = oraculo.mapear('aiPrompt', [[t] for t in textos], bairros=lista)
        assert [montar_prompt_extracao(t, [b[0] for b in lista]) for t in textos] == js


# ------------------------------------------------------------------ normalização da saída do modelo

def test_validar_saida_igual_ao_legado(bairros):
    objetos = objetos_saida_ia()
    js = _sem_from_ai(oraculo.mapear('aiSaida', [[o] for o in objetos]), True)
    oraculo.comparar(objetos, [_res(validar_saida_extracao(o, bairros)) for o in objetos], js, 'validar_saida_extracao')


def test_validar_saida_desvios_documentados(bairros):
    # no JS, TIPO['constructor'] e QUANDO[['hoje']] passavam por herança/conversão; o porte só aceita ids próprios
    o = {'tipos': ['constructor', 'assedio', '__proto__', 'toString'], 'quando': ['hoje'], 'periodo': ['manha']}
    js = oraculo.chamar('aiSaida', o)
    assert js['tipos'] == ['constructor', 'assedio', '__proto__']
    assert js['quando'] == ['hoje'] and js['periodo'] == ['manha']
    r = validar_saida_extracao(o, bairros)
    assert r.tipos == ['assedio'] and r.quando is None and r.periodo is None


def test_string_js():
    valores = [None, True, False, 0, -0.0, 1, 1.0, 0.1 + 0.2, 1e21, 1e-7, 1e-6, 123456789012345680000, 2 ** 53 + 1, 1.5e300,
               -12.5, 5e-324, 1.7976931348623157e308, 10 ** 400, [1, [2, None], 'a'], {'a': 1}, [], [None], 'x']
    # String(x) do JS, visto pelo corte de 30 de "removidos"
    js = [r['removidos'][0] for r in oraculo.mapear('aiSaida', [[{'removidos': [v]}] for v in valores])]
    assert [_string_js(v)[:30] for v in valores] == js


# ------------------------------------------------------------------ provedor heurístico

def test_provedor_heuristico_igual_a_heuristic(bairros):
    p = ProvedorHeuristico()
    ctx = ContextoIA(bairros=bairros)
    textos = CASOS_MANUAIS + textos_longos() + gerar_corpus(1000, semente=43)
    js = _sem_from_ai(oraculo.mapear('heuristic', [[t] for t in textos]), False)  # texto inteiro, como no chat
    oraculo.comparar(textos, [_res(p.extrair(t, ctx)) for t in textos], js, 'ProvedorHeuristico.extrair')


def test_provedor_heuristico_classificar(bairros):
    p = ProvedorHeuristico()
    ctx = ContextoIA(bairros=bairros)
    texto = 'ontem às 22h um cara me seguiu de moto perto da Unesp, estou em perigo'
    r = p.classificar(texto, ctx)
    assert r == ResultadoClassificacao(tipos=['perseguicao', 'veiculo'], urgente=True, quando='ontem', periodo='22-00', confianca=None)
    e = p.extrair(texto, ctx)
    assert isinstance(e, ResultadoExtracao) and e.bairro.nome == 'Bela Vista'
    # como no legado, "socorro" contém "soco" e também marca violência física
    assert p.classificar('socorro', ctx).tipos == ['violencia'] == oraculo.chamar('heuristic', 'socorro')['tipos']


def test_info_do_provedor():
    assert ProvedorHeuristico().info() == {
        'nome': 'heuristica', 'usa_modelo': False, 'modelo': None, 'capacidades': ['extrair', 'classificar'],
        'nao_implementado': ['analise_padroes', 'analise_agregada', 'relatorios'],
    }


def test_capacidades_futuras_nao_fingem_que_existem():
    p = ProvedorHeuristico()
    with pytest.raises(CapacidadeNaoImplementada):
        p.analisar_padroes([])
    with pytest.raises(NotImplementedError):
        p.gerar_relatorio()
    assert issubclass(CapacidadeNaoImplementada, NotImplementedError)
    with pytest.raises(TypeError):
        ProvedorIA()


# ------------------------------------------------------------------ registro

def test_registro_padrao():
    assert 'heuristica' in provedores_disponiveis()
    assert isinstance(obter_provedor('heuristica'), ProvedorHeuristico)
    assert obter_provedor().nome == 'heuristica'
    with pytest.raises(ValueError, match='desconhecido'):
        obter_provedor('gpt-qualquer')


def test_registro_sem_config_usa_heuristica(monkeypatch):
    monkeypatch.setitem(sys.modules, 'backend.config', None)  # import falha com ImportError
    assert obter_provedor().nome == 'heuristica'


def test_registro_le_a_configuracao(monkeypatch):
    class Falso(ProvedorHeuristico):
        nome = 'falso'
    falso = types.ModuleType('backend.config')
    falso.obter_configuracoes = lambda: types.SimpleNamespace(ia_provedor='falso')
    monkeypatch.setitem(sys.modules, 'backend.config', falso)
    monkeypatch.setattr(registro, '_FABRICAS', dict(registro._FABRICAS))
    with pytest.raises(ValueError):
        obter_provedor()
    registrar_provedor('falso', Falso)
    assert obter_provedor().nome == 'falso'
    assert provedores_disponiveis() == ['heuristica', 'ollama', 'falso']
