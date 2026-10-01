"""anonimizar_texto x scrub do src/app.js (executado no Node)."""
import re
import unicodedata

import pytest

from backend.services import anonimizacao
from backend.services.anonimizacao import ResultadoAnonimizacao, anonimizar_texto
from backend.services.texto import regex_js
from backend.tests.paridade import oraculo
from backend.tests.paridade.corpus import (CASOS_MANUAIS, DOCUMENTOS, EMAILS, ENDERECOS, NOMES, PERFIS, PLACAS,
                                          TELEFONES, gerar_corpus)

FRAGMENTOS = TELEFONES + DOCUMENTOS + EMAILS + PLACAS + PERFIS + ENDERECOS + NOMES
# o scrub do legado não é idempotente quando junta espaços: "casa  12" só vira "[número]" na segunda passada
# (a regra usa \s? e o espaço duplo só é juntado no fim). O porte mantém esse comportamento.
NAO_IDEMPOTENTES_CONHECIDOS = {'casa  12', 'se  chama Pedro', 'nº\N{FIGURE SPACE} 2', 'apelido\r\nde\r\nBaixinho',
                               '19\N{THIN SPACE}99876\N{THIN SPACE}\N{NO-BREAK SPACE}5432'}


def _py(s):
    r = anonimizar_texto(s)
    return {'text': r.texto, 'removed': r.removidos}


def padroes(*valores):
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
    js = oraculo.chamar('regexes', 'function scrub')
    assert len(js) == 9
    usados = padroes(*vars(anonimizacao).values())
    for r in js:
        p = regex_js(r['source'], r['flags'])
        assert (p.pattern, p.flags) in usados, r
    assert len(usados) == 9


def test_exemplos_legiveis():
    assert anonimizar_texto('me liga (19) 99876-5432') == ResultadoAnonimizacao('me liga [telefone]', ['telefone'])
    assert anonimizar_texto(None) == ResultadoAnonimizacao('', [])
    assert anonimizar_texto('') == ResultadoAnonimizacao('', [])
    r = anonimizar_texto('me liga +55 (19) 99876-5432 ou maria@x.com, chamado João Silva casa 12')
    assert r.texto == 'me liga [telefone] ou [e-mail], chamado [nome] [número]'
    assert r.removidos == ['e-mail', 'telefone', 'número de endereço', 'nome']
    assert anonimizar_texto('NÚMERO 7').texto == '[número]'
    assert anonimizar_texto('placa BRA2E19').removidos == ['placa']


def test_paridade_casos_manuais():
    entradas = CASOS_MANUAIS + FRAGMENTOS + [f'{a} {b}' for a in FRAGMENTOS[:40] for b in FRAGMENTOS[-40:]]
    oraculo.comparar(entradas, [_py(s) for s in entradas], oraculo.mapear('scrub', [[s] for s in entradas]), 'scrub (manual)')


def test_paridade_corpus_gerado():
    entradas = gerar_corpus(5000)
    oraculo.comparar(entradas, [_py(s) for s in entradas], oraculo.mapear('scrub', [[s] for s in entradas]), 'scrub (gerado)')


def test_flag_i_do_legado_com_letras_parecidas():
    # troca cada letra de "casa", "apto", "número"... por letras que o Python e o JS podem igualar sem ignorar caixa
    parecidas = set('ſıİKÅµßẞúÚùÙûÛüÜºª°oOº0' + 'nNcCaAsSpPtTeErRmMuUiIkK')
    for c in range(0x10000):
        ch = chr(c)
        if len(ch.upper()) == 1 and (ch.upper() in parecidas or ch.lower() in parecidas or ch.casefold() in parecidas):
            parecidas.add(ch)
    modelos = ['nº 1', 'no 2', 'n° 3', 'numero 4', 'número 5', 'casa 6', 'apto 7', 'apartamento 8', 'ap. 9']
    entradas = []
    for m in modelos:
        for i, letra in enumerate(m):
            if letra.isalpha() or letra in 'º°':
                entradas += [m[:i] + x + m[i + 1:] for x in sorted(parecidas)]
    oraculo.comparar(entradas, [_py(s) for s in entradas], oraculo.mapear('scrub', [[s] for s in entradas]), 'scrub (flag i)')


def test_espacos_unicode_e_nfd():
    base = ['chamado João Silva', 'casa 12', '+55 (19) 99876-5432', '@maria.silva', ' @ab_c ', 'nº 45']
    espacos = [chr(c) for c in range(0x10000) if unicodedata.category(chr(c)) in ('Zs', 'Zl', 'Zp', 'Cc', 'Cf')][:400]
    entradas = [b.replace(' ', e) for b in base for e in espacos] + [unicodedata.normalize('NFD', s) for s in CASOS_MANUAIS]
    oraculo.comparar(entradas, [_py(s) for s in entradas], oraculo.mapear('scrub', [[s] for s in entradas]), 'scrub (espaços)')


def test_idempotencia():
    entradas = CASOS_MANUAIS + FRAGMENTOS
    for s in entradas:
        uma = anonimizar_texto(s).texto
        assert anonimizar_texto(uma).texto == uma, s
    for s in NAO_IDEMPOTENTES_CONHECIDOS:
        uma = anonimizar_texto(s).texto
        duas = anonimizar_texto(uma).texto
        assert duas != uma
        assert anonimizar_texto(duas).texto == duas
    # e a dupla passada é igual à do legado em todo o corpus
    todos = entradas + gerar_corpus(3000, semente=5)
    obtidos = [_py(anonimizar_texto(s).texto) for s in todos]
    oraculo.comparar(todos, obtidos, oraculo.mapear('scrub2', [[s] for s in todos]), 'scrub(scrub(x))')


def test_legado_tambem_nao_e_idempotente_nos_casos_conhecidos():
    for s in NAO_IDEMPOTENTES_CONHECIDOS:
        js1 = oraculo.chamar('scrub', s)['text']
        assert oraculo.chamar('scrub', js1)['text'] != js1
