"""classificacao.py e models/vocabulario.py x heuristic, findBairroInText, matchBairro, TIPOS... do src/app.js."""
import re
import unicodedata

import pytest

from backend.models import vocabulario
from backend.models.vocabulario import (PERIODOS, PERIODOS_POR_ID, QUANDO, TIPOS, TIPOS_POR_ID, TipoEvidencia,
                                        periodo_da_hora, vocabulario_publico)
from backend.services import classificacao
from backend.services.classificacao import (Bairro, bairros_de_lista, casar_bairro, classificar_tipos,
                                            encontrar_bairro_no_texto, extrair_campos)
from backend.services.texto import regex_js
from backend.tests.paridade import oraculo
from backend.tests.paridade.corpus import (BAIRROS_FRASES, CASOS_MANUAIS, HORA_FRASES, NOMES, QUANDO_FRASES,
                                          SITUACOES, URGENCIAS, gerar_corpus, nomes_bairros)


@pytest.fixture(scope='module')
def bairros():
    return bairros_de_lista(oraculo.dados_brutos()['bairros'])


def _py(e):
    return {'urgente': e.urgente, 'tipos': e.tipos, 'bairro': e.bairro.nome if e.bairro else None, 'quando': e.quando,
            'periodo': e.periodo, 'descricao': e.descricao, 'removidos': e.removidos, 'resposta': e.resposta}


def _js(lista):
    saida = []
    for r in lista:
        assert r.pop('fromAI') is False
        saida.append(r)
    return saida


def _padroes(*valores):
    achados = set()

    def visitar(v):
        if isinstance(v, re.Pattern):
            achados.add((v.pattern, v.flags))
        elif isinstance(v, (tuple, list)):
            for x in v:
                visitar(x)
    for v in valores:
        visitar(v)
    return achados


def test_regex_sao_copias_literais_do_legado():
    usados = _padroes(*vars(classificacao).values())
    for decl in ('function heuristic', 'const LANDMARKS', 'function findBairroInText', 'function matchBairro', 'const escRe'):
        for r in oraculo.chamar('regexes', decl):
            p = regex_js(r['source'], r['flags'])
            assert (p.pattern, p.flags) in usados, (decl, r)
    kw_js = [t['kw'] for t in oraculo.chamar('vocabulario')['tipos'] if t['kw']]
    kw_py = [t.kw for t in TIPOS if t.kw]
    assert [(p.pattern, p.flags) for p in kw_py] == [(regex_js(k['source'], k['flags']).pattern, regex_js(k['source'], k['flags']).flags) for k in kw_js]


def test_vocabulario_igual_ao_legado():
    js = oraculo.chamar('vocabulario')
    assert [(t.id, t.label, t.long) for t in TIPOS] == [(t['id'], t['label'], t['long']) for t in js['tipos']]
    assert [(p.id, p.label, p.long, p.inicio, p.fim) for p in PERIODOS] == [(p['id'], p['label'], p['long'], p['from'], p['to']) for p in js['periodos']]
    assert list(QUANDO.items()) == list(js['quando'].items())
    assert list(TIPOS_POR_ID) == js['tipoIds']
    assert list(PERIODOS_POR_ID) == js['perIds']
    pub = vocabulario_publico()
    assert pub['tipos'] == [{'id': t['id'], 'label': t['label'], 'long': t['long']} for t in js['tipos']]
    assert pub['periodos'] == js['periodos']
    assert list(pub['quando'].items()) == list(js['quando'].items())
    assert vocabulario.ORIGENS_RELATO == ('chat', 'chat-ia')
    assert TipoEvidencia.CLASSIFICACAO_AUTOMATICA == 'classificacao_automatica'
    assert [e.value for e in TipoEvidencia] == ['relato_comunidade', 'dado_oficial', 'percepcao', 'classificacao_automatica', 'analise_ia']


def test_periodo_da_hora():
    horas = list(range(-3, 30))
    assert [periodo_da_hora(h) for h in horas] == oraculo.mapear('periodOfHour', [[h] for h in horas])


def test_bairros_de_lista_igual_a_linha_107(bairros):
    js = oraculo.chamar('bairros')
    assert [(b.nome, b.lat, b.lng, b.n, b.key) for b in bairros] == [(b['nome'], b['lat'], b['lng'], b['n'], b['key']) for b in js]
    assert all(isinstance(b, Bairro) for b in bairros)


def _entradas_manuais():
    bairros = nomes_bairros()
    variantes = []
    for nome in bairros:
        sem = ''.join(c for c in unicodedata.normalize('NFD', nome) if not unicodedata.combining(c))
        variantes += [nome, nome.upper(), sem, sem.lower(), f'perto do {nome}, ontem', f'no{nome}', f'{nome}x', f'({nome})']
    frases = [f'{a} {b} {c}' for a in SITUACOES[:12] for b in HORA_FRASES[:20] for c in QUANDO_FRASES[:6]]
    return CASOS_MANUAIS + BAIRROS_FRASES + QUANDO_FRASES + HORA_FRASES + SITUACOES + URGENCIAS + NOMES + variantes + frases


def test_extrair_campos_casos_manuais(bairros):
    entradas = _entradas_manuais()
    oraculo.comparar(entradas, [_py(extrair_campos(s, bairros)) for s in entradas],
                     _js(oraculo.mapear('heuristic', [[s] for s in entradas])), 'extrair_campos x heuristic (manual)')


def test_extrair_campos_corpus_gerado(bairros):
    entradas = gerar_corpus(5000, semente=31)
    oraculo.comparar(entradas, [_py(extrair_campos(s, bairros)) for s in entradas],
                     _js(oraculo.mapear('heuristic', [[s] for s in entradas])), 'extrair_campos x heuristic (gerado)')


