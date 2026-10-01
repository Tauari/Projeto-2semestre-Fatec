"""services/texto.py contra o JS: norm do src/app.js e os métodos nativos que o legado usa (slice, trim, regex)."""
import re
import unicodedata

import pytest

from backend.services.texto import S_JS, aparar_js, comprimento_js, fatiar_js, normalizar, regex_js
from backend.services.classificacao import esc_re
from backend.tests.paridade import oraculo
from backend.tests.paridade.corpus import CASOS_MANUAIS, EMOJIS, ESPACOS_UNICODE, gerar_corpus


@pytest.fixture(scope='module')
def corpus():
    return CASOS_MANUAIS + gerar_corpus(1500, semente=11)


def test_normalizar_basico():
    assert normalizar('Chácara Lusa') == 'chacara lusa'
    assert normalizar('VILA OPERÁRIA') == 'vila operaria'
    assert normalizar(None) == ''
    assert normalizar('') == ''
    assert normalizar(0) == ''


def test_normalizar_todos_os_caracteres_um_a_um():
    faixas = [(0, 0x10000), (0x10000, 0x20000), (0x20000, 0x20200), (0x2F800, 0x2FA20), (0xE0000, 0xE0200), (0x10FF00, 0x110000)]
    esperado = oraculo.consultar([{'fn': 'normFaixa', 'args': [a, b]} for a, b in faixas])
    for (a, b), js in zip(faixas, esperado):
        # letras que só existem no Unicode do Node (17, ICU 78) e ainda não no do Python (16) ficam de fora
        pares = [(cp, x) for cp, x in zip(range(a, b), js) if unicodedata.category(chr(cp)) != 'Cn' or normalizar(chr(cp)) == x]
        entradas = [f'U+{cp:04X}' for cp, _ in pares]
        obtidos = [normalizar(chr(cp)) for cp, _ in pares]
        oraculo.comparar(entradas, obtidos, [x for _, x in pares], 'normalizar x norm (um caractere)')
        assert len(pares) >= (b - a) - 64


def test_normalizar_frases(corpus):
    extras = ['ΣΑΣ ΟΔΟΣ ΜΑΣ.', 'ΌΣΟΣ', 'Σ', 'aΣ', 'aΣb', 'aΣ.', 'ǅemal', 'İİ', 'ẞ', 'ﬁ', 'Å', 'K']
    entradas = corpus + extras
    oraculo.comparar(entradas, [normalizar(s) for s in entradas], oraculo.mapear('norm', [[s] for s in entradas]), 'normalizar x norm')


def test_norm_nulo_igual_ao_legado():
    assert oraculo.chamar('norm', None) == normalizar(None) == ''


def test_fatiar_e_comprimento(corpus):
    entradas, args = [], []
    for s in corpus[:600] + ['😡' * 5, 'a😡', '😡a', '', '\U0010ffff']:
        u = comprimento_js(s)
        for n in sorted({0, 1, 2, 3, u - 1, u, u + 1, u // 2, 299, 300, 301, -1, -2, -u - 1}):
            entradas.append((s, n))
            args.append([s, n])
    obtidos = [fatiar_js(s, n) for s, n in entradas]
    oraculo.comparar(entradas, obtidos, oraculo.mapear('slice', args), 'fatiar_js x slice')
    oraculo.comparar(corpus, [comprimento_js(s) for s in corpus], oraculo.mapear('length', [[s] for s in corpus]), 'comprimento_js x length')


def test_fatiar_deixa_substituto_solto_como_o_js():
    s = 'ab😡'
    assert fatiar_js(s, 3) == 'ab' + chr(0xD83D)
    assert fatiar_js(s, 4) == s
    assert fatiar_js(s, 2) == 'ab'


def test_conjunto_de_espacos_igual_ao_js():
    js = oraculo.chamar('espacos')
    s_py = [c for c in range(0x10000) if re.fullmatch(S_JS, chr(c))]
    assert s_py == js['s']
    trim_py = [c for c in range(0x10000) if aparar_js(chr(c)) == '']
    assert trim_py == js['trim']


def test_aparar(corpus):
    entradas = corpus + [e + 'x' + e for e in ESPACOS_UNICODE] + [''.join(ESPACOS_UNICODE)]
    oraculo.comparar(entradas, [aparar_js(s) for s in entradas], oraculo.mapear('trim', [[s] for s in entradas]), 'aparar_js x trim')


# regex de um caractere: o conjunto de unidades UTF-16 que casam tem de ser igual ao do JS
CONJUNTOS = [
    (r'^\s$', ''), (r'^\S$', ''), (r'^[-\s.]$', ''), (r'^.$', ''), (r'^[uú]$', 'i'), (r'^[ºo°]$', 'i'), (r'^n$', 'i'),
    (r'^[A-ZÀ-Ý]$', ''), (r'^[\wÀ-ÿ]$', ''), (r'^\w$', ''), (r'^\d$', ''), (r'^[a-z]$', 'i'), (r'^s$', 'i'), (r'^k$', 'i'),
    (r'^i$', 'i'), (r'^é$', 'i'), (r'^[^a-z0-9]$', ''), (r'^\b.$', ''), (r'^[\s\d]$', ''), (r'^Ω$', 'i'), (r'^[ſµ]$', 'i'),
    (r'^\W$', ''), (r'^\D$', ''),
]


@pytest.mark.parametrize('fonte,flags', CONJUNTOS)
def test_regex_js_conjuntos(fonte, flags):
    js = oraculo.chamar('regexConjunto', fonte, flags)
    p = regex_js(fonte, flags)
    assert [c for c in range(0x10000) if p.search(chr(c))] == js


def test_regex_js_fim_e_ponto():
    casos = ['a', 'a\n', 'a\r', 'a\N{LINE SEPARATOR}', '\n', 'ab', '']
    for fonte in [r'a$', r'^a.?$', r'^.*$', r'(^|x)a($|y)']:
        assert [bool(regex_js(fonte).search(s)) for s in casos] == oraculo.chamar('regexTeste', fonte, '', casos)


def test_regex_js_recusa_o_que_nao_sabe_traduzir():
    for fonte, flags in [(r'a', 'm'), (r'a', 'u'), (r'[\S]', ''), (r'[À-Ý]', 'i')]:
        with pytest.raises(ValueError):
            regex_js(fonte, flags)


def test_esc_re():
    entradas = ['a.b*c+d?e^f$g{h}i(j)k|l[m]n\\o', 'Vila (Nova)', 'São João.', '', '$', '\\\\', 'a-b', '/']
    oraculo.comparar(entradas, [esc_re(s) for s in entradas], oraculo.mapear('escRe', [[s] for s in entradas]), 'esc_re x escRe')


def test_emojis_e_astrais():
    for e in EMOJIS:
        assert fatiar_js(e, comprimento_js(e)) == e