def test_extrair_campos_nulo(bairros):
    e = extrair_campos(None, bairros)
    assert _py(e) == _js([oraculo.chamar('heuristic', None)])[0]


def test_classificar_tipos_igual_aos_tipos_da_heuristica(bairros):
    entradas = _entradas_manuais() + gerar_corpus(1000, semente=3)
    assert [classificar_tipos(s) for s in entradas] == [extrair_campos(s, bairros).tipos for s in entradas]


def test_encontrar_bairro_no_texto(bairros):
    entradas = _entradas_manuais() + gerar_corpus(2000, semente=17)
    obtidos = [(lambda b: b.nome if b else None)(encontrar_bairro_no_texto(s, bairros)) for s in entradas]
    oraculo.comparar(entradas, obtidos, oraculo.mapear('findBairroInText', [[s] for s in entradas]), 'encontrar_bairro_no_texto')


def test_casar_bairro(bairros):
    curtos = ['', ' ', '\N{NO-BREAK SPACE}', 'a', 'jardim', 'vila', 'centro', 'Centro ', ' bela', 'claret', 'nova', 'são',
              'sao', 'II', 'bnh', 'BNH', 'jardim progresso ii', 'Jardim Progresso III', 'Wenzel', 'wenzel novo', 'unesp',
              'Lago Azul', 'rodoviária', 'estação', 'zona central', 'Zona Norte', 'Bela Vista (Unesp)', 'Jd. Claret',
              'Vl. Operária', 'Chácara', 'Parque', 'cidade', 'santa', 'Rio Claro', 'Jardim Rio Claro, perto do centro']
    entradas = curtos + BAIRROS_FRASES + nomes_bairros() + [s[:12] for s in gerar_corpus(800, semente=23)]
    obtidos = [(lambda b: b.nome if b else None)(casar_bairro(s, bairros)) for s in entradas]
    oraculo.comparar(entradas, obtidos, oraculo.mapear('matchBairro', [[s] for s in entradas]), 'casar_bairro x matchBairro')


BAIRROS_ESTRANHOS = [['Vila (Nova)', 1.0, 2.0, 3], ['São João.', 1, 2, 3], ['a+b*c', 1, 2, 3], ['C$ntro', 1, 2, 3],
                     ['[x]', 1, 2, 3], ['Jardim\\Barra', 1, 2, 3], ['abc', 1, 2, 3], ['Bela Vista', 1, 2, 3],
                     ['Bela Vista', 5, 6, 7], ['', 0, 0, 0], ['Centro', 9, 9, 9], ['Zona  Central', 1, 1, 1],
                     ['Ümlaut Ñ', 1, 1, 1], ['x|y', 1, 1, 1], ['ab{2}', 1, 1, 1], ['^inicio', 1, 1, 1], ['fim$', 1, 1, 1],
                     ['ponto.com', 1, 1, 1], ['Estação', 1, 1, 1]]


def test_bairros_com_caracteres_especiais():
    bairros = bairros_de_lista(BAIRROS_ESTRANHOS)
    textos = ['vila (nova)', 'vila nova', 'sao joao.', 'sao joaox', 'a+b*c', 'aab*c', 'c$ntro', 'centro', '[x]', 'x',
              'jardim\\barra', 'abc', 'bela vista', 'fim$', 'fim', '^inicio', 'inicio', 'ab{2}', 'abb', 'x|y', 'x', 'y',
              'ponto.com', 'pontoxcom', 'estacao', 'unesp', 'lago azul', 'zona  central', 'zona central', 'umlaut n', '',
              ' ', 'jardim']
    oraculo.comparar(textos, [(lambda b: b.nome if b else None)(encontrar_bairro_no_texto(s, bairros)) for s in textos],
                     oraculo.mapear('findBairroInText', [[s] for s in textos], bairros=BAIRROS_ESTRANHOS), 'bairros estranhos (find)')
    oraculo.comparar(textos, [(lambda b: b.nome if b else None)(casar_bairro(s, bairros)) for s in textos],
                     oraculo.mapear('matchBairro', [[s] for s in textos], bairros=BAIRROS_ESTRANHOS), 'bairros estranhos (match)')
    oraculo.comparar(textos, [_py(extrair_campos(s, bairros)) for s in textos],
                     _js(oraculo.mapear('heuristic', [[s] for s in textos], bairros=BAIRROS_ESTRANHOS)), 'bairros estranhos (heuristic)')
    # BYNAME: o último "Bela Vista" vence, como no Object.fromEntries
    assert encontrar_bairro_no_texto('perto da unesp', bairros).lat == 5


def test_referencia_cujo_bairro_nao_existe_na_lista():
    # no legado, a primeira referência que casa decide, mesmo que o bairro dela não esteja na lista (devolve null)
    lista = [['Centro', 1, 1, 1], ['Vila Operária', 2, 2, 2], ['Zé', 3, 3, 3]]
    bairros = bairros_de_lista(lista)
    textos = ['unesp e centro', 'na rodoviaria do centro', 'lago azul no centro', 'estacao', 'zona central', 'centro',
              'unesp', 'jardim publico e lago azul', 'ze', 'nada', 'perto da unesp, no lago azul', 'rodoviaria e estacao',
              'unesp, zona central']
    oraculo.comparar(textos, [(lambda b: b.nome if b else None)(encontrar_bairro_no_texto(s, bairros)) for s in textos],
                     oraculo.mapear('findBairroInText', [[s] for s in textos], bairros=lista), 'referência sem bairro')
    assert encontrar_bairro_no_texto('perto da unesp, no lago azul', bairros) is None
    assert encontrar_bairro_no_texto('lago azul', bairros).nome == 'Vila Operária'
